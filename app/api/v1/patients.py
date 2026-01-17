"""Patient management endpoints for staff.

Provides CRUD operations for patient records with:
- Full patient details including related entities
- Audited updates with provenance tracking
- Record update history
- Role-based access control (RBAC)
- Reason-required validation for sensitive fields
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession, get_client_ip, require_permissions
from app.models.user import UserRole
from app.models.audit_event import ActorType
from app.services.rbac import Permission
from app.models.patient import (
    Patient,
    PatientAddress,
    PatientClinicalProfile,
    PatientContact,
    PatientIdentifier,
    PatientPreferences,
    PatientRecordUpdate,
    RecordUpdateActorType,
    RecordUpdateSource,
)
from app.schemas.patient import (
    PatientAddressCreate,
    PatientAddressRead,
    PatientAddressUpdate,
    PatientClinicalProfileRead,
    PatientClinicalProfileUpdate,
    PatientContactCreate,
    PatientContactRead,
    PatientContactUpdate,
    PatientDetailRead,
    PatientIdentifierCreate,
    PatientIdentifierRead,
    PatientIdentifierUpdate,
    PatientListResponse,
    PatientPreferencesRead,
    PatientPreferencesUpdate,
    PatientRead,
    PatientRecordUpdateRead,
    PatientSummary,
    PatientUpdate,
    PatientUpdateRequest,
)
from app.services.audit import write_audit_event

router = APIRouter(prefix="/patients", tags=["patients"])

# Fields that require a reason when changed (for audit/governance)
REASON_REQUIRED_FIELDS = {
    "first_name",
    "last_name",
    "date_of_birth",
    "email",
    "phone_e164",
    "primary_gp_contact_id",
    "emergency_contact_id",
}

ADMIN_ROLES = {UserRole.ADMIN, UserRole.CLINICAL_LEAD}
CLINICIAN_ROLES = {UserRole.CLINICIAN, UserRole.CLINICAL_LEAD}


def _ensure_role(user: CurrentUser, allowed_roles: set[UserRole], action: str) -> None:
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions to {action}",
        )


def _build_record_update_payload(
    entity: str,
    entity_id: str | None,
    old_data: dict | None,
    new_data: dict | None,
    changes: dict | None = None,
) -> dict:
    payload = {"entity": entity, "entity_id": entity_id, "old": old_data, "new": new_data}
    if changes:
        payload["changes"] = changes
    return payload


async def _sync_patient_postcode(session: DbSession, patient_id: str) -> dict | None:
    result = await session.execute(
        select(PatientAddress)
        .where(PatientAddress.patient_id == patient_id)
        .where(PatientAddress.is_primary == True)
        .order_by(PatientAddress.created_at.desc())
    )
    primary = result.scalars().first()
    postcode = primary.postcode if primary and primary.postcode else None

    if not postcode:
        result = await session.execute(
            select(PatientAddress)
            .where(PatientAddress.patient_id == patient_id)
            .where(PatientAddress.type == "current")
            .order_by(PatientAddress.created_at.desc())
        )
        current = result.scalars().first()
        postcode = current.postcode if current and current.postcode else None

    if postcode is None:
        return

    result = await session.execute(
        select(Patient).where(Patient.id == patient_id).where(Patient.is_deleted == False)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        return

    if patient.postcode != postcode:
        old_postcode = patient.postcode
        patient.postcode = postcode
        patient.updated_at = datetime.now(timezone.utc)
        return {"old": old_postcode, "new": postcode}

    return None


# =============================================================================
# Patient CRUD
# =============================================================================


@router.get("", response_model=PatientListResponse)
async def list_patients(
    user: CurrentUser,
    session: DbSession,
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
) -> PatientListResponse:
    """List all patients with pagination and optional search.

    Search matches against first_name, last_name, email, or NHS number.
    """
    # Build base query
    query = select(Patient).where(Patient.is_dummy == False)

    # Apply search filter if provided
    if search:
        search_term = f"%{search.lower()}%"
        query = query.where(
            (Patient.first_name.ilike(search_term)) |
            (Patient.last_name.ilike(search_term)) |
            (Patient.email.ilike(search_term)) |
            (Patient.nhs_number.ilike(search_term))
        )

    # Get total count
    count_query = select(func.count()).select_from(Patient).where(Patient.is_dummy == False)
    if search:
        search_term = f"%{search.lower()}%"
        count_query = count_query.where(
            (Patient.first_name.ilike(search_term)) |
            (Patient.last_name.ilike(search_term)) |
            (Patient.email.ilike(search_term)) |
            (Patient.nhs_number.ilike(search_term))
        )
    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(Patient.created_at.desc()).offset(offset).limit(page_size)

    result = await session.execute(query)
    patients = result.scalars().all()

    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PatientListResponse(
        items=[PatientSummary.model_validate(p) for p in patients],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{patient_id}", response_model=PatientDetailRead)
async def get_patient(
    patient_id: str,
    user: CurrentUser,
    session: DbSession,
) -> Patient:
    """Get full patient details by ID.

    Returns patient with all related entities (addresses, contacts,
    preferences, clinical profile, identifiers).
    """
    result = await session.execute(
        select(Patient)
        .where(Patient.id == patient_id)
        .where(Patient.is_deleted == False)
        .options(
            selectinload(Patient.addresses),
            selectinload(Patient.contacts),
            selectinload(Patient.preferences),
            selectinload(Patient.clinical_profile),
            selectinload(Patient.identifiers),
            selectinload(Patient.primary_gp_contact),
            selectinload(Patient.emergency_contact),
        )
    )
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    return patient


@router.patch(
    "/{patient_id}",
    response_model=PatientRead,
    dependencies=[Depends(require_permissions(Permission.PATIENTS_WRITE))],
)
async def update_patient(
    patient_id: str,
    body: PatientUpdateRequest,
    user: CurrentUser,
    session: DbSession,
    request: Request,
) -> Patient:
    """Update patient record with audit trail.

    Creates a provenance record tracking what changed and why.

    Permission: PATIENTS_WRITE (clinician, admin, clinical_lead, receptionist)

    Reason required for: first_name, last_name, date_of_birth
    """
    result = await session.execute(
        select(Patient)
        .where(Patient.id == patient_id)
        .where(Patient.is_deleted == False)
        .options(
            selectinload(Patient.addresses),
            selectinload(Patient.contacts),
            selectinload(Patient.preferences),
            selectinload(Patient.clinical_profile),
            selectinload(Patient.identifiers),
        )
    )
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    _ensure_role(user, ADMIN_ROLES, "edit patient identity or contact details")

    # Track changes for provenance
    changed_fields: dict = {}
    update_data = body.updates.model_dump(exclude_unset=True)

    allowed_fields = {
        "email",
        "first_name",
        "last_name",
        "preferred_name",
        "date_of_birth",
        "sex_at_birth",
        "gender_identity",
        "ethnicity",
        "preferred_language",
        "interpreter_required",
        "phone_e164",
        "preferred_contact_method",
        "can_leave_voicemail",
        "consent_to_sms",
        "consent_to_email",
        "has_dependents",
        "is_pregnant_or_postnatal",
        "reasonable_adjustments_required",
        "is_active",
        "primary_gp_contact_id",
        "emergency_contact_id",
    }

    invalid_fields = set(update_data.keys()) - allowed_fields
    if invalid_fields:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot edit fields: {', '.join(sorted(invalid_fields))}",
        )

    if "email" in update_data and update_data["email"]:
        result = await session.execute(
            select(Patient.id).where(Patient.email == update_data["email"])
        )
        existing = result.scalar_one_or_none()
        if existing and existing != patient_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email address is already in use",
            )

    if "primary_gp_contact_id" in update_data and update_data["primary_gp_contact_id"]:
        result = await session.execute(
            select(PatientContact).where(
                PatientContact.id == update_data["primary_gp_contact_id"]
            )
        )
        contact = result.scalar_one_or_none()
        if not contact or contact.patient_id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Primary GP contact must belong to this patient",
            )
        if contact.contact_type != "gp":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Primary GP contact must be of type gp",
            )

    if "emergency_contact_id" in update_data and update_data["emergency_contact_id"]:
        result = await session.execute(
            select(PatientContact).where(
                PatientContact.id == update_data["emergency_contact_id"]
            )
        )
        contact = result.scalar_one_or_none()
        if not contact or contact.patient_id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Emergency contact must belong to this patient",
            )
        if contact.contact_type != "emergency":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Emergency contact must be of type emergency",
            )

    for field, new_value in update_data.items():
        old_value = getattr(patient, field, None)
        if old_value != new_value:
            changed_fields[field] = {"old": old_value, "new": new_value}
            setattr(patient, field, new_value)

    if not changed_fields:
        # No actual changes
        return patient

    # Check if any changed fields require a reason
    sensitive_changes = set(changed_fields.keys()) & REASON_REQUIRED_FIELDS
    if sensitive_changes and not body.reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Reason required when changing: {', '.join(sensitive_changes)}",
        )

    # Update timestamp
    patient.updated_at = datetime.now(timezone.utc)

    # Create provenance record
    record_update = PatientRecordUpdate(
        id=str(uuid4()),
        patient_id=patient_id,
        actor_user_id=user.id,
        actor_type=RecordUpdateActorType.STAFF.value,
        source=RecordUpdateSource.STAFF_EDIT.value,
        changed_fields=changed_fields,
        reason=body.reason,
    )
    session.add(record_update)

    await session.commit()
    await session.refresh(patient)

    # Audit event
    client_ip = get_client_ip(request)
    await write_audit_event(
        session=session,
        actor_type=ActorType.STAFF,
        actor_id=user.id,
        actor_email=user.email,
        action="patient_updated",
        action_category="clinical",
        entity_type="patient",
        entity_id=patient_id,
        metadata={
            "changed_fields": list(changed_fields.keys()),
            "reason": body.reason,
        },
        ip_address=client_ip,
        user_agent=request.headers.get("User-Agent"),
    )

    return patient


@router.get("/{patient_id}/updates", response_model=list[PatientRecordUpdateRead])
async def get_patient_updates(
    patient_id: str,
    user: CurrentUser,
    session: DbSession,
    limit: int = 50,
    offset: int = 0,
) -> list[PatientRecordUpdate]:
    """Get patient record update history.

    Returns provenance log of all changes to the patient record.
    """
    # Verify patient exists
    result = await session.execute(
        select(Patient.id)
        .where(Patient.id == patient_id)
        .where(Patient.is_deleted == False)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    result = await session.execute(
        select(PatientRecordUpdate)
        .where(PatientRecordUpdate.patient_id == patient_id)
        .order_by(PatientRecordUpdate.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


# =============================================================================
# Patient Addresses
# =============================================================================


@router.post(
    "/{patient_id}/addresses",
    response_model=PatientAddressRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.PATIENTS_WRITE))],
)
async def create_patient_address(
    patient_id: str,
    body: PatientAddressCreate,
    user: CurrentUser,
    session: DbSession,
    request: Request,
) -> PatientAddress:
    """Add a new address to a patient record.

    Permission: PATIENTS_WRITE
    """
    # Verify patient exists
    result = await session.execute(
        select(Patient.id)
        .where(Patient.id == patient_id)
        .where(Patient.is_deleted == False)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    _ensure_role(user, ADMIN_ROLES, "edit patient addresses")

    address = PatientAddress(
        id=str(uuid4()),
        patient_id=patient_id,
        **body.model_dump(),
    )
    session.add(address)

    # If this is primary, unset other primary addresses
    if body.is_primary:
        await session.execute(
            PatientAddress.__table__.update()
            .where(PatientAddress.patient_id == patient_id)
            .where(PatientAddress.id != address.id)
            .values(is_primary=False)
        )

    await session.flush()

    postcode_change = await _sync_patient_postcode(session, patient_id)
    changed_fields = _build_record_update_payload(
        "address",
        address.id,
        None,
        body.model_dump(),
    )
    if postcode_change:
        changed_fields["patient_postcode"] = postcode_change

    record_update = PatientRecordUpdate(
        id=str(uuid4()),
        patient_id=patient_id,
        actor_user_id=user.id,
        actor_type=RecordUpdateActorType.STAFF.value,
        source=RecordUpdateSource.STAFF_EDIT.value,
        changed_fields=changed_fields,
        reason=None,
    )
    session.add(record_update)
    await session.commit()
    await session.refresh(address)

    # Audit
    await write_audit_event(
        session=session,
        actor_type=ActorType.STAFF,
        actor_id=user.id,
        actor_email=user.email,
        action="patient_address_created",
        action_category="clinical",
        entity_type="patient_address",
        entity_id=address.id,
        metadata={"patient_id": patient_id, "type": body.type},
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    return address


# =============================================================================
# Patient Address Updates
# =============================================================================


@router.patch(
    "/{patient_id}/addresses/{address_id}",
    response_model=PatientAddressRead,
    dependencies=[Depends(require_permissions(Permission.PATIENTS_WRITE))],
)
async def update_patient_address(
    patient_id: str,
    address_id: str,
    body: PatientAddressUpdate,
    user: CurrentUser,
    session: DbSession,
    request: Request,
) -> PatientAddress:
    """Update a patient address.

    Permission: PATIENTS_WRITE (admin only)
    """
    result = await session.execute(
        select(PatientAddress)
        .where(PatientAddress.id == address_id)
        .where(PatientAddress.patient_id == patient_id)
    )
    address = result.scalar_one_or_none()
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found",
        )

    _ensure_role(user, ADMIN_ROLES, "edit patient addresses")

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        return address

    old_values = {}
    new_values = {}
    for field, value in update_data.items():
        old_value = getattr(address, field, None)
        if old_value != value:
            old_values[field] = old_value
            new_values[field] = value
            setattr(address, field, value)

    if not new_values:
        return address

    if update_data.get("is_primary") is True:
        await session.execute(
            PatientAddress.__table__.update()
            .where(PatientAddress.patient_id == patient_id)
            .where(PatientAddress.id != address.id)
            .values(is_primary=False)
        )

    address.updated_at = datetime.now(timezone.utc)

    postcode_change = await _sync_patient_postcode(session, patient_id)
    changed_fields = _build_record_update_payload(
        "address",
        address.id,
        old_values,
        new_values,
    )
    if postcode_change:
        changed_fields["patient_postcode"] = postcode_change

    record_update = PatientRecordUpdate(
        id=str(uuid4()),
        patient_id=patient_id,
        actor_user_id=user.id,
        actor_type=RecordUpdateActorType.STAFF.value,
        source=RecordUpdateSource.STAFF_EDIT.value,
        changed_fields=changed_fields,
        reason=None,
    )
    session.add(record_update)

    await session.commit()
    await session.refresh(address)

    await write_audit_event(
        session=session,
        actor_type=ActorType.STAFF,
        actor_id=user.id,
        actor_email=user.email,
        action="patient_address_updated",
        action_category="clinical",
        entity_type="patient_address",
        entity_id=address.id,
        metadata={"patient_id": patient_id, "type": address.type},
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    return address

# =============================================================================
# Patient Contacts
# =============================================================================


@router.post(
    "/{patient_id}/contacts",
    response_model=PatientContactRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.PATIENTS_WRITE))],
)
async def create_patient_contact(
    patient_id: str,
    body: PatientContactCreate,
    user: CurrentUser,
    session: DbSession,
    request: Request,
) -> PatientContact:
    """Add a new contact (GP, emergency, next-of-kin) to a patient record.

    Permission: PATIENTS_WRITE
    """
    # Verify patient exists
    result = await session.execute(
        select(Patient.id)
        .where(Patient.id == patient_id)
        .where(Patient.is_deleted == False)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    _ensure_role(user, CLINICIAN_ROLES | {UserRole.ADMIN}, "edit patient contacts")

    contact = PatientContact(
        id=str(uuid4()),
        patient_id=patient_id,
        **body.model_dump(),
    )
    session.add(contact)
    await session.flush()

    record_update = PatientRecordUpdate(
        id=str(uuid4()),
        patient_id=patient_id,
        actor_user_id=user.id,
        actor_type=RecordUpdateActorType.STAFF.value,
        source=RecordUpdateSource.STAFF_EDIT.value,
        changed_fields=_build_record_update_payload(
            "contact",
            contact.id,
            None,
            body.model_dump(),
        ),
        reason=None,
    )
    session.add(record_update)

    await session.commit()
    await session.refresh(contact)

    # Audit
    await write_audit_event(
        session=session,
        actor_type=ActorType.STAFF,
        actor_id=user.id,
        actor_email=user.email,
        action="patient_contact_created",
        action_category="clinical",
        entity_type="patient_contact",
        entity_id=contact.id,
        metadata={"patient_id": patient_id, "contact_type": body.contact_type},
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    return contact


# =============================================================================
# Patient Contact Updates
# =============================================================================


@router.patch(
    "/{patient_id}/contacts/{contact_id}",
    response_model=PatientContactRead,
    dependencies=[Depends(require_permissions(Permission.PATIENTS_WRITE))],
)
async def update_patient_contact(
    patient_id: str,
    contact_id: str,
    body: PatientContactUpdate,
    user: CurrentUser,
    session: DbSession,
    request: Request,
) -> PatientContact:
    """Update a patient contact (GP, emergency, next-of-kin).

    Permission: PATIENTS_WRITE (clinician/admin only)
    """
    # Verify patient exists
    result = await session.execute(
        select(Patient)
        .where(Patient.id == patient_id)
        .where(Patient.is_deleted == False)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    _ensure_role(user, CLINICIAN_ROLES | {UserRole.ADMIN}, "edit patient contacts")

    result = await session.execute(
        select(PatientContact)
        .where(PatientContact.id == contact_id)
        .where(PatientContact.patient_id == patient_id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        return contact

    if "contact_type" in update_data:
        new_type = update_data["contact_type"]
        if patient.primary_gp_contact_id == contact_id and new_type != "gp":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Update primary GP pointer before changing contact type",
            )
        if patient.emergency_contact_id == contact_id and new_type != "emergency":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Update emergency contact pointer before changing contact type",
            )

    old_values = {}
    new_values = {}
    for field, new_value in update_data.items():
        old_value = getattr(contact, field, None)
        if old_value != new_value:
            old_values[field] = old_value
            new_values[field] = new_value
            setattr(contact, field, new_value)

    if not new_values:
        return contact

    contact.updated_at = datetime.now(timezone.utc)

    record_update = PatientRecordUpdate(
        id=str(uuid4()),
        patient_id=patient_id,
        actor_user_id=user.id,
        actor_type=RecordUpdateActorType.STAFF.value,
        source=RecordUpdateSource.STAFF_EDIT.value,
        changed_fields=_build_record_update_payload(
            "contact",
            contact.id,
            old_values,
            new_values,
        ),
        reason=None,
    )
    session.add(record_update)

    await session.commit()
    await session.refresh(contact)

    await write_audit_event(
        session=session,
        actor_type=ActorType.STAFF,
        actor_id=user.id,
        actor_email=user.email,
        action="patient_contact_updated",
        action_category="clinical",
        entity_type="patient_contact",
        entity_id=contact.id,
        metadata={"patient_id": patient_id, "contact_type": contact.contact_type},
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    return contact

# =============================================================================
# Patient Preferences
# =============================================================================


@router.put(
    "/{patient_id}/preferences",
    response_model=PatientPreferencesRead,
    dependencies=[Depends(require_permissions(Permission.PATIENTS_WRITE))],
)
async def update_patient_preferences(
    patient_id: str,
    body: PatientPreferencesUpdate,
    user: CurrentUser,
    session: DbSession,
    request: Request,
) -> PatientPreferences:
    """Update or create patient preferences.

    Permission: PATIENTS_WRITE
    """
    # Verify patient exists
    result = await session.execute(
        select(Patient.id)
        .where(Patient.id == patient_id)
        .where(Patient.is_deleted == False)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    _ensure_role(user, CLINICIAN_ROLES | {UserRole.ADMIN}, "edit patient preferences")

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        result = await session.execute(
            select(PatientPreferences).where(PatientPreferences.patient_id == patient_id)
        )
        preferences = result.scalar_one_or_none()
        if preferences:
            return preferences

    # Get or create preferences
    result = await session.execute(
        select(PatientPreferences).where(PatientPreferences.patient_id == patient_id)
    )
    preferences = result.scalar_one_or_none()

    old_values = None
    new_values = None
    if preferences:
        # Update existing
        old_values = {}
        new_values = {}
        for field, value in update_data.items():
            old_value = getattr(preferences, field, None)
            if old_value != value:
                old_values[field] = old_value
                new_values[field] = value
                setattr(preferences, field, value)
        if not new_values:
            return preferences
        preferences.updated_at = datetime.now(timezone.utc)
    else:
        # Create new
        new_values = body.model_dump()
        preferences = PatientPreferences(
            patient_id=patient_id,
            **new_values,
        )
        session.add(preferences)

    record_update = PatientRecordUpdate(
        id=str(uuid4()),
        patient_id=patient_id,
        actor_user_id=user.id,
        actor_type=RecordUpdateActorType.STAFF.value,
        source=RecordUpdateSource.STAFF_EDIT.value,
        changed_fields=_build_record_update_payload(
            "preferences",
            patient_id,
            old_values,
            new_values,
        ),
        reason=None,
    )
    session.add(record_update)

    await session.commit()
    await session.refresh(preferences)

    # Audit
    await write_audit_event(
        session=session,
        actor_type=ActorType.STAFF,
        actor_id=user.id,
        actor_email=user.email,
        action="patient_preferences_updated",
        action_category="clinical",
        entity_type="patient_preferences",
        entity_id=patient_id,
        metadata={"patient_id": patient_id},
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    return preferences


# =============================================================================
# Patient Clinical Profile
# =============================================================================


@router.put(
    "/{patient_id}/clinical-profile",
    response_model=PatientClinicalProfileRead,
    dependencies=[Depends(require_permissions(Permission.PATIENTS_WRITE))],
)
async def update_patient_clinical_profile(
    patient_id: str,
    body: PatientClinicalProfileUpdate,
    user: CurrentUser,
    session: DbSession,
    request: Request,
) -> PatientClinicalProfile:
    """Update or create patient clinical profile.

    Permission: PATIENTS_WRITE
    """
    # Verify patient exists
    result = await session.execute(
        select(Patient.id)
        .where(Patient.id == patient_id)
        .where(Patient.is_deleted == False)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    _ensure_role(user, CLINICIAN_ROLES | {UserRole.ADMIN}, "edit patient clinical profile")

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        result = await session.execute(
            select(PatientClinicalProfile).where(
                PatientClinicalProfile.patient_id == patient_id
            )
        )
        profile = result.scalar_one_or_none()
        if profile:
            return profile

    # Get or create clinical profile
    result = await session.execute(
        select(PatientClinicalProfile).where(
            PatientClinicalProfile.patient_id == patient_id
        )
    )
    profile = result.scalar_one_or_none()

    old_values = None
    new_values = None
    if profile:
        # Update existing
        old_values = {}
        new_values = {}
        for field, value in update_data.items():
            old_value = getattr(profile, field, None)
            if old_value != value:
                old_values[field] = old_value
                new_values[field] = value
                setattr(profile, field, value)
        if not new_values:
            return profile
        profile.updated_at = datetime.now(timezone.utc)
    else:
        # Create new
        new_values = body.model_dump()
        profile = PatientClinicalProfile(
            patient_id=patient_id,
            **new_values,
        )
        session.add(profile)

    record_update = PatientRecordUpdate(
        id=str(uuid4()),
        patient_id=patient_id,
        actor_user_id=user.id,
        actor_type=RecordUpdateActorType.STAFF.value,
        source=RecordUpdateSource.STAFF_EDIT.value,
        changed_fields=_build_record_update_payload(
            "clinical_profile",
            patient_id,
            old_values,
            new_values,
        ),
        reason=None,
    )
    session.add(record_update)

    await session.commit()
    await session.refresh(profile)

    # Audit
    await write_audit_event(
        session=session,
        actor_type=ActorType.STAFF,
        actor_id=user.id,
        actor_email=user.email,
        action="patient_clinical_profile_updated",
        action_category="clinical",
        entity_type="patient_clinical_profile",
        entity_id=patient_id,
        metadata={"patient_id": patient_id},
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    return profile


# =============================================================================
# Patient Identifiers
# =============================================================================


@router.post(
    "/{patient_id}/identifiers",
    response_model=PatientIdentifierRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.IDENTIFIERS_WRITE))],
)
async def create_patient_identifier(
    patient_id: str,
    body: PatientIdentifierCreate,
    user: CurrentUser,
    session: DbSession,
    request: Request,
) -> PatientIdentifier:
    """Add a new identifier (NHS number, etc.) to a patient record.

    Permission: IDENTIFIERS_WRITE (admin-only)

    This is restricted to admins to prevent accidental duplicate NHS numbers
    and maintain data integrity.
    """
    # Verify patient exists
    result = await session.execute(
        select(Patient.id)
        .where(Patient.id == patient_id)
        .where(Patient.is_deleted == False)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    if not body.reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reason required when changing identifiers",
        )

    # Check for duplicate identifier
    result = await session.execute(
        select(PatientIdentifier)
        .where(PatientIdentifier.id_type == body.id_type)
        .where(PatientIdentifier.id_value == body.id_value)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Identifier {body.id_type}:{body.id_value} already exists",
        )

    identifier = PatientIdentifier(
        id=str(uuid4()),
        patient_id=patient_id,
        **body.model_dump(exclude={"reason"}),
    )
    session.add(identifier)
    await session.flush()

    record_update = PatientRecordUpdate(
        id=str(uuid4()),
        patient_id=patient_id,
        actor_user_id=user.id,
        actor_type=RecordUpdateActorType.STAFF.value,
        source=RecordUpdateSource.STAFF_EDIT.value,
        changed_fields=_build_record_update_payload(
            "identifier",
            identifier.id,
            None,
            body.model_dump(exclude={"reason"}),
        ),
        reason=body.reason,
    )
    session.add(record_update)

    await session.commit()
    await session.refresh(identifier)

    # Audit
    await write_audit_event(
        session=session,
        actor_type=ActorType.STAFF,
        actor_id=user.id,
        actor_email=user.email,
        action="patient_identifier_created",
        action_category="clinical",
        entity_type="patient_identifier",
        entity_id=identifier.id,
        metadata={"patient_id": patient_id, "id_type": body.id_type},
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    return identifier


@router.patch(
    "/{patient_id}/identifiers/{identifier_id}",
    response_model=PatientIdentifierRead,
    dependencies=[Depends(require_permissions(Permission.IDENTIFIERS_WRITE))],
)
async def update_patient_identifier(
    patient_id: str,
    identifier_id: str,
    body: PatientIdentifierUpdate,
    user: CurrentUser,
    session: DbSession,
    request: Request,
) -> PatientIdentifier:
    """Update a patient identifier.

    Permission: IDENTIFIERS_WRITE (admin only)
    """
    # Verify patient exists
    result = await session.execute(
        select(Patient.id)
        .where(Patient.id == patient_id)
        .where(Patient.is_deleted == False)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    update_data = body.model_dump(exclude_unset=True)
    reason = update_data.pop("reason", None) if "reason" in update_data else body.reason
    if update_data and not reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reason required when changing identifiers",
        )

    result = await session.execute(
        select(PatientIdentifier)
        .where(PatientIdentifier.id == identifier_id)
        .where(PatientIdentifier.patient_id == patient_id)
    )
    identifier = result.scalar_one_or_none()
    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Identifier not found",
        )

    if not update_data:
        return identifier

    if "id_value" in update_data:
        result = await session.execute(
            select(PatientIdentifier.id)
            .where(PatientIdentifier.id_type == (update_data.get("id_type") or identifier.id_type))
            .where(PatientIdentifier.id_value == update_data["id_value"])
        )
        existing = result.scalar_one_or_none()
        if existing and existing != identifier_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Identifier already exists",
            )

    old_values = {}
    new_values = {}
    for field, value in update_data.items():
        old_value = getattr(identifier, field, None)
        if old_value != value:
            old_values[field] = old_value
            new_values[field] = value
            setattr(identifier, field, value)

    if not new_values:
        return identifier

    identifier.updated_at = datetime.now(timezone.utc)

    record_update = PatientRecordUpdate(
        id=str(uuid4()),
        patient_id=patient_id,
        actor_user_id=user.id,
        actor_type=RecordUpdateActorType.STAFF.value,
        source=RecordUpdateSource.STAFF_EDIT.value,
        changed_fields=_build_record_update_payload(
            "identifier",
            identifier.id,
            old_values,
            new_values,
        ),
        reason=reason,
    )
    session.add(record_update)

    await session.commit()
    await session.refresh(identifier)

    await write_audit_event(
        session=session,
        actor_type=ActorType.STAFF,
        actor_id=user.id,
        actor_email=user.email,
        action="patient_identifier_updated",
        action_category="clinical",
        entity_type="patient_identifier",
        entity_id=identifier.id,
        metadata={"patient_id": patient_id, "id_type": identifier.id_type},
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    return identifier

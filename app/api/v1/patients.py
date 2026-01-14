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
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession, get_client_ip, require_permissions
from app.models.user import UserRole
from app.models.audit_event import ActorType
from app.services.rbac import Permission, RBACService
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


async def _sync_patient_postcode(session: DbSession, patient_id: str) -> None:
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
        patient.postcode = postcode
        patient.updated_at = datetime.now(timezone.utc)


# =============================================================================
# Patient CRUD
# =============================================================================


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

    # Track changes for provenance
    changed_fields: dict = {}
    update_data = body.updates.model_dump(exclude_unset=True)

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

    contact = PatientContact(
        id=str(uuid4()),
        patient_id=patient_id,
        **body.model_dump(),
    )
    session.add(contact)
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

    # Get or create preferences
    result = await session.execute(
        select(PatientPreferences).where(PatientPreferences.patient_id == patient_id)
    )
    preferences = result.scalar_one_or_none()

    if preferences:
        # Update existing
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(preferences, field, value)
        preferences.updated_at = datetime.now(timezone.utc)
    else:
        # Create new
        preferences = PatientPreferences(
            patient_id=patient_id,
            **body.model_dump(),
        )
        session.add(preferences)

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

    # Get or create clinical profile
    result = await session.execute(
        select(PatientClinicalProfile).where(
            PatientClinicalProfile.patient_id == patient_id
        )
    )
    profile = result.scalar_one_or_none()

    if profile:
        # Update existing
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(profile, field, value)
        profile.updated_at = datetime.now(timezone.utc)
    else:
        # Create new
        profile = PatientClinicalProfile(
            patient_id=patient_id,
            **body.model_dump(),
        )
        session.add(profile)

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
        **body.model_dump(),
    )
    session.add(identifier)
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

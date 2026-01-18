"""Intake questionnaire endpoints for patient portal."""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentPatient, DbSession, get_client_ip
from app.core.config import settings
from app.models.audit_event import ActorType
from app.models.consent import Consent
from app.models.questionnaire import QuestionnaireDefinition, QuestionnaireResponse
from app.models.triage_case import TriageCase, TriageCaseStatus
from app.schemas.questionnaire import (
    IntakeDraftSave,
    IntakeResponseSubmit,
    QuestionnaireDefinitionRead,
    QuestionnaireResponseRead,
    SafetyBannerResponse,
)
from app.services.audit import write_audit_event
from app.services.triage import TriageService

router = APIRouter(prefix="/intake", tags=["intake"])


@router.get("/safety-banner", response_model=SafetyBannerResponse)
async def get_safety_banner() -> SafetyBannerResponse:
    """Get safety banner configuration.

    This endpoint is public to ensure safety information is always accessible.
    """
    return SafetyBannerResponse(
        enabled=settings.safety_banner_enabled,
        text=settings.safety_banner_text,
        consent_version=settings.consent_version,
    )


@router.get("/questionnaire/active", response_model=QuestionnaireDefinitionRead)
async def get_active_intake_definition(
    session: DbSession,
) -> QuestionnaireDefinition:
    """Get the currently active intake questionnaire definition.

    Returns the active questionnaire used for patient intake.
    """
    result = await session.execute(
        select(QuestionnaireDefinition)
        .where(QuestionnaireDefinition.is_active == True)  # noqa: E712
        .where(QuestionnaireDefinition.name == "intake")
        .order_by(QuestionnaireDefinition.created_at.desc())
        .limit(1)
    )
    definition = result.scalar_one_or_none()

    if not definition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active intake questionnaire found",
        )

    return definition


@router.get("/questionnaire/{version}", response_model=QuestionnaireDefinitionRead)
async def get_intake_definition_by_version(
    version: str,
    session: DbSession,
) -> QuestionnaireDefinition:
    """Get a specific version of the intake questionnaire.

    Old versions remain retrievable for audit purposes.
    """
    result = await session.execute(
        select(QuestionnaireDefinition)
        .where(QuestionnaireDefinition.name == "intake")
        .where(QuestionnaireDefinition.version == version)
    )
    definition = result.scalar_one_or_none()

    if not definition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Intake questionnaire version '{version}' not found",
        )

    return definition


@router.get("/draft", response_model=QuestionnaireResponseRead | None)
async def get_intake_draft(
    patient: CurrentPatient,
    session: DbSession,
) -> QuestionnaireResponse | None:
    """Get the patient's draft intake response if one exists.

    Returns the incomplete response for resuming intake.
    """
    # Find patient's active triage case with incomplete response
    result = await session.execute(
        select(QuestionnaireResponse)
        .join(TriageCase)
        .where(TriageCase.patient_id == patient.id)
        .where(QuestionnaireResponse.is_complete == False)  # noqa: E712
        .order_by(QuestionnaireResponse.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.post("/draft", response_model=QuestionnaireResponseRead, status_code=status.HTTP_200_OK)
async def save_intake_draft(
    body: IntakeDraftSave,
    patient: CurrentPatient,
    session: DbSession,
    request: Request,
) -> QuestionnaireResponse:
    """Save a draft of the intake questionnaire.

    Creates or updates an incomplete response for later resumption.
    """
    # Get or create triage case for patient
    triage_case = await _get_or_create_triage_case(patient.id, session)

    # Get active questionnaire definition
    result = await session.execute(
        select(QuestionnaireDefinition)
        .where(QuestionnaireDefinition.is_active == True)  # noqa: E712
        .where(QuestionnaireDefinition.name == "intake")
        .order_by(QuestionnaireDefinition.created_at.desc())
        .limit(1)
    )
    definition = result.scalar_one_or_none()

    if not definition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active intake questionnaire found",
        )

    # Find existing draft or create new
    result = await session.execute(
        select(QuestionnaireResponse)
        .where(QuestionnaireResponse.triage_case_id == triage_case.id)
        .where(QuestionnaireResponse.questionnaire_definition_id == definition.id)
        .where(QuestionnaireResponse.is_complete == False)  # noqa: E712
    )
    response = result.scalar_one_or_none()

    if response:
        # Update existing draft
        response.answers = body.answers
        response.updated_at = datetime.now(timezone.utc)
    else:
        # Create new draft
        response = QuestionnaireResponse(
            triage_case_id=triage_case.id,
            questionnaire_definition_id=definition.id,
            answers=body.answers,
            is_complete=False,
        )
        session.add(response)

    await session.commit()
    await session.refresh(response)

    # Audit event
    await write_audit_event(
        session=session,
        actor_type=ActorType.PATIENT,
        actor_id=patient.id,
        actor_email=patient.email,
        action="intake_draft_saved",
        action_category="clinical",
        entity_type="questionnaire_response",
        entity_id=response.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    return response


@router.post("/submit", response_model=QuestionnaireResponseRead, status_code=status.HTTP_201_CREATED)
async def submit_intake_response(
    body: IntakeResponseSubmit,
    patient: CurrentPatient,
    session: DbSession,
    request: Request,
) -> QuestionnaireResponse:
    """Submit the completed intake questionnaire.

    Validates the response against the questionnaire schema and marks as complete.
    """
    # Get or create triage case for patient
    triage_case = await _get_or_create_triage_case(patient.id, session)

    # Get active questionnaire definition
    result = await session.execute(
        select(QuestionnaireDefinition)
        .where(QuestionnaireDefinition.is_active == True)  # noqa: E712
        .where(QuestionnaireDefinition.name == "intake")
        .order_by(QuestionnaireDefinition.created_at.desc())
        .limit(1)
    )
    definition = result.scalar_one_or_none()

    if not definition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active intake questionnaire found",
        )

    # Validate required fields against schema
    validation_errors = _validate_against_schema(body.answers, definition.schema)
    if validation_errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Validation failed", "errors": validation_errors},
        )

    # Check for existing draft to update
    result = await session.execute(
        select(QuestionnaireResponse)
        .where(QuestionnaireResponse.triage_case_id == triage_case.id)
        .where(QuestionnaireResponse.questionnaire_definition_id == definition.id)
        .where(QuestionnaireResponse.is_complete == False)  # noqa: E712
    )
    response = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if response:
        # Complete existing draft
        response.answers = body.answers
        response.is_complete = True
        response.submitted_at = now
        response.updated_at = now
    else:
        # Create new completed response
        response = QuestionnaireResponse(
            triage_case_id=triage_case.id,
            questionnaire_definition_id=definition.id,
            answers=body.answers,
            is_complete=True,
            submitted_at=now,
        )
        session.add(response)

    await session.commit()
    await session.refresh(response)

    # Run triage evaluation
    triage_service = TriageService(session)
    await triage_service.evaluate_case(
        triage_case=triage_case,
        questionnaire_response=response,
        apply_result=True,
    )

    # Audit event
    await write_audit_event(
        session=session,
        actor_type=ActorType.PATIENT,
        actor_id=patient.id,
        actor_email=patient.email,
        action="intake_submitted",
        action_category="clinical",
        entity_type="questionnaire_response",
        entity_id=response.id,
        metadata={
            "questionnaire_version": definition.version,
            "triage_tier": triage_case.tier.value if triage_case.tier else None,
        },
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    return response


async def _get_or_create_triage_case(patient_id: str, session: DbSession) -> TriageCase:
    """Get existing open triage case or create new one."""
    result = await session.execute(
        select(TriageCase)
        .where(TriageCase.patient_id == patient_id)
        .where(TriageCase.status == TriageCaseStatus.PENDING)
        .order_by(TriageCase.created_at.desc())
        .limit(1)
    )
    triage_case = result.scalar_one_or_none()

    if not triage_case:
        triage_case = TriageCase(
            patient_id=patient_id,
            status=TriageCaseStatus.PENDING,
        )
        session.add(triage_case)
        await session.commit()
        await session.refresh(triage_case)

    return triage_case


def _validate_against_schema(answers: dict[str, Any], schema: dict) -> list[str]:
    """Validate answers against questionnaire schema.

    Returns list of validation error messages.
    """
    errors = []
    fields = schema.get("fields", [])

    for field in fields:
        field_id = field.get("id")
        required = field.get("required", False)

        if required and field_id not in answers:
            errors.append(f"Required field '{field_id}' is missing")
        elif required and answers.get(field_id) in (None, "", []):
            errors.append(f"Required field '{field_id}' cannot be empty")

        # Type validation
        if field_id in answers and answers[field_id] is not None:
            field_type = field.get("type")
            value = answers[field_id]

            if field_type == "text" and not isinstance(value, str):
                errors.append(f"Field '{field_id}' must be a string")
            elif field_type == "number" and not isinstance(value, (int, float)):
                errors.append(f"Field '{field_id}' must be a number")
            elif field_type == "boolean" and not isinstance(value, bool):
                errors.append(f"Field '{field_id}' must be a boolean")
            elif field_type == "select" and "options" in field:
                valid_options = [opt.get("value") for opt in field["options"]]
                if value not in valid_options:
                    errors.append(f"Field '{field_id}' has invalid option '{value}'")
            elif field_type == "multiselect" and "options" in field:
                if not isinstance(value, list):
                    errors.append(f"Field '{field_id}' must be a list")
                else:
                    valid_options = [opt.get("value") for opt in field["options"]]
                    for v in value:
                        if v not in valid_options:
                            errors.append(f"Field '{field_id}' has invalid option '{v}'")

    return errors

"""Pydantic schemas for patient operations.

Includes schemas for:
- Patient CRUD operations
- Addresses, contacts, preferences, clinical profile
- Record update provenance
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


# =============================================================================
# Address Schemas
# =============================================================================


class PatientAddressBase(BaseModel):
    """Base schema for patient address."""

    type: str = Field(..., description="Address type: home, current, billing, other")
    line1: str | None = None
    line2: str | None = None
    city: str | None = None
    county: str | None = None
    postcode: str | None = None
    country: str = Field(default="GB")
    valid_from: date | None = None
    valid_to: date | None = None
    is_primary: bool = False


class PatientAddressCreate(PatientAddressBase):
    """Schema for creating a patient address."""

    pass


class PatientAddressRead(PatientAddressBase):
    """Schema for reading a patient address."""

    id: str
    patient_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PatientAddressUpdate(BaseModel):
    """Schema for updating a patient address."""

    type: str | None = None
    line1: str | None = None
    line2: str | None = None
    city: str | None = None
    county: str | None = None
    postcode: str | None = None
    country: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    is_primary: bool | None = None


# =============================================================================
# Contact Schemas
# =============================================================================


class PatientContactBase(BaseModel):
    """Base schema for patient contact (GP, emergency, next-of-kin)."""

    contact_type: str = Field(
        ..., description="Contact type: emergency, gp, next_of_kin, other"
    )
    name: str | None = None
    relationship_to_patient: str | None = None
    phone_e164: str | None = Field(None, description="Phone in E.164 format (+44...)")
    email: EmailStr | None = None
    organisation: str | None = Field(None, description="e.g., GP practice name")
    notes: str | None = None


class PatientContactCreate(PatientContactBase):
    """Schema for creating a patient contact."""

    pass


class PatientContactRead(PatientContactBase):
    """Schema for reading a patient contact."""

    id: str
    patient_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PatientContactUpdate(BaseModel):
    """Schema for updating a patient contact."""

    contact_type: str | None = None
    name: str | None = None
    relationship_to_patient: str | None = None
    phone_e164: str | None = None
    email: EmailStr | None = None
    organisation: str | None = None
    notes: str | None = None


# =============================================================================
# Preferences Schemas
# =============================================================================


class PatientPreferencesBase(BaseModel):
    """Base schema for patient preferences."""

    communication_channel_preference: str | None = Field(
        None, description="Preferred contact: email, sms, phone"
    )
    appointment_format_preference: str | None = Field(
        None, description="Preferred format: in_person, video, phone, no_preference"
    )
    requires_accessibility_support: bool = False
    accessibility_notes: str | None = None
    reasonable_adjustments_notes: str | None = None


class PatientPreferencesUpdate(PatientPreferencesBase):
    """Schema for updating patient preferences."""

    pass


class PatientPreferencesRead(PatientPreferencesBase):
    """Schema for reading patient preferences."""

    patient_id: str
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# =============================================================================
# Clinical Profile Schemas
# =============================================================================


class PatientClinicalProfileBase(BaseModel):
    """Base schema for patient clinical profile."""

    presenting_problem: str | None = None
    previous_mental_health_treatment: str | None = Field(
        None,
        description="Treatment history: none, yes_unknown, yes_talking_therapy, yes_psychiatry, yes_inpatient",
    )
    current_psych_medication: bool | None = None
    current_medication_list: list[dict[str, Any]] | None = Field(
        None, description="List of {name, dose, frequency}"
    )
    physical_health_conditions: bool | None = None
    physical_health_notes: str | None = None
    substance_use_level: str | None = Field(
        None, description="Level: none, low, moderate, high, unknown"
    )
    neurodevelopmental_needs: bool | None = None
    risk_notes_staff_only: str | None = Field(
        None, description="Staff-only risk notes (not shown to patient)"
    )


class PatientClinicalProfileUpdate(PatientClinicalProfileBase):
    """Schema for updating patient clinical profile."""

    pass


class PatientClinicalProfileRead(PatientClinicalProfileBase):
    """Schema for reading patient clinical profile."""

    patient_id: str
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# =============================================================================
# Identifier Schemas
# =============================================================================


class PatientIdentifierBase(BaseModel):
    """Base schema for patient identifier."""

    id_type: str = Field(..., description="Type: nhs_number, private_id, other")
    id_value: str = Field(..., description="The identifier value")
    is_verified: bool = False


class PatientIdentifierCreate(PatientIdentifierBase):
    """Schema for creating a patient identifier."""

    reason: str | None = Field(
        None, description="Reason for creating or changing identifiers"
    )


class PatientIdentifierRead(PatientIdentifierBase):
    """Schema for reading a patient identifier."""

    id: str
    patient_id: str
    verified_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PatientIdentifierUpdate(BaseModel):
    """Schema for updating a patient identifier."""

    id_type: str | None = None
    id_value: str | None = None
    is_verified: bool | None = None
    reason: str | None = Field(
        None, description="Reason for creating or changing identifiers"
    )


# =============================================================================
# Record Update Schemas
# =============================================================================


class PatientRecordUpdateRead(BaseModel):
    """Schema for reading a patient record update (provenance log)."""

    id: str
    patient_id: str
    actor_user_id: str | None = None
    actor_type: str
    source: str
    changed_fields: dict[str, Any] = Field(
        ...,
        description="Changed fields with old/new values",
        examples=[{"postcode": {"old": "", "new": "SW11 1AA"}}],
    )
    reason: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# =============================================================================
# Patient Schemas
# =============================================================================


class PatientBase(BaseModel):
    """Base schema for patient - core identity fields."""

    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    preferred_name: str | None = Field(None, max_length=100)
    date_of_birth: date | None = None
    sex_at_birth: str | None = Field(
        None, description="male, female, intersex, prefer_not_to_say"
    )
    gender_identity: str | None = None
    ethnicity: str | None = Field(None, description="UK ONS ethnicity category")
    preferred_language: str | None = None
    interpreter_required: bool = False

    # Contact
    phone_e164: str | None = Field(None, description="Phone in E.164 format (+44...)")
    preferred_contact_method: str | None = Field(
        None, description="email, sms, phone"
    )
    can_leave_voicemail: bool = False
    consent_to_sms: bool = False
    consent_to_email: bool = True

    # Location
    postcode: str | None = Field(None, max_length=10)
    country: str | None = Field("GB", max_length=5)

    # Safeguarding
    has_dependents: bool | None = None
    is_pregnant_or_postnatal: bool | None = None
    reasonable_adjustments_required: bool = False


class PatientCreate(PatientBase):
    """Schema for creating a patient."""

    is_dummy: bool = Field(False, description="Test mode safety flag")


class PatientUpdate(BaseModel):
    """Schema for updating a patient (PATCH - all fields optional)."""

    # Identity
    email: EmailStr | None = None
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    preferred_name: str | None = None
    date_of_birth: date | None = None
    sex_at_birth: str | None = None
    gender_identity: str | None = None
    ethnicity: str | None = None
    preferred_language: str | None = None
    interpreter_required: bool | None = None

    # Contact
    phone_e164: str | None = None
    preferred_contact_method: str | None = None
    can_leave_voicemail: bool | None = None
    consent_to_sms: bool | None = None
    consent_to_email: bool | None = None

    # Location
    postcode: str | None = None
    country: str | None = None

    # Safeguarding
    has_dependents: bool | None = None
    is_pregnant_or_postnatal: bool | None = None
    reasonable_adjustments_required: bool | None = None

    # Status
    is_active: bool | None = None

    # Link to contacts
    primary_gp_contact_id: str | None = None
    emergency_contact_id: str | None = None


class PatientSummary(BaseModel):
    """Minimal patient summary for list views."""

    id: str
    email: str
    first_name: str
    last_name: str
    preferred_name: str | None = None
    date_of_birth: date | None = None
    postcode: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PatientRead(PatientBase):
    """Full patient read schema with all related data."""

    id: str
    is_active: bool
    is_dummy: bool
    nhs_number: str | None = None
    notes: str | None = None
    consent_given_at: datetime | None = None
    privacy_policy_version: str | None = None
    primary_gp_contact_id: str | None = None
    emergency_contact_id: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    # Related entities
    addresses: list[PatientAddressRead] = []
    contacts: list[PatientContactRead] = []
    preferences: PatientPreferencesRead | None = None
    clinical_profile: PatientClinicalProfileRead | None = None
    identifiers: list[PatientIdentifierRead] = []

    model_config = {"from_attributes": True}


class PatientDetailRead(PatientRead):
    """Extended patient read with emergency and GP contact details."""

    primary_gp_contact: PatientContactRead | None = None
    emergency_contact: PatientContactRead | None = None

    model_config = {"from_attributes": True}


# =============================================================================
# Audit/Update Request Schemas
# =============================================================================


class PatientUpdateRequest(BaseModel):
    """Request schema for staff patient update with reason."""

    updates: PatientUpdate = Field(..., description="Fields to update")
    reason: str | None = Field(
        None, description="Reason for the update (for audit purposes)"
    )

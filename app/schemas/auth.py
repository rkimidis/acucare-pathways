"""Authentication schemas."""

import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field


def validate_email_lenient(v: str) -> str:
    """Validate email with lenient rules that allow .local domains for testing."""
    if not v or "@" not in v:
        raise ValueError("Invalid email address")
    # Basic email pattern that allows .local and other test domains
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, v):
        raise ValueError("Invalid email address format")
    return v.lower()


LenientEmail = Annotated[str, AfterValidator(validate_email_lenient)]


class StaffLoginRequest(BaseModel):
    """Staff login request with email and password."""

    email: LenientEmail
    password: str = Field(min_length=8, max_length=128)


class PatientLoginRequest(BaseModel):
    """Patient login request with magic link token."""

    token: str = Field(min_length=32, max_length=64)


class MagicLinkRequest(BaseModel):
    """Request to generate a magic link for patient authentication."""

    email: LenientEmail


class MagicLinkResponse(BaseModel):
    """Response containing magic link details (dev only - in prod, sent via email)."""

    token: str
    expires_in_minutes: int
    message: str


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenPayload(BaseModel):
    """Decoded JWT token payload."""

    sub: str
    type: str
    exp: int
    iat: int
    role: str | None = None
    actor_type: str | None = None  # "staff" or "patient"


class PatientRegisterRequest(BaseModel):
    """Patient registration request."""

    email: LenientEmail
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)


class PatientRegisterResponse(BaseModel):
    """Patient registration response."""

    id: str
    email: str
    first_name: str
    last_name: str
    message: str

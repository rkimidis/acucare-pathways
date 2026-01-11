"""Authentication schemas."""

from pydantic import BaseModel, EmailStr, Field


class StaffLoginRequest(BaseModel):
    """Staff login request with email and password."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class PatientLoginRequest(BaseModel):
    """Patient login request with magic link token."""

    token: str = Field(min_length=32, max_length=64)


class MagicLinkRequest(BaseModel):
    """Request to generate a magic link for patient authentication."""

    email: EmailStr


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

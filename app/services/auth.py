"""Authentication service for staff and patients."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_magic_link_token,
    hash_password,
    verify_password,
)
from app.models.patient import Patient, PatientMagicLink
from app.models.user import User


class AuthService:
    """Service for handling authentication operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- Staff Authentication ---

    async def authenticate_staff(
        self,
        email: str,
        password: str,
    ) -> User | None:
        """Authenticate staff user with email and password.

        Args:
            email: Staff email address
            password: Plain text password

        Returns:
            User if credentials valid, None otherwise
        """
        result = await self.session.execute(
            select(User).where(User.email == email.lower())
        )
        user = result.scalar_one_or_none()

        if not user:
            return None

        if not user.is_active:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        return user

    async def create_staff_token(self, user: User) -> str:
        """Create JWT access token for staff user.

        Args:
            user: Authenticated User instance

        Returns:
            JWT access token string
        """
        return create_access_token(
            subject=user.id,
            additional_claims={
                "role": user.role.value if hasattr(user.role, 'value') else user.role,
                "actor_type": "staff",
                "email": user.email,
            },
        )

    async def get_staff_by_id(self, user_id: str) -> User | None:
        """Get staff user by ID.

        Args:
            user_id: UUID of the user

        Returns:
            User or None
        """
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    # --- Patient Authentication ---

    async def get_patient_by_email(self, email: str) -> Patient | None:
        """Get patient by email address.

        Args:
            email: Patient email address

        Returns:
            Patient or None
        """
        result = await self.session.execute(
            select(Patient).where(Patient.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def create_magic_link(self, patient: Patient) -> PatientMagicLink:
        """Create a magic link token for patient authentication.

        Args:
            patient: Patient instance

        Returns:
            Created PatientMagicLink with token
        """
        token = generate_magic_link_token()
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.patient_magic_link_ttl_minutes
        )

        magic_link = PatientMagicLink(
            patient_id=patient.id,
            token=token,
            expires_at=expires_at,
        )

        self.session.add(magic_link)
        await self.session.commit()
        await self.session.refresh(magic_link)

        return magic_link

    async def validate_magic_link(self, token: str) -> PatientMagicLink | None:
        """Validate and retrieve a magic link by token.

        Does NOT consume the token - call consume_magic_link for that.

        Args:
            token: Magic link token string

        Returns:
            Valid PatientMagicLink or None if invalid/expired
        """
        result = await self.session.execute(
            select(PatientMagicLink).where(PatientMagicLink.token == token)
        )
        magic_link = result.scalar_one_or_none()

        if not magic_link:
            return None

        if not magic_link.is_valid:
            return None

        return magic_link

    async def consume_magic_link(self, magic_link: PatientMagicLink) -> bool:
        """Mark a magic link as used.

        Args:
            magic_link: PatientMagicLink to consume

        Returns:
            True if successfully consumed, False if already used
        """
        if magic_link.is_used:
            return False

        magic_link.is_used = True
        magic_link.used_at = datetime.now(timezone.utc)
        await self.session.commit()

        return True

    async def create_patient_token(self, patient: Patient) -> str:
        """Create JWT access token for patient.

        Args:
            patient: Authenticated Patient instance

        Returns:
            JWT access token string
        """
        return create_access_token(
            subject=patient.id,
            additional_claims={
                "actor_type": "patient",
                "email": patient.email,
            },
        )

    async def get_patient_by_id(self, patient_id: str) -> Patient | None:
        """Get patient by ID.

        Args:
            patient_id: UUID of the patient

        Returns:
            Patient or None
        """
        result = await self.session.execute(
            select(Patient).where(Patient.id == patient_id)
        )
        return result.scalar_one_or_none()

    # --- Utility Methods ---

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password for storage.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        return hash_password(password)

"""Tests for patient magic link authentication and expiry."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient, PatientMagicLink
from app.services.auth import AuthService


@pytest.mark.asyncio
async def test_magic_link_is_valid_when_not_expired_and_not_used(
    async_session: AsyncSession,
    valid_magic_link: PatientMagicLink,
) -> None:
    """Test that a fresh magic link is valid."""
    assert valid_magic_link.is_valid is True
    assert valid_magic_link.is_expired is False
    assert valid_magic_link.is_used is False


@pytest.mark.asyncio
async def test_magic_link_is_invalid_when_expired(
    async_session: AsyncSession,
    expired_magic_link: PatientMagicLink,
) -> None:
    """Test that an expired magic link is invalid."""
    assert expired_magic_link.is_expired is True
    assert expired_magic_link.is_valid is False


@pytest.mark.asyncio
async def test_magic_link_is_invalid_when_used(
    async_session: AsyncSession,
    used_magic_link: PatientMagicLink,
) -> None:
    """Test that a used magic link is invalid."""
    assert used_magic_link.is_used is True
    assert used_magic_link.is_valid is False


@pytest.mark.asyncio
async def test_validate_magic_link_returns_valid_link(
    async_session: AsyncSession,
    valid_magic_link: PatientMagicLink,
) -> None:
    """Test AuthService.validate_magic_link returns valid link."""
    auth_service = AuthService(async_session)
    result = await auth_service.validate_magic_link(valid_magic_link.token)

    assert result is not None
    assert result.id == valid_magic_link.id


@pytest.mark.asyncio
async def test_validate_magic_link_returns_none_for_expired(
    async_session: AsyncSession,
    expired_magic_link: PatientMagicLink,
) -> None:
    """Test AuthService.validate_magic_link returns None for expired link."""
    auth_service = AuthService(async_session)
    result = await auth_service.validate_magic_link(expired_magic_link.token)

    assert result is None


@pytest.mark.asyncio
async def test_validate_magic_link_returns_none_for_used(
    async_session: AsyncSession,
    used_magic_link: PatientMagicLink,
) -> None:
    """Test AuthService.validate_magic_link returns None for used link."""
    auth_service = AuthService(async_session)
    result = await auth_service.validate_magic_link(used_magic_link.token)

    assert result is None


@pytest.mark.asyncio
async def test_validate_magic_link_returns_none_for_invalid_token(
    async_session: AsyncSession,
) -> None:
    """Test AuthService.validate_magic_link returns None for non-existent token."""
    auth_service = AuthService(async_session)
    result = await auth_service.validate_magic_link("nonexistent_token_here")

    assert result is None


@pytest.mark.asyncio
async def test_consume_magic_link_marks_as_used(
    async_session: AsyncSession,
    valid_magic_link: PatientMagicLink,
) -> None:
    """Test that consuming a magic link marks it as used."""
    auth_service = AuthService(async_session)

    assert valid_magic_link.is_used is False

    result = await auth_service.consume_magic_link(valid_magic_link)

    assert result is True
    assert valid_magic_link.is_used is True
    assert valid_magic_link.used_at is not None


@pytest.mark.asyncio
async def test_consume_magic_link_fails_for_already_used(
    async_session: AsyncSession,
    used_magic_link: PatientMagicLink,
) -> None:
    """Test that consuming an already-used link fails."""
    auth_service = AuthService(async_session)

    result = await auth_service.consume_magic_link(used_magic_link)

    assert result is False


@pytest.mark.asyncio
async def test_create_magic_link_respects_ttl(
    async_session: AsyncSession,
    test_patient: Patient,
) -> None:
    """Test that created magic links have correct expiry based on TTL."""
    from app.core.config import settings

    auth_service = AuthService(async_session)

    # Record time before creation
    before = datetime.now(timezone.utc)

    magic_link = await auth_service.create_magic_link(test_patient)

    # Record time after creation
    after = datetime.now(timezone.utc)

    # Expected expiry should be within TTL range
    expected_min = before + timedelta(minutes=settings.patient_magic_link_ttl_minutes)
    expected_max = after + timedelta(minutes=settings.patient_magic_link_ttl_minutes)

    assert magic_link.expires_at >= expected_min
    assert magic_link.expires_at <= expected_max


@pytest.mark.asyncio
async def test_magic_link_token_is_unique(
    async_session: AsyncSession,
    test_patient: Patient,
) -> None:
    """Test that each magic link gets a unique token."""
    auth_service = AuthService(async_session)

    link1 = await auth_service.create_magic_link(test_patient)
    link2 = await auth_service.create_magic_link(test_patient)

    assert link1.token != link2.token
    assert len(link1.token) >= 32  # Minimum token length for security

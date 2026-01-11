"""Tests for MFA functionality."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


@pytest.mark.asyncio
async def test_mfa_setup_returns_secret_and_codes(
    client: TestClient,
    async_session: AsyncSession,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test that MFA setup returns secret and backup codes."""
    response = client.post(
        "/api/v1/auth/staff/mfa/setup",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert "secret" in data
    assert len(data["secret"]) == 32
    assert "provisioning_uri" in data
    assert "backup_codes" in data
    assert len(data["backup_codes"]) == 10


@pytest.mark.asyncio
async def test_mfa_enable_with_valid_code(
    client: TestClient,
    async_session: AsyncSession,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test that MFA can be enabled with valid OTP code."""
    # First setup MFA
    setup_response = client.post(
        "/api/v1/auth/staff/mfa/setup",
        headers=auth_headers,
    )
    assert setup_response.status_code == 200

    # Enable with stub code (000000 is valid in dev)
    enable_response = client.post(
        "/api/v1/auth/staff/mfa/enable",
        json={"otp_code": "000000"},
        headers=auth_headers,
    )

    assert enable_response.status_code == 200

    # Refresh user from database
    await async_session.refresh(test_user)
    assert test_user.mfa_enabled is True


@pytest.mark.asyncio
async def test_mfa_enable_fails_without_setup(
    client: TestClient,
    async_session: AsyncSession,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test that MFA enable fails if setup wasn't called first."""
    response = client.post(
        "/api/v1/auth/staff/mfa/enable",
        json={"otp_code": "123456"},
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert "setup not initiated" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_mfa_status_shows_disabled_by_default(
    client: TestClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test that MFA status shows disabled by default."""
    response = client.get(
        "/api/v1/auth/staff/mfa/status",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["mfa_enabled"] is False


@pytest.mark.asyncio
async def test_mfa_verify_with_valid_code(
    client: TestClient,
    async_session: AsyncSession,
    mfa_user: User,
) -> None:
    """Test MFA verification with valid code."""
    response = client.post(
        "/api/v1/auth/staff/mfa/verify",
        json={
            "user_id": mfa_user.id,
            "otp_code": "000000",  # Stub accepts this
        },
    )

    assert response.status_code == 200
    assert response.json()["verified"] is True


@pytest.mark.asyncio
async def test_mfa_verify_fails_with_invalid_code(
    client: TestClient,
    async_session: AsyncSession,
    mfa_user: User,
) -> None:
    """Test MFA verification fails with invalid code."""
    response = client.post(
        "/api/v1/auth/staff/mfa/verify",
        json={
            "user_id": mfa_user.id,
            "otp_code": "abc123",  # Invalid - not 6 digits
        },
    )

    assert response.status_code == 401

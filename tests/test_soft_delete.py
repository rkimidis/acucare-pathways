"""Tests for soft delete functionality - no clinical data is hard-deleted."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient
from app.models.triage_case import TriageCase
from app.models.user import User


@pytest.mark.asyncio
async def test_user_soft_delete(async_session: AsyncSession, test_user: User) -> None:
    """Test that users can be soft-deleted."""
    # Soft delete the user
    test_user.soft_delete(deleted_by_id=None)
    await async_session.commit()
    await async_session.refresh(test_user)

    # Verify soft delete fields are set
    assert test_user.is_deleted is True
    assert test_user.deleted_at is not None
    assert test_user.deleted_at <= datetime.now(timezone.utc)

    # Verify user still exists in database
    result = await async_session.execute(
        select(User).where(User.id == test_user.id)
    )
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.is_deleted is True


@pytest.mark.asyncio
async def test_patient_soft_delete(
    async_session: AsyncSession, test_patient: Patient, admin_user: User
) -> None:
    """Test that patients can be soft-deleted with actor tracking."""
    # Soft delete the patient with actor
    test_patient.soft_delete(deleted_by_id=admin_user.id)
    await async_session.commit()
    await async_session.refresh(test_patient)

    # Verify soft delete fields are set
    assert test_patient.is_deleted is True
    assert test_patient.deleted_at is not None
    assert test_patient.deleted_by == admin_user.id

    # Verify patient still exists in database
    result = await async_session.execute(
        select(Patient).where(Patient.id == test_patient.id)
    )
    patient = result.scalar_one_or_none()
    assert patient is not None
    assert patient.is_deleted is True


@pytest.mark.asyncio
async def test_triage_case_soft_delete(
    async_session: AsyncSession, test_triage_case: TriageCase
) -> None:
    """Test that triage cases can be soft-deleted."""
    # Soft delete the triage case
    test_triage_case.soft_delete()
    await async_session.commit()
    await async_session.refresh(test_triage_case)

    # Verify soft delete fields are set
    assert test_triage_case.is_deleted is True
    assert test_triage_case.deleted_at is not None

    # Verify triage case still exists in database
    result = await async_session.execute(
        select(TriageCase).where(TriageCase.id == test_triage_case.id)
    )
    case = result.scalar_one_or_none()
    assert case is not None
    assert case.is_deleted is True


@pytest.mark.asyncio
async def test_soft_deleted_records_remain_queryable(
    async_session: AsyncSession, test_patient: Patient
) -> None:
    """Test that soft-deleted records can still be queried for compliance."""
    original_id = test_patient.id

    # Soft delete
    test_patient.soft_delete()
    await async_session.commit()

    # Records should still be queryable
    result = await async_session.execute(
        select(Patient).where(Patient.id == original_id)
    )
    patient = result.scalar_one_or_none()
    assert patient is not None

    # Can query specifically for deleted records
    result = await async_session.execute(
        select(Patient).where(Patient.is_deleted == True)  # noqa: E712
    )
    deleted_patients = result.scalars().all()
    assert len(deleted_patients) == 1
    assert deleted_patients[0].id == original_id

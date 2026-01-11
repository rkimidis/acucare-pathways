"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.consent import Consent
from app.models.patient import Patient, PatientMagicLink
from app.models.questionnaire import QuestionnaireDefinition, QuestionnaireResponse
from app.models.triage_case import TriageCase, TriageCaseStatus
from app.models.user import User, UserRole


# Use SQLite for testing (simpler than spinning up postgres)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def async_engine():
    """Create async test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for tests."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest.fixture(scope="function")
def client(async_session: AsyncSession) -> Generator[TestClient, None, None]:
    """Create FastAPI test client with overridden dependencies."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield async_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(async_session: AsyncSession) -> User:
    """Create a test staff user."""
    user = User(
        email="test@acucare.local",
        hashed_password=hash_password("testpassword123"),
        role=UserRole.CLINICIAN,
        first_name="Test",
        last_name="User",
        is_active=True,
        mfa_enabled=False,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(async_session: AsyncSession) -> User:
    """Create a test admin user."""
    user = User(
        email="admin@acucare.local",
        hashed_password=hash_password("adminpassword123"),
        role=UserRole.ADMIN,
        first_name="Admin",
        last_name="User",
        is_active=True,
        mfa_enabled=False,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.fixture
async def mfa_user(async_session: AsyncSession) -> User:
    """Create a test user with MFA enabled."""
    user = User(
        email="mfa@acucare.local",
        hashed_password=hash_password("mfapassword123"),
        role=UserRole.CLINICIAN,
        first_name="MFA",
        last_name="User",
        is_active=True,
        mfa_enabled=True,
        otp_secret="JBSWY3DPEHPK3PXP",  # Test secret
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.fixture
async def test_patient(async_session: AsyncSession) -> Patient:
    """Create a test patient."""
    patient = Patient(
        email="patient@example.com",
        first_name="Test",
        last_name="Patient",
        is_active=True,
    )
    async_session.add(patient)
    await async_session.commit()
    await async_session.refresh(patient)
    return patient


@pytest.fixture
async def test_triage_case(
    async_session: AsyncSession, test_patient: Patient
) -> TriageCase:
    """Create a test triage case."""
    case = TriageCase(
        patient_id=test_patient.id,
        status=TriageCaseStatus.PENDING,
    )
    async_session.add(case)
    await async_session.commit()
    await async_session.refresh(case)
    return case


@pytest.fixture
async def valid_magic_link(
    async_session: AsyncSession, test_patient: Patient
) -> PatientMagicLink:
    """Create a valid (not expired, not used) magic link."""
    magic_link = PatientMagicLink(
        patient_id=test_patient.id,
        token="valid_test_token_12345678901234567890",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        is_used=False,
    )
    async_session.add(magic_link)
    await async_session.commit()
    await async_session.refresh(magic_link)
    return magic_link


@pytest.fixture
async def expired_magic_link(
    async_session: AsyncSession, test_patient: Patient
) -> PatientMagicLink:
    """Create an expired magic link."""
    magic_link = PatientMagicLink(
        patient_id=test_patient.id,
        token="expired_test_token_12345678901234567890",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        is_used=False,
    )
    async_session.add(magic_link)
    await async_session.commit()
    await async_session.refresh(magic_link)
    return magic_link


@pytest.fixture
async def used_magic_link(
    async_session: AsyncSession, test_patient: Patient
) -> PatientMagicLink:
    """Create a used magic link."""
    magic_link = PatientMagicLink(
        patient_id=test_patient.id,
        token="used_test_token_123456789012345678901",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        is_used=True,
        used_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    async_session.add(magic_link)
    await async_session.commit()
    await async_session.refresh(magic_link)
    return magic_link


def create_test_token(user: User) -> str:
    """Create a test JWT token for a user."""
    return create_access_token(
        subject=user.id,
        additional_claims={
            "role": user.role.value,
            "actor_type": "staff",
            "email": user.email,
        },
    )


@pytest.fixture
def auth_headers(test_user: User) -> dict[str, str]:
    """Create authorization headers for test user."""
    token = create_test_token(test_user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(admin_user: User) -> dict[str, str]:
    """Create authorization headers for admin user."""
    token = create_test_token(admin_user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def patient_auth_headers(test_patient: Patient) -> dict[str, str]:
    """Create authorization headers for patient."""
    token = create_access_token(
        subject=test_patient.id,
        additional_claims={
            "actor_type": "patient",
            "email": test_patient.email,
        },
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def intake_questionnaire(async_session: AsyncSession) -> QuestionnaireDefinition:
    """Create an active intake questionnaire definition."""
    import hashlib
    import json

    schema = {
        "title": "Initial Assessment",
        "description": "Please answer the following questions.",
        "sections": [
            {"id": "personal", "title": "Personal Information"},
            {"id": "symptoms", "title": "Current Symptoms"},
        ],
        "fields": [
            {
                "id": "presenting_complaint",
                "type": "textarea",
                "label": "What brings you to us today?",
                "required": True,
                "section": "symptoms",
            },
            {
                "id": "symptom_duration",
                "type": "select",
                "label": "How long have you been experiencing these symptoms?",
                "required": True,
                "section": "symptoms",
                "options": [
                    {"value": "less_than_week", "label": "Less than a week"},
                    {"value": "1_to_4_weeks", "label": "1-4 weeks"},
                    {"value": "1_to_3_months", "label": "1-3 months"},
                    {"value": "more_than_3_months", "label": "More than 3 months"},
                ],
            },
            {
                "id": "suicidal_thoughts",
                "type": "boolean",
                "label": "Have you had thoughts of harming yourself?",
                "required": True,
                "section": "symptoms",
            },
            {
                "id": "previous_treatment",
                "type": "boolean",
                "label": "Have you received mental health treatment before?",
                "required": False,
                "section": "personal",
            },
        ],
    }
    schema_json = json.dumps(schema, sort_keys=True)
    schema_hash = hashlib.sha256(schema_json.encode()).hexdigest()

    definition = QuestionnaireDefinition(
        name="intake",
        version="1.0",
        description="Initial patient intake questionnaire",
        schema=schema,
        schema_hash=schema_hash,
        is_active=True,
        display_order=1,
    )
    async_session.add(definition)
    await async_session.commit()
    await async_session.refresh(definition)
    return definition


@pytest.fixture
async def old_intake_questionnaire(
    async_session: AsyncSession, intake_questionnaire: QuestionnaireDefinition
) -> QuestionnaireDefinition:
    """Create an old (inactive) version of intake questionnaire."""
    import hashlib
    import json

    schema = {
        "title": "Initial Assessment (Old)",
        "fields": [
            {
                "id": "presenting_complaint",
                "type": "textarea",
                "label": "What brings you here?",
                "required": True,
            },
        ],
    }
    schema_json = json.dumps(schema, sort_keys=True)
    schema_hash = hashlib.sha256(schema_json.encode()).hexdigest()

    old_definition = QuestionnaireDefinition(
        name="intake",
        version="0.9",
        description="Previous intake questionnaire",
        schema=schema,
        schema_hash=schema_hash,
        is_active=False,
        display_order=1,
    )
    async_session.add(old_definition)
    await async_session.commit()
    await async_session.refresh(old_definition)
    return old_definition

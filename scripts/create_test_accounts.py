"""Create test staff accounts for test-mode deployment.

Run after database migration to create standard test accounts.
"""

import asyncio
import secrets
from datetime import datetime, timezone

# Test account definitions
TEST_ACCOUNTS = [
    {
        "email": "admin@test.acucare.local",
        "name": "Test Admin",
        "role": "admin",
        "permissions": ["*"],
    },
    {
        "email": "clinician1@test.acucare.local",
        "name": "Dr Test Clinician",
        "role": "clinician",
        "permissions": ["triage:read", "triage:write", "triage:override", "audit:read"],
    },
    {
        "email": "clinician2@test.acucare.local",
        "name": "Dr Test Clinician 2",
        "role": "clinician",
        "permissions": ["triage:read", "triage:write", "triage:override", "audit:read"],
    },
    {
        "email": "clinical.lead@test.acucare.local",
        "name": "Dr Test Clinical Lead",
        "role": "clinical_lead",
        "permissions": ["triage:*", "audit:*", "admin:read"],
    },
    {
        "email": "reception@test.acucare.local",
        "name": "Test Reception",
        "role": "receptionist",
        "permissions": ["triage:read", "scheduling:read", "scheduling:write"],
    },
    {
        "email": "readonly@test.acucare.local",
        "name": "Test ReadOnly",
        "role": "readonly",
        "permissions": ["triage:read", "audit:read"],
    },
]


# Test patient accounts for patient portal testing
TEST_PATIENTS = [
    {
        "email": "patient1@test.acucare.local",
        "first_name": "Test",
        "last_name": "Patient One",
        "phone": "+44 7700 900001",
    },
    {
        "email": "patient2@test.acucare.local",
        "first_name": "Test",
        "last_name": "Patient Two",
        "phone": "+44 7700 900002",
    },
    {
        "email": "patient3@test.acucare.local",
        "first_name": "Test",
        "last_name": "Patient Three",
        "phone": "+44 7700 900003",
    },
]


def generate_temp_password() -> str:
    """Generate a temporary password for test accounts."""
    return f"Test{secrets.token_urlsafe(8)}!"


async def create_accounts_db():
    """Create test accounts in database."""
    try:
        from app.db.session import async_session_maker
        from app.models.user import User
        from app.core.security import hash_password
        from sqlalchemy import select

        async with async_session_maker() as session:
            created = []
            skipped = []

            for account in TEST_ACCOUNTS:
                # Check if exists
                existing = await session.scalar(
                    select(User).where(User.email == account["email"])
                )

                if existing:
                    skipped.append(account["email"])
                    continue

                # Create new account - split name into first/last
                name_parts = account["name"].split(" ", 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ""

                temp_password = generate_temp_password()
                user = User(
                    email=account["email"],
                    first_name=first_name,
                    last_name=last_name,
                    role=account["role"],
                    hashed_password=hash_password(temp_password),
                    is_active=True,
                    mfa_enabled=False,  # Disabled for testing
                )
                session.add(user)
                created.append({
                    "email": account["email"],
                    "password": temp_password,
                    "role": account["role"],
                })

            await session.commit()

            return created, skipped

    except ImportError as e:
        print(f"Could not import app modules: {e}")
        return None, None


async def create_patients_db():
    """Create test patients in database."""
    try:
        from app.db.session import async_session_maker
        from app.models.patient import Patient
        from sqlalchemy import select

        async with async_session_maker() as session:
            created = []
            skipped = []

            for patient in TEST_PATIENTS:
                # Check if exists
                existing = await session.scalar(
                    select(Patient).where(Patient.email == patient["email"])
                )

                if existing:
                    skipped.append(patient["email"])
                    continue

                # Create new patient
                new_patient = Patient(
                    email=patient["email"],
                    first_name=patient["first_name"],
                    last_name=patient["last_name"],
                    phone=patient.get("phone"),
                    is_active=True,
                )
                session.add(new_patient)
                created.append(patient["email"])

            await session.commit()

            return created, skipped

    except ImportError as e:
        print(f"Could not import app modules: {e}")
        return None, None


def create_accounts_standalone():
    """Generate account creation SQL for manual execution."""
    print("=" * 60)
    print("TEST ACCOUNT SQL (run manually if DB connection unavailable)")
    print("=" * 60)
    print()

    for account in TEST_ACCOUNTS:
        temp_password = generate_temp_password()
        name_parts = account["name"].split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        print(f"-- {account['name']} ({account['role']})")
        print(f"-- Email: {account['email']}")
        print(f"-- Temp Password: {temp_password}")
        print(f"INSERT INTO users (id, email, first_name, last_name, role, hashed_password, is_active, mfa_enabled, created_at, updated_at)")
        print(f"VALUES (gen_random_uuid(), '{account['email']}', '{first_name}', '{last_name}', '{account['role']}', 'PLACEHOLDER_HASH', true, false, NOW(), NOW());")
        print()


def print_accounts(created: list, skipped: list):
    """Print created accounts summary."""
    print("=" * 60)
    print("TEST ACCOUNTS CREATED")
    print("=" * 60)
    print()

    if created:
        print("NEW ACCOUNTS:")
        print("-" * 60)
        print(f"{'Email':<40} {'Password':<20}")
        print("-" * 60)
        for acc in created:
            print(f"{acc['email']:<40} {acc['password']:<20}")
        print()
        print("⚠️  Save these passwords - they are temporary and shown only once.")
        print()

    if skipped:
        print("SKIPPED (already exist):")
        for email in skipped:
            print(f"  - {email}")
        print()

    print("=" * 60)
    print()
    print("Test account emails use @test.acucare.local domain.")
    print("MFA is disabled for test accounts.")
    print()


async def main():
    """Main entry point."""
    print("Creating test staff accounts...")
    print()

    created, skipped = await create_accounts_db()

    if created is None:
        print("Database connection failed. Generating SQL instead...")
        create_accounts_standalone()
    else:
        print_accounts(created, skipped)

    # Create test patients
    print()
    print("Creating test patient accounts...")
    print()

    patients_created, patients_skipped = await create_patients_db()

    if patients_created is not None:
        print("=" * 60)
        print("TEST PATIENTS CREATED")
        print("=" * 60)
        print()
        if patients_created:
            print("NEW PATIENTS:")
            for email in patients_created:
                print(f"  - {email}")
            print()
        if patients_skipped:
            print("SKIPPED (already exist):")
            for email in patients_skipped:
                print(f"  - {email}")
            print()
        print("Patients use magic link authentication (no password).")
        print("Request a magic link via the patient portal.")


if __name__ == "__main__":
    asyncio.run(main())

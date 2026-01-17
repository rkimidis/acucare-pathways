"""Create test scheduling data (appointment types, clinician profiles, availability)."""

import asyncio
from datetime import datetime, time, timezone, timedelta
from uuid import uuid4

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.scheduling import AppointmentType, ClinicianProfile, AvailabilitySlot
from app.models.user import User, UserRole


async def create_scheduling_data():
    """Create appointment types, clinician profile, and availability slots."""
    async with AsyncSessionLocal() as session:
        # Check if appointment types already exist
        result = await session.execute(select(AppointmentType).limit(1))
        if result.scalar_one_or_none():
            print("Appointment types already exist, skipping...")
        else:
            # Create appointment types
            types = [
                AppointmentType(
                    id=str(uuid4()),
                    code="INITIAL_ASSESSMENT",
                    name="Initial Assessment",
                    description="First appointment with a therapist",
                    duration_minutes=60,
                    buffer_before_minutes=0,
                    buffer_after_minutes=15,
                    is_bookable=True,
                    allowed_tiers=["green", "amber"],
                    display_order=1,
                ),
                AppointmentType(
                    id=str(uuid4()),
                    code="FOLLOW_UP",
                    name="Follow-up Session",
                    description="Regular therapy session",
                    duration_minutes=50,
                    buffer_before_minutes=0,
                    buffer_after_minutes=10,
                    is_bookable=True,
                    allowed_tiers=["green", "amber", "blue"],
                    display_order=2,
                ),
                AppointmentType(
                    id=str(uuid4()),
                    code="URGENT_REVIEW",
                    name="Urgent Clinical Review",
                    description="Urgent appointment for clinical review",
                    duration_minutes=30,
                    buffer_before_minutes=0,
                    buffer_after_minutes=5,
                    is_bookable=False,  # Not self-bookable
                    allowed_tiers=["red", "amber"],
                    display_order=3,
                ),
            ]
            for t in types:
                session.add(t)
            print(f"Created {len(types)} appointment types")
            await session.flush()

        # Get the initial assessment type for later
        result = await session.execute(
            select(AppointmentType).where(AppointmentType.code == "INITIAL_ASSESSMENT")
        )
        initial_assessment = result.scalar_one()
        print(f"Initial Assessment type ID: {initial_assessment.id}")

        # Find a clinician user to create profile for
        result = await session.execute(
            select(User).where(User.role == UserRole.CLINICIAN).limit(1)
        )
        clinician_user = result.scalar_one_or_none()

        if not clinician_user:
            # Use admin user if no clinician exists
            result = await session.execute(
                select(User).where(User.role == UserRole.ADMIN).limit(1)
            )
            clinician_user = result.scalar_one_or_none()

        if not clinician_user:
            print("No users found to create clinician profile for!")
            return

        print(f"Using user {clinician_user.email} for clinician profile")

        # Check if clinician profile exists
        result = await session.execute(
            select(ClinicianProfile).where(ClinicianProfile.user_id == clinician_user.id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            profile = ClinicianProfile(
                id=str(uuid4()),
                user_id=clinician_user.id,
                title="Dr",
                specialty="Clinical Psychology",
                bio="Experienced clinical psychologist specializing in anxiety and depression.",
                qualifications=["DClinPsy", "CPsychol", "HCPC Registered"],
                accepting_new_patients=True,
                max_daily_appointments=8,
            )
            session.add(profile)
            print(f"Created clinician profile: {profile.id}")
            await session.flush()
        else:
            print(f"Clinician profile already exists: {profile.id}")

        # Create availability slots for next 7 days
        result = await session.execute(
            select(AvailabilitySlot).where(AvailabilitySlot.clinician_id == profile.id).limit(1)
        )
        if result.scalar_one_or_none():
            print("Availability slots already exist, skipping...")
        else:
            today = datetime.now(timezone.utc).date()
            slots_created = 0

            for day_offset in range(1, 8):  # Next 7 days
                slot_date = today + timedelta(days=day_offset)

                # Skip weekends
                if slot_date.weekday() >= 5:
                    continue

                # Morning slots: 9 AM - 12 PM
                for hour in [9, 10, 11]:
                    slot = AvailabilitySlot(
                        id=str(uuid4()),
                        clinician_id=profile.id,
                        date=slot_date,
                        start_time=time(hour, 0),
                        end_time=time(hour + 1, 0),
                        is_available=True,
                    )
                    session.add(slot)
                    slots_created += 1

                # Afternoon slots: 2 PM - 5 PM
                for hour in [14, 15, 16]:
                    slot = AvailabilitySlot(
                        id=str(uuid4()),
                        clinician_id=profile.id,
                        date=slot_date,
                        start_time=time(hour, 0),
                        end_time=time(hour + 1, 0),
                        is_available=True,
                    )
                    session.add(slot)
                    slots_created += 1

            print(f"Created {slots_created} availability slots")

        await session.commit()

        print("\n=== Summary ===")
        print(f"Clinician Profile ID: {profile.id}")
        print(f"Initial Assessment Type ID: {initial_assessment.id}")
        print("Scheduling data setup complete!")


if __name__ == "__main__":
    asyncio.run(create_scheduling_data())

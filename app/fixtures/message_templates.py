"""Message template fixtures for AcuCare Pathways.

These templates are used for automated patient communications.
Run this script to seed the database with default templates.
"""

from app.models.messaging import MessageChannel, MessageTemplateType

# Default message templates
MESSAGE_TEMPLATES = [
    # =========================================================================
    # Appointment Confirmation (Email)
    # =========================================================================
    {
        "code": "appointment_confirmed_email",
        "template_type": MessageTemplateType.APPOINTMENT_CONFIRMATION,
        "channel": MessageChannel.EMAIL,
        "subject": "Your appointment is confirmed",
        "body": """Your appointment is confirmed

Date: {{date}}
Time: {{time}}
Clinician: {{clinician_name}}
Format: {{format}}

You can manage or reschedule your appointment via your patient portal.

If you're unable to attend, please let us know as early as possible.

Best regards,
The AcuCare Team""",
        "html_body": """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #3b82f6, #1d4ed8); color: white; padding: 24px; border-radius: 8px 8px 0 0; }
        .header h1 { margin: 0; font-size: 24px; }
        .content { background: #f8fafc; padding: 24px; border: 1px solid #e2e8f0; }
        .appointment-details { background: white; border-radius: 8px; padding: 20px; margin: 16px 0; border: 1px solid #e2e8f0; }
        .detail-row { display: flex; padding: 8px 0; border-bottom: 1px solid #f1f5f9; }
        .detail-row:last-child { border-bottom: none; }
        .detail-label { font-weight: 600; color: #64748b; width: 100px; }
        .detail-value { color: #1e293b; }
        .footer { background: #f1f5f9; padding: 16px 24px; border-radius: 0 0 8px 8px; font-size: 14px; color: #64748b; }
        .cta-button { display: inline-block; background: #3b82f6; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 500; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✓ Your appointment is confirmed</h1>
        </div>
        <div class="content">
            <div class="appointment-details">
                <div class="detail-row">
                    <span class="detail-label">Date</span>
                    <span class="detail-value">{{date}}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Time</span>
                    <span class="detail-value">{{time}}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Clinician</span>
                    <span class="detail-value">{{clinician_name}}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Format</span>
                    <span class="detail-value">{{format}}</span>
                </div>
            </div>
            <p>You can manage or reschedule your appointment via your patient portal.</p>
            <p><a href="{{portal_url}}" class="cta-button">View in Patient Portal</a></p>
        </div>
        <div class="footer">
            <p>If you're unable to attend, please let us know as early as possible.</p>
            <p>The AcuCare Team</p>
        </div>
    </div>
</body>
</html>
""",
        "variables": {
            "date": "Appointment date (e.g., Monday, 15 January 2026)",
            "time": "Appointment time (e.g., 10:00)",
            "clinician_name": "Name of the clinician",
            "format": "In-person or Video",
            "portal_url": "URL to patient portal",
        },
    },
    # =========================================================================
    # Appointment Confirmation (SMS)
    # =========================================================================
    {
        "code": "appointment_confirmed_sms",
        "template_type": MessageTemplateType.APPOINTMENT_CONFIRMATION,
        "channel": MessageChannel.SMS,
        "subject": None,
        "body": "Your appointment is confirmed:\n{{date}} at {{time}}\nWith: {{clinician_name}}\nFormat: {{format}}\n\nManage via your patient portal. If unable to attend, please let us know.",
        "html_body": None,
        "variables": {
            "date": "Appointment date",
            "time": "Appointment time",
            "clinician_name": "Clinician name",
            "format": "In-person or Video",
        },
    },
    # =========================================================================
    # Appointment Reminder (Email)
    # =========================================================================
    {
        "code": "appointment_reminder_email",
        "template_type": MessageTemplateType.APPOINTMENT_REMINDER,
        "channel": MessageChannel.EMAIL,
        "subject": "Reminder: Your appointment is tomorrow",
        "body": """Hi {{patient_name}},

This is a reminder about your upcoming appointment:

Date: {{date}}
Time: {{time}}
Clinician: {{clinician_name}}
Format: {{format}}
{{#if location}}Location: {{location}}{{/if}}
{{#if video_link}}Video link: {{video_link}}{{/if}}

If you need to reschedule or cancel, please do so via your patient portal at least 24 hours in advance.

We look forward to seeing you.

The AcuCare Team""",
        "html_body": None,
        "variables": {
            "patient_name": "Patient's first name",
            "date": "Appointment date",
            "time": "Appointment time",
            "clinician_name": "Clinician name",
            "format": "In-person or Video",
            "location": "Physical location (if in-person)",
            "video_link": "Video consultation link (if remote)",
        },
    },
    # =========================================================================
    # Appointment Reminder (SMS)
    # =========================================================================
    {
        "code": "appointment_reminder_sms",
        "template_type": MessageTemplateType.APPOINTMENT_REMINDER,
        "channel": MessageChannel.SMS,
        "subject": None,
        "body": "Reminder: AcuCare appointment tomorrow at {{time}} with {{clinician_name}}. {{format}}. Need to reschedule? Visit your patient portal.",
        "html_body": None,
        "variables": {
            "time": "Appointment time",
            "clinician_name": "Clinician name",
            "format": "In-person or Video",
        },
    },
    # =========================================================================
    # Intake Reminder 24h (Email)
    # =========================================================================
    {
        "code": "intake_reminder_24h_email",
        "template_type": MessageTemplateType.INTAKE_REMINDER_24H,
        "channel": MessageChannel.EMAIL,
        "subject": "Continue your AcuCare assessment",
        "body": """Hi {{patient_name}},

We noticed you started your mental health assessment but haven't completed it yet.

Your wellbeing matters to us, and we want to make sure you get the support you need.

You can continue where you left off by visiting your AcuCare portal.

If you're having any difficulties with the questionnaire, please don't hesitate to contact us at support@acucare.nhs.uk.

Take care,
The AcuCare Team""",
        "html_body": None,
        "variables": {
            "patient_name": "Patient's first name or 'there'",
            "resume_url": "URL to resume intake",
        },
    },
    # =========================================================================
    # Intake Reminder 72h (Email)
    # =========================================================================
    {
        "code": "intake_reminder_72h_email",
        "template_type": MessageTemplateType.INTAKE_REMINDER_72H,
        "channel": MessageChannel.EMAIL,
        "subject": "We're still here for you - complete your assessment",
        "body": """Hi {{patient_name}},

We wanted to reach out one more time about your mental health assessment.

We understand that starting this process can feel daunting. There's no pressure, and you can take your time.

Your assessment will remain available for you to complete whenever you're ready.

If something is holding you back, or if you'd prefer to speak to someone directly, please call us on 0800 123 4567 or email support@acucare.nhs.uk.

We're here to support you.

Warm regards,
The AcuCare Team

This is our final reminder - we won't send any more emails about this assessment.""",
        "html_body": None,
        "variables": {
            "patient_name": "Patient's first name or 'there'",
            "resume_url": "URL to resume intake",
        },
    },
    # =========================================================================
    # Appointment Confirm Request (Email)
    # =========================================================================
    {
        "code": "appointment_confirm_request_email",
        "template_type": MessageTemplateType.APPOINTMENT_CONFIRM_REQUEST,
        "channel": MessageChannel.EMAIL,
        "subject": "Please confirm your appointment on {{appointment_date}}",
        "body": """Hi {{patient_name}},

Your appointment is coming up:

Date: {{appointment_date}}
Time: {{appointment_time}}
Location: {{location}}

Please let us know if you can attend by clicking the link below or logging into your patient portal.

[Confirm attendance]

If you need to reschedule or cancel, please do so at least 24 hours before your appointment.

Best regards,
The AcuCare Team""",
        "html_body": None,
        "variables": {
            "patient_name": "Patient's first name",
            "appointment_date": "Appointment date",
            "appointment_time": "Appointment time",
            "location": "Location or 'Video Consultation'",
            "confirm_url": "URL to confirm",
            "reschedule_url": "URL to reschedule",
        },
    },
    # =========================================================================
    # Still Want Appointment (Email)
    # =========================================================================
    {
        "code": "still_want_appointment_email",
        "template_type": MessageTemplateType.STILL_WANT_APPOINTMENT,
        "channel": MessageChannel.EMAIL,
        "subject": "Are you still planning to attend your appointment?",
        "body": """Hi {{patient_name}},

We noticed you have an appointment scheduled for {{appointment_date}} at {{appointment_time}}.

We wanted to check if this still works for you. If your circumstances have changed, that's completely fine - just let us know so we can free up the slot for someone else.

Please log into your patient portal to confirm, reschedule, or cancel.

If we don't hear from you, we'll keep your appointment as scheduled.

Best regards,
The AcuCare Team""",
        "html_body": None,
        "variables": {
            "patient_name": "Patient's first name",
            "appointment_date": "Appointment date",
            "appointment_time": "Appointment time",
            "confirm_url": "URL to confirm",
            "cancel_url": "URL to cancel",
        },
    },
]


async def seed_templates(session):
    """Seed the database with default message templates.

    Args:
        session: AsyncSession database session
    """
    from sqlalchemy import select
    from app.models.messaging import MessageTemplate

    for template_data in MESSAGE_TEMPLATES:
        # Check if template already exists
        result = await session.execute(
            select(MessageTemplate).where(
                MessageTemplate.code == template_data["code"]
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing template
            for key, value in template_data.items():
                if key != "code":
                    setattr(existing, key, value)
        else:
            # Create new template
            template = MessageTemplate(
                code=template_data["code"],
                template_type=template_data["template_type"],
                channel=template_data["channel"],
                subject=template_data["subject"],
                body=template_data["body"],
                html_body=template_data.get("html_body"),
                variables=template_data.get("variables"),
                is_active=True,
                version=1,
            )
            session.add(template)

    await session.commit()


if __name__ == "__main__":
    import asyncio
    import os
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    async def main():
        db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://localhost/acucare")
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        engine = create_async_engine(db_url)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            await seed_templates(session)
            print(f"Seeded {len(MESSAGE_TEMPLATES)} message templates")

        await engine.dispose()

    asyncio.run(main())

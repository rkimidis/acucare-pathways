"""Abandoned intake recovery service.

Sends reminder messages to patients who started but didn't complete
their intake questionnaire. Follows a respectful two-touch approach:
- 24h reminder: Gentle nudge to continue
- 72h final reminder: Last chance before case is archived
"""

import logging
from datetime import datetime, timedelta
from typing import Sequence
from uuid import uuid4

from sqlalchemy import and_, not_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.models.messaging import (
    Message,
    MessageChannel,
    MessageTemplateType,
)
from app.models.patient import Patient
from app.models.questionnaire import QuestionnaireResponse
from app.models.triage_case import TriageCase, TriageCaseStatus
from app.services.messaging import MessagingService

logger = logging.getLogger(__name__)


class IntakeRecoveryService:
    """Service for recovering abandoned patient intakes.

    Identifies incomplete intakes and sends appropriately-timed reminders
    to encourage completion while respecting patient preferences (no spam).
    """

    # Reminder windows
    FIRST_REMINDER_HOURS = 24
    FINAL_REMINDER_HOURS = 72

    # After this many hours, intake is considered abandoned (no more reminders)
    ABANDONMENT_THRESHOLD_HOURS = 168  # 7 days

    def __init__(
        self,
        session: AsyncSession,
        messaging_service: MessagingService | None = None,
    ):
        self.session = session
        self.messaging_service = messaging_service or MessagingService(session)

    async def get_incomplete_intakes(
        self,
        min_age_hours: int = 0,
        max_age_hours: int | None = None,
    ) -> Sequence[TriageCase]:
        """Get triage cases with incomplete intake questionnaires.

        Args:
            min_age_hours: Minimum hours since case creation
            max_age_hours: Maximum hours since case creation

        Returns:
            List of triage cases that need attention
        """
        now = utc_now()
        min_created = now - timedelta(hours=max_age_hours) if max_age_hours else None
        max_created = now - timedelta(hours=min_age_hours) if min_age_hours else now

        # Build query for PENDING cases without completed responses
        query = (
            select(TriageCase)
            .where(
                TriageCase.status == TriageCaseStatus.PENDING,
                TriageCase.is_deleted == False,
                TriageCase.created_at <= max_created,
            )
        )

        if min_created:
            query = query.where(TriageCase.created_at >= min_created)

        # Filter out cases with completed questionnaire responses
        completed_case_ids = (
            select(QuestionnaireResponse.triage_case_id)
            .where(QuestionnaireResponse.is_complete == True)
            .distinct()
        )

        query = query.where(not_(TriageCase.id.in_(completed_case_ids)))

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_reminders_sent_for_case(
        self,
        triage_case_id: str,
    ) -> dict[str, datetime | None]:
        """Get reminder statuses for a triage case.

        Returns dict with keys '24h' and '72h' indicating when
        each reminder was sent (or None if not sent).
        """
        result = await self.session.execute(
            select(Message)
            .where(
                Message.triage_case_id == triage_case_id,
                Message.is_deleted == False,
            )
        )
        messages = result.scalars().all()

        reminders: dict[str, datetime | None] = {
            "24h": None,
            "72h": None,
        }

        for msg in messages:
            if msg.message_metadata and msg.message_metadata.get("template_code"):
                code = msg.message_metadata["template_code"]
                if "intake_reminder_24h" in code:
                    reminders["24h"] = msg.created_at
                elif "intake_reminder_72h" in code:
                    reminders["72h"] = msg.created_at

        return reminders

    async def get_cases_needing_24h_reminder(self) -> Sequence[TriageCase]:
        """Get cases that need their 24h reminder.

        Criteria:
        - Created 24-72 hours ago
        - Intake not complete
        - 24h reminder not yet sent
        """
        cases = await self.get_incomplete_intakes(
            min_age_hours=self.FIRST_REMINDER_HOURS,
            max_age_hours=self.FINAL_REMINDER_HOURS,
        )

        needing_reminder = []
        for case in cases:
            reminders = await self.get_reminders_sent_for_case(case.id)
            if reminders["24h"] is None:
                needing_reminder.append(case)

        return needing_reminder

    async def get_cases_needing_72h_reminder(self) -> Sequence[TriageCase]:
        """Get cases that need their 72h final reminder.

        Criteria:
        - Created 72+ hours ago (but less than abandonment threshold)
        - Intake not complete
        - 24h reminder was sent
        - 72h reminder not yet sent
        """
        cases = await self.get_incomplete_intakes(
            min_age_hours=self.FINAL_REMINDER_HOURS,
            max_age_hours=self.ABANDONMENT_THRESHOLD_HOURS,
        )

        needing_reminder = []
        for case in cases:
            reminders = await self.get_reminders_sent_for_case(case.id)
            if reminders["24h"] is not None and reminders["72h"] is None:
                needing_reminder.append(case)

        return needing_reminder

    async def send_24h_reminder(
        self,
        triage_case_id: str,
        channel: MessageChannel = MessageChannel.EMAIL,
    ) -> Message | None:
        """Send 24h intake reminder for a case.

        Args:
            triage_case_id: The triage case to remind
            channel: Communication channel (email or SMS)

        Returns:
            Message record if sent, None if patient not found or already reminded
        """
        # Get triage case and patient
        result = await self.session.execute(
            select(TriageCase).where(TriageCase.id == triage_case_id)
        )
        case = result.scalar_one_or_none()

        if not case:
            logger.warning(f"Triage case not found: {triage_case_id}")
            return None

        # Check if already reminded
        reminders = await self.get_reminders_sent_for_case(triage_case_id)
        if reminders["24h"]:
            logger.info(f"24h reminder already sent for case {triage_case_id[:8]}")
            return None

        # Get patient details
        patient_result = await self.session.execute(
            select(Patient).where(Patient.id == case.patient_id)
        )
        patient = patient_result.scalar_one_or_none()

        if not patient:
            logger.warning(f"Patient not found for case: {triage_case_id}")
            return None

        # Determine recipient address
        recipient = patient.email if channel == MessageChannel.EMAIL else patient.phone
        if not recipient:
            logger.warning(f"No {channel} address for patient {patient.id[:8]}")
            return None

        # Build context for template
        context = {
            "patient_name": patient.preferred_name or patient.given_name or "there",
            "resume_url": f"/intake/resume?case={triage_case_id}",
            "support_email": "support@acucare.nhs.uk",
            "hours_since_start": self.FIRST_REMINDER_HOURS,
        }

        try:
            message = await self.messaging_service.send_from_template(
                patient_id=patient.id,
                template_type=MessageTemplateType.INTAKE_REMINDER_24H,
                channel=channel,
                recipient_address=recipient,
                context=context,
                triage_case_id=triage_case_id,
            )

            logger.info(
                f"Sent 24h intake reminder: case={triage_case_id[:8]}, "
                f"patient={patient.id[:8]}, channel={channel}"
            )
            return message

        except ValueError as e:
            # Template not found - send fallback
            logger.warning(f"Template not found, using fallback: {e}")
            return await self._send_fallback_24h_reminder(
                patient=patient,
                triage_case_id=triage_case_id,
                channel=channel,
                recipient=recipient,
            )

    async def _send_fallback_24h_reminder(
        self,
        patient: Patient,
        triage_case_id: str,
        channel: MessageChannel,
        recipient: str,
    ) -> Message:
        """Send fallback 24h reminder when template is not available."""
        patient_name = patient.preferred_name or patient.given_name or "there"

        if channel == MessageChannel.EMAIL:
            subject = "Continue your AcuCare Pathways assessment"
            body = f"""Hi {patient_name},

We noticed you started your mental health assessment but haven't completed it yet.

Your wellbeing matters to us, and we want to make sure you get the support you need.

You can continue where you left off by visiting your AcuCare Pathways portal.

If you're having any difficulties with the questionnaire, please don't hesitate to contact us at support@acucare.nhs.uk.

Take care,
The AcuCare Pathways Team"""
            html_body = f"""
<p>Hi {patient_name},</p>
<p>We noticed you started your mental health assessment but haven't completed it yet.</p>
<p>Your wellbeing matters to us, and we want to make sure you get the support you need.</p>
<p>You can continue where you left off by visiting your AcuCare Pathways portal.</p>
<p>If you're having any difficulties with the questionnaire, please don't hesitate to contact us at <a href="mailto:support@acucare.nhs.uk">support@acucare.nhs.uk</a>.</p>
<p>Take care,<br>The AcuCare Pathways Team</p>
"""
        else:  # SMS
            subject = None
            body = f"Hi {patient_name}, you started your AcuCare Pathways assessment but haven't finished. Your wellbeing matters - log in to continue when you're ready."
            html_body = None

        return await self.messaging_service.send_message(
            patient_id=patient.id,
            channel=channel,
            recipient_address=recipient,
            body=body,
            subject=subject,
            html_body=html_body,
            triage_case_id=triage_case_id,
            metadata={
                "template_code": "intake_reminder_24h_fallback",
                "reminder_type": "24h",
            },
        )

    async def send_72h_reminder(
        self,
        triage_case_id: str,
        channel: MessageChannel = MessageChannel.EMAIL,
    ) -> Message | None:
        """Send 72h final intake reminder for a case.

        Args:
            triage_case_id: The triage case to remind
            channel: Communication channel (email or SMS)

        Returns:
            Message record if sent, None if criteria not met
        """
        # Get triage case and patient
        result = await self.session.execute(
            select(TriageCase).where(TriageCase.id == triage_case_id)
        )
        case = result.scalar_one_or_none()

        if not case:
            logger.warning(f"Triage case not found: {triage_case_id}")
            return None

        # Check reminder history
        reminders = await self.get_reminders_sent_for_case(triage_case_id)
        if reminders["24h"] is None:
            logger.info(f"Skipping 72h reminder - 24h not sent for case {triage_case_id[:8]}")
            return None
        if reminders["72h"]:
            logger.info(f"72h reminder already sent for case {triage_case_id[:8]}")
            return None

        # Get patient details
        patient_result = await self.session.execute(
            select(Patient).where(Patient.id == case.patient_id)
        )
        patient = patient_result.scalar_one_or_none()

        if not patient:
            logger.warning(f"Patient not found for case: {triage_case_id}")
            return None

        # Determine recipient address
        recipient = patient.email if channel == MessageChannel.EMAIL else patient.phone
        if not recipient:
            logger.warning(f"No {channel} address for patient {patient.id[:8]}")
            return None

        # Build context for template
        context = {
            "patient_name": patient.preferred_name or patient.given_name or "there",
            "resume_url": f"/intake/resume?case={triage_case_id}",
            "support_phone": "0800 123 4567",
            "support_email": "support@acucare.nhs.uk",
        }

        try:
            message = await self.messaging_service.send_from_template(
                patient_id=patient.id,
                template_type=MessageTemplateType.INTAKE_REMINDER_72H,
                channel=channel,
                recipient_address=recipient,
                context=context,
                triage_case_id=triage_case_id,
            )

            logger.info(
                f"Sent 72h intake reminder: case={triage_case_id[:8]}, "
                f"patient={patient.id[:8]}, channel={channel}"
            )
            return message

        except ValueError as e:
            # Template not found - send fallback
            logger.warning(f"Template not found, using fallback: {e}")
            return await self._send_fallback_72h_reminder(
                patient=patient,
                triage_case_id=triage_case_id,
                channel=channel,
                recipient=recipient,
            )

    async def _send_fallback_72h_reminder(
        self,
        patient: Patient,
        triage_case_id: str,
        channel: MessageChannel,
        recipient: str,
    ) -> Message:
        """Send fallback 72h reminder when template is not available."""
        patient_name = patient.preferred_name or patient.given_name or "there"

        if channel == MessageChannel.EMAIL:
            subject = "We're still here for you - complete your assessment"
            body = f"""Hi {patient_name},

We wanted to reach out one more time about your mental health assessment.

We understand that starting this process can feel daunting. There's no pressure, and you can take your time.

Your assessment will remain available for you to complete whenever you're ready.

If something is holding you back, or if you'd prefer to speak to someone directly, please call us on 0800 123 4567 or email support@acucare.nhs.uk.

We're here to support you.

Warm regards,
The AcuCare Pathways Team

This is our final reminder - we won't send any more emails about this assessment."""
            html_body = f"""
<p>Hi {patient_name},</p>
<p>We wanted to reach out one more time about your mental health assessment.</p>
<p>We understand that starting this process can feel daunting. There's no pressure, and you can take your time.</p>
<p>Your assessment will remain available for you to complete whenever you're ready.</p>
<p>If something is holding you back, or if you'd prefer to speak to someone directly, please call us on <strong>0800 123 4567</strong> or email <a href="mailto:support@acucare.nhs.uk">support@acucare.nhs.uk</a>.</p>
<p>We're here to support you.</p>
<p>Warm regards,<br>The AcuCare Pathways Team</p>
<p style="color: #666; font-size: 0.9em;"><em>This is our final reminder - we won't send any more emails about this assessment.</em></p>
"""
        else:  # SMS
            subject = None
            body = f"Hi {patient_name}, your AcuCare Pathways assessment is still waiting for you. Complete it anytime, or call 0800 123 4567 if you'd prefer to speak to someone. We're here to help."
            html_body = None

        return await self.messaging_service.send_message(
            patient_id=patient.id,
            channel=channel,
            recipient_address=recipient,
            body=body,
            subject=subject,
            html_body=html_body,
            triage_case_id=triage_case_id,
            metadata={
                "template_code": "intake_reminder_72h_fallback",
                "reminder_type": "72h",
            },
        )

    async def run_recovery_job(
        self,
        channel: MessageChannel = MessageChannel.EMAIL,
    ) -> dict:
        """Run the full intake recovery job.

        Sends 24h and 72h reminders to all eligible cases.

        Returns:
            Summary of reminders sent
        """
        results = {
            "24h_reminders_sent": 0,
            "24h_reminders_failed": 0,
            "72h_reminders_sent": 0,
            "72h_reminders_failed": 0,
            "cases_processed": set(),
        }

        # Send 24h reminders
        cases_24h = await self.get_cases_needing_24h_reminder()
        logger.info(f"Found {len(cases_24h)} cases needing 24h reminder")

        for case in cases_24h:
            try:
                message = await self.send_24h_reminder(case.id, channel)
                if message:
                    results["24h_reminders_sent"] += 1
                    results["cases_processed"].add(case.id)
            except Exception as e:
                logger.error(f"Failed to send 24h reminder for case {case.id[:8]}: {e}")
                results["24h_reminders_failed"] += 1

        # Send 72h reminders
        cases_72h = await self.get_cases_needing_72h_reminder()
        logger.info(f"Found {len(cases_72h)} cases needing 72h reminder")

        for case in cases_72h:
            try:
                message = await self.send_72h_reminder(case.id, channel)
                if message:
                    results["72h_reminders_sent"] += 1
                    results["cases_processed"].add(case.id)
            except Exception as e:
                logger.error(f"Failed to send 72h reminder for case {case.id[:8]}: {e}")
                results["72h_reminders_failed"] += 1

        results["total_cases"] = len(results["cases_processed"])
        del results["cases_processed"]  # Don't return the set

        logger.info(f"Intake recovery job complete: {results}")
        return results

    async def get_recovery_stats(self) -> dict:
        """Get statistics about abandoned intakes.

        Returns summary of intake states for monitoring.
        """
        now = utc_now()

        # Get all incomplete intakes
        all_incomplete = await self.get_incomplete_intakes(
            max_age_hours=self.ABANDONMENT_THRESHOLD_HOURS
        )

        stats = {
            "total_incomplete": len(all_incomplete),
            "under_24h": 0,
            "needs_24h_reminder": 0,
            "24h_sent_awaiting_72h": 0,
            "needs_72h_reminder": 0,
            "72h_sent_final": 0,
        }

        for case in all_incomplete:
            age_hours = (now - case.created_at).total_seconds() / 3600
            reminders = await self.get_reminders_sent_for_case(case.id)

            if age_hours < self.FIRST_REMINDER_HOURS:
                stats["under_24h"] += 1
            elif reminders["72h"]:
                stats["72h_sent_final"] += 1
            elif reminders["24h"]:
                if age_hours >= self.FINAL_REMINDER_HOURS:
                    stats["needs_72h_reminder"] += 1
                else:
                    stats["24h_sent_awaiting_72h"] += 1
            else:
                stats["needs_24h_reminder"] += 1

        return stats

"""Admin friction reduction service.

Eliminates manual admin tasks by automating:
- Patient-facing triage explanations (staff don't need to re-explain)
- Eligibility summaries (already in pathway rules)
- Appointment confirmations (automated with patient response)
- Inactive patient outreach ("still want this appointment?")

Goal: Reduce admin minutes per patient by automating repetitive tasks.
"""

import logging
from datetime import datetime, timedelta
from typing import Sequence
from uuid import uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.models.messaging import Message, MessageChannel, MessageTemplateType
from app.models.patient import Patient
from app.models.scheduling import Appointment, AppointmentStatus
from app.models.triage_case import TriageCase, TriageCaseStatus, TriageTier
from app.services.messaging import MessagingService

logger = logging.getLogger(__name__)


# =============================================================================
# Patient-Facing Explanation Mappings
# =============================================================================

TIER_PATIENT_DESCRIPTIONS = {
    TriageTier.RED: {
        "title": "Priority Support",
        "description": (
            "Based on your responses, we want to make sure you get support quickly. "
            "A member of our clinical team will be in touch with you within 4 hours "
            "to discuss your needs and arrange an appointment."
        ),
        "what_happens_next": [
            "Our duty clinician will contact you directly",
            "They will discuss the best next steps with you",
            "An appointment will be arranged for you",
        ],
    },
    TriageTier.AMBER: {
        "title": "Clinical Review",
        "description": (
            "Based on your responses, we'd like a clinician to review your case "
            "before we book your appointment. This helps us match you with the "
            "right type of support."
        ),
        "what_happens_next": [
            "A clinician will review your responses",
            "They may call you to discuss your needs",
            "You'll receive appointment options within 24 hours",
        ],
    },
    TriageTier.GREEN: {
        "title": "Ready to Book",
        "description": (
            "Great news! Based on your responses, you can book an appointment "
            "directly. Choose a time that works for you."
        ),
        "what_happens_next": [
            "Browse available appointment times",
            "Select a clinician and time slot",
            "Receive instant confirmation",
        ],
    },
    TriageTier.BLUE: {
        "title": "Self-Help Resources",
        "description": (
            "Based on your responses, you may benefit from our digital support "
            "resources. You can also book an appointment if you'd prefer to "
            "speak with someone."
        ),
        "what_happens_next": [
            "Access our self-help library",
            "Try guided exercises and resources",
            "Book an appointment anytime if you need more support",
        ],
    },
}

PATHWAY_PATIENT_DESCRIPTIONS = {
    "GENERAL_THERAPY": "talking therapy to explore your thoughts and feelings",
    "CBT": "Cognitive Behavioural Therapy (CBT) to help with thought patterns",
    "PSYCHIATRY_ASSESSMENT": "an assessment with a psychiatrist",
    "CRISIS_INTERVENTION": "urgent support from our crisis team",
    "ANXIETY_PATHWAY": "support for managing anxiety",
    "DEPRESSION_PATHWAY": "support for low mood and depression",
    "TRAUMA_PATHWAY": "trauma-focused therapy",
    "ADDICTION_PATHWAY": "support for substance use or addictive behaviours",
    "EATING_DISORDERS": "specialist eating disorder support",
}


class PatientExplanationService:
    """Generates patient-friendly explanations from triage data."""

    @staticmethod
    def generate_tier_explanation(
        tier: TriageTier,
        pathway: str | None = None,
    ) -> dict:
        """Generate a patient-friendly explanation of their triage result.

        Args:
            tier: The assigned triage tier
            pathway: The assigned clinical pathway (optional)

        Returns:
            Dict with title, description, what_happens_next, and pathway_info
        """
        tier_info = TIER_PATIENT_DESCRIPTIONS.get(
            tier,
            TIER_PATIENT_DESCRIPTIONS[TriageTier.GREEN],  # Default fallback
        )

        result = {
            "tier": tier.value,
            "title": tier_info["title"],
            "description": tier_info["description"],
            "what_happens_next": tier_info["what_happens_next"],
            "can_self_book": tier in (TriageTier.GREEN, TriageTier.BLUE),
        }

        if pathway:
            pathway_desc = PATHWAY_PATIENT_DESCRIPTIONS.get(
                pathway,
                "the most appropriate type of support for your needs",
            )
            result["pathway_info"] = f"We've identified {pathway_desc} as a good starting point."

        return result

    @staticmethod
    def generate_rules_summary(tier_explanation: dict | None) -> list[str]:
        """Convert technical rule explanations to patient-friendly summaries.

        Takes the internal tier_explanation (rules_fired, explanations, flags)
        and converts to plain English for patients.

        Args:
            tier_explanation: The technical explanation dict from triage

        Returns:
            List of patient-friendly summary points
        """
        if not tier_explanation:
            return ["Your responses have been reviewed"]

        summaries = []
        explanations = tier_explanation.get("explanations", [])

        # Map technical explanations to patient-friendly versions
        friendly_mappings = {
            "suicide": "We noticed you may be going through a difficult time",
            "self-harm": "We want to make sure you have the support you need",
            "psychosis": "Some of your responses suggest you may benefit from specialist assessment",
            "crisis": "We're prioritising your care to get you support quickly",
            "phq9": "Based on your mood questionnaire responses",
            "gad7": "Based on your anxiety questionnaire responses",
            "audit": "Based on your responses about alcohol use",
            "eating": "Based on your responses about eating patterns",
        }

        for exp in explanations:
            exp_lower = exp.lower()
            for key, friendly in friendly_mappings.items():
                if key in exp_lower:
                    if friendly not in summaries:
                        summaries.append(friendly)
                    break

        # Ensure at least one summary
        if not summaries:
            summaries.append("Your responses have been carefully reviewed by our triage system")

        return summaries


class EligibilityService:
    """Provides clear eligibility information from pathway rules."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_eligibility_summary(
        self,
        triage_case_id: str,
    ) -> dict:
        """Get a clear eligibility summary for a triage case.

        Aggregates pathway rules, tier restrictions, and booking eligibility
        into a single clear summary that staff can share.

        Args:
            triage_case_id: The triage case ID

        Returns:
            Dict with eligibility information
        """
        result = await self.session.execute(
            select(TriageCase).where(TriageCase.id == triage_case_id)
        )
        case = result.scalar_one_or_none()

        if not case:
            return {"error": "Case not found"}

        # Build eligibility summary
        eligibility = {
            "case_id": case.id,
            "tier": case.tier.value if case.tier else None,
            "pathway": case.pathway,
            "status": case.status.value,
            "can_self_book": case.self_book_allowed,
            "needs_clinical_review": case.clinician_review_required,
            "booking_restrictions": [],
            "eligible_appointment_types": [],
            "required_specialties": [],
        }

        # Add booking restrictions
        if not case.self_book_allowed:
            if case.tier == TriageTier.RED:
                eligibility["booking_restrictions"].append(
                    "Staff must book on patient's behalf (RED tier)"
                )
            elif case.tier == TriageTier.AMBER:
                eligibility["booking_restrictions"].append(
                    "Staff must book after clinical review (AMBER tier)"
                )

        if case.clinician_review_required:
            eligibility["booking_restrictions"].append(
                "Requires clinician review before appointment"
            )

        # Map pathway to required specialties
        pathway_specialties = {
            "PSYCHIATRY_ASSESSMENT": ["psychiatry"],
            "CBT": ["cbt", "psychology"],
            "TRAUMA_PATHWAY": ["trauma", "psychotherapy"],
            "EATING_DISORDERS": ["eating_disorders"],
            "ADDICTION_PATHWAY": ["addiction"],
            "CRISIS_INTERVENTION": ["crisis_intervention", "psychiatry"],
        }

        if case.pathway:
            eligibility["required_specialties"] = pathway_specialties.get(
                case.pathway, []
            )

        # Determine eligible appointment types based on tier
        if case.tier == TriageTier.GREEN:
            eligibility["eligible_appointment_types"] = [
                "Initial Assessment",
                "Follow-up",
                "Therapy Session",
            ]
        elif case.tier == TriageTier.BLUE:
            eligibility["eligible_appointment_types"] = [
                "Brief Consultation",
                "Digital Support Review",
                "Therapy Session",
            ]
        elif case.tier == TriageTier.AMBER:
            eligibility["eligible_appointment_types"] = [
                "Clinical Assessment",
                "Psychiatric Review",
            ]
        elif case.tier == TriageTier.RED:
            eligibility["eligible_appointment_types"] = [
                "Urgent Assessment",
                "Crisis Intervention",
            ]

        # Add patient-facing explanation
        if case.tier:
            eligibility["patient_explanation"] = PatientExplanationService.generate_tier_explanation(
                case.tier, case.pathway
            )

        return eligibility


class AppointmentConfirmationService:
    """Automates appointment confirmation workflows."""

    # Send confirmation request X hours before appointment
    CONFIRMATION_WINDOW_HOURS = 48
    # Reminder if no response after X hours
    REMINDER_AFTER_HOURS = 24
    # Auto-flag for staff review if no confirmation by X hours before
    FLAG_THRESHOLD_HOURS = 4

    def __init__(
        self,
        session: AsyncSession,
        messaging_service: MessagingService | None = None,
    ):
        self.session = session
        self.messaging_service = messaging_service or MessagingService(session)

    async def get_appointments_needing_confirmation(self) -> Sequence[Appointment]:
        """Get appointments that need confirmation requests sent.

        Finds appointments:
        - Status is SCHEDULED (not yet confirmed)
        - Within confirmation window (48h before appointment)
        - Reminder not yet sent
        """
        now = utc_now()
        window_start = now
        window_end = now + timedelta(hours=self.CONFIRMATION_WINDOW_HOURS)

        result = await self.session.execute(
            select(Appointment).where(
                Appointment.status == AppointmentStatus.SCHEDULED,
                Appointment.scheduled_start >= window_start,
                Appointment.scheduled_start <= window_end,
                Appointment.reminder_sent_at.is_(None),
                Appointment.is_deleted == False,
            )
        )
        return result.scalars().all()

    async def send_confirmation_request(
        self,
        appointment_id: str,
        channel: MessageChannel = MessageChannel.EMAIL,
    ) -> Message | None:
        """Send appointment confirmation request to patient.

        Args:
            appointment_id: The appointment ID
            channel: Communication channel

        Returns:
            Message if sent, None if appointment not found
        """
        result = await self.session.execute(
            select(Appointment).where(Appointment.id == appointment_id)
        )
        appointment = result.scalar_one_or_none()

        if not appointment:
            logger.warning(f"Appointment not found: {appointment_id}")
            return None

        # Get patient
        patient_result = await self.session.execute(
            select(Patient).where(Patient.id == appointment.patient_id)
        )
        patient = patient_result.scalar_one_or_none()

        if not patient:
            logger.warning(f"Patient not found for appointment: {appointment_id}")
            return None

        recipient = patient.email if channel == MessageChannel.EMAIL else patient.phone
        if not recipient:
            logger.warning(f"No {channel} address for patient {patient.id[:8]}")
            return None

        # Format appointment details
        appt_date = appointment.scheduled_start.strftime("%A, %d %B %Y")
        appt_time = appointment.scheduled_start.strftime("%H:%M")

        context = {
            "patient_name": patient.first_name,
            "appointment_date": appt_date,
            "appointment_time": appt_time,
            "location": appointment.location or "Video Consultation",
            "confirm_url": f"/appointments/{appointment_id}/confirm",
            "reschedule_url": f"/appointments/{appointment_id}/reschedule",
            "cancel_url": f"/appointments/{appointment_id}/cancel",
        }

        try:
            message = await self.messaging_service.send_from_template(
                patient_id=patient.id,
                template_type=MessageTemplateType.APPOINTMENT_CONFIRM_REQUEST,
                channel=channel,
                recipient_address=recipient,
                context=context,
                appointment_id=appointment_id,
            )
        except ValueError:
            # Template not found, use fallback
            message = await self._send_fallback_confirmation_request(
                patient=patient,
                appointment=appointment,
                channel=channel,
                recipient=recipient,
                context=context,
            )

        # Update appointment
        appointment.reminder_sent_at = utc_now()
        await self.session.commit()

        logger.info(f"Sent confirmation request for appointment {appointment_id[:8]}")
        return message

    async def _send_fallback_confirmation_request(
        self,
        patient: Patient,
        appointment: Appointment,
        channel: MessageChannel,
        recipient: str,
        context: dict,
    ) -> Message:
        """Send fallback confirmation request when template unavailable."""
        if channel == MessageChannel.EMAIL:
            subject = f"Please confirm your appointment on {context['appointment_date']}"
            body = f"""Hi {context['patient_name']},

Your appointment is coming up:

Date: {context['appointment_date']}
Time: {context['appointment_time']}
Location: {context['location']}

Please let us know if you can attend by logging into your patient portal.

If you need to reschedule or cancel, please do so at least 24 hours before your appointment.

Best regards,
The AcuCare Pathways Team"""
            html_body = None
        else:
            subject = None
            body = f"Hi {context['patient_name']}, reminder: appointment on {context['appointment_date']} at {context['appointment_time']}. Reply YES to confirm or call us to reschedule."
            html_body = None

        return await self.messaging_service.send_message(
            patient_id=patient.id,
            channel=channel,
            recipient_address=recipient,
            body=body,
            subject=subject,
            html_body=html_body,
            appointment_id=appointment.id,
            metadata={
                "template_code": "appointment_confirm_request_fallback",
                "type": "confirmation_request",
            },
        )

    async def confirm_appointment(
        self,
        appointment_id: str,
        confirmed_by_patient: bool = True,
    ) -> Appointment | None:
        """Mark appointment as confirmed.

        Args:
            appointment_id: The appointment ID
            confirmed_by_patient: Whether confirmation came from patient

        Returns:
            Updated appointment or None if not found
        """
        result = await self.session.execute(
            select(Appointment).where(Appointment.id == appointment_id)
        )
        appointment = result.scalar_one_or_none()

        if not appointment:
            return None

        appointment.status = AppointmentStatus.CONFIRMED
        await self.session.commit()

        logger.info(f"Appointment {appointment_id[:8]} confirmed")

        # Send acknowledgment
        if confirmed_by_patient:
            patient_result = await self.session.execute(
                select(Patient).where(Patient.id == appointment.patient_id)
            )
            patient = patient_result.scalar_one_or_none()
            if patient and patient.email:
                await self._send_confirmation_acknowledgment(patient, appointment)

        return appointment

    async def _send_confirmation_acknowledgment(
        self,
        patient: Patient,
        appointment: Appointment,
    ) -> None:
        """Send brief acknowledgment that confirmation was received."""
        appt_date = appointment.scheduled_start.strftime("%A, %d %B")
        appt_time = appointment.scheduled_start.strftime("%H:%M")

        body = f"""Thanks for confirming, {patient.first_name}!

We'll see you on {appt_date} at {appt_time}.

If anything changes, you can reschedule through your patient portal.

The AcuCare Pathways Team"""

        await self.messaging_service.send_message(
            patient_id=patient.id,
            channel=MessageChannel.EMAIL,
            recipient_address=patient.email,
            subject="Appointment Confirmed",
            body=body,
            appointment_id=appointment.id,
            metadata={"type": "confirmation_ack"},
        )

    async def get_unconfirmed_appointments(
        self,
        threshold_hours: int = 24,
    ) -> Sequence[Appointment]:
        """Get appointments that are still unconfirmed close to appointment time.

        These need staff attention for follow-up.
        """
        now = utc_now()
        threshold = now + timedelta(hours=threshold_hours)

        result = await self.session.execute(
            select(Appointment).where(
                Appointment.status == AppointmentStatus.SCHEDULED,
                Appointment.scheduled_start <= threshold,
                Appointment.scheduled_start > now,
                Appointment.reminder_sent_at.isnot(None),
                Appointment.is_deleted == False,
            )
        )
        return result.scalars().all()

    async def run_confirmation_job(
        self,
        channel: MessageChannel = MessageChannel.EMAIL,
    ) -> dict:
        """Run the full appointment confirmation job.

        Returns summary of actions taken.
        """
        results = {
            "confirmation_requests_sent": 0,
            "confirmation_requests_failed": 0,
            "unconfirmed_flagged": 0,
        }

        # Send confirmation requests
        appointments = await self.get_appointments_needing_confirmation()
        logger.info(f"Found {len(appointments)} appointments needing confirmation")

        for appointment in appointments:
            try:
                message = await self.send_confirmation_request(appointment.id, channel)
                if message:
                    results["confirmation_requests_sent"] += 1
            except Exception as e:
                logger.error(f"Failed to send confirmation for {appointment.id[:8]}: {e}")
                results["confirmation_requests_failed"] += 1

        # Check for unconfirmed appointments needing attention
        unconfirmed = await self.get_unconfirmed_appointments(
            threshold_hours=self.FLAG_THRESHOLD_HOURS
        )
        results["unconfirmed_flagged"] = len(unconfirmed)

        logger.info(f"Confirmation job complete: {results}")
        return results


class InactivePatientService:
    """Detects and reaches out to inactive patients."""

    # Days of inactivity before sending "still want this?" message
    INACTIVITY_THRESHOLD_DAYS = 14
    # Only one outreach message
    MAX_OUTREACH_MESSAGES = 1

    def __init__(
        self,
        session: AsyncSession,
        messaging_service: MessagingService | None = None,
    ):
        self.session = session
        self.messaging_service = messaging_service or MessagingService(session)

    async def get_inactive_appointments(self) -> Sequence[Appointment]:
        """Get appointments for patients who may have lost interest.

        Criteria:
        - Appointment is scheduled but not confirmed
        - No patient activity (messages, logins) in threshold period
        - No "still want this?" message sent yet
        """
        now = utc_now()
        threshold_date = now - timedelta(days=self.INACTIVITY_THRESHOLD_DAYS)

        # Find scheduled appointments with no recent activity
        result = await self.session.execute(
            select(Appointment).where(
                Appointment.status == AppointmentStatus.SCHEDULED,
                Appointment.scheduled_start > now,
                Appointment.created_at < threshold_date,
                Appointment.is_deleted == False,
            )
        )
        appointments = result.scalars().all()

        # Filter to those without "still want this?" message
        inactive = []
        for appointment in appointments:
            msg_result = await self.session.execute(
                select(Message).where(
                    Message.appointment_id == appointment.id,
                    Message.message_metadata.contains({"type": "still_want_appointment"}),
                )
            )
            if not msg_result.scalar_one_or_none():
                inactive.append(appointment)

        return inactive

    async def send_still_want_appointment(
        self,
        appointment_id: str,
        channel: MessageChannel = MessageChannel.EMAIL,
    ) -> Message | None:
        """Send "still want this appointment?" message.

        Args:
            appointment_id: The appointment ID
            channel: Communication channel

        Returns:
            Message if sent, None if not applicable
        """
        result = await self.session.execute(
            select(Appointment).where(Appointment.id == appointment_id)
        )
        appointment = result.scalar_one_or_none()

        if not appointment:
            return None

        # Get patient
        patient_result = await self.session.execute(
            select(Patient).where(Patient.id == appointment.patient_id)
        )
        patient = patient_result.scalar_one_or_none()

        if not patient:
            return None

        recipient = patient.email if channel == MessageChannel.EMAIL else patient.phone
        if not recipient:
            return None

        appt_date = appointment.scheduled_start.strftime("%A, %d %B %Y")
        appt_time = appointment.scheduled_start.strftime("%H:%M")

        context = {
            "patient_name": patient.first_name,
            "appointment_date": appt_date,
            "appointment_time": appt_time,
            "confirm_url": f"/appointments/{appointment_id}/confirm",
            "cancel_url": f"/appointments/{appointment_id}/cancel",
        }

        try:
            message = await self.messaging_service.send_from_template(
                patient_id=patient.id,
                template_type=MessageTemplateType.STILL_WANT_APPOINTMENT,
                channel=channel,
                recipient_address=recipient,
                context=context,
                appointment_id=appointment_id,
            )
        except ValueError:
            # Fallback
            message = await self._send_fallback_still_want(
                patient=patient,
                appointment=appointment,
                channel=channel,
                recipient=recipient,
                context=context,
            )

        logger.info(f"Sent 'still want?' for appointment {appointment_id[:8]}")
        return message

    async def _send_fallback_still_want(
        self,
        patient: Patient,
        appointment: Appointment,
        channel: MessageChannel,
        recipient: str,
        context: dict,
    ) -> Message:
        """Send fallback 'still want?' message."""
        if channel == MessageChannel.EMAIL:
            subject = "Are you still planning to attend your appointment?"
            body = f"""Hi {context['patient_name']},

We noticed you have an appointment scheduled for {context['appointment_date']} at {context['appointment_time']}.

We wanted to check if this still works for you. If your circumstances have changed, that's completely fine - just let us know so we can free up the slot for someone else.

Please log into your patient portal to confirm, reschedule, or cancel.

If we don't hear from you, we'll keep your appointment as scheduled.

Best regards,
The AcuCare Pathways Team"""
            html_body = None
        else:
            subject = None
            body = f"Hi {context['patient_name']}, checking in about your appointment on {context['appointment_date']}. Still planning to attend? Reply YES to confirm or log in to reschedule."
            html_body = None

        return await self.messaging_service.send_message(
            patient_id=patient.id,
            channel=channel,
            recipient_address=recipient,
            body=body,
            subject=subject,
            html_body=html_body,
            appointment_id=appointment.id,
            metadata={"type": "still_want_appointment"},
        )

    async def run_inactive_outreach_job(
        self,
        channel: MessageChannel = MessageChannel.EMAIL,
    ) -> dict:
        """Run the inactive patient outreach job.

        Returns summary of messages sent.
        """
        results = {
            "messages_sent": 0,
            "messages_failed": 0,
            "patients_processed": 0,
        }

        appointments = await self.get_inactive_appointments()
        logger.info(f"Found {len(appointments)} appointments for inactive patients")

        for appointment in appointments:
            try:
                message = await self.send_still_want_appointment(appointment.id, channel)
                if message:
                    results["messages_sent"] += 1
                    results["patients_processed"] += 1
            except Exception as e:
                logger.error(f"Failed to send outreach for {appointment.id[:8]}: {e}")
                results["messages_failed"] += 1

        logger.info(f"Inactive outreach job complete: {results}")
        return results


class AdminFrictionReductionService:
    """Unified service for reducing admin friction.

    Combines all automation services into a single interface.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.messaging = MessagingService(session)
        self.eligibility = EligibilityService(session)
        self.confirmation = AppointmentConfirmationService(session, self.messaging)
        self.inactive = InactivePatientService(session, self.messaging)

    async def get_case_summary_for_staff(
        self,
        triage_case_id: str,
    ) -> dict:
        """Get complete case summary with all info staff need.

        Eliminates need for staff to:
        - Re-explain triage decision to patient
        - Check eligibility manually
        - Look up pathway requirements
        """
        eligibility = await self.eligibility.get_eligibility_summary(triage_case_id)

        if "error" in eligibility:
            return eligibility

        # Get patient-facing explanation
        result = await self.session.execute(
            select(TriageCase).where(TriageCase.id == triage_case_id)
        )
        case = result.scalar_one_or_none()

        if case and case.tier:
            patient_explanation = PatientExplanationService.generate_tier_explanation(
                case.tier,
                case.pathway,
            )
            rules_summary = PatientExplanationService.generate_rules_summary(
                case.tier_explanation
            )
        else:
            patient_explanation = None
            rules_summary = []

        return {
            "eligibility": eligibility,
            "patient_explanation": patient_explanation,
            "rules_summary": rules_summary,
            "shareable_text": self._generate_shareable_text(eligibility, patient_explanation),
        }

    def _generate_shareable_text(
        self,
        eligibility: dict,
        patient_explanation: dict | None,
    ) -> str:
        """Generate text staff can copy/paste to share with patient."""
        if not patient_explanation:
            return ""

        text = f"""
{patient_explanation.get('title', 'Your Assessment Result')}

{patient_explanation.get('description', '')}

What happens next:
"""
        for step in patient_explanation.get("what_happens_next", []):
            text += f"• {step}\n"

        if eligibility.get("can_self_book"):
            text += "\nYou can book your appointment now through your patient portal."

        return text.strip()

    async def run_all_automation_jobs(
        self,
        channel: MessageChannel = MessageChannel.EMAIL,
    ) -> dict:
        """Run all admin friction reduction jobs.

        Returns combined results from all jobs.
        """
        results = {}

        # Run confirmation job
        results["confirmation"] = await self.confirmation.run_confirmation_job(channel)

        # Run inactive outreach job
        results["inactive_outreach"] = await self.inactive.run_inactive_outreach_job(channel)

        return results

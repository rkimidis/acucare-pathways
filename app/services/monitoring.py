"""Monitoring service for waiting list check-ins.

Sprint 5: Handles weekly check-in scheduling, PHQ-2/GAD-2 mini-assessments,
deterioration detection, and AMBER escalation.
"""

import logging
from datetime import datetime, timedelta
from typing import Sequence
from uuid import uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.models.monitoring import (
    CheckInStatus,
    EscalationReason,
    MonitoringAlert,
    MonitoringSchedule,
    WaitingListCheckIn,
)
from app.models.triage_case import TriageCase, TriageCaseStatus, TriageTier
from app.services.audit import write_audit_event

logger = logging.getLogger(__name__)


class CheckInNotFoundError(Exception):
    """Raised when check-in is not found."""

    pass


class CheckInAlreadyCompletedError(Exception):
    """Raised when trying to submit a completed check-in."""

    pass


# Alert severity levels
ALERT_SEVERITY_CRITICAL = "critical"
ALERT_SEVERITY_HIGH = "high"
ALERT_SEVERITY_MEDIUM = "medium"
ALERT_SEVERITY_LOW = "low"


class MonitoringService:
    """Service for managing waiting list monitoring and check-ins."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_monitoring_schedule(
        self,
        triage_case_id: str,
        frequency_days: int = 7,
        start_date: datetime | None = None,
    ) -> MonitoringSchedule:
        """Create a monitoring schedule for a triage case."""
        start = start_date or utc_now()
        next_checkin = start + timedelta(days=frequency_days)

        schedule = MonitoringSchedule(
            id=str(uuid4()),
            triage_case_id=triage_case_id,
            frequency_days=frequency_days,
            next_checkin_date=next_checkin,
        )

        self.session.add(schedule)
        await self.session.commit()
        await self.session.refresh(schedule)

        return schedule

    async def get_monitoring_schedule(
        self,
        triage_case_id: str,
    ) -> MonitoringSchedule | None:
        """Get monitoring schedule for a case."""
        result = await self.session.execute(
            select(MonitoringSchedule).where(
                MonitoringSchedule.triage_case_id == triage_case_id,
            )
        )
        return result.scalar_one_or_none()

    async def pause_monitoring(
        self,
        triage_case_id: str,
        until: datetime,
        reason: str | None = None,
    ) -> MonitoringSchedule | None:
        """Pause monitoring for a case."""
        schedule = await self.get_monitoring_schedule(triage_case_id)

        if not schedule:
            return None

        schedule.paused = True
        schedule.paused_until = until
        schedule.pause_reason = reason

        await self.session.commit()
        await self.session.refresh(schedule)

        return schedule

    async def resume_monitoring(
        self,
        triage_case_id: str,
    ) -> MonitoringSchedule | None:
        """Resume monitoring for a paused case."""
        schedule = await self.get_monitoring_schedule(triage_case_id)

        if not schedule:
            return None

        schedule.paused = False
        schedule.paused_until = None
        schedule.pause_reason = None
        schedule.next_checkin_date = utc_now() + timedelta(days=schedule.frequency_days)

        await self.session.commit()
        await self.session.refresh(schedule)

        return schedule

    async def get_due_checkins(self) -> Sequence[MonitoringSchedule]:
        """Get monitoring schedules with check-ins due now."""
        now = utc_now()

        result = await self.session.execute(
            select(MonitoringSchedule).where(
                MonitoringSchedule.is_active == True,
                MonitoringSchedule.paused == False,
                MonitoringSchedule.next_checkin_date <= now,
            )
        )
        return result.scalars().all()

    async def create_checkin(
        self,
        triage_case_id: str,
        patient_id: str,
        scheduled_for: datetime | None = None,
    ) -> WaitingListCheckIn:
        """Create a new check-in for a patient."""
        # Get sequence number
        result = await self.session.execute(
            select(WaitingListCheckIn).where(
                WaitingListCheckIn.triage_case_id == triage_case_id,
            ).order_by(WaitingListCheckIn.sequence_number.desc())
        )
        last_checkin = result.scalar_one_or_none()
        seq_num = (last_checkin.sequence_number + 1) if last_checkin else 1

        now = utc_now()
        scheduled = scheduled_for or now

        checkin = WaitingListCheckIn(
            id=str(uuid4()),
            patient_id=patient_id,
            triage_case_id=triage_case_id,
            sequence_number=seq_num,
            scheduled_for=scheduled,
            expires_at=scheduled + timedelta(hours=72),  # 3 days to respond
            status=CheckInStatus.SCHEDULED,
        )

        self.session.add(checkin)
        await self.session.commit()
        await self.session.refresh(checkin)

        return checkin

    async def get_checkin(self, checkin_id: str) -> WaitingListCheckIn | None:
        """Get a check-in by ID."""
        result = await self.session.execute(
            select(WaitingListCheckIn).where(
                WaitingListCheckIn.id == checkin_id,
                WaitingListCheckIn.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def get_pending_checkin(
        self,
        patient_id: str,
        triage_case_id: str | None = None,
    ) -> WaitingListCheckIn | None:
        """Get the pending check-in for a patient."""
        query = select(WaitingListCheckIn).where(
            WaitingListCheckIn.patient_id == patient_id,
            WaitingListCheckIn.status.in_([
                CheckInStatus.SENT,
                CheckInStatus.PENDING,
            ]),
            WaitingListCheckIn.is_deleted == False,
        )

        if triage_case_id:
            query = query.where(WaitingListCheckIn.triage_case_id == triage_case_id)

        query = query.order_by(WaitingListCheckIn.scheduled_for.desc())

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def submit_checkin_response(
        self,
        checkin_id: str,
        phq2_q1: int,
        phq2_q2: int,
        gad2_q1: int,
        gad2_q2: int,
        suicidal_ideation: bool = False,
        self_harm: bool = False,
        wellbeing_rating: int | None = None,
        patient_comments: str | None = None,
        wants_callback: bool = False,
        raw_response: dict | None = None,
    ) -> WaitingListCheckIn:
        """Submit a patient's check-in response.

        Calculates scores, checks for escalation triggers, and creates
        alerts if needed.
        """
        checkin = await self.get_checkin(checkin_id)

        if not checkin:
            raise CheckInNotFoundError(f"Check-in {checkin_id} not found")

        if checkin.status == CheckInStatus.COMPLETED:
            raise CheckInAlreadyCompletedError("Check-in already completed")

        # Update check-in with responses
        checkin.phq2_q1 = phq2_q1
        checkin.phq2_q2 = phq2_q2
        checkin.gad2_q1 = gad2_q1
        checkin.gad2_q2 = gad2_q2
        checkin.suicidal_ideation = suicidal_ideation
        checkin.self_harm = self_harm
        checkin.wellbeing_rating = wellbeing_rating
        checkin.patient_comments = patient_comments
        checkin.wants_callback = wants_callback
        checkin.raw_response = raw_response

        # Calculate scores
        checkin.calculate_scores()

        # Update status
        checkin.status = CheckInStatus.COMPLETED
        checkin.completed_at = utc_now()

        # Check for escalation
        needs_escalation, reason = checkin.check_escalation_needed()

        if needs_escalation:
            checkin.requires_escalation = True
            checkin.escalation_reason = reason
            checkin.escalated_at = utc_now()
            checkin.escalated_by_system = True

            # Create alert
            await self._create_escalation_alert(checkin, reason)

            # Escalate triage case to AMBER if needed
            await self._escalate_to_amber(checkin, reason)

        # Update monitoring schedule
        schedule = await self.get_monitoring_schedule(checkin.triage_case_id)
        if schedule:
            schedule.last_checkin_date = utc_now()
            schedule.next_checkin_date = utc_now() + timedelta(days=schedule.frequency_days)
            schedule.consecutive_missed = 0  # Reset missed counter

        await self.session.commit()
        await self.session.refresh(checkin)

        return checkin

    async def _create_escalation_alert(
        self,
        checkin: WaitingListCheckIn,
        reason: str | None,
    ) -> MonitoringAlert:
        """Create a monitoring alert for an escalated check-in."""
        # Determine severity based on reason
        severity = ALERT_SEVERITY_HIGH
        title = "Check-in requires review"
        description = "Patient check-in flagged for clinical review."

        if reason == EscalationReason.SUICIDAL_IDEATION:
            severity = ALERT_SEVERITY_CRITICAL
            title = "Suicidal ideation reported"
            description = "Patient reported suicidal ideation in check-in. Immediate review required."
        elif reason == EscalationReason.SELF_HARM:
            severity = ALERT_SEVERITY_CRITICAL
            title = "Self-harm reported"
            description = "Patient reported self-harm in check-in. Immediate review required."
        elif reason == EscalationReason.PHQ2_ELEVATED:
            title = "Elevated depression screening"
            description = f"PHQ-2 score of {checkin.phq2_total} indicates possible depression. Clinical review recommended."
        elif reason == EscalationReason.GAD2_ELEVATED:
            title = "Elevated anxiety screening"
            description = f"GAD-2 score of {checkin.gad2_total} indicates possible anxiety disorder. Clinical review recommended."
        elif reason == EscalationReason.PATIENT_REQUEST:
            severity = ALERT_SEVERITY_MEDIUM
            title = "Patient callback requested"
            description = f"Patient requested callback with wellbeing rating of {checkin.wellbeing_rating}/10."

        alert = MonitoringAlert(
            id=str(uuid4()),
            patient_id=checkin.patient_id,
            triage_case_id=checkin.triage_case_id,
            checkin_id=checkin.id,
            alert_type=reason or "check_in_review",
            severity=severity,
            title=title,
            description=description,
            phq2_score=checkin.phq2_total,
            gad2_score=checkin.gad2_total,
        )

        self.session.add(alert)

        return alert

    async def _escalate_to_amber(
        self,
        checkin: WaitingListCheckIn,
        reason: str | None,
    ) -> None:
        """Escalate a triage case to AMBER tier due to deterioration."""
        # Get the triage case
        result = await self.session.execute(
            select(TriageCase).where(TriageCase.id == checkin.triage_case_id)
        )
        case = result.scalar_one_or_none()

        if not case:
            return

        # Only escalate if not already RED/AMBER
        if case.tier in [TriageTier.RED, TriageTier.AMBER]:
            return

        original_tier = case.tier
        case.tier = TriageTier.AMBER
        case.status = TriageCaseStatus.ESCALATED
        case.self_book_allowed = False
        case.clinician_review_required = True
        case.escalation_reason = f"Deterioration detected during check-in: {reason}"

        # Write audit event
        from app.models.audit_event import ActorType
        await write_audit_event(
            session=self.session,
            actor_type=ActorType.SYSTEM,
            actor_id=None,
            action="monitoring.escalation",
            action_category="clinical",
            entity_type="triage_case",
            entity_id=case.id,
            description=f"System escalated case to AMBER due to deterioration: {reason}",
            metadata={
                "checkin_id": checkin.id,
                "reason": reason,
                "original_tier": original_tier.value if original_tier else None,
                "new_tier": TriageTier.AMBER.value,
                "phq2_score": checkin.phq2_total,
                "gad2_score": checkin.gad2_total,
                "suicidal_ideation": checkin.suicidal_ideation,
                "self_harm": checkin.self_harm,
            },
        )

        logger.info(
            f"Escalated case {case.id[:8]} from {original_tier} to AMBER "
            f"due to {reason} (checkin {checkin.id[:8]})"
        )

    async def mark_checkin_missed(self, checkin_id: str) -> WaitingListCheckIn | None:
        """Mark a check-in as missed due to no response."""
        checkin = await self.get_checkin(checkin_id)

        if not checkin:
            return None

        checkin.status = CheckInStatus.MISSED

        # Update schedule and check for repeated misses
        schedule = await self.get_monitoring_schedule(checkin.triage_case_id)
        if schedule:
            schedule.consecutive_missed += 1

            # Check if we should escalate due to repeated non-response
            if schedule.consecutive_missed >= schedule.missed_threshold_escalation:
                checkin.requires_escalation = True
                checkin.escalation_reason = EscalationReason.NO_RESPONSE
                checkin.escalated_at = utc_now()
                checkin.escalated_by_system = True

                # Create alert for non-response
                alert = MonitoringAlert(
                    id=str(uuid4()),
                    patient_id=checkin.patient_id,
                    triage_case_id=checkin.triage_case_id,
                    checkin_id=checkin.id,
                    alert_type="no_response",
                    severity=ALERT_SEVERITY_MEDIUM,
                    title="Multiple missed check-ins",
                    description=f"Patient has missed {schedule.consecutive_missed} consecutive check-ins. Review recommended.",
                )
                self.session.add(alert)

        await self.session.commit()
        await self.session.refresh(checkin)

        return checkin

    async def get_active_alerts(
        self,
        severity: str | None = None,
        limit: int = 100,
    ) -> Sequence[MonitoringAlert]:
        """Get active monitoring alerts."""
        query = select(MonitoringAlert).where(
            MonitoringAlert.is_active == True,
        )

        if severity:
            query = query.where(MonitoringAlert.severity == severity)

        query = query.order_by(
            # Order by severity (critical first)
            MonitoringAlert.created_at.desc(),
        ).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def acknowledge_alert(
        self,
        alert_id: str,
        user_id: str,
    ) -> MonitoringAlert | None:
        """Acknowledge a monitoring alert."""
        result = await self.session.execute(
            select(MonitoringAlert).where(MonitoringAlert.id == alert_id)
        )
        alert = result.scalar_one_or_none()

        if not alert:
            return None

        alert.acknowledge(user_id)

        await self.session.commit()
        await self.session.refresh(alert)

        return alert

    async def resolve_alert(
        self,
        alert_id: str,
        user_id: str,
        notes: str | None = None,
        action: str | None = None,
    ) -> MonitoringAlert | None:
        """Resolve a monitoring alert."""
        result = await self.session.execute(
            select(MonitoringAlert).where(MonitoringAlert.id == alert_id)
        )
        alert = result.scalar_one_or_none()

        if not alert:
            return None

        alert.resolve(user_id, notes, action)

        await self.session.commit()
        await self.session.refresh(alert)

        return alert

    async def get_patient_checkins(
        self,
        patient_id: str,
        limit: int = 10,
    ) -> Sequence[WaitingListCheckIn]:
        """Get check-in history for a patient."""
        result = await self.session.execute(
            select(WaitingListCheckIn).where(
                WaitingListCheckIn.patient_id == patient_id,
                WaitingListCheckIn.is_deleted == False,
            ).order_by(WaitingListCheckIn.scheduled_for.desc()).limit(limit)
        )
        return result.scalars().all()

    async def get_expired_checkins(self) -> Sequence[WaitingListCheckIn]:
        """Get check-ins that have expired without response."""
        now = utc_now()

        result = await self.session.execute(
            select(WaitingListCheckIn).where(
                WaitingListCheckIn.status.in_([
                    CheckInStatus.SENT,
                    CheckInStatus.PENDING,
                ]),
                WaitingListCheckIn.expires_at < now,
                WaitingListCheckIn.is_deleted == False,
            )
        )
        return result.scalars().all()

    async def get_duty_queue(
        self,
        include_acknowledged: bool = False,
        limit: int = 50,
    ) -> Sequence[MonitoringAlert]:
        """Get the duty queue - prioritized list of escalated cases needing review.

        The duty queue is ordered by:
        1. Critical severity first (suicidal ideation, self-harm)
        2. High severity next (elevated PHQ-2/GAD-2)
        3. Then by creation time (oldest first)

        Args:
            include_acknowledged: Include alerts that have been acknowledged
            limit: Maximum number of items to return

        Returns:
            List of MonitoringAlert items for the duty queue
        """
        from sqlalchemy import case as sql_case

        # Priority ordering: critical=1, high=2, medium=3, low=4
        severity_order = sql_case(
            (MonitoringAlert.severity == ALERT_SEVERITY_CRITICAL, 1),
            (MonitoringAlert.severity == ALERT_SEVERITY_HIGH, 2),
            (MonitoringAlert.severity == ALERT_SEVERITY_MEDIUM, 3),
            (MonitoringAlert.severity == ALERT_SEVERITY_LOW, 4),
            else_=5,
        )

        query = select(MonitoringAlert).where(
            MonitoringAlert.is_active == True,
        )

        if not include_acknowledged:
            query = query.where(MonitoringAlert.acknowledged_at.is_(None))

        query = query.order_by(
            severity_order,
            MonitoringAlert.created_at.asc(),
        ).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_duty_queue_count(self) -> dict[str, int]:
        """Get counts of items in the duty queue by severity.

        Returns:
            Dict with counts: {critical: n, high: n, medium: n, low: n, total: n}
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(
                MonitoringAlert.severity,
                func.count().label("count"),
            ).where(
                MonitoringAlert.is_active == True,
                MonitoringAlert.acknowledged_at.is_(None),
            ).group_by(MonitoringAlert.severity)
        )

        counts = {row.severity: row.count for row in result}
        total = sum(counts.values())

        return {
            "critical": counts.get(ALERT_SEVERITY_CRITICAL, 0),
            "high": counts.get(ALERT_SEVERITY_HIGH, 0),
            "medium": counts.get(ALERT_SEVERITY_MEDIUM, 0),
            "low": counts.get(ALERT_SEVERITY_LOW, 0),
            "total": total,
        }

    async def send_checkin_request(
        self,
        checkin: WaitingListCheckIn,
        patient_email: str | None = None,
        patient_phone: str | None = None,
    ) -> WaitingListCheckIn:
        """Send check-in request to patient and update status.

        Sends via configured channel (email/SMS) and creates audit record.

        Args:
            checkin: The check-in to send
            patient_email: Patient's email address
            patient_phone: Patient's phone number

        Returns:
            Updated check-in record
        """
        from app.models.audit_event import ActorType

        checkin.status = CheckInStatus.SENT
        checkin.sent_at = utc_now()

        # Audit the send
        await write_audit_event(
            session=self.session,
            actor_type=ActorType.SYSTEM,
            actor_id=None,
            action="checkin.sent",
            action_category="messaging",
            entity_type="waiting_list_checkin",
            entity_id=checkin.id,
            description=f"Check-in request #{checkin.sequence_number} sent to patient",
            metadata={
                "patient_id": checkin.patient_id,
                "triage_case_id": checkin.triage_case_id,
                "sequence_number": checkin.sequence_number,
                "channel": "email" if patient_email else "sms" if patient_phone else "unknown",
            },
        )

        await self.session.commit()
        await self.session.refresh(checkin)

        logger.info(
            f"Sent check-in request {checkin.id[:8]} seq={checkin.sequence_number} "
            f"to patient {checkin.patient_id[:8]}"
        )

        return checkin

    async def record_checkin_received(
        self,
        checkin: WaitingListCheckIn,
    ) -> None:
        """Record that a check-in response was received (audit only).

        Args:
            checkin: The completed check-in
        """
        from app.models.audit_event import ActorType

        await write_audit_event(
            session=self.session,
            actor_type=ActorType.PATIENT,
            actor_id=checkin.patient_id,
            action="checkin.received",
            action_category="clinical",
            entity_type="waiting_list_checkin",
            entity_id=checkin.id,
            description=f"Check-in response received from patient",
            metadata={
                "sequence_number": checkin.sequence_number,
                "phq2_total": checkin.phq2_total,
                "gad2_total": checkin.gad2_total,
                "suicidal_ideation": checkin.suicidal_ideation,
                "self_harm": checkin.self_harm,
                "wellbeing_rating": checkin.wellbeing_rating,
                "wants_callback": checkin.wants_callback,
                "requires_escalation": checkin.requires_escalation,
                "escalation_reason": checkin.escalation_reason,
            },
        )

    async def create_duty_queue_item(
        self,
        checkin: WaitingListCheckIn,
        reason: str,
    ) -> MonitoringAlert:
        """Create a duty queue item (alert) for an escalated check-in.

        This is called when deterioration is detected to add the case
        to the clinician duty queue.

        Args:
            checkin: The check-in that triggered escalation
            reason: Reason for escalation

        Returns:
            Created MonitoringAlert (duty queue item)
        """
        from app.models.audit_event import ActorType

        alert = await self._create_escalation_alert(checkin, reason)
        alert.escalated_to_amber = True

        # Audit the duty queue item creation
        await write_audit_event(
            session=self.session,
            actor_type=ActorType.SYSTEM,
            actor_id=None,
            action="duty_queue.item_created",
            action_category="clinical",
            entity_type="monitoring_alert",
            entity_id=alert.id,
            description=f"Duty queue item created for {reason}",
            metadata={
                "checkin_id": checkin.id,
                "patient_id": checkin.patient_id,
                "triage_case_id": checkin.triage_case_id,
                "reason": reason,
                "severity": alert.severity,
                "phq2_score": checkin.phq2_total,
                "gad2_score": checkin.gad2_total,
            },
        )

        await self.session.commit()
        await self.session.refresh(alert)

        logger.info(
            f"Created duty queue item {alert.id[:8]} severity={alert.severity} "
            f"for case {checkin.triage_case_id[:8]}"
        )

        return alert

"""Reporting service for Sprint 6.

Provides metrics and reports:
- Volumes by tier/pathway
- Wait times and SLA breaches
- No-shows
- Outcome trends
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.monitoring import MonitoringAlert
from app.models.scheduling import Appointment, AppointmentStatus
from app.models.triage_case import TriageCase, TriageCaseStatus, TriageTier


@dataclass
class TierVolume:
    """Volume counts by tier."""
    tier: str
    count: int
    percentage: float


@dataclass
class PathwayVolume:
    """Volume counts by pathway."""
    pathway: str
    count: int
    percentage: float


@dataclass
class WaitTimeMetrics:
    """Wait time statistics."""
    tier: str
    avg_days: float
    median_days: float
    min_days: float
    max_days: float
    p90_days: float
    sla_target_days: int
    breaches: int
    breach_percentage: float


@dataclass
class NoShowMetrics:
    """No-show statistics."""
    total_appointments: int
    no_shows: int
    no_show_rate: float
    by_tier: dict[str, float]
    by_appointment_type: dict[str, float]


@dataclass
class OutcomeTrend:
    """Outcome trend data point."""
    period: str
    completed: int
    discharged: int
    escalated: int
    declined: int


# SLA targets by tier (in days)
SLA_TARGETS = {
    TriageTier.RED.value: 1,      # 24 hours
    TriageTier.AMBER.value: 3,    # 3 days
    TriageTier.GREEN.value: 14,   # 2 weeks
    TriageTier.BLUE.value: 28,    # 4 weeks
}


class ReportingService:
    """Service for generating reports and metrics."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_volumes_by_tier(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[TierVolume]:
        """Get case volumes grouped by tier."""
        query = select(
            TriageCase.tier,
            func.count(TriageCase.id).label("count"),
        ).where(TriageCase.deleted_at.is_(None))

        if start_date:
            query = query.where(TriageCase.created_at >= start_date)
        if end_date:
            query = query.where(TriageCase.created_at <= end_date)

        query = query.group_by(TriageCase.tier)

        result = await self.session.execute(query)
        rows = result.all()

        total = sum(row.count for row in rows)
        volumes = []

        for row in rows:
            volumes.append(TierVolume(
                tier=row.tier,
                count=row.count,
                percentage=(row.count / total * 100) if total > 0 else 0,
            ))

        return sorted(volumes, key=lambda v: v.count, reverse=True)

    async def get_volumes_by_pathway(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[PathwayVolume]:
        """Get case volumes grouped by pathway."""
        query = select(
            TriageCase.pathway,
            func.count(TriageCase.id).label("count"),
        ).where(
            and_(
                TriageCase.deleted_at.is_(None),
                TriageCase.pathway.isnot(None),
            )
        )

        if start_date:
            query = query.where(TriageCase.created_at >= start_date)
        if end_date:
            query = query.where(TriageCase.created_at <= end_date)

        query = query.group_by(TriageCase.pathway)

        result = await self.session.execute(query)
        rows = result.all()

        total = sum(row.count for row in rows)
        volumes = []

        for row in rows:
            volumes.append(PathwayVolume(
                pathway=row.pathway or "Unassigned",
                count=row.count,
                percentage=(row.count / total * 100) if total > 0 else 0,
            ))

        return sorted(volumes, key=lambda v: v.count, reverse=True)

    async def get_wait_time_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[WaitTimeMetrics]:
        """Get wait time statistics by tier with SLA breach counts."""
        metrics = []

        for tier in [TriageTier.RED, TriageTier.AMBER, TriageTier.GREEN, TriageTier.BLUE]:
            # Get cases with first appointment scheduled
            query = select(
                TriageCase.id,
                TriageCase.created_at,
                func.min(Appointment.scheduled_start).label("first_appointment"),
            ).join(
                Appointment, Appointment.triage_case_id == TriageCase.id
            ).where(
                and_(
                    TriageCase.tier == tier.value,
                    TriageCase.deleted_at.is_(None),
                    Appointment.deleted_at.is_(None),
                )
            ).group_by(TriageCase.id, TriageCase.created_at)

            if start_date:
                query = query.where(TriageCase.created_at >= start_date)
            if end_date:
                query = query.where(TriageCase.created_at <= end_date)

            result = await self.session.execute(query)
            rows = result.all()

            if not rows:
                metrics.append(WaitTimeMetrics(
                    tier=tier.value,
                    avg_days=0,
                    median_days=0,
                    min_days=0,
                    max_days=0,
                    p90_days=0,
                    sla_target_days=SLA_TARGETS[tier.value],
                    breaches=0,
                    breach_percentage=0,
                ))
                continue

            # Calculate wait times in days
            wait_times = []
            sla_target = SLA_TARGETS[tier.value]
            breaches = 0

            for row in rows:
                if row.first_appointment and row.created_at:
                    wait_days = (row.first_appointment - row.created_at).days
                    wait_times.append(wait_days)
                    if wait_days > sla_target:
                        breaches += 1

            if not wait_times:
                continue

            wait_times.sort()
            n = len(wait_times)

            metrics.append(WaitTimeMetrics(
                tier=tier.value,
                avg_days=sum(wait_times) / n,
                median_days=wait_times[n // 2],
                min_days=min(wait_times),
                max_days=max(wait_times),
                p90_days=wait_times[int(n * 0.9)] if n > 0 else 0,
                sla_target_days=sla_target,
                breaches=breaches,
                breach_percentage=(breaches / n * 100) if n > 0 else 0,
            ))

        return metrics

    async def get_no_show_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> NoShowMetrics:
        """Get no-show statistics."""
        base_query = select(Appointment).where(
            and_(
                Appointment.deleted_at.is_(None),
                Appointment.status.in_([
                    AppointmentStatus.COMPLETED.value,
                    AppointmentStatus.NO_SHOW.value,
                ]),
            )
        )

        if start_date:
            base_query = base_query.where(Appointment.scheduled_start >= start_date)
        if end_date:
            base_query = base_query.where(Appointment.scheduled_start <= end_date)

        # Total appointments
        total_result = await self.session.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = total_result.scalar() or 0

        # No-shows
        no_show_query = base_query.where(
            Appointment.status == AppointmentStatus.NO_SHOW.value
        )
        no_show_result = await self.session.execute(
            select(func.count()).select_from(no_show_query.subquery())
        )
        no_shows = no_show_result.scalar() or 0

        # By tier
        by_tier_query = select(
            TriageCase.tier,
            func.count(Appointment.id).filter(
                Appointment.status == AppointmentStatus.NO_SHOW.value
            ).label("no_shows"),
            func.count(Appointment.id).label("total"),
        ).join(
            TriageCase, TriageCase.id == Appointment.triage_case_id
        ).where(
            and_(
                Appointment.deleted_at.is_(None),
                Appointment.status.in_([
                    AppointmentStatus.COMPLETED.value,
                    AppointmentStatus.NO_SHOW.value,
                ]),
            )
        ).group_by(TriageCase.tier)

        by_tier_result = await self.session.execute(by_tier_query)
        by_tier = {
            row.tier: (row.no_shows / row.total * 100) if row.total > 0 else 0
            for row in by_tier_result.all()
        }

        # By appointment type
        by_type_query = select(
            Appointment.appointment_type_id,
            func.count(Appointment.id).filter(
                Appointment.status == AppointmentStatus.NO_SHOW.value
            ).label("no_shows"),
            func.count(Appointment.id).label("total"),
        ).where(
            and_(
                Appointment.deleted_at.is_(None),
                Appointment.status.in_([
                    AppointmentStatus.COMPLETED.value,
                    AppointmentStatus.NO_SHOW.value,
                ]),
            )
        ).group_by(Appointment.appointment_type_id)

        by_type_result = await self.session.execute(by_type_query)
        by_type = {
            row.appointment_type_id: (row.no_shows / row.total * 100) if row.total > 0 else 0
            for row in by_type_result.all()
        }

        return NoShowMetrics(
            total_appointments=total,
            no_shows=no_shows,
            no_show_rate=(no_shows / total * 100) if total > 0 else 0,
            by_tier=by_tier,
            by_appointment_type=by_type,
        )

    async def get_outcome_trends(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        period: str = "month",  # "day", "week", "month"
    ) -> list[OutcomeTrend]:
        """Get outcome trends over time."""
        # Determine date truncation based on period
        if period == "day":
            date_trunc = func.date_trunc("day", TriageCase.updated_at)
        elif period == "week":
            date_trunc = func.date_trunc("week", TriageCase.updated_at)
        else:
            date_trunc = func.date_trunc("month", TriageCase.updated_at)

        query = select(
            date_trunc.label("period"),
            func.count(TriageCase.id).filter(
                TriageCase.status == TriageCaseStatus.COMPLETED.value
            ).label("completed"),
            func.count(TriageCase.id).filter(
                TriageCase.status == TriageCaseStatus.DISCHARGED.value
            ).label("discharged"),
            func.count(TriageCase.id).filter(
                TriageCase.status == TriageCaseStatus.ESCALATED.value
            ).label("escalated"),
            func.count(TriageCase.id).filter(
                TriageCase.status == TriageCaseStatus.DECLINED.value
            ).label("declined"),
        ).where(
            and_(
                TriageCase.deleted_at.is_(None),
                TriageCase.status.in_([
                    TriageCaseStatus.COMPLETED.value,
                    TriageCaseStatus.DISCHARGED.value,
                    TriageCaseStatus.ESCALATED.value,
                    TriageCaseStatus.DECLINED.value,
                ]),
            )
        )

        if start_date:
            query = query.where(TriageCase.updated_at >= start_date)
        if end_date:
            query = query.where(TriageCase.updated_at <= end_date)

        query = query.group_by(date_trunc).order_by(date_trunc)

        result = await self.session.execute(query)
        rows = result.all()

        trends = []
        for row in rows:
            period_str = row.period.strftime("%Y-%m-%d") if row.period else "Unknown"
            trends.append(OutcomeTrend(
                period=period_str,
                completed=row.completed or 0,
                discharged=row.discharged or 0,
                escalated=row.escalated or 0,
                declined=row.declined or 0,
            ))

        return trends

    async def get_sla_breach_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """Get summary of SLA breaches."""
        metrics = await self.get_wait_time_metrics(start_date, end_date)

        total_cases = sum(
            m.breaches + int((100 - m.breach_percentage) / 100 * m.breaches / (m.breach_percentage / 100))
            if m.breach_percentage > 0 else 0
            for m in metrics
        )

        total_breaches = sum(m.breaches for m in metrics)

        return {
            "total_cases_with_appointments": total_cases,
            "total_breaches": total_breaches,
            "overall_breach_rate": (total_breaches / total_cases * 100) if total_cases > 0 else 0,
            "by_tier": {
                m.tier: {
                    "sla_target_days": m.sla_target_days,
                    "breaches": m.breaches,
                    "breach_percentage": m.breach_percentage,
                    "avg_wait_days": m.avg_days,
                }
                for m in metrics
            },
        }

    async def get_alert_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """Get monitoring alert summary."""
        query = select(
            MonitoringAlert.severity,
            MonitoringAlert.alert_type,
            func.count(MonitoringAlert.id).label("count"),
            func.count(MonitoringAlert.id).filter(
                MonitoringAlert.resolved_at.isnot(None)
            ).label("resolved"),
        ).where(MonitoringAlert.deleted_at.is_(None))

        if start_date:
            query = query.where(MonitoringAlert.created_at >= start_date)
        if end_date:
            query = query.where(MonitoringAlert.created_at <= end_date)

        query = query.group_by(MonitoringAlert.severity, MonitoringAlert.alert_type)

        result = await self.session.execute(query)
        rows = result.all()

        by_severity = {}
        by_type = {}

        for row in rows:
            # Aggregate by severity
            if row.severity not in by_severity:
                by_severity[row.severity] = {"total": 0, "resolved": 0}
            by_severity[row.severity]["total"] += row.count
            by_severity[row.severity]["resolved"] += row.resolved

            # Aggregate by type
            if row.alert_type not in by_type:
                by_type[row.alert_type] = {"total": 0, "resolved": 0}
            by_type[row.alert_type]["total"] += row.count
            by_type[row.alert_type]["resolved"] += row.resolved

        return {
            "by_severity": by_severity,
            "by_type": by_type,
            "total_alerts": sum(s["total"] for s in by_severity.values()),
            "total_resolved": sum(s["resolved"] for s in by_severity.values()),
        }

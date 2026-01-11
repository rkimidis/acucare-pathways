"""Reporting API endpoints for Sprint 6."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.services.reporting import ReportingService

router = APIRouter(prefix="/reporting", tags=["reporting"])


# Response Models


class TierVolumeResponse(BaseModel):
    """Tier volume data."""
    tier: str
    count: int
    percentage: float


class PathwayVolumeResponse(BaseModel):
    """Pathway volume data."""
    pathway: str
    count: int
    percentage: float


class WaitTimeMetricsResponse(BaseModel):
    """Wait time metrics for a tier."""
    tier: str
    avg_days: float
    median_days: float
    min_days: float
    max_days: float
    p90_days: float
    sla_target_days: int
    breaches: int
    breach_percentage: float


class NoShowMetricsResponse(BaseModel):
    """No-show statistics."""
    total_appointments: int
    no_shows: int
    no_show_rate: float
    by_tier: dict[str, float]
    by_appointment_type: dict[str, float]


class OutcomeTrendResponse(BaseModel):
    """Outcome trend data point."""
    period: str
    completed: int
    discharged: int
    escalated: int
    declined: int


class SLABreachSummaryResponse(BaseModel):
    """SLA breach summary."""
    total_cases_with_appointments: int
    total_breaches: int
    overall_breach_rate: float
    by_tier: dict


class AlertSummaryResponse(BaseModel):
    """Alert summary."""
    by_severity: dict
    by_type: dict
    total_alerts: int
    total_resolved: int


# Endpoints


@router.get("/volumes/tier", response_model=list[TierVolumeResponse])
async def get_volumes_by_tier(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[TierVolumeResponse]:
    """Get case volumes grouped by tier."""
    service = ReportingService(db)
    volumes = await service.get_volumes_by_tier(start_date, end_date)
    return [
        TierVolumeResponse(
            tier=v.tier,
            count=v.count,
            percentage=v.percentage,
        )
        for v in volumes
    ]


@router.get("/volumes/pathway", response_model=list[PathwayVolumeResponse])
async def get_volumes_by_pathway(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[PathwayVolumeResponse]:
    """Get case volumes grouped by pathway."""
    service = ReportingService(db)
    volumes = await service.get_volumes_by_pathway(start_date, end_date)
    return [
        PathwayVolumeResponse(
            pathway=v.pathway,
            count=v.count,
            percentage=v.percentage,
        )
        for v in volumes
    ]


@router.get("/wait-times", response_model=list[WaitTimeMetricsResponse])
async def get_wait_time_metrics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[WaitTimeMetricsResponse]:
    """Get wait time statistics by tier."""
    service = ReportingService(db)
    metrics = await service.get_wait_time_metrics(start_date, end_date)
    return [
        WaitTimeMetricsResponse(
            tier=m.tier,
            avg_days=m.avg_days,
            median_days=m.median_days,
            min_days=m.min_days,
            max_days=m.max_days,
            p90_days=m.p90_days,
            sla_target_days=m.sla_target_days,
            breaches=m.breaches,
            breach_percentage=m.breach_percentage,
        )
        for m in metrics
    ]


@router.get("/no-shows", response_model=NoShowMetricsResponse)
async def get_no_show_metrics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> NoShowMetricsResponse:
    """Get no-show statistics."""
    service = ReportingService(db)
    metrics = await service.get_no_show_metrics(start_date, end_date)
    return NoShowMetricsResponse(
        total_appointments=metrics.total_appointments,
        no_shows=metrics.no_shows,
        no_show_rate=metrics.no_show_rate,
        by_tier=metrics.by_tier,
        by_appointment_type=metrics.by_appointment_type,
    )


@router.get("/outcome-trends", response_model=list[OutcomeTrendResponse])
async def get_outcome_trends(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    period: str = Query(default="month", regex="^(day|week|month)$"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[OutcomeTrendResponse]:
    """Get outcome trends over time."""
    service = ReportingService(db)
    trends = await service.get_outcome_trends(start_date, end_date, period)
    return [
        OutcomeTrendResponse(
            period=t.period,
            completed=t.completed,
            discharged=t.discharged,
            escalated=t.escalated,
            declined=t.declined,
        )
        for t in trends
    ]


@router.get("/sla-breaches", response_model=SLABreachSummaryResponse)
async def get_sla_breach_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> SLABreachSummaryResponse:
    """Get SLA breach summary."""
    service = ReportingService(db)
    summary = await service.get_sla_breach_summary(start_date, end_date)
    return SLABreachSummaryResponse(**summary)


@router.get("/alerts-summary", response_model=AlertSummaryResponse)
async def get_alert_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> AlertSummaryResponse:
    """Get monitoring alert summary."""
    service = ReportingService(db)
    summary = await service.get_alert_summary(start_date, end_date)
    return AlertSummaryResponse(**summary)


@router.get("/dashboard")
async def get_dashboard_data(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get all dashboard metrics in a single call."""
    service = ReportingService(db)

    tier_volumes = await service.get_volumes_by_tier(start_date, end_date)
    pathway_volumes = await service.get_volumes_by_pathway(start_date, end_date)
    wait_times = await service.get_wait_time_metrics(start_date, end_date)
    no_shows = await service.get_no_show_metrics(start_date, end_date)
    outcome_trends = await service.get_outcome_trends(start_date, end_date, "month")
    sla_summary = await service.get_sla_breach_summary(start_date, end_date)
    alert_summary = await service.get_alert_summary(start_date, end_date)

    return {
        "tier_volumes": [
            {"tier": v.tier, "count": v.count, "percentage": v.percentage}
            for v in tier_volumes
        ],
        "pathway_volumes": [
            {"pathway": v.pathway, "count": v.count, "percentage": v.percentage}
            for v in pathway_volumes
        ],
        "wait_times": [
            {
                "tier": m.tier,
                "avg_days": m.avg_days,
                "sla_target_days": m.sla_target_days,
                "breaches": m.breaches,
                "breach_percentage": m.breach_percentage,
            }
            for m in wait_times
        ],
        "no_shows": {
            "total": no_shows.total_appointments,
            "no_shows": no_shows.no_shows,
            "rate": no_shows.no_show_rate,
        },
        "outcome_trends": [
            {
                "period": t.period,
                "completed": t.completed,
                "discharged": t.discharged,
                "escalated": t.escalated,
                "declined": t.declined,
            }
            for t in outcome_trends
        ],
        "sla_summary": sla_summary,
        "alert_summary": alert_summary,
    }

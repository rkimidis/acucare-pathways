"""Disposition service for managing clinical disposition decisions."""

from datetime import datetime, timezone
import json
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.disposition import DispositionDraft, DispositionFinal, RiskFlag
from app.models.patient import Patient
from app.models.questionnaire import QuestionnaireDefinition, QuestionnaireResponse
from app.models.score import Score
from app.models.triage_case import TriageCase, TriageCaseStatus, TriageTier
from app.models.user import User
from app.services.audit import write_audit_event
from app.models.audit_event import ActorType


class DispositionError(Exception):
    """Base exception for disposition errors."""

    pass


class RationaleRequiredError(DispositionError):
    """Raised when override is attempted without rationale."""

    pass


class DispositionAlreadyFinalizedError(DispositionError):
    """Raised when trying to finalize an already finalized disposition."""

    pass


class DispositionService:
    """Service for managing disposition decisions.

    Handles:
    - Confirming draft dispositions
    - Overriding tier/pathway (with required rationale)
    - Audit trail for all decisions
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_draft_for_case(self, triage_case_id: str) -> DispositionDraft | None:
        """Get the latest disposition draft for a case.

        Args:
            triage_case_id: ID of the triage case

        Returns:
            Latest DispositionDraft or None
        """
        result = await self.session.execute(
            select(DispositionDraft)
            .where(DispositionDraft.triage_case_id == triage_case_id)
            .order_by(DispositionDraft.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_final_for_case(self, triage_case_id: str) -> DispositionFinal | None:
        """Get the final disposition for a case.

        Args:
            triage_case_id: ID of the triage case

        Returns:
            DispositionFinal or None
        """
        result = await self.session.execute(
            select(DispositionFinal)
            .where(DispositionFinal.triage_case_id == triage_case_id)
        )
        return result.scalar_one_or_none()

    async def confirm_disposition(
        self,
        triage_case_id: str,
        clinician: User,
        clinical_notes: str | None = None,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> DispositionFinal:
        """Confirm the draft disposition without changes.

        Args:
            triage_case_id: ID of the triage case
            clinician: Clinician confirming the disposition
            clinical_notes: Optional notes
            ip_address: Client IP for audit
            request_id: Request ID for audit

        Returns:
            Created DispositionFinal

        Raises:
            DispositionAlreadyFinalizedError: If already finalized
            ValueError: If no draft exists
        """
        # Check if already finalized
        existing_final = await self.get_final_for_case(triage_case_id)
        if existing_final:
            raise DispositionAlreadyFinalizedError(
                f"Case {triage_case_id} already has a finalized disposition"
            )

        # Get the draft
        draft = await self.get_draft_for_case(triage_case_id)
        if not draft:
            raise ValueError(f"No disposition draft found for case {triage_case_id}")

        now = datetime.now(timezone.utc)

        # Create final disposition (matching draft)
        final = DispositionFinal(
            triage_case_id=triage_case_id,
            draft_id=draft.id,
            tier=draft.tier,
            pathway=draft.pathway,
            self_book_allowed=draft.self_book_allowed,
            is_override=False,
            rationale=None,
            clinician_id=clinician.id,
            finalized_at=now,
            clinical_notes=clinical_notes,
        )

        # Mark draft as applied
        draft.is_applied = True
        draft.approved_by = clinician.id

        # Update triage case
        case_result = await self.session.execute(
            select(TriageCase).where(TriageCase.id == triage_case_id)
        )
        case = case_result.scalar_one_or_none()
        if case:
            case.status = TriageCaseStatus.CLOSED
            case.reviewed_at = now
            case.reviewed_by = clinician.id

        self.session.add(final)
        await self.session.commit()
        await self.session.refresh(final)

        # Write audit event
        await write_audit_event(
            session=self.session,
            actor_type=ActorType.STAFF,
            actor_id=clinician.id,
            actor_email=clinician.email,
            action="disposition.confirm",
            action_category="clinical",
            entity_type="triage_case",
            entity_id=triage_case_id,
            description=f"Disposition confirmed: {draft.tier} / {draft.pathway}",
            metadata={
                "tier": draft.tier,
                "pathway": draft.pathway,
                "draft_id": draft.id,
                "final_id": final.id,
            },
            ip_address=ip_address,
            request_id=request_id,
        )

        return final

    async def override_disposition(
        self,
        triage_case_id: str,
        clinician: User,
        new_tier: str,
        new_pathway: str,
        rationale: str,
        clinical_notes: str | None = None,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> DispositionFinal:
        """Override the draft disposition with a new tier/pathway.

        IMPORTANT: Rationale is REQUIRED for overrides.

        Args:
            triage_case_id: ID of the triage case
            clinician: Clinician performing the override
            new_tier: New tier to assign (RED, AMBER, GREEN, BLUE)
            new_pathway: New pathway to assign
            rationale: Required explanation for the override
            clinical_notes: Optional additional notes
            ip_address: Client IP for audit
            request_id: Request ID for audit

        Returns:
            Created DispositionFinal

        Raises:
            RationaleRequiredError: If rationale is empty
            DispositionAlreadyFinalizedError: If already finalized
        """
        # Validate rationale
        if not rationale or not rationale.strip():
            raise RationaleRequiredError(
                "Rationale is required when overriding a disposition"
            )

        # Check if already finalized
        existing_final = await self.get_final_for_case(triage_case_id)
        if existing_final:
            raise DispositionAlreadyFinalizedError(
                f"Case {triage_case_id} already has a finalized disposition"
            )

        # Get the draft
        draft = await self.get_draft_for_case(triage_case_id)

        now = datetime.now(timezone.utc)

        # Determine self_book_allowed based on new tier
        tier_enum = TriageTier(new_tier.lower())
        self_book_allowed = tier_enum not in (TriageTier.RED, TriageTier.AMBER)

        # Create final disposition (with override)
        final = DispositionFinal(
            triage_case_id=triage_case_id,
            draft_id=draft.id if draft else None,
            tier=new_tier.upper(),
            pathway=new_pathway,
            self_book_allowed=self_book_allowed,
            is_override=True,
            original_tier=draft.tier if draft else None,
            original_pathway=draft.pathway if draft else None,
            rationale=rationale.strip(),
            clinician_id=clinician.id,
            finalized_at=now,
            clinical_notes=clinical_notes,
        )

        # Mark draft as applied if exists
        if draft:
            draft.is_applied = True
            draft.approved_by = clinician.id

        # Update triage case with new tier/pathway
        case_result = await self.session.execute(
            select(TriageCase).where(TriageCase.id == triage_case_id)
        )
        case = case_result.scalar_one_or_none()
        if case:
            case.tier = tier_enum
            case.pathway = new_pathway
            case.self_book_allowed = self_book_allowed
            case.clinician_review_required = tier_enum in (TriageTier.RED, TriageTier.AMBER)
            case.status = TriageCaseStatus.CLOSED
            case.reviewed_at = now
            case.reviewed_by = clinician.id

        self.session.add(final)
        await self.session.commit()
        await self.session.refresh(final)

        # Write audit event
        await write_audit_event(
            session=self.session,
            actor_type=ActorType.STAFF,
            actor_id=clinician.id,
            actor_email=clinician.email,
            action="disposition.override",
            action_category="clinical",
            entity_type="triage_case",
            entity_id=triage_case_id,
            description=f"Disposition overridden: {draft.tier if draft else 'N/A'} -> {new_tier.upper()}",
            metadata={
                "original_tier": draft.tier if draft else None,
                "original_pathway": draft.pathway if draft else None,
                "new_tier": new_tier.upper(),
                "new_pathway": new_pathway,
                "rationale": rationale,
                "draft_id": draft.id if draft else None,
                "final_id": final.id,
            },
            ip_address=ip_address,
            request_id=request_id,
        )

        return final


class DashboardService:
    """Service for triage dashboard operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_queue_by_tier(
        self,
        tier: TriageTier | None = None,
        include_reviewed: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get triage queue filtered by tier.

        Args:
            tier: Optional tier filter (None = all tiers)
            include_reviewed: Whether to include already reviewed cases
            limit: Max results
            offset: Pagination offset

        Returns:
            List of case summaries with SLA info
        """
        query = (
            select(TriageCase)
            .where(TriageCase.is_deleted == False)
        )

        if tier:
            query = query.where(TriageCase.tier == tier)

        if not include_reviewed:
            query = query.where(TriageCase.reviewed_at.is_(None))
            query = query.where(
                TriageCase.status.in_([
                    TriageCaseStatus.TRIAGED,
                    TriageCaseStatus.IN_REVIEW,
                ])
            )

        # Order by SLA deadline (most urgent first)
        query = query.order_by(
            TriageCase.sla_deadline.asc().nullsfirst(),
            TriageCase.created_at.asc(),
        )

        query = query.offset(offset).limit(limit)

        result = await self.session.execute(query)
        cases = result.scalars().all()

        now = datetime.now(timezone.utc)
        queue = []

        for case in cases:
            # Calculate SLA status
            sla_remaining_minutes = None
            sla_status = "unknown"

            if case.sla_deadline:
                remaining = (case.sla_deadline - now).total_seconds() / 60
                sla_remaining_minutes = int(remaining)

                if case.sla_breached or remaining < 0:
                    sla_status = "breached"
                elif remaining < 15:
                    sla_status = "critical"
                elif remaining < 60:
                    sla_status = "warning"
                else:
                    sla_status = "normal"

            queue.append({
                "id": case.id,
                "patient_id": case.patient_id,
                "tier": case.tier.value if hasattr(case.tier, 'value') else case.tier,
                "pathway": case.pathway,
                "status": case.status.value if hasattr(case.status, 'value') else case.status,
                "created_at": case.created_at.isoformat() if case.created_at else None,
                "triaged_at": case.triaged_at.isoformat() if case.triaged_at else None,
                "sla_deadline": case.sla_deadline.isoformat() if case.sla_deadline else None,
                "sla_target_minutes": case.sla_target_minutes,
                "sla_remaining_minutes": sla_remaining_minutes,
                "sla_status": sla_status,
                "sla_breached": case.sla_breached,
                "clinician_review_required": case.clinician_review_required,
                "assigned_to_user_id": case.assigned_to_user_id or case.assigned_clinician_id,
            })

        return queue

    async def get_queue_counts(self) -> dict[str, int]:
        """Get count of pending cases by tier.

        Returns:
            Dict with counts per tier
        """
        result = await self.session.execute(
            select(
                TriageCase.tier,
                func.count(TriageCase.id).label("count"),
            )
            .where(TriageCase.is_deleted == False)
            .where(TriageCase.reviewed_at.is_(None))
            .where(
                TriageCase.status.in_([
                    TriageCaseStatus.TRIAGED,
                    TriageCaseStatus.IN_REVIEW,
                ])
            )
            .group_by(TriageCase.tier)
        )

        counts = {"red": 0, "amber": 0, "green": 0, "blue": 0, "total": 0}

        for row in result:
            tier, count = row
            if tier:
                tier_key = tier.value if hasattr(tier, 'value') else tier
                counts[tier_key] = count
                counts["total"] += count

        return counts

    async def get_oldest_case_info(
        self,
        tier: TriageTier,
    ) -> dict[str, int | bool | None]:
        """Get oldest unreviewed case age and SLA status for a tier."""
        result = await self.session.execute(
            select(TriageCase)
            .where(TriageCase.is_deleted == False)
            .where(TriageCase.tier == tier)
            .where(TriageCase.reviewed_at.is_(None))
            .where(
                TriageCase.status.in_([
                    TriageCaseStatus.TRIAGED,
                    TriageCaseStatus.IN_REVIEW,
                ])
            )
            .order_by(
                func.coalesce(TriageCase.triaged_at, TriageCase.created_at).asc()
            )
            .limit(1)
        )
        case = result.scalar_one_or_none()

        if not case:
            return {"age_minutes": None, "sla_breached": False}

        now = datetime.now(timezone.utc)
        oldest_at = case.triaged_at or case.created_at
        age_minutes = None
        if oldest_at:
            age_minutes = int((now - oldest_at).total_seconds() / 60)

        sla_breached = False
        if case.sla_deadline:
            sla_breached = case.sla_deadline < now
        if case.sla_breached:
            sla_breached = True

        return {"age_minutes": age_minutes, "sla_breached": sla_breached}

    async def get_breached_cases_count(self) -> int:
        """Get count of SLA-breached cases.

        Returns:
            Number of breached cases
        """
        now = datetime.now(timezone.utc)

        result = await self.session.execute(
            select(func.count(TriageCase.id))
            .where(TriageCase.is_deleted == False)
            .where(TriageCase.reviewed_at.is_(None))
            .where(
                or_(
                    TriageCase.sla_breached == True,
                    and_(
                        TriageCase.sla_deadline.isnot(None),
                        TriageCase.sla_deadline < now,
                    ),
                )
            )
        )

        return result.scalar() or 0

    async def get_case_summary(self, triage_case_id: str) -> dict[str, Any] | None:
        """Get detailed case summary for clinician review.

        Includes:
        - Case details
        - Patient info
        - Scores
        - Risk flags
        - Draft disposition
        - Questionnaire responses
        - Rules fired

        Args:
            triage_case_id: ID of the triage case

        Returns:
            Comprehensive case summary dict or None
        """
        # Get case with patient
        case_result = await self.session.execute(
            select(TriageCase)
            .where(TriageCase.id == triage_case_id)
            .where(TriageCase.is_deleted == False)
        )
        case = case_result.scalar_one_or_none()

        if not case:
            return None

        assigned_user_id = case.assigned_to_user_id or case.assigned_clinician_id

        # Get final disposition early (needed for user lookups)
        final_result = await self.session.execute(
            select(DispositionFinal)
            .where(DispositionFinal.triage_case_id == triage_case_id)
        )
        final = final_result.scalar_one_or_none()

        name_map: dict[str, str] = {}
        user_ids = {uid for uid in [assigned_user_id, case.reviewed_by] if uid}
        if final and final.clinician_id:
            user_ids.add(final.clinician_id)
        if user_ids:
            user_rows = await self.session.execute(
                select(User.id, User.first_name, User.last_name).where(User.id.in_(user_ids))
            )
            for row in user_rows.all():
                full_name = f"{row.first_name or ''} {row.last_name or ''}".strip() or row.id
                name_map[row.id] = full_name

        assigned_user_name = name_map.get(assigned_user_id) if assigned_user_id else None

        # Get patient
        patient_result = await self.session.execute(
            select(Patient).where(Patient.id == case.patient_id)
        )
        patient = patient_result.scalar_one_or_none()

        # Get scores
        scores_result = await self.session.execute(
            select(Score)
            .where(Score.triage_case_id == triage_case_id)
            .order_by(Score.created_at.desc())
        )
        scores = scores_result.scalars().all()

        # Get risk flags
        flags_result = await self.session.execute(
            select(RiskFlag)
            .where(RiskFlag.triage_case_id == triage_case_id)
            .order_by(RiskFlag.severity.desc(), RiskFlag.created_at.desc())
        )
        flags = flags_result.scalars().all()

        # Get draft disposition
        draft_result = await self.session.execute(
            select(DispositionDraft)
            .where(DispositionDraft.triage_case_id == triage_case_id)
            .order_by(DispositionDraft.created_at.desc())
            .limit(1)
        )
        draft = draft_result.scalar_one_or_none()

        # Get questionnaire responses
        responses_result = await self.session.execute(
            select(QuestionnaireResponse)
            .where(QuestionnaireResponse.triage_case_id == triage_case_id)
            .order_by(QuestionnaireResponse.created_at.desc())
        )
        responses = responses_result.scalars().all()

        definition_map: dict[str, QuestionnaireDefinition] = {}
        definition_ids = {resp.questionnaire_definition_id for resp in responses}
        if definition_ids:
            definitions_result = await self.session.execute(
                select(QuestionnaireDefinition)
                .where(QuestionnaireDefinition.id.in_(definition_ids))
            )
            definition_map = {
                definition.id: definition
                for definition in definitions_result.scalars().all()
            }

        # Calculate SLA info
        now = datetime.now(timezone.utc)
        sla_remaining_minutes = None
        sla_status = "unknown"

        if case.sla_deadline:
            remaining = (case.sla_deadline - now).total_seconds() / 60
            sla_remaining_minutes = int(remaining)

            if case.sla_breached or remaining < 0:
                sla_status = "breached"
            elif remaining < 15:
                sla_status = "critical"
            elif remaining < 60:
                sla_status = "warning"
            else:
                sla_status = "normal"

        timeline = self._build_case_timeline(
            case=case,
            responses=responses,
            scores=scores,
            draft=draft,
            final=final,
            name_map=name_map,
        )

        return {
            "case": {
                "id": case.id,
                "patient_id": case.patient_id,
                "status": case.status.value if hasattr(case.status, 'value') else case.status,
                "tier": case.tier.value if hasattr(case.tier, 'value') else case.tier,
                "pathway": case.pathway,
                "clinician_review_required": case.clinician_review_required,
                "self_book_allowed": case.self_book_allowed,
                "ruleset_version": case.ruleset_version,
                "ruleset_hash": case.ruleset_hash,
                "tier_explanation": case.tier_explanation,
                "clinical_notes": case.clinical_notes,
                "created_at": case.created_at.isoformat() if case.created_at else None,
                "triaged_at": case.triaged_at.isoformat() if case.triaged_at else None,
                "reviewed_at": case.reviewed_at.isoformat() if case.reviewed_at else None,
                "sla_deadline": case.sla_deadline.isoformat() if case.sla_deadline else None,
                "sla_target_minutes": case.sla_target_minutes,
                "sla_remaining_minutes": sla_remaining_minutes,
                "sla_status": sla_status,
                "sla_breached": case.sla_breached,
                "triage_note_url": case.triage_note_url,
                "assigned_to_user_id": assigned_user_id,
                "assigned_to_user_name": assigned_user_name,
            },
            "patient": {
                "id": patient.id if patient else None,
                "email": patient.email if patient else None,
                "first_name": patient.first_name if patient else None,
                "last_name": patient.last_name if patient else None,
                "date_of_birth": patient.date_of_birth if patient else None,
            } if patient else None,
            "scores": [
                {
                    "id": score.id,
                    "score_type": score.score_type.value if hasattr(score.score_type, 'value') else str(score.score_type),
                    "total_score": score.total_score,
                    "max_score": score.max_score,
                    "severity_band": score.severity_band.value if hasattr(score.severity_band, 'value') else str(score.severity_band),
                    "item_scores": score.item_scores,
                    "metadata": score.score_metadata,
                    "calculated_at": score.calculated_at.isoformat() if score.calculated_at else None,
                }
                for score in scores
            ],
            "risk_flags": [
                {
                    "id": flag.id,
                    "rule_id": flag.rule_id,
                    "flag_type": flag.flag_type.value if hasattr(flag.flag_type, 'value') else str(flag.flag_type),
                    "severity": flag.severity.value if hasattr(flag.severity, 'value') else str(flag.severity),
                    "explanation": flag.explanation,
                    "reviewed": flag.reviewed,
                }
                for flag in flags
            ],
            "draft_disposition": {
                "id": draft.id,
                "tier": draft.tier,
                "pathway": draft.pathway,
                "self_book_allowed": draft.self_book_allowed,
                "clinician_review_required": draft.clinician_review_required,
                "rules_fired": draft.rules_fired,
                "explanations": draft.explanations,
                "ruleset_version": draft.ruleset_version,
                "is_applied": draft.is_applied,
            } if draft else None,
            "final_disposition": {
                "id": final.id,
                "tier": final.tier,
                "pathway": final.pathway,
                "is_override": final.is_override,
                "original_tier": final.original_tier,
                "original_pathway": final.original_pathway,
                "rationale": final.rationale,
                "clinical_notes": final.clinical_notes,
                "finalized_at": final.finalized_at.isoformat() if final.finalized_at else None,
                "clinician_id": final.clinician_id,
            } if final else None,
            "questionnaire_responses": [
                {
                    "id": resp.id,
                    "questionnaire_definition_id": resp.questionnaire_definition_id,
                    "answers": resp.answers,
                    "answers_human": self._build_human_answers(
                        resp.answers,
                        definition_map.get(resp.questionnaire_definition_id),
                    ),
                    "submitted_at": resp.submitted_at.isoformat() if resp.submitted_at else None,
                }
                for resp in responses
            ],
            "timeline": timeline,
        }

    @staticmethod
    def _build_human_answers(
        answers: dict[str, Any],
        definition: QuestionnaireDefinition | None,
    ) -> list[dict[str, str]]:
        """Generate human-readable Q&A from questionnaire answers."""
        if not answers:
            return []

        schema = definition.schema if definition else {}
        fields = schema.get("fields", [])
        field_map = {
            field.get("id"): field
            for field in fields
            if isinstance(field, dict)
        }

        def humanize_field_id(field_id: str) -> str:
            return field_id.replace("_", " ").replace("-", " ").strip().title()

        def format_answer(value: Any, field: dict[str, Any] | None) -> str:
            if value is None or value == "" or value == []:
                return "—"

            field_type = field.get("type") if field else None
            options = field.get("options") if field else None

            def option_label(val: Any) -> str:
                if not isinstance(options, list):
                    return str(val)
                for opt in options:
                    if opt.get("value") == val:
                        return str(opt.get("label") or opt.get("value"))
                return str(val)

            if field_type == "boolean":
                return "Yes" if bool(value) else "No"
            if field_type == "multiselect":
                if isinstance(value, list):
                    return ", ".join(option_label(v) for v in value) or "—"
                return str(value)
            if field_type == "select":
                return option_label(value)
            if field_type in ("number", "text"):
                return str(value)

            if isinstance(value, list):
                return ", ".join(str(v) for v in value)
            if isinstance(value, dict):
                return json.dumps(value, ensure_ascii=True)
            return str(value)

        items: list[dict[str, str]] = []

        for field_id, field in field_map.items():
            if field_id not in answers:
                continue
            question = (
                field.get("label")
                or field.get("question")
                or field.get("title")
                or field.get("prompt")
                or humanize_field_id(field_id)
            )
            items.append(
                {
                    "field_id": field_id,
                    "question": str(question),
                    "answer": format_answer(answers.get(field_id), field),
                }
            )

        for field_id, value in answers.items():
            if field_id in field_map:
                continue
            items.append(
                {
                    "field_id": field_id,
                    "question": humanize_field_id(field_id),
                    "answer": format_answer(value, None),
                }
            )

        return items

    @staticmethod
    def _build_case_timeline(
        case: TriageCase,
        responses: list[QuestionnaireResponse],
        scores: list[Score],
        draft: DispositionDraft | None,
        final: DispositionFinal | None,
        name_map: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Build a compact case timeline for clinician context."""
        entries: list[dict[str, Any]] = []

        submitted_times = [
            r.submitted_at or r.created_at
            for r in responses
            if r.submitted_at or r.created_at
        ]
        if submitted_times:
            intake_time = min(submitted_times)
            entries.append({
                "label": "Intake submitted",
                "timestamp": intake_time,
                "actor_type": "system",
                "actor_name": "System",
            })

        score_times = [s.calculated_at for s in scores if s.calculated_at]
        if score_times:
            score_time = max(score_times)
            entries.append({
                "label": "Scores calculated",
                "timestamp": score_time,
                "actor_type": "system",
                "actor_name": "System",
            })

        if draft and draft.created_at:
            rules_label = (
                f"Rules evaluated (v{draft.ruleset_version})"
                if draft.ruleset_version
                else "Rules evaluated"
            )
            entries.append({
                "label": rules_label,
                "timestamp": draft.created_at,
                "actor_type": "system",
                "actor_name": "System",
            })

        if case.reviewed_at:
            reviewer = name_map.get(case.reviewed_by) if case.reviewed_by else None
            entries.append({
                "label": "Case reviewed",
                "timestamp": case.reviewed_at,
                "actor_type": "clinician",
                "actor_name": reviewer or "Clinician",
            })

        if final and final.finalized_at:
            final_label = "Disposition overridden" if final.is_override else "Disposition confirmed"
            clinician_name = name_map.get(final.clinician_id) if final.clinician_id else None
            entries.append({
                "label": final_label,
                "timestamp": final.finalized_at,
                "actor_type": "clinician",
                "actor_name": clinician_name or "Clinician",
            })

        entries.sort(key=lambda entry: entry["timestamp"])
        return [
            {
                "label": entry["label"],
                "timestamp": entry["timestamp"].isoformat(),
                "actor_type": entry["actor_type"],
                "actor_name": entry["actor_name"],
            }
            for entry in entries
        ]

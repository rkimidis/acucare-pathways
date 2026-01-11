"""LLM summary service for Sprint 6.

Generates clinical note drafts from structured data.
Requires clinician approval and logs prompt version + model + hash.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import LLMSummary, LLMSummaryStatus
from app.models.monitoring import WaitingListCheckIn
from app.models.questionnaire import QuestionnaireResponse
from app.models.score import Score
from app.models.triage_case import TriageCase


# Prompt templates with version tracking
PROMPT_TEMPLATES = {
    "triage_assessment": {
        "version": "1.0.0",
        "template": """Generate a clinical summary note for a psychiatric triage assessment.

Patient Assessment Data:
- Triage Tier: {tier}
- Status: {status}
- Pathway: {pathway}

Questionnaire Responses:
{questionnaire_data}

Assessment Scores:
{scores_data}

Risk Flags:
{risk_flags}

Instructions:
- Write in professional clinical language
- Include all relevant clinical findings
- Note any risk factors identified
- Summarize recommended next steps
- Keep the summary concise but comprehensive

Clinical Summary:""",
    },
    "check_in": {
        "version": "1.0.0",
        "template": """Generate a clinical note summarizing a patient check-in.

Check-in Data:
- Date: {checkin_date}
- PHQ-2 Score: {phq2_total}/6
- GAD-2 Score: {gad2_total}/6
- Wellbeing Rating: {wellbeing_rating}/10
- Suicidal Ideation Reported: {suicidal_ideation}
- Self-Harm Reported: {self_harm}
- Callback Requested: {wants_callback}

Patient Comments:
{patient_comments}

Instructions:
- Write in professional clinical language
- Highlight any concerning responses
- Note changes from previous assessments if available
- Recommend appropriate follow-up actions

Clinical Summary:""",
    },
    "appointment_notes": {
        "version": "1.0.0",
        "template": """Generate structured clinical notes from appointment data.

Appointment Details:
- Date: {appointment_date}
- Type: {appointment_type}
- Clinician: {clinician_name}
- Duration: {duration} minutes

Session Notes:
{session_notes}

Presenting Concerns:
{presenting_concerns}

Mental State Examination:
{mse_data}

Instructions:
- Write in professional clinical language
- Structure using SOAP format if appropriate
- Include relevant clinical observations
- Note any risk factors or concerns
- Summarize treatment plan and follow-up

Clinical Summary:""",
    },
}


@dataclass
class LLMConfig:
    """Configuration for LLM service."""
    model_id: str
    model_version: str
    api_endpoint: str
    api_key: str
    max_tokens: int = 1000
    temperature: float = 0.3


class LLMSummaryService:
    """Service for generating and managing LLM clinical summaries."""

    def __init__(
        self,
        session: AsyncSession,
        llm_config: Optional[LLMConfig] = None,
    ) -> None:
        self.session = session
        self.llm_config = llm_config or LLMConfig(
            model_id="gpt-4",
            model_version="turbo-2024-04-09",
            api_endpoint="https://api.openai.com/v1/chat/completions",
            api_key="",  # Should be set from environment
        )

    @staticmethod
    def compute_hash(content: str) -> str:
        """Compute SHA-256 hash."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _get_prompt_template(self, source_type: str) -> tuple[str, str]:
        """Get prompt template and version."""
        if source_type not in PROMPT_TEMPLATES:
            raise ValueError(f"Unknown source type: {source_type}")

        template_info = PROMPT_TEMPLATES[source_type]
        return template_info["template"], template_info["version"]

    async def generate_triage_summary(
        self,
        triage_case_id: str,
    ) -> LLMSummary:
        """Generate summary from triage assessment data."""
        # Fetch case data
        case_result = await self.session.execute(
            select(TriageCase).where(TriageCase.id == triage_case_id)
        )
        case = case_result.scalar_one_or_none()

        if not case:
            raise ValueError(f"Case not found: {triage_case_id}")

        # Fetch questionnaire responses
        responses_result = await self.session.execute(
            select(QuestionnaireResponse).where(
                QuestionnaireResponse.triage_case_id == triage_case_id
            )
        )
        responses = responses_result.scalars().all()

        # Fetch scores
        scores_result = await self.session.execute(
            select(Score).where(Score.triage_case_id == triage_case_id)
        )
        scores = scores_result.scalars().all()

        # Build source data
        source_data = {
            "case": {
                "tier": case.tier,
                "status": case.status,
                "pathway": case.pathway,
            },
            "responses": [
                {"questionnaire_id": r.questionnaire_id, "answers": r.answers}
                for r in responses
            ],
            "scores": [
                {"type": s.score_type, "value": s.value, "band": s.severity_band}
                for s in scores
            ],
        }

        # Format questionnaire data
        questionnaire_data = "\n".join(
            f"- {r.questionnaire_id}: {json.dumps(r.answers)}"
            for r in responses
        ) or "No questionnaire responses"

        # Format scores data
        scores_data = "\n".join(
            f"- {s.score_type}: {s.value} ({s.severity_band})"
            for s in scores
        ) or "No scores calculated"

        # Get risk flags (simplified - would come from RiskFlag model)
        risk_flags = "None identified"

        # Get template
        template, version = self._get_prompt_template("triage_assessment")

        # Build prompt
        prompt = template.format(
            tier=case.tier,
            status=case.status,
            pathway=case.pathway or "Not assigned",
            questionnaire_data=questionnaire_data,
            scores_data=scores_data,
            risk_flags=risk_flags,
        )

        # Generate summary (mock for now - would call actual LLM API)
        generated_summary = await self._call_llm(prompt)

        # Create summary record
        summary = LLMSummary(
            id=str(uuid.uuid4()),
            triage_case_id=triage_case_id,
            source_data_type="triage_assessment",
            source_data_hash=self.compute_hash(json.dumps(source_data, sort_keys=True)),
            model_id=self.llm_config.model_id,
            model_version=self.llm_config.model_version,
            prompt_template_version=version,
            prompt_hash=self.compute_hash(prompt),
            generated_summary=generated_summary,
            generated_at=datetime.now(),
            status=LLMSummaryStatus.DRAFT.value,
        )

        self.session.add(summary)
        await self.session.commit()
        await self.session.refresh(summary)

        return summary

    async def generate_checkin_summary(
        self,
        checkin_id: str,
    ) -> LLMSummary:
        """Generate summary from check-in data."""
        # Fetch check-in data
        checkin_result = await self.session.execute(
            select(WaitingListCheckIn).where(WaitingListCheckIn.id == checkin_id)
        )
        checkin = checkin_result.scalar_one_or_none()

        if not checkin:
            raise ValueError(f"Check-in not found: {checkin_id}")

        # Build source data
        source_data = {
            "checkin_id": checkin.id,
            "phq2_total": checkin.phq2_total,
            "gad2_total": checkin.gad2_total,
            "wellbeing_rating": checkin.wellbeing_rating,
            "suicidal_ideation": checkin.suicidal_ideation,
            "self_harm": checkin.self_harm,
            "wants_callback": checkin.wants_callback,
            "comments": checkin.patient_comments,
        }

        # Get template
        template, version = self._get_prompt_template("check_in")

        # Build prompt
        prompt = template.format(
            checkin_date=checkin.completed_at.isoformat() if checkin.completed_at else "N/A",
            phq2_total=checkin.phq2_total or 0,
            gad2_total=checkin.gad2_total or 0,
            wellbeing_rating=checkin.wellbeing_rating or "Not reported",
            suicidal_ideation="Yes" if checkin.suicidal_ideation else "No",
            self_harm="Yes" if checkin.self_harm else "No",
            wants_callback="Yes" if checkin.wants_callback else "No",
            patient_comments=checkin.patient_comments or "None provided",
        )

        # Generate summary
        generated_summary = await self._call_llm(prompt)

        # Create summary record
        summary = LLMSummary(
            id=str(uuid.uuid4()),
            triage_case_id=checkin.triage_case_id,
            source_data_type="check_in",
            source_data_hash=self.compute_hash(json.dumps(source_data, sort_keys=True)),
            model_id=self.llm_config.model_id,
            model_version=self.llm_config.model_version,
            prompt_template_version=version,
            prompt_hash=self.compute_hash(prompt),
            generated_summary=generated_summary,
            generated_at=datetime.now(),
            status=LLMSummaryStatus.DRAFT.value,
        )

        self.session.add(summary)
        await self.session.commit()
        await self.session.refresh(summary)

        return summary

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM API to generate summary.

        In production, this would make actual API calls.
        For now, returns a structured placeholder.
        """
        # Mock response for development
        # In production, would use httpx or aiohttp to call API
        return f"""[AI-Generated Draft - Requires Clinician Review]

Clinical Summary:

This summary was generated from structured assessment data. Key observations:

1. Assessment data has been processed and analyzed
2. Risk factors have been identified where present
3. Recommended actions are based on clinical guidelines

This draft requires clinician review and approval before being added to the patient record.

---
Model: {self.llm_config.model_id}
Version: {self.llm_config.model_version}
Generated: {datetime.now().isoformat()}
"""

    async def submit_for_approval(
        self,
        summary_id: str,
    ) -> LLMSummary:
        """Submit a draft summary for clinician approval."""
        result = await self.session.execute(
            select(LLMSummary).where(LLMSummary.id == summary_id)
        )
        summary = result.scalar_one_or_none()

        if not summary:
            raise ValueError(f"Summary not found: {summary_id}")

        summary.submit_for_approval()
        await self.session.commit()
        await self.session.refresh(summary)

        return summary

    async def approve_summary(
        self,
        summary_id: str,
        approver_id: str,
        final_summary: Optional[str] = None,
        edits: Optional[str] = None,
    ) -> LLMSummary:
        """Approve a summary with optional edits."""
        result = await self.session.execute(
            select(LLMSummary).where(LLMSummary.id == summary_id)
        )
        summary = result.scalar_one_or_none()

        if not summary:
            raise ValueError(f"Summary not found: {summary_id}")

        summary.approve(approver_id, final_summary, edits)
        summary.reviewed_by = approver_id
        summary.reviewed_at = datetime.now()

        await self.session.commit()
        await self.session.refresh(summary)

        return summary

    async def reject_summary(
        self,
        summary_id: str,
        rejector_id: str,
        reason: str,
    ) -> LLMSummary:
        """Reject a summary."""
        result = await self.session.execute(
            select(LLMSummary).where(LLMSummary.id == summary_id)
        )
        summary = result.scalar_one_or_none()

        if not summary:
            raise ValueError(f"Summary not found: {summary_id}")

        summary.reject(rejector_id, reason)
        await self.session.commit()
        await self.session.refresh(summary)

        return summary

    async def get_pending_summaries(
        self,
        limit: int = 50,
    ) -> list[LLMSummary]:
        """Get summaries pending approval."""
        result = await self.session.execute(
            select(LLMSummary)
            .where(LLMSummary.status == LLMSummaryStatus.PENDING_APPROVAL.value)
            .order_by(LLMSummary.generated_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_summary_by_case(
        self,
        triage_case_id: str,
    ) -> list[LLMSummary]:
        """Get all summaries for a case."""
        result = await self.session.execute(
            select(LLMSummary)
            .where(LLMSummary.triage_case_id == triage_case_id)
            .order_by(LLMSummary.generated_at.desc())
        )
        return list(result.scalars().all())

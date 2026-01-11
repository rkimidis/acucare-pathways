"""Triage service orchestrating scoring and rules evaluation."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.disposition import DispositionDraft, RiskFlag, RiskFlagType, RiskSeverity
from app.models.questionnaire import QuestionnaireResponse
from app.models.score import Score, ScoreType
from app.models.triage_case import TriageCase, TriageCaseStatus
from app.rules.engine import EvaluationResult, RulesEngine
from app.services.scoring import ScoringService


class TriageService:
    """Service for performing triage evaluations.

    Orchestrates:
    1. Score calculation (PHQ-9, GAD-7, AUDIT-C)
    2. Rules engine evaluation
    3. Risk flag creation
    4. Disposition draft creation
    5. Safeguard enforcement
    """

    def __init__(
        self,
        session: AsyncSession,
        ruleset_filename: str = "uk-private-triage-v1.0.0.yaml",
    ) -> None:
        """Initialize triage service.

        Args:
            session: Database session
            ruleset_filename: Ruleset file to use
        """
        self.session = session
        self.engine = RulesEngine(ruleset_filename)

    async def evaluate_case(
        self,
        triage_case: TriageCase,
        questionnaire_response: QuestionnaireResponse,
        apply_result: bool = False,
    ) -> EvaluationResult:
        """Evaluate a triage case.

        Args:
            triage_case: The triage case to evaluate
            questionnaire_response: The questionnaire response with answers
            apply_result: Whether to apply the result to the case

        Returns:
            EvaluationResult from rules engine
        """
        answers = questionnaire_response.answers

        # Step 1: Calculate scores
        scores = await self._calculate_and_store_scores(
            triage_case_id=triage_case.id,
            response_id=questionnaire_response.id,
            answers=answers,
        )

        # Step 2: Build facts for rules engine
        facts = self._build_facts(answers, scores)

        # Step 3: Evaluate rules
        result = self.engine.evaluate(facts)

        # Step 4: Create risk flags
        await self._create_risk_flags(triage_case.id, result)

        # Step 5: Create disposition draft
        await self._create_disposition_draft(triage_case.id, result)

        # Step 6: Apply result if requested
        if apply_result:
            await self._apply_result(triage_case, result)

        return result

    async def _calculate_and_store_scores(
        self,
        triage_case_id: str,
        response_id: str,
        answers: dict[str, Any],
    ) -> dict[str, Any]:
        """Calculate and store all applicable scores.

        Returns:
            Dict formatted for rules engine
        """
        score_results = ScoringService.calculate_all_applicable(answers)
        scores_for_engine = ScoringService.get_scores_for_rules_engine(answers)

        # Store each score in database
        for result in score_results:
            score = Score(
                triage_case_id=triage_case_id,
                questionnaire_response_id=response_id,
                score_type=result.score_type,
                score_version=result.score_version,
                total_score=result.total_score,
                max_score=result.max_score,
                severity_band=result.severity_band,
                item_scores=result.item_scores,
                score_metadata=result.metadata,
                calculated_at=result.calculated_at,
            )
            self.session.add(score)

        await self.session.commit()

        return scores_for_engine

    def _build_facts(
        self,
        answers: dict[str, Any],
        scores: dict[str, Any],
    ) -> dict[str, Any]:
        """Build facts dictionary for rules engine.

        Combines questionnaire answers with calculated scores and
        derives risk indicators.
        """
        facts = {
            "scores": scores.get("scores", {}),
            "risk": self._derive_risk_facts(answers, scores),
            "presentation": self._derive_presentation_facts(answers),
            "preferences": self._derive_preference_facts(answers),
        }

        return facts

    def _derive_risk_facts(
        self,
        answers: dict[str, Any],
        scores: dict[str, Any],
    ) -> dict[str, Any]:
        """Derive risk-related facts from answers and scores."""
        risk: dict[str, Any] = {}

        # Suicidal ideation indicators
        risk["suicidal_thoughts_present"] = answers.get("suicidal_thoughts", False)
        risk["suicidal_intent_now"] = answers.get("suicidal_intent_now", False)
        risk["suicide_plan"] = answers.get("suicide_plan", False)
        risk["means_access"] = answers.get("means_access", False)
        risk["recent_suicide_attempt"] = answers.get("recent_suicide_attempt", False)
        risk["attempt_required_medical_attention"] = answers.get(
            "attempt_required_medical_attention", False
        )

        # Violence/harm to others
        risk["violence_imminent"] = answers.get("violence_imminent", False)
        risk["harm_to_others"] = answers.get("harm_to_others", False)
        risk["access_to_weapons_or_means"] = answers.get("access_to_weapons", False)

        # Psychosis indicators
        risk["psychosis_severe"] = answers.get("psychosis_severe", False)
        risk["new_psychosis"] = answers.get("new_psychosis", False)
        risk["psychosis_any"] = answers.get("psychosis_any", False)
        risk["command_hallucinations_harm"] = answers.get("command_hallucinations_harm", False)
        risk["intent_to_act_on_commands"] = answers.get("intent_to_act_on_commands", False)
        risk["unable_to_care_for_self"] = answers.get("unable_to_care_for_self", False)

        # Mania indicators
        risk["mania_severe"] = answers.get("mania_severe", False)
        risk["mania_red_flag"] = answers.get("mania_red_flag", False)
        risk["dangerous_behaviour"] = answers.get("dangerous_behaviour", False)

        # Substance risk
        risk["substance_withdrawal_risk"] = answers.get("substance_withdrawal_risk", False)

        # Functional impairment
        risk["functional_impairment_severe"] = answers.get("functional_impairment_severe", False)

        # Panic indicators
        risk["panic_severe_or_frequent"] = answers.get("panic_severe_or_frequent", False)

        # Medication safety
        risk["medication_toxicity_symptoms"] = answers.get("medication_toxicity_symptoms", False)
        risk["serious_med_side_effects"] = answers.get("serious_med_side_effects", False)

        # Dissociation
        risk["dissociation_severe"] = answers.get("dissociation_severe", False)

        # Count suicide risk factors
        risk_factors = [
            answers.get("previous_suicide_attempt", False),
            answers.get("family_history_suicide", False),
            answers.get("social_isolation", False),
            answers.get("recent_loss", False),
            answers.get("substance_use", False),
        ]
        risk["suicide_risk_factors_count"] = sum(1 for f in risk_factors if f)

        # Aggregate flag for any RED/AMBER indicators
        red_amber_indicators = [
            risk["suicidal_intent_now"],
            risk["suicide_plan"],
            risk["violence_imminent"],
            risk["psychosis_severe"],
            risk["mania_severe"],
            risk["new_psychosis"],
            risk["command_hallucinations_harm"],
        ]
        risk["any_red_amber_flag"] = any(red_amber_indicators)

        return risk

    def _derive_presentation_facts(
        self,
        answers: dict[str, Any],
    ) -> dict[str, Any]:
        """Derive presentation-related facts from answers."""
        return {
            "trauma_primary": answers.get("trauma_primary", False),
            "neurodevelopmental_primary": answers.get("neurodevelopmental_primary", False),
            "complex_formulation_needed": answers.get("complex_formulation_needed", False),
        }

    def _derive_preference_facts(
        self,
        answers: dict[str, Any],
    ) -> dict[str, Any]:
        """Derive patient preference facts from answers."""
        return {
            "open_to_digital": answers.get("open_to_digital", False),
            "prefers_in_person": answers.get("prefers_in_person", True),
        }

    async def _create_risk_flags(
        self,
        triage_case_id: str,
        result: EvaluationResult,
    ) -> None:
        """Create risk flag records from evaluation result."""
        for flag_data in result.flags:
            flag_type_str = flag_data.get("type", "COMPLEXITY")
            severity_str = flag_data.get("severity", "LOW")

            # Map string to enum
            try:
                flag_type = RiskFlagType(flag_type_str)
            except ValueError:
                flag_type = RiskFlagType.COMPLEXITY

            try:
                severity = RiskSeverity(severity_str)
            except ValueError:
                severity = RiskSeverity.LOW

            # Find the rule that generated this flag
            rule_id = result.rules_fired[0] if result.rules_fired else "unknown"

            # Find the explanation for this flag
            explanation = result.explanations[0] if result.explanations else None

            flag = RiskFlag(
                triage_case_id=triage_case_id,
                rule_id=rule_id,
                flag_type=flag_type,
                severity=severity,
                explanation=explanation,
                reviewed=False,
            )
            self.session.add(flag)

        await self.session.commit()

    async def _create_disposition_draft(
        self,
        triage_case_id: str,
        result: EvaluationResult,
    ) -> DispositionDraft:
        """Create disposition draft from evaluation result."""
        draft = DispositionDraft(
            triage_case_id=triage_case_id,
            tier=result.tier.value.upper(),
            pathway=result.pathway,
            self_book_allowed=result.self_book_allowed,
            clinician_review_required=result.clinician_review_required,
            rules_fired=result.rules_fired,
            explanations=result.explanations,
            ruleset_version=result.ruleset_version,
            ruleset_hash=result.ruleset_hash,
            evaluation_context=result.evaluation_context,
            is_applied=False,
        )
        self.session.add(draft)
        await self.session.commit()
        await self.session.refresh(draft)

        return draft

    async def _apply_result(
        self,
        triage_case: TriageCase,
        result: EvaluationResult,
    ) -> None:
        """Apply evaluation result to triage case.

        Updates the triage case with tier, pathway, and safeguards.
        """
        triage_case.tier = result.tier
        triage_case.pathway = result.pathway
        triage_case.ruleset_version = result.ruleset_version
        triage_case.ruleset_hash = result.ruleset_hash
        triage_case.tier_explanation = {
            "rules_fired": result.rules_fired,
            "explanations": result.explanations,
            "flags": result.flags,
        }

        # Apply safeguards
        triage_case.clinician_review_required = result.clinician_review_required
        triage_case.self_book_allowed = result.self_book_allowed

        # Update status
        triage_case.status = TriageCaseStatus.TRIAGED

        await self.session.commit()

    async def check_self_booking_allowed(
        self,
        triage_case_id: str,
    ) -> bool:
        """Check if self-booking is allowed for a triage case.

        Enforces safeguards: RED and AMBER tiers cannot self-book.

        Args:
            triage_case_id: ID of the triage case

        Returns:
            True if self-booking is allowed
        """
        result = await self.session.execute(
            select(TriageCase).where(TriageCase.id == triage_case_id)
        )
        case = result.scalar_one_or_none()

        if not case:
            return False

        # Safeguard: RED and AMBER cannot self-book
        if case.tier in (TriageCaseStatus.RED, TriageCaseStatus.AMBER):
            return False

        return case.self_book_allowed

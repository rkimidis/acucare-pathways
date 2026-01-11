"""Clinical assessment scoring service.

Implements validated scoring algorithms for standardized assessments:
- PHQ-9: Patient Health Questionnaire-9 (Depression)
- GAD-7: Generalized Anxiety Disorder-7
- AUDIT-C: Alcohol Use Disorders Identification Test - Consumption

All scoring is deterministic and follows published clinical guidelines.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.models.score import ScoreType, SeverityBand


# Scoring algorithm versions
PHQ9_VERSION = "1.0.0"
GAD7_VERSION = "1.0.0"
AUDIT_C_VERSION = "1.0.0"


@dataclass
class ScoreResult:
    """Result of a score calculation."""

    score_type: ScoreType
    score_version: str
    total_score: int
    max_score: int
    severity_band: SeverityBand
    item_scores: dict[str, int]
    metadata: dict[str, Any]
    calculated_at: datetime


class PHQ9Scorer:
    """PHQ-9 Depression Screening Scorer.

    The PHQ-9 is a 9-item self-report questionnaire for depression screening.
    Each item is scored 0-3 (Not at all, Several days, More than half the days, Nearly every day).
    Total score range: 0-27.

    Severity bands (per Kroenke et al., 2001):
    - 0-4: Minimal/None
    - 5-9: Mild
    - 10-14: Moderate
    - 15-19: Moderately Severe
    - 20-27: Severe

    Item 9 (suicidal ideation) requires special attention regardless of total score.
    """

    ITEMS = [
        "phq9_q1",  # Little interest or pleasure
        "phq9_q2",  # Feeling down, depressed, hopeless
        "phq9_q3",  # Trouble falling/staying asleep, sleeping too much
        "phq9_q4",  # Feeling tired or having little energy
        "phq9_q5",  # Poor appetite or overeating
        "phq9_q6",  # Feeling bad about yourself
        "phq9_q7",  # Trouble concentrating
        "phq9_q8",  # Moving/speaking slowly or being fidgety
        "phq9_q9",  # Thoughts of self-harm or being better off dead
    ]

    MAX_SCORE = 27
    MAX_ITEM_SCORE = 3

    @classmethod
    def calculate(cls, answers: dict[str, Any]) -> ScoreResult:
        """Calculate PHQ-9 score from questionnaire answers.

        Args:
            answers: Dict mapping question IDs to numeric responses (0-3)

        Returns:
            ScoreResult with total score, severity band, and item details
        """
        item_scores: dict[str, int] = {}
        total = 0

        for item in cls.ITEMS:
            value = answers.get(item)
            if value is not None:
                score = cls._normalize_item_score(value)
                item_scores[item] = score
                total += score
            else:
                item_scores[item] = 0

        severity = cls._get_severity_band(total)
        item9_positive = item_scores.get("phq9_q9", 0) > 0

        return ScoreResult(
            score_type=ScoreType.PHQ9,
            score_version=PHQ9_VERSION,
            total_score=total,
            max_score=cls.MAX_SCORE,
            severity_band=severity,
            item_scores=item_scores,
            metadata={
                "item9_positive": item9_positive,
                "item9_value": item_scores.get("phq9_q9", 0),
            },
            calculated_at=datetime.now(timezone.utc),
        )

    @classmethod
    def _normalize_item_score(cls, value: Any) -> int:
        """Normalize item value to 0-3 range."""
        if isinstance(value, bool):
            return 3 if value else 0
        if isinstance(value, str):
            value = value.lower()
            mapping = {
                "not at all": 0,
                "several days": 1,
                "more than half the days": 2,
                "nearly every day": 3,
                "0": 0,
                "1": 1,
                "2": 2,
                "3": 3,
            }
            return mapping.get(value, 0)
        if isinstance(value, (int, float)):
            return max(0, min(cls.MAX_ITEM_SCORE, int(value)))
        return 0

    @classmethod
    def _get_severity_band(cls, total: int) -> SeverityBand:
        """Determine severity band from total score."""
        if total <= 4:
            return SeverityBand.MINIMAL
        elif total <= 9:
            return SeverityBand.MILD
        elif total <= 14:
            return SeverityBand.MODERATE
        elif total <= 19:
            return SeverityBand.MODERATELY_SEVERE
        else:
            return SeverityBand.SEVERE


class GAD7Scorer:
    """GAD-7 Anxiety Screening Scorer.

    The GAD-7 is a 7-item self-report questionnaire for anxiety screening.
    Each item is scored 0-3 (Not at all, Several days, More than half the days, Nearly every day).
    Total score range: 0-21.

    Severity bands (per Spitzer et al., 2006):
    - 0-4: Minimal
    - 5-9: Mild
    - 10-14: Moderate
    - 15-21: Severe
    """

    ITEMS = [
        "gad7_q1",  # Feeling nervous, anxious, or on edge
        "gad7_q2",  # Not being able to stop or control worrying
        "gad7_q3",  # Worrying too much about different things
        "gad7_q4",  # Trouble relaxing
        "gad7_q5",  # Being so restless it's hard to sit still
        "gad7_q6",  # Becoming easily annoyed or irritable
        "gad7_q7",  # Feeling afraid as if something awful might happen
    ]

    MAX_SCORE = 21
    MAX_ITEM_SCORE = 3

    @classmethod
    def calculate(cls, answers: dict[str, Any]) -> ScoreResult:
        """Calculate GAD-7 score from questionnaire answers.

        Args:
            answers: Dict mapping question IDs to numeric responses (0-3)

        Returns:
            ScoreResult with total score, severity band, and item details
        """
        item_scores: dict[str, int] = {}
        total = 0

        for item in cls.ITEMS:
            value = answers.get(item)
            if value is not None:
                score = cls._normalize_item_score(value)
                item_scores[item] = score
                total += score
            else:
                item_scores[item] = 0

        severity = cls._get_severity_band(total)

        return ScoreResult(
            score_type=ScoreType.GAD7,
            score_version=GAD7_VERSION,
            total_score=total,
            max_score=cls.MAX_SCORE,
            severity_band=severity,
            item_scores=item_scores,
            metadata={},
            calculated_at=datetime.now(timezone.utc),
        )

    @classmethod
    def _normalize_item_score(cls, value: Any) -> int:
        """Normalize item value to 0-3 range."""
        if isinstance(value, bool):
            return 3 if value else 0
        if isinstance(value, str):
            value = value.lower()
            mapping = {
                "not at all": 0,
                "several days": 1,
                "more than half the days": 2,
                "nearly every day": 3,
                "0": 0,
                "1": 1,
                "2": 2,
                "3": 3,
            }
            return mapping.get(value, 0)
        if isinstance(value, (int, float)):
            return max(0, min(cls.MAX_ITEM_SCORE, int(value)))
        return 0

    @classmethod
    def _get_severity_band(cls, total: int) -> SeverityBand:
        """Determine severity band from total score."""
        if total <= 4:
            return SeverityBand.MINIMAL
        elif total <= 9:
            return SeverityBand.MILD
        elif total <= 14:
            return SeverityBand.MODERATE
        else:
            return SeverityBand.SEVERE


class AUDITCScorer:
    """AUDIT-C Alcohol Screening Scorer.

    The AUDIT-C is the first 3 questions of the full AUDIT questionnaire.
    It screens for hazardous drinking or active alcohol use disorders.

    Scoring:
    - Q1 (frequency): 0-4 points
    - Q2 (typical quantity): 0-4 points
    - Q3 (binge frequency): 0-4 points
    - Total range: 0-12

    Risk thresholds (NHS UK guidelines):
    - Men: >= 5 indicates hazardous drinking
    - Women: >= 4 indicates hazardous drinking

    For simplicity, we use >= 4 as moderate risk, >= 8 as high risk.
    """

    ITEMS = [
        "auditc_q1",  # How often do you have a drink containing alcohol?
        "auditc_q2",  # How many units of alcohol do you drink on a typical day?
        "auditc_q3",  # How often do you have 6+ units on a single occasion?
    ]

    MAX_SCORE = 12
    MAX_ITEM_SCORE = 4

    @classmethod
    def calculate(cls, answers: dict[str, Any]) -> ScoreResult:
        """Calculate AUDIT-C score from questionnaire answers.

        Args:
            answers: Dict mapping question IDs to numeric responses (0-4)

        Returns:
            ScoreResult with total score, severity band, and item details
        """
        item_scores: dict[str, int] = {}
        total = 0

        for item in cls.ITEMS:
            value = answers.get(item)
            if value is not None:
                score = cls._normalize_item_score(value)
                item_scores[item] = score
                total += score
            else:
                item_scores[item] = 0

        severity = cls._get_severity_band(total)

        return ScoreResult(
            score_type=ScoreType.AUDIT_C,
            score_version=AUDIT_C_VERSION,
            total_score=total,
            max_score=cls.MAX_SCORE,
            severity_band=severity,
            item_scores=item_scores,
            metadata={
                "above_male_threshold": total >= 5,
                "above_female_threshold": total >= 4,
            },
            calculated_at=datetime.now(timezone.utc),
        )

    @classmethod
    def _normalize_item_score(cls, value: Any) -> int:
        """Normalize item value to 0-4 range."""
        if isinstance(value, str):
            value = value.lower()
            # Q1 frequency mapping
            freq_mapping = {
                "never": 0,
                "monthly or less": 1,
                "2-4 times a month": 2,
                "2-3 times a week": 3,
                "4+ times a week": 4,
            }
            if value in freq_mapping:
                return freq_mapping[value]
            # Numeric string mapping
            try:
                return max(0, min(cls.MAX_ITEM_SCORE, int(value)))
            except ValueError:
                return 0
        if isinstance(value, (int, float)):
            return max(0, min(cls.MAX_ITEM_SCORE, int(value)))
        return 0

    @classmethod
    def _get_severity_band(cls, total: int) -> SeverityBand:
        """Determine severity band from total score."""
        if total <= 2:
            return SeverityBand.MINIMAL
        elif total <= 3:
            return SeverityBand.MILD
        elif total <= 7:
            return SeverityBand.MODERATE
        else:
            return SeverityBand.SEVERE


class ScoringService:
    """Service for calculating clinical assessment scores."""

    SCORERS = {
        ScoreType.PHQ9: PHQ9Scorer,
        ScoreType.GAD7: GAD7Scorer,
        ScoreType.AUDIT_C: AUDITCScorer,
    }

    @classmethod
    def calculate_score(
        cls,
        score_type: ScoreType,
        answers: dict[str, Any],
    ) -> ScoreResult:
        """Calculate a specific score type.

        Args:
            score_type: Type of score to calculate
            answers: Questionnaire answers

        Returns:
            ScoreResult

        Raises:
            ValueError: If score type is not supported
        """
        scorer = cls.SCORERS.get(score_type)
        if not scorer:
            raise ValueError(f"Unsupported score type: {score_type}")

        return scorer.calculate(answers)

    @classmethod
    def calculate_all_applicable(
        cls,
        answers: dict[str, Any],
    ) -> list[ScoreResult]:
        """Calculate all applicable scores based on available answers.

        Args:
            answers: Questionnaire answers

        Returns:
            List of ScoreResults for each applicable assessment
        """
        results = []

        # Check for PHQ-9 items
        if any(item in answers for item in PHQ9Scorer.ITEMS):
            results.append(PHQ9Scorer.calculate(answers))

        # Check for GAD-7 items
        if any(item in answers for item in GAD7Scorer.ITEMS):
            results.append(GAD7Scorer.calculate(answers))

        # Check for AUDIT-C items
        if any(item in answers for item in AUDITCScorer.ITEMS):
            results.append(AUDITCScorer.calculate(answers))

        return results

    @classmethod
    def get_scores_for_rules_engine(
        cls,
        answers: dict[str, Any],
    ) -> dict[str, Any]:
        """Calculate scores and format for rules engine consumption.

        Returns a dict structure that matches the ruleset schema:
        {
            "scores": {
                "phq9": {"total": 15, "item9_positive": true, ...},
                "gad7": {"total": 12, ...},
                "auditc": {"total": 5, ...}
            }
        }

        Args:
            answers: Questionnaire answers

        Returns:
            Dict formatted for rules engine
        """
        scores_output: dict[str, Any] = {}

        # PHQ-9
        if any(item in answers for item in PHQ9Scorer.ITEMS):
            result = PHQ9Scorer.calculate(answers)
            scores_output["phq9"] = {
                "total": result.total_score,
                "severity": result.severity_band.value,
                "item9_positive": result.metadata.get("item9_positive", False),
                "item9_value": result.metadata.get("item9_value", 0),
            }

        # GAD-7
        if any(item in answers for item in GAD7Scorer.ITEMS):
            result = GAD7Scorer.calculate(answers)
            scores_output["gad7"] = {
                "total": result.total_score,
                "severity": result.severity_band.value,
            }

        # AUDIT-C
        if any(item in answers for item in AUDITCScorer.ITEMS):
            result = AUDITCScorer.calculate(answers)
            scores_output["auditc"] = {
                "total": result.total_score,
                "severity": result.severity_band.value,
                "above_male_threshold": result.metadata.get("above_male_threshold", False),
                "above_female_threshold": result.metadata.get("above_female_threshold", False),
            }

        return {"scores": scores_output}

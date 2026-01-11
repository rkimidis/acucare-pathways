"""Unit tests for clinical scoring algorithms."""

import pytest

from app.models.score import ScoreType, SeverityBand
from app.services.scoring import (
    AUDITCScorer,
    GAD7Scorer,
    PHQ9Scorer,
    ScoringService,
)


class TestPHQ9Scoring:
    """Tests for PHQ-9 depression screening scorer."""

    def test_minimal_score(self) -> None:
        """Test minimal/no depression (0-4)."""
        answers = {
            "phq9_q1": 0,
            "phq9_q2": 0,
            "phq9_q3": 1,
            "phq9_q4": 0,
            "phq9_q5": 0,
            "phq9_q6": 0,
            "phq9_q7": 0,
            "phq9_q8": 0,
            "phq9_q9": 0,
        }
        result = PHQ9Scorer.calculate(answers)

        assert result.score_type == ScoreType.PHQ9
        assert result.total_score == 1
        assert result.max_score == 27
        assert result.severity_band == SeverityBand.MINIMAL
        assert result.metadata["item9_positive"] is False

    def test_mild_score(self) -> None:
        """Test mild depression (5-9)."""
        answers = {
            "phq9_q1": 1,
            "phq9_q2": 1,
            "phq9_q3": 1,
            "phq9_q4": 1,
            "phq9_q5": 1,
            "phq9_q6": 1,
            "phq9_q7": 0,
            "phq9_q8": 0,
            "phq9_q9": 0,
        }
        result = PHQ9Scorer.calculate(answers)

        assert result.total_score == 6
        assert result.severity_band == SeverityBand.MILD

    def test_moderate_score(self) -> None:
        """Test moderate depression (10-14)."""
        answers = {
            "phq9_q1": 2,
            "phq9_q2": 2,
            "phq9_q3": 2,
            "phq9_q4": 1,
            "phq9_q5": 1,
            "phq9_q6": 1,
            "phq9_q7": 1,
            "phq9_q8": 0,
            "phq9_q9": 0,
        }
        result = PHQ9Scorer.calculate(answers)

        assert result.total_score == 10
        assert result.severity_band == SeverityBand.MODERATE

    def test_moderately_severe_score(self) -> None:
        """Test moderately severe depression (15-19)."""
        answers = {
            "phq9_q1": 2,
            "phq9_q2": 2,
            "phq9_q3": 2,
            "phq9_q4": 2,
            "phq9_q5": 2,
            "phq9_q6": 2,
            "phq9_q7": 2,
            "phq9_q8": 1,
            "phq9_q9": 0,
        }
        result = PHQ9Scorer.calculate(answers)

        assert result.total_score == 15
        assert result.severity_band == SeverityBand.MODERATELY_SEVERE

    def test_severe_score(self) -> None:
        """Test severe depression (20-27)."""
        answers = {
            "phq9_q1": 3,
            "phq9_q2": 3,
            "phq9_q3": 3,
            "phq9_q4": 3,
            "phq9_q5": 2,
            "phq9_q6": 2,
            "phq9_q7": 2,
            "phq9_q8": 1,
            "phq9_q9": 1,
        }
        result = PHQ9Scorer.calculate(answers)

        assert result.total_score == 20
        assert result.severity_band == SeverityBand.SEVERE

    def test_item9_positive_flag(self) -> None:
        """Test that item 9 (suicidal ideation) is flagged when positive."""
        answers = {
            "phq9_q1": 1,
            "phq9_q2": 1,
            "phq9_q3": 0,
            "phq9_q4": 0,
            "phq9_q5": 0,
            "phq9_q6": 0,
            "phq9_q7": 0,
            "phq9_q8": 0,
            "phq9_q9": 1,  # "Several days" for self-harm item
        }
        result = PHQ9Scorer.calculate(answers)

        assert result.metadata["item9_positive"] is True
        assert result.metadata["item9_value"] == 1

    def test_string_input_normalization(self) -> None:
        """Test that string inputs are normalized correctly."""
        answers = {
            "phq9_q1": "not at all",
            "phq9_q2": "several days",
            "phq9_q3": "more than half the days",
            "phq9_q4": "nearly every day",
            "phq9_q5": "0",
            "phq9_q6": "1",
            "phq9_q7": "2",
            "phq9_q8": "3",
            "phq9_q9": 0,
        }
        result = PHQ9Scorer.calculate(answers)

        assert result.item_scores["phq9_q1"] == 0
        assert result.item_scores["phq9_q2"] == 1
        assert result.item_scores["phq9_q3"] == 2
        assert result.item_scores["phq9_q4"] == 3
        assert result.item_scores["phq9_q5"] == 0
        assert result.item_scores["phq9_q6"] == 1
        assert result.item_scores["phq9_q7"] == 2
        assert result.item_scores["phq9_q8"] == 3

    def test_missing_items_default_to_zero(self) -> None:
        """Test that missing items are scored as 0."""
        answers = {
            "phq9_q1": 2,
            # Other items missing
        }
        result = PHQ9Scorer.calculate(answers)

        assert result.total_score == 2
        assert result.item_scores["phq9_q2"] == 0


class TestGAD7Scoring:
    """Tests for GAD-7 anxiety screening scorer."""

    def test_minimal_score(self) -> None:
        """Test minimal anxiety (0-4)."""
        answers = {
            "gad7_q1": 0,
            "gad7_q2": 1,
            "gad7_q3": 0,
            "gad7_q4": 0,
            "gad7_q5": 0,
            "gad7_q6": 0,
            "gad7_q7": 0,
        }
        result = GAD7Scorer.calculate(answers)

        assert result.score_type == ScoreType.GAD7
        assert result.total_score == 1
        assert result.max_score == 21
        assert result.severity_band == SeverityBand.MINIMAL

    def test_mild_score(self) -> None:
        """Test mild anxiety (5-9)."""
        answers = {
            "gad7_q1": 1,
            "gad7_q2": 1,
            "gad7_q3": 1,
            "gad7_q4": 1,
            "gad7_q5": 1,
            "gad7_q6": 0,
            "gad7_q7": 0,
        }
        result = GAD7Scorer.calculate(answers)

        assert result.total_score == 5
        assert result.severity_band == SeverityBand.MILD

    def test_moderate_score(self) -> None:
        """Test moderate anxiety (10-14)."""
        answers = {
            "gad7_q1": 2,
            "gad7_q2": 2,
            "gad7_q3": 2,
            "gad7_q4": 1,
            "gad7_q5": 1,
            "gad7_q6": 1,
            "gad7_q7": 1,
        }
        result = GAD7Scorer.calculate(answers)

        assert result.total_score == 10
        assert result.severity_band == SeverityBand.MODERATE

    def test_severe_score(self) -> None:
        """Test severe anxiety (15-21)."""
        answers = {
            "gad7_q1": 3,
            "gad7_q2": 3,
            "gad7_q3": 2,
            "gad7_q4": 2,
            "gad7_q5": 2,
            "gad7_q6": 2,
            "gad7_q7": 1,
        }
        result = GAD7Scorer.calculate(answers)

        assert result.total_score == 15
        assert result.severity_band == SeverityBand.SEVERE


class TestAUDITCScoring:
    """Tests for AUDIT-C alcohol screening scorer."""

    def test_minimal_score(self) -> None:
        """Test minimal/low risk (0-2)."""
        answers = {
            "auditc_q1": 0,
            "auditc_q2": 0,
            "auditc_q3": 0,
        }
        result = AUDITCScorer.calculate(answers)

        assert result.score_type == ScoreType.AUDIT_C
        assert result.total_score == 0
        assert result.max_score == 12
        assert result.severity_band == SeverityBand.MINIMAL

    def test_mild_score(self) -> None:
        """Test mild risk (3)."""
        answers = {
            "auditc_q1": 1,
            "auditc_q2": 1,
            "auditc_q3": 1,
        }
        result = AUDITCScorer.calculate(answers)

        assert result.total_score == 3
        assert result.severity_band == SeverityBand.MILD

    def test_moderate_score_female_threshold(self) -> None:
        """Test moderate risk crossing female threshold (4)."""
        answers = {
            "auditc_q1": 2,
            "auditc_q2": 1,
            "auditc_q3": 1,
        }
        result = AUDITCScorer.calculate(answers)

        assert result.total_score == 4
        assert result.severity_band == SeverityBand.MODERATE
        assert result.metadata["above_female_threshold"] is True
        assert result.metadata["above_male_threshold"] is False

    def test_moderate_score_male_threshold(self) -> None:
        """Test moderate risk crossing male threshold (5)."""
        answers = {
            "auditc_q1": 2,
            "auditc_q2": 2,
            "auditc_q3": 1,
        }
        result = AUDITCScorer.calculate(answers)

        assert result.total_score == 5
        assert result.metadata["above_male_threshold"] is True
        assert result.metadata["above_female_threshold"] is True

    def test_severe_score(self) -> None:
        """Test severe/high risk (8+)."""
        answers = {
            "auditc_q1": 3,
            "auditc_q2": 3,
            "auditc_q3": 2,
        }
        result = AUDITCScorer.calculate(answers)

        assert result.total_score == 8
        assert result.severity_band == SeverityBand.SEVERE


class TestScoringService:
    """Tests for the main scoring service."""

    def test_calculate_specific_score(self) -> None:
        """Test calculating a specific score type."""
        answers = {"phq9_q1": 2, "phq9_q2": 2}

        result = ScoringService.calculate_score(ScoreType.PHQ9, answers)

        assert result.score_type == ScoreType.PHQ9
        assert result.total_score == 4

    def test_calculate_all_applicable(self) -> None:
        """Test calculating all applicable scores from mixed answers."""
        answers = {
            "phq9_q1": 2,
            "phq9_q2": 2,
            "gad7_q1": 1,
            "gad7_q2": 1,
            "auditc_q1": 1,
        }

        results = ScoringService.calculate_all_applicable(answers)

        score_types = {r.score_type for r in results}
        assert ScoreType.PHQ9 in score_types
        assert ScoreType.GAD7 in score_types
        assert ScoreType.AUDIT_C in score_types

    def test_get_scores_for_rules_engine(self) -> None:
        """Test formatting scores for rules engine."""
        answers = {
            "phq9_q1": 2,
            "phq9_q2": 2,
            "phq9_q9": 1,
            "gad7_q1": 2,
            "gad7_q2": 2,
        }

        output = ScoringService.get_scores_for_rules_engine(answers)

        assert "scores" in output
        assert "phq9" in output["scores"]
        assert "gad7" in output["scores"]
        assert output["scores"]["phq9"]["item9_positive"] is True
        assert output["scores"]["phq9"]["total"] == 5  # q1=2, q2=2, q9=1

    def test_unsupported_score_type_raises(self) -> None:
        """Test that unsupported score type raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported score type"):
            ScoringService.calculate_score(ScoreType.DAST10, {})

"""Unit tests for facts extraction module.

Tests the facts extraction from questionnaire responses and scores.
"""

import pytest

from app.rules.facts import (
    Facts,
    ScoreFacts,
    RiskFacts,
    DemographicFacts,
    extract_facts,
    extract_facts_from_checkin,
)


class TestScoreFacts:
    """Tests for ScoreFacts dataclass."""

    def test_default_values(self) -> None:
        """Test that ScoreFacts initializes with None values."""
        sf = ScoreFacts()
        assert sf.phq9 is None
        assert sf.gad7 is None
        assert sf.phq2 is None
        assert sf.gad2 is None
        assert sf.auditc is None


class TestRiskFacts:
    """Tests for RiskFacts dataclass."""

    def test_default_values(self) -> None:
        """Test that RiskFacts initializes with False values."""
        rf = RiskFacts()
        assert rf.suicidal_ideation is False
        assert rf.self_harm is False
        assert rf.harm_to_others is False
        assert rf.psychosis is False
        assert rf.substance_use_severe is False
        assert rf.recent_crisis is False
        assert rf.previous_inpatient is False
        assert rf.current_treatment is False


class TestDemographicFacts:
    """Tests for DemographicFacts dataclass."""

    def test_default_values(self) -> None:
        """Test that DemographicFacts initializes with default values."""
        df = DemographicFacts()
        assert df.age is None
        assert df.is_minor is False
        assert df.is_elderly is False
        assert df.pregnant is False
        assert df.has_care_plan is False
        assert df.has_gp is False


class TestExtractFactsPHQ9:
    """Tests for PHQ-9 facts extraction."""

    def test_phq9_score_extraction(self) -> None:
        """Test PHQ-9 score is extracted correctly."""
        responses = {
            "phq9": {f"phq9_{i}": 1 for i in range(1, 10)}
        }

        facts = extract_facts(responses)

        assert facts.scores.phq9 is not None
        assert facts.scores.phq9["total"] == 9
        assert facts.scores.phq9["severity"] == "mild"

    def test_phq9_item9_detection(self) -> None:
        """Test PHQ-9 item 9 suicidal ideation detection."""
        responses = {
            "phq9": {f"phq9_{i}": 0 for i in range(1, 10)}
        }
        responses["phq9"]["phq9_9"] = 2

        facts = extract_facts(responses)

        assert facts.scores.phq9["item9_positive"] is True
        assert facts.scores.phq9["item9_value"] == 2
        # Should also set risk flag
        assert facts.risk.suicidal_ideation is True

    def test_phq9_item9_zero_not_flagged(self) -> None:
        """Test PHQ-9 item 9 = 0 does not flag suicidal ideation."""
        responses = {
            "phq9": {f"phq9_{i}": 1 for i in range(1, 10)}
        }
        responses["phq9"]["phq9_9"] = 0

        facts = extract_facts(responses)

        assert facts.scores.phq9["item9_positive"] is False
        assert facts.risk.suicidal_ideation is False

    def test_phq9_severity_bands(self) -> None:
        """Test PHQ-9 severity band extraction."""
        test_cases = [
            (0, "minimal"),
            (5, "mild"),
            (10, "moderate"),
            (15, "moderately_severe"),
            (20, "severe"),
        ]

        for target_total, expected_severity in test_cases:
            responses = {"phq9": {f"phq9_{i}": 0 for i in range(1, 10)}}
            remaining = target_total
            for i in range(1, 10):
                if remaining <= 0:
                    break
                val = min(3, remaining)
                responses["phq9"][f"phq9_{i}"] = val
                remaining -= val

            facts = extract_facts(responses)
            assert facts.scores.phq9["severity"] == expected_severity


class TestExtractFactsGAD7:
    """Tests for GAD-7 facts extraction."""

    def test_gad7_score_extraction(self) -> None:
        """Test GAD-7 score is extracted correctly."""
        responses = {
            "gad7": {f"gad7_{i}": 2 for i in range(1, 8)}
        }

        facts = extract_facts(responses)

        assert facts.scores.gad7 is not None
        assert facts.scores.gad7["total"] == 14
        assert facts.scores.gad7["severity"] == "moderate"

    def test_gad7_individual_items(self) -> None:
        """Test GAD-7 individual item extraction."""
        responses = {
            "gad7": {
                "gad7_1": 1,
                "gad7_2": 2,
                "gad7_3": 0,
                "gad7_4": 3,
                "gad7_5": 1,
                "gad7_6": 2,
                "gad7_7": 0,
            }
        }

        facts = extract_facts(responses)

        assert facts.scores.gad7["nervous"] == 1
        assert facts.scores.gad7["uncontrollable_worry"] == 2


class TestExtractFactsPHQ2:
    """Tests for PHQ-2 facts extraction."""

    def test_phq2_score_extraction(self) -> None:
        """Test PHQ-2 score is extracted correctly."""
        responses = {
            "phq2": {"phq2_1": 2, "phq2_2": 2}
        }

        facts = extract_facts(responses)

        assert facts.scores.phq2 is not None
        assert facts.scores.phq2["total"] == 4
        assert facts.scores.phq2["screen_positive"] is True

    def test_phq2_below_cutoff(self) -> None:
        """Test PHQ-2 below screening cutoff."""
        responses = {
            "phq2": {"phq2_1": 1, "phq2_2": 1}
        }

        facts = extract_facts(responses)

        assert facts.scores.phq2["total"] == 2
        assert facts.scores.phq2["screen_positive"] is False


class TestExtractFactsGAD2:
    """Tests for GAD-2 facts extraction."""

    def test_gad2_score_extraction(self) -> None:
        """Test GAD-2 score is extracted correctly."""
        responses = {
            "gad2": {"gad2_1": 2, "gad2_2": 1}
        }

        facts = extract_facts(responses)

        assert facts.scores.gad2 is not None
        assert facts.scores.gad2["total"] == 3
        assert facts.scores.gad2["screen_positive"] is True

    def test_gad2_below_cutoff(self) -> None:
        """Test GAD-2 below screening cutoff."""
        responses = {
            "gad2": {"gad2_1": 1, "gad2_2": 0}
        }

        facts = extract_facts(responses)

        assert facts.scores.gad2["total"] == 1
        assert facts.scores.gad2["screen_positive"] is False


class TestExtractFactsAUDITC:
    """Tests for AUDIT-C facts extraction."""

    def test_auditc_score_extraction(self) -> None:
        """Test AUDIT-C score is extracted correctly."""
        responses = {
            "auditc": {"auditc_1": 2, "auditc_2": 1, "auditc_3": 1}
        }

        facts = extract_facts(responses)

        assert facts.scores.auditc is not None
        assert facts.scores.auditc["total"] == 4
        assert facts.scores.auditc["risk_level"] == "at_risk"
        assert facts.scores.auditc["above_male_threshold"] is True

    def test_auditc_low_risk(self) -> None:
        """Test AUDIT-C low risk score."""
        responses = {
            "auditc": {"auditc_1": 1, "auditc_2": 0, "auditc_3": 0}
        }

        facts = extract_facts(responses)

        assert facts.scores.auditc["total"] == 1
        assert facts.scores.auditc["risk_level"] == "low"
        assert facts.scores.auditc["high_risk"] is False
        assert facts.risk.substance_use_severe is False

    def test_auditc_high_risk_sets_substance_flag(self) -> None:
        """Test AUDIT-C high risk sets substance_use_severe flag."""
        responses = {
            "auditc": {"auditc_1": 3, "auditc_2": 3, "auditc_3": 2}
        }

        facts = extract_facts(responses)

        assert facts.scores.auditc["total"] == 8
        assert facts.scores.auditc["high_risk"] is True
        assert facts.scores.auditc["risk_level"] == "high_risk"
        assert facts.risk.substance_use_severe is True

    def test_auditc_with_sex_specific_threshold(self) -> None:
        """Test AUDIT-C uses sex-specific thresholds when provided."""
        responses = {
            "auditc": {"auditc_1": 1, "auditc_2": 1, "auditc_3": 1}
        }
        demographics = {"sex": "male"}

        facts = extract_facts(responses, demographics=demographics)

        # Score 3 is below male threshold (4)
        assert facts.scores.auditc["total"] == 3
        assert facts.scores.auditc["risk_level"] == "low"

    def test_auditc_female_threshold(self) -> None:
        """Test AUDIT-C uses female threshold when sex=female."""
        responses = {
            "auditc": {"auditc_1": 1, "auditc_2": 1, "auditc_3": 1}
        }
        demographics = {"sex": "female"}

        facts = extract_facts(responses, demographics=demographics)

        # Score 3 is at female threshold (3)
        assert facts.scores.auditc["total"] == 3
        assert facts.scores.auditc["risk_level"] == "at_risk"

    def test_auditc_individual_items(self) -> None:
        """Test AUDIT-C individual item extraction."""
        responses = {
            "auditc": {"auditc_1": 2, "auditc_2": 3, "auditc_3": 1}
        }

        facts = extract_facts(responses)

        assert facts.scores.auditc["frequency"] == 2
        assert facts.scores.auditc["binge_frequency"] == 1


class TestExtractFactsRisk:
    """Tests for risk facts extraction."""

    def test_risk_answers_extracted(self) -> None:
        """Test risk answers are extracted correctly."""
        responses = {}
        risk_answers = {
            "suicidal_ideation": True,
            "self_harm": True,
            "harm_to_others": False,
            "psychosis": True,
            "substance_use_severe": False,
            "recent_crisis": True,
            "previous_inpatient": False,
            "current_treatment": True,
        }

        facts = extract_facts(responses, risk_answers=risk_answers)

        assert facts.risk.suicidal_ideation is True
        assert facts.risk.self_harm is True
        assert facts.risk.harm_to_others is False
        assert facts.risk.psychosis is True
        assert facts.risk.substance_use_severe is False
        assert facts.risk.recent_crisis is True
        assert facts.risk.previous_inpatient is False
        assert facts.risk.current_treatment is True

    def test_phq9_item9_ors_with_risk_answer(self) -> None:
        """Test PHQ-9 item 9 OR's with explicit risk answer."""
        responses = {
            "phq9": {f"phq9_{i}": 0 for i in range(1, 10)}
        }
        responses["phq9"]["phq9_9"] = 1  # Item 9 positive

        # Explicit risk answer is False
        risk_answers = {"suicidal_ideation": False}

        facts = extract_facts(responses, risk_answers=risk_answers)

        # Should be True because PHQ-9 item 9 is positive
        assert facts.risk.suicidal_ideation is True

    def test_explicit_risk_takes_precedence(self) -> None:
        """Test explicit suicidal ideation risk answer is True."""
        responses = {
            "phq9": {f"phq9_{i}": 0 for i in range(1, 10)}
        }
        # PHQ-9 item 9 = 0, not positive

        risk_answers = {"suicidal_ideation": True}

        facts = extract_facts(responses, risk_answers=risk_answers)

        # Should be True because of explicit risk answer
        assert facts.risk.suicidal_ideation is True


class TestExtractFactsDemographics:
    """Tests for demographics facts extraction."""

    def test_age_extracted(self) -> None:
        """Test age is extracted correctly."""
        responses = {}
        demographics = {"age": 35}

        facts = extract_facts(responses, demographics=demographics)

        assert facts.demographics.age == 35
        assert facts.demographics.is_minor is False
        assert facts.demographics.is_elderly is False

    def test_minor_detection(self) -> None:
        """Test minor (under 18) detection."""
        responses = {}
        demographics = {"age": 16}

        facts = extract_facts(responses, demographics=demographics)

        assert facts.demographics.is_minor is True
        assert facts.demographics.is_elderly is False

    def test_elderly_detection(self) -> None:
        """Test elderly (65+) detection."""
        responses = {}
        demographics = {"age": 70}

        facts = extract_facts(responses, demographics=demographics)

        assert facts.demographics.is_minor is False
        assert facts.demographics.is_elderly is True

    def test_boundary_age_18(self) -> None:
        """Test age 18 is not minor."""
        responses = {}
        demographics = {"age": 18}

        facts = extract_facts(responses, demographics=demographics)

        assert facts.demographics.is_minor is False

    def test_boundary_age_65(self) -> None:
        """Test age 65 is elderly."""
        responses = {}
        demographics = {"age": 65}

        facts = extract_facts(responses, demographics=demographics)

        assert facts.demographics.is_elderly is True

    def test_other_demographics(self) -> None:
        """Test other demographic fields."""
        responses = {}
        demographics = {
            "pregnant": True,
            "has_care_plan": True,
            "has_gp": False,
        }

        facts = extract_facts(responses, demographics=demographics)

        assert facts.demographics.pregnant is True
        assert facts.demographics.has_care_plan is True
        assert facts.demographics.has_gp is False


class TestExtractFactsFromCheckin:
    """Tests for check-in convenience function."""

    def test_basic_checkin(self) -> None:
        """Test basic check-in extraction."""
        facts = extract_facts_from_checkin(
            phq2_q1=1,
            phq2_q2=2,
            gad2_q1=1,
            gad2_q2=1,
        )

        assert facts.scores.phq2["total"] == 3
        assert facts.scores.phq2["screen_positive"] is True
        assert facts.scores.gad2["total"] == 2
        assert facts.scores.gad2["screen_positive"] is False

    def test_checkin_with_risk(self) -> None:
        """Test check-in with risk indicators."""
        facts = extract_facts_from_checkin(
            phq2_q1=1,
            phq2_q2=1,
            gad2_q1=1,
            gad2_q2=1,
            suicidal_ideation=True,
            self_harm=True,
        )

        assert facts.risk.suicidal_ideation is True
        assert facts.risk.self_harm is True

    def test_checkin_with_wellbeing(self) -> None:
        """Test check-in with wellbeing rating."""
        facts = extract_facts_from_checkin(
            phq2_q1=0,
            phq2_q2=0,
            gad2_q1=0,
            gad2_q2=0,
            wellbeing_rating=7,
        )

        assert facts.raw_responses["wellbeing_rating"] == 7


class TestFactsToDict:
    """Tests for Facts.to_dict() method."""

    def test_to_dict_structure(self) -> None:
        """Test to_dict returns correct structure."""
        responses = {
            "phq9": {f"phq9_{i}": 1 for i in range(1, 10)},
            "gad7": {f"gad7_{i}": 1 for i in range(1, 8)},
        }
        risk_answers = {"suicidal_ideation": True}
        demographics = {"age": 35}

        facts = extract_facts(responses, risk_answers, demographics)
        facts_dict = facts.to_dict()

        assert "scores" in facts_dict
        assert "risk" in facts_dict
        assert "demographics" in facts_dict

    def test_to_dict_scores_structure(self) -> None:
        """Test scores in to_dict output."""
        responses = {
            "phq9": {f"phq9_{i}": 2 for i in range(1, 10)}
        }

        facts = extract_facts(responses)
        facts_dict = facts.to_dict()

        assert facts_dict["scores"]["phq9"]["total"] == 18
        assert facts_dict["scores"]["phq9"]["severity"] == "moderately_severe"
        assert facts_dict["scores"]["phq9"]["item9_positive"] is True

    def test_to_dict_risk_structure(self) -> None:
        """Test risk in to_dict output."""
        responses = {}
        risk_answers = {"psychosis": True, "harm_to_others": True}

        facts = extract_facts(responses, risk_answers=risk_answers)
        facts_dict = facts.to_dict()

        assert facts_dict["risk"]["psychosis"] is True
        assert facts_dict["risk"]["harm_to_others"] is True
        assert facts_dict["risk"]["self_harm"] is False

    def test_to_dict_demographics_structure(self) -> None:
        """Test demographics in to_dict output."""
        responses = {}
        demographics = {"age": 16, "pregnant": False}

        facts = extract_facts(responses, demographics=demographics)
        facts_dict = facts.to_dict()

        assert facts_dict["demographics"]["age"] == 16
        assert facts_dict["demographics"]["is_minor"] is True
        assert facts_dict["demographics"]["pregnant"] is False


class TestFactsErrorHandling:
    """Tests for facts extraction error handling."""

    def test_invalid_phq9_ignored(self) -> None:
        """Test invalid PHQ-9 responses are ignored."""
        responses = {
            "phq9": {"phq9_1": "invalid"}  # Missing other items
        }

        facts = extract_facts(responses)

        # Should not raise, but PHQ-9 score should be None
        assert facts.scores.phq9 is None

    def test_invalid_gad7_ignored(self) -> None:
        """Test invalid GAD-7 responses are ignored."""
        responses = {
            "gad7": {"gad7_1": -1}  # Invalid value
        }

        facts = extract_facts(responses)

        # Should not raise, but GAD-7 score should be None
        assert facts.scores.gad7 is None

    def test_empty_responses(self) -> None:
        """Test empty responses return default facts."""
        facts = extract_facts({})

        assert facts.scores.phq9 is None
        assert facts.scores.gad7 is None
        assert facts.scores.phq2 is None
        assert facts.scores.gad2 is None
        assert facts.risk.suicidal_ideation is False
        assert facts.demographics.age is None

    def test_raw_responses_stored(self) -> None:
        """Test raw responses are stored in facts."""
        responses = {
            "phq9": {f"phq9_{i}": 1 for i in range(1, 10)},
            "custom": {"field": "value"},
        }

        facts = extract_facts(responses)

        assert facts.raw_responses == responses

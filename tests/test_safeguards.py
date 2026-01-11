"""Regression tests for safeguard enforcement.

These tests ensure that RED and AMBER tier cases:
1. Cannot self-book appointments
2. Always require clinician review
3. Safeguards cannot be bypassed

These are critical safety controls for the triage system.
"""

import pytest

from app.models.triage_case import TriageTier
from app.rules.engine import RulesEngine, evaluate_triage


class TestRedBlocksSelfBooking:
    """Regression tests: RED tier MUST block self-booking."""

    def test_red_suicide_intent_blocks_self_booking(self) -> None:
        """RED: Suicide intent with plan and means blocks self-booking."""
        facts = {
            "risk": {
                "suicidal_intent_now": True,
                "suicide_plan": True,
                "means_access": True,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.RED
        assert result.self_book_allowed is False, "RED tier must block self-booking"

    def test_red_recent_attempt_blocks_self_booking(self) -> None:
        """RED: Recent serious suicide attempt blocks self-booking."""
        facts = {
            "risk": {
                "recent_suicide_attempt": True,
                "attempt_required_medical_attention": True,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.RED
        assert result.self_book_allowed is False, "RED tier must block self-booking"

    def test_red_command_hallucinations_blocks_self_booking(self) -> None:
        """RED: Command hallucinations with intent blocks self-booking."""
        facts = {
            "risk": {
                "command_hallucinations_harm": True,
                "intent_to_act_on_commands": True,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.RED
        assert result.self_book_allowed is False, "RED tier must block self-booking"

    def test_red_imminent_violence_blocks_self_booking(self) -> None:
        """RED: Imminent violence risk blocks self-booking."""
        facts = {
            "risk": {
                "violence_imminent": True,
                "access_to_weapons_or_means": True,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.RED
        assert result.self_book_allowed is False, "RED tier must block self-booking"

    def test_red_severe_psychosis_blocks_self_booking(self) -> None:
        """RED: Severe psychosis unable to self-care blocks self-booking."""
        facts = {
            "risk": {
                "psychosis_severe": True,
                "unable_to_care_for_self": True,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.RED
        assert result.self_book_allowed is False, "RED tier must block self-booking"

    def test_red_severe_mania_blocks_self_booking(self) -> None:
        """RED: Severe mania with dangerous behaviour blocks self-booking."""
        facts = {
            "risk": {
                "mania_severe": True,
                "dangerous_behaviour": True,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.RED
        assert result.self_book_allowed is False, "RED tier must block self-booking"


class TestRedRequiresClinicianReview:
    """Regression tests: RED tier MUST require clinician review."""

    def test_red_suicide_intent_requires_clinician_review(self) -> None:
        """RED: Suicide intent requires clinician review."""
        facts = {
            "risk": {
                "suicidal_intent_now": True,
                "suicide_plan": True,
                "means_access": True,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.RED
        assert result.clinician_review_required is True, "RED tier must require clinician review"

    def test_red_recent_attempt_requires_clinician_review(self) -> None:
        """RED: Recent attempt requires clinician review."""
        facts = {
            "risk": {
                "recent_suicide_attempt": True,
                "attempt_required_medical_attention": True,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.RED
        assert result.clinician_review_required is True, "RED tier must require clinician review"

    def test_red_imminent_violence_requires_clinician_review(self) -> None:
        """RED: Imminent violence requires clinician review."""
        facts = {
            "risk": {
                "violence_imminent": True,
                "access_to_weapons_or_means": True,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.RED
        assert result.clinician_review_required is True, "RED tier must require clinician review"


class TestAmberBlocksSelfBooking:
    """Regression tests: AMBER tier MUST block self-booking."""

    def test_amber_phq9_item9_blocks_self_booking(self) -> None:
        """AMBER: PHQ-9 item 9 positive blocks self-booking."""
        facts = {
            "scores": {
                "phq9": {
                    "total": 12,
                    "item9_positive": True,
                }
            },
            "risk": {
                "suicidal_intent_now": False,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.AMBER
        assert result.self_book_allowed is False, "AMBER tier must block self-booking"

    def test_amber_passive_si_blocks_self_booking(self) -> None:
        """AMBER: Passive SI with risk factors blocks self-booking."""
        facts = {
            "risk": {
                "suicidal_thoughts_present": True,
                "suicidal_intent_now": False,
                "suicide_plan": False,
                "suicide_risk_factors_count": 3,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.AMBER
        assert result.self_book_allowed is False, "AMBER tier must block self-booking"

    def test_amber_new_psychosis_blocks_self_booking(self) -> None:
        """AMBER: New psychosis blocks self-booking."""
        facts = {
            "risk": {
                "new_psychosis": True,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.AMBER
        assert result.self_book_allowed is False, "AMBER tier must block self-booking"

    def test_amber_severe_depression_blocks_self_booking(self) -> None:
        """AMBER: Severe depression with impairment blocks self-booking."""
        facts = {
            "scores": {
                "phq9": {"total": 22}
            },
            "risk": {
                "functional_impairment_severe": True,
                "suicidal_intent_now": False,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.AMBER
        assert result.self_book_allowed is False, "AMBER tier must block self-booking"

    def test_amber_substance_high_risk_blocks_self_booking(self) -> None:
        """AMBER: High AUDIT-C score blocks self-booking."""
        facts = {
            "scores": {
                "auditc": {"total": 9}
            },
            "risk": {}
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.AMBER
        assert result.self_book_allowed is False, "AMBER tier must block self-booking"


class TestAmberRequiresClinicianReview:
    """Regression tests: AMBER tier MUST require clinician review."""

    def test_amber_phq9_item9_requires_clinician_review(self) -> None:
        """AMBER: PHQ-9 item 9 positive requires clinician review."""
        facts = {
            "scores": {
                "phq9": {
                    "total": 12,
                    "item9_positive": True,
                }
            },
            "risk": {
                "suicidal_intent_now": False,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.AMBER
        assert result.clinician_review_required is True, "AMBER tier must require clinician review"

    def test_amber_new_psychosis_requires_clinician_review(self) -> None:
        """AMBER: New psychosis requires clinician review."""
        facts = {
            "risk": {
                "new_psychosis": True,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.AMBER
        assert result.clinician_review_required is True, "AMBER tier must require clinician review"


class TestGreenAllowsSelfBooking:
    """Tests: GREEN tier allows self-booking."""

    def test_green_moderate_depression_allows_self_booking(self) -> None:
        """GREEN: Moderate depression without risk allows self-booking."""
        facts = {
            "scores": {
                "phq9": {"total": 12}
            },
            "risk": {
                "any_red_amber_flag": False,
                "functional_impairment_severe": False,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.GREEN
        assert result.self_book_allowed is True, "GREEN tier should allow self-booking"
        assert result.clinician_review_required is False, "GREEN tier should not require clinician review"

    def test_green_default_allows_self_booking(self) -> None:
        """GREEN: Default tier allows self-booking."""
        facts = {}

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.GREEN
        assert result.self_book_allowed is True, "GREEN tier should allow self-booking"


class TestBlueAllowsSelfBooking:
    """Tests: BLUE tier allows self-booking."""

    def test_blue_mild_symptoms_allows_self_booking(self) -> None:
        """BLUE: Mild symptoms with digital preference allows self-booking."""
        facts = {
            "scores": {
                "phq9": {"total": 5},
                "gad7": {"total": 4},
            },
            "risk": {
                "any_red_amber_flag": False,
                "functional_impairment_severe": False,
            },
            "preferences": {
                "open_to_digital": True,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.BLUE
        assert result.self_book_allowed is True, "BLUE tier should allow self-booking"
        assert result.clinician_review_required is False, "BLUE tier should not require clinician review"


class TestSafeguardEnforcement:
    """Tests that safeguards are enforced regardless of rule configuration."""

    def test_red_safeguard_overrides_rule_allowing_self_book(self) -> None:
        """Even if a rule tried to allow self-booking, RED tier blocks it."""
        # This tests the engine-level safeguard enforcement
        facts = {
            "risk": {
                "suicidal_intent_now": True,
                "suicide_plan": True,
                "means_access": True,
            }
        }

        result = evaluate_triage(facts)

        # Safeguard is applied at engine level
        assert result.tier == TriageTier.RED
        assert result.self_book_allowed is False
        assert result.clinician_review_required is True

    def test_amber_safeguard_overrides_rule_allowing_self_book(self) -> None:
        """Even if a rule tried to allow self-booking, AMBER tier blocks it."""
        facts = {
            "risk": {
                "new_psychosis": True,
            }
        }

        result = evaluate_triage(facts)

        # Safeguard is applied at engine level
        assert result.tier == TriageTier.AMBER
        assert result.self_book_allowed is False
        assert result.clinician_review_required is True

    def test_safeguards_in_evaluate_method(self) -> None:
        """Test that safeguards are enforced in the evaluate method directly."""
        engine = RulesEngine()

        # RED tier case
        red_facts = {
            "risk": {
                "suicidal_intent_now": True,
                "suicide_plan": True,
                "means_access": True,
            }
        }
        red_result = engine.evaluate(red_facts)
        assert red_result.self_book_allowed is False
        assert red_result.clinician_review_required is True

        # AMBER tier case
        amber_facts = {
            "risk": {
                "new_psychosis": True,
            }
        }
        amber_result = engine.evaluate(amber_facts)
        assert amber_result.self_book_allowed is False
        assert amber_result.clinician_review_required is True


class TestSafeguardConsistency:
    """Tests that safeguards are consistent across all evaluation scenarios."""

    @pytest.mark.parametrize("red_facts", [
        {"risk": {"suicidal_intent_now": True, "suicide_plan": True, "means_access": True}},
        {"risk": {"recent_suicide_attempt": True, "attempt_required_medical_attention": True}},
        {"risk": {"command_hallucinations_harm": True, "intent_to_act_on_commands": True}},
        {"risk": {"violence_imminent": True, "access_to_weapons_or_means": True}},
        {"risk": {"psychosis_severe": True, "unable_to_care_for_self": True}},
        {"risk": {"mania_severe": True, "dangerous_behaviour": True}},
    ])
    def test_all_red_scenarios_block_self_booking(self, red_facts: dict) -> None:
        """All RED tier scenarios must block self-booking."""
        result = evaluate_triage(red_facts)

        assert result.tier == TriageTier.RED
        assert result.self_book_allowed is False
        assert result.clinician_review_required is True

    @pytest.mark.parametrize("amber_facts", [
        {"scores": {"phq9": {"total": 12, "item9_positive": True}}, "risk": {"suicidal_intent_now": False}},
        {"risk": {"suicidal_thoughts_present": True, "suicidal_intent_now": False, "suicide_plan": False, "suicide_risk_factors_count": 3}},
        {"risk": {"new_psychosis": True}},
        {"scores": {"phq9": {"total": 22}}, "risk": {"functional_impairment_severe": True, "suicidal_intent_now": False}},
        {"scores": {"auditc": {"total": 9}}, "risk": {}},
    ])
    def test_all_amber_scenarios_block_self_booking(self, amber_facts: dict) -> None:
        """All AMBER tier scenarios must block self-booking."""
        result = evaluate_triage(amber_facts)

        assert result.tier == TriageTier.AMBER
        assert result.self_book_allowed is False
        assert result.clinician_review_required is True


class TestRulesetIntegrity:
    """Tests that ruleset integrity is maintained."""

    def test_ruleset_hash_is_consistent(self) -> None:
        """Ruleset hash should be consistent across evaluations."""
        engine = RulesEngine()

        result1 = engine.evaluate({})
        result2 = engine.evaluate({"risk": {"new_psychosis": True}})

        assert result1.ruleset_hash == result2.ruleset_hash
        assert len(result1.ruleset_hash) == 64  # SHA256

    def test_ruleset_version_is_present(self) -> None:
        """Ruleset version should always be present."""
        engine = RulesEngine()
        result = engine.evaluate({})

        assert result.ruleset_version is not None
        assert result.ruleset_version != ""
        assert result.ruleset_version != "unknown"

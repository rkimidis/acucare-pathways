"""Golden tests for rules engine evaluation."""

import pytest

from app.models.triage_case import TriageTier
from app.rules.engine import RulesEngine, evaluate_triage


class TestRulesEngineBasics:
    """Basic tests for rules engine functionality."""

    def test_engine_loads_ruleset(self) -> None:
        """Test that engine loads ruleset successfully."""
        engine = RulesEngine()
        engine.load_ruleset()

        assert engine.ruleset is not None
        assert engine.ruleset_hash is not None
        assert len(engine.ruleset_hash) == 64  # SHA256 hex

    def test_engine_returns_version(self) -> None:
        """Test that engine returns ruleset version."""
        engine = RulesEngine()

        assert engine.ruleset_version is not None
        assert engine.ruleset_version == "1.0.0"

    def test_default_tier_is_green(self) -> None:
        """Test that default tier without matching rules is GREEN."""
        engine = RulesEngine()

        # Empty facts should result in GREEN default
        result = engine.evaluate({})

        assert result.tier == TriageTier.GREEN
        assert result.pathway == "THERAPY_ASSESSMENT"
        assert result.self_book_allowed is True


class TestRedTierRules:
    """Golden tests for RED tier rule evaluation."""

    def test_red_suicide_intent_plan_means(self) -> None:
        """Test RED tier for suicide intent with plan and means."""
        facts = {
            "risk": {
                "suicidal_intent_now": True,
                "suicide_plan": True,
                "means_access": True,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.RED
        assert result.pathway == "CRISIS_ESCALATION"
        assert result.self_book_allowed is False
        assert result.clinician_review_required is True
        assert "RED_SUICIDE_INTENT_PLAN_MEANS" in result.rules_fired

    def test_red_recent_serious_attempt(self) -> None:
        """Test RED tier for recent serious suicide attempt."""
        facts = {
            "risk": {
                "recent_suicide_attempt": True,
                "attempt_required_medical_attention": True,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.RED
        assert result.clinician_review_required is True
        assert result.self_book_allowed is False
        assert "RED_RECENT_SERIOUS_ATTEMPT" in result.rules_fired

    def test_red_command_hallucinations(self) -> None:
        """Test RED tier for command hallucinations with intent to act."""
        facts = {
            "risk": {
                "command_hallucinations_harm": True,
                "intent_to_act_on_commands": True,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.RED
        assert "RED_COMMAND_HALLUCINATIONS_HARM" in result.rules_fired

    def test_red_imminent_violence(self) -> None:
        """Test RED tier for imminent violence risk."""
        facts = {
            "risk": {
                "violence_imminent": True,
                "access_to_weapons_or_means": True,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.RED
        assert "RED_IMMINENT_VIOLENCE_RISK" in result.rules_fired

    def test_red_severe_psychosis(self) -> None:
        """Test RED tier for severe psychosis unable to self-care."""
        facts = {
            "risk": {
                "psychosis_severe": True,
                "unable_to_care_for_self": True,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.RED
        assert "RED_SEVERE_PSYCHOSIS_UNABLE_SELFCARE" in result.rules_fired

    def test_red_severe_mania(self) -> None:
        """Test RED tier for severe mania with dangerous behaviour."""
        facts = {
            "risk": {
                "mania_severe": True,
                "dangerous_behaviour": True,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.RED
        assert "RED_SEVERE_MANIA_DANGEROUS" in result.rules_fired


class TestAmberTierRules:
    """Golden tests for AMBER tier rule evaluation."""

    def test_amber_phq9_item9_positive(self) -> None:
        """Test AMBER tier for PHQ-9 item 9 positive with moderate depression."""
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
        assert result.self_book_allowed is False
        assert result.clinician_review_required is True
        assert "AMBER_PHQ9_ITEM9_POSITIVE_MODERATE_OR_HIGH" in result.rules_fired

    def test_amber_passive_si_with_risk_factors(self) -> None:
        """Test AMBER tier for passive SI with multiple risk factors."""
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
        assert "AMBER_PASSIVE_SI_WITH_RISK_FACTORS" in result.rules_fired

    def test_amber_new_psychosis(self) -> None:
        """Test AMBER tier for new psychosis."""
        facts = {
            "risk": {
                "new_psychosis": True,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.AMBER
        assert result.pathway == "PSYCHIATRY_ASSESSMENT"
        assert "AMBER_NEW_PSYCHOSIS" in result.rules_fired

    def test_amber_severe_depression_impairment(self) -> None:
        """Test AMBER tier for severe depression with functional impairment."""
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
        assert "AMBER_SEVERE_DEPRESSION_FUNCTIONAL_IMPAIRMENT" in result.rules_fired

    def test_amber_substance_high_risk(self) -> None:
        """Test AMBER tier for high AUDIT-C score."""
        facts = {
            "scores": {
                "auditc": {"total": 9}
            },
            "risk": {}
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.AMBER
        assert result.pathway == "SUBSTANCE_PATHWAY"
        assert "AMBER_SUBSTANCE_WITHDRAWAL_OR_HIGH_RISK" in result.rules_fired


class TestGreenTierRules:
    """Golden tests for GREEN tier rule evaluation."""

    def test_green_moderate_depression(self) -> None:
        """Test GREEN tier for moderate depression without acute risk."""
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
        assert result.pathway == "THERAPY_ASSESSMENT"
        assert result.self_book_allowed is True
        assert result.clinician_review_required is False

    def test_green_trauma_primary(self) -> None:
        """Test GREEN tier for trauma presentation."""
        facts = {
            "risk": {
                "any_red_amber_flag": False,
                "dissociation_severe": False,
            },
            "presentation": {
                "trauma_primary": True,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.GREEN
        assert result.pathway == "TRAUMA_THERAPY_PATHWAY"
        assert "GREEN_TRAUMA_PRESENT_ROUTE_TRAUMA_PATHWAY" in result.rules_fired

    def test_green_neurodevelopmental(self) -> None:
        """Test GREEN tier for neurodevelopmental request."""
        facts = {
            "risk": {
                "any_red_amber_flag": False,
            },
            "presentation": {
                "neurodevelopmental_primary": True,
            }
        }

        result = evaluate_triage(facts)

        assert result.tier == TriageTier.GREEN
        assert result.pathway == "NEURODEVELOPMENTAL_TRIAGE"
        assert "GREEN_NEURODEVELOPMENTAL_REQUEST_LOW_RISK" in result.rules_fired


class TestBlueTierRules:
    """Golden tests for BLUE tier rule evaluation."""

    def test_blue_mild_symptoms_digital_preference(self) -> None:
        """Test BLUE tier for mild symptoms with digital preference."""
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
        assert result.pathway == "LOW_INTENSITY_DIGITAL"
        assert result.self_book_allowed is True
        assert "BLUE_MILD_SYMPTOMS_LOW_IMPAIRMENT_DIGITAL" in result.rules_fired


class TestRulePriorityOrder:
    """Tests for rule priority ordering."""

    def test_red_takes_priority_over_amber(self) -> None:
        """Test that RED rules take priority over AMBER rules."""
        facts = {
            "risk": {
                "suicidal_intent_now": True,
                "suicide_plan": True,
                "means_access": True,
                "new_psychosis": True,  # Would trigger AMBER
            }
        }

        result = evaluate_triage(facts)

        # RED should win
        assert result.tier == TriageTier.RED
        assert result.rules_fired[0] == "RED_SUICIDE_INTENT_PLAN_MEANS"

    def test_amber_takes_priority_over_green(self) -> None:
        """Test that AMBER rules take priority over GREEN rules."""
        facts = {
            "risk": {
                "new_psychosis": True,
                "any_red_amber_flag": False,  # Would allow GREEN
            },
            "presentation": {
                "trauma_primary": True,  # Would trigger GREEN
            }
        }

        result = evaluate_triage(facts)

        # AMBER should win (lower priority number)
        assert result.tier == TriageTier.AMBER


class TestSafeguards:
    """Tests for safeguard enforcement."""

    def test_red_enforces_clinician_review(self) -> None:
        """Test that RED tier always requires clinician review."""
        facts = {
            "risk": {
                "suicidal_intent_now": True,
                "suicide_plan": True,
                "means_access": True,
            }
        }

        result = evaluate_triage(facts)

        assert result.clinician_review_required is True

    def test_amber_enforces_clinician_review(self) -> None:
        """Test that AMBER tier always requires clinician review."""
        facts = {
            "risk": {
                "new_psychosis": True,
            }
        }

        result = evaluate_triage(facts)

        assert result.clinician_review_required is True

    def test_green_does_not_require_clinician_review(self) -> None:
        """Test that GREEN tier does not require clinician review."""
        facts = {
            "risk": {
                "any_red_amber_flag": False,
            }
        }

        result = evaluate_triage(facts)

        assert result.clinician_review_required is False

    def test_red_disables_self_booking(self) -> None:
        """Test that RED tier disables self-booking."""
        facts = {
            "risk": {
                "suicidal_intent_now": True,
                "suicide_plan": True,
                "means_access": True,
            }
        }

        result = evaluate_triage(facts)

        assert result.self_book_allowed is False

    def test_amber_disables_self_booking(self) -> None:
        """Test that AMBER tier disables self-booking."""
        facts = {
            "risk": {
                "new_psychosis": True,
            }
        }

        result = evaluate_triage(facts)

        assert result.self_book_allowed is False


class TestEvaluationOutput:
    """Tests for evaluation output structure."""

    def test_result_includes_rules_fired(self) -> None:
        """Test that result includes list of fired rules."""
        facts = {
            "risk": {
                "new_psychosis": True,
            }
        }

        result = evaluate_triage(facts)

        assert isinstance(result.rules_fired, list)
        assert len(result.rules_fired) > 0

    def test_result_includes_explanations(self) -> None:
        """Test that result includes explanations."""
        facts = {
            "risk": {
                "new_psychosis": True,
            }
        }

        result = evaluate_triage(facts)

        assert isinstance(result.explanations, list)
        assert len(result.explanations) > 0
        assert "psychotic" in result.explanations[0].lower()

    def test_result_includes_ruleset_metadata(self) -> None:
        """Test that result includes ruleset version and hash."""
        facts = {}

        result = evaluate_triage(facts)

        assert result.ruleset_version is not None
        assert result.ruleset_hash is not None
        assert len(result.ruleset_hash) == 64

    def test_result_includes_evaluation_context(self) -> None:
        """Test that result includes evaluation context."""
        facts = {"risk": {}}

        result = evaluate_triage(facts)

        assert "total_rules_evaluated" in result.evaluation_context
        assert "matches_found" in result.evaluation_context
        assert "evaluation_mode" in result.evaluation_context


class TestConditionOperators:
    """Tests for condition operator evaluation."""

    def test_equals_operator(self) -> None:
        """Test == operator."""
        engine = RulesEngine()
        condition = {"fact": "risk.test", "op": "==", "value": True}

        assert engine._evaluate_single_condition(condition, {"risk": {"test": True}}) is True
        assert engine._evaluate_single_condition(condition, {"risk": {"test": False}}) is False

    def test_not_equals_operator(self) -> None:
        """Test != operator."""
        engine = RulesEngine()
        condition = {"fact": "risk.test", "op": "!=", "value": True}

        assert engine._evaluate_single_condition(condition, {"risk": {"test": False}}) is True
        assert engine._evaluate_single_condition(condition, {"risk": {"test": True}}) is False

    def test_greater_than_operator(self) -> None:
        """Test > operator."""
        engine = RulesEngine()
        condition = {"fact": "scores.phq9.total", "op": ">", "value": 10}

        assert engine._evaluate_single_condition(condition, {"scores": {"phq9": {"total": 15}}}) is True
        assert engine._evaluate_single_condition(condition, {"scores": {"phq9": {"total": 10}}}) is False

    def test_greater_than_or_equal_operator(self) -> None:
        """Test >= operator."""
        engine = RulesEngine()
        condition = {"fact": "scores.phq9.total", "op": ">=", "value": 10}

        assert engine._evaluate_single_condition(condition, {"scores": {"phq9": {"total": 10}}}) is True
        assert engine._evaluate_single_condition(condition, {"scores": {"phq9": {"total": 9}}}) is False

    def test_less_than_operator(self) -> None:
        """Test < operator."""
        engine = RulesEngine()
        condition = {"fact": "scores.phq9.total", "op": "<", "value": 10}

        assert engine._evaluate_single_condition(condition, {"scores": {"phq9": {"total": 5}}}) is True
        assert engine._evaluate_single_condition(condition, {"scores": {"phq9": {"total": 10}}}) is False

    def test_nested_fact_path(self) -> None:
        """Test dot-notation fact path resolution."""
        engine = RulesEngine()
        condition = {"fact": "scores.phq9.item9_positive", "op": "==", "value": True}

        facts = {"scores": {"phq9": {"item9_positive": True}}}
        assert engine._evaluate_single_condition(condition, facts) is True

    def test_missing_fact_returns_false(self) -> None:
        """Test that missing facts return False (unless checking for None)."""
        engine = RulesEngine()
        condition = {"fact": "nonexistent.path", "op": "==", "value": True}

        assert engine._evaluate_single_condition(condition, {}) is False

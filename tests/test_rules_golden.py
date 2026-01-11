"""Golden tests for rules engine evaluation.

These tests verify that specific clinical scenarios trigger the correct
triage tier and pathway. They serve as a regression safety net and
documentation of expected behavior.
"""

import pytest

from app.rules.engine import evaluate_ruleset
from app.rules.loader import load_ruleset


# Load ruleset once for all tests
@pytest.fixture(scope="module")
def ruleset():
    """Load the UK private triage ruleset."""
    ruleset_data, ruleset_hash = load_ruleset("uk-private-triage-v1.0.0.yaml")
    return ruleset_data, ruleset_hash


class TestRedTierGolden:
    """Golden tests for RED tier (crisis/immediate risk)."""

    def test_red_suicide_intent_plan_means_triggers_red(self, ruleset):
        """Active suicidal intent with plan and means = RED CRISIS."""
        ruleset_data, ruleset_hash = ruleset
        facts = {
            "risk.suicidal_intent_now": True,
            "risk.suicide_plan": True,
            "risk.means_access": True,
            "scores.phq9.item9_positive": True,
            "scores.phq9.total": 18,
            "risk.any_red_amber_flag": True,
        }

        decision = evaluate_ruleset(ruleset_data, facts, ruleset_hash)

        assert decision.tier == "RED"
        assert decision.pathway == "CRISIS_ESCALATION"
        assert "RED_SUICIDE_INTENT_PLAN_MEANS" in decision.rules_fired
        assert "Active suicidal intent" in decision.explanations[0]

    def test_red_recent_serious_attempt(self, ruleset):
        """Recent suicide attempt with medical attention = RED."""
        ruleset_data, ruleset_hash = ruleset
        facts = {
            "risk.recent_suicide_attempt": True,
            "risk.attempt_required_medical_attention": True,
        }

        decision = evaluate_ruleset(ruleset_data, facts, ruleset_hash)

        assert decision.tier == "RED"
        assert decision.pathway == "CRISIS_ESCALATION"
        assert "RED_RECENT_SERIOUS_ATTEMPT" in decision.rules_fired

    def test_red_command_hallucinations_harm(self, ruleset):
        """Command hallucinations with intent to act = RED."""
        ruleset_data, ruleset_hash = ruleset
        facts = {
            "risk.command_hallucinations_harm": True,
            "risk.intent_to_act_on_commands": True,
        }

        decision = evaluate_ruleset(ruleset_data, facts, ruleset_hash)

        assert decision.tier == "RED"
        assert "RED_COMMAND_HALLUCINATIONS_HARM" in decision.rules_fired

    def test_red_imminent_violence_risk(self, ruleset):
        """Imminent violence with access to means = RED."""
        ruleset_data, ruleset_hash = ruleset
        facts = {
            "risk.violence_imminent": True,
            "risk.access_to_weapons_or_means": True,
        }

        decision = evaluate_ruleset(ruleset_data, facts, ruleset_hash)

        assert decision.tier == "RED"
        assert "RED_IMMINENT_VIOLENCE_RISK" in decision.rules_fired

    def test_red_severe_psychosis_unable_selfcare(self, ruleset):
        """Severe psychosis with inability to self-care = RED."""
        ruleset_data, ruleset_hash = ruleset
        facts = {
            "risk.psychosis_severe": True,
            "risk.unable_to_care_for_self": True,
        }

        decision = evaluate_ruleset(ruleset_data, facts, ruleset_hash)

        assert decision.tier == "RED"
        assert "RED_SEVERE_PSYCHOSIS_UNABLE_SELFCARE" in decision.rules_fired

    def test_red_severe_mania_dangerous(self, ruleset):
        """Severe mania with dangerous behaviour = RED."""
        ruleset_data, ruleset_hash = ruleset
        facts = {
            "risk.mania_severe": True,
            "risk.dangerous_behaviour": True,
        }

        decision = evaluate_ruleset(ruleset_data, facts, ruleset_hash)

        assert decision.tier == "RED"
        assert "RED_SEVERE_MANIA_DANGEROUS" in decision.rules_fired


class TestAmberTierGolden:
    """Golden tests for AMBER tier (significant risk/complexity)."""

    def test_amber_item9_positive_moderate_triggers_amber(self, ruleset):
        """PHQ-9 item 9 positive with moderate depression = AMBER."""
        ruleset_data, ruleset_hash = ruleset
        facts = {
            "risk.suicidal_intent_now": False,
            "risk.suicide_plan": False,
            "risk.means_access": False,
            "scores.phq9.item9_positive": True,
            "scores.phq9.total": 12,
            "risk.any_red_amber_flag": True,
        }

        decision = evaluate_ruleset(ruleset_data, facts, ruleset_hash)

        assert decision.tier == "AMBER"
        assert decision.pathway == "DUTY_CLINICIAN_REVIEW"
        assert "AMBER_PHQ9_ITEM9_POSITIVE_MODERATE_OR_HIGH" in decision.rules_fired

    def test_amber_passive_si_with_risk_factors(self, ruleset):
        """Passive SI with multiple risk factors = AMBER."""
        ruleset_data, ruleset_hash = ruleset
        facts = {
            "risk.suicidal_thoughts_present": True,
            "risk.suicidal_intent_now": False,
            "risk.suicide_plan": False,
            "risk.suicide_risk_factors_count": 3,
        }

        decision = evaluate_ruleset(ruleset_data, facts, ruleset_hash)

        assert decision.tier == "AMBER"
        assert "AMBER_PASSIVE_SI_WITH_RISK_FACTORS" in decision.rules_fired

    def test_amber_new_psychosis(self, ruleset):
        """New psychotic symptoms = AMBER psychiatry."""
        ruleset_data, ruleset_hash = ruleset
        facts = {
            "risk.new_psychosis": True,
        }

        decision = evaluate_ruleset(ruleset_data, facts, ruleset_hash)

        assert decision.tier == "AMBER"
        assert decision.pathway == "PSYCHIATRY_ASSESSMENT"
        assert "AMBER_NEW_PSYCHOSIS" in decision.rules_fired

    def test_amber_severe_depression_functional_impairment(self, ruleset):
        """Severe depression with functional impairment = AMBER."""
        ruleset_data, ruleset_hash = ruleset
        facts = {
            "scores.phq9.total": 22,
            "risk.functional_impairment_severe": True,
            "risk.suicidal_intent_now": False,
        }

        decision = evaluate_ruleset(ruleset_data, facts, ruleset_hash)

        assert decision.tier == "AMBER"
        assert "AMBER_SEVERE_DEPRESSION_FUNCTIONAL_IMPAIRMENT" in decision.rules_fired

    def test_amber_substance_high_risk(self, ruleset):
        """High AUDIT-C score = AMBER substance pathway."""
        ruleset_data, ruleset_hash = ruleset
        facts = {
            "scores.auditc.total": 9,
        }

        decision = evaluate_ruleset(ruleset_data, facts, ruleset_hash)

        assert decision.tier == "AMBER"
        assert decision.pathway == "SUBSTANCE_PATHWAY"
        assert "AMBER_SUBSTANCE_WITHDRAWAL_OR_HIGH_RISK" in decision.rules_fired

    def test_amber_bipolar_mania_flags(self, ruleset):
        """Mania red flags = AMBER psychiatry."""
        ruleset_data, ruleset_hash = ruleset
        facts = {
            "risk.mania_red_flag": True,
        }

        decision = evaluate_ruleset(ruleset_data, facts, ruleset_hash)

        assert decision.tier == "AMBER"
        assert decision.pathway == "PSYCHIATRY_ASSESSMENT"
        assert "AMBER_BIPOLAR_OR_MANIA_FLAGS" in decision.rules_fired


class TestGreenTierGolden:
    """Golden tests for GREEN tier (routine care)."""

    def test_green_low_risk_routes_to_therapy(self, ruleset):
        """Low risk with mild/moderate symptoms = GREEN therapy."""
        ruleset_data, ruleset_hash = ruleset
        facts = {
            "risk.any_red_amber_flag": False,
            "scores.phq9.total": 12,
            "scores.gad7.total": 9,
            "risk.suicidal_intent_now": False,
            "risk.new_psychosis": False,
            "risk.mania_red_flag": False,
            "risk.functional_impairment_severe": False,
        }

        decision = evaluate_ruleset(ruleset_data, facts, ruleset_hash)

        assert decision.tier == "GREEN"
        assert decision.pathway == "THERAPY_ASSESSMENT"
        assert decision.self_book_allowed is True

    def test_green_trauma_primary(self, ruleset):
        """Trauma primary without risk = GREEN trauma pathway."""
        ruleset_data, ruleset_hash = ruleset
        facts = {
            "risk.any_red_amber_flag": False,
            "presentation.trauma_primary": True,
            "risk.dissociation_severe": False,
        }

        decision = evaluate_ruleset(ruleset_data, facts, ruleset_hash)

        assert decision.tier == "GREEN"
        assert decision.pathway == "TRAUMA_THERAPY_PATHWAY"
        assert "GREEN_TRAUMA_PRESENT_ROUTE_TRAUMA_PATHWAY" in decision.rules_fired

    def test_green_neurodevelopmental_request(self, ruleset):
        """ND assessment request without risk = GREEN ND triage."""
        ruleset_data, ruleset_hash = ruleset
        facts = {
            "risk.any_red_amber_flag": False,
            "presentation.neurodevelopmental_primary": True,
        }

        decision = evaluate_ruleset(ruleset_data, facts, ruleset_hash)

        assert decision.tier == "GREEN"
        assert decision.pathway == "NEURODEVELOPMENTAL_TRIAGE"
        assert "GREEN_NEURODEVELOPMENTAL_REQUEST_LOW_RISK" in decision.rules_fired


class TestBlueTierGolden:
    """Golden tests for BLUE tier (low intensity/digital)."""

    def test_blue_mild_symptoms_digital_preference(self, ruleset):
        """Mild symptoms with digital preference = BLUE digital."""
        ruleset_data, ruleset_hash = ruleset
        facts = {
            "risk.any_red_amber_flag": False,
            "scores.phq9.total": 5,
            "scores.gad7.total": 4,
            "risk.functional_impairment_severe": False,
            "preferences.open_to_digital": True,
        }

        decision = evaluate_ruleset(ruleset_data, facts, ruleset_hash)

        assert decision.tier == "BLUE"
        assert decision.pathway == "LOW_INTENSITY_DIGITAL"
        assert decision.self_book_allowed is True
        assert "BLUE_MILD_SYMPTOMS_LOW_IMPAIRMENT_DIGITAL" in decision.rules_fired


class TestRulePriorityGolden:
    """Golden tests for rule priority (first match wins)."""

    def test_red_takes_priority_over_amber(self, ruleset):
        """RED rule wins when both RED and AMBER would match."""
        ruleset_data, ruleset_hash = ruleset
        facts = {
            # RED trigger
            "risk.suicidal_intent_now": True,
            "risk.suicide_plan": True,
            "risk.means_access": True,
            # AMBER trigger (would match if RED didn't)
            "risk.new_psychosis": True,
        }

        decision = evaluate_ruleset(ruleset_data, facts, ruleset_hash)

        assert decision.tier == "RED"
        assert decision.rules_fired[0] == "RED_SUICIDE_INTENT_PLAN_MEANS"

    def test_amber_takes_priority_over_green(self, ruleset):
        """AMBER rule wins when both AMBER and GREEN would match."""
        ruleset_data, ruleset_hash = ruleset
        facts = {
            # AMBER trigger
            "risk.new_psychosis": True,
            # GREEN would match without the above
            "risk.any_red_amber_flag": False,
            "presentation.trauma_primary": True,
            "risk.dissociation_severe": False,
        }

        decision = evaluate_ruleset(ruleset_data, facts, ruleset_hash)

        # AMBER has lower priority number, so wins
        assert decision.tier == "AMBER"


class TestSafeguardsGolden:
    """Golden tests for built-in safeguards."""

    def test_red_disables_self_booking(self, ruleset):
        """RED tier always disables self-booking."""
        ruleset_data, ruleset_hash = ruleset
        facts = {
            "risk.suicidal_intent_now": True,
            "risk.suicide_plan": True,
            "risk.means_access": True,
        }

        decision = evaluate_ruleset(ruleset_data, facts, ruleset_hash)

        assert decision.self_book_allowed is False
        assert decision.clinician_review_required is True

    def test_amber_disables_self_booking(self, ruleset):
        """AMBER tier always disables self-booking."""
        ruleset_data, ruleset_hash = ruleset
        facts = {
            "risk.new_psychosis": True,
        }

        decision = evaluate_ruleset(ruleset_data, facts, ruleset_hash)

        assert decision.self_book_allowed is False
        assert decision.clinician_review_required is True

    def test_green_allows_self_booking(self, ruleset):
        """GREEN tier allows self-booking."""
        ruleset_data, ruleset_hash = ruleset
        facts = {
            "risk.any_red_amber_flag": False,
        }

        decision = evaluate_ruleset(ruleset_data, facts, ruleset_hash)

        assert decision.self_book_allowed is True
        assert decision.clinician_review_required is False


class TestEvaluationOutputGolden:
    """Golden tests for evaluation output structure."""

    def test_decision_includes_ruleset_metadata(self, ruleset):
        """Decision includes ruleset version and hash."""
        ruleset_data, ruleset_hash = ruleset
        facts = {"risk.any_red_amber_flag": False}

        decision = evaluate_ruleset(ruleset_data, facts, ruleset_hash)

        assert decision.ruleset_version == "1.0.0"
        assert decision.ruleset_hash == ruleset_hash
        assert len(decision.ruleset_hash) == 64

    def test_decision_includes_explanations(self, ruleset):
        """Decision includes human-readable explanations."""
        ruleset_data, ruleset_hash = ruleset
        facts = {
            "risk.suicidal_intent_now": True,
            "risk.suicide_plan": True,
            "risk.means_access": True,
        }

        decision = evaluate_ruleset(ruleset_data, facts, ruleset_hash)

        assert len(decision.explanations) > 0
        assert "suicidal" in decision.explanations[0].lower()

    def test_decision_includes_flags(self, ruleset):
        """Decision includes risk flags."""
        ruleset_data, ruleset_hash = ruleset
        facts = {
            "risk.suicidal_intent_now": True,
            "risk.suicide_plan": True,
            "risk.means_access": True,
        }

        decision = evaluate_ruleset(ruleset_data, facts, ruleset_hash)

        assert len(decision.flags) > 0
        assert decision.flags[0]["type"] == "SUICIDE_RISK"
        assert decision.flags[0]["severity"] == "HIGH"


class TestFlatFactsSupport:
    """Tests for flat (dot-notation) facts support."""

    def test_flat_facts_are_unflattened(self, ruleset):
        """Flat facts with dots are converted to nested dicts."""
        ruleset_data, ruleset_hash = ruleset

        # Flat format
        flat_facts = {
            "risk.suicidal_intent_now": True,
            "risk.suicide_plan": True,
            "risk.means_access": True,
        }

        decision = evaluate_ruleset(ruleset_data, flat_facts, ruleset_hash)
        assert decision.tier == "RED"

    def test_nested_facts_work_directly(self, ruleset):
        """Nested facts work without transformation."""
        ruleset_data, ruleset_hash = ruleset

        # Nested format
        nested_facts = {
            "risk": {
                "suicidal_intent_now": True,
                "suicide_plan": True,
                "means_access": True,
            }
        }

        decision = evaluate_ruleset(ruleset_data, nested_facts, ruleset_hash)
        assert decision.tier == "RED"

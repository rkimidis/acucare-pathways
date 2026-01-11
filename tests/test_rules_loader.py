"""Tests for ruleset loader and integrity verification."""

from pathlib import Path

import pytest

from app.rules.engine import RulesEngine, evaluate_triage
from app.rules.loader import RulesetLoader, compute_ruleset_hash, load_ruleset


class TestRulesetLoader:
    """Tests for the RulesetLoader class."""

    def test_load_ruleset_returns_dict_and_hash(self) -> None:
        """Test that load_ruleset returns both ruleset dict and hash."""
        ruleset, ruleset_hash = load_ruleset("uk-private-triage-v1.0.0.yaml")

        assert isinstance(ruleset, dict)
        assert isinstance(ruleset_hash, str)
        assert len(ruleset_hash) == 64  # SHA256 hex is 64 chars

    def test_load_ruleset_has_required_fields(self) -> None:
        """Test that loaded ruleset has required fields."""
        ruleset, _ = load_ruleset("uk-private-triage-v1.0.0.yaml")

        assert "id" in ruleset
        assert "version" in ruleset
        assert "rules" in ruleset
        assert isinstance(ruleset["rules"], list)

    def test_compute_hash_is_deterministic(self) -> None:
        """Test that hash computation is deterministic."""
        content = "test content for hashing"

        hash1 = compute_ruleset_hash(content)
        hash2 = compute_ruleset_hash(content)

        assert hash1 == hash2

    def test_different_content_produces_different_hash(self) -> None:
        """Test that different content produces different hashes."""
        hash1 = compute_ruleset_hash("content version 1")
        hash2 = compute_ruleset_hash("content version 2")

        assert hash1 != hash2

    def test_hash_is_stable_across_loads(self) -> None:
        """Test that same ruleset file produces same hash on multiple loads."""
        _, hash1 = load_ruleset("uk-private-triage-v1.0.0.yaml")
        _, hash2 = load_ruleset("uk-private-triage-v1.0.0.yaml")

        assert hash1 == hash2

    def test_loader_caches_ruleset(self) -> None:
        """Test that RulesetLoader caches loaded rulesets."""
        loader = RulesetLoader()

        ruleset1, hash1 = loader.load("uk-private-triage-v1.0.0.yaml")
        ruleset2, hash2 = loader.load("uk-private-triage-v1.0.0.yaml")

        # Should be same objects due to caching
        assert ruleset1 is ruleset2
        assert hash1 == hash2

    def test_loader_clear_cache(self) -> None:
        """Test that cache clearing works."""
        loader = RulesetLoader()

        ruleset1, _ = loader.load("uk-private-triage-v1.0.0.yaml")
        loader.clear_cache()
        ruleset2, _ = loader.load("uk-private-triage-v1.0.0.yaml")

        # Should be different objects after cache clear
        assert ruleset1 is not ruleset2

    def test_loader_list_rulesets(self) -> None:
        """Test listing available rulesets."""
        loader = RulesetLoader()
        rulesets = loader.list_rulesets()

        assert isinstance(rulesets, list)
        assert "uk-private-triage-v1.0.0.yaml" in rulesets

    def test_load_nonexistent_ruleset_raises_error(self) -> None:
        """Test that loading non-existent ruleset raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_ruleset("nonexistent-ruleset.yaml")


class TestRulesEngine:
    """Tests for the RulesEngine class."""

    def test_engine_loads_ruleset(self) -> None:
        """Test that engine loads ruleset on initialization."""
        engine = RulesEngine()

        assert engine.ruleset is not None
        assert engine.ruleset_hash is not None
        assert engine.ruleset_version is not None

    def test_engine_evaluate_returns_result(self) -> None:
        """Test that evaluate returns a TriageTierResult."""
        engine = RulesEngine()
        result = engine.evaluate({})

        assert result.tier is not None
        assert result.explanations is not None
        assert result.ruleset_version is not None
        assert result.ruleset_hash is not None
        assert isinstance(result.rules_fired, list)

    def test_engine_red_tier_for_immediate_danger(self) -> None:
        """Test that suicide risk with intent, plan and means triggers RED tier."""
        engine = RulesEngine()
        # Use actual facts from uk-private-triage-v1.0.0.yaml
        result = engine.evaluate({
            "risk": {
                "suicidal_intent_now": True,
                "suicide_plan": True,
                "means_access": True,
            }
        })

        from app.models.triage_case import TriageTier

        assert result.tier == TriageTier.RED
        assert "RED_SUICIDE_INTENT_PLAN_MEANS" in result.rules_fired

    def test_engine_red_tier_for_serious_attempt(self) -> None:
        """Test that recent serious suicide attempt triggers RED tier."""
        engine = RulesEngine()
        # Use actual facts from uk-private-triage-v1.0.0.yaml
        result = engine.evaluate({
            "risk": {
                "recent_suicide_attempt": True,
                "attempt_required_medical_attention": True,
            }
        })

        from app.models.triage_case import TriageTier

        assert result.tier == TriageTier.RED

    def test_engine_amber_tier_for_new_psychosis(self) -> None:
        """Test that new psychosis triggers AMBER tier."""
        engine = RulesEngine()
        # Use actual facts from uk-private-triage-v1.0.0.yaml
        result = engine.evaluate({
            "risk": {
                "new_psychosis": True,
            }
        })

        from app.models.triage_case import TriageTier

        assert result.tier == TriageTier.AMBER

    def test_engine_green_tier_default(self) -> None:
        """Test that no matching rules defaults to GREEN tier."""
        engine = RulesEngine()
        result = engine.evaluate({"random_field": "value"})

        from app.models.triage_case import TriageTier

        assert result.tier == TriageTier.GREEN
        assert len(result.rules_fired) == 0

    def test_evaluate_triage_convenience_function(self) -> None:
        """Test the evaluate_triage convenience function."""
        result = evaluate_triage({"immediate_danger": False})

        assert result.tier is not None
        assert result.ruleset_version is not None

    def test_engine_explanation_contains_details(self) -> None:
        """Test that explanations contains useful details when rule fires."""
        engine = RulesEngine()
        # Use facts that will trigger a rule with explanation
        result = engine.evaluate({
            "risk": {
                "new_psychosis": True,
            }
        })

        # Check that the result has expected attributes
        assert result.tier is not None
        assert result.rules_fired is not None
        assert isinstance(result.explanations, list)
        # When a rule fires, there should be an explanation
        assert len(result.explanations) > 0

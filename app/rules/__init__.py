"""Deterministic triage rules engine.

This module provides a YAML-based rules engine for triage tier assignment.
All triage decisions are deterministic and explainable - no AI/ML is used.
"""

from app.rules.engine import (
    RulesEngine,
    RulesetDecision,
    evaluate_triage,
    evaluate_ruleset,
)
from app.rules.loader import RulesetLoader, compute_ruleset_hash, load_ruleset

__all__ = [
    "RulesetLoader",
    "load_ruleset",
    "compute_ruleset_hash",
    "RulesEngine",
    "RulesetDecision",
    "evaluate_triage",
    "evaluate_ruleset",
]

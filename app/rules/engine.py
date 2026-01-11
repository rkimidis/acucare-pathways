"""Deterministic triage rules engine.

This engine evaluates patient questionnaire responses against
a ruleset to determine triage tier. All decisions are:
- Deterministic (same input = same output)
- Explainable (provides triggered rules and explanations)
- Auditable (records ruleset version and hash)

NO AI/ML is used for tier assignment.
"""

from dataclasses import dataclass, field
from typing import Any

from app.models.triage_case import TriageTier
from app.rules.loader import RulesetLoader


@dataclass
class RuleMatch:
    """Result of a single rule match."""

    rule_id: str
    priority: int
    tier: str
    pathway: str
    self_book_allowed: bool
    flags: list[dict[str, Any]]
    explanation: str


@dataclass
class EvaluationResult:
    """Complete result of rules engine evaluation."""

    tier: TriageTier
    pathway: str
    self_book_allowed: bool
    clinician_review_required: bool
    rules_fired: list[str]
    explanations: list[str]
    flags: list[dict[str, Any]]
    ruleset_version: str
    ruleset_hash: str
    evaluation_context: dict[str, Any] = field(default_factory=dict)


class RulesEngine:
    """Deterministic rules engine for triage evaluation.

    Evaluates rules in priority order and produces:
    - Tier (RED/AMBER/GREEN/BLUE)
    - Pathway
    - Rules fired
    - Explanations
    - Risk flags
    """

    def __init__(self, ruleset_filename: str = "uk-private-triage-v1.0.0.yaml") -> None:
        """Initialize engine with a specific ruleset.

        Args:
            ruleset_filename: Name of ruleset file to use
        """
        self.ruleset_filename = ruleset_filename
        self.loader = RulesetLoader()
        self._ruleset: dict[str, Any] | None = None
        self._hash: str | None = None

    def load_ruleset(self) -> None:
        """Load the configured ruleset."""
        self._ruleset, self._hash = self.loader.load(self.ruleset_filename)

    @property
    def ruleset(self) -> dict[str, Any]:
        """Get loaded ruleset, loading if necessary."""
        if self._ruleset is None:
            self.load_ruleset()
        return self._ruleset  # type: ignore

    @property
    def ruleset_hash(self) -> str:
        """Get ruleset hash."""
        if self._hash is None:
            self.load_ruleset()
        return self._hash  # type: ignore

    @property
    def ruleset_version(self) -> str:
        """Get ruleset version string."""
        return self.ruleset.get("version", "unknown")

    @property
    def evaluation_mode(self) -> str:
        """Get evaluation mode from ruleset."""
        ruleset_config = self.ruleset.get("ruleset", {})
        evaluation = ruleset_config.get("evaluation", {})
        return evaluation.get("mode", "first_match_wins")

    def evaluate(self, facts: dict[str, Any]) -> EvaluationResult:
        """Evaluate facts against ruleset.

        This is the core triage function. It evaluates facts against
        rules in priority order (lowest number = highest priority).

        Args:
            facts: Dict of facts from questionnaire responses and scores
                   Structure: {"risk": {...}, "scores": {...}, "presentation": {...}, ...}

        Returns:
            EvaluationResult with tier, pathway, rules fired, explanations, and flags
        """
        rules = self.ruleset.get("rules", [])

        # Sort rules by priority (lower = higher priority)
        sorted_rules = sorted(rules, key=lambda r: r.get("priority", 999))

        matches: list[RuleMatch] = []
        all_flags: list[dict[str, Any]] = []
        rules_fired: list[str] = []
        explanations: list[str] = []

        # Evaluate rules in priority order
        for rule in sorted_rules:
            if self._evaluate_rule_conditions(rule, facts):
                match = self._extract_rule_match(rule)
                matches.append(match)
                rules_fired.append(match.rule_id)
                if match.explanation:
                    explanations.append(match.explanation)
                all_flags.extend(match.flags)

                # In first_match_wins mode, stop at first match
                if self.evaluation_mode == "first_match_wins":
                    break

        # Determine final disposition
        if matches:
            # Use highest priority match for tier/pathway
            best_match = matches[0]
            tier = self._tier_from_string(best_match.tier)
            pathway = best_match.pathway
            self_book_allowed = best_match.self_book_allowed
        else:
            # Use defaults from ruleset
            defaults = self._get_defaults()
            tier = self._tier_from_string(defaults.get("tier", "GREEN"))
            pathway = defaults.get("pathway", "THERAPY_ASSESSMENT")
            self_book_allowed = defaults.get("booking", {}).get("self_book_allowed", True)

        # Safeguards: RED and AMBER require clinician review
        clinician_review_required = tier in (TriageTier.RED, TriageTier.AMBER)

        # Safeguards: RED and AMBER disable self-booking
        if tier in (TriageTier.RED, TriageTier.AMBER):
            self_book_allowed = False

        return EvaluationResult(
            tier=tier,
            pathway=pathway,
            self_book_allowed=self_book_allowed,
            clinician_review_required=clinician_review_required,
            rules_fired=rules_fired,
            explanations=explanations,
            flags=all_flags,
            ruleset_version=self.ruleset_version,
            ruleset_hash=self.ruleset_hash,
            evaluation_context={
                "total_rules_evaluated": len(rules),
                "matches_found": len(matches),
                "evaluation_mode": self.evaluation_mode,
                "fact_keys": list(facts.keys()),
            },
        )

    def _get_defaults(self) -> dict[str, Any]:
        """Get default disposition from ruleset."""
        ruleset_config = self.ruleset.get("ruleset", {})
        evaluation = ruleset_config.get("evaluation", {})
        return evaluation.get("default", {})

    def _evaluate_rule_conditions(
        self,
        rule: dict[str, Any],
        facts: dict[str, Any],
    ) -> bool:
        """Evaluate all conditions in a rule.

        Args:
            rule: Rule definition
            facts: Available facts

        Returns:
            True if rule conditions are met
        """
        when = rule.get("when", {})

        if not when:
            return False

        # Handle 'all' conditions (AND)
        if "all" in when:
            return self._evaluate_all_conditions(when["all"], facts)

        # Handle 'any' conditions (OR)
        if "any" in when:
            return self._evaluate_any_conditions(when["any"], facts)

        return False

    def _evaluate_all_conditions(
        self,
        conditions: list[dict[str, Any]],
        facts: dict[str, Any],
    ) -> bool:
        """Evaluate conditions with AND logic."""
        for condition in conditions:
            # Handle nested any
            if "any" in condition:
                if not self._evaluate_any_conditions(condition["any"], facts):
                    return False
            # Handle regular condition
            elif not self._evaluate_single_condition(condition, facts):
                return False
        return True

    def _evaluate_any_conditions(
        self,
        conditions: list[dict[str, Any]],
        facts: dict[str, Any],
    ) -> bool:
        """Evaluate conditions with OR logic."""
        for condition in conditions:
            # Handle nested all
            if "all" in condition:
                if self._evaluate_all_conditions(condition["all"], facts):
                    return True
            # Handle regular condition
            elif self._evaluate_single_condition(condition, facts):
                return True
        return False

    def _evaluate_single_condition(
        self,
        condition: dict[str, Any],
        facts: dict[str, Any],
    ) -> bool:
        """Evaluate a single condition.

        Supports operators: ==, !=, >, >=, <, <=, in, contains

        Args:
            condition: Condition dict with fact, op, value
            facts: Available facts

        Returns:
            True if condition is met
        """
        fact_path = condition.get("fact")
        operator = condition.get("op", "==")
        expected = condition.get("value")

        if fact_path is None:
            return False

        actual = self._get_fact_value(fact_path, facts)

        # Handle missing facts
        if actual is None:
            return operator == "==" and expected is None

        # Evaluate based on operator
        try:
            if operator == "==":
                return actual == expected
            elif operator == "!=":
                return actual != expected
            elif operator == ">":
                return actual > expected
            elif operator == ">=":
                return actual >= expected
            elif operator == "<":
                return actual < expected
            elif operator == "<=":
                return actual <= expected
            elif operator == "in":
                return actual in expected if isinstance(expected, (list, tuple)) else False
            elif operator == "contains":
                return expected in actual if isinstance(actual, (str, list, tuple)) else False
        except (TypeError, ValueError):
            return False

        return False

    def _get_fact_value(self, path: str, facts: dict[str, Any]) -> Any:
        """Get a fact value by dot-notation path.

        Args:
            path: Dot-separated path (e.g., "scores.phq9.total")
            facts: Facts dictionary

        Returns:
            Value at path or None if not found
        """
        parts = path.split(".")
        current = facts

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None

            if current is None:
                return None

        return current

    def _extract_rule_match(self, rule: dict[str, Any]) -> RuleMatch:
        """Extract match details from a rule."""
        then = rule.get("then", {})
        booking = then.get("booking", {})

        return RuleMatch(
            rule_id=rule.get("id", "unknown"),
            priority=rule.get("priority", 999),
            tier=then.get("tier", "GREEN"),
            pathway=then.get("pathway", "THERAPY_ASSESSMENT"),
            self_book_allowed=booking.get("self_book_allowed", True),
            flags=then.get("flags", []),
            explanation=then.get("explain", ""),
        )

    def _tier_from_string(self, tier_str: str) -> TriageTier:
        """Convert string tier to TriageTier enum."""
        tier_map = {
            "RED": TriageTier.RED,
            "AMBER": TriageTier.AMBER,
            "GREEN": TriageTier.GREEN,
            "BLUE": TriageTier.BLUE,
        }
        return tier_map.get(tier_str.upper(), TriageTier.GREEN)


def evaluate_triage(
    facts: dict[str, Any],
    ruleset_filename: str = "uk-private-triage-v1.0.0.yaml",
) -> EvaluationResult:
    """Convenience function to evaluate triage with default ruleset.

    Args:
        facts: Facts from questionnaire responses and scores
        ruleset_filename: Ruleset to use

    Returns:
        EvaluationResult
    """
    engine = RulesEngine(ruleset_filename)
    return engine.evaluate(facts)


@dataclass
class RulesetDecision:
    """Decision result from ruleset evaluation.

    Simpler output format for golden tests and API consumers.
    """

    tier: str
    pathway: str
    self_book_allowed: bool
    clinician_review_required: bool
    rules_fired: list[str]
    explanations: list[str]
    flags: list[dict[str, Any]]
    ruleset_version: str
    ruleset_hash: str


def _unflatten_facts(flat_facts: dict[str, Any]) -> dict[str, Any]:
    """Convert flat dot-notation facts to nested dict.

    Args:
        flat_facts: Dict with keys like "risk.suicidal_intent_now"

    Returns:
        Nested dict like {"risk": {"suicidal_intent_now": ...}}
    """
    result: dict[str, Any] = {}

    for key, value in flat_facts.items():
        parts = key.split(".")
        current = result

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value

    return result


def evaluate_ruleset(
    ruleset: dict[str, Any],
    facts: dict[str, Any],
    ruleset_hash: str = "",
) -> RulesetDecision:
    """Evaluate facts against a loaded ruleset.

    This is the primary evaluation function for golden tests.
    Accepts flat facts (dot-notation keys) for convenience.

    Args:
        ruleset: Loaded ruleset dictionary
        facts: Facts dict, can be flat (dot-notation) or nested
        ruleset_hash: Optional pre-computed hash

    Returns:
        RulesetDecision with tier, pathway, rules_fired, explanations

    Example:
        >>> ruleset, hash = load_ruleset("uk-private-triage-v1.0.0.yaml")
        >>> facts = {"risk.suicidal_intent_now": True, "scores.phq9.total": 18}
        >>> decision = evaluate_ruleset(ruleset, facts, hash)
        >>> print(decision.tier)
        "RED"
    """
    # Check if facts are flat (contain dots in keys) and unflatten
    if any("." in key for key in facts.keys()):
        nested_facts = _unflatten_facts(facts)
    else:
        nested_facts = facts

    rules = ruleset.get("rules", [])
    ruleset_config = ruleset.get("ruleset", {})
    evaluation_config = ruleset_config.get("evaluation", {})
    evaluation_mode = evaluation_config.get("mode", "first_match_wins")
    defaults = evaluation_config.get("default", {})

    # Sort rules by priority
    sorted_rules = sorted(rules, key=lambda r: r.get("priority", 999))

    matches: list[dict[str, Any]] = []
    rules_fired: list[str] = []
    explanations: list[str] = []
    all_flags: list[dict[str, Any]] = []

    for rule in sorted_rules:
        if _evaluate_rule_conditions(rule.get("when", {}), nested_facts):
            then = rule.get("then", {})
            matches.append({
                "rule_id": rule.get("id", "unknown"),
                "priority": rule.get("priority", 999),
                "tier": then.get("tier", "GREEN"),
                "pathway": then.get("pathway", "THERAPY_ASSESSMENT"),
                "self_book_allowed": then.get("booking", {}).get("self_book_allowed", True),
                "flags": then.get("flags", []),
                "explain": then.get("explain", ""),
            })
            rules_fired.append(rule.get("id", "unknown"))
            if then.get("explain"):
                explanations.append(then.get("explain"))
            all_flags.extend(then.get("flags", []))

            if evaluation_mode == "first_match_wins":
                break

    # Determine final disposition
    if matches:
        best = matches[0]
        tier = best["tier"]
        pathway = best["pathway"]
        self_book_allowed = best["self_book_allowed"]
    else:
        tier = defaults.get("tier", "GREEN")
        pathway = defaults.get("pathway", "THERAPY_ASSESSMENT")
        self_book_allowed = defaults.get("booking", {}).get("self_book_allowed", True)

    # Safeguards
    clinician_review_required = tier in ("RED", "AMBER")
    if tier in ("RED", "AMBER"):
        self_book_allowed = False

    return RulesetDecision(
        tier=tier,
        pathway=pathway,
        self_book_allowed=self_book_allowed,
        clinician_review_required=clinician_review_required,
        rules_fired=rules_fired,
        explanations=explanations,
        flags=all_flags,
        ruleset_version=ruleset.get("version", "unknown"),
        ruleset_hash=ruleset_hash,
    )


def _evaluate_rule_conditions(when: dict[str, Any], facts: dict[str, Any]) -> bool:
    """Evaluate rule conditions against facts.

    Args:
        when: Condition block from rule
        facts: Nested facts dict

    Returns:
        True if conditions are satisfied
    """
    if not when:
        return False

    if "all" in when:
        return _evaluate_all(when["all"], facts)

    if "any" in when:
        return _evaluate_any(when["any"], facts)

    return False


def _evaluate_all(conditions: list[dict[str, Any]], facts: dict[str, Any]) -> bool:
    """Evaluate AND conditions."""
    for cond in conditions:
        if "any" in cond:
            if not _evaluate_any(cond["any"], facts):
                return False
        elif "all" in cond:
            if not _evaluate_all(cond["all"], facts):
                return False
        elif not _evaluate_single(cond, facts):
            return False
    return True


def _evaluate_any(conditions: list[dict[str, Any]], facts: dict[str, Any]) -> bool:
    """Evaluate OR conditions."""
    for cond in conditions:
        if "all" in cond:
            if _evaluate_all(cond["all"], facts):
                return True
        elif "any" in cond:
            if _evaluate_any(cond["any"], facts):
                return True
        elif _evaluate_single(cond, facts):
            return True
    return False


def _evaluate_single(cond: dict[str, Any], facts: dict[str, Any]) -> bool:
    """Evaluate a single condition."""
    fact_path = cond.get("fact")
    op = cond.get("op", "==")
    expected = cond.get("value")

    if not fact_path:
        return False

    actual = _get_nested_value(facts, fact_path)

    if actual is None:
        return op == "==" and expected is None

    try:
        if op == "==":
            return actual == expected
        elif op == "!=":
            return actual != expected
        elif op == ">":
            return actual > expected
        elif op == ">=":
            return actual >= expected
        elif op == "<":
            return actual < expected
        elif op == "<=":
            return actual <= expected
        elif op == "in":
            return actual in expected if isinstance(expected, (list, tuple)) else False
        elif op == "contains":
            return expected in actual if actual else False
    except (TypeError, ValueError):
        return False

    return False


def _get_nested_value(data: dict[str, Any], path: str) -> Any:
    """Get value from nested dict using dot notation."""
    parts = path.split(".")
    current = data

    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
        if current is None:
            return None

    return current

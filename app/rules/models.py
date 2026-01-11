"""Rule and ruleset data models."""

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ConditionOperator(str, Enum):
    """Operators for rule conditions."""
    EQUALS = "eq"
    NOT_EQUALS = "neq"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    IN = "in"
    NOT_IN = "not_in"
    IS_TRUE = "is_true"
    IS_FALSE = "is_false"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    CONTAINS = "contains"


@dataclass
class Condition:
    """A single condition in a rule."""
    field: str
    operator: ConditionOperator
    value: Any = None

    def evaluate(self, facts: dict) -> bool:
        """Evaluate this condition against the facts."""
        # Get the fact value using dot notation
        fact_value = self._get_nested_value(facts, self.field)

        op = self.operator
        expected = self.value

        if op == ConditionOperator.EQUALS:
            return fact_value == expected
        elif op == ConditionOperator.NOT_EQUALS:
            return fact_value != expected
        elif op == ConditionOperator.GREATER_THAN:
            return fact_value is not None and fact_value > expected
        elif op == ConditionOperator.GREATER_THAN_OR_EQUAL:
            return fact_value is not None and fact_value >= expected
        elif op == ConditionOperator.LESS_THAN:
            return fact_value is not None and fact_value < expected
        elif op == ConditionOperator.LESS_THAN_OR_EQUAL:
            return fact_value is not None and fact_value <= expected
        elif op == ConditionOperator.IN:
            return fact_value in expected
        elif op == ConditionOperator.NOT_IN:
            return fact_value not in expected
        elif op == ConditionOperator.IS_TRUE:
            return fact_value is True
        elif op == ConditionOperator.IS_FALSE:
            return fact_value is False
        elif op == ConditionOperator.IS_NULL:
            return fact_value is None
        elif op == ConditionOperator.IS_NOT_NULL:
            return fact_value is not None
        elif op == ConditionOperator.CONTAINS:
            return expected in fact_value if fact_value else False

        return False

    def _get_nested_value(self, data: dict, path: str) -> Any:
        """Get value from nested dict using dot notation."""
        keys = path.split(".")
        value = data

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None

        return value


@dataclass
class Rule:
    """A triage rule with conditions and outcome."""
    id: str
    name: str
    description: str
    priority: int  # Lower = higher priority
    conditions: list[Condition]
    outcome: dict  # e.g., {"tier": "red", "pathway": "crisis"}
    enabled: bool = True
    explain_template: str = ""  # Template for explanation

    def evaluate(self, facts: dict) -> bool:
        """Evaluate all conditions (AND logic)."""
        if not self.enabled:
            return False

        return all(condition.evaluate(facts) for condition in self.conditions)

    def get_explanation(self, facts: dict) -> str:
        """Generate explanation for why this rule matched."""
        if self.explain_template:
            try:
                # Simple template substitution
                explanation = self.explain_template
                for key, value in self._flatten_facts(facts).items():
                    explanation = explanation.replace(f"{{{key}}}", str(value))
                return explanation
            except Exception:
                pass

        # Default explanation
        matched_conditions = []
        for condition in self.conditions:
            fact_value = condition._get_nested_value(facts, condition.field)
            matched_conditions.append(
                f"{condition.field} {condition.operator.value} {condition.value} "
                f"(actual: {fact_value})"
            )

        return f"Rule '{self.name}' matched: " + "; ".join(matched_conditions)

    def _flatten_facts(self, facts: dict, prefix: str = "") -> dict:
        """Flatten nested facts dict for template substitution."""
        result = {}
        for key, value in facts.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                result.update(self._flatten_facts(value, full_key))
            else:
                result[full_key] = value
        return result


@dataclass
class Ruleset:
    """A versioned set of rules."""
    id: str
    name: str
    version: str
    description: str
    rules: list[Rule] = field(default_factory=list)

    _hash: Optional[str] = field(default=None, repr=False)

    @property
    def content_hash(self) -> str:
        """Compute SHA-256 hash of ruleset content."""
        if self._hash is None:
            content = {
                "id": self.id,
                "version": self.version,
                "rules": [
                    {
                        "id": r.id,
                        "priority": r.priority,
                        "conditions": [
                            {"field": c.field, "operator": c.operator.value, "value": c.value}
                            for c in r.conditions
                        ],
                        "outcome": r.outcome,
                    }
                    for r in self.rules
                ],
            }
            content_str = json.dumps(content, sort_keys=True)
            self._hash = hashlib.sha256(content_str.encode()).hexdigest()
        return self._hash

    def get_sorted_rules(self) -> list[Rule]:
        """Get rules sorted by priority (ascending)."""
        return sorted(
            [r for r in self.rules if r.enabled],
            key=lambda r: r.priority
        )

    @classmethod
    def from_dict(cls, data: dict) -> "Ruleset":
        """Create Ruleset from dictionary representation."""
        rules = []
        for rule_data in data.get("rules", []):
            conditions = []
            for cond_data in rule_data.get("conditions", []):
                conditions.append(Condition(
                    field=cond_data["field"],
                    operator=ConditionOperator(cond_data["operator"]),
                    value=cond_data.get("value"),
                ))

            rules.append(Rule(
                id=rule_data["id"],
                name=rule_data["name"],
                description=rule_data.get("description", ""),
                priority=rule_data["priority"],
                conditions=conditions,
                outcome=rule_data["outcome"],
                enabled=rule_data.get("enabled", True),
                explain_template=rule_data.get("explain_template", ""),
            ))

        return cls(
            id=data["id"],
            name=data["name"],
            version=data["version"],
            description=data.get("description", ""),
            rules=rules,
        )

    def to_dict(self) -> dict:
        """Convert Ruleset to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "rules": [
                {
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "priority": r.priority,
                    "conditions": [
                        {
                            "field": c.field,
                            "operator": c.operator.value,
                            "value": c.value,
                        }
                        for c in r.conditions
                    ],
                    "outcome": r.outcome,
                    "enabled": r.enabled,
                    "explain_template": r.explain_template,
                }
                for r in self.rules
            ],
        }

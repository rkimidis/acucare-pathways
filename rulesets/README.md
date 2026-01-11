# Rulesets

This directory contains versioned YAML ruleset files for deterministic triage tier assignment.

## Versioning

Rulesets follow semantic versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Breaking changes to rule structure or evaluation logic
- **MINOR**: New rules or conditions added
- **PATCH**: Bug fixes or documentation updates

## File Naming Convention

```
{identifier}-v{MAJOR}.{MINOR}.{PATCH}.yaml
```

Example: `uk-private-triage-v1.0.0.yaml`

## Integrity Verification

Each ruleset's SHA256 hash is computed and stored with triage results for audit purposes:

```python
from app.rules.loader import load_ruleset, compute_ruleset_hash

ruleset, hash = load_ruleset("uk-private-triage-v1.0.0.yaml")
print(f"Ruleset hash: {hash}")
```

## Ruleset Structure

```yaml
id: uk-private-triage
version: "1.0.0"
description: "UK private psychiatric clinic triage rules"
effective_date: "2024-01-01"

rules:
  - id: rule_001
    name: "Immediate risk"
    description: "Patient indicates immediate danger"
    tier: red
    conditions:
      - field: "immediate_danger"
        operator: "eq"
        value: true

  - id: rule_002
    name: "Suicidal ideation"
    description: "Patient reports suicidal thoughts"
    tier: red
    conditions:
      - field: "suicidal_ideation_score"
        operator: "gte"
        value: 8
```

## Supported Operators

| Operator   | Description                  | Example                          |
|------------|------------------------------|----------------------------------|
| `eq`       | Equals                       | `{"field": "x", "operator": "eq", "value": true}` |
| `ne`       | Not equals                   | `{"field": "x", "operator": "ne", "value": 0}` |
| `gt`       | Greater than                 | `{"field": "score", "operator": "gt", "value": 5}` |
| `gte`      | Greater than or equal        | `{"field": "score", "operator": "gte", "value": 5}` |
| `lt`       | Less than                    | `{"field": "score", "operator": "lt", "value": 3}` |
| `lte`      | Less than or equal           | `{"field": "score", "operator": "lte", "value": 3}` |
| `in`       | Value in list                | `{"field": "type", "operator": "in", "value": ["a", "b"]}` |
| `contains` | String/list contains value   | `{"field": "symptoms", "operator": "contains", "value": "anxiety"}` |

## Important Notes

1. **Rules are evaluated in order** - RED rules first, then AMBER, then GREEN default
2. **Conditions use AND logic** - All conditions in a rule must match
3. **No AI/ML** - All tier decisions are deterministic
4. **Rulesets are immutable** - Create new versions, never modify existing ones
5. **Clinical oversight required** - Rule changes require clinical approval

## Creating New Rulesets

1. Copy an existing ruleset as a template
2. Increment the version number
3. Document changes in the ruleset description
4. Get clinical approval before deployment
5. Test thoroughly with representative scenarios

## Audit Trail

Every triage decision records:
- Ruleset version used
- Ruleset SHA256 hash
- List of triggered rules
- Complete explanation

# Rules Engine Documentation

## Overview

The AcuCare Pathways triage rules engine is a **deterministic, auditable** system for assigning triage tiers to patient cases. It evaluates patient questionnaire responses and clinical scores against a predefined ruleset to produce consistent, explainable outcomes.

**Key Principles:**
- **NO AI/ML** is used for tier assignment - all decisions are rule-based
- **Same input = Same output** - fully deterministic evaluation
- **Full auditability** - every decision records ruleset version, hash, and fired rules
- **Safeguards enforced** - RED/AMBER tiers automatically block self-booking

## Triage Tiers

| Tier | Description | Self-Booking | Clinician Review |
|------|-------------|--------------|------------------|
| **RED** | Crisis/Urgent - Immediate clinical attention required | Blocked | Required |
| **AMBER** | Elevated risk - Clinical review before proceeding | Blocked | Required |
| **GREEN** | Routine - Standard assessment pathway | Allowed | Optional |
| **BLUE** | Low intensity - Digital/self-guided options | Allowed | Optional |

## YAML Ruleset Schema

Rulesets are stored as YAML files in `/rulesets/` and registered in the database with a SHA256 content hash for integrity verification.

### File Structure

```yaml
ruleset:
  id: uk-private-triage
  version: "1.0.0"
  description: "UK Private Psychiatric Triage Rules"
  author: "Clinical Team"
  effective_date: "2024-01-01"

  evaluation:
    mode: first_match_wins  # or "all_matches"
    default:
      tier: GREEN
      pathway: THERAPY_ASSESSMENT
      booking:
        self_book_allowed: true

rules:
  - id: RED_SUICIDE_INTENT_PLAN_MEANS
    priority: 10
    when:
      all:
        - fact: risk.suicidal_intent_now
          op: "=="
          value: true
        - fact: risk.suicide_plan
          op: "=="
          value: true
        - fact: risk.means_access
          op: "=="
          value: true
    then:
      tier: RED
      pathway: CRISIS_ESCALATION
      explain: "Active suicidal intent with plan and access to means identified."
      booking:
        self_book_allowed: false
      flags:
        - type: SUICIDE_RISK
          severity: CRITICAL
```

### Rule Components

#### `ruleset` (Required)
Top-level metadata about the ruleset.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique ruleset identifier |
| `version` | string | Yes | Semantic version (e.g., "1.0.0") |
| `description` | string | No | Human-readable description |
| `author` | string | No | Author or team responsible |
| `effective_date` | string | No | ISO 8601 date when ruleset becomes effective |

#### `ruleset.evaluation` (Required)
Controls how rules are evaluated.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `mode` | string | `first_match_wins` | Evaluation mode: `first_match_wins` or `all_matches` |
| `default.tier` | string | `GREEN` | Default tier if no rules match |
| `default.pathway` | string | `THERAPY_ASSESSMENT` | Default pathway if no rules match |
| `default.booking.self_book_allowed` | boolean | `true` | Default self-booking setting |

#### `rules[]` (Required)
Array of rule definitions, evaluated in priority order.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique rule identifier (SCREAMING_SNAKE_CASE) |
| `priority` | integer | Yes | Evaluation order (lower = higher priority) |
| `when` | object | Yes | Condition block (see Conditions below) |
| `then` | object | Yes | Actions block (see Actions below) |

### Conditions (`when` block)

Conditions use `all` (AND) and `any` (OR) operators with nestable structure.

```yaml
when:
  all:                          # All conditions must be true (AND)
    - fact: risk.suicidal_intent_now
      op: "=="
      value: true
    - any:                      # At least one must be true (OR)
        - fact: risk.suicide_plan
          op: "=="
          value: true
        - fact: risk.means_access
          op: "=="
          value: true
```

#### Condition Fields

| Field | Type | Description |
|-------|------|-------------|
| `fact` | string | Dot-notation path to fact (e.g., `scores.phq9.total`) |
| `op` | string | Comparison operator |
| `value` | any | Value to compare against |

#### Supported Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `==` | Equals | `{ fact: "risk.test", op: "==", value: true }` |
| `!=` | Not equals | `{ fact: "risk.test", op: "!=", value: false }` |
| `>` | Greater than | `{ fact: "scores.phq9.total", op: ">", value: 10 }` |
| `>=` | Greater than or equal | `{ fact: "scores.phq9.total", op: ">=", value: 10 }` |
| `<` | Less than | `{ fact: "scores.phq9.total", op: "<", value: 5 }` |
| `<=` | Less than or equal | `{ fact: "scores.phq9.total", op: "<=", value: 5 }` |
| `in` | Value in list | `{ fact: "tier", op: "in", value: ["RED", "AMBER"] }` |
| `contains` | List contains value | `{ fact: "symptoms", op: "contains", value: "anxiety" }` |

### Actions (`then` block)

```yaml
then:
  tier: RED                      # Required: RED, AMBER, GREEN, or BLUE
  pathway: CRISIS_ESCALATION     # Required: Pathway identifier
  explain: "Human-readable explanation for clinicians and audit log."
  booking:
    self_book_allowed: false     # Whether patient can self-book
  flags:
    - type: SUICIDE_RISK         # Flag type for clinical review
      severity: CRITICAL         # CRITICAL, HIGH, MEDIUM, LOW
```

#### Action Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tier` | string | Yes | Triage tier: `RED`, `AMBER`, `GREEN`, `BLUE` |
| `pathway` | string | Yes | Clinical pathway identifier |
| `explain` | string | No | Human-readable explanation |
| `booking.self_book_allowed` | boolean | No | Self-booking permission (overridden by safeguards) |
| `flags[]` | array | No | Risk flags to create |

## Fact Structure

Facts are derived from questionnaire responses and calculated scores.

```python
facts = {
    "scores": {
        "phq9": {
            "total": 15,
            "item9_positive": True,
            "severity_band": "MODERATELY_SEVERE"
        },
        "gad7": {
            "total": 10,
            "severity_band": "MODERATE"
        },
        "auditc": {
            "total": 5,
            "above_male_threshold": True,
            "above_female_threshold": True
        }
    },
    "risk": {
        "suicidal_intent_now": False,
        "suicidal_thoughts_present": True,
        "suicide_plan": False,
        "means_access": False,
        "recent_suicide_attempt": False,
        "violence_imminent": False,
        "psychosis_severe": False,
        "new_psychosis": False,
        "mania_severe": False,
        "functional_impairment_severe": True,
        "suicide_risk_factors_count": 2,
        "any_red_amber_flag": False
    },
    "presentation": {
        "trauma_primary": False,
        "neurodevelopmental_primary": False,
        "complex_formulation_needed": False
    },
    "preferences": {
        "open_to_digital": True,
        "prefers_in_person": False
    }
}
```

### Scores Facts

| Path | Type | Description |
|------|------|-------------|
| `scores.phq9.total` | int | PHQ-9 total score (0-27) |
| `scores.phq9.item9_positive` | bool | PHQ-9 item 9 (suicidal ideation) > 0 |
| `scores.phq9.severity_band` | string | MINIMAL, MILD, MODERATE, MODERATELY_SEVERE, SEVERE |
| `scores.gad7.total` | int | GAD-7 total score (0-21) |
| `scores.gad7.severity_band` | string | MINIMAL, MILD, MODERATE, SEVERE |
| `scores.auditc.total` | int | AUDIT-C total score (0-12) |
| `scores.auditc.above_male_threshold` | bool | Score >= 5 |
| `scores.auditc.above_female_threshold` | bool | Score >= 4 |

### Risk Facts

| Path | Type | Description |
|------|------|-------------|
| `risk.suicidal_intent_now` | bool | Current suicidal intent |
| `risk.suicidal_thoughts_present` | bool | Any suicidal ideation |
| `risk.suicide_plan` | bool | Has a suicide plan |
| `risk.means_access` | bool | Access to lethal means |
| `risk.recent_suicide_attempt` | bool | Attempt in past 6 months |
| `risk.attempt_required_medical_attention` | bool | Attempt needed medical care |
| `risk.violence_imminent` | bool | Imminent violence risk |
| `risk.harm_to_others` | bool | Risk of harming others |
| `risk.access_to_weapons_or_means` | bool | Access to weapons |
| `risk.psychosis_severe` | bool | Severe psychotic symptoms |
| `risk.new_psychosis` | bool | First episode psychosis |
| `risk.command_hallucinations_harm` | bool | Voices commanding harm |
| `risk.intent_to_act_on_commands` | bool | Intent to act on commands |
| `risk.unable_to_care_for_self` | bool | Unable to perform self-care |
| `risk.mania_severe` | bool | Severe manic episode |
| `risk.dangerous_behaviour` | bool | Engaging in dangerous behaviour |
| `risk.functional_impairment_severe` | bool | Severe functional impairment |
| `risk.suicide_risk_factors_count` | int | Count of risk factors (0-5) |
| `risk.any_red_amber_flag` | bool | Any high-priority risk indicator |

## Evaluation Semantics

### Priority Order

Rules are evaluated in **ascending priority order** (lower number = higher priority):

```
Priority 10:  RED rules (crisis/urgent)
Priority 20:  AMBER rules (elevated risk)
Priority 30:  GREEN rules (routine)
Priority 40:  BLUE rules (low intensity)
```

### Evaluation Modes

#### `first_match_wins` (Default)

Evaluation stops at the first matching rule. The highest-priority match determines the outcome.

```
Rule Priority 10 (RED_SUICIDE)     → MATCH → Stop, return RED
Rule Priority 20 (AMBER_PSYCHOSIS) → Not evaluated
Rule Priority 30 (GREEN_ROUTINE)   → Not evaluated
```

#### `all_matches`

All rules are evaluated. The highest-priority match determines tier/pathway, but all flags and explanations are collected.

### Safeguard Enforcement

**Engine-level safeguards override rule configuration:**

```python
# In RulesEngine.evaluate():
if tier in (TriageTier.RED, TriageTier.AMBER):
    self_book_allowed = False          # Always blocked
    clinician_review_required = True   # Always required
```

This ensures that even if a rule incorrectly allows self-booking for RED/AMBER, the safeguard prevents it.

## Evaluation Output

```python
@dataclass
class EvaluationResult:
    tier: TriageTier                    # RED, AMBER, GREEN, BLUE
    pathway: str                        # Clinical pathway
    self_book_allowed: bool             # Can patient self-book?
    clinician_review_required: bool     # Must clinician review?
    rules_fired: list[str]              # List of matched rule IDs
    explanations: list[str]             # Human-readable explanations
    flags: list[dict]                   # Risk flags for review
    ruleset_version: str                # Ruleset version (e.g., "1.0.0")
    ruleset_hash: str                   # SHA256 of ruleset content
    evaluation_context: dict            # Metadata (rules evaluated, etc.)
```

### Example Output

```python
EvaluationResult(
    tier=TriageTier.RED,
    pathway="CRISIS_ESCALATION",
    self_book_allowed=False,
    clinician_review_required=True,
    rules_fired=["RED_SUICIDE_INTENT_PLAN_MEANS"],
    explanations=["Active suicidal intent with plan and access to means identified."],
    flags=[{"type": "SUICIDE_RISK", "severity": "CRITICAL"}],
    ruleset_version="1.0.0",
    ruleset_hash="a1b2c3d4e5f6...",  # 64-char SHA256
    evaluation_context={
        "total_rules_evaluated": 25,
        "matches_found": 1,
        "evaluation_mode": "first_match_wins",
        "fact_keys": ["scores", "risk", "presentation", "preferences"]
    }
)
```

## Change Control

### Ruleset Versioning

Rulesets follow semantic versioning:
- **MAJOR**: Breaking changes to rule logic or tier assignments
- **MINOR**: New rules added, non-breaking enhancements
- **PATCH**: Documentation, explanation text, typo fixes

### Deployment Process

1. **Create new ruleset file** with incremented version
2. **Run validation tests** against golden test cases
3. **Register in database** with new hash
4. **Set `is_active = true`** for the new version
5. **Set `is_active = false`** for the previous version

### Database Registration

```sql
INSERT INTO ruleset_definitions (
    id, ruleset_id, version, content_hash, is_active, filename, content_json, rule_count
) VALUES (
    'uuid-here',
    'uk-private-triage',
    '1.0.1',
    'sha256-hash-here',
    true,
    'uk-private-triage-v1.0.1.yaml',
    '{"ruleset": {...}}',
    25
);

-- Deactivate previous version
UPDATE ruleset_definitions
SET is_active = false
WHERE ruleset_id = 'uk-private-triage' AND version = '1.0.0';
```

### Audit Trail

Every triage evaluation records:
- `ruleset_version`: Which ruleset version was used
- `ruleset_hash`: SHA256 hash for integrity verification
- `rules_fired`: Exactly which rules matched
- `explanations`: Why each rule fired

This enables:
- Retrospective analysis of triage decisions
- Investigation of adverse events
- Regulatory compliance (CQC)
- A/B testing of ruleset changes

### Testing Requirements

Before deploying a ruleset change:

1. **Unit tests pass** for all scoring algorithms
2. **Golden tests pass** for expected tier assignments
3. **Regression tests pass** for safeguard enforcement
4. **Clinical review** of any tier-affecting changes

### Rollback Procedure

If issues are detected post-deployment:

```sql
-- Reactivate previous version
UPDATE ruleset_definitions
SET is_active = true
WHERE ruleset_id = 'uk-private-triage' AND version = '1.0.0';

-- Deactivate problematic version
UPDATE ruleset_definitions
SET is_active = false
WHERE ruleset_id = 'uk-private-triage' AND version = '1.0.1';
```

## Clinical Pathways

| Pathway ID | Description | Typical Tier |
|------------|-------------|--------------|
| `CRISIS_ESCALATION` | Immediate crisis intervention | RED |
| `PSYCHIATRY_ASSESSMENT` | Psychiatric evaluation needed | AMBER |
| `SUBSTANCE_PATHWAY` | Substance use assessment | AMBER |
| `THERAPY_ASSESSMENT` | Standard therapy intake | GREEN |
| `TRAUMA_THERAPY_PATHWAY` | Trauma-focused therapy | GREEN |
| `NEURODEVELOPMENTAL_TRIAGE` | ADHD/ASD assessment | GREEN |
| `LOW_INTENSITY_DIGITAL` | Digital/self-guided resources | BLUE |

## Risk Flag Types

| Type | Description |
|------|-------------|
| `SUICIDE_RISK` | Suicidal ideation or behaviour |
| `VIOLENCE_RISK` | Risk of violence to others |
| `PSYCHOSIS` | Psychotic symptoms present |
| `MANIA` | Manic episode indicators |
| `SUBSTANCE_USE` | Problematic substance use |
| `SAFEGUARDING` | Child or vulnerable adult concerns |
| `COMPLEXITY` | Complex presentation requiring MDT |

## Risk Severity Levels

| Severity | Description | Action Required |
|----------|-------------|-----------------|
| `CRITICAL` | Immediate danger | Same-day response |
| `HIGH` | Significant risk | Priority review |
| `MEDIUM` | Moderate concern | Standard review |
| `LOW` | Minor indicator | Note for assessment |

## Code References

- **Rules Engine**: `app/rules/engine.py`
- **Ruleset Loader**: `app/rules/loader.py`
- **Triage Service**: `app/services/triage.py`
- **Scoring Service**: `app/services/scoring.py`
- **Models**: `app/models/score.py`, `app/models/disposition.py`, `app/models/ruleset.py`
- **Tests**: `tests/test_rules_engine.py`, `tests/test_scoring.py`, `tests/test_safeguards.py`

## Compliance Notes

- All tier assignments are logged with full audit trail
- Ruleset changes require clinical governance approval
- RED/AMBER cases automatically flagged for clinician review
- Self-booking blocked for elevated risk cases
- CQC inspection-ready audit logging

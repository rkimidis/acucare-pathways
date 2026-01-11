# CQC Inspection Walkthrough Guide

This document provides step-by-step demonstration scenarios for CQC inspections.
Each scenario is repeatable and generates evidence artifacts.

## Quick Start

```bash
# Run all scenarios
python scripts/cqc_demo.py all

# Run individual scenario
python scripts/cqc_demo.py scenario1

# Export evidence to custom directory
python scripts/cqc_demo.py all --output-dir /path/to/evidence
```

---

## Scenario 1: "Show me how you identify and manage suicide risk"

**KLOE**: Safe - S1, S2 | Effective - E1

### Steps to Demonstrate

1. **Create test patient → Start intake**
   - Navigate to: Staff Dashboard → New Intake
   - Create patient with test identifier

2. **Answer suicide risk questions**
   - Suicidal intent now: **YES**
   - Suicide plan: **YES**
   - Access to means: **YES**
   - PHQ-9 item 9 (self-harm thoughts): **Nearly every day (3)**

3. **Submit intake**

### Expected System Evidence

| Check | Expected Value |
|-------|---------------|
| Case tier | **RED** |
| Self-booking | **Disabled** |
| Dashboard position | **Top of queue** |
| SLA countdown | **2 hours** |
| Rule fired | `RED_SUICIDE_INTENT_PLAN_MEANS` |

### Audit Events to Show

```
[T+0s]   INTAKE_SUBMITTED
[T+1s]   TRIAGE_EVALUATED → rule: RED_SUICIDE_INTENT_PLAN_MEANS
[T+1s]   TIER_ASSIGNED → RED
[T+1s]   ESCALATION_FLAG_SET
[T+1s]   SELF_BOOKING_DISABLED
[T+2s]   DUTY_CLINICIAN_NOTIFIED
```

### Staff Workflow to Demonstrate

1. Show RED case at top of dashboard queue
2. Click into case → show decision rationale
3. Show contact attempt documentation
4. Show incident creation (if unable to reach)

### Artifacts to Export

- `scenario1_case_decision_<timestamp>.json` - Rules fired + timestamps
- `scenario1_audit_trail_<timestamp>.json` - Complete audit trail

---

## Scenario 2: "What happens if someone deteriorates while waiting?"

**KLOE**: Safe - S1, S3 | Responsive - R2

### Steps to Demonstrate

1. **Create GREEN case with future appointment**
   - Tier: GREEN
   - Pathway: Therapy Assessment
   - Appointment: 3 weeks out

2. **Trigger weekly check-in** (day 7)
   - In staging: Admin → Trigger Check-in
   - Or wait for scheduled job

3. **Patient responds with worsening**
   - PHQ-2 Q1: Nearly every day (3)
   - PHQ-2 Q2: Nearly every day (3)
   - Suicidal thoughts: **Yes (passive)**
   - Wellbeing: 2/10

### Expected System Evidence

| Check | Expected Value |
|-------|---------------|
| New tier | **AMBER** (escalated from GREEN) |
| Queue | Moved to **Duty Queue** |
| Original appointment | Flagged for review |
| Rule fired | `AMBER_PASSIVE_SI_WITH_RISK_FACTORS` |

### Audit Events to Show

```
[Day 7 09:00]  CHECKIN_SENT
[Day 7 15:00]  CHECKIN_REMINDER_SENT
[Day 7 16:32]  CHECKIN_RESPONSE_RECEIVED
[Day 7 16:32]  CHECKIN_EVALUATED → PHQ-2: 6, passive SI: true
[Day 7 16:32]  ESCALATION_RULE_FIRED → AMBER_PASSIVE_SI_WITH_RISK_FACTORS
[Day 7 16:32]  TIER_ESCALATED → GREEN to AMBER
[Day 7 16:33]  MOVED_TO_DUTY_QUEUE
[Day 7 16:33]  DUTY_CLINICIAN_NOTIFIED
```

### Key Points for Inspector

- Automated monitoring catches deterioration
- Escalation happens in real-time (< 1 minute)
- Duty clinician notified immediately
- Original appointment flagged, not cancelled

---

## Scenario 3: "How do you ensure the right clinician sees the right patient?"

**KLOE**: Effective - E1, E2 | Well-led - W3

### Steps to Demonstrate

1. **Create intake with psychosis indicators**
   - New psychotic symptoms: **Yes**
   - Hallucinations: **Present**
   - Delusions: **Present**

2. **Submit intake**

### Expected System Evidence

| Check | Expected Value |
|-------|---------------|
| Tier | **AMBER** |
| Pathway | **PSYCHIATRY_ASSESSMENT** |
| Available slots | Psychiatrists only |
| Booking mode | Staff-only (no self-book) |
| Rule fired | `AMBER_NEW_PSYCHOSIS` |

### Scheduling Constraints to Demonstrate

```
Available clinician types:   [PSYCHIATRIST]
Excluded clinician types:    [THERAPIST, PSYCHOLOGIST, NURSE]
Booking mode:                STAFF_ONLY
Reason:                      AMBER tier + PSYCHIATRY_ASSESSMENT pathway
```

### Audit Events to Show

```
[T+0]   INTAKE_SUBMITTED
[T+1s]  PATHWAY_ASSIGNED → PSYCHIATRY_ASSESSMENT
        Rationale: "New psychotic symptoms detected"
[T+1s]  CLINICIAN_TYPE_CONSTRAINT_SET → PSYCHIATRIST
[T+2s]  CASE_ADDED_TO_PSYCHIATRY_QUEUE
```

### Key Points for Inspector

- Pathway determined by clinical rules, not manual selection
- Scheduling automatically constrained to appropriate clinicians
- Audit trail shows reasoning for pathway assignment

---

## Scenario 4: "Show me governance: who changed the triage rules and why?"

**KLOE**: Well-led - W1, W2, W4

### Steps to Demonstrate

1. **Show current ruleset**
   - Navigate to: Admin → Rulesets
   - Show active version: v1.0.0

2. **Propose change**
   - Click: Propose Change
   - Modify PHQ-9 item 9 threshold: 10 → 5
   - Add rationale: "Earlier intervention needed"
   - Submit

3. **Show approval workflow**
   - Log in as Medical Director
   - Review change diff
   - Approve with notes

4. **Show activation**
   - Confirm new version active
   - Show previous version archived

### Expected System Evidence

| Check | Expected Value |
|-------|---------------|
| Self-approval | **Blocked** |
| Approver role required | Medical Director |
| Diff shown | Yes |
| Rationale required | Yes |

### Change Control Log Structure

```json
{
  "change_request": {
    "submitted_by": "clinical.governance@clinic.nhs.uk",
    "submitted_at": "2024-01-15T10:30:00Z",
    "change_summary": "Lower PHQ-9 item 9 threshold",
    "rationale": "Clinical review identified need for earlier intervention"
  },
  "approval": {
    "approver": "dr.medical.director@clinic.nhs.uk",
    "approved_at": "2024-01-15T14:00:00Z",
    "notes": "Approved following clinical governance committee review"
  },
  "activation": {
    "previous_version": "1.0.0",
    "new_version": "1.0.1"
  }
}
```

### Audit Events to Show

```
[T+0]     RULESET_CHANGE_PROPOSED → v1.0.1
[T+1s]    CHANGE_DIFF_GENERATED
[T+1s]    APPROVAL_REQUESTED
[T+2h]    APPROVAL_GRANTED by dr.medical.director@clinic.nhs.uk
[T+2h 1s] RULESET_ACTIVATED → v1.0.1
[T+2h 1s] PREVIOUS_VERSION_ARCHIVED → v1.0.0
```

### Key Points for Inspector

- All changes require clinical rationale
- Self-approval is blocked
- Full diff recorded for audit
- Historical cases retain original version reference

---

## Evidence Export Commands

### Export All Evidence for Date Range

```bash
# Export audit events
curl -X POST /api/v1/evidence/export \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"start_date": "2024-01-01", "end_date": "2024-01-31", "type": "audit"}'

# Export case decisions
curl -X POST /api/v1/evidence/export \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"start_date": "2024-01-01", "end_date": "2024-01-31", "type": "decisions"}'

# Export change control log
curl -X POST /api/v1/evidence/export \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"type": "change_control"}'
```

### Verify Export Integrity

```bash
# Check tamper-evident hash
python -c "
from app.services.evidence_export import verify_export_integrity
result = verify_export_integrity('export_20240115.json')
print(f'Valid: {result.valid}')
print(f'Hash: {result.computed_hash}')
"
```

---

## Quick Reference: Rule → Tier → Pathway

| Rule ID | Tier | Pathway | Self-Book |
|---------|------|---------|-----------|
| `RED_SUICIDE_INTENT_PLAN_MEANS` | RED | CRISIS_ESCALATION | No |
| `RED_RECENT_SERIOUS_ATTEMPT` | RED | CRISIS_ESCALATION | No |
| `AMBER_PHQ9_ITEM9_POSITIVE_MODERATE_OR_HIGH` | AMBER | DUTY_CLINICIAN_REVIEW | No |
| `AMBER_NEW_PSYCHOSIS` | AMBER | PSYCHIATRY_ASSESSMENT | No |
| `GREEN_MODERATE_DEPRESSION_OR_ANXIETY` | GREEN | THERAPY_ASSESSMENT | Yes |
| `BLUE_MILD_SYMPTOMS_DIGITAL` | BLUE | LOW_INTENSITY_DIGITAL | Yes |

---

## Contact for Demo Support

For assistance running demos during CQC inspection:
- Technical: tech.support@clinic.nhs.uk
- Clinical Governance: clinical.governance@clinic.nhs.uk

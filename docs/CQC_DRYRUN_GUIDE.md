# CQC Dry-Run Walkthrough Guide

**Purpose:** Rehearsal guide for CQC inspection demonstration
**Participants:** Clinician + Non-technical Observer
**Duration:** 45-60 minutes
**Focus:** Clarity, not architecture

---

## Before You Start

### Prerequisites
```bash
# Ensure you're in the project directory
cd "C:\projects\acucare pathways"

# Verify the demo script works
python scripts/cqc_demo.py --help
```

### Participants
- **Clinician:** Will validate clinical appropriateness
- **Observer:** Will note anything confusing to a non-technical inspector

### Materials Needed
- Laptop with system access
- Notepad for clarity issues
- This guide

---

## Walkthrough Script

### Introduction (2 minutes)

**Say to the inspector (practice this):**

> "AcuCare Pathways is our digital triage and monitoring system. It helps us:
> 1. Safely triage new patient enquiries using validated questionnaires
> 2. Monitor patients on our waiting list for deterioration
> 3. Maintain complete audit trails for governance
>
> I'll show you four scenarios that demonstrate how we handle patient safety."

---

## Scenario 1: Suicide Risk Identification

**Run:**
```bash
python scripts/cqc_demo.py scenario1
```

**What to explain:**

1. **Patient completes intake questionnaire**
   - "The patient answered validated screening questions including PHQ-9 and safety questions"

2. **System assigns RED tier**
   - "Because the patient indicated suicidal intent with a plan and access to means, the system automatically assigned RED tier"
   - Point to the rule that fired: `RED_SUICIDE_INTENT_PLAN_MEANS`

3. **Self-booking disabled**
   - "RED tier patients cannot self-book appointments - this is enforced by the system"
   - "A clinician must book on their behalf after review"

4. **Audit trail**
   - "Every step is logged with timestamps"
   - Show the audit events with actor, action, and timestamp

**Questions the inspector might ask:**
- Q: "What if the system fails?"
- A: "We have business continuity procedures for manual triage. The system defaults to requiring clinician review if uncertain."

- Q: "Who reviews RED cases?"
- A: "The duty clinician within 4 hours. I can show you the duty queue."

**Clarity check (Observer):** Note anything confusing about this output.

---

## Scenario 2: Deterioration While Waiting

**Run:**
```bash
python scripts/cqc_demo.py scenario2
```

**What to explain:**

1. **GREEN case on waiting list**
   - "This patient was initially triaged as GREEN - standard priority"

2. **Weekly check-in sent**
   - "We automatically send PHQ-2, GAD-2 and safety questions weekly"

3. **Patient reports worsening**
   - "The patient indicated suicidal ideation in their check-in"

4. **Automatic escalation to AMBER**
   - "The system immediately escalated to AMBER tier"
   - "Self-booking was disabled"
   - "A CRITICAL alert was created in the duty queue"

5. **Audit trail of monitoring**
   - "Complete record of: check-in sent, response received, escalation triggered"

**Questions the inspector might ask:**
- Q: "How quickly does escalation happen?"
- A: "Immediately upon submission - within seconds"

- Q: "What if the patient doesn't complete check-ins?"
- A: "Missed check-ins are tracked. After 2 consecutive misses, an alert is raised for staff follow-up."

**Clarity check (Observer):** Was the escalation flow clear?

---

## Scenario 3: Pathway Routing

**Run:**
```bash
python scripts/cqc_demo.py scenario3
```

**What to explain:**

1. **Patient indicates psychosis symptoms**
   - "First-episode psychotic symptoms require psychiatric assessment"

2. **System routes to PSYCHIATRY_ASSESSMENT pathway**
   - "The pathway determines what type of appointment is needed"
   - "This ensures the right clinician sees the patient"

3. **Booking restrictions**
   - "AMBER cases can only be booked by staff, not self-booked"

**Questions the inspector might ask:**
- Q: "How do you ensure the right clinician is available?"
- A: "The scheduling system matches pathway requirements to clinician specialties"

**Clarity check (Observer):** Is pathway routing explained clearly?

---

## Scenario 4: Change Control

**Run:**
```bash
python scripts/cqc_demo.py scenario4
```

**What to explain:**

1. **Clinical rules are version-controlled**
   - "Any changes to triage rules require formal approval"

2. **Self-approval blocked**
   - "The person who submits a change cannot approve it"

3. **Approval workflow**
   - "A different clinician must review and approve"
   - "Rejection requires a rationale"

4. **Audit trail**
   - "Complete record of who submitted, who approved/rejected, and when"

5. **Cases retain ruleset version**
   - "Each case records which ruleset version was used for triage"

**Questions the inspector might ask:**
- Q: "Who can approve rule changes?"
- A: "Only users with CLINICAL_LEAD or ADMIN roles"

- Q: "How do you test changes before going live?"
- A: "We have a staging environment. Changes are tested with golden-path test cases before activation."

**Clarity check (Observer):** Is the governance process clear?

---

## Export Evidence Bundle

**Run:**
```bash
python scripts/cqc_demo.py export --days 30 --output-dir ./evidence
```

**What to explain:**

1. **Comprehensive export**
   - "This generates a complete evidence bundle for any date range"

2. **Tamper-evident**
   - "Each export includes a SHA-256 hash chain"
   - "Any modification would be detectable"

3. **Includes**
   - Audit logs
   - Incident records
   - Ruleset approval history
   - Reporting summary

**Show the output directory:**
```bash
dir evidence
```

---

## Post-Walkthrough Debrief

### For the Clinician

1. Were the triage rules clinically appropriate?
2. Were escalation thresholds correct?
3. Any patient safety concerns?

### For the Observer

1. What was unclear or confusing?
2. What would an inspector struggle to understand?
3. Any jargon that needs plain English?

### Clarity Issues Log

| Scenario | Issue | Suggested Fix |
|----------|-------|---------------|
| | | |
| | | |
| | | |

---

## Common Inspector Questions (Prepare Answers)

### Safe

| Question | Answer |
|----------|--------|
| How do you identify patients at risk of suicide? | Validated PHQ-9 item 9 + direct safety questions in intake |
| What happens when risk is identified? | Automatic RED tier, self-booking blocked, duty clinician review |
| How do you monitor waiting patients? | Weekly PHQ-2/GAD-2 + safety check-ins, auto-escalation on deterioration |

### Effective

| Question | Answer |
|----------|--------|
| How do you ensure evidence-based triage? | Validated instruments (PHQ-9, GAD-7, AUDIT-C), deterministic rules |
| How do you track outcomes? | Disposition tracking, pathway completion, no-show rates |
| How do you learn from incidents? | Incident workflow with lessons learned, preventive actions |

### Well-led

| Question | Answer |
|----------|--------|
| How do you control changes to clinical rules? | Formal approval workflow, self-approval blocked, complete audit trail |
| How do you ensure staff competence? | Role-based access, mandatory training before system access |
| How do you maintain audit trails? | Append-only audit events, tamper-evident exports, SHA-256 verification |

---

## Final Checklist

Before actual CQC inspection:

- [ ] All scenarios run without errors
- [ ] Clinician comfortable with explanations
- [ ] Observer confirmed clarity
- [ ] Clarity issues fixed
- [ ] Evidence export tested and verified
- [ ] Backup plan if system unavailable

---

*Guide version: 1.0*
*Last rehearsal date: ___________*
*Issues resolved: ___________*

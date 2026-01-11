# Clinical Sign-Off Pack

**Purpose:** Clinical governance documentation for AcuCare Pathways
**Audience:** Clinical Lead, Medical Director, Caldicott Guardian
**Version:** 1.0

---

## 1. Triage Rules Summary (Non-Technical)

### How the System Assigns Triage Tiers

The system uses a **rules-based approach** (not AI) to assign patients to one of four triage tiers based on their questionnaire responses. Rules are evaluated in priority order - higher-risk rules are checked first.

### Tier Definitions

| Tier | Meaning | Response Target | Self-Booking |
|------|---------|-----------------|--------------|
| **RED** | Immediate safety concern | 4 hours | Not allowed |
| **AMBER** | Significant risk or complexity | 72 hours | Not allowed |
| **GREEN** | Standard presentation | 2 weeks | Allowed |
| **BLUE** | Low intensity / digital suitable | 2 weeks | Allowed |

### What Triggers Each Tier

#### RED Tier (Immediate Safety)
A patient is assigned RED if ANY of these are true:
- Active suicidal intent with a plan AND access to means
- Recent serious suicide attempt requiring medical attention
- Command hallucinations with intent to act on them
- Imminent violence risk with access to weapons
- Severe psychosis with inability to care for self
- Severe mania with dangerous behaviour

#### AMBER Tier (Urgent/Complex)
A patient is assigned AMBER if ANY of these are true:
- New psychotic symptoms (first episode)
- Bipolar indicators or mania red flags
- Severe depression (PHQ-9 score 20+)
- Moderate depression with failed previous treatment
- Moderate anxiety with significant impairment
- Substance misuse with withdrawal risk
- History of psychiatric admission within 6 months

#### GREEN Tier (Standard Care)
A patient is assigned GREEN if:
- Mild to moderate depression or anxiety
- Stable presentation
- No active safety concerns
- Suitable for standard psychological therapy

#### BLUE Tier (Low Intensity)
A patient is assigned BLUE if:
- Mild symptoms only
- Good functioning
- Suitable for digital CBT or guided self-help

### Key Safety Features

1. **Fail-Safe Default:** If no rules match, system defaults to GREEN (not BLUE), ensuring clinical review
2. **Override Capability:** Clinicians can override any tier with documented rationale
3. **Audit Trail:** Every decision is logged with timestamp and rule that fired
4. **Human Review:** RED and AMBER cases always require clinician review before booking

---

## 2. Escalation Flow Diagram

```
                    PATIENT COMPLETES INTAKE
                              |
                              v
                    +-------------------+
                    | Rules Engine      |
                    | Evaluates Answers |
                    +-------------------+
                              |
              +---------------+---------------+
              |               |               |
              v               v               v
         +-------+       +---------+     +---------+
         |  RED  |       |  AMBER  |     |GREEN/BLUE|
         +-------+       +---------+     +---------+
              |               |               |
              v               v               v
    +-----------------+ +-------------+ +--------------+
    | CRISIS          | | DUTY QUEUE  | | SELF-BOOKING |
    | ESCALATION      | | for Review  | | AVAILABLE    |
    | Immediate call  | | 72hr SLA    | | 2-week SLA   |
    +-----------------+ +-------------+ +--------------+


                    PATIENT ON WAITING LIST
                              |
                              v
                    +-------------------+
                    | Weekly Check-In   |
                    | (PHQ-2, GAD-2,    |
                    |  Safety Questions)|
                    +-------------------+
                              |
              +---------------+---------------+
              |                               |
              v                               v
    +-------------------+           +-------------------+
    | DETERIORATION     |           | STABLE            |
    | DETECTED:         |           | Continue waiting  |
    | - SI reported     |           | Next check-in     |
    | - PHQ-2 >= 3      |           | scheduled         |
    | - GAD-2 >= 3      |           +-------------------+
    | - Patient request |
    +-------------------+
              |
              v
    +-------------------+
    | ESCALATE TO AMBER |
    | - Disable self-book|
    | - Add to duty queue|
    | - Create alert     |
    | - Audit logged     |
    +-------------------+
              |
              v
    +-------------------+
    | DUTY CLINICIAN    |
    | REVIEWS WITHIN    |
    | 72 HOURS          |
    +-------------------+
```

---

## 3. What Happens If Someone Deteriorates

### Scenario: Patient reports suicidal thoughts during weekly check-in

**Step 1: Immediate Detection**
- Patient completes weekly PHQ-2/GAD-2 check-in via SMS/email link
- Patient indicates "Yes" to suicidal ideation question
- System immediately flags the response

**Step 2: Automatic Escalation (within seconds)**
- Case tier changed from GREEN/BLUE to AMBER
- Self-booking disabled
- Alert created with CRITICAL severity
- Case added to top of duty queue
- Audit event logged: "System escalated case to AMBER due to deterioration: suicidal_ideation"

**Step 3: Clinician Notification**
- Duty clinician sees new CRITICAL alert on dashboard
- Alert shows: "Suicidal ideation reported - Immediate review required"
- Patient's full history and check-in responses visible
- SLA clock starts: 72-hour response target

**Step 4: Clinical Response**
- Duty clinician reviews case
- Contacts patient by phone (number on file)
- Documents outcome in system
- Either:
  - Books urgent appointment (staff-booked, not self-book)
  - Escalates to crisis team if imminent risk
  - De-escalates with rationale if false positive

**Step 5: Audit & Governance**
- Complete trail available:
  - Original check-in submission time
  - Automatic escalation time
  - Alert acknowledgement time
  - Clinical response time
  - Outcome and rationale
- Available for CQC inspection at any time

### What if the clinician misses the alert?

- Unacknowledged alerts remain at top of queue
- Daily summary includes open alerts
- SLA breach tracking for governance review
- Incident workflow available if harm occurs

---

## 4. Known Limitations

### Clinical Limitations

| Limitation | Mitigation |
|------------|------------|
| **Questionnaire-based only:** System cannot detect non-verbal cues or observe behaviour | Clinician review required for RED/AMBER; check-ins include free-text comments |
| **Self-reported data:** Patients may under-report or over-report symptoms | Validated instruments (PHQ-9, GAD-7) with known psychometric properties |
| **Language barriers:** Questionnaires in English only (v1) | Interpreter services available for clinical appointments |
| **Digital access required:** Patients need smartphone/email | Reception can assist with phone-based intake |
| **Point-in-time assessment:** Symptoms may change between check-ins | Weekly monitoring; patients can request callback anytime |

### System Limitations

| Limitation | Mitigation |
|------------|------------|
| **No AI/ML predictions:** System uses deterministic rules only | Rules clinically validated; no black-box decisions |
| **Single ruleset:** One ruleset for all patient populations | Rules designed for UK private adult psychiatry; paediatric/specialist may need adaptation |
| **SMS/Email delivery:** Messages may fail | Delivery tracking; staff follow-up for missed check-ins |
| **Database dependency:** System requires database availability | Standard infrastructure resilience; backup procedures |

### What This System Does NOT Do

- Does NOT replace clinical judgement
- Does NOT make treatment decisions
- Does NOT contact emergency services automatically
- Does NOT store appointment clinical notes (separate EHR)
- Does NOT integrate with NHS systems (private practice only)

---

## 5. Clinical Sign-Off

By signing below, I confirm that I have:

1. Reviewed the triage rules and agree they are clinically appropriate
2. Understood the escalation pathways and response requirements
3. Reviewed the known limitations and accept the residual risk
4. Agreed that the system is safe for clinical use with the stated mitigations

| Role | Name | GMC/HCPC | Date | Signature |
|------|------|----------|------|-----------|
| Clinical Lead | | | | |
| Medical Director | | | | |
| Clinical Safety Officer | | | | |

### Conditions of Sign-Off

- [ ] Staff training completed before go-live
- [ ] Emergency escalation procedures documented
- [ ] Out-of-hours coverage confirmed
- [ ] Incident response procedure in place
- [ ] Review scheduled at 3 months post go-live

---

*Document version: 1.0*
*Clinical review date: ___________*
*Next review due: 12 months from sign-off*

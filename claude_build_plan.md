Below is a **development plan** for a UK private, CQC-registered psychiatric triage platform with associated apps. It’s written to be executable: phases, milestones, deliverables, roles, and the “definition of done” for each step. I’ll assume you’re building with Claude Code and want a **safe, auditable MVP fast**, then scale.

---

## 0) Product scope and delivery approach

### Product surfaces

1. **Patient Web Portal (MVP)** – intake, consent, booking, reminders, check-ins
2. **Staff Web Console (MVP)** – triage dashboard, case review, scheduling, messaging, audit
3. **Mobile apps (Phase 3+)** – optional; start with web (mobile-first) to reduce risk

### Delivery approach

* **Modular monolith first**, cleanly separated modules internally.
* Deterministic triage (rules engine) first; LLM only for **draft summaries** later.
* Strong governance from day 1: audit logs, versioned rules/forms, DPIA/security baseline.

---

## 1) Workstreams (run in parallel)

1. **Clinical & Governance**

* Triage tiers, pathways, escalation protocol
* Clinical content: questionnaires, safety messaging, templates
* Governance: policies, audits, incident workflow, training

2. **Platform Engineering**

* Infrastructure, security, CI/CD, observability, backups
* Core data model, RBAC, audit/eventing

3. **Application Development**

* Patient portal
* Staff console
* Messaging/scheduling integration
* Reporting

4. **Quality & Compliance**

* DPIA, security testing, clinical safety testing
* Pen test readiness
* CQC evidence pack

---

## 2) Phase plan (with deliverables)

### Phase 0 — Discovery + Clinical specification (1–2 weeks)

**Goal:** Freeze “what the clinic does” into implementable rules.

**Deliverables**

* Service map: pathways offered (psychiatry/psychology/therapy/nursing/ND/addiction)
* Triage tiers + SLAs + duty clinician responsibilities
* Escalation playbook (RED/AMBER): who calls, timeframe, what’s documented
* Questionnaire set (MVP) + scoring definitions
* Patient comms templates (invite, reminders, risk banner, waiting-list deterioration)
* Data retention and access principles (UK GDPR aligned)
* Clinical sign-off on:

  * deterministic rules approach
  * “not an emergency service” copy placement
  * safeguarding triggers

**Definition of done**

* A single signed-off spec doc: pathways + tiers + escalation + questionnaires + outputs.

---

### Phase 1 — Foundations (2–3 weeks)

**Goal:** Build the secure skeleton: identity, data model, audit, environments.

**Engineering deliverables**

* Repo structure + coding standards + linting + test framework
* Environments: dev/staging/prod (UK region)
* CI/CD pipeline (build, test, deploy)
* Auth:

  * Patients: magic link
  * Staff: MFA + RBAC
* Postgres schema v1 + migrations
* Audit event stream (append-only) wired into key actions
* Basic object storage for uploads/PDFs
* Observability: logs + metrics + alerting baseline
* Backup + restore plan (tested at least once in staging)

**Product deliverables**

* Clickable shell UIs for Patient + Staff (navigation + empty states)

**Definition of done**

* A staff user can log in with MFA; a patient can log in with magic link.
* Create/view a triage case end-to-end with audit events recorded.

---

### Phase 2 — Clinical Triage MVP (3–5 weeks)

**Goal:** Functioning triage: intake → scoring → rules → clinician review → disposition.

**Core features**

1. **Digital intake**

   * Consent capture
   * Branching questionnaires (MVP set)
   * Save/resume
   * Safety banner on key pages
2. **Scoring service**

   * PHQ-9, GAD-7, AUDIT-C (plus your chosen add-ons)
   * Store form version + computed score version
3. **Deterministic rules engine**

   * Versioned rulesets (YAML/JSON)
   * Produces tier + pathway + “rules fired”
   * Unit tests for every critical rule
4. **Staff triage dashboard**

   * Queues by tier with SLA countdowns
   * Case summary view (scores, flags, raw answers)
   * Disposition editor with rationale + override logging
5. **Clinical documentation outputs**

   * Triage summary note template
   * PDF export (or EHR message export)

**Definition of done**

* A real patient can complete intake on mobile.
* System assigns tier/pathway deterministically.
* Duty clinician can review and disposition within the console.
* All decisions are audit-trailed and linked to ruleset/form versions.

---

### Phase 3 — Scheduling, Messaging, and Payments (3–5 weeks)

**Goal:** Turn triage into booked care with minimal admin work.

**Features**

* Scheduling:

  * clinician availability management (slot types)
  * self-booking for GREEN/BLUE only
  * staff booking for AMBER/RED only
  * calendar sync optional (later)
* Messaging:

  * invite links
  * appointment reminders
  * “what to do if you worsen” messages
  * delivery receipts and failure handling
* Payments (if applicable):

  * deposits / session payment
  * invoice/receipt generation
  * refund/cancellation rules

**Operational controls**

* No-show policy workflow
* Cancellation and rescheduling flows
* Safe auto-messaging guardrails (never reassuring crisis content)

**Definition of done**

* 80%+ of routine patients can go from enquiry → booked appointment without staff calls.
* Messaging and booking events are visible in the case timeline.

---

### Phase 4 — Waiting-list monitoring + step-up logic (2–4 weeks)

**Goal:** Reduce risk and cost while patients wait; create “step up when needed”.

**Features**

* Automated weekly check-ins (PHQ-2/GAD-2 + risk check)
* Deterioration alerts to duty clinician queue
* “Still want appointment?” reconfirmation to reduce no-shows
* Step-up rules:

  * e.g., move from therapy to psychiatry if non-response or flags
* Outcome tracking basics: baseline vs follow-up trend charts

**Definition of done**

* Deterioration creates an AMBER item in the dashboard with clear next actions.
* Clear evidence trail for “monitoring while waiting” (CQC-friendly).

---

### Phase 5 — Reporting, QA, and CQC evidence pack (2–4 weeks, overlaps)

**Goal:** Make the system inspectable and continuously improving.

**Features**

* Reporting dashboards:

  * volumes by pathway/tier
  * wait times & SLA breaches
  * conversion rates
  * no-shows
  * outcomes (PROMs)
* Governance tools:

  * ruleset change log (who changed what, when, why)
  * incident management workflow
  * audit exports
* Clinical QA:

  * random sampling review workflow
  * false positive/negative review for triage rules

**Definition of done**

* You can demonstrate Safe/Effective/Well-led with system artifacts:

  * audit logs
  * incident process
  * monitoring process
  * change control records

---

### Phase 6 — Mobile apps (optional; do only if web isn’t enough)

**Goal:** Improve engagement, reminders, check-ins, secure messaging.

**Approach**

* Start with **PWA** enhancements first (push notifications)
* If native is required:

  * React Native app for patients only (staff stays web)
  * Same API + auth flows
  * Offline-lite for questionnaires (optional)

**Definition of done**

* App adds measurable benefit (completion rate, attendance, check-in adherence).

---

## 3) Engineering milestones and “hard gates” (don’t skip)

### Gate A — Clinical safety gate (before real patient use)

* Triage rules unit tested + reviewed
* RED/AMBER escalation flows tested with simulated cases
* No self-booking possible for escalated tiers
* Emergency banners present in all required places

### Gate B — Security gate

* MFA enforced for staff
* Pen test (or at least professional vulnerability scan) before going live
* Secrets management, least privilege, encrypted storage
* Audit log integrity verified

### Gate C — Operational readiness gate

* Backups/restore tested
* On-call/incident procedure for system downtime
* Monitoring alerts configured (queue backlog, SMS failures, 500 errors)

---

## 4) Team plan (even if you’re solo, these hats must be covered)

* Product owner (you)
* Clinical lead / duty clinician (sign-off + governance)
* Engineer(s) (backend, frontend)
* Security/compliance support (DPIA + pen test)
* Ops/admin rep (workflow realism)

---

## 5) Suggested timeline (pragmatic)

If you’re building intensely:

* MVP triage (Phases 0–2): **6–10 weeks**
* Booking + messaging (Phase 3): **+3–5 weeks**
* Monitoring + reporting (Phases 4–5): **+4–8 weeks**
* Apps (Phase 6): **only if needed**

(Those are “calendar” ranges; you can compress if scope is tight.)

---

## 6) What to build first (highest leverage backlog)

1. Data model + audit events (foundation)
2. Intake forms + scoring
3. Deterministic rules engine + tests
4. Staff triage queue + disposition workflow
5. Messaging + booking automation
6. Waiting-list monitoring
7. Reporting + governance

---

## 7) Deliverable checklist you can paste into your project board

### MVP checklist

* [ ] Patient magic-link login
* [ ] Staff login with MFA + RBAC
* [ ] Intake wizard with consent + safety banners
* [ ] Scoring (PHQ-9, GAD-7, AUDIT-C)
* [ ] Rules engine v1 (versioned) + unit tests
* [ ] Triage dashboard (queues + SLA)
* [ ] Case view (summary + raw answers + timeline)
* [ ] Disposition + override rationale (logged)
* [ ] Audit events for key actions
* [ ] PDF triage summary export
* [ ] Backups + restore tested in staging

### Post-MVP

* [ ] Self-booking (GREEN/BLUE) + staff booking (AMBER/RED)
* [ ] SMS/email invites + reminders + receipts
* [ ] Waiting list check-ins + deterioration alerts
* [ ] Incident workflow + governance exports
* [ ] Reporting dashboards

---

If you want, I can turn this into a **detailed sprint plan** (Sprint 1–6) with user stories and acceptance criteria, and I can also generate a **risk register** tailored to CQC/UK GDPR (clinical, legal, and technical).




Below is a **delivery-grade Sprint Plan (Sprint 1–6)** with **explicit user stories, acceptance criteria**, and a **CQC / UK GDPR–tailored risk register**.
This is written so you can **paste it directly into Jira / Linear / GitHub Projects** and then use **Claude Code** to generate each component systematically.

---

# DELIVERY MODEL ASSUMPTIONS

* **Sprint length:** 2 weeks
* **Team:** You (+ optional reviewer)
* **Architecture:** Modular monolith (FastAPI or NestJS), web-first
* **Definition of Done (global):**

  * Code merged to main
  * Unit tests passing
  * Audit events written
  * Security checks pass
  * Clinically safe behaviour verified (for triage logic)

---

# SPRINT 1 — PLATFORM FOUNDATIONS & GOVERNANCE

**Goal:** Secure, inspectable skeleton that CQC would accept as a clinical system.

---

## Epic: Identity, Access, Audit, Data Model

### Story 1.1 — Staff authentication with MFA

**As a** staff member
**I want** secure login with MFA
**So that** access to clinical data is protected

**Acceptance criteria**

* Staff login requires email + password + MFA
* Roles supported: Admin, Duty Triage Clinician, Psychiatrist, Psychologist, Therapist, Nurse, Reception
* Failed login attempts logged
* MFA enforcement cannot be disabled for staff

---

### Story 1.2 — Patient magic-link authentication

**As a** patient
**I want** simple login without passwords
**So that** access barriers are low

**Acceptance criteria**

* Magic link sent via email/SMS
* Link expires after configurable time
* Login events are audit logged
* No staff-only endpoints accessible

---

### Story 1.3 — Core data model & migrations

**As a** developer
**I want** a stable clinical data model
**So that** future features don’t break auditability

**Acceptance criteria**

* Postgres schema includes:

  * patients, referrals, triage_cases
  * questionnaire_definitions (versioned)
  * questionnaire_responses
  * audit_events (append-only)
* All schema changes via migrations
* No hard deletes on clinical data

---

### Story 1.4 — Immutable audit event framework

**As a** governance lead
**I want** all significant actions logged
**So that** CQC inspections are defensible

**Acceptance criteria**

* Audit events written for:

  * login
  * case creation
  * intake submission
  * triage decision
  * override
  * message sent
* Audit events are append-only
* Cannot be edited or deleted via UI

---

**Sprint 1 Exit Criteria**

* Staff + patient authentication works
* A triage case can be created
* Audit log shows full lifecycle
* Deployed to dev + staging

---

# SPRINT 2 — DIGITAL INTAKE & CONSENT

**Goal:** Collect clinically usable data safely and legally.

---

## Epic: Intake, Consent, Safety Messaging

### Story 2.1 — Patient intake wizard

**As a** patient
**I want** a guided intake form
**So that** I can explain my needs clearly

**Acceptance criteria**

* Mobile-first UI
* Save-and-resume supported
* Branching logic based on answers
* Completion time < 10 minutes (median)

---

### Story 2.2 — Consent & legal statements

**As a** clinic
**I want** explicit consent capture
**So that** UK GDPR and CQC requirements are met

**Acceptance criteria**

* Consent checkboxes for:

  * assessment
  * messaging
  * data sharing
* Capacity assumption statement shown
* Consent timestamped and stored
* Consent version stored

---

### Story 2.3 — Safety & emergency messaging

**As a** patient
**I want** clear emergency guidance
**So that** I know what to do if I’m unsafe

**Acceptance criteria**

* “Not an emergency service” banner on:

  * intake start
  * high-risk questions
  * submission confirmation
* Emergency instructions shown when high-risk answers selected

---

### Story 2.4 — Questionnaire versioning

**As a** clinical lead
**I want** versioned questionnaires
**So that** scoring decisions are auditable

**Acceptance criteria**

* Questionnaire definitions versioned
* Responses tied to version
* Old versions still renderable for audit

---

**Sprint 2 Exit Criteria**

* A patient completes intake end-to-end
* Consent stored and reviewable
* Safety messaging demonstrably present

---

# SPRINT 3 — SCORING & DETERMINISTIC TRIAGE ENGINE

**Goal:** Safe, explainable triage decisions.

---

## Epic: Scoring, Rules, Risk Stratification

### Story 3.1 — Clinical score computation

**As a** clinician
**I want** validated scores
**So that** decisions are evidence-based

**Acceptance criteria**

* PHQ-9, GAD-7, AUDIT-C implemented
* Scores stored with severity bands
* Unit tests for each score

---

### Story 3.2 — Deterministic triage rules engine

**As a** clinic
**I want** explainable triage decisions
**So that** patient routing is safe and auditable

**Acceptance criteria**

* Rules defined in versioned YAML/JSON
* Engine outputs:

  * tier (RED/AMBER/GREEN/BLUE)
  * pathway
  * rules fired
* Rule evaluation unit-tested
* Ruleset version stored on case

---

### Story 3.3 — Automatic escalation safeguards

**As a** duty clinician
**I want** unsafe cases blocked from self-booking
**So that** patients are protected

**Acceptance criteria**

* RED/AMBER disable self-booking
* Escalation banner shown to staff
* Clinical safety event logged

---

**Sprint 3 Exit Criteria**

* Intake → score → tier → pathway works automatically
* Rules explainability visible in staff UI
* No black-box AI involved in decisions

---

# SPRINT 4 — STAFF TRIAGE DASHBOARD & CLINICAL OVERSIGHT

**Goal:** Enable safe human oversight where required.

---

## Epic: Clinical Review & Disposition

### Story 4.1 — Triage dashboard

**As a** duty clinician
**I want** a prioritised queue
**So that** urgent cases are handled first

**Acceptance criteria**

* Queues grouped by tier
* SLA countdown visible
* RED/AMBER visually distinct

---

### Story 4.2 — Case review & disposition

**As a** clinician
**I want** to confirm or override triage
**So that** clinical judgement is applied

**Acceptance criteria**

* One-page case summary
* Override requires rationale
* Original rules preserved
* Override audit logged

---

### Story 4.3 — Clinical documentation output

**As a** clinician
**I want** an auto-generated triage note
**So that** admin time is reduced

**Acceptance criteria**

* Draft summary generated from structured data
* Editable before finalisation
* PDF export available
* Stored in document store

---

**Sprint 4 Exit Criteria**

* Duty clinician can manage entire triage workload
* Clear accountability trail exists
* Notes are exportable

---

# SPRINT 5 — BOOKING, MESSAGING & WAITING-LIST SAFETY

**Goal:** Convert triage into care safely and efficiently.

---

## Epic: Scheduling, Communications, Monitoring

### Story 5.1 — Role-aware scheduling

**As a** patient
**I want** to book appropriate appointments
**So that** I see the right clinician

**Acceptance criteria**

* GREEN/BLUE: self-book
* AMBER/RED: staff-only booking
* Clinician availability respected

---

### Story 5.2 — Messaging automation

**As a** clinic
**I want** automated communications
**So that** admin effort is reduced

**Acceptance criteria**

* Invite, reminder, follow-up templates
* SMS + email supported
* Delivery status tracked
* Messages logged to case

---

### Story 5.3 — Waiting-list monitoring

**As a** clinic
**I want** to detect deterioration
**So that** patients don’t become unsafe while waiting

**Acceptance criteria**

* Weekly PHQ-2/GAD-2 sent
* Risk check included
* Deterioration escalates to AMBER
* Audit event created

---

**Sprint 5 Exit Criteria**

* End-to-end: enquiry → booked appointment
* Evidence of “monitoring while waiting” exists

---

# SPRINT 6 — GOVERNANCE, REPORTING & CQC READINESS

**Goal:** Inspection-ready, measurable, improvable system.

---

## Epic: QA, Reporting, Risk Management

### Story 6.1 — Governance & incident workflow

**As a** clinic lead
**I want** incident tracking
**So that** learning is documented

**Acceptance criteria**

* Incidents linkable to cases
* Status workflow (open/reviewed/closed)
* Learning notes stored

---

### Story 6.2 — Reporting dashboards

**As a** manager
**I want** operational insight
**So that** services improve

**Acceptance criteria**

* Reports:

  * volumes by tier/pathway
  * wait times
  * no-shows
  * outcomes
* Exportable for inspection

---

### Story 6.3 — Rules & form change governance

**As a** regulator
**I want** evidence of change control
**So that** safety is maintained

**Acceptance criteria**

* Ruleset change log
* Questionnaire version history
* Named approver for changes

---

**Sprint 6 Exit Criteria**

* CQC Safe / Effective / Well-led evidence demonstrable
* DPIA completed
* System ready for live patients

---

# CQC & UK GDPR RISK REGISTER

## Clinical Risks

| Risk                        | Impact | Mitigation                                                         |
| --------------------------- | ------ | ------------------------------------------------------------------ |
| Missed suicide risk         | Severe | Deterministic rules, mandatory SI questions, duty clinician review |
| Over-reliance on automation | High   | Human override + rationale required                                |
| Deterioration while waiting | High   | Weekly monitoring + escalation                                     |
| Wrong clinician routing     | Medium | Pathway eligibility rules + audit                                  |

---

## Legal / Regulatory Risks

| Risk                     | Impact | Mitigation                                   |
| ------------------------ | ------ | -------------------------------------------- |
| UK GDPR breach           | Severe | DPIA, RBAC, encryption, audit                |
| Lack of consent evidence | High   | Versioned consent capture                    |
| Inadequate audit trail   | High   | Append-only audit events                     |
| CQC non-compliance       | High   | Explicit safety workflows + evidence exports |

---

## Technical Risks

| Risk              | Impact | Mitigation                                  |
| ----------------- | ------ | ------------------------------------------- |
| Rules regression  | High   | Unit tests + versioning                     |
| Data loss         | High   | Backups + restore drills                    |
| SMS/email failure | Medium | Delivery tracking + alerts                  |
| LLM hallucination | Medium | No autonomous decisions, clinician approval |

---

## Operational Risks

| Risk                     | Impact | Mitigation                      |
| ------------------------ | ------ | ------------------------------- |
| Staff misuse of override | Medium | Mandatory rationale + QA review |
| Alert fatigue            | Medium | Threshold tuning + batching     |
| System downtime          | High   | Monitoring + incident playbook  |

---

## FINAL NOTE (IMPORTANT)

When using **Claude Code**, treat these as **generation units**:

* One sprint = one prompt bundle
* Generate code **per story**, not per sprint
* Lock schemas, rules, and audits early

If you want next:

* **Sprint-by-sprint Claude Code prompt templates**
* **Rules engine YAML + test cases**
* **CQC inspection walkthrough (“show me how the system handles X”)**

Say the word and I’ll generate them.



Cool — I’ll give you (1) **Sprint-by-sprint Claude Code prompt packs** you can paste directly, (2) a **versioned ruleset YAML spec + example rules**, (3) **unit test cases** (pytest-style, FastAPI-flavoured), and (4) a **CQC inspection walkthrough script** (“show me how…” scenarios).

I’m going to assume **FastAPI + Postgres + Alembic + Redis queue**. If you’re using NestJS instead, say so and I’ll translate the prompts/tests.

---

## A) Sprint-by-sprint Claude Code prompt packs (paste-ready)

### Global “project guardrails” prompt (use at the start of every sprint)

```text
You are building a UK private psychiatric clinic platform (CQC-registered) with a patient portal and staff console.

Non-negotiables:
- UK GDPR: least privilege RBAC, encryption in transit, no public DB, auditability.
- CQC “Safe/Well-led”: append-only audit log, versioned questionnaires + rulesets, explicit risk escalation workflow.
- Triage decisions MUST be deterministic and explainable. No AI for tier/pathway decisions.
- LLM (if used later) only drafts summaries; requires clinician approval.

Tech assumptions:
- Backend: FastAPI + Postgres + Alembic migrations + SQLAlchemy.
- Queue: Redis + RQ (or Celery).
- Frontend: Next.js (patient + staff).
- All core actions emit audit events.

Output expectations:
- Provide code changes as concrete files with paths.
- Include unit tests for clinical scoring and rule evaluation.
- Include minimal docs in /docs (README, runbook, decision log).

Start by listing planned files/paths, then produce code.
```

---

### Sprint 1 prompt pack — Foundations (Auth, RBAC, Audit, Core schema)

```text
Using the global guardrails, implement Sprint 1.

Scope:
1) Backend skeleton FastAPI:
- /app/main.py, /app/api router structure, /app/core config
- SQLAlchemy base + Alembic migrations
- Models: users, roles, permissions, patients, referrals, triage_cases, audit_events
- Auth:
  - Staff: email/password + MFA placeholder endpoints (store mfa_enabled + otp_secret but actual OTP can be stubbed)
  - Patient: magic link login (token table + expiry)
- RBAC middleware enforcing permissions on staff endpoints
- Audit event writer:
  - append-only
  - record actor_id, actor_type (staff/patient), action, entity_type, entity_id, timestamp, metadata JSON

2) Frontend shells (Next.js):
- /apps/patient and /apps/staff basic navigation and auth pages (can be minimal)
- Shared component library optional

Acceptance criteria:
- Staff can log in; patient magic link flow works.
- Creating a triage case emits audit events.
- No clinical data is hard-deleted.

Deliver:
- Alembic migration scripts
- pytest tests for audit append-only and auth token expiry
- /docs/ARCHITECTURE.md and /docs/SECURITY_BASELINE.md
```

---

### Sprint 2 prompt pack — Intake + Consent + Questionnaire versioning

```text
Implement Sprint 2 on top of Sprint 1.

Backend:
- QuestionnaireDefinition model (id, name, version, schema_json, active)
- QuestionnaireResponse model (case_id, definition_id, version, answers_json, submitted_at)
- Consent model (patient_id, consent_version, channels, agreed_at)
- Endpoints:
  - GET active intake definition
  - POST intake response (validates against schema)
  - POST consent capture
- Safety banner text stored as config and returned by API

Frontend (patient):
- Intake wizard rendering JSON schema (use a simple renderer)
- Save/resume draft (store partial answers)
- Consent step with required checkboxes
- Emergency banner appears on start + confirmation + risk section

Tests:
- Questionnaire versioning test (old versions remain retrievable)
- Consent capture test (timestamp + version stored)
- Validation test for required fields

Docs:
- /docs/CLINICAL_CONTENT.md describing intake sections and safety messaging placement
```

---

### Sprint 3 prompt pack — Scoring + Deterministic Rules Engine (versioned)

```text
Implement Sprint 3.

Backend:
1) Scoring module:
- Implement PHQ-9, GAD-7, AUDIT-C scoring with severity bands.
- Store Score records linked to case_id + response_id + score_version.

2) Rules engine:
- Rulesets stored as YAML in /rulesets/*.yaml and registered in DB with hash/version.
- Engine loads active ruleset, evaluates in priority order:
  - Produces tier (RED/AMBER/GREEN/BLUE), pathway, rules_fired[], explanations[].
- Store outputs in RiskFlag and DispositionDraft tables.

3) Safeguards:
- If tier in {RED, AMBER}, mark case as clinician_review_required and disable self-booking.

Tests:
- Unit tests for each score calculation
- Golden tests for rule evaluation (given inputs -> expected tier/pathway + rules fired)
- Regression tests ensuring RED blocks self-booking

Docs:
- /docs/RULES_ENGINE.md with YAML schema, evaluation semantics, and change control
```

---

### Sprint 4 prompt pack — Staff triage dashboard + disposition + audit

```text
Implement Sprint 4.

Backend:
- Triage dashboard endpoints:
  - list cases by tier with SLA timers
  - get case summary (scores, risk flags, responses)
- Disposition:
  - clinician can confirm draft or override tier/pathway
  - override requires rationale
  - store DispositionFinal with clinician_id + rationale + timestamp
- Generate a “triage note” draft from structured data (no LLM yet):
  - template-based narrative
  - export PDF to object storage

Frontend (staff):
- Triage queue view (filters, SLA countdown)
- Case detail view with “rules fired” and raw answers tabs
- Disposition editor requiring rationale for override
- Download PDF note

Tests:
- Override requires rationale
- Audit events emitted for review + override + export
- Permission tests: receptionist cannot override clinical disposition

Docs:
- /docs/TRIAGE_WORKFLOW.md (end-to-end)
```

---

### Sprint 5 prompt pack — Scheduling + Messaging + waiting list monitoring

```text
Implement Sprint 5.

Backend:
- Scheduling:
  - Clinician profiles with role, specialties, availability slots
  - Appointment types and booking rules:
    - GREEN/BLUE self-book enabled
    - RED/AMBER staff-only
- Messaging:
  - Templates (invite, reminder, check-in)
  - Provider abstraction (SMS/email) with delivery receipts
- Monitoring:
  - Weekly check-in scheduler for waiting cases
  - Check-in includes PHQ-2/GAD-2 + risk check
  - Deterioration escalates to AMBER and adds to triage queue

Frontend:
- Patient: booking page, reminders, check-in form
- Staff: availability management, appointment list, monitoring alerts

Tests:
- Self-book blocked for RED/AMBER
- Delivery receipt updates message status
- Deterioration triggers AMBER + audit event
```

---

### Sprint 6 prompt pack — Governance, reporting, CQC evidence exports + optional LLM summaries

```text
Implement Sprint 6.

Backend:
- Incident workflow: open/review/close incidents linked to cases
- Reporting:
  - volumes by tier/pathway
  - wait times + SLA breaches
  - no-shows
  - outcome trends
- Change control:
  - ruleset approval records (who approved, why, when)
  - questionnaire definition version history UI
- Evidence export:
  - audit export for a date range
  - “show me the pathway for this case” export (decision + rules fired + timestamps)

Optional:
- LLM summary service that drafts clinician note from structured data:
  - requires clinician approval
  - logs prompt version + model + hash

Tests:
- Export contains correct audit events and is tamper-evident (hash)
- Ruleset changes require approver role
- Incident workflow permissions validated

Docs:
- /docs/CQC_EVIDENCE_PACK.md listing screenshots/exports to show inspectors
```

---

## B) Rules engine YAML spec + example ruleset (buildable)

### YAML schema (simple, auditable)

```yaml
ruleset:
  id: "uk-private-triage-v1"
  version: "1.0.0"
  created_at: "2026-01-11"
  author: "Clinical Lead"
  evaluation:
    mode: "first_match_wins"   # evaluate rules in order
    default:
      tier: "GREEN"
      pathway: "THERAPY_ASSESSMENT"
rules:
  - id: "RED_SUICIDE_INTENT_PLAN_MEANS"
    priority: 10
    when:
      all:
        - fact: "risk.suicidal_intent_now"     # boolean facts extracted from intake
          op: "=="
          value: true
        - fact: "risk.suicide_plan"
          op: "=="
          value: true
        - fact: "risk.means_access"
          op: "=="
          value: true
    then:
      tier: "RED"
      pathway: "CRISIS_ESCALATION"
      flags:
        - type: "SUICIDE_RISK"
          severity: "HIGH"
      explain: "Active suicidal intent with plan and access to means."

  - id: "AMBER_PHQ9_ITEM9_POSITIVE_MODERATE"
    priority: 20
    when:
      all:
        - fact: "scores.phq9.item9_positive"
          op: "=="
          value: true
        - fact: "scores.phq9.total"
          op: ">="
          value: 10
        - fact: "risk.suicidal_intent_now"
          op: "=="
          value: false
    then:
      tier: "AMBER"
      pathway: "DUTY_CLINICIAN_REVIEW"
      flags:
        - type: "SUICIDE_RISK"
          severity: "MEDIUM"
      explain: "PHQ-9 item 9 positive with at least moderate depression; requires clinician review."

  - id: "GREEN_ANXIETY_DEPRESSION_LOW_RISK_DIGITAL"
    priority: 50
    when:
      all:
        - fact: "risk.any_red_amber_flag"
          op: "=="
          value: false
        - fact: "scores.phq9.total"
          op: "<="
          value: 14
        - fact: "scores.gad7.total"
          op: "<="
          value: 14
    then:
      tier: "GREEN"
      pathway: "THERAPY_OR_DIGITAL_CBT"
      flags: []
      explain: "Low-to-moderate anxiety/depression without acute risk; route to therapy/digital CBT."

  - id: "PSYCHIATRY_GATE_PSYCHOSIS_BIPOLAR"
    priority: 30
    when:
      any:
        - fact: "risk.new_psychosis"
          op: "=="
          value: true
        - fact: "risk.mania_red_flag"
          op: "=="
          value: true
    then:
      tier: "AMBER"
      pathway: "PSYCHIATRY_ASSESSMENT"
      flags:
        - type: "COMPLEXITY"
          severity: "HIGH"
      explain: "Possible psychosis or bipolar spectrum; psychiatry assessment required."
```

### Minimal evaluation semantics (what your engine should do)

* Extract a `facts` dict from responses + scores:

  * `scores.phq9.total`, `scores.phq9.item9_positive`, etc.
  * `risk.*` booleans from direct questions
* Evaluate rules by ascending `priority` (or file order)
* First match wins; record `rules_fired = [rule.id]` and `explain`
* Always store `ruleset_id + version + hash`

---

## C) Unit tests (pytest) for scoring + rules engine

### 1) PHQ-9 scoring tests (example)

```python
# tests/test_scoring_phq9.py
from app.scoring.phq9 import score_phq9

def test_phq9_total_and_item9_positive():
    # items 1..9 each 0-3
    answers = {f"phq9_{i}": 1 for i in range(1, 10)}
    answers["phq9_9"] = 2
    result = score_phq9(answers)

    assert result.total == 10  # 8*1 + 2 = 10
    assert result.item9_positive is True
    assert result.severity in ("moderate", "moderately_severe", "severe")
```

### 2) Rules evaluation “golden tests”

```python
# tests/test_rules_engine.py
from app.rules.engine import evaluate_ruleset
from app.rules.loader import load_ruleset

def test_red_suicide_intent_plan_means_triggers_red():
    ruleset = load_ruleset("rulesets/uk-private-triage-v1.yaml")
    facts = {
        "risk.suicidal_intent_now": True,
        "risk.suicide_plan": True,
        "risk.means_access": True,
        "scores.phq9.item9_positive": True,
        "scores.phq9.total": 18,
        "risk.any_red_amber_flag": True
    }
    decision = evaluate_ruleset(ruleset, facts)

    assert decision.tier == "RED"
    assert decision.pathway == "CRISIS_ESCALATION"
    assert "RED_SUICIDE_INTENT_PLAN_MEANS" in decision.rules_fired
    assert "Active suicidal intent" in decision.explanations[0]

def test_amber_item9_positive_moderate_triggers_amber():
    ruleset = load_ruleset("rulesets/uk-private-triage-v1.yaml")
    facts = {
        "risk.suicidal_intent_now": False,
        "risk.suicide_plan": False,
        "risk.means_access": False,
        "scores.phq9.item9_positive": True,
        "scores.phq9.total": 12,
        "risk.any_red_amber_flag": True
    }
    decision = evaluate_ruleset(ruleset, facts)

    assert decision.tier == "AMBER"
    assert decision.pathway == "DUTY_CLINICIAN_REVIEW"
    assert "AMBER_PHQ9_ITEM9_POSITIVE_MODERATE" in decision.rules_fired

def test_green_low_risk_routes_to_therapy_or_digital():
    ruleset = load_ruleset("rulesets/uk-private-triage-v1.yaml")
    facts = {
        "risk.any_red_amber_flag": False,
        "scores.phq9.total": 8,
        "scores.gad7.total": 9,
        "risk.suicidal_intent_now": False,
        "risk.new_psychosis": False,
        "risk.mania_red_flag": False
    }
    decision = evaluate_ruleset(ruleset, facts)

    assert decision.tier == "GREEN"
    assert decision.pathway == "THERAPY_OR_DIGITAL_CBT"
```

### 3) Safety safeguard test: RED/AMBER blocks self-book

```python
# tests/test_booking_safeguards.py
from app.booking.policy import can_patient_self_book

def test_red_blocks_self_booking():
    assert can_patient_self_book(tier="RED") is False

def test_amber_blocks_self_booking():
    assert can_patient_self_book(tier="AMBER") is False

def test_green_allows_self_booking():
    assert can_patient_self_book(tier="GREEN") is True
```

---

## D) CQC inspection walkthrough (scripts + “show me” evidence)

This is a **repeatable demo** you can run in staging.

### Scenario 1: “Show me how you identify and manage suicide risk”

**Steps**

1. Create a test patient → start intake
2. Answer SI: **intent now + plan + means**
3. Submit intake

**Expected system evidence**

* Case tier = **RED**
* Self-booking disabled
* Dashboard shows RED case at top with SLA
* Audit events show:

  * intake submitted
  * rule fired (which one)
  * escalation required flag set
* Staff workflow:

  * duty clinician opens case
  * documents contact attempt/outcome
  * incident opened if needed

**Artifacts to export**

* Case decision export (rules fired + timestamps)
* Audit trail export for that case

---

### Scenario 2: “What happens if someone deteriorates while waiting?”

**Steps**

1. Create a GREEN case, book for 3 weeks out
2. Trigger weekly check-in (manual run in staging)
3. Patient answers worsening + SI passive

**Expected**

* Monitoring creates alert → escalates to **AMBER**
* Moves to duty queue
* Audit shows:

  * check-in sent
  * response received
  * escalation rule fired
  * duty clinician notified

---

### Scenario 3: “How do you ensure the right clinician sees the right patient?”

**Steps**

1. Intake indicates psychosis/bipolar red flag
2. Submit

**Expected**

* Pathway = psychiatry assessment
* Scheduling only offers psychiatrist slots (or staff-only if AMBER)
* Audit shows pathway assignment + rationale

---

### Scenario 4: “Show me governance: who changed the triage rules and why?”

**Steps**

1. Create a ruleset v1
2. Propose v1.0.1 change
3. Approver signs off
4. Activate

**Expected**

* Change control log with:

  * diff/summary
  * approver identity
  * date/time
* Cases created before change retain v1.0.0 reference

---

## E) Risk register (expanded, action-ready)

Use this as a live register with owner + review cadence.

### Clinical

* **Missed high-risk SI**
  Owner: Clinical Lead | Likelihood: Low | Impact: Severe
  Mitigation: Mandatory SI questions + deterministic escalation rules + duty review + tests
  Monitoring: monthly audit of flagged vs outcomes

* **Alert fatigue (too many AMBERs)**
  Owner: Duty Clinician | Likelihood: Medium | Impact: High
  Mitigation: tune thresholds, require protective-factor capture, batch non-urgent alerts
  Monitoring: weekly alert volume review

* **Wrong pathway (e.g., ADHD requests clog general psychiatry)**
  Owner: Ops Lead | Likelihood: Medium | Impact: Medium
  Mitigation: separate ND triage stream, clear inclusion/exclusion criteria
  Monitoring: monthly pathway leakage report

### Legal / UK GDPR

* **Unlawful processing / missing DPIA**
  Owner: Data Protection Lead | Likelihood: Medium | Impact: Severe
  Mitigation: DPIA early, data map, lawful basis documented, retention policy
  Monitoring: quarterly DPIA review on feature changes

* **Access control failure (staff see wrong cases)**
  Owner: Tech Lead | Likelihood: Low | Impact: Severe
  Mitigation: RBAC + relationship checks, automated permission tests
  Monitoring: quarterly access log review

* **Vendor risk (SMS/email provider)**
  Owner: Ops | Likelihood: Medium | Impact: High
  Mitigation: DPA with vendors, minimisation, delivery failure handling
  Monitoring: vendor review annually

### Technical

* **Rules regression**
  Owner: Tech Lead | Likelihood: Medium | Impact: High
  Mitigation: golden tests, ruleset version pinning per case, approvals
  Monitoring: CI gate + weekly change review

* **Data loss / corruption**
  Owner: Tech Lead | Likelihood: Low | Impact: Severe
  Mitigation: PITR backups + restore drills, immutable audit snapshots
  Monitoring: monthly restore drill in staging

* **Messaging failures cause missed appointments**
  Owner: Ops | Likelihood: Medium | Impact: Medium
  Mitigation: delivery receipts + retries + fallback email/SMS + dashboards
  Monitoring: daily failed message report

---

## Next thing I can generate (pick one, I’ll just do it)

1. **A full Jira/Linear import CSV** for Sprint 1–6 stories + acceptance criteria
2. A **complete ruleset pack** (v1.0.0) covering RED/AMBER/GREEN/BLUE + pathways (psychiatry/psychology/therapy/nursing/substance/ND)
3. A **ready-to-run FastAPI repo scaffold** specification (file tree + key modules) that you can feed to Claude Code to generate in one go

Tell me which one you want first (1/2/3).




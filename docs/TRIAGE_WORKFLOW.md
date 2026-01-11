# Triage Workflow Documentation

## Overview

This document describes the end-to-end triage workflow for the AcuCare Pathways system, from patient intake through disposition finalization and note export.

## Workflow Stages

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        TRIAGE WORKFLOW                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. INTAKE          2. SCORING         3. RULES ENGINE                  │
│  ┌──────────┐       ┌──────────┐       ┌──────────────┐                 │
│  │ Patient  │──────>│ PHQ-9    │──────>│ Evaluate     │                 │
│  │ Portal   │       │ GAD-7    │       │ Rules        │                 │
│  │ Q'naire  │       │ AUDIT-C  │       │              │                 │
│  └──────────┘       └──────────┘       └──────┬───────┘                 │
│                                               │                         │
│                                               ▼                         │
│  6. EXPORT          5. DISPOSITION     4. DRAFT                        │
│  ┌──────────┐       ┌──────────┐       ┌──────────────┐                 │
│  │ PDF Note │<──────│ Clinician│<──────│ Tier/Pathway │                 │
│  │ Storage  │       │ Review   │       │ Risk Flags   │                 │
│  └──────────┘       └──────────┘       └──────────────┘                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Stage Details

### 1. Patient Intake

**Actor:** Patient (via patient portal)

**Flow:**
1. Patient receives magic link (from referral or registration)
2. Patient logs in to patient portal
3. Patient completes intake questionnaire (JSON Schema rendered)
4. Patient provides consent (data processing, treatment)
5. Questionnaire response is saved and linked to triage case

**Key Components:**
- `QuestionnaireDefinition` - Active intake form definition
- `QuestionnaireResponse` - Patient's answers
- `Consent` - Captured consent records
- `TriageCase` - Created with status `PENDING`

### 2. Clinical Scoring

**Actor:** System (automatic)

**Flow:**
1. On questionnaire submission, scoring service calculates:
   - **PHQ-9** (0-27) - Depression severity
   - **GAD-7** (0-21) - Anxiety severity
   - **AUDIT-C** (0-12) - Alcohol use risk
2. Scores stored with case and response reference
3. Severity bands assigned per clinical guidelines

**Key Components:**
- `Score` - Individual score records
- `ScoringService` - PHQ9Scorer, GAD7Scorer, AUDITCScorer

**Severity Bands:**
| Score | PHQ-9 | GAD-7 | AUDIT-C |
|-------|-------|-------|---------|
| Minimal | 0-4 | 0-4 | 0-2 |
| Mild | 5-9 | 5-9 | 3 |
| Moderate | 10-14 | 10-14 | 4-7 |
| Severe | 15+ | 15+ | 8+ |

### 3. Rules Engine Evaluation

**Actor:** System (automatic)

**Flow:**
1. Facts assembled from answers and scores
2. Rules evaluated in priority order (lower = higher priority)
3. First matching rule determines tier/pathway
4. Safeguards applied:
   - RED/AMBER → `clinician_review_required = true`
   - RED/AMBER → `self_book_allowed = false`

**Key Components:**
- `RulesEngine` - Evaluates facts against YAML rulesets
- `RulesetDefinition` - Version-controlled rule files
- See [RULES_ENGINE.md](./RULES_ENGINE.md) for full documentation

**Tier Assignments:**
| Tier | SLA Target | Self-Book | Clinician Review |
|------|-----------|-----------|------------------|
| RED | 15 min | Blocked | Required |
| AMBER | 60 min | Blocked | Required |
| GREEN | 8 hours | Allowed | Optional |
| BLUE | 24 hours | Allowed | Optional |

### 4. Draft Disposition

**Actor:** System (automatic)

**Flow:**
1. `DispositionDraft` created with:
   - Tier and pathway from rules engine
   - List of rules fired
   - Explanations for each rule
   - Ruleset version and hash (for audit)
2. Risk flags created for high-priority indicators
3. Case status updated to `TRIAGED`
4. SLA timer started (deadline calculated from tier)

**Key Components:**
- `DispositionDraft` - Proposed disposition
- `RiskFlag` - Risk indicators for review
- `TriageCase.sla_deadline` - Review deadline

### 5. Clinician Review & Disposition

**Actor:** Clinician (via staff dashboard)

**Flow:**
1. Clinician views triage queue (sorted by SLA urgency)
2. Clinician opens case detail view with:
   - Patient info
   - Scores and severity bands
   - Risk flags (severity-sorted)
   - Rules fired with explanations
   - Raw questionnaire answers
3. Clinician chooses disposition action:
   - **Confirm** - Accept draft disposition as-is
   - **Override** - Change tier/pathway (REQUIRES RATIONALE)
4. `DispositionFinal` created
5. Case status updated to `CLOSED`
6. Audit event emitted

**Key Endpoints:**
- `GET /api/v1/dashboard/queue` - List queue by tier
- `GET /api/v1/dashboard/cases/{id}/summary` - Full case detail
- `POST /api/v1/dashboard/cases/{id}/disposition/confirm` - Accept draft
- `POST /api/v1/dashboard/cases/{id}/disposition/override` - Override with rationale

**Permission Requirements:**
| Action | Required Permission | Roles |
|--------|---------------------|-------|
| View Queue | `triage:read` | All staff |
| Confirm | `disposition:confirm` | Clinician, Clinical Lead, Admin |
| Override | `disposition:override` | Clinician, Clinical Lead, Admin |
| Export PDF | `disposition:export` | Clinician, Clinical Lead, Admin |

**Receptionist Restriction:**
Receptionists can VIEW triage cases but CANNOT:
- Confirm or override dispositions
- Export triage notes
- Modify clinical data

### 6. Triage Note Export

**Actor:** Clinician (via staff dashboard)

**Flow:**
1. Clinician requests PDF export
2. System generates template-based narrative (no LLM)
3. PDF created with:
   - Case summary
   - Patient info
   - Scores and interpretations
   - Risk flags
   - Disposition details
   - Override rationale (if applicable)
   - Audit metadata (ruleset version, hash)
4. PDF uploaded to object storage
5. URL stored on triage case
6. Audit event emitted

**Key Components:**
- `TriageNoteGenerator` - Template-based narrative
- `PDFExporter` - ReportLab PDF generation
- `StorageBackend` - Local or S3 storage

## SLA Management

### SLA Targets by Tier

| Tier | Target | Description |
|------|--------|-------------|
| RED | 15 minutes | Crisis - immediate clinical attention |
| AMBER | 60 minutes | Elevated risk - priority review |
| GREEN | 8 hours | Routine - standard workflow |
| BLUE | 24 hours | Low intensity - flexible timing |

### SLA Status Indicators

| Status | Meaning | UI Indicator |
|--------|---------|--------------|
| `normal` | > 60 min remaining | Green |
| `warning` | 15-60 min remaining | Yellow |
| `critical` | < 15 min remaining | Orange (pulsing) |
| `breached` | Past deadline | Red (highlighted row) |

### SLA Breach Handling

1. `sla_breached` flag set on case when deadline passed
2. Breach count displayed prominently in dashboard header
3. Breached cases highlighted in queue table
4. All breaches logged in audit trail

## Audit Trail

Every significant action is logged to `audit_events`:

| Action | Category | When |
|--------|----------|------|
| `disposition.confirm` | clinical | Disposition confirmed |
| `disposition.override` | clinical | Disposition overridden |
| `triage_note.export` | clinical | PDF note generated |
| `triage.evaluate` | clinical | Rules engine evaluation |

**Audit Event Contents:**
- Actor type and ID (staff/system)
- Action and category
- Entity type and ID
- Metadata (tier changes, rationale, etc.)
- IP address and request ID

## Data Flow Diagram

```
Patient Portal                 Backend                    Staff Dashboard
     │                            │                            │
     │  Submit Questionnaire      │                            │
     │ ──────────────────────────>│                            │
     │                            │ Calculate Scores           │
     │                            │ ─────────────────>         │
     │                            │                            │
     │                            │ Evaluate Rules             │
     │                            │ ─────────────────>         │
     │                            │                            │
     │                            │ Create Draft               │
     │                            │ ─────────────────>         │
     │                            │                            │
     │                            │ Set SLA Timer              │
     │                            │ ─────────────────>         │
     │                            │                            │
     │                            │<───────────────── Fetch Queue
     │                            │                            │
     │                            │<───────────────── Review Case
     │                            │                            │
     │                            │<───────────────── Confirm/Override
     │                            │                            │
     │                            │ Write Audit Event          │
     │                            │ ─────────────────>         │
     │                            │                            │
     │                            │<───────────────── Export PDF
     │                            │                            │
     │                            │ Store PDF                  │
     │                            │ ─────────────────>         │
```

## Error Handling

### Common Error Scenarios

| Scenario | HTTP Code | Response |
|----------|-----------|----------|
| Case not found | 404 | `{"detail": "Case {id} not found"}` |
| Already finalized | 409 | `{"detail": "Case already has a finalized disposition"}` |
| Rationale required | 422 | `{"detail": "Rationale is required when overriding"}` |
| Insufficient permissions | 403 | `{"detail": "Insufficient permissions"}` |
| Not authenticated | 401 | `{"detail": "Not authenticated"}` |

### Validation Rules

- Override rationale: minimum 10 characters, maximum 5000 characters
- Clinical notes: maximum 10,000 characters
- Tier: must be one of RED, AMBER, GREEN, BLUE
- Pathway: maximum 100 characters

## Frontend Components

### Staff Dashboard Pages

| Route | Component | Purpose |
|-------|-----------|---------|
| `/dashboard` | Dashboard | Overview with counts |
| `/dashboard/triage` | TriageQueuePage | Queue with filters |
| `/dashboard/triage/[id]` | CaseDetailPage | Full case review |

### Key UI Features

1. **Queue View:**
   - Tier filter buttons with counts
   - SLA countdown timers
   - Breach alert banner
   - Auto-refresh every 30 seconds

2. **Case Detail View:**
   - Tabbed interface (Overview, Scores, Rules, Answers, Disposition)
   - Risk flag severity indicators
   - Rules fired with explanations
   - Raw answers JSON viewer
   - PDF download button

3. **Disposition Editor:**
   - Confirm/Override mode toggle
   - Tier and pathway dropdowns
   - Required rationale textarea (for override)
   - Character count validation
   - Loading state during submission

## Integration Points

### External Systems

| System | Integration | Purpose |
|--------|-------------|---------|
| S3/MinIO | PDF Storage | Store generated triage notes |
| SMTP | Email (future) | Notification of SLA breaches |
| NHS Spine | (future) | Patient demographics lookup |

### Internal APIs

| Endpoint | Used By | Purpose |
|----------|---------|---------|
| `/api/v1/dashboard/*` | Staff frontend | Dashboard operations |
| `/api/v1/triage-cases/*` | Both portals | Case management |
| `/api/v1/audit/*` | Admin views | Audit log access |

## Compliance Notes

### CQC Requirements

- All tier assignments logged with ruleset version
- Override rationale captured and auditable
- SLA compliance tracked and reportable
- PDF notes available for inspection

### UK GDPR

- Minimum data exposure in queue views
- Audit trail for all data access
- Consent captured before processing
- Soft-delete only (no hard deletes)

## Code References

- **Models:** `app/models/disposition.py`, `app/models/triage_case.py`
- **Services:** `app/services/disposition.py`, `app/services/triage_note.py`
- **API:** `app/api/v1/dashboard.py`
- **Frontend:** `apps/staff/src/app/dashboard/triage/`
- **Tests:** `tests/test_disposition.py`

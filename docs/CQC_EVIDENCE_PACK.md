# CQC Evidence Pack

This document outlines the evidence exports and documentation available to demonstrate compliance with Care Quality Commission (CQC) regulatory requirements for AcuCare Pathways.

## Overview

AcuCare Pathways provides comprehensive audit trails, tamper-evident exports, and governance controls to support CQC inspections across all five key questions:

- **Safe** - Incident management, risk escalation, clinical safety
- **Effective** - Outcome tracking, evidence-based triage, SLA compliance
- **Caring** - Patient feedback, communication records
- **Responsive** - Wait times, pathway efficiency, accessibility
- **Well-led** - Change control, governance, audit trails

---

## 1. Audit Log Exports

### Purpose
Complete record of all system actions for audit and compliance purposes.

### Export Location
Staff Portal > Evidence Export > Audit Log Export

### Contents
- User authentication events
- Clinical decision records
- Data access logs
- System configuration changes
- Patient consent records

### Export Format
```json
{
  "manifest": {
    "export_id": "uuid",
    "export_type": "audit_log",
    "exported_by": "user-id",
    "exported_at": "ISO8601 timestamp",
    "export_reason": "CQC inspection evidence",
    "record_count": 1250,
    "content_hash": "SHA-256 hash",
    "hash_algorithm": "sha256"
  },
  "events": [
    {
      "id": "event-id",
      "timestamp": "ISO8601",
      "action": "triage.case_created",
      "category": "clinical",
      "actor_type": "user",
      "actor_id": "user-id",
      "entity_type": "triage_case",
      "entity_id": "case-id",
      "metadata": {}
    }
  ]
}
```

### Tamper Evidence
- SHA-256 chained hash computed across all records
- Hash included in manifest for integrity verification
- Verification tool available at `/api/v1/evidence/verify`

---

## 2. Case Pathway Exports

### Purpose
Complete pathway documentation for individual cases showing:
- Triage decisions made
- Rules fired during assessment
- Clinical scores and escalations
- Timestamps for all actions

### Export Location
Staff Portal > Evidence Export > Case Pathway Export

### Contents
- Case metadata (tier, status, pathway)
- All audit events for the case
- Questionnaire responses and answers
- Assessment scores and severity bands
- Risk flags identified
- Disposition decisions

### Export Format
```json
{
  "manifest": {...},
  "case": {
    "id": "case-id",
    "patient_id": "patient-id",
    "tier": "amber",
    "status": "active",
    "pathway": "anxiety",
    "created_at": "ISO8601"
  },
  "pathway_steps": [
    {
      "timestamp": "ISO8601",
      "step_type": "triage.case_created",
      "description": "Case created",
      "actor": "user-id",
      "data": {}
    }
  ],
  "audit_events": [...],
  "questionnaire_responses": [...],
  "scores": [...]
}
```

---

## 3. Incident Reports

### Purpose
Documentation of clinical incidents for CQC notification and learning.

### Export Location
Staff Portal > Incidents

### Evidence Available
- Incident reference numbers
- Severity and category classification
- Full timeline from reporting to closure
- Review notes and investigation details
- Lessons learned and preventive actions
- CQC notification tracking

### Screenshot Locations

| Evidence Type | Location |
|--------------|----------|
| Open Incidents | Dashboard > Incidents (filter: Open) |
| Incident Timeline | Incidents > [Select Incident] > Timeline |
| Closure Records | Incidents > [Select Incident] > Closure Details |
| CQC Reportable | Incidents > [Select Incident] > CQC Badge |

---

## 4. Reports & Analytics

### Purpose
Operational metrics demonstrating effective service delivery.

### Export Location
Staff Portal > Reporting

### Available Reports

#### 4.1 Volume Reports
- Cases by triage tier (RED/AMBER/GREEN/BLUE)
- Cases by clinical pathway
- Referral source breakdown

#### 4.2 Wait Time & SLA Compliance
- Average wait times by tier
- SLA target vs actual performance
- Breach counts and percentages
- Trend analysis

#### 4.3 No-Show Metrics
- Overall no-show rate
- No-shows by tier
- No-shows by appointment type

#### 4.4 Outcome Trends
- Completed cases
- Discharged patients
- Escalated cases
- Declined referrals

#### 4.5 Alert Summary
- Monitoring alerts by severity
- Resolution rates
- Response times

### Screenshot Locations

| Evidence Type | Location |
|--------------|----------|
| Volume by Tier | Reporting > Cases by Tier |
| SLA Compliance | Reporting > Wait Times & SLA |
| No-Show Stats | Reporting > No-Show Statistics |
| Outcome Trends | Reporting > Outcome Trends |

---

## 5. Change Control Evidence

### Purpose
Demonstrate controlled change management for clinical rules and questionnaires.

### Export Location
Staff Portal > Change Control

### Evidence Available

#### 5.1 Ruleset Approvals
- Change summaries and rationale
- Submitter and approver details
- Approval/rejection timestamps
- Content hash for integrity
- Activation history

#### 5.2 Questionnaire Versions
- Version history
- Change documentation
- Approval records
- Active version tracking

### Screenshot Locations

| Evidence Type | Location |
|--------------|----------|
| Pending Approvals | Change Control > Pending |
| Approval History | Change Control > History |
| Questionnaire Versions | Change Control > Questionnaires |

---

## 6. Clinical Safety Evidence

### Purpose
Demonstrate clinical safety controls and escalation pathways.

### Evidence Available

#### 6.1 Triage System
- Validated scoring instruments (PHQ-9, GAD-7)
- Evidence-based tier assignment
- Automated escalation rules

#### 6.2 Monitoring Alerts
- Deterioration detection
- PHQ-2/GAD-2 threshold monitoring
- Risk flag identification
- Automatic AMBER escalation

#### 6.3 Self-Booking Controls
- RED/AMBER tier booking restrictions
- Staff-only booking for high-risk patients
- Appointment type access controls

### Screenshot Locations

| Evidence Type | Location |
|--------------|----------|
| Alert Dashboard | Monitoring > Alerts |
| Risk Escalations | Monitoring > [Alert] > Details |
| Booking Restrictions | Scheduling > Self-Book Rules |

---

## 7. Access Controls

### Purpose
Demonstrate role-based access and data protection.

### Evidence Available
- Role definitions and permissions
- Multi-factor authentication enforcement
- Session management
- Audit trail of access events

### Permission Matrix

| Role | Create Incident | Close Incident | Approve Rules | Export Data |
|------|----------------|----------------|---------------|-------------|
| Admin | Yes | Yes | Yes | Yes |
| Clinical Lead | Yes | Yes | Yes | Yes |
| Manager | Yes | Yes | No | Yes |
| Clinician | Yes | No | No | Yes |
| Nurse | Yes | No | No | No |

---

## 8. Consent Management

### Purpose
Demonstrate proper consent collection and management.

### Evidence Available
- Consent types collected
- Consent timestamps
- Withdrawal records
- Purpose-specific consent tracking

---

## 9. Evidence Bundle Export

### Purpose
Generate a comprehensive evidence bundle combining all evidence types for CQC inspection.

### Export Location
Staff Portal > Evidence Export > Full Bundle Export

### API Endpoint
```
POST /api/v1/evidence/bundle
Body: {
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-01-31T23:59:59Z",
  "export_reason": "CQC scheduled inspection Q1 2024",
  "include_audit_log": true,
  "include_incidents": true,
  "include_ruleset_approvals": true,
  "include_reporting_summary": true
}
```

### Bundle Contents
```json
{
  "bundle_type": "cqc_evidence",
  "manifest": {
    "export_id": "uuid",
    "export_type": "evidence_bundle",
    "record_count": 1542,
    "content_hash": "SHA-256 hash",
    "sections_included": ["audit_log", "incidents", "ruleset_approvals", "reporting_summary"]
  },
  "sections": {
    "audit_log": {
      "record_count": 1200,
      "events": [...]
    },
    "incidents": {
      "record_count": 15,
      "summary": {
        "total": 15,
        "by_status": {"open": 2, "under_review": 3, "closed": 10},
        "by_severity": {"critical": 1, "high": 4, "medium": 8, "low": 2},
        "cqc_reportable": 2
      },
      "incidents": [...]
    },
    "ruleset_approvals": {
      "record_count": 5,
      "summary": {
        "total": 5,
        "by_status": {"approved": 4, "rejected": 1},
        "currently_active": 2
      },
      "approvals": [...]
    },
    "reporting_summary": {
      "available_reports": ["volumes/tier", "wait-times", "sla-breaches", ...]
    }
  }
}
```

### CLI Export
```bash
# Run CQC demo scenarios and generate evidence
python scripts/cqc_demo.py all --output-dir ./evidence

# Generate evidence bundle only
python scripts/cqc_demo.py export --days 30 --output-dir ./evidence
```

---

## 10. Export Verification

### Purpose
Verify integrity of exported evidence.

### How to Verify
1. Navigate to Evidence Export > Verify
2. Upload or paste export JSON
3. System recalculates hash
4. Comparison result displayed

### API Endpoint
```
POST /api/v1/evidence/verify
Body: { "export_data": {...} }
Response: { "is_valid": true/false, "content_hash": "...", "message": "..." }
```

---

## 11. Quick Reference - CQC Key Lines of Enquiry

### Safe (S)
| KLOE | Evidence Location |
|------|-------------------|
| S1 - Risk management | Incidents > All Reports |
| S2 - Safeguarding | Incidents > Category: Safeguarding |
| S3 - Staffing | User Management > Staff List |

### Effective (E)
| KLOE | Evidence Location |
|------|-------------------|
| E1 - Needs assessment | Case Pathway Export |
| E2 - Care delivery | Reporting > Outcomes |
| E3 - Outcomes | Reporting > Outcome Trends |

### Caring (C)
| KLOE | Evidence Location |
|------|-------------------|
| C1 - Kindness | Patient Feedback (if collected) |
| C2 - Involvement | Consent Records |

### Responsive (R)
| KLOE | Evidence Location |
|------|-------------------|
| R1 - Meeting needs | Reporting > Wait Times |
| R2 - Access | Reporting > Volumes by Pathway |

### Well-led (W)
| KLOE | Evidence Location |
|------|-------------------|
| W1 - Leadership | Change Control > Approvals |
| W2 - Governance | Audit Log Export |
| W3 - Quality improvement | Incidents > Lessons Learned |

---

## Contact

For questions about evidence exports or CQC compliance:
- Technical Support: support@acucare.example
- Clinical Governance: governance@acucare.example

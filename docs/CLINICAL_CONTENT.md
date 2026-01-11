# Clinical Content Guide

This document describes the intake questionnaire sections, safety messaging placement, and clinical content guidelines for AcuCare Pathways.

## Overview

The patient intake process is designed with safety as the primary concern. All clinical content must be reviewed and approved by the clinical lead before deployment.

## Intake Wizard Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INTAKE WIZARD FLOW                            │
└─────────────────────────────────────────────────────────────────────┘

    ┌──────────────────┐
    │  Emergency Banner │ ← Always visible at start
    │  (Safety Info)    │
    └────────┬─────────┘
             │
    ┌────────▼─────────┐
    │  Step 1: Consent  │
    │  - Data processing│
    │  - Privacy policy │
    │  - Communication  │
    └────────┬─────────┘
             │
    ┌────────▼──────────────┐
    │  Step 2: Questionnaire │
    │  - Personal info       │
    │  - Current symptoms    │
    │  - Risk assessment     │ ← Emergency banner reappears
    │  - History             │
    └────────┬──────────────┘
             │
         ┌───┴───┐
         │ Risk? │
         └───┬───┘
             │
    ┌────────┼────────┐
    │Yes             No│
    │                  │
    ▼                  ▼
┌─────────────┐  ┌────────────┐
│Risk Warning │  │Confirmation│
│+ Safety Info│  │+ Safety    │
└──────┬──────┘  │  Banner    │
       │         └─────┬──────┘
       │               │
       └───────┬───────┘
               │
    ┌──────────▼──────────┐
    │  Submission Complete │
    └─────────────────────┘
```

## Safety Messaging

### Emergency Banner

The emergency banner appears at key points throughout the intake:

| Location | When Shown | Dismissable |
|----------|------------|-------------|
| Intake Start | Always | Yes |
| Risk Questions Section | When viewing | No |
| Risk Warning Step | If risk indicators present | No |
| Confirmation Step | Always | Yes |

### Banner Content

The safety banner text is configured via environment variable `SAFETY_BANNER_TEXT`. Default text:

> If you are experiencing a mental health emergency or have thoughts of harming yourself or others, please call 999 or go to your nearest A&E. You can also contact the Samaritans 24/7 on 116 123 (free call).

### Emergency Contact Information

Always include in safety messaging:
- **999** - Emergency services
- **116 123** - Samaritans (24/7, free)
- **Text SHOUT to 85258** - Crisis Text Line
- **NHS 111** - Option 2 for mental health crisis

## Intake Sections

### 1. Consent Section

**Purpose**: Capture explicit patient consent before collecting clinical data.

**Required Consents** (must be accepted):
- Data Processing Agreement
- Privacy Policy

**Optional Consents**:
- Email Communications
- SMS Communications

**Compliance Notes**:
- Consent version is stored with timestamp
- All consent records are immutable
- Multiple consent records can exist per patient
- Re-consent required when consent version changes

### 2. Personal Information Section

**Fields**:
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Full Name | Text | Yes | Auto-filled from registration |
| Date of Birth | Date | Yes | Used for age-appropriate care |
| NHS Number | Text | No | Optional for private patients |
| GP Details | Text | No | For care coordination |
| Emergency Contact | Text | Yes | Required for safety |

### 3. Current Symptoms Section

**Fields**:
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Presenting Complaint | Textarea | Yes | Open-ended description |
| Symptom Duration | Select | Yes | Categorized options |
| Symptom Severity | Scale | Yes | 1-10 scale |
| Sleep Disturbance | Boolean | No | Common indicator |
| Appetite Changes | Boolean | No | Common indicator |

### 4. Risk Assessment Section

**CRITICAL**: This section triggers safety protocols.

**Fields**:
| Field | Type | Required | Triggers Risk Warning |
|-------|------|----------|----------------------|
| Suicidal Thoughts | Boolean | Yes | If True |
| Self-Harm | Boolean | Yes | If True |
| Thoughts of Harm to Others | Boolean | Yes | If True |
| Current Substance Use | Boolean | No | No |

**Risk Protocol**:
1. If ANY risk field is `true`, show Risk Warning step
2. Risk Warning displays full emergency contact information
3. Patient must acknowledge safety information before submitting
4. All responses with risk indicators are flagged for urgent clinical review

### 5. History Section

**Fields**:
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Previous Treatment | Boolean | No | Mental health history |
| Current Medications | Textarea | No | Include all medications |
| Allergies | Textarea | No | Important for prescribing |
| Medical Conditions | Textarea | No | Comorbidities |
| Family History | Textarea | No | Relevant mental health history |

## Questionnaire Versioning

### Version Management

- All questionnaire definitions are immutable once published
- Changes require creating a new version
- Previous versions remain retrievable for audit
- SHA256 hash ensures schema integrity

### Version Format

Use semantic versioning: `MAJOR.MINOR`
- **MAJOR**: Breaking changes to question structure
- **MINOR**: New optional fields or wording changes

### Creating New Version

1. Create new `QuestionnaireDefinition` with incremented version
2. Set `previous_version_id` to link versions
3. Set `is_active=True` on new version
4. Set `is_active=False` on old version
5. Test thoroughly before activation

## Triage Integration

### Tier Assignment

Intake responses feed into the deterministic triage engine:

| Tier | Criteria | Action |
|------|----------|--------|
| RED | Any risk indicator = true | Immediate clinical review |
| RED | Severity >= 8 + short duration | Urgent attention |
| AMBER | Moderate symptoms | Standard clinical review |
| GREEN | Low risk indicators | Self-booking available |

### Escalation Path

```
RED Tier → No self-booking → Clinical team alerted → 24h contact target
AMBER Tier → Staff approval required → 48h contact target
GREEN Tier → Self-booking OK → Standard pathway
```

## Accessibility Requirements

All clinical content must be:
- Written at reading level suitable for general public
- Available in accessible formats (screen reader compatible)
- Clear and unambiguous
- Culturally sensitive

## Content Review Process

1. **Draft**: Clinical content drafted by product team
2. **Clinical Review**: Reviewed by Clinical Lead
3. **Legal Review**: Checked for compliance
4. **Approval**: Sign-off required before deployment
5. **Version Control**: All changes tracked in questionnaire versioning

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SAFETY_BANNER_TEXT` | Emergency banner content | (see above) |
| `SAFETY_BANNER_ENABLED` | Enable/disable banner | `true` |
| `CONSENT_VERSION` | Current consent version | `1.0` |

### Updating Safety Banner

To update the safety banner text:

1. Set `SAFETY_BANNER_TEXT` in environment
2. Restart the application
3. Changes take effect immediately

No database migration or redeployment required.

## Compliance Notes

### CQC Requirements

- All clinical decisions must be explainable
- Audit trail for all patient interactions
- Risk assessment must be documented
- Escalation procedures clearly defined

### UK GDPR

- Explicit consent required before data collection
- Consent records retained indefinitely
- Patient can request their data
- Data minimization principle applied

### Clinical Safety

- Safety messaging reviewed quarterly
- Emergency contacts verified monthly
- Risk assessment criteria reviewed by clinical board
- Incident reporting for any safety concerns

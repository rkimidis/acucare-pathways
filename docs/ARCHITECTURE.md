# Architecture

## System Overview

AcuCare Pathways is designed as a **modular monolith** with clear boundaries between domains. This approach balances simplicity with the ability to extract services later if needed.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Frontend Applications                           │
│  ┌─────────────────────────┐    ┌─────────────────────────────────────┐ │
│  │   Patient Portal        │    │       Staff Console                 │ │
│  │   (Next.js :3000)       │    │       (Next.js :3001)               │ │
│  └───────────┬─────────────┘    └──────────────┬──────────────────────┘ │
└──────────────┼─────────────────────────────────┼────────────────────────┘
               │                                 │
               └─────────────┬───────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────────────┐
│                      API Gateway (FastAPI)                               │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    RBAC Middleware                                  │ │
│  │         Permission-based access control on all staff endpoints      │ │
│  └────────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ ┌────────────┐ │
│  │   Auth   │  │  Triage  │  │  Audit   │  │ Referral │ │Questionnaire│ │
│  │  Module  │  │  Module  │  │  Module  │  │  Module  │ │   Module   │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ └─────┬──────┘ │
│       │             │             │              │             │        │
├───────┴─────────────┴─────────────┴──────────────┴─────────────┴────────┤
│                         Service Layer                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │AuthService│ │AuditService││RBACService│ │RulesEngine│                 │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘                 │
├─────────────────────────────────────────────────────────────────────────┤
│                         Data Layer (SQLAlchemy 2.0)                      │
│  Users │ Roles │ Permissions │ Patients │ Referrals │ TriageCases │ ... │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │    PostgreSQL     │
                    └───────────────────┘
```

## Module Boundaries

### Auth Module (`app/api/v1/auth_*.py`, `app/api/v1/mfa.py`)
- Staff authentication (email/password + MFA)
- Patient authentication (magic links)
- Token generation and validation
- MFA setup/enable/verify/disable

### Triage Module (`app/api/v1/triage_cases.py`, `app/rules/`)
- Triage case lifecycle management
- Deterministic tier assignment via rules engine
- Escalation workflow (RED/AMBER cases)

### Audit Module (`app/api/v1/audit.py`, `app/services/audit.py`)
- Append-only event logging
- Read-only query interface
- No modification endpoints (by design)

### Referral Module (stub)
- Referral intake from various sources
- Conversion to triage cases
- Referrer tracking

### Questionnaire Module (stub)
- Versioned questionnaire definitions
- Response collection and scoring
- Links to triage cases

## Data Model

```
┌──────────────┐
│  Permissions │
└──────┬───────┘
       │ M:N
┌──────┴───────┐     M:N    ┌──────────────┐
│    Roles     │────────────│    Users     │
└──────────────┘            │   (staff)    │
                            └──────┬───────┘
                                   │
                            ┌──────┴───────┐
                            │   Referrals  │
                            └──────┬───────┘
                                   │
┌──────────────┐            ┌──────┴───────┐
│   Patients   │◀───────────│ TriageCases  │
└──────┬───────┘            └──────────────┘
       │
┌──────┴───────┐
│ MagicLinks   │
└──────────────┘

┌──────────────────────────────────────────────────────┐
│                    AuditEvents                        │
│  (append-only, no update/delete)                     │
└──────────────────────────────────────────────────────┘
```

## Authentication Flows

### Staff Authentication
```
1. POST /api/v1/auth/staff/login (email + password)
   ├── If MFA disabled → Return JWT token
   └── If MFA enabled → Return {mfa_required: true, user_id}

2. POST /api/v1/auth/staff/mfa/verify (user_id + otp_code)
   └── Return JWT token with full access
```

### Patient Authentication
```
1. POST /api/v1/auth/patient/request-magic-link (email)
   └── Creates magic link token (sent via email in prod)

2. POST /api/v1/auth/patient/login (token)
   └── Consumes token, returns JWT
```

## RBAC System

### Role Hierarchy
| Role          | Description                        | Key Permissions                |
|---------------|------------------------------------|--------------------------------|
| ADMIN         | Full system access                 | All permissions + ADMIN_ALL    |
| CLINICAL_LEAD | Clinical oversight                 | Triage + Clinical + Users read |
| CLINICIAN     | Patient care and triage            | Triage + Clinical notes        |
| RECEPTIONIST  | Patient admin                      | Patients + Triage read         |
| READONLY      | View-only access                   | Read-only on patients/triage   |

### Permission Categories
- `patients:*` - Patient data access
- `triage:*` - Triage case management
- `clinical:*` - Clinical notes
- `audit:*` - Audit log access
- `users:*` - User management
- `admin:*` - Administrative functions

## Key Design Decisions

### 1. Modular Monolith over Microservices
- Simpler deployment and debugging
- Easier to enforce transactional consistency
- Clear module boundaries allow future extraction

### 2. RBAC Middleware
- Centralized permission enforcement
- Endpoint-to-permission mapping
- Middleware intercepts all staff endpoints

### 3. Soft Delete Pattern
- Clinical data is never hard-deleted
- `is_deleted`, `deleted_at`, `deleted_by` fields
- Queryable for compliance audits

### 4. MFA Support
- TOTP-based authentication
- Backup codes for recovery
- Per-user opt-in with admin visibility

### 5. Append-only Audit Log
- CQC compliance requirement
- Immutable record of all actions
- No API endpoints for modification

## Frontend Architecture

### Patient Portal (Next.js - Port 3000)
- Magic link authentication
- Questionnaire completion
- Triage status viewing
- Appointment booking (GREEN tier)

### Staff Console (Next.js - Port 3001)
- Email/password + MFA authentication
- Triage case management
- Clinical notes
- Audit log viewing
- Patient management

Both frontends proxy API calls to the backend via Next.js rewrites.

## Future Considerations

- **Service Extraction**: Audit module could become separate service
- **Event Sourcing**: Consider for complex clinical workflows
- **Redis Caching**: Cache frequently accessed data
- **Background Jobs**: RQ/Celery for async processing
- **WebSocket**: Real-time notifications for urgent cases

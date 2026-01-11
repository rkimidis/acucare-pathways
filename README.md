# AcuCare Pathways

UK Private Psychiatric Clinic Platform (CQC-registered)

## Overview

AcuCare Pathways is a clinical platform for UK private psychiatric clinics, designed to meet CQC (Care Quality Commission) requirements and UK GDPR compliance. The platform provides:

- **Patient Portal**: Self-service triage questionnaires and appointment booking
- **Staff Console**: Clinical workflow management and case review
- **Deterministic Triage**: Rule-based tier assignment (RED/AMBER/GREEN) with full audit trail

## Key Features

- **Append-only Audit Log**: All clinical actions are recorded immutably
- **Versioned Questionnaires & Rulesets**: Full traceability for clinical decisions
- **RBAC**: Role-based access control with least-privilege principle
- **MFA Support**: TOTP-based multi-factor authentication for staff
- **Magic Link Authentication**: Passwordless patient authentication
- **Soft Delete**: Clinical data is never hard-deleted
- **Deterministic Triage**: No AI/ML - all tier decisions are rule-based and explainable

## Non-Negotiables

1. **UK GDPR**: Least privilege RBAC, encryption in transit, no public DB, auditability
2. **CQC "Safe/Well-led"**: Append-only audit log, versioned questionnaires + rulesets, explicit risk escalation
3. **Deterministic Triage**: All tier/pathway decisions are explainable, no AI
4. **LLM Usage**: If used, only for draft summaries requiring clinician approval

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Make

### Backend Setup

```bash
# Clone and enter directory
cd acucare-pathways

# Copy environment file
cp .env.example .env

# Start services
docker compose up --build -d

# Run migrations
make migrate

# Run tests
make test
```

### Frontend Setup

```bash
# Patient Portal (port 3000)
cd apps/patient
npm install
npm run dev

# Staff Console (port 3001)
cd apps/staff
npm install
npm run dev
```

### Development

```bash
# Install Python dependencies
make install

# Run backend development server (with hot reload)
make dev

# Run linting
make lint

# Run type checking
make typecheck
```

## API Documentation

When running in development mode, API docs are available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
.
├── app/
│   ├── api/          # API routes and dependencies
│   │   └── v1/       # Versioned endpoints
│   ├── core/         # Config, security, logging
│   ├── db/           # Database session and base
│   ├── middleware/   # RBAC middleware
│   ├── models/       # SQLAlchemy models
│   ├── rules/        # Deterministic triage engine
│   ├── schemas/      # Pydantic schemas
│   ├── services/     # Business logic
│   └── utils/        # Utilities
├── alembic/          # Database migrations
├── apps/
│   ├── patient/      # Patient portal (Next.js)
│   └── staff/        # Staff console (Next.js)
├── rulesets/         # YAML triage rulesets
├── tests/            # Test suite
└── docs/             # Documentation
```

## Authentication

### Staff
- Email/password login
- Optional MFA (TOTP)
- JWT tokens with role claims

### Patients
- Magic link authentication
- Single-use tokens
- Configurable expiry

## Triage Tiers

| Tier   | Description                          | Booking         |
|--------|--------------------------------------|-----------------|
| RED    | Urgent - immediate clinical review   | No self-booking |
| AMBER  | Moderate - requires clinical review  | Staff approval  |
| GREEN  | Routine - low risk                   | Self-booking OK |

## RBAC Roles

| Role          | Description                        |
|---------------|------------------------------------|
| ADMIN         | Full system access                 |
| CLINICAL_LEAD | Clinical oversight + user read     |
| CLINICIAN     | Patient care and triage            |
| RECEPTIONIST  | Patient admin, no clinical notes   |
| READONLY      | View-only access                   |

## Configuration

Key environment variables (see `.env.example`):

| Variable                       | Description                    |
|--------------------------------|--------------------------------|
| `ENV`                          | Environment (dev/staging/prod) |
| `DATABASE_URL`                 | PostgreSQL connection string   |
| `SECRET_KEY`                   | JWT signing key                |
| `PATIENT_MAGIC_LINK_TTL_MINUTES` | Magic link expiry            |
| `LOG_LEVEL`                    | Logging verbosity              |

## Testing

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
pytest tests/test_health.py -v

# Run specific test category
pytest tests/test_rbac.py -v
pytest tests/test_audit_append_only.py -v
```

## Security

See [SECURITY_BASELINE.md](docs/SECURITY_BASELINE.md) for security controls.

## Architecture

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for system design.

## Decision Log

See [DECISIONS.md](docs/DECISIONS.md) for architectural decisions.

## License

Proprietary - All rights reserved.

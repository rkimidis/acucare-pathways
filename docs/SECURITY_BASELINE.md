# Security Baseline

This document outlines the security controls implemented in AcuCare Pathways to meet UK GDPR and CQC requirements.

## Authentication

### Staff Authentication
- Email/password authentication with bcrypt hashing (cost factor 12)
- JWT tokens with configurable expiry (default 60 minutes)
- Password minimum length: 8 characters
- **MFA Support**:
  - TOTP-based (Google Authenticator, Authy compatible)
  - 10 backup codes generated on setup
  - Per-user enable/disable
- Account lockout after failed attempts (configurable)

### Patient Authentication
- Passwordless magic link authentication
- Links expire after configurable TTL (default 30 minutes)
- Single-use tokens (consumed on login)
- No password storage for patients
- IP and user agent tracking on magic link creation

## Authorization (RBAC)

### Roles
| Role          | Description                        |
|---------------|------------------------------------|
| ADMIN         | Full system access                 |
| CLINICAL_LEAD | Clinical oversight + user read     |
| CLINICIAN     | Patient care and triage            |
| RECEPTIONIST  | Patient admin, no clinical notes   |
| READONLY      | View-only access                   |

### Permission Model
- **Database-backed roles and permissions**
- Many-to-many relationship: Users ↔ Roles ↔ Permissions
- Permission codes follow `domain:action` pattern
- Examples: `triage:read`, `clinical:notes:write`, `admin:all`

### RBAC Middleware
- Centralized enforcement on all staff endpoints
- Endpoint-to-permission mapping in middleware
- Pre-flight permission checks before handler execution
- 401 for unauthenticated, 403 for unauthorized

## Data Protection

### Encryption
- **In Transit**: HTTPS/TLS required in production
- **At Rest**: Database encryption delegated to cloud provider
- **Secrets**: Environment variables, never in code
- **MFA Secrets**: Stored in database (consider HSM for production)

### Data Minimization
- Only necessary patient data collected
- Clinical data separated from administrative
- Audit logs exclude sensitive content (no passwords, tokens)

### Soft Delete
- **Clinical data is never hard-deleted**
- All patient-related models include:
  - `is_deleted` flag
  - `deleted_at` timestamp
  - `deleted_by` actor reference
- Soft-deleted records remain queryable for compliance

## Audit Trail

### Append-Only Events
- All significant actions logged
- No UPDATE or DELETE operations on audit table
- Events include: actor, action, entity, timestamp, metadata

### Logged Events
| Category | Events                                      |
|----------|---------------------------------------------|
| Auth     | login_success, login_failed, logout         |
|          | magic_link_requested, magic_link_login      |
|          | mfa_enabled, mfa_disabled, mfa_verify_*     |
| Triage   | triage_case_created, triage_case_updated    |
|          | tier_assigned, case_escalated               |
| Clinical | clinical_notes_updated                      |
| Admin    | user_created, user_updated, role_changed    |

### Event Schema
```json
{
  "id": "uuid",
  "actor_type": "staff|patient|system",
  "actor_id": "uuid",
  "actor_email": "string",
  "action": "string",
  "action_category": "auth|triage|clinical|admin",
  "entity_type": "string",
  "entity_id": "uuid",
  "metadata": {},
  "ip_address": "string",
  "user_agent": "string",
  "request_id": "string",
  "created_at": "timestamp"
}
```

## API Security

### Input Validation
- Pydantic schemas validate all input
- SQL injection prevented via ORM
- XSS prevented via JSON-only responses
- Request body size limits

### Authentication Headers
- `Authorization: Bearer <token>` for all protected endpoints
- Token includes: sub, role, actor_type, exp, iat

### Public Endpoints
Only these endpoints are accessible without authentication:
- `/` - Root
- `/api/v1/health` - Health check
- `/api/v1/auth/staff/login` - Staff login
- `/api/v1/auth/staff/mfa/verify` - MFA verification
- `/api/v1/auth/patient/request-magic-link` - Magic link request
- `/api/v1/auth/patient/login` - Patient login

## Infrastructure Security

### Database
- No public access
- Connection via private network
- Separate credentials per environment
- PostgreSQL with row-level security (optional)

### Docker
- Non-root container user (`appuser:appgroup`)
- Minimal base image (`python:3.11-slim`)
- Health checks configured
- No secrets in image layers

### Environment Separation
| Environment | Docs | Debug | MFA Required | Data |
|-------------|------|-------|--------------|------|
| dev         | Yes  | Yes   | No           | Test |
| staging     | No   | No    | Optional     | Test |
| prod        | No   | No    | Recommended  | Real |

## Compliance Checklist

### UK GDPR
- [x] Data minimization implemented
- [x] Audit trail for access logging
- [x] Soft delete for data retention
- [ ] Right to access endpoint (to implement)
- [ ] Data export endpoint (to implement)
- [ ] Data breach notification process
- [ ] DPA in place with processors

### CQC Safe/Well-led
- [x] Append-only audit log
- [x] Versioned clinical rulesets with SHA256
- [x] Deterministic triage (no AI)
- [x] Role-based access control
- [x] MFA support for staff
- [ ] Risk escalation workflow (in progress)
- [ ] Staff training records

## Incident Response

1. **Detection**: Monitor logs for anomalies
2. **Containment**: Disable affected accounts/endpoints
3. **Investigation**: Review audit logs
4. **Recovery**: Restore from backups if needed
5. **Reporting**: Notify ICO within 72 hours if required

## Security Testing

- Static analysis via ruff (security rules enabled)
- Type checking via mypy (strict mode)
- Dependency vulnerability scanning (to be configured)
- Penetration testing (scheduled annually)
- Code review required for all changes

# Architectural Decision Log

This document records significant architectural decisions for AcuCare Pathways.

---

## ADR-001: Modular Monolith Architecture

**Date**: 2024-01-01

**Status**: Accepted

**Context**:
We need to build a clinical platform that handles patient data, triage workflows, and compliance requirements. The team is small and time-to-market is important.

**Decision**:
Adopt a modular monolith architecture with clear domain boundaries rather than microservices.

**Consequences**:
- (+) Simpler deployment and operations
- (+) Easier debugging and testing
- (+) Strong consistency without distributed transactions
- (+) Clear module boundaries allow future extraction
- (-) Potential scaling limitations
- (-) Single deployment unit

---

## ADR-002: Deterministic Triage Rules Engine

**Date**: 2024-01-01

**Status**: Accepted

**Context**:
Triage tier assignment (RED/AMBER/GREEN) directly impacts patient safety. CQC requires decisions to be auditable and explainable.

**Decision**:
Implement a YAML-based deterministic rules engine. No AI/ML for tier assignment.

**Rationale**:
- Clinical decisions must be explainable
- Rules can be reviewed and approved by clinical staff
- SHA256 hashes ensure ruleset integrity
- Full audit trail of which rules triggered

**Consequences**:
- (+) 100% deterministic and explainable
- (+) Rules versioned and audited
- (+) No AI bias concerns
- (-) Requires manual rule updates
- (-) May not capture complex patterns

---

## ADR-003: Append-Only Audit Log

**Date**: 2024-01-01

**Status**: Accepted

**Context**:
CQC and UK GDPR require comprehensive audit trails. Events must not be modifiable after creation.

**Decision**:
Implement audit_events table with no UPDATE or DELETE operations exposed via API.

**Implementation**:
- `write_audit_event()` is the only way to create events
- No PUT/PATCH/DELETE endpoints for audit
- Events include actor, action, entity, metadata

**Consequences**:
- (+) Immutable audit trail for compliance
- (+) Full history of all actions
- (-) Storage grows continuously
- (-) Need archival strategy for old events

---

## ADR-004: Magic Link Patient Authentication

**Date**: 2024-01-01

**Status**: Accepted

**Context**:
Patients need secure authentication without managing passwords. Many patients may have difficulty with complex login flows.

**Decision**:
Implement passwordless magic link authentication for patients.

**Implementation**:
- Single-use tokens with configurable TTL (default 30 min)
- Token consumed on successful login
- Email delivery in production (stub in dev)
- IP/User agent tracking

**Consequences**:
- (+) No password storage for patients
- (+) Reduced friction for patient access
- (+) Email serves as second factor
- (-) Requires reliable email delivery
- (-) Subject to email security

---

## ADR-005: MFA Support for Staff

**Date**: 2024-01-01

**Status**: Accepted

**Context**:
Staff access sensitive clinical data. Additional authentication factors improve security posture and may be required for compliance.

**Decision**:
Implement optional TOTP-based MFA for staff accounts.

**Implementation**:
- Per-user opt-in (admin can view status)
- TOTP compatible with Google Authenticator, Authy
- 10 backup codes generated on setup
- OTP secret stored in database

**Consequences**:
- (+) Stronger authentication for high-privilege users
- (+) Industry-standard TOTP approach
- (+) Backup codes prevent lockout
- (-) Additional login step for users
- (-) Need secure secret storage (consider HSM for production)

---

## ADR-006: Database-Backed RBAC with Middleware

**Date**: 2024-01-01

**Status**: Accepted

**Context**:
Staff have different responsibilities requiring different access levels. CQC requires least-privilege access control.

**Decision**:
Implement database-backed roles and permissions with middleware enforcement.

**Implementation**:
- `roles` and `permissions` tables with M:N relationship
- `user_roles` junction table for user-role assignment
- RBAC middleware intercepts all staff endpoints
- Endpoint-to-permission mapping in middleware config

**Consequences**:
- (+) Fine-grained permission control
- (+) Roles can be modified without code changes
- (+) Centralized enforcement
- (-) Database query on every request
- (-) Permission mapping must be maintained

---

## ADR-007: Soft Delete Pattern

**Date**: 2024-01-01

**Status**: Accepted

**Context**:
Clinical data must be retained for compliance. Hard deletes make audit trails incomplete.

**Decision**:
Implement soft delete on all clinical models using a mixin.

**Implementation**:
- `SoftDeleteMixin` with `is_deleted`, `deleted_at`, `deleted_by`
- Applied to: User, Patient, TriageCase, Referral
- `soft_delete()` method sets fields
- Records remain queryable

**Consequences**:
- (+) Complete audit trail maintained
- (+) Data recovery possible
- (+) Compliance with retention requirements
- (-) Database grows indefinitely
- (-) Queries must filter `is_deleted`

---

## ADR-008: Separate Frontend Applications

**Date**: 2024-01-01

**Status**: Accepted

**Context**:
Patients and staff have fundamentally different needs and security requirements.

**Decision**:
Create separate Next.js applications for patient portal and staff console.

**Implementation**:
- Patient portal: `apps/patient` (port 3000)
- Staff console: `apps/staff` (port 3001)
- Both proxy API calls via Next.js rewrites
- Separate authentication flows

**Consequences**:
- (+) Clear separation of concerns
- (+) Different security policies per app
- (+) Independent deployment possible
- (-) Some code duplication
- (-) Two apps to maintain

---

## ADR-009: Referral Model for Patient Intake

**Date**: 2024-01-01

**Status**: Accepted

**Context**:
Patients arrive from various sources (GP, self-referral, NHS, insurance). Need to track referral source and convert to triage cases.

**Decision**:
Implement dedicated Referral model separate from Patient/TriageCase.

**Implementation**:
- Referral captures intake data before patient record exists
- Links to Patient once created
- Links to TriageCase when converted
- Tracks referrer information

**Consequences**:
- (+) Clear intake workflow
- (+) Referrer tracking for analytics
- (+) Supports multiple referral sources
- (-) Additional model complexity
- (-) Conversion logic needed

---

## Future Decisions Pending

- **ADR-010**: Caching strategy (Redis vs in-memory)
- **ADR-011**: Background job processing (RQ vs Celery)
- **ADR-012**: File storage for clinical documents
- **ADR-013**: Real-time notifications (WebSocket vs SSE)
- **ADR-014**: HSM integration for MFA secrets

# Security Review Checklist

**Purpose:** Pre-production security assurance for AcuCare Pathways
**Estimated Duration:** 2-5 days
**Deliverable:** Security report with findings and sign-off

---

## 1. Authentication Boundaries

### 1.1 Staff Authentication
| Check | Method | Pass/Fail | Notes |
|-------|--------|-----------|-------|
| MFA required for all staff logins | Attempt login without MFA code | | |
| MFA bypass not possible via API manipulation | Send auth request without MFA step | | |
| Password complexity enforced | Try weak passwords | | |
| Account lockout after failed attempts | Attempt 5+ wrong passwords | | |
| Session invalidated on logout | Check token after logout | | |

### 1.2 Patient Authentication
| Check | Method | Pass/Fail | Notes |
|-------|--------|-----------|-------|
| Magic links expire correctly | Use link after TTL (default 15 min) | | |
| Magic links single-use | Reuse consumed link | | |
| Magic link tokens unpredictable | Analyze token entropy | | |
| No password-based patient auth | Confirm no password endpoints | | |

---

## 2. Token Security

### 2.1 JWT Configuration
| Check | Method | Pass/Fail | Notes |
|-------|--------|-----------|-------|
| Tokens expire within acceptable window | Decode JWT, check `exp` claim | | |
| Algorithm is RS256/ES256 (not HS256 with weak secret) | Decode header | | |
| Refresh token rotation implemented | Check refresh flow | | |
| Tokens invalidated on password change | Change password, use old token | | |

### 2.2 Token Handling
| Check | Method | Pass/Fail | Notes |
|-------|--------|-----------|-------|
| Tokens not logged | Check application logs | | |
| Tokens transmitted only via HTTPS | Network inspection | | |
| No tokens in URL parameters | Check all endpoints | | |
| Secure cookie flags set (HttpOnly, Secure, SameSite) | Inspect cookies | | |

---

## 3. RBAC Enforcement

### 3.1 Role Boundaries
| Check | Method | Pass/Fail | Notes |
|-------|--------|-----------|-------|
| READONLY cannot create triage cases | API call with READONLY token | | |
| CLINICIAN cannot approve ruleset changes | API call attempt | | |
| PATIENT cannot access staff endpoints | Cross-boundary access attempt | | |
| ADMIN-only endpoints protected | Access audit logs without ADMIN role | | |

### 3.2 Permission Matrix Verification
| Endpoint | ADMIN | CLINICAL_LEAD | CLINICIAN | READONLY | PATIENT |
|----------|-------|---------------|-----------|----------|---------|
| POST /triage/cases | Y | Y | Y | N | N |
| POST /incidents | Y | Y | Y | Y | N |
| POST /incidents/{id}/close | Y | Y | N | N | N |
| POST /change-control/approve | Y | Y | N | N | N |
| GET /evidence/audit-log | Y | Y | Y | N | N |
| POST /scheduling/appointments (self) | - | - | - | - | GREEN/BLUE only |

### 3.3 Vertical Privilege Escalation
| Check | Method | Pass/Fail | Notes |
|-------|--------|-----------|-------|
| Cannot modify own role | API manipulation | | |
| Cannot access other users' permissions | IDOR attempt | | |
| Role changes require re-authentication | Modify role, check session | | |

---

## 4. IDOR (Insecure Direct Object Reference)

### 4.1 Patient Data Access
| Check | Method | Pass/Fail | Notes |
|-------|--------|-----------|-------|
| Patient A cannot view Patient B's case | Change case ID in request | | |
| Patient cannot access other patients' check-ins | Enumerate check-in IDs | | |
| Patient cannot view other patients' appointments | ID manipulation | | |

### 4.2 Staff Data Access
| Check | Method | Pass/Fail | Notes |
|-------|--------|-----------|-------|
| Staff cannot access cases outside their scope | Cross-clinic access attempt | | |
| Audit logs show only authorized records | Query with unauthorized entity IDs | | |

### 4.3 UUID Unpredictability
| Check | Method | Pass/Fail | Notes |
|-------|--------|-----------|-------|
| Entity IDs are UUIDv4 (random) | Analyze ID patterns | | |
| Sequential enumeration not possible | Attempt ID guessing | | |

---

## 5. Input Validation & Injection

### 5.1 SQL Injection
| Check | Method | Pass/Fail | Notes |
|-------|--------|-----------|-------|
| Search parameters sanitized | SQLi payloads in search fields | | |
| Filter parameters sanitized | SQLi in date/status filters | | |
| Parameterized queries used | Code review | | |

### 5.2 XSS Prevention
| Check | Method | Pass/Fail | Notes |
|-------|--------|-----------|-------|
| Patient comments sanitized | XSS payloads in intake | | |
| Staff notes sanitized | XSS in disposition notes | | |
| Content-Type headers correct | Response header inspection | | |

### 5.3 Command Injection
| Check | Method | Pass/Fail | Notes |
|-------|--------|-----------|-------|
| No shell execution with user input | Code review | | |
| File paths validated | Path traversal attempts | | |

---

## 6. Data Protection

### 6.1 Encryption
| Check | Method | Pass/Fail | Notes |
|-------|--------|-----------|-------|
| Database encryption at rest | Infrastructure review | | |
| TLS 1.2+ for all connections | SSL Labs test | | |
| Sensitive fields encrypted in DB | Database inspection | | |

### 6.2 Audit Trail Integrity
| Check | Method | Pass/Fail | Notes |
|-------|--------|-----------|-------|
| Audit events cannot be modified | Attempt UPDATE on audit_events | | |
| Audit events cannot be deleted | Attempt DELETE on audit_events | | |
| Hash chain integrity verifiable | Run verification endpoint | | |

---

## 7. Clinical Safety Controls

### 7.1 Booking Restrictions
| Check | Method | Pass/Fail | Notes |
|-------|--------|-----------|-------|
| RED tier cannot self-book | API attempt with RED case | | |
| AMBER tier cannot self-book | API attempt with AMBER case | | |
| Bypass attempts blocked | Tier manipulation in request | | |

### 7.2 Escalation Triggers
| Check | Method | Pass/Fail | Notes |
|-------|--------|-----------|-------|
| Suicidal ideation triggers escalation | Submit check-in with SI=true | | |
| PHQ-2 >= 3 triggers escalation | Submit elevated scores | | |
| Escalations cannot be suppressed | API manipulation attempt | | |

---

## 8. API Security

### 8.1 Rate Limiting
| Check | Method | Pass/Fail | Notes |
|-------|--------|-----------|-------|
| Auth endpoints rate limited | Rapid request test | | |
| Magic link generation limited | Burst request test | | |

### 8.2 Error Handling
| Check | Method | Pass/Fail | Notes |
|-------|--------|-----------|-------|
| Stack traces not exposed | Trigger errors, check responses | | |
| Sensitive data not in errors | Review error payloads | | |
| Consistent error formats | Compare error responses | | |

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Security Reviewer | | | |
| Technical Lead | | | |
| Clinical Safety Officer | | | |

### Findings Summary

**Critical:** ___
**High:** ___
**Medium:** ___
**Low:** ___
**Informational:** ___

### Remediation Required Before Go-Live

| Finding | Severity | Remediation | Owner | Due Date |
|---------|----------|-------------|-------|----------|
| | | | | |

---

*Checklist version: 1.0*
*Last updated: 2026-01-11*

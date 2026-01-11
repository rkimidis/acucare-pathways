# Risk Register

**Document Owner:** Clinical Governance Committee
**Last Updated:** 2024-01-15
**Review Cadence:** Monthly (or after significant incidents)
**Next Review:** 2024-02-15

---

## Risk Matrix

| Likelihood / Impact | Low | Medium | High | Severe |
|---------------------|-----|--------|------|--------|
| **High** | Monitor | Mitigate | Urgent | Critical |
| **Medium** | Accept | Monitor | Mitigate | Urgent |
| **Low** | Accept | Accept | Monitor | Mitigate |

---

## 1. Clinical Risks

### RISK-C001: Missed High-Risk Suicidal Ideation

| Field | Value |
|-------|-------|
| **Risk ID** | RISK-C001 |
| **Category** | Clinical Safety |
| **Owner** | Clinical Lead |
| **Likelihood** | Low |
| **Impact** | Severe |
| **Risk Rating** | **MITIGATE** |
| **Status** | Active |

**Description:**
Patient with active suicidal ideation is not identified or escalated appropriately, leading to potential patient harm.

**Mitigations:**
- [ ] Mandatory SI questions in all intake pathways (PHQ-9 item 9 + direct questions)
- [ ] Deterministic escalation rules with no manual override for RED tier
- [ ] Duty clinician review required for all RED/AMBER cases
- [ ] Automated golden tests for SI detection rules
- [ ] Self-booking automatically disabled for RED/AMBER tiers
- [ ] 2-hour SLA for RED tier first contact

**Monitoring:**
| Metric | Frequency | Threshold | Action if Breached |
|--------|-----------|-----------|-------------------|
| SI flagged vs clinical outcomes | Monthly | Any missed SI requiring crisis intervention | Immediate rule review |
| RED tier SLA compliance | Weekly | < 95% contacted within 2 hours | Duty staffing review |
| Item 9 positive capture rate | Monthly | < 99% triggering AMBER/RED | Rule audit |

**Review History:**
| Date | Reviewer | Notes |
|------|----------|-------|
| 2024-01-15 | Dr. Clinical Lead | Initial risk assessment |

---

### RISK-C002: Alert Fatigue (Excessive AMBER Cases)

| Field | Value |
|-------|-------|
| **Risk ID** | RISK-C002 |
| **Category** | Clinical Operations |
| **Owner** | Duty Clinician Lead |
| **Likelihood** | Medium |
| **Impact** | High |
| **Risk Rating** | **MITIGATE** |
| **Status** | Active |

**Description:**
Too many AMBER tier cases overwhelm duty clinicians, leading to delayed response times or desensitization to genuine urgent cases.

**Mitigations:**
- [ ] Tune AMBER thresholds based on clinical review data
- [ ] Require protective factor capture (support network, coping strategies)
- [ ] Batch non-urgent AMBER alerts (e.g., medication reviews)
- [ ] Implement AMBER sub-prioritization (AMBER-1, AMBER-2)
- [ ] Dashboard shows AMBER age to prioritize oldest cases

**Monitoring:**
| Metric | Frequency | Threshold | Action if Breached |
|--------|-----------|-----------|-------------------|
| AMBER cases per duty clinician per day | Weekly | > 15 cases/day average | Threshold review meeting |
| AMBER → GREEN downgrade rate | Monthly | > 40% downgraded | Rule sensitivity review |
| Duty clinician overtime hours | Weekly | > 10% over contracted | Staffing escalation |

**Review History:**
| Date | Reviewer | Notes |
|------|----------|-------|
| 2024-01-15 | Duty Clinician Lead | Monitoring baseline established |

---

### RISK-C003: Wrong Pathway Assignment

| Field | Value |
|-------|-------|
| **Risk ID** | RISK-C003 |
| **Category** | Clinical Operations |
| **Owner** | Operations Lead |
| **Likelihood** | Medium |
| **Impact** | Medium |
| **Risk Rating** | **MONITOR** |
| **Status** | Active |

**Description:**
Patients routed to incorrect pathway (e.g., ADHD requests filling general psychiatry slots), causing delays and inefficient resource use.

**Mitigations:**
- [ ] Separate neurodevelopmental (ND) triage stream with dedicated rules
- [ ] Clear inclusion/exclusion criteria documented in ruleset
- [ ] Pathway-specific intake questions to improve routing accuracy
- [ ] Staff override capability with mandatory reason logging
- [ ] Quarterly pathway accuracy audit

**Monitoring:**
| Metric | Frequency | Threshold | Action if Breached |
|--------|-----------|-----------|-------------------|
| Pathway reassignment rate | Monthly | > 15% reassigned after initial triage | Rule refinement |
| ND cases in general psychiatry queue | Monthly | > 5% leakage | ND stream review |
| Time to first appointment by pathway | Monthly | > 20% variance from target | Capacity review |

**Review History:**
| Date | Reviewer | Notes |
|------|----------|-------|
| 2024-01-15 | Operations Lead | ND stream launched |

---

## 2. Legal / UK GDPR Risks

### RISK-L001: Unlawful Processing / Missing DPIA

| Field | Value |
|-------|-------|
| **Risk ID** | RISK-L001 |
| **Category** | Data Protection |
| **Owner** | Data Protection Lead |
| **Likelihood** | Medium |
| **Impact** | Severe |
| **Risk Rating** | **MITIGATE** |
| **Status** | Active |

**Description:**
Processing of special category health data without appropriate lawful basis, DPIA, or documentation, leading to ICO enforcement action.

**Mitigations:**
- [ ] DPIA completed before any new feature processing health data
- [ ] Data map maintained with all processing activities
- [ ] Lawful basis documented for each processing activity
- [ ] Retention policy implemented and enforced technically
- [ ] Privacy notice updated and accessible
- [ ] Subject access request (SAR) process documented and tested

**Monitoring:**
| Metric | Frequency | Threshold | Action if Breached |
|--------|-----------|-----------|-------------------|
| DPIA coverage for new features | Per release | 100% coverage | Block release |
| Data retention compliance | Monthly | Any data beyond retention period | Immediate deletion |
| SAR response time | Per request | > 30 days | Escalate to DPO |

**Lawful Basis Register:**
| Processing Activity | Lawful Basis | Special Category Condition |
|--------------------|--------------|---------------------------|
| Patient intake | Contract (Art 6(1)(b)) | Healthcare (Art 9(2)(h)) |
| Clinical triage | Contract | Healthcare |
| Audit logging | Legal obligation (Art 6(1)(c)) | Healthcare |
| Research (anonymised) | Legitimate interest | N/A (anonymised) |

**Review History:**
| Date | Reviewer | Notes |
|------|----------|-------|
| 2024-01-15 | Data Protection Lead | DPIA v1 approved |

---

### RISK-L002: Access Control Failure

| Field | Value |
|-------|-------|
| **Risk ID** | RISK-L002 |
| **Category** | Information Security |
| **Owner** | Tech Lead |
| **Likelihood** | Low |
| **Impact** | Severe |
| **Risk Rating** | **MITIGATE** |
| **Status** | Active |

**Description:**
Staff member accesses patient data they are not authorized to see, breaching confidentiality and UK GDPR principles.

**Mitigations:**
- [ ] Role-based access control (RBAC) implemented
- [ ] Care relationship checks (staff must be assigned to case)
- [ ] Automated permission tests in CI pipeline
- [ ] Break-glass access with mandatory justification logging
- [ ] All access logged with immutable audit trail
- [ ] Least privilege principle enforced

**Monitoring:**
| Metric | Frequency | Threshold | Action if Breached |
|--------|-----------|-----------|-------------------|
| Unauthorized access attempts | Real-time | Any blocked attempt | Security review |
| Break-glass usage | Weekly | > 5 per week | Usage audit |
| Permission test coverage | Per release | < 100% | Block release |
| Access log review | Quarterly | Anomalous patterns | Investigation |

**Review History:**
| Date | Reviewer | Notes |
|------|----------|-------|
| 2024-01-15 | Tech Lead | RBAC audit complete |

---

### RISK-L003: Vendor Risk (SMS/Email Providers)

| Field | Value |
|-------|-------|
| **Risk ID** | RISK-L003 |
| **Category** | Third Party Risk |
| **Owner** | Operations Lead |
| **Likelihood** | Medium |
| **Impact** | High |
| **Risk Rating** | **MITIGATE** |
| **Status** | Active |

**Description:**
Third-party messaging providers (SMS, email) process patient data inappropriately or experience data breach.

**Mitigations:**
- [ ] Data Processing Agreement (DPA) with all vendors
- [ ] Data minimisation (no clinical content in messages, only links)
- [ ] UK/EU data residency requirement in contracts
- [ ] Delivery failure handling with fallback channels
- [ ] Vendor security assessment before onboarding
- [ ] Right to audit clause in contracts

**Vendors Register:**
| Vendor | Service | DPA Signed | Last Security Review | Data Location |
|--------|---------|------------|---------------------|---------------|
| Twilio | SMS | 2024-01-01 | 2024-01-01 | UK |
| SendGrid | Email | 2024-01-01 | 2024-01-01 | EU |
| Gov.uk Notify | SMS/Email | N/A (Govt) | N/A | UK |

**Monitoring:**
| Metric | Frequency | Threshold | Action if Breached |
|--------|-----------|-----------|-------------------|
| Vendor security review | Annually | Overdue > 30 days | Escalate to DPO |
| Delivery success rate | Daily | < 95% | Switch to backup |
| Vendor incident notifications | Real-time | Any breach | Incident response |

**Review History:**
| Date | Reviewer | Notes |
|------|----------|-------|
| 2024-01-15 | Operations Lead | Vendor DPAs renewed |

---

## 3. Technical Risks

### RISK-T001: Rules Regression

| Field | Value |
|-------|-------|
| **Risk ID** | RISK-T001 |
| **Category** | Software Quality |
| **Owner** | Tech Lead |
| **Likelihood** | Medium |
| **Impact** | High |
| **Risk Rating** | **MITIGATE** |
| **Status** | Active |

**Description:**
Change to triage rules introduces regression that causes incorrect tier assignment, potentially missing high-risk cases.

**Mitigations:**
- [ ] Golden tests for all critical rule paths (RED, AMBER scenarios)
- [ ] Ruleset version pinned per case (historical decisions preserved)
- [ ] Change approval workflow (cannot self-approve)
- [ ] CI gate blocks merge if golden tests fail
- [ ] Ruleset content hash stored with every decision
- [ ] Staging environment for rule testing before production

**Monitoring:**
| Metric | Frequency | Threshold | Action if Breached |
|--------|-----------|-----------|-------------------|
| Golden test pass rate | Per commit | < 100% | Block merge |
| Ruleset changes | Weekly | > 3 changes/week | Review meeting |
| Post-change tier distribution shift | Per release | > 10% shift | Clinical review |

**Review History:**
| Date | Reviewer | Notes |
|------|----------|-------|
| 2024-01-15 | Tech Lead | Golden tests expanded |

---

### RISK-T002: Data Loss / Corruption

| Field | Value |
|-------|-------|
| **Risk ID** | RISK-T002 |
| **Category** | Infrastructure |
| **Owner** | Tech Lead |
| **Likelihood** | Low |
| **Impact** | Severe |
| **Risk Rating** | **MITIGATE** |
| **Status** | Active |

**Description:**
Database failure, corruption, or accidental deletion causes loss of patient records or clinical decisions.

**Mitigations:**
- [ ] Point-in-time recovery (PITR) enabled (35-day retention)
- [ ] Daily automated backups with offsite replication
- [ ] Monthly restore drills in staging environment
- [ ] Immutable audit log snapshots (separate from main DB)
- [ ] Soft delete for all patient data (no hard deletes)
- [ ] Database encryption at rest and in transit

**Monitoring:**
| Metric | Frequency | Threshold | Action if Breached |
|--------|-----------|-----------|-------------------|
| Backup success rate | Daily | < 100% | Immediate investigation |
| Restore drill success | Monthly | Any failure | DR plan review |
| Replication lag | Real-time | > 1 minute | Alert on-call |
| Storage utilisation | Weekly | > 80% | Capacity planning |

**Restore Drill Log:**
| Date | Environment | Data Set | Result | Time to Restore |
|------|-------------|----------|--------|-----------------|
| 2024-01-10 | Staging | Full DB | Success | 45 minutes |

**Review History:**
| Date | Reviewer | Notes |
|------|----------|-------|
| 2024-01-15 | Tech Lead | PITR verified |

---

### RISK-T003: Messaging Failures

| Field | Value |
|-------|-------|
| **Risk ID** | RISK-T003 |
| **Category** | Operations |
| **Owner** | Operations Lead |
| **Likelihood** | Medium |
| **Impact** | Medium |
| **Risk Rating** | **MONITOR** |
| **Status** | Active |

**Description:**
SMS/email delivery failures cause patients to miss appointment reminders or check-in requests.

**Mitigations:**
- [ ] Delivery receipt tracking for all messages
- [ ] Automatic retry with exponential backoff
- [ ] Fallback channel (SMS → email → phone call)
- [ ] Dashboard showing failed messages for manual follow-up
- [ ] Patient communication preferences stored
- [ ] Multiple provider support for redundancy

**Monitoring:**
| Metric | Frequency | Threshold | Action if Breached |
|--------|-----------|-----------|-------------------|
| SMS delivery rate | Daily | < 95% | Switch provider |
| Email delivery rate | Daily | < 98% | Investigate bounces |
| Failed message queue size | Real-time | > 50 messages | Manual follow-up |
| Appointment no-show rate | Weekly | > 15% | Communication review |

**Review History:**
| Date | Reviewer | Notes |
|------|----------|-------|
| 2024-01-15 | Operations Lead | Fallback channels implemented |

---

## Risk Review Schedule

| Risk Category | Review Frequency | Next Review | Reviewer |
|---------------|-----------------|-------------|----------|
| Clinical (C001-C003) | Monthly | 2024-02-15 | Clinical Lead |
| Legal (L001-L003) | Quarterly | 2024-04-15 | Data Protection Lead |
| Technical (T001-T003) | Monthly | 2024-02-15 | Tech Lead |
| All Risks | Quarterly | 2024-04-15 | Clinical Governance Committee |

---

## Escalation Matrix

| Risk Rating | Response Time | Escalation Path |
|-------------|--------------|-----------------|
| Critical | Immediate | CEO + Board |
| Urgent | 24 hours | Clinical Governance Committee |
| Mitigate | 1 week | Risk Owner + Line Manager |
| Monitor | Next scheduled review | Risk Owner |
| Accept | Annual review | Risk Owner |

---

## Appendix: Risk Assessment Definitions

### Likelihood

| Rating | Definition | Frequency |
|--------|------------|-----------|
| Low | Unlikely to occur | < 1 per year |
| Medium | May occur occasionally | 1-4 per year |
| High | Likely to occur | > 4 per year |

### Impact

| Rating | Definition |
|--------|------------|
| Low | Minor inconvenience, no patient harm, easily recoverable |
| Medium | Service disruption, potential complaint, recoverable |
| High | Significant service impact, potential regulatory interest |
| Severe | Patient harm possible, regulatory action, reputational damage |

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024-01-15 | Clinical Governance | Initial version |

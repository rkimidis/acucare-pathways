'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { getToken, removeToken } from '@/lib/auth';
import { AppShell, EmptyState, PageHeader, SegmentedControl, StatCard, StatusBadge } from '@/ui/components';
import styles from './triage.module.css';

interface QueueItem {
  id: string;
  patient_id: string;
  patient_ref: string;
  tier: string | null;
  pathway: string | null;
  status: string | null;
  created_at: string | null;
  triaged_at: string | null;
  sla_deadline: string | null;
  sla_minutes_remaining: number | null;
  sla_breached: boolean;
  clinician_review_required: boolean;
  assigned_to_user_id: string | null;
  assigned_to_user_initials: string | null;
  assigned_to_user_name: string | null;
  assigned_to_me: boolean;
  assigned_at: string | null;
  rules_fired: string[];
  ruleset_version: string | null;
  last_staff_action_at: string | null;
  age_minutes: number | null;
}

type TierFilter = 'all' | 'red' | 'amber' | 'green' | 'blue';
type AssignmentFilter = 'any' | 'unassigned' | 'me' | 'others';

interface DutyRosterUser {
  id: string;
  full_name: string;
  title: string | null;
  role: string | null;
}

interface DutyRosterResponse {
  id: string | null;
  starts_at: string | null;
  ends_at: string | null;
  primary: DutyRosterUser | null;
  backup: DutyRosterUser | null;
}

interface QueueResponse {
  items: QueueItem[];
  total: number;
  red_count: number;
  amber_count: number;
  green_count: number;
  blue_count: number;
  breached_count: number;
}

interface QueueCounts {
  total: number;
  red: number;
  amber: number;
  green: number;
  blue: number;
  breached: number;
}

export default function TriageQueuePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [counts, setCounts] = useState<QueueCounts | null>(null);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState<TierFilter>('all');
  const [assignmentFilter, setAssignmentFilter] = useState<AssignmentFilter | null>(null);
  const [caseStatus, setCaseStatus] = useState<string | null>(null);
  const [lastFetchedAt, setLastFetchedAt] = useState<Date | null>(null);
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);
  const [dutyRoster, setDutyRoster] = useState<DutyRosterResponse | null>(null);
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [currentUserRole, setCurrentUserRole] = useState<string | null>(null);


  const decodeTokenPayload = (token: string) => {
    try {
      const payload = token.split('.')[1];
      if (!payload) return null;
      const decoded = JSON.parse(atob(payload));
      return {
        userId: decoded.sub as string | undefined,
        role: decoded.role as string | undefined,
      };
    } catch {
      return null;
    }
  };

  const fetchQueue = useCallback(async (
    token: string,
    tierFilter: TierFilter,
    assignedFilter: AssignmentFilter | null,
    statusFilter: string | null,
  ) => {
    try {
      setLoading(true);
      setError('');
      const params = new URLSearchParams();
      if (tierFilter !== 'all') {
        params.set('tier', tierFilter);
      }
      if (assignedFilter && assignedFilter !== 'any') {
        params.set('assigned', assignedFilter);
      }
      if (statusFilter) {
        params.set('case_status', statusFilter);
      }
      const url = `/api/v1/triage-cases/queue?${params.toString()}`;

      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.status === 401 || response.status === 403) {
        removeToken();
        router.push('/auth/login');
        return;
      }

      if (!response.ok) throw new Error('Failed to fetch queue');

      const data: QueueResponse = await response.json();

      // Sort by tier priority (RED → AMBER → GREEN → BLUE) then by age (oldest first)
      const tierPriority: Record<string, number> = {
        red: 0,
        amber: 1,
        green: 2,
        blue: 3,
      };
      const sortedItems = [...(data.items || [])].sort((a, b) => {
        const tierA = tierPriority[a.tier?.toLowerCase() || 'green'] ?? 2;
        const tierB = tierPriority[b.tier?.toLowerCase() || 'green'] ?? 2;
        if (tierA !== tierB) return tierA - tierB;
        // Oldest first (higher age_minutes first)
        return (b.age_minutes || 0) - (a.age_minutes || 0);
      });
      setQueue(sortedItems);
      setCounts({
        total: data.total,
        red: data.red_count,
        amber: data.amber_count,
        green: data.green_count,
        blue: data.blue_count,
        breached: data.breached_count,
      });
      setLastFetchedAt(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load queue');
    } finally {
      setLoading(false);
    }
  }, [router]);

  const fetchDutyRoster = useCallback(async (token: string) => {
    try {
      const response = await fetch('/api/v1/duty-roster/current', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) return;
      const data: DutyRosterResponse = await response.json();
      setDutyRoster(data);
    } catch {
      // Ignore duty roster failures.
    }
  }, []);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    const payload = decodeTokenPayload(token);
    setCurrentUserId(payload?.userId ?? null);
    setCurrentUserRole(payload?.role ?? null);
    fetchDutyRoster(token);
  }, [fetchDutyRoster, getToken]);

  useEffect(() => {
    if (assignmentFilter !== null || !currentUserId) return;
    const isDuty =
      dutyRoster?.primary?.id === currentUserId ||
      dutyRoster?.backup?.id === currentUserId;
    setAssignmentFilter(isDuty ? 'unassigned' : 'me');
  }, [assignmentFilter, currentUserId, dutyRoster]);

  useEffect(() => {
    const tierParam = searchParams.get('tier');
    const assignedParam = searchParams.get('assigned');
    const assignedLegacyParam = searchParams.get('assigned_to_me');
    const statusParam = searchParams.get('case_status');

    if (tierParam && ['red', 'amber', 'green', 'blue'].includes(tierParam)) {
      setFilter(tierParam as TierFilter);
    } else {
      setFilter('all');
    }

    if (assignedParam && ['any', 'unassigned', 'me', 'others'].includes(assignedParam)) {
      setAssignmentFilter(assignedParam as AssignmentFilter);
    } else if (assignedLegacyParam !== null) {
      setAssignmentFilter(assignedLegacyParam === 'true' ? 'me' : 'any');
    } else {
      setAssignmentFilter(null);
    }

    setCaseStatus(statusParam || null);
  }, [searchParams]);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push('/auth/login');
      return;
    }

    if (assignmentFilter === null) {
      return;
    }
    fetchQueue(token, filter, assignmentFilter, caseStatus);

    // Refresh every 60 seconds
    const interval = setInterval(() => {
      const t = getToken();
      if (t && assignmentFilter !== null) {
        fetchQueue(t, filter, assignmentFilter, caseStatus);
      }
    }, 60000);

    return () => clearInterval(interval);
  }, [router, filter, assignmentFilter, caseStatus, fetchQueue, getToken]);

  const handleFilterChange = (newFilter: TierFilter) => {
    setFilter(newFilter);
    const token = getToken();
    if (token && assignmentFilter !== null) {
      fetchQueue(token, newFilter, assignmentFilter, caseStatus);
    }
  };
 
  const handleAssignmentFilterChange = (nextFilter: AssignmentFilter) => {
    setAssignmentFilter(nextFilter);
    const token = getToken();
    if (token) {
      fetchQueue(token, filter, nextFilter, caseStatus);
    }
  };

  const handleClaim = async (caseId: string) => {
    try {
      const token = getToken();
      if (!token) {
        router.push('/auth/login');
        return;
      }

      const response = await fetch(`/api/v1/triage-cases/${caseId}/claim`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        throw new Error('Failed to claim case');
      }

      if (assignmentFilter !== null) {
        fetchQueue(token, filter, assignmentFilter, caseStatus);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to claim case');
    }
  };

  const handleUnassign = async (caseId: string) => {
    try {
      const token = getToken();
      if (!token) {
        router.push('/auth/login');
        return;
      }

      const response = await fetch(`/api/v1/triage-cases/${caseId}/unassign`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        throw new Error('Failed to unassign case');
      }

      if (assignmentFilter !== null) {
        fetchQueue(token, filter, assignmentFilter, caseStatus);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to unassign case');
    }
  };

  const handleReassign = async (caseId: string) => {
    const targetUserId = window.prompt('Reassign to user ID');
    if (!targetUserId) return;
    const reason = window.prompt('Reason for reassignment');
    if (!reason) return;

    try {
      const token = getToken();
      if (!token) {
        router.push('/auth/login');
        return;
      }

      const response = await fetch(`/api/v1/triage-cases/${caseId}/reassign`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_id: targetUserId, reason }),
      });

      if (!response.ok) {
        throw new Error('Failed to reassign case');
      }

      if (assignmentFilter !== null) {
        fetchQueue(token, filter, assignmentFilter, caseStatus);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reassign case');
    }
  };

  const formatDuration = (minutes: number | null): string => {
    if (minutes === null) return '--';
    if (minutes < 0) return '0m';

    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;

    if (hours > 0) {
      return `${hours}h ${mins}m`;
    }
    return `${mins}m`;
  };

  const formatRelativeTime = (isoString: string | null): string => {
    if (!isoString) return '--';
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    if (diffMs < 0) return '0m ago';
    const totalMinutes = Math.floor(diffMs / 60000);
    if (totalMinutes < 60) return `${totalMinutes}m ago`;
    const hours = Math.floor(totalMinutes / 60);
    const mins = totalMinutes % 60;
    return `${hours}h ${mins}m ago`;
  };

  // Map rule IDs to human-readable labels for the "Why here" display
  const getRuleLabel = (ruleId: string): string => {
    const ruleLabels: Record<string, string> = {
      // Safety / escalation rules
      'suicidal_ideation_active': 'Active safety concern',
      'suicidal_ideation_passive': 'Safety monitoring needed',
      'self_harm_recent': 'Recent self-harm',
      'self_harm_history': 'Self-harm history',
      'crisis_presentation': 'Crisis presentation',
      'acute_risk_flagged': 'Acute risk flagged',
      'safeguarding_concern': 'Safeguarding concern',

      // Tier assignment rules
      'red_tier_escalation': 'Urgent clinical review',
      'amber_tier_clinical_review': 'Clinical review required',
      'green_tier_default': 'Standard assessment',
      'blue_tier_signpost': 'Signposting pathway',

      // Pathway rules
      'therapy_pathway_default': 'Therapy assessment',
      'therapy_pathway_low_risk': 'Low risk – therapy pathway',
      'medication_review_indicated': 'Medication review indicated',
      'psychiatry_referral_indicated': 'Psychiatry referral',
      'wellbeing_support': 'Wellbeing support',
      'social_prescribing': 'Social prescribing',

      // Assessment rules
      'phq9_moderate': 'PHQ-9 moderate',
      'phq9_severe': 'PHQ-9 severe',
      'gad7_moderate': 'GAD-7 moderate',
      'gad7_severe': 'GAD-7 severe',
      'pcl5_threshold': 'PTSD screen positive',
      'audit_hazardous': 'Alcohol use concern',

      // Process rules
      'incomplete_assessment': 'Incomplete assessment',
      'consent_pending': 'Consent pending',
      'awaiting_gp_response': 'Awaiting GP response',
      'follow_up_due': 'Follow-up due',

      // Default/fallback routing rules (human-friendly labels)
      'FALLBACK_GREEN_THERAPY_ASSESSMENT': 'Default therapy assessment',
      'FALLBACK_GREEN': 'Standard assessment',
      'FALLBACK_BLUE': 'Signposting pathway',
      'DEFAULT_THERAPY_PATHWAY': 'Default therapy assessment',
      'DEFAULT_GREEN_ROUTING': 'Low risk – standard pathway',
      'GREEN_THERAPY_ASSESSMENT': 'Therapy assessment',
      'GREEN_DEFAULT': 'Low risk – standard pathway',
      'BLUE_SIGNPOST': 'Signposting pathway',
      'AMBER_CLINICAL_REVIEW': 'Clinical review required',
      'RED_URGENT': 'Urgent clinical review',
      'NO_RULES_MATCHED': 'Default assessment pathway',
    };

    // Check for exact match first
    if (ruleLabels[ruleId]) {
      return ruleLabels[ruleId];
    }

    // Check case-insensitive match
    const lowerRuleId = ruleId.toLowerCase();
    const lowerKey = Object.keys(ruleLabels).find(
      (key) => key.toLowerCase() === lowerRuleId
    );
    if (lowerKey) {
      return ruleLabels[lowerKey];
    }

    // Fallback: convert to readable format
    // Remove common prefixes and convert to title case
    let readable = ruleId
      .replace(/^(FALLBACK_|DEFAULT_|RULE_)/i, '')
      .replace(/_/g, ' ')
      .toLowerCase();

    // Title case the result
    readable = readable.replace(/\b\w/g, (c) => c.toUpperCase());

    // Make it more concise
    readable = readable
      .replace(/\bAssessment\b/i, 'assessment')
      .replace(/\bPathway\b/i, 'pathway')
      .replace(/\bTherapy\b/i, 'therapy');

    return readable || 'Standard assessment';
  };

  const getSlaIndicatorClass = (item: QueueItem): string => {
    if (item.sla_breached) return styles.slaBreach;
    if (item.sla_minutes_remaining !== null && item.sla_minutes_remaining <= 30) {
      return styles.slaWarning;
    }
    return styles.slaNormal;
  };

  // Get age indicator class based on thresholds:
  // <24h (1440 min) → neutral, 24-72h → amber, >72h → red
  const getAgeIndicatorClass = (ageMinutes: number | null): string => {
    if (ageMinutes === null) return '';
    if (ageMinutes > 4320) return styles.ageRed;      // >72h
    if (ageMinutes > 1440) return styles.ageAmber;    // 24-72h
    return '';                                         // <24h neutral
  };

  const getTierTone = (tier: string | null) => {
    switch (tier) {
      case 'red':
        return { tone: 'red' as const, label: 'Red' };
      case 'amber':
        return { tone: 'amber' as const, label: 'Amber' };
      case 'green':
        return { tone: 'green' as const, label: 'Green' };
      case 'blue':
        return { tone: 'blue' as const, label: 'Blue' };
      default:
        return { tone: 'neutral' as const, label: 'Pending' };
    }
  };

  const isStale = lastFetchedAt
    ? Date.now() - lastFetchedAt.getTime() > 5 * 60 * 1000
    : false;

  const isDutyClinician =
    !!currentUserId &&
    (dutyRoster?.primary?.id === currentUserId ||
      dutyRoster?.backup?.id === currentUserId);
  const canOverrideAssignment =
    isDutyClinician || currentUserRole === 'admin' || currentUserRole === 'clinical_lead';
  const canClaimCase =
    currentUserRole === 'clinician' ||
    currentUserRole === 'clinical_lead' ||
    currentUserRole === 'admin';
  const dutyLabel = dutyRoster?.primary?.full_name || 'Not set';
  const assignmentValue = assignmentFilter ?? 'any';

  const handleLogout = () => {
    removeToken();
    router.push('/');
  };

  return (
    <AppShell activeNav="triage" onSignOut={handleLogout}>
      <PageHeader
        title="Triage Queue"
        breadcrumb={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Triage Queue' },
        ]}
        statusPill={
          counts && counts.breached > 0 ? (
            <StatusBadge
              tone="red"
              label={`${counts.breached} SLA breached`}
            />
          ) : undefined
        }
        actions={
          <div className={styles.headerActions}>
            <SegmentedControl
              options={[
                { label: 'All', value: 'any' },
                { label: 'Unassigned', value: 'unassigned' },
                { label: 'Assigned to me', value: 'me' },
                { label: 'Assigned to others', value: 'others' },
              ]}
              value={assignmentValue}
              onChange={(value) => handleAssignmentFilterChange(value as AssignmentFilter)}
            />
            <span className={styles.dutyIndicator}>
              Duty clinician: {dutyLabel}
            </span>
          </div>
        }
      />

      <div className={styles.content}>
          {error && <div className={styles.error}>{error}</div>}
          {isStale && lastFetchedAt && (
            <div className={styles.staleBanner}>
              Warning: data may be stale (last refreshed {formatRelativeTime(lastFetchedAt.toISOString())})
            </div>
          )}

          {/* Queue Counts */}
          {counts && (
            <div className={styles.countsGrid}>
              <StatCard
                label="All Pending"
                value={counts.total}
                active={filter === 'all'}
                onClick={() => handleFilterChange('all')}
              />
              <StatCard
                label="Red"
                value={counts.red}
                tone="red"
                active={filter === 'red'}
                onClick={() => handleFilterChange('red')}
              />
              <StatCard
                label="Amber"
                value={counts.amber}
                tone="amber"
                active={filter === 'amber'}
                onClick={() => handleFilterChange('amber')}
              />
              <StatCard
                label="Green"
                value={counts.green}
                tone="green"
                active={filter === 'green'}
                onClick={() => handleFilterChange('green')}
              />
              <StatCard
                label="Blue"
                value={counts.blue}
                tone="blue"
                active={filter === 'blue'}
                onClick={() => handleFilterChange('blue')}
              />
            </div>
          )}

          {/* Queue List */}
          <section className={styles.section}>
            {loading ? (
              <EmptyState title="Loading queue" variant="loading" />
            ) : queue.length === 0 ? (
              <EmptyState
                title="No active triage cases"
                message="You're all caught up."
              />
            ) : (
              <div className={styles.caseList}>
                {queue.map((item) => {
                  const rules = item.rules_fired.slice(0, 2).map(getRuleLabel);
                  const whyHere = rules.length > 0 ? rules.join(' · ') : '--';
                  const rulesetLabel = item.ruleset_version
                    ? `ruleset v${item.ruleset_version}`
                    : 'ruleset version unknown';
                  const slaText = item.sla_breached
                    ? 'SLA: breached'
                    : item.sla_minutes_remaining !== null
                      ? `SLA: ${formatDuration(item.sla_minutes_remaining)} left`
                      : 'SLA: Not started';
                  const assignedLabel = item.assigned_to_user_initials || '--';
                  const assignedTitle = item.assigned_to_user_name || 'Unassigned';
                  const isAssigned = !!item.assigned_to_user_id;
                  const isAssignedToMe = item.assigned_to_me;
                  const tierStatus = getTierTone(item.tier);
                  const ageClass = getAgeIndicatorClass(item.age_minutes);

                  return (
                    <div key={item.id} className={styles.caseRow}>
                      <div className={styles.caseMain}>
                        <div className={styles.caseHeader}>
                          <StatusBadge
                            tone={tierStatus.tone}
                            label={tierStatus.label}
                          />
                          <Link
                            href={`/dashboard/triage/${item.id}`}
                            className={styles.patientRef}
                            title="Internal reference — click to view full case"
                          >
                            {item.patient_ref}
                          </Link>
                          <span
                            className={styles.pathwayLabel}
                            title="Current recommended pathway"
                          >
                            {item.pathway || '--'}
                          </span>
                        </div>
                        <div
                          className={styles.caseReason}
                          title={`Determined automatically using ${rulesetLabel}`}
                        >
                          Why here: {whyHere}
                        </div>
                        <div className={styles.caseUpdate}>
                          Last update: {formatRelativeTime(item.last_staff_action_at)}
                        </div>
                      </div>
                      <div className={styles.caseIndicators}>
                        <span className={`${styles.caseIndicator} ${ageClass}`}>
                          Age: {formatDuration(item.age_minutes)}
                        </span>
                        <span className={`${styles.caseIndicator} ${getSlaIndicatorClass(item)}`}>
                          {slaText}
                        </span>
                        <span className={styles.caseIndicator} title={assignedTitle}>
                          Assigned: {assignedLabel}
                        </span>
                      </div>
                      <div className={styles.caseActions}>
                        <Link
                          href={`/dashboard/triage/${item.id}`}
                          className={styles.openCaseButton}
                        >
                          Open Case
                        </Link>
                        {!isAssigned && canClaimCase && (
                          <button
                            className={styles.claimButton}
                            type="button"
                            onClick={() => handleClaim(item.id)}
                          >
                            Claim
                          </button>
                        )}
                        {isAssignedToMe && (
                          <button
                            className={styles.unassignButton}
                            type="button"
                            onClick={() => handleUnassign(item.id)}
                          >
                            Unassign
                          </button>
                        )}
                        {isAssigned && !isAssignedToMe && canOverrideAssignment && (
                          <button
                            className={styles.reassignButton}
                            type="button"
                            onClick={() => handleReassign(item.id)}
                          >
                            Reassign
                          </button>
                        )}
                        <div className={styles.menu}>
                          <button
                            type="button"
                            className={styles.menuButton}
                            onClick={() => setActiveMenuId(activeMenuId === item.id ? null : item.id)}
                            aria-label="More actions"
                          >
                            ⋮
                          </button>
                          {activeMenuId === item.id && (
                            <div className={styles.menuList}>
                              {!isAssigned && canClaimCase && (
                                <button
                                  type="button"
                                  className={styles.menuItem}
                                  onClick={() => {
                                    setActiveMenuId(null);
                                    handleClaim(item.id);
                                  }}
                                >
                                  Claim case
                                </button>
                              )}
                              {isAssignedToMe && (
                                <button
                                  type="button"
                                  className={styles.menuItem}
                                  onClick={() => {
                                    setActiveMenuId(null);
                                    handleUnassign(item.id);
                                  }}
                                >
                                  Unassign case
                                </button>
                              )}
                              {isAssigned && !isAssignedToMe && canOverrideAssignment && (
                                <button
                                  type="button"
                                  className={styles.menuItem}
                                  onClick={() => {
                                    setActiveMenuId(null);
                                    handleReassign(item.id);
                                  }}
                                >
                                  Reassign case
                                </button>
                              )}
                              <Link
                                href={`/dashboard/incidents?case_id=${item.id}`}
                                className={styles.menuItem}
                                onClick={() => setActiveMenuId(null)}
                              >
                                Create incident
                              </Link>
                              <Link
                                href={`/dashboard/audit?entity_id=${item.id}`}
                                className={styles.menuItem}
                                onClick={() => setActiveMenuId(null)}
                              >
                                View audit trail
                              </Link>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
      </div>
    </AppShell>
  );
}

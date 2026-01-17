'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { getToken, removeToken } from '@/lib/auth';
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
      setQueue(data.items || []);
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

  const formatRuleId = (ruleId: string) => ruleId.replace(/_/g, ' ');

  const getSlaIndicatorClass = (item: QueueItem): string => {
    if (item.sla_breached) return styles.slaBreach;
    if (item.sla_minutes_remaining !== null && item.sla_minutes_remaining <= 30) {
      return styles.slaWarning;
    }
    return styles.slaNormal;
  };

  const getTierBadgeClass = (tier: string | null): string => {
    switch (tier) {
      case 'red':
        return styles.tierRed;
      case 'amber':
        return styles.tierAmber;
      case 'green':
        return styles.tierGreen;
      case 'blue':
        return styles.tierBlue;
      default:
        return styles.tierPending;
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

  return (
    <div className={styles.layout}>
      <aside className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <span className={styles.logo}>AcuCare</span>
        </div>
        <nav className={styles.nav}>
          <Link href="/dashboard" className={styles.navItem}>
            Dashboard
          </Link>
          <Link href="/dashboard/triage" className={styles.navItemActive}>
            Triage Queue
          </Link>
          <Link href="/dashboard/patients" className={styles.navItem}>
            Patients
          </Link>
          <Link href="/dashboard/audit" className={styles.navItem}>
            Audit Log
          </Link>
          <Link href="/governance/pilot-feedback" className={styles.navItem}>
            Pilot Feedback
          </Link>
        </nav>
      </aside>

      <main className={styles.main}>
        <header className={styles.header}>
          <div>
            <h1>Triage Queue</h1>
            {counts && counts.breached > 0 && (
              <div className={styles.breachAlert}>
                {counts.breached} case{counts.breached !== 1 ? 's' : ''} breached SLA
              </div>
            )}
          </div>
          <div className={styles.headerActions}>
            <div className={styles.assignmentFilters}>
              <button
                className={`${styles.filterChip} ${assignmentValue === 'any' ? styles.filterChipActive : ''}`}
                onClick={() => handleAssignmentFilterChange('any')}
              >
                All
              </button>
              <button
                className={`${styles.filterChip} ${assignmentValue === 'unassigned' ? styles.filterChipActive : ''}`}
                onClick={() => handleAssignmentFilterChange('unassigned')}
              >
                Unassigned
              </button>
              <button
                className={`${styles.filterChip} ${assignmentValue === 'me' ? styles.filterChipActive : ''}`}
                onClick={() => handleAssignmentFilterChange('me')}
              >
                Assigned to me
              </button>
              <button
                className={`${styles.filterChip} ${assignmentValue === 'others' ? styles.filterChipActive : ''}`}
                onClick={() => handleAssignmentFilterChange('others')}
              >
                Assigned to others
              </button>
            </div>
            <span className={styles.dutyIndicator}>
              Duty clinician: {dutyLabel}
            </span>
          </div>
        </header>

        {error && <div className={styles.error}>{error}</div>}
        {isStale && lastFetchedAt && (
          <div className={styles.staleBanner}>
            Warning: data may be stale (last refreshed {formatRelativeTime(lastFetchedAt.toISOString())})
          </div>
        )}

        {/* Queue Counts */}
        {counts && (
          <div className={styles.countsGrid}>
            <button
              className={`${styles.countCard} ${filter === 'all' ? styles.countCardActive : ''}`}
              onClick={() => handleFilterChange('all')}
            >
              <span className={styles.countValue}>{counts.total}</span>
              <span className={styles.countLabel}>All Pending</span>
            </button>
            <button
              className={`${styles.countCard} ${styles.countCardRed} ${filter === 'red' ? styles.countCardActive : ''}`}
              onClick={() => handleFilterChange('red')}
            >
              <span className={styles.countValue}>{counts.red}</span>
              <span className={styles.countLabel}>RED</span>
            </button>
            <button
              className={`${styles.countCard} ${styles.countCardAmber} ${filter === 'amber' ? styles.countCardActive : ''}`}
              onClick={() => handleFilterChange('amber')}
            >
              <span className={styles.countValue}>{counts.amber}</span>
              <span className={styles.countLabel}>AMBER</span>
            </button>
            <button
              className={`${styles.countCard} ${styles.countCardGreen} ${filter === 'green' ? styles.countCardActive : ''}`}
              onClick={() => handleFilterChange('green')}
            >
              <span className={styles.countValue}>{counts.green}</span>
              <span className={styles.countLabel}>GREEN</span>
            </button>
            <button
              className={`${styles.countCard} ${styles.countCardBlue} ${filter === 'blue' ? styles.countCardActive : ''}`}
              onClick={() => handleFilterChange('blue')}
            >
              <span className={styles.countValue}>{counts.blue}</span>
              <span className={styles.countLabel}>BLUE</span>
            </button>
          </div>
        )}

        {/* Queue List */}
        <section className={styles.section}>
          {loading ? (
            <p className={styles.loading}>Loading queue...</p>
          ) : queue.length === 0 ? (
            <p className={styles.emptyState}>
              <span>✅ No active triage cases</span>
              <span>You're all caught up.</span>
            </p>
          ) : (
            <div className={styles.caseList}>
              {queue.map((item) => {
                const rules = item.rules_fired.slice(0, 2).map(formatRuleId);
                const whyHere = rules.length > 0 ? rules.join(' · ') : '--';
                const rulesetLabel = item.ruleset_version
                  ? `ruleset v${item.ruleset_version}`
                  : 'ruleset version unknown';
                const slaText = item.sla_breached
                  ? 'SLA: breached'
                  : item.sla_minutes_remaining !== null
                    ? `SLA: ${formatDuration(item.sla_minutes_remaining)} left`
                    : 'SLA: --';
                const assignedLabel = item.assigned_to_user_initials || '--';
                const assignedTitle = item.assigned_to_user_name || 'Unassigned';
                const isAssigned = !!item.assigned_to_user_id;
                const isAssignedToMe = item.assigned_to_me;

                return (
                  <div key={item.id} className={styles.caseRow}>
                    <div className={styles.caseMain}>
                      <div className={styles.caseHeader}>
                        <span
                          className={getTierBadgeClass(item.tier)}
                          title={`Highest current risk tier (${rulesetLabel})`}
                        >
                          {item.tier?.toUpperCase() || 'Pending'}
                        </span>
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
                      <span className={styles.caseIndicator}>
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
      </main>
    </div>
  );
}

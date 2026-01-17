'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { getToken, removeToken } from '@/lib/auth';
import styles from './dashboard.module.css';

interface QueueItem {
  id: string;
  patient_id: string;
  patient_ref: string;
  tier: string | null;
  pathway: string | null;
  rules_fired: string[];
  ruleset_version: string | null;
  sla_breached: boolean;
  sla_minutes_remaining: number | null;
  age_minutes: number | null;
}

interface PriorityQueueResponse {
  items: QueueItem[];
  total: number;
  red_count: number;
  amber_count: number;
  green_count: number;
  blue_count: number;
  breached_count: number;
}

interface QueueCountsResponse {
  red: number;
  amber: number;
  green: number;
  blue: number;
  total: number;
  breached: number;
  red_oldest_minutes: number | null;
  red_oldest_breached: boolean;
  amber_oldest_minutes: number | null;
  amber_oldest_breached: boolean;
}

interface FeedbackConfig {
  active_window: string | null;
  banner_enabled: boolean;
}

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

type QueueScope = 'all' | 'me';

export default function DashboardPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [priorityCases, setPriorityCases] = useState<QueueItem[]>([]);
  const [error, setError] = useState('');
  const [queueCounts, setQueueCounts] = useState<QueueCountsResponse | null>(null);
  const [pendingCount, setPendingCount] = useState<number | null>(null);
  const [myActiveCount, setMyActiveCount] = useState<number | null>(null);
  const [lastSuccessAt, setLastSuccessAt] = useState<Date | null>(null);
  const [feedbackConfig, setFeedbackConfig] = useState<FeedbackConfig | null>(null);
  const [dutyRoster, setDutyRoster] = useState<DutyRosterResponse | null>(null);
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [queueScope, setQueueScope] = useState<QueueScope | null>(null);
  const incidentLoggedRef = useRef(false);

  const decodeTokenPayload = (token: string) => {
    try {
      const payload = token.split('.')[1];
      if (!payload) return null;
      const decoded = JSON.parse(atob(payload));
      return decoded as { sub?: string };
    } catch {
      return null;
    }
  };

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push('/auth/login');
      return;
    }

    const payload = decodeTokenPayload(token);
    setCurrentUserId(payload?.sub ?? null);

    Promise.all([
      fetchQueueCounts(token),
      fetchPriorityQueue(token, queueScope ?? 'all'),
      fetchPendingCount(token),
      fetchMyActiveCount(token),
      fetchDutyRoster(token),
      fetchFeedbackConfig(token),
    ]);
  }, [router, queueScope]);

  const getPilotPhase = async (token: string) => {
    try {
      const response = await fetch('/api/v1/pilot/status', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) return null;
      const data = await response.json();
      return data.phase as string;
    } catch {
      return null;
    }
  };

  const logIncidentCandidate = async (token: string, message: string) => {
    if (incidentLoggedRef.current) return;
    incidentLoggedRef.current = true;

    try {
      const pilotPhase = await getPilotPhase(token);
      const severity = pilotPhase === 'pilot' ? 'critical' : 'high';
      const reviewNote = pilotPhase === 'pilot' ? 'Pilot review required.' : 'Auto-logged by staff dashboard.';

      await fetch('/api/v1/incidents', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: 'Incident candidate: Triage queue unavailable',
          description: `Dashboard failed to load triage cases. Error: ${message}. Pilot phase: ${
            pilotPhase || 'unknown'
          }.`,
          category: 'access',
          severity,
          immediate_actions_taken: reviewNote,
        }),
      });
    } catch {
      // Intentionally ignore logging failures to avoid masking the primary error.
    }
  };

  const fetchQueueCounts = async (token: string) => {
    try {
      const response = await fetch('/api/v1/dashboard/queue/counts', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        return;
      }

      const data: QueueCountsResponse = await response.json();
      setQueueCounts(data);
    } catch {
      // Ignore count failures to keep the dashboard usable.
    }
  };

  const fetchPriorityQueue = async (token: string, scope: QueueScope) => {
    setLoading(true);
    setError('');

    try {
      const params = new URLSearchParams({ limit: '5' });
      if (scope === 'me') {
        params.set('assigned', 'me');
      }
      const response = await fetch(`/api/v1/triage-cases/queue?${params.toString()}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.status === 401 || response.status === 403) {
        removeToken();
        router.push('/auth/login');
        return;
      }

      if (!response.ok) {
        throw new Error('Failed to fetch priority cases');
      }

      const data: PriorityQueueResponse = await response.json();
      setPriorityCases(data.items || []);
      setLastSuccessAt(new Date());
      incidentLoggedRef.current = false;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load data';
      setError(message);
      await logIncidentCandidate(token, message);
    } finally {
      setLoading(false);
    }
  };

  const fetchDutyRoster = async (token: string) => {
    try {
      const response = await fetch('/api/v1/duty-roster/current', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) return;
      const data: DutyRosterResponse = await response.json();
      setDutyRoster(data);
    } catch {
      // Ignore duty roster failures.
    }
  };

  useEffect(() => {
    if (queueScope !== null || !currentUserId) return;
    const isDuty =
      dutyRoster?.primary?.id === currentUserId ||
      dutyRoster?.backup?.id === currentUserId;
    setQueueScope(isDuty ? 'all' : 'me');
  }, [queueScope, currentUserId, dutyRoster]);

  const fetchFeedbackConfig = async (token: string) => {
    try {
      const response = await fetch('/api/v1/pilot-feedback/config', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) return;
      const data = await response.json();
      setFeedbackConfig(data);
    } catch {
      // Ignore feedback config failures.
    }
  };

  const fetchPendingCount = async (token: string) => {
    try {
      const response = await fetch('/api/v1/triage-cases/queue?case_status=pending&limit=1', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        return;
      }

      const data: PriorityQueueResponse = await response.json();
      setPendingCount(data.total);
    } catch {
      // Ignore pending count failures to keep the dashboard usable.
    }
  };

  const fetchMyActiveCount = async (token: string) => {
    try {
      const response = await fetch('/api/v1/triage-cases/queue?assigned=me&limit=1', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        return;
      }

      const data: PriorityQueueResponse = await response.json();
      setMyActiveCount(data.total);
    } catch {
      // Ignore failures.
    }
  };

  const handleLogout = () => {
    removeToken();
    router.push('/');
  };

  const formatLastSuccess = (timestamp: Date | null) => {
    if (!timestamp) return '--';
    return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const formatDuration = (minutes?: number | null) => {
    if (minutes === null || minutes === undefined) return '--';
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  };

  const formatOldest = (minutes: number | null | undefined) => {
    if (minutes === null || minutes === undefined) return '--';
    return formatDuration(minutes);
  };

  const formatRuleId = (ruleId: string) => ruleId.replace(/_/g, ' ');

  const isStale = lastSuccessAt
    ? Date.now() - lastSuccessAt.getTime() > 5 * 60 * 1000
    : false;
  const hasData = priorityCases.length > 0;
  const statValue = (value: number | null) => (
    loading || (error && !hasData) || value === null ? '--' : value.toString()
  );

  const urgentCases = priorityCases.filter(
    (item) => item.tier === 'red' || item.tier === 'amber'
  );

  const redOldestMinutes = queueCounts?.red_oldest_minutes ?? null;
  const amberOldestMinutes = queueCounts?.amber_oldest_minutes ?? null;
  const redOldestBreached = queueCounts?.red_oldest_breached ?? false;
  const amberOldestBreached = queueCounts?.amber_oldest_breached ?? false;

  const feedbackWindowLabel = feedbackConfig?.active_window === 'WEEK_1'
    ? 'Week 1'
    : feedbackConfig?.active_window === 'WEEK_4'
      ? 'Week 4'
      : null;

  const dutyPrimaryName = dutyRoster?.primary?.full_name || 'Not set';
  const dutyPrimaryRole = dutyRoster?.primary?.title || dutyRoster?.primary?.role || '';
  const dutyBackupName = dutyRoster?.backup?.full_name || '--';
  const dutyBackupRole = dutyRoster?.backup?.title || dutyRoster?.backup?.role || '';

  const scopeValue = queueScope ?? 'all';
  const assignmentParam = scopeValue === 'me' ? 'assigned=me' : '';
  const buildQueueLink = (base: string) => {
    if (!assignmentParam) return base;
    return base.includes('?') ? `${base}&${assignmentParam}` : `${base}?${assignmentParam}`;
  };

  const lastUpdatedMinutes = lastSuccessAt
    ? Math.floor((Date.now() - lastSuccessAt.getTime()) / 60000)
    : null;

  return (
    <div className={styles.layout}>
      <aside className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <span className={styles.logo}>AcuCare</span>
        </div>
        <nav className={styles.nav}>
          <Link href="/dashboard" className={styles.navItemActive}>
            Dashboard
          </Link>
          <Link href="/dashboard/triage" className={styles.navItem}>
            Triage Cases
          </Link>
          <Link href="/dashboard/patients" className={styles.navItem}>
            Patients
          </Link>
          <Link href="/dashboard/referrals" className={styles.navItem}>
            Referrals
          </Link>
          <Link href="/dashboard/audit" className={styles.navItem}>
            Audit Log
          </Link>
          <Link href="/governance/pilot-feedback" className={styles.navItem}>
            Pilot Feedback
          </Link>
        </nav>
        <div className={styles.sidebarFooter}>
          <button onClick={handleLogout} className={styles.logoutButton}>
            Sign Out
          </button>
        </div>
      </aside>

      <main className={styles.main}>
        <header className={styles.header}>
          <h1>Dashboard</h1>
        </header>

        <div className={styles.content}>
          <div className={`${styles.statusBanner} ${styles.statusBannerTop}`}>
            {error || isStale ? (
              <p className={styles.statusTitle}>
                Warning: some services delayed - triage data last updated{' '}
                {lastUpdatedMinutes === null ? '--' : `${lastUpdatedMinutes}m`} ago
              </p>
            ) : (
              <p className={styles.statusTitle}>System operational</p>
            )}
            <p className={styles.statusMeta}>Last data refresh: {formatLastSuccess(lastSuccessAt)}</p>
          </div>

          {feedbackConfig?.banner_enabled && feedbackWindowLabel && (
            <div className={styles.feedbackBanner}>
              <span>Pilot feedback is open ({feedbackWindowLabel})</span>
              <Link
                href={`/governance/pilot-feedback?window=${feedbackConfig.active_window}`}
                className={styles.feedbackLink}
              >
                Give feedback
              </Link>
            </div>
          )}

          <div className={styles.kpiStrip}>
            <Link
              href={buildQueueLink('/dashboard/triage')}
              className={`${styles.statCard} ${styles.statCardLink}`}
            >
              <span className={styles.statValue}>{statValue(queueCounts?.total ?? null)}</span>
              <span className={styles.statLabel}>Active</span>
              <span className={styles.statCta}>View cases -&gt;</span>
            </Link>
            <Link
              href={buildQueueLink('/dashboard/triage?tier=red')}
              className={`${styles.statCard} ${styles.statCardLink} ${
                redOldestBreached ? styles.statCardBreach : ''
              }`}
            >
              <span className={styles.statValue}>{statValue(queueCounts?.red ?? null)}</span>
              <span className={styles.statLabel}>RED</span>
              <span
                className={`${styles.statSubtext} ${
                  redOldestBreached ? styles.statSubtextBreach : ''
                }`}
              >
                Oldest case: {formatOldest(redOldestMinutes)}
              </span>
              <span className={styles.statCta}>View cases -&gt;</span>
            </Link>
            <Link
              href={buildQueueLink('/dashboard/triage?tier=amber')}
              className={`${styles.statCard} ${styles.statCardLink} ${
                amberOldestBreached ? styles.statCardBreach : ''
              }`}
            >
              <span className={styles.statValue}>{statValue(queueCounts?.amber ?? null)}</span>
              <span className={styles.statLabel}>AMBER</span>
              <span
                className={`${styles.statSubtext} ${
                  amberOldestBreached ? styles.statSubtextBreach : ''
                }`}
              >
                Oldest case: {formatOldest(amberOldestMinutes)}
              </span>
              <span className={styles.statCta}>View cases -&gt;</span>
            </Link>
            <Link
              href={buildQueueLink('/dashboard/triage?case_status=pending')}
              className={`${styles.statCard} ${styles.statCardLink}`}
            >
              <span className={styles.statValue}>{statValue(pendingCount)}</span>
              <span className={styles.statLabel}>Pending</span>
              <span className={styles.statCta}>View cases -&gt;</span>
            </Link>
          </div>

          <section className={styles.dutyPanel}>
            <div>
              <h2>On duty today</h2>
              <p className={styles.dutyLine}>
                {dutyPrimaryName} <span>({dutyPrimaryRole || '—'})</span>
              </p>
              <p className={styles.dutyLine}>
                Backup: {dutyBackupName} <span>({dutyBackupRole || '—'})</span>
              </p>
            </div>
            <div className={styles.myCases}>
              <p className={styles.myCasesLabel}>My active cases</p>
              <p className={styles.myCasesValue}>{statValue(myActiveCount)}</p>
            </div>
          </section>

          <section className={styles.prioritySection}>
            <div className={styles.priorityHeader}>
              <h2>Priority cases</h2>
              <div className={styles.priorityControls}>
                <div className={styles.queueToggle}>
                  <button
                    className={`${styles.queueToggleButton} ${
                      scopeValue === 'all' ? styles.queueToggleActive : ''
                    }`}
                    onClick={() => setQueueScope('all')}
                  >
                    All cases
                  </button>
                  <button
                    className={`${styles.queueToggleButton} ${
                      scopeValue === 'me' ? styles.queueToggleActive : ''
                    }`}
                    onClick={() => setQueueScope('me')}
                  >
                    My cases
                  </button>
                </div>
                <Link href={buildQueueLink('/dashboard/triage')} className={styles.priorityLink}>
                  View full queue
                </Link>
              </div>
            </div>
            {loading && !hasData ? (
              <p className={styles.emptyState}>Loading priority cases...</p>
            ) : urgentCases.length === 0 ? (
              <p className={styles.emptyState}>
                <span>✅ No urgent cases right now</span>
                <span>You're all caught up.</span>
              </p>
            ) : (
              <div className={styles.priorityList}>
                {urgentCases.map((item) => {
                  const whyHere = item.rules_fired.length
                    ? formatRuleId(item.rules_fired[0])
                    : '--';
                  const slaText = item.sla_breached
                    ? 'SLA: breached'
                    : item.sla_minutes_remaining !== null
                      ? `SLA: ${formatDuration(item.sla_minutes_remaining)} left`
                      : 'SLA: --';
                  return (
                    <div key={item.id} className={styles.priorityRow}>
                      <div>
                        <div className={styles.priorityTop}>
                          <span
                            className={`${styles.priorityTier} ${
                              item.tier === 'amber' ? styles.priorityTierAmber : styles.priorityTierRed
                            }`}
                          >
                            {item.tier?.toUpperCase()}
                          </span>
                          <span className={styles.priorityRef}>{item.patient_ref}</span>
                          <span className={styles.priorityPathway}>
                            — {item.pathway || '--'}
                          </span>
                        </div>
                        <div className={styles.priorityWhy}>Why: {whyHere}</div>
                        <div className={styles.priorityMeta}>
                          Age: {formatDuration(item.age_minutes)} | {slaText}
                        </div>
                      </div>
                      <Link
                        href={`/dashboard/triage/${item.id}`}
                        className={styles.openCaseButton}
                      >
                        Open
                      </Link>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          <div className={styles.footerUtilities}>
            <Link href="/dashboard/audit" className={styles.footerLink}>
              View audit log
            </Link>
            <Link href="/dashboard/incidents" className={styles.footerLink}>
              System status
            </Link>
            <Link href="/dashboard/monitoring" className={styles.footerLink}>
              Help / escalation protocol
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}

'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import styles from './triage.module.css';

interface QueueCounts {
  red: number;
  amber: number;
  green: number;
  blue: number;
  total: number;
  breached: number;
}

interface QueueItem {
  id: string;
  patient_id: string;
  tier: string | null;
  pathway: string | null;
  status: string | null;
  created_at: string | null;
  triaged_at: string | null;
  sla_deadline: string | null;
  sla_target_minutes: number | null;
  sla_remaining_minutes: number | null;
  sla_status: string;
  sla_breached: boolean;
  clinician_review_required: boolean;
  assigned_clinician_id: string | null;
}

type TierFilter = 'all' | 'red' | 'amber' | 'green' | 'blue';

export default function TriageQueuePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [counts, setCounts] = useState<QueueCounts | null>(null);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState<TierFilter>('all');

  const getToken = useCallback(() => {
    return localStorage.getItem('access_token');
  }, []);

  const fetchCounts = useCallback(async (token: string) => {
    try {
      const response = await fetch('/api/v1/dashboard/queue/counts', {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.status === 401) {
        localStorage.removeItem('access_token');
        router.push('/auth/login');
        return;
      }

      if (!response.ok) throw new Error('Failed to fetch counts');

      const data = await response.json();
      setCounts(data);
    } catch (err) {
      console.error('Error fetching counts:', err);
    }
  }, [router]);

  const fetchQueue = useCallback(async (token: string, tierFilter: TierFilter) => {
    try {
      setLoading(true);
      const url = tierFilter === 'all'
        ? '/api/v1/dashboard/queue'
        : `/api/v1/dashboard/queue?tier=${tierFilter}`;

      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.status === 401) {
        localStorage.removeItem('access_token');
        router.push('/auth/login');
        return;
      }

      if (!response.ok) throw new Error('Failed to fetch queue');

      const data = await response.json();
      setQueue(data.items || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load queue');
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push('/auth/login');
      return;
    }

    fetchCounts(token);
    fetchQueue(token, filter);

    // Refresh every 30 seconds
    const interval = setInterval(() => {
      const t = getToken();
      if (t) {
        fetchCounts(t);
        fetchQueue(t, filter);
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [router, filter, fetchCounts, fetchQueue, getToken]);

  const handleFilterChange = (newFilter: TierFilter) => {
    setFilter(newFilter);
    const token = getToken();
    if (token) {
      fetchQueue(token, newFilter);
    }
  };

  const formatSlaTime = (minutes: number | null): string => {
    if (minutes === null) return '--';
    if (minutes < 0) return 'OVERDUE';

    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;

    if (hours > 0) {
      return `${hours}h ${mins}m`;
    }
    return `${mins}m`;
  };

  const getSlaStatusClass = (status: string): string => {
    switch (status) {
      case 'breached':
        return styles.slaBreach;
      case 'critical':
        return styles.slaCritical;
      case 'warning':
        return styles.slaWarning;
      default:
        return styles.slaNormal;
    }
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
        </nav>
      </aside>

      <main className={styles.main}>
        <header className={styles.header}>
          <h1>Triage Queue</h1>
          {counts && counts.breached > 0 && (
            <div className={styles.breachAlert}>
              {counts.breached} case{counts.breached !== 1 ? 's' : ''} breached SLA
            </div>
          )}
        </header>

        {error && <div className={styles.error}>{error}</div>}

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

        {/* Queue Table */}
        <section className={styles.section}>
          {loading ? (
            <p className={styles.loading}>Loading queue...</p>
          ) : queue.length === 0 ? (
            <p className={styles.emptyState}>No cases in queue.</p>
          ) : (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Case ID</th>
                  <th>Tier</th>
                  <th>Pathway</th>
                  <th>Status</th>
                  <th>SLA Remaining</th>
                  <th>Triaged</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {queue.map((item) => (
                  <tr key={item.id} className={item.sla_breached ? styles.rowBreach : ''}>
                    <td>{item.id.substring(0, 8)}...</td>
                    <td>
                      <span className={getTierBadgeClass(item.tier)}>
                        {item.tier?.toUpperCase() || 'Pending'}
                      </span>
                    </td>
                    <td>{item.pathway || '--'}</td>
                    <td>
                      <span className={styles.statusBadge}>{item.status}</span>
                    </td>
                    <td>
                      <span className={getSlaStatusClass(item.sla_status)}>
                        {formatSlaTime(item.sla_remaining_minutes)}
                      </span>
                    </td>
                    <td>
                      {item.triaged_at
                        ? new Date(item.triaged_at).toLocaleString()
                        : '--'}
                    </td>
                    <td>
                      <Link
                        href={`/dashboard/triage/${item.id}`}
                        className={styles.reviewButton}
                      >
                        Review
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </main>
    </div>
  );
}

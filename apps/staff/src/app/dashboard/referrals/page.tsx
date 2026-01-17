'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { getToken, removeToken } from '@/lib/auth';
import styles from './referrals.module.css';

interface Referral {
  id: string;
  patient_first_name: string;
  patient_last_name: string;
  patient_email: string;
  status: string;
  assigned_tier: string | null;
  assigned_pathway: string | null;
  disposition_confirmed_at: string | null;
  disposition_confirmed_by: string | null;
  created_at: string;
}

const TIER_LABELS: Record<string, string> = {
  TIER_1: 'Tier 1 - Self-Help',
  TIER_2: 'Tier 2 - Guided Self-Help',
  TIER_3: 'Tier 3 - Brief Therapy',
  TIER_4: 'Tier 4 - Specialist',
  CRISIS: 'Crisis Pathway',
};

const PATHWAY_LABELS: Record<string, string> = {
  SELF_HELP: 'Self-Help Resources',
  GUIDED_SELF_HELP: 'Guided Self-Help',
  CBT: 'CBT',
  COUNSELLING: 'Counselling',
  EMDR: 'EMDR',
  COMPLEX_NEEDS: 'Complex Needs',
  CRISIS: 'Crisis Team',
};

export default function ReferralsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [referrals, setReferrals] = useState<Referral[]>([]);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push('/auth/login');
      return;
    }

    // Fetch completed triage items (referrals)
    const params = new URLSearchParams({
      status: 'COMPLETED',
      limit: '100',
    });

    fetch(`/api/v1/triage?${params}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (res) => {
        if (res.status === 401 || res.status === 403) {
          removeToken();
          router.push('/auth/login');
          return;
        }
        if (!res.ok) {
          throw new Error('Failed to load referrals');
        }
        const data = await res.json();
        setReferrals(data);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load referrals');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [router]);

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  };

  const filteredReferrals = referrals.filter((r) => {
    if (filter === 'all') return true;
    return r.assigned_tier === filter;
  });

  const tierCounts = referrals.reduce((acc, r) => {
    const tier = r.assigned_tier || 'UNASSIGNED';
    acc[tier] = (acc[tier] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.breadcrumb}>
          <Link href="/dashboard">Dashboard</Link>
          <span>/</span>
          <span>Referrals</span>
        </div>
        <h1>Completed Referrals</h1>
        <p className={styles.subtitle}>
          {referrals.length} referral{referrals.length !== 1 ? 's' : ''} processed
        </p>
      </header>

      <div className={styles.filters}>
        <button
          className={`${styles.filterButton} ${filter === 'all' ? styles.active : ''}`}
          onClick={() => setFilter('all')}
        >
          All ({referrals.length})
        </button>
        {Object.entries(tierCounts).map(([tier, count]) => (
          <button
            key={tier}
            className={`${styles.filterButton} ${filter === tier ? styles.active : ''}`}
            onClick={() => setFilter(tier)}
          >
            {TIER_LABELS[tier] || tier} ({count})
          </button>
        ))}
      </div>

      <main className={styles.main}>
        {loading ? (
          <div className={styles.loading}>Loading referrals...</div>
        ) : error ? (
          <div className={styles.error}>
            <p>{error}</p>
            <button onClick={() => window.location.reload()} className={styles.retryButton}>
              Retry
            </button>
          </div>
        ) : filteredReferrals.length === 0 ? (
          <div className={styles.emptyState}>
            <p>No completed referrals found.</p>
            <Link href="/dashboard/triage" className={styles.triageLink}>
              Go to Triage Queue
            </Link>
          </div>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Patient</th>
                <th>Tier</th>
                <th>Pathway</th>
                <th>Confirmed</th>
                <th>Referred Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredReferrals.map((referral) => (
                <tr key={referral.id}>
                  <td className={styles.patientCell}>
                    <span className={styles.patientName}>
                      {referral.patient_first_name} {referral.patient_last_name}
                    </span>
                    <span className={styles.patientEmail}>{referral.patient_email}</span>
                  </td>
                  <td>
                    <span className={`${styles.tierBadge} ${styles[`tier${referral.assigned_tier?.replace('TIER_', '') || ''}`]}`}>
                      {TIER_LABELS[referral.assigned_tier || ''] || referral.assigned_tier || '-'}
                    </span>
                  </td>
                  <td>
                    {PATHWAY_LABELS[referral.assigned_pathway || ''] || referral.assigned_pathway || '-'}
                  </td>
                  <td>
                    {referral.disposition_confirmed_by ? (
                      <span className={styles.confirmed}>Yes</span>
                    ) : (
                      <span className={styles.pending}>Pending</span>
                    )}
                  </td>
                  <td>{formatDate(referral.disposition_confirmed_at || referral.created_at)}</td>
                  <td>
                    <Link href={`/dashboard/triage/${referral.id}`} className={styles.actionLink}>
                      View Details
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </main>
    </div>
  );
}

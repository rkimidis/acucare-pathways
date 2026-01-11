'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import styles from './dashboard.module.css';

interface TriageCase {
  id: string;
  patient_id: string;
  status: string;
  tier: string | null;
  created_at: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [triageCases, setTriageCases] = useState<TriageCase[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/auth/login');
      return;
    }

    // Fetch triage cases
    fetchTriageCases(token);
  }, [router]);

  const fetchTriageCases = async (token: string) => {
    try {
      const response = await fetch('/api/v1/triage-cases?limit=10', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.status === 401) {
        localStorage.removeItem('access_token');
        router.push('/auth/login');
        return;
      }

      if (!response.ok) {
        throw new Error('Failed to fetch triage cases');
      }

      const data = await response.json();
      setTriageCases(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    router.push('/');
  };

  const getTierBadgeClass = (tier: string | null) => {
    switch (tier) {
      case 'red':
        return styles.tierRed;
      case 'amber':
        return styles.tierAmber;
      case 'green':
        return styles.tierGreen;
      default:
        return styles.tierPending;
    }
  };

  if (loading) {
    return (
      <main className={styles.main}>
        <p>Loading...</p>
      </main>
    );
  }

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
          {error && <div className={styles.error}>{error}</div>}

          <div className={styles.statsGrid}>
            <div className={styles.statCard}>
              <span className={styles.statValue}>{triageCases.length}</span>
              <span className={styles.statLabel}>Active Cases</span>
            </div>
            <div className={styles.statCard}>
              <span className={styles.statValue}>
                {triageCases.filter((c) => c.tier === 'red').length}
              </span>
              <span className={styles.statLabel}>RED Tier</span>
            </div>
            <div className={styles.statCard}>
              <span className={styles.statValue}>
                {triageCases.filter((c) => c.tier === 'amber').length}
              </span>
              <span className={styles.statLabel}>AMBER Tier</span>
            </div>
            <div className={styles.statCard}>
              <span className={styles.statValue}>
                {triageCases.filter((c) => c.status === 'pending').length}
              </span>
              <span className={styles.statLabel}>Pending Triage</span>
            </div>
          </div>

          <section className={styles.section}>
            <h2>Recent Triage Cases</h2>
            {triageCases.length === 0 ? (
              <p className={styles.emptyState}>No triage cases found.</p>
            ) : (
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Case ID</th>
                    <th>Status</th>
                    <th>Tier</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {triageCases.map((tc) => (
                    <tr key={tc.id}>
                      <td>{tc.id.substring(0, 8)}...</td>
                      <td>
                        <span className={styles.statusBadge}>{tc.status}</span>
                      </td>
                      <td>
                        <span className={getTierBadgeClass(tc.tier)}>
                          {tc.tier || 'Pending'}
                        </span>
                      </td>
                      <td>{new Date(tc.created_at).toLocaleDateString()}</td>
                      <td>
                        <Link
                          href={`/dashboard/triage/${tc.id}`}
                          className={styles.viewLink}
                        >
                          View
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}

'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { getToken, removeToken } from '@/lib/auth';
import { AppShell, EmptyState, PageHeader } from '@/ui/components';
import styles from './referrals.module.css';

interface CompletedCase {
  id: string;
  patient_id: string;
  patient_first_name: string;
  patient_last_name: string;
  pathway: string | null;
  status: string;
  closed_at: string | null;
  closed_by_name: string | null;
  final_outcome: string | null;
  final_outcome_type: string | null;
  has_pdf: boolean;
}

interface CompletedCasesResponse {
  items: CompletedCase[];
  total: number;
}

// Map outcome types to human-readable labels
const OUTCOME_LABELS: Record<string, string> = {
  ASSESSMENT_BOOKED: 'Assessment booked',
  TREATMENT_STARTED: 'Treatment started',
  EXTERNAL_REFERRAL: 'Referred externally',
  DISCHARGED: 'Discharged with advice',
  SIGNPOSTED: 'Signposted to resources',
  DECLINED: 'Patient declined',
  INAPPROPRIATE: 'Inappropriate referral',
  NO_CONTACT: 'Unable to contact',
  SELF_DISCHARGE: 'Self-discharged',
  COMPLETED_CARE: 'Care completed',
};

const PATHWAY_LABELS: Record<string, string> = {
  THERAPY_ASSESSMENT: 'Therapy Assessment',
  PSYCHIATRY_ASSESSMENT: 'Psychiatry Assessment',
  MEDICATION_REVIEW: 'Medication Review',
  WELLBEING_SUPPORT: 'Wellbeing Support',
  CRISIS_SUPPORT: 'Crisis Support',
  SIGNPOSTING: 'Signposting',
};

export default function CompletedCasesPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [cases, setCases] = useState<CompletedCase[]>([]);
  const [total, setTotal] = useState(0);

  const fetchCompletedCases = useCallback(async () => {
    const token = getToken();
    if (!token) {
      router.push('/auth/login');
      return;
    }

    setLoading(true);
    setFetchError(null);

    try {
      // Fetch closed triage cases
      const params = new URLSearchParams({
        case_status: 'closed',
        limit: '100',
      });

      const res = await fetch(`/api/v1/triage-cases/queue?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.status === 401 || res.status === 403) {
        removeToken();
        router.push('/auth/login');
        return;
      }

      if (!res.ok) {
        throw new Error('Failed to load completed cases');
      }

      const data: CompletedCasesResponse = await res.json();
      setCases(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      // Only set error for genuine API failures
      setFetchError(err instanceof Error ? err.message : 'Failed to load completed cases');
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    fetchCompletedCases();
  }, [fetchCompletedCases]);

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  };

  const getOutcomeLabel = (outcomeType: string | null, outcome: string | null): string => {
    if (outcomeType && OUTCOME_LABELS[outcomeType]) {
      return OUTCOME_LABELS[outcomeType];
    }
    if (outcome) {
      return outcome;
    }
    return 'Closed';
  };

  const getPathwayLabel = (pathway: string | null): string => {
    if (!pathway) return '-';
    if (PATHWAY_LABELS[pathway]) {
      return PATHWAY_LABELS[pathway];
    }
    // Convert snake_case to Title Case
    return pathway
      .replace(/_/g, ' ')
      .toLowerCase()
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  const handleDownloadPdf = async (caseId: string) => {
    const token = getToken();
    if (!token) return;

    try {
      const res = await fetch(`/api/v1/triage-cases/${caseId}/pdf`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) throw new Error('Failed to download PDF');

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `case-${caseId.substring(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to download PDF:', err);
    }
  };

  const handleLogout = () => {
    removeToken();
    router.push('/');
  };

  return (
    <AppShell activeNav="referrals" onSignOut={handleLogout}>
      <PageHeader
        title="Completed Cases"
        breadcrumb={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Completed Cases' },
        ]}
        metaText={total > 0 ? `${total} case${total !== 1 ? 's' : ''} closed` : undefined}
      />

      <div className={styles.content}>
        {/* Page definition */}
        <p className={styles.pageDefinition}>
          Triage cases that have been reviewed and closed with a final outcome.
        </p>

        <main className={styles.main}>
          {loading ? (
            <EmptyState title="Loading completed cases" variant="loading" />
          ) : fetchError ? (
            // Only show error for genuine API failures
            <EmptyState
              title="Unable to load completed cases"
              message={fetchError}
              actionLabel="Retry"
              onAction={fetchCompletedCases}
              variant="error"
            />
          ) : cases.length === 0 ? (
            // Neutral empty state - not an error
            <div className={styles.emptyStateBox}>
              <div className={styles.emptyStateIcon}>📋</div>
              <h3>No completed cases yet</h3>
              <p>Completed cases will appear here once triage reviews are finalised.</p>
            </div>
          ) : (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Patient</th>
                  <th>Case ID</th>
                  <th>Final Outcome</th>
                  <th>Pathway</th>
                  <th>Date Closed</th>
                  <th>Closed By</th>
                  <th>Evidence</th>
                </tr>
              </thead>
              <tbody>
                {cases.map((caseItem) => (
                  <tr key={caseItem.id}>
                    <td className={styles.patientCell}>
                      <Link
                        href={`/dashboard/triage/${caseItem.id}`}
                        className={styles.patientLink}
                      >
                        {caseItem.patient_first_name} {caseItem.patient_last_name}
                      </Link>
                    </td>
                    <td className={styles.caseId}>
                      {caseItem.id.substring(0, 8)}
                    </td>
                    <td>
                      <span className={styles.outcomeBadge}>
                        {getOutcomeLabel(caseItem.final_outcome_type, caseItem.final_outcome)}
                      </span>
                    </td>
                    <td>{getPathwayLabel(caseItem.pathway)}</td>
                    <td>{formatDate(caseItem.closed_at)}</td>
                    <td>{caseItem.closed_by_name || '-'}</td>
                    <td>
                      <button
                        onClick={() => handleDownloadPdf(caseItem.id)}
                        className={styles.pdfButton}
                        title="Download case PDF"
                      >
                        PDF
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </main>
      </div>
    </AppShell>
  );
}

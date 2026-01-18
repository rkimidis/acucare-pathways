'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { getToken, removeToken } from '@/lib/auth';
import { AppShell, Button, EmptyState, PageHeader, StatusBadge } from '@/ui/components';
import styles from './patients.module.css';

interface Patient {
  id: string;
  first_name: string;
  last_name: string;
  preferred_name: string | null;
  email: string;
  phone_e164: string | null;
  date_of_birth: string | null;
  postcode: string | null;
  nhs_number: string | null;
  is_active: boolean;
  created_at: string;
  possible_duplicate?: boolean;
  matched_field?: string;
}

interface PaginatedResponse {
  items: Patient[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

type DataCompleteness = 'complete' | 'partial' | 'critical';

export default function PatientsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const pageSize = 25;
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  // Data completeness assessment
  const getDataCompleteness = (patient: Patient): DataCompleteness => {
    // Critical: DOB or contact (email/phone) missing
    if (!patient.date_of_birth || (!patient.email && !patient.phone_e164)) {
      return 'critical';
    }
    // Partial: postcode missing
    if (!patient.postcode) {
      return 'partial';
    }
    // Complete: all core demographics present
    return 'complete';
  };

  const getCompletenessLabel = (completeness: DataCompleteness) => {
    switch (completeness) {
      case 'complete':
        return { icon: '🟢', text: 'Complete', className: styles.completenessComplete };
      case 'partial':
        return { icon: '🟠', text: 'Partial', className: styles.completenessPartial };
      case 'critical':
        return { icon: '🔴', text: 'Missing critical', className: styles.completenessCritical };
    }
  };

  const fetchPatients = useCallback(async (query: string, pageNum: number) => {
    const token = getToken();
    if (!token) {
      router.push('/auth/login');
      return;
    }

    setLoading(true);
    const params = new URLSearchParams({
      page: pageNum.toString(),
      page_size: pageSize.toString(),
    });
    if (query) {
      params.append('search', query);
    }

    try {
      const res = await fetch(`/api/v1/patients?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.status === 401 || res.status === 403) {
        removeToken();
        router.push('/auth/login');
        return;
      }
      if (!res.ok) {
        throw new Error('Failed to load patients');
      }
      const data: PaginatedResponse = await res.json();
      setPatients(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load patients');
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    fetchPatients(searchQuery, page);
  }, [page, searchQuery, fetchPatients]);

  // Debounced search on typing
  const handleSearchInput = (value: string) => {
    setSearchInput(value);

    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(() => {
      setPage(1);
      setSearchQuery(value);
    }, 400);
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    setPage(1);
    setSearchQuery(searchInput);
  };

  // Highlight matched text in search results
  const highlightMatch = (text: string, query: string) => {
    if (!query || !text) return text;
    const lowerText = text.toLowerCase();
    const lowerQuery = query.toLowerCase();
    const index = lowerText.indexOf(lowerQuery);
    if (index === -1) return text;

    return (
      <>
        {text.substring(0, index)}
        <mark className={styles.searchHighlight}>{text.substring(index, index + query.length)}</mark>
        {text.substring(index + query.length)}
      </>
    );
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-GB');
  };

  const totalPages = Math.ceil(total / pageSize);

  const handleLogout = () => {
    removeToken();
    router.push('/');
  };

  return (
    <AppShell activeNav="patients" onSignOut={handleLogout}>
      <PageHeader
        title="Patient Records"
        breadcrumb={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Patients' },
        ]}
        metaText={`${total} patient${total !== 1 ? 's' : ''} in the system`}
      />

      <div className={styles.content}>
        <div className={styles.toolbar}>
          <form onSubmit={handleSearch} className={styles.searchForm}>
            <div className={styles.searchInputWrapper}>
              <input
                type="text"
                placeholder="Search by name, email, or NHS number..."
                value={searchInput}
                onChange={(e) => handleSearchInput(e.target.value)}
                className={styles.searchInput}
              />
              {searchInput && loading && (
                <span className={styles.searchingIndicator}>Searching...</span>
              )}
            </div>
            <Button type="submit" variant="primary">
              Search
            </Button>
          </form>
        </div>

        <main className={styles.main}>
          {loading ? (
            <EmptyState title="Loading patients" variant="loading" />
          ) : error ? (
            <EmptyState
              title="Failed to load patients"
            message={error}
            actionLabel="Retry"
            onAction={() => window.location.reload()}
            variant="error"
          />
        ) : patients.length === 0 ? (
          <EmptyState
            title="No patients found"
            message={searchQuery ? `No matches for "${searchQuery}".` : 'No patients available yet.'}
          />
        ) : (
          <>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Data</th>
                  <th>Email</th>
                  <th>Phone</th>
                  <th>DOB</th>
                  <th>Postcode</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {patients.map((patient) => {
                  const completeness = getDataCompleteness(patient);
                  const completenessLabel = getCompletenessLabel(completeness);
                  const fullName = `${patient.first_name} ${patient.last_name}`;

                  return (
                    <tr key={patient.id}>
                      <td className={styles.nameCell}>
                        <Link
                          href={`/dashboard/patients/${patient.id}`}
                          className={styles.nameLink}
                        >
                          <span className={styles.fullName}>
                            {searchQuery ? highlightMatch(fullName, searchQuery) : fullName}
                          </span>
                          {patient.preferred_name && (
                            <span className={styles.preferredName}>
                              "{patient.preferred_name}"
                            </span>
                          )}
                        </Link>
                        {patient.possible_duplicate && (
                          <span className={styles.duplicateWarning} title="Possible duplicate record">
                            ⚠️ Possible duplicate
                          </span>
                        )}
                      </td>
                      <td>
                        <span
                          className={`${styles.completenessIndicator} ${completenessLabel.className}`}
                          title={completeness === 'critical' ? 'Missing DOB or contact info' : completeness === 'partial' ? 'Missing postcode' : 'All core data present'}
                        >
                          {completenessLabel.icon} {completenessLabel.text}
                        </span>
                      </td>
                      <td>{searchQuery ? highlightMatch(patient.email, searchQuery) : patient.email}</td>
                      <td>{patient.phone_e164 || '-'}</td>
                      <td>{formatDate(patient.date_of_birth)}</td>
                      <td>{patient.postcode || '-'}</td>
                      <td>
                        <StatusBadge
                          tone={patient.is_active ? 'green' : 'neutral'}
                          label={patient.is_active ? 'Active' : 'Inactive'}
                        />
                      </td>
                      <td className={styles.actions}>
                        <Link
                          href={`/dashboard/patients/${patient.id}/history`}
                          className={styles.actionLink}
                        >
                          History
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {totalPages > 1 && (
              <div className={styles.pagination}>
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className={styles.pageButton}
                >
                  Previous
                </button>
                <span className={styles.pageInfo}>
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className={styles.pageButton}
                >
                  Next
                </button>
              </div>
            )}
          </>
          )}
        </main>
      </div>
    </AppShell>
  );
}

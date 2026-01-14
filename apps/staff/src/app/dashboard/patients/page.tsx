'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
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
  is_active: boolean;
  created_at: string;
}

interface PaginatedResponse {
  items: Patient[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

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

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/auth/login');
      return;
    }

    setLoading(true);
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    });
    if (searchQuery) {
      params.append('search', searchQuery);
    }

    fetch(`/api/v1/patients?${params}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (res) => {
        if (res.status === 401) {
          localStorage.removeItem('access_token');
          router.push('/auth/login');
          return;
        }
        if (!res.ok) {
          throw new Error('Failed to load patients');
        }
        const data: PaginatedResponse = await res.json();
        setPatients(data.items);
        setTotal(data.total);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load patients');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [page, searchQuery, router]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    setSearchQuery(searchInput);
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-GB');
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.breadcrumb}>
          <Link href="/dashboard">Dashboard</Link>
          <span>/</span>
          <span>Patients</span>
        </div>
        <h1>Patient Records</h1>
        <p className={styles.subtitle}>
          {total} patient{total !== 1 ? 's' : ''} in the system
        </p>
      </header>

      <div className={styles.toolbar}>
        <form onSubmit={handleSearch} className={styles.searchForm}>
          <input
            type="text"
            placeholder="Search by name, email, or NHS number..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className={styles.searchInput}
          />
          <button type="submit" className={styles.searchButton}>
            Search
          </button>
        </form>
      </div>

      <main className={styles.main}>
        {loading ? (
          <div className={styles.loading}>Loading patients...</div>
        ) : error ? (
          <div className={styles.error}>
            <p>{error}</p>
            <button onClick={() => window.location.reload()} className={styles.retryButton}>
              Retry
            </button>
          </div>
        ) : patients.length === 0 ? (
          <div className={styles.emptyState}>
            <p>No patients found{searchQuery ? ` matching "${searchQuery}"` : ''}.</p>
          </div>
        ) : (
          <>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Phone</th>
                  <th>DOB</th>
                  <th>Postcode</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {patients.map((patient) => (
                  <tr key={patient.id}>
                    <td className={styles.nameCell}>
                      <span className={styles.fullName}>
                        {patient.first_name} {patient.last_name}
                      </span>
                      {patient.preferred_name && (
                        <span className={styles.preferredName}>
                          "{patient.preferred_name}"
                        </span>
                      )}
                    </td>
                    <td>{patient.email}</td>
                    <td>{patient.phone_e164 || '-'}</td>
                    <td>{formatDate(patient.date_of_birth)}</td>
                    <td>{patient.postcode || '-'}</td>
                    <td>
                      <span className={patient.is_active ? styles.statusActive : styles.statusInactive}>
                        {patient.is_active ? 'Active' : 'Inactive'}
                      </span>
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
                ))}
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
  );
}

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import EmergencyBanner from '@/components/EmergencyBanner';
import { getToken, removeToken } from '@/lib/auth';
import styles from './appointments.module.css';

interface Appointment {
  id: string;
  scheduled_datetime: string;
  appointment_type: string;
  clinician_name: string | null;
  status: string;
  location_or_link: string | null;
  notes: string | null;
}

export default function AppointmentsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push('/auth/login');
      return;
    }

    fetch('/api/v1/scheduling/patient/appointments', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (res) => {
        if (res.status === 401) {
          removeToken();
          router.push('/auth/login');
          return;
        }
        if (!res.ok) {
          throw new Error('Failed to load appointments');
        }
        const data = await res.json();
        setAppointments(data);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load appointments');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [router]);

  const handleLogout = () => {
    removeToken();
    router.push('/');
  };

  const formatDateTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString('en-GB', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status.toLowerCase()) {
      case 'confirmed':
        return styles.statusConfirmed;
      case 'pending':
        return styles.statusPending;
      case 'cancelled':
        return styles.statusCancelled;
      case 'completed':
        return styles.statusCompleted;
      default:
        return '';
    }
  };

  return (
    <main className={styles.main}>
      <EmergencyBanner />

      <header className={styles.header}>
        <div className={styles.headerNav}>
          <Link href="/dashboard" className={styles.backLink}>
            Back to Dashboard
          </Link>
          <h1>My Appointments</h1>
        </div>
        <button onClick={handleLogout} className={styles.logoutButton}>
          Sign Out
        </button>
      </header>

      <div className={styles.content}>
        {loading ? (
          <div className={styles.loading}>Loading appointments...</div>
        ) : error ? (
          <div className={styles.error}>
            <p>{error}</p>
            <button
              onClick={() => window.location.reload()}
              className={styles.retryButton}
            >
              Retry
            </button>
          </div>
        ) : appointments.length === 0 ? (
          <section className={styles.emptyState}>
            <h2>No Appointments</h2>
            <p>You don&apos;t have any scheduled appointments at this time.</p>
            <p className={styles.hint}>
              Once your intake questionnaire has been reviewed and a triage tier
              assigned, you&apos;ll be able to book appointments here.
            </p>
            <Link href="/dashboard" className={styles.primaryButton}>
              Return to Dashboard
            </Link>
          </section>
        ) : (
          <>
            <section className={styles.upcomingSection}>
              <h2>Upcoming Appointments</h2>
              {appointments
                .filter((apt) => new Date(apt.scheduled_datetime) >= new Date())
                .map((apt) => (
                  <div key={apt.id} className={styles.appointmentCard}>
                    <div className={styles.appointmentHeader}>
                      <span className={styles.appointmentType}>
                        {apt.appointment_type}
                      </span>
                      <span
                        className={`${styles.statusBadge} ${getStatusBadgeClass(apt.status)}`}
                      >
                        {apt.status}
                      </span>
                    </div>
                    <div className={styles.appointmentDetails}>
                      <p className={styles.dateTime}>
                        {formatDateTime(apt.scheduled_datetime)}
                      </p>
                      {apt.clinician_name && (
                        <p className={styles.clinician}>
                          With: {apt.clinician_name}
                        </p>
                      )}
                      {apt.location_or_link && (
                        <p className={styles.location}>
                          {apt.location_or_link.startsWith('http') ? (
                            <a
                              href={apt.location_or_link}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              Join Video Call
                            </a>
                          ) : (
                            <>Location: {apt.location_or_link}</>
                          )}
                        </p>
                      )}
                      {apt.notes && (
                        <p className={styles.notes}>{apt.notes}</p>
                      )}
                    </div>
                  </div>
                ))}
              {appointments.filter(
                (apt) => new Date(apt.scheduled_datetime) >= new Date()
              ).length === 0 && (
                <p className={styles.placeholder}>No upcoming appointments.</p>
              )}
            </section>

            <section className={styles.pastSection}>
              <h2>Past Appointments</h2>
              {appointments
                .filter((apt) => new Date(apt.scheduled_datetime) < new Date())
                .slice(0, 5)
                .map((apt) => (
                  <div
                    key={apt.id}
                    className={`${styles.appointmentCard} ${styles.pastCard}`}
                  >
                    <div className={styles.appointmentHeader}>
                      <span className={styles.appointmentType}>
                        {apt.appointment_type}
                      </span>
                      <span
                        className={`${styles.statusBadge} ${getStatusBadgeClass(apt.status)}`}
                      >
                        {apt.status}
                      </span>
                    </div>
                    <div className={styles.appointmentDetails}>
                      <p className={styles.dateTime}>
                        {formatDateTime(apt.scheduled_datetime)}
                      </p>
                      {apt.clinician_name && (
                        <p className={styles.clinician}>
                          With: {apt.clinician_name}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              {appointments.filter(
                (apt) => new Date(apt.scheduled_datetime) < new Date()
              ).length === 0 && (
                <p className={styles.placeholder}>No past appointments.</p>
              )}
            </section>
          </>
        )}
      </div>
    </main>
  );
}

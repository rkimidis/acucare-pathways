'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import EmergencyBanner from '@/components/EmergencyBanner';
import CancelAppointmentModal, { CancelResult } from '@/components/CancelAppointmentModal';
import RescheduleAppointmentModal, { RescheduleResult } from '@/components/RescheduleAppointmentModal';
import { getToken, removeToken } from '@/lib/auth';
import styles from './appointments.module.css';

interface Appointment {
  id: string;
  scheduled_datetime: string;
  appointment_type: string;
  appointment_type_id: string;
  clinician_id: string;
  clinician_name: string | null;
  status: string;
  location_or_link: string | null;
  notes: string | null;
  reschedule_count?: number;
  triage_case_id?: string;
}

export default function AppointmentsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Modal state
  const [cancelModal, setCancelModal] = useState<Appointment | null>(null);
  const [rescheduleModal, setRescheduleModal] = useState<Appointment | null>(null);
  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'info'; text: string } | null>(null);

  const fetchAppointments = useCallback(async () => {
    const token = getToken();
    if (!token) {
      router.push('/auth/login');
      return;
    }

    try {
      const res = await fetch('/api/v1/scheduling/patient/appointments?include_past=true', {
        headers: { Authorization: `Bearer ${token}` },
      });

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
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load appointments');
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    fetchAppointments();
  }, [fetchAppointments]);

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
      case 'scheduled':
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

  const canModifyAppointment = (apt: Appointment) => {
    const status = apt.status.toLowerCase();
    return (
      status !== 'cancelled' &&
      status !== 'completed' &&
      status !== 'no_show' &&
      new Date(apt.scheduled_datetime) > new Date()
    );
  };

  const handleCancelSuccess = (result: CancelResult) => {
    setCancelModal(null);

    if (result.cancelled) {
      setActionMessage({ type: 'success', text: 'Your appointment has been cancelled.' });
      fetchAppointments();
    } else if (result.safety_workflow_triggered) {
      setActionMessage({ type: 'info', text: 'A member of our team will contact you soon.' });
    } else if (result.request_submitted) {
      setActionMessage({ type: 'info', text: 'Your cancellation request has been received.' });
    }

    // Clear message after 5 seconds
    setTimeout(() => setActionMessage(null), 5000);
  };

  const handleRescheduleSuccess = (result: RescheduleResult) => {
    setRescheduleModal(null);

    if (result.rescheduled) {
      setActionMessage({ type: 'success', text: 'Your appointment has been rescheduled.' });
      fetchAppointments();
    } else if (result.request_submitted) {
      setActionMessage({ type: 'info', text: 'Your reschedule request has been received.' });
    }

    // Clear message after 5 seconds
    setTimeout(() => setActionMessage(null), 5000);
  };

  const upcomingAppointments = appointments.filter(
    (apt) => new Date(apt.scheduled_datetime) >= new Date()
  );

  const pastAppointments = appointments
    .filter((apt) => new Date(apt.scheduled_datetime) < new Date())
    .slice(0, 5);

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
        {actionMessage && (
          <div className={`${styles.actionMessage} ${styles[actionMessage.type]}`}>
            {actionMessage.text}
          </div>
        )}

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
              {upcomingAppointments.map((apt) => (
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

                  {canModifyAppointment(apt) && (
                    <div className={styles.appointmentActions}>
                      <button
                        onClick={() => setRescheduleModal(apt)}
                        className={styles.rescheduleButton}
                      >
                        Reschedule
                      </button>
                      <button
                        onClick={() => setCancelModal(apt)}
                        className={styles.cancelButton}
                      >
                        Cancel
                      </button>
                    </div>
                  )}
                </div>
              ))}
              {upcomingAppointments.length === 0 && (
                <p className={styles.placeholder}>No upcoming appointments.</p>
              )}
            </section>

            <section className={styles.pastSection}>
              <h2>Past Appointments</h2>
              {pastAppointments.map((apt) => (
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
              {pastAppointments.length === 0 && (
                <p className={styles.placeholder}>No past appointments.</p>
              )}
            </section>
          </>
        )}
      </div>

      {/* Cancel Modal */}
      {cancelModal && (
        <CancelAppointmentModal
          appointment={cancelModal}
          onClose={() => setCancelModal(null)}
          onSuccess={handleCancelSuccess}
        />
      )}

      {/* Reschedule Modal */}
      {rescheduleModal && (
        <RescheduleAppointmentModal
          appointment={rescheduleModal}
          onClose={() => setRescheduleModal(null)}
          onSuccess={handleRescheduleSuccess}
        />
      )}
    </main>
  );
}

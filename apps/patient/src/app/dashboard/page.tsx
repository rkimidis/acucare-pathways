'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import EmergencyBanner from '@/components/EmergencyBanner';
import { getToken, removeToken } from '@/lib/auth';
import styles from './dashboard.module.css';

export default function DashboardPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [intakeComplete, setIntakeComplete] = useState(false);

  useEffect(() => {
    // Check for auth token
    const token = getToken();
    if (!token) {
      router.push('/auth/login');
    } else {
      setLoading(false);
      // Check if intake was just completed
      if (searchParams.get('intake') === 'complete') {
        setIntakeComplete(true);
      }
    }
  }, [router, searchParams]);

  const handleLogout = () => {
    removeToken();
    router.push('/');
  };

  const handleStartIntake = () => {
    router.push('/intake');
  };

  if (loading) {
    return (
      <main className={styles.main}>
        <p>Loading...</p>
      </main>
    );
  }

  return (
    <main className={styles.main}>
      <EmergencyBanner />

      <header className={styles.header}>
        <h1>Patient Dashboard</h1>
        <button onClick={handleLogout} className={styles.logoutButton}>
          Sign Out
        </button>
      </header>

      <div className={styles.content}>
        {intakeComplete && (
          <section className={styles.successCard}>
            <h2>Questionnaire Submitted</h2>
            <p>
              Thank you for completing the intake questionnaire. Our clinical
              team will review your responses and contact you within 24-48
              hours with next steps.
            </p>
          </section>
        )}

        <section className={styles.card}>
          <h2>Welcome</h2>
          <p>
            This is your patient portal. From here you can complete
            questionnaires, view your triage status, and manage your
            appointments.
          </p>
        </section>

        <section className={styles.card}>
          <h2>Pending Questionnaires</h2>
          {intakeComplete ? (
            <p className={styles.placeholder}>
              Your intake questionnaire has been submitted and is pending
              review.
            </p>
          ) : (
            <>
              <p>Complete your initial assessment to begin the triage process.</p>
              <button
                onClick={handleStartIntake}
                className={styles.primaryButton}
              >
                Start Intake Questionnaire
              </button>
            </>
          )}
        </section>

        <section className={styles.card}>
          <h2>Triage Status</h2>
          <p className={styles.placeholder}>
            {intakeComplete
              ? 'Your triage tier will be assigned once our clinical team reviews your responses.'
              : 'Your triage information will appear here once you complete the intake questionnaire.'}
          </p>
        </section>

        <section className={styles.card}>
          <h2>Upcoming Appointments</h2>
          <p className={styles.placeholder}>No upcoming appointments.</p>
        </section>
      </div>
    </main>
  );
}

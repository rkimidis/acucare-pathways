'use client';

import Link from 'next/link';
import styles from './page.module.css';

export default function Home() {
  return (
    <main className={styles.main}>
      <div className={styles.container}>
        <h1 className={styles.title}>AcuCare Patient Portal</h1>
        <p className={styles.description}>
          Welcome to the AcuCare patient portal. Please sign in to access your
          appointments, questionnaires, and clinical information.
        </p>
        <div className={styles.actions}>
          <Link href="/auth/login" className={styles.primaryButton}>
            Sign In
          </Link>
          <Link href="/auth/request-link" className={styles.secondaryButton}>
            Request Magic Link
          </Link>
        </div>
        <footer className={styles.footer}>
          <p>
            Need help? Contact us at{' '}
            <a href="mailto:support@acucare.local">support@acucare.local</a>
          </p>
          <p className={styles.legal}>
            This is a CQC-registered private psychiatric clinic. All data is
            handled in accordance with UK GDPR.
          </p>
        </footer>
      </div>
    </main>
  );
}

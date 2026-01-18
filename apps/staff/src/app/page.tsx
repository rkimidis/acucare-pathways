'use client';

import Link from 'next/link';
import styles from './page.module.css';

export default function Home() {
  return (
    <main className={styles.main}>
      <div className={styles.container}>
        <div className={styles.logo}>AcuCare Pathways</div>
        <h1 className={styles.title}>Staff Console</h1>
        <p className={styles.description}>
          Clinical workflow management for AcuCare Pathways staff. Sign in to access
          patient triage, appointments, and clinical tools.
        </p>
        <div className={styles.actions}>
          <Link href="/auth/login" className={styles.primaryButton}>
            Staff Sign In
          </Link>
        </div>
        <footer className={styles.footer}>
          <p className={styles.legal}>
            Authorised personnel only. All access is logged for CQC compliance.
          </p>
        </footer>
      </div>
    </main>
  );
}

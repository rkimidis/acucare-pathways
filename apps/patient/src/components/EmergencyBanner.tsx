'use client';

import { useEffect, useState } from 'react';
import styles from './EmergencyBanner.module.css';

interface SafetyBanner {
  enabled: boolean;
  text: string;
  consent_version: string;
}

export default function EmergencyBanner() {
  const [banner, setBanner] = useState<SafetyBanner | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    // Fetch safety banner from API
    fetch('/api/v1/intake/safety-banner')
      .then((res) => res.json())
      .then((data) => setBanner(data))
      .catch((err) => {
        console.error('Failed to fetch safety banner:', err);
        // Show fallback banner if API fails
        setBanner({
          enabled: true,
          text: 'If you are experiencing a mental health emergency or have thoughts of harming yourself or others, please call 999 or go to your nearest A&E.',
          consent_version: '1.0',
        });
      });
  }, []);

  if (!banner?.enabled || dismissed) {
    return null;
  }

  return (
    <div className={styles.banner} role="alert" aria-live="polite">
      <div className={styles.icon}>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
      </div>
      <div className={styles.content}>
        <strong>Emergency Help</strong>
        <p>{banner.text}</p>
        <div className={styles.contacts}>
          <a href="tel:999" className={styles.emergencyLink}>
            Call 999
          </a>
          <a href="tel:116123" className={styles.helplineLink}>
            Samaritans: 116 123
          </a>
        </div>
      </div>
      <button
        className={styles.dismissButton}
        onClick={() => setDismissed(true)}
        aria-label="Dismiss emergency banner"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>
  );
}

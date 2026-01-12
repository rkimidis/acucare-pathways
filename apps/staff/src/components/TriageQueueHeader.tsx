'use client';

/**
 * Triage Queue Header Component
 *
 * Shows a banner when queue filter includes AMBER or RED cases
 * that require clinical review before booking.
 */

import { copy } from '@/copy';
import styles from './TriageQueueHeader.module.css';

interface TriageQueueHeaderProps {
  /** Current queue filter */
  filter: 'all' | 'red' | 'amber' | 'green' | 'blue';
  /** Number of cases requiring review */
  reviewRequiredCount?: number;
}

export default function TriageQueueHeader({
  filter,
  reviewRequiredCount = 0,
}: TriageQueueHeaderProps) {
  // Show banner when filter includes AMBER or RED
  const showBanner = filter === 'all' || filter === 'red' || filter === 'amber';

  if (!showBanner || reviewRequiredCount === 0) {
    return null;
  }

  return (
    <div id="triage-queue-banner" className={styles.banner} role="status">
      <div className={styles.icon}>
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
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      </div>
      <p className={styles.text}>{copy.staff.triageQueue.banner}</p>
      <span className={styles.count}>{reviewRequiredCount} pending</span>
    </div>
  );
}

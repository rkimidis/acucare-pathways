'use client';

/**
 * Check-In Escalated Component
 *
 * Displayed when a patient's check-in indicates deterioration
 * and requires clinical review.
 *
 * Precondition: checkIn.result == "escalated"
 */

import { useEffect } from 'react';
import { copy } from '@/copy';
import { trackEvent, EVENTS } from '@/lib/analytics';
import EmergencyBanner from './EmergencyBanner';
import styles from './CheckInEscalated.module.css';

interface CheckInEscalatedProps {
  /** Callback when user acknowledges */
  onAcknowledge?: () => void;
}

export default function CheckInEscalated({
  onAcknowledge,
}: CheckInEscalatedProps) {
  // Track escalated view on mount
  useEffect(() => {
    trackEvent(EVENTS.CHECKIN_ESCALATED_VIEWED);
  }, []);

  const handleAcknowledge = () => {
    trackEvent(EVENTS.ESCALATION_ACKNOWLEDGED, { type: 'checkin_escalated' });
    onAcknowledge?.();
  };

  return (
    <div className={styles.container}>
      {/* Amber emergency banner */}
      <EmergencyBanner variant="amber" dismissible={false} />

      <div className={styles.card}>
        {/* Header with icon */}
        <div className={styles.header}>
          <div className={styles.icon}>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="32"
              height="32"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
          </div>
          <h1 id="checkin-escalated-title" className={styles.title}>
            {copy.patient.checkIn.escalated.title}
          </h1>
        </div>

        {/* Main message */}
        <p className={styles.body}>
          {copy.patient.checkIn.escalated.body}
        </p>

        {/* Next steps */}
        <div className={styles.nextSteps}>
          <p>{copy.patient.checkIn.escalated.nextSteps}</p>
        </div>

        {/* [CLINICAL] Safety footer - always present */}
        <div className={styles.safetyFooter}>
          <span className={styles.safetyIcon}>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
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
          </span>
          <p>{copy.shared.safetyFooter.default}</p>
        </div>

        {/* Acknowledge button */}
        {onAcknowledge && (
          <button onClick={handleAcknowledge} className={styles.acknowledgeButton}>
            {copy.patient.checkIn.escalated.acknowledgeCta}
          </button>
        )}
      </div>
    </div>
  );
}

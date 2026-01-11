'use client';

/**
 * AMBER Escalation Component - Clinician Review Required
 *
 * This component displays when a clinician review is needed.
 * The copy is supportive but maintains clear safety messaging.
 */

import styles from './AmberEscalation.module.css';

interface AmberEscalationProps {
  /** Expected contact timeframe (default: 24-72 hours) */
  contactTimeframe?: string;
  /** Callback when user dismisses/acknowledges */
  onDismiss?: () => void;
}

export default function AmberEscalation({
  contactTimeframe = '24–72 hours',
  onDismiss,
}: AmberEscalationProps) {
  return (
    <div className={styles.container}>
      <div className={styles.card}>
        {/* Header */}
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
              <circle cx="12" cy="12" r="10" />
              <path d="M12 16v-4" />
              <path d="M12 8h.01" />
            </svg>
          </div>
          <h2 className={styles.title}>
            We want to make sure you&apos;re supported appropriately
          </h2>
        </div>

        {/* Main message */}
        <p className={styles.mainMessage}>
          Some of your responses indicate that a clinician should review your
          assessment before booking.
        </p>

        {/* Contact timeframe */}
        <div className={styles.timeframeBox}>
          <p>
            A member of our clinical team will contact you within{' '}
            <strong>{contactTimeframe}</strong>.
          </p>
        </div>

        {/* Safety line - always present */}
        <div className={styles.safetyLine}>
          <span className={styles.safetyIcon}>⚠️</span>
          <p>
            If you feel unsafe at any point, please contact <strong>999</strong>{' '}
            or attend <strong>A&amp;E</strong>.
          </p>
        </div>

        {/* Dismiss button */}
        {onDismiss && (
          <button onClick={onDismiss} className={styles.dismissButton}>
            I understand
          </button>
        )}
      </div>
    </div>
  );
}

'use client';

/**
 * Deterioration Escalation Component
 *
 * Displayed when a patient's check-in indicates things have worsened
 * while they're waiting for their appointment.
 */

import styles from './DeteriorationEscalation.module.css';

interface DeteriorationEscalationProps {
  /** Callback when user acknowledges */
  onAcknowledge?: () => void;
}

export default function DeteriorationEscalation({
  onAcknowledge,
}: DeteriorationEscalationProps) {
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
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
          </div>
          <h2 className={styles.title}>We&apos;d like to review your care plan</h2>
        </div>

        {/* Main message */}
        <p className={styles.mainMessage}>
          Your recent check-in suggests things may have become more difficult.
        </p>

        {/* What happens next */}
        <div className={styles.nextSteps}>
          <p>
            A clinician will review this and may contact you to discuss next
            steps.
          </p>
        </div>

        {/* Safety line - always present */}
        <div className={styles.safetyLine}>
          <span className={styles.safetyIcon}>⚠️</span>
          <p>
            If you feel unsafe, please contact <strong>999</strong> or attend{' '}
            <strong>A&amp;E</strong> immediately.
          </p>
        </div>

        {/* Acknowledge button */}
        {onAcknowledge && (
          <button onClick={onAcknowledge} className={styles.acknowledgeButton}>
            I understand
          </button>
        )}
      </div>
    </div>
  );
}

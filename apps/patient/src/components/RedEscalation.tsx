'use client';

/**
 * RED Escalation Component - Immediate Risk Detected
 *
 * CRITICAL: This component displays when immediate risk is detected.
 * The copy is intentionally clear, calm, and non-reassuring.
 * Do not personalise or soften beyond this language.
 */

import styles from './RedEscalation.module.css';

interface RedEscalationProps {
  /** Whether to show the optional trusted person message */
  showTrustedPersonOption?: boolean;
  /** Callback when user acknowledges (optional - may not be appropriate) */
  onAcknowledge?: () => void;
}

export default function RedEscalation({
  showTrustedPersonOption = false,
  onAcknowledge,
}: RedEscalationProps) {
  return (
    <div className={styles.container} role="alert" aria-live="assertive">
      <div className={styles.card}>
        {/* Header - Clear and direct */}
        <div className={styles.header}>
          <div className={styles.warningIcon}>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="48"
              height="48"
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
          <h1 className={styles.title}>We&apos;re concerned about your safety</h1>
        </div>

        {/* Primary instruction - Do not hedge */}
        <p className={styles.primaryInstruction}>
          Based on your responses, you may be at immediate risk.
        </p>

        {/* Clear action - Direct and prominent */}
        <div className={styles.actionBox}>
          <p className={styles.actionText}>
            Please contact <strong>999</strong> now or attend your nearest{' '}
            <strong>A&amp;E department</strong>.
          </p>
          <a href="tel:999" className={styles.emergencyButton}>
            Call 999 Now
          </a>
        </div>

        {/* Supportive but firm */}
        <p className={styles.firmStatement}>
          We cannot provide emergency support through this service.
        </p>

        {/* Optional trusted person message */}
        {showTrustedPersonOption && (
          <p className={styles.optionalMessage}>
            If you&apos;re able to do so safely, consider contacting a trusted person
            to be with you.
          </p>
        )}

        {/* Additional resources - secondary */}
        <div className={styles.additionalResources}>
          <p className={styles.resourcesLabel}>Other crisis lines:</p>
          <div className={styles.resourceLinks}>
            <a href="tel:116123" className={styles.resourceLink}>
              <span className={styles.resourceName}>Samaritans</span>
              <span className={styles.resourceNumber}>116 123</span>
            </a>
            <a href="tel:0800689999" className={styles.resourceLink}>
              <span className={styles.resourceName}>Crisis Text Line</span>
              <span className={styles.resourceNumber}>Text SHOUT to 85258</span>
            </a>
          </div>
        </div>

        {/* Acknowledge button - only if appropriate */}
        {onAcknowledge && (
          <button onClick={onAcknowledge} className={styles.acknowledgeButton}>
            I understand
          </button>
        )}
      </div>
    </div>
  );
}

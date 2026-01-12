'use client';

/**
 * RED Escalation Component - Immediate Risk Detected
 *
 * CRITICAL: This component displays when immediate risk is detected.
 * The copy is intentionally clear, calm, and non-reassuring.
 * Do not personalise or soften beyond this language.
 *
 * [CLINICAL] [LEGAL] - DO NOT MODIFY WITHOUT CLINICAL REVIEW
 */

import { useEffect } from 'react';
import { copy } from '@/copy';
import { trackEvent, EVENTS } from '@/lib/analytics';
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
  // Track RED escalation shown
  useEffect(() => {
    trackEvent(EVENTS.ESCALATION_RED_SHOWN);
  }, []);

  const handle999Click = () => {
    trackEvent(EVENTS.ESCALATION_RED_999_CLICKED);
  };

  const handleAcknowledge = () => {
    trackEvent(EVENTS.ESCALATION_ACKNOWLEDGED, { tier: 'RED' });
    onAcknowledge?.();
  };

  return (
    <div id="emergency-banner-red" className={styles.container} role="alert" aria-live="assertive">
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
          {/* [CLINICAL] [LEGAL] - DO NOT MODIFY */}
          <h1 id="escalation-red-title" className={styles.title}>
            {copy.patient.escalation.red.title}
          </h1>
        </div>

        {/* [CLINICAL] [LEGAL] Primary instruction - DO NOT MODIFY */}
        <p id="escalation-red-body" className={styles.primaryInstruction}>
          {copy.patient.escalation.red.body}
        </p>

        {/* [CLINICAL] [LEGAL] Clear action - DO NOT MODIFY */}
        <div className={styles.actionBox}>
          <p className={styles.actionText}>
            {copy.patient.escalation.red.primaryAction}
          </p>
          <a
            href="tel:999"
            className={styles.emergencyButton}
            onClick={handle999Click}
          >
            {copy.patient.escalation.red.callCta}
          </a>
        </div>

        {/* [CLINICAL] [LEGAL] Supportive but firm - DO NOT MODIFY */}
        <p className={styles.firmStatement}>
          {copy.patient.escalation.red.firmStatement}
        </p>

        {/* Optional trusted person message */}
        {showTrustedPersonOption && (
          <p className={styles.optionalMessage}>
            {copy.patient.escalation.red.trustedPerson}
          </p>
        )}

        {/* Additional resources - secondary */}
        <div className={styles.additionalResources}>
          <p className={styles.resourcesLabel}>{copy.patient.triage.red.crisisResources.title}</p>
          <div className={styles.resourceLinks}>
            <a href="tel:116123" className={styles.resourceLink}>
              <span className={styles.resourceName}>{copy.patient.triage.red.crisisResources.samaritans.name}</span>
              <span className={styles.resourceNumber}>{copy.patient.triage.red.crisisResources.samaritans.number}</span>
            </a>
            <a href="sms:85258?body=SHOUT" className={styles.resourceLink}>
              <span className={styles.resourceName}>{copy.patient.triage.red.crisisResources.shout.name}</span>
              <span className={styles.resourceNumber}>{copy.patient.triage.red.crisisResources.shout.action}</span>
            </a>
          </div>
        </div>

        {/* Acknowledge button - only if appropriate */}
        {onAcknowledge && (
          <button onClick={handleAcknowledge} className={styles.acknowledgeButton}>
            {copy.patient.escalation.red.acknowledgeCta}
          </button>
        )}
      </div>
    </div>
  );
}

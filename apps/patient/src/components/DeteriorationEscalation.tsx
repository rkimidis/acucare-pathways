'use client';

/**
 * Deterioration Escalation Component
 *
 * Displayed when a patient's check-in indicates things have worsened
 * while they're waiting for their appointment.
 */

import { useEffect } from 'react';
import { copy } from '@/copy';
import { trackEvent, EVENTS } from '@/lib/analytics';
import styles from './DeteriorationEscalation.module.css';

interface DeteriorationEscalationProps {
  /** Callback when user acknowledges */
  onAcknowledge?: () => void;
}

export default function DeteriorationEscalation({
  onAcknowledge,
}: DeteriorationEscalationProps) {
  // Track escalation shown
  useEffect(() => {
    trackEvent(EVENTS.CHECKIN_ESCALATION_SHOWN);
  }, []);

  const handleAcknowledge = () => {
    trackEvent(EVENTS.ESCALATION_ACKNOWLEDGED, { type: 'deterioration' });
    onAcknowledge?.();
  };

  return (
    <div id="deterioration-escalation" className={styles.container}>
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
          <h2 id="deterioration-title" className={styles.title}>
            {copy.patient.waitingList.deterioration.title}
          </h2>
        </div>

        {/* Main message */}
        <p id="deterioration-body" className={styles.mainMessage}>
          {copy.patient.waitingList.deterioration.body}
        </p>

        {/* What happens next */}
        <div className={styles.nextSteps}>
          <p>{copy.patient.waitingList.deterioration.nextSteps}</p>
        </div>

        {/* [CLINICAL] Safety line - always present - DO NOT MODIFY */}
        <div className={styles.safetyLine}>
          <span className={styles.safetyIcon}>⚠️</span>
          <p>{copy.shared.safetyFooter.default}</p>
        </div>

        {/* Acknowledge button */}
        {onAcknowledge && (
          <button onClick={handleAcknowledge} className={styles.acknowledgeButton}>
            {copy.patient.waitingList.deterioration.acknowledgeCta}
          </button>
        )}
      </div>
    </div>
  );
}

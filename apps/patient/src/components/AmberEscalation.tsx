'use client';

/**
 * AMBER Escalation Component - Clinician Review Required
 *
 * This component displays when a clinician review is needed.
 * The copy is supportive but maintains clear safety messaging.
 */

import { useEffect } from 'react';
import { copy, renderTemplate } from '@/copy';
import { trackEvent, EVENTS } from '@/lib/analytics';
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
  // Track AMBER escalation shown
  useEffect(() => {
    trackEvent(EVENTS.ESCALATION_AMBER_SHOWN);
  }, []);

  const handleDismiss = () => {
    trackEvent(EVENTS.ESCALATION_ACKNOWLEDGED, { tier: 'AMBER' });
    onDismiss?.();
  };

  return (
    <div id="emergency-banner-amber" className={styles.container}>
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
          <h2 id="escalation-amber-title" className={styles.title}>
            {copy.patient.escalation.amber.title}
          </h2>
        </div>

        {/* Main message */}
        <p id="escalation-amber-body" className={styles.mainMessage}>
          {copy.patient.escalation.amber.body}
        </p>

        {/* Contact timeframe */}
        <div className={styles.timeframeBox}>
          <p>
            {renderTemplate(copy.patient.escalation.amber.contactTimeframe, {
              timeframe: contactTimeframe,
            })}
          </p>
        </div>

        {/* [CLINICAL] Safety line - always present - DO NOT MODIFY */}
        <div className={styles.safetyLine}>
          <span className={styles.safetyIcon}>⚠️</span>
          <p>{copy.shared.emergencyBanner.amber.body}</p>
        </div>

        {/* Dismiss button */}
        {onDismiss && (
          <button onClick={handleDismiss} className={styles.dismissButton}>
            {copy.patient.escalation.amber.acknowledgeCta}
          </button>
        )}
      </div>
    </div>
  );
}

'use client';

/**
 * Immediate Safety Action Component - RED Tier
 *
 * Displayed when a patient's triage tier is RED (immediate risk).
 * Provides clear, actionable safety guidance.
 *
 * [CLINICAL] [LEGAL] - DO NOT MODIFY WITHOUT CLINICAL REVIEW
 */

import { useEffect } from 'react';
import { copy } from '@/copy';
import { trackEvent, EVENTS } from '@/lib/analytics';
import styles from './ImmediateSafetyAction.module.css';

interface ImmediateSafetyActionProps {
  /** Whether to show the optional support message */
  showOptionalSupport?: boolean;
  /** Whether to show the Find A&E button (requires location service) */
  showFindAeButton?: boolean;
  /** Callback when user acknowledges */
  onAcknowledge?: () => void;
}

export default function ImmediateSafetyAction({
  showOptionalSupport = true,
  showFindAeButton = true,
  onAcknowledge,
}: ImmediateSafetyActionProps) {
  // Track RED safety page viewed
  useEffect(() => {
    trackEvent(EVENTS.RED_SAFETY_PAGE_VIEWED);
  }, []);

  const handle999Click = () => {
    trackEvent(EVENTS.RED_SAFETY_999_CLICKED);
  };

  const handleAeClick = () => {
    trackEvent(EVENTS.RED_SAFETY_AE_CLICKED);
  };

  return (
    <div className={styles.container} role="alert" aria-live="assertive">
      <div className={styles.card}>
        {/* Header - Clear and direct */}
        <div className={styles.header}>
          <div className={styles.warningIcon}>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="56"
              height="56"
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
          <h1 id="red-safety-title" className={styles.title}>
            {copy.patient.red.title}
          </h1>
        </div>

        {/* [CLINICAL] [LEGAL] Primary instruction - DO NOT MODIFY */}
        <p id="red-safety-primary" className={styles.primaryInstruction}>
          {copy.patient.red.primaryInstruction}
        </p>

        {/* Prominent action buttons */}
        <div className={styles.actionButtons}>
          <a
            id="call-999-button"
            href="tel:999"
            className={styles.call999Button}
            onClick={handle999Click}
          >
            <span className={styles.buttonIcon}>📞</span>
            {copy.patient.red.callCta}
          </a>

          {showFindAeButton && (
            <a
              id="find-ae-button"
              href={copy.patient.red.aeGuidanceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.findAeButton}
              onClick={handleAeClick}
            >
              <span className={styles.buttonIcon}>🏥</span>
              {copy.patient.red.findAeCta}
            </a>
          )}
        </div>

        {/* [CLINICAL] [LEGAL] Firm boundary statement - DO NOT MODIFY */}
        <p id="red-safety-boundary" className={styles.boundaryStatement}>
          {copy.patient.red.boundary}
        </p>

        {/* Optional support message */}
        {showOptionalSupport && (
          <p className={styles.optionalSupport}>
            {copy.patient.red.optionalSupport}
          </p>
        )}

        {/* Additional crisis resources */}
        <div className={styles.crisisResources}>
          <p className={styles.resourcesLabel}>{copy.patient.triage.red.crisisResources.title}</p>
          <div className={styles.resourceLinks}>
            <a href="tel:116123" className={styles.resourceLink}>
              <span className={styles.resourceName}>
                {copy.patient.triage.red.crisisResources.samaritans.name}
              </span>
              <span className={styles.resourceNumber}>
                {copy.patient.triage.red.crisisResources.samaritans.number}
              </span>
            </a>
            <a href="sms:85258?body=SHOUT" className={styles.resourceLink}>
              <span className={styles.resourceName}>
                {copy.patient.triage.red.crisisResources.shout.name}
              </span>
              <span className={styles.resourceNumber}>
                {copy.patient.triage.red.crisisResources.shout.action}
              </span>
            </a>
          </div>
        </div>

        {/* Emergency banner - always visible */}
        <div id="emergency-banner-red" className={styles.emergencyBanner}>
          <span className={styles.emergencyIcon}>⚠️</span>
          <p>{copy.shared.emergencyBanner.red.body}</p>
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

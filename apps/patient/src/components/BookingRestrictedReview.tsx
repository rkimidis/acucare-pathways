'use client';

/**
 * Booking Restricted Review Component - AMBER Tier
 *
 * Displayed when a patient's triage tier is AMBER.
 * Booking is restricted pending clinical review.
 */

import { useEffect } from 'react';
import { copy } from '@/copy';
import { trackEvent, EVENTS } from '@/lib/analytics';
import EmergencyBanner from './EmergencyBanner';
import styles from './BookingRestrictedReview.module.css';

interface BookingRestrictedReviewProps {
  /** Callback when user acknowledges */
  onAcknowledge?: () => void;
}

export default function BookingRestrictedReview({
  onAcknowledge,
}: BookingRestrictedReviewProps) {
  // Track review required page viewed
  useEffect(() => {
    trackEvent(EVENTS.REVIEW_REQUIRED_VIEWED);
  }, []);

  return (
    <div className={styles.container}>
      {/* AMBER emergency banner */}
      <EmergencyBanner variant="amber" dismissible={false} />

      <div className={styles.card}>
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.icon}>
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
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          </div>
          <h1 id="review-required-title" className={styles.title}>
            {copy.patient.reviewRequired.title}
          </h1>
        </div>

        {/* Main message */}
        <p className={styles.body}>
          {copy.patient.reviewRequired.body}
        </p>

        {/* Reassurance */}
        <div className={styles.reassurance}>
          <p>{copy.patient.reviewRequired.reassurance}</p>
        </div>

        {/* What happens next */}
        <div id="review-required-next-steps" className={styles.nextSteps}>
          <h2 className={styles.nextStepsTitle}>{copy.patient.reviewRequired.nextStepsTitle}</h2>
          <ul className={styles.nextStepsList}>
            {copy.patient.reviewRequired.nextStepsList.map((step, index) => (
              <li key={index}>{step}</li>
            ))}
          </ul>
        </div>

        {/* Timeline / Safety notice */}
        <div className={styles.timeline}>
          <span className={styles.timelineIcon}>
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
          <p>{copy.patient.reviewRequired.timeline}</p>
        </div>

        {/* Contact preferences */}
        <p className={styles.contactPreferences}>
          {copy.patient.reviewRequired.contactPreferences}
        </p>

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

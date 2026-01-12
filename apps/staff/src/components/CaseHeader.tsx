'use client';

/**
 * Case Header Component
 *
 * One-glance summary showing tier badge, pathway, SLA countdown,
 * and review-required indicator.
 */

import { copy } from '@/copy';
import styles from './CaseHeader.module.css';

type Tier = 'red' | 'amber' | 'green' | 'blue' | null;

interface CaseHeaderProps {
  /** Case tier (RED, AMBER, GREEN, BLUE) */
  tier: Tier;
  /** Assigned pathway */
  pathway: string | null;
  /** SLA remaining in minutes (negative = overdue) */
  slaRemainingMinutes: number | null;
  /** Whether SLA is breached */
  slaBreached?: boolean;
  /** Whether clinician review is required */
  reviewRequired?: boolean;
  /** Rules that triggered triage outcome */
  rulesFired?: string[];
}

export default function CaseHeader({
  tier,
  pathway,
  slaRemainingMinutes,
  slaBreached = false,
  reviewRequired = false,
  rulesFired = [],
}: CaseHeaderProps) {
  const formatSlaTime = (minutes: number | null): string => {
    if (minutes === null) return '--';
    if (minutes < 0) return 'OVERDUE';

    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;

    if (hours > 0) {
      return `${hours}h ${mins}m`;
    }
    return `${mins}m`;
  };

  const getTierClass = (): string => {
    switch (tier) {
      case 'red':
        return styles.tierRed;
      case 'amber':
        return styles.tierAmber;
      case 'green':
        return styles.tierGreen;
      case 'blue':
        return styles.tierBlue;
      default:
        return styles.tierPending;
    }
  };

  const getSlaClass = (): string => {
    if (slaBreached || (slaRemainingMinutes !== null && slaRemainingMinutes < 0)) {
      return styles.slaBreached;
    }
    if (slaRemainingMinutes !== null && slaRemainingMinutes < 30) {
      return styles.slaCritical;
    }
    if (slaRemainingMinutes !== null && slaRemainingMinutes < 60) {
      return styles.slaWarning;
    }
    return styles.slaNormal;
  };

  return (
    <div className={styles.header}>
      {/* Tier badge */}
      <div className={styles.field}>
        <span className={styles.label}>{copy.staff.case.tier}</span>
        <span id="case-tier-badge" className={`${styles.tierBadge} ${getTierClass()}`}>
          {tier?.toUpperCase() || 'PENDING'}
        </span>
      </div>

      {/* Pathway */}
      <div className={styles.field}>
        <span className={styles.label}>{copy.staff.case.pathway}</span>
        <span id="case-pathway-label" className={styles.pathwayLabel}>
          {pathway || '--'}
        </span>
      </div>

      {/* SLA countdown */}
      <div className={styles.field}>
        <span className={styles.label}>{copy.staff.case.sla}</span>
        <span id="case-sla-countdown" className={`${styles.slaCountdown} ${getSlaClass()}`}>
          {formatSlaTime(slaRemainingMinutes)}
        </span>
      </div>

      {/* Review required indicator */}
      {reviewRequired && (
        <div className={styles.reviewRequired}>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
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
          <span>{copy.staff.case.reviewRequired}</span>
        </div>
      )}

      {/* Rules fired */}
      {rulesFired.length > 0 && (
        <div id="case-rules-fired" className={styles.rulesFired}>
          <span className={styles.rulesLabel}>{copy.staff.case.rulesFiredLabel}:</span>
          <div className={styles.rulesList}>
            {rulesFired.map((rule, index) => (
              <span key={index} className={styles.ruleTag}>
                {rule}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

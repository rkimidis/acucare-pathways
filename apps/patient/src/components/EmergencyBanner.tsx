'use client';

/**
 * Emergency Banner Component
 *
 * Displays safety information based on context/variant.
 * [CLINICAL] [LEGAL] - Safety copy should not be modified without clinical review.
 */

import { useEffect, useState } from 'react';
import { copy } from '@/copy';
import { trackEvent, EVENTS } from '@/lib/analytics';
import styles from './EmergencyBanner.module.css';

interface SafetyBanner {
  enabled: boolean;
  text: string;
  consent_version: string;
}

interface EmergencyBannerProps {
  /** Banner variant: 'default' | 'amber' | 'red' */
  variant?: 'default' | 'amber' | 'red';
  /** Whether the banner can be dismissed */
  dismissible?: boolean;
}

export default function EmergencyBanner({
  variant = 'default',
  dismissible = true,
}: EmergencyBannerProps) {
  const [banner, setBanner] = useState<SafetyBanner | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    // Track banner shown
    trackEvent(EVENTS.EMERGENCY_BANNER_SHOWN, { variant });

    // Fetch safety banner from API for default variant
    if (variant === 'default') {
      fetch('/api/v1/intake/safety-banner')
        .then((res) => res.json())
        .then((data) => setBanner(data))
        .catch((err) => {
          console.error('Failed to fetch safety banner:', err);
          // Show fallback banner if API fails
          setBanner({
            enabled: true,
            text: copy.shared.emergencyBanner.default.body,
            consent_version: '1.0',
          });
        });
    } else {
      // For amber/red variants, use copy directly
      setBanner({
        enabled: true,
        text: copy.shared.emergencyBanner[variant].body,
        consent_version: '1.0',
      });
    }
  }, [variant]);

  const handleDismiss = () => {
    trackEvent(EVENTS.EMERGENCY_BANNER_DISMISSED, { variant });
    setDismissed(true);
  };

  const handle999Click = () => {
    trackEvent(EVENTS.EMERGENCY_BANNER_999_CLICKED, { variant });
  };

  if (!banner?.enabled || dismissed) {
    return null;
  }

  // Get variant-specific copy
  const bannerCopy = copy.shared.emergencyBanner[variant];

  // Determine banner styling based on variant
  const variantClass = variant === 'red'
    ? styles.bannerRed
    : variant === 'amber'
    ? styles.bannerAmber
    : styles.banner;

  const bannerId = `emergency-banner-${variant}`;

  return (
    <div id={bannerId} className={variantClass} role="alert" aria-live="polite">
      <div className={styles.icon}>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
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
      <div className={styles.content}>
        {/* [CLINICAL] [LEGAL] - DO NOT MODIFY */}
        <strong>{bannerCopy.title}</strong>
        <p>{banner.text}</p>
        <div className={styles.contacts}>
          <a href="tel:999" className={styles.emergencyLink} onClick={handle999Click}>
            Call 999
          </a>
          <a href="tel:116123" className={styles.helplineLink}>
            Samaritans: 116 123
          </a>
        </div>
      </div>
      {dismissible && (
        <button
          className={styles.dismissButton}
          onClick={handleDismiss}
          aria-label="Dismiss emergency banner"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      )}
    </div>
  );
}

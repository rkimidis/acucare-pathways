'use client';

import { useState } from 'react';
import styles from './ConsentStep.module.css';

interface ConsentStepProps {
  consentVersion: string;
  onConsent: (consent: {
    consent_items: Record<string, boolean>;
    channels: Record<string, boolean>;
  }) => void;
  disabled?: boolean;
}

export default function ConsentStep({
  consentVersion,
  onConsent,
  disabled = false,
}: ConsentStepProps) {
  const [consentItems, setConsentItems] = useState<Record<string, boolean>>({
    data_processing: false,
    privacy_policy: false,
    communication_email: false,
    communication_sms: false,
  });

  const [error, setError] = useState<string | null>(null);

  const handleChange = (key: string, value: boolean) => {
    setConsentItems((prev) => ({
      ...prev,
      [key]: value,
    }));
    setError(null);
  };

  const handleSubmit = () => {
    // Validate required consents
    if (!consentItems.data_processing || !consentItems.privacy_policy) {
      setError(
        'You must agree to data processing and the privacy policy to continue.'
      );
      return;
    }

    onConsent({
      consent_items: consentItems,
      channels: {
        email: consentItems.communication_email,
        sms: consentItems.communication_sms,
      },
    });
  };

  const allRequiredChecked =
    consentItems.data_processing && consentItems.privacy_policy;

  return (
    <div className={styles.consentStep}>
      <h2 className={styles.title}>Consent and Privacy</h2>
      <p className={styles.version}>Consent Version: {consentVersion}</p>

      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>Required Consents</h3>

        <label className={`${styles.consentItem} ${styles.required}`}>
          <input
            type="checkbox"
            checked={consentItems.data_processing}
            onChange={(e) => handleChange('data_processing', e.target.checked)}
            disabled={disabled}
          />
          <div className={styles.consentContent}>
            <span className={styles.consentLabel}>
              Data Processing Agreement
              <span className={styles.requiredMark}>*</span>
            </span>
            <p className={styles.consentDescription}>
              I consent to AcuCare Pathways processing my personal and health
              data for the purpose of providing psychiatric care services. My
              data will be handled in accordance with UK GDPR and stored
              securely.
            </p>
          </div>
        </label>

        <label className={`${styles.consentItem} ${styles.required}`}>
          <input
            type="checkbox"
            checked={consentItems.privacy_policy}
            onChange={(e) => handleChange('privacy_policy', e.target.checked)}
            disabled={disabled}
          />
          <div className={styles.consentContent}>
            <span className={styles.consentLabel}>
              Privacy Policy
              <span className={styles.requiredMark}>*</span>
            </span>
            <p className={styles.consentDescription}>
              I have read and understood the{' '}
              <a href="/privacy" target="_blank" rel="noopener noreferrer">
                Privacy Policy
              </a>
              . I understand how my data will be used, stored, and protected.
            </p>
          </div>
        </label>
      </div>

      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>Communication Preferences</h3>
        <p className={styles.sectionDescription}>
          These are optional. You can update your preferences at any time.
        </p>

        <label className={styles.consentItem}>
          <input
            type="checkbox"
            checked={consentItems.communication_email}
            onChange={(e) =>
              handleChange('communication_email', e.target.checked)
            }
            disabled={disabled}
          />
          <div className={styles.consentContent}>
            <span className={styles.consentLabel}>Email Communications</span>
            <p className={styles.consentDescription}>
              I agree to receive appointment reminders and health information
              via email.
            </p>
          </div>
        </label>

        <label className={styles.consentItem}>
          <input
            type="checkbox"
            checked={consentItems.communication_sms}
            onChange={(e) => handleChange('communication_sms', e.target.checked)}
            disabled={disabled}
          />
          <div className={styles.consentContent}>
            <span className={styles.consentLabel}>SMS Communications</span>
            <p className={styles.consentDescription}>
              I agree to receive appointment reminders via SMS text message.
            </p>
          </div>
        </label>
      </div>

      {error && <p className={styles.error}>{error}</p>}

      <button
        className={styles.continueButton}
        onClick={handleSubmit}
        disabled={disabled || !allRequiredChecked}
      >
        I Agree - Continue
      </button>

      <p className={styles.note}>
        By clicking &quot;I Agree - Continue&quot;, you confirm that you have
        read and understood the above consents and agree to them.
      </p>
    </div>
  );
}

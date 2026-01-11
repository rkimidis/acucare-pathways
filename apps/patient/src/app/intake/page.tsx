'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import EmergencyBanner from '@/components/EmergencyBanner';
import QuestionnaireRenderer from '@/components/QuestionnaireRenderer';
import ConsentStep from '@/components/ConsentStep';
import styles from './intake.module.css';

interface QuestionnaireDefinition {
  id: string;
  name: string;
  version: string;
  schema: {
    title?: string;
    description?: string;
    sections?: { id: string; title: string; description?: string }[];
    fields: Array<{
      id: string;
      type: string;
      label: string;
      description?: string;
      required?: boolean;
      options?: { value: string; label: string }[];
      section?: string;
    }>;
  };
}

interface ConsentStatus {
  has_consented: boolean;
  consent_version: string | null;
  current_version: string;
  needs_reconsent: boolean;
}

type WizardStep = 'consent' | 'questionnaire' | 'risk-warning' | 'confirmation';

export default function IntakePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState<WizardStep>('consent');
  const [questionnaire, setQuestionnaire] =
    useState<QuestionnaireDefinition | null>(null);
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [consentStatus, setConsentStatus] = useState<ConsentStatus | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [draftSaveStatus, setDraftSaveStatus] = useState<
    'saved' | 'saving' | 'error' | null
  >(null);

  // Load consent status and questionnaire on mount
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/auth/login');
      return;
    }

    const fetchData = async () => {
      try {
        // Fetch consent status
        const consentRes = await fetch('/api/v1/consent/status', {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (consentRes.ok) {
          const consent = await consentRes.json();
          setConsentStatus(consent);

          // If already consented, skip to questionnaire
          if (consent.has_consented && !consent.needs_reconsent) {
            setStep('questionnaire');
          }
        }

        // Fetch questionnaire
        const qRes = await fetch('/api/v1/intake/questionnaire/active', {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (qRes.ok) {
          const q = await qRes.json();
          setQuestionnaire(q);
        }

        // Try to load draft
        const draftRes = await fetch('/api/v1/intake/draft', {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (draftRes.ok) {
          const draft = await draftRes.json();
          if (draft && draft.answers) {
            setAnswers(draft.answers);
          }
        }
      } catch (err) {
        console.error('Failed to load intake data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [router]);

  // Auto-save draft when answers change
  const saveDraft = useCallback(async () => {
    const token = localStorage.getItem('access_token');
    if (!token || Object.keys(answers).length === 0) return;

    setDraftSaveStatus('saving');
    try {
      const res = await fetch('/api/v1/intake/draft', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ answers }),
      });

      if (res.ok) {
        setDraftSaveStatus('saved');
      } else {
        setDraftSaveStatus('error');
      }
    } catch {
      setDraftSaveStatus('error');
    }
  }, [answers]);

  // Debounced auto-save
  useEffect(() => {
    if (step !== 'questionnaire' || Object.keys(answers).length === 0) return;

    const timeout = setTimeout(() => {
      saveDraft();
    }, 2000);

    return () => clearTimeout(timeout);
  }, [answers, step, saveDraft]);

  const handleConsentSubmit = async (consent: {
    consent_items: Record<string, boolean>;
    channels: Record<string, boolean>;
  }) => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    setSubmitting(true);
    try {
      const res = await fetch('/api/v1/consent/capture', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(consent),
      });

      if (res.ok) {
        setStep('questionnaire');
      } else {
        const data = await res.json();
        alert(data.detail?.message || 'Failed to save consent');
      }
    } catch (err) {
      console.error('Consent error:', err);
      alert('Failed to save consent. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const validateAnswers = (): boolean => {
    if (!questionnaire) return false;

    const newErrors: Record<string, string> = {};
    const fields = questionnaire.schema.fields || [];

    fields.forEach((field) => {
      if (field.required) {
        const value = answers[field.id];
        if (value === undefined || value === null || value === '') {
          newErrors[field.id] = 'This field is required';
        } else if (Array.isArray(value) && value.length === 0) {
          newErrors[field.id] = 'Please select at least one option';
        }
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleQuestionnaireSubmit = () => {
    if (!validateAnswers()) {
      // Scroll to first error
      const firstErrorField = Object.keys(errors)[0];
      const element = document.getElementById(firstErrorField);
      element?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }

    // Check for risk indicators
    const riskFields = ['suicidal_thoughts', 'self_harm', 'harm_to_others'];
    const hasRiskIndicators = riskFields.some(
      (field) => answers[field] === true || answers[field] === 'yes'
    );

    if (hasRiskIndicators) {
      setStep('risk-warning');
    } else {
      setStep('confirmation');
    }
  };

  const handleFinalSubmit = async () => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    setSubmitting(true);
    try {
      const res = await fetch('/api/v1/intake/submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ answers }),
      });

      if (res.ok) {
        router.push('/dashboard?intake=complete');
      } else {
        const data = await res.json();
        if (data.detail?.errors) {
          const newErrors: Record<string, string> = {};
          data.detail.errors.forEach((err: string) => {
            const match = err.match(/field '([^']+)'/);
            if (match) {
              newErrors[match[1]] = err;
            }
          });
          setErrors(newErrors);
          setStep('questionnaire');
        } else {
          alert(data.detail?.message || 'Submission failed');
        }
      }
    } catch (err) {
      console.error('Submit error:', err);
      alert('Failed to submit. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <main className={styles.main}>
        <div className={styles.loading}>Loading...</div>
      </main>
    );
  }

  return (
    <main className={styles.main}>
      <EmergencyBanner />

      <div className={styles.container}>
        {/* Progress indicator */}
        <div className={styles.progress}>
          <div
            className={`${styles.progressStep} ${
              step === 'consent' ? styles.active : styles.completed
            }`}
          >
            1. Consent
          </div>
          <div
            className={`${styles.progressStep} ${
              step === 'questionnaire'
                ? styles.active
                : ['risk-warning', 'confirmation'].includes(step)
                ? styles.completed
                : ''
            }`}
          >
            2. Questionnaire
          </div>
          <div
            className={`${styles.progressStep} ${
              step === 'confirmation' ? styles.active : ''
            }`}
          >
            3. Complete
          </div>
        </div>

        {/* Step content */}
        <div className={styles.content}>
          {step === 'consent' && consentStatus && (
            <ConsentStep
              consentVersion={consentStatus.current_version}
              onConsent={handleConsentSubmit}
              disabled={submitting}
            />
          )}

          {step === 'questionnaire' && questionnaire && (
            <>
              {draftSaveStatus && (
                <div className={styles.draftStatus}>
                  {draftSaveStatus === 'saving' && 'Saving draft...'}
                  {draftSaveStatus === 'saved' && 'Draft saved'}
                  {draftSaveStatus === 'error' && 'Failed to save draft'}
                </div>
              )}

              <QuestionnaireRenderer
                schema={questionnaire.schema}
                answers={answers}
                onChange={setAnswers}
                errors={errors}
                disabled={submitting}
              />

              <div className={styles.actions}>
                <button
                  className={styles.saveButton}
                  onClick={saveDraft}
                  disabled={submitting}
                >
                  Save Draft
                </button>
                <button
                  className={styles.submitButton}
                  onClick={handleQuestionnaireSubmit}
                  disabled={submitting}
                >
                  Continue
                </button>
              </div>
            </>
          )}

          {step === 'risk-warning' && (
            <div className={styles.riskWarning}>
              <EmergencyBanner />

              <h2>Important Safety Information</h2>
              <p>
                Based on your responses, we want to make sure you have access to
                immediate support if needed.
              </p>

              <div className={styles.safetyInfo}>
                <h3>If you are in immediate danger:</h3>
                <ul>
                  <li>
                    <strong>Call 999</strong> for emergency services
                  </li>
                  <li>
                    Go to your <strong>nearest A&E department</strong>
                  </li>
                </ul>

                <h3>For non-emergency mental health support:</h3>
                <ul>
                  <li>
                    <strong>Samaritans:</strong> 116 123 (free, 24/7)
                  </li>
                  <li>
                    <strong>Crisis Text Line:</strong> Text &quot;SHOUT&quot; to
                    85258
                  </li>
                  <li>
                    <strong>NHS 111:</strong> Option 2 for mental health crisis
                  </li>
                </ul>
              </div>

              <p className={styles.confirmText}>
                Please confirm you have read this information before continuing.
              </p>

              <div className={styles.actions}>
                <button
                  className={styles.backButton}
                  onClick={() => setStep('questionnaire')}
                >
                  Go Back
                </button>
                <button
                  className={styles.submitButton}
                  onClick={() => setStep('confirmation')}
                >
                  I Understand - Continue
                </button>
              </div>
            </div>
          )}

          {step === 'confirmation' && (
            <div className={styles.confirmation}>
              <h2>Review Your Submission</h2>
              <p>
                Please review your responses before submitting. Once submitted,
                a member of our clinical team will review your information.
              </p>

              <div className={styles.summaryNote}>
                <strong>What happens next:</strong>
                <ol>
                  <li>Your responses will be reviewed by our clinical team</li>
                  <li>
                    You will receive a triage tier assignment (usually within 24
                    hours)
                  </li>
                  <li>
                    We will contact you with next steps based on your tier
                  </li>
                </ol>
              </div>

              <EmergencyBanner />

              <div className={styles.actions}>
                <button
                  className={styles.backButton}
                  onClick={() => setStep('questionnaire')}
                >
                  Go Back & Edit
                </button>
                <button
                  className={styles.submitButton}
                  onClick={handleFinalSubmit}
                  disabled={submitting}
                >
                  {submitting ? 'Submitting...' : 'Submit Questionnaire'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import EmergencyBanner from '@/components/EmergencyBanner';
import QuestionnaireRenderer from '@/components/QuestionnaireRenderer';
import ConsentStep from '@/components/ConsentStep';
import { copy, renderTemplate } from '@/copy';
import { trackEvent, EVENTS } from '@/lib/analytics';
import styles from './intake.module.css';

type FieldType = 'text' | 'textarea' | 'number' | 'boolean' | 'select' | 'multiselect' | 'date';

interface QuestionnaireField {
  id: string;
  type: FieldType;
  label: string;
  description?: string;
  required?: boolean;
  options?: { value: string; label: string }[];
  section?: string;
}

interface QuestionnaireDefinition {
  id: string;
  name: string;
  version: string;
  schema: {
    title?: string;
    description?: string;
    sections?: { id: string; title: string; description?: string }[];
    fields: QuestionnaireField[];
  };
}

interface ConsentStatus {
  has_consented: boolean;
  consent_version: string | null;
  current_version: string;
  needs_reconsent: boolean;
}

// 6-step wizard for clear progress tracking
type WizardStep =
  | 'landing'
  | 'consent'
  | 'background'
  | 'symptoms'
  | 'safety'
  | 'review'
  | 'complete';

const STEP_LABELS: Record<WizardStep, string> = {
  landing: 'Welcome',
  consent: 'Consent',
  background: 'Background',
  symptoms: 'Current symptoms',
  safety: 'Safety',
  review: 'Review',
  complete: 'Complete',
};

// Map sections to wizard steps (adjust based on your questionnaire schema)
const SECTION_TO_STEP: Record<string, WizardStep> = {
  demographics: 'background',
  background: 'background',
  presenting: 'symptoms',
  symptoms: 'symptoms',
  phq9: 'symptoms',
  gad7: 'symptoms',
  safety: 'safety',
  risk: 'safety',
  auditc: 'background',
};

export default function IntakePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState<WizardStep>('landing');
  const [questionnaire, setQuestionnaire] =
    useState<QuestionnaireDefinition | null>(null);
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [consentStatus, setConsentStatus] = useState<ConsentStatus | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [draftSaveStatus, setDraftSaveStatus] = useState<
    'saved' | 'saving' | 'error' | null
  >(null);
  const [currentQuestionnaireStep, setCurrentQuestionnaireStep] = useState(0);

  // Define the main steps for progress display (6 visible steps)
  const progressSteps: WizardStep[] = [
    'consent',
    'background',
    'symptoms',
    'safety',
    'review',
    'complete',
  ];

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
    const questionnaireSteps: WizardStep[] = ['background', 'symptoms', 'safety'];
    if (!questionnaireSteps.includes(step) || Object.keys(answers).length === 0)
      return;

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
        setStep('background');
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

  const validateCurrentSection = (): boolean => {
    if (!questionnaire) return false;

    const newErrors: Record<string, string> = {};
    const fields = questionnaire.schema.fields || [];

    // Get fields for current step
    const currentFields = fields.filter((field) => {
      const fieldStep = SECTION_TO_STEP[field.section || ''] || 'background';
      return fieldStep === step;
    });

    currentFields.forEach((field) => {
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

  const validateAllAnswers = (): boolean => {
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

  const handleNextStep = () => {
    if (!validateCurrentSection()) {
      const firstErrorField = Object.keys(errors)[0];
      const element = document.getElementById(firstErrorField);
      element?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }

    // Move to next step
    if (step === 'background') {
      setStep('symptoms');
    } else if (step === 'symptoms') {
      setStep('safety');
    } else if (step === 'safety') {
      setStep('review');
    }

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handlePreviousStep = () => {
    if (step === 'symptoms') {
      setStep('background');
    } else if (step === 'safety') {
      setStep('symptoms');
    } else if (step === 'review') {
      setStep('safety');
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleFinalSubmit = async () => {
    if (!validateAllAnswers()) {
      // Find which step has the first error
      const firstErrorField = Object.keys(errors)[0];
      const field = questionnaire?.schema.fields.find(
        (f) => f.id === firstErrorField
      );
      if (field) {
        const fieldStep = SECTION_TO_STEP[field.section || ''] || 'background';
        setStep(fieldStep);
        setTimeout(() => {
          const element = document.getElementById(firstErrorField);
          element?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 100);
      }
      return;
    }

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
        setStep('complete');
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
          setStep('background');
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

  // Get current step number (1-indexed for display)
  const getCurrentStepNumber = (): number => {
    const index = progressSteps.indexOf(step);
    return index >= 0 ? index + 1 : 1;
  };

  // Get fields for a specific wizard step
  const getFieldsForStep = (wizardStep: WizardStep) => {
    if (!questionnaire) return [];
    return questionnaire.schema.fields.filter((field) => {
      const fieldStep = SECTION_TO_STEP[field.section || ''] || 'background';
      return fieldStep === wizardStep;
    });
  };

  // Track page views and step changes
  useEffect(() => {
    if (step === 'landing') {
      trackEvent(EVENTS.INTAKE_LANDING_VIEWED);
    } else if (step === 'safety') {
      trackEvent(EVENTS.INTAKE_SAFETY_BLOCK_SHOWN);
      trackEvent(EVENTS.INTAKE_STEP_VIEWED, { step: 'safety', label: STEP_LABELS.safety });
    } else if (step === 'complete') {
      trackEvent(EVENTS.INTAKE_SUBMITTED);
    } else {
      // Remaining steps: consent, background, symptoms, review
      trackEvent(EVENTS.INTAKE_STEP_VIEWED, { step, label: STEP_LABELS[step] });
    }
  }, [step]);

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
        {/* Landing Page */}
        {step === 'landing' && (
          <div className={styles.landing}>
            <div className={styles.landingContent}>
              <h1 id="intake-landing-title" className={styles.landingHeader}>
                {copy.patient.intake.landing.title}
              </h1>
              <p id="intake-landing-subtitle" className={styles.landingSubheader}>
                {copy.patient.intake.landing.subtitle}
              </p>

              <div id="intake-landing-time" className={styles.timeIndicator}>
                <span className={styles.timeIcon}>⏱</span>
                {renderTemplate(copy.patient.intake.landing.timeEstimate, { minutes: '8–10' })}
              </div>

              <div className={styles.reassuranceBox}>
                <p>{copy.patient.intake.landing.reassurance}</p>
                <p>{copy.patient.intake.landing.privacyNote}</p>
              </div>

              {/* [CLINICAL] [LEGAL] Emergency notice - DO NOT MODIFY */}
              <div id="emergency-banner-default" className={styles.emergencyNotice}>
                <span className={styles.warningIcon}>⚠️</span>
                <div>
                  <strong>{copy.shared.emergencyBanner.default.title}</strong>
                  <p>{copy.shared.emergencyBanner.default.body}</p>
                </div>
              </div>

              <button
                id="intake-start-button"
                className={styles.startButton}
                onClick={() => {
                  trackEvent(EVENTS.INTAKE_STARTED_CLICKED);
                  if (
                    consentStatus?.has_consented &&
                    !consentStatus?.needs_reconsent
                  ) {
                    setStep('background');
                  } else {
                    setStep('consent');
                  }
                }}
              >
                {copy.patient.intake.landing.cta}
              </button>
            </div>
          </div>
        )}

        {/* Progress indicator (persistent at top) */}
        {step !== 'landing' && step !== 'complete' && (
          <div className={styles.progressContainer}>
            <div className={styles.progressHeader}>
              <div className={styles.progressHeaderMain}>
                <span id="intake-progress-label" className={styles.stepIndicator}>
                  {renderTemplate(copy.patient.intake.progress.stepLabel, {
                    current: getCurrentStepNumber(),
                    total: progressSteps.length,
                    label: STEP_LABELS[step],
                  })}
                </span>
              </div>
              <div className={styles.progressTooltipWrapper}>
                <span
                  className={styles.infoIcon}
                  title={copy.patient.intake.progress.tooltip}
                >
                  ⓘ
                </span>
                <div id="intake-progress-tooltip" className={styles.progressTooltip}>
                  {copy.patient.intake.progress.tooltip}
                </div>
              </div>
            </div>
            <div className={styles.progressBar}>
              <div
                className={styles.progressFill}
                style={{
                  width: `${(getCurrentStepNumber() / progressSteps.length) * 100}%`,
                }}
              />
            </div>
          </div>
        )}

        {/* Step content */}
        <div className={step === 'landing' ? '' : styles.content}>
          {step === 'consent' && consentStatus && (
            <ConsentStep
              consentVersion={consentStatus.current_version}
              onConsent={handleConsentSubmit}
              disabled={submitting}
            />
          )}

          {step === 'background' && questionnaire && (
            <>
              {draftSaveStatus && (
                <div className={styles.draftStatus}>
                  {draftSaveStatus === 'saving' && 'Saving...'}
                  {draftSaveStatus === 'saved' && '✓ Progress saved'}
                  {draftSaveStatus === 'error' && 'Failed to save'}
                </div>
              )}

              <QuestionnaireRenderer
                schema={{
                  ...questionnaire.schema,
                  fields: getFieldsForStep('background'),
                }}
                answers={answers}
                onChange={setAnswers}
                errors={errors}
                disabled={submitting}
              />

              <div className={styles.actions}>
                <button
                  className={styles.backButton}
                  onClick={() => setStep('landing')}
                >
                  Back
                </button>
                <button
                  className={styles.submitButton}
                  onClick={handleNextStep}
                  disabled={submitting}
                >
                  Continue
                </button>
              </div>
            </>
          )}

          {step === 'symptoms' && questionnaire && (
            <>
              {draftSaveStatus && (
                <div className={styles.draftStatus}>
                  {draftSaveStatus === 'saving' && 'Saving...'}
                  {draftSaveStatus === 'saved' && '✓ Progress saved'}
                  {draftSaveStatus === 'error' && 'Failed to save'}
                </div>
              )}

              <QuestionnaireRenderer
                schema={{
                  ...questionnaire.schema,
                  fields: getFieldsForStep('symptoms'),
                }}
                answers={answers}
                onChange={setAnswers}
                errors={errors}
                disabled={submitting}
              />

              <div className={styles.actions}>
                <button
                  className={styles.backButton}
                  onClick={handlePreviousStep}
                >
                  Back
                </button>
                <button
                  className={styles.submitButton}
                  onClick={handleNextStep}
                  disabled={submitting}
                >
                  Continue
                </button>
              </div>
            </>
          )}

          {step === 'safety' && questionnaire && (
            <>
              {draftSaveStatus && (
                <div className={styles.draftStatus}>
                  {draftSaveStatus === 'saving' && 'Saving...'}
                  {draftSaveStatus === 'saved' && '✓ Progress saved'}
                  {draftSaveStatus === 'error' && 'Failed to save'}
                </div>
              )}

              {/* Safety section framing - critical for reducing drop-off */}
              <div className={styles.safetyFraming}>
                <h2 id="intake-safety-title" className={styles.safetyFramingHeader}>
                  {copy.patient.intake.safety.title}
                </h2>
                <p id="intake-safety-body" className={styles.safetyFramingText}>
                  {copy.patient.intake.safety.body}
                </p>
                <div className={styles.microReassurance}>
                  {copy.patient.intake.safety.microReassurance}
                </div>
              </div>

              {/* Inline reassurance for SI questions */}
              <div id="intake-si-support-text" className={styles.siReassurance}>
                {copy.patient.intake.si.inlineSupport}
              </div>

              <QuestionnaireRenderer
                schema={{
                  ...questionnaire.schema,
                  fields: getFieldsForStep('safety'),
                }}
                answers={answers}
                onChange={setAnswers}
                errors={errors}
                disabled={submitting}
              />

              <div className={styles.actions}>
                <button
                  className={styles.backButton}
                  onClick={handlePreviousStep}
                >
                  Back
                </button>
                <button
                  className={styles.submitButton}
                  onClick={handleNextStep}
                  disabled={submitting}
                >
                  Continue
                </button>
              </div>
            </>
          )}

          {step === 'review' && (
            <div className={styles.review}>
              <h2>Review your information</h2>
              <p className={styles.reviewIntro}>
                Please review your responses before submitting. You can go back
                to any section to make changes.
              </p>

              <div className={styles.reviewSummary}>
                <p>
                  <strong>Sections completed:</strong> Background, Current
                  symptoms, Safety
                </p>
                <p>
                  <strong>Total questions answered:</strong>{' '}
                  {Object.keys(answers).length}
                </p>
              </div>

              <EmergencyBanner />

              <div className={styles.actions}>
                <button
                  className={styles.backButton}
                  onClick={handlePreviousStep}
                >
                  Go back & edit
                </button>
                <button
                  className={styles.submitButton}
                  onClick={handleFinalSubmit}
                  disabled={submitting}
                >
                  {submitting ? 'Submitting...' : 'Submit assessment'}
                </button>
              </div>
            </div>
          )}

          {step === 'complete' && (
            <div className={styles.complete}>
              <div className={styles.completeIcon}>✓</div>
              <h1 id="intake-submitted-title" className={styles.completeHeader}>
                {copy.patient.intake.submitted.title}
              </h1>
              <p className={styles.completePrimary}>
                {copy.patient.intake.submitted.primary}
              </p>

              <div id="intake-submitted-next-steps" className={styles.whatHappensNext}>
                <h2>{copy.patient.intake.submitted.nextStepsTitle}</h2>
                <ul>
                  {copy.patient.intake.submitted.nextStepsList.map((item, i) => (
                    <li key={i}>
                      {renderTemplate(item, { timeframe: '1–2 working days' })}
                    </li>
                  ))}
                </ul>
              </div>

              <div id="intake-submitted-timeline" className={styles.timeExpectation}>
                <strong>{copy.patient.intake.submitted.timeline}</strong>
              </div>

              {/* [CLINICAL] Safety reminder - DO NOT MODIFY */}
              <div className={styles.safetyReminder}>
                <span className={styles.warningIcon}>⚠️</span>
                <p>{copy.shared.safetyFooter.default}</p>
              </div>

              <button
                className={styles.dashboardButton}
                onClick={() => router.push('/dashboard')}
              >
                Go to your dashboard
              </button>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

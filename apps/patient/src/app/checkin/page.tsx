'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import EmergencyBanner from '@/components/EmergencyBanner';
import styles from './checkin.module.css';

interface CheckIn {
  id: string;
  sequence_number: number;
  scheduled_for: string;
  expires_at: string | null;
  status: string;
}

interface CheckInFormData {
  phq2_q1: number;
  phq2_q2: number;
  gad2_q1: number;
  gad2_q2: number;
  suicidal_ideation: boolean;
  self_harm: boolean;
  wellbeing_rating: number;
  patient_comments: string;
  wants_callback: boolean;
}

const PHQ2_OPTIONS = [
  { value: 0, label: 'Not at all' },
  { value: 1, label: 'Several days' },
  { value: 2, label: 'More than half the days' },
  { value: 3, label: 'Nearly every day' },
];

const GAD2_OPTIONS = [
  { value: 0, label: 'Not at all' },
  { value: 1, label: 'Several days' },
  { value: 2, label: 'More than half the days' },
  { value: 3, label: 'Nearly every day' },
];

export default function CheckInPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checkin, setCheckin] = useState<CheckIn | null>(null);
  const [step, setStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  const [formData, setFormData] = useState<CheckInFormData>({
    phq2_q1: -1,
    phq2_q2: -1,
    gad2_q1: -1,
    gad2_q2: -1,
    suicidal_ideation: false,
    self_harm: false,
    wellbeing_rating: 5,
    patient_comments: '',
    wants_callback: false,
  });

  const getToken = () => localStorage.getItem('access_token');

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push('/auth/login');
      return;
    }
    loadPendingCheckin();
  }, [router]);

  const loadPendingCheckin = async () => {
    try {
      const token = getToken();
      const res = await fetch('/api/v1/monitoring/patient/checkin', {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        const data = await res.json();
        if (data) {
          setCheckin(data);
        }
      }
      setLoading(false);
    } catch (err) {
      setError('Failed to load check-in');
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!checkin) return;

    // Validate all required fields
    if (formData.phq2_q1 < 0 || formData.phq2_q2 < 0 ||
        formData.gad2_q1 < 0 || formData.gad2_q2 < 0) {
      setError('Please answer all questions');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const token = getToken();
      const res = await fetch(`/api/v1/monitoring/patient/checkin/${checkin.id}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to submit check-in');
      }

      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit check-in');
    } finally {
      setSubmitting(false);
    }
  };

  const updateField = (field: keyof CheckInFormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const nextStep = () => setStep(s => s + 1);
  const prevStep = () => setStep(s => s - 1);

  if (loading) {
    return (
      <main className={styles.main}>
        <EmergencyBanner />
        <div className={styles.content}>
          <p>Loading...</p>
        </div>
      </main>
    );
  }

  if (!checkin) {
    return (
      <main className={styles.main}>
        <EmergencyBanner />
        <header className={styles.header}>
          <h1>Weekly Check-In</h1>
        </header>
        <div className={styles.content}>
          <div className={styles.card}>
            <h2>No Check-In Due</h2>
            <p>You don't have a pending check-in at this time.</p>
            <button
              onClick={() => router.push('/dashboard')}
              className={styles.primaryButton}
            >
              Return to Dashboard
            </button>
          </div>
        </div>
      </main>
    );
  }

  if (success) {
    return (
      <main className={styles.main}>
        <EmergencyBanner />
        <div className={styles.content}>
          <div className={styles.successCard}>
            <h2>Check-In Complete</h2>
            <p>Thank you for completing your weekly check-in.</p>
            {formData.suicidal_ideation || formData.self_harm ? (
              <div className={styles.urgentNotice}>
                <p>
                  Based on your responses, a member of our clinical team will be
                  in touch with you shortly. If you need immediate help, please
                  call our crisis line or 999.
                </p>
              </div>
            ) : formData.wants_callback ? (
              <p className={styles.callbackNotice}>
                We've noted that you'd like someone to call you. A member of our
                team will be in touch within 24 hours.
              </p>
            ) : null}
            <button
              onClick={() => router.push('/dashboard')}
              className={styles.primaryButton}
            >
              Return to Dashboard
            </button>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className={styles.main}>
      <EmergencyBanner />

      <header className={styles.header}>
        <h1>Weekly Check-In</h1>
        <span className={styles.progress}>Step {step} of 4</span>
      </header>

      <div className={styles.content}>
        {error && <div className={styles.errorBanner}>{error}</div>}

        <div className={styles.progressBar}>
          {[1, 2, 3, 4].map(s => (
            <div
              key={s}
              className={`${styles.progressStep} ${s <= step ? styles.progressStepActive : ''}`}
            />
          ))}
        </div>

        {/* Step 1: PHQ-2 Depression Screening */}
        {step === 1 && (
          <div className={styles.card}>
            <h2>Over the last 2 weeks, how often have you been bothered by the following?</h2>
            <p className={styles.subtitle}>Depression Screening (PHQ-2)</p>

            <div className={styles.question}>
              <p>1. Little interest or pleasure in doing things</p>
              <div className={styles.optionGrid}>
                {PHQ2_OPTIONS.map(opt => (
                  <label
                    key={opt.value}
                    className={`${styles.optionCard} ${formData.phq2_q1 === opt.value ? styles.optionCardSelected : ''}`}
                  >
                    <input
                      type="radio"
                      name="phq2_q1"
                      value={opt.value}
                      checked={formData.phq2_q1 === opt.value}
                      onChange={() => updateField('phq2_q1', opt.value)}
                    />
                    <span>{opt.label}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className={styles.question}>
              <p>2. Feeling down, depressed, or hopeless</p>
              <div className={styles.optionGrid}>
                {PHQ2_OPTIONS.map(opt => (
                  <label
                    key={opt.value}
                    className={`${styles.optionCard} ${formData.phq2_q2 === opt.value ? styles.optionCardSelected : ''}`}
                  >
                    <input
                      type="radio"
                      name="phq2_q2"
                      value={opt.value}
                      checked={formData.phq2_q2 === opt.value}
                      onChange={() => updateField('phq2_q2', opt.value)}
                    />
                    <span>{opt.label}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className={styles.navButtons}>
              <button onClick={() => router.push('/dashboard')} className={styles.secondaryButton}>
                Cancel
              </button>
              <button
                onClick={nextStep}
                disabled={formData.phq2_q1 < 0 || formData.phq2_q2 < 0}
                className={styles.primaryButton}
              >
                Next
              </button>
            </div>
          </div>
        )}

        {/* Step 2: GAD-2 Anxiety Screening */}
        {step === 2 && (
          <div className={styles.card}>
            <h2>Over the last 2 weeks, how often have you been bothered by the following?</h2>
            <p className={styles.subtitle}>Anxiety Screening (GAD-2)</p>

            <div className={styles.question}>
              <p>1. Feeling nervous, anxious, or on edge</p>
              <div className={styles.optionGrid}>
                {GAD2_OPTIONS.map(opt => (
                  <label
                    key={opt.value}
                    className={`${styles.optionCard} ${formData.gad2_q1 === opt.value ? styles.optionCardSelected : ''}`}
                  >
                    <input
                      type="radio"
                      name="gad2_q1"
                      value={opt.value}
                      checked={formData.gad2_q1 === opt.value}
                      onChange={() => updateField('gad2_q1', opt.value)}
                    />
                    <span>{opt.label}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className={styles.question}>
              <p>2. Not being able to stop or control worrying</p>
              <div className={styles.optionGrid}>
                {GAD2_OPTIONS.map(opt => (
                  <label
                    key={opt.value}
                    className={`${styles.optionCard} ${formData.gad2_q2 === opt.value ? styles.optionCardSelected : ''}`}
                  >
                    <input
                      type="radio"
                      name="gad2_q2"
                      value={opt.value}
                      checked={formData.gad2_q2 === opt.value}
                      onChange={() => updateField('gad2_q2', opt.value)}
                    />
                    <span>{opt.label}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className={styles.navButtons}>
              <button onClick={prevStep} className={styles.secondaryButton}>
                Back
              </button>
              <button
                onClick={nextStep}
                disabled={formData.gad2_q1 < 0 || formData.gad2_q2 < 0}
                className={styles.primaryButton}
              >
                Next
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Safety Questions */}
        {step === 3 && (
          <div className={styles.card}>
            <h2>Safety Questions</h2>
            <p className={styles.subtitle}>
              These questions help us ensure your safety. Please answer honestly.
            </p>

            <div className={styles.safetyQuestion}>
              <p>Have you had thoughts of harming yourself or ending your life?</p>
              <div className={styles.yesNoButtons}>
                <button
                  className={`${styles.yesNoButton} ${formData.suicidal_ideation === true ? styles.yesButtonSelected : ''}`}
                  onClick={() => updateField('suicidal_ideation', true)}
                >
                  Yes
                </button>
                <button
                  className={`${styles.yesNoButton} ${formData.suicidal_ideation === false ? styles.noButtonSelected : ''}`}
                  onClick={() => updateField('suicidal_ideation', false)}
                >
                  No
                </button>
              </div>
            </div>

            <div className={styles.safetyQuestion}>
              <p>Have you harmed yourself in the past 2 weeks?</p>
              <div className={styles.yesNoButtons}>
                <button
                  className={`${styles.yesNoButton} ${formData.self_harm === true ? styles.yesButtonSelected : ''}`}
                  onClick={() => updateField('self_harm', true)}
                >
                  Yes
                </button>
                <button
                  className={`${styles.yesNoButton} ${formData.self_harm === false ? styles.noButtonSelected : ''}`}
                  onClick={() => updateField('self_harm', false)}
                >
                  No
                </button>
              </div>
            </div>

            {(formData.suicidal_ideation || formData.self_harm) && (
              <div className={styles.crisisInfo}>
                <p>
                  If you are in immediate danger, please call 999 or go to your
                  nearest A&E. You can also contact the Samaritans on 116 123
                  (available 24/7).
                </p>
              </div>
            )}

            <div className={styles.navButtons}>
              <button onClick={prevStep} className={styles.secondaryButton}>
                Back
              </button>
              <button onClick={nextStep} className={styles.primaryButton}>
                Next
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Wellbeing & Additional Info */}
        {step === 4 && (
          <div className={styles.card}>
            <h2>How are you feeling overall?</h2>

            <div className={styles.wellbeingScale}>
              <p>Rate your overall wellbeing (1 = Very poor, 10 = Excellent)</p>
              <div className={styles.scaleButtons}>
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(n => (
                  <button
                    key={n}
                    className={`${styles.scaleButton} ${formData.wellbeing_rating === n ? styles.scaleButtonSelected : ''}`}
                    onClick={() => updateField('wellbeing_rating', n)}
                  >
                    {n}
                  </button>
                ))}
              </div>
              <div className={styles.scaleLabels}>
                <span>Very poor</span>
                <span>Excellent</span>
              </div>
            </div>

            <div className={styles.formGroup}>
              <label>Is there anything else you'd like to tell us? (Optional)</label>
              <textarea
                value={formData.patient_comments}
                onChange={e => updateField('patient_comments', e.target.value)}
                placeholder="Share any additional thoughts or concerns..."
                maxLength={2000}
                rows={4}
              />
            </div>

            <div className={styles.callbackOption}>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={formData.wants_callback}
                  onChange={e => updateField('wants_callback', e.target.checked)}
                />
                I would like someone from the team to call me
              </label>
            </div>

            <div className={styles.navButtons}>
              <button onClick={prevStep} className={styles.secondaryButton}>
                Back
              </button>
              <button
                onClick={handleSubmit}
                disabled={submitting}
                className={styles.submitButton}
              >
                {submitting ? 'Submitting...' : 'Submit Check-In'}
              </button>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

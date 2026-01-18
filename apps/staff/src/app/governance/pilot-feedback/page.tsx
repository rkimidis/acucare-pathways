'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { getToken, removeToken } from '@/lib/auth';
import { AppShell, PageHeader } from '@/ui/components';
import styles from './pilot-feedback.module.css';

type LikertValue = 'strongly_agree' | 'agree' | 'neutral' | 'disagree' | 'strongly_disagree';

interface FeedbackConfig {
  active_window: string | null;
  banner_enabled: boolean;
}

const likertOptions: { label: string; value: LikertValue }[] = [
  { label: 'Strongly agree', value: 'strongly_agree' },
  { label: 'Agree', value: 'agree' },
  { label: 'Neutral', value: 'neutral' },
  { label: 'Disagree', value: 'disagree' },
  { label: 'Strongly disagree', value: 'strongly_disagree' },
];

const likertQuestions = [
  {
    id: 'safety_understand_escalation',
    text: 'I understand why cases are escalated to RED/AMBER.',
    section: 'Safety and trust',
  },
  {
    id: 'safety_prioritise',
    text: 'The system helps me prioritise patients safely.',
    section: 'Safety and trust',
  },
  {
    id: 'safety_override_confidence',
    text: 'I feel able to override decisions when clinically appropriate.',
    section: 'Safety and trust',
  },
  {
    id: 'workflow_next_case',
    text: 'Finding the next case I need to act on is easy.',
    section: 'Workflow efficiency',
  },
  {
    id: 'workflow_dashboard_signal',
    text: 'The dashboard shows me what matters most.',
    section: 'Workflow efficiency',
  },
  {
    id: 'workflow_admin_time',
    text: 'I spend less time on admin compared to previous workflows.',
    section: 'Workflow efficiency',
  },
  {
    id: 'escalation_deterioration',
    text: 'Deterioration while waiting is handled appropriately.',
    section: 'Escalation and monitoring',
  },
  {
    id: 'escalation_alerts',
    text: 'Escalation alerts are timely and proportionate.',
    section: 'Escalation and monitoring',
  },
];

const openQuestions = [
  {
    id: 'open_worry',
    text: 'What, if anything, worried you while using the system?',
  },
  {
    id: 'open_friction',
    text: 'Where did you feel slowed down or frustrated?',
  },
  {
    id: 'open_override_reason',
    text: 'Did you override a decision? If yes, why?',
  },
  {
    id: 'open_change',
    text: 'One change that would most improve safety or usability.',
  },
];

export default function PilotFeedbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [config, setConfig] = useState<FeedbackConfig | null>(null);
  const [likertAnswers, setLikertAnswers] = useState<Record<string, LikertValue>>({});
  const [openAnswers, setOpenAnswers] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push('/auth/login');
      return;
    }

    fetch('/api/v1/pilot-feedback/config', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => data && setConfig(data))
      .catch(() => {});
  }, [router]);

  const windowParam = searchParams.get('window');
  const caseIdParam = searchParams.get('case_id');

  const resolvedWindow = useMemo(() => {
    if (windowParam) return windowParam;
    if (config?.active_window) return config.active_window;
    return 'AD_HOC';
  }, [windowParam, config]);

  const windowLabel = resolvedWindow === 'WEEK_1'
    ? 'Week 1'
    : resolvedWindow === 'WEEK_4'
      ? 'Week 4'
      : resolvedWindow === 'POST_CASE'
        ? 'Post case'
        : 'Ad hoc';

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError('');

    try {
      const token = getToken();
      if (!token) {
        router.push('/auth/login');
        return;
      }

      const response = await fetch('/api/v1/pilot-feedback', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          window: resolvedWindow,
          case_id: caseIdParam || null,
          answers: { likert: likertAnswers },
          free_text: { open: openAnswers },
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to submit feedback');
      }

      setSuccess(true);
      setLikertAnswers({});
      setOpenAnswers({});
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit feedback');
    } finally {
      setSubmitting(false);
    }
  };

  const allLikertAnswered = likertQuestions.every((q) => Boolean(likertAnswers[q.id]));

  const handleLogout = () => {
    removeToken();
    router.push('/');
  };

  return (
    <AppShell activeNav="pilot" onSignOut={handleLogout}>
      <PageHeader
        title="Pilot Feedback"
        breadcrumb={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Pilot Feedback' },
        ]}
        metaText={`10-12 questions, about 5 minutes. Window: ${windowLabel}${
          caseIdParam ? ` (Case ${caseIdParam.slice(0, 8)})` : ''
        }`}
      />

      <div className={styles.content}>
        {success && (
          <div className={styles.success}>
            Thanks for sharing feedback. It will be reviewed weekly during the pilot.
          </div>
        )}
        {error && <div className={styles.error}>{error}</div>}

        <form onSubmit={handleSubmit}>
          <section className={styles.section}>
            <h2>Safety and trust</h2>
            {likertQuestions
              .filter((q) => q.section === 'Safety and trust')
              .map((question) => (
                <div key={question.id} className={styles.question}>
                  <div className={styles.questionLabel}>{question.text}</div>
                  <div className={styles.options}>
                    {likertOptions.map((option) => (
                      <label key={option.value} className={styles.optionLabel}>
                        <input
                          type="radio"
                          name={question.id}
                          value={option.value}
                          checked={likertAnswers[question.id] === option.value}
                          onChange={() =>
                            setLikertAnswers((prev) => ({
                              ...prev,
                              [question.id]: option.value,
                            }))
                          }
                          required
                        />
                        {option.label}
                      </label>
                    ))}
                  </div>
                </div>
              ))}
          </section>

          <section className={styles.section}>
            <h2>Workflow efficiency</h2>
            {likertQuestions
              .filter((q) => q.section === 'Workflow efficiency')
              .map((question) => (
                <div key={question.id} className={styles.question}>
                  <div className={styles.questionLabel}>{question.text}</div>
                  <div className={styles.options}>
                    {likertOptions.map((option) => (
                      <label key={option.value} className={styles.optionLabel}>
                        <input
                          type="radio"
                          name={question.id}
                          value={option.value}
                          checked={likertAnswers[question.id] === option.value}
                          onChange={() =>
                            setLikertAnswers((prev) => ({
                              ...prev,
                              [question.id]: option.value,
                            }))
                          }
                          required
                        />
                        {option.label}
                      </label>
                    ))}
                  </div>
                </div>
              ))}
          </section>

          <section className={styles.section}>
            <h2>Escalation and monitoring</h2>
            {likertQuestions
              .filter((q) => q.section === 'Escalation and monitoring')
              .map((question) => (
                <div key={question.id} className={styles.question}>
                  <div className={styles.questionLabel}>{question.text}</div>
                  <div className={styles.options}>
                    {likertOptions.map((option) => (
                      <label key={option.value} className={styles.optionLabel}>
                        <input
                          type="radio"
                          name={question.id}
                          value={option.value}
                          checked={likertAnswers[question.id] === option.value}
                          onChange={() =>
                            setLikertAnswers((prev) => ({
                              ...prev,
                              [question.id]: option.value,
                            }))
                          }
                          required
                        />
                        {option.label}
                      </label>
                    ))}
                  </div>
                </div>
              ))}
          </section>

          <section className={styles.section}>
            <h2>Open text</h2>
            {openQuestions.map((question) => (
              <div key={question.id} className={styles.question}>
                <div className={styles.questionLabel}>{question.text}</div>
                <textarea
                  className={styles.textArea}
                  rows={3}
                  value={openAnswers[question.id] || ''}
                  onChange={(e) =>
                    setOpenAnswers((prev) => ({
                      ...prev,
                      [question.id]: e.target.value,
                    }))
                  }
                />
              </div>
            ))}
            <p className={styles.helperNote}>
              Responses are reviewed weekly and categorized into safety, UX friction, or training
              gaps. This is not a performance review.
            </p>
          </section>

          <div className={styles.actions}>
            <button
              type="submit"
              className={styles.submitButton}
              disabled={!allLikertAnswered || submitting}
            >
              {submitting ? 'Submitting...' : 'Submit feedback'}
            </button>
          </div>
          <p className={styles.footerNote}>
            Thank you for helping improve safety and usability during the pilot.
          </p>
        </form>
      </div>
    </AppShell>
  );
}

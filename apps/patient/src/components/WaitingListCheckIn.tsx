'use client';

/**
 * Waiting List Check-In Component
 *
 * Weekly check-in while patient is waiting for appointment.
 * Helps detect deterioration and provide appropriate support.
 */

import { useState } from 'react';
import styles from './WaitingListCheckIn.module.css';

interface CheckInQuestion {
  id: string;
  text: string;
  options: { value: string; label: string }[];
}

interface WaitingListCheckInProps {
  /** Patient's first name */
  patientName?: string;
  /** Questions to display */
  questions?: CheckInQuestion[];
  /** Callback when check-in is submitted */
  onSubmit: (answers: Record<string, string>) => void;
  /** Whether submission is in progress */
  submitting?: boolean;
}

const DEFAULT_QUESTIONS: CheckInQuestion[] = [
  {
    id: 'overall_feeling',
    text: 'Overall, how have you been feeling this week?',
    options: [
      { value: 'much_better', label: 'Much better' },
      { value: 'a_bit_better', label: 'A bit better' },
      { value: 'about_the_same', label: 'About the same' },
      { value: 'a_bit_worse', label: 'A bit worse' },
      { value: 'much_worse', label: 'Much worse' },
    ],
  },
  {
    id: 'safety',
    text: 'Have you had thoughts of harming yourself?',
    options: [
      { value: 'no', label: 'No' },
      { value: 'occasionally', label: 'Occasionally, but fleeting' },
      { value: 'frequently', label: 'Yes, frequently' },
      { value: 'with_plan', label: 'Yes, with thoughts of how' },
    ],
  },
];

export default function WaitingListCheckIn({
  patientName,
  questions = DEFAULT_QUESTIONS,
  onSubmit,
  submitting = false,
}: WaitingListCheckInProps) {
  const [answers, setAnswers] = useState<Record<string, string>>({});

  const handleOptionChange = (questionId: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  };

  const handleSubmit = () => {
    onSubmit(answers);
  };

  const allAnswered = questions.every((q) => answers[q.id]);

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <h1 className={styles.title}>Checking in — how are you feeling?</h1>
      </div>

      {/* Introduction */}
      <div className={styles.intro}>
        <p>
          {patientName ? `Hi ${patientName}, we're` : "We're"} checking in while
          you&apos;re waiting for your appointment.
        </p>
        <p className={styles.purpose}>
          This short check-in helps us notice if things have changed and whether
          additional support is needed.
        </p>
      </div>

      {/* Questions */}
      <div className={styles.questions}>
        {questions.map((question, index) => (
          <div key={question.id} className={styles.question}>
            <label className={styles.questionLabel}>
              {index + 1}. {question.text}
            </label>
            <div className={styles.options}>
              {question.options.map((option) => (
                <label
                  key={option.value}
                  className={`${styles.option} ${
                    answers[question.id] === option.value ? styles.optionSelected : ''
                  }`}
                >
                  <input
                    type="radio"
                    name={question.id}
                    value={option.value}
                    checked={answers[question.id] === option.value}
                    onChange={() => handleOptionChange(question.id, option.value)}
                    className={styles.radioInput}
                  />
                  <span className={styles.optionLabel}>{option.label}</span>
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!allAnswered || submitting}
        className={styles.submitButton}
      >
        {submitting ? 'Submitting...' : 'Submit check-in'}
      </button>

      {/* Safety footer - always present */}
      <div className={styles.safetyFooter}>
        <span className={styles.warningIcon}>⚠️</span>
        <p>
          If you&apos;re in immediate danger, please contact <strong>999</strong> or
          attend <strong>A&amp;E</strong>.
        </p>
      </div>
    </div>
  );
}

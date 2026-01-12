'use client';

/**
 * Incident Creation Prompt Component
 *
 * Prompts clinician to create an incident record.
 *
 * Display rules - Auto-suggest when:
 * - tier is RED
 * - or clinician escalates
 * - or safety contact attempt fails
 */

import { copy } from '@/copy';
import styles from './IncidentPrompt.module.css';

interface IncidentPromptProps {
  /** Whether prompt is visible */
  isOpen: boolean;
  /** Callback when create button is clicked */
  onCreate: () => void;
  /** Callback when dismiss button is clicked */
  onDismiss: () => void;
  /** Reason for showing prompt (for context) */
  reason?: 'red_tier' | 'escalation' | 'safety_contact_failed';
}

export default function IncidentPrompt({
  isOpen,
  onCreate,
  onDismiss,
  reason,
}: IncidentPromptProps) {
  if (!isOpen) {
    return null;
  }

  return (
    <div id="incident-prompt" className={styles.prompt} role="alert">
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
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="12" y1="18" x2="12" y2="12" />
          <line x1="9" y1="15" x2="15" y2="15" />
        </svg>
      </div>

      <div className={styles.content}>
        <h3 className={styles.title}>{copy.staff.incidentPrompt.title}</h3>
        <p className={styles.body}>{copy.staff.incidentPrompt.body}</p>
      </div>

      <div className={styles.actions}>
        <button
          id="incident-create-button"
          type="button"
          className={styles.createButton}
          onClick={onCreate}
        >
          {copy.staff.incidentPrompt.createButton}
        </button>
        <button
          type="button"
          className={styles.dismissButton}
          onClick={onDismiss}
        >
          {copy.staff.incidentPrompt.dismissButton}
        </button>
      </div>
    </div>
  );
}

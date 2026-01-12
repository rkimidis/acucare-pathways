'use client';

/**
 * Override Confirmation Dialog Component
 *
 * Modal dialog for clinical override confirmation.
 * Requires rationale input (min 20 characters) before confirmation.
 *
 * Acceptance rules:
 * - UI: Confirm button disabled until rationale length >= 20 chars
 * - Backend: Also enforces rationale required
 */

import { useState } from 'react';
import { copy } from '@/copy';
import styles from './OverrideDialog.module.css';

const MIN_RATIONALE_LENGTH = 20;

interface OverrideDialogProps {
  /** Whether dialog is open */
  isOpen: boolean;
  /** Callback when dialog is closed */
  onClose: () => void;
  /** Callback when override is confirmed with rationale */
  onConfirm: (rationale: string) => void;
  /** Whether confirmation is in progress */
  confirming?: boolean;
}

export default function OverrideDialog({
  isOpen,
  onClose,
  onConfirm,
  confirming = false,
}: OverrideDialogProps) {
  const [rationale, setRationale] = useState('');

  const isValid = rationale.trim().length >= MIN_RATIONALE_LENGTH;
  const charsRemaining = MIN_RATIONALE_LENGTH - rationale.trim().length;

  const handleConfirm = () => {
    if (isValid) {
      onConfirm(rationale.trim());
    }
  };

  const handleClose = () => {
    setRationale('');
    onClose();
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className={styles.overlay} onClick={handleClose}>
      <div
        id="override-dialog"
        className={styles.dialog}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="override-dialog-title"
      >
        {/* Header */}
        <div className={styles.header}>
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
          <h2 id="override-dialog-title" className={styles.title}>
            {copy.staff.override.title}
          </h2>
        </div>

        {/* Body */}
        <p className={styles.body}>{copy.staff.override.body}</p>

        {/* Rationale textarea */}
        <div className={styles.field}>
          <label htmlFor="override-rationale-textarea" className={styles.label}>
            {copy.staff.override.rationaleLabel}
          </label>
          <textarea
            id="override-rationale-textarea"
            className={styles.textarea}
            placeholder={copy.staff.override.rationalePlaceholder}
            value={rationale}
            onChange={(e) => setRationale(e.target.value)}
            rows={4}
            disabled={confirming}
          />
          <span className={`${styles.hint} ${isValid ? styles.hintValid : ''}`}>
            {isValid
              ? 'Rationale meets minimum requirement'
              : `${copy.staff.override.rationaleHint} (${charsRemaining} more needed)`}
          </span>
        </div>

        {/* Actions */}
        <div className={styles.actions}>
          <button
            type="button"
            className={styles.cancelButton}
            onClick={handleClose}
            disabled={confirming}
          >
            {copy.staff.override.cancelButton}
          </button>
          <button
            id="override-confirm-button"
            type="button"
            className={styles.confirmButton}
            onClick={handleConfirm}
            disabled={!isValid || confirming}
          >
            {confirming ? 'Confirming...' : copy.staff.override.confirmButton}
          </button>
        </div>
      </div>
    </div>
  );
}

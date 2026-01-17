'use client';

import { useState } from 'react';
import { getToken } from '@/lib/auth';
import styles from './CancelAppointmentModal.module.css';

interface Appointment {
  id: string;
  scheduled_datetime: string;
  appointment_type: string;
  clinician_name: string | null;
}

export interface CancelResult {
  success: boolean;
  message: string;
  cancelled: boolean;
  request_submitted: boolean;
  safety_workflow_triggered: boolean;
}

interface CancelAppointmentModalProps {
  appointment: Appointment;
  onClose: () => void;
  onSuccess: (result: CancelResult) => void;
}

export default function CancelAppointmentModal({
  appointment,
  onClose,
  onSuccess,
}: CancelAppointmentModalProps) {
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CancelResult | null>(null);

  const formatDateTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString('en-GB', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);

    const token = getToken();
    if (!token) {
      setError('Please log in again');
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(
        `/api/v1/scheduling/patient/appointments/${appointment.id}/cancel`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ reason: reason || null }),
        }
      );

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to cancel appointment');
      }

      const data: CancelResult = await response.json();
      setResult(data);

      // If immediate cancellation, notify parent to refresh
      if (data.cancelled) {
        setTimeout(() => onSuccess(data), 2000);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (result) {
      onSuccess(result);
    } else {
      onClose();
    }
  };

  // Show result state
  if (result) {
    // Safety workflow triggered - show caring message
    if (result.safety_workflow_triggered) {
      return (
        <div className={styles.overlay} onClick={handleClose}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.resultContent}>
              <div className={styles.safetyIcon}>
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
                </svg>
              </div>
              <h2 className={styles.safetyTitle}>We&apos;ve received your message</h2>
              <p className={styles.safetyMessage}>
                A member of our team will contact you soon. If you need immediate
                support, please call <strong>999</strong> or attend <strong>A&amp;E</strong>.
              </p>
              <button onClick={handleClose} className={styles.closeButton}>
                Close
              </button>
            </div>
          </div>
        </div>
      );
    }

    // Request submitted (needs staff review)
    if (result.request_submitted) {
      return (
        <div className={styles.overlay} onClick={handleClose}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.resultContent}>
              <div className={styles.pendingIcon}>
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12,6 12,12 16,14" />
                </svg>
              </div>
              <h2 className={styles.resultTitle}>Cancellation request received</h2>
              <p className={styles.resultMessage}>
                Our team will review your request and be in touch shortly.
              </p>
              <button onClick={handleClose} className={styles.closeButton}>
                Close
              </button>
            </div>
          </div>
        </div>
      );
    }

    // Immediate cancellation success
    return (
      <div className={styles.overlay} onClick={handleClose}>
        <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
          <div className={styles.resultContent}>
            <div className={styles.successIcon}>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
            </div>
            <h2 className={styles.resultTitle}>Appointment cancelled</h2>
            <p className={styles.resultMessage}>
              Your appointment has been cancelled.
            </p>
            <button onClick={handleClose} className={styles.closeButton}>
              Close
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Show cancel form
  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>Cancel appointment</h2>
          <button onClick={onClose} className={styles.closeX} aria-label="Close">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className={styles.body}>
          <div className={styles.appointmentSummary}>
            <p className={styles.appointmentType}>{appointment.appointment_type}</p>
            <p className={styles.appointmentTime}>
              {formatDateTime(appointment.scheduled_datetime)}
            </p>
            {appointment.clinician_name && (
              <p className={styles.clinicianName}>
                With: {appointment.clinician_name}
              </p>
            )}
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="cancel-reason" className={styles.label}>
              Reason for cancellation (optional)
            </label>
            <textarea
              id="cancel-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Let us know why you need to cancel..."
              className={styles.textarea}
              rows={3}
              disabled={loading}
            />
          </div>

          {error && <p className={styles.error}>{error}</p>}
        </div>

        <div className={styles.footer}>
          <button
            onClick={onClose}
            className={styles.secondaryButton}
            disabled={loading}
          >
            Keep appointment
          </button>
          <button
            onClick={handleSubmit}
            className={styles.dangerButton}
            disabled={loading}
          >
            {loading ? 'Cancelling...' : 'Cancel appointment'}
          </button>
        </div>
      </div>
    </div>
  );
}

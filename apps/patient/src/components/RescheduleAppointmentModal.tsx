'use client';

import { useState, useEffect, useMemo } from 'react';
import { getToken } from '@/lib/auth';
import styles from './RescheduleAppointmentModal.module.css';

interface Appointment {
  id: string;
  scheduled_datetime: string;
  appointment_type: string;
  appointment_type_id: string;
  clinician_id: string;
  clinician_name: string | null;
  reschedule_count?: number;
}

interface AvailableSlot {
  start: string;
  end: string;
  clinician_id: string;
  is_remote: boolean;
  location: string | null;
}

export interface RescheduleResult {
  success: boolean;
  message: string;
  rescheduled: boolean;
  request_submitted: boolean;
  new_appointment_id: string | null;
}

interface RescheduleAppointmentModalProps {
  appointment: Appointment;
  onClose: () => void;
  onSuccess: (result: RescheduleResult) => void;
}

const MAX_RESCHEDULES = 2;

export default function RescheduleAppointmentModal({
  appointment,
  onClose,
  onSuccess,
}: RescheduleAppointmentModalProps) {
  const [selectedSlot, setSelectedSlot] = useState<AvailableSlot | null>(null);
  const [availableSlots, setAvailableSlots] = useState<AvailableSlot[]>([]);
  const [loadingSlots, setLoadingSlots] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RescheduleResult | null>(null);

  const rescheduleCount = appointment.reschedule_count || 0;
  const remainingReschedules = MAX_RESCHEDULES - rescheduleCount;
  const canReschedule = remainingReschedules > 0;

  // Fetch available slots
  useEffect(() => {
    const fetchSlots = async () => {
      const token = getToken();
      if (!token) {
        setError('Please log in again');
        setLoadingSlots(false);
        return;
      }

      try {
        // Fetch next 14 days of availability
        const startDate = new Date();
        const endDate = new Date();
        endDate.setDate(endDate.getDate() + 14);

        const params = new URLSearchParams({
          clinician_id: appointment.clinician_id,
          appointment_type_id: appointment.appointment_type_id,
          start_date: startDate.toISOString().split('T')[0],
          end_date: endDate.toISOString().split('T')[0],
        });

        const response = await fetch(
          `/api/v1/scheduling/patient/available-slots?${params}`,
          {
            headers: { Authorization: `Bearer ${token}` },
          }
        );

        if (!response.ok) {
          throw new Error('Failed to load available times');
        }

        const data: AvailableSlot[] = await response.json();
        setAvailableSlots(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load times');
      } finally {
        setLoadingSlots(false);
      }
    };

    if (canReschedule) {
      fetchSlots();
    } else {
      setLoadingSlots(false);
    }
  }, [appointment, canReschedule]);

  // Group slots by date
  const slotsByDate = useMemo(() => {
    const groups: Record<string, AvailableSlot[]> = {};
    availableSlots.forEach((slot) => {
      const dateKey = new Date(slot.start).toDateString();
      if (!groups[dateKey]) {
        groups[dateKey] = [];
      }
      groups[dateKey].push(slot);
    });
    return groups;
  }, [availableSlots]);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-GB', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
    });
  };

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

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
    if (!selectedSlot) return;

    setSubmitting(true);
    setError(null);

    const token = getToken();
    if (!token) {
      setError('Please log in again');
      setSubmitting(false);
      return;
    }

    try {
      const response = await fetch(
        `/api/v1/scheduling/patient/appointments/${appointment.id}/reschedule`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            new_scheduled_start: selectedSlot.start,
          }),
        }
      );

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to reschedule appointment');
      }

      const data: RescheduleResult = await response.json();
      setResult(data);

      if (data.rescheduled) {
        setTimeout(() => onSuccess(data), 2000);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setSubmitting(false);
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
              <h2 className={styles.resultTitle}>Reschedule request received</h2>
              <p className={styles.resultMessage}>
                Our team will review and confirm your new time shortly.
              </p>
              <button onClick={handleClose} className={styles.closeButton}>
                Close
              </button>
            </div>
          </div>
        </div>
      );
    }

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
            <h2 className={styles.resultTitle}>Appointment rescheduled</h2>
            <p className={styles.resultMessage}>
              Your new appointment is confirmed for{' '}
              <strong>{selectedSlot ? formatDateTime(selectedSlot.start) : ''}</strong>
            </p>
            <button onClick={handleClose} className={styles.closeButton}>
              Close
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Can't reschedule - limit reached
  if (!canReschedule) {
    return (
      <div className={styles.overlay} onClick={onClose}>
        <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
          <div className={styles.header}>
            <h2>Reschedule appointment</h2>
            <button onClick={onClose} className={styles.closeX} aria-label="Close">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <div className={styles.body}>
            <div className={styles.limitReached}>
              <p className={styles.limitMessage}>
                This appointment cannot be rescheduled further. Please contact us
                if you need to make changes.
              </p>
            </div>
          </div>
          <div className={styles.footer}>
            <button onClick={onClose} className={styles.primaryButton}>
              Close
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Show reschedule form
  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>Reschedule appointment</h2>
          <button onClick={onClose} className={styles.closeX} aria-label="Close">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className={styles.body}>
          <div className={styles.currentAppointment}>
            <p className={styles.currentLabel}>Current appointment:</p>
            <p className={styles.currentTime}>
              {formatDateTime(appointment.scheduled_datetime)}
            </p>
            {appointment.clinician_name && (
              <p className={styles.clinicianName}>
                With: {appointment.clinician_name}
              </p>
            )}
          </div>

          <p className={styles.remainingCount}>
            {remainingReschedules} reschedule{remainingReschedules !== 1 ? 's' : ''} remaining
          </p>

          {loadingSlots ? (
            <div className={styles.loadingSlots}>Loading available times...</div>
          ) : availableSlots.length === 0 ? (
            <div className={styles.noSlots}>
              No available times found in the next 14 days. Please contact us.
            </div>
          ) : (
            <div className={styles.slotsContainer}>
              <p className={styles.selectLabel}>Select a new time:</p>
              {Object.entries(slotsByDate).map(([dateKey, slots]) => (
                <div key={dateKey} className={styles.dateGroup}>
                  <h3 className={styles.dateHeader}>{formatDate(slots[0].start)}</h3>
                  <div className={styles.timeSlots}>
                    {slots.map((slot) => (
                      <button
                        key={slot.start}
                        onClick={() => setSelectedSlot(slot)}
                        className={`${styles.timeSlot} ${
                          selectedSlot?.start === slot.start ? styles.selected : ''
                        }`}
                      >
                        {formatTime(slot.start)}
                        {slot.is_remote && (
                          <span className={styles.remoteTag}>Video</span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {error && <p className={styles.error}>{error}</p>}
        </div>

        <div className={styles.footer}>
          <button
            onClick={onClose}
            className={styles.secondaryButton}
            disabled={submitting}
          >
            Keep current time
          </button>
          <button
            onClick={handleSubmit}
            className={styles.primaryButton}
            disabled={submitting || !selectedSlot}
          >
            {submitting ? 'Rescheduling...' : 'Reschedule'}
          </button>
        </div>
      </div>
    </div>
  );
}

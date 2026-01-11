'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import EmergencyBanner from '@/components/EmergencyBanner';
import styles from './booking.module.css';

interface Clinician {
  id: string;
  title: string;
  specialties: string[];
  bio: string | null;
}

interface AppointmentType {
  id: string;
  code: string;
  name: string;
  description: string | null;
  duration_minutes: number;
  allow_remote: boolean;
}

interface AvailableSlot {
  start: string;
  end: string;
  clinician_id: string;
  is_remote: boolean;
  location: string | null;
}

interface SelfBookCheck {
  allowed: boolean;
  reason: string | null;
}

export default function BookingPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const triageCaseId = searchParams.get('case');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Form state
  const [clinicians, setClinicians] = useState<Clinician[]>([]);
  const [appointmentTypes, setAppointmentTypes] = useState<AppointmentType[]>([]);
  const [selectedClinician, setSelectedClinician] = useState<string>('');
  const [selectedType, setSelectedType] = useState<string>('');
  const [availableSlots, setAvailableSlots] = useState<AvailableSlot[]>([]);
  const [selectedSlot, setSelectedSlot] = useState<AvailableSlot | null>(null);
  const [isRemote, setIsRemote] = useState(false);
  const [patientNotes, setPatientNotes] = useState('');

  // Self-book eligibility
  const [selfBookCheck, setSelfBookCheck] = useState<SelfBookCheck | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const getToken = () => localStorage.getItem('access_token');

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push('/auth/login');
      return;
    }
    loadInitialData();
  }, [router]);

  const loadInitialData = async () => {
    try {
      const token = getToken();
      const headers = { Authorization: `Bearer ${token}` };

      // Load clinicians and appointment types in parallel
      const [cliniciansRes, typesRes] = await Promise.all([
        fetch('/api/v1/scheduling/patient/clinicians', { headers }),
        fetch('/api/v1/scheduling/patient/appointment-types', { headers }),
      ]);

      if (!cliniciansRes.ok || !typesRes.ok) {
        throw new Error('Failed to load booking options');
      }

      const cliniciansData = await cliniciansRes.json();
      const typesData = await typesRes.json();

      setClinicians(cliniciansData);
      setAppointmentTypes(typesData);
      setLoading(false);
    } catch (err) {
      setError('Failed to load booking options. Please try again.');
      setLoading(false);
    }
  };

  const checkSelfBookEligibility = async () => {
    if (!triageCaseId || !selectedType) return;

    try {
      const token = getToken();
      const res = await fetch(
        `/api/v1/scheduling/patient/self-book-check?triage_case_id=${triageCaseId}&appointment_type_id=${selectedType}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (res.ok) {
        const data = await res.json();
        setSelfBookCheck(data);
      }
    } catch (err) {
      console.error('Failed to check self-book eligibility', err);
    }
  };

  useEffect(() => {
    if (selectedType && triageCaseId) {
      checkSelfBookEligibility();
    }
  }, [selectedType, triageCaseId]);

  const loadAvailableSlots = async () => {
    if (!selectedClinician || !selectedType) return;

    try {
      const token = getToken();

      // Get slots for the next 14 days
      const startDate = new Date().toISOString().split('T')[0];
      const endDate = new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

      const res = await fetch(
        `/api/v1/scheduling/patient/available-slots?clinician_id=${selectedClinician}&appointment_type_id=${selectedType}&start_date=${startDate}&end_date=${endDate}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (res.ok) {
        const slots = await res.json();
        setAvailableSlots(slots);
      }
    } catch (err) {
      console.error('Failed to load available slots', err);
    }
  };

  useEffect(() => {
    if (selectedClinician && selectedType) {
      loadAvailableSlots();
    }
  }, [selectedClinician, selectedType]);

  const handleBookAppointment = async () => {
    if (!selectedSlot || !selectedType) return;

    setSubmitting(true);
    setError(null);

    try {
      const token = getToken();
      const res = await fetch('/api/v1/scheduling/patient/appointments', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          clinician_id: selectedClinician,
          appointment_type_id: selectedType,
          scheduled_start: selectedSlot.start,
          triage_case_id: triageCaseId,
          is_remote: isRemote,
          location: selectedSlot.location,
          patient_notes: patientNotes || null,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        if (res.status === 403) {
          throw new Error(data.detail || 'Self-booking is not allowed for your triage tier');
        }
        if (res.status === 409) {
          throw new Error('This time slot is no longer available. Please select another.');
        }
        throw new Error(data.detail || 'Failed to book appointment');
      }

      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to book appointment');
    } finally {
      setSubmitting(false);
    }
  };

  const formatDateTime = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleString('en-GB', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const groupSlotsByDate = (slots: AvailableSlot[]) => {
    const groups: Record<string, AvailableSlot[]> = {};
    slots.forEach(slot => {
      const date = new Date(slot.start).toLocaleDateString('en-GB', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
      });
      if (!groups[date]) groups[date] = [];
      groups[date].push(slot);
    });
    return groups;
  };

  if (loading) {
    return (
      <main className={styles.main}>
        <EmergencyBanner />
        <div className={styles.content}>
          <p>Loading booking options...</p>
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
            <h2>Appointment Booked</h2>
            <p>
              Your appointment has been successfully scheduled. You will receive
              a confirmation email with the details.
            </p>
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

  if (selfBookCheck && !selfBookCheck.allowed) {
    return (
      <main className={styles.main}>
        <EmergencyBanner />
        <header className={styles.header}>
          <h1>Book an Appointment</h1>
          <button onClick={() => router.push('/dashboard')} className={styles.backButton}>
            Back to Dashboard
          </button>
        </header>
        <div className={styles.content}>
          <div className={styles.blockedCard}>
            <h2>Booking Not Available</h2>
            <p>{selfBookCheck.reason}</p>
            <p className={styles.helpText}>
              Please wait for our clinical team to contact you, or call our
              reception to schedule an appointment.
            </p>
          </div>
        </div>
      </main>
    );
  }

  const slotsByDate = groupSlotsByDate(availableSlots);

  return (
    <main className={styles.main}>
      <EmergencyBanner />

      <header className={styles.header}>
        <h1>Book an Appointment</h1>
        <button onClick={() => router.push('/dashboard')} className={styles.backButton}>
          Back to Dashboard
        </button>
      </header>

      <div className={styles.content}>
        {error && <div className={styles.errorBanner}>{error}</div>}

        {/* Step 1: Select Appointment Type */}
        <section className={styles.card}>
          <h2>1. Select Appointment Type</h2>
          <div className={styles.typeGrid}>
            {appointmentTypes.map(type => (
              <button
                key={type.id}
                className={`${styles.typeCard} ${selectedType === type.id ? styles.typeCardSelected : ''}`}
                onClick={() => {
                  setSelectedType(type.id);
                  setSelectedSlot(null);
                }}
              >
                <h3>{type.name}</h3>
                <p>{type.description}</p>
                <span className={styles.duration}>{type.duration_minutes} minutes</span>
                {type.allow_remote && <span className={styles.remoteBadge}>Video available</span>}
              </button>
            ))}
          </div>
        </section>

        {/* Step 2: Select Clinician */}
        {selectedType && (
          <section className={styles.card}>
            <h2>2. Select Clinician</h2>
            <div className={styles.clinicianGrid}>
              {clinicians.map(clinician => (
                <button
                  key={clinician.id}
                  className={`${styles.clinicianCard} ${selectedClinician === clinician.id ? styles.clinicianCardSelected : ''}`}
                  onClick={() => {
                    setSelectedClinician(clinician.id);
                    setSelectedSlot(null);
                  }}
                >
                  <h3>{clinician.title}</h3>
                  <p className={styles.specialties}>
                    {clinician.specialties.join(', ')}
                  </p>
                  {clinician.bio && <p className={styles.bio}>{clinician.bio}</p>}
                </button>
              ))}
            </div>
          </section>
        )}

        {/* Step 3: Select Time Slot */}
        {selectedClinician && selectedType && (
          <section className={styles.card}>
            <h2>3. Select Date and Time</h2>
            {availableSlots.length === 0 ? (
              <p className={styles.noSlots}>No available slots in the next 14 days.</p>
            ) : (
              <div className={styles.slotsContainer}>
                {Object.entries(slotsByDate).map(([date, slots]) => (
                  <div key={date} className={styles.dateGroup}>
                    <h3 className={styles.dateHeader}>{date}</h3>
                    <div className={styles.slotGrid}>
                      {slots.map((slot, idx) => {
                        const time = new Date(slot.start).toLocaleTimeString('en-GB', {
                          hour: '2-digit',
                          minute: '2-digit',
                        });
                        return (
                          <button
                            key={idx}
                            className={`${styles.slotButton} ${selectedSlot?.start === slot.start ? styles.slotButtonSelected : ''}`}
                            onClick={() => setSelectedSlot(slot)}
                          >
                            {time}
                            {slot.is_remote && <span className={styles.remoteIcon}>📹</span>}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* Step 4: Confirm Booking */}
        {selectedSlot && (
          <section className={styles.card}>
            <h2>4. Confirm Your Booking</h2>

            <div className={styles.summary}>
              <div className={styles.summaryItem}>
                <span className={styles.label}>Appointment:</span>
                <span>{appointmentTypes.find(t => t.id === selectedType)?.name}</span>
              </div>
              <div className={styles.summaryItem}>
                <span className={styles.label}>Clinician:</span>
                <span>{clinicians.find(c => c.id === selectedClinician)?.title}</span>
              </div>
              <div className={styles.summaryItem}>
                <span className={styles.label}>Date & Time:</span>
                <span>{formatDateTime(selectedSlot.start)}</span>
              </div>
              {selectedSlot.location && (
                <div className={styles.summaryItem}>
                  <span className={styles.label}>Location:</span>
                  <span>{selectedSlot.location}</span>
                </div>
              )}
            </div>

            {selectedSlot.is_remote && (
              <div className={styles.remoteOption}>
                <label className={styles.checkboxLabel}>
                  <input
                    type="checkbox"
                    checked={isRemote}
                    onChange={e => setIsRemote(e.target.checked)}
                  />
                  I would prefer a video consultation
                </label>
              </div>
            )}

            <div className={styles.formGroup}>
              <label htmlFor="notes">Notes for the clinician (optional)</label>
              <textarea
                id="notes"
                value={patientNotes}
                onChange={e => setPatientNotes(e.target.value)}
                placeholder="Any information you'd like the clinician to know before your appointment..."
                maxLength={2000}
                rows={3}
              />
            </div>

            <button
              onClick={handleBookAppointment}
              disabled={submitting}
              className={styles.bookButton}
            >
              {submitting ? 'Booking...' : 'Confirm Booking'}
            </button>
          </section>
        )}
      </div>
    </main>
  );
}

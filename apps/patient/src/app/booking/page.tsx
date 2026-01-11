'use client';

import { useEffect, useState, useMemo } from 'react';
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
  tier?: string;
}

interface TriageCaseInfo {
  tier: string | null;
  pathway: string | null;
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

  // Self-book eligibility and triage info
  const [selfBookCheck, setSelfBookCheck] = useState<SelfBookCheck | null>(null);
  const [triageCaseInfo, setTriageCaseInfo] = useState<TriageCaseInfo | null>(null);
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

      // Load clinicians, appointment types, and triage info in parallel
      const fetchPromises: Promise<Response>[] = [
        fetch('/api/v1/scheduling/patient/clinicians', { headers }),
        fetch('/api/v1/scheduling/patient/appointment-types', { headers }),
      ];

      // Also fetch triage case info if we have a case ID
      if (triageCaseId) {
        fetchPromises.push(
          fetch(`/api/v1/admin/cases/${triageCaseId}/eligibility`, { headers })
        );
      }

      const responses = await Promise.all(fetchPromises);
      const [cliniciansRes, typesRes, triageRes] = responses;

      if (!cliniciansRes.ok || !typesRes.ok) {
        throw new Error('Failed to load booking options');
      }

      const cliniciansData = await cliniciansRes.json();
      const typesData = await typesRes.json();

      setClinicians(cliniciansData);
      setAppointmentTypes(typesData);

      // Set triage case info if available
      if (triageRes && triageRes.ok) {
        const triageData = await triageRes.json();
        setTriageCaseInfo({
          tier: triageData.tier,
          pathway: triageData.pathway,
        });
      }

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

  // Compute availability insights for soft nudges
  const availabilityInsights = useMemo(() => {
    if (availableSlots.length === 0) return null;

    const now = new Date();
    const today = now.toDateString();
    const tomorrow = new Date(now.getTime() + 24 * 60 * 60 * 1000).toDateString();
    const thisWeekEnd = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);

    const slotsToday = availableSlots.filter(
      (s) => new Date(s.start).toDateString() === today
    );
    const slotsTomorrow = availableSlots.filter(
      (s) => new Date(s.start).toDateString() === tomorrow
    );
    const slotsThisWeek = availableSlots.filter(
      (s) => new Date(s.start) <= thisWeekEnd
    );

    // Find earliest slot
    const sortedSlots = [...availableSlots].sort(
      (a, b) => new Date(a.start).getTime() - new Date(b.start).getTime()
    );
    const earliestSlot = sortedSlots[0];
    const daysUntilEarliest = Math.ceil(
      (new Date(earliestSlot.start).getTime() - now.getTime()) / (24 * 60 * 60 * 1000)
    );

    return {
      totalSlots: availableSlots.length,
      slotsToday: slotsToday.length,
      slotsTomorrow: slotsTomorrow.length,
      slotsThisWeek: slotsThisWeek.length,
      earliestSlot,
      daysUntilEarliest,
    };
  }, [availableSlots]);

  const groupSlotsByDate = (slots: AvailableSlot[]) => {
    const groups: Record<string, AvailableSlot[]> = {};
    slots.forEach((slot) => {
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

  // Highlight "soonest" slots
  const isEarlySlot = (slot: AvailableSlot) => {
    const slotDate = new Date(slot.start);
    const threeDaysFromNow = new Date(Date.now() + 3 * 24 * 60 * 60 * 1000);
    return slotDate <= threeDaysFromNow;
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
            <div className={styles.successIcon}>✓</div>
            <h2>Appointment Booked!</h2>
            <p>
              Your appointment has been successfully scheduled. You will receive a
              confirmation email with the details.
            </p>
            <div className={styles.successDetails}>
              <p>
                <strong>What happens next:</strong>
              </p>
              <ul>
                <li>Check your email for confirmation and calendar invite</li>
                <li>You can view and manage your appointment on your dashboard</li>
                <li>We&apos;ll send you a reminder 24 hours before</li>
              </ul>
            </div>
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

  // AMBER tier - Booking restricted, clinician review required
  if (selfBookCheck && !selfBookCheck.allowed) {
    return (
      <main className={styles.main}>
        <EmergencyBanner />
        <header className={styles.header}>
          <h1>We&apos;re reviewing your assessment</h1>
          <button onClick={() => router.push('/dashboard')} className={styles.backButton}>
            Back to Dashboard
          </button>
        </header>
        <div className={styles.content}>
          <div className={styles.reviewCard}>
            <div className={styles.reviewIcon}>🔍</div>
            <p className={styles.reviewMainCopy}>
              Some aspects of your assessment mean a clinician needs to review it
              before booking an appointment.
            </p>

            <div className={styles.reassuranceBox}>
              <p>
                <strong>This doesn&apos;t mean something is &quot;wrong&quot;</strong> — it helps
                ensure your care is safe and appropriate.
              </p>
            </div>

            <div className={styles.whatHappensNext}>
              <h3>What happens next:</h3>
              <ul>
                <li>A clinician will review your information</li>
                <li>We&apos;ll contact you to arrange the next step</li>
                <li>This usually happens within 24–72 hours</li>
              </ul>
            </div>

            <div className={styles.safetyReminder}>
              <span className={styles.warningIcon}>⚠️</span>
              <p>
                If your situation worsens or you feel unsafe, please contact 999
                or attend A&amp;E.
              </p>
            </div>

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

  const slotsByDate = groupSlotsByDate(availableSlots);

  // Get clinician type description based on selected type
  const getClinicianTypeDescription = () => {
    const selectedTypeObj = appointmentTypes.find((t) => t.id === selectedType);
    const typeName = selectedTypeObj?.name?.toLowerCase() || 'clinician';

    if (typeName.includes('therapy') || typeName.includes('counselling')) {
      return "You'll meet with a qualified therapist who specialises in concerns like yours.";
    } else if (typeName.includes('psychiatr')) {
      return "You'll meet with a psychiatrist who can provide specialist assessment and support.";
    } else if (typeName.includes('assessment')) {
      return "You'll have an initial assessment with one of our qualified clinicians.";
    }
    return "You'll meet with a qualified clinician who can provide the support you need.";
  };

  return (
    <main className={styles.main}>
      <EmergencyBanner />

      <header className={styles.header}>
        <h1>Book your appointment</h1>
        <button onClick={() => router.push('/dashboard')} className={styles.backButton}>
          Back to Dashboard
        </button>
      </header>

      <div className={styles.content}>
        {/* Pathway explanation for trust */}
        <div className={styles.pathwayExplanation}>
          <p className={styles.pathwayMain}>
            Based on your assessment, this is the most appropriate starting point for your care.
          </p>
          {selectedType && (
            <p className={styles.clinicianTypeExplanation}>
              {getClinicianTypeDescription()}
              <br />
              <span className={styles.careEscalation}>
                If at any point a different level of care is needed, we&apos;ll guide you through that.
              </span>
            </p>
          )}
        </div>

        {/* Availability framing */}
        {availabilityInsights && availabilityInsights.slotsThisWeek > 0 && (
          <div className={styles.availabilityFraming}>
            <span className={styles.availabilityIcon}>📅</span>
            <span>Appointments available as soon as this week.</span>
          </div>
        )}

        {error && <div className={styles.errorBanner}>{error}</div>}

        {/* Step 1: Select Appointment Type */}
        <section className={styles.card}>
          <h2>1. Select Appointment Type</h2>
          <div className={styles.typeGrid}>
            {appointmentTypes.map((type) => (
              <button
                key={type.id}
                className={`${styles.typeCard} ${
                  selectedType === type.id ? styles.typeCardSelected : ''
                }`}
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
            <p className={styles.stepHint}>
              Any of our clinicians can help you. Choose based on availability or specialty.
            </p>
            <div className={styles.clinicianGrid}>
              {clinicians.map((clinician) => (
                <button
                  key={clinician.id}
                  className={`${styles.clinicianCard} ${
                    selectedClinician === clinician.id ? styles.clinicianCardSelected : ''
                  }`}
                  onClick={() => {
                    setSelectedClinician(clinician.id);
                    setSelectedSlot(null);
                  }}
                >
                  <h3>{clinician.title}</h3>
                  <p className={styles.specialties}>{clinician.specialties.join(', ')}</p>
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

            {/* Availability insights nudge */}
            {availabilityInsights && (
              <div className={styles.availabilityNudge}>
                {availabilityInsights.slotsThisWeek > 0 && (
                  <div className={styles.nudgeHighlight}>
                    <span className={styles.nudgeIcon}>⚡</span>
                    <span>
                      <strong>{availabilityInsights.slotsThisWeek} appointments</strong> available
                      this week
                      {availabilityInsights.slotsToday > 0 && (
                        <span className={styles.todayBadge}>
                          {availabilityInsights.slotsToday} today!
                        </span>
                      )}
                    </span>
                  </div>
                )}
                {availabilityInsights.daysUntilEarliest <= 2 && (
                  <div className={styles.earliestNudge}>
                    Earliest available:{' '}
                    <strong>
                      {availabilityInsights.daysUntilEarliest === 0
                        ? 'Today'
                        : availabilityInsights.daysUntilEarliest === 1
                        ? 'Tomorrow'
                        : `In ${availabilityInsights.daysUntilEarliest} days`}
                    </strong>
                  </div>
                )}
              </div>
            )}

            {availableSlots.length === 0 ? (
              <p className={styles.noSlots}>No available slots in the next 14 days.</p>
            ) : (
              <div className={styles.slotsContainer}>
                {Object.entries(slotsByDate).map(([date, slots]) => {
                  const hasEarlySlots = slots.some(isEarlySlot);
                  return (
                    <div
                      key={date}
                      className={`${styles.dateGroup} ${
                        hasEarlySlots ? styles.dateGroupHighlighted : ''
                      }`}
                    >
                      <h3 className={styles.dateHeader}>
                        {date}
                        {hasEarlySlots && (
                          <span className={styles.earlyBadge}>Earlier availability</span>
                        )}
                      </h3>
                      <div className={styles.slotGrid}>
                        {slots.map((slot, idx) => {
                          const time = new Date(slot.start).toLocaleTimeString('en-GB', {
                            hour: '2-digit',
                            minute: '2-digit',
                          });
                          const isEarly = isEarlySlot(slot);
                          return (
                            <button
                              key={idx}
                              className={`${styles.slotButton} ${
                                selectedSlot?.start === slot.start ? styles.slotButtonSelected : ''
                              } ${isEarly ? styles.slotButtonEarly : ''}`}
                              onClick={() => setSelectedSlot(slot)}
                            >
                              {time}
                              {slot.is_remote && <span className={styles.remoteIcon}>📹</span>}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
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
                <span>{appointmentTypes.find((t) => t.id === selectedType)?.name}</span>
              </div>
              <div className={styles.summaryItem}>
                <span className={styles.label}>Clinician:</span>
                <span>{clinicians.find((c) => c.id === selectedClinician)?.title}</span>
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
                    onChange={(e) => setIsRemote(e.target.checked)}
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
                onChange={(e) => setPatientNotes(e.target.value)}
                placeholder="Any information you'd like the clinician to know before your appointment..."
                maxLength={2000}
                rows={3}
              />
            </div>

            {/* Payment copy */}
            <div className={styles.paymentNotice}>
              <p>
                <strong>Payment is required to confirm your appointment.</strong>
              </p>
              <p className={styles.paymentReason}>
                This helps us reduce missed appointments and keep waiting times short.
              </p>
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

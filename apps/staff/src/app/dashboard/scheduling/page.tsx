'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import styles from './scheduling.module.css';

interface ClinicianProfile {
  id: string;
  user_id: string;
  title: string;
  specialties: string[];
}

interface AvailabilitySlot {
  id: string;
  clinician_id: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  is_active: boolean;
  location: string | null;
  is_remote: boolean;
}

interface Appointment {
  id: string;
  patient_id: string;
  clinician_id: string;
  scheduled_start: string;
  scheduled_end: string;
  status: string;
  booking_source: string;
  is_remote: boolean;
  location: string | null;
}

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export default function SchedulingPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [clinicians, setClinicians] = useState<ClinicianProfile[]>([]);
  const [selectedClinician, setSelectedClinician] = useState<string>('');
  const [availabilitySlots, setAvailabilitySlots] = useState<AvailabilitySlot[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);

  // Modal state for adding slots
  const [showAddSlot, setShowAddSlot] = useState(false);
  const [newSlot, setNewSlot] = useState({
    day_of_week: 0,
    start_time: '09:00',
    end_time: '17:00',
    location: '',
    is_remote: false,
  });

  const [activeTab, setActiveTab] = useState<'availability' | 'appointments'>('availability');

  const getToken = () => localStorage.getItem('access_token');

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push('/auth/login');
      return;
    }
    loadClinicians();
  }, [router]);

  const loadClinicians = async () => {
    try {
      const token = getToken();
      const res = await fetch('/api/v1/scheduling/staff/clinicians', {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) throw new Error('Failed to load clinicians');

      const data = await res.json();
      setClinicians(data);
      setLoading(false);
    } catch (err) {
      setError('Failed to load clinicians');
      setLoading(false);
    }
  };

  const loadAvailability = async (clinicianId: string) => {
    try {
      const token = getToken();
      const res = await fetch(`/api/v1/scheduling/staff/clinicians/${clinicianId}/availability`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        const data = await res.json();
        setAvailabilitySlots(data);
      }
    } catch (err) {
      console.error('Failed to load availability');
    }
  };

  const loadAppointments = async (clinicianId: string) => {
    try {
      const token = getToken();
      // Get appointments for next 7 days
      const startDate = new Date().toISOString().split('T')[0];
      const endDate = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

      const res = await fetch(
        `/api/v1/scheduling/staff/clinicians/${clinicianId}/appointments?start_date=${startDate}&end_date=${endDate}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (res.ok) {
        const data = await res.json();
        setAppointments(data);
      }
    } catch (err) {
      console.error('Failed to load appointments');
    }
  };

  useEffect(() => {
    if (selectedClinician) {
      loadAvailability(selectedClinician);
      loadAppointments(selectedClinician);
    }
  }, [selectedClinician]);

  const handleAddSlot = async () => {
    if (!selectedClinician) return;

    try {
      const token = getToken();
      const res = await fetch(`/api/v1/scheduling/staff/clinicians/${selectedClinician}/availability`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newSlot),
      });

      if (res.ok) {
        setShowAddSlot(false);
        loadAvailability(selectedClinician);
        setNewSlot({
          day_of_week: 0,
          start_time: '09:00',
          end_time: '17:00',
          location: '',
          is_remote: false,
        });
      }
    } catch (err) {
      setError('Failed to add availability slot');
    }
  };

  const handleToggleSlot = async (slotId: string, currentActive: boolean) => {
    try {
      const token = getToken();
      const res = await fetch(`/api/v1/scheduling/staff/availability/${slotId}`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ is_active: !currentActive }),
      });

      if (res.ok && selectedClinician) {
        loadAvailability(selectedClinician);
      }
    } catch (err) {
      setError('Failed to update slot');
    }
  };

  const handleUpdateAppointmentStatus = async (appointmentId: string, newStatus: string) => {
    try {
      const token = getToken();
      const res = await fetch(`/api/v1/scheduling/staff/appointments/${appointmentId}/status`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status: newStatus }),
      });

      if (res.ok && selectedClinician) {
        loadAppointments(selectedClinician);
      }
    } catch (err) {
      setError('Failed to update appointment');
    }
  };

  const formatDateTime = (isoString: string) => {
    return new Date(isoString).toLocaleString('en-GB', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'confirmed': return styles.statusConfirmed;
      case 'completed': return styles.statusCompleted;
      case 'cancelled': return styles.statusCancelled;
      case 'no_show': return styles.statusNoShow;
      default: return styles.statusScheduled;
    }
  };

  const slotsByDay = DAYS.map((day, idx) =>
    availabilitySlots.filter(s => s.day_of_week === idx)
  );

  if (loading) {
    return (
      <div className={styles.layout}>
        <aside className={styles.sidebar}>
          <div className={styles.sidebarHeader}>
            <span className={styles.logo}>AcuCare</span>
          </div>
          <nav className={styles.nav}>
            <Link href="/dashboard" className={styles.navItem}>Dashboard</Link>
            <Link href="/dashboard/triage" className={styles.navItem}>Triage Cases</Link>
            <Link href="/dashboard/scheduling" className={styles.navItemActive}>Scheduling</Link>
            <Link href="/dashboard/monitoring" className={styles.navItem}>Monitoring</Link>
          </nav>
        </aside>
        <main className={styles.main}>
          <p>Loading...</p>
        </main>
      </div>
    );
  }

  return (
    <div className={styles.layout}>
      <aside className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <span className={styles.logo}>AcuCare</span>
        </div>
        <nav className={styles.nav}>
          <Link href="/dashboard" className={styles.navItem}>Dashboard</Link>
          <Link href="/dashboard/triage" className={styles.navItem}>Triage Cases</Link>
          <Link href="/dashboard/scheduling" className={styles.navItemActive}>Scheduling</Link>
          <Link href="/dashboard/monitoring" className={styles.navItem}>Monitoring</Link>
        </nav>
      </aside>

      <main className={styles.main}>
        <header className={styles.header}>
          <h1>Scheduling</h1>
        </header>

        <div className={styles.content}>
          {error && <div className={styles.error}>{error}</div>}

          {/* Clinician Selection */}
          <div className={styles.clinicianSelect}>
            <label>Select Clinician:</label>
            <select
              value={selectedClinician}
              onChange={e => setSelectedClinician(e.target.value)}
            >
              <option value="">-- Select --</option>
              {clinicians.map(c => (
                <option key={c.id} value={c.id}>{c.title}</option>
              ))}
            </select>
          </div>

          {selectedClinician && (
            <>
              {/* Tab Navigation */}
              <div className={styles.tabs}>
                <button
                  className={activeTab === 'availability' ? styles.tabActive : styles.tab}
                  onClick={() => setActiveTab('availability')}
                >
                  Availability
                </button>
                <button
                  className={activeTab === 'appointments' ? styles.tabActive : styles.tab}
                  onClick={() => setActiveTab('appointments')}
                >
                  Appointments ({appointments.length})
                </button>
              </div>

              {/* Availability Tab */}
              {activeTab === 'availability' && (
                <div className={styles.tabContent}>
                  <div className={styles.tabHeader}>
                    <h2>Weekly Availability</h2>
                    <button
                      onClick={() => setShowAddSlot(true)}
                      className={styles.addButton}
                    >
                      + Add Slot
                    </button>
                  </div>

                  <div className={styles.availabilityGrid}>
                    {DAYS.map((day, idx) => (
                      <div key={day} className={styles.dayColumn}>
                        <h3>{day}</h3>
                        {slotsByDay[idx].length === 0 ? (
                          <p className={styles.noSlots}>No slots</p>
                        ) : (
                          slotsByDay[idx].map(slot => (
                            <div
                              key={slot.id}
                              className={`${styles.slotCard} ${!slot.is_active ? styles.slotInactive : ''}`}
                            >
                              <span className={styles.slotTime}>
                                {slot.start_time} - {slot.end_time}
                              </span>
                              {slot.is_remote && <span className={styles.remoteBadge}>Video</span>}
                              {slot.location && <span className={styles.location}>{slot.location}</span>}
                              <button
                                onClick={() => handleToggleSlot(slot.id, slot.is_active)}
                                className={slot.is_active ? styles.deactivateBtn : styles.activateBtn}
                              >
                                {slot.is_active ? 'Deactivate' : 'Activate'}
                              </button>
                            </div>
                          ))
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Appointments Tab */}
              {activeTab === 'appointments' && (
                <div className={styles.tabContent}>
                  <h2>Upcoming Appointments (Next 7 Days)</h2>

                  {appointments.length === 0 ? (
                    <p className={styles.emptyState}>No appointments scheduled.</p>
                  ) : (
                    <table className={styles.table}>
                      <thead>
                        <tr>
                          <th>Date & Time</th>
                          <th>Patient</th>
                          <th>Status</th>
                          <th>Type</th>
                          <th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {appointments.map(apt => (
                          <tr key={apt.id}>
                            <td>{formatDateTime(apt.scheduled_start)}</td>
                            <td>{apt.patient_id.substring(0, 8)}...</td>
                            <td>
                              <span className={getStatusClass(apt.status)}>
                                {apt.status}
                              </span>
                            </td>
                            <td>
                              {apt.is_remote ? 'Video' : 'In-person'}
                              {apt.booking_source === 'patient_self_book' && (
                                <span className={styles.selfBookBadge}>Self-booked</span>
                              )}
                            </td>
                            <td>
                              <select
                                value={apt.status}
                                onChange={e => handleUpdateAppointmentStatus(apt.id, e.target.value)}
                                className={styles.statusSelect}
                              >
                                <option value="scheduled">Scheduled</option>
                                <option value="confirmed">Confirmed</option>
                                <option value="checked_in">Checked In</option>
                                <option value="in_progress">In Progress</option>
                                <option value="completed">Completed</option>
                                <option value="cancelled">Cancelled</option>
                                <option value="no_show">No Show</option>
                              </select>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* Add Slot Modal */}
        {showAddSlot && (
          <div className={styles.modal}>
            <div className={styles.modalContent}>
              <h2>Add Availability Slot</h2>

              <div className={styles.formGroup}>
                <label>Day of Week</label>
                <select
                  value={newSlot.day_of_week}
                  onChange={e => setNewSlot(s => ({ ...s, day_of_week: parseInt(e.target.value) }))}
                >
                  {DAYS.map((day, idx) => (
                    <option key={idx} value={idx}>{day}</option>
                  ))}
                </select>
              </div>

              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label>Start Time</label>
                  <input
                    type="time"
                    value={newSlot.start_time}
                    onChange={e => setNewSlot(s => ({ ...s, start_time: e.target.value }))}
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>End Time</label>
                  <input
                    type="time"
                    value={newSlot.end_time}
                    onChange={e => setNewSlot(s => ({ ...s, end_time: e.target.value }))}
                  />
                </div>
              </div>

              <div className={styles.formGroup}>
                <label>Location (optional)</label>
                <input
                  type="text"
                  value={newSlot.location}
                  onChange={e => setNewSlot(s => ({ ...s, location: e.target.value }))}
                  placeholder="e.g., Room 101"
                />
              </div>

              <div className={styles.formGroup}>
                <label className={styles.checkboxLabel}>
                  <input
                    type="checkbox"
                    checked={newSlot.is_remote}
                    onChange={e => setNewSlot(s => ({ ...s, is_remote: e.target.checked }))}
                  />
                  Video consultation slot
                </label>
              </div>

              <div className={styles.modalActions}>
                <button onClick={() => setShowAddSlot(false)} className={styles.cancelButton}>
                  Cancel
                </button>
                <button onClick={handleAddSlot} className={styles.saveButton}>
                  Add Slot
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

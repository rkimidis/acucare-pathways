'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getToken, removeToken } from '@/lib/auth';
import { AppShell, EmptyState, PageHeader } from '@/ui/components';
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

interface CancellationRequest {
  id: string;
  appointment_id: string;
  patient_id: string;
  request_type: 'CANCEL' | 'RESCHEDULE';
  tier_at_request: string;
  reason: string | null;
  safety_concern_flagged: boolean;
  status: 'pending' | 'approved' | 'denied' | 'auto_approved';
  within_24h: boolean;
  requested_new_start: string | null;
  created_at: string;
  appointment?: {
    scheduled_start: string;
    clinician_name?: string;
  };
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

  const [activeTab, setActiveTab] = useState<'availability' | 'appointments' | 'requests'>('availability');

  // Cancellation requests state
  const [requests, setRequests] = useState<CancellationRequest[]>([]);
  const [requestFilter, setRequestFilter] = useState<'pending' | 'all'>('pending');
  const [approveModal, setApproveModal] = useState<CancellationRequest | null>(null);
  const [denyModal, setDenyModal] = useState<CancellationRequest | null>(null);
  const [reviewNotes, setReviewNotes] = useState('');
  const [denialReason, setDenialReason] = useState('');
  const [submitting, setSubmitting] = useState(false);

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
      // Get appointments for next 14 days
      const startDate = new Date().toISOString().split('T')[0];
      const endDate = new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

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

  const loadRequests = async () => {
    try {
      const token = getToken();
      const params = new URLSearchParams();
      if (requestFilter === 'pending') {
        params.set('status', 'pending');
      }

      const res = await fetch(`/api/v1/scheduling/staff/cancellation-requests?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        const data = await res.json();
        setRequests(data);
      }
    } catch (err) {
      console.error('Failed to load cancellation requests');
    }
  };

  const handleApproveRequest = async () => {
    if (!approveModal) return;
    setSubmitting(true);

    try {
      const token = getToken();
      const res = await fetch(`/api/v1/scheduling/staff/cancellation-requests/${approveModal.id}/approve`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ notes: reviewNotes || undefined }),
      });

      if (res.ok) {
        setApproveModal(null);
        setReviewNotes('');
        loadRequests();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to approve request');
      }
    } catch (err) {
      setError('Failed to approve request');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDenyRequest = async () => {
    if (!denyModal || !denialReason.trim()) return;
    setSubmitting(true);

    try {
      const token = getToken();
      const res = await fetch(`/api/v1/scheduling/staff/cancellation-requests/${denyModal.id}/deny`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ denial_reason: denialReason }),
      });

      if (res.ok) {
        setDenyModal(null);
        setDenialReason('');
        loadRequests();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to deny request');
      }
    } catch (err) {
      setError('Failed to deny request');
    } finally {
      setSubmitting(false);
    }
  };

  useEffect(() => {
    if (selectedClinician) {
      loadAvailability(selectedClinician);
      loadAppointments(selectedClinician);
    }
  }, [selectedClinician]);

  useEffect(() => {
    if (activeTab === 'requests') {
      loadRequests();
    }
  }, [activeTab, requestFilter]);

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

  const getTierBadgeClass = (tier: string) => {
    switch (tier.toLowerCase()) {
      case 'red': return styles.tierRed;
      case 'amber': return styles.tierAmber;
      case 'green': return styles.tierGreen;
      case 'blue': return styles.tierBlue;
      default: return '';
    }
  };

  const pendingRequestCount = requests.filter(r => r.status === 'pending').length;

  const slotsByDay = DAYS.map((day, idx) =>
    availabilitySlots.filter(s => s.day_of_week === idx)
  );

  const handleLogout = () => {
    removeToken();
    router.push('/');
  };

  return (
    <AppShell activeNav="scheduling" onSignOut={handleLogout}>
      <PageHeader
        title="Scheduling"
        breadcrumb={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Scheduling' },
        ]}
      />

      <div className={styles.content}>
        {/* Explanatory Header */}
        <div className={styles.sectionIntro}>
          <h2>Clinician availability &amp; capacity</h2>
          <p>
            Manage clinician availability and review upcoming appointments.
            <br />
            <span className={styles.introHint}>Patient booking is handled from triage cases or the patient portal.</span>
          </p>
        </div>

        {loading ? (
          <EmptyState title="Loading clinicians" variant="loading" />
        ) : (
          <>
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

            {/* Empty state before clinician selected */}
            {!selectedClinician && (
              <div className={styles.emptyStateBox}>
                <div className={styles.emptyStateIcon}>📋</div>
                <p className={styles.emptyStateText}>Select a clinician to view or manage availability</p>
              </div>
            )}

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
                  <button
                    className={activeTab === 'requests' ? styles.tabActive : styles.tab}
                    onClick={() => setActiveTab('requests')}
                  >
                    Requests
                    {pendingRequestCount > 0 && (
                      <span className={styles.badge}>{pendingRequestCount}</span>
                    )}
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
                        + Add availability
                      </button>
                    </div>

                    {availabilitySlots.length === 0 ? (
                      <div className={styles.noAvailabilityBox}>
                        <div className={styles.noAvailabilityIcon}>📅</div>
                        <h3>No availability configured</h3>
                        <p>This clinician has no available slots yet.</p>
                        <button
                          onClick={() => setShowAddSlot(true)}
                          className={styles.addButton}
                        >
                          Add availability to enable booking
                        </button>
                      </div>
                    ) : (
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
                    )}
                  </div>
                )}

                {/* Appointments Tab */}
                {activeTab === 'appointments' && (
                  <div className={styles.tabContent}>
                    <h2>Upcoming Appointments (Next 14 Days)</h2>
                    <p className={styles.tabSubtitle}>Read-only view of scheduled appointments</p>

                    {appointments.length === 0 ? (
                      <EmptyState title="No appointments scheduled" />
                    ) : (
                      <table className={styles.table}>
                        <thead>
                          <tr>
                            <th>Date &amp; Time</th>
                            <th>Patient</th>
                            <th>Type</th>
                            <th>Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {appointments.map(apt => (
                            <tr key={apt.id}>
                              <td>{formatDateTime(apt.scheduled_start)}</td>
                              <td>
                                <a
                                  href={`/dashboard/patients/${apt.patient_id}`}
                                  className={styles.patientLink}
                                >
                                  {apt.patient_id.substring(0, 8)}...
                                </a>
                              </td>
                              <td>
                                {apt.is_remote ? 'Video' : 'In-person'}
                                {apt.booking_source === 'patient_self_book' && (
                                  <span className={styles.selfBookBadge}>Self-booked</span>
                                )}
                              </td>
                              <td>
                                <span className={getStatusClass(apt.status)}>
                                  {apt.status}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                )}

                {/* Requests Tab */}
                {activeTab === 'requests' && (
                  <div className={styles.tabContent}>
                    <div className={styles.tabHeader}>
                      <h2>Cancellation & Reschedule Requests</h2>
                      <select
                        value={requestFilter}
                        onChange={e => setRequestFilter(e.target.value as 'pending' | 'all')}
                        className={styles.filterSelect}
                      >
                        <option value="pending">Pending Only</option>
                        <option value="all">All Requests</option>
                      </select>
                    </div>

                    {requests.length === 0 ? (
                      <EmptyState title={requestFilter === 'pending' ? 'No pending requests' : 'No requests found'} />
                    ) : (
                      <div className={styles.requestsList}>
                        {requests.map(req => (
                          <div
                            key={req.id}
                            className={`${styles.requestCard} ${req.safety_concern_flagged ? styles.safetyFlagged : ''}`}
                          >
                            {req.safety_concern_flagged && (
                              <div className={styles.safetyBanner}>
                                ⚠ Safety concern flagged - prioritise review
                              </div>
                            )}

                            <div className={styles.requestHeader}>
                              <span className={styles.requestType}>
                                {req.request_type === 'CANCEL' ? 'Cancellation' : 'Reschedule'}
                              </span>
                              <span className={`${styles.tierBadge} ${getTierBadgeClass(req.tier_at_request)}`}>
                                {req.tier_at_request}
                              </span>
                              {req.status !== 'pending' && (
                                <span className={`${styles.statusBadge} ${styles[`status${req.status.charAt(0).toUpperCase() + req.status.slice(1)}`]}`}>
                                  {req.status}
                                </span>
                              )}
                            </div>

                            <div className={styles.requestDetails}>
                              <p><strong>Patient:</strong> {req.patient_id.substring(0, 8)}...</p>
                              {req.appointment?.scheduled_start && (
                                <p><strong>Appointment:</strong> {formatDateTime(req.appointment.scheduled_start)}</p>
                              )}
                              <p><strong>Submitted:</strong> {formatDateTime(req.created_at)}</p>
                              {req.within_24h && (
                                <p className={styles.urgentNote}>⏰ Within 24h of appointment</p>
                              )}
                              {req.request_type === 'RESCHEDULE' && req.requested_new_start && (
                                <p><strong>Requested new time:</strong> {formatDateTime(req.requested_new_start)}</p>
                              )}
                            </div>

                            {req.reason && (
                              <div className={styles.reasonBox}>
                                <strong>Reason:</strong> {req.reason}
                              </div>
                            )}

                            {req.status === 'pending' && (
                              <div className={styles.requestActions}>
                                <button
                                  onClick={() => setApproveModal(req)}
                                  className={styles.approveButton}
                                >
                                  Approve
                                </button>
                                <button
                                  onClick={() => setDenyModal(req)}
                                  className={styles.denyButton}
                                >
                                  Deny
                                </button>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </>
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

      {/* Approve Request Modal */}
      {approveModal && (
        <div className={styles.modal}>
          <div className={styles.modalContent}>
            <h2>Approve {approveModal.request_type === 'CANCEL' ? 'Cancellation' : 'Reschedule'} Request</h2>

            <div className={styles.requestSummary}>
              <p><strong>Patient:</strong> {approveModal.patient_id.substring(0, 8)}...</p>
              <p><strong>Type:</strong> {approveModal.request_type}</p>
              {approveModal.reason && (
                <p><strong>Reason:</strong> {approveModal.reason}</p>
              )}
            </div>

            <div className={styles.formGroup}>
              <label>Review Notes (optional)</label>
              <textarea
                value={reviewNotes}
                onChange={e => setReviewNotes(e.target.value)}
                placeholder="Add any notes about this decision..."
                rows={3}
              />
            </div>

            <div className={styles.modalActions}>
              <button
                onClick={() => {
                  setApproveModal(null);
                  setReviewNotes('');
                }}
                className={styles.cancelButton}
                disabled={submitting}
              >
                Cancel
              </button>
              <button
                onClick={handleApproveRequest}
                className={styles.saveButton}
                disabled={submitting}
              >
                {submitting ? 'Approving...' : 'Approve Request'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Deny Request Modal */}
      {denyModal && (
        <div className={styles.modal}>
          <div className={styles.modalContent}>
            <h2>Deny {denyModal.request_type === 'CANCEL' ? 'Cancellation' : 'Reschedule'} Request</h2>

            <div className={styles.requestSummary}>
              <p><strong>Patient:</strong> {denyModal.patient_id.substring(0, 8)}...</p>
              <p><strong>Type:</strong> {denyModal.request_type}</p>
              {denyModal.reason && (
                <p><strong>Reason given:</strong> {denyModal.reason}</p>
              )}
            </div>

            <div className={styles.formGroup}>
              <label>Denial Reason (required)</label>
              <textarea
                value={denialReason}
                onChange={e => setDenialReason(e.target.value)}
                placeholder="Explain why this request is being denied..."
                rows={3}
                required
              />
              {denialReason.trim() === '' && (
                <p className={styles.fieldHint}>A reason is required to deny a request</p>
              )}
            </div>

            <div className={styles.modalActions}>
              <button
                onClick={() => {
                  setDenyModal(null);
                  setDenialReason('');
                }}
                className={styles.cancelButton}
                disabled={submitting}
              >
                Cancel
              </button>
              <button
                onClick={handleDenyRequest}
                className={styles.denyButtonModal}
                disabled={submitting || !denialReason.trim()}
              >
                {submitting ? 'Denying...' : 'Deny Request'}
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}

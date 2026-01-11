'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import styles from './incidents.module.css';

interface Incident {
  id: string;
  reference_number: string;
  title: string;
  description: string;
  category: string;
  severity: string;
  status: string;
  triage_case_id: string | null;
  patient_id: string | null;
  reported_by: string;
  reported_at: string;
  reviewer_id: string | null;
  review_started_at: string | null;
  review_notes: string | null;
  closed_by: string | null;
  closed_at: string | null;
  closure_reason: string | null;
  lessons_learned: string | null;
  preventive_actions: string | null;
  reportable_to_cqc: boolean;
  cqc_reported_at: string | null;
}

interface IncidentCounts {
  open: number;
  under_review: number;
  closed: number;
}

const CATEGORIES = [
  { value: 'clinical', label: 'Clinical' },
  { value: 'safeguarding', label: 'Safeguarding' },
  { value: 'medication', label: 'Medication' },
  { value: 'communication', label: 'Communication' },
  { value: 'access', label: 'Access' },
  { value: 'information_governance', label: 'Information Governance' },
  { value: 'other', label: 'Other' },
];

const SEVERITIES = [
  { value: 'low', label: 'Low', color: '#64748b' },
  { value: 'medium', label: 'Medium', color: '#f59e0b' },
  { value: 'high', label: 'High', color: '#f97316' },
  { value: 'critical', label: 'Critical', color: '#dc2626' },
];

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [counts, setCounts] = useState<IncidentCounts>({ open: 0, under_review: 0, closed: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState<string>('open');
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);

  // Form state for creating incident
  const [newIncident, setNewIncident] = useState({
    title: '',
    description: '',
    category: 'other',
    severity: 'medium',
    immediate_actions_taken: '',
  });

  // Form state for closing incident
  const [closeForm, setCloseForm] = useState({
    closure_reason: '',
    lessons_learned: '',
    preventive_actions: '',
  });

  useEffect(() => {
    loadIncidents();
    loadCounts();
  }, [statusFilter, severityFilter, categoryFilter]);

  const loadIncidents = async () => {
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.append('status_filter', statusFilter);
      if (severityFilter) params.append('severity', severityFilter);
      if (categoryFilter) params.append('category', categoryFilter);

      const response = await fetch(`/api/v1/incidents?${params}`);
      if (!response.ok) throw new Error('Failed to load incidents');
      const data = await response.json();
      setIncidents(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const loadCounts = async () => {
    try {
      const response = await fetch('/api/v1/incidents/counts');
      if (response.ok) {
        const data = await response.json();
        setCounts(data);
      }
    } catch (err) {
      console.error('Failed to load counts:', err);
    }
  };

  const handleCreateIncident = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await fetch('/api/v1/incidents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newIncident),
      });

      if (!response.ok) throw new Error('Failed to create incident');

      setShowCreateModal(false);
      setNewIncident({
        title: '',
        description: '',
        category: 'other',
        severity: 'medium',
        immediate_actions_taken: '',
      });
      loadIncidents();
      loadCounts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  const handleStartReview = async (incidentId: string) => {
    try {
      const response = await fetch(`/api/v1/incidents/${incidentId}/start-review`, {
        method: 'POST',
      });

      if (!response.ok) throw new Error('Failed to start review');

      loadIncidents();
      loadCounts();
      setShowDetailModal(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  const handleCloseIncident = async (incidentId: string) => {
    try {
      const response = await fetch(`/api/v1/incidents/${incidentId}/close`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(closeForm),
      });

      if (!response.ok) throw new Error('Failed to close incident');

      setShowDetailModal(false);
      setCloseForm({ closure_reason: '', lessons_learned: '', preventive_actions: '' });
      loadIncidents();
      loadCounts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  const handleMarkCQCReportable = async (incidentId: string) => {
    try {
      const response = await fetch(`/api/v1/incidents/${incidentId}/mark-cqc-reportable`, {
        method: 'POST',
      });

      if (!response.ok) throw new Error('Failed to mark CQC reportable');

      loadIncidents();
      if (selectedIncident) {
        setSelectedIncident({ ...selectedIncident, reportable_to_cqc: true });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  const getSeverityColor = (severity: string) => {
    const sev = SEVERITIES.find(s => s.value === severity);
    return sev?.color || '#64748b';
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className={styles.layout}>
      <aside className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <span className={styles.logo}>AcuCare</span>
        </div>
        <nav className={styles.nav}>
          <Link href="/dashboard" className={styles.navItem}>Dashboard</Link>
          <Link href="/dashboard/queue" className={styles.navItem}>Triage Queue</Link>
          <Link href="/dashboard/scheduling" className={styles.navItem}>Scheduling</Link>
          <Link href="/dashboard/monitoring" className={styles.navItem}>Monitoring</Link>
          <Link href="/dashboard/incidents" className={styles.navItemActive}>Incidents</Link>
          <Link href="/dashboard/reporting" className={styles.navItem}>Reporting</Link>
          <Link href="/dashboard/evidence" className={styles.navItem}>Evidence Export</Link>
          <Link href="/dashboard/change-control" className={styles.navItem}>Change Control</Link>
        </nav>
      </aside>

      <main className={styles.main}>
        <header className={styles.header}>
          <h1>Incident Management</h1>
          <button
            className={styles.createButton}
            onClick={() => setShowCreateModal(true)}
          >
            Report Incident
          </button>
        </header>

        {error && <div className={styles.error}>{error}</div>}

        <div className={styles.content}>
          {/* Status Summary Cards */}
          <div className={styles.statusSummary}>
            <div
              className={`${styles.statusCard} ${styles.openCard} ${statusFilter === 'open' ? styles.selected : ''}`}
              onClick={() => setStatusFilter('open')}
            >
              <span className={styles.count}>{counts.open}</span>
              <span className={styles.label}>Open</span>
            </div>
            <div
              className={`${styles.statusCard} ${styles.reviewCard} ${statusFilter === 'under_review' ? styles.selected : ''}`}
              onClick={() => setStatusFilter('under_review')}
            >
              <span className={styles.count}>{counts.under_review}</span>
              <span className={styles.label}>Under Review</span>
            </div>
            <div
              className={`${styles.statusCard} ${styles.closedCard} ${statusFilter === 'closed' ? styles.selected : ''}`}
              onClick={() => setStatusFilter('closed')}
            >
              <span className={styles.count}>{counts.closed}</span>
              <span className={styles.label}>Closed</span>
            </div>
          </div>

          {/* Filters */}
          <div className={styles.filters}>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
            >
              <option value="">All Severities</option>
              {SEVERITIES.map(s => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
            >
              <option value="">All Categories</option>
              {CATEGORIES.map(c => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
          </div>

          {/* Incidents List */}
          <div className={styles.incidentsList}>
            {loading ? (
              <p className={styles.loading}>Loading incidents...</p>
            ) : incidents.length === 0 ? (
              <p className={styles.emptyState}>No incidents found</p>
            ) : (
              <div className={styles.incidents}>
                {incidents.map((incident) => (
                  <div
                    key={incident.id}
                    className={styles.incidentCard}
                    onClick={() => {
                      setSelectedIncident(incident);
                      setShowDetailModal(true);
                    }}
                  >
                    <div className={styles.incidentHeader}>
                      <span className={styles.reference}>{incident.reference_number}</span>
                      <span
                        className={styles.severityBadge}
                        style={{ backgroundColor: getSeverityColor(incident.severity) }}
                      >
                        {incident.severity.toUpperCase()}
                      </span>
                      {incident.reportable_to_cqc && (
                        <span className={styles.cqcBadge}>CQC</span>
                      )}
                    </div>
                    <h3 className={styles.incidentTitle}>{incident.title}</h3>
                    <p className={styles.incidentDescription}>
                      {incident.description.substring(0, 150)}...
                    </p>
                    <div className={styles.incidentMeta}>
                      <span className={styles.category}>{incident.category}</span>
                      <span className={styles.date}>{formatDate(incident.reported_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Create Incident Modal */}
        {showCreateModal && (
          <div className={styles.modal}>
            <div className={styles.modalContent}>
              <h2>Report New Incident</h2>
              <form onSubmit={handleCreateIncident}>
                <div className={styles.formGroup}>
                  <label>Title</label>
                  <input
                    type="text"
                    value={newIncident.title}
                    onChange={(e) => setNewIncident({ ...newIncident, title: e.target.value })}
                    required
                    minLength={5}
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>Description</label>
                  <textarea
                    value={newIncident.description}
                    onChange={(e) => setNewIncident({ ...newIncident, description: e.target.value })}
                    required
                    minLength={10}
                    rows={4}
                  />
                </div>
                <div className={styles.formRow}>
                  <div className={styles.formGroup}>
                    <label>Category</label>
                    <select
                      value={newIncident.category}
                      onChange={(e) => setNewIncident({ ...newIncident, category: e.target.value })}
                    >
                      {CATEGORIES.map(c => (
                        <option key={c.value} value={c.value}>{c.label}</option>
                      ))}
                    </select>
                  </div>
                  <div className={styles.formGroup}>
                    <label>Severity</label>
                    <select
                      value={newIncident.severity}
                      onChange={(e) => setNewIncident({ ...newIncident, severity: e.target.value })}
                    >
                      {SEVERITIES.map(s => (
                        <option key={s.value} value={s.value}>{s.label}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className={styles.formGroup}>
                  <label>Immediate Actions Taken</label>
                  <textarea
                    value={newIncident.immediate_actions_taken}
                    onChange={(e) => setNewIncident({ ...newIncident, immediate_actions_taken: e.target.value })}
                    rows={3}
                  />
                </div>
                <div className={styles.modalActions}>
                  <button type="button" className={styles.cancelButton} onClick={() => setShowCreateModal(false)}>
                    Cancel
                  </button>
                  <button type="submit" className={styles.submitButton}>
                    Report Incident
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Incident Detail Modal */}
        {showDetailModal && selectedIncident && (
          <div className={styles.modal}>
            <div className={styles.modalContentLarge}>
              <div className={styles.detailHeader}>
                <div>
                  <span className={styles.reference}>{selectedIncident.reference_number}</span>
                  <h2>{selectedIncident.title}</h2>
                </div>
                <button className={styles.closeButton} onClick={() => setShowDetailModal(false)}>
                  &times;
                </button>
              </div>

              <div className={styles.detailBadges}>
                <span
                  className={styles.severityBadge}
                  style={{ backgroundColor: getSeverityColor(selectedIncident.severity) }}
                >
                  {selectedIncident.severity.toUpperCase()}
                </span>
                <span className={styles.statusBadge}>{selectedIncident.status.replace('_', ' ').toUpperCase()}</span>
                <span className={styles.categoryBadge}>{selectedIncident.category}</span>
                {selectedIncident.reportable_to_cqc && (
                  <span className={styles.cqcBadge}>CQC Reportable</span>
                )}
              </div>

              <div className={styles.detailSection}>
                <h3>Description</h3>
                <p>{selectedIncident.description}</p>
              </div>

              {selectedIncident.immediate_actions_taken && (
                <div className={styles.detailSection}>
                  <h3>Immediate Actions Taken</h3>
                  <p>{selectedIncident.immediate_actions_taken}</p>
                </div>
              )}

              <div className={styles.detailSection}>
                <h3>Timeline</h3>
                <div className={styles.timeline}>
                  <div className={styles.timelineItem}>
                    <span className={styles.timelineLabel}>Reported:</span>
                    <span>{formatDate(selectedIncident.reported_at)}</span>
                  </div>
                  {selectedIncident.review_started_at && (
                    <div className={styles.timelineItem}>
                      <span className={styles.timelineLabel}>Review Started:</span>
                      <span>{formatDate(selectedIncident.review_started_at)}</span>
                    </div>
                  )}
                  {selectedIncident.closed_at && (
                    <div className={styles.timelineItem}>
                      <span className={styles.timelineLabel}>Closed:</span>
                      <span>{formatDate(selectedIncident.closed_at)}</span>
                    </div>
                  )}
                </div>
              </div>

              {selectedIncident.review_notes && (
                <div className={styles.detailSection}>
                  <h3>Review Notes</h3>
                  <pre className={styles.reviewNotes}>{selectedIncident.review_notes}</pre>
                </div>
              )}

              {selectedIncident.closure_reason && (
                <div className={styles.detailSection}>
                  <h3>Closure Details</h3>
                  <p><strong>Reason:</strong> {selectedIncident.closure_reason}</p>
                  {selectedIncident.lessons_learned && (
                    <p><strong>Lessons Learned:</strong> {selectedIncident.lessons_learned}</p>
                  )}
                  {selectedIncident.preventive_actions && (
                    <p><strong>Preventive Actions:</strong> {selectedIncident.preventive_actions}</p>
                  )}
                </div>
              )}

              {/* Actions based on status */}
              <div className={styles.detailActions}>
                {selectedIncident.status === 'open' && (
                  <>
                    <button
                      className={styles.primaryButton}
                      onClick={() => handleStartReview(selectedIncident.id)}
                    >
                      Start Review
                    </button>
                    {!selectedIncident.reportable_to_cqc && (
                      <button
                        className={styles.warningButton}
                        onClick={() => handleMarkCQCReportable(selectedIncident.id)}
                      >
                        Mark CQC Reportable
                      </button>
                    )}
                  </>
                )}

                {selectedIncident.status === 'under_review' && (
                  <div className={styles.closeForm}>
                    <h3>Close Incident</h3>
                    <div className={styles.formGroup}>
                      <label>Closure Reason (required)</label>
                      <textarea
                        value={closeForm.closure_reason}
                        onChange={(e) => setCloseForm({ ...closeForm, closure_reason: e.target.value })}
                        required
                        minLength={10}
                        rows={3}
                      />
                    </div>
                    <div className={styles.formGroup}>
                      <label>Lessons Learned</label>
                      <textarea
                        value={closeForm.lessons_learned}
                        onChange={(e) => setCloseForm({ ...closeForm, lessons_learned: e.target.value })}
                        rows={2}
                      />
                    </div>
                    <div className={styles.formGroup}>
                      <label>Preventive Actions</label>
                      <textarea
                        value={closeForm.preventive_actions}
                        onChange={(e) => setCloseForm({ ...closeForm, preventive_actions: e.target.value })}
                        rows={2}
                      />
                    </div>
                    <button
                      className={styles.successButton}
                      onClick={() => handleCloseIncident(selectedIncident.id)}
                      disabled={closeForm.closure_reason.length < 10}
                    >
                      Close Incident
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

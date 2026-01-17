'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { getToken } from '@/lib/auth';
import styles from './monitoring.module.css';

interface AlertCounts {
  critical: number;
  high: number;
  medium: number;
  low: number;
  total: number;
}

interface MonitoringAlert {
  id: string;
  patient_id: string;
  triage_case_id: string;
  checkin_id: string | null;
  alert_type: string;
  severity: string;
  title: string;
  description: string;
  phq2_score: number | null;
  gad2_score: number | null;
  is_active: boolean;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  resolved_at: string | null;
  resolution_notes: string | null;
  action_taken: string | null;
  escalated_to_amber: boolean;
  created_at: string;
}

export default function MonitoringPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [alertCounts, setAlertCounts] = useState<AlertCounts | null>(null);
  const [alerts, setAlerts] = useState<MonitoringAlert[]>([]);
  const [selectedSeverity, setSelectedSeverity] = useState<string | null>(null);

  // Resolve modal
  const [resolveAlert, setResolveAlert] = useState<MonitoringAlert | null>(null);
  const [resolveNotes, setResolveNotes] = useState('');
  const [resolveAction, setResolveAction] = useState('');


  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push('/auth/login');
      return;
    }
    loadData();
  }, [router]);

  const loadData = async () => {
    await Promise.all([loadAlertCounts(), loadAlerts()]);
    setLoading(false);
  };

  const loadAlertCounts = async () => {
    try {
      const token = getToken();
      const res = await fetch('/api/v1/monitoring/staff/alerts/counts', {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        const data = await res.json();
        setAlertCounts(data);
      }
    } catch (err) {
      console.error('Failed to load alert counts');
    }
  };

  const loadAlerts = async (severity?: string) => {
    try {
      const token = getToken();
      const url = severity
        ? `/api/v1/monitoring/staff/alerts?severity=${severity}`
        : '/api/v1/monitoring/staff/alerts';

      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        const data = await res.json();
        setAlerts(data);
      }
    } catch (err) {
      setError('Failed to load alerts');
    }
  };

  useEffect(() => {
    if (!loading) {
      loadAlerts(selectedSeverity || undefined);
    }
  }, [selectedSeverity]);

  const handleAcknowledge = async (alertId: string) => {
    try {
      const token = getToken();
      const res = await fetch(`/api/v1/monitoring/staff/alerts/${alertId}/acknowledge`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        loadAlerts(selectedSeverity || undefined);
        loadAlertCounts();
      }
    } catch (err) {
      setError('Failed to acknowledge alert');
    }
  };

  const handleResolve = async () => {
    if (!resolveAlert) return;

    try {
      const token = getToken();
      const res = await fetch(`/api/v1/monitoring/staff/alerts/${resolveAlert.id}/resolve`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          notes: resolveNotes || null,
          action: resolveAction || null,
        }),
      });

      if (res.ok) {
        setResolveAlert(null);
        setResolveNotes('');
        setResolveAction('');
        loadAlerts(selectedSeverity || undefined);
        loadAlertCounts();
      }
    } catch (err) {
      setError('Failed to resolve alert');
    }
  };

  const getSeverityClass = (severity: string) => {
    switch (severity) {
      case 'critical': return styles.severityCritical;
      case 'high': return styles.severityHigh;
      case 'medium': return styles.severityMedium;
      case 'low': return styles.severityLow;
      default: return '';
    }
  };

  const getAlertTypeIcon = (alertType: string) => {
    switch (alertType) {
      case 'suicidal_ideation': return '!!!';
      case 'self_harm': return '!!';
      case 'phq2_elevated': return 'PHQ';
      case 'gad2_elevated': return 'GAD';
      case 'patient_request': return 'REQ';
      case 'no_response': return 'NR';
      default: return '?';
    }
  };

  const formatTime = (isoString: string) => {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);

    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString('en-GB');
  };

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
            <Link href="/dashboard/scheduling" className={styles.navItem}>Scheduling</Link>
            <Link href="/dashboard/monitoring" className={styles.navItemActive}>Monitoring</Link>
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
          <Link href="/dashboard/scheduling" className={styles.navItem}>Scheduling</Link>
          <Link href="/dashboard/monitoring" className={styles.navItemActive}>Monitoring</Link>
        </nav>
      </aside>

      <main className={styles.main}>
        <header className={styles.header}>
          <h1>Monitoring Alerts</h1>
        </header>

        <div className={styles.content}>
          {error && <div className={styles.error}>{error}</div>}

          {/* Alert Summary */}
          {alertCounts && (
            <div className={styles.alertSummary}>
              <button
                className={`${styles.summaryCard} ${styles.criticalCard} ${selectedSeverity === 'critical' ? styles.selected : ''}`}
                onClick={() => setSelectedSeverity(selectedSeverity === 'critical' ? null : 'critical')}
              >
                <span className={styles.count}>{alertCounts.critical}</span>
                <span className={styles.label}>Critical</span>
              </button>
              <button
                className={`${styles.summaryCard} ${styles.highCard} ${selectedSeverity === 'high' ? styles.selected : ''}`}
                onClick={() => setSelectedSeverity(selectedSeverity === 'high' ? null : 'high')}
              >
                <span className={styles.count}>{alertCounts.high}</span>
                <span className={styles.label}>High</span>
              </button>
              <button
                className={`${styles.summaryCard} ${styles.mediumCard} ${selectedSeverity === 'medium' ? styles.selected : ''}`}
                onClick={() => setSelectedSeverity(selectedSeverity === 'medium' ? null : 'medium')}
              >
                <span className={styles.count}>{alertCounts.medium}</span>
                <span className={styles.label}>Medium</span>
              </button>
              <button
                className={`${styles.summaryCard} ${styles.lowCard} ${selectedSeverity === 'low' ? styles.selected : ''}`}
                onClick={() => setSelectedSeverity(selectedSeverity === 'low' ? null : 'low')}
              >
                <span className={styles.count}>{alertCounts.low}</span>
                <span className={styles.label}>Low</span>
              </button>
            </div>
          )}

          {/* Alerts List */}
          <div className={styles.alertsList}>
            <h2>
              {selectedSeverity ? `${selectedSeverity.charAt(0).toUpperCase() + selectedSeverity.slice(1)} Alerts` : 'All Alerts'}
              <span className={styles.alertCount}>({alerts.length})</span>
            </h2>

            {alerts.length === 0 ? (
              <div className={styles.emptyState}>
                <p>No active alerts</p>
              </div>
            ) : (
              <div className={styles.alerts}>
                {alerts.map(alert => (
                  <div
                    key={alert.id}
                    className={`${styles.alertCard} ${getSeverityClass(alert.severity)}`}
                  >
                    <div className={styles.alertHeader}>
                      <span className={styles.alertType}>{getAlertTypeIcon(alert.alert_type)}</span>
                      <span className={styles.alertTitle}>{alert.title}</span>
                      <span className={styles.alertTime}>{formatTime(alert.created_at)}</span>
                    </div>

                    <p className={styles.alertDescription}>{alert.description}</p>

                    {(alert.phq2_score !== null || alert.gad2_score !== null) && (
                      <div className={styles.scores}>
                        {alert.phq2_score !== null && (
                          <span className={styles.score}>PHQ-2: {alert.phq2_score}</span>
                        )}
                        {alert.gad2_score !== null && (
                          <span className={styles.score}>GAD-2: {alert.gad2_score}</span>
                        )}
                      </div>
                    )}

                    {alert.escalated_to_amber && (
                      <div className={styles.escalatedBadge}>
                        Escalated to AMBER
                      </div>
                    )}

                    <div className={styles.alertActions}>
                      <Link
                        href={`/dashboard/triage/${alert.triage_case_id}`}
                        className={styles.viewCaseLink}
                      >
                        View Case
                      </Link>

                      {!alert.acknowledged_at && (
                        <button
                          onClick={() => handleAcknowledge(alert.id)}
                          className={styles.acknowledgeButton}
                        >
                          Acknowledge
                        </button>
                      )}

                      {alert.acknowledged_at && !alert.resolved_at && (
                        <span className={styles.acknowledgedLabel}>
                          Acknowledged
                        </span>
                      )}

                      {alert.is_active && (
                        <button
                          onClick={() => setResolveAlert(alert)}
                          className={styles.resolveButton}
                        >
                          Resolve
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Resolve Modal */}
        {resolveAlert && (
          <div className={styles.modal}>
            <div className={styles.modalContent}>
              <h2>Resolve Alert</h2>
              <p className={styles.modalDescription}>{resolveAlert.title}</p>

              <div className={styles.formGroup}>
                <label>Action Taken</label>
                <select
                  value={resolveAction}
                  onChange={e => setResolveAction(e.target.value)}
                >
                  <option value="">Select action...</option>
                  <option value="contacted_patient">Contacted Patient</option>
                  <option value="escalated_clinician">Escalated to Clinician</option>
                  <option value="scheduled_appointment">Scheduled Appointment</option>
                  <option value="referred_crisis">Referred to Crisis Team</option>
                  <option value="no_action_needed">No Action Needed</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div className={styles.formGroup}>
                <label>Resolution Notes</label>
                <textarea
                  value={resolveNotes}
                  onChange={e => setResolveNotes(e.target.value)}
                  placeholder="Add notes about how this alert was resolved..."
                  rows={4}
                />
              </div>

              <div className={styles.modalActions}>
                <button
                  onClick={() => {
                    setResolveAlert(null);
                    setResolveNotes('');
                    setResolveAction('');
                  }}
                  className={styles.cancelButton}
                >
                  Cancel
                </button>
                <button
                  onClick={handleResolve}
                  className={styles.saveButton}
                >
                  Resolve Alert
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

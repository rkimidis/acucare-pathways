'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import styles from './case-detail.module.css';

interface Score {
  id: string;
  score_type: string;
  total_score: number;
  max_score: number;
  severity_band: string;
  metadata: Record<string, unknown>;
}

interface RiskFlag {
  id: string;
  rule_id: string;
  flag_type: string;
  severity: string;
  explanation: string | null;
}

interface DraftDisposition {
  id: string;
  tier: string;
  pathway: string;
  rules_fired: string[];
  explanations: string[];
  ruleset_version: string;
  is_applied: boolean;
}

interface FinalDisposition {
  id: string;
  tier: string;
  pathway: string;
  is_override: boolean;
  original_tier: string | null;
  original_pathway: string | null;
  rationale: string | null;
  finalized_at: string;
}

interface QuestionnaireResponse {
  id: string;
  answers: Record<string, unknown>;
  submitted_at: string | null;
}

interface CaseSummary {
  case: {
    id: string;
    tier: string | null;
    pathway: string | null;
    status: string | null;
    clinician_review_required: boolean;
    self_book_allowed: boolean;
    sla_deadline: string | null;
    sla_remaining_minutes: number | null;
    sla_status: string;
    ruleset_version: string | null;
    tier_explanation: Record<string, unknown> | null;
    triaged_at: string | null;
    reviewed_at: string | null;
  };
  patient: {
    id: string;
    first_name: string | null;
    last_name: string | null;
    date_of_birth: string | null;
    phone?: string | null;
  } | null;
  scores: Score[];
  risk_flags: RiskFlag[];
  draft_disposition: DraftDisposition | null;
  final_disposition: FinalDisposition | null;
  questionnaire_responses: QuestionnaireResponse[];
}

interface QueueItem {
  id: string;
  tier: string | null;
}

type TabType = 'overview' | 'scores' | 'answers' | 'disposition';

export default function CaseDetailPage() {
  const router = useRouter();
  const params = useParams();
  const caseId = params.id as string;

  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<CaseSummary | null>(null);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [isDisposing, setIsDisposing] = useState(false);
  const [dispositionMode, setDispositionMode] = useState<'confirm' | 'override'>('confirm');
  const [overrideForm, setOverrideForm] = useState({
    tier: '',
    pathway: '',
    rationale: '',
    clinical_notes: '',
  });
  const [dispositionError, setDispositionError] = useState('');
  const [showWhyPathway, setShowWhyPathway] = useState(false);
  const [queueCases, setQueueCases] = useState<QueueItem[]>([]);
  const [showKeyboardHelp, setShowKeyboardHelp] = useState(false);

  // Load queue for navigation
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    fetch('/api/v1/dashboard/queue', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => setQueueCases(data.items || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/auth/login');
      return;
    }

    fetchCaseSummary(token);
  }, [caseId, router]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in an input
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        e.target instanceof HTMLSelectElement
      ) {
        return;
      }

      const currentIndex = queueCases.findIndex((c) => c.id === caseId);

      switch (e.key.toLowerCase()) {
        case 'j':
        case 'arrowdown':
          // Next case
          if (currentIndex < queueCases.length - 1) {
            e.preventDefault();
            router.push(`/dashboard/triage/${queueCases[currentIndex + 1].id}`);
          }
          break;
        case 'k':
        case 'arrowup':
          // Previous case
          if (currentIndex > 0) {
            e.preventDefault();
            router.push(`/dashboard/triage/${queueCases[currentIndex - 1].id}`);
          }
          break;
        case 'b':
          // Book (for GREEN/BLUE)
          if (
            summary &&
            (summary.case.tier?.toLowerCase() === 'green' ||
              summary.case.tier?.toLowerCase() === 'blue') &&
            !summary.final_disposition
          ) {
            e.preventDefault();
            handleBookAppointment();
          }
          break;
        case 'c':
          // Call patient
          if (summary?.patient?.phone) {
            e.preventDefault();
            window.open(`tel:${summary.patient.phone}`);
          }
          break;
        case 'enter':
          // Confirm disposition
          if (summary?.draft_disposition && !summary.final_disposition && !isDisposing) {
            e.preventDefault();
            handleConfirmDisposition();
          }
          break;
        case 'escape':
          // Go back to queue
          e.preventDefault();
          router.push('/dashboard/triage');
          break;
        case '?':
          // Show keyboard help
          e.preventDefault();
          setShowKeyboardHelp((prev) => !prev);
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [caseId, queueCases, router, summary, isDisposing]);

  const fetchCaseSummary = async (token: string) => {
    try {
      setLoading(true);
      const response = await fetch(`/api/v1/dashboard/cases/${caseId}/summary`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.status === 401) {
        localStorage.removeItem('access_token');
        router.push('/auth/login');
        return;
      }

      if (!response.ok) throw new Error('Failed to fetch case');

      const data = await response.json();
      setSummary(data);

      // Pre-fill override form with current values
      if (data.draft_disposition) {
        setOverrideForm((prev) => ({
          ...prev,
          tier: data.draft_disposition.tier,
          pathway: data.draft_disposition.pathway,
        }));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load case');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmDisposition = async () => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    setIsDisposing(true);
    setDispositionError('');

    try {
      const response = await fetch(`/api/v1/dashboard/cases/${caseId}/disposition/confirm`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ clinical_notes: overrideForm.clinical_notes || null }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to confirm disposition');
      }

      // Refresh case data
      await fetchCaseSummary(token);
      setActiveTab('overview');
    } catch (err) {
      setDispositionError(err instanceof Error ? err.message : 'Failed to confirm');
    } finally {
      setIsDisposing(false);
    }
  };

  const handleOverrideDisposition = async () => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    // Validate rationale
    if (!overrideForm.rationale || overrideForm.rationale.length < 10) {
      setDispositionError('Rationale is required and must be at least 10 characters');
      return;
    }

    setIsDisposing(true);
    setDispositionError('');

    try {
      const response = await fetch(`/api/v1/dashboard/cases/${caseId}/disposition/override`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tier: overrideForm.tier,
          pathway: overrideForm.pathway,
          rationale: overrideForm.rationale,
          clinical_notes: overrideForm.clinical_notes || null,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to override disposition');
      }

      // Refresh case data
      await fetchCaseSummary(token);
      setActiveTab('overview');
    } catch (err) {
      setDispositionError(err instanceof Error ? err.message : 'Failed to override');
    } finally {
      setIsDisposing(false);
    }
  };

  const handleBookAppointment = () => {
    router.push(`/dashboard/scheduling?case_id=${caseId}`);
  };

  const handleDownloadPdf = async () => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    try {
      const response = await fetch(`/api/v1/dashboard/cases/${caseId}/note/download`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) throw new Error('Failed to download PDF');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `triage_note_${caseId.substring(0, 8)}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Failed to download PDF');
    }
  };

  const getTierBadgeClass = (tier: string | null): string => {
    switch (tier?.toLowerCase()) {
      case 'red':
        return styles.tierRed;
      case 'amber':
        return styles.tierAmber;
      case 'green':
        return styles.tierGreen;
      case 'blue':
        return styles.tierBlue;
      default:
        return styles.tierPending;
    }
  };

  const getSeverityClass = (severity: string): string => {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
        return styles.severityCritical;
      case 'HIGH':
        return styles.severityHigh;
      case 'MEDIUM':
        return styles.severityMedium;
      default:
        return styles.severityLow;
    }
  };

  const formatSlaTime = (minutes: number | null): string => {
    if (minutes === null) return '--';
    if (minutes < 0) return 'OVERDUE';

    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;

    if (hours > 24) {
      const days = Math.floor(hours / 24);
      return `${days}d ${hours % 24}h`;
    }
    if (hours > 0) {
      return `${hours}h ${mins}m`;
    }
    return `${mins}m`;
  };

  const getSlaClass = (status: string): string => {
    switch (status) {
      case 'breached':
        return styles.slaBreach;
      case 'critical':
        return styles.slaCritical;
      case 'warning':
        return styles.slaWarning;
      default:
        return styles.slaNormal;
    }
  };

  // Determine primary action based on tier
  const getPrimaryAction = () => {
    if (!summary || summary.final_disposition) return null;

    const tier = summary.case.tier?.toLowerCase();

    if (tier === 'green' || tier === 'blue') {
      return {
        label: 'Book Appointment',
        shortcut: 'B',
        action: handleBookAppointment,
        className: styles.primaryActionBook,
      };
    } else if (tier === 'amber') {
      return {
        label: 'Call Patient',
        shortcut: 'C',
        action: () => window.open(`tel:${summary.patient?.phone || ''}`),
        className: styles.primaryActionCall,
      };
    } else if (tier === 'red') {
      return {
        label: 'Escalate to Crisis',
        shortcut: 'E',
        action: () => router.push(`/dashboard/incidents/new?case_id=${caseId}&type=crisis`),
        className: styles.primaryActionEscalate,
      };
    }
    return null;
  };

  const currentIndex = queueCases.findIndex((c) => c.id === caseId);
  const hasPrevious = currentIndex > 0;
  const hasNext = currentIndex < queueCases.length - 1;

  if (loading) {
    return (
      <div className={styles.layout}>
        <main className={styles.main}>
          <p>Loading case...</p>
        </main>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className={styles.layout}>
        <main className={styles.main}>
          <p>Case not found</p>
          <Link href="/dashboard/triage">Back to Queue</Link>
        </main>
      </div>
    );
  }

  const isFinalized = !!summary.final_disposition;
  const primaryAction = getPrimaryAction();

  return (
    <div className={styles.layout}>
      <aside className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <span className={styles.logo}>AcuCare</span>
        </div>
        <nav className={styles.nav}>
          <Link href="/dashboard" className={styles.navItem}>
            Dashboard
          </Link>
          <Link href="/dashboard/triage" className={styles.navItemActive}>
            Triage Queue
          </Link>
        </nav>
      </aside>

      <main className={styles.main}>
        {/* Navigation Bar */}
        <div className={styles.navBar}>
          <Link href="/dashboard/triage" className={styles.backLink}>
            ← Back to Queue
          </Link>
          <div className={styles.caseNavigation}>
            <button
              className={styles.navButton}
              disabled={!hasPrevious}
              onClick={() =>
                hasPrevious && router.push(`/dashboard/triage/${queueCases[currentIndex - 1].id}`)
              }
              title="Previous case (K or ↑)"
            >
              ← Prev
            </button>
            <span className={styles.casePosition}>
              {currentIndex + 1} / {queueCases.length}
            </span>
            <button
              className={styles.navButton}
              disabled={!hasNext}
              onClick={() =>
                hasNext && router.push(`/dashboard/triage/${queueCases[currentIndex + 1].id}`)
              }
              title="Next case (J or ↓)"
            >
              Next →
            </button>
          </div>
          <button
            className={styles.keyboardHelpButton}
            onClick={() => setShowKeyboardHelp((prev) => !prev)}
            title="Keyboard shortcuts (?)"
          >
            ⌨️ ?
          </button>
        </div>

        {/* Keyboard Help Modal */}
        {showKeyboardHelp && (
          <div className={styles.keyboardHelp}>
            <h4>Keyboard Shortcuts</h4>
            <div className={styles.shortcutGrid}>
              <kbd>J</kbd> <span>Next case</span>
              <kbd>K</kbd> <span>Previous case</span>
              <kbd>B</kbd> <span>Book appointment (GREEN/BLUE)</span>
              <kbd>C</kbd> <span>Call patient</span>
              <kbd>Enter</kbd> <span>Confirm disposition</span>
              <kbd>Esc</kbd> <span>Back to queue</span>
              <kbd>?</kbd> <span>Toggle this help</span>
            </div>
            <button onClick={() => setShowKeyboardHelp(false)}>Close</button>
          </div>
        )}

        {error && <div className={styles.error}>{error}</div>}

        {/* ONE-GLANCE CASE HEADER */}
        <div className={styles.caseHeader}>
          <div className={styles.caseHeaderMain}>
            {/* Large Tier Badge */}
            <div className={`${styles.tierBadgeLarge} ${getTierBadgeClass(summary.case.tier)}`}>
              {summary.case.tier?.toUpperCase() || 'PENDING'}
            </div>

            {/* Patient & Case Info */}
            <div className={styles.caseInfo}>
              <h1 className={styles.patientName}>
                {summary.patient
                  ? `${summary.patient.first_name} ${summary.patient.last_name}`
                  : 'Unknown Patient'}
              </h1>
              <div className={styles.caseMetaRow}>
                <span className={styles.caseId}>Case {caseId.substring(0, 8)}</span>
                <span className={styles.pathwayBadge}>{summary.case.pathway || 'No pathway'}</span>
                {isFinalized && <span className={styles.finalizedBadge}>✓ Finalized</span>}
              </div>
            </div>

            {/* SLA Countdown */}
            <div className={`${styles.slaBox} ${getSlaClass(summary.case.sla_status)}`}>
              <span className={styles.slaLabel}>SLA</span>
              <span className={styles.slaValue}>
                {formatSlaTime(summary.case.sla_remaining_minutes)}
              </span>
            </div>
          </div>

          {/* Why This Pathway? */}
          {summary.draft_disposition && summary.draft_disposition.rules_fired.length > 0 && (
            <div className={styles.whyPathway}>
              <button
                className={styles.whyPathwayToggle}
                onClick={() => setShowWhyPathway(!showWhyPathway)}
              >
                {showWhyPathway ? '▼' : '▶'} Why this pathway?
              </button>
              {showWhyPathway && (
                <div className={styles.rulesSummary}>
                  {summary.draft_disposition.rules_fired.map((rule, idx) => (
                    <div key={rule} className={styles.ruleSummaryItem}>
                      <code>{rule}</code>
                      {summary.draft_disposition!.explanations[idx] && (
                        <span>{summary.draft_disposition!.explanations[idx]}</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Risk Flags Banner */}
          {summary.risk_flags.length > 0 && (
            <div className={styles.riskFlagsBanner}>
              {summary.risk_flags.map((flag) => (
                <span key={flag.id} className={`${styles.riskFlag} ${getSeverityClass(flag.severity)}`}>
                  {flag.flag_type}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* PRIMARY ACTION BAR */}
        {!isFinalized && (
          <div className={styles.actionBar}>
            {primaryAction && (
              <button className={primaryAction.className} onClick={primaryAction.action}>
                {primaryAction.label}
                <kbd>{primaryAction.shortcut}</kbd>
              </button>
            )}
            <button
              className={styles.confirmButton}
              onClick={handleConfirmDisposition}
              disabled={isDisposing || !summary.draft_disposition}
              title="Confirm disposition (Enter)"
            >
              {isDisposing ? 'Confirming...' : '✓ Confirm Disposition'}
              <kbd>Enter</kbd>
            </button>
            <button onClick={handleDownloadPdf} className={styles.downloadButton}>
              PDF
            </button>
          </div>
        )}

        {/* Tabs */}
        <div className={styles.tabs}>
          {(['overview', 'scores', 'answers', 'disposition'] as TabType[]).map((tab) => (
            <button
              key={tab}
              className={activeTab === tab ? styles.tabActive : styles.tab}
              onClick={() => setActiveTab(tab)}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className={styles.tabContent}>
          {activeTab === 'overview' && (
            <div className={styles.overviewGrid}>
              {/* Patient Info */}
              <section className={styles.section}>
                <h3>Patient Information</h3>
                {summary.patient ? (
                  <dl className={styles.dl}>
                    <dt>Name</dt>
                    <dd>
                      {summary.patient.first_name} {summary.patient.last_name}
                    </dd>
                    <dt>Date of Birth</dt>
                    <dd>{summary.patient.date_of_birth || 'Not recorded'}</dd>
                    {summary.patient.phone && (
                      <>
                        <dt>Phone</dt>
                        <dd>
                          <a href={`tel:${summary.patient.phone}`}>{summary.patient.phone}</a>
                        </dd>
                      </>
                    )}
                  </dl>
                ) : (
                  <p className={styles.muted}>Patient data unavailable</p>
                )}
              </section>

              {/* Clinical Scores Summary */}
              <section className={styles.section}>
                <h3>Clinical Scores</h3>
                {summary.scores.length === 0 ? (
                  <p className={styles.muted}>No scores calculated</p>
                ) : (
                  <div className={styles.scoresGrid}>
                    {summary.scores.map((score) => (
                      <div key={score.id} className={styles.scoreCard}>
                        <span className={styles.scoreType}>{score.score_type}</span>
                        <span className={styles.scoreValue}>
                          {score.total_score}/{score.max_score}
                        </span>
                        <span className={styles.scoreBand}>{score.severity_band}</span>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              {/* Final Disposition Info */}
              {summary.final_disposition && (
                <section className={styles.section}>
                  <h3>Final Disposition</h3>
                  <dl className={styles.dl}>
                    <dt>Tier</dt>
                    <dd>{summary.final_disposition.tier}</dd>
                    <dt>Pathway</dt>
                    <dd>{summary.final_disposition.pathway}</dd>
                    {summary.final_disposition.is_override && (
                      <>
                        <dt>Override</dt>
                        <dd className={styles.override}>
                          Changed from {summary.final_disposition.original_tier} →{' '}
                          {summary.final_disposition.tier}
                        </dd>
                        <dt>Rationale</dt>
                        <dd>{summary.final_disposition.rationale}</dd>
                      </>
                    )}
                    <dt>Finalized</dt>
                    <dd>{new Date(summary.final_disposition.finalized_at).toLocaleString()}</dd>
                  </dl>
                </section>
              )}
            </div>
          )}

          {activeTab === 'scores' && (
            <section className={styles.section}>
              <h3>Clinical Scores</h3>
              {summary.scores.length === 0 ? (
                <p className={styles.muted}>No scores calculated</p>
              ) : (
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Assessment</th>
                      <th>Score</th>
                      <th>Severity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.scores.map((score) => (
                      <tr key={score.id}>
                        <td>{score.score_type}</td>
                        <td>
                          {score.total_score} / {score.max_score}
                        </td>
                        <td>{score.severity_band}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
          )}

          {activeTab === 'answers' && (
            <section className={styles.section}>
              <h3>Questionnaire Responses</h3>
              {summary.questionnaire_responses.length === 0 ? (
                <p className={styles.muted}>No responses recorded</p>
              ) : (
                summary.questionnaire_responses.map((resp) => (
                  <div key={resp.id} className={styles.responseBlock}>
                    <p className={styles.responseTime}>
                      Submitted: {resp.submitted_at ? new Date(resp.submitted_at).toLocaleString() : 'Draft'}
                    </p>
                    <pre className={styles.answersJson}>{JSON.stringify(resp.answers, null, 2)}</pre>
                  </div>
                ))
              )}
            </section>
          )}

          {activeTab === 'disposition' && (
            <section className={styles.section}>
              <h3>Disposition Decision</h3>

              {isFinalized ? (
                <div className={styles.finalizedMessage}>
                  This case has already been finalized. View the final disposition in the Overview tab.
                </div>
              ) : (
                <>
                  {!summary.draft_disposition ? (
                    <div className={styles.warning}>
                      No draft disposition available. Triage must be completed first.
                    </div>
                  ) : (
                    <>
                      <div className={styles.modeSelector}>
                        <button
                          className={dispositionMode === 'confirm' ? styles.modeActive : styles.modeButton}
                          onClick={() => setDispositionMode('confirm')}
                        >
                          Confirm Draft
                        </button>
                        <button
                          className={dispositionMode === 'override' ? styles.modeActive : styles.modeButton}
                          onClick={() => setDispositionMode('override')}
                        >
                          Override
                        </button>
                      </div>

                      {dispositionError && <div className={styles.dispositionError}>{dispositionError}</div>}

                      {dispositionMode === 'confirm' ? (
                        <div className={styles.confirmSection}>
                          <p>
                            Confirm the draft disposition:
                            <strong> {summary.draft_disposition.tier}</strong> tier,
                            <strong> {summary.draft_disposition.pathway}</strong> pathway
                          </p>
                          <div className={styles.formGroup}>
                            <label>Clinical Notes (optional)</label>
                            <textarea
                              value={overrideForm.clinical_notes}
                              onChange={(e) =>
                                setOverrideForm((prev) => ({ ...prev, clinical_notes: e.target.value }))
                              }
                              rows={3}
                              placeholder="Add any additional notes..."
                            />
                          </div>
                          <button
                            onClick={handleConfirmDisposition}
                            disabled={isDisposing}
                            className={styles.confirmButtonLarge}
                          >
                            {isDisposing ? 'Confirming...' : 'Confirm Disposition'}
                          </button>
                        </div>
                      ) : (
                        <div className={styles.overrideSection}>
                          <div className={styles.overrideWarning}>
                            You are overriding the rules engine decision. A rationale is REQUIRED.
                          </div>

                          <div className={styles.formGroup}>
                            <label>New Tier *</label>
                            <select
                              value={overrideForm.tier}
                              onChange={(e) =>
                                setOverrideForm((prev) => ({ ...prev, tier: e.target.value }))
                              }
                            >
                              <option value="RED">RED - Crisis</option>
                              <option value="AMBER">AMBER - Elevated Risk</option>
                              <option value="GREEN">GREEN - Routine</option>
                              <option value="BLUE">BLUE - Low Intensity</option>
                            </select>
                          </div>

                          <div className={styles.formGroup}>
                            <label>New Pathway *</label>
                            <select
                              value={overrideForm.pathway}
                              onChange={(e) =>
                                setOverrideForm((prev) => ({ ...prev, pathway: e.target.value }))
                              }
                            >
                              <option value="CRISIS_ESCALATION">Crisis Escalation</option>
                              <option value="PSYCHIATRY_ASSESSMENT">Psychiatry Assessment</option>
                              <option value="SUBSTANCE_PATHWAY">Substance Pathway</option>
                              <option value="THERAPY_ASSESSMENT">Therapy Assessment</option>
                              <option value="TRAUMA_THERAPY_PATHWAY">Trauma Therapy Pathway</option>
                              <option value="NEURODEVELOPMENTAL_TRIAGE">Neurodevelopmental Triage</option>
                              <option value="LOW_INTENSITY_DIGITAL">Low Intensity Digital</option>
                            </select>
                          </div>

                          <div className={styles.formGroup}>
                            <label>Rationale * (min 10 characters)</label>
                            <textarea
                              value={overrideForm.rationale}
                              onChange={(e) =>
                                setOverrideForm((prev) => ({ ...prev, rationale: e.target.value }))
                              }
                              rows={4}
                              placeholder="Explain why you are overriding the rules engine decision..."
                              required
                            />
                            <span className={styles.charCount}>
                              {overrideForm.rationale.length} / 10 minimum
                            </span>
                          </div>

                          <div className={styles.formGroup}>
                            <label>Clinical Notes (optional)</label>
                            <textarea
                              value={overrideForm.clinical_notes}
                              onChange={(e) =>
                                setOverrideForm((prev) => ({ ...prev, clinical_notes: e.target.value }))
                              }
                              rows={3}
                              placeholder="Add any additional notes..."
                            />
                          </div>

                          <button
                            onClick={handleOverrideDisposition}
                            disabled={isDisposing || overrideForm.rationale.length < 10}
                            className={styles.overrideButtonLarge}
                          >
                            {isDisposing ? 'Overriding...' : 'Override Disposition'}
                          </button>
                        </div>
                      )}
                    </>
                  )}
                </>
              )}
            </section>
          )}
        </div>
      </main>
    </div>
  );
}

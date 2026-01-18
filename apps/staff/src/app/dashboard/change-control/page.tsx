'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { removeToken } from '@/lib/auth';
import { AppShell, EmptyState, PageHeader } from '@/ui/components';
import styles from './change-control.module.css';

interface RulesetApproval {
  id: string;
  ruleset_type: string;
  ruleset_version: string;
  previous_version: string | null;
  change_summary: string;
  change_rationale: string;
  content_hash: string;
  submitted_by: string;
  submitted_at: string;
  status: string;
  approved_by: string | null;
  approved_at: string | null;
  approval_notes: string | null;
  rejected_by: string | null;
  rejected_at: string | null;
  rejection_reason: string | null;
  is_active: boolean;
  activated_at: string | null;
}

interface QuestionnaireVersion {
  id: string;
  questionnaire_code: string;
  version: string;
  title: string;
  description: string | null;
  content_hash: string;
  change_summary: string | null;
  created_by: string;
  status: string;
  approved_by: string | null;
  approved_at: string | null;
  is_active: boolean;
  activated_at: string | null;
  created_at: string;
}

type TabType = 'rulesets' | 'questionnaires';

export default function ChangeControlPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<TabType>('rulesets');
  const [pendingRulesets, setPendingRulesets] = useState<RulesetApproval[]>([]);
  const [rulesetHistory, setRulesetHistory] = useState<RulesetApproval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedRuleset, setSelectedRuleset] = useState<RulesetApproval | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [approvalNotes, setApprovalNotes] = useState('');

  useEffect(() => {
    loadData();
  }, [activeTab]);

  const loadData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'rulesets') {
        const [pendingRes, historyRes] = await Promise.all([
          fetch('/api/v1/change-control/rulesets/pending'),
          fetch('/api/v1/change-control/rulesets/history'),
        ]);

        if (pendingRes.ok) {
          setPendingRulesets(await pendingRes.json());
        }
        if (historyRes.ok) {
          setRulesetHistory(await historyRes.json());
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (approvalId: string) => {
    try {
      const response = await fetch(`/api/v1/change-control/rulesets/${approvalId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes: approvalNotes || null }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to approve');
      }

      setShowDetailModal(false);
      setApprovalNotes('');
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  const handleReject = async (approvalId: string) => {
    if (!rejectReason || rejectReason.length < 10) {
      setError('Rejection reason must be at least 10 characters');
      return;
    }

    try {
      const response = await fetch(`/api/v1/change-control/rulesets/${approvalId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rejection_reason: rejectReason }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to reject');
      }

      setShowDetailModal(false);
      setRejectReason('');
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  const handleActivate = async (approvalId: string) => {
    try {
      const response = await fetch(`/api/v1/change-control/rulesets/${approvalId}/activate`, {
        method: 'POST',
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to activate');
      }

      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
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

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: '#f59e0b',
      approved: '#16a34a',
      rejected: '#dc2626',
    };
    return colors[status] || '#64748b';
  };

  const handleLogout = () => {
    removeToken();
    router.push('/');
  };

  return (
    <AppShell activeNav="change-control" onSignOut={handleLogout}>
      <PageHeader
        title="Change Control"
        breadcrumb={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Change Control' },
        ]}
        metaText="Manage ruleset approvals and questionnaire versions"
      />

      <div className={styles.content}>
        {error && (
          <div className={styles.error}>
            {error}
            <button onClick={() => setError(null)}>&times;</button>
          </div>
        )}

        {/* Tabs */}
        <div className={styles.tabs}>
          <button
            className={`${styles.tab} ${activeTab === 'rulesets' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('rulesets')}
          >
            Ruleset Approvals
          </button>
          <button
            className={`${styles.tab} ${activeTab === 'questionnaires' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('questionnaires')}
          >
            Questionnaire Versions
          </button>
        </div>

        {loading ? (
          <EmptyState title="Loading change control" variant="loading" />
        ) : activeTab === 'rulesets' ? (
          <>
            {/* Pending Approvals */}
            {pendingRulesets.length > 0 && (
              <div className={styles.section}>
                <h2>Pending Approvals ({pendingRulesets.length})</h2>
                <div className={styles.approvalList}>
                  {pendingRulesets.map((approval) => (
                    <div
                      key={approval.id}
                      className={styles.approvalCard}
                      onClick={() => {
                        setSelectedRuleset(approval);
                        setShowDetailModal(true);
                      }}
                    >
                      <div className={styles.approvalHeader}>
                        <span className={styles.rulesetType}>{approval.ruleset_type}</span>
                        <span className={styles.version}>v{approval.ruleset_version}</span>
                        <span
                          className={styles.statusBadge}
                          style={{ backgroundColor: getStatusColor(approval.status) }}
                        >
                          {approval.status.toUpperCase()}
                        </span>
                      </div>
                      <p className={styles.changeSummary}>{approval.change_summary}</p>
                      <div className={styles.approvalMeta}>
                        <span>Submitted {formatDate(approval.submitted_at)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Approval History */}
            <div className={styles.section}>
              <h2>Approval History</h2>
              {rulesetHistory.length === 0 ? (
                <EmptyState title="No approval history" />
              ) : (
                <table className={styles.historyTable}>
                  <thead>
                    <tr>
                      <th>Type</th>
                      <th>Version</th>
                      <th>Status</th>
                      <th>Submitted</th>
                      <th>Reviewer</th>
                      <th>Active</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rulesetHistory.map((approval) => (
                      <tr key={approval.id}>
                        <td>{approval.ruleset_type}</td>
                        <td>v{approval.ruleset_version}</td>
                        <td>
                          <span
                            className={styles.statusBadgeSmall}
                            style={{ backgroundColor: getStatusColor(approval.status) }}
                          >
                            {approval.status}
                          </span>
                        </td>
                        <td>{formatDate(approval.submitted_at)}</td>
                        <td>
                          {approval.approved_by || approval.rejected_by || '-'}
                        </td>
                        <td>
                          {approval.is_active ? (
                            <span className={styles.activeBadge}>Active</span>
                          ) : '-'}
                        </td>
                        <td>
                          {approval.status === 'approved' && !approval.is_active && (
                            <button
                              className={styles.activateButton}
                              onClick={() => handleActivate(approval.id)}
                            >
                              Activate
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </>
        ) : (
          <div className={styles.section}>
            <h2>Questionnaire Version History</h2>
            <EmptyState title="Select a questionnaire to view version history" />
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {showDetailModal && selectedRuleset && (
        <div className={styles.modal}>
          <div className={styles.modalContentLarge}>
            <div className={styles.modalHeader}>
              <div>
                <h2>{selectedRuleset.ruleset_type}</h2>
                <span className={styles.version}>Version {selectedRuleset.ruleset_version}</span>
              </div>
              <button className={styles.closeButton} onClick={() => setShowDetailModal(false)}>
                &times;
              </button>
            </div>

            <div className={styles.detailSection}>
              <h3>Change Summary</h3>
              <p>{selectedRuleset.change_summary}</p>
            </div>

            <div className={styles.detailSection}>
              <h3>Rationale</h3>
              <p>{selectedRuleset.change_rationale}</p>
            </div>

            <div className={styles.detailRow}>
              <div>
                <strong>Submitted by:</strong> {selectedRuleset.submitted_by}
              </div>
              <div>
                <strong>Submitted:</strong> {formatDate(selectedRuleset.submitted_at)}
              </div>
            </div>

            <div className={styles.detailSection}>
              <h3>Content Hash</h3>
              <code className={styles.hash}>{selectedRuleset.content_hash}</code>
            </div>

            {selectedRuleset.status === 'pending' && (
              <div className={styles.approvalActions}>
                <div className={styles.formGroup}>
                  <label>Approval Notes (optional)</label>
                  <textarea
                    value={approvalNotes}
                    onChange={(e) => setApprovalNotes(e.target.value)}
                    rows={2}
                    placeholder="Add any notes about this approval..."
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>Rejection Reason (required if rejecting)</label>
                  <textarea
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    rows={2}
                    placeholder="Explain why this change is being rejected..."
                  />
                </div>
                <div className={styles.actionButtons}>
                  <button
                    className={styles.rejectButton}
                    onClick={() => handleReject(selectedRuleset.id)}
                  >
                    Reject
                  </button>
                  <button
                    className={styles.approveButton}
                    onClick={() => handleApprove(selectedRuleset.id)}
                  >
                    Approve
                  </button>
                </div>
              </div>
            )}

            {selectedRuleset.status === 'approved' && selectedRuleset.approval_notes && (
              <div className={styles.detailSection}>
                <h3>Approval Notes</h3>
                <p>{selectedRuleset.approval_notes}</p>
              </div>
            )}

            {selectedRuleset.status === 'rejected' && (
              <div className={styles.detailSection}>
                <h3>Rejection Reason</h3>
                <p className={styles.rejectionReason}>{selectedRuleset.rejection_reason}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </AppShell>
  );
}

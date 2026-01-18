'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { getToken, removeToken } from '@/lib/auth';
import { AppShell, Button, EmptyState, PageHeader, StatusBadge } from '@/ui/components';
import styles from './audit.module.css';

interface AuditEvent {
  id: string;
  actor_type: string;
  actor_id: string | null;
  actor_email: string | null;
  action: string;
  action_category: string;
  entity_type: string;
  entity_id: string;
  metadata: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

const ACTION_LABELS: Record<string, string> = {
  patient_created: 'Patient Created',
  patient_updated: 'Patient Updated',
  patient_address_created: 'Address Added',
  patient_address_updated: 'Address Updated',
  patient_contact_created: 'Contact Added',
  patient_contact_updated: 'Contact Updated',
  patient_preferences_updated: 'Preferences Updated',
  patient_clinical_profile_updated: 'Clinical Profile Updated',
  patient_identifier_created: 'Identifier Added',
  patient_identifier_updated: 'Identifier Updated',
  triage_case_created: 'Triage Case Created',
  triage_case_opened: 'Case Opened',
  triage_case_assigned: 'Case Assigned',
  triage_case_escalated: 'Case Escalated',
  disposition_confirmed: 'Disposition Confirmed',
  disposition_overridden: 'Disposition Overridden',
  login_success: 'Login Success',
  login_failed: 'Login Failed',
  logout: 'Logout',
  mfa_enabled: 'MFA Enabled',
  mfa_disabled: 'MFA Disabled',
};

const CATEGORY_LABELS: Record<string, string> = {
  clinical: 'Clinical',
  authentication: 'Authentication',
  system: 'System',
  admin: 'Admin',
};

const ENTITY_TYPE_LABELS: Record<string, string> = {
  patient: 'Patient',
  triage_case: 'Triage Case',
  user: 'User',
  patient_address: 'Patient Address',
  patient_contact: 'Patient Contact',
  patient_preferences: 'Patient Preferences',
  patient_clinical_profile: 'Clinical Profile',
  patient_identifier: 'Patient Identifier',
};

export default function AuditLogPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [offset, setOffset] = useState(0);
  const limit = 50;

  // Filters from URL params
  const entityId = searchParams.get('entity_id');
  const entityType = searchParams.get('entity_type');
  const actorId = searchParams.get('actor_id');
  const action = searchParams.get('action');
  const category = searchParams.get('category');

  const [filterCategory, setFilterCategory] = useState(category || '');

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push('/auth/login');
      return;
    }

    setLoading(true);
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: '0',
    });
    if (entityId) params.append('entity_id', entityId);
    if (entityType) params.append('entity_type', entityType);
    if (actorId) params.append('actor_id', actorId);
    if (action) params.append('action', action);
    if (filterCategory) params.append('action_category', filterCategory);

    fetch(`/api/v1/audit/events?${params}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (res) => {
        if (res.status === 401) {
          removeToken();
          router.push('/auth/login');
          return;
        }
        if (res.status === 403) {
          setError('You do not have permission to view the audit log.');
          return;
        }
        if (!res.ok) {
          throw new Error('Failed to load audit events');
        }
        const data = await res.json();
        setEvents(data);
        setHasMore(data.length === limit);
        setOffset(0);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load audit events');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [entityId, entityType, actorId, action, filterCategory, router]);

  const loadMore = async () => {
    const token = getToken();
    if (!token) return;

    const newOffset = offset + limit;
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: newOffset.toString(),
    });
    if (entityId) params.append('entity_id', entityId);
    if (entityType) params.append('entity_type', entityType);
    if (actorId) params.append('actor_id', actorId);
    if (action) params.append('action', action);
    if (filterCategory) params.append('action_category', filterCategory);

    try {
      const res = await fetch(`/api/v1/audit/events?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setEvents((prev) => [...prev, ...data]);
        setOffset(newOffset);
        setHasMore(data.length === limit);
      }
    } catch (err) {
      console.error('Failed to load more events:', err);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const clearFilters = () => {
    setFilterCategory('');
    router.push('/dashboard/audit');
  };

  const hasFilters = entityId || entityType || actorId || action || filterCategory;

  const handleLogout = () => {
    removeToken();
    router.push('/');
  };

  return (
    <AppShell activeNav="audit" onSignOut={handleLogout}>
      <PageHeader
        title="Audit Log"
        breadcrumb={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Audit Log' },
        ]}
        metaText="System activity and change history (read-only)"
      />

      <div className={styles.content}>
        <div className={styles.toolbar}>
          <div className={styles.filters}>
            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className={styles.filterSelect}
            >
              <option value="">All Categories</option>
              <option value="clinical">Clinical</option>
              <option value="authentication">Authentication</option>
              <option value="system">System</option>
              <option value="admin">Admin</option>
            </select>

            {hasFilters && (
              <Button variant="tertiary" onClick={clearFilters}>
                Clear Filters
              </Button>
            )}
          </div>

          {hasFilters && (
            <div className={styles.activeFilters}>
              {entityId && <span className={styles.filterTag}>Entity: {entityId.slice(0, 8)}...</span>}
              {entityType && <span className={styles.filterTag}>Type: {ENTITY_TYPE_LABELS[entityType] || entityType}</span>}
              {actorId && <span className={styles.filterTag}>Actor: {actorId.slice(0, 8)}...</span>}
              {action && <span className={styles.filterTag}>Action: {ACTION_LABELS[action] || action}</span>}
              {filterCategory && <span className={styles.filterTag}>Category: {CATEGORY_LABELS[filterCategory] || filterCategory}</span>}
            </div>
          )}
        </div>

        <main className={styles.main}>
          {loading ? (
            <EmptyState title="Loading audit events" variant="loading" />
          ) : error ? (
            <EmptyState
              title="Failed to load audit events"
              message={error}
              actionLabel="Retry"
              onAction={() => window.location.reload()}
              variant="error"
            />
          ) : events.length === 0 ? (
            <EmptyState
              title="No audit events found"
              message={hasFilters ? 'No results match the current filters.' : 'No audit events yet.'}
            />
          ) : (
            <>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Action</th>
                    <th>Category</th>
                    <th>Entity</th>
                    <th>Actor</th>
                    <th>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((event) => (
                    <tr key={event.id}>
                      <td className={styles.timestampCell}>
                        {formatDate(event.created_at)}
                      </td>
                      <td>
                        <span className={styles.actionLabel}>
                          {ACTION_LABELS[event.action] || event.action}
                        </span>
                      </td>
                      <td>
                        <StatusBadge
                          tone={event.action_category === 'clinical'
                            ? 'green'
                            : event.action_category === 'authentication'
                              ? 'blue'
                              : event.action_category === 'system'
                                ? 'amber'
                                : 'neutral'}
                          label={CATEGORY_LABELS[event.action_category] || event.action_category}
                        />
                      </td>
                      <td className={styles.entityCell}>
                        <span className={styles.entityType}>
                          {ENTITY_TYPE_LABELS[event.entity_type] || event.entity_type}
                        </span>
                        <span className={styles.entityId}>
                          {event.entity_id.slice(0, 8)}...
                        </span>
                      </td>
                      <td className={styles.actorCell}>
                        {event.actor_email ? (
                          <>
                            <span className={styles.actorEmail}>{event.actor_email}</span>
                            <span className={styles.actorType}>{event.actor_type}</span>
                          </>
                        ) : (
                          <span className={styles.actorType}>{event.actor_type}</span>
                        )}
                      </td>
                      <td className={styles.detailsCell}>
                        {event.metadata && Object.keys(event.metadata).length > 0 ? (
                          <details className={styles.metadataDetails}>
                            <summary>View</summary>
                            <pre className={styles.metadataContent}>
                              {JSON.stringify(event.metadata, null, 2)}
                            </pre>
                          </details>
                        ) : (
                          <span className={styles.noDetails}>-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {hasMore && (
                <div className={styles.loadMore}>
                  <Button onClick={loadMore} variant="secondary">
                    Load More
                  </Button>
                </div>
              )}
            </>
          )}
        </main>

        <footer className={styles.footer}>
          <p className={styles.footerNote}>
            Audit events are append-only and cannot be modified or deleted.
          </p>
        </footer>
      </div>
    </AppShell>
  );
}

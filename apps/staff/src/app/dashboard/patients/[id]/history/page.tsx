'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { getToken, removeToken } from '@/lib/auth';
import styles from './history.module.css';

interface PatientRecordUpdate {
  id: string;
  patient_id: string;
  actor_user_id: string | null;
  actor_type: string;
  source: string;
  changed_fields: Record<string, { old: unknown; new: unknown }>;
  reason: string | null;
  created_at: string;
}

interface PatientSummary {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
}

// Human-readable field names
const FIELD_LABELS: Record<string, string> = {
  first_name: 'First Name',
  last_name: 'Last Name',
  preferred_name: 'Preferred Name',
  date_of_birth: 'Date of Birth',
  sex_at_birth: 'Sex at Birth',
  gender_identity: 'Gender Identity',
  ethnicity: 'Ethnicity',
  preferred_language: 'Preferred Language',
  interpreter_required: 'Interpreter Required',
  email: 'Email',
  phone_e164: 'Phone',
  preferred_contact_method: 'Preferred Contact Method',
  can_leave_voicemail: 'Can Leave Voicemail',
  consent_to_sms: 'SMS Consent',
  consent_to_email: 'Email Consent',
  postcode: 'Postcode',
  country: 'Country',
  has_dependents: 'Has Dependents',
  is_pregnant_or_postnatal: 'Pregnant / Postnatal',
  reasonable_adjustments_required: 'Reasonable Adjustments Required',
  is_active: 'Active Status',
  nhs_number: 'NHS Number',
  presenting_problem: 'Presenting Problem',
  previous_mental_health_treatment: 'Previous MH Treatment',
  current_psych_medication: 'Current Psych Medication',
  substance_use_level: 'Substance Use Level',
  physical_health_conditions: 'Physical Health Conditions',
  physical_health_notes: 'Physical Health Notes',
  neurodevelopmental_needs: 'Neurodevelopmental Needs',
  risk_notes_staff_only: 'Risk Notes (Staff Only)',
  communication_channel_preference: 'Communication Preference',
  appointment_format_preference: 'Appointment Format Preference',
  requires_accessibility_support: 'Requires Accessibility Support',
  accessibility_notes: 'Accessibility Notes',
  reasonable_adjustments_notes: 'Adjustments Notes',
};

// Human-readable source labels
const SOURCE_LABELS: Record<string, string> = {
  INTAKE: 'Patient Intake',
  STAFF_EDIT: 'Staff Edit',
  IMPORT: 'Data Import',
  SYSTEM: 'System',
};

// Human-readable actor type labels
const ACTOR_TYPE_LABELS: Record<string, string> = {
  STAFF: 'Staff',
  PATIENT: 'Patient',
  SYSTEM: 'System',
};

function formatValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '(empty)';
  }
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }
  if (typeof value === 'string') {
    if (value === '') return '(empty)';
    // Replace underscores with spaces and capitalize
    return value.replace(/_/g, ' ');
  }
  if (Array.isArray(value)) {
    return value.length > 0 ? `${value.length} items` : '(empty)';
  }
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function PatientHistoryPage() {
  const router = useRouter();
  const params = useParams();
  const patientId = params.id as string;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updates, setUpdates] = useState<PatientRecordUpdate[]>([]);
  const [patient, setPatient] = useState<PatientSummary | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [offset, setOffset] = useState(0);
  const limit = 50;

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push('/auth/login');
      return;
    }

    // Fetch patient summary and updates in parallel
    Promise.all([
      fetch(`/api/v1/patients/${patientId}`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
      fetch(`/api/v1/patients/${patientId}/updates?limit=${limit}&offset=0`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
    ])
      .then(async ([patientRes, updatesRes]) => {
        if (patientRes.status === 401 || updatesRes.status === 401 ||
            patientRes.status === 403 || updatesRes.status === 403) {
          removeToken();
          router.push('/auth/login');
          return;
        }

        if (!patientRes.ok) {
          throw new Error('Failed to load patient');
        }

        if (!updatesRes.ok) {
          throw new Error('Failed to load update history');
        }

        const patientData = await patientRes.json();
        const updatesData = await updatesRes.json();

        setPatient({
          id: patientData.id,
          first_name: patientData.first_name,
          last_name: patientData.last_name,
          email: patientData.email,
        });
        setUpdates(updatesData);
        setHasMore(updatesData.length === limit);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load data');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [patientId, router]);

  const loadMore = async () => {
    const token = getToken();
    if (!token) return;

    const newOffset = offset + limit;
    try {
      const res = await fetch(
        `/api/v1/patients/${patientId}/updates?limit=${limit}&offset=${newOffset}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (res.ok) {
        const data = await res.json();
        setUpdates((prev) => [...prev, ...data]);
        setOffset(newOffset);
        setHasMore(data.length === limit);
      }
    } catch (err) {
      console.error('Failed to load more updates:', err);
    }
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Loading update history...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <div className={styles.error}>
          <p>{error}</p>
          <button onClick={() => router.back()} className={styles.backButton}>
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.breadcrumb}>
          <Link href="/dashboard/triage">Dashboard</Link>
          <span>/</span>
          <span>Patient History</span>
        </div>
        <h1>Update History</h1>
        {patient && (
          <p className={styles.patientInfo}>
            {patient.first_name} {patient.last_name} ({patient.email})
          </p>
        )}
      </header>

      <main className={styles.main}>
        {updates.length === 0 ? (
          <div className={styles.emptyState}>
            <p>No updates recorded for this patient.</p>
          </div>
        ) : (
          <div className={styles.timeline}>
            {updates.map((update) => (
              <div key={update.id} className={styles.updateCard}>
                <div className={styles.updateHeader}>
                  <div className={styles.updateMeta}>
                    <span className={styles.updateDate}>
                      {formatDate(update.created_at)}
                    </span>
                    <span className={styles.updateSource}>
                      {SOURCE_LABELS[update.source] || update.source}
                    </span>
                    <span className={styles.updateActor}>
                      {ACTOR_TYPE_LABELS[update.actor_type] || update.actor_type}
                      {update.actor_user_id && (
                        <span className={styles.actorId}> ({update.actor_user_id.slice(0, 8)}...)</span>
                      )}
                    </span>
                  </div>
                </div>

                <div className={styles.changesTable}>
                  <table>
                    <thead>
                      <tr>
                        <th>Field</th>
                        <th>Previous Value</th>
                        <th></th>
                        <th>New Value</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(update.changed_fields).map(([field, values]) => (
                        <tr key={field}>
                          <td className={styles.fieldName}>
                            {FIELD_LABELS[field] || field.replace(/_/g, ' ')}
                          </td>
                          <td className={styles.oldValue}>
                            {formatValue(values.old)}
                          </td>
                          <td className={styles.arrow}>→</td>
                          <td className={styles.newValue}>
                            {formatValue(values.new)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {update.reason && (
                  <div className={styles.reason}>
                    <span className={styles.reasonLabel}>Reason:</span>
                    <span className={styles.reasonText}>{update.reason}</span>
                  </div>
                )}
              </div>
            ))}

            {hasMore && (
              <button onClick={loadMore} className={styles.loadMoreButton}>
                Load More
              </button>
            )}
          </div>
        )}
      </main>

      <footer className={styles.footer}>
        <button onClick={() => router.back()} className={styles.backButton}>
          ← Back to Case
        </button>
      </footer>
    </div>
  );
}

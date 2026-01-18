'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getToken, removeToken } from '@/lib/auth';
import { AppShell, EmptyState, PageHeader } from '@/ui/components';
import styles from './history.module.css';

interface PatientRecordUpdate {
  id: string;
  patient_id: string;
  actor_user_id: string | null;
  actor_user_name: string | null;
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
  address_line_1: 'Address Line 1',
  address_line_2: 'Address Line 2',
  city: 'City',
  country: 'Country',
  has_dependents: 'Has Dependents',
  is_pregnant_or_postnatal: 'Pregnant / Postnatal',
  reasonable_adjustments_required: 'Reasonable Adjustments Required',
  is_active: 'Active Status',
  nhs_number: 'NHS Number',
  gp_practice_name: 'GP Practice',
  gp_practice_code: 'GP Practice Code',
  presenting_problem: 'Presenting Problem',
  previous_mental_health_treatment: 'Previous MH Treatment',
  current_psych_medication: 'Current Psych Medication',
  substance_use_level: 'Substance Use Level',
  physical_health_conditions: 'Physical Health Conditions',
  physical_health_notes: 'Physical Health Notes',
  neurodevelopmental_needs: 'Neurodevelopmental Needs',
  risk_notes_staff_only: 'Risk Notes (Staff Only)',
  clinical_notes: 'Clinical Notes',
  emergency_contact_name: 'Emergency Contact Name',
  emergency_contact_phone: 'Emergency Contact Phone',
  emergency_contact_relationship: 'Emergency Contact Relationship',
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

function formatValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '(empty)';
  }
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }
  if (typeof value === 'string') {
    if (value === '') return '(empty)';
    // Truncate long values
    if (value.length > 80) {
      return value.substring(0, 80) + '...';
    }
    return value.replace(/_/g, ' ');
  }
  if (Array.isArray(value)) {
    return value.length > 0 ? `${value.length} items` : '(empty)';
  }
  if (typeof value === 'object') {
    const str = JSON.stringify(value);
    if (str.length > 80) return str.substring(0, 80) + '...';
    return str;
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
  const [patientError, setPatientError] = useState<string | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);
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

    setLoading(true);
    setPatientError(null);
    setHistoryError(null);

    // Fetch patient summary first, then history
    fetch(`/api/v1/patients/${patientId}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (patientRes) => {
        if (patientRes.status === 401 || patientRes.status === 403) {
          removeToken();
          router.push('/auth/login');
          return;
        }

        if (patientRes.status === 404) {
          setPatientError('Patient record not found');
          setLoading(false);
          return;
        }

        if (!patientRes.ok) {
          setPatientError('Unable to load patient record');
          setLoading(false);
          return;
        }

        const patientData = await patientRes.json();
        setPatient({
          id: patientData.id,
          first_name: patientData.first_name,
          last_name: patientData.last_name,
          email: patientData.email,
        });

        // Now fetch history
        try {
          const historyRes = await fetch(
            `/api/v1/patients/${patientId}/updates?limit=${limit}&offset=0`,
            { headers: { Authorization: `Bearer ${token}` } }
          );

          if (historyRes.ok) {
            const historyData = await historyRes.json();
            setUpdates(historyData);
            setHasMore(historyData.length === limit);
          } else {
            // History failed but patient loaded - partial failure
            setHistoryError('Update history temporarily unavailable');
          }
        } catch {
          setHistoryError('Update history temporarily unavailable');
        }

        setLoading(false);
      })
      .catch(() => {
        setPatientError('Unable to load patient record');
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

  const handleLogout = () => {
    removeToken();
    router.push('/');
  };

  const patientName = patient ? `${patient.first_name} ${patient.last_name}` : 'Patient';

  return (
    <AppShell activeNav="patients" onSignOut={handleLogout}>
      <PageHeader
        title="Update History"
        breadcrumb={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Patients', href: '/dashboard/patients' },
          { label: patientName, href: patient ? `/dashboard/patients/${patient.id}` : undefined },
          { label: 'History' },
        ]}
      />

      <div className={styles.content}>
        {/* Page intro - boring, factual */}
        <p className={styles.pageIntro}>
          Documented changes to this patient's record, with timestamps and reasons.
        </p>

        {loading ? (
          <EmptyState title="Loading update history" variant="loading" />
        ) : patientError ? (
          // True failure - patient not found or access denied
          <div className={styles.errorState}>
            <div className={styles.errorIcon}>⚠️</div>
            <h3>Unable to load patient record</h3>
            <p>This may be due to access restrictions or the record no longer existing.</p>
            <button onClick={() => router.push('/dashboard/patients')} className={styles.backLink}>
              Return to Patient List
            </button>
          </div>
        ) : (
          <>
            {/* Patient header - subtle */}
            {patient && (
              <div className={styles.patientHeader}>
                <span className={styles.patientName}>{patientName}</span>
                <span className={styles.patientEmail}>{patient.email}</span>
              </div>
            )}

            <main className={styles.main}>
              {historyError ? (
                // Partial failure - patient loaded but history didn't
                <div className={styles.partialError}>
                  <p><strong>Update history temporarily unavailable</strong></p>
                  <p>The patient record is intact. Please try again later or check the audit log.</p>
                </div>
              ) : updates.length === 0 ? (
                // Empty state - positive framing (this is normal)
                <div className={styles.emptyState}>
                  <div className={styles.emptyIcon}>📋</div>
                  <h3>No recorded updates yet</h3>
                  <p>This patient's core record has not been modified since creation.</p>
                </div>
              ) : (
                <div className={styles.timeline}>
                  {updates.map((update) => (
                    <div key={update.id} className={styles.updateCard}>
                      <div className={styles.updateHeader}>
                        <span className={styles.updateDate}>
                          {formatDate(update.created_at)}
                        </span>
                        <span className={styles.updateSource}>
                          {SOURCE_LABELS[update.source] || update.source}
                        </span>
                        <span className={styles.updateActor}>
                          {update.actor_user_name || (update.actor_type === 'SYSTEM' ? 'System' : 'Unknown')}
                        </span>
                      </div>

                      <table className={styles.changesTable}>
                        <thead>
                          <tr>
                            <th>Field</th>
                            <th>Previous</th>
                            <th></th>
                            <th>New</th>
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
          </>
        )}
      </div>

      <footer className={styles.footer}>
        <button onClick={() => router.back()} className={styles.backButton}>
          ← Back
        </button>
      </footer>
    </AppShell>
  );
}

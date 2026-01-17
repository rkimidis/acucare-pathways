'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { getToken, removeToken } from '@/lib/auth';
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
  answers_human?: AnswerItem[];
  submitted_at: string | null;
}

interface AnswerItem {
  field_id: string;
  question: string;
  answer: string;
}

interface TimelineEntry {
  label: string;
  timestamp: string;
  actor_type: string;
  actor_name: string | null;
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
    assigned_to_user_id?: string | null;
    assigned_to_user_name?: string | null;
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
  timeline: TimelineEntry[];
}

interface QueueItem {
  id: string;
  tier: string | null;
}

type TabType = 'overview' | 'patient-details' | 'scores' | 'answers' | 'disposition';

interface PatientAddress {
  id: string;
  type: string;
  line1: string | null;
  line2: string | null;
  city: string | null;
  county: string | null;
  postcode: string | null;
  country: string;
  valid_from: string | null;
  valid_to: string | null;
  is_primary: boolean;
  created_at: string;
}

interface PatientContact {
  id: string;
  contact_type: string;
  name: string | null;
  relationship_to_patient: string | null;
  phone_e164: string | null;
  email: string | null;
  organisation: string | null;
  notes: string | null;
  created_at: string;
}

interface PatientPreferences {
  communication_channel_preference: string | null;
  appointment_format_preference: string | null;
  requires_accessibility_support: boolean;
  accessibility_notes: string | null;
  reasonable_adjustments_notes: string | null;
}

interface PatientClinicalProfile {
  presenting_problem: string | null;
  previous_mental_health_treatment: string | null;
  current_psych_medication: boolean | null;
  current_medication_list: Array<{ name: string; dose: string; frequency: string }> | null;
  physical_health_conditions: boolean | null;
  physical_health_notes: string | null;
  substance_use_level: string | null;
  neurodevelopmental_needs: boolean | null;
  risk_notes_staff_only: string | null;
}

interface PatientIdentifier {
  id: string;
  id_type: string;
  id_value: string;
  is_verified: boolean;
  verified_at: string | null;
  created_at: string;
}

interface PatientDetail {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  preferred_name: string | null;
  date_of_birth: string | null;
  sex_at_birth: string | null;
  gender_identity: string | null;
  ethnicity: string | null;
  preferred_language: string | null;
  interpreter_required: boolean;
  phone_e164: string | null;
  preferred_contact_method: string | null;
  can_leave_voicemail: boolean;
  consent_to_sms: boolean;
  consent_to_email: boolean;
  postcode: string | null;
  country: string | null;
  has_dependents: boolean | null;
  is_pregnant_or_postnatal: boolean | null;
  reasonable_adjustments_required: boolean;
  is_active: boolean;
  nhs_number: string | null;
  created_at: string;
  updated_at: string | null;
  addresses: PatientAddress[];
  contacts: PatientContact[];
  preferences: PatientPreferences | null;
  clinical_profile: PatientClinicalProfile | null;
  identifiers: PatientIdentifier[];
  primary_gp_contact_id: string | null;
  emergency_contact_id: string | null;
  primary_gp_contact: PatientContact | null;
  emergency_contact: PatientContact | null;
}

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
  const [showOverrideConfirm, setShowOverrideConfirm] = useState(false);
  const [showConfirmPrompt, setShowConfirmPrompt] = useState(false);
  const [showIncidentPrompt, setShowIncidentPrompt] = useState(false);
  const [showFeedbackPrompt, setShowFeedbackPrompt] = useState(true);
  const [showRawAnswers, setShowRawAnswers] = useState<Record<string, boolean>>({});
  const [showTimeline, setShowTimeline] = useState(false);
  const [whyPathwayStorageKey, setWhyPathwayStorageKey] = useState<string | null>(null);
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [patientDetails, setPatientDetails] = useState<PatientDetail | null>(null);
  const [patientDetailsLoading, setPatientDetailsLoading] = useState(false);
  const [patientDetailsError, setPatientDetailsError] = useState<string | null>(null);
  const [currentUserRole, setCurrentUserRole] = useState<string | null>(null);
  const [confirmNotes, setConfirmNotes] = useState('');
  const [showConfirmBanner, setShowConfirmBanner] = useState(false);

  // Edit mode state
  type EditSection =
    | 'identity'
    | 'contact'
    | 'contacts'
    | 'address'
    | 'identifiers'
    | 'safeguarding'
    | 'clinical'
    | 'preferences'
    | null;
  const [editingSection, setEditingSection] = useState<EditSection>(null);
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<Record<string, unknown>>({});
  const [editReason, setEditReason] = useState('');
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  // Fields that require a reason when changed
  const REASON_REQUIRED_FIELDS = [
    'first_name',
    'last_name',
    'date_of_birth',
    'email',
    'phone_e164',
    'primary_gp_contact_id',
    'emergency_contact_id',
  ];

  // Check if user can edit patient details
  const isAdminEditor = currentUserRole && ['admin', 'clinical_lead'].includes(currentUserRole);
  const isClinicianEditor = currentUserRole && ['clinician', 'clinical_lead', 'admin'].includes(currentUserRole);

  const canEditSection = (section: EditSection) => {
    if (!section) return false;
    if (section === 'preferences' || section === 'clinical' || section === 'contacts') {
      return !!isClinicianEditor;
    }
    if (section === 'identity' || section === 'contact' || section === 'safeguarding' || section === 'address' || section === 'identifiers') {
      return !!isAdminEditor;
    }
    return false;
  };


  const decodeTokenPayload = (token: string) => {
    try {
      const payload = token.split('.')[1];
      if (!payload) return null;
      const decoded = JSON.parse(atob(payload));
      return {
        userId: decoded.sub as string | undefined,
        role: decoded.role as string | undefined,
      };
    } catch {
      return null;
    }
  };

  // Load queue for navigation
  useEffect(() => {
    const token = getToken();
    if (!token) return;

    fetch('/api/v1/dashboard/queue', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => setQueueCases(data.items || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push('/auth/login');
      return;
    }

    const payload = decodeTokenPayload(token);
    setCurrentUserId(payload?.userId ?? null);
    setCurrentUserRole(payload?.role ?? null);

    fetchCaseSummary(token);
  }, [caseId, router]);

  useEffect(() => {
    setShowConfirmBanner(false);
    setConfirmNotes('');
  }, [caseId]);

  useEffect(() => {
    if (!caseId) return;
    const storageKey = `whyPathwayExpanded:${caseId}`;
    setWhyPathwayStorageKey(storageKey);
    const stored = localStorage.getItem(storageKey);
    if (stored === null) {
      setShowWhyPathway(true);
      localStorage.setItem(storageKey, 'true');
    } else {
      setShowWhyPathway(stored === 'true');
    }
  }, [caseId]);

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
            setShowConfirmPrompt(true);
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

      if (response.status === 401 || response.status === 403) {
        removeToken();
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

  const fetchPatientDetails = async (patientId: string) => {
    const token = getToken();
    if (!token) return;

    try {
      setPatientDetailsLoading(true);
      setPatientDetailsError(null);
      const response = await fetch(`/api/v1/patients/${patientId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setPatientDetails(data);
      } else if (response.status === 404) {
        setPatientDetailsError('Patient record not found');
      } else if (response.status === 403) {
        setPatientDetailsError('You do not have permission to view this patient');
      } else {
        setPatientDetailsError('Unable to load patient details');
      }
    } catch (err) {
      console.error('Failed to fetch patient details:', err);
      setPatientDetailsError('Unable to load patient details. Please try again.');
    } finally {
      setPatientDetailsLoading(false);
    }
  };

  const retryPatientDetails = () => {
    if (summary?.patient?.id) {
      setPatientDetails(null);
      fetchPatientDetails(summary.patient.id);
    }
  };

  // Start editing a section
  const startEditSection = (section: EditSection, itemId: string | null = null) => {
    if (!patientDetails || !canEditSection(section)) return;

    // Pre-fill form based on section
    let formData: Record<string, unknown> = {};

    switch (section) {
      case 'identity':
        formData = {
          first_name: patientDetails.first_name,
          last_name: patientDetails.last_name,
          preferred_name: patientDetails.preferred_name || '',
          date_of_birth: patientDetails.date_of_birth || '',
          sex_at_birth: patientDetails.sex_at_birth || '',
          gender_identity: patientDetails.gender_identity || '',
          ethnicity: patientDetails.ethnicity || '',
          preferred_language: patientDetails.preferred_language || '',
          interpreter_required: patientDetails.interpreter_required,
        };
        break;
      case 'contact':
        formData = {
          email: patientDetails.email,
          phone_e164: patientDetails.phone_e164 || '',
          preferred_contact_method: patientDetails.preferred_contact_method || '',
          can_leave_voicemail: patientDetails.can_leave_voicemail,
          consent_to_sms: patientDetails.consent_to_sms,
          consent_to_email: patientDetails.consent_to_email,
          primary_gp_contact_id: patientDetails.primary_gp_contact_id || '',
          emergency_contact_id: patientDetails.emergency_contact_id || '',
        };
        break;
      case 'contacts': {
        const contact = patientDetails.contacts.find((item) => item.id === itemId);
        formData = {
          contact_type: contact?.contact_type || '',
          name: contact?.name || '',
          relationship_to_patient: contact?.relationship_to_patient || '',
          phone_e164: contact?.phone_e164 || '',
          email: contact?.email || '',
          organisation: contact?.organisation || '',
          notes: contact?.notes || '',
        };
        break;
      }
      case 'address': {
        const address = patientDetails.addresses.find((item) => item.id === itemId);
        formData = {
          type: address?.type || '',
          line1: address?.line1 || '',
          line2: address?.line2 || '',
          city: address?.city || '',
          county: address?.county || '',
          postcode: address?.postcode || '',
          country: address?.country || 'GB',
          valid_from: address?.valid_from || '',
          valid_to: address?.valid_to || '',
          is_primary: address?.is_primary || false,
        };
        break;
      }
      case 'identifiers': {
        const identifier = patientDetails.identifiers.find((item) => item.id === itemId);
        formData = {
          id_type: identifier?.id_type || '',
          id_value: identifier?.id_value || '',
          is_verified: identifier?.is_verified || false,
        };
        break;
      }
      case 'safeguarding':
        formData = {
          has_dependents: patientDetails.has_dependents,
          is_pregnant_or_postnatal: patientDetails.is_pregnant_or_postnatal,
          reasonable_adjustments_required: patientDetails.reasonable_adjustments_required,
        };
        break;
      case 'preferences':
        formData = {
          communication_channel_preference: patientDetails.preferences?.communication_channel_preference || '',
          appointment_format_preference: patientDetails.preferences?.appointment_format_preference || '',
          requires_accessibility_support: patientDetails.preferences?.requires_accessibility_support || false,
          accessibility_notes: patientDetails.preferences?.accessibility_notes || '',
          reasonable_adjustments_notes: patientDetails.preferences?.reasonable_adjustments_notes || '',
        };
        break;
      case 'clinical':
        formData = {
          presenting_problem: patientDetails.clinical_profile?.presenting_problem || '',
          previous_mental_health_treatment: patientDetails.clinical_profile?.previous_mental_health_treatment || '',
          current_psych_medication: patientDetails.clinical_profile?.current_psych_medication,
          substance_use_level: patientDetails.clinical_profile?.substance_use_level || '',
          physical_health_conditions: patientDetails.clinical_profile?.physical_health_conditions,
          physical_health_notes: patientDetails.clinical_profile?.physical_health_notes || '',
          neurodevelopmental_needs: patientDetails.clinical_profile?.neurodevelopmental_needs,
          risk_notes_staff_only: patientDetails.clinical_profile?.risk_notes_staff_only || '',
        };
        break;
    }

    setEditForm(formData);
    setEditReason('');
    setEditError(null);
    setEditingSection(section);
    setEditingItemId(itemId);
  };

  const cancelEdit = () => {
    setEditingSection(null);
    setEditingItemId(null);
    setEditForm({});
    setEditReason('');
    setEditError(null);
  };

  const getChangedFieldsForSection = (): string[] => {
    if (!patientDetails || !editingSection) return [];

    const normalizeValue = (value: unknown) => (value === '' ? null : value);
    const compareAgainst = (source: Record<string, unknown> | null) =>
      Object.keys(editForm).filter(
        (key) => normalizeValue(editForm[key]) !== normalizeValue(source?.[key] as unknown)
      );

    if (editingSection === 'identity' || editingSection === 'contact' || editingSection === 'safeguarding') {
      return compareAgainst(patientDetails as unknown as Record<string, unknown>);
    }
    if (editingSection === 'preferences') {
      return compareAgainst((patientDetails.preferences || {}) as unknown as Record<string, unknown>);
    }
    if (editingSection === 'clinical') {
      return compareAgainst((patientDetails.clinical_profile || {}) as unknown as Record<string, unknown>);
    }
    if (editingSection === 'contacts') {
      const contact = patientDetails.contacts.find((item) => item.id === editingItemId);
      if (!contact) {
        return Object.keys(editForm).filter(
          (key) => editForm[key] !== '' && editForm[key] !== null && editForm[key] !== undefined
        );
      }
      return compareAgainst(contact as unknown as Record<string, unknown>);
    }
    if (editingSection === 'address') {
      const address = patientDetails.addresses.find((item) => item.id === editingItemId);
      if (!address) {
        return Object.keys(editForm).filter(
          (key) => editForm[key] !== '' && editForm[key] !== null && editForm[key] !== undefined
        );
      }
      return compareAgainst(address as unknown as Record<string, unknown>);
    }
    if (editingSection === 'identifiers') {
      const identifier = patientDetails.identifiers.find((item) => item.id === editingItemId);
      if (!identifier) {
        return Object.keys(editForm).filter(
          (key) => editForm[key] !== '' && editForm[key] !== null && editForm[key] !== undefined
        );
      }
      return compareAgainst(identifier as unknown as Record<string, unknown>);
    }
    return [];
  };

  const saveEdit = async () => {
    if (!patientDetails || !editingSection) return;

    const token = getToken();
    if (!token) return;

    const normalizedForm = Object.fromEntries(
      Object.entries(editForm).map(([key, value]) => [key, value === '' ? null : value])
    );

    // Check if reason is required for any changed fields
    const changedFields = getChangedFieldsForSection();
    const needsReason = editingSection === 'identifiers'
      ? changedFields.length > 0
      : changedFields.some((f) => REASON_REQUIRED_FIELDS.includes(f));
    if (needsReason && !editReason.trim()) {
      setEditError('Reason required for this change');
      return;
    }

    setEditSaving(true);
    setEditError(null);

    try {
      let endpoint = '';
      let method = 'PATCH';
      let body: Record<string, unknown> = {};

      if (editingSection === 'identity' || editingSection === 'contact' || editingSection === 'safeguarding') {
        // These fields go to PATCH /patients/{id}
        endpoint = `/api/v1/patients/${patientDetails.id}`;
        body = {
          updates: normalizedForm,
          reason: needsReason ? editReason : null,
        };
      } else if (editingSection === 'preferences') {
        // PUT /patients/{id}/preferences
        endpoint = `/api/v1/patients/${patientDetails.id}/preferences`;
        method = 'PUT';
        body = normalizedForm;
      } else if (editingSection === 'clinical') {
        // PUT /patients/{id}/clinical-profile
        endpoint = `/api/v1/patients/${patientDetails.id}/clinical-profile`;
        method = 'PUT';
        body = normalizedForm;
      } else if (editingSection === 'contacts') {
        if (editingItemId) {
          endpoint = `/api/v1/patients/${patientDetails.id}/contacts/${editingItemId}`;
          method = 'PATCH';
        } else {
          endpoint = `/api/v1/patients/${patientDetails.id}/contacts`;
          method = 'POST';
        }
        body = normalizedForm;
      } else if (editingSection === 'address') {
        if (editingItemId) {
          endpoint = `/api/v1/patients/${patientDetails.id}/addresses/${editingItemId}`;
          method = 'PATCH';
        } else {
          endpoint = `/api/v1/patients/${patientDetails.id}/addresses`;
          method = 'POST';
        }
        body = normalizedForm;
      } else if (editingSection === 'identifiers') {
        if (editingItemId) {
          endpoint = `/api/v1/patients/${patientDetails.id}/identifiers/${editingItemId}`;
          method = 'PATCH';
        } else {
          endpoint = `/api/v1/patients/${patientDetails.id}/identifiers`;
          method = 'POST';
        }
        body = { ...normalizedForm, reason: editReason || null };
      }

      const response = await fetch(endpoint, {
        method,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to save changes');
      }

      // Refresh patient details
      await fetchPatientDetails(patientDetails.id);
      cancelEdit();
    } catch (err) {
      setEditError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setEditSaving(false);
    }
  };

  // Fetch patient details when patient ID is available (for summary header)
  useEffect(() => {
    if (summary?.patient?.id && !patientDetails && !patientDetailsLoading) {
      fetchPatientDetails(summary.patient.id);
    }
  }, [summary?.patient?.id, patientDetails, patientDetailsLoading]);

  const handleClaimCase = async () => {
    try {
      const token = getToken();
      if (!token) {
        router.push('/auth/login');
        return;
      }

      const response = await fetch(`/api/v1/triage-cases/${caseId}/claim`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) throw new Error('Failed to claim case');

      await fetchCaseSummary(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to claim case');
    }
  };

  const handleUnassignCase = async () => {
    try {
      const token = getToken();
      if (!token) {
        router.push('/auth/login');
        return;
      }

      const response = await fetch(`/api/v1/triage-cases/${caseId}/unassign`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) throw new Error('Failed to unassign case');

      await fetchCaseSummary(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to unassign case');
    }
  };

  const handleConfirmDisposition = async () => {
    const token = getToken();
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
        body: JSON.stringify({ clinical_notes: confirmNotes || null }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to confirm disposition');
      }

      setShowConfirmPrompt(false);
      setShowConfirmBanner(true);
      setConfirmNotes('');

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
    const token = getToken();
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
    const token = getToken();
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

  const humanizeKey = (key: string): string =>
    key.replace(/[_-]+/g, ' ').trim().replace(/\b\w/g, (c) => c.toUpperCase());

  const formatAnswerValue = (value: unknown): string => {
    if (value === null || value === undefined || value === '') return '—';
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (Array.isArray(value)) {
      return value.length ? value.map((v) => String(v)).join(', ') : '—';
    }
    if (typeof value === 'object') {
      try {
        return JSON.stringify(value);
      } catch {
        return String(value);
      }
    }
    return String(value);
  };

  const buildFallbackAnswers = (answers: Record<string, unknown>): AnswerItem[] =>
    Object.entries(answers).map(([fieldId, value]) => ({
      field_id: fieldId,
      question: humanizeKey(fieldId),
      answer: formatAnswerValue(value),
    }));

  const findPrimaryComplaint = (): string | null => {
    if (!summary) return null;
    const questionMatches = [
      'primary complaint',
      'primary concern',
      'main concern',
      'presenting problem',
      'presenting issue',
      'reason for referral',
      'what brings',
      'main problem',
    ];
    const keyMatches = [
      'primary_complaint',
      'primary_concern',
      'main_concern',
      'presenting_problem',
      'presenting_issue',
      'reason_for_referral',
      'complaint',
    ];

    const responses = [...summary.questionnaire_responses].sort((a, b) => {
      const aTime = a.submitted_at ? new Date(a.submitted_at).getTime() : 0;
      const bTime = b.submitted_at ? new Date(b.submitted_at).getTime() : 0;
      return bTime - aTime;
    });

    for (const resp of responses) {
      if (resp.answers_human && resp.answers_human.length > 0) {
        const match = resp.answers_human.find((item) =>
          questionMatches.some((q) => item.question.toLowerCase().includes(q))
        );
        if (match && match.answer) return match.answer;
      }

      for (const [key, value] of Object.entries(resp.answers)) {
        if (keyMatches.some((matchKey) => key.toLowerCase().includes(matchKey))) {
          return formatAnswerValue(value);
        }
      }
    }

    return null;
  };

  const findPhq9Score = (): string | null => {
    if (!summary) return null;
    const score = summary.scores.find((item) => item.score_type.toLowerCase().includes('phq'));
    if (!score) return null;
    const band = score.severity_band ? score.severity_band.toLowerCase() : null;
    return `${score.total_score}${band ? ` (${band})` : ''}`;
  };

  const hasSafetyConcerns = (): boolean => {
    if (!summary) return false;
    const keywordMatch = (text: string) =>
      ['suicide', 'self-harm', 'self harm', 'safety', 'harm'].some((keyword) =>
        text.toLowerCase().includes(keyword)
      );

    if (summary.risk_flags.some((flag) => flag.severity === 'CRITICAL' || flag.severity === 'HIGH')) {
      return true;
    }

    if (summary.risk_flags.some((flag) => keywordMatch(flag.flag_type))) {
      return true;
    }

    if (summary.draft_disposition?.explanations?.some((exp) => keywordMatch(exp || ''))) {
      return true;
    }

    return false;
  };

  const formatTimelineActor = (entry: TimelineEntry): string => {
    if (entry.actor_type === 'system') return 'System';
    if (entry.actor_name) return entry.actor_name;
    return 'Clinician';
  };

  const formatPathwayLabel = (pathway: string | null): string => {
    if (!pathway) return 'Unknown pathway';
    return pathway
      .replace(/_/g, ' ')
      .toLowerCase()
      .replace(/\b\w/g, (c) => c.toUpperCase());
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

  const assignedUserId = summary?.case.assigned_to_user_id ?? null;
  const assignedUserName = summary?.case.assigned_to_user_name || '-';
  const isAssignedToMe = !!assignedUserId && assignedUserId === currentUserId;
  const canClaimCase =
    currentUserRole === 'clinician' ||
    currentUserRole === 'clinical_lead' ||
    currentUserRole === 'admin';

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
  const isRedAmberFinalized = isFinalized
    && (summary.case.tier?.toLowerCase() === 'red' || summary.case.tier?.toLowerCase() === 'amber');
  const tier = summary.case.tier?.toLowerCase() || null;
  const isBookableTier = tier === 'green' || tier === 'blue';
  const isBookingRestricted = tier === 'amber' || tier === 'red';
  const confirmBannerText = isBookableTier
    ? 'Next step: Patient can now book an appointment.'
    : 'Next step: Clinician review required before booking.';
  const confirmPathwayLabel = formatPathwayLabel(
    summary.draft_disposition?.pathway || summary.case.pathway || null
  );
  const editReasonNeeded = editingSection
    ? (editingSection === 'identifiers'
        ? getChangedFieldsForSection().length > 0
        : getChangedFieldsForSection().some((field) => REASON_REQUIRED_FIELDS.includes(field)))
    : false;
  const timelineEntries = (summary.timeline || [])
    .filter((entry) => entry.timestamp)
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  const primaryComplaint = findPrimaryComplaint();
  const phq9Score = findPhq9Score();
  const safetyLine = hasSafetyConcerns() ? 'Safety concerns flagged' : 'No current safety concerns';
  const rulesetVersion = summary.draft_disposition?.ruleset_version || summary.case.ruleset_version || 'Unknown';

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
          <Link href="/governance/pilot-feedback" className={styles.navItem}>
            Pilot Feedback
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

        {/* Clinical Review Banner - RED/AMBER cases */}
        {summary && !isFinalized && (summary.case.tier?.toLowerCase() === 'red' || summary.case.tier?.toLowerCase() === 'amber') && (
          <div className={`${styles.clinicalReviewBanner} ${summary.case.tier?.toLowerCase() === 'red' ? styles.bannerRed : styles.bannerAmber}`}>
            <div className={styles.bannerIcon}>
              {summary.case.tier?.toLowerCase() === 'red' ? '⚠️' : '🔒'}
            </div>
            <div className={styles.bannerContent}>
              <strong>Clinical review required — booking restricted</strong>
              <p>
                {summary.case.tier?.toLowerCase() === 'red'
                  ? 'This patient may be at immediate risk. Review the assessment and take appropriate action before proceeding.'
                  : 'A clinician must review this assessment before the patient can book an appointment.'}
              </p>
            </div>
          </div>
        )}

        {summary.final_disposition && !summary.final_disposition.is_override && showConfirmBanner && (
          <div className={styles.confirmBanner}>
            <strong>Disposition confirmed</strong>
            <span>{confirmBannerText}</span>
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

          <div className={styles.ownershipStrip}>
            <span className={styles.ownershipLabel}>Assigned to:</span>
            <span className={styles.ownershipValue}>
              {assignedUserId ? assignedUserName : '—'}
            </span>
            {!assignedUserId && canClaimCase && (
              <button
                type="button"
                className={styles.ownershipAction}
                onClick={handleClaimCase}
              >
                Claim case
              </button>
            )}
            {assignedUserId && isAssignedToMe && canClaimCase && (
              <button
                type="button"
                className={styles.ownershipAction}
                onClick={handleUnassignCase}
              >
                Unassign
              </button>
            )}
          </div>

          {/* Patient Summary Header */}
          {patientDetails && (
            <div className={styles.patientSummaryHeader}>
              <div className={styles.patientSummaryItem}>
                <span className={styles.patientSummaryLabel}>Age:</span>
                <span className={styles.patientSummaryValue}>
                  {patientDetails.date_of_birth
                    ? Math.floor((Date.now() - new Date(patientDetails.date_of_birth).getTime()) / (365.25 * 24 * 60 * 60 * 1000))
                    : '—'}
                </span>
              </div>
              <div className={styles.patientSummaryItem}>
                <span className={styles.patientSummaryLabel}>Postcode:</span>
                <span className={styles.patientSummaryValue}>
                  {patientDetails.postcode || '—'}
                </span>
              </div>
              <div className={styles.patientSummaryItem}>
                <span className={styles.patientSummaryLabel}>Language:</span>
                <span className={styles.patientSummaryValue}>
                  {patientDetails.preferred_language || 'English'}
                </span>
              </div>
              <div className={styles.patientSummaryItem}>
                <span className={styles.patientSummaryLabel}>Contact:</span>
                <span className={styles.patientSummaryValue}>
                  {patientDetails.preferred_contact_method || 'email'}
                </span>
              </div>
              {patientDetails.interpreter_required && (
                <span className={`${styles.patientFlagIcon} ${styles.interpreter}`} title="Interpreter Required">
                  🌐
                </span>
              )}
              {patientDetails.reasonable_adjustments_required && (
                <span className={`${styles.patientFlagIcon} ${styles.adjustments}`} title="Reasonable Adjustments Required">
                  ♿
                </span>
              )}
              {patientDetails.preferences?.requires_accessibility_support && (
                <span className={`${styles.patientFlagIcon} ${styles.adjustments}`} title="Accessibility Support Needed">
                  👁
                </span>
              )}
              <div className={styles.patientSummaryMeta}>
                {patientDetails.updated_at && (
                  <span className={styles.lastUpdated}>
                    Updated {new Date(patientDetails.updated_at).toLocaleDateString()}
                  </span>
                )}
                <button
                  onClick={() => setActiveTab('patient-details')}
                  className={styles.viewHistoryLink}
                >
                  View details →
                </button>
              </div>
            </div>
          )}

          {/* Why This Pathway? */}
          {summary.draft_disposition && (
            <div className={styles.whyPathway}>
              <button
                className={styles.whyPathwayToggle}
                onClick={() => {
                  if (!whyPathwayStorageKey) return;
                  setShowWhyPathway((prev) => {
                    const next = !prev;
                    localStorage.setItem(whyPathwayStorageKey, String(next));
                    return next;
                  });
                }}
              >
                {showWhyPathway ? 'v' : '>'} Why this pathway?
              </button>
              {showWhyPathway && (
                <div className={styles.rulesSummary}>
                  <div className={styles.rulesIntro}>Why this pathway was selected</div>
                  <ul className={styles.rulesList}>
                    <li>PHQ-9 score: {phq9Score || 'Not recorded'}</li>
                    <li>{safetyLine}</li>
                    <li>Primary complaint: {primaryComplaint || 'Not recorded'}</li>
                    <li>Ruleset: {rulesetVersion}</li>
                  </ul>
                  {summary.draft_disposition.rules_fired.length > 0 && (
                    <div className={styles.ruleTriggers}>
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
            {isBookingRestricted && (
              <button
                className={styles.restrictedButton}
                disabled
                title="Booking restricted - clinician review required"
              >
                Book Appointment
              </button>
            )}
            <div className={styles.confirmBlock}>
              <button
                className={styles.confirmButton}
                onClick={() => setShowConfirmPrompt(true)}
                disabled={isDisposing || !summary.draft_disposition}
                title="Confirm disposition (Enter)"
              >
                {isDisposing ? 'Confirming...' : 'Confirm Disposition'}
                <kbd>Enter</kbd>
              </button>
              <div className={styles.confirmHint}>
                Confirms the recommended pathway. You can override this with a rationale if needed.
              </div>
            </div>
            {(summary.case.tier?.toLowerCase() === 'red' || summary.case.tier?.toLowerCase() === 'amber') && (
              <button
                onClick={() => setShowIncidentPrompt(true)}
                className={styles.incidentButton}
                title="Create clinical incident record"
              >
                📋 Incident
              </button>
            )}
            <button onClick={handleDownloadPdf} className={styles.downloadButton}>
              PDF
            </button>
          </div>
        )}

        {/* Tabs */}
        <div className={styles.tabs}>
          {(['overview', 'patient-details', 'scores', 'answers', 'disposition'] as TabType[]).map((tab) => (
            <button
              key={tab}
              className={activeTab === tab ? styles.tabActive : styles.tab}
              onClick={() => setActiveTab(tab)}
            >
              {tab === 'patient-details' ? 'Patient Details' : tab.charAt(0).toUpperCase() + tab.slice(1)}
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

              <section className={styles.section}>
                <div className={styles.sectionHeader}>
                  <h3>Case Timeline</h3>
                  <button
                    type="button"
                    className={styles.timelineToggle}
                    onClick={() => setShowTimeline((prev) => !prev)}
                  >
                    {showTimeline ? 'Hide' : 'Show'}
                  </button>
                </div>
                {!showTimeline && (
                  <p className={styles.muted}>Timeline collapsed</p>
                )}
                {showTimeline && (
                  <div className={styles.timelineList}>
                    {timelineEntries.length === 0 ? (
                      <p className={styles.muted}>No timeline events recorded</p>
                    ) : (
                      timelineEntries.map((entry, index) => (
                        <div key={`${entry.label}-${entry.timestamp}-${index}`} className={styles.timelineItem}>
                          <div className={styles.timelineLabel}>{entry.label}</div>
                          <div className={styles.timelineMeta}>
                            <span>{new Date(entry.timestamp).toLocaleString()}</span>
                            <span className={styles.timelineActor}>{formatTimelineActor(entry)}</span>
                          </div>
                        </div>
                      ))
                    )}
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

              {isRedAmberFinalized && showFeedbackPrompt && (
                <section className={styles.section}>
                  <div className={styles.feedbackPrompt}>
                    <div>
                      <h3>Quick feedback on this case</h3>
                      <p className={styles.feedbackPromptText}>
                        Did anything worry you during this RED/AMBER case?
                      </p>
                    </div>
                    <div className={styles.feedbackActions}>
                      <Link
                        href={`/governance/pilot-feedback?window=POST_CASE&case_id=${caseId}`}
                        className={styles.feedbackLink}
                      >
                        Give feedback (2-3 min)
                      </Link>
                      <button
                        type="button"
                        className={styles.feedbackDismiss}
                        onClick={() => setShowFeedbackPrompt(false)}
                      >
                        Not now
                      </button>
                    </div>
                  </div>
                </section>
              )}
            </div>
          )}

          {activeTab === 'patient-details' && (
            <div className={styles.patientDetailsGrid}>
              {patientDetailsLoading ? (
                /* Loading Skeletons */
                <>
                  {[1, 2, 3, 4].map((i) => (
                    <section key={i} className={styles.patientSection}>
                      <div className={styles.skeletonTitle} />
                      <div className={styles.skeletonLine} />
                      <div className={styles.skeletonLine} />
                      <div className={styles.skeletonLineShort} />
                      <div className={styles.skeletonLine} />
                    </section>
                  ))}
                </>
              ) : patientDetailsError ? (
                /* Error State */
                <div className={styles.patientDetailsError}>
                  <div className={styles.errorIcon}>⚠️</div>
                  <p>{patientDetailsError}</p>
                  <button onClick={retryPatientDetails} className={styles.retryButton}>
                    Retry
                  </button>
                </div>
              ) : !patientDetails ? (
                <p className={styles.muted}>Patient details unavailable</p>
              ) : (
                <>
                  {/* Section 1: Identity & Demographics */}
                  <section className={styles.patientSection}>
                    <div className={styles.sectionHeaderEditable}>
                      <h3>Identity & Demographics</h3>
                      {canEditSection('identity') && editingSection !== 'identity' && (
                        <button
                          className={styles.editButton}
                          onClick={() => startEditSection('identity')}
                        >
                          Edit
                        </button>
                      )}
                    </div>

                    {editingSection === 'identity' ? (
                      <div className={styles.editForm}>
                        {editError && <div className={styles.editError}>{editError}</div>}
                        <div className={styles.editFormGrid}>
                          <div className={styles.editField}>
                            <label>First Name *</label>
                            <input
                              type="text"
                              value={editForm.first_name as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, first_name: e.target.value })}
                            />
                          </div>
                          <div className={styles.editField}>
                            <label>Last Name *</label>
                            <input
                              type="text"
                              value={editForm.last_name as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, last_name: e.target.value })}
                            />
                          </div>
                          <div className={styles.editField}>
                            <label>Preferred Name</label>
                            <input
                              type="text"
                              value={editForm.preferred_name as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, preferred_name: e.target.value })}
                            />
                          </div>
                          <div className={styles.editField}>
                            <label>Date of Birth *</label>
                            <input
                              type="date"
                              value={editForm.date_of_birth as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, date_of_birth: e.target.value })}
                            />
                          </div>
                          <div className={styles.editField}>
                            <label>Sex at Birth</label>
                            <select
                              value={editForm.sex_at_birth as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, sex_at_birth: e.target.value })}
                            >
                              <option value="">Select...</option>
                              <option value="male">Male</option>
                              <option value="female">Female</option>
                              <option value="intersex">Intersex</option>
                              <option value="prefer_not_to_say">Prefer not to say</option>
                            </select>
                          </div>
                          <div className={styles.editField}>
                            <label>Gender Identity</label>
                            <input
                              type="text"
                              value={editForm.gender_identity as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, gender_identity: e.target.value })}
                            />
                          </div>
                          <div className={styles.editField}>
                            <label>Ethnicity</label>
                            <input
                              type="text"
                              value={editForm.ethnicity as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, ethnicity: e.target.value })}
                            />
                          </div>
                          <div className={styles.editField}>
                            <label>Preferred Language</label>
                            <input
                              type="text"
                              value={editForm.preferred_language as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, preferred_language: e.target.value })}
                            />
                          </div>
                          <div className={styles.editFieldCheckbox}>
                            <label>
                              <input
                                type="checkbox"
                                checked={editForm.interpreter_required as boolean || false}
                                onChange={(e) => setEditForm({ ...editForm, interpreter_required: e.target.checked })}
                              />
                              Interpreter Required
                            </label>
                          </div>
                        </div>
                        {editReasonNeeded && (
                          <div className={styles.editReasonBox}>
                            <label>Reason for changes (required for sensitive updates)</label>
                            <textarea
                              value={editReason}
                              onChange={(e) => setEditReason(e.target.value)}
                              placeholder="Why are you making this change?"
                              rows={2}
                            />
                          </div>
                        )}
                        <div className={styles.editActions}>
                          <button onClick={cancelEdit} className={styles.cancelButton} disabled={editSaving}>
                            Cancel
                          </button>
                          <button onClick={saveEdit} className={styles.saveButton} disabled={editSaving}>
                            {editSaving ? 'Saving...' : 'Save Changes'}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <dl className={styles.dl}>
                        <dt>Full Name</dt>
                        <dd>{patientDetails.first_name} {patientDetails.last_name}</dd>
                        <dt>Preferred Name</dt>
                        <dd>{patientDetails.preferred_name || <span className={styles.notRecorded}>Not recorded</span>}</dd>
                        <dt>Date of Birth</dt>
                        <dd>
                          {patientDetails.date_of_birth ? (
                            <>
                              {patientDetails.date_of_birth}
                              <span className={styles.ageBadge}>
                                {Math.floor((Date.now() - new Date(patientDetails.date_of_birth).getTime()) / (365.25 * 24 * 60 * 60 * 1000))} years
                              </span>
                            </>
                          ) : <span className={styles.notRecorded}>Not recorded</span>}
                        </dd>
                        <dt>Sex at Birth</dt>
                        <dd>{patientDetails.sex_at_birth ? patientDetails.sex_at_birth.replace(/_/g, ' ') : <span className={styles.notRecorded}>Not recorded</span>}</dd>
                        <dt>Gender Identity</dt>
                        <dd>{patientDetails.gender_identity || <span className={styles.notRecorded}>Not recorded</span>}</dd>
                        <dt>Ethnicity</dt>
                        <dd>{patientDetails.ethnicity || <span className={styles.notRecorded}>Not recorded</span>}</dd>
                        <dt>Preferred Language</dt>
                        <dd>
                          {patientDetails.preferred_language || <span className={styles.notRecorded}>Not recorded</span>}
                          {patientDetails.interpreter_required && (
                            <span className={styles.flagBadge}>Interpreter Required</span>
                          )}
                        </dd>
                      </dl>
                    )}
                  </section>

                  {/* Section 2: Contact */}
                  <section className={styles.patientSection}>
                    <div className={styles.sectionHeaderEditable}>
                      <h3>Contact</h3>
                      {canEditSection('contact') && editingSection !== 'contact' && (
                        <button
                          className={styles.editButton}
                          onClick={() => startEditSection('contact')}
                        >
                          Edit
                        </button>
                      )}
                    </div>

                    {editingSection === 'contact' ? (
                      <div className={styles.editForm}>
                        {editError && <div className={styles.editError}>{editError}</div>}
                        <div className={styles.editFormGrid}>
                          <div className={styles.editField}>
                            <label>Email</label>
                            <input
                              type="email"
                              value={editForm.email as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                            />
                          </div>
                          <div className={styles.editField}>
                            <label>Phone (E.164 format)</label>
                            <input
                              type="tel"
                              value={editForm.phone_e164 as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, phone_e164: e.target.value })}
                              placeholder="+447..."
                            />
                          </div>
                          <div className={styles.editField}>
                            <label>Preferred Contact Method</label>
                            <select
                              value={editForm.preferred_contact_method as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, preferred_contact_method: e.target.value })}
                            >
                              <option value="">Select...</option>
                              <option value="email">Email</option>
                              <option value="sms">SMS</option>
                              <option value="phone">Phone</option>
                            </select>
                          </div>
                          <div className={styles.editFieldCheckbox}>
                            <label>
                              <input
                                type="checkbox"
                                checked={editForm.can_leave_voicemail as boolean || false}
                                onChange={(e) => setEditForm({ ...editForm, can_leave_voicemail: e.target.checked })}
                              />
                              Can Leave Voicemail
                            </label>
                          </div>
                          <div className={styles.editFieldCheckbox}>
                            <label>
                              <input
                                type="checkbox"
                                checked={editForm.consent_to_sms as boolean || false}
                                onChange={(e) => setEditForm({ ...editForm, consent_to_sms: e.target.checked })}
                              />
                              SMS Consent
                            </label>
                          </div>
                          <div className={styles.editFieldCheckbox}>
                            <label>
                              <input
                                type="checkbox"
                                checked={editForm.consent_to_email as boolean || false}
                                onChange={(e) => setEditForm({ ...editForm, consent_to_email: e.target.checked })}
                              />
                              Email Consent
                            </label>
                          </div>
                          <div className={styles.editField}>
                            <label>Emergency Contact Pointer</label>
                            <select
                              value={editForm.emergency_contact_id as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, emergency_contact_id: e.target.value })}
                            >
                              <option value="">None</option>
                              {patientDetails.contacts
                                .filter((contact) => contact.contact_type === 'emergency')
                                .map((contact) => (
                                  <option key={contact.id} value={contact.id}>
                                    {contact.name || contact.organisation || contact.contact_type}
                                  </option>
                                ))}
                            </select>
                          </div>
                          <div className={styles.editField}>
                            <label>Primary GP Pointer</label>
                            <select
                              value={editForm.primary_gp_contact_id as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, primary_gp_contact_id: e.target.value })}
                            >
                              <option value="">None</option>
                              {patientDetails.contacts
                                .filter((contact) => contact.contact_type === 'gp')
                                .map((contact) => (
                                  <option key={contact.id} value={contact.id}>
                                    {contact.organisation || contact.name || contact.contact_type}
                                  </option>
                                ))}
                            </select>
                          </div>
                        </div>
                        {editReasonNeeded && (
                          <div className={styles.editReasonBox}>
                            <label>Reason for changes (required for sensitive updates)</label>
                            <textarea
                              value={editReason}
                              onChange={(e) => setEditReason(e.target.value)}
                              placeholder="Why are you making this change?"
                              rows={2}
                            />
                          </div>
                        )}
                        <div className={styles.editActions}>
                          <button onClick={cancelEdit} className={styles.cancelButton} disabled={editSaving}>
                            Cancel
                          </button>
                          <button onClick={saveEdit} className={styles.saveButton} disabled={editSaving}>
                            {editSaving ? 'Saving...' : 'Save Changes'}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <dl className={styles.dl}>
                        <dt>Email</dt>
                        <dd className={styles.copyableField}>
                          <a href={`mailto:${patientDetails.email}`}>{patientDetails.email}</a>
                          <button
                            className={styles.copyButton}
                            onClick={() => navigator.clipboard.writeText(patientDetails.email)}
                            title="Copy email"
                          >
                            📋
                          </button>
                        </dd>
                        <dt>Phone</dt>
                        <dd className={styles.copyableField}>
                          {patientDetails.phone_e164 ? (
                            <>
                              <a href={`tel:${patientDetails.phone_e164}`}>{patientDetails.phone_e164}</a>
                              <button
                                className={styles.copyButton}
                                onClick={() => navigator.clipboard.writeText(patientDetails.phone_e164!)}
                                title="Copy phone"
                              >
                                📋
                              </button>
                            </>
                          ) : (
                            <span className={styles.notRecorded}>Not recorded</span>
                          )}
                        </dd>
                        <dt>Preferred Contact</dt>
                        <dd>{patientDetails.preferred_contact_method || <span className={styles.notRecorded}>Not recorded</span>}</dd>
                        <dt>Voicemail Permission</dt>
                        <dd>{patientDetails.can_leave_voicemail ? 'Yes' : 'No'}</dd>
                        <dt>SMS Consent</dt>
                        <dd>{patientDetails.consent_to_sms ? 'Yes' : 'No'}</dd>
                        <dt>Email Consent</dt>
                        <dd>{patientDetails.consent_to_email ? 'Yes' : 'No'}</dd>
                      </dl>
                    )}

                    {/* Emergency Contact */}
                    {patientDetails.emergency_contact && (
                      <div className={styles.contactCard}>
                        <h4>Emergency Contact</h4>
                        <dl className={styles.dl}>
                          <dt>Name</dt>
                          <dd>{patientDetails.emergency_contact.name || '—'}</dd>
                          <dt>Relationship</dt>
                          <dd>{patientDetails.emergency_contact.relationship_to_patient || '—'}</dd>
                          <dt>Phone</dt>
                          <dd>{patientDetails.emergency_contact.phone_e164 || '—'}</dd>
                        </dl>
                      </div>
                    )}

                    {/* GP Contact */}
                    {patientDetails.primary_gp_contact && (
                      <div className={styles.contactCard}>
                        <h4>GP / Primary Care</h4>
                        <dl className={styles.dl}>
                          <dt>Practice</dt>
                          <dd>{patientDetails.primary_gp_contact.organisation || '—'}</dd>
                          <dt>Name</dt>
                          <dd>{patientDetails.primary_gp_contact.name || '—'}</dd>
                          <dt>Phone</dt>
                          <dd>{patientDetails.primary_gp_contact.phone_e164 || '—'}</dd>
                        </dl>
                      </div>
                    )}
                  </section>

                  {/* Section 2b: Contacts */}
                  <section className={styles.patientSection}>
                    <div className={styles.sectionHeaderEditable}>
                      <h3>Contacts</h3>
                      {canEditSection('contacts') && editingSection !== 'contacts' && (
                        <button
                          className={styles.editButton}
                          onClick={() => startEditSection('contacts')}
                        >
                          Add contact
                        </button>
                      )}
                    </div>

                    {editingSection === 'contacts' ? (
                      <div className={styles.editForm}>
                        {editError && <div className={styles.editError}>{editError}</div>}
                        <div className={styles.editFormGrid}>
                          <div className={styles.editField}>
                            <label>Contact Type</label>
                            <select
                              value={editForm.contact_type as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, contact_type: e.target.value })}
                            >
                              <option value="">Select...</option>
                              <option value="emergency">Emergency</option>
                              <option value="gp">GP</option>
                              <option value="next_of_kin">Next of Kin</option>
                              <option value="other">Other</option>
                            </select>
                          </div>
                          <div className={styles.editField}>
                            <label>Name</label>
                            <input
                              type="text"
                              value={editForm.name as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                            />
                          </div>
                          <div className={styles.editField}>
                            <label>Relationship to Patient</label>
                            <input
                              type="text"
                              value={editForm.relationship_to_patient as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, relationship_to_patient: e.target.value })}
                            />
                          </div>
                          <div className={styles.editField}>
                            <label>Phone</label>
                            <input
                              type="tel"
                              value={editForm.phone_e164 as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, phone_e164: e.target.value })}
                            />
                          </div>
                          <div className={styles.editField}>
                            <label>Email</label>
                            <input
                              type="email"
                              value={editForm.email as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                            />
                          </div>
                          <div className={styles.editField}>
                            <label>Organisation</label>
                            <input
                              type="text"
                              value={editForm.organisation as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, organisation: e.target.value })}
                            />
                          </div>
                          <div className={styles.editFieldFull}>
                            <label>Notes</label>
                            <textarea
                              value={editForm.notes as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                              rows={3}
                            />
                          </div>
                        </div>
                        <div className={styles.editActions}>
                          <button onClick={cancelEdit} className={styles.cancelButton} disabled={editSaving}>
                            Cancel
                          </button>
                          <button onClick={saveEdit} className={styles.saveButton} disabled={editSaving}>
                            {editSaving ? 'Saving...' : 'Save Contact'}
                          </button>
                        </div>
                      </div>
                    ) : patientDetails.contacts.length > 0 ? (
                      patientDetails.contacts.map((contact) => (
                        <div key={contact.id} className={styles.contactCard}>
                          <div className={styles.contactHeader}>
                            <span className={styles.contactType}>{contact.contact_type.replace(/_/g, ' ')}</span>
                            {canEditSection('contacts') && (
                              <button
                                className={styles.editButtonSmall}
                                onClick={() => startEditSection('contacts', contact.id)}
                              >
                                Edit
                              </button>
                            )}
                          </div>
                          <dl className={styles.dl}>
                            <dt>Name</dt>
                            <dd>{contact.name || '-'}</dd>
                            <dt>Relationship</dt>
                            <dd>{contact.relationship_to_patient || '-'}</dd>
                            <dt>Phone</dt>
                            <dd>{contact.phone_e164 || '-'}</dd>
                            <dt>Email</dt>
                            <dd>{contact.email || '-'}</dd>
                            <dt>Organisation</dt>
                            <dd>{contact.organisation || '-'}</dd>
                          </dl>
                        </div>
                      ))
                    ) : (
                      <p className={styles.muted}>No contacts recorded</p>
                    )}
                  </section>

                  {/* Section 3: Address */}
                  <section className={styles.patientSection}>
                    <div className={styles.sectionHeaderEditable}>
                      <h3>Address</h3>
                      {canEditSection('address') && editingSection !== 'address' && (
                        <button
                          className={styles.editButton}
                          onClick={() => startEditSection('address')}
                        >
                          Add address
                        </button>
                      )}
                    </div>
                    <div className={styles.postcodeDisplay}>
                      <span className={styles.postcodeLabel}>Postcode</span>
                      <span className={styles.postcodeValue}>{patientDetails.postcode || '-'}</span>
                    </div>
                    {editingSection === 'address' && (
                      <div className={styles.editForm}>
                        {editError && <div className={styles.editError}>{editError}</div>}
                        <div className={styles.editFormGrid}>
                          <div className={styles.editField}>
                            <label>Type</label>
                            <select
                              value={editForm.type as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, type: e.target.value })}
                            >
                              <option value="">Select...</option>
                              <option value="home">Home</option>
                              <option value="current">Current</option>
                              <option value="billing">Billing</option>
                              <option value="other">Other</option>
                            </select>
                          </div>
                          <div className={styles.editField}>
                            <label>Line 1</label>
                            <input
                              type="text"
                              value={editForm.line1 as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, line1: e.target.value })}
                            />
                          </div>
                          <div className={styles.editField}>
                            <label>Line 2</label>
                            <input
                              type="text"
                              value={editForm.line2 as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, line2: e.target.value })}
                            />
                          </div>
                          <div className={styles.editField}>
                            <label>City</label>
                            <input
                              type="text"
                              value={editForm.city as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, city: e.target.value })}
                            />
                          </div>
                          <div className={styles.editField}>
                            <label>County</label>
                            <input
                              type="text"
                              value={editForm.county as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, county: e.target.value })}
                            />
                          </div>
                          <div className={styles.editField}>
                            <label>Postcode</label>
                            <input
                              type="text"
                              value={editForm.postcode as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, postcode: e.target.value })}
                            />
                          </div>
                          <div className={styles.editField}>
                            <label>Country</label>
                            <input
                              type="text"
                              value={editForm.country as string || 'GB'}
                              onChange={(e) => setEditForm({ ...editForm, country: e.target.value })}
                            />
                          </div>
                          <div className={styles.editField}>
                            <label>Valid From</label>
                            <input
                              type="date"
                              value={editForm.valid_from as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, valid_from: e.target.value })}
                            />
                          </div>
                          <div className={styles.editField}>
                            <label>Valid To</label>
                            <input
                              type="date"
                              value={editForm.valid_to as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, valid_to: e.target.value })}
                            />
                          </div>
                          <div className={styles.editFieldCheckbox}>
                            <label>
                              <input
                                type="checkbox"
                                checked={editForm.is_primary as boolean || false}
                                onChange={(e) => setEditForm({ ...editForm, is_primary: e.target.checked })}
                              />
                              Primary address
                            </label>
                          </div>
                        </div>
                        <div className={styles.editActions}>
                          <button onClick={cancelEdit} className={styles.cancelButton} disabled={editSaving}>
                            Cancel
                          </button>
                          <button onClick={saveEdit} className={styles.saveButton} disabled={editSaving}>
                            {editSaving ? 'Saving...' : 'Save Address'}
                          </button>
                        </div>
                      </div>
                    )}
                    {patientDetails.addresses.length > 0 ? (
                      patientDetails.addresses.map((addr) => (
                        <div key={addr.id} className={styles.addressCard}>
                          <div className={styles.addressHeader}>
                            <span className={styles.addressType}>{addr.type}</span>
                            {addr.is_primary && <span className={styles.primaryBadge}>Primary</span>}
                            {canEditSection('address') && (
                              <button
                                className={styles.editButtonSmall}
                                onClick={() => startEditSection('address', addr.id)}
                              >
                                Edit
                              </button>
                            )}
                          </div>
                          <div className={styles.addressLines}>
                            {addr.line1 && <div>{addr.line1}</div>}
                            {addr.line2 && <div>{addr.line2}</div>}
                            {addr.city && <div>{addr.city}</div>}
                            {addr.county && <div>{addr.county}</div>}
                            {addr.postcode && <div>{addr.postcode}</div>}
                            <div>{addr.country}</div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className={styles.muted}>No addresses on file</p>
                    )}
                  </section>

                  {/* Section 4: Safeguarding & Adjustments */}
                  <section className={styles.patientSection}>
                    <div className={styles.sectionHeaderEditable}>
                      <h3>Safeguarding & Adjustments</h3>
                      {canEditSection('safeguarding') && editingSection !== 'safeguarding' && (
                        <button
                          className={styles.editButton}
                          onClick={() => startEditSection('safeguarding')}
                        >
                          Edit
                        </button>
                      )}
                    </div>

                    {editingSection === 'safeguarding' ? (
                      <div className={styles.editForm}>
                        {editError && <div className={styles.editError}>{editError}</div>}
                        <div className={styles.editFormGrid}>
                          <div className={styles.editField}>
                            <label>Dependents / Caring Responsibilities</label>
                            <select
                              value={editForm.has_dependents === null ? '' : editForm.has_dependents ? 'yes' : 'no'}
                              onChange={(e) => setEditForm({
                                ...editForm,
                                has_dependents: e.target.value === '' ? null : e.target.value === 'yes'
                              })}
                            >
                              <option value="">Unknown</option>
                              <option value="yes">Yes</option>
                              <option value="no">No</option>
                            </select>
                          </div>
                          <div className={styles.editField}>
                            <label>Pregnant / Postnatal</label>
                            <select
                              value={editForm.is_pregnant_or_postnatal === null ? '' : editForm.is_pregnant_or_postnatal ? 'yes' : 'no'}
                              onChange={(e) => setEditForm({
                                ...editForm,
                                is_pregnant_or_postnatal: e.target.value === '' ? null : e.target.value === 'yes'
                              })}
                            >
                              <option value="">Unknown</option>
                              <option value="yes">Yes</option>
                              <option value="no">No</option>
                            </select>
                          </div>
                          <div className={styles.editFieldCheckbox}>
                            <label>
                              <input
                                type="checkbox"
                                checked={editForm.reasonable_adjustments_required as boolean || false}
                                onChange={(e) => setEditForm({ ...editForm, reasonable_adjustments_required: e.target.checked })}
                              />
                              Reasonable Adjustments Required
                            </label>
                          </div>
                        </div>
                        <div className={styles.editActions}>
                          <button onClick={cancelEdit} className={styles.cancelButton} disabled={editSaving}>
                            Cancel
                          </button>
                          <button onClick={saveEdit} className={styles.saveButton} disabled={editSaving}>
                            {editSaving ? 'Saving...' : 'Save Changes'}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <dl className={styles.dl}>
                          <dt>Dependents / Caring Responsibilities</dt>
                          <dd>
                            {patientDetails.has_dependents === null
                              ? <span className={styles.notRecorded}>Unknown</span>
                              : patientDetails.has_dependents ? 'Yes' : 'No'}
                          </dd>
                          <dt>Pregnant / Postnatal</dt>
                          <dd>
                            {patientDetails.is_pregnant_or_postnatal === null
                              ? <span className={styles.notRecorded}>Unknown</span>
                              : patientDetails.is_pregnant_or_postnatal ? 'Yes' : 'No'}
                          </dd>
                          <dt>Reasonable Adjustments Required</dt>
                          <dd>
                            {patientDetails.reasonable_adjustments_required ? (
                              <span className={styles.flagBadge}>Yes</span>
                            ) : 'No'}
                          </dd>
                        </dl>
                        {patientDetails.preferences && (
                          <dl className={styles.dl}>
                            <dt>Accessibility Support</dt>
                            <dd>
                              {patientDetails.preferences.requires_accessibility_support ? (
                                <span className={styles.flagBadge}>Yes</span>
                              ) : 'No'}
                            </dd>
                            {patientDetails.preferences.accessibility_notes && (
                              <>
                                <dt>Accessibility Notes</dt>
                                <dd>{patientDetails.preferences.accessibility_notes}</dd>
                              </>
                            )}
                            {patientDetails.preferences.reasonable_adjustments_notes && (
                              <>
                                <dt>Adjustments Notes</dt>
                                <dd>{patientDetails.preferences.reasonable_adjustments_notes}</dd>
                              </>
                            )}
                          </dl>
                        )}
                      </>
                    )}
                  </section>

                  {/* Section 5: Clinical Context */}
                  <section className={styles.patientSection}>
                    <div className={styles.sectionHeaderEditable}>
                      <h3>Clinical Context</h3>
                    {canEditSection('clinical') && editingSection !== 'clinical' && (
                        <button
                          className={styles.editButton}
                          onClick={() => startEditSection('clinical')}
                        >
                          Edit
                        </button>
                      )}
                    </div>

                    {editingSection === 'clinical' ? (
                      <div className={styles.editForm}>
                        {editError && <div className={styles.editError}>{editError}</div>}
                        <div className={styles.editFormGrid}>
                          <div className={`${styles.editField} ${styles.editFieldFull}`}>
                            <label>Presenting Problem</label>
                            <textarea
                              value={editForm.presenting_problem as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, presenting_problem: e.target.value })}
                              rows={3}
                            />
                          </div>
                          <div className={styles.editField}>
                            <label>Previous MH Treatment</label>
                            <select
                              value={editForm.previous_mental_health_treatment as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, previous_mental_health_treatment: e.target.value })}
                            >
                              <option value="">Select...</option>
                              <option value="none">None</option>
                              <option value="yes_unknown">Yes (unknown type)</option>
                              <option value="yes_talking_therapy">Yes (talking therapy)</option>
                              <option value="yes_psychiatry">Yes (psychiatry)</option>
                              <option value="yes_inpatient">Yes (inpatient)</option>
                            </select>
                          </div>
                          <div className={styles.editField}>
                            <label>Current Psych Medication</label>
                            <select
                              value={editForm.current_psych_medication === null ? '' : editForm.current_psych_medication ? 'yes' : 'no'}
                              onChange={(e) => setEditForm({
                                ...editForm,
                                current_psych_medication: e.target.value === '' ? null : e.target.value === 'yes'
                              })}
                            >
                              <option value="">Unknown</option>
                              <option value="yes">Yes</option>
                              <option value="no">No</option>
                            </select>
                          </div>
                          <div className={styles.editField}>
                            <label>Substance Use Level</label>
                            <select
                              value={editForm.substance_use_level as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, substance_use_level: e.target.value })}
                            >
                              <option value="">Select...</option>
                              <option value="none">None</option>
                              <option value="low">Low</option>
                              <option value="moderate">Moderate</option>
                              <option value="high">High</option>
                              <option value="unknown">Unknown</option>
                            </select>
                          </div>
                          <div className={styles.editField}>
                            <label>Physical Health Conditions</label>
                            <select
                              value={editForm.physical_health_conditions === null ? '' : editForm.physical_health_conditions ? 'yes' : 'no'}
                              onChange={(e) => setEditForm({
                                ...editForm,
                                physical_health_conditions: e.target.value === '' ? null : e.target.value === 'yes'
                              })}
                            >
                              <option value="">Unknown</option>
                              <option value="yes">Yes</option>
                              <option value="no">No</option>
                            </select>
                          </div>
                          <div className={`${styles.editField} ${styles.editFieldFull}`}>
                            <label>Physical Health Notes</label>
                            <textarea
                              value={editForm.physical_health_notes as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, physical_health_notes: e.target.value })}
                              rows={2}
                            />
                          </div>
                          <div className={styles.editField}>
                            <label>Neurodevelopmental Needs</label>
                            <select
                              value={editForm.neurodevelopmental_needs === null ? '' : editForm.neurodevelopmental_needs ? 'yes' : 'no'}
                              onChange={(e) => setEditForm({
                                ...editForm,
                                neurodevelopmental_needs: e.target.value === '' ? null : e.target.value === 'yes'
                              })}
                            >
                              <option value="">Unknown</option>
                              <option value="yes">Yes</option>
                              <option value="no">No</option>
                            </select>
                          </div>
                          <div className={`${styles.editField} ${styles.editFieldFull}`}>
                            <label>
                              Risk Notes
                              <span className={styles.staffOnlyLabel}>Staff-only (not visible to patient)</span>
                            </label>
                            <textarea
                              value={editForm.risk_notes_staff_only as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, risk_notes_staff_only: e.target.value })}
                              rows={3}
                              className={styles.riskNotesInput}
                            />
                          </div>
                        </div>
                        <div className={styles.editActions}>
                          <button onClick={cancelEdit} className={styles.cancelButton} disabled={editSaving}>
                            Cancel
                          </button>
                          <button onClick={saveEdit} className={styles.saveButton} disabled={editSaving}>
                            {editSaving ? 'Saving...' : 'Save Changes'}
                          </button>
                        </div>
                      </div>
                    ) : patientDetails.clinical_profile ? (
                      <dl className={styles.dl}>
                        <dt>Presenting Problem</dt>
                        <dd className={styles.presentingProblem}>
                          {patientDetails.clinical_profile.presenting_problem || <span className={styles.notRecorded}>Not recorded</span>}
                        </dd>
                        <dt>Previous MH Treatment</dt>
                        <dd>
                          {patientDetails.clinical_profile.previous_mental_health_treatment
                            ? patientDetails.clinical_profile.previous_mental_health_treatment.replace(/_/g, ' ')
                            : <span className={styles.notRecorded}>Not recorded</span>}
                        </dd>
                        <dt>Current Psych Medication</dt>
                        <dd>
                          {patientDetails.clinical_profile.current_psych_medication === null
                            ? <span className={styles.notRecorded}>Unknown</span>
                            : patientDetails.clinical_profile.current_psych_medication
                            ? 'Yes'
                            : 'No'}
                        </dd>
                        {patientDetails.clinical_profile.current_medication_list && patientDetails.clinical_profile.current_medication_list.length > 0 && (
                          <>
                            <dt>Medications</dt>
                            <dd>
                              <ul className={styles.medicationList}>
                                {patientDetails.clinical_profile.current_medication_list.map((med, idx) => (
                                  <li key={idx}>
                                    {med.name} - {med.dose} ({med.frequency})
                                  </li>
                                ))}
                              </ul>
                            </dd>
                          </>
                        )}
                        <dt>Substance Use Level</dt>
                        <dd>
                          {patientDetails.clinical_profile.substance_use_level
                            ? patientDetails.clinical_profile.substance_use_level.replace(/_/g, ' ')
                            : <span className={styles.notRecorded}>Not recorded</span>}
                        </dd>
                        <dt>Physical Health Conditions</dt>
                        <dd>
                          {patientDetails.clinical_profile.physical_health_conditions === null
                            ? <span className={styles.notRecorded}>Unknown</span>
                            : patientDetails.clinical_profile.physical_health_conditions
                            ? 'Yes'
                            : 'No'}
                        </dd>
                        {patientDetails.clinical_profile.physical_health_notes && (
                          <>
                            <dt>Physical Health Notes</dt>
                            <dd>{patientDetails.clinical_profile.physical_health_notes}</dd>
                          </>
                        )}
                        <dt>Neurodevelopmental Needs</dt>
                        <dd>
                          {patientDetails.clinical_profile.neurodevelopmental_needs === null
                            ? <span className={styles.notRecorded}>Unknown</span>
                            : patientDetails.clinical_profile.neurodevelopmental_needs
                            ? 'Yes'
                            : 'No'}
                        </dd>
                        {patientDetails.clinical_profile.risk_notes_staff_only && (
                          <>
                            <dt>
                              Risk Notes
                              <span className={styles.staffOnlyLabel}>Staff-only (not visible to patient)</span>
                            </dt>
                            <dd className={styles.riskNotes}>
                              {patientDetails.clinical_profile.risk_notes_staff_only}
                            </dd>
                          </>
                        )}
                      </dl>
                    ) : (
                      <p className={styles.muted}>No clinical profile recorded. Click Edit to add clinical context.</p>
                    )}
                  </section>

                  {/* Section 6: Preferences */}
                  <section className={styles.patientSection}>
                    <div className={styles.sectionHeaderEditable}>
                      <h3>Preferences</h3>
                    {canEditSection('preferences') && editingSection !== 'preferences' && (
                        <button
                          className={styles.editButton}
                          onClick={() => startEditSection('preferences')}
                        >
                          Edit
                        </button>
                      )}
                    </div>

                    {editingSection === 'preferences' ? (
                      <div className={styles.editForm}>
                        {editError && <div className={styles.editError}>{editError}</div>}
                        <div className={styles.editFormGrid}>
                          <div className={styles.editField}>
                            <label>Communication Channel Preference</label>
                            <select
                              value={editForm.communication_channel_preference as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, communication_channel_preference: e.target.value })}
                            >
                              <option value="">No preference</option>
                              <option value="email">Email</option>
                              <option value="sms">SMS</option>
                              <option value="phone">Phone</option>
                            </select>
                          </div>
                          <div className={styles.editField}>
                            <label>Appointment Format Preference</label>
                            <select
                              value={editForm.appointment_format_preference as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, appointment_format_preference: e.target.value })}
                            >
                              <option value="">No preference</option>
                              <option value="in_person">In person</option>
                              <option value="video">Video</option>
                              <option value="phone">Phone</option>
                            </select>
                          </div>
                          <div className={styles.editFieldCheckbox}>
                            <label>
                              <input
                                type="checkbox"
                                checked={editForm.requires_accessibility_support as boolean || false}
                                onChange={(e) => setEditForm({ ...editForm, requires_accessibility_support: e.target.checked })}
                              />
                              Requires Accessibility Support
                            </label>
                          </div>
                          <div className={`${styles.editField} ${styles.editFieldFull}`}>
                            <label>Accessibility Notes</label>
                            <textarea
                              value={editForm.accessibility_notes as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, accessibility_notes: e.target.value })}
                              rows={2}
                              placeholder="e.g., hearing impairment, visual aids needed"
                            />
                          </div>
                          <div className={`${styles.editField} ${styles.editFieldFull}`}>
                            <label>Reasonable Adjustments Notes</label>
                            <textarea
                              value={editForm.reasonable_adjustments_notes as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, reasonable_adjustments_notes: e.target.value })}
                              rows={2}
                              placeholder="e.g., extra time needed, quiet room preferred"
                            />
                          </div>
                        </div>
                        <div className={styles.editActions}>
                          <button onClick={cancelEdit} className={styles.cancelButton} disabled={editSaving}>
                            Cancel
                          </button>
                          <button onClick={saveEdit} className={styles.saveButton} disabled={editSaving}>
                            {editSaving ? 'Saving...' : 'Save Changes'}
                          </button>
                        </div>
                      </div>
                    ) : patientDetails.preferences ? (
                      <dl className={styles.dl}>
                        <dt>Communication Channel</dt>
                        <dd>{patientDetails.preferences.communication_channel_preference || <span className={styles.notRecorded}>No preference</span>}</dd>
                        <dt>Appointment Format</dt>
                        <dd>
                          {patientDetails.preferences.appointment_format_preference
                            ? patientDetails.preferences.appointment_format_preference.replace(/_/g, ' ')
                            : <span className={styles.notRecorded}>No preference</span>}
                        </dd>
                        <dt>Accessibility Support</dt>
                        <dd>
                          {patientDetails.preferences.requires_accessibility_support ? (
                            <span className={styles.flagBadge}>Yes</span>
                          ) : 'No'}
                        </dd>
                        {patientDetails.preferences.accessibility_notes && (
                          <>
                            <dt>Accessibility Notes</dt>
                            <dd>{patientDetails.preferences.accessibility_notes}</dd>
                          </>
                        )}
                        {patientDetails.preferences.reasonable_adjustments_notes && (
                          <>
                            <dt>Adjustments Notes</dt>
                            <dd>{patientDetails.preferences.reasonable_adjustments_notes}</dd>
                          </>
                        )}
                      </dl>
                    ) : (
                      <p className={styles.muted}>No preferences recorded. Click Edit to add preferences.</p>
                    )}
                  </section>

                  {/* Section 7: Identifiers */}
                  <section className={styles.patientSection}>
                    <div className={styles.sectionHeaderEditable}>
                      <h3>Identifiers</h3>
                      {canEditSection('identifiers') && editingSection !== 'identifiers' && (
                        <button
                          className={styles.editButton}
                          onClick={() => startEditSection('identifiers')}
                        >
                          Add identifier
                        </button>
                      )}
                    </div>
                    {editingSection === 'identifiers' ? (
                      <div className={styles.editForm}>
                        {editError && <div className={styles.editError}>{editError}</div>}
                        <div className={styles.editFormGrid}>
                          <div className={styles.editField}>
                            <label>Identifier Type</label>
                            <select
                              value={editForm.id_type as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, id_type: e.target.value })}
                            >
                              <option value="">Select...</option>
                              <option value="nhs_number">NHS Number</option>
                              <option value="private_id">Private ID</option>
                              <option value="other">Other</option>
                            </select>
                          </div>
                          <div className={styles.editField}>
                            <label>Identifier Value</label>
                            <input
                              type="text"
                              value={editForm.id_value as string || ''}
                              onChange={(e) => setEditForm({ ...editForm, id_value: e.target.value })}
                            />
                          </div>
                          <div className={styles.editFieldCheckbox}>
                            <label>
                              <input
                                type="checkbox"
                                checked={editForm.is_verified as boolean || false}
                                onChange={(e) => setEditForm({ ...editForm, is_verified: e.target.checked })}
                              />
                              Verified
                            </label>
                          </div>
                        </div>
                        {editReasonNeeded && (
                          <div className={styles.editReasonBox}>
                            <label>Reason for changes (required for identifiers)</label>
                            <textarea
                              value={editReason}
                              onChange={(e) => setEditReason(e.target.value)}
                              placeholder="Why are you making this change?"
                              rows={2}
                            />
                          </div>
                        )}
                        <div className={styles.editActions}>
                          <button onClick={cancelEdit} className={styles.cancelButton} disabled={editSaving}>
                            Cancel
                          </button>
                          <button onClick={saveEdit} className={styles.saveButton} disabled={editSaving}>
                            {editSaving ? 'Saving...' : 'Save Identifier'}
                          </button>
                        </div>
                      </div>
                    ) : (
                      (() => {
                        // Check if NHS number exists in identifiers table (preferred)
                        const nhsFromIdentifiers = patientDetails.identifiers.find(
                          (id) => id.id_type.toLowerCase() === 'nhs_number'
                        );
                        // Only show legacy field if not migrated to identifiers
                        const showLegacyNhs = patientDetails.nhs_number && !nhsFromIdentifiers;

                        const hasAnyIdentifiers = patientDetails.identifiers.length > 0 || showLegacyNhs;

                        if (!hasAnyIdentifiers) {
                          return <p className={styles.muted}>No identifiers on file</p>;
                        }

                        return (
                          <>
                            {patientDetails.identifiers.map((ident) => (
                              <div key={ident.id} className={styles.identifierCard}>
                                <div className={styles.identifierHeader}>
                                  <span className={styles.identifierType}>
                                    {ident.id_type.replace(/_/g, ' ')}
                                  </span>
                                  {canEditSection('identifiers') && (
                                    <button
                                      className={styles.editButtonSmall}
                                      onClick={() => startEditSection('identifiers', ident.id)}
                                    >
                                      Edit
                                    </button>
                                  )}
                                </div>
                                <span className={styles.identifierValue}>{ident.id_value}</span>
                                <button
                                  className={styles.copyButton}
                                  onClick={() => navigator.clipboard.writeText(ident.id_value)}
                                  title="Copy to clipboard"
                                >
                                  ??
                                </button>
                                {ident.is_verified ? (
                                  <span className={styles.verifiedBadge}>Verified</span>
                                ) : (
                                  <span className={styles.unverifiedBadge}>Unverified</span>
                                )}
                              </div>
                            ))}
                            {showLegacyNhs && (
                              <div className={styles.identifierCard}>
                                <span className={styles.identifierType}>NHS Number</span>
                                <span className={styles.identifierValue}>{patientDetails.nhs_number}</span>
                                <button
                                  className={styles.copyButton}
                                  onClick={() => navigator.clipboard.writeText(patientDetails.nhs_number!)}
                                  title="Copy to clipboard"
                                >
                                  ??
                                </button>
                                <span className={styles.legacyBadge}>Legacy</span>
                              </div>
                            )}
                          </>
                        );
                      })()
                    )}
                  </section>

                  {/* Section 7: Update History */}
                  <section className={styles.patientSection}>
                    <h3>Update History</h3>
                    <Link
                      href={`/dashboard/patients/${patientDetails.id}/history`}
                      className={styles.historyLink}
                    >
                      View change history →
                    </Link>
                  </section>
                </>
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
                    <div className={styles.answerList}>
                      {(resp.answers_human && resp.answers_human.length > 0
                        ? resp.answers_human
                        : buildFallbackAnswers(resp.answers)
                      ).map((item) => (
                        <div key={`${resp.id}-${item.field_id}`} className={styles.answerItem}>
                          <div className={styles.answerQuestion}>{item.question}</div>
                          <div className={styles.answerValue}>{item.answer}</div>
                        </div>
                      ))}
                    </div>
                    <button
                      type="button"
                      className={styles.rawToggle}
                      onClick={() =>
                        setShowRawAnswers((prev) => ({
                          ...prev,
                          [resp.id]: !prev[resp.id],
                        }))
                      }
                    >
                      {showRawAnswers[resp.id] ? 'Hide raw data' : 'View raw data'}
                    </button>
                    {showRawAnswers[resp.id] && (
                      <pre className={styles.answersJson}>{JSON.stringify(resp.answers, null, 2)}</pre>
                    )}
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
                          <button
                            onClick={() => setShowConfirmPrompt(true)}
                            disabled={isDisposing}
                            className={styles.confirmButtonLarge}
                          >
                            {isDisposing ? 'Confirming...' : 'Confirm Disposition'}
                          </button>
                        </div>
                      ) : (
                        <div className={styles.overrideSection}>
                          <div className={styles.overrideInfo}>
                            <h4>Confirm clinical override</h4>
                            <p className={styles.overrideExplainer}>
                              Please record your clinical rationale. This will be saved as part of the patient&apos;s record.
                            </p>
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
                            <label>Clinical Rationale *</label>
                            <textarea
                              value={overrideForm.rationale}
                              onChange={(e) =>
                                setOverrideForm((prev) => ({ ...prev, rationale: e.target.value }))
                              }
                              rows={4}
                              placeholder="Record your clinical rationale for this override..."
                              required
                            />
                            <span className={styles.formHint}>
                              This rationale is part of the clinical record. Minimum 10 characters.
                            </span>
                          </div>

                          <div className={styles.formGroup}>
                            <label>Additional Clinical Notes (optional)</label>
                            <textarea
                              value={overrideForm.clinical_notes}
                              onChange={(e) =>
                                setOverrideForm((prev) => ({ ...prev, clinical_notes: e.target.value }))
                              }
                              rows={3}
                              placeholder="Any additional context or notes..."
                            />
                          </div>

                          <button
                            onClick={() => setShowOverrideConfirm(true)}
                            disabled={isDisposing || overrideForm.rationale.length < 10}
                            className={styles.overrideButtonLarge}
                          >
                            Override Disposition
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

        {/* Confirm Disposition Modal */}
        {showConfirmPrompt && (
          <div className={styles.modalBackdrop} onClick={() => setShowConfirmPrompt(false)}>
            <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
              <div className={styles.modalHeader}>
                <h3>Confirm disposition</h3>
              </div>
              <div className={styles.modalBody}>
                <p className={styles.modalInfo}>
                  You are confirming: <strong>{confirmPathwayLabel}</strong>
                </p>
                <div className={styles.formGroup}>
                  <label>Clinical Notes (optional)</label>
                  <textarea
                    value={confirmNotes}
                    onChange={(e) => setConfirmNotes(e.target.value)}
                    rows={3}
                    placeholder="Add any additional notes..."
                  />
                </div>
              </div>
              <div className={styles.modalActions}>
                <button
                  className={styles.modalCancel}
                  onClick={() => setShowConfirmPrompt(false)}
                >
                  Cancel
                </button>
                <button
                  className={styles.modalConfirm}
                  onClick={handleConfirmDisposition}
                  disabled={isDisposing}
                >
                  {isDisposing ? 'Confirming...' : 'Confirm Disposition'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Override Confirmation Modal */}
        {showOverrideConfirm && (
          <div className={styles.modalBackdrop} onClick={() => setShowOverrideConfirm(false)}>
            <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
              <div className={styles.modalHeader}>
                <h3>Confirm clinical override</h3>
              </div>
              <div className={styles.modalBody}>
                <p className={styles.modalWarning}>
                  You are changing this disposition from <strong>{summary?.draft_disposition?.tier}</strong> to <strong>{overrideForm.tier}</strong>.
                </p>
                <p className={styles.modalInfo}>
                  Your rationale will be saved as part of the patient&apos;s clinical record and may be audited.
                </p>
                <div className={styles.modalRationale}>
                  <strong>Your rationale:</strong>
                  <p>{overrideForm.rationale}</p>
                </div>
              </div>
              <div className={styles.modalActions}>
                <button
                  className={styles.modalCancel}
                  onClick={() => setShowOverrideConfirm(false)}
                >
                  Cancel
                </button>
                <button
                  className={styles.modalConfirm}
                  onClick={() => {
                    setShowOverrideConfirm(false);
                    handleOverrideDisposition();
                  }}
                  disabled={isDisposing}
                >
                  {isDisposing ? 'Processing...' : 'Confirm Override'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Incident Creation Prompt */}
        {showIncidentPrompt && (
          <div className={styles.modalBackdrop} onClick={() => setShowIncidentPrompt(false)}>
            <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
              <div className={styles.modalHeader}>
                <h3>Create clinical incident record?</h3>
              </div>
              <div className={styles.modalBody}>
                <p className={styles.modalInfo}>
                  Use this to document safety concerns, escalation actions, and learning points.
                </p>
                <p className={styles.modalDetails}>
                  This creates a formal incident record that will be linked to this case for audit and governance purposes.
                </p>
              </div>
              <div className={styles.modalActions}>
                <button
                  className={styles.modalCancel}
                  onClick={() => setShowIncidentPrompt(false)}
                >
                  Not now
                </button>
                <button
                  className={styles.modalConfirm}
                  onClick={() => {
                    setShowIncidentPrompt(false);
                    router.push(`/dashboard/incidents/new?case_id=${caseId}`);
                  }}
                >
                  Create Incident Record
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}








/**
 * Staff Console Copy Dictionary (en-GB)
 *
 * Canonical source: /copy/en-GB.json
 * Copy for staff-facing components.
 */

export const copy = {
  staff: {
    triageQueue: {
      banner: 'Clinical review required - booking restricted',
    },

    case: {
      reviewRequired: 'Clinical review required',
      rulesFiredLabel: 'Rules fired',
      tier: 'Tier',
      pathway: 'Pathway',
      sla: 'SLA',
      status: 'Status',
    },

    override: {
      title: 'Confirm clinical override',
      body: 'Please record your clinical rationale. This will be saved as part of the patient\'s record.',
      rationaleLabel: 'Clinical rationale',
      rationalePlaceholder: 'Record your clinical rationale for this override...',
      rationaleHint: 'Minimum 20 characters required',
      confirmButton: 'Confirm override',
      cancelButton: 'Cancel',
    },

    incidentPrompt: {
      title: 'Create clinical incident record?',
      body: 'Use this to document safety concerns, escalation actions, and learning points.',
      createButton: 'Create incident',
      dismissButton: 'Not now',
    },

    // Legacy triage review banner (keep for compatibility)
    triage: {
      reviewBanner: {
        title: 'Clinical review required - booking restricted',
        red: 'This patient may be at immediate risk. Review the assessment and take appropriate action before proceeding.',
        amber: 'A clinician must review this assessment before the patient can book an appointment.',
      },
    },
  },

  shared: {
    emergencyBanner: {
      default: {
        title: 'This service is not for emergencies.',
        body: 'If you are in immediate danger or at risk of harming yourself or others, please call 999 or attend A&E.',
      },
      amber: {
        title: 'If you feel unsafe at any point, please call 999 or attend A&E.',
        body: 'We will contact you within 24-72 hours to arrange the next step.',
      },
      red: {
        title: 'We\'re concerned about your safety.',
        body: 'Please contact 999 now or attend your nearest A&E department. We cannot provide emergency support through this service.',
      },
    },

    ui: {
      loading: 'Loading...',
      error: 'Something went wrong. Please try again.',
      back: 'Back',
      continue: 'Continue',
      submit: 'Submit',
      cancel: 'Cancel',
      close: 'Close',
    },
  },
} as const;

export type StaffCopyDictionary = typeof copy;

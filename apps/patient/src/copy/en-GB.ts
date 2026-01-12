/**
 * Patient Portal Copy Dictionary (en-GB)
 *
 * IMPORTANT: Copy in this file is clinically reviewed.
 * Do not modify safety-critical sections without clinical sign-off.
 *
 * Canonical source: /copy/en-GB.json
 * Sections marked with [CLINICAL] require clinical review before changes.
 * Sections marked with [LEGAL] require legal review before changes.
 */

export const copy = {
  patient: {
    // =========================================================================
    // INTAKE FLOW
    // =========================================================================
    intake: {
      landing: {
        title: 'Get matched to the right mental health professional',
        subtitle: 'This short assessment helps us understand what you\'re experiencing so we can safely recommend the most appropriate care.',
        timeEstimate: 'Takes about 8-10 minutes',
        reassurance: 'Your answers are reviewed by qualified clinicians. We do not use automated diagnosis.',
        privacyNote: 'Your responses are stored securely and only shared with your care team.',
        cta: 'Start assessment',
      },

      progress: {
        stepLabel: 'Step {{current}} of {{total}} - {{label}}',
        tooltip: 'Most people complete this in one sitting. You can save and return at any time.',
      },

      // [CLINICAL] Safety framing - shown before risk questions
      safety: {
        title: 'Your safety matters',
        body: 'The next questions ask about safety and risk. We ask everyone these questions - answering honestly helps us make sure you receive the right level of support.',
        microReassurance: 'Your answers do not automatically mean emergency action. They help us plan care safely.',
      },

      // [CLINICAL] Suicide/self-harm inline support text
      si: {
        inlineSupport: 'Many people experience thoughts like these during periods of distress. Sharing this information helps us respond appropriately and safely.',
      },

      submitted: {
        title: 'Thank you - your information has been received',
        primary: 'A clinician will review your responses to determine the most appropriate next step in your care.',
        nextStepsTitle: 'What happens next:',
        nextStepsList: [
          'We review your assessment carefully',
          'We match you to the most suitable professional',
          'You\'ll be able to book an appointment or we\'ll contact you if a review is needed',
        ],
        timeline: 'Most patients hear from us within 1-2 working days.',
      },

      // Section labels for progress indicator
      sections: {
        about_you: 'About you',
        mood: 'Mood & feelings',
        anxiety: 'Anxiety',
        sleep: 'Sleep & energy',
        risk: 'Safety questions',
        history: 'History',
        preferences: 'Your preferences',
        review: 'Review',
      },
    },

    // =========================================================================
    // TRIAGE RESULT ROUTING
    // =========================================================================
    triage: {
      // GREEN/BLUE - Self-booking allowed
      green: {
        title: 'You\'re ready to book',
        subtitle: 'Based on your assessment, you can book an appointment directly.',
        pathwayExplanation: 'You\'ve been matched with: {{pathway}}',
        clinicianType: {
          therapist: 'You\'ll see a therapist who specialises in talk-based support.',
          counsellor: 'You\'ll see a counsellor for guided wellbeing support.',
          psychologist: 'You\'ll see a psychologist for structured psychological therapy.',
          psychiatrist: 'You\'ll see a psychiatrist who can discuss both therapy and medication options.',
        },
        availabilityFraming: 'Appointments are usually available within {{days}} days.',
        bookingCta: 'Choose appointment',
      },

      // AMBER - Clinician review required
      amber: {
        title: 'We\'re reviewing your assessment',
        subtitle: 'Some aspects of your assessment mean a clinician needs to review it before booking an appointment.',
        reassuranceTitle: 'This doesn\'t mean something is "wrong"',
        reassuranceBody: 'It helps us ensure your care is safe and appropriate for your needs.',
        nextSteps: 'A member of our clinical team will contact you within {{timeframe}}.',
        waitingAdvice: 'You don\'t need to do anything right now. We\'ll be in touch soon.',
      },

      // [CLINICAL] [LEGAL] RED - Immediate safety concern
      red: {
        title: 'We\'re concerned about your safety',
        subtitle: 'Based on your responses, you may be at immediate risk.',
        primaryAction: 'Please contact 999 now or attend your nearest A&E department.',
        firmStatement: 'We cannot provide emergency support through this service.',
        trustedPerson: 'If you\'re able to do so safely, consider contacting a trusted person to be with you.',
        crisisResources: {
          title: 'Other crisis lines:',
          samaritans: { name: 'Samaritans', number: '116 123' },
          shout: { name: 'Crisis Text Line', action: 'Text SHOUT to 85258' },
        },
      },
    },

    // =========================================================================
    // CHECK-IN (Waiting List Monitoring)
    // =========================================================================
    checkIn: {
      title: 'Weekly Check-In',
      intro: 'Checking in - how are you feeling?',
      body: 'We\'re checking in while you\'re waiting for your appointment. This short check-in helps us notice if things have changed and whether additional support is needed.',
      noCheckInDue: 'No Check-In Due',
      submitCta: 'Submit check-in',
      submitting: 'Submitting...',

      // Escalation after deterioration
      escalated: {
        title: 'We\'d like to review your care plan',
        body: 'Your recent check-in suggests things may have become more difficult.',
        nextSteps: 'A clinician will review this and may contact you to discuss next steps.',
        acknowledgeCta: 'I understand',
      },
    },

    // =========================================================================
    // BOOKING
    // =========================================================================
    booking: {
      title: 'Book your appointment',
      pathwayExplanation: 'Based on your assessment, this is the most appropriate starting point for your care.',
      clinicianTypeExplanation: 'You\'ll meet with a qualified clinician who specialises in concerns like yours. If at any point a different level of care is needed, we\'ll guide you through that.',
      // Pathway-specific explanations (extended from canonical)
      clinicianTypeByPathway: {
        THERAPY_ASSESSMENT: 'You\'ll meet with a qualified therapist who specialises in talk-based support for concerns like yours.',
        PSYCHOLOGY_ASSESSMENT: 'You\'ll meet with a clinical psychologist who can provide specialist psychological assessment and therapy.',
        PSYCHIATRY_ASSESSMENT: 'You\'ll meet with a psychiatrist who can provide specialist assessment and discuss both therapy and medication options.',
        COUNSELLING: 'You\'ll meet with a qualified counsellor for guided wellbeing support.',
        LOW_INTENSITY_DIGITAL: 'You\'ll have access to guided digital support with check-ins from our team.',
      },
      availabilityFraming: 'Appointments available as soon as this week.',
      availabilityEarliest: 'Earliest available: {{when}}',
      paymentRequired: 'Payment is required to confirm your appointment. This helps us reduce missed appointments and keep waiting times short.',
      selectTypeCta: 'Select Appointment Type',
      selectClinicianCta: 'Select Clinician',
      selectTimeCta: 'Select Date and Time',
      confirmCta: 'Confirm Booking',

      selfBook: {
        title: 'Choose your appointment',
        subtitle: 'Select a time that works for you.',
        formatOptions: {
          video: 'Video call',
          phone: 'Phone call',
          inPerson: 'In-person',
        },
        formatDescription: {
          video: 'Convenient from home. You\'ll receive a secure link before your appointment.',
          phone: 'We\'ll call you at your scheduled time.',
          inPerson: 'Visit us at the clinic address shown.',
        },
        paymentNotice: 'No payment is required at this stage.',
      },

      confirmation: {
        title: 'Appointment confirmed',
        subtitle: 'Your appointment has been booked.',
        detailsTitle: 'Appointment details',
        addToCalendar: 'Add to calendar',
        whatToExpect: 'What to expect',
        expectationsList: [
          'Your clinician will introduce themselves',
          'You\'ll discuss what brought you here',
          'Together you\'ll talk about next steps',
        ],
        cancellationPolicy: 'Need to cancel or reschedule? Please let us know at least 24 hours before.',
        portalCta: 'Go to patient portal',
      },
    },

    // =========================================================================
    // APPOINTMENT CONFIRMED
    // =========================================================================
    appointmentConfirmed: {
      title: 'Your appointment is confirmed',
      detailsTemplate: 'Date: {{date}}\nTime: {{time}}\nClinician: {{clinician_name}}\nFormat: {{format}}',
      formatLabel: 'Format',
      locationLabel: 'Location',
      manageLink: 'Manage or reschedule in your patient portal.',
      addToCalendarCta: 'Add to calendar',
      whatToExpect: {
        title: 'What to expect',
        items: [
          'Your clinician will introduce themselves',
          'You\'ll discuss what brought you here',
          'Together you\'ll talk about next steps',
        ],
      },
      preparation: {
        title: 'Before your appointment',
        items: [
          'Find a quiet, private space if joining by video',
          'Have any relevant documents or notes ready',
          'Write down any questions you\'d like to ask',
        ],
      },
      cancellationNotice: 'Need to cancel or reschedule? Please let us know at least 24 hours before.',
    },

    // =========================================================================
    // REVIEW REQUIRED (AMBER)
    // =========================================================================
    reviewRequired: {
      title: 'We\'re reviewing your assessment',
      body: 'Some aspects of your assessment mean a clinician needs to review it before booking an appointment.',
      reassurance: 'This doesn\'t mean something is "wrong" - it helps ensure your care is safe and appropriate.',
      nextStepsTitle: 'What happens next',
      nextStepsList: [
        'A clinician will review your information',
        'We\'ll contact you to arrange the next step',
        'This usually happens within 24-72 hours',
      ],
      timeline: 'If your situation worsens or you feel unsafe, please call 999 or attend A&E.',
      contactPreferences: 'We\'ll contact you using the details you provided during registration.',
    },

    // =========================================================================
    // RED - IMMEDIATE SAFETY ACTION
    // =========================================================================
    red: {
      // [CLINICAL] [LEGAL] - DO NOT MODIFY WITHOUT CLINICAL REVIEW
      title: 'We\'re concerned about your safety',
      primaryInstruction: 'Based on your responses, you may be at immediate risk. Please contact 999 now or attend your nearest A&E department.',
      boundary: 'We cannot provide emergency support through this service.',
      optionalSupport: 'If you\'re able to do so safely, consider contacting a trusted person to be with you.',
      callCta: 'Call 999 Now',
      findAeCta: 'Find nearest A&E',
      aeGuidanceUrl: 'https://www.nhs.uk/service-search/other-services/Accident-and-emergency-services/LocationSearch/428',
    },

    // =========================================================================
    // WAITING LIST
    // =========================================================================
    waitingList: {
      checkIn: {
        title: 'Checking in - how are you feeling?',
        intro: 'We\'re checking in while you\'re waiting for your appointment.',
        purpose: 'This short check-in helps us notice if things have changed and whether additional support is needed.',
        submitCta: 'Submit check-in',
        submitting: 'Submitting...',
      },

      questions: {
        overallFeeling: {
          text: 'Overall, how have you been feeling this week?',
          options: {
            much_better: 'Much better',
            a_bit_better: 'A bit better',
            about_the_same: 'About the same',
            a_bit_worse: 'A bit worse',
            much_worse: 'Much worse',
          },
        },
        // [CLINICAL] Safety question
        safety: {
          text: 'Have you had thoughts of harming yourself?',
          options: {
            no: 'No',
            occasionally: 'Occasionally, but fleeting',
            frequently: 'Yes, frequently',
            with_plan: 'Yes, with thoughts of how',
          },
        },
      },

      // [CLINICAL] Deterioration escalation
      deterioration: {
        title: 'We\'d like to review your care plan',
        body: 'Your recent check-in suggests things may have become more difficult.',
        nextSteps: 'A clinician will review this and may contact you to discuss next steps.',
        acknowledgeCta: 'I understand',
      },
    },

    // =========================================================================
    // ESCALATION PAGES
    // =========================================================================
    escalation: {
      // [CLINICAL] AMBER escalation
      amber: {
        title: 'We want to make sure you\'re supported appropriately',
        body: 'Some of your responses indicate that a clinician should review your assessment before booking.',
        contactTimeframe: 'A member of our clinical team will contact you within {{timeframe}}.',
        acknowledgeCta: 'I understand',
      },

      // [CLINICAL] [LEGAL] RED escalation - DO NOT MODIFY WITHOUT CLINICAL REVIEW
      red: {
        title: 'We\'re concerned about your safety',
        body: 'Based on your responses, you may be at immediate risk.',
        primaryAction: 'Please contact 999 now or attend your nearest A&E department.',
        firmStatement: 'We cannot provide emergency support through this service.',
        callCta: 'Call 999 Now',
        trustedPerson: 'If you\'re able to do so safely, consider contacting a trusted person to be with you.',
        acknowledgeCta: 'I understand',
      },
    },

    // =========================================================================
    // APPOINTMENT MANAGEMENT
    // =========================================================================
    appointment: {
      reminder: {
        title: 'Reminder: Your appointment is tomorrow',
        body: 'This is a reminder about your upcoming appointment.',
      },

      stillWant: {
        title: 'Are you still planning to attend?',
        body: 'We noticed you have an appointment scheduled. We wanted to check if this still works for you.',
        confirmCta: 'Yes, I\'ll attend',
        rescheduleCta: 'Reschedule',
        cancelCta: 'Cancel appointment',
      },
    },
  },

  // ===========================================================================
  // SHARED COPY (used across patient + staff portals)
  // ===========================================================================
  shared: {
    // [CLINICAL] [LEGAL] Emergency banner - DO NOT MODIFY WITHOUT CLINICAL REVIEW
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

    // [CLINICAL] [LEGAL] Safety footer - appears on all check-in/escalation pages
    safetyFooter: {
      default: 'If you\'re in immediate danger, please contact 999 or attend A&E.',
      withIcon: true,
    },

    // Common UI elements
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

  // ===========================================================================
  // STAFF CONSOLE COPY
  // ===========================================================================
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
} as const;

// Type helper for copy keys
export type CopyDictionary = typeof copy;

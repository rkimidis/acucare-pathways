"""Booking policy enforcement.

Implements safety safeguards for patient self-booking based on triage tier.
This is a critical safety layer - RED and AMBER tiers MUST NOT self-book.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class BookingRestriction(str, Enum):
    """Reason for booking restriction."""

    CRISIS_TIER = "crisis_tier"
    CLINICIAN_REVIEW_REQUIRED = "clinician_review_required"
    PATHWAY_RESTRICTION = "pathway_restriction"
    NONE = "none"


@dataclass
class BookingPolicy:
    """Policy decision for booking requests.

    Attributes:
        allowed: Whether booking action is allowed
        restriction: Reason for restriction if not allowed
        requires_clinician: Whether clinician must make booking
        message: Human-readable explanation
    """

    allowed: bool
    restriction: BookingRestriction
    requires_clinician: bool
    message: str


# Tiers that block self-booking (safety-critical)
BLOCKED_TIERS = frozenset({"RED", "AMBER"})

# Tiers that allow self-booking
ALLOWED_TIERS = frozenset({"GREEN", "BLUE"})


def can_patient_self_book(
    tier: str,
    pathway: Optional[str] = None,
    override_allowed: bool = False,
) -> bool:
    """Check if patient can self-book based on triage tier.

    SAFETY CRITICAL: RED and AMBER tiers MUST NOT self-book.
    This is a hard safety constraint that cannot be overridden
    without explicit clinical authorization.

    Args:
        tier: Triage tier (RED, AMBER, GREEN, BLUE)
        pathway: Optional pathway for additional restrictions
        override_allowed: If True, allows GREEN/BLUE pathway overrides
                         (never overrides RED/AMBER block)

    Returns:
        True if self-booking is allowed, False otherwise

    Examples:
        >>> can_patient_self_book(tier="RED")
        False
        >>> can_patient_self_book(tier="AMBER")
        False
        >>> can_patient_self_book(tier="GREEN")
        True
        >>> can_patient_self_book(tier="BLUE")
        True
    """
    tier_upper = tier.upper()

    # SAFETY: RED and AMBER ALWAYS block self-booking
    # This is non-negotiable for patient safety
    if tier_upper in BLOCKED_TIERS:
        return False

    # GREEN and BLUE allow self-booking by default
    if tier_upper in ALLOWED_TIERS:
        return True

    # Unknown tier - fail safe by blocking
    return False


def get_booking_policy(
    tier: str,
    pathway: Optional[str] = None,
) -> BookingPolicy:
    """Get detailed booking policy for a triage outcome.

    Returns a full policy decision with explanation.

    Args:
        tier: Triage tier (RED, AMBER, GREEN, BLUE)
        pathway: Optional pathway for additional context

    Returns:
        BookingPolicy with decision and explanation
    """
    tier_upper = tier.upper()

    if tier_upper == "RED":
        return BookingPolicy(
            allowed=False,
            restriction=BookingRestriction.CRISIS_TIER,
            requires_clinician=True,
            message="RED tier requires immediate clinician contact. Self-booking disabled for safety.",
        )

    if tier_upper == "AMBER":
        return BookingPolicy(
            allowed=False,
            restriction=BookingRestriction.CLINICIAN_REVIEW_REQUIRED,
            requires_clinician=True,
            message="AMBER tier requires clinician review before booking. Self-booking disabled.",
        )

    if tier_upper == "GREEN":
        return BookingPolicy(
            allowed=True,
            restriction=BookingRestriction.NONE,
            requires_clinician=False,
            message="GREEN tier allows patient self-booking.",
        )

    if tier_upper == "BLUE":
        return BookingPolicy(
            allowed=True,
            restriction=BookingRestriction.NONE,
            requires_clinician=False,
            message="BLUE tier allows patient self-booking for low-intensity services.",
        )

    # Unknown tier - fail safe
    return BookingPolicy(
        allowed=False,
        restriction=BookingRestriction.PATHWAY_RESTRICTION,
        requires_clinician=True,
        message=f"Unknown tier '{tier}'. Booking restricted pending review.",
    )


def validate_booking_request(
    tier: str,
    requested_by: str,
    is_clinician: bool = False,
) -> tuple[bool, str]:
    """Validate a booking request against policy.

    Args:
        tier: Triage tier
        requested_by: User ID making the request
        is_clinician: Whether requestor is a clinician

    Returns:
        Tuple of (allowed, reason)
    """
    policy = get_booking_policy(tier)

    if policy.allowed:
        return True, "Booking allowed"

    if policy.requires_clinician and is_clinician:
        return True, "Clinician override accepted"

    return False, policy.message


# =============================================================================
# CANCELLATION AND RESCHEDULING POLICY
# =============================================================================

# Safety-critical phrases that trigger immediate safety workflow
SAFETY_CONCERN_PHRASES = frozenset({
    "unsafe",
    "feel unsafe",
    "i feel unsafe",
    "not safe",
    "danger",
    "harm myself",
    "hurt myself",
    "harm myself",
    "self harm",
    "self-harm",
    "suicide",
    "suicidal",
    "end my life",
    "kill myself",
    "don't want to live",
    "can't go on",
})

# Maximum reschedules allowed per appointment
MAX_RESCHEDULES_PER_APPOINTMENT = 2

# Cancellation threshold before flagging (within 90 days)
CANCELLATION_FLAG_THRESHOLD = 2

# Hours before appointment when self-service is restricted
SELF_SERVICE_WINDOW_HOURS = 24


def can_patient_self_cancel(
    tier: str,
    hours_until_appointment: float,
) -> tuple[bool, str, bool]:
    """Check if patient can immediately self-cancel their appointment.

    SAFETY CRITICAL: AMBER/RED tiers always require staff review.
    GREEN/BLUE can self-cancel up to 24h before appointment.

    Args:
        tier: Triage tier (RED, AMBER, GREEN, BLUE)
        hours_until_appointment: Hours until the appointment starts

    Returns:
        Tuple of (allowed, message, requires_request)
        - allowed: True if immediate cancellation is permitted
        - message: Human-readable explanation
        - requires_request: True if a CancellationRequest should be created
    """
    tier_upper = tier.upper()

    # RED tier: Always requires staff - highest risk
    if tier_upper == "RED":
        return (
            False,
            "Please contact us to cancel your appointment. "
            "If you're feeling unsafe, call 999 or attend A&E.",
            True,
        )

    # AMBER tier: Always requires staff review
    if tier_upper == "AMBER":
        return (
            False,
            "Please contact us to arrange your cancellation. "
            "Our team will find the best next steps for you.",
            True,
        )

    # GREEN/BLUE: Check time window
    if tier_upper in ALLOWED_TIERS:
        if hours_until_appointment >= SELF_SERVICE_WINDOW_HOURS:
            return (
                True,
                "Your appointment has been cancelled.",
                False,
            )
        else:
            return (
                False,
                f"Cancellations within {SELF_SERVICE_WINDOW_HOURS} hours "
                "need to be reviewed. We'll confirm shortly.",
                True,
            )

    # Unknown tier - fail safe
    return (
        False,
        "Please contact us to cancel your appointment.",
        True,
    )


def can_patient_self_reschedule(
    tier: str,
    hours_until_appointment: float,
    current_reschedule_count: int,
) -> tuple[bool, str, bool]:
    """Check if patient can immediately self-reschedule their appointment.

    SAFETY CRITICAL: AMBER/RED tiers cannot self-reschedule.
    GREEN/BLUE can reschedule up to 24h before, max 2 times per appointment.

    Args:
        tier: Triage tier (RED, AMBER, GREEN, BLUE)
        hours_until_appointment: Hours until the appointment starts
        current_reschedule_count: How many times this appointment has been rescheduled

    Returns:
        Tuple of (allowed, message, requires_request)
    """
    tier_upper = tier.upper()

    # Check reschedule limit first (applies to all tiers)
    if current_reschedule_count >= MAX_RESCHEDULES_PER_APPOINTMENT:
        return (
            False,
            "This appointment has reached the maximum number of reschedules. "
            "Please contact us if you need to make changes.",
            True,
        )

    # RED/AMBER: No self-reschedule
    if tier_upper in BLOCKED_TIERS:
        return (
            False,
            "Please contact us to reschedule your appointment.",
            True,
        )

    # GREEN/BLUE: Check time window
    if tier_upper in ALLOWED_TIERS:
        if hours_until_appointment >= SELF_SERVICE_WINDOW_HOURS:
            return (
                True,
                "You can reschedule your appointment.",
                False,
            )
        else:
            return (
                False,
                f"Rescheduling within {SELF_SERVICE_WINDOW_HOURS} hours "
                "is not available online. Please contact us.",
                True,
            )

    # Unknown tier - fail safe
    return (
        False,
        "Please contact us to reschedule your appointment.",
        True,
    )


def check_safety_concern_in_reason(reason: Optional[str]) -> bool:
    """Check if a cancellation reason contains safety-critical phrases.

    SAFETY CRITICAL: If this returns True, staff must be immediately notified
    and a safety workflow must be triggered.

    Args:
        reason: The patient-provided cancellation reason

    Returns:
        True if safety concern detected, False otherwise
    """
    if not reason:
        return False

    reason_lower = reason.lower()
    return any(phrase in reason_lower for phrase in SAFETY_CONCERN_PHRASES)


def should_flag_patient_cancellations(cancellation_count_90d: int) -> bool:
    """Check if patient has exceeded cancellation threshold.

    Patients with excessive cancellations may require deposit or staff booking.

    Args:
        cancellation_count_90d: Number of cancellations in last 90 days

    Returns:
        True if patient should be flagged for review
    """
    return cancellation_count_90d >= CANCELLATION_FLAG_THRESHOLD

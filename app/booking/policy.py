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

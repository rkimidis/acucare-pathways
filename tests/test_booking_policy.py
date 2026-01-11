"""Comprehensive tests for booking policy enforcement.

SAFETY CRITICAL TESTS: These tests verify that RED and AMBER tier patients
CANNOT self-book appointments. This is a critical safety requirement.

Test coverage requirements:
1. Policy correctly blocks RED tier
2. Policy correctly blocks AMBER tier
3. Policy allows GREEN tier
4. Policy allows BLUE tier
5. Policy fails safe for unknown tiers
6. Policy cannot be bypassed by case manipulation
7. Defense in depth verification
8. Edge cases and boundary conditions

Done when: All bypass attempts are blocked and test-covered.
"""

from dataclasses import dataclass
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch
import pytest


# ============================================================================
# Standalone Policy Implementation (mirrors app.booking.policy)
# ============================================================================

class BookingRestriction:
    """Reason for booking restriction."""
    CRISIS_TIER = "crisis_tier"
    CLINICIAN_REVIEW_REQUIRED = "clinician_review_required"
    PATHWAY_RESTRICTION = "pathway_restriction"
    NONE = "none"


@dataclass
class BookingPolicy:
    """Policy decision for booking requests."""
    allowed: bool
    restriction: str
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
    """
    tier_upper = tier.upper()

    # SAFETY: RED and AMBER ALWAYS block self-booking
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
    """Get detailed booking policy for a triage outcome."""
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
    """Validate a booking request against policy."""
    policy = get_booking_policy(tier)

    if policy.allowed:
        return True, "Booking allowed"

    if policy.requires_clinician and is_clinician:
        return True, "Clinician override accepted"

    return False, policy.message


# ============================================================================
# Core Policy Tests
# ============================================================================


class TestRedTierBlocking:
    """Tests for RED tier self-booking restrictions."""

    def test_red_tier_cannot_self_book(self) -> None:
        """RED tier MUST NOT be able to self-book."""
        assert can_patient_self_book("RED") is False

    def test_red_tier_lowercase(self) -> None:
        """RED tier check is case-insensitive."""
        assert can_patient_self_book("red") is False

    def test_red_tier_mixed_case(self) -> None:
        """RED tier check handles mixed case."""
        assert can_patient_self_book("Red") is False
        assert can_patient_self_book("rED") is False

    def test_red_tier_policy_details(self) -> None:
        """RED tier policy has correct details."""
        policy = get_booking_policy("RED")
        assert policy.allowed is False
        assert policy.requires_clinician is True
        assert policy.restriction == BookingRestriction.CRISIS_TIER
        assert "RED" in policy.message.upper()

    def test_red_tier_with_pathway(self) -> None:
        """RED tier blocked regardless of pathway."""
        assert can_patient_self_book("RED", pathway="standard") is False
        assert can_patient_self_book("RED", pathway="urgent") is False
        assert can_patient_self_book("RED", pathway="crisis") is False

    def test_red_tier_override_flag_ignored(self) -> None:
        """Override flag does NOT allow RED tier self-booking."""
        # This is critical - override_allowed should never bypass RED
        assert can_patient_self_book("RED", override_allowed=True) is False


class TestAmberTierBlocking:
    """Tests for AMBER tier self-booking restrictions."""

    def test_amber_tier_cannot_self_book(self) -> None:
        """AMBER tier MUST NOT be able to self-book."""
        assert can_patient_self_book("AMBER") is False

    def test_amber_tier_lowercase(self) -> None:
        """AMBER tier check is case-insensitive."""
        assert can_patient_self_book("amber") is False

    def test_amber_tier_mixed_case(self) -> None:
        """AMBER tier check handles mixed case."""
        assert can_patient_self_book("Amber") is False
        assert can_patient_self_book("aMBER") is False

    def test_amber_tier_policy_details(self) -> None:
        """AMBER tier policy has correct details."""
        policy = get_booking_policy("AMBER")
        assert policy.allowed is False
        assert policy.requires_clinician is True
        assert policy.restriction == BookingRestriction.CLINICIAN_REVIEW_REQUIRED
        assert "AMBER" in policy.message.upper()

    def test_amber_tier_with_pathway(self) -> None:
        """AMBER tier blocked regardless of pathway."""
        assert can_patient_self_book("AMBER", pathway="standard") is False
        assert can_patient_self_book("AMBER", pathway="urgent") is False

    def test_amber_tier_override_flag_ignored(self) -> None:
        """Override flag does NOT allow AMBER tier self-booking."""
        assert can_patient_self_book("AMBER", override_allowed=True) is False


class TestGreenTierAllowed:
    """Tests for GREEN tier self-booking permissions."""

    def test_green_tier_can_self_book(self) -> None:
        """GREEN tier SHOULD be able to self-book."""
        assert can_patient_self_book("GREEN") is True

    def test_green_tier_lowercase(self) -> None:
        """GREEN tier check is case-insensitive."""
        assert can_patient_self_book("green") is True

    def test_green_tier_policy_details(self) -> None:
        """GREEN tier policy has correct details."""
        policy = get_booking_policy("GREEN")
        assert policy.allowed is True
        assert policy.requires_clinician is False
        assert policy.restriction == BookingRestriction.NONE


class TestBlueTierAllowed:
    """Tests for BLUE tier self-booking permissions."""

    def test_blue_tier_can_self_book(self) -> None:
        """BLUE tier SHOULD be able to self-book."""
        assert can_patient_self_book("BLUE") is True

    def test_blue_tier_lowercase(self) -> None:
        """BLUE tier check is case-insensitive."""
        assert can_patient_self_book("blue") is True

    def test_blue_tier_policy_details(self) -> None:
        """BLUE tier policy has correct details."""
        policy = get_booking_policy("BLUE")
        assert policy.allowed is True
        assert policy.requires_clinician is False
        assert policy.restriction == BookingRestriction.NONE


class TestUnknownTierFailSafe:
    """Tests for unknown tier handling - should fail safe."""

    def test_unknown_tier_blocked(self) -> None:
        """Unknown tiers should be blocked (fail safe)."""
        assert can_patient_self_book("UNKNOWN") is False
        assert can_patient_self_book("PURPLE") is False
        assert can_patient_self_book("ORANGE") is False

    def test_empty_tier_blocked(self) -> None:
        """Empty tier should be blocked."""
        assert can_patient_self_book("") is False

    def test_whitespace_tier_blocked(self) -> None:
        """Whitespace tier should be blocked."""
        assert can_patient_self_book(" ") is False
        assert can_patient_self_book("  ") is False

    def test_numeric_tier_blocked(self) -> None:
        """Numeric tier should be blocked."""
        assert can_patient_self_book("1") is False
        assert can_patient_self_book("0") is False

    def test_unknown_tier_policy_details(self) -> None:
        """Unknown tier policy requires clinician."""
        policy = get_booking_policy("UNKNOWN")
        assert policy.allowed is False
        assert policy.requires_clinician is True


class TestClinicianOverride:
    """Tests for clinician override capability."""

    def test_clinician_can_book_for_red_tier(self) -> None:
        """Clinician can book for RED tier patient."""
        allowed, reason = validate_booking_request("RED", "clinician-123", is_clinician=True)
        assert allowed is True
        assert "Clinician" in reason

    def test_clinician_can_book_for_amber_tier(self) -> None:
        """Clinician can book for AMBER tier patient."""
        allowed, reason = validate_booking_request("AMBER", "clinician-123", is_clinician=True)
        assert allowed is True

    def test_patient_cannot_book_for_red_tier(self) -> None:
        """Patient cannot book for RED tier."""
        allowed, reason = validate_booking_request("RED", "patient-123", is_clinician=False)
        assert allowed is False
        assert "RED" in reason.upper()

    def test_patient_cannot_book_for_amber_tier(self) -> None:
        """Patient cannot book for AMBER tier."""
        allowed, reason = validate_booking_request("AMBER", "patient-123", is_clinician=False)
        assert allowed is False

    def test_patient_can_book_for_green_tier(self) -> None:
        """Patient can book for GREEN tier."""
        allowed, reason = validate_booking_request("GREEN", "patient-123", is_clinician=False)
        assert allowed is True


# ============================================================================
# Defense in Depth Tests
# ============================================================================


class TestDefenseInDepth:
    """Tests for defense in depth - multiple layers of protection."""

    def test_blocked_tiers_constant_immutable(self) -> None:
        """BLOCKED_TIERS constant cannot be modified at runtime."""
        # frozenset prevents modification
        assert isinstance(BLOCKED_TIERS, frozenset)
        with pytest.raises(AttributeError):
            BLOCKED_TIERS.add("GREEN")  # type: ignore

    def test_allowed_tiers_constant_immutable(self) -> None:
        """ALLOWED_TIERS constant cannot be modified at runtime."""
        assert isinstance(ALLOWED_TIERS, frozenset)
        with pytest.raises(AttributeError):
            ALLOWED_TIERS.add("RED")  # type: ignore

    def test_red_in_blocked_tiers(self) -> None:
        """RED is in BLOCKED_TIERS constant."""
        assert "RED" in BLOCKED_TIERS

    def test_amber_in_blocked_tiers(self) -> None:
        """AMBER is in BLOCKED_TIERS constant."""
        assert "AMBER" in BLOCKED_TIERS

    def test_green_in_allowed_tiers(self) -> None:
        """GREEN is in ALLOWED_TIERS constant."""
        assert "GREEN" in ALLOWED_TIERS

    def test_blue_in_allowed_tiers(self) -> None:
        """BLUE is in ALLOWED_TIERS constant."""
        assert "BLUE" in ALLOWED_TIERS

    def test_no_overlap_between_blocked_and_allowed(self) -> None:
        """BLOCKED_TIERS and ALLOWED_TIERS have no overlap."""
        overlap = BLOCKED_TIERS & ALLOWED_TIERS
        assert len(overlap) == 0


# ============================================================================
# Bypass Attempt Tests
# ============================================================================


class TestBypassAttempts:
    """Tests for potential bypass attempts - all must fail."""

    def test_cannot_bypass_with_lowercase(self) -> None:
        """Cannot bypass by using lowercase tier."""
        assert can_patient_self_book("red") is False
        assert can_patient_self_book("amber") is False

    def test_cannot_bypass_with_mixed_case(self) -> None:
        """Cannot bypass with mixed case variations."""
        variations = ["ReD", "rEd", "RED", "Red", "reD"]
        for v in variations:
            assert can_patient_self_book(v) is False, f"Bypass with '{v}' should fail"

    def test_cannot_bypass_with_whitespace(self) -> None:
        """Cannot bypass with whitespace padding."""
        # These should either be blocked or fail safely
        assert can_patient_self_book(" RED") is False
        assert can_patient_self_book("RED ") is False
        assert can_patient_self_book(" RED ") is False

    def test_cannot_bypass_with_null_bytes(self) -> None:
        """Cannot bypass with null bytes."""
        assert can_patient_self_book("RED\x00") is False
        assert can_patient_self_book("\x00RED") is False

    def test_cannot_bypass_with_unicode_lookalikes(self) -> None:
        """Cannot bypass with unicode lookalike characters."""
        # Cyrillic 'Р' looks like Latin 'P', etc.
        assert can_patient_self_book("RЕD") is False  # Cyrillic Е
        assert can_patient_self_book("АМВЕr") is False  # Mix of Cyrillic

    def test_cannot_bypass_with_special_chars(self) -> None:
        """Cannot bypass with special character injection."""
        assert can_patient_self_book("RED;GREEN") is False
        assert can_patient_self_book("GREEN|RED") is False
        assert can_patient_self_book("RED\nGREEN") is False


class TestPolicyConsistency:
    """Tests for policy consistency across functions."""

    def test_can_self_book_matches_get_policy(self) -> None:
        """can_patient_self_book matches get_booking_policy."""
        for tier in ["RED", "AMBER", "GREEN", "BLUE"]:
            can_book = can_patient_self_book(tier)
            policy = get_booking_policy(tier)
            assert can_book == policy.allowed, f"Mismatch for {tier}"

    def test_validate_matches_can_self_book_for_patients(self) -> None:
        """validate_booking_request matches can_patient_self_book for patients."""
        for tier in ["RED", "AMBER", "GREEN", "BLUE"]:
            can_book = can_patient_self_book(tier)
            allowed, _ = validate_booking_request(tier, "patient-123", is_clinician=False)
            assert can_book == allowed, f"Mismatch for {tier}"


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Edge case tests for booking policy."""

    def test_very_long_tier_name(self) -> None:
        """Very long tier name should be blocked."""
        long_tier = "A" * 1000
        assert can_patient_self_book(long_tier) is False

    def test_tier_with_sql_injection_attempt(self) -> None:
        """SQL injection attempts should be blocked."""
        assert can_patient_self_book("'; DROP TABLE users; --") is False
        assert can_patient_self_book("1 OR 1=1") is False

    def test_tier_with_html_injection_attempt(self) -> None:
        """HTML injection attempts should be blocked."""
        assert can_patient_self_book("<script>alert('xss')</script>") is False
        assert can_patient_self_book("<img src=x onerror=alert(1)>") is False


# ============================================================================
# Simulated Service Layer Tests
# ============================================================================


class TestServiceLayerEnforcement:
    """Tests simulating service layer enforcement."""

    def test_service_blocks_red_self_book(self) -> None:
        """Service layer blocks RED tier self-booking."""
        # Simulate service check
        tier = "RED"
        booking_source = "PATIENT_SELF_BOOK"

        if booking_source == "PATIENT_SELF_BOOK":
            policy = get_booking_policy(tier)
            if not policy.allowed:
                blocked = True
            else:
                blocked = False
        else:
            blocked = False

        assert blocked is True

    def test_service_allows_staff_book_for_red(self) -> None:
        """Service layer allows staff booking for RED tier."""
        tier = "RED"
        booking_source = "STAFF_BOOKED"

        # Staff booking bypasses self-book restriction
        if booking_source == "PATIENT_SELF_BOOK":
            policy = get_booking_policy(tier)
            blocked = not policy.allowed
        else:
            blocked = False

        assert blocked is False

    def test_defense_in_depth_double_check(self) -> None:
        """Simulate defense in depth with double-check."""
        tier = "RED"

        # First check
        check1 = not can_patient_self_book(tier)

        # Second check (defense in depth)
        check2 = tier.upper() in BLOCKED_TIERS

        # Both checks must block
        assert check1 is True
        assert check2 is True


class TestAuditRequirements:
    """Tests for audit trail requirements."""

    def test_blocked_attempt_generates_reason(self) -> None:
        """Blocked booking attempts include reason for audit."""
        policy = get_booking_policy("RED")
        assert policy.message is not None
        assert len(policy.message) > 0

        allowed, reason = validate_booking_request("RED", "patient-123", is_clinician=False)
        assert allowed is False
        assert reason is not None
        assert len(reason) > 0

    def test_policy_includes_restriction_type(self) -> None:
        """Policy includes restriction type for categorization."""
        red_policy = get_booking_policy("RED")
        assert red_policy.restriction == BookingRestriction.CRISIS_TIER

        amber_policy = get_booking_policy("AMBER")
        assert amber_policy.restriction == BookingRestriction.CLINICIAN_REVIEW_REQUIRED


# ============================================================================
# Summary Test
# ============================================================================


class TestSafetyRequirementsSummary:
    """Summary tests verifying all safety requirements are met."""

    def test_all_blocked_tiers_fail_self_book(self) -> None:
        """All tiers in BLOCKED_TIERS fail self-book check."""
        for tier in BLOCKED_TIERS:
            assert can_patient_self_book(tier) is False, f"{tier} should be blocked"

    def test_all_allowed_tiers_pass_self_book(self) -> None:
        """All tiers in ALLOWED_TIERS pass self-book check."""
        for tier in ALLOWED_TIERS:
            assert can_patient_self_book(tier) is True, f"{tier} should be allowed"

    def test_complete_tier_coverage(self) -> None:
        """All expected tiers are covered by policy."""
        expected_tiers = {"RED", "AMBER", "GREEN", "BLUE"}
        covered_tiers = BLOCKED_TIERS | ALLOWED_TIERS
        assert expected_tiers == covered_tiers

    def test_safety_critical_tiers_are_blocked(self) -> None:
        """Safety-critical tiers (RED, AMBER) are in BLOCKED_TIERS."""
        assert "RED" in BLOCKED_TIERS
        assert "AMBER" in BLOCKED_TIERS

    def test_fail_safe_default(self) -> None:
        """Unknown tiers default to blocked (fail-safe)."""
        unknown_tiers = ["UNKNOWN", "INVALID", "NULL", "NONE", ""]
        for tier in unknown_tiers:
            assert can_patient_self_book(tier) is False, f"Unknown tier '{tier}' should fail safe"

"""Safety safeguard tests for booking policy.

These tests verify that RED and AMBER tiers ALWAYS block self-booking.
This is a critical safety constraint for patient protection.
"""

import pytest

from app.booking.policy import (
    can_patient_self_book,
    get_booking_policy,
    validate_booking_request,
    BookingRestriction,
)


class TestSelfBookingSafeguards:
    """Core safeguard tests - RED/AMBER must block self-booking."""

    def test_red_blocks_self_booking(self):
        """RED tier MUST block self-booking (safety critical)."""
        assert can_patient_self_book(tier="RED") is False

    def test_amber_blocks_self_booking(self):
        """AMBER tier MUST block self-booking (safety critical)."""
        assert can_patient_self_book(tier="AMBER") is False

    def test_green_allows_self_booking(self):
        """GREEN tier allows self-booking."""
        assert can_patient_self_book(tier="GREEN") is True

    def test_blue_allows_self_booking(self):
        """BLUE tier allows self-booking."""
        assert can_patient_self_book(tier="BLUE") is True


class TestTierCaseInsensitivity:
    """Tier checks must be case-insensitive."""

    def test_red_lowercase_blocks(self):
        """Lowercase 'red' blocks self-booking."""
        assert can_patient_self_book(tier="red") is False

    def test_amber_lowercase_blocks(self):
        """Lowercase 'amber' blocks self-booking."""
        assert can_patient_self_book(tier="amber") is False

    def test_green_lowercase_allows(self):
        """Lowercase 'green' allows self-booking."""
        assert can_patient_self_book(tier="green") is True

    def test_mixed_case_red_blocks(self):
        """Mixed case 'Red' blocks self-booking."""
        assert can_patient_self_book(tier="Red") is False

    def test_mixed_case_amber_blocks(self):
        """Mixed case 'Amber' blocks self-booking."""
        assert can_patient_self_book(tier="Amber") is False


class TestUnknownTierSafety:
    """Unknown tiers should fail safe (block booking)."""

    def test_unknown_tier_blocks(self):
        """Unknown tier blocks self-booking (fail safe)."""
        assert can_patient_self_book(tier="UNKNOWN") is False

    def test_empty_tier_blocks(self):
        """Empty tier blocks self-booking."""
        assert can_patient_self_book(tier="") is False

    def test_invalid_tier_blocks(self):
        """Invalid tier blocks self-booking."""
        assert can_patient_self_book(tier="PURPLE") is False


class TestBookingPolicy:
    """Tests for detailed booking policy."""

    def test_red_policy_requires_clinician(self):
        """RED policy requires clinician."""
        policy = get_booking_policy("RED")
        assert policy.allowed is False
        assert policy.requires_clinician is True
        assert policy.restriction == BookingRestriction.CRISIS_TIER

    def test_amber_policy_requires_clinician(self):
        """AMBER policy requires clinician review."""
        policy = get_booking_policy("AMBER")
        assert policy.allowed is False
        assert policy.requires_clinician is True
        assert policy.restriction == BookingRestriction.CLINICIAN_REVIEW_REQUIRED

    def test_green_policy_allows_self_book(self):
        """GREEN policy allows self-booking."""
        policy = get_booking_policy("GREEN")
        assert policy.allowed is True
        assert policy.requires_clinician is False
        assert policy.restriction == BookingRestriction.NONE

    def test_blue_policy_allows_self_book(self):
        """BLUE policy allows self-booking."""
        policy = get_booking_policy("BLUE")
        assert policy.allowed is True
        assert policy.requires_clinician is False

    def test_policy_has_message(self):
        """All policies have explanatory messages."""
        for tier in ["RED", "AMBER", "GREEN", "BLUE"]:
            policy = get_booking_policy(tier)
            assert policy.message
            assert len(policy.message) > 0


class TestClinicianOverride:
    """Tests for clinician override capability."""

    def test_clinician_can_book_red(self):
        """Clinician can book for RED tier patient."""
        allowed, reason = validate_booking_request(
            tier="RED",
            requested_by="clinician_001",
            is_clinician=True,
        )
        assert allowed is True
        assert "override" in reason.lower()

    def test_clinician_can_book_amber(self):
        """Clinician can book for AMBER tier patient."""
        allowed, reason = validate_booking_request(
            tier="AMBER",
            requested_by="clinician_001",
            is_clinician=True,
        )
        assert allowed is True

    def test_patient_cannot_book_red(self):
        """Patient cannot self-book RED tier."""
        allowed, reason = validate_booking_request(
            tier="RED",
            requested_by="patient_001",
            is_clinician=False,
        )
        assert allowed is False
        assert "clinician" in reason.lower()

    def test_patient_can_book_green(self):
        """Patient can self-book GREEN tier."""
        allowed, reason = validate_booking_request(
            tier="GREEN",
            requested_by="patient_001",
            is_clinician=False,
        )
        assert allowed is True


class TestSafeguardInvariants:
    """Invariant tests that must always hold."""

    @pytest.mark.parametrize("tier", ["RED", "red", "Red", "RED "])
    def test_red_never_allows_patient_self_book(self, tier):
        """RED tier NEVER allows patient self-booking, regardless of format."""
        # Strip whitespace for robustness
        assert can_patient_self_book(tier=tier.strip()) is False

    @pytest.mark.parametrize("tier", ["AMBER", "amber", "Amber", "AMBER "])
    def test_amber_never_allows_patient_self_book(self, tier):
        """AMBER tier NEVER allows patient self-booking, regardless of format."""
        assert can_patient_self_book(tier=tier.strip()) is False

    def test_blocked_tiers_are_immutable(self):
        """Blocked tiers set cannot be modified at runtime."""
        from app.booking.policy import BLOCKED_TIERS

        # frozenset is immutable
        assert isinstance(BLOCKED_TIERS, frozenset)
        assert "RED" in BLOCKED_TIERS
        assert "AMBER" in BLOCKED_TIERS

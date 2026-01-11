"""Unit tests for AUDIT-C scoring module.

Tests the pure scoring logic from app.scoring.auditc.
"""

import pytest

from app.scoring.auditc import (
    AUDITCResult,
    MALE_THRESHOLD,
    FEMALE_THRESHOLD,
    HIGH_RISK_THRESHOLD,
    get_risk_level,
    score_auditc,
    needs_full_audit,
    needs_clinical_assessment,
)


class TestAUDITCScoring:
    """Tests for AUDIT-C score calculation."""

    def test_all_zeros(self) -> None:
        """Test scoring when all items are 0 (non-drinker)."""
        answers = {"auditc_1": 0, "auditc_2": 0, "auditc_3": 0}
        result = score_auditc(answers)

        assert result.total == 0
        assert result.risk_level == "low"
        assert result.above_male_threshold is False
        assert result.above_female_threshold is False
        assert result.high_risk is False

    def test_all_fours(self) -> None:
        """Test maximum score (all items = 4)."""
        answers = {"auditc_1": 4, "auditc_2": 4, "auditc_3": 4}
        result = score_auditc(answers)

        assert result.total == 12
        assert result.risk_level == "high_risk"
        assert result.above_male_threshold is True
        assert result.above_female_threshold is True
        assert result.high_risk is True

    def test_total_calculation(self) -> None:
        """Test total is sum of all items."""
        answers = {"auditc_1": 1, "auditc_2": 2, "auditc_3": 3}
        result = score_auditc(answers)

        assert result.total == 6

    def test_individual_item_scores(self) -> None:
        """Test that individual item scores are captured correctly."""
        answers = {
            "auditc_1": 2,  # frequency
            "auditc_2": 1,  # typical_quantity
            "auditc_3": 3,  # binge_frequency
        }
        result = score_auditc(answers)

        assert result.frequency == 2
        assert result.typical_quantity == 1
        assert result.binge_frequency == 3
        assert result.total == 6


class TestAUDITCRiskLevels:
    """Tests for AUDIT-C risk level determination."""

    def test_low_risk(self) -> None:
        """Test low risk (below all thresholds)."""
        answers = {"auditc_1": 1, "auditc_2": 0, "auditc_3": 0}
        result = score_auditc(answers)

        assert result.total == 1
        assert result.risk_level == "low"

    def test_female_threshold(self) -> None:
        """Test at-risk at female threshold (3)."""
        answers = {"auditc_1": 1, "auditc_2": 1, "auditc_3": 1}
        result = score_auditc(answers)

        assert result.total == 3
        assert result.above_female_threshold is True
        assert result.above_male_threshold is False
        assert result.risk_level == "at_risk"

    def test_male_threshold(self) -> None:
        """Test at-risk at male threshold (4)."""
        answers = {"auditc_1": 2, "auditc_2": 1, "auditc_3": 1}
        result = score_auditc(answers)

        assert result.total == 4
        assert result.above_female_threshold is True
        assert result.above_male_threshold is True
        assert result.risk_level == "at_risk"

    def test_high_risk_threshold(self) -> None:
        """Test high risk at threshold (8)."""
        answers = {"auditc_1": 3, "auditc_2": 3, "auditc_3": 2}
        result = score_auditc(answers)

        assert result.total == 8
        assert result.high_risk is True
        assert result.risk_level == "high_risk"

    def test_sex_specific_risk_male(self) -> None:
        """Test male-specific risk assessment."""
        answers = {"auditc_1": 1, "auditc_2": 1, "auditc_3": 1}
        result = score_auditc(answers, sex="male")

        assert result.total == 3
        # Score 3 is below male threshold (4)
        assert result.risk_level == "low"

    def test_sex_specific_risk_female(self) -> None:
        """Test female-specific risk assessment."""
        answers = {"auditc_1": 1, "auditc_2": 1, "auditc_3": 1}
        result = score_auditc(answers, sex="female")

        assert result.total == 3
        # Score 3 is at female threshold (3)
        assert result.risk_level == "at_risk"

    def test_risk_level_without_sex(self) -> None:
        """Test risk level uses conservative (female) threshold without sex."""
        assert get_risk_level(3) == "at_risk"  # Female threshold
        assert get_risk_level(2) == "low"


class TestAUDITCKeyFormats:
    """Tests for different answer key formats."""

    def test_auditc_underscore_format(self) -> None:
        """Test 'auditc_N' key format."""
        answers = {"auditc_1": 1, "auditc_2": 1, "auditc_3": 1}
        result = score_auditc(answers)
        assert result.total == 3

    def test_item_format(self) -> None:
        """Test 'itemN' key format."""
        answers = {"item1": 1, "item2": 1, "item3": 1}
        result = score_auditc(answers)
        assert result.total == 3

    def test_q_format(self) -> None:
        """Test 'qN' key format."""
        answers = {"q1": 1, "q2": 1, "q3": 1}
        result = score_auditc(answers)
        assert result.total == 3

    def test_numeric_format(self) -> None:
        """Test 'N' (numeric string) key format."""
        answers = {"1": 1, "2": 1, "3": 1}
        result = score_auditc(answers)
        assert result.total == 3

    def test_auditc_q_format(self) -> None:
        """Test 'auditc_qN' key format."""
        answers = {"auditc_q1": 1, "auditc_q2": 1, "auditc_q3": 1}
        result = score_auditc(answers)
        assert result.total == 3

    def test_audit_c_underscore_format(self) -> None:
        """Test 'audit_c_N' key format."""
        answers = {"audit_c_1": 1, "audit_c_2": 1, "audit_c_3": 1}
        result = score_auditc(answers)
        assert result.total == 3


class TestAUDITCValidationErrors:
    """Tests for AUDIT-C input validation."""

    def test_missing_item_raises(self) -> None:
        """Test that missing items raise ValueError."""
        answers = {"auditc_1": 1, "auditc_2": 1}  # Missing item 3

        with pytest.raises(ValueError, match="Missing AUDIT-C item 3"):
            score_auditc(answers)

    def test_value_below_range_raises(self) -> None:
        """Test that values below 0 raise ValueError."""
        answers = {"auditc_1": -1, "auditc_2": 1, "auditc_3": 1}

        with pytest.raises(ValueError, match="AUDIT-C item 1 must be integer 0-4"):
            score_auditc(answers)

    def test_value_above_range_raises(self) -> None:
        """Test that values above 4 raise ValueError."""
        answers = {"auditc_1": 1, "auditc_2": 5, "auditc_3": 1}

        with pytest.raises(ValueError, match="AUDIT-C item 2 must be integer 0-4"):
            score_auditc(answers)

    def test_non_integer_raises(self) -> None:
        """Test that non-integer values raise ValueError."""
        answers = {"auditc_1": "daily", "auditc_2": 1, "auditc_3": 1}

        with pytest.raises(ValueError, match="AUDIT-C item 1 must be integer 0-4"):
            score_auditc(answers)

    def test_float_raises(self) -> None:
        """Test that float values raise ValueError."""
        answers = {"auditc_1": 1.5, "auditc_2": 1, "auditc_3": 1}

        with pytest.raises(ValueError, match="AUDIT-C item 1 must be integer 0-4"):
            score_auditc(answers)


class TestNeedsFullAudit:
    """Tests for full AUDIT recommendation."""

    def test_low_score_no_full_audit(self) -> None:
        """Test low score doesn't need full AUDIT."""
        answers = {"auditc_1": 1, "auditc_2": 0, "auditc_3": 0}
        result = score_auditc(answers)
        assert needs_full_audit(result) is False

    def test_at_female_threshold_needs_full_audit(self) -> None:
        """Test score at female threshold needs full AUDIT."""
        answers = {"auditc_1": 1, "auditc_2": 1, "auditc_3": 1}
        result = score_auditc(answers)
        assert needs_full_audit(result) is True

    def test_high_risk_needs_full_audit(self) -> None:
        """Test high risk score needs full AUDIT."""
        answers = {"auditc_1": 3, "auditc_2": 3, "auditc_3": 2}
        result = score_auditc(answers)
        assert needs_full_audit(result) is True


class TestNeedsClinicalAssessment:
    """Tests for clinical assessment recommendation."""

    def test_low_score_no_clinical_assessment(self) -> None:
        """Test low score doesn't need clinical assessment."""
        answers = {"auditc_1": 1, "auditc_2": 1, "auditc_3": 1}
        result = score_auditc(answers)
        assert needs_clinical_assessment(result) is False

    def test_at_risk_no_clinical_assessment(self) -> None:
        """Test at-risk score doesn't need clinical assessment."""
        answers = {"auditc_1": 2, "auditc_2": 2, "auditc_3": 1}
        result = score_auditc(answers)
        assert needs_clinical_assessment(result) is False

    def test_high_risk_needs_clinical_assessment(self) -> None:
        """Test high risk score needs clinical assessment."""
        answers = {"auditc_1": 3, "auditc_2": 3, "auditc_3": 2}
        result = score_auditc(answers)
        assert needs_clinical_assessment(result) is True


class TestAUDITCResult:
    """Tests for AUDITCResult dataclass."""

    def test_result_contains_all_fields(self) -> None:
        """Test that result contains all expected fields."""
        answers = {"auditc_1": 1, "auditc_2": 2, "auditc_3": 3}
        result = score_auditc(answers)

        assert hasattr(result, "total")
        assert hasattr(result, "risk_level")
        assert hasattr(result, "above_male_threshold")
        assert hasattr(result, "above_female_threshold")
        assert hasattr(result, "high_risk")
        assert hasattr(result, "items")
        assert hasattr(result, "frequency")
        assert hasattr(result, "typical_quantity")
        assert hasattr(result, "binge_frequency")

    def test_items_dict_structure(self) -> None:
        """Test that items dict has correct structure."""
        answers = {"auditc_1": 1, "auditc_2": 2, "auditc_3": 3}
        result = score_auditc(answers)

        assert len(result.items) == 3
        assert result.items["item1"] == 1
        assert result.items["item2"] == 2
        assert result.items["item3"] == 3


class TestAUDITCThresholdConstants:
    """Tests for threshold constants."""

    def test_thresholds_are_correct(self) -> None:
        """Verify threshold constants match clinical guidelines."""
        assert MALE_THRESHOLD == 4
        assert FEMALE_THRESHOLD == 3
        assert HIGH_RISK_THRESHOLD == 8

    def test_female_threshold_lower_than_male(self) -> None:
        """Female threshold should be lower (more conservative)."""
        assert FEMALE_THRESHOLD < MALE_THRESHOLD

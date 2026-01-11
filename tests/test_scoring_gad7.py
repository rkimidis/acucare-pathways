"""Unit tests for GAD-7 scoring module.

Tests the pure scoring logic from app.scoring.gad7.
"""

import pytest

from app.scoring.gad7 import (
    GAD7Result,
    SEVERITY_BANDS,
    get_severity_band,
    score_gad7,
    is_gad_likely,
)


class TestGAD7Scoring:
    """Tests for GAD-7 score calculation."""

    def test_all_zeros(self) -> None:
        """Test scoring when all items are 0."""
        answers = {f"gad7_{i}": 0 for i in range(1, 8)}
        result = score_gad7(answers)

        assert result.total == 0
        assert result.severity == "minimal"

    def test_all_threes(self) -> None:
        """Test maximum score (all items = 3)."""
        answers = {f"gad7_{i}": 3 for i in range(1, 8)}
        result = score_gad7(answers)

        assert result.total == 21
        assert result.severity == "severe"

    def test_total_calculation(self) -> None:
        """Test total is sum of all items."""
        answers = {f"gad7_{i}": i % 4 for i in range(1, 8)}
        result = score_gad7(answers)

        # Items: 1, 2, 3, 0, 1, 2, 3 = 12
        assert result.total == 12

    def test_individual_item_scores(self) -> None:
        """Test that individual item scores are captured correctly."""
        answers = {
            "gad7_1": 0,  # nervous
            "gad7_2": 1,  # uncontrollable_worry
            "gad7_3": 2,  # excessive_worry
            "gad7_4": 3,  # trouble_relaxing
            "gad7_5": 0,  # restlessness
            "gad7_6": 1,  # irritable
            "gad7_7": 2,  # afraid
        }
        result = score_gad7(answers)

        assert result.nervous == 0
        assert result.uncontrollable_worry == 1
        assert result.excessive_worry == 2
        assert result.trouble_relaxing == 3
        assert result.restlessness == 0
        assert result.irritable == 1
        assert result.afraid == 2
        assert result.total == 9


class TestGAD7SeverityBands:
    """Tests for GAD-7 severity band determination."""

    def test_minimal_band_lower_bound(self) -> None:
        """Test minimal severity at score 0."""
        assert get_severity_band(0) == "minimal"

    def test_minimal_band_upper_bound(self) -> None:
        """Test minimal severity at score 4."""
        assert get_severity_band(4) == "minimal"

    def test_mild_band_lower_bound(self) -> None:
        """Test mild severity at score 5."""
        assert get_severity_band(5) == "mild"

    def test_mild_band_upper_bound(self) -> None:
        """Test mild severity at score 9."""
        assert get_severity_band(9) == "mild"

    def test_moderate_band_lower_bound(self) -> None:
        """Test moderate severity at score 10."""
        assert get_severity_band(10) == "moderate"

    def test_moderate_band_upper_bound(self) -> None:
        """Test moderate severity at score 14."""
        assert get_severity_band(14) == "moderate"

    def test_severe_band_lower_bound(self) -> None:
        """Test severe at score 15."""
        assert get_severity_band(15) == "severe"

    def test_severe_band_upper_bound(self) -> None:
        """Test severe at score 21."""
        assert get_severity_band(21) == "severe"

    def test_integration_with_score(self) -> None:
        """Test severity bands through score_gad7."""
        test_cases = [
            (0, "minimal"),
            (4, "minimal"),
            (5, "mild"),
            (9, "mild"),
            (10, "moderate"),
            (14, "moderate"),
            (15, "severe"),
            (21, "severe"),
        ]

        for target_score, expected_severity in test_cases:
            # Build answers to achieve target score
            answers = {f"gad7_{i}": 0 for i in range(1, 8)}
            remaining = target_score
            for i in range(1, 8):
                if remaining <= 0:
                    break
                item_value = min(3, remaining)
                answers[f"gad7_{i}"] = item_value
                remaining -= item_value

            result = score_gad7(answers)
            assert result.total == target_score, f"Expected total {target_score}, got {result.total}"
            assert result.severity == expected_severity, (
                f"Score {target_score}: expected {expected_severity}, got {result.severity}"
            )


class TestGAD7KeyFormats:
    """Tests for different answer key formats."""

    def test_gad7_underscore_format(self) -> None:
        """Test 'gad7_N' key format."""
        answers = {f"gad7_{i}": 1 for i in range(1, 8)}
        result = score_gad7(answers)
        assert result.total == 7

    def test_item_format(self) -> None:
        """Test 'itemN' key format."""
        answers = {f"item{i}": 1 for i in range(1, 8)}
        result = score_gad7(answers)
        assert result.total == 7

    def test_q_format(self) -> None:
        """Test 'qN' key format."""
        answers = {f"q{i}": 1 for i in range(1, 8)}
        result = score_gad7(answers)
        assert result.total == 7

    def test_numeric_format(self) -> None:
        """Test 'N' (numeric string) key format."""
        answers = {str(i): 1 for i in range(1, 8)}
        result = score_gad7(answers)
        assert result.total == 7

    def test_gad7_item_format(self) -> None:
        """Test 'gad7_itemN' key format."""
        answers = {f"gad7_item{i}": 1 for i in range(1, 8)}
        result = score_gad7(answers)
        assert result.total == 7


class TestGAD7ValidationErrors:
    """Tests for GAD-7 input validation."""

    def test_missing_item_raises(self) -> None:
        """Test that missing items raise ValueError."""
        answers = {f"gad7_{i}": 1 for i in range(1, 7)}  # Missing item 7

        with pytest.raises(ValueError, match="Missing GAD-7 item 7"):
            score_gad7(answers)

    def test_value_below_range_raises(self) -> None:
        """Test that values below 0 raise ValueError."""
        answers = {f"gad7_{i}": 1 for i in range(1, 8)}
        answers["gad7_3"] = -1

        with pytest.raises(ValueError, match="GAD-7 item 3 must be integer 0-3"):
            score_gad7(answers)

    def test_value_above_range_raises(self) -> None:
        """Test that values above 3 raise ValueError."""
        answers = {f"gad7_{i}": 1 for i in range(1, 8)}
        answers["gad7_5"] = 4

        with pytest.raises(ValueError, match="GAD-7 item 5 must be integer 0-3"):
            score_gad7(answers)

    def test_non_integer_raises(self) -> None:
        """Test that non-integer values raise ValueError."""
        answers = {f"gad7_{i}": 1 for i in range(1, 8)}
        answers["gad7_1"] = "severe"

        with pytest.raises(ValueError, match="GAD-7 item 1 must be integer 0-3"):
            score_gad7(answers)

    def test_float_raises(self) -> None:
        """Test that float values raise ValueError."""
        answers = {f"gad7_{i}": 1 for i in range(1, 8)}
        answers["gad7_2"] = 1.5

        with pytest.raises(ValueError, match="GAD-7 item 2 must be integer 0-3"):
            score_gad7(answers)


class TestIsGADLikely:
    """Tests for GAD likely screening function."""

    def test_below_threshold(self) -> None:
        """Test scores below 10 return False."""
        answers = {f"gad7_{i}": 1 for i in range(1, 8)}
        result = score_gad7(answers)
        # Total = 7, below threshold
        assert is_gad_likely(result) is False

    def test_at_threshold(self) -> None:
        """Test score of exactly 10 returns True."""
        answers = {f"gad7_{i}": 0 for i in range(1, 8)}
        answers["gad7_1"] = 3
        answers["gad7_2"] = 3
        answers["gad7_3"] = 3
        answers["gad7_4"] = 1
        result = score_gad7(answers)
        assert result.total == 10
        assert is_gad_likely(result) is True

    def test_above_threshold(self) -> None:
        """Test scores above 10 return True."""
        answers = {f"gad7_{i}": 2 for i in range(1, 8)}
        result = score_gad7(answers)
        # Total = 14, above threshold
        assert is_gad_likely(result) is True


class TestGAD7Result:
    """Tests for GAD7Result dataclass."""

    def test_result_contains_all_fields(self) -> None:
        """Test that result contains all expected fields."""
        answers = {f"gad7_{i}": i % 4 for i in range(1, 8)}
        result = score_gad7(answers)

        assert hasattr(result, "total")
        assert hasattr(result, "severity")
        assert hasattr(result, "items")
        assert hasattr(result, "nervous")
        assert hasattr(result, "uncontrollable_worry")
        assert hasattr(result, "excessive_worry")
        assert hasattr(result, "trouble_relaxing")
        assert hasattr(result, "restlessness")
        assert hasattr(result, "irritable")
        assert hasattr(result, "afraid")

    def test_items_dict_structure(self) -> None:
        """Test that items dict has correct structure."""
        answers = {f"gad7_{i}": 1 for i in range(1, 8)}
        result = score_gad7(answers)

        assert len(result.items) == 7
        for i in range(1, 8):
            assert f"item{i}" in result.items
            assert result.items[f"item{i}"] == 1

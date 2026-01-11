"""Unit tests for PHQ-9 scoring module.

Tests the pure scoring logic from app.scoring.phq9.
"""

import pytest

from app.scoring.phq9 import (
    PHQ9Result,
    SEVERITY_BANDS,
    get_severity_band,
    score_phq9,
    is_major_depression_likely,
)


class TestPHQ9Scoring:
    """Tests for PHQ-9 score calculation."""

    def test_phq9_total_and_item9_positive(self) -> None:
        """Test total calculation and item9 detection."""
        answers = {f"phq9_{i}": 1 for i in range(1, 10)}
        answers["phq9_9"] = 2
        result = score_phq9(answers)
        assert result.total == 10  # 8*1 + 2 = 10
        assert result.item9_positive is True

    def test_all_zeros(self) -> None:
        """Test scoring when all items are 0."""
        answers = {f"phq9_{i}": 0 for i in range(1, 10)}
        result = score_phq9(answers)

        assert result.total == 0
        assert result.severity == "minimal"
        assert result.item9_positive is False
        assert result.item9_value == 0

    def test_all_threes(self) -> None:
        """Test maximum score (all items = 3)."""
        answers = {f"phq9_{i}": 3 for i in range(1, 10)}
        result = score_phq9(answers)

        assert result.total == 27
        assert result.severity == "severe"
        assert result.item9_positive is True
        assert result.item9_value == 3

    def test_item9_zero_not_positive(self) -> None:
        """Test that item9 = 0 is not flagged as positive."""
        answers = {f"phq9_{i}": 2 for i in range(1, 10)}
        answers["phq9_9"] = 0
        result = score_phq9(answers)

        assert result.item9_positive is False
        assert result.item9_value == 0

    def test_item9_one_is_positive(self) -> None:
        """Test that item9 = 1 is flagged as positive."""
        answers = {f"phq9_{i}": 0 for i in range(1, 10)}
        answers["phq9_9"] = 1
        result = score_phq9(answers)

        assert result.item9_positive is True
        assert result.item9_value == 1

    def test_individual_item_scores(self) -> None:
        """Test that individual item scores are captured correctly."""
        answers = {
            "phq9_1": 0,  # interest_loss
            "phq9_2": 1,  # depressed_mood
            "phq9_3": 2,  # sleep_problems
            "phq9_4": 3,  # fatigue
            "phq9_5": 0,  # appetite_changes
            "phq9_6": 1,  # self_criticism
            "phq9_7": 2,  # concentration
            "phq9_8": 3,  # psychomotor
            "phq9_9": 0,  # suicidal_ideation
        }
        result = score_phq9(answers)

        assert result.interest_loss == 0
        assert result.depressed_mood == 1
        assert result.sleep_problems == 2
        assert result.fatigue == 3
        assert result.appetite_changes == 0
        assert result.self_criticism == 1
        assert result.concentration == 2
        assert result.psychomotor == 3
        assert result.suicidal_ideation == 0
        assert result.total == 12


class TestPHQ9SeverityBands:
    """Tests for PHQ-9 severity band determination."""

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

    def test_moderately_severe_band_lower_bound(self) -> None:
        """Test moderately severe at score 15."""
        assert get_severity_band(15) == "moderately_severe"

    def test_moderately_severe_band_upper_bound(self) -> None:
        """Test moderately severe at score 19."""
        assert get_severity_band(19) == "moderately_severe"

    def test_severe_band_lower_bound(self) -> None:
        """Test severe at score 20."""
        assert get_severity_band(20) == "severe"

    def test_severe_band_upper_bound(self) -> None:
        """Test severe at score 27."""
        assert get_severity_band(27) == "severe"

    def test_integration_with_score(self) -> None:
        """Test severity bands through score_phq9."""
        test_cases = [
            (0, "minimal"),
            (4, "minimal"),
            (5, "mild"),
            (9, "mild"),
            (10, "moderate"),
            (14, "moderate"),
            (15, "moderately_severe"),
            (19, "moderately_severe"),
            (20, "severe"),
            (27, "severe"),
        ]

        for target_score, expected_severity in test_cases:
            # Build answers to achieve target score
            answers = {f"phq9_{i}": 0 for i in range(1, 10)}
            remaining = target_score
            for i in range(1, 10):
                if remaining <= 0:
                    break
                item_value = min(3, remaining)
                answers[f"phq9_{i}"] = item_value
                remaining -= item_value

            result = score_phq9(answers)
            assert result.total == target_score, f"Expected total {target_score}, got {result.total}"
            assert result.severity == expected_severity, (
                f"Score {target_score}: expected {expected_severity}, got {result.severity}"
            )


class TestPHQ9KeyFormats:
    """Tests for different answer key formats."""

    def test_phq9_underscore_format(self) -> None:
        """Test 'phq9_N' key format."""
        answers = {f"phq9_{i}": 1 for i in range(1, 10)}
        result = score_phq9(answers)
        assert result.total == 9

    def test_item_format(self) -> None:
        """Test 'itemN' key format."""
        answers = {f"item{i}": 1 for i in range(1, 10)}
        result = score_phq9(answers)
        assert result.total == 9

    def test_q_format(self) -> None:
        """Test 'qN' key format."""
        answers = {f"q{i}": 1 for i in range(1, 10)}
        result = score_phq9(answers)
        assert result.total == 9

    def test_numeric_format(self) -> None:
        """Test 'N' (numeric string) key format."""
        answers = {str(i): 1 for i in range(1, 10)}
        result = score_phq9(answers)
        assert result.total == 9

    def test_phq9_item_format(self) -> None:
        """Test 'phq9_itemN' key format."""
        answers = {f"phq9_item{i}": 1 for i in range(1, 10)}
        result = score_phq9(answers)
        assert result.total == 9

    def test_mixed_formats(self) -> None:
        """Test mixed key formats (first found is used)."""
        answers = {
            "phq9_1": 3,  # Should use this one
            "item1": 0,   # Ignored
            "phq9_2": 2,
            "q3": 1,
            "4": 0,
            "phq9_5": 1,
            "phq9_6": 1,
            "phq9_7": 0,
            "phq9_8": 0,
            "phq9_9": 1,
        }
        result = score_phq9(answers)
        assert result.total == 9


class TestPHQ9ValidationErrors:
    """Tests for PHQ-9 input validation."""

    def test_missing_item_raises(self) -> None:
        """Test that missing items raise ValueError."""
        answers = {f"phq9_{i}": 1 for i in range(1, 9)}  # Missing item 9

        with pytest.raises(ValueError, match="Missing PHQ-9 item 9"):
            score_phq9(answers)

    def test_value_below_range_raises(self) -> None:
        """Test that values below 0 raise ValueError."""
        answers = {f"phq9_{i}": 1 for i in range(1, 10)}
        answers["phq9_3"] = -1

        with pytest.raises(ValueError, match="PHQ-9 item 3 must be integer 0-3"):
            score_phq9(answers)

    def test_value_above_range_raises(self) -> None:
        """Test that values above 3 raise ValueError."""
        answers = {f"phq9_{i}": 1 for i in range(1, 10)}
        answers["phq9_5"] = 4

        with pytest.raises(ValueError, match="PHQ-9 item 5 must be integer 0-3"):
            score_phq9(answers)

    def test_non_integer_raises(self) -> None:
        """Test that non-integer values raise ValueError."""
        answers = {f"phq9_{i}": 1 for i in range(1, 10)}
        answers["phq9_1"] = "high"

        with pytest.raises(ValueError, match="PHQ-9 item 1 must be integer 0-3"):
            score_phq9(answers)

    def test_float_raises(self) -> None:
        """Test that float values raise ValueError."""
        answers = {f"phq9_{i}": 1 for i in range(1, 10)}
        answers["phq9_2"] = 1.5

        with pytest.raises(ValueError, match="PHQ-9 item 2 must be integer 0-3"):
            score_phq9(answers)


class TestMajorDepressionLikely:
    """Tests for major depression screening criterion."""

    def test_meets_criteria(self) -> None:
        """Test case meeting major depression criteria."""
        answers = {
            "phq9_1": 2,  # Core symptom >= 2
            "phq9_2": 2,  # Core symptom >= 2
            "phq9_3": 2,
            "phq9_4": 2,
            "phq9_5": 2,
            "phq9_6": 0,
            "phq9_7": 0,
            "phq9_8": 0,
            "phq9_9": 0,
        }
        result = score_phq9(answers)
        assert is_major_depression_likely(result) is True

    def test_insufficient_items(self) -> None:
        """Test case with fewer than 5 items >= 2."""
        answers = {
            "phq9_1": 2,  # Core symptom
            "phq9_2": 2,  # Core symptom
            "phq9_3": 2,
            "phq9_4": 2,
            "phq9_5": 0,  # Only 4 items >= 2
            "phq9_6": 0,
            "phq9_7": 0,
            "phq9_8": 0,
            "phq9_9": 0,
        }
        result = score_phq9(answers)
        assert is_major_depression_likely(result) is False

    def test_no_core_symptoms(self) -> None:
        """Test case with 5+ items >= 2 but no core symptoms."""
        answers = {
            "phq9_1": 1,  # Core symptom < 2
            "phq9_2": 1,  # Core symptom < 2
            "phq9_3": 2,
            "phq9_4": 2,
            "phq9_5": 2,
            "phq9_6": 2,
            "phq9_7": 2,
            "phq9_8": 0,
            "phq9_9": 0,
        }
        result = score_phq9(answers)
        assert is_major_depression_likely(result) is False

    def test_core_symptom_item1_only(self) -> None:
        """Test that item 1 alone satisfies core symptom requirement."""
        answers = {
            "phq9_1": 2,  # Core symptom >= 2
            "phq9_2": 0,  # Other core < 2
            "phq9_3": 2,
            "phq9_4": 2,
            "phq9_5": 2,
            "phq9_6": 2,
            "phq9_7": 0,
            "phq9_8": 0,
            "phq9_9": 0,
        }
        result = score_phq9(answers)
        assert is_major_depression_likely(result) is True

    def test_core_symptom_item2_only(self) -> None:
        """Test that item 2 alone satisfies core symptom requirement."""
        answers = {
            "phq9_1": 0,  # Core < 2
            "phq9_2": 2,  # Core symptom >= 2
            "phq9_3": 2,
            "phq9_4": 2,
            "phq9_5": 2,
            "phq9_6": 2,
            "phq9_7": 0,
            "phq9_8": 0,
            "phq9_9": 0,
        }
        result = score_phq9(answers)
        assert is_major_depression_likely(result) is True


class TestPHQ9Result:
    """Tests for PHQ9Result dataclass."""

    def test_result_contains_all_fields(self) -> None:
        """Test that result contains all expected fields."""
        answers = {f"phq9_{i}": i % 4 for i in range(1, 10)}
        result = score_phq9(answers)

        assert hasattr(result, "total")
        assert hasattr(result, "severity")
        assert hasattr(result, "item9_positive")
        assert hasattr(result, "item9_value")
        assert hasattr(result, "items")
        assert hasattr(result, "interest_loss")
        assert hasattr(result, "depressed_mood")
        assert hasattr(result, "sleep_problems")
        assert hasattr(result, "fatigue")
        assert hasattr(result, "appetite_changes")
        assert hasattr(result, "self_criticism")
        assert hasattr(result, "concentration")
        assert hasattr(result, "psychomotor")
        assert hasattr(result, "suicidal_ideation")

    def test_items_dict_structure(self) -> None:
        """Test that items dict has correct structure."""
        answers = {f"phq9_{i}": 1 for i in range(1, 10)}
        result = score_phq9(answers)

        assert len(result.items) == 9
        for i in range(1, 10):
            assert f"item{i}" in result.items
            assert result.items[f"item{i}"] == 1

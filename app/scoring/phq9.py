"""PHQ-9 (Patient Health Questionnaire-9) scoring module.

The PHQ-9 is a validated 9-item depression screening instrument.
Each item is scored 0-3:
- 0 = Not at all
- 1 = Several days
- 2 = More than half the days
- 3 = Nearly every day

Total score ranges 0-27.

Severity bands:
- 0-4: Minimal/None
- 5-9: Mild
- 10-14: Moderate
- 15-19: Moderately Severe
- 20-27: Severe

Item 9 specifically asks about suicidal ideation and requires special attention.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PHQ9Result:
    """Result of PHQ-9 scoring."""
    total: int
    severity: str
    item9_positive: bool
    item9_value: int
    items: dict[str, int]

    # Individual item scores for detailed analysis
    interest_loss: int      # Item 1: Little interest or pleasure
    depressed_mood: int     # Item 2: Feeling down, depressed, hopeless
    sleep_problems: int     # Item 3: Trouble sleeping or sleeping too much
    fatigue: int            # Item 4: Feeling tired or having little energy
    appetite_changes: int   # Item 5: Poor appetite or overeating
    self_criticism: int     # Item 6: Feeling bad about yourself
    concentration: int      # Item 7: Trouble concentrating
    psychomotor: int        # Item 8: Moving/speaking slowly or being restless
    suicidal_ideation: int  # Item 9: Thoughts of self-harm


# Severity band thresholds
SEVERITY_BANDS = [
    (0, 4, "minimal"),
    (5, 9, "mild"),
    (10, 14, "moderate"),
    (15, 19, "moderately_severe"),
    (20, 27, "severe"),
]


def get_severity_band(total: int) -> str:
    """Determine severity band from total score."""
    for low, high, band in SEVERITY_BANDS:
        if low <= total <= high:
            return band
    # Fallback for edge cases
    if total < 0:
        return "minimal"
    return "severe"


def score_phq9(answers: dict[str, int]) -> PHQ9Result:
    """Score PHQ-9 questionnaire responses.

    Args:
        answers: Dictionary with keys like "phq9_1" through "phq9_9"
                 or "item1" through "item9", values 0-3.

    Returns:
        PHQ9Result with total score, severity, and item breakdown.

    Raises:
        ValueError: If required items are missing or values out of range.
    """
    # Normalize key format and extract item values
    items = {}

    for i in range(1, 10):
        # Try different key formats
        key_formats = [
            f"phq9_{i}",
            f"phq9_item{i}",
            f"item{i}",
            f"q{i}",
            str(i),
        ]

        value = None
        for key in key_formats:
            if key in answers:
                value = answers[key]
                break

        if value is None:
            raise ValueError(f"Missing PHQ-9 item {i}")

        if not isinstance(value, int) or value < 0 or value > 3:
            raise ValueError(f"PHQ-9 item {i} must be integer 0-3, got {value}")

        items[f"item{i}"] = value

    # Calculate total
    total = sum(items.values())

    # Get severity band
    severity = get_severity_band(total)

    # Check item 9 (suicidal ideation)
    item9_value = items["item9"]
    item9_positive = item9_value > 0

    return PHQ9Result(
        total=total,
        severity=severity,
        item9_positive=item9_positive,
        item9_value=item9_value,
        items=items,
        interest_loss=items["item1"],
        depressed_mood=items["item2"],
        sleep_problems=items["item3"],
        fatigue=items["item4"],
        appetite_changes=items["item5"],
        self_criticism=items["item6"],
        concentration=items["item7"],
        psychomotor=items["item8"],
        suicidal_ideation=items["item9"],
    )


def is_major_depression_likely(result: PHQ9Result) -> bool:
    """Check if major depression is likely based on DSM-5 criteria.

    Major depression requires:
    - At least 5 items scored >= 2 (more than half the days)
    - Must include item 1 OR item 2 (core symptoms)
    """
    # Count items >= 2
    items_ge_2 = sum(1 for v in result.items.values() if v >= 2)

    # Check core symptoms
    core_symptom_present = result.interest_loss >= 2 or result.depressed_mood >= 2

    return items_ge_2 >= 5 and core_symptom_present


def get_functional_impairment_question() -> str:
    """Return the standard PHQ-9 functional impairment question.

    This is typically asked after the 9 items to assess impact on functioning.
    """
    return (
        "If you checked off any problems, how difficult have these problems "
        "made it for you to do your work, take care of things at home, or get "
        "along with other people?"
    )

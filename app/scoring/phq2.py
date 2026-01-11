"""PHQ-2 (Patient Health Questionnaire-2) scoring module.

The PHQ-2 is a brief 2-item depression screening using the first two
items of the PHQ-9.

Each item scored 0-3:
- 0 = Not at all
- 1 = Several days
- 2 = More than half the days
- 3 = Nearly every day

Total score ranges 0-6.
A score >= 3 is the standard cutoff for further evaluation.
"""

from dataclasses import dataclass


@dataclass
class PHQ2Result:
    """Result of PHQ-2 scoring."""
    total: int
    screen_positive: bool
    items: dict[str, int]
    interest_loss: int      # Item 1: Little interest or pleasure
    depressed_mood: int     # Item 2: Feeling down, depressed, hopeless


# Standard cutoff for positive screen
POSITIVE_CUTOFF = 3


def score_phq2(answers: dict[str, int]) -> PHQ2Result:
    """Score PHQ-2 questionnaire responses.

    Args:
        answers: Dictionary with keys like "phq2_1", "phq2_2" or
                 "phq2_q1", "phq2_q2" or "q1", "q2", values 0-3.

    Returns:
        PHQ2Result with total score and screen positive indicator.

    Raises:
        ValueError: If required items are missing or values out of range.
    """
    items = {}

    for i in range(1, 3):
        key_formats = [
            f"phq2_{i}",
            f"phq2_q{i}",
            f"phq2_item{i}",
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
            raise ValueError(f"Missing PHQ-2 item {i}")

        if not isinstance(value, int) or value < 0 or value > 3:
            raise ValueError(f"PHQ-2 item {i} must be integer 0-3, got {value}")

        items[f"item{i}"] = value

    total = sum(items.values())
    screen_positive = total >= POSITIVE_CUTOFF

    return PHQ2Result(
        total=total,
        screen_positive=screen_positive,
        items=items,
        interest_loss=items["item1"],
        depressed_mood=items["item2"],
    )

"""GAD-2 (Generalized Anxiety Disorder-2) scoring module.

The GAD-2 is a brief 2-item anxiety screening using the first two
items of the GAD-7.

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
class GAD2Result:
    """Result of GAD-2 scoring."""
    total: int
    screen_positive: bool
    items: dict[str, int]
    nervous: int           # Item 1: Feeling nervous, anxious, on edge
    uncontrollable_worry: int  # Item 2: Not being able to stop worrying


# Standard cutoff for positive screen
POSITIVE_CUTOFF = 3


def score_gad2(answers: dict[str, int]) -> GAD2Result:
    """Score GAD-2 questionnaire responses.

    Args:
        answers: Dictionary with keys like "gad2_1", "gad2_2" or
                 "gad2_q1", "gad2_q2" or "q1", "q2", values 0-3.

    Returns:
        GAD2Result with total score and screen positive indicator.

    Raises:
        ValueError: If required items are missing or values out of range.
    """
    items = {}

    for i in range(1, 3):
        key_formats = [
            f"gad2_{i}",
            f"gad2_q{i}",
            f"gad2_item{i}",
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
            raise ValueError(f"Missing GAD-2 item {i}")

        if not isinstance(value, int) or value < 0 or value > 3:
            raise ValueError(f"GAD-2 item {i} must be integer 0-3, got {value}")

        items[f"item{i}"] = value

    total = sum(items.values())
    screen_positive = total >= POSITIVE_CUTOFF

    return GAD2Result(
        total=total,
        screen_positive=screen_positive,
        items=items,
        nervous=items["item1"],
        uncontrollable_worry=items["item2"],
    )

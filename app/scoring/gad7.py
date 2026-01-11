"""GAD-7 (Generalized Anxiety Disorder-7) scoring module.

The GAD-7 is a validated 7-item anxiety screening instrument.
Each item is scored 0-3:
- 0 = Not at all
- 1 = Several days
- 2 = More than half the days
- 3 = Nearly every day

Total score ranges 0-21.

Severity bands:
- 0-4: Minimal
- 5-9: Mild
- 10-14: Moderate
- 15-21: Severe
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class GAD7Result:
    """Result of GAD-7 scoring."""
    total: int
    severity: str
    items: dict[str, int]

    # Individual item scores
    nervous: int           # Item 1: Feeling nervous, anxious, on edge
    uncontrollable_worry: int  # Item 2: Not being able to stop worrying
    excessive_worry: int   # Item 3: Worrying too much about different things
    trouble_relaxing: int  # Item 4: Trouble relaxing
    restlessness: int      # Item 5: Being so restless it's hard to sit still
    irritable: int         # Item 6: Becoming easily annoyed or irritable
    afraid: int            # Item 7: Feeling afraid something awful might happen


# Severity band thresholds
SEVERITY_BANDS = [
    (0, 4, "minimal"),
    (5, 9, "mild"),
    (10, 14, "moderate"),
    (15, 21, "severe"),
]


def get_severity_band(total: int) -> str:
    """Determine severity band from total score."""
    for low, high, band in SEVERITY_BANDS:
        if low <= total <= high:
            return band
    if total < 0:
        return "minimal"
    return "severe"


def score_gad7(answers: dict[str, int]) -> GAD7Result:
    """Score GAD-7 questionnaire responses.

    Args:
        answers: Dictionary with keys like "gad7_1" through "gad7_7"
                 or "item1" through "item7", values 0-3.

    Returns:
        GAD7Result with total score, severity, and item breakdown.

    Raises:
        ValueError: If required items are missing or values out of range.
    """
    items = {}

    for i in range(1, 8):
        # Try different key formats
        key_formats = [
            f"gad7_{i}",
            f"gad7_item{i}",
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
            raise ValueError(f"Missing GAD-7 item {i}")

        if not isinstance(value, int) or value < 0 or value > 3:
            raise ValueError(f"GAD-7 item {i} must be integer 0-3, got {value}")

        items[f"item{i}"] = value

    # Calculate total
    total = sum(items.values())

    # Get severity band
    severity = get_severity_band(total)

    return GAD7Result(
        total=total,
        severity=severity,
        items=items,
        nervous=items["item1"],
        uncontrollable_worry=items["item2"],
        excessive_worry=items["item3"],
        trouble_relaxing=items["item4"],
        restlessness=items["item5"],
        irritable=items["item6"],
        afraid=items["item7"],
    )


def is_gad_likely(result: GAD7Result) -> bool:
    """Check if GAD is likely based on screening criteria.

    A score >= 10 suggests clinically significant anxiety.
    """
    return result.total >= 10

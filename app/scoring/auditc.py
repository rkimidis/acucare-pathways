"""AUDIT-C (Alcohol Use Disorders Identification Test - Consumption) scoring module.

The AUDIT-C is a brief 3-item alcohol screening using the first three
items of the full AUDIT questionnaire.

Scoring:
- Q1 (frequency): 0-4 points
- Q2 (typical quantity): 0-4 points
- Q3 (binge frequency): 0-4 points

Total score ranges 0-12.

Risk thresholds:
- Men: >= 4 indicates at-risk drinking
- Women: >= 3 indicates at-risk drinking
- >= 8 indicates high-risk / possible dependence

Clinical note: Higher scores warrant full AUDIT or clinical assessment.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AUDITCResult:
    """Result of AUDIT-C scoring."""

    total: int
    risk_level: str
    above_male_threshold: bool
    above_female_threshold: bool
    high_risk: bool
    items: dict[str, int]

    # Individual item scores
    frequency: int       # Q1: How often do you have a drink containing alcohol?
    typical_quantity: int  # Q2: How many drinks on a typical drinking day?
    binge_frequency: int   # Q3: How often 6+ drinks on one occasion?


# Risk thresholds
MALE_THRESHOLD = 4
FEMALE_THRESHOLD = 3
HIGH_RISK_THRESHOLD = 8


def get_risk_level(total: int, sex: Optional[str] = None) -> str:
    """Determine risk level from total score.

    Args:
        total: AUDIT-C total score
        sex: Optional 'male' or 'female' for sex-specific thresholds

    Returns:
        Risk level: 'low', 'at_risk', or 'high_risk'
    """
    if total >= HIGH_RISK_THRESHOLD:
        return "high_risk"

    if sex and sex.lower() == "female":
        if total >= FEMALE_THRESHOLD:
            return "at_risk"
    elif sex and sex.lower() == "male":
        if total >= MALE_THRESHOLD:
            return "at_risk"
    else:
        # Without sex info, use more conservative female threshold
        if total >= FEMALE_THRESHOLD:
            return "at_risk"

    return "low"


def score_auditc(answers: dict[str, int], sex: Optional[str] = None) -> AUDITCResult:
    """Score AUDIT-C questionnaire responses.

    Args:
        answers: Dictionary with keys like "auditc_1", "auditc_2", "auditc_3"
                 or "q1", "q2", "q3", values 0-4.
        sex: Optional 'male' or 'female' for sex-specific risk assessment

    Returns:
        AUDITCResult with total score, risk level, and item breakdown.

    Raises:
        ValueError: If required items are missing or values out of range.

    Item scoring reference:
        Q1 - How often do you have a drink containing alcohol?
            0 = Never
            1 = Monthly or less
            2 = 2-4 times a month
            3 = 2-3 times a week
            4 = 4+ times a week

        Q2 - How many standard drinks on a typical day when drinking?
            0 = 1-2
            1 = 3-4
            2 = 5-6
            3 = 7-9
            4 = 10+

        Q3 - How often do you have 6+ drinks on one occasion?
            0 = Never
            1 = Less than monthly
            2 = Monthly
            3 = Weekly
            4 = Daily or almost daily
    """
    items = {}

    for i in range(1, 4):
        # Try different key formats
        key_formats = [
            f"auditc_{i}",
            f"auditc_q{i}",
            f"auditc_item{i}",
            f"audit_c_{i}",
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
            raise ValueError(f"Missing AUDIT-C item {i}")

        if not isinstance(value, int) or value < 0 or value > 4:
            raise ValueError(f"AUDIT-C item {i} must be integer 0-4, got {value}")

        items[f"item{i}"] = value

    # Calculate total
    total = sum(items.values())

    # Determine thresholds
    above_male_threshold = total >= MALE_THRESHOLD
    above_female_threshold = total >= FEMALE_THRESHOLD
    high_risk = total >= HIGH_RISK_THRESHOLD

    # Get risk level
    risk_level = get_risk_level(total, sex)

    return AUDITCResult(
        total=total,
        risk_level=risk_level,
        above_male_threshold=above_male_threshold,
        above_female_threshold=above_female_threshold,
        high_risk=high_risk,
        items=items,
        frequency=items["item1"],
        typical_quantity=items["item2"],
        binge_frequency=items["item3"],
    )


def needs_full_audit(result: AUDITCResult) -> bool:
    """Check if full AUDIT assessment is recommended.

    Full AUDIT recommended when AUDIT-C >= 3 (female) or >= 4 (male),
    or when any concerning patterns are present.
    """
    return result.above_female_threshold or result.high_risk


def needs_clinical_assessment(result: AUDITCResult) -> bool:
    """Check if clinical assessment for alcohol use disorder is recommended.

    Clinical assessment recommended when score indicates high risk.
    """
    return result.high_risk

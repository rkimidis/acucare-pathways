"""Facts extraction from responses and scores.

Extracts a structured facts dictionary from questionnaire responses
and calculated scores for use in rules evaluation.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from app.scoring.phq9 import score_phq9, PHQ9Result
from app.scoring.gad7 import score_gad7, GAD7Result
from app.scoring.phq2 import score_phq2, PHQ2Result
from app.scoring.gad2 import score_gad2, GAD2Result
from app.scoring.auditc import score_auditc, AUDITCResult


@dataclass
class ScoreFacts:
    """Score-related facts."""
    phq9: Optional[dict] = None
    gad7: Optional[dict] = None
    phq2: Optional[dict] = None
    gad2: Optional[dict] = None
    auditc: Optional[dict] = None


@dataclass
class RiskFacts:
    """Risk-related facts from direct questions."""
    suicidal_ideation: bool = False
    self_harm: bool = False
    harm_to_others: bool = False
    psychosis: bool = False
    substance_use_severe: bool = False
    recent_crisis: bool = False
    previous_inpatient: bool = False
    current_treatment: bool = False


@dataclass
class DemographicFacts:
    """Demographic and context facts."""
    age: Optional[int] = None
    is_minor: bool = False
    is_elderly: bool = False
    pregnant: bool = False
    has_care_plan: bool = False
    has_gp: bool = False


@dataclass
class Facts:
    """Complete facts extracted from assessment data."""
    scores: ScoreFacts = field(default_factory=ScoreFacts)
    risk: RiskFacts = field(default_factory=RiskFacts)
    demographics: DemographicFacts = field(default_factory=DemographicFacts)
    raw_responses: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to flat dictionary for rules evaluation."""
        return {
            "scores": asdict(self.scores),
            "risk": asdict(self.risk),
            "demographics": asdict(self.demographics),
        }


def extract_facts(
    responses: dict[str, dict],
    risk_answers: Optional[dict[str, bool]] = None,
    demographics: Optional[dict] = None,
) -> Facts:
    """Extract facts from questionnaire responses and additional data.

    Args:
        responses: Dict of questionnaire responses keyed by questionnaire code.
                   e.g., {"phq9": {"phq9_1": 2, ...}, "gad7": {...}}
        risk_answers: Dict of risk-related boolean answers.
                      e.g., {"suicidal_ideation": True, "self_harm": False}
        demographics: Dict of demographic data.
                      e.g., {"age": 35, "pregnant": False}

    Returns:
        Facts object with extracted scores and risk indicators.
    """
    facts = Facts()

    # Process PHQ-9 if present
    if "phq9" in responses:
        try:
            phq9_result = score_phq9(responses["phq9"])
            facts.scores.phq9 = {
                "total": phq9_result.total,
                "severity": phq9_result.severity,
                "item9_positive": phq9_result.item9_positive,
                "item9_value": phq9_result.item9_value,
                "interest_loss": phq9_result.interest_loss,
                "depressed_mood": phq9_result.depressed_mood,
            }
            # PHQ-9 item 9 is a risk indicator
            if phq9_result.item9_positive:
                facts.risk.suicidal_ideation = True
        except ValueError:
            pass

    # Process GAD-7 if present
    if "gad7" in responses:
        try:
            gad7_result = score_gad7(responses["gad7"])
            facts.scores.gad7 = {
                "total": gad7_result.total,
                "severity": gad7_result.severity,
                "nervous": gad7_result.nervous,
                "uncontrollable_worry": gad7_result.uncontrollable_worry,
            }
        except ValueError:
            pass

    # Process PHQ-2 if present
    if "phq2" in responses:
        try:
            phq2_result = score_phq2(responses["phq2"])
            facts.scores.phq2 = {
                "total": phq2_result.total,
                "screen_positive": phq2_result.screen_positive,
            }
        except ValueError:
            pass

    # Process GAD-2 if present
    if "gad2" in responses:
        try:
            gad2_result = score_gad2(responses["gad2"])
            facts.scores.gad2 = {
                "total": gad2_result.total,
                "screen_positive": gad2_result.screen_positive,
            }
        except ValueError:
            pass

    # Process AUDIT-C if present
    if "auditc" in responses:
        try:
            # Get sex from demographics for sex-specific thresholds
            sex = demographics.get("sex") if demographics else None
            auditc_result = score_auditc(responses["auditc"], sex=sex)
            facts.scores.auditc = {
                "total": auditc_result.total,
                "risk_level": auditc_result.risk_level,
                "above_male_threshold": auditc_result.above_male_threshold,
                "above_female_threshold": auditc_result.above_female_threshold,
                "high_risk": auditc_result.high_risk,
                "frequency": auditc_result.frequency,
                "binge_frequency": auditc_result.binge_frequency,
            }
            # High risk AUDIT-C is a substance use indicator
            if auditc_result.high_risk:
                facts.risk.substance_use_severe = True
        except ValueError:
            pass

    # Process explicit risk answers
    if risk_answers:
        facts.risk.suicidal_ideation = risk_answers.get("suicidal_ideation", False) or facts.risk.suicidal_ideation
        facts.risk.self_harm = risk_answers.get("self_harm", False)
        facts.risk.harm_to_others = risk_answers.get("harm_to_others", False)
        facts.risk.psychosis = risk_answers.get("psychosis", False)
        facts.risk.substance_use_severe = risk_answers.get("substance_use_severe", False)
        facts.risk.recent_crisis = risk_answers.get("recent_crisis", False)
        facts.risk.previous_inpatient = risk_answers.get("previous_inpatient", False)
        facts.risk.current_treatment = risk_answers.get("current_treatment", False)

    # Process demographics
    if demographics:
        age = demographics.get("age")
        if age is not None:
            facts.demographics.age = age
            facts.demographics.is_minor = age < 18
            facts.demographics.is_elderly = age >= 65

        facts.demographics.pregnant = demographics.get("pregnant", False)
        facts.demographics.has_care_plan = demographics.get("has_care_plan", False)
        facts.demographics.has_gp = demographics.get("has_gp", False)

    # Store raw responses
    facts.raw_responses = responses

    return facts


def extract_facts_from_checkin(
    phq2_q1: int,
    phq2_q2: int,
    gad2_q1: int,
    gad2_q2: int,
    suicidal_ideation: bool = False,
    self_harm: bool = False,
    wellbeing_rating: Optional[int] = None,
) -> Facts:
    """Extract facts from a waiting list check-in.

    Convenience function for check-in processing.
    """
    responses = {
        "phq2": {"phq2_1": phq2_q1, "phq2_2": phq2_q2},
        "gad2": {"gad2_1": gad2_q1, "gad2_2": gad2_q2},
    }

    risk_answers = {
        "suicidal_ideation": suicidal_ideation,
        "self_harm": self_harm,
    }

    facts = extract_facts(responses, risk_answers)

    # Add wellbeing rating to raw responses
    if wellbeing_rating is not None:
        facts.raw_responses["wellbeing_rating"] = wellbeing_rating

    return facts

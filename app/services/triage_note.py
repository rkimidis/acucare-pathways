"""Triage note generation service.

Generates structured clinical triage notes from case data.
Template-based narrative generation (no LLM).
"""

from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.triage_case import TriageTier


class TriageNoteGenerator:
    """Generates structured triage notes from case data.

    Uses template-based narrative generation without LLM.
    """

    # Tier descriptions for narrative
    TIER_DESCRIPTIONS = {
        TriageTier.RED: "Crisis presentation requiring immediate clinical review",
        TriageTier.AMBER: "Elevated risk presentation requiring priority clinical review",
        TriageTier.GREEN: "Routine presentation suitable for standard assessment pathway",
        TriageTier.BLUE: "Mild presentation suitable for low-intensity/digital pathway",
    }

    # Pathway descriptions
    PATHWAY_DESCRIPTIONS = {
        "CRISIS_ESCALATION": "Immediate crisis team escalation",
        "PSYCHIATRY_ASSESSMENT": "Psychiatric assessment required",
        "SUBSTANCE_PATHWAY": "Substance use service referral",
        "THERAPY_ASSESSMENT": "Standard therapy assessment",
        "TRAUMA_THERAPY_PATHWAY": "Trauma-focused therapy pathway",
        "NEURODEVELOPMENTAL_TRIAGE": "Neurodevelopmental assessment triage",
        "LOW_INTENSITY_DIGITAL": "Low-intensity digital support",
    }

    def __init__(self, case_summary: dict[str, Any]) -> None:
        """Initialize generator with case summary.

        Args:
            case_summary: Full case summary from DashboardService.get_case_summary()
        """
        self.case = case_summary.get("case", {})
        self.patient = case_summary.get("patient", {})
        self.scores = case_summary.get("scores", [])
        self.risk_flags = case_summary.get("risk_flags", [])
        self.draft = case_summary.get("draft_disposition", {})
        self.final = case_summary.get("final_disposition", {})
        self.responses = case_summary.get("questionnaire_responses", [])

    def generate_narrative(self) -> str:
        """Generate a template-based narrative note.

        Returns:
            Structured narrative string
        """
        sections = [
            self._header_section(),
            self._patient_section(),
            self._scores_section(),
            self._risk_flags_section(),
            self._disposition_section(),
            self._clinical_notes_section(),
            self._footer_section(),
        ]

        return "\n\n".join(s for s in sections if s)

    def _header_section(self) -> str:
        """Generate header section."""
        tier = self.case.get("tier", "").upper()
        pathway = self.case.get("pathway", "")
        case_id = self.case.get("id", "N/A")[:8]

        return f"""TRIAGE ASSESSMENT SUMMARY
{'=' * 50}
Case Reference: {case_id}...
Assessment Date: {self._format_datetime(self.case.get('triaged_at'))}
Tier Assignment: {tier}
Pathway: {pathway}"""

    def _patient_section(self) -> str:
        """Generate patient information section."""
        if not self.patient:
            return ""

        return f"""PATIENT INFORMATION
{'-' * 30}
Name: {self.patient.get('first_name', '')} {self.patient.get('last_name', '')}
Date of Birth: {self.patient.get('date_of_birth', 'Not recorded')}
Patient ID: {self.patient.get('id', 'N/A')[:8]}..."""

    def _scores_section(self) -> str:
        """Generate clinical scores section."""
        if not self.scores:
            return """CLINICAL SCREENING SCORES
{'-' * 30}
No standardized assessments completed."""

        lines = ["CLINICAL SCREENING SCORES", "-" * 30]

        for score in self.scores:
            score_type = score.get("score_type", "Unknown")
            total = score.get("total_score", 0)
            max_score = score.get("max_score", 0)
            severity = score.get("severity_band", "Unknown")

            interpretation = self._get_score_interpretation(score_type, severity)

            lines.append(f"\n{score_type}:")
            lines.append(f"  Score: {total}/{max_score}")
            lines.append(f"  Severity: {severity}")
            lines.append(f"  Interpretation: {interpretation}")

            # Add PHQ-9 item 9 note if applicable
            metadata = score.get("metadata", {})
            if score_type == "PHQ9" and metadata.get("item9_positive"):
                lines.append("  ** PHQ-9 Item 9 (suicidal ideation) endorsed **")

        return "\n".join(lines)

    def _get_score_interpretation(self, score_type: str, severity: str) -> str:
        """Get clinical interpretation for score."""
        interpretations = {
            ("PHQ9", "MINIMAL"): "No significant depressive symptoms",
            ("PHQ9", "MILD"): "Mild depressive symptoms - monitor",
            ("PHQ9", "MODERATE"): "Moderate depression - treatment indicated",
            ("PHQ9", "MODERATELY_SEVERE"): "Moderately severe depression - active treatment required",
            ("PHQ9", "SEVERE"): "Severe depression - urgent treatment indicated",
            ("GAD7", "MINIMAL"): "No significant anxiety symptoms",
            ("GAD7", "MILD"): "Mild anxiety - monitor",
            ("GAD7", "MODERATE"): "Moderate anxiety - treatment indicated",
            ("GAD7", "SEVERE"): "Severe anxiety - urgent treatment indicated",
            ("AUDIT_C", "MINIMAL"): "Low-risk alcohol use",
            ("AUDIT_C", "MILD"): "Increasing-risk alcohol use",
            ("AUDIT_C", "MODERATE"): "Higher-risk alcohol use - brief intervention indicated",
            ("AUDIT_C", "SEVERE"): "Possible dependence - specialist referral indicated",
        }

        return interpretations.get(
            (score_type, severity),
            "Clinical interpretation required"
        )

    def _risk_flags_section(self) -> str:
        """Generate risk flags section."""
        lines = ["RISK INDICATORS", "-" * 30]

        if not self.risk_flags:
            lines.append("No elevated risk indicators identified.")
        else:
            # Group by severity
            critical = [f for f in self.risk_flags if f.get("severity") == "CRITICAL"]
            high = [f for f in self.risk_flags if f.get("severity") == "HIGH"]
            medium = [f for f in self.risk_flags if f.get("severity") == "MEDIUM"]
            low = [f for f in self.risk_flags if f.get("severity") == "LOW"]

            for severity, flags in [
                ("CRITICAL", critical),
                ("HIGH", high),
                ("MEDIUM", medium),
                ("LOW", low),
            ]:
                if flags:
                    lines.append(f"\n{severity} Risk:")
                    for flag in flags:
                        lines.append(f"  - {flag.get('flag_type', 'Unknown')}")
                        if flag.get("explanation"):
                            lines.append(f"    {flag.get('explanation')}")

        return "\n".join(lines)

    def _disposition_section(self) -> str:
        """Generate disposition section."""
        lines = ["TRIAGE DISPOSITION", "-" * 30]

        tier_str = self.case.get("tier", "").upper()
        tier = TriageTier(tier_str.lower()) if tier_str else None
        tier_desc = self.TIER_DESCRIPTIONS.get(tier, "")
        pathway = self.case.get("pathway", "")
        pathway_desc = self.PATHWAY_DESCRIPTIONS.get(pathway, "")

        lines.append(f"\nTier: {tier_str}")
        lines.append(f"Description: {tier_desc}")
        lines.append(f"\nPathway: {pathway}")
        lines.append(f"Description: {pathway_desc}")

        # Add disposition details
        if self.final:
            lines.append(f"\nDisposition Status: FINALIZED")
            if self.final.get("is_override"):
                lines.append("** CLINICIAN OVERRIDE **")
                lines.append(f"Original Tier: {self.final.get('original_tier')}")
                lines.append(f"Original Pathway: {self.final.get('original_pathway')}")
                lines.append(f"Override Rationale: {self.final.get('rationale')}")
            lines.append(f"Finalized: {self._format_datetime(self.final.get('finalized_at'))}")
        elif self.draft:
            lines.append(f"\nDisposition Status: DRAFT (awaiting review)")

        # Add rules fired
        if self.draft and self.draft.get("rules_fired"):
            lines.append("\nRules Applied:")
            for rule in self.draft.get("rules_fired", []):
                lines.append(f"  - {rule}")

        # Add explanations
        if self.draft and self.draft.get("explanations"):
            lines.append("\nRule Explanations:")
            for exp in self.draft.get("explanations", []):
                lines.append(f"  - {exp}")

        # Add booking restrictions
        self_book = self.case.get("self_book_allowed", True)
        review_required = self.case.get("clinician_review_required", False)

        lines.append(f"\nBooking Restrictions:")
        lines.append(f"  Self-booking: {'Allowed' if self_book else 'BLOCKED'}")
        lines.append(f"  Clinician review: {'REQUIRED' if review_required else 'Optional'}")

        return "\n".join(lines)

    def _clinical_notes_section(self) -> str:
        """Generate clinical notes section."""
        notes = self.case.get("clinical_notes") or ""
        final_notes = self.final.get("clinical_notes") if self.final else None

        if not notes and not final_notes:
            return ""

        lines = ["CLINICAL NOTES", "-" * 30]

        if notes:
            lines.append(notes)
        if final_notes:
            lines.append(f"\nDisposition Notes: {final_notes}")

        return "\n".join(lines)

    def _footer_section(self) -> str:
        """Generate footer section."""
        ruleset_version = self.case.get("ruleset_version", "Unknown")
        ruleset_hash = self.case.get("ruleset_hash", "")[:8] if self.case.get("ruleset_hash") else "N/A"
        generated_at = datetime.now(timezone.utc).isoformat()

        return f"""{'=' * 50}
AUDIT INFORMATION
Ruleset Version: {ruleset_version}
Ruleset Hash: {ruleset_hash}...
Generated: {generated_at}

This is an automatically generated triage assessment summary.
Clinical decisions should be made by qualified healthcare professionals."""

    def _format_datetime(self, dt_str: str | None) -> str:
        """Format datetime string for display."""
        if not dt_str:
            return "Not recorded"
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            return dt.strftime("%d %B %Y at %H:%M UTC")
        except (ValueError, AttributeError):
            return dt_str


class PDFExporter:
    """Exports triage notes to PDF format."""

    def __init__(self) -> None:
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self) -> None:
        """Setup custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name="Header",
            parent=self.styles["Heading1"],
            fontSize=16,
            spaceAfter=12,
        ))
        self.styles.add(ParagraphStyle(
            name="SectionHeader",
            parent=self.styles["Heading2"],
            fontSize=12,
            spaceAfter=8,
            textColor=colors.darkblue,
        ))
        self.styles.add(ParagraphStyle(
            name="BodyText",
            parent=self.styles["Normal"],
            fontSize=10,
            spaceAfter=6,
        ))
        self.styles.add(ParagraphStyle(
            name="AlertText",
            parent=self.styles["Normal"],
            fontSize=10,
            textColor=colors.red,
            fontName="Helvetica-Bold",
        ))
        self.styles.add(ParagraphStyle(
            name="Footer",
            parent=self.styles["Normal"],
            fontSize=8,
            textColor=colors.grey,
        ))

    def generate_pdf(self, case_summary: dict[str, Any]) -> bytes:
        """Generate PDF from case summary.

        Args:
            case_summary: Full case summary dict

        Returns:
            PDF bytes
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        story = []
        case = case_summary.get("case", {})
        patient = case_summary.get("patient", {})
        scores = case_summary.get("scores", [])
        risk_flags = case_summary.get("risk_flags", [])
        draft = case_summary.get("draft_disposition", {})
        final = case_summary.get("final_disposition", {})

        # Header
        story.append(Paragraph("TRIAGE ASSESSMENT SUMMARY", self.styles["Header"]))
        story.append(Spacer(1, 5 * mm))

        # Case info table
        tier = case.get("tier", "").upper()
        tier_color = self._get_tier_color(tier)

        case_data = [
            ["Case ID:", case.get("id", "N/A")[:8] + "..."],
            ["Tier:", tier],
            ["Pathway:", case.get("pathway", "N/A")],
            ["Status:", case.get("status", "N/A").upper()],
            ["Triaged:", self._format_datetime(case.get("triaged_at"))],
        ]

        case_table = Table(case_data, colWidths=[80, 300])
        case_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (1, 1), (1, 1), "Helvetica-Bold"),
            ("TEXTCOLOR", (1, 1), (1, 1), tier_color),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(case_table)
        story.append(Spacer(1, 8 * mm))

        # Patient info
        if patient:
            story.append(Paragraph("PATIENT INFORMATION", self.styles["SectionHeader"]))
            patient_data = [
                ["Name:", f"{patient.get('first_name', '')} {patient.get('last_name', '')}"],
                ["DOB:", patient.get("date_of_birth", "Not recorded")],
            ]
            patient_table = Table(patient_data, colWidths=[80, 300])
            patient_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
            ]))
            story.append(patient_table)
            story.append(Spacer(1, 6 * mm))

        # Scores
        if scores:
            story.append(Paragraph("CLINICAL SCREENING SCORES", self.styles["SectionHeader"]))
            score_data = [["Assessment", "Score", "Severity"]]
            for score in scores:
                score_data.append([
                    score.get("score_type", "Unknown"),
                    f"{score.get('total_score', 0)}/{score.get('max_score', 0)}",
                    score.get("severity_band", "Unknown"),
                ])

            score_table = Table(score_data, colWidths=[120, 80, 120])
            score_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ]))
            story.append(score_table)
            story.append(Spacer(1, 6 * mm))

        # Risk Flags
        if risk_flags:
            story.append(Paragraph("RISK INDICATORS", self.styles["SectionHeader"]))
            for flag in risk_flags:
                severity = flag.get("severity", "")
                if severity in ["CRITICAL", "HIGH"]:
                    style = self.styles["AlertText"]
                else:
                    style = self.styles["BodyText"]

                text = f"[{severity}] {flag.get('flag_type', '')}"
                if flag.get("explanation"):
                    text += f" - {flag.get('explanation')}"
                story.append(Paragraph(text, style))
            story.append(Spacer(1, 6 * mm))

        # Disposition
        story.append(Paragraph("DISPOSITION", self.styles["SectionHeader"]))

        if final and final.get("is_override"):
            story.append(Paragraph(
                "** CLINICIAN OVERRIDE **",
                self.styles["AlertText"]
            ))
            story.append(Paragraph(
                f"Original: {final.get('original_tier')} / {final.get('original_pathway')}",
                self.styles["BodyText"]
            ))
            story.append(Paragraph(
                f"Override Rationale: {final.get('rationale')}",
                self.styles["BodyText"]
            ))

        disp_data = [
            ["Final Tier:", case.get("tier", "").upper()],
            ["Final Pathway:", case.get("pathway", "")],
            ["Self-booking:", "Allowed" if case.get("self_book_allowed") else "BLOCKED"],
            ["Clinician Review:", "REQUIRED" if case.get("clinician_review_required") else "Optional"],
        ]
        disp_table = Table(disp_data, colWidths=[100, 280])
        disp_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
        ]))
        story.append(disp_table)
        story.append(Spacer(1, 6 * mm))

        # Rules fired
        if draft and draft.get("rules_fired"):
            story.append(Paragraph("RULES APPLIED", self.styles["SectionHeader"]))
            for rule in draft.get("rules_fired", []):
                story.append(Paragraph(f"• {rule}", self.styles["BodyText"]))
            story.append(Spacer(1, 6 * mm))

        # Footer
        story.append(Spacer(1, 10 * mm))
        footer_text = f"""
        Ruleset Version: {case.get('ruleset_version', 'Unknown')} |
        Ruleset Hash: {case.get('ruleset_hash', '')[:8]}... |
        Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
        """
        story.append(Paragraph(footer_text.strip(), self.styles["Footer"]))
        story.append(Paragraph(
            "This is an automatically generated triage assessment summary. "
            "Clinical decisions should be made by qualified healthcare professionals.",
            self.styles["Footer"]
        ))

        doc.build(story)

        return buffer.getvalue()

    def _get_tier_color(self, tier: str) -> colors.Color:
        """Get color for tier."""
        tier_colors = {
            "RED": colors.red,
            "AMBER": colors.orange,
            "GREEN": colors.green,
            "BLUE": colors.blue,
        }
        return tier_colors.get(tier.upper(), colors.black)

    def _format_datetime(self, dt_str: str | None) -> str:
        """Format datetime string."""
        if not dt_str:
            return "Not recorded"
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            return dt.strftime("%d %B %Y %H:%M UTC")
        except (ValueError, AttributeError):
            return dt_str

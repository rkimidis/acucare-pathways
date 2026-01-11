"""Database fixtures for AcuCare Pathways.

Contains seed data for:
- Message templates
- Questionnaire definitions
- Default triage rules
"""

from app.fixtures.message_templates import MESSAGE_TEMPLATES, seed_templates

__all__ = ["MESSAGE_TEMPLATES", "seed_templates"]

"""Tests for evidence export service.

Sprint 6 tests covering:
- Export contains correct audit events
- Export is tamper-evident (hash verification)
- Chain hash computation
"""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.evidence_export import EvidenceExportService


class TestTamperEvidentExport:
    """Tests that exports are tamper-evident with hash verification."""

    def test_compute_hash_consistency(self) -> None:
        """Same content produces same hash."""
        content = "test content for hashing"

        hash1 = EvidenceExportService.compute_hash(content)
        hash2 = EvidenceExportService.compute_hash(content)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 produces 64-char hex

    def test_compute_hash_different_content(self) -> None:
        """Different content produces different hash."""
        hash1 = EvidenceExportService.compute_hash("content A")
        hash2 = EvidenceExportService.compute_hash("content B")

        assert hash1 != hash2

    def test_compute_chain_hash_ordering(self) -> None:
        """Chain hash depends on record order."""
        records = [
            {"id": "1", "action": "create"},
            {"id": "2", "action": "update"},
            {"id": "3", "action": "delete"},
        ]

        hash1 = EvidenceExportService.compute_chain_hash(records)

        # Reversed order should produce different hash
        reversed_records = list(reversed(records))
        hash2 = EvidenceExportService.compute_chain_hash(reversed_records)

        assert hash1 != hash2

    def test_compute_chain_hash_empty_list(self) -> None:
        """Empty list produces empty chain hash."""
        hash_result = EvidenceExportService.compute_chain_hash([])
        assert hash_result == ""

    def test_compute_chain_hash_single_record(self) -> None:
        """Single record produces valid hash."""
        records = [{"id": "1", "action": "test"}]
        hash_result = EvidenceExportService.compute_chain_hash(records)

        assert len(hash_result) == 64

    def test_compute_chain_hash_deterministic(self) -> None:
        """Same records in same order produce same hash."""
        records = [
            {"id": "1", "timestamp": "2024-01-01T00:00:00"},
            {"id": "2", "timestamp": "2024-01-01T00:01:00"},
        ]

        hash1 = EvidenceExportService.compute_chain_hash(records)
        hash2 = EvidenceExportService.compute_chain_hash(records)

        assert hash1 == hash2

    def test_chain_hash_detects_tampering(self) -> None:
        """Modifying any record changes the chain hash."""
        original_records = [
            {"id": "1", "action": "create", "data": "original"},
            {"id": "2", "action": "update", "data": "value"},
        ]

        original_hash = EvidenceExportService.compute_chain_hash(original_records)

        # Tamper with data
        tampered_records = [
            {"id": "1", "action": "create", "data": "TAMPERED"},
            {"id": "2", "action": "update", "data": "value"},
        ]

        tampered_hash = EvidenceExportService.compute_chain_hash(tampered_records)

        assert original_hash != tampered_hash


class TestExportIntegrityVerification:
    """Tests for export integrity verification."""

    def test_verify_valid_audit_log_export(self) -> None:
        """Valid audit log export passes verification."""
        events = [
            {"id": "1", "action": "test1"},
            {"id": "2", "action": "test2"},
        ]
        content_hash = EvidenceExportService.compute_chain_hash(events)

        export_data = {
            "manifest": {
                "export_type": "audit_log",
                "content_hash": content_hash,
            },
            "events": events,
        }

        is_valid = EvidenceExportService.verify_export_integrity(export_data)
        assert is_valid is True

    def test_verify_tampered_audit_log_fails(self) -> None:
        """Tampered audit log export fails verification."""
        original_events = [
            {"id": "1", "action": "test1"},
            {"id": "2", "action": "test2"},
        ]
        content_hash = EvidenceExportService.compute_chain_hash(original_events)

        # Tamper with events after hash was computed
        tampered_events = [
            {"id": "1", "action": "TAMPERED"},
            {"id": "2", "action": "test2"},
        ]

        export_data = {
            "manifest": {
                "export_type": "audit_log",
                "content_hash": content_hash,  # Original hash
            },
            "events": tampered_events,  # Tampered data
        }

        is_valid = EvidenceExportService.verify_export_integrity(export_data)
        assert is_valid is False

    def test_verify_valid_case_pathway_export(self) -> None:
        """Valid case pathway export passes verification."""
        audit_events = [{"id": "1", "action": "triage.created"}]
        responses = [{"id": "r1", "questionnaire_id": "q1"}]
        scores = [{"id": "s1", "type": "phq9", "value": 15}]

        all_records = audit_events + responses + scores
        content_hash = EvidenceExportService.compute_chain_hash(all_records)

        export_data = {
            "manifest": {
                "export_type": "case_pathway",
                "content_hash": content_hash,
            },
            "audit_events": audit_events,
            "questionnaire_responses": responses,
            "scores": scores,
        }

        is_valid = EvidenceExportService.verify_export_integrity(export_data)
        assert is_valid is True

    def test_verify_missing_hash_fails(self) -> None:
        """Export without hash fails verification."""
        export_data = {
            "manifest": {
                "export_type": "audit_log",
                # No content_hash
            },
            "events": [{"id": "1"}],
        }

        is_valid = EvidenceExportService.verify_export_integrity(export_data)
        assert is_valid is False

    def test_verify_unknown_export_type_fails(self) -> None:
        """Unknown export type fails verification."""
        export_data = {
            "manifest": {
                "export_type": "unknown_type",
                "content_hash": "abc123",
            },
        }

        is_valid = EvidenceExportService.verify_export_integrity(export_data)
        assert is_valid is False


class TestAuditLogExport:
    """Tests for audit log export functionality."""

    @pytest.mark.asyncio
    async def test_export_includes_all_events_in_range(self) -> None:
        """Export includes all audit events within date range."""
        mock_session = AsyncMock()

        # Mock audit events
        mock_events = [
            MagicMock(
                id="event-1",
                timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                action="triage.created",
                category="clinical",
                actor_type="user",
                actor_id="user-1",
                entity_type="triage_case",
                entity_id="case-1",
                metadata={"tier": "amber"},
            ),
            MagicMock(
                id="event-2",
                timestamp=datetime(2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc),
                action="triage.scored",
                category="clinical",
                actor_type="system",
                actor_id=None,
                entity_type="triage_case",
                entity_id="case-1",
                metadata={"score": 15},
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_events
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        service = EvidenceExportService(mock_session)

        export_data, export_record = await service.export_audit_log(
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
            exported_by="admin-user",
            export_reason="CQC inspection evidence",
        )

        # Verify all events included
        assert len(export_data["events"]) == 2
        assert export_data["events"][0]["id"] == "event-1"
        assert export_data["events"][1]["id"] == "event-2"

    @pytest.mark.asyncio
    async def test_export_manifest_contains_required_fields(self) -> None:
        """Export manifest contains all required metadata."""
        mock_session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        service = EvidenceExportService(mock_session)

        export_data, _ = await service.export_audit_log(
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
            exported_by="admin-user",
            export_reason="Internal audit",
        )

        manifest = export_data["manifest"]
        assert "export_id" in manifest
        assert "export_type" in manifest
        assert "exported_by" in manifest
        assert "exported_at" in manifest
        assert "export_reason" in manifest
        assert "record_count" in manifest
        assert "content_hash" in manifest
        assert "hash_algorithm" in manifest

        assert manifest["export_type"] == "audit_log"
        assert manifest["exported_by"] == "admin-user"
        assert manifest["hash_algorithm"] == "sha256"


class TestCasePathwayExport:
    """Tests for case pathway export functionality."""

    @pytest.mark.asyncio
    async def test_export_includes_all_case_data(self) -> None:
        """Export includes case, events, responses, and scores."""
        mock_session = AsyncMock()

        # Mock case
        mock_case = MagicMock(
            id="case-123",
            patient_id="patient-456",
            tier="amber",
            status="active",
            pathway="anxiety",
            created_at=datetime(2024, 1, 10, tzinfo=timezone.utc),
        )

        # Mock audit events
        mock_events = [
            MagicMock(
                id="event-1",
                timestamp=datetime(2024, 1, 10, 10, 0, 0, tzinfo=timezone.utc),
                action="triage.case_created",
                category="clinical",
                actor_type="system",
                actor_id=None,
                entity_type="triage_case",
                entity_id="case-123",
                metadata={},
            ),
        ]

        # Mock responses
        mock_responses = [
            MagicMock(
                id="response-1",
                questionnaire_id="phq9",
                submitted_at=datetime(2024, 1, 10, 11, 0, 0, tzinfo=timezone.utc),
                answers={"q1": 2, "q2": 1},
            ),
        ]

        # Mock scores
        mock_scores = [
            MagicMock(
                id="score-1",
                score_type="phq9",
                value=15,
                severity_band="moderate",
                created_at=datetime(2024, 1, 10, 11, 5, 0, tzinfo=timezone.utc),
            ),
        ]

        # Set up execute returns
        mock_session.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=mock_case)),
                MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=mock_events)))),
                MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=mock_responses)))),
                MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=mock_scores)))),
            ]
        )
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        service = EvidenceExportService(mock_session)

        export_data, _ = await service.export_case_pathway(
            triage_case_id="case-123",
            exported_by="admin-user",
            export_reason="Clinical review",
        )

        assert export_data["case"]["id"] == "case-123"
        assert export_data["case"]["tier"] == "amber"
        assert len(export_data["audit_events"]) == 1
        assert len(export_data["questionnaire_responses"]) == 1
        assert len(export_data["scores"]) == 1

    @pytest.mark.asyncio
    async def test_export_raises_for_nonexistent_case(self) -> None:
        """Export raises error if case not found."""
        mock_session = AsyncMock()

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        service = EvidenceExportService(mock_session)

        with pytest.raises(ValueError, match="Case not found"):
            await service.export_case_pathway(
                triage_case_id="nonexistent-case",
                exported_by="admin-user",
                export_reason="Test",
            )

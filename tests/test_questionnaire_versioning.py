"""Tests for questionnaire versioning functionality."""

import pytest
from fastapi.testclient import TestClient


class TestQuestionnaireVersioning:
    """Tests for questionnaire definition versioning."""

    def test_get_active_intake_questionnaire(
        self, client: TestClient, intake_questionnaire, patient_auth_headers
    ) -> None:
        """Test retrieving the active intake questionnaire."""
        response = client.get(
            "/api/v1/intake/questionnaire/active",
            headers=patient_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "intake"
        assert data["version"] == "1.0"
        assert data["is_active"] is True
        assert "schema" in data
        assert "fields" in data["schema"]

    def test_get_old_questionnaire_version_by_version(
        self,
        client: TestClient,
        intake_questionnaire,
        old_intake_questionnaire,
        patient_auth_headers,
    ) -> None:
        """Test that old questionnaire versions remain retrievable."""
        response = client.get(
            "/api/v1/intake/questionnaire/0.9",
            headers=patient_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "intake"
        assert data["version"] == "0.9"
        assert data["is_active"] is False

    def test_get_current_questionnaire_version_by_version(
        self, client: TestClient, intake_questionnaire, patient_auth_headers
    ) -> None:
        """Test retrieving current version by version number."""
        response = client.get(
            "/api/v1/intake/questionnaire/1.0",
            headers=patient_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.0"
        assert data["is_active"] is True

    def test_get_nonexistent_version_returns_404(
        self, client: TestClient, intake_questionnaire, patient_auth_headers
    ) -> None:
        """Test that requesting nonexistent version returns 404."""
        response = client.get(
            "/api/v1/intake/questionnaire/99.99",
            headers=patient_auth_headers,
        )

        assert response.status_code == 404

    def test_questionnaire_includes_schema_hash(
        self, client: TestClient, intake_questionnaire, patient_auth_headers
    ) -> None:
        """Test that questionnaire definition includes schema hash for integrity."""
        response = client.get(
            "/api/v1/intake/questionnaire/active",
            headers=patient_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "schema_hash" in data
        assert len(data["schema_hash"]) == 64  # SHA256 hex length

    def test_multiple_versions_can_coexist(
        self,
        client: TestClient,
        intake_questionnaire,
        old_intake_questionnaire,
        patient_auth_headers,
    ) -> None:
        """Test that multiple versions can exist in the database."""
        # Get active version
        active_response = client.get(
            "/api/v1/intake/questionnaire/active",
            headers=patient_auth_headers,
        )
        assert active_response.status_code == 200
        active_data = active_response.json()

        # Get old version
        old_response = client.get(
            "/api/v1/intake/questionnaire/0.9",
            headers=patient_auth_headers,
        )
        assert old_response.status_code == 200
        old_data = old_response.json()

        # Verify they are different
        assert active_data["id"] != old_data["id"]
        assert active_data["version"] != old_data["version"]
        assert active_data["schema_hash"] != old_data["schema_hash"]


class TestSafetyBanner:
    """Tests for safety banner endpoint."""

    def test_get_safety_banner_public_access(self, client: TestClient) -> None:
        """Test that safety banner is accessible without authentication."""
        response = client.get("/api/v1/intake/safety-banner")

        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert "text" in data
        assert "consent_version" in data

    def test_safety_banner_contains_emergency_info(self, client: TestClient) -> None:
        """Test that safety banner contains emergency contact information."""
        response = client.get("/api/v1/intake/safety-banner")

        assert response.status_code == 200
        data = response.json()
        # Should mention emergency services
        assert "999" in data["text"] or "emergency" in data["text"].lower()

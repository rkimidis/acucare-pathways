"""Tests for consent capture functionality."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consent import Consent


class TestConsentCapture:
    """Tests for consent capture endpoint."""

    def test_capture_consent_success(
        self, client: TestClient, test_patient, patient_auth_headers
    ) -> None:
        """Test successful consent capture with required items."""
        response = client.post(
            "/api/v1/consent/capture",
            json={
                "consent_items": {
                    "data_processing": True,
                    "privacy_policy": True,
                    "communication_email": True,
                    "communication_sms": False,
                },
                "channels": {
                    "email": True,
                    "sms": False,
                },
            },
            headers=patient_auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["patient_id"] == test_patient.id
        assert "consent_version" in data
        assert "agreed_at" in data
        assert data["channels"]["email"] is True
        assert data["channels"]["sms"] is False

    def test_consent_stores_timestamp(
        self, client: TestClient, test_patient, patient_auth_headers
    ) -> None:
        """Test that consent stores accurate timestamp."""
        before = datetime.now(timezone.utc)

        response = client.post(
            "/api/v1/consent/capture",
            json={
                "consent_items": {
                    "data_processing": True,
                    "privacy_policy": True,
                },
                "channels": {},
            },
            headers=patient_auth_headers,
        )

        after = datetime.now(timezone.utc)

        assert response.status_code == 201
        data = response.json()
        agreed_at = datetime.fromisoformat(data["agreed_at"].replace("Z", "+00:00"))
        assert before <= agreed_at <= after

    def test_consent_stores_version(
        self, client: TestClient, test_patient, patient_auth_headers
    ) -> None:
        """Test that consent stores the version number."""
        response = client.post(
            "/api/v1/consent/capture",
            json={
                "consent_items": {
                    "data_processing": True,
                    "privacy_policy": True,
                },
                "channels": {},
            },
            headers=patient_auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["consent_version"] is not None
        assert len(data["consent_version"]) > 0

    def test_consent_fails_without_required_items(
        self, client: TestClient, test_patient, patient_auth_headers
    ) -> None:
        """Test that consent fails when required items not accepted."""
        response = client.post(
            "/api/v1/consent/capture",
            json={
                "consent_items": {
                    "data_processing": False,
                    "privacy_policy": True,
                },
                "channels": {},
            },
            headers=patient_auth_headers,
        )

        assert response.status_code == 422
        data = response.json()
        assert "data_processing" in str(data["detail"])

    def test_consent_fails_missing_privacy_policy(
        self, client: TestClient, test_patient, patient_auth_headers
    ) -> None:
        """Test that consent fails when privacy policy not accepted."""
        response = client.post(
            "/api/v1/consent/capture",
            json={
                "consent_items": {
                    "data_processing": True,
                    "privacy_policy": False,
                },
                "channels": {},
            },
            headers=patient_auth_headers,
        )

        assert response.status_code == 422

    def test_consent_unauthenticated_fails(self, client: TestClient) -> None:
        """Test that consent endpoint requires authentication."""
        response = client.post(
            "/api/v1/consent/capture",
            json={
                "consent_items": {
                    "data_processing": True,
                    "privacy_policy": True,
                },
                "channels": {},
            },
        )

        assert response.status_code == 401


class TestConsentStatus:
    """Tests for consent status endpoint."""

    def test_consent_status_no_consent(
        self, client: TestClient, test_patient, patient_auth_headers
    ) -> None:
        """Test consent status when patient has not consented."""
        response = client.get(
            "/api/v1/consent/status",
            headers=patient_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_consented"] is False
        assert data["needs_reconsent"] is True
        assert "current_version" in data

    def test_consent_status_after_consent(
        self, client: TestClient, test_patient, patient_auth_headers
    ) -> None:
        """Test consent status after patient has consented."""
        # First capture consent
        client.post(
            "/api/v1/consent/capture",
            json={
                "consent_items": {
                    "data_processing": True,
                    "privacy_policy": True,
                },
                "channels": {},
            },
            headers=patient_auth_headers,
        )

        # Check status
        response = client.get(
            "/api/v1/consent/status",
            headers=patient_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_consented"] is True
        assert data["agreed_at"] is not None


class TestConsentHistory:
    """Tests for consent history endpoint."""

    def test_consent_history_empty(
        self, client: TestClient, test_patient, patient_auth_headers
    ) -> None:
        """Test consent history when no consents exist."""
        response = client.get(
            "/api/v1/consent/history",
            headers=patient_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_consent_history_with_records(
        self, client: TestClient, test_patient, patient_auth_headers
    ) -> None:
        """Test consent history returns all consent records."""
        # Capture consent twice
        for _ in range(2):
            client.post(
                "/api/v1/consent/capture",
                json={
                    "consent_items": {
                        "data_processing": True,
                        "privacy_policy": True,
                    },
                    "channels": {},
                },
                headers=patient_auth_headers,
            )

        response = client.get(
            "/api/v1/consent/history",
            headers=patient_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_consent_immutable_records(
        self, client: TestClient, test_patient, patient_auth_headers
    ) -> None:
        """Test that consent records are immutable (new records created)."""
        # Capture first consent
        response1 = client.post(
            "/api/v1/consent/capture",
            json={
                "consent_items": {
                    "data_processing": True,
                    "privacy_policy": True,
                    "communication_email": False,
                },
                "channels": {"email": False},
            },
            headers=patient_auth_headers,
        )

        # Capture second consent with different preferences
        response2 = client.post(
            "/api/v1/consent/capture",
            json={
                "consent_items": {
                    "data_processing": True,
                    "privacy_policy": True,
                    "communication_email": True,
                },
                "channels": {"email": True},
            },
            headers=patient_auth_headers,
        )

        assert response1.status_code == 201
        assert response2.status_code == 201

        data1 = response1.json()
        data2 = response2.json()

        # Different IDs means new record was created
        assert data1["id"] != data2["id"]

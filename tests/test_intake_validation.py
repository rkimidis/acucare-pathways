"""Tests for intake questionnaire validation."""

import pytest
from fastapi.testclient import TestClient


class TestIntakeValidation:
    """Tests for intake response validation against schema."""

    def test_submit_valid_answers(
        self,
        client: TestClient,
        test_patient,
        intake_questionnaire,
        patient_auth_headers,
    ) -> None:
        """Test submitting valid answers passes validation."""
        response = client.post(
            "/api/v1/intake/submit",
            json={
                "answers": {
                    "presenting_complaint": "I have been feeling anxious",
                    "symptom_duration": "1_to_4_weeks",
                    "suicidal_thoughts": False,
                    "previous_treatment": True,
                }
            },
            headers=patient_auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["is_complete"] is True
        assert data["submitted_at"] is not None

    def test_submit_missing_required_field(
        self,
        client: TestClient,
        test_patient,
        intake_questionnaire,
        patient_auth_headers,
    ) -> None:
        """Test that missing required field fails validation."""
        response = client.post(
            "/api/v1/intake/submit",
            json={
                "answers": {
                    # Missing "presenting_complaint" which is required
                    "symptom_duration": "1_to_4_weeks",
                    "suicidal_thoughts": False,
                }
            },
            headers=patient_auth_headers,
        )

        assert response.status_code == 422
        data = response.json()
        assert "presenting_complaint" in str(data["detail"])

    def test_submit_empty_required_field(
        self,
        client: TestClient,
        test_patient,
        intake_questionnaire,
        patient_auth_headers,
    ) -> None:
        """Test that empty required field fails validation."""
        response = client.post(
            "/api/v1/intake/submit",
            json={
                "answers": {
                    "presenting_complaint": "",  # Empty string
                    "symptom_duration": "1_to_4_weeks",
                    "suicidal_thoughts": False,
                }
            },
            headers=patient_auth_headers,
        )

        assert response.status_code == 422

    def test_submit_invalid_select_option(
        self,
        client: TestClient,
        test_patient,
        intake_questionnaire,
        patient_auth_headers,
    ) -> None:
        """Test that invalid select option fails validation."""
        response = client.post(
            "/api/v1/intake/submit",
            json={
                "answers": {
                    "presenting_complaint": "Test complaint",
                    "symptom_duration": "invalid_option",  # Not in options list
                    "suicidal_thoughts": False,
                }
            },
            headers=patient_auth_headers,
        )

        assert response.status_code == 422
        data = response.json()
        assert "symptom_duration" in str(data["detail"])

    def test_submit_optional_field_can_be_omitted(
        self,
        client: TestClient,
        test_patient,
        intake_questionnaire,
        patient_auth_headers,
    ) -> None:
        """Test that optional fields can be omitted."""
        response = client.post(
            "/api/v1/intake/submit",
            json={
                "answers": {
                    "presenting_complaint": "Test complaint",
                    "symptom_duration": "1_to_4_weeks",
                    "suicidal_thoughts": False,
                    # "previous_treatment" is optional, omitting it
                }
            },
            headers=patient_auth_headers,
        )

        assert response.status_code == 201


class TestDraftSaveResume:
    """Tests for draft save and resume functionality."""

    def test_save_draft(
        self,
        client: TestClient,
        test_patient,
        intake_questionnaire,
        patient_auth_headers,
    ) -> None:
        """Test saving a draft response."""
        response = client.post(
            "/api/v1/intake/draft",
            json={
                "answers": {
                    "presenting_complaint": "Partial answer",
                }
            },
            headers=patient_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_complete"] is False
        assert data["answers"]["presenting_complaint"] == "Partial answer"

    def test_resume_draft(
        self,
        client: TestClient,
        test_patient,
        intake_questionnaire,
        patient_auth_headers,
    ) -> None:
        """Test resuming a saved draft."""
        # Save draft first
        client.post(
            "/api/v1/intake/draft",
            json={
                "answers": {
                    "presenting_complaint": "Initial draft",
                }
            },
            headers=patient_auth_headers,
        )

        # Resume draft
        response = client.get(
            "/api/v1/intake/draft",
            headers=patient_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["answers"]["presenting_complaint"] == "Initial draft"

    def test_update_draft(
        self,
        client: TestClient,
        test_patient,
        intake_questionnaire,
        patient_auth_headers,
    ) -> None:
        """Test updating an existing draft."""
        # Save initial draft
        client.post(
            "/api/v1/intake/draft",
            json={
                "answers": {
                    "presenting_complaint": "First draft",
                }
            },
            headers=patient_auth_headers,
        )

        # Update draft
        response = client.post(
            "/api/v1/intake/draft",
            json={
                "answers": {
                    "presenting_complaint": "Updated draft",
                    "symptom_duration": "1_to_4_weeks",
                }
            },
            headers=patient_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["answers"]["presenting_complaint"] == "Updated draft"
        assert data["answers"]["symptom_duration"] == "1_to_4_weeks"

    def test_draft_not_found_returns_null(
        self,
        client: TestClient,
        test_patient,
        intake_questionnaire,
        patient_auth_headers,
    ) -> None:
        """Test that getting draft when none exists returns null."""
        response = client.get(
            "/api/v1/intake/draft",
            headers=patient_auth_headers,
        )

        assert response.status_code == 200
        # Should return null/None when no draft exists
        assert response.json() is None

    def test_complete_from_draft(
        self,
        client: TestClient,
        test_patient,
        intake_questionnaire,
        patient_auth_headers,
    ) -> None:
        """Test completing a questionnaire from a saved draft."""
        # Save partial draft
        client.post(
            "/api/v1/intake/draft",
            json={
                "answers": {
                    "presenting_complaint": "From draft",
                }
            },
            headers=patient_auth_headers,
        )

        # Submit complete answers
        response = client.post(
            "/api/v1/intake/submit",
            json={
                "answers": {
                    "presenting_complaint": "From draft",
                    "symptom_duration": "1_to_4_weeks",
                    "suicidal_thoughts": False,
                }
            },
            headers=patient_auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["is_complete"] is True
        assert data["submitted_at"] is not None


class TestIntakeAuthentication:
    """Tests for intake endpoint authentication."""

    def test_submit_unauthenticated_fails(
        self, client: TestClient, intake_questionnaire
    ) -> None:
        """Test that submit endpoint requires authentication."""
        response = client.post(
            "/api/v1/intake/submit",
            json={"answers": {}},
        )

        assert response.status_code == 401

    def test_draft_unauthenticated_fails(
        self, client: TestClient, intake_questionnaire
    ) -> None:
        """Test that draft endpoints require authentication."""
        response = client.post(
            "/api/v1/intake/draft",
            json={"answers": {}},
        )

        assert response.status_code == 401

        response = client.get("/api/v1/intake/draft")
        assert response.status_code == 401

    def test_staff_cannot_submit_intake(
        self, client: TestClient, intake_questionnaire, auth_headers
    ) -> None:
        """Test that staff tokens cannot access patient intake endpoints."""
        response = client.post(
            "/api/v1/intake/submit",
            json={
                "answers": {
                    "presenting_complaint": "Test",
                    "symptom_duration": "1_to_4_weeks",
                    "suicidal_thoughts": False,
                }
            },
            headers=auth_headers,  # Staff auth headers
        )

        assert response.status_code == 403

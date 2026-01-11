"""Tests for RBAC (Role-Based Access Control)."""

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.models.user import User, UserRole
from app.services.rbac import Permission, RBACService


class TestRBACService:
    """Tests for RBACService class."""

    def test_admin_has_all_permissions(self) -> None:
        """Test that admin role has all permissions."""
        permissions = RBACService.get_permissions(UserRole.ADMIN)

        assert Permission.TRIAGE_READ in permissions
        assert Permission.TRIAGE_WRITE in permissions
        assert Permission.AUDIT_READ in permissions
        assert Permission.USERS_WRITE in permissions
        assert Permission.ADMIN_ALL in permissions

    def test_clinician_has_clinical_permissions(self) -> None:
        """Test that clinician has appropriate permissions."""
        permissions = RBACService.get_permissions(UserRole.CLINICIAN)

        assert Permission.TRIAGE_READ in permissions
        assert Permission.TRIAGE_WRITE in permissions
        assert Permission.CLINICAL_NOTES_READ in permissions
        assert Permission.CLINICAL_NOTES_WRITE in permissions
        # But not admin permissions
        assert Permission.ADMIN_ALL not in permissions
        assert Permission.USERS_WRITE not in permissions

    def test_readonly_has_limited_permissions(self) -> None:
        """Test that readonly role has minimal permissions."""
        permissions = RBACService.get_permissions(UserRole.READONLY)

        assert Permission.TRIAGE_READ in permissions
        assert Permission.PATIENTS_READ in permissions
        # No write permissions
        assert Permission.TRIAGE_WRITE not in permissions
        assert Permission.PATIENTS_WRITE not in permissions

    def test_has_permission_returns_true_for_valid_permission(self) -> None:
        """Test has_permission returns True for valid permission."""
        result = RBACService.has_permission(UserRole.ADMIN, Permission.TRIAGE_READ)
        assert result is True

    def test_has_permission_returns_false_for_invalid_permission(self) -> None:
        """Test has_permission returns False for invalid permission."""
        result = RBACService.has_permission(UserRole.READONLY, Permission.ADMIN_ALL)
        assert result is False

    def test_has_any_permission_with_one_matching(self) -> None:
        """Test has_any_permission with at least one matching."""
        result = RBACService.has_any_permission(
            UserRole.CLINICIAN,
            [Permission.ADMIN_ALL, Permission.TRIAGE_READ],
        )
        assert result is True

    def test_has_any_permission_with_none_matching(self) -> None:
        """Test has_any_permission with no matches."""
        result = RBACService.has_any_permission(
            UserRole.READONLY,
            [Permission.ADMIN_ALL, Permission.USERS_WRITE],
        )
        assert result is False


class TestRBACEndpoints:
    """Tests for RBAC enforcement on API endpoints."""

    def test_readonly_user_cannot_create_triage_case(
        self, client: TestClient, test_patient
    ) -> None:
        """Test that readonly users cannot create triage cases."""
        # Create token for readonly user
        token = create_access_token(
            subject="readonly-user-id",
            additional_claims={
                "role": UserRole.READONLY.value,
                "actor_type": "staff",
                "email": "readonly@test.local",
            },
        )

        response = client.post(
            "/api/v1/triage-cases",
            json={"patient_id": test_patient.id},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    def test_clinician_can_create_triage_case(
        self, client: TestClient, test_patient, auth_headers
    ) -> None:
        """Test that clinicians can create triage cases."""
        response = client.post(
            "/api/v1/triage-cases",
            json={"patient_id": test_patient.id},
            headers=auth_headers,
        )

        assert response.status_code == 201

    def test_admin_can_access_audit_logs(
        self, client: TestClient, admin_auth_headers
    ) -> None:
        """Test that admin can access audit logs."""
        response = client.get(
            "/api/v1/audit/events",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200

    def test_readonly_cannot_access_audit_logs(self, client: TestClient) -> None:
        """Test that readonly users cannot access audit logs."""
        token = create_access_token(
            subject="readonly-user-id",
            additional_claims={
                "role": UserRole.READONLY.value,
                "actor_type": "staff",
                "email": "readonly@test.local",
            },
        )

        response = client.get(
            "/api/v1/audit/events",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    def test_unauthenticated_request_returns_401(self, client: TestClient) -> None:
        """Test that unauthenticated requests return 401."""
        response = client.get("/api/v1/triage-cases")
        assert response.status_code == 401

    def test_patient_token_cannot_access_staff_endpoints(
        self, client: TestClient, patient_auth_headers
    ) -> None:
        """Test that patient tokens cannot access staff endpoints."""
        response = client.get(
            "/api/v1/triage-cases",
            headers=patient_auth_headers,
        )

        assert response.status_code == 403

"""
Authentication API tests — demonstrates testing patterns.

Tests cover: registration, login, email verification, password flows.
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch

from apps.authentication.models import EmailVerificationToken, PasswordResetToken
from apps.users.constants import UserStatus
from tests.factories.factories import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_client(api_client):
    user = UserFactory(status=UserStatus.ACTIVE, is_email_verified=True)
    api_client.force_authenticate(user=user)
    return api_client, user


@pytest.mark.django_db
class TestRegistration:
    """Tests for POST /api/v1/auth/register/"""

    URL = "/api/v1/auth/register/"

    @patch("apps.authentication.services.send_email_verification_task.delay")
    def test_register_success(self, mock_email, api_client):
        payload = {
            "email": "newuser@example.com",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
            "first_name": "John",
            "last_name": "Doe",
        }
        response = api_client.post(self.URL, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["success"] is True
        assert response.data["data"]["email"] == "newuser@example.com"
        mock_email.assert_called_once()

    def test_register_duplicate_email(self, api_client):
        UserFactory(email="existing@example.com")
        payload = {
            "email": "existing@example.com",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        }
        response = api_client.post(self.URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in str(response.data)

    def test_register_password_mismatch(self, api_client):
        payload = {
            "email": "new@example.com",
            "password": "StrongPass123!",
            "confirm_password": "WrongPass!",
        }
        response = api_client.post(self.URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_weak_password(self, api_client):
        payload = {
            "email": "new@example.com",
            "password": "123",
            "confirm_password": "123",
        }
        response = api_client.post(self.URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLogin:
    """Tests for POST /api/v1/auth/login/"""

    URL = "/api/v1/auth/login/"

    def test_login_success(self, api_client):
        user = UserFactory(
            email="login@example.com",
            status=UserStatus.ACTIVE,
            is_email_verified=True,
        )
        user.set_password("TestPass123!")
        user.save()

        response = api_client.post(
            self.URL,
            {"email": "login@example.com", "password": "TestPass123!"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data["data"]
        assert "refresh" in response.data["data"]

    def test_login_wrong_password(self, api_client):
        UserFactory(email="user@example.com", is_email_verified=True)
        response = api_client.post(
            self.URL,
            {"email": "user@example.com", "password": "WrongPass!"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_unverified_email(self, api_client):
        user = UserFactory(email="unverified@example.com", is_email_verified=False)
        user.set_password("TestPass123!")
        user.save()

        response = api_client.post(
            self.URL,
            {"email": "unverified@example.com", "password": "TestPass123!"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["code"] == "email_not_verified"

    def test_login_nonexistent_user(self, api_client):
        response = api_client.post(
            self.URL,
            {"email": "ghost@example.com", "password": "AnyPass123!"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestEmailVerification:
    """Tests for POST /api/v1/auth/verify-email/"""

    URL = "/api/v1/auth/verify-email/"

    @patch("apps.authentication.services.send_welcome_email_task.delay")
    def test_verify_email_success(self, mock_email, api_client):
        user = UserFactory(is_email_verified=False, status=UserStatus.PENDING)
        token = EmailVerificationToken.objects.create(user=user)

        response = api_client.post(self.URL, {"token": token.token}, format="json")
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.is_email_verified is True
        assert user.status == UserStatus.ACTIVE

    def test_verify_invalid_token(self, api_client):
        response = api_client.post(self.URL, {"token": "invalidtoken123"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_verify_expired_token(self, api_client):
        from django.utils import timezone
        user = UserFactory(is_email_verified=False)
        token = EmailVerificationToken.objects.create(user=user)
        token.expires_at = timezone.now() - timezone.timedelta(hours=1)
        token.save()

        response = api_client.post(self.URL, {"token": token.token}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestChangePassword:
    """Tests for POST /api/v1/auth/change-password/"""

    URL = "/api/v1/auth/change-password/"

    def test_change_password_success(self, authenticated_client):
        client, user = authenticated_client
        user.set_password("OldPass123!")
        user.save()

        response = client.post(
            self.URL,
            {
                "old_password": "OldPass123!",
                "new_password": "NewPass456!",
                "confirm_new_password": "NewPass456!",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.check_password("NewPass456!") is True

    def test_change_password_wrong_old(self, authenticated_client):
        client, user = authenticated_client
        response = client.post(
            self.URL,
            {
                "old_password": "WrongOld!",
                "new_password": "NewPass456!",
                "confirm_new_password": "NewPass456!",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_unauthenticated(self, api_client):
        response = api_client.post(self.URL, {}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserProfile:
    """Tests for GET/PATCH /api/v1/users/me/"""

    URL = "/api/v1/users/me/"

    def test_get_profile(self, authenticated_client):
        client, user = authenticated_client
        response = client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["email"] == user.email

    def test_update_profile(self, authenticated_client):
        client, user = authenticated_client
        response = client.patch(
            self.URL,
            {"first_name": "UpdatedName"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["first_name"] == "UpdatedName"

    def test_profile_unauthenticated(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

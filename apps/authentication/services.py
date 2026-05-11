"""
Authentication service — all auth business logic.

Implements:
- Registration with email verification
- Login with brute-force protection
- Email verification
- Forgot/Reset password
- Change password
- Logout with token blacklisting
- OAuth-ready architecture hook
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.models import EmailVerificationToken, PasswordResetToken
from apps.users.constants import UserStatus
from apps.users.models import User
from apps.users.repository import UserRepository
from celery_tasks.email_tasks import (
    send_email_verification_task,
    send_password_reset_task,
    send_welcome_email_task,
)
from core.exceptions.exceptions import (
    AccountDisabledException,
    AuthenticationException,
    EmailVerificationException,
    NotFoundException,
    ValidationException,
)

logger = logging.getLogger(__name__)


class AuthService:
    """Business logic for authentication flows."""

    def __init__(self) -> None:
        self.user_repo = UserRepository()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    @transaction.atomic
    def register(self, validated_data: dict) -> User:
        """
        Register a new customer account.

        Steps:
        1. Create user (status=PENDING, email_verified=False)
        2. Create email verification token
        3. Queue verification email via Celery
        """
        user = self.user_repo.create(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            phone=validated_data.get("phone", ""),
        )

        token = EmailVerificationToken.objects.create(user=user)
        verification_url = f"{settings.EMAIL_VERIFICATION_URL}?token={token.token}"

        # Queue async email
        send_email_verification_task.delay(
            user_id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            verification_url=verification_url,
        )

        logger.info("New user registered: %s", user.email)
        return user

    # ------------------------------------------------------------------
    # Email Verification
    # ------------------------------------------------------------------

    @transaction.atomic
    def verify_email(self, token_str: str) -> User:
        """Verify user email with one-time token."""
        try:
            token = EmailVerificationToken.objects.select_related("user").get(token=token_str)
        except EmailVerificationToken.DoesNotExist:
            raise ValidationException("Invalid verification token.")

        if not token.is_valid:
            raise ValidationException(
                "This token has already been used or has expired. Please request a new one."
            )

        user = token.user
        token.consume()

        # Activate user
        self.user_repo.update(user, is_email_verified=True, status=UserStatus.ACTIVE)

        # Queue welcome email
        send_welcome_email_task.delay(user_id=str(user.id), email=user.email, full_name=user.full_name)

        logger.info("Email verified for user: %s", user.email)
        return user

    def resend_verification_email(self, email: str) -> None:
        """Resend email verification link."""
        user = self.user_repo.get_by_email(email)
        if not user:
            # Return silently to prevent email enumeration
            return
        if user.is_email_verified:
            raise ValidationException("Email is already verified.")

        # Invalidate old tokens
        EmailVerificationToken.objects.filter(user=user, is_used=False).update(is_used=True)

        token = EmailVerificationToken.objects.create(user=user)
        verification_url = f"{settings.EMAIL_VERIFICATION_URL}?token={token.token}"

        send_email_verification_task.delay(
            user_id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            verification_url=verification_url,
        )

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    def login(self, email: str, password: str, ip_address: str | None = None) -> dict:
        """
        Authenticate user and return JWT token pair.

        Handles:
        - Account locked check
        - Password verification
        - Failed login counter
        - Email verification check
        - Account status check
        """
        user = self.user_repo.get_by_email(email)

        if not user:
            raise AuthenticationException("Invalid email or password.")

        # Brute force lock check
        if user.is_account_locked:
            raise AuthenticationException(
                "Your account has been temporarily locked due to too many failed login attempts. "
                "Please try again in 30 minutes."
            )

        # Password check
        if not user.check_password(password):
            user.record_failed_login()
            raise AuthenticationException("Invalid email or password.")

        # Email verification check
        if not user.is_email_verified:
            raise EmailVerificationException()

        # Account status check
        if user.status != UserStatus.ACTIVE:
            raise AccountDisabledException()

        if not user.is_active:
            raise AccountDisabledException()

        # Successful login
        user.record_login(ip_address=ip_address)
        tokens = self._generate_tokens(user)

        logger.info("User logged in: %s from %s", user.email, ip_address)
        return {**tokens, "user": user}

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    def logout(self, refresh_token: str) -> None:
        """Blacklist the refresh token to invalidate the session."""
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info("Token blacklisted.")
        except Exception as exc:
            logger.warning("Logout token blacklist failed: %s", exc)
            raise ValidationException("Invalid or expired refresh token.")

    # ------------------------------------------------------------------
    # Password Reset
    # ------------------------------------------------------------------

    def forgot_password(self, email: str) -> None:
        """
        Initiate password reset flow.
        Always returns success to prevent email enumeration.
        """
        user = self.user_repo.get_by_email(email)
        if not user or not user.is_email_verified:
            return  # Silent — don't reveal if email exists

        # Invalidate old tokens
        PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)

        token = PasswordResetToken.objects.create(user=user)
        reset_url = f"{settings.PASSWORD_RESET_URL}?token={token.token}"

        send_password_reset_task.delay(
            user_id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            reset_url=reset_url,
        )
        logger.info("Password reset initiated for: %s", email)

    @transaction.atomic
    def reset_password(self, token_str: str, new_password: str) -> None:
        """Reset password using one-time token."""
        try:
            token = PasswordResetToken.objects.select_related("user").get(token=token_str)
        except PasswordResetToken.DoesNotExist:
            raise ValidationException("Invalid reset token.")

        if not token.is_valid:
            raise ValidationException("This token has expired or already been used.")

        user = token.user
        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])
        token.consume()

        # Invalidate all other reset tokens
        PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)

        logger.info("Password reset successful for: %s", user.email)

    def change_password(self, user: User, old_password: str, new_password: str) -> None:
        """Change password while authenticated."""
        if not user.check_password(old_password):
            raise ValidationException("Current password is incorrect.")
        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])
        logger.info("Password changed for: %s", user.email)

    # ------------------------------------------------------------------
    # OAuth (future-ready hook)
    # ------------------------------------------------------------------

    def oauth_authenticate(self, provider: str, oauth_data: dict) -> dict:
        """
        Authenticate via OAuth provider (Google, etc.).

        Called from the OAuth callback view once the provider
        returns user info. Creates account if first login.
        """
        email = oauth_data.get("email")
        oauth_uid = oauth_data.get("sub") or oauth_data.get("id")

        if not email or not oauth_uid:
            raise AuthenticationException("Invalid OAuth response.")

        # Check if user exists by OAuth UID
        user = self.user_repo.get_by_oauth(provider, oauth_uid)

        if not user:
            # Try to link to existing account by email
            user = self.user_repo.get_by_email(email)

            if user:
                # Link OAuth to existing account
                self.user_repo.update(user, oauth_provider=provider, oauth_uid=oauth_uid)
            else:
                # Create new account via OAuth
                user = self.user_repo.create(
                    email=email,
                    first_name=oauth_data.get("given_name", ""),
                    last_name=oauth_data.get("family_name", ""),
                    avatar=oauth_data.get("picture"),
                    oauth_provider=provider,
                    oauth_uid=oauth_uid,
                    is_email_verified=True,
                    status=UserStatus.ACTIVE,
                )

        tokens = self._generate_tokens(user)
        return {**tokens, "user": user}

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_tokens(user: User) -> dict:
        """Generate JWT access + refresh token pair."""
        refresh = RefreshToken.for_user(user)
        # Add custom claims
        refresh["email"] = user.email
        refresh["role"] = user.role
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

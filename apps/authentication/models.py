"""Authentication support models — tokens for email verification and password reset."""
import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


def default_expiry_verification():
    return timezone.now() + timedelta(hours=settings.EMAIL_VERIFICATION_EXPIRY_HOURS)


def default_expiry_reset():
    return timezone.now() + timedelta(hours=settings.PASSWORD_RESET_EXPIRY_HOURS)


class EmailVerificationToken(models.Model):
    """One-time token for verifying a user's email address."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verification_tokens",
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        default=secrets.token_urlsafe,
        db_index=True,
    )
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField(default=default_expiry_verification)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "email_verification_tokens"
        indexes = [models.Index(fields=["token", "is_used"])]

    def __str__(self) -> str:
        return f"VerifyToken({self.user.email})"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @property
    def is_valid(self) -> bool:
        return not self.is_used and not self.is_expired

    def consume(self) -> None:
        self.is_used = True
        self.save(update_fields=["is_used"])


class PasswordResetToken(models.Model):
    """One-time token for resetting a user's password."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        default=secrets.token_urlsafe,
        db_index=True,
    )
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField(default=default_expiry_reset)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "password_reset_tokens"
        indexes = [models.Index(fields=["token", "is_used"])]

    def __str__(self) -> str:
        return f"ResetToken({self.user.email})"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @property
    def is_valid(self) -> bool:
        return not self.is_used and not self.is_expired

    def consume(self) -> None:
        self.is_used = True
        self.save(update_fields=["is_used"])

"""
Custom User model with email-based authentication and RBAC.

Extends AbstractBaseUser for full control, compatible with future
OAuth providers (Google, etc.) via the oauth_provider / oauth_uid fields.
"""
import uuid

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone

from apps.users.constants import UserRole, UserStatus


class UserManager(BaseUserManager):
    """Custom manager for email-based auth."""

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields,
    ) -> "User":
        if not email:
            raise ValueError("Email address is required.")
        email = self.normalize_email(email)
        extra_fields.setdefault("role", UserRole.CUSTOMER)
        extra_fields.setdefault("status", UserStatus.PENDING)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_staff(self, email: str, role: str, password: str | None = None, **extra_fields) -> "User":
        extra_fields.setdefault("status", UserStatus.ACTIVE)
        extra_fields["role"] = role
        extra_fields["is_staff"] = True
        return self.create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str, **extra_fields) -> "User":
        extra_fields["role"] = UserRole.SUPER_ADMIN
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        extra_fields["status"] = UserStatus.ACTIVE
        extra_fields["is_email_verified"] = True
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Enterprise custom user model.

    - Email-based authentication (no username)
    - Role-based access control via `role` field
    - OAuth-ready: oauth_provider + oauth_uid fields
    - Soft-delete compatible via status field
    - Full audit trail: created_at, updated_at, last_login
    """

    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Identity
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    avatar = models.URLField(blank=True, null=True)

    # RBAC
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CUSTOMER,
        db_index=True,
    )

    # Account state
    status = models.CharField(
        max_length=20,
        choices=UserStatus.choices,
        default=UserStatus.PENDING,
        db_index=True,
    )
    is_email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # OAuth (future-ready — Google, etc.)
    oauth_provider = models.CharField(max_length=50, blank=True, null=True)
    oauth_uid = models.CharField(max_length=255, blank=True, null=True)

    # Address (JSON — flexible)
    default_address = models.JSONField(null=True, blank=True)

    # Metadata
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=["email", "status"]),
            models.Index(fields=["role", "status"]),
            models.Index(fields=["oauth_provider", "oauth_uid"]),
        ]

    def __str__(self) -> str:
        return f"{self.email} ({self.role})"

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.email

    @property
    def is_super_admin(self) -> bool:
        return self.role == UserRole.SUPER_ADMIN

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def is_manager(self) -> bool:
        return self.role == UserRole.MANAGER

    @property
    def is_customer(self) -> bool:
        return self.role == UserRole.CUSTOMER

    @property
    def is_account_locked(self) -> bool:
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False

    @property
    def is_verified_and_active(self) -> bool:
        return self.is_email_verified and self.status == UserStatus.ACTIVE

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------

    def record_login(self, ip_address: str | None = None) -> None:
        """Record a successful login."""
        self.failed_login_attempts = 0
        self.locked_until = None
        if ip_address:
            self.last_login_ip = ip_address
        self.save(update_fields=["failed_login_attempts", "locked_until", "last_login_ip", "updated_at"])

    def record_failed_login(self) -> None:
        """Increment failed login counter and lock if threshold exceeded."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.locked_until = timezone.now() + timezone.timedelta(minutes=30)
        self.save(update_fields=["failed_login_attempts", "locked_until", "updated_at"])

    def unlock_account(self) -> None:
        """Manually unlock a locked account."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(update_fields=["failed_login_attempts", "locked_until", "updated_at"])

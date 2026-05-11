"""
User repository — all User ORM queries live here.

Implements the Repository pattern: views/services never write raw ORM queries.
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from django.db.models import Q, QuerySet

from apps.users.models import User

logger = logging.getLogger(__name__)


class UserRepository:
    """
    Encapsulates all database operations for the User model.

    - No business logic here — only queries
    - All methods return typed QuerySet or model instances
    - Use select_related / prefetch_related to avoid N+1
    """

    @staticmethod
    def get_by_id(user_id: UUID | str) -> Optional[User]:
        """Fetch a single user by UUID. Returns None if not found."""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_by_email(email: str) -> Optional[User]:
        """Fetch user by email (case-insensitive)."""
        try:
            return User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_by_oauth(provider: str, uid: str) -> Optional[User]:
        """Fetch user by OAuth provider and UID."""
        try:
            return User.objects.get(oauth_provider=provider, oauth_uid=uid)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_all() -> QuerySet[User]:
        """All users — for admin listing."""
        return User.objects.all().order_by("-created_at")

    @staticmethod
    def get_active_users() -> QuerySet[User]:
        """Active, verified users only."""
        return User.objects.filter(is_active=True, is_email_verified=True)

    @staticmethod
    def get_by_role(role: str) -> QuerySet[User]:
        """Users filtered by role."""
        return User.objects.filter(role=role, is_active=True)

    @staticmethod
    def search(query: str) -> QuerySet[User]:
        """Full-text search across name/email/phone."""
        return User.objects.filter(
            Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(phone__icontains=query)
        )

    @staticmethod
    def create(
        email: str,
        password: str | None = None,
        **fields,
    ) -> User:
        """Create a new user."""
        return User.objects.create_user(email=email, password=password, **fields)

    @staticmethod
    def update(user: User, **fields) -> User:
        """Update specific fields on a user instance."""
        update_fields = []
        for field, value in fields.items():
            setattr(user, field, value)
            update_fields.append(field)
        update_fields.append("updated_at")
        user.save(update_fields=update_fields)
        return user

    @staticmethod
    def exists_by_email(email: str) -> bool:
        """Check if a user with this email already exists."""
        return User.objects.filter(email__iexact=email).exists()

    @staticmethod
    def get_locked_accounts() -> QuerySet[User]:
        """Users with active account locks."""
        from django.utils import timezone

        return User.objects.filter(locked_until__gt=timezone.now())

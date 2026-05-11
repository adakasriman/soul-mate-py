"""
User service layer — all user business logic lives here.

Views call services, services call repositories.
No ORM queries directly in views or serializers.
"""
from __future__ import annotations

import logging
from uuid import UUID

from django.db import transaction

from apps.users.models import User
from apps.users.repository import UserRepository
from core.exceptions.exceptions import (
    ConflictException,
    NotFoundException,
    PermissionDeniedException,
)

logger = logging.getLogger(__name__)


class UserService:
    """Business logic for user management operations."""

    def __init__(self) -> None:
        self.repo = UserRepository()

    def get_user_or_404(self, user_id: UUID | str) -> User:
        user = self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException(f"User {user_id} not found.")
        return user

    def update_profile(self, user: User, validated_data: dict) -> User:
        """Update user profile fields."""
        return self.repo.update(user, **validated_data)

    def update_role(self, actor: User, target_user_id: UUID | str, new_role: str) -> User:
        """
        Admin-only: update another user's role.
        Enforces role hierarchy — cannot promote beyond actor's role.
        """
        from apps.users.constants import ROLE_HIERARCHY, UserRole

        target_user = self.get_user_or_404(target_user_id)

        # Cannot modify own role
        if str(target_user.id) == str(actor.id):
            raise PermissionDeniedException("You cannot modify your own role.")

        # Role hierarchy enforcement
        actor_rank = ROLE_HIERARCHY.index(actor.role) if actor.role in ROLE_HIERARCHY else -1
        new_role_rank = ROLE_HIERARCHY.index(new_role) if new_role in ROLE_HIERARCHY else -1

        if new_role_rank >= actor_rank and actor.role != UserRole.SUPER_ADMIN:
            raise PermissionDeniedException("You cannot assign a role equal to or higher than your own.")

        logger.info(
            "Role change: actor=%s, target=%s, old=%s, new=%s",
            actor.id,
            target_user.id,
            target_user.role,
            new_role,
        )
        return self.repo.update(target_user, role=new_role)

    def update_status(self, actor: User, target_user_id: UUID | str, new_status: str) -> User:
        """Admin-only: activate, suspend, or deactivate a user."""
        target_user = self.get_user_or_404(target_user_id)

        if str(target_user.id) == str(actor.id):
            raise PermissionDeniedException("You cannot modify your own account status.")

        logger.info(
            "Status change: actor=%s, target=%s, old=%s, new=%s",
            actor.id,
            target_user.id,
            target_user.status,
            new_status,
        )
        return self.repo.update(target_user, status=new_status)

    @transaction.atomic
    def soft_delete_user(self, actor: User, target_user_id: UUID | str) -> None:
        """Super Admin: permanently deactivate a user account."""
        target_user = self.get_user_or_404(target_user_id)

        if str(target_user.id) == str(actor.id):
            raise PermissionDeniedException("You cannot delete your own account via this API.")

        self.repo.update(target_user, is_active=False)
        logger.info("User deactivated: actor=%s, target=%s", actor.id, target_user.id)

    def list_users(
        self,
        role: str | None = None,
        search: str | None = None,
    ):
        """Admin-only: list users with optional role filter and search."""
        if search:
            qs = self.repo.search(search)
        else:
            qs = self.repo.get_all()

        if role:
            qs = qs.filter(role=role)

        return qs

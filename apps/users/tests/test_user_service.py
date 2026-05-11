"""Unit tests for RBAC permissions and User service."""
import pytest
from unittest.mock import MagicMock
from rest_framework.test import APIRequestFactory

from apps.users.constants import UserRole
from apps.users.services import UserService
from core.exceptions.exceptions import NotFoundException, PermissionDeniedException
from core.permissions.roles import (
    IsAdminOrAbove,
    IsManagerOrAbove,
    IsSuperAdmin,
    HasRole,
)
from tests.factories.factories import (
    AdminFactory,
    ManagerFactory,
    SuperAdminFactory,
    UserFactory,
)


@pytest.mark.django_db
class TestRBACPermissions:
    """Test permission classes enforce role hierarchy correctly."""

    factory = APIRequestFactory()

    def _make_request(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_super_admin_passes_all(self):
        user = SuperAdminFactory()
        request = self._make_request(user)
        assert IsSuperAdmin().has_permission(request, None) is True
        assert IsAdminOrAbove().has_permission(request, None) is True
        assert IsManagerOrAbove().has_permission(request, None) is True

    def test_admin_blocked_from_super_admin_endpoint(self):
        user = AdminFactory()
        request = self._make_request(user)
        assert IsSuperAdmin().has_permission(request, None) is False
        assert IsAdminOrAbove().has_permission(request, None) is True

    def test_manager_blocked_from_admin_endpoint(self):
        user = ManagerFactory()
        request = self._make_request(user)
        assert IsAdminOrAbove().has_permission(request, None) is False
        assert IsManagerOrAbove().has_permission(request, None) is True

    def test_customer_blocked_from_staff_endpoints(self):
        user = UserFactory(role=UserRole.CUSTOMER)
        request = self._make_request(user)
        assert IsManagerOrAbove().has_permission(request, None) is False
        assert IsAdminOrAbove().has_permission(request, None) is False
        assert IsSuperAdmin().has_permission(request, None) is False

    def test_has_role_factory(self):
        user = ManagerFactory()
        request = self._make_request(user)
        perm = HasRole(UserRole.MANAGER, UserRole.ADMIN)()
        assert perm.has_permission(request, None) is True

    def test_has_role_blocks_wrong_role(self):
        user = UserFactory(role=UserRole.CUSTOMER)
        request = self._make_request(user)
        perm = HasRole(UserRole.ADMIN)()
        assert perm.has_permission(request, None) is False


@pytest.mark.django_db
class TestUserService:
    """Unit tests for UserService business logic."""

    service = UserService()

    def test_get_user_or_404_raises_not_found(self):
        import uuid
        with pytest.raises(NotFoundException):
            self.service.get_user_or_404(uuid.uuid4())

    def test_get_user_or_404_success(self):
        user = UserFactory()
        result = self.service.get_user_or_404(user.id)
        assert result.id == user.id

    def test_update_role_cannot_self_promote(self):
        admin = AdminFactory()
        with pytest.raises(PermissionDeniedException):
            self.service.update_role(actor=admin, target_user_id=admin.id, new_role=UserRole.MANAGER)

    def test_update_role_hierarchy_enforcement(self):
        """Admin cannot promote someone to Super Admin."""
        admin = AdminFactory()
        target = UserFactory(role=UserRole.MANAGER)
        with pytest.raises(PermissionDeniedException):
            self.service.update_role(
                actor=admin, target_user_id=target.id, new_role=UserRole.SUPER_ADMIN
            )

    def test_update_role_success(self):
        super_admin = SuperAdminFactory()
        target = UserFactory(role=UserRole.CUSTOMER)
        updated = self.service.update_role(
            actor=super_admin, target_user_id=target.id, new_role=UserRole.MANAGER
        )
        assert updated.role == UserRole.MANAGER

    def test_update_profile(self):
        user = UserFactory(first_name="Old")
        updated = self.service.update_profile(user, {"first_name": "New"})
        assert updated.first_name == "New"

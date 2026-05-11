"""
Reusable Role-Based Access Control (RBAC) permission classes.

Usage in views:
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    permission_classes = [IsAuthenticated, IsAdminOrAbove]
    permission_classes = [IsAuthenticated, HasRole("manager", "admin")]
"""
from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.users.constants import UserRole


class RolePermission(BasePermission):
    """Base class for role-based permission checks."""

    allowed_roles: tuple[str, ...] = ()

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in self.allowed_roles


class IsSuperAdmin(RolePermission):
    """Only Super Admins."""

    allowed_roles = (UserRole.SUPER_ADMIN,)
    message = "Only Super Admins can perform this action."


class IsAdmin(RolePermission):
    """Only Admins."""

    allowed_roles = (UserRole.ADMIN,)
    message = "Only Admins can perform this action."


class IsAdminOrAbove(RolePermission):
    """Super Admin or Admin."""

    allowed_roles = (UserRole.SUPER_ADMIN, UserRole.ADMIN)
    message = "Admin access required."


class IsManagerOrAbove(RolePermission):
    """Super Admin, Admin, or Manager."""

    allowed_roles = (UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER)
    message = "Manager or higher access required."


class IsSalesPerson(RolePermission):
    """Only Sales Persons."""

    allowed_roles = (UserRole.SALES_PERSON,)
    message = "Sales Person access required."


class IsSalesOrAbove(RolePermission):
    """Super Admin, Admin, Manager, or Sales Person."""

    allowed_roles = (
        UserRole.SUPER_ADMIN,
        UserRole.ADMIN,
        UserRole.MANAGER,
        UserRole.SALES_PERSON,
    )
    message = "Sales or higher access required."


class IsAccounts(RolePermission):
    """Only Accounts role."""

    allowed_roles = (UserRole.ACCOUNTS,)
    message = "Accounts access required."


class IsAccountsOrAbove(RolePermission):
    """Accounts, Manager, Admin, or Super Admin."""

    allowed_roles = (
        UserRole.SUPER_ADMIN,
        UserRole.ADMIN,
        UserRole.MANAGER,
        UserRole.ACCOUNTS,
    )
    message = "Accounts or higher access required."


class IsCustomer(RolePermission):
    """Only Customers."""

    allowed_roles = (UserRole.CUSTOMER,)
    message = "Customer access required."


class IsStaffMember(RolePermission):
    """Any internal staff (not Customer)."""

    allowed_roles = (
        UserRole.SUPER_ADMIN,
        UserRole.ADMIN,
        UserRole.MANAGER,
        UserRole.SALES_PERSON,
        UserRole.ACCOUNTS,
    )
    message = "Staff access required."


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission: owner of the object OR admin+.

    The view must set `owner_field` attribute to specify the field
    that holds the owner FK (defaults to 'user').
    """

    message = "You do not have permission to access this resource."

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        # Admins and above always pass
        if request.user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN):
            return True

        # Check ownership
        owner_field = getattr(view, "owner_field", "user")
        owner = getattr(obj, owner_field, None)
        if owner is None:
            return False

        owner_id = owner.id if hasattr(owner, "id") else owner
        return str(owner_id) == str(request.user.id)


def HasRole(*roles: str) -> type[BasePermission]:
    """
    Factory that creates a permission class for the given roles.

    Usage:
        permission_classes = [IsAuthenticated, HasRole("manager", "admin")]
    """

    class DynamicRolePermission(BasePermission):
        allowed_roles = roles
        message = f"Required roles: {', '.join(roles)}."

        def has_permission(self, request: Request, view: APIView) -> bool:
            if not request.user or not request.user.is_authenticated:
                return False
            return request.user.role in self.allowed_roles

    return DynamicRolePermission

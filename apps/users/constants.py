"""User-related constants and enumerations."""
from django.db import models


class UserRole(models.TextChoices):
    """Available user roles in the system."""

    SUPER_ADMIN = "super_admin", "Super Admin"
    ADMIN = "admin", "Admin"
    MANAGER = "manager", "Manager"
    SALES_PERSON = "sales_person", "Sales Person"
    ACCOUNTS = "accounts", "Accounts"
    CUSTOMER = "customer", "Customer"


class UserStatus(models.TextChoices):
    """User account status."""

    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"
    SUSPENDED = "suspended", "Suspended"
    PENDING = "pending", "Pending Verification"


# Role hierarchy — higher index = more privilege
ROLE_HIERARCHY = [
    UserRole.CUSTOMER,
    UserRole.ACCOUNTS,
    UserRole.SALES_PERSON,
    UserRole.MANAGER,
    UserRole.ADMIN,
    UserRole.SUPER_ADMIN,
]

STAFF_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN,
    UserRole.MANAGER,
    UserRole.SALES_PERSON,
    UserRole.ACCOUNTS,
]

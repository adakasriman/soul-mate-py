"""User serializers — input validation and output representation."""
from rest_framework import serializers

from apps.users.constants import UserRole, UserStatus
from apps.users.models import User


class UserPublicSerializer(serializers.ModelSerializer):
    """Minimal user info — safe to expose to customers."""

    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "full_name", "avatar", "role"]
        read_only_fields = fields


class UserProfileSerializer(serializers.ModelSerializer):
    """Full user profile — for the user themselves."""

    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "avatar",
            "role",
            "status",
            "is_email_verified",
            "default_address",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "email", "role", "status", "is_email_verified", "created_at", "updated_at"]


class UserAdminSerializer(serializers.ModelSerializer):
    """Full user info — for admin management."""

    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "avatar",
            "role",
            "status",
            "is_email_verified",
            "is_active",
            "is_staff",
            "oauth_provider",
            "default_address",
            "last_login",
            "last_login_ip",
            "failed_login_attempts",
            "locked_until",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "email", "oauth_provider", "created_at", "updated_at"]


class UpdateProfileSerializer(serializers.ModelSerializer):
    """Update user profile fields."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone", "default_address"]

    def validate_phone(self, value: str) -> str:
        if value and not value.replace("+", "").replace("-", "").replace(" ", "").isdigit():
            raise serializers.ValidationError("Invalid phone number format.")
        return value


class UpdateUserRoleSerializer(serializers.Serializer):
    """Admin-only: update a user's role."""

    role = serializers.ChoiceField(choices=UserRole.choices)

    def validate_role(self, value: str) -> str:
        # Prevent promoting to super_admin via API
        request = self.context.get("request")
        if value == UserRole.SUPER_ADMIN and (
            not request or request.user.role != UserRole.SUPER_ADMIN
        ):
            raise serializers.ValidationError("Only Super Admins can assign Super Admin role.")
        return value


class UpdateUserStatusSerializer(serializers.Serializer):
    """Admin-only: update a user's status."""

    status = serializers.ChoiceField(choices=UserStatus.choices)

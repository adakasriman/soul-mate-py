"""Authentication serializers — all auth-related input/output schemas."""
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.users.models import User


class RegisterSerializer(serializers.Serializer):
    """User registration input."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150, required=False, default="")
    last_name = serializers.CharField(max_length=150, required=False, default="")
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate(self, attrs: dict) -> dict:
        if attrs["password"] != attrs.pop("confirm_password"):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        try:
            validate_password(attrs["password"])
        except Exception as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs


class LoginSerializer(serializers.Serializer):
    """Login credentials."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class TokenResponseSerializer(serializers.Serializer):
    """JWT token pair response."""

    access = serializers.CharField()
    refresh = serializers.CharField()
    user = serializers.SerializerMethodField()

    def get_user(self, obj: dict) -> dict:
        from apps.users.serializers import UserProfileSerializer
        return UserProfileSerializer(obj["user"]).data


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT with additional claims (role, email)."""

    @classmethod
    def get_token(cls, user: User):
        token = super().get_token(user)
        token["email"] = user.email
        token["role"] = user.role
        token["full_name"] = user.full_name
        return token


class VerifyEmailSerializer(serializers.Serializer):
    """Email verification token."""

    token = serializers.CharField()


class ForgotPasswordSerializer(serializers.Serializer):
    """Forgot password — request email."""

    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    """Reset password with token."""

    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs: dict) -> dict:
        if attrs["password"] != attrs.pop("confirm_password"):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        try:
            validate_password(attrs["password"])
        except Exception as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """Change password while logged in."""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_new_password = serializers.CharField(write_only=True)

    def validate(self, attrs: dict) -> dict:
        if attrs["new_password"] != attrs.pop("confirm_new_password"):
            raise serializers.ValidationError({"confirm_new_password": "New passwords do not match."})
        try:
            validate_password(attrs["new_password"])
        except Exception as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)})
        return attrs


class RefreshTokenSerializer(serializers.Serializer):
    """Refresh token input."""

    refresh = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    """Logout — blacklist refresh token."""

    refresh = serializers.CharField()

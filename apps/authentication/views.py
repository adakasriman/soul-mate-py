"""Authentication views — thin controllers delegating to AuthService."""
import logging

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.authentication.serializers import (
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    RefreshTokenSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    VerifyEmailSerializer,
)
from apps.authentication.services import AuthService
from apps.users.serializers import UserProfileSerializer
from core.response import created_response, success_response

logger = logging.getLogger(__name__)
auth_service = AuthService()


class AuthRateThrottle(AnonRateThrottle):
    scope = "auth"


class PasswordResetThrottle(AnonRateThrottle):
    scope = "password_reset"


class RegisterView(APIView):
    """POST /auth/register/ — create a new customer account."""

    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = auth_service.register(serializer.validated_data)
        return created_response(
            data=UserProfileSerializer(user).data,
            message="Registration successful. Please check your email to verify your account.",
        )


class LoginView(APIView):
    """POST /auth/login/ — authenticate and return JWT tokens."""

    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip_address = self._get_client_ip(request)
        result = auth_service.login(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            ip_address=ip_address,
        )
        return success_response(
            data={
                "access": result["access"],
                "refresh": result["refresh"],
                "user": UserProfileSerializer(result["user"]).data,
            },
            message="Login successful.",
        )

    @staticmethod
    def _get_client_ip(request: Request) -> str | None:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


class LogoutView(APIView):
    """POST /auth/logout/ — blacklist the refresh token."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        auth_service.logout(serializer.validated_data["refresh"])
        return success_response(message="Logged out successfully.")


class VerifyEmailView(APIView):
    """POST /auth/verify-email/ — verify user email with token."""

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = auth_service.verify_email(serializer.validated_data["token"])
        return success_response(
            data=UserProfileSerializer(user).data,
            message="Email verified successfully. You can now log in.",
        )


class ResendVerificationView(APIView):
    """POST /auth/resend-verification/ — resend verification email."""

    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request: Request) -> Response:
        email = request.data.get("email", "")
        auth_service.resend_verification_email(email)
        return success_response(
            message="If your email is registered and unverified, you will receive a new verification link."
        )


class ForgotPasswordView(APIView):
    """POST /auth/forgot-password/ — send password reset email."""

    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetThrottle]

    def post(self, request: Request) -> Response:
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        auth_service.forgot_password(serializer.validated_data["email"])
        return success_response(
            message="If your email is registered, you will receive a password reset link shortly."
        )


class ResetPasswordView(APIView):
    """POST /auth/reset-password/ — reset password with token."""

    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetThrottle]

    def post(self, request: Request) -> Response:
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        auth_service.reset_password(
            token_str=serializer.validated_data["token"],
            new_password=serializer.validated_data["password"],
        )
        return success_response(message="Password reset successfully. You can now log in.")


class ChangePasswordView(APIView):
    """POST /auth/change-password/ — change password while logged in."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        auth_service.change_password(
            user=request.user,
            old_password=serializer.validated_data["old_password"],
            new_password=serializer.validated_data["new_password"],
        )
        return success_response(message="Password changed successfully.")

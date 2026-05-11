"""
Centralized custom exception hierarchy.

All business logic should raise these exceptions instead of DRF exceptions
directly. The custom_exception_handler maps them to proper HTTP responses.
"""
from rest_framework import status


class AppException(Exception):
    """Base application exception."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_code: str = "error"
    default_detail: str = "An unexpected error occurred."

    def __init__(self, detail: str | None = None, code: str | None = None) -> None:
        self.detail = detail or self.default_detail
        self.code = code or self.default_code

    def __str__(self) -> str:
        return str(self.detail)


class ValidationException(AppException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "validation_error"
    default_detail = "Validation failed."


class AuthenticationException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "authentication_error"
    default_detail = "Authentication credentials are invalid."


class PermissionDeniedException(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "permission_denied"
    default_detail = "You do not have permission to perform this action."


class NotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = "not_found"
    default_detail = "The requested resource was not found."


class ConflictException(AppException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "conflict"
    default_detail = "A conflict occurred."


class ServiceUnavailableException(AppException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = "service_unavailable"
    default_detail = "Service is temporarily unavailable."


class InsufficientStockException(ValidationException):
    default_code = "insufficient_stock"
    default_detail = "Insufficient stock available."


class PaymentException(AppException):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_code = "payment_error"
    default_detail = "Payment processing failed."


class EmailVerificationException(AuthenticationException):
    default_code = "email_not_verified"
    default_detail = "Please verify your email before proceeding."


class AccountDisabledException(AuthenticationException):
    default_code = "account_disabled"
    default_detail = "Your account has been disabled. Contact support."

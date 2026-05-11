"""Custom DRF exception handler — unified error response format."""
import logging
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

from core.exceptions.exceptions import AppException
from core.response import ErrorResponse

logger = logging.getLogger(__name__)


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """
    Custom exception handler that returns a consistent error response.

    Response format:
    {
        "success": false,
        "message": "Human-readable error",
        "code": "machine_readable_code",
        "errors": {...}  // field-level errors if applicable
    }
    """
    # Convert Django ValidationError to DRF ValidationError
    if isinstance(exc, DjangoValidationError):
        exc = ValidationError(detail=exc.message_dict if hasattr(exc, "message_dict") else exc.messages)

    # Convert Http404 to DRF 404
    if isinstance(exc, Http404):
        exc = APIException(detail="Not found.")
        exc.status_code = status.HTTP_404_NOT_FOUND  # type: ignore[attr-defined]

    # Handle our custom AppExceptions
    if isinstance(exc, AppException):
        logger.warning(
            "AppException: %s | code=%s | detail=%s",
            type(exc).__name__,
            exc.code,
            exc.detail,
        )
        return Response(
            ErrorResponse(message=exc.detail, code=exc.code).to_dict(),
            status=exc.status_code,
        )

    # Handle DRF built-in exceptions
    response = exception_handler(exc, context)

    if response is not None:
        errors: dict | list | None = None
        message = "An error occurred."
        code = "error"

        if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
            code = "authentication_error"
            message = str(exc.detail) if hasattr(exc, "detail") else "Authentication required."
        elif isinstance(exc, PermissionDenied):
            code = "permission_denied"
            message = "You do not have permission to perform this action."
        elif isinstance(exc, ValidationError):
            code = "validation_error"
            message = "Validation failed."
            errors = response.data
        elif hasattr(exc, "detail"):
            message = str(exc.detail)
            code = getattr(exc, "default_code", "error")

        response.data = ErrorResponse(message=message, code=code, errors=errors).to_dict()
        return response

    # Unexpected exceptions
    logger.exception("Unhandled exception: %s", exc)
    return Response(
        ErrorResponse(
            message="An unexpected server error occurred.",
            code="server_error",
        ).to_dict(),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

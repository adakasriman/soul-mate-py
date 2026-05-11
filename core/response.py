"""
Standardized API response objects.

All views should return responses via these helpers to ensure
a consistent JSON structure across the entire API.
"""
from dataclasses import dataclass, field
from typing import Any

from rest_framework import status
from rest_framework.response import Response


@dataclass
class SuccessResponse:
    """Successful response wrapper."""

    data: Any = None
    message: str = "Success"
    meta: dict | None = None

    def to_dict(self) -> dict:
        payload: dict[str, Any] = {
            "success": True,
            "message": self.message,
            "data": self.data,
        }
        if self.meta:
            payload["meta"] = self.meta
        return payload


@dataclass
class ErrorResponse:
    """Error response wrapper."""

    message: str = "An error occurred."
    code: str = "error"
    errors: dict | list | None = None

    def to_dict(self) -> dict:
        payload: dict[str, Any] = {
            "success": False,
            "message": self.message,
            "code": self.code,
        }
        if self.errors is not None:
            payload["errors"] = self.errors
        return payload


def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = status.HTTP_200_OK,
    meta: dict | None = None,
) -> Response:
    """Return a standardized success Response."""
    return Response(
        SuccessResponse(data=data, message=message, meta=meta).to_dict(),
        status=status_code,
    )


def created_response(data: Any = None, message: str = "Created successfully.") -> Response:
    return success_response(data=data, message=message, status_code=status.HTTP_201_CREATED)


def no_content_response(message: str = "Deleted successfully.") -> Response:
    return Response(
        SuccessResponse(message=message).to_dict(),
        status=status.HTTP_200_OK,
    )

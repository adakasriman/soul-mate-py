"""Audit middleware — captures created_by / updated_by from request user."""
import threading
from typing import Callable

from django.http import HttpRequest, HttpResponse

_request_local = threading.local()


def get_current_user():
    """Return the current request's user (used in models/services)."""
    return getattr(_request_local, "user", None)


class AuditMiddleware:
    """
    Stores the current authenticated user in thread-local storage
    so models/services can access it without passing it explicitly.
    """

    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = getattr(request, "user", None)
        _request_local.user = user if (user and user.is_authenticated) else None
        response = self.get_response(request)
        _request_local.user = None
        return response

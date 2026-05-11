"""Request ID middleware — adds X-Request-ID to every response."""
import uuid
from typing import Callable

import structlog
from django.http import HttpRequest, HttpResponse

logger = structlog.get_logger(__name__)


class RequestIDMiddleware:
    """Attaches a unique request ID to each request and response."""

    HEADER = "X-Request-ID"

    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.headers.get(self.HEADER) or str(uuid.uuid4())
        request.request_id = request_id  # type: ignore[attr-defined]

        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = self.get_response(request)
        response[self.HEADER] = request_id
        return response

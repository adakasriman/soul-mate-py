"""Health check endpoint."""
import logging

from django.db import connection
from django.core.cache import cache
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """
    GET /health/ — Returns system health status.
    Used by load balancers, Kubernetes liveness probes, etc.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request: Request) -> Response:
        health = {
            "status": "healthy",
            "database": self._check_database(),
            "cache": self._check_cache(),
        }
        all_healthy = all(v == "ok" for v in health.values() if v != "healthy")
        status_code = 200 if all_healthy else 503
        return Response(health, status=status_code)

    @staticmethod
    def _check_database() -> str:
        try:
            connection.ensure_connection()
            return "ok"
        except Exception as exc:
            logger.error("DB health check failed: %s", exc)
            return "error"

    @staticmethod
    def _check_cache() -> str:
        try:
            cache.set("health_check", "ok", timeout=5)
            return "ok" if cache.get("health_check") == "ok" else "error"
        except Exception as exc:
            logger.error("Cache health check failed: %s", exc)
            return "error"

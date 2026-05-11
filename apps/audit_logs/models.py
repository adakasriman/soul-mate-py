"""Audit logs model — records every significant action."""
import uuid

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """
    Immutable audit log entry.

    Records: who did what, to which resource, when, and from where.
    Never soft-deleted — always retained.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Actor
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    actor_email = models.EmailField(blank=True)  # snapshot in case user is deleted

    # Action
    action = models.CharField(max_length=100, db_index=True)
    resource_type = models.CharField(max_length=100, db_index=True)
    resource_id = models.CharField(max_length=100, blank=True, db_index=True)

    # Context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    request_id = models.CharField(max_length=50, blank=True)
    endpoint = models.CharField(max_length=500, blank=True)
    method = models.CharField(max_length=10, blank=True)

    # Diff
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    extra_data = models.JSONField(null=True, blank=True)

    # Status
    is_successful = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["actor", "action"]),
            models.Index(fields=["resource_type", "resource_id"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["action", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"AuditLog({self.action} on {self.resource_type}/{self.resource_id} by {self.actor_email})"

    @classmethod
    def log(
        cls,
        action: str,
        resource_type: str,
        resource_id: str = "",
        actor=None,
        ip_address: str | None = None,
        old_value: dict | None = None,
        new_value: dict | None = None,
        extra_data: dict | None = None,
        is_successful: bool = True,
        error_message: str = "",
        request=None,
    ) -> "AuditLog":
        """Convenience factory method for creating audit log entries."""
        if request and actor is None:
            actor = getattr(request, "user", None)

        return cls.objects.create(
            actor=actor if actor and actor.is_authenticated else None,
            actor_email=actor.email if actor and actor.is_authenticated else "",
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            ip_address=ip_address or (
                request.META.get("REMOTE_ADDR") if request else None
            ),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500] if request else "",
            request_id=getattr(request, "request_id", "") if request else "",
            endpoint=request.path if request else "",
            method=request.method if request else "",
            old_value=old_value,
            new_value=new_value,
            extra_data=extra_data,
            is_successful=is_successful,
            error_message=error_message,
        )

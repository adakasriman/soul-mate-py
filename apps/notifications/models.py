"""Notifications app models."""
from django.conf import settings
from django.db import models

from core.models import BaseModel


class Notification(BaseModel):
    """In-app notification for a user."""

    class Type(models.TextChoices):
        ORDER_PLACED = "order_placed", "Order Placed"
        ORDER_CONFIRMED = "order_confirmed", "Order Confirmed"
        ORDER_SHIPPED = "order_shipped", "Order Shipped"
        ORDER_DELIVERED = "order_delivered", "Order Delivered"
        ORDER_CANCELLED = "order_cancelled", "Order Cancelled"
        PAYMENT_SUCCESS = "payment_success", "Payment Success"
        PAYMENT_FAILED = "payment_failed", "Payment Failed"
        LOW_STOCK = "low_stock", "Low Stock Alert"
        PROMOTION = "promotion", "Promotion"
        SYSTEM = "system", "System"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        db_index=True,
    )
    notification_type = models.CharField(max_length=30, choices=Type.choices, db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    # Link to related resource
    resource_type = models.CharField(max_length=50, blank=True)
    resource_id = models.CharField(max_length=100, blank=True)
    extra_data = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["recipient", "notification_type"]),
        ]

    def __str__(self) -> str:
        return f"Notification({self.recipient.email}): {self.title}"

    def mark_read(self) -> None:
        from django.utils import timezone
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=["is_read", "read_at"])

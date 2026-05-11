"""Payments app models."""
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from core.models import BaseModel


class Payment(BaseModel):
    """Payment record linked to an order."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"
        CANCELLED = "cancelled", "Cancelled"

    class Method(models.TextChoices):
        CARD = "card", "Credit/Debit Card"
        UPI = "upi", "UPI"
        NET_BANKING = "net_banking", "Net Banking"
        WALLET = "wallet", "Wallet"
        COD = "cod", "Cash on Delivery"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"

    order = models.ForeignKey(
        "orders.Order", on_delete=models.PROTECT, related_name="payments"
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payments",
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default="INR")

    method = models.CharField(max_length=20, choices=Method.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    # Gateway fields
    gateway = models.CharField(max_length=50, blank=True)  # razorpay, stripe, etc.
    gateway_payment_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    gateway_order_id = models.CharField(max_length=255, blank=True, null=True)
    gateway_signature = models.CharField(max_length=512, blank=True, null=True)
    gateway_response = models.JSONField(null=True, blank=True)

    # Refund
    refunded_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    refund_reason = models.TextField(blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)

    failure_reason = models.TextField(blank=True)

    class Meta:
        db_table = "payments"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "status"]),
            models.Index(fields=["gateway_payment_id"]),
            models.Index(fields=["customer", "status"]),
        ]

    def __str__(self) -> str:
        return f"Payment({self.order.order_number}) ₹{self.amount} [{self.status}]"

    @property
    def is_refundable(self) -> bool:
        return (
            self.status == self.Status.COMPLETED
            and self.refunded_amount < self.amount
        )

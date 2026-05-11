"""Invoices app models."""
from django.conf import settings
from django.db import models
from core.models import BaseModel


class Invoice(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        PAID = "paid", "Paid"
        OVERDUE = "overdue", "Overdue"
        CANCELLED = "cancelled", "Cancelled"

    invoice_number = models.CharField(max_length=30, unique=True, db_index=True, editable=False)
    order = models.OneToOneField("orders.Order", on_delete=models.PROTECT, related_name="invoice")
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="invoices")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    billing_address = models.JSONField()
    customer_email = models.EmailField()
    customer_name = models.CharField(max_length=300)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    issue_date = models.DateField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    pdf_url = models.URLField(blank=True, null=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "invoices"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invoice {self.invoice_number}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            import random, string
            from django.utils import timezone
            year = timezone.now().year
            suffix = "".join(random.choices(string.digits, k=6))
            self.invoice_number = f"INV-{year}-{suffix}"
        super().save(*args, **kwargs)

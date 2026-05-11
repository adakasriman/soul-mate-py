"""Inventory app models — stock tracking."""
from django.core.validators import MinValueValidator
from django.db import models

from core.models import BaseModel


class Inventory(BaseModel):
    """
    Tracks stock levels per product/variant.

    Each product (or variant) has exactly one Inventory record.
    """

    product = models.OneToOneField(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="inventory",
        null=True,
        blank=True,
    )
    variant = models.OneToOneField(
        "products.ProductVariant",
        on_delete=models.CASCADE,
        related_name="inventory",
        null=True,
        blank=True,
    )

    quantity_on_hand = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    quantity_reserved = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    low_stock_threshold = models.IntegerField(default=10)
    reorder_quantity = models.IntegerField(default=50)
    warehouse_location = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "inventory"
        verbose_name_plural = "inventories"
        constraints = [
            models.CheckConstraint(
                check=models.Q(product__isnull=False) | models.Q(variant__isnull=False),
                name="inventory_product_or_variant_required",
            )
        ]

    def __str__(self) -> str:
        target = self.product or self.variant
        return f"Inventory({target}): {self.available_quantity}"

    @property
    def available_quantity(self) -> int:
        return max(0, self.quantity_on_hand - self.quantity_reserved)

    @property
    def is_low_stock(self) -> bool:
        return self.available_quantity <= self.low_stock_threshold

    @property
    def is_out_of_stock(self) -> bool:
        return self.available_quantity == 0

    def reserve(self, quantity: int) -> bool:
        """Reserve stock for an order. Returns False if insufficient."""
        if self.available_quantity < quantity:
            return False
        self.quantity_reserved += quantity
        self.save(update_fields=["quantity_reserved", "updated_at"])
        return True

    def release_reservation(self, quantity: int) -> None:
        """Release previously reserved stock."""
        self.quantity_reserved = max(0, self.quantity_reserved - quantity)
        self.save(update_fields=["quantity_reserved", "updated_at"])

    def deduct(self, quantity: int) -> None:
        """Deduct stock after order fulfillment."""
        self.quantity_on_hand = max(0, self.quantity_on_hand - quantity)
        self.quantity_reserved = max(0, self.quantity_reserved - quantity)
        self.save(update_fields=["quantity_on_hand", "quantity_reserved", "updated_at"])


class StockMovement(BaseModel):
    """Audit log of every inventory change."""

    class MovementType(models.TextChoices):
        PURCHASE = "purchase", "Purchase"
        SALE = "sale", "Sale"
        RETURN = "return", "Return"
        ADJUSTMENT = "adjustment", "Adjustment"
        RESERVED = "reserved", "Reserved"
        RELEASED = "released", "Released"
        DAMAGED = "damaged", "Damaged"

    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name="movements")
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity_change = models.IntegerField()  # positive = in, negative = out
    quantity_before = models.IntegerField()
    quantity_after = models.IntegerField()
    reference = models.CharField(max_length=255, blank=True)  # order ID, PO number etc.
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "stock_movements"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["inventory", "movement_type"]),
            models.Index(fields=["created_at"]),
        ]

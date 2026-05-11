"""Cart app models."""
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from core.models import BaseModel


class Cart(BaseModel):
    """Shopping cart — one per user (session or authenticated)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
        null=True,
        blank=True,
    )
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    coupon_code = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "carts"
        indexes = [models.Index(fields=["user"]), models.Index(fields=["session_key"])]

    def __str__(self) -> str:
        owner = self.user.email if self.user else f"Session:{self.session_key}"
        return f"Cart({owner})"

    @property
    def total_items(self) -> int:
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        return sum(item.line_total for item in self.items.select_related("product"))


class CartItem(BaseModel):
    """Item in a shopping cart."""

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "products.Product", on_delete=models.CASCADE, related_name="cart_items"
    )
    variant = models.ForeignKey(
        "products.ProductVariant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cart_items",
    )
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        db_table = "cart_items"
        unique_together = [("cart", "product", "variant")]
        indexes = [models.Index(fields=["cart", "product"])]

    def __str__(self) -> str:
        return f"{self.quantity}x {self.product.name}"

    @property
    def unit_price(self):
        if self.variant and self.variant.price is not None:
            return self.variant.price
        return self.product.price

    @property
    def line_total(self):
        return self.unit_price * self.quantity

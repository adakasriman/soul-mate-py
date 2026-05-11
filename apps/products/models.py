"""Products app models."""
from django.core.validators import MinValueValidator
from django.db import models

from core.models import SoftDeleteModel


class Category(SoftDeleteModel):
    """Product category with optional parent (tree structure)."""

    name = models.CharField(max_length=255, unique=True, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True)
    image = models.URLField(blank=True, null=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "categories"
        verbose_name_plural = "categories"
        ordering = ["sort_order", "name"]
        indexes = [models.Index(fields=["slug", "is_active"])]

    def __str__(self) -> str:
        return self.name


class Product(SoftDeleteModel):
    """Core product model."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        OUT_OF_STOCK = "out_of_stock", "Out of Stock"
        DISCONTINUED = "discontinued", "Discontinued"

    name = models.CharField(max_length=500, db_index=True)
    slug = models.SlugField(max_length=500, unique=True, db_index=True)
    description = models.TextField(blank=True)
    short_description = models.CharField(max_length=500, blank=True)
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    barcode = models.CharField(max_length=100, blank=True, null=True, db_index=True)

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        db_index=True,
    )

    # Pricing
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    compare_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    cost_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    is_digital = models.BooleanField(default=False)

    # Physical attributes
    weight = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    dimensions = models.JSONField(null=True, blank=True)  # {length, width, height}

    # SEO
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=500, blank=True)

    # Tags (stored as array)
    tags = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "products"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "category"]),
            models.Index(fields=["slug", "status"]),
            models.Index(fields=["is_featured", "status"]),
            models.Index(fields=["sku"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.sku})"

    @property
    def is_on_sale(self) -> bool:
        return self.compare_price is not None and self.compare_price > self.price

    @property
    def discount_percentage(self) -> float | None:
        if self.compare_price and self.compare_price > 0:
            return round(((self.compare_price - self.price) / self.compare_price) * 100, 1)
        return None


class ProductImage(models.Model):
    """Product images (multiple per product)."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    url = models.URLField()
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "product_images"
        ordering = ["sort_order", "created_at"]

    def __str__(self) -> str:
        return f"Image for {self.product.name}"


class ProductVariant(SoftDeleteModel):
    """Product variants (size, color, etc.)."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    name = models.CharField(max_length=255)  # e.g. "Red - Large"
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    attributes = models.JSONField(default=dict)  # {color: "red", size: "L"}
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "product_variants"
        indexes = [models.Index(fields=["product", "is_active"])]

    def __str__(self) -> str:
        return f"{self.product.name} — {self.name}"

    @property
    def effective_price(self):
        return self.price if self.price is not None else self.product.price

"""Product serializers — with N+1-safe patterns."""
from rest_framework import serializers

from apps.products.models import Category, Product, ProductImage, ProductVariant


class CategorySerializer(serializers.ModelSerializer):
    """Category output serializer."""

    children_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id", "name", "slug", "description", "image",
            "parent", "is_active", "sort_order", "children_count",
        ]

    def get_children_count(self, obj: Category) -> int:
        # Uses prefetched data — no extra query
        return obj.children.count() if hasattr(obj, "_prefetched_objects_cache") else 0


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "url", "alt_text", "is_primary", "sort_order"]


class ProductVariantSerializer(serializers.ModelSerializer):
    effective_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = ProductVariant
        fields = ["id", "name", "sku", "attributes", "price", "effective_price", "is_active"]


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""

    primary_image = serializers.SerializerMethodField()
    category_name = serializers.CharField(source="category.name", read_only=True)
    is_on_sale = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.FloatField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "sku", "price", "compare_price",
            "is_on_sale", "discount_percentage", "status", "is_featured",
            "category_name", "primary_image",
        ]

    def get_primary_image(self, obj: Product) -> str | None:
        # Relies on prefetch_related("images") in the view's queryset
        images = obj.images.all()
        primary = next((img for img in images if img.is_primary), None)
        if primary:
            return primary.url
        return images[0].url if images else None


class ProductDetailSerializer(serializers.ModelSerializer):
    """Full product detail serializer."""

    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    is_on_sale = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.FloatField(read_only=True)
    inventory_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "description", "short_description",
            "sku", "barcode", "category", "price", "compare_price",
            "cost_price", "tax_rate", "status", "is_featured", "is_digital",
            "weight", "dimensions", "tags", "meta_title", "meta_description",
            "is_on_sale", "discount_percentage", "images", "variants",
            "inventory_count", "created_at", "updated_at",
        ]

    def get_inventory_count(self, obj: Product) -> int | None:
        if hasattr(obj, "inventory"):
            return obj.inventory.available_quantity
        return None


class ProductWriteSerializer(serializers.ModelSerializer):
    """Create/update product serializer."""

    class Meta:
        model = Product
        fields = [
            "name", "slug", "description", "short_description",
            "sku", "barcode", "category", "price", "compare_price",
            "cost_price", "tax_rate", "status", "is_featured", "is_digital",
            "weight", "dimensions", "tags", "meta_title", "meta_description",
        ]

    def validate_sku(self, value: str) -> str:
        qs = Product.objects.filter(sku__iexact=value)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists():
            raise serializers.ValidationError("A product with this SKU already exists.")
        return value.upper()

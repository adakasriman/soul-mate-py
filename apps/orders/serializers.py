"""Order serializers."""
from rest_framework import serializers

from apps.orders.models import Order, OrderItem
from apps.users.serializers import UserPublicSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "id", "product", "variant", "product_name", "sku",
            "variant_name", "quantity", "unit_price", "tax_rate",
            "discount_amount", "total_price",
        ]


class OrderListSerializer(serializers.ModelSerializer):
    customer_email = serializers.EmailField(source="customer.email", read_only=True)
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "order_number", "customer_email", "customer_name",
            "status", "payment_status", "total_amount", "item_count",
            "created_at",
        ]

    def get_item_count(self, obj: Order) -> int:
        return obj.items.count()


class OrderDetailSerializer(serializers.ModelSerializer):
    customer = UserPublicSerializer(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "order_number", "customer", "status", "payment_status",
            "subtotal", "tax_amount", "shipping_amount", "discount_amount",
            "total_amount", "shipping_address", "billing_address",
            "notes", "coupon_code", "items",
            "confirmed_at", "shipped_at", "delivered_at", "cancelled_at",
            "created_at", "updated_at",
        ]


class CreateOrderSerializer(serializers.Serializer):
    """Input serializer for placing an order from cart."""

    shipping_address = serializers.JSONField()
    billing_address = serializers.JSONField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    coupon_code = serializers.CharField(required=False, allow_blank=True, default="")
    payment_method = serializers.ChoiceField(choices=["card", "upi", "net_banking", "wallet", "cod"])

    def validate_shipping_address(self, value: dict) -> dict:
        required_fields = ["full_name", "address_line1", "city", "state", "postal_code", "country"]
        missing = [f for f in required_fields if not value.get(f)]
        if missing:
            raise serializers.ValidationError(f"Missing required address fields: {', '.join(missing)}")
        return value


class UpdateOrderStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)
    notes = serializers.CharField(required=False, allow_blank=True)

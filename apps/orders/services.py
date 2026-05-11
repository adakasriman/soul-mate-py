"""
Order service — handles the complete order placement lifecycle.

Flow:
  Cart → Validate → Reserve Stock → Create Order → Queue Notifications
"""
from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.cart.models import Cart
from apps.inventory.models import Inventory, StockMovement
from apps.orders.models import Order, OrderItem
from apps.users.models import User
from celery_tasks.email_tasks import send_order_confirmation_task
from celery_tasks.notification_tasks import create_notification_task
from core.exceptions.exceptions import (
    InsufficientStockException,
    NotFoundException,
    ValidationException,
)

logger = logging.getLogger(__name__)


class OrderService:
    """Business logic for order management."""

    @transaction.atomic
    def place_order(self, customer: User, validated_data: dict) -> Order:
        """
        Place an order from the customer's cart.

        Steps:
        1. Load cart + items (optimized query)
        2. Validate cart is not empty
        3. Check + reserve stock atomically
        4. Compute pricing
        5. Create Order + OrderItems
        6. Clear cart
        7. Queue email + notification
        """
        cart = self._get_cart_or_raise(customer)
        cart_items = list(
            cart.items.select_related(
                "product__inventory",
                "variant__inventory",
            ).all()
        )

        if not cart_items:
            raise ValidationException("Cannot place an order with an empty cart.")

        # === Reserve stock atomically ===
        self._reserve_stock(cart_items)

        # === Compute totals ===
        subtotal = Decimal("0.00")
        tax_total = Decimal("0.00")

        order_items_data = []
        for item in cart_items:
            product = item.product
            variant = item.variant
            unit_price = item.unit_price
            tax_rate = product.tax_rate or Decimal("0.00")
            tax_amount = (unit_price * item.quantity * tax_rate / 100).quantize(Decimal("0.01"))
            line_total = (unit_price * item.quantity).quantize(Decimal("0.01"))

            subtotal += line_total
            tax_total += tax_amount

            order_items_data.append({
                "product": product,
                "variant": variant,
                "product_name": product.name,
                "sku": variant.sku if variant else product.sku,
                "variant_name": variant.name if variant else "",
                "quantity": item.quantity,
                "unit_price": unit_price,
                "tax_rate": tax_rate,
                "discount_amount": Decimal("0.00"),
                "total_price": line_total,
            })

        shipping_amount = Decimal("0.00")  # TODO: integrate shipping calculator
        discount_amount = Decimal("0.00")  # TODO: integrate coupon engine
        total_amount = subtotal + tax_total + shipping_amount - discount_amount

        # === Create Order ===
        order = Order.objects.create(
            customer=customer,
            status=Order.Status.PENDING,
            subtotal=subtotal,
            tax_amount=tax_total,
            shipping_amount=shipping_amount,
            discount_amount=discount_amount,
            total_amount=total_amount,
            shipping_address=validated_data["shipping_address"],
            billing_address=validated_data.get("billing_address") or validated_data["shipping_address"],
            notes=validated_data.get("notes", ""),
            coupon_code=validated_data.get("coupon_code", ""),
            created_by=customer,
        )

        # === Create Order Items ===
        OrderItem.objects.bulk_create([
            OrderItem(order=order, created_by=customer, **item_data)
            for item_data in order_items_data
        ])

        # === Clear Cart ===
        cart.items.all().delete()

        # === Async tasks ===
        send_order_confirmation_task.delay(
            order_id=str(order.id),
            email=customer.email,
            full_name=customer.full_name,
        )
        create_notification_task.delay(
            recipient_id=str(customer.id),
            notification_type="order_placed",
            title="Order Placed Successfully!",
            message=f"Your order {order.order_number} has been placed. We'll confirm it shortly.",
            resource_type="order",
            resource_id=str(order.id),
        )

        logger.info("Order placed: %s by customer %s", order.order_number, customer.email)
        return order

    @transaction.atomic
    def update_order_status(
        self,
        order_id: UUID | str,
        new_status: str,
        actor: User,
        notes: str = "",
    ) -> Order:
        """Update order status with audit trail."""
        try:
            order = Order.objects.select_for_update().get(id=order_id)
        except Order.DoesNotExist:
            raise NotFoundException(f"Order {order_id} not found.")

        old_status = order.status
        order.status = new_status
        order.updated_by = actor

        # Set timestamp fields
        now = timezone.now()
        if new_status == Order.Status.CONFIRMED:
            order.confirmed_at = now
        elif new_status == Order.Status.SHIPPED:
            order.shipped_at = now
        elif new_status == Order.Status.DELIVERED:
            order.delivered_at = now
            self._deduct_stock_on_delivery(order)
        elif new_status == Order.Status.CANCELLED:
            order.cancelled_at = now
            self._release_stock_on_cancel(order)

        if notes:
            order.internal_notes = f"{order.internal_notes}\n[{now}] {notes}".strip()

        order.save()

        # Notify customer
        status_messages = {
            Order.Status.CONFIRMED: ("Order Confirmed", "Your order has been confirmed!"),
            Order.Status.SHIPPED: ("Order Shipped", "Your order is on the way!"),
            Order.Status.DELIVERED: ("Order Delivered", "Your order has been delivered. Enjoy!"),
            Order.Status.CANCELLED: ("Order Cancelled", "Your order has been cancelled."),
        }
        if new_status in status_messages:
            title, message = status_messages[new_status]
            create_notification_task.delay(
                recipient_id=str(order.customer_id),
                notification_type=f"order_{new_status}",
                title=title,
                message=f"{message} Order: {order.order_number}",
                resource_type="order",
                resource_id=str(order.id),
            )

        logger.info(
            "Order status: %s → %s (actor=%s)", old_status, new_status, actor.email
        )
        return order

    def get_customer_orders(self, customer: User):
        """Paginated order list for a customer."""
        return (
            Order.objects
            .filter(customer=customer)
            .prefetch_related("items__product")
            .order_by("-created_at")
        )

    def get_order_detail(self, order_id: UUID | str, customer: User | None = None) -> Order:
        """Get full order detail, optionally scoped to a customer."""
        try:
            qs = Order.objects.select_related("customer").prefetch_related(
                "items__product", "items__variant", "payments"
            )
            if customer:
                order = qs.get(id=order_id, customer=customer)
            else:
                order = qs.get(id=order_id)
            return order
        except Order.DoesNotExist:
            raise NotFoundException(f"Order {order_id} not found.")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_cart_or_raise(customer: User) -> Cart:
        try:
            return Cart.objects.get(user=customer)
        except Cart.DoesNotExist:
            raise NotFoundException("Cart not found.")

    @staticmethod
    def _reserve_stock(cart_items: list) -> None:
        """Reserve stock for all items. Rolls back if any item fails."""
        for item in cart_items:
            inventory: Inventory | None = (
                item.variant.inventory if item.variant and hasattr(item.variant, "inventory")
                else getattr(item.product, "inventory", None)
            )
            if not inventory:
                raise ValidationException(
                    f"Inventory not configured for '{item.product.name}'."
                )
            if not inventory.reserve(item.quantity):
                raise InsufficientStockException(
                    f"Only {inventory.available_quantity} units available for '{item.product.name}'."
                )

    @staticmethod
    def _release_stock_on_cancel(order: Order) -> None:
        """Release reserved stock when an order is cancelled."""
        for item in order.items.select_related("product__inventory", "variant__inventory"):
            inventory = (
                item.variant.inventory
                if item.variant and hasattr(item.variant, "inventory")
                else getattr(item.product, "inventory", None)
            )
            if inventory:
                inventory.release_reservation(item.quantity)

    @staticmethod
    def _deduct_stock_on_delivery(order: Order) -> None:
        """Permanently deduct stock when order is delivered."""
        for item in order.items.select_related("product__inventory", "variant__inventory"):
            inventory = (
                item.variant.inventory
                if item.variant and hasattr(item.variant, "inventory")
                else getattr(item.product, "inventory", None)
            )
            if inventory:
                before = inventory.quantity_on_hand
                inventory.deduct(item.quantity)
                StockMovement.objects.create(
                    inventory=inventory,
                    movement_type=StockMovement.MovementType.SALE,
                    quantity_change=-item.quantity,
                    quantity_before=before,
                    quantity_after=inventory.quantity_on_hand,
                    reference=order.order_number,
                )

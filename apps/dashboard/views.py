"""Dashboard API — aggregated metrics for admin dashboards."""
import logging
from datetime import timedelta

from django.core.cache import cache
from django.db.models import Count, DecimalField, Q, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order
from apps.users.models import User
from core.permissions.roles import IsManagerOrAbove
from core.response import success_response

logger = logging.getLogger(__name__)

DASHBOARD_CACHE_TTL = 300  # 5 minutes


class DashboardSummaryView(APIView):
    """
    GET /dashboard/summary/ — key business metrics.

    Cached for 5 minutes to reduce DB load on busy dashboards.
    """

    permission_classes = [IsAuthenticated, IsManagerOrAbove]

    def get(self, request: Request) -> Response:
        cache_key = f"dashboard:summary:{request.user.role}"
        cached = cache.get(cache_key)
        if cached:
            return success_response(data=cached)

        today = timezone.now().date()
        this_month_start = today.replace(day=1)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)

        # Orders
        orders_qs = Order.objects.all()
        total_orders = orders_qs.count()
        orders_today = orders_qs.filter(created_at__date=today).count()
        orders_this_month = orders_qs.filter(created_at__date__gte=this_month_start).count()

        # Revenue
        revenue_today = (
            orders_qs.filter(created_at__date=today, payment_status="paid")
            .aggregate(total=Coalesce(Sum("total_amount"), 0, output_field=DecimalField()))["total"]
        )
        revenue_this_month = (
            orders_qs.filter(created_at__date__gte=this_month_start, payment_status="paid")
            .aggregate(total=Coalesce(Sum("total_amount"), 0, output_field=DecimalField()))["total"]
        )
        revenue_last_month = (
            orders_qs.filter(
                created_at__date__gte=last_month_start,
                created_at__date__lt=this_month_start,
                payment_status="paid",
            )
            .aggregate(total=Coalesce(Sum("total_amount"), 0, output_field=DecimalField()))["total"]
        )

        # Users
        total_customers = User.objects.filter(role="customer").count()
        new_customers_this_month = User.objects.filter(
            role="customer", created_at__date__gte=this_month_start
        ).count()

        # Order status distribution
        status_distribution = (
            orders_qs.values("status").annotate(count=Count("id")).order_by("status")
        )

        # Revenue trend (last 30 days)
        thirty_days_ago = today - timedelta(days=30)
        revenue_trend = list(
            orders_qs.filter(
                created_at__date__gte=thirty_days_ago,
                payment_status="paid",
            )
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(revenue=Coalesce(Sum("total_amount"), 0, output_field=DecimalField()))
            .order_by("date")
        )

        data = {
            "orders": {
                "total": total_orders,
                "today": orders_today,
                "this_month": orders_this_month,
            },
            "revenue": {
                "today": float(revenue_today),
                "this_month": float(revenue_this_month),
                "last_month": float(revenue_last_month),
                "growth_percentage": self._calculate_growth(revenue_this_month, revenue_last_month),
            },
            "customers": {
                "total": total_customers,
                "new_this_month": new_customers_this_month,
            },
            "order_status_distribution": list(status_distribution),
            "revenue_trend": [
                {"date": str(item["date"]), "revenue": float(item["revenue"])}
                for item in revenue_trend
            ],
        }

        cache.set(cache_key, data, DASHBOARD_CACHE_TTL)
        return success_response(data=data)

    @staticmethod
    def _calculate_growth(current: float, previous: float) -> float | None:
        if not previous:
            return None
        return round(((float(current) - float(previous)) / float(previous)) * 100, 1)


class DashboardOrdersView(APIView):
    """GET /dashboard/orders/ — recent orders for dashboard table."""

    permission_classes = [IsAuthenticated, IsManagerOrAbove]

    def get(self, request: Request) -> Response:
        from apps.orders.models import Order

        orders = (
            Order.objects
            .select_related("customer")
            .order_by("-created_at")[:20]
        )
        from apps.orders.serializers import OrderListSerializer
        return success_response(data=OrderListSerializer(orders, many=True).data)

"""Notification and report generation Celery tasks."""
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name="notifications.create",
)
def create_notification_task(
    self,
    recipient_id: str,
    notification_type: str,
    title: str,
    message: str,
    resource_type: str = "",
    resource_id: str = "",
    extra_data: dict | None = None,
) -> None:
    """Create an in-app notification for a user."""
    from apps.notifications.models import Notification
    from apps.users.models import User

    try:
        user = User.objects.get(id=recipient_id)
        Notification.objects.create(
            recipient=user,
            notification_type=notification_type,
            title=title,
            message=message,
            resource_type=resource_type,
            resource_id=resource_id,
            extra_data=extra_data,
        )
        logger.info("Notification created for user %s: %s", recipient_id, title)
    except User.DoesNotExist:
        logger.error("User %s not found for notification", recipient_id)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(name="inventory.check_low_stock", bind=True, max_retries=2)
def check_low_stock_task(self) -> None:
    """Periodic task: find low-stock items and notify managers."""
    from apps.inventory.models import Inventory

    low_stock_items = Inventory.objects.filter(
        quantity_on_hand__lte=models.F("low_stock_threshold")
    ).select_related("product", "variant")

    if not low_stock_items.exists():
        return

    logger.warning("Low stock detected: %d items", low_stock_items.count())
    # Queue notifications to managers


@shared_task(name="reports.generate_daily_sales", bind=True, max_retries=2)
def generate_daily_sales_report_task(self) -> None:
    """Generate daily sales summary report."""
    from apps.orders.models import Order

    today = timezone.now().date()
    yesterday = today - timezone.timedelta(days=1)

    orders = Order.objects.filter(
        created_at__date=yesterday,
        status__in=["confirmed", "processing", "shipped", "delivered"],
    )

    total_orders = orders.count()
    total_revenue = orders.aggregate(total=models.Sum("total_amount"))["total"] or 0

    logger.info(
        "Daily sales report: date=%s, orders=%d, revenue=%.2f",
        yesterday,
        total_orders,
        total_revenue,
    )
    # TODO: Save to Report model / send to admins


@shared_task(name="tokens.cleanup_expired", bind=True, max_retries=1)
def cleanup_expired_tokens_task(self) -> None:
    """Periodic task: remove expired verification and reset tokens."""
    from apps.authentication.models import EmailVerificationToken, PasswordResetToken

    cutoff = timezone.now()
    ev_deleted, _ = EmailVerificationToken.objects.filter(expires_at__lt=cutoff).delete()
    pr_deleted, _ = PasswordResetToken.objects.filter(expires_at__lt=cutoff).delete()
    logger.info(
        "Token cleanup: %d verification tokens, %d reset tokens deleted",
        ev_deleted,
        pr_deleted,
    )


# Import models inside tasks to avoid circular imports
from django.db import models  # noqa: E402

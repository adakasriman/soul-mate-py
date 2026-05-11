"""
Email Celery tasks — asynchronous email delivery.

All email sending is queued through Celery to keep request/response
cycles fast. Failed tasks retry automatically with exponential back-off.
"""
import logging

from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

logger = logging.getLogger(__name__)


def _send_html_email(
    subject: str,
    to_email: str,
    text_content: str,
    html_content: str | None = None,
) -> bool:
    """Internal helper to send an email."""
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        if html_content:
            msg.attach_alternative(html_content, "text/html")
        msg.send()
        return True
    except Exception as exc:
        logger.error("Email send failed to %s: %s", to_email, exc)
        raise


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="email.send_verification",
)
def send_email_verification_task(
    self,
    user_id: str,
    email: str,
    full_name: str,
    verification_url: str,
) -> None:
    """Queue and send email verification email."""
    subject = "Verify your email address"
    text_content = (
        f"Hello {full_name or 'there'},\n\n"
        f"Please verify your email by clicking the link below:\n{verification_url}\n\n"
        f"This link expires in {settings.EMAIL_VERIFICATION_EXPIRY_HOURS} hours.\n\n"
        f"If you did not create an account, you can safely ignore this email."
    )
    html_content = f"""
    <h2>Verify your email</h2>
    <p>Hello {full_name or 'there'},</p>
    <p>Click the button below to verify your email address:</p>
    <a href="{verification_url}" style="background:#4F46E5;color:white;padding:12px 24px;border-radius:6px;text-decoration:none;display:inline-block;">
      Verify Email
    </a>
    <p>This link expires in {settings.EMAIL_VERIFICATION_EXPIRY_HOURS} hours.</p>
    """
    try:
        _send_html_email(subject, email, text_content, html_content)
        logger.info("Verification email sent to %s", email)
    except Exception as exc:
        logger.warning("Retrying verification email for %s: %s", email, exc)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="email.send_welcome",
)
def send_welcome_email_task(self, user_id: str, email: str, full_name: str) -> None:
    """Send welcome email after successful verification."""
    subject = "Welcome to our platform!"
    text_content = (
        f"Hello {full_name or 'there'},\n\n"
        f"Welcome! Your account is now active.\n\n"
        f"Start shopping at: {settings.FRONTEND_URL}"
    )
    try:
        _send_html_email(subject, email, text_content)
        logger.info("Welcome email sent to %s", email)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="email.send_password_reset",
)
def send_password_reset_task(
    self,
    user_id: str,
    email: str,
    full_name: str,
    reset_url: str,
) -> None:
    """Send password reset email."""
    subject = "Reset your password"
    text_content = (
        f"Hello {full_name or 'there'},\n\n"
        f"Click the link below to reset your password:\n{reset_url}\n\n"
        f"This link expires in {settings.PASSWORD_RESET_EXPIRY_HOURS} hours.\n\n"
        f"If you did not request a password reset, please ignore this email."
    )
    html_content = f"""
    <h2>Reset your password</h2>
    <p>Hello {full_name or 'there'},</p>
    <p>Click the button below to reset your password:</p>
    <a href="{reset_url}" style="background:#DC2626;color:white;padding:12px 24px;border-radius:6px;text-decoration:none;display:inline-block;">
      Reset Password
    </a>
    <p>This link expires in {settings.PASSWORD_RESET_EXPIRY_HOURS} hours.</p>
    """
    try:
        _send_html_email(subject, email, text_content, html_content)
        logger.info("Password reset email sent to %s", email)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    name="email.send_order_confirmation",
)
def send_order_confirmation_task(self, order_id: str, email: str, full_name: str) -> None:
    """Send order confirmation email."""
    from apps.orders.models import Order

    try:
        order = Order.objects.select_related("customer").prefetch_related(
            "items__product"
        ).get(id=order_id)
    except Order.DoesNotExist:
        logger.error("Order %s not found for confirmation email", order_id)
        return

    subject = f"Order Confirmed — {order.order_number}"
    text_content = (
        f"Hello {full_name},\n\n"
        f"Your order {order.order_number} has been confirmed.\n"
        f"Total: ₹{order.total_amount}\n\n"
        f"Track your order at: {settings.FRONTEND_URL}/orders/{order.id}"
    )
    try:
        _send_html_email(subject, email, text_content)
    except Exception as exc:
        raise self.retry(exc=exc)

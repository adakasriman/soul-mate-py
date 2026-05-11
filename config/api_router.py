"""API v1 router — all app URLs registered here."""
from django.urls import include, path

app_name = "api-v1"

urlpatterns = [
    path("auth/", include("apps.authentication.urls", namespace="auth")),
    path("users/", include("apps.users.urls", namespace="users")),
    path("products/", include("apps.products.urls", namespace="products")),
    path("categories/", include("apps.categories.urls", namespace="categories")),
    path("inventory/", include("apps.inventory.urls", namespace="inventory")),
    path("orders/", include("apps.orders.urls", namespace="orders")),
    path("cart/", include("apps.cart.urls", namespace="cart")),
    path("payments/", include("apps.payments.urls", namespace="payments")),
    path("invoices/", include("apps.invoices.urls", namespace="invoices")),
    path("dashboard/", include("apps.dashboard.urls", namespace="dashboard")),
    path("reports/", include("apps.reports.urls", namespace="reports")),
    path("notifications/", include("apps.notifications.urls", namespace="notifications")),
    path("audit-logs/", include("apps.audit_logs.urls", namespace="audit_logs")),
    path("files/", include("apps.files.urls", namespace="files")),
]

"""Dashboard app URLs."""
from django.urls import path

from apps.dashboard.views import DashboardOrdersView, DashboardSummaryView

app_name = "dashboard"

urlpatterns = [
    path("summary/", DashboardSummaryView.as_view(), name="summary"),
    path("orders/", DashboardOrdersView.as_view(), name="orders"),
]

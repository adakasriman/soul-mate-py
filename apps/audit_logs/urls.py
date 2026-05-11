"""Audit logs URLs."""
from django.urls import path
from apps.audit_logs.views import AuditLogDetailView, AuditLogListView
app_name = "audit_logs"
urlpatterns = [
    path("", AuditLogListView.as_view(), name="list"),
    path("<uuid:id>/", AuditLogDetailView.as_view(), name="detail"),
]

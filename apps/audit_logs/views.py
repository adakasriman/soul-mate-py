"""Audit log views."""
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from apps.audit_logs.models import AuditLog
from core.pagination import StandardResultsPagination
from core.permissions.roles import IsAdminOrAbove

class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ["id","actor_email","action","resource_type","resource_id","ip_address","endpoint","method","old_value","new_value","is_successful","error_message","created_at"]

class AuditLogListView(ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminOrAbove]
    serializer_class = AuditLogSerializer
    pagination_class = StandardResultsPagination
    def get_queryset(self):
        qs = AuditLog.objects.order_by("-created_at")
        if action := self.request.query_params.get("action"):
            qs = qs.filter(action=action)
        if rt := self.request.query_params.get("resource_type"):
            qs = qs.filter(resource_type=rt)
        return qs

class AuditLogDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated, IsAdminOrAbove]
    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.all()
    lookup_field = "id"

"""
User management views — thin controllers.

Views only: validate input → call service → return response.
Zero business logic here.
"""
import logging

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.serializers import (
    UpdateProfileSerializer,
    UpdateUserRoleSerializer,
    UpdateUserStatusSerializer,
    UserAdminSerializer,
    UserProfileSerializer,
)
from apps.users.services import UserService
from core.pagination import StandardResultsPagination
from core.permissions.roles import IsAdminOrAbove, IsOwnerOrAdmin, IsSuperAdmin
from core.response import success_response

logger = logging.getLogger(__name__)
user_service = UserService()


class MeView(APIView):
    """GET /users/me/ — current user's profile."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        serializer = UserProfileSerializer(request.user)
        return success_response(data=serializer.data)

    def patch(self, request: Request) -> Response:
        serializer = UpdateProfileSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_user = user_service.update_profile(request.user, serializer.validated_data)
        return success_response(
            data=UserProfileSerializer(updated_user).data,
            message="Profile updated successfully.",
        )


class UserListView(ListAPIView):
    """GET /users/ — list all users (admin+)."""

    permission_classes = [IsAuthenticated, IsAdminOrAbove]
    serializer_class = UserAdminSerializer
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["role", "status", "is_email_verified"]
    search_fields = ["email", "first_name", "last_name", "phone"]
    ordering_fields = ["created_at", "email", "role"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return user_service.list_users(
            role=self.request.query_params.get("role"),
            search=self.request.query_params.get("search"),
        )


class UserDetailView(APIView):
    """GET/PATCH /users/<id>/ — retrieve or update a specific user."""

    permission_classes = [IsAuthenticated, IsAdminOrAbove]

    def get(self, request: Request, user_id: str) -> Response:
        user = user_service.get_user_or_404(user_id)
        return success_response(data=UserAdminSerializer(user).data)


class UpdateUserRoleView(APIView):
    """PATCH /users/<id>/role/ — update a user's role (admin+)."""

    permission_classes = [IsAuthenticated, IsAdminOrAbove]

    def patch(self, request: Request, user_id: str) -> Response:
        serializer = UpdateUserRoleSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        updated_user = user_service.update_role(
            actor=request.user,
            target_user_id=user_id,
            new_role=serializer.validated_data["role"],
        )
        return success_response(
            data=UserAdminSerializer(updated_user).data,
            message="User role updated successfully.",
        )


class UpdateUserStatusView(APIView):
    """PATCH /users/<id>/status/ — update a user's status (admin+)."""

    permission_classes = [IsAuthenticated, IsAdminOrAbove]

    def patch(self, request: Request, user_id: str) -> Response:
        serializer = UpdateUserStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated_user = user_service.update_status(
            actor=request.user,
            target_user_id=user_id,
            new_status=serializer.validated_data["status"],
        )
        return success_response(
            data=UserAdminSerializer(updated_user).data,
            message="User status updated successfully.",
        )


class DeleteUserView(APIView):
    """DELETE /users/<id>/ — deactivate user (super admin only)."""

    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def delete(self, request: Request, user_id: str) -> Response:
        user_service.soft_delete_user(actor=request.user, target_user_id=user_id)
        return success_response(message="User deactivated successfully.")

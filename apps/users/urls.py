"""User app URLs."""
from django.urls import path

from apps.users.views import (
    DeleteUserView,
    MeView,
    UpdateUserRoleView,
    UpdateUserStatusView,
    UserDetailView,
    UserListView,
)

app_name = "users"

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("", UserListView.as_view(), name="user-list"),
    path("<uuid:user_id>/", UserDetailView.as_view(), name="user-detail"),
    path("<uuid:user_id>/role/", UpdateUserRoleView.as_view(), name="user-role"),
    path("<uuid:user_id>/status/", UpdateUserStatusView.as_view(), name="user-status"),
    path("<uuid:user_id>/delete/", DeleteUserView.as_view(), name="user-delete"),
]

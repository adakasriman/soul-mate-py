"""
Base abstract models used across all apps.

All models should extend BaseModel or SoftDeleteModel depending
on whether soft-deletion is needed.
"""
import uuid
from typing import Any

from django.conf import settings
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Abstract model that adds created_at and updated_at fields."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class BaseModel(TimeStampedModel):
    """
    Enterprise base model.

    Adds:
    - UUID primary key
    - Audit fields (created_by, updated_by)
    - Soft delete support (is_deleted, deleted_at, deleted_by)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_updated",
    )

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    """Custom QuerySet with soft-delete support."""

    def active(self) -> "SoftDeleteQuerySet":
        """Return only non-deleted records."""
        return self.filter(is_deleted=False)

    def deleted(self) -> "SoftDeleteQuerySet":
        """Return only soft-deleted records."""
        return self.filter(is_deleted=True)

    def delete(self, deleted_by: Any = None) -> tuple[int, dict]:
        """Soft delete all records in the queryset."""
        return self.update(
            is_deleted=True,
            deleted_at=timezone.now(),
            deleted_by=deleted_by,
        )

    def hard_delete(self) -> tuple[int, dict]:
        """Permanently delete records (use with caution)."""
        return super().delete()


class SoftDeleteManager(models.Manager):
    """Manager that excludes soft-deleted records by default."""

    def get_queryset(self) -> SoftDeleteQuerySet:
        return SoftDeleteQuerySet(self.model, using=self._db).active()

    def all_with_deleted(self) -> SoftDeleteQuerySet:
        return SoftDeleteQuerySet(self.model, using=self._db)

    def deleted_only(self) -> SoftDeleteQuerySet:
        return SoftDeleteQuerySet(self.model, using=self._db).deleted()


class SoftDeleteModel(BaseModel):
    """
    Abstract model with soft delete capability.

    Provides:
    - is_deleted flag
    - deleted_at timestamp
    - deleted_by FK
    - Default manager excludes deleted records
    - all_objects manager includes deleted records
    """

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_deleted",
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, deleted_by: Any = None, **kwargs: Any) -> None:  # type: ignore[override]
        """Soft delete this record."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"])

    def hard_delete(self, **kwargs: Any) -> None:
        """Permanently delete this record (use with caution)."""
        super().delete(**kwargs)

    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"])

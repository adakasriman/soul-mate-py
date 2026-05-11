"""File upload model."""
import os, uuid
from django.conf import settings
from django.db import models
from core.models import BaseModel

def upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"uploads/{instance.resource_type}/{uuid.uuid4().hex}{ext}"

class FileUpload(BaseModel):
    class ResourceType(models.TextChoices):
        PRODUCT_IMAGE = "product_images", "Product Image"
        INVOICE_PDF = "invoice_pdfs", "Invoice PDF"
        AVATAR = "avatars", "Avatar"
        DOCUMENT = "documents", "Document"

    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="uploads")
    resource_type = models.CharField(max_length=50, choices=ResourceType.choices)
    resource_id = models.CharField(max_length=100, blank=True)
    original_filename = models.CharField(max_length=500)
    file_path = models.CharField(max_length=1000)
    url = models.URLField(max_length=2000)
    mime_type = models.CharField(max_length=100)
    file_size = models.PositiveBigIntegerField()

    class Meta:
        db_table = "file_uploads"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.resource_type}/{self.original_filename}"

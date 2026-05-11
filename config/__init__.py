"""Config package — make Celery app available at import time."""
from .celery import app as celery_app

__all__ = ["celery_app"]

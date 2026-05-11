"""Development settings — extends base."""
from .base import *  # noqa: F401, F403

DEBUG = True

# Relax throttling in dev
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {  # noqa: F405
    "anon": "1000/hour",
    "user": "10000/hour",
    "auth": "100/minute",
    "password_reset": "50/hour",
}

# Use console email backend in dev
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Django Debug Toolbar (optional — install separately)
# INSTALLED_APPS += ["debug_toolbar"]
# MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
# INTERNAL_IPS = ["127.0.0.1"]

# Disable SSL for local DB
DATABASES["default"]["OPTIONS"]["sslmode"] = "prefer"  # noqa: F405

# Show SQL queries
LOGGING["loggers"]["django.db.backends"]["level"] = "DEBUG"  # noqa: F405

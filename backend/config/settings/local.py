"""Local development settings."""
from .base import *  # noqa: F401, F403

DEBUG = True

# CORS - allow frontend in development
CORS_ALLOW_ALL_ORIGINS = True

# Additional apps for development
INSTALLED_APPS += [  # noqa: F405
    "django_extensions",
]

# Email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

"""Local development settings."""
from .base import *  # noqa: F401, F403

DEBUG = True

# CORS - allow frontend in development
CORS_ALLOW_ALL_ORIGINS = True

# CSRF trusted origins for ngrok tunnels
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:4000",
    "http://localhost:4001",
    "http://localhost:4002",
    "https://*.ngrok.io",
    "https://*.ngrok-free.app",
    "https://*.ngrok.app",
]

# Additional apps for development
INSTALLED_APPS += [  # noqa: F405
    "django_extensions",
]

# Email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

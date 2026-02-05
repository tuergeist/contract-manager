"""Test settings."""
from .base import *  # noqa: F401, F403

DEBUG = False

# Use in-memory SQLite for faster tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Faster password hashing in tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable audit log in tests (unless explicitly needed)
AUDITLOG_INCLUDE_ALL_MODELS = False

# Use in-memory cache for tests (no Redis dependency)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

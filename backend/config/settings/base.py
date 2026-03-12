"""Base settings for contract-manager project."""
import os
from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Environment
env = environ.Env(
    DEBUG=(bool, False),
)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("DJANGO_SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DJANGO_DEBUG")

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

LOGIN_URL = "/accounts/login/"

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "strawberry_django",
    "corsheaders",
    "auditlog",
    "oauth2_provider",
    "rest_framework",
    "mcp_server",
]

LOCAL_APPS = [
    "apps.core",
    "apps.tenants",
    "apps.customers",
    "apps.products",
    "apps.contracts",
    "apps.invoices",
    "apps.audit",
    "apps.todos",
    "apps.banking",
    "apps.mcp",
    "apps.offers",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "auditlog.middleware.AuditlogMiddleware",
    "apps.tenants.middleware.TenantMiddleware",
    "apps.audit.middleware.AuditUserMiddleware",
    "apps.mcp.middleware.McpResourceMetadataMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
DATABASES = {
    "default": env.db("DATABASE_URL"),
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Custom user model
AUTH_USER_MODEL = "tenants.User"

# Internationalization
LANGUAGE_CODE = "de"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("de", "Deutsch"),
    ("en", "English"),
]

LOCALE_PATHS = [
    BASE_DIR / "locale",
]

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# File upload settings
MAX_UPLOAD_SIZE = env.int("MAX_UPLOAD_SIZE", default=10 * 1024 * 1024)  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE
ALLOWED_ATTACHMENT_EXTENSIONS = [
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt", ".rtf",
    ".png", ".jpg", ".jpeg", ".gif",
    ".zip", ".rar", ".7z",
]

# Invoice file upload settings
ALLOWED_LOGO_EXTENSIONS = [".png", ".jpg", ".jpeg", ".svg"]
MAX_LOGO_SIZE = 5 * 1024 * 1024  # 5MB
MAX_REFERENCE_PDF_SIZE = 20 * 1024 * 1024  # 20MB

# S3-compatible Object Storage (Scaleway)
# Uses native django-storages setting names
AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default="")
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="fr-par")

# Storage backend - use S3 if configured, otherwise local filesystem
if AWS_S3_ENDPOINT_URL:
    # S3Boto3Storage settings for Scaleway (S3-compatible)
    AWS_S3_ADDRESSING_STYLE = "path"  # Required for Scaleway
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None  # Use bucket default ACL
    AWS_QUERYSTRING_AUTH = True  # Generate signed URLs

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Auditlog
AUDITLOG_INCLUDE_ALL_MODELS = True

# Cache
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/0"),
    }
}

# Anthropic (Claude API for PDF analysis)
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")

# Feedback integration
FEEDBACK_BACKEND = env("FEEDBACK_BACKEND", default="todoist")  # "todoist" or "github"

# Todoist backend
TODOIST_API_TOKEN = env("TODOIST_API_TOKEN", default="")
TODOIST_PROJECT_ID = env("TODOIST_PROJECT_ID", default="")

# GitHub Issues backend
GITHUB_FEEDBACK_REPO = env("GITHUB_FEEDBACK_REPO", default="")  # "owner/repo"
GITHUB_FEEDBACK_TOKEN = env("GITHUB_FEEDBACK_TOKEN", default="")

# Public signup
SIGNUP_ENABLED = env.bool("SIGNUP_ENABLED", default=True)

# System SMTP (for transactional emails not tied to a tenant, e.g. signup verification)
SYSTEM_SMTP_HOST = env("SYSTEM_SMTP_HOST", default="")
SYSTEM_SMTP_PORT = env.int("SYSTEM_SMTP_PORT", default=587)
SYSTEM_SMTP_USERNAME = env("SYSTEM_SMTP_USERNAME", default="")
SYSTEM_SMTP_PASSWORD = env("SYSTEM_SMTP_PASSWORD", default="")
SYSTEM_SMTP_FROM_ADDRESS = env("SYSTEM_SMTP_FROM_ADDRESS", default="")
SYSTEM_SMTP_FROM_NAME = env("SYSTEM_SMTP_FROM_NAME", default="Contract Manager")
SYSTEM_SMTP_USE_TLS = env.bool("SYSTEM_SMTP_USE_TLS", default=True)

# Strawberry GraphQL
STRAWBERRY_DJANGO = {
    "FIELD_DESCRIPTION_FROM_HELP_TEXT": True,
    "TYPE_DESCRIPTION_FROM_MODEL_DOCSTRING": True,
}

# OAuth2 / django-oauth-toolkit
OAUTH2_PROVIDER = {
    "PKCE_REQUIRED": True,
    "ACCESS_TOKEN_EXPIRE_SECONDS": 3600,  # 1 hour
    "REFRESH_TOKEN_EXPIRE_SECONDS": 86400 * 7,  # 7 days
    "ROTATE_REFRESH_TOKEN": True,
    "ALLOWED_REDIRECT_URI_SCHEMES": ["http", "https"],
    "SCOPES": {"read": "Read access", "write": "Write access"},
    "DEFAULT_SCOPES": ["read", "write"],
    "OIDC_ENABLED": False,
}

# Django REST Framework (required by django-oauth-toolkit)
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
    ],
}

# MCP Server
DJANGO_MCP_AUTHENTICATION_CLASSES = [
    "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
]
DJANGO_MCP_GLOBAL_SERVER_CONFIG = {
    "name": "contract-manager",
    "instructions": "Contract management system. Query customers, contracts, products, invoices, and bank transactions. Generate invoices, void them, send emails, and manage contracts.",
    "stateless": True,
}

# Celery configuration
CELERY_BROKER_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ACKS_LATE = True  # Ensure tasks aren't lost on worker crash
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_BEAT_SCHEDULE = {
    "refresh-time-tracking-data": {
        "task": "apps.contracts.tasks.refresh_all_time_tracking_data",
        "schedule": 43200,  # every 12 hours
    },
    "sync-hubspot-all-tenants": {
        "task": "apps.customers.tasks.sync_all_hubspot_tenants",
        "schedule": 21600,  # every 6 hours
    },
    "auto-link-time-tracking": {
        "task": "apps.contracts.tasks.auto_link_time_tracking_projects",
        "schedule": 86400,  # daily
    },
    "capture-fte-snapshots": {
        "task": "apps.banking.tasks.capture_monthly_fte_snapshots",
        "schedule": 86400,  # daily (checks capture day internally)
    },
}

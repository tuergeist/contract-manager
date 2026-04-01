"""Tenant and User models for multi-tenant support."""
import hashlib
import secrets
import string
from datetime import timedelta
from functools import cached_property

from cryptography.fernet import Fernet
from django.conf import settings as django_settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone

from apps.core.models import TimestampedModel


def _get_fernet():
    """Get Fernet instance using SECRET_KEY."""
    import base64
    key = hashlib.sha256(django_settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


class Tenant(TimestampedModel):
    """A tenant represents a company using the system."""

    name = models.CharField(max_length=255)
    currency = models.CharField(max_length=3, default="EUR")
    hubspot_config = models.JSONField(default=dict, blank=True)
    time_tracking_config = models.JSONField(default=dict, blank=True)
    settings = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def currency_symbol(self) -> str:
        """Return the currency symbol for the tenant's currency."""
        symbols = {
            "EUR": "\u20ac",
            "USD": "$",
            "GBP": "\u00a3",
            "CHF": "CHF ",
        }
        return symbols.get(self.currency, self.currency + " ")


class Role(TimestampedModel):
    """Roles for permission management within a tenant."""

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="roles",
    )
    name = models.CharField(max_length=100)
    permissions = models.JSONField(default=dict, blank=True)
    is_default = models.BooleanField(default=False)
    is_system = models.BooleanField(default=False)

    class Meta:
        ordering = ["tenant", "name"]
        unique_together = ["tenant", "name"]

    def __str__(self):
        return f"{self.tenant.name} - {self.name}"


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model with tenant association."""

    username = None  # Remove username field
    email = models.EmailField(unique=True)

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    roles = models.ManyToManyField(
        Role,
        blank=True,
        related_name="users",
    )
    is_admin = models.BooleanField(default=False)
    notification_preferences = models.JSONField(default=dict, blank=True)
    dashboard_preferences = models.JSONField(default=dict, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return self.email

    @property
    def is_super_admin(self) -> bool:
        """Check if user is the super-admin."""
        return self.email == "admin@test.local"

    @cached_property
    def effective_permissions(self) -> set[str]:
        """Compute the union of all permissions from assigned roles."""
        perms = set()
        for role in self.roles.all():
            for key, granted in (role.permissions or {}).items():
                if granted:
                    perms.add(key)
        return perms

    def has_perm_check(self, resource: str, action: str) -> bool:
        """Check if user has a specific permission via their roles."""
        if self.is_super_admin:
            return True
        return f"{resource}.{action}" in self.effective_permissions


class UserInvitation(TimestampedModel):
    """Invitation for a new user to join a tenant."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        USED = "used", "Used"
        REVOKED = "revoked", "Revoked"

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    expires_at = models.DateTimeField()
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_invitations",
    )
    role_ids = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invitation for {self.email} ({self.status})"

    @classmethod
    def create_invitation(cls, tenant, email, created_by):
        """Create a new invitation with a secure token."""
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(days=7)
        return cls.objects.create(
            tenant=tenant,
            email=email,
            token=token,
            expires_at=expires_at,
            created_by=created_by,
        )

    @property
    def is_valid(self) -> bool:
        """Check if invitation is still valid."""
        return self.status == self.Status.PENDING and self.expires_at > timezone.now()

    @property
    def is_expired(self) -> bool:
        """Check if invitation has expired."""
        return self.expires_at <= timezone.now()


class PasswordResetToken(TimestampedModel):
    """Token for password reset."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )
    token = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Password reset for {self.user.email}"

    @classmethod
    def create_token(cls, user):
        """Create a new password reset token."""
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=24)
        return cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at,
        )

    @property
    def is_valid(self) -> bool:
        """Check if token is still valid."""
        return not self.used and self.expires_at > timezone.now()

    @property
    def is_expired(self) -> bool:
        """Check if token has expired."""
        return self.expires_at <= timezone.now()


class SignupVerification(TimestampedModel):
    """Token for verifying a new tenant signup."""

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="signup_verifications",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="signup_verifications",
    )
    token = models.CharField(max_length=64, unique=True)
    email = models.EmailField()
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Signup verification for {self.email}"

    @classmethod
    def create_token(cls, tenant, user):
        """Create a new signup verification token."""
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=24)
        return cls.objects.create(
            tenant=tenant,
            user=user,
            token=token,
            email=user.email,
            expires_at=expires_at,
        )

    @property
    def is_valid(self) -> bool:
        """Check if token is still valid."""
        return not self.used and self.expires_at > timezone.now()

    @property
    def is_expired(self) -> bool:
        """Check if token has expired."""
        return self.expires_at <= timezone.now()


class TwoFactorConfig(TimestampedModel):
    """Two-factor authentication configuration for a user."""

    class Method(models.TextChoices):
        TOTP = "totp", "Authenticator App"
        EMAIL = "email", "Email Code"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="two_factor_config",
    )
    method = models.CharField(max_length=10, choices=Method.choices)
    totp_secret_encrypted = models.TextField(blank=True, default="")
    recovery_codes_hashed = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"2FA ({self.method}) for {self.user.email}"

    def set_totp_secret(self, secret: str):
        """Encrypt and store TOTP secret."""
        f = _get_fernet()
        self.totp_secret_encrypted = f.encrypt(secret.encode()).decode()

    def get_totp_secret(self) -> str:
        """Decrypt and return TOTP secret."""
        f = _get_fernet()
        return f.decrypt(self.totp_secret_encrypted.encode()).decode()

    @staticmethod
    def generate_recovery_codes() -> tuple[list[str], list[str]]:
        """Generate recovery codes. Returns (plaintext_codes, hashed_codes)."""
        chars = string.ascii_lowercase + string.digits
        codes = ["".join(secrets.choice(chars) for _ in range(8)) for _ in range(10)]
        hashed = [hashlib.sha256(c.encode()).hexdigest() for c in codes]
        return codes, hashed

    def verify_recovery_code(self, code: str) -> bool:
        """Verify and consume a recovery code. Returns True if valid."""
        code_hash = hashlib.sha256(code.strip().lower().encode()).hexdigest()
        if code_hash in self.recovery_codes_hashed:
            self.recovery_codes_hashed.remove(code_hash)
            self.save(update_fields=["recovery_codes_hashed"])
            return True
        return False


class APIKey(TimestampedModel):
    """API key for programmatic access with scoped permissions."""

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="api_keys",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="api_keys",
    )
    name = models.CharField(max_length=100)
    key_hash = models.CharField(max_length=128, unique=True)
    prefix = models.CharField(max_length=8)
    permissions = models.JSONField(default=dict)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"APIKey {self.prefix}... ({self.name}) for {self.user.email}"

    @staticmethod
    def generate():
        """Generate a new API key. Returns (raw_key, prefix, key_hash)."""
        raw = secrets.token_urlsafe(32)
        prefix = raw[:8]
        key_hash = hashlib.sha256(raw.encode()).hexdigest()
        return raw, prefix, key_hash

    @staticmethod
    def hash_key(raw_key: str) -> str:
        """Hash a raw API key for lookup."""
        return hashlib.sha256(raw_key.encode()).hexdigest()

    @property
    def is_valid(self) -> bool:
        """Check if the API key is still valid (active and not expired)."""
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True

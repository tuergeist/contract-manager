"""Celery tasks for tenant operations."""

import logging

from celery import shared_task

from apps.core.smtp import SmtpError, send_notification

logger = logging.getLogger(__name__)

PASSWORD_RESET_TEMPLATES = {
    "en": {
        "subject": "Reset your password",
        "body": """
<div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #1a1a1a;">Reset your password</h2>
  <p>You requested a password reset for your account at <strong>{tenant_name}</strong>.</p>
  <p>Click the link below to set a new password. This link is valid for 24 hours.</p>
  <p style="margin: 24px 0;">
    <a href="{reset_url}" style="background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
      Reset Password
    </a>
  </p>
  <p style="color: #666; font-size: 14px;">If you didn't request this, you can safely ignore this email.</p>
  <p style="color: #999; font-size: 12px;">Or copy this link: {reset_url}</p>
</div>
""",
    },
    "de": {
        "subject": "Passwort zurücksetzen",
        "body": """
<div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #1a1a1a;">Passwort zurücksetzen</h2>
  <p>Sie haben eine Passwort-Zurücksetzung für Ihr Konto bei <strong>{tenant_name}</strong> angefordert.</p>
  <p>Klicken Sie auf den folgenden Link, um ein neues Passwort festzulegen. Der Link ist 24 Stunden gültig.</p>
  <p style="margin: 24px 0;">
    <a href="{reset_url}" style="background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
      Passwort zurücksetzen
    </a>
  </p>
  <p style="color: #666; font-size: 14px;">Falls Sie dies nicht angefordert haben, können Sie diese E-Mail ignorieren.</p>
  <p style="color: #999; font-size: 12px;">Oder kopieren Sie diesen Link: {reset_url}</p>
</div>
""",
    },
}


@shared_task(bind=True, max_retries=0)
def send_password_reset_email(self, user_id: int, reset_url: str) -> bool:
    """Send a password reset email to a user.

    Args:
        user_id: ID of the user to send the email to
        reset_url: The full password reset URL with token

    Returns:
        True if sent successfully, False otherwise
    """
    from apps.tenants.models import User

    try:
        user = User.objects.select_related("tenant").get(id=user_id)
    except User.DoesNotExist:
        logger.error("Password reset email: user %s not found", user_id)
        return False

    tenant = user.tenant
    if not tenant:
        logger.error("Password reset email: user %s has no tenant", user_id)
        return False

    lang = (tenant.settings or {}).get("language", "de")
    template = PASSWORD_RESET_TEMPLATES.get(lang, PASSWORD_RESET_TEMPLATES["de"])
    tenant_name = tenant.name or "Contract Manager"

    subject = template["subject"]
    body_html = template["body"].format(
        reset_url=reset_url,
        tenant_name=tenant_name,
    )

    try:
        send_notification(tenant, to=[user.email], subject=subject, body_html=body_html)
        logger.info("Password reset email sent to %s", user.email)
        return True
    except SmtpError as e:
        logger.error("Failed to send password reset email to %s: %s", user.email, e)
        return False

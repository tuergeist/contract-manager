"""Celery tasks for tenant operations."""

import logging
import secrets

from celery import shared_task
from django.core.cache import cache

from apps.core.smtp import SmtpError, send_notification, send_system_notification

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


TWO_FA_CODE_TEMPLATES = {
    "en": {
        "subject": "Your verification code",
        "body": """
<div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #1a1a1a;">Your verification code</h2>
  <p>Use the following code to sign in to your account at <strong>{tenant_name}</strong>:</p>
  <p style="margin: 24px 0; text-align: center;">
    <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; background: #f3f4f6; padding: 12px 24px; border-radius: 8px;">{code}</span>
  </p>
  <p style="color: #666; font-size: 14px;">This code expires in 5 minutes. If you didn't request this, please change your password immediately.</p>
</div>
""",
    },
    "de": {
        "subject": "Ihr Bestätigungscode",
        "body": """
<div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #1a1a1a;">Ihr Bestätigungscode</h2>
  <p>Verwenden Sie den folgenden Code, um sich bei <strong>{tenant_name}</strong> anzumelden:</p>
  <p style="margin: 24px 0; text-align: center;">
    <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; background: #f3f4f6; padding: 12px 24px; border-radius: 8px;">{code}</span>
  </p>
  <p style="color: #666; font-size: 14px;">Dieser Code ist 5 Minuten gültig. Falls Sie dies nicht angefordert haben, ändern Sie bitte sofort Ihr Passwort.</p>
</div>
""",
    },
}


@shared_task(bind=True, max_retries=0)
def send_2fa_email_code(self, user_id: int) -> bool:
    """Generate and send a 2FA email code.

    Stores the code in cache with 5-minute TTL.

    Returns:
        True if sent successfully, False otherwise
    """
    from apps.tenants.models import User

    try:
        user = User.objects.select_related("tenant").get(id=user_id)
    except User.DoesNotExist:
        logger.error("2FA email code: user %s not found", user_id)
        return False

    tenant = user.tenant
    if not tenant:
        logger.error("2FA email code: user %s has no tenant", user_id)
        return False

    # Generate 6-digit code
    code = f"{secrets.randbelow(1000000):06d}"
    cache.set(f"2fa_code:{user_id}", code, timeout=300)  # 5 min

    lang = (tenant.settings or {}).get("language", "de")
    template = TWO_FA_CODE_TEMPLATES.get(lang, TWO_FA_CODE_TEMPLATES["de"])
    tenant_name = tenant.name or "Contract Manager"

    subject = template["subject"]
    body_html = template["body"].format(code=code, tenant_name=tenant_name)

    try:
        send_notification(tenant, to=[user.email], subject=subject, body_html=body_html)
        logger.info("2FA code sent to %s", user.email)
        return True
    except SmtpError as e:
        logger.error("Failed to send 2FA code to %s: %s", user.email, e)
        return False


SIGNUP_VERIFICATION_TEMPLATES = {
    "en": {
        "subject": "Verify your account",
        "body": """
<div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #1a1a1a;">Verify your account</h2>
  <p>Thank you for signing up! Please verify your email address to activate your account.</p>
  <p style="margin: 24px 0;">
    <a href="{verify_url}" style="background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
      Verify Email
    </a>
  </p>
  <p style="color: #666; font-size: 14px;">This link is valid for 24 hours.</p>
  <p style="color: #999; font-size: 12px;">Or copy this link: {verify_url}</p>
</div>
""",
    },
    "de": {
        "subject": "Bestätige dein Konto",
        "body": """
<div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #1a1a1a;">Bestätige dein Konto</h2>
  <p>Vielen Dank für die Registrierung! Bitte bestätige deine E-Mail-Adresse, um dein Konto zu aktivieren.</p>
  <p style="margin: 24px 0;">
    <a href="{verify_url}" style="background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
      E-Mail bestätigen
    </a>
  </p>
  <p style="color: #666; font-size: 14px;">Dieser Link ist 24 Stunden gültig.</p>
  <p style="color: #999; font-size: 12px;">Oder kopiere diesen Link: {verify_url}</p>
</div>
""",
    },
}


@shared_task(bind=True, max_retries=0)
def send_signup_verification_email(self, verification_id: int, base_url: str) -> bool:
    """Send signup verification email.

    Args:
        verification_id: ID of the SignupVerification record
        base_url: Frontend base URL for building the verification link

    Returns:
        True if sent successfully, False otherwise
    """
    from apps.tenants.models import SignupVerification

    try:
        verification = SignupVerification.objects.get(id=verification_id)
    except SignupVerification.DoesNotExist:
        logger.error("Signup verification %s not found", verification_id)
        return False

    verify_url = f"{base_url}/verify-signup?token={verification.token}"

    # Default to German
    template = SIGNUP_VERIFICATION_TEMPLATES["de"]

    subject = template["subject"]
    body_html = template["body"].format(verify_url=verify_url)

    try:
        send_system_notification(to=[verification.email], subject=subject, body_html=body_html)
        logger.info("Signup verification email sent to %s", verification.email)
        return True
    except SmtpError as e:
        logger.error("Failed to send signup verification to %s: %s", verification.email, e)
        return False


INVITATION_TEMPLATES = {
    "en": {
        "subject": "You've been invited to {tenant_name}",
        "body": """
<div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #1a1a1a;">You've been invited!</h2>
  <p><strong>{inviter_name}</strong> ({inviter_email}) has invited you to join <strong>{tenant_name}</strong> on Contract Manager.</p>
  <p>Click the link below to set up your account. This invitation is valid for 7 days.</p>
  <p style="margin: 24px 0;">
    <a href="{invite_url}" style="background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
      Accept Invitation
    </a>
  </p>
  <p style="color: #999; font-size: 12px;">Or copy this link: {invite_url}</p>
</div>
""",
    },
    "de": {
        "subject": "Einladung zu {tenant_name}",
        "body": """
<div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #1a1a1a;">Du wurdest eingeladen!</h2>
  <p><strong>{inviter_name}</strong> ({inviter_email}) hat dich eingeladen, <strong>{tenant_name}</strong> im Contract Manager beizutreten.</p>
  <p>Klicke auf den Link, um dein Konto einzurichten. Die Einladung ist 7 Tage gültig.</p>
  <p style="margin: 24px 0;">
    <a href="{invite_url}" style="background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
      Einladung annehmen
    </a>
  </p>
  <p style="color: #999; font-size: 12px;">Oder kopiere diesen Link: {invite_url}</p>
</div>
""",
    },
}


@shared_task(bind=True, max_retries=0)
def send_invitation_email(self, invitation_id: int, invite_url: str, inviter_user_id: int) -> bool:
    """Send invitation email to an invited user.

    Args:
        invitation_id: ID of the UserInvitation record
        invite_url: Full URL to accept the invitation
        inviter_user_id: ID of the user who created the invitation
    """
    from apps.tenants.models import User, UserInvitation

    try:
        invitation = UserInvitation.objects.select_related("tenant").get(id=invitation_id)
    except UserInvitation.DoesNotExist:
        logger.error("Invitation %s not found", invitation_id)
        return False

    try:
        inviter = User.objects.get(id=inviter_user_id)
    except User.DoesNotExist:
        logger.error("Inviter user %s not found", inviter_user_id)
        return False

    tenant = invitation.tenant
    if not tenant:
        logger.error("Invitation %s has no tenant", invitation_id)
        return False

    lang = (tenant.settings or {}).get("language", "de")
    template = INVITATION_TEMPLATES.get(lang, INVITATION_TEMPLATES["de"])
    tenant_name = tenant.name or "Contract Manager"
    inviter_name = inviter.get_full_name() or inviter.email
    inviter_email = inviter.email

    subject = template["subject"].format(tenant_name=tenant_name)
    body_html = template["body"].format(
        invite_url=invite_url,
        tenant_name=tenant_name,
        inviter_name=inviter_name,
        inviter_email=inviter_email,
    )

    try:
        send_notification(tenant, to=[invitation.email], subject=subject, body_html=body_html)
        logger.info("Invitation email sent to %s", invitation.email)
        return True
    except SmtpError as e:
        logger.error("Failed to send invitation to %s: %s", invitation.email, e)
        return False

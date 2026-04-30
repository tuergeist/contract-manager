"""SMTP notification service for internal transactional emails.

Uses smtplib directly for per-tenant SMTP configuration.
Independent from M365 (which handles invoice emails).
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

logger = logging.getLogger(__name__)


class SmtpError(Exception):
    """Error communicating via SMTP."""


def _get_config(tenant) -> dict:
    """Extract and validate SMTP config from tenant settings."""
    config = (tenant.settings or {}).get("smtp", {})
    if not all(config.get(k) for k in ("host", "port", "username", "password", "from_address")):
        raise SmtpError("SMTP not configured")
    return config


def _connect(config: dict) -> smtplib.SMTP:
    """Create an authenticated SMTP connection.

    Port 465 uses implicit TLS (SMTPS); other ports use plain SMTP with
    optional STARTTLS upgrade when ``use_tls`` is set.
    """
    try:
        port = int(config["port"])
        if port == 465:
            server = smtplib.SMTP_SSL(config["host"], port, timeout=15)
            server.ehlo()
        else:
            server = smtplib.SMTP(config["host"], port, timeout=15)
            server.ehlo()
            if config.get("use_tls", True):
                server.starttls()
                server.ehlo()
        server.login(config["username"], config["password"])
        return server
    except smtplib.SMTPException as e:
        raise SmtpError(f"SMTP connection failed: {e}") from e
    except OSError as e:
        raise SmtpError(f"SMTP connection failed: {e}") from e


def test_connection(tenant) -> dict:
    """Test SMTP connection by performing handshake + auth without sending."""
    config = _get_config(tenant)
    server = _connect(config)
    server.quit()
    return {"success": True}


def send_system_notification(*, to: list[str], subject: str, body_html: str) -> None:
    """Send a notification email via system-level SMTP (not tenant-scoped).

    Used for transactional emails that aren't tied to a tenant,
    e.g. signup verification.

    Raises:
        SmtpError: On configuration or delivery failure
    """
    from django.conf import settings

    config = {
        "host": settings.SYSTEM_SMTP_HOST,
        "port": settings.SYSTEM_SMTP_PORT,
        "username": settings.SYSTEM_SMTP_USERNAME,
        "password": settings.SYSTEM_SMTP_PASSWORD,
        "from_address": settings.SYSTEM_SMTP_FROM_ADDRESS,
        "from_name": settings.SYSTEM_SMTP_FROM_NAME,
        "use_tls": settings.SYSTEM_SMTP_USE_TLS,
    }
    if not all(config.get(k) for k in ("host", "port", "username", "password", "from_address")):
        raise SmtpError("System SMTP not configured")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    from_name = config.get("from_name", "")
    msg["From"] = formataddr((from_name, config["from_address"])) if from_name else config["from_address"]
    msg["To"] = ", ".join(to)
    msg.attach(MIMEText(body_html, "html"))

    try:
        server = _connect(config)
        server.sendmail(config["from_address"], to, msg.as_string())
        server.quit()
        logger.info("System notification sent via SMTP: to=%s, subject=%s", to, subject)
    except SmtpError:
        raise
    except smtplib.SMTPException as e:
        raise SmtpError(f"Failed to send email: {e}") from e


def send_notification(tenant, *, to: list[str], subject: str, body_html: str) -> None:
    """Send a notification email via SMTP.

    Args:
        tenant: Tenant with SMTP config in settings
        to: List of recipient email addresses
        subject: Email subject
        body_html: HTML body content

    Raises:
        SmtpError: On configuration or delivery failure
    """
    config = _get_config(tenant)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    from_name = config.get("from_name", "")
    msg["From"] = formataddr((from_name, config["from_address"])) if from_name else config["from_address"]
    msg["To"] = ", ".join(to)
    msg.attach(MIMEText(body_html, "html"))

    try:
        server = _connect(config)
        server.sendmail(config["from_address"], to, msg.as_string())
        server.quit()
        logger.info("Notification sent via SMTP: to=%s, subject=%s", to, subject)
    except SmtpError:
        raise
    except smtplib.SMTPException as e:
        raise SmtpError(f"Failed to send email: {e}") from e

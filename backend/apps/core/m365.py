"""Microsoft 365 integration via Microsoft Graph API.

Uses MSAL ConfidentialClientApplication with client credentials flow
for server-side (daemon) access. Requires Azure AD app registration with
Mail.Send application permission + admin consent.
"""

import base64
import logging

import httpx
from msal import ConfidentialClientApplication

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
AUTHORITY_BASE = "https://login.microsoftonline.com"
SCOPES = ["https://graph.microsoft.com/.default"]


class M365Error(Exception):
    """Error communicating with Microsoft 365."""


def _get_config(tenant):
    """Extract M365 config from tenant settings."""
    config = (tenant.settings or {}).get("m365", {})
    if not config.get("tenant_id") or not config.get("client_id") or not config.get("client_secret"):
        raise M365Error("M365 not configured")
    return config


def _get_token(config: dict) -> str:
    """Acquire an access token using client credentials flow."""
    app = ConfidentialClientApplication(
        client_id=config["client_id"],
        client_credential=config["client_secret"],
        authority=f"{AUTHORITY_BASE}/{config['tenant_id']}",
    )
    result = app.acquire_token_for_client(scopes=SCOPES)
    if "access_token" in result:
        return result["access_token"]
    error = result.get("error_description", result.get("error", "Unknown error"))
    raise M365Error(f"Authentication failed: {error}")


def get_m365_token(tenant) -> str:
    """Acquire M365 token for a tenant."""
    config = _get_config(tenant)
    return _get_token(config)


def test_connection(tenant) -> dict:
    """Test M365 connection by acquiring a token.

    Only requires Mail.Send permission — no extra Graph read permissions needed.
    """
    config = _get_config(tenant)
    _get_token(config)  # raises M365Error on auth failure
    return {"success": True, "organization": config.get("tenant_id", "")}


def list_mailboxes(tenant) -> list[dict]:
    """List mailboxes the app can send from."""
    config = _get_config(tenant)
    token = _get_token(config)
    # List users with mail attribute (includes shared mailboxes)
    resp = httpx.get(
        f"{GRAPH_BASE}/users?$select=mail,displayName,userPrincipalName&$top=100",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    if resp.status_code != 200:
        raise M365Error(f"Failed to list mailboxes: {resp.status_code} {resp.text[:200]}")

    users = resp.json().get("value", [])
    mailboxes = []
    for u in users:
        email = u.get("mail") or u.get("userPrincipalName", "")
        if email and "@" in email:
            mailboxes.append({
                "email": email,
                "display_name": u.get("displayName", email),
            })
    return mailboxes


def send_mail(tenant, *, to: list[str], subject: str, body_html: str,
              attachments: list[dict] | None = None) -> str:
    """Send an email via Microsoft Graph API.

    Args:
        tenant: Tenant with M365 config
        to: List of recipient email addresses
        subject: Email subject
        body_html: HTML body content
        attachments: List of dicts with 'name', 'content_type', 'content_bytes' (bytes)

    Returns:
        Message ID from Graph API response headers
    """
    config = _get_config(tenant)
    sender = config.get("sender_mailbox")
    if not sender:
        raise M365Error("No sender mailbox configured")

    token = _get_token(config)

    message = {
        "subject": subject,
        "body": {"contentType": "HTML", "content": body_html},
        "toRecipients": [
            {"emailAddress": {"address": addr}} for addr in to
        ],
    }

    if attachments:
        message["attachments"] = [
            {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": att["name"],
                "contentType": att["content_type"],
                "contentBytes": base64.b64encode(att["content_bytes"]).decode(),
            }
            for att in attachments
        ]

    resp = httpx.post(
        f"{GRAPH_BASE}/users/{sender}/sendMail",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"message": message, "saveToSentItems": True},
        timeout=30,
    )

    if resp.status_code == 202:
        # sendMail returns 202 Accepted with no body
        message_id = resp.headers.get("request-id", "")
        logger.info("Email sent via M365: to=%s, subject=%s", to, subject)
        return message_id

    raise M365Error(f"Failed to send email: {resp.status_code} {resp.text[:500]}")

"""Notification event system.

Fires email notifications for subscribed users when events occur.
Uses send_notification() from apps/core/smtp.py for delivery.
"""

import logging

from apps.core.smtp import SmtpError, send_notification

logger = logging.getLogger(__name__)


def is_subscribed(user, event_type: str) -> bool:
    """Check if a user is subscribed to an event type.

    Missing key = subscribed (opt-out model).
    Only explicit False means unsubscribed.
    """
    prefs = user.notification_preferences or {}
    return prefs.get(event_type, True) is not False


def _todo_entity_url(todo, base_url):
    """Build a frontend URL to the entity linked to a todo."""
    if todo.contract_id:
        return f"{base_url}/contracts/{todo.contract_id}"
    if todo.contract_item_id:
        return f"{base_url}/contracts/{todo.contract_item.contract_id}"
    if todo.customer_id:
        return f"{base_url}/customers/{todo.customer_id}"
    return None


def _build_todo_assigned_email(*, todo, assigner, base_url="", **kwargs):
    """Build subject and body for todo assignment notification."""
    assigner_name = assigner.get_full_name() or assigner.email
    subject = f"Todo assigned to you: {todo.text[:60]}"

    lines = [
        f"<p><strong>{assigner_name}</strong> assigned a todo to you:</p>",
        f"<p style='padding: 12px; background: #f5f5f5; border-radius: 4px;'>{todo.text}</p>",
    ]

    if base_url:
        entity_url = _todo_entity_url(todo, base_url)
        if entity_url and todo.entity_name:
            lines.append(
                f"<p>Related: <a href=\"{entity_url}\">{todo.entity_name}</a></p>"
            )
        todo_url = f"{base_url}/todos"
        lines.append(f"<p><a href=\"{todo_url}\">Open Todos</a></p>")

    body_html = "\n".join(lines)
    return subject, body_html


def _build_hubspot_new_contract_email(*, contract_name, customer_name, **kwargs):
    """Build subject and body for new HubSpot contract notification."""
    subject = f"New contract from HubSpot: {contract_name}"
    body_html = (
        f"<p>A new contract has arrived via HubSpot deal sync:</p>"
        f"<p><strong>{contract_name}</strong> for <strong>{customer_name}</strong></p>"
    )
    return subject, body_html


def _build_hubspot_sync_completed_email(*, results, errors=None, **kwargs):
    """Build subject and body for HubSpot sync completion notification."""
    errors = errors or {}
    subject = "HubSpot Sync Summary"

    lines = ["<p><strong>HubSpot Sync Summary</strong></p>", "<ul>"]
    for sync_type, counts in results.items():
        label = sync_type.replace("_", " ").title()
        parts = [f"{v} {k}" for k, v in counts.items()]
        lines.append(f"<li>{label}: {', '.join(parts)}</li>")
    lines.append("</ul>")

    if errors:
        for sync_type, error_msg in errors.items():
            label = sync_type.replace("_", " ").title()
            lines.append(
                f"<p style='color: #b45309;'>&#9888; {label} sync failed: {error_msg}</p>"
            )

    body_html = "\n".join(lines)
    return subject, body_html


def _build_time_tracking_sync_completed_email(
    *, synced, total, failed, **kwargs
):
    """Build subject and body for time tracking sync completion notification."""
    subject = "Time Tracking Sync Summary"

    lines = [
        "<p><strong>Time Tracking Sync Summary</strong></p>",
        f"<p>Mappings refreshed: {synced}/{total}</p>",
    ]
    if failed:
        lines.append(
            f"<p style='color: #b45309;'>&#9888; {failed} mapping(s) failed to sync</p>"
        )

    body_html = "\n".join(lines)
    return subject, body_html


NOTIFICATION_TYPES = {
    "todo_assigned": {
        "description": "Todo assigned to me",
        "build_email": _build_todo_assigned_email,
    },
    "hubspot_new_contract": {
        "description": "New contract from HubSpot",
        "build_email": _build_hubspot_new_contract_email,
    },
    "hubspot_sync_completed": {
        "description": "HubSpot sync summary",
        "build_email": _build_hubspot_sync_completed_email,
    },
    "time_tracking_sync_completed": {
        "description": "Time tracking sync summary",
        "build_email": _build_time_tracking_sync_completed_email,
    },
}


def notify(tenant, event_type: str, *, recipients=None, **kwargs):
    """Fire a notification event.

    Args:
        tenant: The tenant context
        event_type: Key from NOTIFICATION_TYPES
        recipients: List of User objects to notify. If None, must be provided.
        **kwargs: Context passed to the email builder (e.g., todo, assigner)
    """
    if event_type not in NOTIFICATION_TYPES:
        logger.warning("Unknown notification event type: %s", event_type)
        return

    if not recipients:
        return

    config = NOTIFICATION_TYPES[event_type]
    build_email = config["build_email"]

    for user in recipients:
        if not is_subscribed(user, event_type):
            continue

        try:
            subject, body_html = build_email(**kwargs)
            send_notification(tenant, to=[user.email], subject=subject, body_html=body_html)
            logger.info("Notification sent: type=%s, to=%s", event_type, user.email)
        except SmtpError as e:
            logger.error("Failed to send notification: type=%s, to=%s, error=%s", event_type, user.email, e)
        except Exception:
            logger.exception("Unexpected error sending notification: type=%s, to=%s", event_type, user.email)

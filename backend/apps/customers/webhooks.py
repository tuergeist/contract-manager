"""HubSpot webhook receiver endpoint."""

import hashlib
import json
import logging

from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)


def _verify_signature(client_secret: str, request_body: bytes, signature: str) -> bool:
    """Verify HubSpot webhook signature (v1).

    HubSpot v1 signature = SHA-256(clientSecret + requestBody).
    """
    expected = hashlib.sha256(
        client_secret.encode("utf-8") + request_body
    ).hexdigest()
    return expected == signature


def _find_tenant_by_portal_id(portal_id: int) -> Tenant | None:
    """Look up an active tenant by HubSpot portal ID."""
    for tenant in Tenant.objects.filter(is_active=True):
        config = tenant.hubspot_config or {}
        if config.get("portal_id") and int(config["portal_id"]) == portal_id:
            return tenant
    return None


@method_decorator(csrf_exempt, name="dispatch")
class HubSpotWebhookView(View):
    """Receive and dispatch HubSpot webhook events."""

    http_method_names = ["post"]

    def post(self, request):
        signature = request.headers.get("X-HubSpot-Signature")
        if not signature:
            return HttpResponse(status=401)

        body = request.body

        # Parse the payload to extract portalId for tenant lookup
        try:
            events = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            return HttpResponse(status=400)

        if not isinstance(events, list):
            events = [events]

        if not events:
            return HttpResponse(status=200)

        # All events in a batch share the same portalId
        portal_id = events[0].get("portalId")
        if not portal_id:
            logger.warning("Webhook event missing portalId")
            return HttpResponse(status=200)

        tenant = _find_tenant_by_portal_id(int(portal_id))
        if not tenant:
            logger.warning("No tenant found for HubSpot portalId=%s", portal_id)
            return HttpResponse(status=200)

        client_secret = (tenant.hubspot_config or {}).get("client_secret")
        if not client_secret:
            logger.warning(
                "Tenant %s has no client_secret configured for webhook verification",
                tenant.id,
            )
            return HttpResponse(status=200)

        # Verify HMAC signature
        if not _verify_signature(client_secret, body, signature):
            return HttpResponse(status=401)

        # Dispatch each event as an async Celery task
        from apps.customers.tasks import process_hubspot_webhook_event

        for event in events:
            process_hubspot_webhook_event.delay(event, tenant.id)

        # Update last received timestamp
        from django.utils import timezone as tz

        tenant.hubspot_config["webhook_last_received"] = tz.now().isoformat()
        tenant.save(update_fields=["hubspot_config"])

        return HttpResponse(status=200)

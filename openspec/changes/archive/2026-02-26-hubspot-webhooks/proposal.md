## Why

The current HubSpot integration syncs customers, products, and deals on a 6-hour polling cycle. This means changes in HubSpot can take up to 6 hours to appear in the app. Webhooks provide near-real-time updates — HubSpot pushes changes as they happen, so the app always reflects the latest CRM state without waiting for the next sync window.

## What Changes

- Add a webhook endpoint that receives HubSpot event notifications (company/product/deal create, update, delete, and property changes)
- Validate incoming webhook requests using HubSpot's `X-HubSpot-Signature` HMAC verification
- Process webhook events by mapping them to existing sync logic (create/update individual records rather than full-table sync)
- Add a settings UI to enable/disable webhook mode as an alternative to polling sync
- Store the HubSpot App ID and Client Secret on the tenant (required for webhook signature verification)
- Keep the existing 6-hour polling sync as a fallback — tenants choose one or the other

## Capabilities

### New Capabilities
- `webhook-receiver`: Public HTTP endpoint that accepts HubSpot webhook POST requests, verifies signatures, and dispatches events to async processing
- `webhook-event-processing`: Celery tasks that process individual webhook events (company/product/deal changes) using existing HubSpotService methods
- `webhook-settings`: Settings UI for configuring webhook mode — entering App ID/Client Secret, enabling webhook sync, and viewing webhook status/activity

### Modified Capabilities
- `hubspot-auto-sync`: The sync mode selection (polling vs webhooks) changes how auto-sync behaves — polling is disabled when webhooks are active

## Impact

- **Backend**: New Django URL route for webhook endpoint (public, no auth — uses HMAC verification instead), new Celery tasks for event processing, new fields in `hubspot_config` JSON
- **Frontend**: New section in HubSpot integration settings for webhook configuration
- **Infrastructure**: The webhook endpoint must be publicly accessible over HTTPS — already the case for the production deployment
- **Dependencies**: No new packages — uses stdlib `hashlib`/`hmac` for signature verification
- **Security**: Webhook endpoint is unauthenticated but protected by HMAC signature validation using the HubSpot app's client secret

## Context

The app currently syncs HubSpot data (companies, products, deals) via a Celery beat task (`sync_all_hubspot_tenants`) that runs every 6 hours. Each sync does a full-table paginated fetch of all records from HubSpot's CRM API. This works but means changes in HubSpot can take hours to appear.

HubSpot's Webhooks API (v3) can push events in near-real-time when CRM records are created, updated, or deleted. Webhooks require a HubSpot App (not just a private app token) — the app's client secret is used for HMAC signature verification.

The existing `HubSpotService._sync_company()` and `_sync_product()` methods already handle upserting individual records and can be reused for webhook event processing.

## Goals / Non-Goals

**Goals:**
- Receive and process HubSpot webhook events for companies, products, and deals in near-real-time
- Verify webhook authenticity using HMAC signature validation
- Reuse existing `HubSpotService` sync methods for processing individual records
- Let tenants choose between polling (6h cycle) and webhooks
- Keep polling as fallback — webhook mode doesn't remove the ability to manually sync

**Non-Goals:**
- Managing HubSpot webhook subscriptions programmatically (admin configures subscriptions in HubSpot's developer portal manually)
- Supporting webhook events beyond CRM objects (no workflow events, no conversation events)
- Real-time UI updates via WebSocket push — the webhook updates the DB; the user sees changes on next page load/refetch

## Decisions

### 1. Multi-tenant webhook routing via portal ID

HubSpot webhook payloads include `portalId` (the HubSpot account ID). We store the portal ID on the tenant's `hubspot_config` and use it to route incoming events to the correct tenant.

**Why not one endpoint per tenant?** A single `/api/hubspot/webhook/` endpoint is simpler — no per-tenant URL management. The portal ID in the payload is the natural tenant discriminator.

**Alternative considered:** URL-based routing with a tenant identifier in the path. Rejected because it leaks tenant info in the URL and adds URL management complexity.

### 2. Signature verification using HubSpot App client secret

HubSpot signs webhook payloads with `X-HubSpot-Signature` (v1: SHA-256 of `clientSecret + requestBody`). We verify this before processing any event.

Each tenant stores their HubSpot App's `client_secret` in `hubspot_config`. The webhook endpoint looks up the tenant by `portalId`, retrieves the secret, and verifies the signature.

**Why store client secret per tenant?** Different tenants may use different HubSpot apps. Even if they share an app, the secret is tied to the app, not the account, so it makes sense at the tenant level.

### 3. Async processing via Celery

The webhook endpoint returns `200 OK` immediately after signature verification, then dispatches a Celery task to process the event. This keeps response times under HubSpot's 5-second timeout and prevents retries from stacking up.

**Why not process inline?** HubSpot retries on timeouts > 5s. Processing inline risks timeouts on slow DB operations or when HubSpot sends batches of up to 100 events.

### 4. Fetch-then-sync for create/update events

For `company.creation`, `company.propertyChange`, `product.*`, `deal.*` events: fetch the full record from HubSpot's CRM API, then pass it through the existing `_sync_company()` / `_sync_product()` methods. Don't try to apply partial property changes from the webhook payload.

**Why not apply the delta directly?** The webhook payload only contains the changed property, but `_sync_company()` needs the full property set (name, address, etc.). Fetching the full record is simpler, consistent, and handles cases where multiple properties change in quick succession.

**For deletion events:** Mark the customer/product as inactive (soft-delete). Set `hubspot_deleted_at` timestamp for customers. Don't hard-delete because contracts may reference them.

### 5. Sync mode toggle (polling vs webhooks)

Add a `sync_mode` field to `hubspot_config` with values `"polling"` (default) and `"webhooks"`. When `"webhooks"`:
- The 6h Celery beat task skips this tenant
- The webhook endpoint processes events for this tenant

When `"polling"`:
- The webhook endpoint still accepts and processes events (no harm in receiving them) but the primary sync mechanism is the scheduled task

This means switching modes is safe — there's no gap where data could be missed.

### 6. Single Django view endpoint

Add `api/hubspot/webhook/` as a new URL in `config/urls.py` pointing to a Django View. It's a simple POST handler, no need for DRF or GraphQL. Exempt from CSRF (external caller). No auth middleware — uses HMAC verification instead.

## Risks / Trade-offs

**[Event ordering not guaranteed]** → HubSpot doesn't guarantee delivery order. Mitigated by fetch-then-sync approach: we always fetch the latest state from HubSpot, so out-of-order events converge to the correct state.

**[Duplicate events]** → HubSpot may send the same event multiple times. Mitigated by the idempotent upsert logic in `_sync_company()` — processing the same event twice has no adverse effect.

**[Webhook endpoint must be public HTTPS]** → Already the case in production. No additional infrastructure needed. For local development, webhooks won't work (need ngrok or similar) — polling mode remains the dev workflow.

**[Client secret rotation]** → If a tenant regenerates their HubSpot app's client secret, webhooks fail until updated in settings. The polling fallback still works, and the UI should show webhook health status.

**[HubSpot App requirement]** → Webhooks require a HubSpot App (developer account), not just a private app token. This is a different setup than the current API key flow. Tenants using only a private app token continue using polling mode.

**[Portal ID must be stored]** → Tenants need to enter their HubSpot portal ID in settings. This is a one-time setup step. Could auto-detect from an API call using the existing token.

## Migration Plan

1. Add new fields to `hubspot_config` JSON: `portal_id`, `client_secret`, `sync_mode`, `webhook_last_received`
2. Add webhook endpoint — no migration needed, just URL routing
3. Add Celery task for async event processing
4. Update `sync_all_hubspot_tenants` to skip tenants with `sync_mode == "webhooks"`
5. Add settings UI section for webhook configuration
6. Deploy — existing tenants continue on polling. Opt-in to webhooks by configuring portal ID + client secret and switching mode.

**Rollback:** Switch tenant back to `sync_mode: "polling"`. No data loss — polling picks up where it left off on next 6h cycle.

## Open Questions

- Should we auto-detect the portal ID from the existing HubSpot API key (via `GET /account-info/v3/api-usage/daily`)? Would simplify setup.
- Do we need a webhook event log table for debugging, or is standard Django logging sufficient for now?

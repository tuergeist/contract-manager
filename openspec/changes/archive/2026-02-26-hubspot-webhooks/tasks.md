## 1. Backend: Webhook Endpoint

- [x] 1.1 Create `backend/apps/customers/webhooks.py` with `HubSpotWebhookView` Django View — accepts POST, parses JSON body, returns 200/401/405
- [x] 1.2 Implement HMAC signature verification: compute SHA-256 of `client_secret + request_body`, compare to `X-HubSpot-Signature` header
- [x] 1.3 Implement tenant lookup by `portalId` from the event payload — log warning and return 200 for unknown portal IDs
- [x] 1.4 Add URL route `api/hubspot/webhook/` in `config/urls.py` with `csrf_exempt`
- [x] 1.5 Write tests for webhook endpoint: valid signature, invalid signature, missing header, unknown portal, empty payload, non-POST methods

## 2. Backend: Event Processing Celery Task

- [x] 2.1 Create `process_hubspot_webhook_event` Celery task in `backend/apps/customers/tasks.py` — receives event dict and tenant ID
- [x] 2.2 Implement company event handling: `company.creation` / `company.propertyChange` → fetch full company from HubSpot CRM API, call `_sync_company()`; `company.deletion` → mark customer inactive
- [x] 2.3 Implement product event handling: `product.creation` / `product.propertyChange` → fetch full product, sync; `product.deletion` → mark inactive
- [x] 2.4 Implement deal event handling: `deal.creation` / `deal.propertyChange` → fetch full deal, run deal sync logic
- [x] 2.5 Add single-record fetch methods to `HubSpotService`: `fetch_company(hubspot_id)`, `fetch_product(hubspot_id)`, `fetch_deal(hubspot_id)` — return the CRM object or None on 404
- [x] 2.6 Add retry logic: retry up to 3 times with exponential backoff on 429/5xx from HubSpot API
- [x] 2.7 Ignore unsupported event types at DEBUG log level
- [x] 2.8 Write tests for event processing: company create/update/delete, product create/update/delete, unknown event type, HubSpot 404 on fetch, duplicate event idempotency

## 3. Backend: Polling Task Update

- [x] 3.1 Update `sync_all_hubspot_tenants` in `tasks.py` to skip tenants where `hubspot_config.sync_mode == "webhooks"`
- [x] 3.2 Write test: tenant with `sync_mode: "webhooks"` is skipped by periodic sync

## 4. Backend: GraphQL Schema

- [x] 4.1 Add `saveWebhookSettings` mutation — accepts `portalId`, `clientSecret`, `syncMode`; stores in `hubspot_config`; validates that portal ID and secret are set before allowing webhook mode
- [x] 4.2 Extend `hubspotSettings` query to return `portalId`, `clientSecretSet` (boolean), `syncMode`, `webhookLastReceived`
- [x] 4.3 Write tests for the new mutation: save settings, switch modes, validation errors

## 5. Frontend: Webhook Settings UI

- [x] 5.1 Add webhook settings section to HubSpot integration settings (in `IntegrationSettingsTabs` or `Settings.tsx` hubspot section) — portal ID input, client secret input (masked), sync mode radio/toggle
- [x] 5.2 Display the webhook endpoint URL with a copy button
- [x] 5.3 Show "Last webhook received" timestamp when available
- [x] 5.4 Disable webhook mode toggle when portal ID or client secret is missing
- [x] 5.5 Add translations for webhook settings in `en.json` and `de.json`

## 6. Verification

- [x] 6.1 Run `make test-back` — all tests pass
- [x] 6.2 Run `npx tsc --noEmit` in frontend — no type errors
- [x] 6.3 Manual test: configure webhook settings, send a test POST to `/api/hubspot/webhook/` with valid HMAC signature, verify event processed
- [x] 6.4 Manual test: switch sync mode to webhooks, verify 6h polling skips this tenant

## ADDED Requirements

### Requirement: Public webhook endpoint accepts HubSpot events

The system SHALL expose a public HTTP POST endpoint at `/api/hubspot/webhook/` that accepts webhook event payloads from HubSpot.

#### Scenario: Valid webhook request accepted
- **WHEN** HubSpot sends a POST request to `/api/hubspot/webhook/` with a valid `X-HubSpot-Signature` header
- **THEN** the system returns HTTP 200
- **AND** dispatches the event payload for async processing

#### Scenario: Missing signature header rejected
- **WHEN** a POST request arrives at `/api/hubspot/webhook/` without an `X-HubSpot-Signature` header
- **THEN** the system returns HTTP 401
- **AND** does not process the payload

#### Scenario: Invalid signature rejected
- **WHEN** a POST request arrives with an `X-HubSpot-Signature` header that does not match the computed HMAC
- **THEN** the system returns HTTP 401
- **AND** does not process the payload

#### Scenario: Non-POST methods rejected
- **WHEN** a GET, PUT, or DELETE request arrives at `/api/hubspot/webhook/`
- **THEN** the system returns HTTP 405

### Requirement: Signature verification uses tenant's client secret

The system SHALL verify webhook signatures by computing SHA-256 of `clientSecret + requestBody` and comparing it to the `X-HubSpot-Signature` header value.

#### Scenario: Signature verified against correct tenant
- **WHEN** a webhook payload contains `portalId` matching Tenant A's stored portal ID
- **THEN** the system uses Tenant A's `hubspot_config.client_secret` for HMAC verification

#### Scenario: Unknown portal ID rejected
- **WHEN** a webhook payload contains a `portalId` that matches no tenant
- **THEN** the system returns HTTP 200 (to prevent HubSpot retries)
- **AND** logs a warning
- **AND** does not process the event

#### Scenario: Tenant without client secret configured
- **WHEN** a webhook payload matches a tenant that has no `client_secret` in `hubspot_config`
- **THEN** the system returns HTTP 200
- **AND** logs a warning
- **AND** does not process the event

### Requirement: Endpoint handles batch payloads

HubSpot sends arrays of up to 100 events per request. The system SHALL accept and dispatch each event individually.

#### Scenario: Batch of events dispatched individually
- **WHEN** HubSpot sends a payload containing 5 events
- **THEN** the system dispatches 5 separate async tasks (one per event)
- **AND** returns HTTP 200 after all tasks are dispatched

#### Scenario: Empty payload handled gracefully
- **WHEN** HubSpot sends a payload with an empty array
- **THEN** the system returns HTTP 200
- **AND** dispatches no tasks

### Requirement: Endpoint is CSRF-exempt and unauthenticated

The webhook endpoint SHALL NOT require authentication tokens or CSRF tokens since it is called by HubSpot's servers, not by browser clients.

#### Scenario: No auth token required
- **WHEN** HubSpot sends a webhook request without an `Authorization` header
- **AND** the signature is valid
- **THEN** the system processes the request normally

#### Scenario: CSRF token not required
- **WHEN** HubSpot sends a POST request without a CSRF token
- **AND** the signature is valid
- **THEN** the system processes the request normally

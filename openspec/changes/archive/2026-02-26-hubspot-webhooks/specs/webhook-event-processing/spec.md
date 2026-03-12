## ADDED Requirements

### Requirement: Company events trigger customer sync

The system SHALL process HubSpot company webhook events by fetching the full company record from HubSpot and upserting the corresponding customer.

#### Scenario: Company created
- **WHEN** a `company.creation` event is received
- **THEN** the system fetches the company from HubSpot CRM API using the `objectId`
- **AND** creates or updates the local customer using existing sync logic
- **AND** applies company filter rules to determine active status

#### Scenario: Company property changed
- **WHEN** a `company.propertyChange` event is received
- **THEN** the system fetches the full company record from HubSpot
- **AND** updates the local customer with the latest properties

#### Scenario: Company deleted
- **WHEN** a `company.deletion` event is received
- **THEN** the system marks the corresponding customer as inactive
- **AND** sets `hubspot_deleted_at` to the event timestamp

#### Scenario: Company not found in HubSpot (deleted before fetch)
- **WHEN** processing a company event
- **AND** the HubSpot CRM API returns 404 for the `objectId`
- **THEN** the system marks the local customer as inactive if it exists
- **AND** logs a warning

### Requirement: Product events trigger product sync

The system SHALL process HubSpot product webhook events by fetching the full product record and upserting it.

#### Scenario: Product created
- **WHEN** a `product.creation` event is received
- **THEN** the system fetches the product from HubSpot CRM API
- **AND** creates or updates the local product using existing sync logic

#### Scenario: Product property changed
- **WHEN** a `product.propertyChange` event is received
- **THEN** the system fetches the full product record from HubSpot
- **AND** updates the local product

#### Scenario: Product deleted
- **WHEN** a `product.deletion` event is received
- **THEN** the system marks the corresponding product as inactive

### Requirement: Deal events trigger deal sync

The system SHALL process HubSpot deal webhook events by fetching the full deal record and running existing deal sync logic.

#### Scenario: Deal created
- **WHEN** a `deal.creation` event is received
- **THEN** the system fetches the deal from HubSpot CRM API
- **AND** processes it using existing deal sync logic (creates contract group if applicable)

#### Scenario: Deal property changed
- **WHEN** a `deal.propertyChange` event is received
- **THEN** the system fetches the full deal record from HubSpot
- **AND** updates the local deal data

### Requirement: Events are processed asynchronously via Celery

Each webhook event SHALL be processed in a Celery task to prevent blocking the webhook endpoint.

#### Scenario: Task dispatched per event
- **WHEN** the webhook endpoint receives a valid event
- **THEN** it dispatches a `process_hubspot_webhook_event` Celery task with the event data and tenant ID

#### Scenario: Task failure does not affect other events
- **WHEN** processing one event fails (e.g., HubSpot API timeout)
- **THEN** the failure is logged
- **AND** other events in the same batch are unaffected (each is a separate task)

#### Scenario: Task retries on transient failure
- **WHEN** fetching a record from HubSpot fails with a 429 or 5xx error
- **THEN** the Celery task retries up to 3 times with exponential backoff

### Requirement: Unsupported event types are ignored

The system SHALL silently ignore webhook events for object types it does not handle.

#### Scenario: Unknown event type
- **WHEN** a webhook event has `subscriptionType` of `contact.creation` or any non-handled type
- **THEN** the system logs at DEBUG level and takes no action
- **AND** does not raise an error

### Requirement: Idempotent processing

Processing the same event multiple times SHALL produce the same result as processing it once.

#### Scenario: Duplicate event processed
- **WHEN** HubSpot sends the same `company.propertyChange` event twice
- **THEN** the system fetches and upserts the company both times
- **AND** the final state is identical to processing it once

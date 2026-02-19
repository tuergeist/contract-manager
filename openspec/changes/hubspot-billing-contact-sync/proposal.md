## Why

Billing email addresses on customers are currently manually managed or transferred from imported invoices. HubSpot already tracks "Billing Contact" associations on companies — syncing these emails automatically eliminates manual data entry and keeps billing contacts in sync with the CRM as the source of truth.

## What Changes

- Add a HubSpot integration setting to configure which association label (typeId) identifies billing contacts (default: `930` = "Billing Contact")
- During company sync, for customers that have at least one active contract, fetch contacts with the configured billing contact association label via the HubSpot v4 associations API
- Retrieve the email addresses of those billing contacts and store them as the customer's `billing_emails`
- HubSpot-synced billing emails are authoritative: they replace the current list entirely during sync (not merged with manual edits)
- In the frontend, billing emails that were synced from HubSpot are displayed as read-only (not manually editable); manual add/remove is disabled when the customer has a HubSpot ID and billing contact sync is configured
- The HubSpot API token requires the `crm.objects.contacts.read` scope — surface a clear error if this scope is missing

## Capabilities

### New Capabilities
- `hubspot-billing-contact-sync`: Syncing billing contact emails from HubSpot company associations into customer billing_emails during company sync

### Modified Capabilities
- `customer-billing-contacts`: Billing emails become read-only on the frontend when sourced from HubSpot sync

## Impact

- **Backend**: `apps/customers/hubspot.py` — extend `sync_companies` / `_sync_company` to fetch v4 associations and contact emails; add setting for association label typeId
- **Backend**: `apps/customers/schema.py` — expose sync source info so frontend knows whether emails are HubSpot-managed
- **Frontend**: `CustomerDetail.tsx` — conditionally disable manual email editing when HubSpot-synced
- **Frontend**: Settings page — add association label configuration field
- **API scope**: HubSpot token needs `crm.objects.contacts.read` scope added

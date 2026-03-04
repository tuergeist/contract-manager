## Why

When a deal comes in from HubSpot as a draft contract and gets finalized by sales, activating the contract should offer to send an order confirmation (Auftragsbestätigung / AB) to the customer. Currently there's no mechanism for this — users must manually create and send order confirmations outside the system.

## What Changes

- Add an order confirmation (AB) prompt during the contract activation flow (draft → active)
- AB includes a preview step so the user can review and go back to make changes
- User can add a personal message and additional email addresses before sending
- If skipped during activation, a "Send AB" button appears on the active contract
- Track AB send date and display it on the contract dashboard
- AB detail view (similar to invoice detail view) showing full AB content
- AB is sent to the billing contact + optional additional addresses (user input)

## Capabilities

### New Capabilities

- `order-confirmation`: Order confirmation document model, HTML rendering/preview, PDF generation, email sending via existing M365 integration, tracking fields on contract

### Modified Capabilities

- `activation-checklist`: Activation flow extended with optional AB prompt after successful checklist validation
- `email-sending`: Reuse existing M365 email infrastructure for AB delivery (new template, same send mechanism)

## Impact

- **Backend**: New `OrderConfirmation` model linked to Contract, new fields on Contract (`order_confirmation_sent_at`, `order_confirmation_id`), new Celery task for sending AB email, new HTML template for AB document, new GraphQL mutations/queries
- **Frontend**: Activation dialog extended with AB step (preview + message + additional emails), contract detail page gets "Send AB" button and sent date display, new AB detail view page
- **Infrastructure**: No new dependencies — reuses existing M365 connection and email sending
- **No breaking changes** to existing functionality

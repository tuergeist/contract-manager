## Why

When contracts are created from HubSpot won deals, they start as drafts. Activating them currently just flips the status, but in practice the user also needs to send an order confirmation (Auftragsbestätigung/AB) to the customer and optionally set up time tracking projects. Requiring manual follow-up steps after activation is error-prone and slows down the process. An activation workflow modal consolidates these steps into a single guided action.

## What Changes

- Replace the simple "Activate" confirmation dialog with a multi-step activation workflow modal
- Add an order confirmation (AB) document generation and email sending capability, modeled after the existing invoice PDF/email pipeline
- The modal presents checkboxes before activation:
  - "Send order confirmation?" (default: yes) — generates an AB PDF from a template and emails it to the customer's billing addresses
  - Time tracking project creation options (deferred to a later change)
- On confirm: activate the contract, then trigger the selected post-activation actions
- AB document uses the customer's `invoice_language` for localization (DE/EN), similar to invoice PDFs
- AB email sending reuses the M365 email infrastructure from invoice sending

## Capabilities

### New Capabilities
- `order-confirmation`: Generation of order confirmation (Auftragsbestätigung) PDFs from contract data, with a configurable template (accent color, logo, header/footer text) analogous to invoice templates. Includes email dispatch via M365 to customer billing addresses.
- `activation-workflow`: The activation modal UI that replaces the simple confirm dialog. Presents activation options (send AB, future: create time tracking projects), validates activation checklist, and orchestrates the activation + post-actions.

### Modified Capabilities
- `activation-checklist`: The checklist validation is now embedded within the new activation workflow modal instead of the old confirm dialog. Behavior unchanged, just relocated.

## Impact

- **Frontend**: `ContractDetail.tsx` status transition logic for `draft → active` changes from a simple confirm dialog to the new activation workflow modal
- **Backend**: New `OrderConfirmation` model, PDF generation (similar to invoice PDF pipeline), GraphQL mutations for generating and sending AB documents
- **Settings**: New "Order Confirmation" template settings section (analogous to invoice template settings) — accent color, logo, header/footer, email template
- **Email**: Reuses existing M365 email sending infrastructure, new Celery task for AB email dispatch
- **Dependencies**: Same as invoice PDF generation (WeasyPrint/PDF libraries already in use)

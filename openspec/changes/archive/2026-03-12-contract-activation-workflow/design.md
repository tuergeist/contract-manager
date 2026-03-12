## Context

Contract activation currently uses a simple confirm dialog (`StatusTransitionModal` in `ContractForm.tsx`). The dialog shows activation checklist warnings if required fields are missing, and on confirm calls `transition_contract_status`. There are no post-activation actions — no order confirmation document, no automated setup of external systems.

The invoice pipeline provides a proven pattern: WeasyPrint HTML→PDF generation, Django FileField storage, Celery tasks for async PDF generation and M365 email dispatch. The M365 `send_mail()` helper is generic and reusable beyond invoices.

## Goals / Non-Goals

**Goals:**
- Replace the activate confirm dialog with a workflow modal that presents post-activation options
- Generate order confirmation (AB) PDFs from contract data using the existing WeasyPrint pipeline
- Send AB documents via email using the existing M365 infrastructure
- Support DE/EN localization for AB documents based on customer's `invoice_language`
- Allow tenant-level AB template configuration (logo, colors, text) in Settings

**Non-Goals:**
- Time tracking / Clockodo integration (deferred to a separate change)
- Changing the activation checklist logic (behavior unchanged, just relocated into the new modal)
- AB for non-draft→active transitions (only draft→active gets the workflow modal)
- Credit notes or cancellation documents
- AB approval workflow (the AB is sent immediately on activation, no draft state)

## Decisions

### 1. New `OrderConfirmation` model vs. field on Contract

**Decision**: New `OrderConfirmation` model in `apps/contracts/`.

**Rationale**: An order confirmation is a distinct document with its own lifecycle (generated, sent, etc.). Storing it as a separate model allows tracking `pdf_file`, `sent_at`, `sent_to` independently — same pattern as `InvoiceRecord`. Putting a FileField on Contract would mix concerns and make it hard to track email delivery status.

```
OrderConfirmation:
  - contract (FK, unique — one AB per contract)
  - pdf_file (FileField)
  - generated_at (DateTimeField)
  - email_sent_at (DateTimeField, nullable)
  - email_sent_to (JSONField, list of emails)
  - email_message_id (CharField, nullable)
  - language (CharField — de/en, captured at generation time)
  - created_by (FK User)
```

**Alternative considered**: FileField on Contract — simpler but no email tracking, no generation timestamp, mixes document concerns with contract data.

### 2. PDF generation approach

**Decision**: Dedicated HTML template `order_confirmation.html` rendered via WeasyPrint, same as invoices.

**Rationale**: Reuses the proven pipeline. The AB document structure is different from an invoice (no line-item pricing table needed, instead: contract summary, items list, start date, billing info). A separate template is cleaner than conditional logic in the invoice template.

**Content of the AB PDF**:
- Company header (from tenant company data + logo)
- Customer address block
- "Auftragsbestätigung" / "Order Confirmation" title with AB number
- Contract reference (name, SO number, PO number)
- Contract items table (product, description, quantity — no prices unless we decide otherwise)
- Contract dates (start, end/indefinite, billing interval)
- Footer text (configurable per tenant)
- Tenant legal footer (same as invoices)

### 3. AB template settings storage

**Decision**: Store in `tenant.settings` JSONField under `order_confirmation_template` key, same pattern as invoice templates.

```json
{
  "order_confirmation_template": {
    "header_text": "...",
    "footer_text": "...",
    "show_prices": false
  },
  "order_confirmation_email_templates": {
    "de": { "subject": "...", "body": "..." },
    "en": { "subject": "...", "body": "..." }
  }
}
```

**Rationale**: No migration needed. Invoice template settings (accent color, logo) are already tenant-level and reused — AB shares the same logo/accent color. Only AB-specific text (header, footer, email template) needs separate config. The `show_prices` flag allows tenants to choose whether to include pricing in the AB.

### 4. Activation workflow modal design

**Decision**: Replace `StatusTransitionModal` content for `draft→active` with a new `ActivationWorkflowModal` component.

**Flow**:
1. User clicks "Activate" → modal opens
2. Modal shows activation checklist warnings (if any required fields missing → activate button disabled, same as today)
3. Below the checklist section, show options:
   - ☑ Send order confirmation (default checked, disabled if no M365 configured or no billing emails)
   - ☐ Time tracking options (greyed out / "coming soon", or hidden entirely for now)
4. User clicks "Activate" → mutation fires
5. On success: if "send AB" was checked, trigger AB generation + email in the backend

**Alternative considered**: Multi-step wizard — rejected as over-engineered for 1-2 checkboxes. A single modal with options is simpler and faster.

### 5. Backend orchestration

**Decision**: The `transition_contract_status` mutation gets an optional `activation_options` input for the `draft→active` case.

```graphql
input ActivationOptionsInput {
  sendOrderConfirmation: Boolean = true
}

mutation TransitionContractStatus(
  $contractId: Int!
  $newStatus: String!
  $activationOptions: ActivationOptionsInput
)
```

**Flow**:
1. Mutation validates checklist (existing logic)
2. Transitions status to active
3. If `sendOrderConfirmation` is true:
   - Creates `OrderConfirmation` record
   - Fires `generate_order_confirmation_task.delay(order_confirmation_id)`
4. Celery task generates PDF, then if M365 is configured + customer has billing emails, sends the email automatically

**Rationale**: Keeping the orchestration in the existing mutation avoids a second round-trip. The Celery task handles the slow work (PDF generation, email) asynchronously. This mirrors how invoice generation works: mutation creates the record, Celery generates the PDF and sends email.

### 6. AB number format

**Decision**: Reuse the contract's existing `order_confirmation_number` field as the AB document number.

**Rationale**: The field already exists on Contract and ContractItem models and is displayed on invoice PDFs. The AB document simply references this same number. If the field is empty, the AB uses the contract name or a generated reference instead.

## Risks / Trade-offs

- **M365 not configured**: If M365 isn't set up, the "Send AB" checkbox is shown but disabled with a hint. The AB PDF is still generated and stored, just not emailed. → User can download it manually.
- **No billing emails on customer**: Same handling — checkbox disabled with explanation. PDF still generated.
- **PDF generation failure**: Celery task retries once (same as invoice PDF). If it fails, the `OrderConfirmation` record exists without a `pdf_file` — frontend can show a "retry" button.
- **Template not configured**: Falls back to sensible defaults (same approach as invoice email templates). The AB PDF always works with defaults; only email text is customizable.
- **AB already exists for contract**: The `OrderConfirmation` has a unique constraint on `contract`. Re-activating a contract (paused→active) does NOT trigger the AB workflow — only `draft→active` does.

## Open Questions

- Should the AB PDF include line item prices or just product/quantity? (Proposed: configurable via `show_prices` setting, default off)
- Should there be a "Preview AB" button in the modal before sending? (Proposed: not for v1, add later if requested)

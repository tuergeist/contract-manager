## Architecture

### Order Confirmation Model

New `OrderConfirmation` model in `apps/contracts/`:

```
OrderConfirmation
├── id (UUID)
├── tenant (FK → Tenant)
├── contract (FK → Contract, related_name="order_confirmations")
├── created_by (FK → User)
├── created_at (DateTimeField)
├── sent_at (DateTimeField, nullable)
├── sent_to (JSONField — list of email addresses)
├── email_message_id (CharField — Graph API message ID)
├── additional_emails (JSONField — extra recipients from user input)
├── personal_message (TextField — optional message from user)
├── pdf_file (FileField — generated AB PDF, nullable)
├── language (CharField — de/en, inherited from customer)
└── status (CharField — draft/sent)
```

### Activation Flow (Extended)

```
User clicks "Activate"
  → Activation checklist validation (existing)
  → If valid: show AB prompt dialog
    → Option A: "Send AB now"
      → Show AB preview (HTML, like invoice preview)
      → User adds personal message + additional emails
      → User confirms → Contract activated + AB sent
    → Option B: "Skip / Send later"
      → Contract activated without AB
      → "Send AB" button shown on contract detail
```

### AB Document Content

The order confirmation document includes:
- Company header with logo (same as invoice template)
- Customer billing address
- Contract reference number + order confirmation number
- Contract start date, end date (if applicable)
- Line items table (from contract items): position, description, quantity, unit, unit price, amount
- Total (net, VAT, gross)
- Personal message (if provided)
- Legal footer (from tenant settings)

### Email Sending

Reuses the existing M365 email infrastructure:
- Same `send_email_via_graph` Celery task pattern as invoice sending
- New email template for AB (subject: "Auftragsbestätigung {number}" / "Order Confirmation {number}")
- Recipients: customer `billing_emails` + `additional_emails` from user input
- Attachment: AB as PDF

### GraphQL API

**New Types:**
- `OrderConfirmationType` — full AB details

**New Queries:**
- `orderConfirmation(id: ID!)` — single AB detail
- Extend `ContractType` with `orderConfirmations` field

**New Mutations:**
- `createOrderConfirmation(contractId: ID!, personalMessage: String, additionalEmails: [String!])` — creates draft AB
- `sendOrderConfirmation(orderConfirmationId: ID!)` — sends AB via email
- `previewOrderConfirmation(contractId: ID!)` — returns rendered HTML for preview (no persistence)

### Frontend Components

1. **ActivationDialog extension** — after checklist passes, show AB step:
   - Preview panel (rendered HTML)
   - Personal message textarea
   - Additional emails input (tag-style, multiple)
   - "Send & Activate" / "Skip & Activate" buttons

2. **Contract detail** — when active + no AB sent:
   - "Send AB" button (opens same preview/message dialog)
   - When AB sent: show `sent_at` date, clickable to AB detail view

3. **AB Detail View** — `/contracts/:id/order-confirmation/:abId`
   - Full rendered AB (like invoice detail view)
   - Send metadata (date, recipients)

### Dashboard Integration

- Contract list/dashboard shows AB sent date column (or icon)
- Clicking the date opens the AB detail view

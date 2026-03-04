## Tasks

### Backend

- [ ] **B1: OrderConfirmation model** — Create model with fields: tenant, contract (FK), created_by, created_at, sent_at, sent_to (JSON), email_message_id, additional_emails (JSON), personal_message, include_message_in_pdf (bool), include_message_in_email (bool), pdf_file, language, status, order_confirmation_number. Add migration.
- [ ] **B1b: AB number scheme** — Create `OrderConfirmationNumberScheme` model (pattern, next_counter, reset_period) mirroring `InvoiceNumberScheme`. Auto-generate AB number on creation. Default pattern: "AB-{YYYY}-{NNNN}".
- [ ] **B2: AB HTML template** — Create `order_confirmation.html` template mirroring invoice template structure (company header, customer address, contract items table, totals, personal message, footer). Support de/en.
- [ ] **B3: AB PDF generation** — Reuse invoice PDF pipeline (WeasyPrint) to render AB HTML to PDF. Store on OrderConfirmation.pdf_file.
- [ ] **B4: AB email sending task** — New Celery task `send_order_confirmation_email` using existing M365 Graph API integration. Attach PDF. Send to billing_emails + additional_emails. Use configured AB email template.
- [ ] **B4b: AB email template settings** — Add `ab_email_templates` to tenant settings (de/en). Support placeholders: `{order_confirmation_number}`, `{customer_name}`, `{contract_reference}`, `{personal_message}`. Provide sensible defaults.
- [ ] **B5: GraphQL mutations** — `createOrderConfirmation`, `sendOrderConfirmation`, `previewOrderConfirmationHtml` (returns rendered HTML string).
- [ ] **B6: GraphQL queries** — `orderConfirmation(id)` query. Extend `ContractType` with `orderConfirmations` field and `orderConfirmationSentAt` convenience field.
- [ ] **B7: Permissions** — AB operations require `contracts.write` permission.

### Frontend

- [ ] **F1: Activation dialog AB step** — After checklist validation, show AB prompt with preview panel, personal message textarea with "Include in PDF" / "Include in email" checkboxes, additional emails input, "Send & Activate" / "Skip & Activate" buttons.
- [ ] **F2: AB preview component** — Render AB HTML in an iframe/container (reuse invoice preview pattern).
- [ ] **F3: Contract detail "Send AB" button** — Show on active contracts without a sent AB. Opens same preview/message dialog.
- [ ] **F4: AB sent date on dashboard** — Display `orderConfirmationSentAt` column/badge on contract list. Clickable.
- [ ] **F5: AB detail view page** — New route `/contracts/:id/order-confirmation/:abId` showing rendered AB + send metadata.
- [ ] **F6: i18n** — Add de/en translations for all new UI strings.
- [ ] **F7: AB number scheme settings** — Add AB number scheme configuration to Settings page (pattern, reset period) mirroring invoice number scheme UI.
- [ ] **F8: AB email template editor** — Add AB email template editor in Email settings alongside invoice template editor.

### Infrastructure

- [ ] **I1: No new infra required** — Reuses existing M365 connection and object storage.

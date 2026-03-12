## ADDED Requirements

### Requirement: Order confirmation model
The system SHALL store order confirmations as `OrderConfirmation` records linked to a contract (one-to-one). Each record SHALL track: `contract` (FK, unique), `pdf_file` (FileField), `generated_at`, `email_sent_at`, `email_sent_to` (list), `email_message_id`, `language` (de/en), and `created_by` (FK User).

#### Scenario: Order confirmation created on activation
- **WHEN** a contract is activated with `sendOrderConfirmation: true`
- **THEN** an `OrderConfirmation` record is created linked to the contract
- **AND** `generated_at` is set to the current timestamp
- **AND** `language` is set to the customer's `invoice_language` (defaulting to "de")

#### Scenario: One confirmation per contract
- **WHEN** an `OrderConfirmation` already exists for a contract
- **THEN** attempting to create another SHALL raise a unique constraint error

### Requirement: PDF generation
The system SHALL generate order confirmation PDFs using WeasyPrint from an HTML template (`order_confirmation.html`). The PDF SHALL contain: company header (logo, name, address from tenant company data), customer address, document title ("Auftragsbestätigung" / "Order Confirmation"), the contract's `order_confirmation_number` (or contract name if absent), contract reference info (SO number, PO number), a table of contract items (product name, description, quantity), contract dates (start date, end date or "indefinite", billing interval), configurable footer text, and the tenant legal footer.

#### Scenario: PDF generated in German
- **WHEN** the customer's `invoice_language` is "de" or unset
- **THEN** the PDF title SHALL be "Auftragsbestätigung"
- **AND** all labels SHALL be in German

#### Scenario: PDF generated in English
- **WHEN** the customer's `invoice_language` is "en"
- **THEN** the PDF title SHALL be "Order Confirmation"
- **AND** all labels SHALL be in English

#### Scenario: Prices shown when configured
- **WHEN** tenant setting `order_confirmation_template.show_prices` is true
- **THEN** the items table SHALL include unit price and total columns

#### Scenario: Prices hidden by default
- **WHEN** tenant setting `order_confirmation_template.show_prices` is absent or false
- **THEN** the items table SHALL show only product, description, and quantity

#### Scenario: AB number absent
- **WHEN** the contract has no `order_confirmation_number`
- **THEN** the PDF SHALL use the contract name as the document reference

### Requirement: Async PDF generation
PDF generation SHALL run as a Celery task (`generate_order_confirmation_pdf_task`). The task SHALL retry once on failure with a 10-second backoff. The task SHALL be idempotent — if `pdf_file` is already set, it SHALL skip generation.

#### Scenario: Successful async generation
- **WHEN** `generate_order_confirmation_pdf_task` runs for an OrderConfirmation without a pdf_file
- **THEN** the PDF is generated and saved to the `pdf_file` field

#### Scenario: Task is idempotent
- **WHEN** `generate_order_confirmation_pdf_task` runs for an OrderConfirmation that already has a pdf_file
- **THEN** the task completes without regenerating the PDF

### Requirement: Email dispatch
The system SHALL send the AB PDF via email using the existing M365 infrastructure. Email dispatch SHALL run as a Celery task (`send_order_confirmation_email_task`) triggered after successful PDF generation. The email SHALL use a configurable template from `tenant.settings["order_confirmation_email_templates"][language]` with fallback to hardcoded defaults.

#### Scenario: Email sent successfully
- **WHEN** PDF generation completes and M365 is configured and customer has billing emails
- **THEN** the email is sent to all customer billing email addresses
- **AND** `email_sent_at`, `email_sent_to`, and `email_message_id` are recorded on the OrderConfirmation

#### Scenario: M365 not configured
- **WHEN** M365 is not configured in tenant settings
- **THEN** the email task SHALL skip sending without error
- **AND** the PDF remains available for manual download

#### Scenario: No billing emails
- **WHEN** the customer has no billing email addresses
- **THEN** the email task SHALL skip sending without error

#### Scenario: Default email template
- **WHEN** no custom AB email template is configured for the language
- **THEN** the system SHALL use a hardcoded default (subject: "Auftragsbestätigung {contract_name}" / "Order Confirmation {contract_name}", body: standard confirmation text)

### Requirement: Template settings
Tenant admins SHALL be able to configure AB-specific settings in the Settings page: `header_text`, `footer_text`, `show_prices` (boolean). The AB PDF SHALL reuse the tenant's invoice logo and accent color. Email templates (subject + body per language) SHALL be configurable separately from invoice email templates.

#### Scenario: Custom footer text
- **WHEN** tenant has `order_confirmation_template.footer_text` set
- **THEN** the AB PDF SHALL display this text in the footer area

#### Scenario: Shared visual identity
- **WHEN** an AB PDF is generated
- **THEN** it SHALL use the same logo and accent color as configured for invoices

### Requirement: GraphQL API
The system SHALL expose: a query to fetch the OrderConfirmation for a contract, a mutation to regenerate the PDF (if generation failed), and the `pdf_url` field for downloading. The OrderConfirmation SHALL be accessible via the contract detail query.

#### Scenario: Fetch order confirmation for contract
- **WHEN** querying a contract that has an OrderConfirmation
- **THEN** the response SHALL include `orderConfirmation { id, pdfUrl, generatedAt, emailSentAt, emailSentTo }`

#### Scenario: Contract without order confirmation
- **WHEN** querying a contract that has no OrderConfirmation
- **THEN** `orderConfirmation` SHALL be null

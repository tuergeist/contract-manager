## ADDED Requirements

### Requirement: Prompt AB during contract activation
When a contract transitions from draft to active and M365 email is configured, the system SHALL prompt the user to send an order confirmation (Auftragsbestätigung). The user can send immediately or skip.

#### Scenario: Activation shows AB prompt when M365 configured
- **WHEN** user activates a draft contract and M365 email is configured for the tenant
- **THEN** after activation checklist passes, an AB dialog appears with preview, personal message input, additional emails input, and "Send & Activate" / "Skip & Activate" buttons

#### Scenario: Activation skips AB prompt when M365 not configured
- **WHEN** user activates a draft contract and M365 email is not configured
- **THEN** the contract activates directly without showing the AB prompt

#### Scenario: User sends AB during activation
- **WHEN** user clicks "Send & Activate" in the AB dialog
- **THEN** the contract transitions to active AND an OrderConfirmation is created and sent

#### Scenario: User skips AB during activation
- **WHEN** user clicks "Skip & Activate" in the AB dialog
- **THEN** the contract transitions to active without creating an OrderConfirmation

### Requirement: AB preview before sending
The system SHALL display a rendered HTML preview of the order confirmation before sending, allowing the user to review and go back to make changes.

#### Scenario: Preview shows full AB content
- **WHEN** the AB dialog is open
- **THEN** a rendered HTML preview is displayed showing company header, customer address, contract items, totals, and personal message

#### Scenario: User can go back from preview
- **WHEN** the user reviews the preview and notices incorrect data
- **THEN** the user can close the dialog, edit the contract, and retry activation

### Requirement: AB numbering scheme
The system SHALL provide a configurable order confirmation number scheme in tenant settings, following the same pattern as InvoiceNumberScheme (pattern with placeholders like `{YYYY}`, `{NNNN}`, reset period). Each AB receives an auto-generated number on creation.

#### Scenario: Admin configures AB number pattern
- **WHEN** a tenant admin sets the AB number pattern to "AB-{YYYY}-{NNNN}" with yearly reset
- **THEN** the next order confirmation receives number "AB-2026-0001"

#### Scenario: AB number auto-increments
- **GIVEN** the last AB number was "AB-2026-0003"
- **WHEN** a new AB is created
- **THEN** it receives number "AB-2026-0004"

#### Scenario: Default AB number pattern
- **WHEN** no AB number scheme is configured for a tenant
- **THEN** the system uses default pattern "AB-{YYYY}-{NNNN}" with yearly reset

### Requirement: Personal message and additional recipients
The user SHALL be able to enter an optional personal message and additional email addresses before sending the AB. The personal message SHALL optionally be included in the PDF document and/or the email body, controlled by checkboxes. These are stored on the OrderConfirmation record.

#### Scenario: AB with personal message in both PDF and email
- **GIVEN** a customer with billing_emails ["billing@acme.com"]
- **WHEN** user enters personal message "Welcome aboard", checks "Include in PDF" and "Include in email", and adds additional emails ["cfo@acme.com"]
- **THEN** the AB PDF contains the personal message, the email body contains the personal message, and it is sent to billing@acme.com and cfo@acme.com

#### Scenario: AB with personal message in email only
- **WHEN** user enters a personal message and checks only "Include in email"
- **THEN** the AB PDF does not contain the personal message, but the email body does

#### Scenario: AB with personal message in PDF only
- **WHEN** user enters a personal message and checks only "Include in PDF"
- **THEN** the AB PDF contains the personal message, but the email body does not

#### Scenario: AB without optional fields
- **WHEN** user sends AB without personal message or additional emails
- **THEN** the AB is sent only to billing_emails without a personal message section

### Requirement: Deferred AB sending
If the user skips AB during activation, the active contract SHALL display a "Send AB" button that opens the same preview/message flow.

#### Scenario: Send AB button on active contract without AB
- **WHEN** an active contract has no sent order confirmation
- **THEN** a "Send AB" button is displayed on the contract detail page

#### Scenario: Send AB button hidden after AB sent
- **WHEN** an active contract has a sent order confirmation
- **THEN** the "Send AB" button is not displayed

#### Scenario: Deferred send opens same dialog
- **WHEN** user clicks "Send AB" on an active contract
- **THEN** the AB preview/message dialog opens with the same flow as during activation

### Requirement: AB send tracking and dashboard display
The system SHALL track sent_at, sent_to, and email_message_id on the OrderConfirmation. The sent date SHALL be displayed on the contract dashboard.

#### Scenario: Sent date shown on dashboard
- **WHEN** a contract has a sent order confirmation
- **THEN** the AB sent date is displayed on the contract dashboard/list

#### Scenario: Clicking sent date opens AB detail
- **WHEN** user clicks the AB sent date on the dashboard
- **THEN** the AB detail view opens

#### Scenario: No date shown when AB not sent
- **WHEN** a contract has no sent order confirmation
- **THEN** no AB sent date is displayed

### Requirement: AB detail view
A detail view SHALL display the full rendered order confirmation and send metadata, similar to the invoice detail view.

#### Scenario: AB detail view content
- **WHEN** user opens the AB detail view
- **THEN** the full rendered AB is displayed along with sent date, recipient list, and personal message

### Requirement: AB document content
The order confirmation SHALL include: company header with logo, customer billing address, contract reference and order confirmation number, contract dates, line items with quantities/prices, net/VAT/gross totals, personal message (if provided), and legal footer.

#### Scenario: AB includes all contract data
- **WHEN** an AB is generated for a contract with 3 line items
- **THEN** the AB shows all 3 line items with correct quantities, unit prices, and amounts, plus totals

#### Scenario: AB uses customer language
- **GIVEN** a customer with invoice_language "en"
- **WHEN** an AB is generated
- **THEN** labels and email subject are in English ("Order Confirmation")
- **GIVEN** a customer with no invoice_language
- **THEN** AB defaults to German ("Auftragsbestätigung")

### Requirement: AB email template settings
The system SHALL allow tenant administrators to configure custom email subject and body templates for order confirmations per language (DE, EN), stored in `tenant.settings.ab_email_templates`. Templates SHALL support `{placeholder}` syntax with placeholders like `{order_confirmation_number}`, `{customer_name}`, `{contract_reference}`, `{personal_message}`. If no custom template is configured, a sensible default SHALL be used.

#### Scenario: Admin configures German AB email template
- **WHEN** admin saves a German AB email template with subject "Auftragsbestätigung {order_confirmation_number}" and a custom body
- **THEN** system stores it under `tenant.settings.ab_email_templates.de`

#### Scenario: Admin configures English AB email template
- **WHEN** admin saves an English AB email template
- **THEN** system stores it under `tenant.settings.ab_email_templates.en`

#### Scenario: Default template used when none configured
- **WHEN** no custom AB email template exists for the customer's language
- **THEN** the system uses a built-in default template

#### Scenario: Template editor in settings
- **WHEN** admin opens the Email settings page
- **THEN** an AB email template editor is displayed alongside the invoice email template editor, with subject field, body textarea, placeholder reference, and live preview

### Requirement: AB email sending via M365
The system SHALL send the AB email via the existing M365 Graph API integration with the PDF attached, using the configured AB email template. Recipients are the customer's billing_emails plus any additional_emails.

#### Scenario: Successful AB email send
- **WHEN** sendOrderConfirmation is called with a valid OrderConfirmation
- **THEN** a Celery task sends the email via Graph API with the AB PDF attached
- **AND** sent_at, sent_to, and email_message_id are populated

#### Scenario: Send fails gracefully
- **WHEN** the Graph API returns an error during AB send
- **THEN** the error is logged, sent_at remains null, and the user can retry

### Requirement: AB GraphQL API
The system SHALL expose mutations for creating, previewing (HTML), and sending an AB, a query for AB details, and extend the Contract type with an orderConfirmations field.

#### Scenario: Preview AB mutation
- **WHEN** user calls previewOrderConfirmationHtml(contractId) with contracts.write permission
- **THEN** system returns rendered HTML string of the AB

#### Scenario: Create and send AB mutation
- **WHEN** user calls createOrderConfirmation(contractId, personalMessage, additionalEmails)
- **THEN** an OrderConfirmation record is created in draft status
- **WHEN** user calls sendOrderConfirmation(orderConfirmationId)
- **THEN** the AB is sent and status changes to sent

#### Scenario: AB requires contracts.write permission
- **WHEN** a user without contracts.write calls any AB mutation
- **THEN** system returns a permission error

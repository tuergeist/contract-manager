## ADDED Requirements

### Requirement: Invoice email uses tenant-configured template

The `send_invoice_email_task` SHALL use the tenant's custom email template when available, falling back to the hardcoded default when no custom template is configured.

#### Scenario: Custom template configured for customer language
- **WHEN** the system sends an invoice email
- **AND** the customer's language is DE
- **AND** the tenant has a custom DE template in settings
- **THEN** the email subject and body SHALL be rendered from the custom template
- **AND** all placeholders SHALL be substituted with invoice data

#### Scenario: No custom template configured
- **WHEN** the system sends an invoice email
- **AND** the tenant has no custom template for the customer's language
- **THEN** the email subject and body SHALL be rendered from the hardcoded default template

#### Scenario: Custom template has rendering error
- **WHEN** the system sends an invoice email using a custom template
- **AND** rendering fails (e.g., invalid placeholder)
- **THEN** the system SHALL fall back to the hardcoded default template
- **AND** SHALL still send the email successfully
- **AND** SHALL log a warning about the template error

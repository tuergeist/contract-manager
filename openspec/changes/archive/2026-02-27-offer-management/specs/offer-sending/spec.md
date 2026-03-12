## Requirements

### Requirement: Send offer email with recipient selection

The system SHALL allow sending an offer PDF by email with the ability to add additional recipients before sending.

#### Scenario: Send dialog shows pre-filled recipients
- **WHEN** user clicks "Send" on an offer
- **THEN** a dialog SHALL appear with the customer's billing emails pre-filled as recipients
- **AND** the user SHALL be able to add additional email addresses
- **AND** the user SHALL be able to remove pre-filled addresses

#### Scenario: Send email with PDF attachment
- **WHEN** user confirms sending
- **THEN** the system SHALL send the email via M365 Graph API
- **AND** attach the offer PDF
- **AND** use an offer-specific email subject and body template
- **AND** update the offer: set `email_sent_at`, `email_sent_to` (all recipients), `email_message_id`
- **AND** transition status from `draft` to `sent`

#### Scenario: Send requires PDF
- **WHEN** an offer has no generated PDF
- **THEN** the "Send" action SHALL not be available

#### Scenario: Send requires M365 configuration
- **WHEN** the tenant has no M365 email configured
- **THEN** the "Send" action SHALL not be available
- **AND** a hint SHALL indicate that email configuration is required

#### Scenario: Email template
- **WHEN** an offer email is sent in German
- **THEN** the subject SHALL include the offer number (e.g., "Angebot {offer_number}")
- **WHEN** sent in English
- **THEN** the subject SHALL include the offer number (e.g., "Offer {offer_number}")

### Requirement: Offer numbering scheme configurable in settings

The system SHALL provide a settings UI for configuring the offer numbering pattern.

#### Scenario: Settings section for offer numbering
- **WHEN** user navigates to invoice/company settings
- **THEN** an "Offer Numbering" section SHALL be visible
- **AND** it SHALL allow configuring the pattern, reset period, and next counter
- **AND** it SHALL follow the same UI pattern as invoice and credit note numbering

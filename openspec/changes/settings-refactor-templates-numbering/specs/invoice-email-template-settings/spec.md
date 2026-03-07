## MODIFIED Requirements

### Requirement: Email template settings are accessible from settings
The system SHALL provide email template configuration in a dedicated "Email Templates" section within the application settings, separate from document-specific settings.

#### Scenario: Navigate to email template settings
- **WHEN** user navigates to Settings > Email Templates
- **THEN** system displays sub-tabs for Invoice Email and Order Confirmation Email templates

#### Scenario: Cross-link to numbering
- **WHEN** user views any email template settings tab
- **THEN** system displays an info link to the Numbering settings section

#### Scenario: Navigate to numbering settings
- **WHEN** user navigates to Settings > Numbering
- **THEN** system displays sub-tabs for Invoice, Credit Note, Offer, and Order Confirmation numbering schemes

#### Scenario: Cross-link to email templates
- **WHEN** user views any numbering settings tab
- **THEN** system displays an info link to the Email Templates settings section

#### Scenario: Navigate to document settings
- **WHEN** user navigates to Settings > Documents
- **THEN** system displays sub-tabs for Company Data, PDF Template, and Zugferd settings

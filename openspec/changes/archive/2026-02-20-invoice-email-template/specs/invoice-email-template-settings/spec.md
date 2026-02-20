## ADDED Requirements

### Requirement: Tenant can configure invoice email templates per language

The system SHALL allow tenant administrators to configure custom email subject and body templates for each supported language (DE, EN). Templates are stored in `tenant.settings.invoice_email_templates`.

#### Scenario: Save a custom German template
- **WHEN** admin sets subject to "Rechnung Nr. {invoice_number}" and body to custom HTML for language DE
- **THEN** system stores the template under `tenant.settings.invoice_email_templates.de`
- **AND** returns success

#### Scenario: Save a custom English template
- **WHEN** admin sets subject and body for language EN
- **THEN** system stores the template under `tenant.settings.invoice_email_templates.en`
- **AND** the DE template (if any) is not affected

#### Scenario: Retrieve current templates
- **WHEN** admin queries invoice email templates
- **AND** custom templates exist for DE but not EN
- **THEN** system returns the custom DE template
- **AND** returns the hardcoded default for EN

#### Scenario: Retrieve templates when none configured
- **WHEN** admin queries invoice email templates
- **AND** no custom templates have been saved
- **THEN** system returns the hardcoded defaults for both DE and EN

#### Scenario: Reset template to default
- **WHEN** admin saves an empty subject and body for language DE
- **THEN** system removes the custom DE template from settings
- **AND** subsequent queries return the hardcoded default for DE

### Requirement: Templates use placeholder syntax

The system SHALL support `{placeholder}` syntax in email templates with a fixed set of available placeholders.

#### Scenario: Available placeholders
- **WHEN** a template is rendered
- **THEN** the following placeholders SHALL be substituted: `{invoice_number}`, `{total_gross}`, `{currency}`, `{period_start}`, `{period_end}`, `{company_name}`

#### Scenario: Invalid placeholder in template
- **WHEN** a template contains an unrecognized placeholder (e.g., `{foo}`)
- **AND** the system attempts to render it for sending
- **THEN** the system SHALL fall back to the hardcoded default template for that language
- **AND** log a warning with the error details

### Requirement: Settings UI provides template editor with preview

The system SHALL display a template editor in the Email settings sub-tab with subject field, HTML body textarea, placeholder reference, and a live preview.

#### Scenario: Editor shows current templates
- **WHEN** admin navigates to Settings > Email
- **THEN** the template editor displays the current subject and body for the selected language
- **AND** a language selector allows switching between DE and EN

#### Scenario: Placeholder reference is visible
- **WHEN** admin views the template editor
- **THEN** available placeholders are listed as reference (e.g., badges or inline help)

#### Scenario: Live preview renders with sample data
- **WHEN** admin edits the subject or body
- **THEN** a preview panel renders the template with sample placeholder values
- **AND** the preview updates as the user types

#### Scenario: Permission required
- **WHEN** a user without `settings.write` permission views Settings > Email
- **THEN** the template editor fields are read-only

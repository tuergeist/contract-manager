## ADDED Requirements

### Requirement: User can upload reference invoice PDFs

The system SHALL allow users to upload one or more existing invoice PDF files as visual references for template configuration.

#### Scenario: Upload a reference PDF
- **WHEN** user navigates to `/settings/invoice-template`
- **AND** uploads a PDF file via the upload area
- **THEN** system stores the file and displays it in the reference list
- **AND** user can view/download the uploaded PDF

#### Scenario: Upload multiple reference PDFs
- **WHEN** user uploads additional PDF files
- **THEN** system stores all files and displays them in the reference list
- **AND** each file shows filename, upload date, and file size

#### Scenario: Delete a reference PDF
- **WHEN** user clicks delete on a reference PDF
- **THEN** system removes the file from storage and the reference list

#### Scenario: Reject invalid file types
- **WHEN** user attempts to upload a non-PDF file (e.g., .doc, .exe)
- **THEN** system rejects the upload with an error message
- **AND** only PDF files are accepted

#### Scenario: Enforce file size limit
- **WHEN** user attempts to upload a PDF larger than 20MB
- **THEN** system rejects the upload with a file size error message

### Requirement: User can configure invoice template settings

The system SHALL provide a settings form for configuring the invoice template appearance.

#### Scenario: Configure company logo
- **WHEN** user uploads a logo image (PNG, JPG, SVG) in the template settings
- **THEN** system stores the logo
- **AND** the logo appears on generated invoice PDFs in the header area
- **AND** logo file size MUST NOT exceed 5MB

#### Scenario: Configure accent color
- **WHEN** user selects an accent color via color picker
- **THEN** system stores the color value
- **AND** generated invoices use this color for headings, borders, and accents

#### Scenario: Configure header text
- **WHEN** user enters custom header text (e.g., tagline, subtitle)
- **THEN** system stores the text
- **AND** it appears below the company name in the invoice header

#### Scenario: Configure footer text
- **WHEN** user enters custom footer text (e.g., payment terms, notes)
- **THEN** system stores the text
- **AND** it appears at the bottom of each invoice page

#### Scenario: Default template when no configuration exists
- **WHEN** no template configuration has been saved
- **THEN** system uses default values: no logo, blue accent color (#2563eb), no header text, no footer text

### Requirement: User can preview the configured template

The system SHALL display a live preview of the invoice template with sample data.

#### Scenario: Preview with current settings
- **WHEN** user is on the template settings page
- **THEN** system displays a preview panel showing a sample invoice rendered with current template settings
- **AND** the preview updates when settings are changed

#### Scenario: Preview includes legal data
- **WHEN** company legal data has been configured
- **THEN** the preview shows legal fields (company name, address, tax IDs, register info) in their designated positions on the invoice

#### Scenario: Preview without legal data
- **WHEN** company legal data has NOT been configured
- **THEN** the preview shows placeholder text where legal fields would appear
- **AND** a warning indicates that legal data must be configured before generating real invoices

### Requirement: Template configuration is tenant-scoped

Each tenant SHALL have its own independent template configuration.

#### Scenario: Tenant isolation for templates
- **WHEN** Tenant A configures their invoice template
- **THEN** Tenant B's template is unaffected
- **AND** each tenant sees only their own template settings and reference PDFs

### Requirement: Template settings page requires authorization

The template settings page SHALL require appropriate permissions.

#### Scenario: Authorized access
- **WHEN** user with "settings.write" permission accesses `/settings/invoice-template`
- **THEN** system displays the template configuration page

#### Scenario: Unauthorized access
- **WHEN** user without "settings.write" permission accesses `/settings/invoice-template`
- **THEN** system denies access or hides the menu item

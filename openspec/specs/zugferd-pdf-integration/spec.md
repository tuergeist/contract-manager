## MODIFIED Requirements

### Requirement: ZUGFeRD generation handles missing optional data gracefully

#### Scenario: Generate without bank details
- **WHEN** `CompanyLegalData` has no bank details configured
- **THEN** ZUGFeRD PDF is still generated
- **AND** the payment means section is omitted from the XML
- **AND** no error is raised

#### Scenario: Generate without buyer address
- **WHEN** the customer has no address data
- **THEN** ZUGFeRD PDF is still generated
- **AND** the buyer address section contains only the customer name
- **AND** a validation warning is logged

#### Scenario: Generate without company legal data
- **WHEN** `CompanyLegalData` is not configured for the tenant
- **THEN** system SHALL raise an error
- **AND** SHALL not produce a ZUGFeRD PDF
- **AND** error message SHALL indicate that company legal data is required

#### Scenario: Generate with customer VAT ID
- **WHEN** a ZUGFeRD PDF is generated for a customer with `vat_id` set
- **THEN** the XML buyer section SHALL include a tax registration with type "VA" and the customer's VAT ID value

#### Scenario: Generate without customer VAT ID
- **WHEN** a ZUGFeRD PDF is generated for a customer without a VAT ID
- **THEN** the XML buyer section SHALL omit the tax registration element
- **AND** no error is raised

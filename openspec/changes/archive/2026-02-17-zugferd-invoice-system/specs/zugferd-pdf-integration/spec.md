## ADDED Requirements

### Requirement: System produces PDF/A-3b compliant invoices with embedded ZUGFeRD XML

The system SHALL generate PDF/A-3b documents containing the ZUGFeRD XML as an embedded attachment with correct metadata.

#### Scenario: Generate ZUGFeRD PDF from invoice
- **WHEN** user requests a ZUGFeRD PDF for a finalized invoice
- **THEN** system generates the visual PDF via WeasyPrint (as today)
- **AND** generates the ZUGFeRD EN 16931 XML
- **AND** embeds the XML as `factur-x.xml` attachment in the PDF
- **AND** outputs a PDF/A-3b compliant document

#### Scenario: PDF contains correct XMP metadata
- **WHEN** a ZUGFeRD PDF is generated
- **THEN** the PDF's XMP metadata SHALL declare:
  - `fx:DocumentType` = "INVOICE"
  - `fx:DocumentFileName` = "factur-x.xml"
  - `fx:Version` = "1.0"
  - `fx:ConformanceLevel` = "EN 16931"
- **AND** the PDF/A identification SHALL declare PDF/A-3b conformance

#### Scenario: PDF attachment has correct relationship
- **WHEN** the ZUGFeRD XML is embedded in the PDF
- **THEN** the attachment SHALL have relationship type "Data" (AFRelationship)
- **AND** the attachment filename SHALL be "factur-x.xml"
- **AND** the MIME type SHALL be "text/xml"

#### Scenario: Visual content is preserved
- **WHEN** a ZUGFeRD PDF is generated
- **THEN** the visual content (layout, fonts, colors, logo, legal footer) SHALL be identical to the regular PDF export
- **AND** the PDF SHALL be readable in any standard PDF viewer

#### Scenario: Fonts are fully embedded
- **WHEN** a ZUGFeRD PDF/A-3b is generated
- **THEN** all fonts used in the document SHALL be fully embedded
- **AND** no external font references SHALL remain

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

### Requirement: ZUGFeRD PDF can be generated for individual and batch exports

#### Scenario: Single ZUGFeRD PDF
- **WHEN** user exports a single invoice as ZUGFeRD
- **THEN** system returns a single PDF/A-3b file with embedded XML

#### Scenario: Batch ZUGFeRD PDFs as ZIP
- **WHEN** user exports multiple invoices as individual ZUGFeRD PDFs
- **THEN** system returns a ZIP containing one PDF/A-3b per invoice
- **AND** each PDF has its own embedded `factur-x.xml`
- **AND** each PDF filename follows the pattern `invoice-{customer}-{contract}-YYYY-MM.pdf`

#### Scenario: Combined ZUGFeRD PDF (multiple invoices)
- **WHEN** user exports multiple invoices as a single combined PDF
- **THEN** system SHALL NOT embed ZUGFeRD XML (a combined PDF with multiple invoices cannot be a valid ZUGFeRD document)
- **AND** system SHALL fall back to regular PDF/A-3b without XML
- **AND** system SHALL inform the user that ZUGFeRD requires individual PDFs

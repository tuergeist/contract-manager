## Why

Starting January 1, 2025, all B2B invoices in Germany must be receivable in structured electronic format per the Wachstumschancengesetz (Growth Opportunities Act). From January 1, 2027, companies above EUR 800k revenue must also *send* e-invoices. ZUGFeRD 2.x / Factur-X is the most widely adopted hybrid format — it embeds machine-readable UN/CEFACT CII XML inside a human-readable PDF/A-3 document, satisfying both the legal requirement and the practical need for a visual invoice.

The contract manager already generates legally compliant German invoices (UStG §14) as PDF via WeasyPrint, with company legal data, sequential numbering, tax calculation, and line item snapshots. However, the current PDFs are plain PDF 1.7 — they contain no structured XML metadata and are not PDF/A compliant. To meet the upcoming e-invoicing mandate and enable automated processing by customers' ERP systems, the invoice output must be upgraded to ZUGFeRD EN 16931 (Comfort profile).

## What Changes

- **ZUGFeRD XML generation**: A new service generates UN/CEFACT Cross-Industry Invoice (CII) XML from existing `InvoiceRecord` / `InvoiceData` objects, conforming to the EN 16931 profile. The XML includes seller/buyer identification, invoice metadata, line items, tax breakdown, and payment information.
- **PDF/A-3 output**: The existing WeasyPrint PDF generation is upgraded to produce PDF/A-3b variant documents with the ZUGFeRD XML embedded as a `factur-x.xml` attachment and proper XMP/RDF metadata declaring ZUGFeRD conformance.
- **Updated invoice export**: The export endpoints (`/invoices/export/` and the GraphQL mutations) gain a new `zugferd` format option. The existing `pdf` format can optionally be upgraded to always produce ZUGFeRD output, controlled by a tenant-level setting.
- **Validation**: Generated XML is validated against the official EN 16931 XSD schemas before embedding.

## Capabilities

### New Capabilities
- `zugferd-xml-generation`: Generate UN/CEFACT CII XML (EN 16931 profile) from invoice data including seller/buyer info, line items, tax summary, and payment means
- `zugferd-pdf-integration`: Embed ZUGFeRD XML into PDF/A-3b documents with correct XMP/RDF metadata, attachment relationship, and conformance declaration

### Modified Capabilities
- `invoice-export`: Add ZUGFeRD PDF as an export format alongside existing PDF and Excel options; tenant-level setting to make ZUGFeRD the default PDF format

## Impact

- **Backend**: New `zugferd.py` service module for XML generation, updated `services.py` for PDF/A-3 rendering, new dependency on `drafthorse` (or `lxml` for manual XML generation)
- **Frontend**: New export format option "ZUGFeRD PDF" in the invoice export page; tenant setting toggle for default ZUGFeRD output
- **Database**: No new models required — uses existing `CompanyLegalData`, `InvoiceRecord`, `InvoiceData`, and `InvoiceTemplate`
- **Dependencies**: `drafthorse>=2.3` for ZUGFeRD XML generation and PDF attachment, WeasyPrint already present (need >=64.0 for `pdf_variant` and RDF metadata support, currently `>=62.0` — version bump required)
- **API**: Updated export endpoint with new format parameter; new GraphQL field on tenant settings for ZUGFeRD preference

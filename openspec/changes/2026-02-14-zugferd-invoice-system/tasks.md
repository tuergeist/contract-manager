## Tasks

### 1. Add `drafthorse` dependency and bump WeasyPrint version
- Add `drafthorse>=2.3` to `pyproject.toml` dependencies
- Bump `weasyprint>=62.0` to `weasyprint>=64.0`
- Update Docker image to include new dependency
- Verify both libraries install correctly in the container

### 2. Implement ZUGFeRD XML generation service
- Create `backend/apps/invoices/zugferd.py` with `ZugferdService` class
- Implement `generate_xml(invoice_record: InvoiceRecord) -> bytes` method using `drafthorse`
- Map `CompanyLegalData` fields to CII SellerTradeParty
- Map `Customer` data to CII BuyerTradeParty
- Map `line_items_snapshot` to CII IncludedSupplyChainTradeLineItem entries
- Map tax data to ApplicableTradeTax (single VAT breakdown)
- Map monetary totals to SpecifiedTradeSettlementHeaderMonetarySummation
- Map bank details to SpecifiedTradePaymentTerms (SEPA transfer)
- Include billing period (period_start / period_end)
- Include invoice note from invoice_text
- Add XSD validation with warning-level logging
- Write unit tests for XML generation with various data combinations

### 3. Implement `generate_xml_from_invoice_data()` for preview/on-demand invoices
- Add method that generates XML from `InvoiceData` dataclass (not persisted)
- Fetch current `CompanyLegalData` for seller information
- Use "PREVIEW" as invoice number
- Write tests

### 4. Implement ZUGFeRD PDF generation (XML embedding into PDF/A-3)
- Add `generate_zugferd_pdf()` method to `InvoiceService`
- Call existing `generate_pdf()` to get the visual PDF bytes
- Call `ZugferdService.generate_xml()` to get the CII XML
- Use `drafthorse.pdf.attach_xml()` to embed XML into PDF with correct metadata
- Verify output is PDF/A-3b compliant (basic checks)
- Handle edge cases: missing company data, missing customer address
- Write tests for PDF generation pipeline

### 5. Add `generate_individual_zugferd_pdfs()` for batch export
- Similar to existing `generate_individual_pdfs()` but produces ZUGFeRD PDFs
- Each invoice gets its own PDF/A-3 with individual `factur-x.xml`
- Package as ZIP
- Write tests

### 6. Update REST export endpoint
- Add `format=zugferd` and `format=zugferd-single` to `InvoiceExportView`
- `zugferd` format: returns ZIP of individual ZUGFeRD PDFs (uses finalized InvoiceRecords)
- `zugferd-single` format: returns single ZUGFeRD PDF for a specific invoice ID
- Validate that invoices are finalized before ZUGFeRD export
- Validate that company legal data exists
- Return appropriate error messages
- Write integration tests

### 7. Update GraphQL schema
- Add `zugferd_default` field to tenant settings (in `Tenant.settings` JSONField)
- Add `exportZugferdInvoices(year, month)` mutation
- Add `exportZugferdInvoice(invoiceId)` mutation
- Return download URLs or direct file content
- Write tests

### 8. Add tenant-level ZUGFeRD settings
- Add `zugferd_default` boolean to `Tenant.settings` JSON schema
- When enabled, regular PDF export automatically produces ZUGFeRD
- Add GraphQL mutation to toggle the setting
- Write tests

### 9. Frontend: Add ZUGFeRD export button to invoice export page
- Add "ZUGFeRD PDF" button to the export button group
- Implement click handler calling the ZUGFeRD export endpoint
- Add loading state and error handling
- Add German/English translations for labels and tooltips
- Update `de.json` and `en.json` locale files

### 10. Frontend: Add ZUGFeRD toggle in tenant settings
- Add toggle switch in settings page for "ZUGFeRD als Standard-PDF-Format"
- Wire to GraphQL mutation for saving the setting
- Add German/English translations

### 11. Write E2E tests
- Test ZUGFeRD export button visibility and click behavior
- Test ZUGFeRD PDF download
- Test settings toggle
- Test error states (no legal data, no finalized invoices)

### 12. Validation and documentation
- Test generated ZUGFeRD PDFs with Mustang validator (manual verification)
- Test with veraPDF for PDF/A-3 compliance (manual verification)
- Document the ZUGFeRD feature in user-facing help text
- Update CLAUDE.md if new commands or conventions are needed

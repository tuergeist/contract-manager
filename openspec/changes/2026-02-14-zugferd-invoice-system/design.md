## Context

The contract manager generates German-compliant invoices via `InvoiceService` using WeasyPrint HTML-to-PDF rendering. The system has:

- `CompanyLegalData` model with full UStG §14 / HGB §35a fields (company name, address, tax number, VAT ID, commercial register, managing directors, bank details)
- `InvoiceRecord` model with frozen line item snapshots, tax amounts, invoice numbers, and company data snapshots
- `InvoiceData` / `InvoiceLineItem` dataclasses for on-demand invoice calculation
- `InvoiceNumberScheme` for sequential numbering
- HTML template rendering via Django templates + WeasyPrint
- Export as combined PDF, individual PDFs (ZIP), and Excel

The current PDFs are standard PDF 1.7 — not PDF/A-3 and not ZUGFeRD compliant. Germany's Wachstumschancengesetz mandates structured e-invoicing for B2B starting 2025 (receive) and 2027 (send). ZUGFeRD 2.x (= Factur-X) is the dominant format: a PDF/A-3 with embedded UN/CEFACT CII XML conforming to EN 16931.

## Goals / Non-Goals

**Goals:**
- Generate valid ZUGFeRD EN 16931 (Comfort) profile XML from existing invoice data
- Produce PDF/A-3b compliant invoices with embedded ZUGFeRD XML and correct XMP/RDF metadata
- Validate XML against EN 16931 XSD before embedding
- Integrate ZUGFeRD output into the existing export workflow
- Keep the existing plain PDF export available as a fallback

**Non-Goals:**
- XRechnung (pure XML, no PDF) — different delivery channel, future enhancement
- Peppol network transmission — requires access point registration, out of scope
- Incoming ZUGFeRD parsing (reading ZUGFeRD XML from imported invoices) — separate feature
- Extended profile fields beyond EN 16931 — Comfort profile covers B2B requirements
- Credit notes / corrective invoices in ZUGFeRD format — future enhancement
- Per-line-item tax rates in ZUGFeRD — current system uses a single tax rate

## Decisions

### 1. XML generation library: `drafthorse` vs raw `lxml` vs `factur-x`

**Decision**: Use `drafthorse` (by pretix) for ZUGFeRD XML generation.

**Why drafthorse**:
- Pure Python, models the ZUGFeRD/CII data model 1:1 with Python classes
- Built-in XSD validation of generated XML
- Automatic profile level detection based on populated fields
- Built-in `attach_xml()` function that handles PDF attachment + XMP metadata in one step
- Actively maintained (pretix uses it in production for event ticketing invoices)
- Supports ZUGFeRD 2.3 data model (compatible with EN 16931)

**Why not raw lxml**: Building CII XML manually requires managing ~15 XML namespaces (`ram:`, `rsm:`, `udt:`, `qdt:`, etc.), deeply nested element hierarchies, and correct EN 16931 business rules. Error-prone and hard to maintain.

**Why not factur-x (Akretion)**: Primarily designed for *attaching* an already-generated XML to a PDF — less help with XML *generation*. The `drafthorse` library covers both generation and attachment.

**Why not WeasyPrint native approach**: While WeasyPrint >=64.0 supports `pdf_variant='pdf/a-3b'` and attachments, using `drafthorse.pdf.attach_xml()` on the WeasyPrint output is simpler — it handles XMP metadata, attachment relationship, and PDF/A-3 conversion in one call. This avoids manually building RDF/XMP XML.

### 2. Integration approach: Post-processing vs inline generation

**Decision**: Post-processing — generate the PDF with WeasyPrint first (as today), then use `drafthorse.pdf.attach_xml()` to convert it to PDF/A-3 and embed the XML.

**Why**: This keeps the existing HTML template rendering unchanged. The `attach_xml()` function from drafthorse takes the WeasyPrint PDF bytes as input and returns ZUGFeRD-compliant PDF/A-3 bytes with the XML embedded. Clean separation of concerns: visual rendering (WeasyPrint) vs. structured data (drafthorse).

**Alternative considered**: Generate PDF/A-3 directly from WeasyPrint using `write_pdf(pdf_variant='pdf/a-3b')` and attach XML manually. This requires building XMP/RDF metadata XML by hand and using WeasyPrint's `Attachment` API. More code, same result.

### 3. ZUGFeRD profile level: EN 16931 (Comfort)

**Decision**: Target the EN 16931 profile (also called "Comfort" in ZUGFeRD terminology).

**Why**: EN 16931 is the European norm mandated by the Wachstumschancengesetz. It covers all fields needed for standard B2B invoicing: seller/buyer info, invoice date/number, line items with descriptions and amounts, tax breakdown, payment terms, and bank details. The Extended profile adds optional fields (delivery details, logistics, allowances/charges) that our data model doesn't currently support.

**Profile hierarchy** (for reference):
- MINIMUM — invoice number, date, amounts only
- BASIC WL — adds seller/buyer names
- BASIC — adds line items
- **EN 16931 (Comfort)** — full European norm ← our target
- EXTENDED — additional trade/logistics fields

### 4. Data mapping: InvoiceRecord/InvoiceData → ZUGFeRD XML

**Decision**: Map from existing data structures without new models.

| ZUGFeRD Field | Source |
|---|---|
| Seller name, address | `CompanyLegalData` (or `company_data_snapshot` on InvoiceRecord) |
| Seller VAT ID | `CompanyLegalData.vat_id` |
| Seller tax number | `CompanyLegalData.tax_number` |
| Buyer name, address | `Customer.name`, `Customer.address` |
| Invoice number | `InvoiceRecord.invoice_number` |
| Invoice date | `InvoiceRecord.billing_date` |
| Service period | `InvoiceRecord.period_start` / `period_end` |
| Line items | `InvoiceRecord.line_items_snapshot` |
| Tax rate / amount | `InvoiceRecord.tax_rate` / `tax_amount` |
| Net total | `InvoiceRecord.total_net` |
| Gross total | `InvoiceRecord.total_gross` |
| Currency | `Tenant.currency` |
| Payment means (bank) | `CompanyLegalData.iban`, `bic`, `bank_name` |
| Invoice note | `InvoiceRecord.invoice_text` |

**Missing fields for EN 16931 that need addressing**:
- **Buyer VAT ID / tax number**: Not currently stored on `Customer`. For B2B ZUGFeRD, the buyer's VAT ID is recommended but not strictly required at EN 16931 level. We'll make it optional and pull from `Customer.address` JSON if available, or leave empty.
- **Payment due date**: Not currently stored. Can be derived from `invoice_text` or a new field. For now, we'll omit it (not required at EN 16931).
- **Unit of measure (UOM)**: Line items don't have a UOM field. Default to "C62" (one/piece) per UN/ECE Recommendation 20, which is the standard for software license quantities.

### 5. WeasyPrint version requirement

**Decision**: Bump `weasyprint>=62.0` to `weasyprint>=64.0` in `pyproject.toml`.

**Why**: WeasyPrint 64.0 introduced `pdf_variant` parameter support and the `rdf_metadata_generator` API. While we'll use `drafthorse.pdf.attach_xml()` for the final PDF/A-3 conversion (which doesn't require WeasyPrint 64), having the newer version ensures compatibility and allows a potential future switch to native WeasyPrint PDF/A-3 generation.

### 6. Export integration: New format vs. replacing existing PDF

**Decision**: Add `zugferd` as a new export format option alongside `pdf`, `pdf-individual`, and `excel`. Add a tenant-level setting `zugferd_default` (boolean, default False) that, when enabled, makes the regular `pdf` export automatically produce ZUGFeRD output.

**Why**: Gradual rollout — users can test ZUGFeRD output explicitly before switching their default. Existing integrations consuming the `pdf` format continue working unchanged until the tenant opts in.

**API changes**:
- Export endpoint: `format=zugferd` produces a single ZUGFeRD PDF; `format=zugferd-individual` produces a ZIP of individual ZUGFeRD PDFs
- When `zugferd_default=True` on tenant settings, `format=pdf` silently upgrades to ZUGFeRD

### 7. Validation strategy

**Decision**: Validate generated XML against EN 16931 XSD schemas before embedding in PDF. Log warnings for validation failures but still produce the PDF (with XML) — don't block invoice generation.

**Why**: XSD validation catches structural errors (missing required elements, wrong data types). However, EN 16931 also has Schematron business rules that are harder to validate programmatically. Blocking invoice generation on validation failure would be too disruptive. Instead, log the validation result and surface it in the UI as a warning.

**Future**: Add optional Schematron validation using the official EN 16931 rules for stricter compliance checking.

## Risks / Trade-offs

**[PDF/A-3 conversion quality]** → `drafthorse.pdf.attach_xml()` modifies the PDF to make it PDF/A-3 compliant. WeasyPrint's output may have features (transparency, certain fonts) that cause issues. Mitigation: test with the actual invoice HTML template and verify with veraPDF validator.

**[drafthorse maintenance]** → The library is maintained by the pretix team, which acknowledges limited bandwidth. Mitigation: the library is pure Python with no C extensions; we can fork or patch if needed. The XML schema itself is stable (EN 16931 hasn't changed structurally).

**[Missing buyer data]** → EN 16931 recommends buyer VAT ID for B2B invoices. Our Customer model stores address as a JSONField without a dedicated VAT ID field. Mitigation: add `vat_id` to the Customer address JSON schema; treat as optional in the XML (the profile allows it).

**[Single tax rate limitation]** → Current system uses one tax rate per invoice. ZUGFeRD supports multiple tax categories per invoice. Mitigation: generate a single VATBreakdown entry. When multi-rate support is added later, the ZUGFeRD generation will need updating.

**[Font embedding for PDF/A-3]** → PDF/A-3 requires all fonts to be embedded. WeasyPrint generally handles this, but the `attach_xml()` post-processing must preserve font embedding. Mitigation: verify with veraPDF after generation.

## Open Questions

- Should we add a `vat_id` field to the Customer model (as a proper DB field) for B2B buyer identification in ZUGFeRD? Or is the JSONField `address` sufficient?
- Should the system support both ZUGFeRD and XRechnung output from the same invoice data? XRechnung is pure XML (no PDF wrapper) used for government/public sector invoices in Germany.
- Should we store the generated ZUGFeRD XML alongside the InvoiceRecord (as a file or in a JSONField) for archival purposes?

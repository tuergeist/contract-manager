## Context

Invoice PDFs are generated via `InvoiceService.generate_pdf()` which renders `invoices/invoice.html` with a `invoice_dict`. The data pipeline already collects `invoice_text`, `po_number`, and `order_confirmation_number` from contracts into `InvoiceData`, but these fields are not included in the `invoice_dict` passed to the template, and the template doesn't render them.

The LABELS dict already has entries for `contract` but not for PO number or order confirmation number.

## Goals / Non-Goals

**Goals:**
- Render invoice text below line items on the PDF
- Show PO number and order confirmation number in the invoice metadata table (when present)
- Add German and English labels for new fields
- Update both `generate_pdf()` and `generate_preview_pdf()` so preview reflects the changes

**Non-Goals:**
- Per-customer VAT rate logic (tax rate is already applied globally from company data)
- Changing how these fields are stored or collected — only the PDF rendering

## Decisions

**1. Field placement on invoice PDF**

- **PO number** and **order confirmation number**: Add rows to the invoice metadata table (the right-aligned key-value section with date, invoice number, service period, contract). These are reference numbers that belong in the header area.
- **Invoice text**: Render below the totals section, before the footer. This is free-form text (payment terms, special notes) that belongs after the financial summary.

Rationale: Follows German invoice conventions (DIN 5008) where reference numbers go in the header and notes/terms go after the totals.

**2. Conditional rendering**

All three fields render only when non-empty. Use `{% if %}` guards in the template to avoid blank rows/sections.

**3. Labels**

Add to the existing LABELS dict:
- `po_number`: "Bestellnummer" / "PO Number"
- `order_confirmation`: "Auftragsbestätigung" / "Order Confirmation"
- `invoice_text` needs no label — it renders as free-form text block

## Risks / Trade-offs

- **PDF layout shift**: Adding rows to the metadata table and a text block could push content onto a second page for invoices with many line items → Acceptable, WeasyPrint handles page breaks automatically.
- **Long invoice text**: Very long text could take significant space → Acceptable, it's user-controlled content they want on the invoice.

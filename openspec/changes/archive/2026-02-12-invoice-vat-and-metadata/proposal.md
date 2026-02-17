## Why

Generated invoice PDFs are missing key information that German business invoices require: the contract's invoice text (special instructions, references), PO numbers, and order confirmation numbers. While VAT calculation already works, these metadata fields exist in the data model but are not rendered on the PDF template or passed through to the template context.

## What Changes

- Add **invoice text** from the contract to the invoice PDF, displayed below line items
- Add **PO number** (from contract) to the invoice metadata section when present
- Add **order confirmation number** (from contract) to the invoice metadata section when present
- Pass these fields through the `invoice_dict` used for PDF rendering in `InvoiceService.generate_pdf()`
- Add corresponding German/English labels to the LABELS dict

## Capabilities

### New Capabilities

_(none — this enhances existing invoice generation)_

### Modified Capabilities

- `invoice-generation`: Add invoice text, PO number, and order confirmation number to generated PDF invoices

## Impact

- `backend/apps/invoices/services.py`: Pass `invoice_text`, `po_number`, `order_confirmation_number` through `invoice_dict` in `generate_pdf()` and `generate_preview_pdf()`
- `backend/apps/invoices/templates/invoices/invoice.html`: Render the new fields in the metadata section and below line items
- `backend/apps/invoices/services.py`: Add labels for PO number and order confirmation to LABELS dict

## 1. Labels

- [x] 1.1 Add `po_number` and `order_confirmation` entries to the DE and EN LABELS dicts in `backend/apps/invoices/services.py`

## 2. PDF Template

- [x] 2.1 Add conditional PO number row to the invoice metadata table in `invoice.html`
- [x] 2.2 Add conditional order confirmation number row to the invoice metadata table in `invoice.html`
- [x] 2.3 Add conditional invoice text block below the totals section (before footer) in `invoice.html`
- [x] 2.4 Add CSS for the invoice text block

## 3. Template Context

- [x] 3.1 Pass `invoice_text`, `po_number`, `order_confirmation_number` through `invoice_dict` in `generate_pdf()`
- [x] 3.2 Pass the same fields through `invoice_dict` in `generate_preview_pdf()` with sample data

## 4. Testing

- [x] 4.1 Update existing PDF generation tests to verify new fields appear when set
- [x] 4.2 Run backend tests to confirm nothing breaks

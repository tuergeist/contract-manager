## 1. Backend - Invoice HTML rendering

- [x] 1.1 Add `generate_invoice_html()` method to `InvoiceService` that renders `invoices/invoice.html` for a single `InvoiceData` and returns the HTML string (reuse same template context logic as `generate_pdf`, skip WeasyPrint)
- [x] 1.2 Add `InvoicePreviewHtmlView` REST endpoint at `/api/invoices/preview-html/` accepting `year`, `month`, `contract_id` query params; returns `text/html` response
- [x] 1.3 In the endpoint: authenticate user, check `invoices.export` permission, resolve per-customer language, look up finalized InvoiceRecord for invoice number, calculate domestic/reverse-charge tax
- [x] 1.4 Register the new URL in `config/urls.py`
- [x] 1.5 Write backend tests for the preview-html endpoint (auth, permission, 404, successful HTML response with/without invoice number)

## 2. Frontend - Preview dialog

- [x] 2.1 Add an Eye/preview icon button to each invoice row in `InvoiceExportPage.tsx` (stop propagation so row expand is not triggered)
- [x] 2.2 Create invoice preview dialog component that fetches HTML from `/api/invoices/preview-html/` with auth header and renders it in an iframe via `srcdoc`
- [x] 2.3 Add loading state in the dialog while HTML is being fetched
- [x] 2.4 Add i18n keys for preview button tooltip/label in `de.json` and `en.json`

## 3. Testing & verification

- [x] 3.1 Verify preview renders correctly with template customizations (accent color, logo, header/footer text)
- [x] 3.2 Verify preview omits invoice number for ungenerated invoices and includes it for finalized ones
- [x] 3.3 Run `npx tsc --noEmit` to confirm no TypeScript errors

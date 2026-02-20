## Context

The `/invoices/export` page currently shows a summary table with expandable line items, but users can't see the actual rendered invoice layout before exporting. The backend already has:
- `InvoiceService.get_invoices_for_month()` — returns `InvoiceData` for a month
- `InvoiceService.generate_pdf()` — renders `invoices/invoice.html` template → WeasyPrint PDF
- `InvoiceService.generate_preview_pdf()` — renders a dummy invoice as PDF
- `invoices/invoice.html` — full Django template with company header, customer address, line items, totals, legal footer

The HTML template is self-contained (inline CSS, no external assets except base64-encoded logo). This makes it ideal for returning as raw HTML that can be displayed in an iframe.

## Goals / Non-Goals

**Goals:**
- Let users preview each real invoice as rendered HTML (matching PDF layout) directly on the export page
- Show all invoice data except the invoice number (which is assigned on generation)
- Reuse the existing `invoices/invoice.html` template — no duplication

**Non-Goals:**
- Replacing the existing summary table — the preview is an additional action per row
- Making the HTML preview editable
- Changing the PDF rendering pipeline or template

## Decisions

### 1. New REST endpoint returning HTML (not extending the existing export endpoint)

Add `GET /api/invoices/preview-html/?year=Y&month=M&contract_id=C` that returns a single invoice rendered as HTML.

**Why not extend `/api/invoices/export/` with `format=html`?** The export endpoint is designed for file downloads (sets `Content-Disposition: attachment`). A preview endpoint serves a different purpose — inline rendering — and keeping them separate is cleaner.

**Why not a GraphQL query returning HTML?** GraphQL is poorly suited for returning large HTML blobs. A REST endpoint returning `text/html` is straightforward and allows direct use in an iframe `src`.

**Alternative considered: batch all invoices in one response.** Rejected because invoices for a month can be 50+; rendering one at a time keeps the response fast and memory usage low.

### 2. Frontend renders preview in a dialog with iframe

When the user clicks a preview icon on an invoice row, a dialog opens containing an `<iframe>` whose `src` points to the preview HTML endpoint.

**Why iframe?** The invoice template has its own CSS (A4 page styles, custom fonts, `@page` rules). Embedding raw HTML in the React DOM would cause style conflicts. An iframe provides complete style isolation.

**Why dialog instead of inline expand?** The invoice is A4-format content that needs space to be readable. An expandable row would be too narrow. A dialog/sheet gives full width.

**Alternative considered: fetch HTML and use `srcdoc`.** This works but adds complexity (auth header management, CORS). Using `src` with the auth token as a query param is simpler, and since this is an internal tool the token-in-URL tradeoff is acceptable. However, we'll use `srcdoc` with a fetched HTML string to keep the auth token in the Authorization header (not in URL).

### 3. Backend: new `generate_invoice_html()` method

Add a thin method to `InvoiceService` that reuses the same logic as `generate_pdf()` but returns the rendered HTML string instead of passing it through WeasyPrint. This is essentially the render step without the PDF conversion.

The method accepts a single `InvoiceData` + language and returns an HTML string. The invoice number is explicitly omitted (empty string passed to template).

### 4. Per-customer language resolution in the endpoint

The preview endpoint resolves the invoice language per-customer (same logic as the export endpoint) so the preview matches what the exported PDF will show.

## Risks / Trade-offs

- **HTML vs PDF fidelity**: The HTML preview will closely match the PDF but not pixel-perfectly (WeasyPrint interprets CSS slightly differently than a browser). This is acceptable — the purpose is data verification, not pixel-perfect proofing.
  → Mitigation: Same template, same data. Visual differences are minor (margins, page breaks).

- **Auth token handling**: Using `fetch()` + `srcdoc` means we need to handle the async fetch in the dialog component.
  → Mitigation: Simple loading state in the dialog while HTML is fetched.

- **Logo rendering**: The template uses base64-encoded logos which work in both browser and WeasyPrint.
  → No mitigation needed — already handled.

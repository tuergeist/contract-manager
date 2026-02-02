## 1. Backend - Invoice Service

- [x] 1.1 Create `apps/invoices/` Django app with basic structure
- [x] 1.2 Implement `InvoiceService.get_invoices_for_month(year, month)` that aggregates billing events from all active contracts
- [x] 1.3 Create invoice data classes/types (InvoiceData, InvoiceLineItem) for structured return values
- [x] 1.4 Add unit tests for invoice generation logic

## 2. Backend - GraphQL API

- [x] 2.1 Create `InvoiceType` and `InvoiceLineItemType` Strawberry types
- [x] 2.2 Add `invoicesForMonth(year: Int!, month: Int!)` query to schema
- [x] 2.3 Add tests for GraphQL invoice query

## 3. Backend - PDF Export

- [x] 3.1 Add WeasyPrint to requirements and Docker image
- [x] 3.2 Create HTML template for invoice PDF
- [x] 3.3 Implement `InvoiceService.generate_pdf(invoices)` for combined PDF
- [x] 3.4 Implement `InvoiceService.generate_individual_pdfs(invoices)` returning ZIP
- [x] 3.5 Add tests for PDF generation

## 4. Backend - Excel Export

- [x] 4.1 Implement `InvoiceService.generate_excel(invoices)` with Summary, Invoices, Line Items sheets
- [x] 4.2 Add tests for Excel generation

## 5. Backend - REST Export Endpoint

- [x] 5.1 Create REST view at `/api/invoices/export/` with year, month, format parameters
- [x] 5.2 Add content-disposition headers for file downloads
- [x] 5.3 Add tests for export endpoint

## 6. Frontend - Invoice Export Page

- [x] 6.1 Create `/invoices/export` route in React Router
- [x] 6.2 Add "Invoice Export" link to main navigation
- [x] 6.3 Create `InvoiceExportPage` component with month/year picker
- [x] 6.4 Implement GraphQL query hook for `invoicesForMonth`
- [x] 6.5 Create `InvoicePreviewTable` component with contract name, customer name, total amount
- [x] 6.6 Add totals summary above preview table

## 7. Frontend - Export Actions

- [x] 7.1 Add "Export PDF" button for combined PDF download
- [x] 7.2 Add "Export Individual PDFs" button for ZIP download
- [x] 7.3 Add "Export Excel" button for Excel download
- [x] 7.4 Implement loading states and error handling
- [x] 7.5 Disable export buttons when no invoices

## 8. Localization

- [x] 8.1 Add German translations to `de.json`
- [x] 8.2 Add English translations to `en.json`
- [x] 8.3 Add German/English labels for PDF template

## 9. Testing

- [x] 9.1 Add E2E test for invoice export flow
- [x] 9.2 Test with various contract configurations

## Why

Users need to generate invoices for a specific month to send to customers or import into accounting systems. Currently, the billing schedule is calculated internally but there's no way to export invoices for a given period as downloadable files.

## What Changes

- Add a new "Invoice Export" page accessible from the main navigation
- User can select a target month (month + year picker)
- System calculates all billing events due in that month across all active contracts
- User can preview the invoice list before exporting
- Export options:
  - **PDF**: Individual invoice PDFs (one per contract/customer) or combined
  - **Excel**: Single spreadsheet with all invoices and line items
- Include contract details, customer info, line items, and totals in exports

## Capabilities

### New Capabilities

- `invoice-generation`: Logic to calculate which invoices are due in a given month, aggregating billing events from all active contracts
- `invoice-export`: UI and backend for exporting invoices as PDF or Excel files, including preview functionality

### Modified Capabilities

None - this feature uses existing billing schedule calculation without changing its requirements.

## Impact

- **Backend**: New GraphQL queries/mutations for invoice generation and export endpoints
- **Frontend**: New route `/invoices/export`, new components for month picker and invoice preview
- **Dependencies**: PDF generation library (e.g., WeasyPrint or reportlab), Excel library (openpyxl already available via import feature)
- **Localization**: New translation keys for German and English

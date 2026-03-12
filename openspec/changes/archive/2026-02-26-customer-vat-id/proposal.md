## Why

Outgoing invoices need to show the customer's VAT ID (USt-IdNr.) for EU reverse-charge compliance and proper bookkeeping. Currently only the company's own VAT ID appears in the invoice footer. Customers have no field to store their VAT registration number.

## What Changes

- Add optional `vat_id` field to the Customer model
- Expose `vat_id` in GraphQL schema (read + write)
- Display customer VAT ID on the invoice PDF below the recipient address block
- Include customer VAT ID in ZUGFeRD XML as buyer tax registration
- Snapshot customer VAT ID into InvoiceRecord at generation time (so historical invoices remain correct even if the customer's VAT ID changes later)
- Sync VAT ID from HubSpot if available (`vatid` property)

## Capabilities

### New Capabilities
- `customer-vat-id`: Adding VAT ID field to customer, displaying it on invoices and embedding in ZUGFeRD XML

### Modified Capabilities
- `invoice-generation`: Invoice data now includes customer VAT ID; template renders it in recipient block
- `zugferd-pdf-integration`: Buyer tax registration populated from customer VAT ID

## Impact

- **Backend models**: Customer gets new `vat_id` CharField (migration needed)
- **Invoice template**: `invoices/invoice.html` — add VAT ID line in recipient block
- **Invoice services**: `InvoiceData` dataclass gains `customer_vat_id` field; snapshotted into `InvoiceRecord.company_data_snapshot` or a new field
- **ZUGFeRD**: `zugferd.py` — set buyer tax registration from customer VAT ID
- **GraphQL**: CustomerType, CreateCustomerInput, UpdateCustomerInput
- **HubSpot sync**: Map `vatid` property to `Customer.vat_id`
- **Frontend**: Customer detail/edit forms, invoice preview

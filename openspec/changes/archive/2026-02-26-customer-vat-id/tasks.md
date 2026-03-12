## Tasks

### 1. Backend: Customer model + migration

- [x] 1.1 Add `vat_id = CharField(max_length=50, blank=True, default="")` to Customer model
- [x] 1.2 Create and run migration

### 2. Backend: GraphQL schema

- [x] 2.1 Add `vat_id` to CustomerType (auto-exposed via strawberry-django)
- [x] 2.2 Add UpdateCustomerVatIdInput/Result types
- [x] 2.3 Add `update_customer_vat_id` mutation (follows per-field mutation pattern)

### 3. Backend: HubSpot sync

- [x] 3.1 Add `vatid` to HubSpot properties fetch list in `hubspot.py`
- [x] 3.2 Map `properties.get("vatid", "")` → `customer.vat_id` in sync logic (don't clear if empty)
- [x] 3.3 Update HubSpot sync test for `vatid` property

### 4. Backend: Invoice generation

- [x] 4.1 Add `customer_vat_id: str = ""` to `InvoiceData` dataclass in `types.py`
- [x] 4.2 Populate `customer_vat_id` from `contract.customer.vat_id` in `generate_invoices()` in `services.py`
- [x] 4.3 Add `"customer_vat_id"` to invoice_dict in `generate_pdf()` and `generate_invoice_html()` template contexts
- [x] 4.4 Add `"vat_id"` label to LABELS dict: DE="USt-IdNr.", EN="VAT ID"
- [x] 4.5 Add VAT ID line to `invoice.html` template below customer address block (conditional on non-empty)

### 5. Backend: ZUGFeRD

- [x] 5.1 Add `customer_vat_id: str = ""` parameter to `_build_xml()` in `zugferd.py`
- [x] 5.2 Replace `customer_address.get("vat_id", "")` with the explicit `customer_vat_id` parameter
- [x] 5.3 Pass `customer_vat_id` from `generate_xml_from_record()` (read from `record.customer.vat_id`)
- [x] 5.4 Pass `customer_vat_id` from `generate_xml_from_invoice_data()` (read from `invoice_data.customer_vat_id`)

### 6. Frontend: CustomerDetail

- [x] 6.1 Add `vatId` to the customer GraphQL query
- [x] 6.2 Add `vatId` to the update customer mutation input
- [x] 6.3 Add VAT ID field to customer info section (editable inline like other fields)
- [x] 6.4 Add i18n keys for DE/EN: "USt-IdNr." / "VAT ID"

### 7. Backend: MCP tools

- [x] 7.1 Add `vat_id` to MCP `get_customer` / `list_customers` tool output (if not auto-exposed)

### 8. Tests

- [x] 8.1 Backend test: create/update customer with vat_id via GraphQL
- [x] 8.2 Backend test: HubSpot sync with vatid property
- [x] 8.3 Backend test: invoice generation includes customer_vat_id in context

## Context

Invoices must show the customer's VAT ID (USt-IdNr.) for EU reverse-charge compliance. Currently only the company's own VAT ID appears in the invoice footer. The Customer model has no `vat_id` field. ZUGFeRD XML already has a placeholder reading `customer_address.get("vat_id", "")` but it's never populated.

## Goals / Non-Goals

**Goals:**
- Store customer VAT ID as a dedicated model field
- Display VAT ID on invoice PDFs (recipient block)
- Include VAT ID in ZUGFeRD XML buyer tax registration
- Snapshot VAT ID at invoice generation time
- Sync from HubSpot if available
- Editable in frontend customer detail

**Non-Goals:**
- VAT ID format validation (customers may have non-EU tax IDs)
- Automatic reverse-charge logic based on VAT ID presence (already handled by country comparison)
- Adding VAT ID to imported invoices (those come from external systems)

## Decisions

### 1. Dedicated CharField on Customer model

Add `vat_id = CharField(max_length=50, blank=True, default="")` to Customer.

**Why not extend the address JSONField?** ZUGFeRD already reads `customer_address.get("vat_id")`, so that would work, but a dedicated field is queryable, visible in admin, and explicit. The address JSON is for postal address data.

### 2. Snapshot via `customer_vat_id` on InvoiceData + pass to template

Add `customer_vat_id: str = ""` to `InvoiceData` dataclass. Populate from `contract.customer.vat_id` during invoice generation. Pass through to the template context dict alongside `customer_address`.

For `InvoiceRecord`, the VAT ID is already implicitly stored if we include it in the template render context. No new DB column needed on InvoiceRecord — the PDF itself is the snapshot. For ZUGFeRD XML generation from records, read from `record.customer.vat_id` (same as current `customer_address` reads from `record.customer`).

### 3. Invoice template placement

Show VAT ID below the customer address block, above the contract info line:

```
Customer Name
Street
ZIP City
Country
USt-IdNr.: DE123456789    ← new line (only if non-empty)
```

Label: "USt-IdNr." (DE) / "VAT ID" (EN) — add to LABELS dict in services.py.

### 4. ZUGFeRD buyer tax registration

`_build_xml()` already handles buyer VAT ID at line 388-392 via `customer_address.get("vat_id")`. Change this to accept an explicit `customer_vat_id` parameter instead, matching the dedicated field approach.

### 5. HubSpot sync

Map `vatid` HubSpot property → `Customer.vat_id`. Add to the properties list in `hubspot.py`. HubSpot's standard company property for EU VAT is `vatid`.

### 6. Frontend: inline edit on CustomerDetail

Add a VAT ID field to the customer info section in CustomerDetail, editable like other fields. No separate form needed.

## Risks / Trade-offs

- **HubSpot overwrites manual edits**: If a customer is HubSpot-synced and someone edits the VAT ID manually, the next sync could overwrite it. This is consistent with how `name` and `address` already work. → Acceptable, same pattern as other fields.
- **Existing invoices**: Already-generated PDF/ZUGFeRD files won't retroactively include VAT ID. → Expected, invoices are point-in-time snapshots.

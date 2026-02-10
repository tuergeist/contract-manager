## Context

The banking module stores counterparty information as denormalized string fields on `BankTransaction` (counterparty_name, counterparty_iban, counterparty_bic) and `RecurringPattern` (counterparty_name, counterparty_iban). The frontend routes to counterparty detail pages using the raw name in the URL (`/banking/counterparty/:name`).

This creates several problems:
- Names with special characters require URL encoding and can cause routing issues
- Renaming a counterparty would require updating every transaction record
- No way to merge duplicate counterparties (e.g., "ACME Inc" vs "ACME Inc.")
- The same counterparty may appear with slight name variations across transactions

## Goals / Non-Goals

**Goals:**
- Create a proper `Counterparty` entity with UUID primary key for stable identification
- Enable counterparty renaming without breaking any references
- Support counterparty merging (combine duplicates into one)
- Use UUID in URLs for stable, encoding-safe routes
- Migrate existing data without loss

**Non-Goals:**
- Automatic fuzzy matching/deduplication of counterparties (future enhancement)
- Linking counterparties to external systems (CRM, etc.)
- Counterparty categorization or tagging (can be added later)

## Decisions

### 1. UUID Primary Key vs Auto-increment ID

**Decision**: Use UUID (uuid.uuid4) as the primary key

**Rationale**: UUIDs provide URL-safe identifiers that don't expose record counts. They're better for potential future multi-tenant scenarios and don't require database coordination. The performance overhead is negligible for this use case.

**Alternative considered**: Auto-increment integer ID - simpler but exposes ordering, requires slug for URLs

### 2. Foreign Key Strategy

**Decision**: Add nullable FK on BankTransaction and RecurringPattern pointing to Counterparty

**Rationale**: Nullable FK allows a phased migration - existing transactions can be updated gradually. The FK provides proper referential integrity and enables efficient queries.

**Alternative considered**: Keep counterparty_name as a backup field - adds complexity and data duplication

### 3. Migration Approach

**Decision**: Two-phase migration:
1. Add Counterparty model and nullable FK fields
2. Data migration: extract unique names per tenant, create Counterparty records (with first non-empty IBAN/BIC), update FKs
3. Make FK non-nullable and remove old string fields

**Rationale**: Phased approach allows rollback at each step. Matching by name only since only ~5% of transactions have IBAN data.

**Alternative considered**: Single atomic migration - riskier, harder to debug if issues arise

### 4. Counterparty Matching Key

**Decision**: Match counterparties by (tenant, name) only. Store first non-empty IBAN/BIC found on the Counterparty record.

**Rationale**: Only ~5% of transactions have IBAN data. Matching by name alone provides better consolidation. If the same counterparty appears with different IBANs (multiple bank accounts), they still represent one entity. The stored IBAN serves as reference data, not a matching key.

### 5. Keep Original Fields Temporarily

**Decision**: Keep counterparty_name, counterparty_iban, counterparty_bic on BankTransaction during migration, remove in final migration.

**Rationale**: Allows verification that FK data matches original data before removing the source of truth. Enables easy rollback if issues found.

## Risks / Trade-offs

**[Data inconsistency during migration]** → Run migration in a maintenance window, verify counts match before/after

**[Duplicate counterparties from slight name variations]** → Accept initial duplicates (e.g., "ACME Inc" vs "ACME Inc."), provide merge functionality for manual cleanup later

**[Breaking API change]** → Document in release notes, frontend is internal so can update simultaneously

**[Performance on counterparty queries]** → Add index on Counterparty.name for filtering, FK indexes auto-created

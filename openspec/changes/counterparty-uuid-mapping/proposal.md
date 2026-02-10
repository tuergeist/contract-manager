## Why

The banking module currently identifies counterparties by their raw name string stored directly on transactions and recurring patterns. This makes counterparty renaming impossible (breaking all references), causes URL encoding issues with special characters, and prevents proper entity management. A dedicated Counterparty model with UUID primary key enables stable identification, safe renaming, and proper relational structure.

## What Changes

- Add new `Counterparty` model with UUID primary key, name, and optional IBAN/BIC fields
- **BREAKING**: Replace `counterparty_name`, `counterparty_iban`, `counterparty_bic` fields on `BankTransaction` with a foreign key to `Counterparty`
- **BREAKING**: Replace `counterparty_name`, `counterparty_iban` fields on `RecurringPattern` with a foreign key to `Counterparty`
- Update frontend routes from `/banking/counterparty/:name` to `/banking/counterparty/:id` (UUID-based)
- Add GraphQL mutations for counterparty CRUD operations
- Data migration to extract unique counterparties from existing transactions and create records

## Capabilities

### New Capabilities
- `counterparty-management`: CRUD operations for counterparty entities including merge, rename, and linking to transactions

### Modified Capabilities
- `bank-transactions`: Transaction queries/mutations now reference counterparty by FK instead of storing name inline
- `recurring-payment-detection`: Patterns now reference counterparty by FK for consistent identification

## Impact

- **Backend**: New model + migration, schema changes for transaction/pattern types and mutations
- **Frontend**: CounterpartyDetailPage route change, BankingPage counterparty links, GraphQL queries
- **Database**: Data migration required to create Counterparty records from existing transaction names
- **API**: Breaking change to transaction/pattern GraphQL types (counterparty becomes object reference)

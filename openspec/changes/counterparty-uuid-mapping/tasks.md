## 1. Backend Model & Migration Phase 1

- [x] 1.1 Create Counterparty model with UUID primary key, name, iban, bic fields
- [x] 1.2 Add unique constraint on (tenant, name) for Counterparty
- [x] 1.3 Add nullable counterparty FK to BankTransaction model
- [x] 1.4 Add nullable counterparty FK to RecurringPattern model
- [x] 1.5 Generate and run migration for new model and FK fields

## 2. Data Migration

- [x] 2.1 Write data migration to extract unique counterparty names per tenant
- [x] 2.2 Create Counterparty records with first non-empty IBAN/BIC found
- [x] 2.3 Update all BankTransaction records to reference their Counterparty FK
- [x] 2.4 Update all RecurringPattern records to reference their Counterparty FK
- [x] 2.5 Verify migration is idempotent (can run multiple times safely)

## 3. Backend Model & Migration Phase 2

- [x] 3.1 Make counterparty FK non-nullable on BankTransaction
- [x] 3.2 Make counterparty FK non-nullable on RecurringPattern
- [x] 3.3 Remove old counterparty_name, counterparty_iban, counterparty_bic fields from BankTransaction
- [x] 3.4 Remove old counterparty_name, counterparty_iban fields from RecurringPattern
- [x] 3.5 Generate and run final cleanup migration

## 4. GraphQL Schema

- [x] 4.1 Create CounterpartyType with id, name, iban, bic, transactionCount fields
- [x] 4.2 Add counterparty(id: ID!) query
- [x] 4.3 Add counterparties query with pagination and search
- [x] 4.4 Add updateCounterparty mutation for rename/update
- [x] 4.5 Add mergeCounterparties mutation
- [x] 4.6 Update BankTransactionType to include counterparty object instead of string fields
- [x] 4.7 Update RecurringPatternType to include counterparty object instead of string fields

## 5. MT940 Import Update

- [x] 5.1 Update MT940 parser to find-or-create Counterparty on transaction import
- [x] 5.2 Update import hash computation to use counterparty name (for backwards compatibility)
- [ ] 5.3 Add tests for counterparty creation during import

## 6. Frontend Route & Navigation

- [x] 6.1 Update App.tsx route from /banking/counterparty/:name to /banking/counterparty/:id
- [x] 6.2 Update BankingPage counterparty links to use UUID
- [x] 6.3 Update CounterpartyDetailPage to fetch by UUID instead of name

## 7. Frontend Counterparty Detail Page

- [x] 7.1 Update GraphQL query to use counterparty(id: ID!)
- [ ] 7.2 Add rename functionality with inline edit or modal
- [ ] 7.3 Add merge functionality UI (select target counterparty)
- [x] 7.4 Update transaction table to show counterparty.name from FK

## 8. Frontend Transaction & Pattern Display

- [x] 8.1 Update BankingPage transaction table to use counterparty.name and counterparty.id for links
- [x] 8.2 Update RecurringPattern display to use counterparty.name from FK
- [x] 8.3 Update LiquidityForecast to use counterparty from FK

## 9. Testing

- [ ] 9.1 Add backend tests for Counterparty CRUD operations
- [ ] 9.2 Add backend tests for merge functionality
- [ ] 9.3 Add backend tests for data migration
- [x] 9.4 Add frontend type checks pass (npx tsc --noEmit)
- [ ] 9.5 Verify existing banking E2E tests still pass

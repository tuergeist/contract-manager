## 1. Backend Setup

- [x] 1.1 Create `backend/apps/banking/` app with `__init__.py`, `apps.py`
- [x] 1.2 Register app in `config/settings/base.py` LOCAL_APPS
- [x] 1.3 Add `mt-940` package to `pyproject.toml` dependencies and rebuild Docker image
- [x] 1.4 Add `banking.read` and `banking.write` to the RBAC permission definitions

## 2. Data Models

- [x] 2.1 Create `BankAccount` model (TenantModel) with fields: name, bank_code, account_number, iban, bic; unique constraint on (tenant, bank_code, account_number)
- [x] 2.2 Create `BankTransaction` model (TenantModel) with fields: account FK, entry_date, value_date, amount, currency, transaction_type, counterparty_name, counterparty_iban, counterparty_bic, booking_text, reference, raw_data, opening_balance, closing_balance, import_hash; unique constraint on (tenant, import_hash)
- [x] 2.3 Add database indexes: composite (tenant, account, entry_date), individual on amount, counterparty_name
- [x] 2.4 Create and apply migrations

## 3. MT940 Parser Service

- [x] 3.1 Create `backend/apps/banking/services.py` with MT940 parsing service using `mt-940` package
- [x] 3.2 Implement `:86:` subfield extraction (counterparty from `?32`/`?33`, booking text from `?20`–`?29`, IBAN/BIC from subfields)
- [x] 3.3 Implement import_hash computation (SHA256 of account_id + entry_date + amount + currency + reference + counterparty_name)
- [x] 3.4 Implement bulk import with `bulk_create(ignore_conflicts=True)` and return stats (imported, skipped)
- [x] 3.5 Implement account number validation (`:25:` field vs target account)
- [x] 3.6 Write tests for MT940 parsing using the sample file in `resources/`
- [x] 3.7 Write tests for deduplication (re-import same file, overlapping imports)

## 4. GraphQL Schema

- [x] 4.1 Create `backend/apps/banking/schema.py` with BankAccountType and BankTransactionType
- [x] 4.2 Implement `bank_accounts` query (list all accounts with transaction counts)
- [x] 4.3 Implement `bank_transactions` query with arguments: account_id, search, date_from, date_to, amount_min, amount_max, direction (debit/credit), sort_by, sort_order, page, page_size
- [x] 4.4 Implement `create_bank_account` mutation
- [x] 4.5 Implement `update_bank_account` mutation (name, iban, bic only)
- [x] 4.6 Implement `delete_bank_account` mutation (cascades transactions)
- [x] 4.7 Register BankingQuery and BankingMutation in `config/schema.py`
- [x] 4.8 Write tests for GraphQL queries and mutations

## 5. File Upload Endpoint

- [x] 5.1 Create `backend/apps/banking/views.py` with `UploadStatementView` (POST, accepts MT940 file)
- [x] 5.2 Add URL route `api/banking/upload/<account_id>/` in `config/urls.py`
- [x] 5.3 Validate account ownership (tenant match) and file format before parsing
- [x] 5.4 Return JSON response with import stats: `{total, imported, skipped, errors}`
- [x] 5.5 Write tests for upload endpoint (valid file, invalid file, wrong account, duplicate import)

## 6. Frontend: Translations & Routing

- [x] 6.1 Add German and English translations for banking section in `locales/de.json` and `locales/en.json`
- [x] 6.2 Add sidebar navigation entry with Landmark icon and `banking.read` permission
- [x] 6.3 Add `/banking` route in `App.tsx`

## 7. Frontend: Banking Page

- [x] 7.1 Create `frontend/src/features/banking/BankingPage.tsx` as main page component
- [x] 7.2 Implement bank account management section (list, create dialog, edit dialog, delete with confirmation)
- [x] 7.3 Implement MT940 file upload button per account with progress/result feedback
- [x] 7.4 Implement transaction table with columns: date, counterparty, booking text, amount, account
- [x] 7.5 Implement search input (filters counterparty name and booking text)
- [x] 7.6 Implement account filter dropdown (all accounts / specific account)
- [x] 7.7 Implement date range filter (date-from, date-to inputs)
- [x] 7.8 Implement amount range filter (amount-min, amount-max inputs)
- [x] 7.9 Implement debit/credit direction filter
- [x] 7.10 Implement column sorting (date, amount, counterparty)
- [x] 7.11 Implement pagination (50 rows per page)
- [x] 7.12 Implement empty state for no accounts and no transactions

## 8. Testing & Polish

- [x] 8.1 Run `make test-back` — all existing + new tests pass
- [x] 8.2 Run `npx tsc --noEmit` — no frontend type errors
- [ ] 8.3 Manual test: upload sample MT940 file, verify transactions appear
- [ ] 8.4 Manual test: re-upload same file, verify 0 new imports
- [ ] 8.5 Manual test: search, filter, sort, paginate transactions

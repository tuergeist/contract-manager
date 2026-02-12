## 1. Backend: ImportedInvoice Model

- [x] 1.1 Create ImportedInvoice model with fields: invoice_number, invoice_date, total_amount, currency, customer_name, customer FK, pdf_file, extraction_status, extraction_error, created_by
- [x] 1.2 Add ExtractionStatus choices: pending, extracting, extracted, extraction_failed, confirmed
- [x] 1.3 Create migration for ImportedInvoice
- [x] 1.4 Add customer FK to Counterparty model
- [x] 1.5 Create migration for Counterparty.customer field

## 2. Backend: InvoicePaymentMatch Model

- [x] 2.1 Create InvoicePaymentMatch model with fields: invoice FK, transaction FK, match_type, confidence, matched_at, matched_by FK
- [x] 2.2 Add MatchType choices: invoice_number, amount_customer, manual
- [x] 2.3 Create migration for InvoicePaymentMatch
- [x] 2.4 Add is_paid computed property to ImportedInvoice

## 3. Backend: Invoice Import GraphQL

- [x] 3.1 Create ImportedInvoiceType with all fields including payment_status
- [x] 3.2 Add importedInvoices query with pagination, search, and filters
- [x] 3.3 Add importedInvoice query for single invoice by ID
- [x] 3.4 Add uploadInvoice mutation accepting base64 PDF content
- [x] 3.5 Add deleteInvoice mutation
- [x] 3.6 Add updateInvoice mutation for correcting extracted fields

## 4. Backend: Invoice Extraction Service

- [x] 4.1 Create extraction prompt for invoice_number, invoice_date, total_amount, currency, customer_name
- [x] 4.2 Create extract_invoice_data function using Claude API
- [x] 4.3 Add run_extraction task that updates invoice status and stores results
- [x] 4.4 Handle extraction errors and update status to extraction_failed
- [x] 4.5 Add reExtractInvoice mutation to retry extraction

## 5. Backend: Customer Matching Service

- [x] 5.1 Enable pg_trgm extension in PostgreSQL (if not already)
- [x] 5.2 Create match_customer_by_name function using trigram similarity
- [x] 5.3 Return matches with confidence scores
- [x] 5.4 Add confirmCustomerMatch mutation to link invoice to customer
- [x] 5.5 Add customerMatchSuggestions query for an invoice

## 6. Backend: Payment Matching Service

- [x] 6.1 Create PaymentMatcher service class
- [x] 6.2 Implement invoice_number_strategy: search booking_text with fuzzy matching
- [x] 6.3 Implement amount_customer_strategy: match amount + counterparty.customer
- [x] 6.4 Add findPaymentMatches query returning potential matches with confidence
- [x] 6.5 Add createPaymentMatch mutation for manual/auto matches
- [x] 6.6 Add deletePaymentMatch mutation to unlink

## 7. Backend: Bank Transaction Extensions

- [x] 7.1 Add paymentMatches field to BankTransactionType
- [x] 7.2 Add matchedInvoice computed field to BankTransactionType
- [x] 7.3 Add linkCounterpartyToCustomer mutation
- [x] 7.4 Add unlinkCounterpartyFromCustomer mutation
- [x] 7.5 Add unmatchedCredits filter to transactions query

## 8. Backend: Tests

- [x] 8.1 Add tests for ImportedInvoice model and is_paid property
- [x] 8.2 Add tests for invoice extraction service
- [x] 8.3 Add tests for customer matching with trigram similarity
- [x] 8.4 Add tests for payment matching strategies
- [x] 8.5 Add tests for GraphQL mutations and queries

## 9. Frontend: Invoice List Page

- [x] 9.1 Create /invoices/imported route in App.tsx
- [x] 9.2 Add "Imported Invoices" to navigation
- [x] 9.3 Create ImportedInvoiceList component with table
- [x] 9.4 Add pagination, search by invoice number, filter by payment status
- [x] 9.5 Show payment status badge (Paid/Unpaid) on each row
- [x] 9.6 Add delete action with confirmation

## 10. Frontend: Invoice Upload

- [x] 10.1 Create InvoiceUploadModal with file dropzone
- [x] 10.2 Validate PDF file type and size
- [x] 10.3 Convert to base64 and call uploadInvoice mutation
- [x] 10.4 Show upload progress and extraction status

## 11. Frontend: Extraction Review

- [x] 11.1 Create ExtractionReviewModal showing extracted fields
- [x] 11.2 Allow editing each extracted field
- [x] 11.3 Show customer match suggestions with confidence
- [x] 11.4 Add confirm button to finalize extraction
- [x] 11.5 Add re-extract button for failed extractions

## 12. Frontend: Payment Matching UI

- [x] 12.1 Create PaymentMatchModal showing potential matches
- [x] 12.2 Show match type and confidence for each suggestion
- [x] 12.3 Allow selecting/confirming a match
- [x] 12.4 Add manual search for transactions
- [x] 12.5 Show matched transactions on invoice detail

## 13. Frontend: Transaction Extensions

- [x] 13.1 Add matched invoice indicator to transaction table rows
- [x] 13.2 Add "Match to Invoice" action on unmatched credit transactions
- [x] 13.3 Add invoice match info to transaction detail/hover
- [x] 13.4 Add "Unmatched Credits" filter option

## 14. Frontend: Counterparty-Customer Linking

- [x] 14.1 Add "Link to Customer" button on CounterpartyDetailPage
- [x] 14.2 Create CustomerSearchModal for selecting customer
- [x] 14.3 Show linked customer on counterparty detail
- [x] 14.4 Add "Unlink Customer" action

## 15. Localization

- [x] 15.1 Add English translations for invoice import UI
- [x] 15.2 Add German translations for invoice import UI

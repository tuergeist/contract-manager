## 1. InvoiceList

- [x] 1.1 Replace `useState` with `usePersistedState` for sortField, sortOrder, sourceFilter, and paymentStatus in `ImportedInvoiceList.tsx` using keys `cm:invoiceList:sortField`, `cm:invoiceList:sortOrder`, `cm:invoiceList:sourceFilter`, `cm:invoiceList:paymentStatus`

## 2. BankingPage

- [x] 2.1 Replace `useState` with `usePersistedState` for activeTab, sortBy, sortOrder, cpSortBy, and cpSortOrder in `BankingPage.tsx` using keys `cm:banking:activeTab`, `cm:banking:sortBy`, `cm:banking:sortOrder`, `cm:banking:cpSortBy`, `cm:banking:cpSortOrder`

## 3. CounterpartyDetailPage

- [x] 3.1 Replace `useState` with `usePersistedState` for sortBy and sortOrder in `CounterpartyDetailPage.tsx` using keys `cm:counterpartyDetail:sortBy`, `cm:counterpartyDetail:sortOrder`

## 4. AuditLogPage

- [x] 4.1 Replace `useState` with `usePersistedState` for entityTypeFilter and actionFilter in `AuditLogPage.tsx` using keys `cm:auditLog:entityTypeFilter`, `cm:auditLog:actionFilter`

## 5. ProjectList

- [x] 5.1 Replace `useState` with `usePersistedState` for statusFilter in `ProjectList.tsx` using key `cm:projectList:statusFilter`

## 6. CustomerDetail

- [x] 6.1 Replace `useState` with `usePersistedState` for activeTab and contract sort column/order in `CustomerDetail.tsx` using keys `cm:customerDetail:activeTab`, `cm:customerDetail:sortBy`, `cm:customerDetail:sortOrder`

## 7. Verification

- [x] 7.1 Run `npx tsc --noEmit` to confirm no type errors

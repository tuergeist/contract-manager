## Why

Heute sind "Eingangsrechnung bestätigen" und "Bank-Tx zuordnen" zwei separate Aktionen mit zwei separaten Roundtrips. Wenn die Counterparty-Match-Heuristik einen eindeutigen Kandidaten gefunden hat (z.B. genau eine Tx mit `entry_date >= invoice_date` und gleichem Betrag), sollte ein einzelner Klick beides erledigen können. Voraussetzung für Quick Win #1 (Confirm + Next) und für die Inbox-Triage-Page.

## What Changes

- Neue GraphQL-Mutation:
  ```graphql
  mutation ConfirmAndMatch($invoiceId: ID!, $transactionId: Int) {
    confirmAndMatchIncoming(invoiceId: $invoiceId, transactionId: $transactionId) {
      success
      error
      invoice { id status }
      match { id }
    }
  }
  ```
- Wenn `transactionId` weggelassen wird, sucht der Resolver einen eindeutigen Match selbst (Reuse von `_payment_match_counterparty`); bei Mehrdeutigkeit nur Confirm, kein Match
- Neuer UI-Button "Confirm + Match BTX 30.04. -805,93 €" im `IncomingInvoiceDetail` der nur erscheint, wenn ein eindeutiger Tx-Kandidat existiert
- Backend führt beide Operationen in einer DB-Transaktion aus → Rollback bei Fehler

## Capabilities

### New Capabilities
- Keine

### Modified Capabilities
- `incoming-invoice-import`: erweitert um eine kombinierte Confirm+Match-Aktion und das verfügbare Tx-Match-Feld in der Detail-Query
- `banking-invoice-matching`: erweitert um die Möglichkeit, einen Match aus dem Incoming-Invoice-Kontext heraus zu erstellen

## Impact

- **Backend**: 1 neue Resolver-Methode (~50 Zeilen), Reuse von bestehendem Counterparty-Match-Code; Tests
- **Frontend**: `IncomingInvoiceDetail.tsx` (Button + Display von Match-Suggestion-Hint)
- **Performance**: 1 GraphQL-Request statt 2 → ~150ms Einsparung pro Confirm-Match

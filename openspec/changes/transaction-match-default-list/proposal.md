## Why

Wenn ein User eine Banktransaktion ohne Customer-Link öffnet (z.B. ein neuer Lieferant) und das `TransactionMatchSheet` keine Suggestions findet, sieht er eine **leere Sektion** mit leerem Such-Feld. Er muss erraten, dass er den Rechnungs-Namen tippen sollte. Bessere UX: Default-Liste zeigen.

## What Changes

- Wenn `suggestedInvoiceMatches` leer zurückkommt, automatisch eine Default-Liste laden:
  - Bei Debit-Tx: bis zu 10 ungematchte Eingangsrechnungen der letzten 30 Tage, sortiert nach Datum absteigend
  - Bei Credit-Tx: bis zu 10 ungematchte Ausgangsrechnungen der letzten 30 Tage
- Sichtbare Headline ändert sich: statt "Suggested matches" → "Recent unmatched invoices" (DE: "Letzte ungematchte Rechnungen")
- Wenn die Default-Liste mehr als 10 Items hat, Hint "+ N weitere — über Suche eingrenzen"
- Such-Feld ersetzt die Default-Liste sobald getippt wird (≥ 2 Zeichen, wie heute)

## Capabilities

### New Capabilities
- Keine

### Modified Capabilities
- `banking-invoice-matching`: Erweitert die Match-Sheet-Anforderungen um eine Default-Vorschlagsliste bei leeren Suggestions

## Impact

- **Frontend**: `frontend/src/features/banking/TransactionMatchSheet.tsx`
- **Backend**: ggf. neue Query `recentUnmatchedInvoices(invoiceType, days, limit)` falls bestehende Resolver nicht reichen — sonst Reuse von `searchInvoicesForMatching` mit leerem Suchterm
- **i18n**: 2 neue Keys

## Why

In der Banking-Tabelle bedeutet das `Link2`-Icon zwei verschiedene Dinge: graues Icon = "Match-Sheet öffnen", blaues Icon = "ist bereits gematcht (Sheet zum Bearbeiten öffnen)". Daneben steht ein zweites Icon (`FileText`) für "geh zur gematchten Rechnung". Drei Bedeutungen, zwei Icons — User muss raten.

## What Changes

- **Status-Pill** ersetzt das blaue `Link2`-Icon: kompakter Text-Badge "Bezahlt" (grün) / "Offen" (grau) / "Teilweise" (gelb), basierend auf `totalMatched / amount`
- **Action-Icon** behält nur die "Match-Sheet öffnen"-Bedeutung — einheitlich grau, immer klickbar
- **`FileText`-Icon** bleibt als Quick-Link zur gematchten Rechnung, aber nur wenn `matchedInvoice` gesetzt ist
- Bei mehreren Matches (Teilzahlungen): Status-Pill zeigt "2/3" oder "Teilweise (200 €/300 €)"

## Capabilities

### New Capabilities
- Keine

### Modified Capabilities
- `banking-invoice-matching`: Verändert die Action-Icon-Semantik in der Transaction-Liste

## Impact

- **Frontend**: `frontend/src/features/banking/BankingPage.tsx`, `frontend/src/features/banking/CounterpartyDetailPage.tsx` (gleiche Logik in beiden)
- **Backend**: keine Änderung — `totalMatched` ist bereits in `transactionMatchDetails` verfügbar; ggf. als List-Field auf `BankTransactionType` ergänzen, falls nicht in der Listing-Query enthalten
- **i18n**: 3 neue Status-Texts

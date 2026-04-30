## Why

`BankingPage.tsx` ist heute 1645 Zeilen mit 3 logischen Verantwortlichkeiten: Konten-Header, Transaktions-Tab, Counterparties-Tab. Die Datei ist schwer zu reviewen, neue Features (Inbox-Triage, Drag-and-drop-Match, etc.) verschärfen das Problem. Splitten erleichtert spätere UX-Erweiterungen ohne Merge-Konflikte.

## What Changes

- Aufteilung in:
  - `BankingPage.tsx` (~150 LOC): Routing + Tabs + State-Management
  - `BankAccountsHeader.tsx` (~150 LOC): Konten-Cards mit Saldo, Upload-Buttons
  - `BankTransactionsTab.tsx` (~700 LOC): Transaktions-Tabelle mit Filter, Sort, Match-Sheet-Integration
  - `BankCounterpartiesTab.tsx` (~400 LOC): Counterparty-Liste mit Stats
  - `useBankingFilters.tsx` (~100 LOC): Filter/Sort-Logic als Custom Hook (für künftige Reuse in Inbox-Triage)
- Keine Verhaltens-Änderung — reiner Refactor
- Test-Coverage bleibt durch bestehende E2E-Tests gesichert

## Capabilities

### New Capabilities
- Keine

### Modified Capabilities
- Keine — interner Refactor

## Impact

- **Frontend**: 1 Datei → 5 Dateien (1645 LOC → ca. 1500 LOC verteilt, leichte Reduktion durch entfernte Duplikate)
- **Backend**: keine Änderung
- **Tests**: bestehende E2E-Tests müssen grün bleiben; ggf. minor Selektor-Anpassungen

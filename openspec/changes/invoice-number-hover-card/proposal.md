## Why

Heute braucht jeder Blick auf eine Rechnungsnummer in Banking einen kompletten Page-Wechsel: User klickt Icon → andere Page lädt → er prüft Datum/Betrag/PDF → `Browser-Back` → Filter und Scroll-Position verloren. Für 10–20 schnelle Cross-Checks pro Triage-Session sind das massive Reibungspunkte. Eine **HoverCard** zeigt das Wesentliche ohne Page-Wechsel.

## What Changes

- Neue Shared-Komponente `frontend/src/components/InvoiceHoverCard.tsx` (Wrapper um Shadcn `HoverCard`):
  - Trigger: ein beliebiges Element (typischerweise Invoice-Number-Text)
  - Inhalt: Datum, Betrag, Status-Pill, Counterparty/Customer, PDF-Thumbnail (klickbar → Volle Page), Match-Status
  - Lazy-Load: GraphQL-Query erst bei Hover-Open (vermeidet N+1 in Listen)
- Drei initiale Einsatzorte:
  1. `BankingPage.tsx` — `matchedInvoice.invoiceNumber` neben Tx-Zeile
  2. `CounterpartyDetailPage.tsx` — alle Invoice-Nummern in der Saldo-Tabelle
  3. `IncomingInvoicesPage.tsx` — Invoice-Nummer in der Liste (zeigt PDF-Preview)
- Hover-Trigger optional auch auf `Counterparty-Name` (zeigt Saldo-Mini, Outstanding) und `Tx-Reference` (zeigt Tx-Details) — separate Components, gleiche Pattern

## Capabilities

### New Capabilities
- `invoice-hover-card`: Definiert die Hover-Card-Anforderungen für Invoice-Lookup ohne Page-Wechsel

### Modified Capabilities
- Keine

## Impact

- **Frontend**: 1 neue Komponente (~120 LOC), 3 Aufrufstellen erweitert (~5 Zeilen jeweils)
- **Backend**: keine Änderung — Daten sind bereits in den Listing-Queries enthalten oder via existierender Detail-Query nachladbar
- **Performance**: Lazy-Load + 5min Apollo-Cache — keine spürbare Last

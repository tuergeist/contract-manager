## Context

Aktuell rendert die Banking-Tabelle pro Tx-Zeile ein `Link2`-Icon (graue Farbe wenn ungematcht, blaue wenn gematcht — beide klicken öffnen das Match-Sheet) plus optional ein `FileText`-Icon (Quick-Link zur Rechnungsdetail-Seite). Der Doppel-Bedeutung des `Link2` ist die Hauptfehlerquelle bei der visuellen Interpretation.

`BankTransactionType` exposiert bereits `matchedInvoice` und Match-Daten via `transactionMatchDetails`. `totalMatched` und `difference` sind in der Detail-Query, müssen aber für die Listing-Performance auch in der Tabellen-Query verfügbar sein.

## Goals

- Status (offen/teilweise/bezahlt) und Aktion (Sheet öffnen) klar trennen
- Mehrfach-Matches (Teilzahlungen) sichtbar machen
- Kein zusätzlicher Roundtrip pro Zeile

## Non-Goals

- Sortier-/Filter-Anpassungen (kommt mit `#11 banking-page-component-split`)
- Backend-Schema-Refactor

## Decisions

### Decision 1: Status-Pill statt blauem Icon

| Match-Stand | Pill-Text | Farbe |
|---|---|---|
| 0 % matched | "Offen" | grau |
| > 0 % und < 100 % | "Teilweise" | gelb |
| ≥ 100 % | "Bezahlt" | grün |

Bei mehrfachen Matches wird der Text um Anzahl ergänzt: "Bezahlt (3)" / "Teilweise (1/3)".

### Decision 2: Action-Icon einheitlich grau

Klick auf `Link2`-Icon öffnet immer das Match-Sheet — egal ob gematcht oder nicht. Tooltip macht den Zweck klar: "Match bearbeiten" wenn gematcht, "Zuordnen" wenn nicht.

### Decision 3: `FileText`-Quick-Link nur bei Single-Match

Wenn genau eine Rechnung gematcht ist, zeigt das Zeilen-Ende ein `FileText`-Icon → führt zur Rechnungsdetail (mit Type-Routing für incoming vs imported vs generated, wie heute). Bei mehreren Matches (z.B. eine Banktx zahlt 2 Rechnungen) wird das Icon ausgeblendet — stattdessen rendert das Match-Sheet die Liste der gematchten Rechnungen.

### Decision 4: Backend-Field für Listing

`BankTransactionType` braucht für die Listen-Queries:
- `matchStatus: 'open' | 'partial' | 'paid'` (computed)
- `matchCount: int`
- `totalMatched: Decimal` (bereits über `transactionMatchDetails` verfügbar)

Einfachste Lösung: ein neues nested Object `matchSummary` in der Listen-Query, mit zwei zusätzlichen Spalten gegenüber `matchedInvoice` (das nur den ersten Match referenziert).

## Risks / Trade-offs

- **[Risk]** Performance: Jeder Tx-Listing-Eintrag berechnet jetzt aggregate. Bei 1000 Tx pro Page = 1000 Aggregations.
  → **Mitigation**: SQL-Aggregat in einem Subquery pro Page, nicht in Loops. Bestehende `prefetch_related("invoice_matches")` reicht in Django, wenn Sum lokal in Python ausgeführt wird.
- **[Trade-off]** Verlust des "Color-Hint" auf dem Action-Icon. Akzeptiert — Status-Pill ist deutlich expliziter.

## Migration Plan

- Schritt 1: Backend-Schema erweitert um `matchSummary`-Feld auf `BankTransactionType`.
- Schritt 2: Frontend liest neues Feld; alte `matchedInvoice`-Logik bleibt für `FileText`-Link.
- Schritt 3: Neue Pill-Komponente in `BankingPage.tsx` und `CounterpartyDetailPage.tsx`.
- Schritt 4: Alte blau/grau-Klassen entfernt.

## Open Questions

- Sollen Pills auch in `CounterpartyDetailPage`'s Saldo-Tabelle erscheinen? → Ja, gleiche Komponente, bessere Konsistenz.

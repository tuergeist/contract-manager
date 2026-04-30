## Context

`TransactionMatchSheet` zeigt drei Sektionen: Match-Liste (oben), Suggested Matches (Mitte), Search (unten). Wenn `suggestedInvoiceMatches` leer zurückkommt (kein verlinkter Customer / keine Counterparty), bleibt die Mitte leer. User glaubt: "keine Rechnungen vorhanden", obwohl es 50 ungematchte gibt — er müsste nur zu suchen anfangen.

## Goals

- Sinnvolle Default-Liste statt leerem Block
- Zeigen, dass das System weiß "es gibt diese Rechnungen, ich kann sie dir nicht spezifisch zuordnen"
- Performance: keine zusätzlichen Roundtrips wenn Suggestions schon da sind

## Non-Goals

- Smarter Ranking-Algorithmus (kommt später mit ML-Match-Scoring)
- Auto-Vorauswahl

## Decisions

### Decision 1: Reuse `searchInvoicesForMatching` mit leerem Such-String

Resolver akzeptiert heute `search` als optional. Wir erweitern ihn um einen Parameter `defaultRecent: bool = false`. Wenn `defaultRecent=true` und `search` leer ist, gibt der Resolver bis zu 10 ungematchte Rechnungen der letzten 30 Tage zurück, sortiert nach Datum desc.

Vorteile: ein Resolver, kein neuer GraphQL-Endpoint, gleiche Berechtigungs-/Filter-Logik.

### Decision 2: Auswahl-Kriterien für "recent unmatched"

- **Debit-Tx** (User zahlt eine Lieferantenrechnung): Eingangsrechnungen `extraction_status in (extracted, confirmed)` ohne aktive Zahlungsmatches
- **Credit-Tx** (Kunde zahlt uns): Ausgangsrechnungen mit `total_amount > sum(matches)` (also offene Beträge)

### Decision 3: Sichtbare Headline ändert sich

```
if (suggestions.items.length > 0) → "Vorgeschlagene Treffer"
else if (defaultList.length > 0)  → "Letzte ungematchte Rechnungen"
else                              → leere Zustand mit "Keine Rechnungen — bitte suchen"
```

### Decision 4: Übergang von Default-Liste zu Such-Ergebnis

Sobald User ≥ 2 Zeichen tippt, ersetzt die Such-Liste die Default-Liste. Ein-Zeichen-Eingaben führen nicht zu unnötigen Roundtrips. Beim Löschen der Suche kommt die Default-Liste zurück.

## Risks / Trade-offs

- **[Risk]** Default-Liste mit 10 Items irritiert wenn keine davon passt.
  → **Mitigation**: Klare Headline "Letzte ungematchte Rechnungen — bitte prüfen oder suchen", plus Hint "+ N weitere".
- **[Trade-off]** 30-Tage-Fenster ist arbiträr. Akzeptiert — 90 % der zu matchenden Rechnungen sind unter 30 Tage alt.

## Migration Plan

Reine Frontend + Backend-Resolver-Erweiterung. Kein Schema-Bruch.

## Open Questions

- Soll die Default-Liste auf Counterparty filtern, wenn die Tx eine bekannte Counterparty hat aber keine Customer-Verbindung? → Ja: wenn Counterparty bekannt → Default-Liste kann auf `counterparty=...` filtern (für eingehende Rechnungen).

## Context

Backend kennt 6 Statuswerte für `IncomingInvoice.extraction_status`: `pending`, `extracting`, `extracted`, `confirmed`, `matched`, `extraction_failed`. Im Frontend werden diese 1:1 als Badges gerendert — der User muss verstehen, was technisch zwischen "extracting" und "extracted" steht. Aus Anwendersicht zählt nur: ist da Arbeit für mich, ja oder nein, und wo?

## Goals

- Mentale Komplexität reduzieren von 6 auf 3 sichtbare Zustände
- Backend-Schema unverändert lassen (Frontend-only Mapping)
- Filter-Dropdown analog vereinfachen

## Non-Goals

- Backend-Status-Modell ändern
- Status-Migration für historische Datensätze

## Decisions

### Decision 1: Mapping-Tabelle (Frontend-Konstante)

```ts
type DisplayStatus = 'inProgress' | 'review' | 'ready' | 'done' | 'error'

function mapStatus(s: BackendStatus): DisplayStatus {
  switch (s) {
    case 'pending':
    case 'extracting':       return 'inProgress'
    case 'extracted':        return 'review'
    case 'confirmed':        return 'ready'
    case 'matched':          return 'done'
    case 'extraction_failed':return 'error'
  }
}
```

`'inProgress'` rendert kein Badge sondern einen kleinen Spinner — verhindert visuelles Rauschen bei lauter laufender AI-Extraktion.

### Decision 2: Color-Coding

| DisplayStatus | Farbe | Label DE | Label EN |
|---|---|---|---|
| inProgress | (Spinner) | – | – |
| review | gelb | "Prüfen" | "Review" |
| ready | blau | "Bereit" | "Ready" |
| done | grün | "Erledigt" | "Done" |
| error | rot | "Fehler" | "Error" |

### Decision 3: Filter-Dropdown

Statt 6 Optionen jetzt 4 + 1 Toggle:
- "Alle"
- "Prüfen" (review)
- "Bereit" (ready)
- "Erledigt" (done)
- Toggle "Auch fehlerhafte zeigen" (default: on)

`inProgress` wird nicht in den Filter aufgenommen — der User braucht nur lesen, AI arbeitet ohnehin nicht lange genug, um zu filtern.

### Decision 4: Backend-Filter weiterhin nach Backend-Status

Filter-Logik im Backend bleibt unverändert (akzeptiert weiter `pending`/`extracted`/`confirmed`/`matched`). Der Frontend-Filter mapt die User-Wahl auf 1–N Backend-Werte:
- "Prüfen" → `extracted`
- "Bereit" → `confirmed`
- "Erledigt" → `matched`
- "Fehler" → `extraction_failed`

Die `pending` und `extracting` States werden immer ausgeblendet außer bei "Alle".

## Risks / Trade-offs

- **[Risk]** Bestehende Bookmarks / Deep-Links mit `?status=extracted` brechen.
  → **Mitigation**: Backend-Param-Werte bleiben gültig; nur das UI-Mapping ändert sich. Filter-Dropdown akzeptiert beide Werte vorübergehend (Backwards-compat-Mapping in Querystring-Reader).
- **[Trade-off]** "Extraction failed" ist konzeptuell auch "Prüfen" — könnte man zusammenführen. Wir trennen, weil bei Fehler ein expliziter Retry-Button sinnvoller ist als ein Confirm.

## Migration Plan

Reine Frontend-Änderung. Bei Roll-out optional: einmaliger Toast "Status-Anzeige vereinfacht — Details unter Hilfe" zur User-Information (low priority).

## Open Questions

- Keine.

## Context

Heute öffnet `IncomingInvoicesPage` ein `IncomingInvoiceDetail`-Sheet (Shadcn `Sheet`-Component) mit der per `selectedId` gesteuerten Detail-Ansicht. Nach `Confirm` (das nur `confirmIncomingInvoice`-Mutation aufruft und `extraction_status` setzt) bleibt `selectedId` gesetzt, das Sheet offen, der User muss schließen und manuell neu navigieren.

Die Listen-Query `INCOMING_INVOICES` liefert paginated Items mit Sortierung. Beim Confirm-Klick lädt nur die Mutation, kein Listen-Refetch passiert nicht direkt (der Parent macht `onUpdate={() => refetch()}`).

## Goals

- Ein Klick → confirm + zur nächsten pending Rechnung
- Sheet schließt automatisch wenn keine pending mehr da
- Funktioniert respektvoll mit dem aktuellen Filter/Sort der Page (kein "magisches" Springen außerhalb der sichtbaren Selektion)
- Keyboard-Shortcut `Cmd/Ctrl + Enter`

## Non-Goals

- Backend-Änderung — die "next id"-Logik ist client-seitig
- Vorausladen kompletter Rechnungs-Detail-Daten für alle pending Items (keep it simple)
- Cross-Page-Navigation (z.B. zur nächsten Page wenn die aktuelle leer ist) — vorerst nur innerhalb der geladenen Items

## Decisions

### Decision 1: Next-ID per `pendingIds`-Array vom Parent

Page hat bereits die Listen-Daten. Statt einer separaten Query lasse ich die Page einen sortierten Array der pending IDs an das Detail-Sheet weitergeben:

```tsx
<IncomingInvoiceDetail
  id={selectedId}
  pendingIds={pendingIds}      // ['id1', 'id2', 'id3', ...]
  onClose={...}
  onUpdate={() => refetch()}
/>
```

Im Sheet:
```tsx
const currentIdx = pendingIds.indexOf(id)
const nextId = currentIdx >= 0 && currentIdx < pendingIds.length - 1
  ? pendingIds[currentIdx + 1]
  : null
```

**Alternative**: GraphQL-Query `nextPendingIncomingInvoice(currentId)`. Verworfen — extra Roundtrip, doppelte Sortier-Logik.

### Decision 2: "pending" = `extracted | confirmed-without-cp`

Was zählt als "muss noch bearbeitet werden"? Aktuelle Status-Definitionen:
- `pending`/`extracting`: AI arbeitet — nicht zeigbar
- `extracted`: AI fertig, User muss bestätigen → **ja, pending**
- `confirmed`: User hat bestätigt, keine CP zugeordnet → **ja, pending** (CP fehlt)
- `matched`: erledigt → nein

Das `pendingIds`-Array filtert auf diese zwei States. Wenn der User eine Confirm-Aktion durchführt und die Rechnung dann ohne CP confirmed bleibt, kann sie wieder im Array auftauchen — was OK ist (sie braucht ja noch was).

**Verfeinerung**: Wir stoppen den Loop, wenn die *gleiche* ID nochmal kommt — sonst Endlos-Schleife bei "confirm ohne CP".

### Decision 3: Auto-Close-Toast statt stilles Schließen

Wenn keine pending mehr da, schließt das Sheet und wir zeigen Toast: "Alle eingehenden Rechnungen bearbeitet ✓". Macht User-feedback explizit.

### Decision 4: Keyboard-Shortcut nur wenn Focus im Sheet

`useHotkeys`-Pattern oder simpler `keydown`-Listener. Shortcut `Cmd/Ctrl+Enter` triggert "Confirm + Next". Reine `Enter` triggert nicht (verhindert Doppel-Submit, weil Inputs `Enter` schon abfangen).

## Risks / Trade-offs

- **[Risk]** User scrollt Liste, Filter ändert sich → `pendingIds` ist stale, "next" überrascht
  → **Mitigation**: Page passes immer aktuell sortiertes Array; bei Refetch wird das Array automatisch erneuert. Wenn gerade ein Confirm läuft und die Liste sich währenddessen ändert, ist das ein seltener Race-Case → akzeptiert.
- **[Risk]** User confirmt, Rechnung bleibt aber "needs CP" und springt sofort wieder rein — wirkt wie ein Bug
  → **Mitigation**: Die Rechnung wird nach Confirm aus dem aktuellen `pendingIds`-Array genommen (lokal), erst beim nächsten Refetch potentiell wieder rein. Verhindert Endlos-Loop.
- **[Trade-off]** Pagination: Wenn `pendingIds` nur die aktuelle Page enthält, hört der Loop am Page-Ende auf. Akzeptiert — User kann nächste Page laden und neu starten. Alternative wäre, alle pending-Items auf einmal vom Backend zu holen — overkill für einen UX-Quick-Win.

## Migration Plan

Reine Frontend-Änderung. Kein Feature-Flag nötig. Roll-out: deploy → User merken sofort den neuen Button. Bei Beschwerden: Button ausblenden via `if (false)`-Patch (sehr unwahrscheinlich).

## Open Questions

- Sollte der "Confirm + Next"-Button auch einen Match auslösen, wenn eindeutiger Kandidat existiert? → Verschoben auf Change `confirm-and-match-mutation` (#9), das hier einbezogen werden kann.

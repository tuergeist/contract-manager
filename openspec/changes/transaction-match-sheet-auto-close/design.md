## Context

Im `TransactionMatchSheet` ruft der User `createMatch` (oder eine der drei Varianten für imported / record / incoming). Nach Mutation-Success ruft das Sheet `refetch()` und `refetchSuggestions()` — bleibt aber offen. Bei Massen-Matching (10+ Tx pro Session) sind das 10+ unnötige manuelle Closes.

Das Sheet zeigt bereits einen "Fully matched"-Indikator (Total Matched + grünes Banner). Es fehlt nur noch die Aktion: schließen + sanftes Feedback.

## Goals

- Bei vollem Match (`abs(amount) - totalMatched < 0.01`) das Sheet automatisch schließen
- Klein bisschen Verzögerung (~400ms), damit der User die "Fully matched"-Bestätigung sehen kann
- User kann auto-close in seinen Settings deaktivieren

## Non-Goals

- Auto-Close bei Teilmatch — User soll bewusst die Differenz auflösen
- "Nächste ungematchte Tx automatisch öffnen" — kommt mit der Inbox-Page, nicht hier
- Backend-Änderungen

## Decisions

### Decision 1: Schwelle für "fully matched"

Direkt aus der bestehenden `difference`-Field auf `TransactionMatchDetailsType` ableitbar — wenn `Math.abs(parseFloat(difference)) < 0.01` → fully matched. Schwelle 0.01 entspricht 1 Cent, deckt Float-Rundung ab.

### Decision 2: Delay 400ms

Empirisch: 200ms ist nicht wahrnehmbar (User glaubt es war ein Bug), 800ms ist nervig. 400ms ist die Goldlocke — User sieht die grüne Bestätigung kurz, dann fadet das Sheet sauber raus.

### Decision 3: Setting per User, Default "an"

Neue Boolean-Spalte in `User.settings` (JSON-Field, dort lassen sich Preferences ohne Migration ergänzen): `auto_close_match_sheet: true`. UI: Toggle in `UserSettings`. Per-Tenant-Override unnötig — ist persönliche Präferenz.

### Decision 4: Toast bei auto-close

"Match gespeichert" + Aktion-Link "rückgängig" (5s, ruft `deletePaymentMatch` mit der ID des gerade erstellten Matches). Niedrige Implementierungskosten, hohe Sicherheit gegen Fehlmatches.

## Risks / Trade-offs

- **[Risk]** User klickt versehentlich, Sheet schließt, Match falsch.
  → **Mitigation**: 5s Undo-Toast.
- **[Risk]** Race: User setzt zweiten Match während des 400ms-Delay → Sheet versucht zu schließen, bevor neue Mutation läuft.
  → **Mitigation**: Im `setTimeout`-Callback erneut prüfen, ob Sheet noch "fully matched" ist (state könnte sich geändert haben). Sonst Close abbrechen.
- **[Trade-off]** Setting-UI für ein einziges Feature wirkt overkill. Akzeptiert — Setting bleibt klein, kann später durch andere Match-Settings erweitert werden.

## Migration Plan

- Frontend-Only-Change.
- Setting-Default ist "an" — User die das nicht wollen, schalten es im Settings-Tab ab.

## Open Questions

- Sollte der Undo-Toast auch beim manuellen Close erscheinen? → Nein, Konsistenz: Undo nur bei nicht-explizitem Close.

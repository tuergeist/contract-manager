## Why

Offene Rechnungen werden aktuell zwar erkannt (Zahlungszuordnung pro Kunde/Vertrag und global), aber es gibt keinen Weg, säumige Kunden aus dem Contract Manager heraus zu mahnen. Mahnungen werden außerhalb des Systems erstellt, ohne Bezug zur Rechnung und ohne nachvollziehbare Historie. Wir brauchen einen integrierten, manuell ausgelösten Mahnprozess mit Eskalationsstufen, Vorlagen und vollständiger Sichtbarkeit am Rechnungs-, Kunden- und Vertragsobjekt.

## What Changes

- Neue **Mahnung**-Entität: eine Mahnung gehört zu genau einer Rechnung; erfasst Mahnstufe, generiertes PDF, Versandstatus und Zeitpunkt.
- **Mehrstufige Mahnungen** (Zahlungserinnerung + 1./2./3. Mahnung) mit Eskalations-Tracking pro Rechnung — die nächste fällige Stufe wird je Rechnung vorgeschlagen. Der Titel jeder Stufe ist in der Vorlage frei festlegbar.
- **Zahlungsziel** je Rechnung: konfigurierbar global, pro Kunde und pro Vertrag; bestimmt Fälligkeit und damit Verzug.
- **Manueller Auslöser**: aus der Rechnungsübersicht / Kundenansicht werden Rechnungen ab einem konfigurierbaren Verzugs-Schwellwert (X Tage) als mahnfähig angezeigt; der User wählt eine Rechnung und löst die Mahnung aus.
- **Vorlagen DE/EN** mit vorbefülltem Text je Mahnstufe; der User kann den Text vor Versand anpassen.
- **Mahngebühren & Verzugszinsen**: konfigurierbar (z. B. BGB-Pauschale + Zinssatz); pro Mahnung einzeln an-/abwählbar.
- **Ausgabe**: Mahn-PDF wird generiert UND per E-Mail versendet (bestehende E-Mail-Infrastruktur).
- **Verzugsspalte** (Tage überfällig) in allen Rechnungsübersichten; ab konfigurierbarem Schwellwert wird der Wert rot dargestellt.
- **Sichtbarkeit**: Mahnungen erscheinen im Rechnungsverlauf sowie in der Kunden- und Vertragsansicht, inkl. Zuordnung zu den gemahnten Rechnungen.
- **Permissions**: neue Permission "Mahnen" (Mahnung erstellen/versenden) und neue Permission "Mahn-Einstellungen" (Vorlagen, Zinssatz, Gebühren). Mahnungen ansehen erfordert keine eigene Permission — wer Rechnungen sehen darf, sieht auch Mahnungen.

## Capabilities

### New Capabilities

- `payment-reminders`: Mahnung-Entität und -Workflow — mehrstufige Mahnungen pro Rechnung, PDF-Generierung, E-Mail-Versand, Eskalations-Tracking, Sichtbarkeit in Rechnungsverlauf/Kunden-/Vertragsansicht, neue Permission "Mahnen".
- `payment-reminder-settings`: Konfiguration für Mahnwesen — Vorlagen DE/EN je Mahnstufe, Verzugszinssatz, Mahngebühren, Verzugs-Schwellwert für Mahnfähigkeit und Rot-Schwelle der Verzugsspalte; neue Permission "Mahn-Einstellungen".
- `invoice-overdue-column`: Verzugsspalte (Tage überfällig) in allen Rechnungsübersichten, rote Hervorhebung ab konfigurierbarem Schwellwert.

### Modified Capabilities

<!-- Keine Anforderungsänderungen an bestehenden Specs. Neue Permissions sind Teil der neuen Specs; RBAC-Framework bleibt unverändert. -->

## Impact

- **Backend**: neues Mahnung-Model in `apps/contracts` (oder neue App) mit FK auf genau eine Rechnung; neue Settings-Felder am Tenant für Zinssatz/Gebühren/Schwellwerte; Migrations.
- **GraphQL**: neue Types/Mutations (Mahnung erstellen, versenden), neue Queries (Mahnungen pro Rechnung/Kunde/Vertrag), Verzugstage als Feld auf Invoice-Type.
- **PDF**: neuer Mahn-PDF-Generator analog zur Rechnungs-PDF-Erzeugung.
- **E-Mail**: Nutzung der bestehenden E-Mail-Versand-Infrastruktur (`email-sending` / `smtp-mail-service`).
- **Permissions/RBAC**: zwei neue Permissions in `role-based-access-control` registrieren; Rollen-/Permission-UI muss sie anzeigen.
- **Frontend**: neue Mahn-Auslöse-UI (Auswahl mahnfähiger Rechnungen, Stufe, Gebühr-Toggle, Textanpassung), Verzugsspalte in allen Rechnungstabellen, Mahnungs-Anzeige in Rechnungsdetail / Kundendetail / Vertragsdetail, neue Settings-Tab-Sektion.
- **i18n**: deutsche und englische Übersetzungen für UI und Vorlagentexte.
- **Sidebar-Suche**: neue Settings-Sektion in `searchablePages` ergänzen.

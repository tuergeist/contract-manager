## ADDED Requirements

### Requirement: Mahnvorlagen je Sprache und Stufe

Das System SHALL Mahnvorlagen pro Sprache (de/en) und pro Mahnstufe (0–3) verwalten. Jede Vorlage MUST aus einem frei festlegbaren Titel, einem E-Mail-Betreff und einem Textkörper bestehen. Fehlt eine tenant-spezifische Vorlage, MUST eine eingebaute Standardvorlage verwendet werden.

#### Scenario: Vorlage bearbeiten

- **WHEN** ein berechtigter Benutzer Titel, Betreff oder Text einer Vorlage für eine Sprache und Stufe speichert
- **THEN** verwendet das System diese Vorlage bei künftigen Mahnungen dieser Sprache und Stufe

#### Scenario: Fehlende Vorlage fällt auf Standard zurück

- **WHEN** für eine Sprache und Stufe keine tenant-spezifische Vorlage existiert
- **THEN** verwendet das System die eingebaute Standardvorlage

#### Scenario: Stufentitel ist frei wählbar

- **WHEN** ein Benutzer den Titel der Vorlage für Stufe 0 auf „Freundliche Zahlungserinnerung" setzt
- **THEN** erscheint dieser Titel als Überschrift im Mahn-PDF von Stufe-0-Mahnungen

### Requirement: Verzugszinssatz konfigurieren

Das System SHALL einen tenant-weiten Verzugszinssatz (Jahresprozentsatz) konfigurierbar machen, der zur Vorberechnung der Verzugszinsen einer Mahnung verwendet wird.

#### Scenario: Zinssatz wird gesetzt

- **WHEN** ein berechtigter Benutzer den Verzugszinssatz speichert
- **THEN** verwendet das System diesen Satz zur Vorberechnung der Verzugszinsen neuer Mahnungen

### Requirement: Mahngebühren je Stufe konfigurieren

Das System SHALL eine Mahngebühr pro Mahnstufe (0–3) konfigurierbar machen, die als Vorschlagswert beim Erstellen einer Mahnung herangezogen wird.

#### Scenario: Gebühr je Stufe wird gesetzt

- **WHEN** ein berechtigter Benutzer für Stufe 2 eine Mahngebühr von 5,00 € speichert
- **THEN** schlägt das System beim Erstellen einer Stufe-2-Mahnung 5,00 € als Mahngebühr vor

### Requirement: Zahlungsziel konfigurieren

Das System SHALL ein Zahlungsziel in Tagen auf drei Ebenen verwalten: ein tenant-weiter Default, ein optionaler Wert pro Kunde und ein optionaler Wert pro Vertrag. Bei der Rechnungserstellung MUST das Zahlungsziel in der Reihenfolge Vertrag, dann Kunde, dann globaler Default aufgelöst und als Fälligkeitsdatum der Rechnung gespeichert werden.

#### Scenario: Globaler Default greift

- **WHEN** weder Vertrag noch Kunde ein Zahlungsziel gesetzt haben und eine Rechnung erstellt wird
- **THEN** verwendet das System den globalen Default zur Berechnung des Fälligkeitsdatums

#### Scenario: Vertragswert übersteuert Kundenwert

- **WHEN** sowohl Kunde als auch Vertrag ein Zahlungsziel gesetzt haben und eine Rechnung des Vertrags erstellt wird
- **THEN** verwendet das System das Zahlungsziel des Vertrags

#### Scenario: Kundenwert greift ohne Vertragswert

- **WHEN** der Kunde ein Zahlungsziel gesetzt hat, der Vertrag jedoch nicht
- **THEN** verwendet das System das Zahlungsziel des Kunden

### Requirement: Verzugs-Schwellwerte konfigurieren

Das System SHALL zwei tenant-weite Schwellwerte in Verzugstagen konfigurierbar machen: einen Mahnfähig-Schwellwert, ab dem eine Rechnung gemahnt werden kann, und einen Rot-Schwellwert, ab dem die Verzugstage in Rechnungsübersichten rot dargestellt werden.

#### Scenario: Mahnfähig-Schwellwert wird gesetzt

- **WHEN** ein Benutzer den Mahnfähig-Schwellwert auf 30 Tage setzt
- **THEN** werden Rechnungen erst ab 30 Verzugstagen als mahnfähig angezeigt

#### Scenario: Rot-Schwellwert wird gesetzt

- **WHEN** ein Benutzer den Rot-Schwellwert auf 14 Tage setzt
- **THEN** werden Verzugstage ab 14 in Rechnungsübersichten rot dargestellt

### Requirement: Berechtigung für Mahn-Einstellungen

Das System SHALL das Bearbeiten von Mahnvorlagen, Zinssatz, Mahngebühren, Zahlungsziel-Default und Verzugs-Schwellwerten auf Benutzer mit der Permission `reminders.settings` beschränken.

#### Scenario: Benutzer ohne Einstellungs-Permission

- **WHEN** ein Benutzer ohne `reminders.settings` versucht, eine Mahn-Einstellung zu speichern
- **THEN** verweigert das System die Aktion mit einem Berechtigungsfehler

#### Scenario: Mahnen ohne Einstellungs-Permission

- **WHEN** ein Benutzer die Permission `reminders.send`, jedoch nicht `reminders.settings` besitzt
- **THEN** kann er Mahnungen versenden, aber keine Mahn-Einstellungen bearbeiten

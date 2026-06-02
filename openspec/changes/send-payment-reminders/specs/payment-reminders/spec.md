## ADDED Requirements

### Requirement: Mahnfähige Rechnungen identifizieren

Das System SHALL eine Rechnung als mahnfähig kennzeichnen, wenn sie nicht bezahlt ist (`is_paid == false`), nicht storniert/voided ist und ihre Verzugstage den konfigurierten Mahnfähig-Schwellwert erreichen oder überschreiten.

#### Scenario: Rechnung erreicht Mahnfähig-Schwelle

- **WHEN** eine unbezahlte Rechnung den konfigurierten Mahnfähig-Schwellwert an Verzugstagen erreicht
- **THEN** wird die Rechnung in der Rechnungsübersicht als mahnfähig markiert und kann gemahnt werden

#### Scenario: Bezahlte Rechnung ist nicht mahnfähig

- **WHEN** eine Rechnung mindestens einen Zahlungs-Match besitzt (`is_paid == true`)
- **THEN** wird sie nicht als mahnfähig angezeigt, unabhängig von ihren Verzugstagen

### Requirement: Mahnung erstellen

Das System SHALL es einem berechtigten Benutzer ermöglichen, zu genau einer mahnfähigen Rechnung eine Mahnung als Entwurf zu erstellen. Der Entwurf MUST mit dem Vorlagentext der zutreffenden Sprache und Mahnstufe sowie mit vorberechneten Werten für Mahngebühr und Verzugszinsen vorbefüllt sein.

#### Scenario: Entwurf wird vorbefüllt

- **WHEN** ein berechtigter Benutzer für eine mahnfähige Rechnung eine Mahnung anlegt
- **THEN** liefert das System einen Entwurf mit Titel, Betreff und Text aus der Vorlage der Rechnungssprache und der vorgeschlagenen Mahnstufe sowie mit vorberechneter Mahngebühr und Verzugszinsen

#### Scenario: Mahnung gehört zu genau einer Rechnung

- **WHEN** eine Mahnung erstellt wird
- **THEN** ist sie genau einer Rechnung zugeordnet und es können nicht mehrere Rechnungen in einer Mahnung gebündelt werden

### Requirement: Mehrstufige Eskalation

Das System SHALL Mahnstufen von 0 bis 3 unterstützen (Stufe 0 = Zahlungserinnerung, Stufen 1–3 = 1./2./3. Mahnung) und als nächste Stufe `höchste bisherige Stufe der Rechnung + 1` vorschlagen, beginnend bei 0 und begrenzt auf 3. Der Benutzer MUST die vorgeschlagene Stufe überschreiben können.

#### Scenario: Nächste Stufe wird vorgeschlagen

- **WHEN** für eine Rechnung bereits eine Mahnung der Stufe 1 versendet wurde und der Benutzer eine neue Mahnung anlegt
- **THEN** schlägt das System Stufe 2 vor

#### Scenario: Erste Mahnung einer Rechnung

- **WHEN** für eine Rechnung noch keine Mahnung existiert
- **THEN** schlägt das System Stufe 0 (Zahlungserinnerung) vor

#### Scenario: Stufe ist überschreibbar

- **WHEN** das System Stufe 2 vorschlägt
- **THEN** kann der Benutzer im Auslöse-Dialog eine andere Stufe (z. B. erneut Stufe 1) auswählen

### Requirement: Mahntext vor Versand anpassen

Das System SHALL es dem Benutzer ermöglichen, Betreff und Text der Mahnung vor dem Versand zu bearbeiten. Der finale Text MUST auf der Mahnung gespeichert werden.

#### Scenario: Benutzer ändert den Text

- **WHEN** ein Benutzer den vorbefüllten Mahntext im Auslöse-Dialog bearbeitet und die Mahnung versendet
- **THEN** verwendet das System den bearbeiteten Text in PDF und E-Mail und speichert ihn auf der Mahnung

### Requirement: Mahngebühr und Verzugszinsen pro Mahnung steuern

Das System SHALL Mahngebühr und Verzugszinsen pro Mahnung einzeln an- und abwählbar machen. Die tatsächlich verwendeten Beträge sowie der zugrunde liegende Zinssatz und die Verzugstage MUST als Snapshot auf der Mahnung gespeichert werden, sodass spätere Einstellungsänderungen historische Mahnungen nicht verändern.

#### Scenario: Benutzer wählt Gebühr ab

- **WHEN** ein Benutzer beim Erstellen einer Mahnung die Mahngebühr deaktiviert
- **THEN** wird die Mahnung ohne Gebührenbetrag erstellt und versendet

#### Scenario: Werte werden als Snapshot gespeichert

- **WHEN** eine Mahnung mit Verzugszinsen versendet wurde und danach der Zinssatz in den Einstellungen geändert wird
- **THEN** bleibt der auf der versendeten Mahnung gespeicherte Zinsbetrag unverändert

### Requirement: Mahn-PDF erzeugen

Das System SHALL beim Versand einer Mahnung ein PDF-Dokument erzeugen, das Firmen-Rechtsdaten, Logo und Akzentfarbe des Tenants verwendet und den Stufentitel aus der Vorlage als Überschrift trägt. Das PDF MUST auf der Mahnung referenziert werden.

#### Scenario: PDF wird erzeugt und referenziert

- **WHEN** eine Mahnung versendet wird
- **THEN** erzeugt das System ein Mahn-PDF mit dem konfigurierten Stufentitel als Überschrift und speichert die Referenz auf der Mahnung

### Requirement: Mahnung per E-Mail versenden

Das System SHALL die Mahnung per E-Mail an die Rechnungsempfänger versenden, mit dem Mahn-PDF als Anhang. Der Versand MUST asynchron erfolgen; Versandzeitpunkt und Empfänger MUST nach erfolgreichem Versand auf der Mahnung gespeichert werden.

#### Scenario: Erfolgreicher Versand

- **WHEN** ein Benutzer eine Mahnung versendet
- **THEN** stellt das System die E-Mail mit PDF-Anhang zu und speichert Versandzeitpunkt und Empfänger auf der Mahnung

#### Scenario: Versand schlägt fehl

- **WHEN** der E-Mail-Versand fehlschlägt
- **THEN** wird die Mahnung nicht als versendet markiert und der Versand bleibt erneut auslösbar

### Requirement: Rechnungsstatus bei Mahnung

Das System SHALL den Rechnungsstatus auf `DUNNING` setzen, sobald die erste Mahnung zu der Rechnung erfolgreich versendet wurde. Sobald die Rechnung später vollständig bezahlt ist, MUST der Status auf `PAID` gesetzt werden.

#### Scenario: Status wird auf DUNNING gesetzt

- **WHEN** die erste Mahnung zu einer Rechnung erfolgreich versendet wird
- **THEN** wechselt der Rechnungsstatus auf `DUNNING`

#### Scenario: Zahlung setzt DUNNING zurück

- **WHEN** einer gemahnten Rechnung eine Zahlung zugeordnet wird und die Rechnung dadurch vollständig bezahlt ist
- **THEN** wechselt der Rechnungsstatus von `DUNNING` auf `PAID`

### Requirement: Versand für bezahlte Rechnung verhindern

Das System SHALL unmittelbar vor dem Versand einer Mahnung erneut prüfen, ob die Rechnung bezahlt ist, und den Versand abbrechen, wenn die Rechnung inzwischen bezahlt wurde.

#### Scenario: Rechnung wurde zwischenzeitlich bezahlt

- **WHEN** zwischen Erstellung und Versand einer Mahnung der Rechnung eine Zahlung zugeordnet wurde
- **THEN** bricht das System den Versand ab und meldet, dass die Rechnung bereits bezahlt ist

### Requirement: Mahnungen sichtbar machen

Das System SHALL versendete Mahnungen im Rechnungsverlauf der Rechnung sowie in der Kunden- und Vertragsansicht anzeigen. Jede angezeigte Mahnung MUST ihre zugeordnete Rechnung, Mahnstufe und ihren Versandzeitpunkt erkennen lassen.

#### Scenario: Mahnung im Rechnungsverlauf

- **WHEN** ein Benutzer die Detailansicht einer gemahnten Rechnung öffnet
- **THEN** sieht er alle zu dieser Rechnung versendeten Mahnungen mit Stufe und Versandzeitpunkt

#### Scenario: Mahnung in der Kundenansicht

- **WHEN** ein Benutzer die Kunden- oder Vertragsansicht öffnet
- **THEN** sieht er die zugehörigen Mahnungen inklusive der jeweils gemahnten Rechnung

### Requirement: Berechtigung zum Mahnen

Das System SHALL das Erstellen und Versenden von Mahnungen auf Benutzer mit der Permission `reminders.send` beschränken. Das Ansehen von Mahnungen MUST keine eigene Permission erfordern und für jeden Benutzer mit `invoices.read` möglich sein.

#### Scenario: Benutzer ohne Mahn-Permission

- **WHEN** ein Benutzer ohne `reminders.send` versucht, eine Mahnung zu erstellen oder zu versenden
- **THEN** verweigert das System die Aktion mit einem Berechtigungsfehler

#### Scenario: Mahnungen ansehen ohne Mahn-Permission

- **WHEN** ein Benutzer mit `invoices.read`, aber ohne `reminders.send`, eine Rechnung öffnet
- **THEN** sieht er die zu der Rechnung versendeten Mahnungen

### Requirement: Mahnung im Audit-Log

Das System SHALL den erfolgreichen Versand einer Mahnung im Audit-Log erfassen, mit Rechnungsbezug, Mahnstufe, auslösendem Benutzer und Zeitpunkt.

#### Scenario: Versand wird protokolliert

- **WHEN** eine Mahnung erfolgreich versendet wurde
- **THEN** existiert ein Audit-Log-Eintrag mit Rechnung, Mahnstufe, Benutzer und Zeitpunkt

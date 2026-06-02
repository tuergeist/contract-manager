## ADDED Requirements

### Requirement: Verzugstage berechnen

Das System SHALL für jede Rechnung die Verzugstage als Anzahl der Tage zwischen dem Fälligkeitsdatum und dem heutigen Tag bereitstellen. Ist die Rechnung bezahlt oder noch nicht fällig, MUST der Wert 0 betragen.

#### Scenario: Überfällige unbezahlte Rechnung

- **WHEN** das Fälligkeitsdatum einer unbezahlten Rechnung 12 Tage zurückliegt
- **THEN** weist das System 12 Verzugstage aus

#### Scenario: Bezahlte Rechnung hat keinen Verzug

- **WHEN** eine Rechnung bezahlt ist
- **THEN** weist das System 0 Verzugstage aus, unabhängig vom Fälligkeitsdatum

#### Scenario: Noch nicht fällige Rechnung

- **WHEN** das Fälligkeitsdatum einer Rechnung in der Zukunft liegt
- **THEN** weist das System 0 Verzugstage aus

### Requirement: Verzugsspalte in allen Rechnungsübersichten

Das System SHALL in jeder Rechnungsübersicht eine Spalte „Verzug" mit den Verzugstagen der jeweiligen Rechnung anzeigen.

#### Scenario: Verzugsspalte ist sichtbar

- **WHEN** ein Benutzer eine Rechnungsübersicht öffnet
- **THEN** enthält die Tabelle eine Spalte „Verzug" mit den Verzugstagen je Rechnung

### Requirement: Verzugstage sortierbar

Das System SHALL die Verzugsspalte wie alle anderen Datenspalten durch Klick auf die Spaltenüberschrift sortierbar machen.

#### Scenario: Sortierung nach Verzug

- **WHEN** ein Benutzer auf die Überschrift der Verzugsspalte klickt
- **THEN** sortiert das System die Rechnungsübersicht nach Verzugstagen

### Requirement: Rote Hervorhebung ab Schwellwert

Das System SHALL die Verzugstage rot darstellen, sobald sie den konfigurierten Rot-Schwellwert erreichen oder überschreiten, und andernfalls in normaler Farbe.

#### Scenario: Verzug erreicht Rot-Schwellwert

- **WHEN** die Verzugstage einer Rechnung den konfigurierten Rot-Schwellwert erreichen oder überschreiten
- **THEN** stellt das System den Wert in der Verzugsspalte rot dar

#### Scenario: Verzug unter Rot-Schwellwert

- **WHEN** die Verzugstage einer Rechnung unter dem Rot-Schwellwert liegen
- **THEN** stellt das System den Wert in normaler Farbe dar

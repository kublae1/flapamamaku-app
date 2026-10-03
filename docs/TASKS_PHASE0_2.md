# Zentrale Aufgabenliste – Phase 0 bis Phase 2

Statuswerte: `OFFEN` · `IN ARBEIT` · `TESTBEREIT` · `GETESTET` · `FREIGEGEBEN`

## Phase 0 – Ausgangspunkt sichern

| ID | Aufgabe | Status |
|---|---|---|
| P0-01 | Masterplan im Repository dokumentieren | GETESTET |
| P0-02 | Baseline-Commit, App-Version und Architektur dokumentieren | GETESTET |
| P0-03 | Inhaltsquellen Server vs. Asset erfassen | GETESTET |
| P0-04 | bekannte Hardcodes/Testdaten erfassen | GETESTET |
| P0-05 | README auf tatsächlichen Projektstand bringen | GETESTET |

## Phase 1 – Datenfluss und Grundstabilität

| ID | Aufgabe | Status |
|---|---|---|
| P1-01 | Bei konfiguriertem Server keine lokalen Beispiel-News als Live-Inhalt anzeigen | GETESTET |
| P1-02 | Bei konfiguriertem Server keine lokalen Beispiel-Termine als Live-Inhalt anzeigen | GETESTET |
| P1-03 | Bei konfiguriertem Server keine lokalen Beispiel-Mitglieder als Live-Inhalt anzeigen | GETESTET |
| P1-04 | Logout darf bei Serverbetrieb keine Beispielinhalte im UI reaktivieren | GETESTET |
| P1-05 | Hero bei Serverbetrieb ausschliesslich aus Serverinhalt/neutralem Leerzustand beziehen | GETESTET |
| P1-06 | Mobile Admin-News von fest eingebauten Vereinsbildern entkoppeln | GETESTET |
| P1-07 | feste Markenbezeichnung in Biometrie-Texten entfernen | GETESTET |
| P1-08 | Speicher-/API-Fehler über benutzerfreundliche Meldungen ausgeben | GETESTET |
| P1-09 | manuelle Aktualisierung mit sichtbarem Sync-/Fehlerstatus vereinheitlichen | GETESTET |
| P1-10 | Tests für produktiven Servermodus vs. lokale Demo-Daten ergänzen | GETESTET |
| P1-11 | API-CRUD-Pfade für News, Termine, Mitglieder, Content/Sujet und Archiv in CI absichern | GETESTET |

## Phase 2 – Adminbereich als Vereins-CMS

| ID | Aufgabe | Status |
|---|---|---|
| P2-01 | PC-Admin-Navigation auf zentrale CMS-Bereiche prüfen/vereinheitlichen | GETESTET |
| P2-02 | Bearbeitungszustand (neu/bearbeiten) klar sichtbar machen | GETESTET |
| P2-03 | Löschen mit Bestätigung für zentrale Inhalte vereinheitlichen | GETESTET |
| P2-04 | Erfolg/Fehler/Uploadstatus als einheitlichen Status darstellen | GETESTET |
| P2-05 | Startseite/Hero im Medien-CMS eindeutig benennen und vorschauen | GETESTET |
| P2-06 | Sujet, Archiv, Fotoalben, Galerie, Dokumente und Links im Medien-CMS klar trennen | GETESTET |
| P2-07 | Telefon-/App-Vorschau auf die zentralen administrierbaren Inhalte ausrichten | GETESTET |
| P2-08 | Vereins- und Systemeinstellungen klar von Inhaltsverwaltung trennen | GETESTET |
| P2-09 | Admin-CMS-Bedienstruktur in einem automatischen Contract-Smoke-Test prüfen | GETESTET |
| P2-10 | Phase-2-Abnahme dokumentieren | GETESTET |

## Technische Gates

Der vollständige **Phase 0-2 Gate** wurde auf dem finalen Code-Stand erfolgreich ausgeführt. Abgedeckt sind:

- Phase-1-HTTP-/Persistenzvertrag,
- Phase-2-PC-CMS-Vertrag,
- `flutter analyze`,
- vollständige Flutter-Tests.

Die Einträge sind daher technisch als `GETESTET` abgeschlossen. `FREIGEGEBEN` bleibt eine separate produktive/businessseitige Entscheidung.

## Gesperrt

Alle Aufgaben aus Phase 3 oder später sind bis zur ausdrücklichen Freigabe gesperrt. Erkenntnisse dazu werden nur dokumentiert, nicht umgesetzt.

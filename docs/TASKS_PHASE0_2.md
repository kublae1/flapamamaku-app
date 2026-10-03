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
| P1-01 | Bei konfiguriertem Server keine lokalen Beispiel-News als Live-Inhalt anzeigen | TESTBEREIT |
| P1-02 | Bei konfiguriertem Server keine lokalen Beispiel-Termine als Live-Inhalt anzeigen | TESTBEREIT |
| P1-03 | Bei konfiguriertem Server keine lokalen Beispiel-Mitglieder als Live-Inhalt anzeigen | TESTBEREIT |
| P1-04 | Logout darf bei Serverbetrieb keine Beispielinhalte im UI reaktivieren | TESTBEREIT |
| P1-05 | Hero bei Serverbetrieb ausschliesslich aus Serverinhalt/neutralem Leerzustand beziehen | TESTBEREIT |
| P1-06 | Mobile Admin-News von fest eingebauten Vereinsbildern entkoppeln | TESTBEREIT |
| P1-07 | feste Markenbezeichnung in Biometrie-Texten entfernen | TESTBEREIT |
| P1-08 | Speicher-/API-Fehler über benutzerfreundliche Meldungen ausgeben | TESTBEREIT |
| P1-09 | manuelle Aktualisierung mit sichtbarem Sync-/Fehlerstatus vereinheitlichen | TESTBEREIT |
| P1-10 | Tests für produktiven Servermodus vs. lokale Demo-Daten ergänzen | TESTBEREIT |
| P1-11 | API-CRUD-Pfade für News, Termine, Mitglieder, Content/Sujet und Archiv in CI absichern | TESTBEREIT |

## Phase 2 – Adminbereich als Vereins-CMS

| ID | Aufgabe | Status |
|---|---|---|
| P2-01 | PC-Admin-Navigation auf zentrale CMS-Bereiche prüfen/vereinheitlichen | TESTBEREIT |
| P2-02 | Bearbeitungszustand (neu/bearbeiten) klar sichtbar machen | TESTBEREIT |
| P2-03 | Löschen mit Bestätigung für zentrale Inhalte vereinheitlichen | TESTBEREIT |
| P2-04 | Erfolg/Fehler/Uploadstatus als einheitlichen Status darstellen | TESTBEREIT |
| P2-05 | Startseite/Hero im Medien-CMS eindeutig benennen und vorschauen | TESTBEREIT |
| P2-06 | Sujet, Archiv, Fotoalben, Galerie, Dokumente und Links im Medien-CMS klar trennen | TESTBEREIT |
| P2-07 | Telefon-/App-Vorschau auf die zentralen administrierbaren Inhalte ausrichten | TESTBEREIT |
| P2-08 | Vereins- und Systemeinstellungen klar von Inhaltsverwaltung trennen | TESTBEREIT |
| P2-09 | Admin-CMS-Bedienstruktur in einem automatischen Contract-Smoke-Test prüfen | TESTBEREIT |
| P2-10 | Phase-2-Abnahme dokumentieren | GETESTET |

## Technische Gates

Die finale technische Einstufung auf `GETESTET` erfolgt, sobald der vollständige **Phase 0-2 Gate** auf dem finalen Branch-Stand grün ist. Das Gate umfasst:

- Phase-1-HTTP-/Persistenzvertrag,
- Phase-2-PC-CMS-Vertrag,
- `flutter analyze`,
- vollständige Flutter-Tests.

## Gesperrt

Alle Aufgaben aus Phase 3 oder später sind bis zur ausdrücklichen Freigabe gesperrt. Erkenntnisse dazu werden nur dokumentiert, nicht umgesetzt.

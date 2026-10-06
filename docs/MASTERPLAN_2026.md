# FLAPAMAMAKU – Verbindlicher Projekt-Masterplan

**Gültig ab:** 2. Oktober 2026  
**Status:** verbindlich  
**Grundsatz:** Erst Stabilität, dann Ausbau, dann Mehrvereinsbetrieb. Keine Phase wird übersprungen.

## Verbindliche Reihenfolge

1. Stabilität und Datenfluss
2. Admin-CMS
3. Bestehende Funktionen fertigstellen
4. Sujet/Archiv professionell strukturieren
5. Multi-Tenant-Sicherheit
6. Backup / Logging / Betrieb
7. FLAPAMAMAKU-Praxistest
8. Pilot mit 2–3 Vereinen
9. Plattformverwaltung / Abrechnung
10. Testbetrieb bis 10 Vereine
11. Version 1.0

## Phase 0 – Projekt einfrieren und Ausgangspunkt sichern

**Ziel:** eindeutiger technischer Ausgangspunkt, keine neue Funktionalität.

- GitHub-Ausgangsstand festhalten.
- App-, Backend-, Docker- und Datenbankstand dokumentieren.
- Bestehende Funktionen und bekannte Fehler zentral erfassen.
- Testdaten von echten Vereinsdaten trennen.
- Für jeden Inhalt festlegen: Serverquelle oder statisches App-Asset.
- Alte Test-/Hardcode-Inhalte identifizieren.

**Abnahme:** Es ist eindeutig dokumentiert, was funktioniert, was nicht funktioniert und woher jeder Inhalt stammt.

## Phase 1 – Datenfluss und Grundstabilität

**Verbindliches Architekturprinzip:** `Admin → API → Datenbank → App`.

Zu prüfen und zu vereinheitlichen:

- Hauptbild / Hero
- Logo / Branding
- Jahresmotto / Sujet
- News
- Termine
- Mitglieder
- Galerie
- Fotoalben
- Archiv
- Dokumente
- Links
- Vereinseinstellungen

Zusätzlich:

- Keine versteckten Testdaten in produktiv konfigurierten Apps.
- Speichervorgänge warten die Serverantwort vollständig ab.
- Erfolg und Fehler werden sichtbar rückgemeldet.
- Aktualisieren funktioniert zuverlässig.
- Netzwerkausfälle führen nicht zu App-Abstürzen.
- 401/403/404/409/413/422/429/5xx werden verständlich behandelt.

**Abnahme:** News, Termin, Mitglied, Sujet, Galerie/Album und Archiv können serverseitig verwaltet, gespeichert, aktualisiert und in der App korrekt angezeigt werden.

## Phase 2 – Adminbereich zum Vereins-CMS ausbauen

**Ziel:** Ein Vereinsadministrator kann die wichtigsten Inhalte ohne technische Kenntnisse verwalten.

CMS-Bereiche:

- Startseite
- aktuelles Sujet
- News
- Termine
- Mitglieder
- Galerie
- Fotoalben
- vergangene Sujets
- Dokumente
- Links
- Benutzer
- Berechtigungen
- Vereinseinstellungen

Bedienregeln:

- Klare Aktionen: Neu / Bearbeiten / Löschen.
- Bestätigung vor destruktiven Aktionen.
- Bildvorschau und Uploadstatus.
- Verständliche Fehler- und Erfolgsmeldungen.
- Sortierung und eindeutiger Bearbeitungszustand.
- Visuelle App-Vorschau, wo sie die Pflege verbessert.

**Abnahme:** Die zentralen Inhalte können im PC-Admin ohne Quellcodeänderung sicher und nachvollziehbar gepflegt werden.

## Phasen 3–11

- Phase 3: bestehende App-Funktionen fertigstellen
- Phase 4: Jahresmotto und Archiv als eigenes Datenmodell
- Phase 5: Multi-Tenant-Härtung
- Phase 6: Migrationen, Backup, Logging, Monitoring
- Phase 7: FLAPAMAMAKU-Pilotbetrieb
- Phase 8: 2–3 weitere Vereine
- Phase 9: Plattformverwaltung und Abrechnung
- Phase 10: Testbetrieb bis 10 Vereine
- Phase 11: Version 1.0

## Verbindliche Entwicklungsregeln

1. Keine spontane Feature-Entwicklung.
2. Eine Phase nach der anderen.
3. Kein „nebenbei noch schnell“ ausserhalb des freigegebenen Pakets.
4. Eine zentrale Aufgabenliste mit `OFFEN / IN ARBEIT / TESTBEREIT / GETESTET / FREIGEGEBEN`.
5. GitHub ist die technische Wahrheit; keine dauerhaften lokalen Sonderstände.
6. Administrierbare Inhalte stammen aus Server/API/Datenbank, nicht aus fest eingebauten Testdaten.
7. Kein Produktions-Update ohne Build und Tests.
8. Datenbankänderungen werden ab der dafür vorgesehenen Phase migrationsgeführt.
9. Keine sensiblen Vereinsdaten, Passwörter oder Tokens im Repository.
10. Wenn eine notwendige Änderung ausserhalb der freigegebenen Phase liegt, wird an dieser Stelle gestoppt und die Entscheidung des Auftraggebers eingeholt.

## Aktuelle Freigabe

- Phase 0 bis einschließlich Phase 8 wurden umgesetzt, getestet und nach `main` übernommen.
- Am 5. Oktober 2026 wurde **Phase 9 – Plattformverwaltung / Abrechnung** ausdrücklich zur selbstständigen vollständigen Umsetzung freigegeben.
- Die Freigabe umfasst notwendige Datenbank-Migrationen, Superuser-/Plattformverwaltung, Abrechnung, softwareseitige Vereinssperren, Tests, Builds, Pull Request und Merge nach `main`.
- **Phase 10 und Phase 11 bleiben gesperrt**, bis eine neue ausdrückliche Freigabe erfolgt.

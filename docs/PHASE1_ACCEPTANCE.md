# Phase 1 – Datenfluss und Grundstabilität: Abnahmeprotokoll

**Arbeitsbranch:** `feature/masterplan-phase0-2-20261003`  
**Verbindliches Architekturprinzip:** `Admin → API → Datenbank → App`

## Umgesetzte Stabilisierung

- Produktiv konfigurierter Serverbetrieb zeigt keine gebündelten Demo-News, Demo-Termine oder Demo-Mitglieder mehr als Live-Inhalt.
- Die Startseite verwendet für das Hauptbild den Serverbereich `hero`; bei fehlendem Hero wird ein neutraler Leerzustand bzw. das serverseitige Vereinslogo verwendet, kein fest eingebautes FLAPAMAMAKU-Hauptbild.
- Der mobile Admin verwendet keine fest eingebauten Vereinsbilder mehr als News-Auswahl.
- News-, Termin- und Mitglieder-Speicheroperationen warten die Serverantwort ab und zeigen Erfolg bzw. benutzerfreundliche Fehler an.
- Löschen in der mobilen Administration wird bestätigt, abgewartet und mit Erfolg/Fehler rückgemeldet.
- Manuelles Aktualisieren ist in den Adminlisten vorhanden; Synchronisationsfehler werden sichtbar angezeigt.
- Bildexport verwendet neutrale Dateinamen-Fallbacks und die zentrale freundliche Fehlerbehandlung.
- Der vorhandene Offline-Cache bleibt erhalten und wird nach erfolgreicher Server-Synchronisation aktualisiert.

## API-/Persistenzvertrag

`backend/tests/phase1_contract_smoke.py` prüft über echte HTTP-Aufrufe gegen ein isoliertes Backend:

- öffentliche Instanzidentität über `/api/app-config`,
- Login und Adminberechtigungen,
- 401 für nicht angemeldete geschützte Inhalte,
- CRUD und anschliessendes Lesen aus der Datenbank für News,
- CRUD und anschliessendes Lesen aus der Datenbank für Termine,
- CRUD und anschliessendes Lesen aus der Datenbank für Mitglieder,
- Erstellen/Lesen/Löschen für `hero`, `sujet`, `archive`, `photos`, `gallery`, `documents` und `links`.

Damit wird der vereinbarte Kern-Datenfluss automatisiert gegen Regressionen abgesichert.

## Flutter-Vertrag

`test/runtime_content_policy_test.dart` prüft explizit:

- Lokaler Entwicklungsbetrieb ohne Server darf Demo-Daten verwenden.
- Ein konfigurierter Vereinsserver darf keine gebündelten Demo-Daten als Vereinsinhalt verwenden.

Zusätzlich laufen `flutter analyze` und der vollständige Flutter-Testbestand im Phase-0-2-Gate.

## Fehlerbehandlung

Die bestehende zentrale API-Schicht übersetzt HTTP- und Netzwerkfehler in verständliche Meldungen. Relevant abgedeckt sind insbesondere:

- 400 – Eingabeproblem
- 401 – Anmeldung ungültig
- 403 – fehlende Berechtigung
- 404 – Inhalt nicht gefunden
- 409 – Datenkonflikt
- 413 – Datei zu gross
- 422 – Eingabedaten prüfen
- 429 – zu viele Anfragen
- 5xx – Serverproblem
- Timeout / Netzwerk nicht erreichbar

## Abgrenzung

Der fachliche Ausbau von Terminen, Mitgliedern, Sujet-Datenmodell oder Multi-Tenant-Funktionen gehört nicht in Phase 1 und wurde nicht vorgezogen.

## Technischer Abnahmestatus

Phase 1 ist **GETESTET**, sobald der vollständige `Phase 0-2 Gate` auf dem finalen Branch-Stand erfolgreich abgeschlossen ist.

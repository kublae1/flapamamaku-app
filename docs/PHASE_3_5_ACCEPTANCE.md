# Phase 3–5 – Abnahmeprotokoll

Stand: 5. Oktober 2026

Dieses Dokument markiert den finalen Abnahmestand der verbindlich freigegebenen Masterplan-Phasen 3 bis 5.

## Phase 3 – bestehende App-Funktionen fertigstellen

Umgesetzt sind die erweiterten Termine (Beginn/Ende, Treffpunkt, Beschreibung, verantwortliche Person, Anmeldeschluss, An-/Abmeldung, Teilnehmer, Karte und Dokument-Link), die vollständigen Mitglieder-Kontaktdaten mit Direktaktionen sowie die Trennung und Bedienung von Galerie und Fotoalben inklusive Vollbild/Zoom/Navigation und administrativer Verwaltung.

## Phase 4 – Jahres-Sujet und Archivmodell

Das Jahres-Sujet ist servergeführt und besitzt Jahr, Titel, Motto, Logo, Beschreibung, Bilder und Aktivstatus. Es gibt einen eindeutigen aktiven Jahresdatensatz; der Wechsel erfolgt ohne neuen App-Build und ältere Sujets bleiben im Archiv verfügbar.

## Phase 5 – Multi-Tenant-Härtung

Die Vereinsinstanz ist serverseitig gebunden. Tenant-relevante Daten erhalten eine Vereinszuordnung; Sitzungen werden an die konfigurierte Instanz gebunden. Cross-Tenant-Zugriffe und falsche Vereinsinstanzen werden durch Backend- und Contract-Tests geprüft. Vereinsstatus und Berechtigungen werden serverseitig durchgesetzt.

## Qualitäts-Gate

Vor der Übernahme nach `main` wurde der Phase-3–5-Gate vollständig grün ausgeführt:

- Backend kompiliert
- Phase-2-CMS-Regression grün
- Admin → API → Datenbank → App Baseline grün
- Phase-3–5 HTTP-/Tenant-Isolation grün
- Phase-3–5 Implementierungsvertrag grün
- `flutter analyze` grün
- Flutter-Tests grün
- Android Release APK erfolgreich gebaut

Nach dem Merge wurde zusätzlich die Core-Session-Migration so korrigiert, dass `init_db()` und die Authentifizierung dieselbe Tenant-Bindung (`instance_id`) verwenden. Die regulären `main`-Workflows dieses Commits bilden die finale Integrationsprüfung.

## Version

App-Version: `0.9.1+37`

## Abgrenzung

Dieses Protokoll deckt ausschließlich Phase 3 bis einschließlich Phase 5 ab. Arbeiten aus Phase 6 oder später sind nicht Bestandteil dieses Pakets.

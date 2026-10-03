# Phase 0 – Technischer Ausgangspunkt

**Stichtag:** 3. Oktober 2026  
**Basis-Commit `main`:** `7581f3d8319a8f17220e5e4b11de1e94c7afcab0`  
**Arbeitsbranch:** `feature/masterplan-phase0-2-20261003`  
**Mobile App:** `0.8.32+34`

## 1. Systemaufbau

Das Projekt besteht aus:

- Flutter-App für Android, iOS-Pipeline vorbereitet.
- FastAPI-Backend.
- SQLite-Persistenz im Docker-Backend.
- Browserbasierter PC-Admin unter `/admin`.
- Docker-/Portainer-Betrieb.
- GitHub Actions für Android, iOS, Backend, öffentliche Smoke-Tests, Backend-Image und Release-Candidate-Gate.
- Rollen-/Berechtigungsmodell.
- White-Label-/Vereinskonfiguration über `/api/app-config`.
- Offline-Cache in der mobilen App.
- Push-Infrastruktur.

## 2. Verbindliche Inhaltsquellen

| Bereich | Soll-Quelle | Stand Phase 0 | Massnahme Phase 1 |
|---|---|---|---|
| App-Name / Untertitel / Logo / Farbe | `/api/app-config` | servergeführt, lokale Defaults vorhanden | lokale Defaults nur als neutralen Start-/Entwicklungsfallback behandeln |
| Hauptbild / Hero | `content` mit Section `hero` | servergeführt, aber festes FLAPAMAMAKU-Bild als Fallback | produktive App darf bei fehlendem Server-Hero kein vereinsfremdes Hardcode-Hero zeigen |
| News | `/api/news` | servergeführt, lokale Testdaten werden beim Store-Start und Logout erneut eingesetzt | bei konfiguriertem Server keine Testdaten verwenden |
| Termine | `/api/events` | servergeführt, lokale Testdaten werden beim Store-Start und Logout erneut eingesetzt | bei konfiguriertem Server keine Testdaten verwenden |
| Mitglieder | `/api/members` | servergeführt, lokale Testdaten werden beim Store-Start und Logout erneut eingesetzt | bei konfiguriertem Server keine Testdaten verwenden |
| Mitgliederfilter | `/api/member-filters` | servergeführt | beibehalten |
| Sujet | `content` Section `sujet` | servergeführt | beibehalten, Fehler-/Leerzustände prüfen |
| Archiv | `content` Section `archive` | servergeführt | beibehalten |
| Fotoalben | `content` Section `photos` | servergeführt | beibehalten |
| Galerie | `content` Section `gallery` + Snapshots | servergeführt | beibehalten |
| Dokumente | `content` Section `documents` | servergeführt | beibehalten |
| Umfragen | `/api/polls` | servergeführt | beibehalten |
| Links / WhatsApp | `content` | servergeführt | beibehalten |
| Vereinseinstellungen | `/api/app-config` / Settings-Endpunkte | servergeführt | PC-Admin als zentrale Pflegeoberfläche konsolidieren |

## 3. Gefundene Inkonsistenzen / Altlasten

### P0-01 – lokale Testdaten trotz konfiguriertem Server
`AppStore` startet grundsätzlich mit lokalen Beispiel-News, Beispiel-Terminen und Beispiel-Mitgliedern. Nach Logout werden diese erneut eingesetzt. In einer produktiv konfigurierten Vereins-App ist das nicht zulässig.

### P0-02 – fest eingebautes Hero als produktiver Fallback
Die Startseite verwendet bei fehlendem Server-Hero `assets/images/hero_wasserturm_saurocker.png`. Für FLAPAMAMAKU ist das optisch passend, widerspricht aber der verbindlichen Regel, dass administrierbare Vereinsinhalte servergeführt sind und bei White-Label-Instanzen nicht auf fremdes Vereinsmaterial zurückfallen dürfen.

### P0-03 – mobile Admin-News enthalten fest eingebaute Bildauswahl
Der mobile Admin bietet lokale Asset-Bilder (`Schweine Rocker`, `Zylinder`, `Wikinger`, `Feuerwerk`) als Newsfoto an. Diese Bilder sind nicht serveradministriert und skalieren nicht auf andere Vereine.

### P0-04 – einzelne feste Markenbezeichnungen in Systemtexten
Mindestens ein Biometrie-Text verwendet noch fest `FLAPAMAMAKU` statt den geladenen App-/Vereinsnamen.

### P0-05 – README technisch veraltet
Die README bezeichnet das Projekt noch als Version 0.7 und mehrere inzwischen erledigte Punkte fälschlich als „nächste Entwicklungsschritte“.

### P0-06 – Fehlerzustand und Bearbeitungszustand im Admin nicht überall einheitlich
Die API besitzt bereits brauchbare freundliche Fehlermeldungen. Mobile und PC-Admin-Oberflächen verwenden diese Rückmeldungen aber nicht überall mit einem einheitlichen sichtbaren Statusmuster.

## 4. Bereits solide vorhandene Grundlagen

- API-Fehler werden zentral in `ApiService` in benutzerverständliche Meldungen übersetzt.
- `AppStore` wartet bei News-/Termin-/Mitglieder-Schreiboperationen auf den Server und synchronisiert danach neu.
- Offline-Cache ist vorhanden.
- PC-Admin besitzt bereits CMS-artige Zweispaltenstruktur, Medienverwaltung und Telefonvorschau.
- News-, Termin-, Mitglieder-, Rollen- und Inhalts-APIs sind vorhanden.
- White-Label-App-Konfiguration und Instance-ID-Prüfung sind vorhanden.
- GitHub-Actions-Infrastruktur ist deutlich weiter als die alte README dokumentiert.

## 5. Phase-0-Abnahme

Phase 0 gilt als technisch vorbereitet, sobald:

- dieser Ausgangspunkt im Repository versioniert ist,
- die verbindliche zentrale Aufgabenliste existiert,
- die README an den tatsächlichen Stand angepasst ist,
- keine weiteren unklaren Inhaltsquellen für Phase 1 offen bleiben.

# FLAPAMAMAKU Vereinsplattform

Aktueller Entwicklungsstand: **Beta / Vor-1.0**  
Mobile App laut `pubspec.yaml`: **0.8.33+35**.  
Phase-0-Ausgangsversion am 03.10.2026: **0.8.32+34**.

Das Projekt besteht aus einer mobilen Flutter-App und einem zentralen Docker-Backend mit Browser-Administration. Der verbindliche Projektplan liegt unter [`docs/MASTERPLAN_2026.md`](docs/MASTERPLAN_2026.md).

## Architektur

### Mobile App

- Flutter für Android; iOS-Buildpipeline ist vorbereitet.
- Login und rollenbasierte Berechtigungen.
- servergeführtes Vereins-Branding / White-Label-Konfiguration.
- News, Termine, Mitglieder, Mitgliederfilter.
- Hauptbild / Hero, Sujet, Archiv, Galerie, Fotoalben und Dokumente.
- Umfragen und Links.
- Offline-Cache für zuletzt erfolgreich synchronisierte Daten.
- Biometrie und Push-Infrastruktur.
- konfigurierbare Serveradresse je Build/Installation.

### Backend / PC-Admin

Im Ordner `backend`:

- FastAPI REST-API.
- persistente SQLite-Datenbank.
- Browser-CMS unter `/admin`.
- Benutzer, Rollen und Einzelberechtigungen.
- Vereins-/App-Konfiguration.
- Bild-/Datei-Uploads.
- Dockerfile und Compose-Konfigurationen.
- öffentliche Deployment-Dokumentation.

## Datenfluss

Für produktiv administrierbare Inhalte gilt verbindlich:

```text
PC-Admin / App-Admin
        ↓
       API
        ↓
    Datenbank
        ↓
   Mobile App
```

Feste App-Assets sind nur für technische/visuelle Grundbestandteile und neutrale Fallbacks vorgesehen. Produktive Vereinsinhalte dürfen nicht aus versteckten Testdaten stammen.

## Backend starten

Nach dem Docker-Start:

- PC-Admin: `http://SERVER-IP:8087/admin`
- API-Status: `http://SERVER-IP:8087/api/health`
- API-Dokumentation: `http://SERVER-IP:8087/api/docs`

Weitere Hinweise: [`backend/README.md`](backend/README.md) und [`backend/PUBLIC_DEPLOYMENT.md`](backend/PUBLIC_DEPLOYMENT.md).

## Mobile App mit Backend verbinden

Die Build-Adresse wird über `API_BASE_URL` gesetzt. In GitHub Actions wird dafür die Repository-Variable `FLAPAMAMAKU_API_BASE_URL` verwendet.

Die App kann zusätzlich eine gespeicherte Serveradresse verwenden, sofern der Build `ALLOW_SERVER_CHANGE` zulässt. Vor dem Verbinden prüft die App die Server-Instanz über `/api/app-config` und die erwartete `CLUB_INSTANCE_ID`.

## Synchronisation und Offline-Verhalten

- Nach erfolgreicher Anmeldung werden News, Termine, Mitglieder, Filter und Inhalte vom Server geladen.
- Im laufenden Betrieb erfolgt periodische Synchronisation.
- Die Oberflächen unterstützen manuelles Aktualisieren.
- Nach erfolgreicher Synchronisation wird ein lokaler Offline-Cache gespeichert.
- Bei vorübergehend fehlendem Server können zuletzt synchronisierte Daten weiter angezeigt werden.
- Bei konfiguriertem Vereinsserver werden keine eingebauten Demo-Inhalte als Live-Daten angezeigt.

## CI / Builds

GitHub Actions enthält unter anderem Workflows für:

- Android-Build.
- iOS-Build.
- Backend-Tests.
- Backend-Docker-Image.
- Public Smoke Tests.
- White-Label-Profilvalidierung.
- Release-Candidate-Gate.
- verbindliches `Phase 0-2 Gate` mit API-/Persistenzvertrag, PC-CMS-Vertrag, Flutter-Analyse und Flutter-Tests.

Release-/Store-Konfiguration: [`docs/RELEASE_SETUP.md`](docs/RELEASE_SETUP.md).

## Aktuelle verbindliche Entwicklungsphase

Am 03.10.2026 wurden **Phase 0 bis einschließlich Phase 2** des Masterplans freigegeben und auf dem Arbeitsbranch technisch umgesetzt:

1. Phase 0 – Ausgangspunkt sichern.
2. Phase 1 – Datenfluss und Grundstabilität.
3. Phase 2 – Adminbereich zum Vereins-CMS konsolidieren.

Phase 3 und später bleiben gesperrt, bis der Auftraggeber sie ausdrücklich freigibt.

Dokumentation:

- [`docs/PHASE0_BASELINE.md`](docs/PHASE0_BASELINE.md)
- [`docs/PHASE1_ACCEPTANCE.md`](docs/PHASE1_ACCEPTANCE.md)
- [`docs/PHASE2_CMS_ACCEPTANCE.md`](docs/PHASE2_CMS_ACCEPTANCE.md)
- [`docs/TASKS_PHASE0_2.md`](docs/TASKS_PHASE0_2.md)

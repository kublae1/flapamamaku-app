# Öffentlicher Betrieb / White Label

Die öffentliche Bereitstellung ist bewusst White-Label-fähig aufgebaut. FLAPAMAMAKU ist die erste Instanz; weitere Vereine verwenden dieselbe Codebasis mit eigener Domain und eigener Konfiguration.

## Öffentliche Adresse je Verein

Jede Instanz erhält eine eigene HTTPS-Adresse, zum Beispiel:

```
https://app.verein-a.ch
https://app.verein-b.ch
```

Für Builds und externe Prüfungen wird bevorzugt die Repository-Variable
`WHITE_LABEL_API_BASE_URL` verwendet.

Für die bestehende FLAPAMAMAKU-Instanz bleibt
`FLAPAMAMAKU_API_BASE_URL` als kompatibler Fallback erhalten.

Zusätzlich wird die erwartete Vereinsinstanz geprüft. Dafür kann
`WHITE_LABEL_INSTANCE_ID` gesetzt werden. Für FLAPAMAMAKU bleibt
`FLAPAMAMAKU_INSTANCE_ID` als Fallback erhalten; ohne Variable wird
`flapamamaku` erwartet.

Ohne gesetzte Variable verwendet dieses Repository weiterhin:

```
https://flapamamaku.kublaecloud.synology.me
```

## Zielarchitektur

```
Android / iPhone / Browser
          |
        HTTPS
          |
  Reverse Proxy / TLS
          |
   Backend-Container
          |
 Vereins-Datenbank
```

Die Datenbank wird niemals direkt veröffentlicht. Öffentlich erreichbar ist nur die HTTPS-Adresse des jeweiligen Backends.

## Produktionsbetrieb

Für jede Vereinsinstanz gelten dieselben Anforderungen:

- eigener HTTPS-Hostname
- gültiges TLS-Zertifikat
- Backend nur hinter Reverse Proxy erreichbar
- `FLAPAMAMAKU_ENV=production`
- eindeutige `FLAPAMAMAKU_INSTANCE_ID` pro Vereinsinstanz
- `FLAPAMAMAKU_ALLOWED_ORIGINS` auf die konkrete HTTPS-Adresse der Instanz beschränken
- eigene persistente Daten
- eigenes Backup/Restore
- eigene Benutzer und Berechtigungen

Die Namen der bestehenden Backend-Umgebungsvariablen bleiben vorerst kompatibel, damit die laufende FLAPAMAMAKU-Installation nicht umgebaut werden muss.

## GitHub Public HTTPS Smoke Test

Der Workflow `.github/workflows/public-smoke.yml` prüft die konfigurierte öffentliche Adresse von GitHub aus dem Internet.

Geprüft werden:

- URL verwendet HTTPS
- DNS/TLS-Verbindung funktioniert
- `/api/health` antwortet korrekt
- Backend-Version, Build-SHA und Schema sind vorhanden
- die öffentliche URL liefert die erwartete `instance_id`
- HSTS und weitere Security-Header sind gesetzt
- öffentliche API-Dokumentation ist im Produktionsmodus deaktiviert
- Auth-Status-Endpunkt ist erreichbar

Damit kann derselbe Test für jede White-Label-Instanz verwendet werden.

Der Public-Smoke-Workflow verwendet dieselben Profile wie der Android-Build:
`config/white-label/<profil>.json`.

Beim manuellen Start des Workflows wird nur noch das Profil gewählt. Der Test liest daraus automatisch:
- `api_base_url`
- `instance_id`

Damit gibt es für Verein 1 bis Verein 10 keine separate zweite Pflege der öffentlichen URL und der erwarteten Vereinsinstanz.

## Reverse Proxy

Beispiel Synology:

- Quelle: HTTPS
- Hostname: öffentliche Vereinsdomain
- Port: 443
- Ziel: HTTP
- Zielhost: interner Docker-/Synology-Host
- Zielport: Backend-Port der Instanz

Von aussen wird nur HTTPS/443 freigegeben. Der interne Backend-Port wird nicht direkt ins Internet weitergeleitet.

## Vor Freigabe einer Vereinsinstanz

Vor der Freigabe prüfen:

- DNS
- TLS-Zertifikat
- Public HTTPS Smoke Test
- normaler Mitglieder-Login
- Admin-Berechtigungen
- Medienzugriff
- Session-Verhalten
- Backup
- kontrollierter Restore-Test
- Android-Build mit der öffentlichen Instanz-URL

Erst danach wird die jeweilige Vereinsinstanz freigegeben.


## White-Label Android-Identität

Für eine weitere Vereinsinstanz können in GitHub Repository Variables folgende Werte gesetzt werden:

- `WHITE_LABEL_API_BASE_URL` — öffentliche HTTPS-Adresse des Vereinsservers
- `WHITE_LABEL_APP_NAME` — Anzeigename der App
- `WHITE_LABEL_APP_SUBTITLE` — Untertitel vor der Anmeldung
- `WHITE_LABEL_APP_ICON_URL` — öffentliche HTTPS-Adresse zu einem PNG-App-Icon

Das Icon wird während des Android-Builds geladen und sowohl als Launcher-Icon als auch als lokales Fallback-Logo verwendet. Die Quelldatei im Repository wird dabei nicht dauerhaft überschrieben.

Wenn keine White-Label-Werte gesetzt sind, bleiben die bestehenden FLAPAMAMAKU-Werte und das FLAPAMAMAKU-App-Icon unverändert.

Die Android Application ID und die Release-Signierung werden durch diese Branding-Einstellungen nicht verändert.


## White-Label Push / Firebase

Jede Vereinsinstanz kann ein eigenes Firebase-Projekt verwenden. Dafür können folgende GitHub Repository Secrets gesetzt werden:

- `WHITE_LABEL_FIREBASE_API_KEY`
- `WHITE_LABEL_FIREBASE_APP_ID`
- `WHITE_LABEL_FIREBASE_MESSAGING_SENDER_ID`
- `WHITE_LABEL_FIREBASE_PROJECT_ID`

Sind diese White-Label-Secrets nicht gesetzt, verwendet der Android-Build weiterhin die bestehenden FLAPAMAMAKU-Secrets:

- `FLAPAMAMAKU_FIREBASE_API_KEY`
- `FLAPAMAMAKU_FIREBASE_APP_ID`
- `FLAPAMAMAKU_FIREBASE_MESSAGING_SENDER_ID`
- `FLAPAMAMAKU_FIREBASE_PROJECT_ID`

Dadurch bleibt die bestehende FLAPAMAMAKU-Push-Konfiguration unverändert, während weitere Vereine ihre Push-Benachrichtigungen vollständig getrennt betreiben können.

Der sichtbare Name des Android-Benachrichtigungskanals und der Fallback-Titel übernehmen den jeweiligen `WHITE_LABEL_APP_NAME`.


## White-Label Build-Profile für mehrere Vereine

Für bis zu 10 Testvereine kann jede App-Instanz ein eigenes Build-Profil unter
`config/white-label/<profil>.json` erhalten.

Ein Build-Profil enthält nur technische Startwerte wie:

- Vereins-/App-Name
- Untertitel
- öffentliche API-Adresse
- optionales App-Icon

Das vorhandene Referenzprofil ist:

`config/white-label/flapamamaku.json`

FLAPAMAMAKU bleibt das Standardprofil und damit die Referenzinstanz.

Beim manuellen Android-Build kann über den Workflow-Eingabewert `profile` ein anderes Profil ausgewählt werden. Dadurch kann später für Verein 2 bis Verein 10 jeweils ein eigener Build erzeugt werden, ohne die FLAPAMAMAKU-Konfiguration umzuschreiben.

Alle Profile werden zusätzlich durch den Workflow
`.github/workflows/validate-white-label-profiles.yml` gemeinsam geprüft. Dabei werden unter anderem doppelte `instance_id`, doppelte öffentliche API-Adressen, ungültige HTTPS-Adressen, fehlende Pflichtfelder und aktuell mehr als 10 Testprofile blockiert.

Wichtig: Das Build-Profil ersetzt **nicht** die autonome Vereinsverwaltung. Laufende Inhalte und Vereinsdaten wie Mitglieder, Termine, News, Bilder, Dokumente, Module, Farben, Kontaktdaten, Benutzer und Berechtigungen werden weiterhin über die jeweilige Admin-Oberfläche und das jeweilige Backend verwaltet.

Ein Verein benötigt dafür keinen eigenen Docker-Server. Das gleiche Profil-/Instanzmodell kann sowohl auf einem eigenen Docker-Host als auch auf einer zentral betriebenen Cloud-Infrastruktur verwendet werden.

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
- HSTS und weitere Security-Header sind gesetzt
- öffentliche API-Dokumentation ist im Produktionsmodus deaktiviert
- Auth-Status-Endpunkt ist erreichbar

Damit kann derselbe Test für jede White-Label-Instanz verwendet werden. Es muss nur deren `WHITE_LABEL_API_BASE_URL` gesetzt werden.

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

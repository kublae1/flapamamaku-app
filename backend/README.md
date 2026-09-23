# FLAPAMAMAKU Backend + PC-Admin (Version 0.7)

Diese erste Serverbasis ist absichtlich getrennt von der mobilen Flutter-App.

## Enthalten

- REST-API für **News**, **Termine** und **Mitglieder**
- persistente SQLite-Datenbank
- PC-Admin unter `/admin`
- API-Dokumentation unter `/api/docs`
- Docker-/Synology-fähige Konfiguration
- News werden serverseitig nach `created_at` absteigend geliefert, also neueste zuerst

## Lokal / Synology mit Docker

Im Verzeichnis `backend`:

```bash
docker compose up -d --build
```

Danach:

- Admin: `http://SERVER-IP:8087/admin`
- API: `http://SERVER-IP:8087/api/health`
- API-Doku: `http://SERVER-IP:8087/api/docs`

Die Daten liegen im Docker-Volume `flapamamaku-data` und bleiben bei Container-Neustarts erhalten.

## Nächste Stufe

1. Login und Berechtigungen
2. echter Bild-/Datei-Upload
3. Flutter-App an diese API anbinden
4. Termin-Anmeldungen serverseitig speichern
5. Push-Mitteilungen
6. später bei Bedarf Wechsel von SQLite auf PostgreSQL/MariaDB

> Diese Version ist eine Entwicklungsgrundlage. Der Adminbereich ist noch nicht für das öffentliche Internet abgesichert.


## Deployment über GitHub Container Registry (GHCR)

Das Backend-Image wird automatisch bei Änderungen unter `backend/**` gebaut und nach GHCR veröffentlicht.

Image:

```
ghcr.io/kublae1/flapamamaku-backend:latest
```

Für Synology / Portainer kann direkt die Datei `docker-compose.yml` verwendet werden.
Sie lädt das aktuelle Image aus GHCR und speichert die SQLite-Datenbank weiterhin persistent im Volume `flapamamaku-data`.

Nach einem Backend-Update:
1. GitHub Actions baut und veröffentlicht automatisch ein neues `latest`-Image.
2. In Portainer beim Stack/Container das aktuelle Image neu ziehen und redeployen.
3. Die Daten im Volume bleiben erhalten.

Zusätzlich wird pro Build ein unveränderlicher SHA-Tag veröffentlicht, z. B. `sha-abcdef1`, damit bei Bedarf auf einen bestimmten Stand zurückgegangen werden kann.

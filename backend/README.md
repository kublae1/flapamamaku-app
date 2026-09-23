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

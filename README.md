# FLAPAMAMAKU App – Version 0.7

FLAPAMAMAKU besteht jetzt aus zwei getrennten Teilen:

1. **Mobile Flutter-App** für Android, später auch iOS.
2. **Backend + PC-Admin** als Docker-fähige Serverkomponente.

## Mobile App

Enthalten:
- Startseite
- News-Feed
- Termine mit Wischaktionen
- Mitglieder
- Partnerin / Partner
- Telefon, E-Mail und Google-Maps-Aufruf
- Archiv und Sujet-Galerie
- Android-App-Icon
- lokaler Admin-Prototyp

## Backend / PC-Admin

Im Ordner `backend`:

- REST-API für News, Termine und Mitglieder
- persistente SQLite-Datenbank
- Web-Administration für PC/Notebook
- Dockerfile
- Docker Compose für Synology / Portainer
- API-Dokumentation
- GitHub-Actions-Test für Backend und Docker-Build

Nach dem Docker-Start:

- PC-Admin: `http://SERVER-IP:8087/admin`
- API-Status: `http://SERVER-IP:8087/api/health`
- API-Dokumentation: `http://SERVER-IP:8087/api/docs`

Siehe `backend/README.md`.

## Nächste Entwicklungsschritte

- mobile App an die zentrale API anbinden
- Login und Berechtigungen
- echter Foto-/Datei-Upload
- Termin-Anmeldungen zentral speichern
- Dokumente und Fotoalben
- Push-Mitteilungen
- Backup-/Restore-Konzept für Synology

Der aktuelle PC-Admin ist eine Entwicklungsgrundlage und noch nicht für eine öffentliche Internetfreigabe abgesichert.


## Mobile App mit Backend verbinden

Die App liest die Server-Adresse über den Build-Wert `API_BASE_URL`.

In GitHub kann dafür später die Repository-Variable
`FLAPAMAMAKU_API_BASE_URL` gesetzt werden, z. B.:

```
http://192.168.1.50:8087
```

Der Android-Build übernimmt diesen Wert automatisch.

Verhalten:
- ohne Server-Adresse: App benutzt weiterhin die lokalen Testdaten
- mit Server-Adresse: App synchronisiert News, Termine und Mitglieder beim Start
- danach automatische Synchronisation alle 30 Sekunden
- News können zusätzlich per Ziehen nach unten manuell aktualisiert werden
- wenn der Server vorübergehend nicht erreichbar ist, bleibt die App mit den zuletzt vorhandenen Daten bedienbar

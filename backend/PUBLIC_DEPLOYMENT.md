# Öffentlicher FLAPAMAMAKU-Zugriff

Zielarchitektur:

```
Android / iPhone / Browser
          |
        HTTPS
          |
  Reverse Proxy / TLS
          |
   127.0.0.1:8087
          |
 FLAPAMAMAKU FastAPI
          |
 /data/flapamamaku.db
```

Die SQLite-Datenbank wird **niemals direkt** veröffentlicht. Öffentlich erreichbar
ist nur die HTTPS-Adresse des Backends.

## 1. Öffentliche Adresse

Wir verwenden später eine feste Subdomain, zum Beispiel:

```
https://app.flapamamaku.ch
```

Die endgültige Adresse wird danach in GitHub als Repository Variable
`FLAPAMAMAKU_API_BASE_URL` hinterlegt. Android und iOS verwenden dann dieselbe API.

## 2. Produktions-Stack

Für den öffentlichen Betrieb ist `backend/docker-compose.production.yml` vorgesehen.

Wichtig:
- Backend-Port ist nur an `127.0.0.1:8087` gebunden.
- Die Datenbank bleibt im persistenten Docker-Volume.
- Zugriff aus dem Internet erfolgt nur über den Reverse Proxy.
- `FLAPAMAMAKU_ALLOWED_ORIGINS` wird auf die echte HTTPS-Adresse gesetzt.
- `FLAPAMAMAKU_ENV=production` deaktiviert die öffentliche API-Dokumentation.
- Das Backend setzt zusätzliche Security-Header; HSTS wird nur im Produktionsmodus aktiviert.

## 3. Synology Reverse Proxy

Auf der Synology wird ein Reverse-Proxy-Eintrag benötigt:

- Quelle: `HTTPS`
- Hostname: die spätere FLAPAMAMAKU-Subdomain
- Port: `443`
- Ziel: `HTTP`
- Zielhost: `127.0.0.1`
- Zielport: `8087`

Dazu gehört ein gültiges TLS-Zertifikat für die Subdomain.

## 4. Router / Firewall

Von aussen wird nur HTTPS/443 benötigt. Port 8087 wird **nicht** direkt ins Internet
weitergeleitet.

## 5. Vor öffentlicher Freigabe

Vor der echten Internetfreigabe prüfen wir gemeinsam:
- öffentliche DNS-Auflösung
- gültiges HTTPS-Zertifikat
- Anmeldung als normales Mitglied
- Admin-Berechtigungen
- Bild-/Galeriezugriff nach Anmeldung
- Session-Verhalten
- Backup der Docker-Daten
- Wiederherstellungstest
- Android mit öffentlicher URL
- iOS mit derselben öffentlichen URL

Erst nach diesen Prüfungen wird die Adresse für Mitglieder freigegeben.

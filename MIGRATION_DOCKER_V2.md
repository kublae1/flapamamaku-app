# FLAPAMAMAKU – Docker Integration V2

## Ziel

Die bestehende Flutter-App bleibt die technische und funktionale Basis. Funktionierende Bereiche werden nicht neu entwickelt.

## Unverändert übernehmen

- bestehende Flutter-Struktur unter `lib/`
- Navigation
- Login und Sitzungstoken
- biometrische Entsperrung
- News-, Termin- und Mitgliederansichten
- bestehende Modelle soweit API-kompatibel
- bestehende lokale Fallback-Daten

## Anpassen

- Docker-/Backend-API an die bereits vorhandenen App-Endpunkte angleichen
- Speichern/Bearbeiten/Löschen von News, Terminen und Mitgliedern zuverlässig machen
- Content-Bereiche wie Sujet und Archiv sauber vom Server laden
- Serveradresse weiterhin über `API_BASE_URL`
- bestehende Berechtigungen weiterverwenden

## Vorgehen

1. Bestehende App/API-Verträge erfassen.
2. Bestehendes Backend prüfen.
3. Nur inkompatible Backend-Endpunkte oder Datenfelder korrigieren.
4. App nur ändern, wenn eine Serveranpassung allein nicht genügt.
5. Danach gezielter Funktionstest App ↔ Docker-Admin.
6. Erst danach optische Anpassungen.

## Branch

`feature/docker-integration-v2`

`main` bleibt während dieser Arbeiten unangetastet.


## Analyse 24.09.2026

### Bereits kompatibel – keine Neuentwicklung nötig

Die bestehende Flutter-App verwendet bereits dieselben REST-Endpunkte wie das vorhandene Docker-Backend:

- `POST/PUT/DELETE /api/news`
- `POST/PUT/DELETE /api/events`
- `POST/PUT/DELETE /api/members`
- `GET /api/content` für Sujet, Archiv und weitere Inhaltsbereiche
- `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout`
- Bearer-Token und bestehende Berechtigungsfelder stimmen überein.

Damit bleiben die vorhandenen App-Funktionen bestehen. Für die Docker-Umgebung muss primär der richtige Serverstand bereitgestellt und die App mit dessen `API_BASE_URL` verbunden werden.

### Nächste Prüfung

1. laufenden Docker-Backend-Stand mit Repository-Stand vergleichen
2. Administratorrechte des verwendeten Kontos prüfen
3. Serveradresse der installierten App prüfen
4. erst danach gezielte Korrektur einzelner Fehler

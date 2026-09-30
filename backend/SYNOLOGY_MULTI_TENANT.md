# Synology-Betrieb: FLAPAMAMAKU + zweiter Testverein

## Ziel

FLAPAMAMAKU bleibt der produktive Hauptverein und läuft zunächst auf der eigenen Synology.

Ein zweiter neutraler Testverein wird **im selben Backend und in derselben Datenbank** als eigener Mandant angelegt. Damit wird die fertige Multi-Tenant-Architektur real geprüft, ohne bereits einen Cloud-Server bereitzustellen.

Die Cloud-Fähigkeit bleibt vorbereitet, wird aber aktuell nicht aktiviert.

## Architektur auf der Synology

```
Android / iPhone / Browser
          |
        HTTPS
          |
  DSM Reverse Proxy
          |
 flapamamaku-backend
          |
 /data/flapamamaku.db
          |
        club_id
      /         \
FLAPAMAMAKU   Testverein
  Tenant 1      Tenant 2
```

Es gibt bewusst:

- nur einen Backend-Container
- nur eine gemeinsame SQLite-Datenbank
- getrennte Vereinsdaten über `club_id`
- getrennte Rollen und Berechtigungen je Verein
- keinen zweiten Docker-Stack nur für den Testverein

## Persistente Daten

Empfohlener Synology-Pfad:

```
/volume1/docker/flapamamaku/data
```

Der Container bindet diesen Ordner nach:

```
/data
```

Die Datenbank liegt damit persistent unter:

```
/volume1/docker/flapamamaku/data/flapamamaku.db
```

Vor jedem produktiven Update muss dieser Ordner in die normale Synology-Backupstrategie aufgenommen werden.

## Beispiel-Compose

Die Datei

```
backend/docker-compose.synology.example.yml
```

ist eine zusätzliche Vorlage für Synology Container Manager / Portainer.

Sie verändert keine bestehende Portainer-Konfiguration automatisch.

Wichtig:

- Backend-Port `8087` bleibt an `127.0.0.1` gebunden.
- Öffentlicher Zugriff erfolgt nur über DSM Reverse Proxy und HTTPS.
- `FLAPAMAMAKU_ALLOWED_ORIGINS` muss auf die produktive HTTPS-Adresse gesetzt werden.
- SQLite bleibt auf einem einzelnen Backend-Knoten.

## Erster produktiver Ablauf

1. Persistenten Synology-Ordner für `/data` anlegen.
2. FLAPAMAMAKU-Backend mit dem bestehenden stabilen Image starten.
3. DSM Reverse Proxy auf den lokalen Backend-Port konfigurieren.
4. HTTPS-Zertifikat aktivieren.
5. `/api/health` über die öffentliche HTTPS-Adresse prüfen.
6. Mit FLAPAMAMAKU anmelden und bestehende Daten kontrollieren.
7. Backup der Datenbank erstellen.
8. Erst danach den neutralen Testverein über die Super-Admin-Oberfläche anlegen.

## Zweiter Verein: realer Isolationstest

Der Testverein wird **nicht** als zweite App-Kopie und **nicht** als zweiter Server erstellt.

Über die Super-Admin-Oberfläche:

1. Neuer Verein anlegen, z. B. `Testverein`.
2. Eigene Farben und eigenes Logo setzen.
3. Gewünschte Module aktivieren/deaktivieren.
4. Einen eigenen Vereinsadmin anlegen.
5. Testdaten erzeugen:
   - News
   - Termin
   - Mitglied
   - Dokument
   - Galeriebild
   - Fotoalbum
6. Als Testvereinsadmin anmelden.
7. Prüfen, dass nur Testvereinsdaten sichtbar sind.
8. Prüfen, dass kein Wechsel zu FLAPAMAMAKU möglich ist.
9. Als Super-Admin zurück zu FLAPAMAMAKU wechseln.
10. Prüfen, dass dort keine Testvereinsdaten sichtbar sind.

## Bereits automatisiert abgesichert

Die bestehende Testsuite prüft genau dieses Modell bereits technisch:

- `backend/tests/test_multitenant_isolation.py`
  - FLAPAMAMAKU + Testverein auf derselben Datenbank
  - getrennte News, Termine, Mitglieder
  - getrennte Dokumente, Galerie, Fotoalbum und Mitgliedsbilder
  - getrennte Push-Geräte und Push-Verläufe
  - getrennte Systemstatus-Daten
  - 403/404 bei unzulässigen vereinsfremden Zugriffen
  - Super-Admin-Wechsel zwischen beiden Vereinen

- `backend/tests/test_white_label_onboarding.py`
  - Verein anlegen
  - Module konfigurieren
  - Logo setzen
  - Vereinsadmin anlegen
  - direkter Login in den richtigen Verein
  - FLAPAMAMAKU bleibt unverändert

Der Synology-Test ist damit kein neues Funktionsmodell, sondern die reale Betriebsprüfung der bereits automatisiert getesteten Mandantentrennung.

## Abnahmekriterien für den Testverein

Der Test gilt erst als bestanden, wenn:

- FLAPAMAMAKU weiterhin vollständig funktioniert
- Testverein einen eigenen Admin hat
- Vereinsdaten gegenseitig nicht sichtbar sind
- Medien gegenseitig nicht abrufbar sind
- Testvereinsadmin FLAPAMAMAKU nicht auswählen kann
- Super-Admin beide Vereine gezielt öffnen kann
- Backup der gemeinsamen Datenbank funktioniert
- kontrollierter Restore-Test erfolgreich ist

## Cloud später

Die spätere Cloud-Bereitstellung verwendet dieselbe Multi-Tenant-Architektur:

- gleiche Codebasis
- gleiches Backend
- gleiche `club_id`-Trennung
- zunächst ebenfalls ein einzelner Backend-Knoten mit persistentem `/data`

Es ist daher kein späterer Architektur-Neubau nötig. Für den Moment bleibt Cloud jedoch ausdrücklich nur vorbereitet.

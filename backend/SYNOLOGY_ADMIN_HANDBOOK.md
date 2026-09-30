# FLAPAMAMAKU – Installationshandbuch für Administratoren

## Zweck dieses Handbuchs

Dieses Handbuch beschreibt die Installation und Inbetriebnahme von FLAPAMAMAKU auf einer Synology NAS so, dass auch ein Administrator ohne vertiefte Linux- oder Docker-Kenntnisse den Ablauf Schritt für Schritt durchführen kann.

Die Anleitung ist bewusst konservativ aufgebaut: Zuerst wird FLAPAMAMAKU in Betrieb genommen und geprüft. Erst wenn dieser Stand funktioniert und gesichert ist, wird ein zweiter Testverein angelegt.

Cloud-Betrieb ist vorbereitet, wird in dieser Anleitung aber nicht aktiviert.

---

# 1. Grundprinzip verstehen

FLAPAMAMAKU läuft als eine gemeinsame Anwendung mit:

- einem Backend-Container
- einer gemeinsamen Datenbank
- mehreren getrennten Vereinen
- einer eindeutigen `club_id` pro Verein
- getrennten Benutzern, Rollen und Vereinsdaten

Das bedeutet:

- FLAPAMAMAKU bleibt der Hauptverein.
- Ein weiterer Verein wird nicht als zweite App-Kopie installiert.
- Der zweite Verein erhält innerhalb derselben Anwendung einen eigenen Mandantenbereich.
- Vereinsadmins sehen nur ihren eigenen Verein.
- Der Super-Admin kann zwischen den Vereinen wechseln.

Für den ersten realen Test wird nur FLAPAMAMAKU plus ein neutraler Testverein betrieben.

---

# 2. Was vor der Installation vorhanden sein muss

Vor Beginn prüfen:

- [ ] Synology NAS ist eingeschaltet und erreichbar
- [ ] DSM funktioniert
- [ ] Container Manager oder Portainer ist installiert
- [ ] genügend freier Speicherplatz ist vorhanden
- [ ] ein Administratorkonto für DSM ist vorhanden
- [ ] Internetzugang der Synology funktioniert
- [ ] ein Backup-Ziel ist vorhanden
- [ ] die produktive HTTPS-Adresse ist bekannt
- [ ] Zugang zu GitHub Container Registry bzw. zum freigegebenen Container-Image ist vorhanden, falls erforderlich

Wichtig:

Niemals eine bestehende produktive Konfiguration überschreiben, wenn nicht vorher ein Backup erstellt wurde.

---

# 3. Empfohlene Ordnerstruktur auf der Synology

Im gemeinsamen Docker-Verzeichnis einen Ordner anlegen:

```
/volume1/docker/flapamamaku
```

Darunter:

```
/volume1/docker/flapamamaku/data
```

Optional für spätere strukturierte Dateiablagen:

```
/volume1/docker/flapamamaku/media
/volume1/docker/flapamamaku/backups
```

Der wichtigste Ordner ist:

```
/volume1/docker/flapamamaku/data
```

Dort liegt die persistente Datenbank.

---

# 4. Datenbank und Vereinsdaten

Die Datenbank wird im Container unter folgendem Pfad verwendet:

```
/data/flapamamaku.db
```

Auf der Synology entspricht dies:

```
/volume1/docker/flapamamaku/data/flapamamaku.db
```

Alle Vereine verwenden dieselbe Datenbankdatei.

Die Trennung erfolgt über die jeweilige `club_id`.

Beispiel:

- FLAPAMAMAKU = Verein 1
- Testverein = Verein 2
- späterer Verein = Verein 3

Ein Vereinsadmin darf nur die Daten seines eigenen Vereins abrufen.

---

# 5. Docker-Compose-Vorlage

Im Projekt ist die vorbereitete Vorlage vorhanden:

```
backend/docker-compose.synology.example.yml
```

Sie enthält sinngemäss:

```yaml
services:
  flapamamaku-backend:
    image: ghcr.io/kublae1/flapamamaku-backend:latest
    pull_policy: always
    container_name: flapamamaku-backend
    restart: unless-stopped
    ports:
      - "127.0.0.1:8087:8000"
    environment:
      FLAPAMAMAKU_DB: /data/flapamamaku.db
      FLAPAMAMAKU_ENV: production
      FLAPAMAMAKU_ALLOWED_ORIGINS: ${FLAPAMAMAKU_ALLOWED_ORIGINS}
    volumes:
      - /volume1/docker/flapamamaku/data:/data
```

Wichtig:

- Die Vorlage verändert nichts automatisch.
- Sie muss bewusst in Container Manager oder Portainer verwendet werden.
- Der Port `8087` wird nur lokal auf der Synology bereitgestellt.
- Öffentlicher Zugriff soll über HTTPS und Reverse Proxy erfolgen.

---

# 6. Umgebungsvariable setzen

Die Variable

```
FLAPAMAMAKU_ALLOWED_ORIGINS
```

muss auf die produktive HTTPS-Adresse zeigen.

Beispiel:

```
https://verein.example.ch
```

Keinen erfundenen oder alten Domainnamen übernehmen.

Nur die tatsächlich verwendete produktive Adresse eintragen.

---

# 7. Container in Portainer anlegen

## Variante A – Portainer Stack

1. Portainer öffnen.
2. Links auf **Stacks** klicken.
3. **Add stack** wählen.
4. Name eingeben:

```
flapamamaku
```

5. Die vorbereitete Compose-Konfiguration einfügen.
6. Die benötigte Umgebungsvariable setzen.
7. Vor dem Start nochmals kontrollieren:
   - Datenpfad korrekt?
   - Port korrekt?
   - Image korrekt?
   - keine bestehende produktive Instanz wird überschrieben?
8. **Deploy the stack** starten.

Danach einige Sekunden warten und unter **Containers** prüfen.

Erwarteter Status:

```
running
```

---

# 8. Container in Synology Container Manager anlegen

Falls kein Portainer verwendet wird:

1. DSM öffnen.
2. **Container Manager** starten.
3. Projekt beziehungsweise Compose-Projekt anlegen.
4. Compose-Datei einfügen.
5. Datenordner kontrollieren.
6. Umgebungsvariablen eintragen.
7. Projekt starten.
8. Containerstatus kontrollieren.

Erwarteter Zustand:

- Container läuft
- kein ständiger Neustart
- keine roten Fehlermeldungen

---

# 9. Erste technische Kontrolle

Nach dem Start prüfen:

```
https://DEINE-ADRESSE/api/health
```

Die genaue öffentliche Adresse muss der real verwendeten Domain entsprechen.

Der Aufruf muss eine erfolgreiche Health-Antwort liefern.

Falls nicht:

1. Containerstatus prüfen.
2. Container-Logs öffnen.
3. Reverse Proxy prüfen.
4. HTTPS-Zertifikat prüfen.
5. Umgebungsvariable `FLAPAMAMAKU_ALLOWED_ORIGINS` kontrollieren.

---

# 10. Reverse Proxy in DSM einrichten

Ziel:

Die Anwendung soll nicht direkt über einen offenen Container-Port veröffentlicht werden.

Der vorgesehene Weg ist:

```
Internet
   |
 HTTPS
   |
DSM Reverse Proxy
   |
127.0.0.1:8087
   |
FLAPAMAMAKU Backend
```

In DSM:

1. **Systemsteuerung** öffnen.
2. **Anmeldeportal** bzw. **Reverse Proxy** öffnen.
3. Neue Regel erstellen.
4. Quelle:
   - HTTPS
   - gewünschte Domain
   - Port 443
5. Ziel:
   - HTTP
   - Host `127.0.0.1`
   - Port `8087`
6. Speichern.

---

# 11. HTTPS-Zertifikat

Für die verwendete Domain muss ein gültiges Zertifikat vorhanden sein.

In DSM:

1. **Systemsteuerung**
2. **Sicherheit**
3. **Zertifikat**
4. Zertifikat hinzufügen oder vorhandenes zuweisen
5. Zertifikat der verwendeten Domain und Reverse-Proxy-Regel zuordnen

Nicht produktiv weiterarbeiten, wenn der Browser eine Zertifikatswarnung zeigt.

---

# 12. FLAPAMAMAKU zuerst alleine testen

Bevor ein zweiter Verein angelegt wird:

- [ ] Login funktioniert
- [ ] Startseite funktioniert
- [ ] News werden angezeigt
- [ ] Termine funktionieren
- [ ] Mitglieder sind sichtbar
- [ ] Dokumente funktionieren
- [ ] Galerie funktioniert
- [ ] Fotoalbum funktioniert
- [ ] Adminbereich funktioniert
- [ ] bestehende FLAPAMAMAKU-Daten sind vorhanden
- [ ] keine Daten fehlen
- [ ] keine unerwarteten Fehlermeldungen

Erst wenn alle Punkte erfüllt sind, mit dem Testverein fortfahren.

---

# 13. Backup vor dem zweiten Verein

Vor der Anlage eines zweiten Vereins:

1. Backend sauber laufen lassen.
2. Datenbank sichern.
3. Den gesamten Ordner sichern:

```
/volume1/docker/flapamamaku/data
```

Empfohlenes Backup-Ziel:

```
/volume1/docker/flapamamaku/backups
```

Zusätzlich sollte dieser Ordner in Hyper Backup oder eine vergleichbare Synology-Backupstrategie aufgenommen werden.

Kontrollpunkt:

- [ ] Backup existiert
- [ ] Dateigrösse ist plausibel
- [ ] Backup wurde nicht nur geplant, sondern tatsächlich erstellt

---

# 14. Zweiten Testverein anlegen

Der Testverein wird nicht als neuer Docker-Container angelegt.

Er wird innerhalb der bestehenden Anwendung über den Super-Admin erstellt.

Ablauf:

1. Als Super-Admin anmelden.
2. **Neuen Verein** wählen.
3. Vereinsname eingeben, zum Beispiel:

```
Testverein
```

4. Eigenes Logo hinterlegen.
5. Eigene Farben konfigurieren.
6. Benötigte Module aktivieren.
7. Einen eigenen Vereinsadmin anlegen.
8. Zugangsdaten des Testvereinsadmins notieren.

---

# 15. Testdaten im Testverein erstellen

Im Testverein folgende Testdaten anlegen:

- [ ] eine News
- [ ] einen Termin
- [ ] ein Mitglied
- [ ] ein Dokument
- [ ] ein Galeriebild
- [ ] ein Fotoalbum

Danach abmelden.

---

# 16. Isolationstest

Als Testvereinsadmin anmelden.

Prüfen:

- [ ] nur Testvereinsdaten sichtbar
- [ ] keine FLAPAMAMAKU-Mitglieder sichtbar
- [ ] keine FLAPAMAMAKU-News sichtbar
- [ ] keine FLAPAMAMAKU-Termine sichtbar
- [ ] keine FLAPAMAMAKU-Dokumente sichtbar
- [ ] keine FLAPAMAMAKU-Bilder sichtbar
- [ ] kein Wechsel zu FLAPAMAMAKU möglich

Danach wieder als Super-Admin anmelden.

FLAPAMAMAKU öffnen.

Prüfen:

- [ ] keine Testvereins-News sichtbar
- [ ] keine Testvereins-Mitglieder sichtbar
- [ ] keine Testvereins-Termine sichtbar
- [ ] keine Testvereins-Dokumente sichtbar
- [ ] keine Testvereins-Bilder sichtbar

Erst wenn beide Richtungen sauber getrennt sind, gilt der Test als bestanden.

---

# 17. Bilder und Dokumente

Bei mehreren Vereinen können Bilder und Dokumente langfristig viel Speicher benötigen.

Für den ersten Test mit FLAPAMAMAKU plus einem zweiten Verein ist der vorhandene Aufbau ausreichend.

Für einen späteren grösseren Betrieb gilt:

- Datenbank für Benutzer, Rechte, Vereine und Metadaten
- Dateien möglichst separat persistent speichern
- Dateiablage nach Verein strukturieren
- Backup von Datenbank und Dateien gemeinsam planen
- Speicherplatz überwachen

Eine spätere Optimierung der Medienablage soll bewusst durchgeführt werden und nicht unkontrolliert in den produktiven Stable eingebaut werden.

---

# 18. Update-Regel

Vor jedem produktiven Update:

1. Backup erstellen.
2. Aktuellen funktionierenden Stand notieren.
3. Neues Image erst danach laden.
4. Container neu starten.
5. Health-Check prüfen.
6. Login prüfen.
7. FLAPAMAMAKU prüfen.
8. Testverein prüfen.

Wenn ein Update Probleme verursacht:

- nicht weiter verändern
- Logs sichern
- auf den vorherigen funktionierenden Stand zurückgehen
- Datenbankbackup nicht überschreiben

---

# 19. Was ein normaler Vereinsadmin NICHT tun soll

Ein normaler Vereinsadmin soll nicht:

- Docker-Container ändern
- Datenbankdateien bearbeiten
- `club_id` manuell ändern
- Synology-Systemdateien verändern
- Ports freigeben
- Zertifikate löschen
- Compose-Dateien verändern
- Backups löschen
- andere Vereine verwalten

Diese Aufgaben gehören nur zum System-/Super-Admin.

---

# 20. Fehlerbehebung für Nicht-Profis

## Problem: Webseite nicht erreichbar

Prüfen:

1. Läuft die Synology?
2. Läuft der Container?
3. Ist der Reverse Proxy vorhanden?
4. Ist das Zertifikat gültig?
5. Funktioniert die Domain?

## Problem: Container startet immer wieder neu

Container-Logs öffnen.

Nicht blind Einstellungen ändern.

Fehlermeldung vollständig sichern.

## Problem: Login funktioniert nicht

Prüfen:

- richtige Adresse?
- richtiger Verein?
- richtiger Benutzer?
- Tippfehler?
- Backend erreichbar?

## Problem: FLAPAMAMAKU-Daten fehlen

Sofort stoppen.

Keine neue Datenbank erzeugen.

Datenpfad kontrollieren:

```
/volume1/docker/flapamamaku/data
```

Backup prüfen.

## Problem: Testvereinsdaten erscheinen bei FLAPAMAMAKU

Test sofort abbrechen.

Keine weiteren Produktivdaten eingeben.

Dieser Zustand darf nicht akzeptiert werden.

---

# 21. Abnahmeprotokoll

Die Installation gilt als erfolgreich, wenn alle Punkte erfüllt sind:

- [ ] Container läuft stabil
- [ ] HTTPS funktioniert ohne Warnung
- [ ] `/api/health` funktioniert
- [ ] FLAPAMAMAKU Login funktioniert
- [ ] bestehende FLAPAMAMAKU-Daten sind vorhanden
- [ ] Backup funktioniert
- [ ] zweiter Testverein kann angelegt werden
- [ ] eigener Vereinsadmin funktioniert
- [ ] Testverein sieht nur eigene Daten
- [ ] FLAPAMAMAKU sieht keine Testvereinsdaten
- [ ] Super-Admin kann beide Vereine gezielt verwalten
- [ ] Restore-Test wurde mindestens einmal kontrolliert durchgeführt

---

# 22. Wichtigste Regel

Immer in dieser Reihenfolge arbeiten:

```
Backup
  ↓
Änderung
  ↓
Health-Check
  ↓
FLAPAMAMAKU prüfen
  ↓
Testverein prüfen
  ↓
erst danach weiterarbeiten
```

Wenn ein Punkt rot ist, nicht einfach mit dem nächsten Schritt weitermachen.

---

# 23. Ziel für den späteren externen Verein

Mit diesem Handbuch kann ein externer Verein den Installationsablauf testweise selbst durchspielen.

Der technische Aufbau bleibt dabei identisch:

- gleiche Codebasis
- gleiche Backend-Anwendung
- eigene Vereinsidentität
- eigene Benutzer
- eigene Rollen
- logisch getrennte Daten
- Cloud später optional möglich

Damit lässt sich auf der Synology bereits realistisch testen, ob der spätere Selbstinstallationsprozess für einen externen Verein verständlich und robust genug ist.

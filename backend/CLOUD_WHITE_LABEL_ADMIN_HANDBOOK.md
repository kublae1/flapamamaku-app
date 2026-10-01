# White-Label Vereinsplattform – Cloud-Installationshandbuch

**Stand: 01.10.2026**

Dieses Handbuch beschreibt die Installation einer White-Label-Vereinsplattform auf einem Cloud-Server so, dass auch ein Administrator ohne vertiefte Linux-, Docker- oder Cloud-Kenntnisse den Ablauf Schritt für Schritt durchführen kann.

Als konkretes Beispiel wird **Infomaniak Jelastic Cloud** verwendet. Der technische Aufbau ist aber bewusst so beschrieben, dass er später auch auf einem anderen Docker-fähigen Cloud-Anbieter umgesetzt werden kann.

---

# 1. Was dieses Handbuch abdeckt

Dieses Handbuch ist für zwei Situationen gedacht:

1. Ein externer Verein möchte eine eigene White-Label-Instanz betreiben.
2. Mehrere Vereine sollen später gemeinsam auf einer zentral betriebenen Multi-Tenant-Plattform laufen.

Die Software selbst bleibt dieselbe Codebasis.

Die Unterschiede liegen nur in:

- Domain
- Branding
- Vereinsdaten
- Benutzer und Rollen
- Konfiguration
- Hosting
- Backups
- optional Push/Firebase

Es wird **keine zweite Softwarekopie entwickelt**.

---

# 2. Wichtig: Standardarchitektur der Plattform

Der aktuelle stabile Stand ist Multi-Tenant-fähig.

Das bedeutet:

- eine Codebasis
- ein Backend
- eine Datenbank
- mehrere Vereine
- Trennung über `club_id`
- getrennte Benutzer, Rollen und Vereinsdaten
- Super-Admin kann mehrere Vereine verwalten
- Vereinsadmin sieht nur seinen eigenen Verein

Beispiel:

```
Cloud-Umgebung
      |
      +-- Backend
      |
      +-- flapamamaku.db
             |
             +-- club_id 1 = Verein A
             +-- club_id 2 = Verein B
             +-- club_id 3 = Verein C
```

Für eine **eigenständige White-Label-Installation eines einzelnen Kunden** kann dieselbe Plattform auch nur mit einem Verein betrieben werden.

---

# 3. Was bei Infomaniak/Jelastic vorhanden sein muss

Vor Beginn:

- [ ] Infomaniak-Konto vorhanden
- [ ] Jelastic Cloud freigeschaltet
- [ ] kostenpflichtiges Jelastic-Konto aktiv, wenn ein eigenes Docker-Image verwendet wird
- [ ] eigene Domain oder Subdomain vorhanden
- [ ] Zugriff auf das freigegebene Docker-Image vorhanden
- [ ] Administrator kennt die gewünschte Vereinsbezeichnung
- [ ] Logo vorhanden
- [ ] gewünschte Vereinsfarben bekannt
- [ ] Backup-Ziel festgelegt
- [ ] Super-Admin-Zugang wird sicher verwahrt

Wichtig:

Bei Infomaniak sind benutzerdefinierte Docker-Images nach aktuellem Stand nicht im reinen Testkonto verfügbar. Für diesen Installationsweg ist daher ein kostenpflichtiges Jelastic-Konto einzuplanen.

---

# 4. Begriffe einfach erklärt

## Jelastic-Umgebung

Eine Umgebung ist der gesamte Cloud-Bereich, in dem die Anwendung läuft.

## Docker-Container

Der Container enthält das FLAPAMAMAKU-/White-Label-Backend inklusive aller benötigten Python-Abhängigkeiten.

## Persistenter Speicher

Daten, die einen Neustart oder Austausch des Containers überleben müssen.

Dazu gehört insbesondere:

```
/data/flapamamaku.db
```

## Load Balancer

Der Load Balancer nimmt HTTPS-Anfragen aus dem Internet entgegen und leitet sie intern an den Backend-Container weiter.

## Domain

Beispiel:

```
https://verein.example.ch
```

## SSL/TLS

Sorgt dafür, dass die Verbindung verschlüsselt über HTTPS läuft.

---

# 5. Zielarchitektur auf Jelastic

Empfohlener Aufbau für die erste White-Label-Cloud-Installation:

```
Internet
   |
 HTTPS
   |
Domain
   |
Load Balancer / TLS
   |
Backend Docker Container
   |
persistenter Speicher
   |
/data/flapamamaku.db
```

Für den aktuellen SQLite-Stand gilt:

**Nur einen schreibenden Backend-Knoten verwenden.**

Nicht mehrere Backend-Knoten parallel auf dieselbe SQLite-Datei schreiben lassen.

---

# 6. Aktueller Daten- und Medienspeicher

Wichtig für die Planung:

Im aktuellen stabilen Stand werden verschiedene Bilder und Dokumente direkt als Binärdaten in SQLite gespeichert.

Dazu gehören unter anderem:

- News-Bilder
- Mitgliederfotos
- Content-Bilder
- Fotoalbum-Bilder
- Galerie-Snapshots
- Dokumente

Das bedeutet:

**Ein Backup der Datenbank sichert derzeit auch einen großen Teil der Medien mit.**

Folge:

Je mehr Vereine und Bilder vorhanden sind, desto größer wird die SQLite-Datei.

Für einen ersten Testbetrieb oder wenige Vereine ist das akzeptabel.

Für einen späteren großen Betrieb mit vielen Vereinen und sehr vielen Fotos sollte die Medienablage bewusst auf getrennten Datei-/Objektspeicher migriert werden.

Diese Migration ist **nicht Bestandteil der Erstinstallation**.

---

# 7. Domain festlegen

Vor der Cloud-Einrichtung eine Domain oder Subdomain bestimmen.

Beispiele:

```
https://app.meinverein.ch
```

oder für eine zentrale Plattform:

```
https://vereinsplattform.example.ch
```

Nicht mit einer vorläufigen Adresse produktiv starten und später unkontrolliert wechseln.

Die produktive Adresse wird auch für:

- CORS / Allowed Origins
- App-Build
- Public Smoke Test
- Browser-Admin
- HTTPS-Zertifikat

verwendet.

---

# 8. Docker-Image festlegen

Aktuell wird das Backend aus einem Docker-Image der GitHub Container Registry betrieben.

Beispiel:

```
ghcr.io/kublae1/flapamamaku-backend:latest
```

Für einen echten externen Kunden soll der Administrator nur das **freigegebene Image beziehungsweise den freigegebenen Tag** verwenden.

Wenn das Image privat ist, müssen in Jelastic Zugangsdaten für die Container Registry eingerichtet werden.

Wenn das Image öffentlich ist, ist keine Registry-Anmeldung erforderlich.

Für Produktion sollte ein dokumentierter, geprüfter Stand verwendet werden.

---

# 9. Neue Jelastic-Umgebung anlegen

Im Infomaniak/Jelastic-Dashboard:

1. Bei Infomaniak anmelden.
2. Jelastic Cloud öffnen.
3. **Neue Umgebung** auswählen.
4. Zum Bereich **Docker** wechseln.
5. **Image auswählen** beziehungsweise benutzerdefiniertes Docker-Image eintragen.
6. Das freigegebene Backend-Image angeben.
7. Zunächst **einen Backend-Knoten** anlegen.
8. Zusätzlich einen Load Balancer, z. B. NGINX, hinzufügen.
9. Umgebung benennen.

Beispiel:

```
verein-test
```

oder:

```
white-label-produktiv
```

Danach Umgebung erstellen.

---

# 10. Ressourcen für den Start

Für einen kleinen Testbetrieb nicht unnötig groß starten.

Jelastic kann Ressourcen später erhöhen.

Zu Beginn:

- ein Backend-Knoten
- ein Load-Balancer-Knoten
- ausreichend RAM für Backend und Bildverarbeitung
- ausreichend SSD-Speicher für Datenbank und Medien
- Ressourcenverbrauch beobachten

Wichtig:

Nicht automatisch mehrere Backend-Knoten aktivieren, solange SQLite verwendet wird.

---

# 11. Persistenten Speicher einrichten

Der wichtigste technische Punkt ist der persistente Speicher.

Der Container erwartet:

```
FLAPAMAMAKU_DB=/data/flapamamaku.db
```

Daher muss der Pfad:

```
/data
```

persistent sein.

Ziel:

Wenn der Docker-Container neu erstellt, aktualisiert oder ersetzt wird, darf die Datenbank nicht verschwinden.

Kontrollfragen:

- [ ] Ist `/data` persistent?
- [ ] Bleibt die Datei nach Container-Neustart vorhanden?
- [ ] Bleibt sie auch nach einem Image-Update erhalten?
- [ ] Ist dieser Speicher Teil der Backupstrategie?

Ohne bestätigte Persistenz keine produktiven Vereinsdaten erfassen.

---

# 12. Umgebungsvariablen setzen

Mindestens:

```
FLAPAMAMAKU_DB=/data/flapamamaku.db
FLAPAMAMAKU_ENV=production
FLAPAMAMAKU_ALLOWED_ORIGINS=https://DEINE-DOMAIN
```

Beispiel:

```
FLAPAMAMAKU_ALLOWED_ORIGINS=https://app.meinverein.ch
```

Keine Platzhalter stehen lassen.

Keine alte Synology-Domain übernehmen, wenn eine neue Cloud-Domain verwendet wird.

---

# 13. Optional: Abrechnungsdaten

Wenn die eingebaute Vereinsabrechnung genutzt wird, können zusätzlich die dafür vorgesehenen Umgebungsvariablen gesetzt werden.

Beispielhafte Variablen des aktuellen Backends:

```
FLAPAMAMAKU_BILLING_ISSUER_NAME
FLAPAMAMAKU_BILLING_ISSUER_ADDRESS
FLAPAMAMAKU_BILLING_PAYMENT_INFO
```

Diese Angaben erscheinen in der erzeugten Vereinsrechnung.

Nur echte, geprüfte Rechnungsangaben verwenden.

---

# 14. Container-Port

Der Backend-Container arbeitet intern auf:

```
8000
```

Der Port soll nicht unnötig direkt öffentlich ins Internet gestellt werden.

Empfohlener Weg:

```
Internet
  |
443 HTTPS
  |
Load Balancer
  |
Backend:8000
```

---

# 15. Load Balancer konfigurieren

Der Load Balancer ist die öffentliche Eintrittsstelle.

Er übernimmt:

- HTTPS
- Domain
- Weiterleitung zum Backend
- später optional weitere Schutz-/Proxy-Funktionen

Der Load Balancer muss zum Backend-Port 8000 weiterleiten.

Nach der Einrichtung zuerst mit der Jelastic-Standardadresse testen.

Danach eigene Domain anbinden.

---

# 16. Eigene Domain verbinden

Beim DNS-Anbieter der Domain die nötigen DNS-Einträge so setzen, wie Jelastic sie für die konkrete Umgebung vorgibt.

Danach in Jelastic die benutzerdefinierte Domain der Umgebung beziehungsweise dem Load Balancer zuweisen.

Wichtig:

DNS-Änderungen können Zeit benötigen.

Nicht gleichzeitig mehrere unterschiedliche DNS-Konfigurationen ausprobieren.

---

# 17. HTTPS / Let's Encrypt aktivieren

Für den produktiven Betrieb HTTPS verwenden.

Infomaniak/Jelastic unterstützt Let's Encrypt.

Vorgehen:

1. Domain muss korrekt auf die Jelastic-Umgebung zeigen.
2. Load Balancer öffnen.
3. Let's-Encrypt-/SSL-Funktion aktivieren.
4. Domain auswählen.
5. Zertifikat erstellen.
6. HTTPS testen.

Nicht produktiv freigeben, wenn:

- Browser Zertifikatswarnung zeigt
- Zertifikat abgelaufen ist
- falscher Hostname im Zertifikat steht

---

# 18. Erster Health-Check

Nach erfolgreicher Bereitstellung:

```
https://DEINE-DOMAIN/api/health
```

aufrufen.

Erwartung:

- HTTP erfolgreich
- Backend antwortet
- keine Serverfehlermeldung
- Version und Schema vorhanden

Wenn nicht:

1. Containerstatus prüfen.
2. Container-Logs prüfen.
3. Umgebungsvariablen prüfen.
4. Load Balancer prüfen.
5. Domain/DNS prüfen.
6. HTTPS prüfen.

---

# 19. Erstinitialisierung

Bei einer komplett neuen White-Label-Instanz zuerst den vorgesehenen Plattform-/Super-Admin einrichten.

Super-Admin-Zugang:

- nicht an normale Vereinsmitglieder weitergeben
- starkes Passwort verwenden
- Zugang sicher dokumentieren
- später möglichst nur für Plattformverwaltung nutzen

Danach über die Super-Admin-Oberfläche den ersten Verein einrichten.

---

# 20. White-Label-Verein einrichten

Über die Super-Admin-Oberfläche:

1. **Neuer Verein**
2. Vereinsname
3. Kurzname
4. Untertitel
5. Hauptfarbe
6. Zweitfarbe
7. Logo
8. Module
9. Vereinsadmin
10. Speichern

Danach ist der Verein als eigener Mandant vorhanden.

---

# 21. Vereinsadmin testen

Mit dem neu erstellten Vereinsadmin anmelden.

Prüfen:

- [ ] Login funktioniert
- [ ] Benutzer landet direkt in seinem Verein
- [ ] richtiger Vereinsname sichtbar
- [ ] richtige Farben sichtbar
- [ ] richtiges Logo sichtbar
- [ ] aktivierte Module stimmen
- [ ] kein fremder Verein sichtbar
- [ ] kein Super-Admin-Bereich zugänglich

---

# 22. Testdaten anlegen

Für den Abnahmetest mindestens:

- [ ] eine News
- [ ] einen Termin
- [ ] ein Mitglied
- [ ] ein Dokument
- [ ] ein Galeriebild
- [ ] ein Fotoalbum
- [ ] optional ein Sujet
- [ ] optional Push-Gerät

Danach Daten nochmals öffnen und bearbeiten.

---

# 23. Zweiten Verein zum Isolationstest anlegen

Wenn die Cloud-Umgebung mehrere Vereine tragen soll:

1. Als Super-Admin zweiten neutralen Verein erstellen.
2. Eigene Farben setzen.
3. Eigenes Logo setzen.
4. Eigenen Vereinsadmin anlegen.
5. Eigene Testdaten erzeugen.
6. Als Vereinsadmin anmelden.
7. Prüfen, dass Verein 1 unsichtbar ist.
8. Als Super-Admin Verein 1 öffnen.
9. Prüfen, dass Verein 2 dort unsichtbar ist.

Der Test gilt nur als bestanden, wenn die Trennung in **beide Richtungen** funktioniert.

---

# 24. Backup

Da im aktuellen Stand viele Bilder und Dokumente direkt in SQLite gespeichert werden, ist die Datei:

```
/data/flapamamaku.db
```

besonders wichtig.

Backupstrategie:

- regelmäßige automatische Sicherung
- zusätzliche Sicherung vor jedem Update
- mehrere Generationen behalten
- Backup außerhalb des laufenden Containers speichern
- mindestens einmal Restore testen

Ein Backup ist erst vertrauenswürdig, wenn ein Restore erfolgreich getestet wurde.

---

# 25. Restore-Test

Restore niemals zuerst auf der einzigen produktiven Instanz ausprobieren.

Sicherer Ablauf:

1. Backup kopieren.
2. Testumgebung verwenden.
3. Container stoppen.
4. Datenbank durch Backup-Kopie ersetzen.
5. Container starten.
6. Health-Check.
7. Login.
8. Vereinsdaten.
9. Bilder.
10. Dokumente.
11. Adminrechte.
12. Multi-Tenant-Trennung prüfen.

---

# 26. Update-Ablauf

Vor jedem Backend-Update:

1. funktionierenden Image-Stand notieren
2. Datenbank sichern
3. Backup kontrollieren
4. neues freigegebenes Image auswählen
5. Container aktualisieren
6. Health-Check
7. Super-Admin-Login
8. Vereinsadmin-Login
9. News/Termine/Mitglieder prüfen
10. Bilder und Dokumente prüfen

Erst danach Update als erfolgreich markieren.

---

# 27. Rollback

Wenn ein Update fehlschlägt:

1. keine weiteren Änderungen durchführen
2. Logs sichern
3. vorheriges Docker-Image wieder verwenden
4. Anwendung starten
5. nur wenn erforderlich Datenbank-Backup zurückspielen
6. Health-Check durchführen
7. Vereinsdaten prüfen

Datenbank niemals vorschnell durch ein altes Backup überschreiben.

---

# 28. Logs

Bei Problemen zuerst die Logs öffnen.

Typische Kategorien:

- Startfehler
- Datenbankfehler
- Schreibrechte
- falsche Umgebungsvariable
- CORS
- Upload
- Speicherplatz
- HTTPS/Proxy

Fehlermeldung vollständig sichern.

Nicht nur die letzte Zeile kopieren.

---

# 29. Speicher überwachen

Da Medien derzeit teilweise direkt in SQLite liegen:

Regelmäßig prüfen:

- Größe der Datenbankdatei
- gesamter Speicherverbrauch
- Backup-Größe
- freier SSD-Speicher
- Wachstum pro Monat

Bei vielen Fotoalben kann die Datenbank deutlich wachsen.

---

# 30. Wann die Medienarchitektur erweitert werden sollte

Eine getrennte Medienablage sollte geprüft werden, wenn:

- viele Vereine produktiv sind
- sehr viele Fotoalben entstehen
- Datenbank-Backups sehr groß werden
- Restore zu lange dauert
- Speicherwachstum stark zunimmt

Dann wäre ein späterer Ausbau sinnvoll:

```
Datenbank
   |
   +-- Benutzer
   +-- Rechte
   +-- Vereinsdaten
   +-- Metadaten
   +-- Dateiverweise

Objektspeicher / Dateispeicher
   |
   +-- Verein 1
   +-- Verein 2
   +-- Verein 3
```

Das ist eine spätere gezielte Migration und kein Bestandteil dieser Erstinstallation.

---

# 31. SQLite und horizontale Skalierung

Der aktuelle stabile Stand nutzt SQLite.

Deshalb:

- einen aktiven Backend-Knoten verwenden
- nicht mehrere schreibende Backend-Knoten auf dieselbe DB-Datei setzen
- vertikal skalieren, wenn mehr CPU/RAM nötig ist
- horizontale Skalierung erst nach geplanter Datenbankmigration prüfen

Für deutlich größere Installationen kann später PostgreSQL vorgesehen werden.

---

# 32. Push / Firebase

Wenn Push-Nachrichten genutzt werden, muss für die jeweilige White-Label-Konfiguration die vorgesehene Firebase-Konfiguration vorhanden sein.

White-Label-Secrets können getrennt verwaltet werden.

Die Zugangsdaten gehören nicht in öffentlich sichtbare Dateien.

---

# 33. White-Label-App-Build

Die Serverinstallation und der mobile App-Build sind zwei getrennte Vorgänge.

Der Cloud-Server stellt das Backend bereit.

Die App verwendet die öffentliche HTTPS-Adresse dieses Backends.

Für einen dedizierten White-Label-Build werden unter anderem verwendet:

- API-Adresse
- App-Name
- Untertitel
- App-Icon
- optional eigene Firebase-Konfiguration

Die Android Application ID und das Signing dürfen nicht unkontrolliert verändert werden.

---

# 34. Sicherheit

Mindestens:

- HTTPS erzwingen
- starke Admin-Passwörter
- Super-Admin nur wenigen Personen geben
- keine Datenbank direkt veröffentlichen
- keine Secrets in Git committen
- Registry-Zugang nur mit minimal benötigten Rechten
- regelmäßige Backups
- Logs kontrollieren
- Softwareupdates geplant durchführen

---

# 35. Was ein Vereinsadmin nicht braucht

Der Vereinsadmin braucht keinen Zugang zu:

- Infomaniak
- Jelastic
- Docker
- GitHub
- Container Registry
- Datenbankdatei
- Load Balancer
- DNS
- SSL-Konfiguration

Er verwaltet seinen Verein ausschließlich über die dafür vorgesehene Admin-Oberfläche.

---

# 36. Was der Plattform-/Systemadmin verwaltet

Der Systemadmin verwaltet:

- Jelastic
- Docker-Image
- Domain
- HTTPS
- Persistenz
- Backups
- Restore
- Updates
- Super-Admin
- Plattformbetrieb

---

# 37. Fehlerhilfe für Nicht-Profis

## Domain funktioniert nicht

Prüfen:

1. DNS-Eintrag korrekt?
2. Jelastic-Umgebung läuft?
3. Load Balancer läuft?
4. Domain korrekt zugewiesen?
5. DNS-Änderung eventuell noch nicht verteilt?

## HTTPS funktioniert nicht

Prüfen:

1. Domain zeigt korrekt?
2. Zertifikat vorhanden?
3. Let's Encrypt erfolgreich?
4. Zertifikat zur richtigen Domain?

## Backend nicht erreichbar

Prüfen:

1. Docker-Knoten läuft?
2. Container-Logs?
3. interner Port 8000?
4. Load Balancer Weiterleitung?
5. Health-Endpunkt?

## Nach Neustart sind Daten weg

Sofort stoppen.

Wahrscheinlicher Fehler:

`/data` war nicht persistent.

Keine neuen Produktivdaten eingeben, bis Persistenz geklärt ist.

## Upload funktioniert nicht

Prüfen:

- freier Speicher
- Container-Logs
- Dateigröße
- Dateityp
- Backend erreichbar

## Fremde Vereinsdaten sichtbar

Sofort Test abbrechen.

Keine produktive Freigabe.

Dieser Zustand ist ein Sicherheitsfehler und muss vor Betrieb behoben werden.

---

# 38. Abnahmecheckliste

Die Cloud-Installation ist erst fertig, wenn:

- [ ] Jelastic-Umgebung läuft
- [ ] Docker-Backend läuft
- [ ] `/data` ist persistent
- [ ] Domain funktioniert
- [ ] HTTPS ohne Warnung
- [ ] `/api/health` erfolgreich
- [ ] Super-Admin funktioniert
- [ ] White-Label-Verein angelegt
- [ ] Vereinsadmin funktioniert
- [ ] Branding stimmt
- [ ] News funktionieren
- [ ] Termine funktionieren
- [ ] Mitglieder funktionieren
- [ ] Dokumente funktionieren
- [ ] Bilder funktionieren
- [ ] Backup erstellt
- [ ] Restore getestet
- [ ] zweiter Verein getestet, wenn Multi-Tenant genutzt wird
- [ ] gegenseitige Mandantentrennung erfolgreich
- [ ] keine Secrets öffentlich gespeichert

---

# 39. Empfohlene Reihenfolge

Immer:

```
Cloud-Umgebung
      ↓
Persistenz
      ↓
Backend
      ↓
Domain
      ↓
HTTPS
      ↓
Health-Check
      ↓
Super-Admin
      ↓
Verein
      ↓
Vereinsadmin
      ↓
Testdaten
      ↓
Backup
      ↓
Restore-Test
      ↓
Isolationstest
      ↓
Freigabe
```

Wenn ein Schritt fehlschlägt, nicht einfach zum nächsten wechseln.

---

# 40. Unterschied Synology ↔ Cloud

## Synology

- Server steht beim Betreiber vor Ort
- DSM / Portainer
- lokaler persistenter Ordner
- eigener Reverse Proxy

## Jelastic Cloud

- Server läuft beim Cloud-Anbieter
- Jelastic verwaltet Infrastruktur
- Docker-Knoten in Cloud
- persistenter Cloud-Speicher
- Load Balancer
- Cloud-Domain / eigene Domain
- Let's Encrypt

Die eigentliche Anwendung bleibt dieselbe.

---

# 41. Für einen externen White-Label-Kunden

Der externe Verein kann später zwei Betriebsmodelle wählen.

## Modell A – zentral betrieben

Der Plattformbetreiber hostet Backend und Datenbank.

Der Verein verwaltet nur:

- Branding
- Mitglieder
- Termine
- News
- Dokumente
- Bilder
- Vereinsadmin

Das ist für technisch wenig versierte Vereine die einfachste Variante.

## Modell B – selbst gehostet

Der Verein betreibt seine eigene Cloud-Umgebung nach diesem Handbuch.

Dann ist der Verein zusätzlich für:

- Cloud-Konto
- Domain
- Backups
- Updates
- Betrieb

verantwortlich.

---

# 42. Infomaniak/Jelastic-spezifische Hinweise

Nach aktuellem Infomaniak-Stand:

- Jelastic unterstützt benutzerdefinierte Docker-Container.
- NGINX kann als Load Balancer verwendet werden.
- Let's Encrypt kann für HTTPS eingesetzt werden.
- Ressourcen können später angepasst werden.
- Infomaniak betreibt die Infrastruktur in der Schweiz.
- benutzerdefinierte Docker-Images benötigen ein kostenpflichtiges Konto.

Da sich Bedienoberflächen ändern können, können Schaltflächen später leicht anders heißen. Die Architektur und Prüfreihenfolge dieses Handbuchs bleiben davon unberührt.

---

# 43. Offizielle Infomaniak-Unterlagen

Aktuelle Informationen vor einer Neuinstallation prüfen:

- Jelastic Cloud – Erste Schritte:
  https://www.infomaniak.com/de/support/faq/2252/erste-schritte-jelastic-cloud

- Docker-Installation als Beispiel:
  https://www.infomaniak.com/de/support/faq/2253/n8n-auf-jelastic-cloud-per-docker-image-installieren

- Container und Knoten:
  https://www.infomaniak.com/de/support/faq/2254/container-und-knoten-in-der-jelastic-cloud-verstehen

- SSL-Zertifikat:
  https://www.infomaniak.com/de/support/faq/169/ein-ssl-zertifikat-auf-jelastic-cloud-installieren

- verfügbare Ressourcen / Kontotypen:
  https://www.infomaniak.com/de/support/faq/2262/die-verfugbaren-ressourcen-von-jelastic-cloud-verstehen-je-nach-kontotyp

---

# 44. Abschlussregel

Ein White-Label-Verein wird erst produktiv freigegeben, wenn drei Dinge bestätigt sind:

1. **Betrieb:** Backend, Domain, HTTPS und Persistenz funktionieren.
2. **Daten:** Backup und Restore funktionieren.
3. **Isolation:** Ein Vereinsadmin kann ausschließlich seinen eigenen Verein sehen und verwalten.

Erst dann gilt die Cloud-Installation als betriebsbereit.

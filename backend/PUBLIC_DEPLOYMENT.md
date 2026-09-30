# Öffentlicher Betrieb / Multi-Verein / White Label

Der Standardbetrieb ist die gemeinsame Multi-Vereins-Plattform:

- **eine Codebasis**
- **ein Backend**
- **eine gemeinsame Datenbank**
- saubere Mandantentrennung über `club_id`
- FLAPAMAMAKU bleibt Verein / Tenant 1
- weitere Vereine werden über die Super-Admin-Oberfläche angelegt
- Benutzer mit einem Verein öffnen diesen direkt; Benutzer mit mehreren Vereinen können wechseln
- Super-Admins können zwischen Vereinen wechseln

Separate Codekopien oder ein eigener Server pro Verein sind **nicht** die Standardlösung.

## Öffentliche Adresse

Im zentralen Multi-Tenant-Betrieb verwenden alle Vereine dieselbe öffentliche HTTPS-Adresse des gemeinsamen Backends, zum Beispiel:

```
https://vereinsplattform.example.ch
```

Für die bestehende FLAPAMAMAKU-Installation bleibt
`FLAPAMAMAKU_API_BASE_URL` als kompatibler Fallback erhalten.

Build-Profile unter `config/white-label/` bleiben für Branding- und optionale dedizierte Builds bestehen. Sie ändern jedoch nichts an der serverseitigen `club_id`-Mandantentrennung.

## Zielarchitektur

```
Android / iPhone / Browser
          |
        HTTPS
          |
 Reverse Proxy / Plattform-TLS
          |
   gemeinsamer Backend-Container
          |
 gemeinsame Datenbank
          |
       club_id
   /      |      \
Verein 1 Verein 2 ... Verein 10
```

Die Datenbank wird niemals direkt veröffentlicht. Öffentlich erreichbar ist nur die HTTPS-Adresse des gemeinsamen Backends.

## Produktionsbetrieb

Für den zentralen Multi-Tenant-Betrieb gelten:

- eine öffentliche HTTPS-Adresse
- gültiges TLS-Zertifikat
- Backend ausschließlich hinter HTTPS / Reverse Proxy
- `FLAPAMAMAKU_ENV=production`
- `FLAPAMAMAKU_ALLOWED_ORIGINS` auf die produktive HTTPS-Adresse beschränken
- persistente Daten unter `/data`
- regelmäßige Backups und kontrollierte Restore-Tests
- Vereinsdaten ausschließlich über `club_id` trennen
- keine direkten Datenbankzugriffe aus Android/iOS
- Benutzer, Rollen, Module und Abrechnung bleiben vereinsbezogen

Die vorhandenen Umgebungsvariablen bleiben kompatibel, damit die bestehende FLAPAMAMAKU-Installation nicht umgebaut werden muss.

### Optionaler dedizierter Betrieb

Die bestehende Profil-/Instanzlogik kann weiterhin für einen bewusst separat betriebenen White-Label-Backend-Host genutzt werden. Das ist eine optionale Sonderform und nicht die Standardarchitektur für die zentrale Vereinsplattform.

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

Ein Verein benötigt dafür keinen eigenen Docker-Server. Im Standardbetrieb greifen alle Vereine auf das zentrale Multi-Tenant-Backend zu.

## Empfohlener Cloud-Pfad: Infomaniak Jelastic Cloud

Für den aktuellen Docker-Stand ist Jelastic Cloud der bevorzugte erste Cloud-Test, weil benutzerdefinierte Docker-Container unterstützt werden und die Plattform die zugrunde liegende Systemadministration weitgehend übernimmt.

Für den ersten Testbetrieb mit bis zu 10 Vereinen:

1. einen **einzelnen** Backend-Container aus dem bestehenden Image bereitstellen
2. Container-Port `8000` nur über die öffentliche HTTPS-Route freigeben
3. einen persistenten Datenträger nach `/data` einbinden
4. `FLAPAMAMAKU_DB=/data/flapamamaku.db` verwenden
5. `FLAPAMAMAKU_ENV=production` setzen
6. `FLAPAMAMAKU_ALLOWED_ORIGINS` auf die produktive HTTPS-Adresse begrenzen
7. automatische Plattform-Backups plus den vorhandenen App-Backup/Restore-Test verwenden
8. zunächst **nur einen Applikationsknoten** betreiben; SQLite darf nicht gleichzeitig von mehreren horizontal skalierten Backend-Knoten beschrieben werden
9. zuerst FLAPAMAMAKU und den neutralen Testverein als zwei Mandanten auf derselben Datenbank prüfen
10. erst nach erfolgreichem Restore-, Login-, Medien-, Abrechnungs- und Isolationstest weitere Vereine freigeben

### Datenbankstrategie

Der aktuelle stabile Stand verwendet SQLite. Für den Test mit wenigen Vereinen bleibt das die Variante mit dem geringsten Umbau.

Eine spätere Migration auf PostgreSQL ist sinnvoll, wenn echte horizontale Skalierung, mehrere gleichzeitig schreibende Backend-Knoten oder deutlich höhere Last erforderlich werden. Diese Migration ist **kein** Bestandteil des ersten Cloud-Rollouts und darf nicht nebenbei in den stabilen Stand eingebaut werden.

### Supabase

Supabase bleibt eine mögliche spätere PostgreSQL-Plattform. Für den jetzigen Stand wäre dafür aber eine bewusste Datenbankmigration von SQLite auf PostgreSQL nötig. Deshalb wird Supabase nicht als erster produktiver Cloud-Schritt verwendet.

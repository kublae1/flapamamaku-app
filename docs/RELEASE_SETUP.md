# FLAPAMAMAKU Release-Vorbereitung

## Android: dauerhafte Signierung

Für updatefähige Android-Releases wird immer derselbe private Keystore verwendet.
Der Keystore selbst wird **nicht** im Repository gespeichert.

In GitHub müssen einmalig diese Repository Secrets angelegt werden:

- `FLAPAMAMAKU_ANDROID_KEYSTORE_BASE64`
- `FLAPAMAMAKU_ANDROID_KEYSTORE_PASSWORD`
- `FLAPAMAMAKU_ANDROID_KEY_ALIAS`
- `FLAPAMAMAKU_ANDROID_KEY_PASSWORD`

Repository Variable:

- `FLAPAMAMAKU_ANDROID_APPLICATION_ID` — Standard im Workflow: `ch.flapamamaku.app`
- `FLAPAMAMAKU_API_BASE_URL` — später die öffentliche HTTPS-Adresse, z. B. `https://app-api.example.ch`

Der Workflow erzeugt:
- signierte APK für direkte Installation/Tests
- AAB für Google Play

Solange die vier Signing-Secrets fehlen, können Entwicklungsbuilds auf dem Feature-Branch
weiter erstellt werden. Auf `main` wird ein distributabler Release ohne dauerhafte
Signierung bewusst blockiert.

### Einmaliger Übergang

Die heute installierten APKs wurden mit wechselnder Build-Signatur erstellt.
Nach Einrichtung des dauerhaften Keystores muss die alte App **ein letztes Mal**
deinstalliert und die neue dauerhaft signierte APK installiert werden.
Danach können neue APK-Versionen über die vorhandene App installiert werden.

## Öffentliche Serveradresse

Vor Store-Veröffentlichung wird die bisherige LAN-Adresse durch eine öffentliche
**HTTPS**-Adresse ersetzt. Die App liest sie bereits aus `FLAPAMAMAKU_API_BASE_URL`.

Für den öffentlichen Betrieb noch erforderlich:
- DNS-Name
- gültiges TLS/HTTPS-Zertifikat
- Reverse Proxy vor dem Docker-Backend
- kein direkter öffentlicher SQLite-/Container-Port
- CORS/Host-/Rate-Limit-/Login-Härtung vor Internetfreigabe
- Backup der persistenten Docker-Daten

## Google Play

Für die spätere Veröffentlichung:
- endgültige Android Application ID beibehalten
- dauerhaften Keystore sichern und zusätzlich offline archivieren
- AAB verwenden
- Play Console App anlegen
- Store-Eintrag, Screenshots, Datenschutzangaben und App-Icon vorbereiten
- Versionscode bei jedem Release erhöhen
- erst interner Testtrack, danach Produktion

Eine automatische Play-Store-Veröffentlichung wird erst aktiviert, wenn das
Google-Play-Servicekonto eingerichtet und als GitHub Secret hinterlegt ist.

## Apple / iOS

Für iOS wird danach ein eigener Release-Schritt aufgebaut:
- Apple Developer Account / Team
- endgültiger Bundle Identifier
- App Store Connect App
- Distribution Certificate / Signing
- Provisioning bzw. App-Store-Connect-API-Key
- iOS App-Icon und Launch-Konfiguration
- HTTPS-Backend
- TestFlight vor App-Store-Produktion

Private Apple-Schlüssel und Zertifikate gehören ebenfalls ausschliesslich in
GitHub Secrets bzw. in Apples Signing-Infrastruktur und niemals ins Repository.

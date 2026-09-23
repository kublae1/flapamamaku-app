# FLAPAMAMAKU App – Version 0.1

Erste technische Grundversion der mobilen FLAPAMAMAKU-App.

## Enthalten
- Startseite
- News
- Termine
- Mitglieder
- Mehr-Menü
- Testdaten
- Material-3-Design in FLAPAMAMAKU-Rot
- GitHub-Actions-Workflow zum Erzeugen einer Android-APK

## Noch nicht enthalten
- Login / Benutzerrechte
- echte Mitgliederdaten
- Server / API / Datenbank
- Push-Mitteilungen
- Foto-Uploads
- PDF-Anzeige
- Admin-Weboberfläche

## Android APK über GitHub erzeugen
1. Unter **Actions** den Workflow **Build Android APK** öffnen.
2. **Run workflow** starten.
3. Nach erfolgreichem Lauf unter **Artifacts** die Datei `flapamamaku-android-apk` herunterladen.
4. ZIP entpacken und `app-release.apk` auf dem Android-Gerät installieren.

Für eine Store-Veröffentlichung werden später App-Signierung, Paket-ID, App-Icon, Datenschutzangaben und Store-Konfiguration ergänzt.

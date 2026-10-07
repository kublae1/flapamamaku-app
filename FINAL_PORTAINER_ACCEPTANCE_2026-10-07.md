# FLAPAMAMAKU – Finaler Portainer/Synology-Abnahmetest

Stand: 2026-10-07

## Freigegebener RC

- Quell-SHA: `af77311ec5a642030bdc72622992179a9ab9fb70`
- Stable-Referenz: `stable/masterplan-20261007-af77311`
- Docker-Image: `ghcr.io/kublae1/flapamamaku-backend:masterplan-phase9-rc-sha-af77311ec5a642030bdc72622992179a9ab9fb70`
- APK: `flapamamaku-0.8.33-build-261007004.apk`
- Paket-ID: `ch.flapamamaku.app`

## 1. Vor dem Update – Pflicht

1. Bestehenden Portainer-Stack nicht löschen.
2. Bestehendes Datenvolume nicht löschen.
3. Kein `docker volume rm` und kein `docker system prune --volumes` ausführen.
4. Aktuelle Stack-Konfiguration kopieren/sichern.
5. Bestehende Datenbankdatei `/data/flapamamaku.db` sichern.
6. Falls der Hostpfad verwendet wird, zusätzlich `/volume1/docker/flapamamaku/data` sichern.
7. Vorhandenes aktuell funktionierendes Docker-Image notieren, damit ein Rollback ohne Datenänderung möglich bleibt.

## 2. Portainer-Stack für den RC

Als Vorlage kann `backend/docker-compose.synology-masterplan-rc-20261007.yml` verwendet werden.

Nur die Image-Zeile des bestehenden produktiven Stacks auf den freigegebenen RC umstellen:

```yaml
image: ghcr.io/kublae1/flapamamaku-backend:masterplan-phase9-rc-sha-af77311ec5a642030bdc72622992179a9ab9fb70
```

Bestehende Ports, Reverse-Proxy-Konfiguration, Umgebungsvariablen und Datenpfade unverändert lassen, sofern sie im aktuell funktionierenden Stack abweichen.

## 3. Container-Start prüfen

Nach `Update the stack` kontrollieren:

- Container `flapamamaku-backend` läuft.
- Keine Restart-Schleife.
- Bestehendes Datenvolume ist weiterhin eingebunden.
- Keine neue/leere Datenbank wurde erzeugt.
- `GET /api/health` liefert HTTP 200 und `status: ok`.
- `instance_id` ist `flapamamaku`.
- `build_sha` entspricht dem RC-Stand.

Bei einem Fehler hier NICHT mit App-Tests fortfahren. Stack auf das vorherige Image zurückstellen; Datenvolume unverändert lassen.

## 4. Datenbestand prüfen

Vor App-Update im Admin/CMS prüfen:

- bestehende Benutzer vorhanden
- bestehende Mitglieder vorhanden
- News vorhanden
- Termine vorhanden
- Bilder/Galerien vorhanden
- aktuelles Sujet und Archiv vorhanden
- Vereinszuordnung korrekt
- Plattform-/Billing-Daten erreichbar

Es dürfen keine Demo-Daten oder leere Ersatzdaten anstelle des bestehenden Bestands erscheinen.

## 5. Android-Update ohne Deinstallation

Die vorhandene FLAPAMAMAKU-App NICHT deinstallieren.

APK `flapamamaku-0.8.33-build-261007004.apk` über die bereits installierte App installieren.

Erwartung:

- Android akzeptiert das Update.
- Keine Signaturwarnung wegen inkompatibler Signatur.
- App-Daten bleiben erhalten.
- Paket-ID bleibt `ch.flapamamaku.app`.

## 6. Session-/Login-Abnahme

Reihenfolge verbindlich:

1. App öffnen.
2. Falls bereits angemeldet: direkt in der App landen.
3. App vollständig beenden.
4. App neu öffnen.
5. Sitzung muss weiterhin aktiv sein.
6. Biometrie darf den Restore nicht blockieren.
7. Danach bewusst `Abmelden` wählen.
8. App neu starten.
9. Jetzt muss Benutzername/Passwort wieder verlangt werden.
10. Neu anmelden und nochmals Neustart testen.

Bestanden nur, wenn kein normaler App-Neustart das gespeicherte Login löscht.

## 7. Vereins-/Mandantenisolation

Mindestens zwei Vereine verwenden, sofern Testkonten vorhanden sind.

Prüfen:

- Benutzer Club A sieht nur Club-A-Mitgliedsdaten.
- Termine aus Club B erscheinen nicht in Club A.
- News aus Club B erscheinen nicht in Club A.
- Bilder/Galerien aus Club B erscheinen nicht in Club A.
- Sujet aus Club B erscheint nicht in Club A.
- Dokumente/Umfragen bleiben club-isoliert.
- Ein Benutzer, der mehreren Clubs angehört, erhält nach Wechsel des `active_club_id` die korrekte Mitgliedsidentität.
- Normaler Vereinsadmin kann nicht global den Verein wechseln.
- Superadmin kann den vorgesehenen Vereinswechsel verwenden.

Bei irgendeinem Cross-Club-Leak: Abnahme STOPP, kein Produktiv-Freigabestatus.

## 8. Push-Abnahme

Mit mindestens zwei Testbenutzern bzw. zwei Vereinskontexten prüfen:

1. App öffnen und Push-Berechtigung erlauben.
2. FCM-Token registrieren lassen.
3. Push an Club A senden.
4. Nur Geräte/Tokens von Club A dürfen die Nachricht erhalten.
5. Push an Club B senden.
6. Nur Geräte/Tokens von Club B dürfen die Nachricht erhalten.
7. App einmal neu starten und Registrierung/Push nochmals prüfen.

Keine Änderung an funktionierenden Push-Triggern oder pauschale Trigger-Löschung durchführen.

## 9. Medien/Sujet

Prüfen:

- Bilder laden zuverlässig.
- Galerie zeigt nur Bilder des aktiven Vereins.
- Fotoalbum funktioniert.
- aktuelles Jahres-Sujet wird korrekt angezeigt.
- Archiv vergangener Sujets funktioniert.
- genau ein aktuelles Sujet.
- keine falsche Legacy-Sujet-Schreibroute wird sichtbar verwendet.

## 10. Phase 9 – Plattform/Billing

Als Superadmin prüfen:

- Vereinsübersicht vorhanden.
- Billing/Rechnungsdaten erreichbar.
- ganzen Verein testweise sperren, sofern ein dafür vorgesehener Testverein vorhanden ist.
- gesperrter Verein erhält keinen normalen Softwarezugriff.
- Verein wieder freigeben.
- Zugriff funktioniert wieder.
- andere Vereine bleiben währenddessen unbeeinflusst.

Nicht mit einem produktiv benötigten Verein testen, wenn eine Sperrung den laufenden Betrieb beeinträchtigen würde.

## 11. Backup/Restore-Sicherheit

- Bestehende Backups weiterhin vorhanden.
- Datenbank-Integrität ohne Fehler.
- Keine destructive migration durchgeführt.
- Kein bestehender Recovery-Punkt gelöscht.

Ein echter Restore auf die produktive DB ist für die Abnahme nicht erforderlich, wenn dadurch unnötiges Risiko entsteht; Restore-Funktion nur mit separater Testkopie validieren.

## 12. Rollback

Falls Backendfehler auftreten:

1. Keine Datenbankdatei löschen.
2. Stack stoppen bzw. Image-Zeile auf das vorher funktionierende Image zurücksetzen.
3. Stack erneut starten.
4. Datenvolume unverändert verwenden.
5. Health, Login und Datenbestand kontrollieren.

Zusätzliche feste Rückfallpunkte:

- `ghcr.io/kublae1/flapamamaku-backend:masterplan-push-hotfix-sha-bef0b14fb22f50b967890f28ce0b914684e6c112`
- `ghcr.io/kublae1/flapamamaku-backend:recovery-app581-sha-de981c0`
- `ghcr.io/kublae1/flapamamaku-backend:sha-175c23b`

Die Wahl des Rollback-Images richtet sich nach dem unmittelbar vor dem Test tatsächlich laufenden Stand. Nicht blind auf einen älteren Stand wechseln, wenn der aktuelle Produktionsstand neuer ist.

## 13. Freigabekriterium

Phase 0–9 gilt für den Praxistest als freigegeben, wenn alle folgenden Punkte grün sind:

- Backend startet mit bestehender DB.
- Health OK.
- vorhandene Daten vollständig.
- APK aktualisiert ohne Deinstallation.
- Login funktioniert.
- Session bleibt nach Neustart bestehen.
- Logout erzwingt danach Login.
- Biometrie funktioniert ohne Session-Regression.
- Vereinsisolation vollständig korrekt.
- Medien korrekt isoliert.
- Push korrekt isoliert.
- Superadmin-/Vereinsadmin-Rechte korrekt.
- Phase-9 Billing/Sperrung korrekt.
- keine Datenverluste.
- Rollback bleibt möglich.

Nach erfolgreicher manueller Abnahme kann dieser RC als finaler Phase-0–9-Stand markiert werden. Phase 10+ bleibt ausserhalb dieses Tests.

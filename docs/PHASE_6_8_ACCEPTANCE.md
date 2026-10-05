# FLAPAMAMAKU – Abnahme Phase 6 bis 8

**Geltungsbereich:** ausschließlich Masterplan Phase 6, 7 und 8.  
**Nicht enthalten:** Phase 9 Plattformverwaltung/Abrechnung und spätere Phasen.

## Phase 6 – Migrationen, Backup, Logging, Monitoring

Abnahmekriterien:

- Datenbankschema bleibt migrationsgeführt und erreicht `CURRENT_SCHEMA_VERSION = 10`.
- Backups werden als konsistente SQLite-Kopien erstellt und per `PRAGMA integrity_check` geprüft.
- Manuelle und automatische Backups verwenden das konfigurierte Backup-Verzeichnis und eine begrenzte Aufbewahrung.
- Restore prüft Integrität und Vereinsinstanz vor dem Austausch der produktiven Datenbank.
- Vor einem Restore wird automatisch ein Sicherheitsbackup erstellt.
- Nach Restore werden bestehende Sessions ungültig gemacht.
- `/api/system/status` liefert Datenbankintegrität, Speicher-, Backup- und Sessionstatus.
- Produktions-Compose enthält Container-Healthcheck und begrenzte Docker-Logrotation.
- Betriebsparameter werden über Umgebungsvariablen konfiguriert; keine Secrets liegen im Repository.

Automatisierte Nachweise:

- `backend/tests/phase6_8_operations.py`
- `backend/tests/phase7_praxis_smoke.py`
- Phase-6–8-GitHub-Action-Gate

## Phase 7 – FLAPAMAMAKU-Praxistest

Der Praxistest läuft gegen einen echten gestarteten Backend-Prozess und prüft den Betriebsweg aus Sicht eines Administrators:

1. Healthcheck und korrekte Vereinsinstanz.
2. Bootstrap/Login eines Administrators.
3. Systemstatus und Datenbankintegrität.
4. Manuelles Backup.
5. Backup-Download.
6. Restore dieses Backups.
7. Automatische Invalidierung alter Sessions.
8. Erneuter Login.
9. Sichtbarkeit von manuellem Backup und Restore-Sicherheitsbackup.
10. Datenbankintegrität nach dem Restore.

Zusätzlich müssen alle bestehenden Phase-1-, Phase-2- und Phase-3–5-Verträge weiter grün bleiben.

## Phase 8 – Pilotvorbereitung für drei weitere Vereine

Für die technische Pilotierung werden drei neutrale, datenschutzneutrale Vereinsprofile geführt:

- `pilot-verein-a`
- `pilot-verein-b`
- `pilot-verein-c`

Die Profile enthalten keine realen Vereins-, Personen- oder Zugangsdaten. Reale Vereinsnamen, Domains, Icons und Zugangsdaten werden erst beim konkreten Onboarding ausserhalb des Repositorys eingesetzt.

Abnahmekriterien:

- Eindeutige `id`, `instance_id` und API-Hosts pro Pilotprofil.
- Serverwechsel ist für Pilot-Builds standardmässig deaktiviert.
- Jede Pilotinstanz erhält eine eigene SQLite-Datenbank und ein eigenes Backup-Verzeichnis.
- Der Datenbank-Tenant-Guard verhindert Inserts mit fremder `club_id`.
- Ein automatisierter Matrix-Test startet drei getrennte Instanzen und weist nach, dass keine News-/Testdaten zwischen den Vereinsdatenbanken sichtbar werden.
- White-Label-Profile werden syntaktisch und semantisch validiert.

Automatisierter Nachweis:

- `backend/tests/phase8_pilot_matrix.py`

## Abschluss-Gate

Phase 6–8 gelten erst als abgeschlossen, wenn gleichzeitig:

- Backend-Kompilierung grün ist,
- bestehende Vertrags-/Regressionstests grün sind,
- Phase-6-Backup/Restore-Test grün ist,
- Phase-7-Praxistest grün ist,
- Phase-8-Pilotmatrix grün ist,
- Flutter `analyze` grün ist,
- Flutter Tests grün sind,
- Android Release APK erfolgreich baut,
- Pull Request nach `main` gemergt ist,
- und der gemergte `main`-Stand seine regulären Build-/Backend-Checks erfolgreich durchläuft.

Erst danach darf Phase 9 freigegeben werden.

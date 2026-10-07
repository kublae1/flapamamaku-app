# FLAPAMAMAKU Masterplan Gap Report — 2026-10-07

## Referenzstand

- Arbeitsbranch: `feature/masterplan-on-recovered-20261006`
- geprüfter HEAD: `af77311ec5a642030bdc72622992179a9ab9fb70`
- Commit: `Masterplan: finalize Phase 9 release CI`
- gesicherter Rückfallbranch: `stable/masterplan-20261007-af77311`

## Ergebnis Phase 0–9

Der geprüfte Stand enthält die Masterplan-Gates für Backend, Flutter, Phase 1, Phase 3–5, Phase 6/8 und Phase 9 sowie den gehärteten Android-Releasepfad. Der Masterplan-Gate-Lauf für den geprüften HEAD war erfolgreich. Der Android-V8-Build für denselben HEAD war erfolgreich.

### Phase 0–2

Status: funktional abgedeckt durch bestehenden stabilen Basisstand und CMS-/Baseline-Contracts. Keine destruktive Änderung vorgenommen.

### Phase 3–5

Status: Contract-Test `backend/tests/phase3_5_contract.py` ist Bestandteil des Masterplan-Gates. Die aktuelle Canonical-Sujet-/Termin-Logik bleibt unangetastet.

### Phase 6

Status: `backend/tests/phase6_8_operations.py` ist Bestandteil des Masterplan-Gates. Bestehende Backup-/Datenpfade bleiben unverändert.

### Phase 7–8

Status: `backend/tests/phase8_pilot_matrix.py` sowie der integrierte Multi-Club-Runtime-Start sind Bestandteil des Masterplan-Gates. Bestehende Mandantenisolation wird nicht zurückgebaut.

### Phase 9

Status: `backend/tests/phase9_platform_contract.py` und `backend/tests/platform_club_selector_contract.py` sind Bestandteil des Masterplan-Gates. Release-Candidate-Gate validiert zusätzlich Runtime, öffentliche Backend-Identität, Flutter und Android-Releaseinputs.

## Android

Der gehärtete Android-V8-Build verwendet:

- Paket-ID `ch.flapamamaku.app`
- permanente Release-Signatur über die FLAPAMAMAKU-Keystore-Secrets
- native Firebase-Ressourcen
- `POST_NOTIFICATIONS`
- Biometrie-Unterstützung
- monoton aus Datum + Workflow-Run abgeleitete Buildnummer
- eindeutigen APK-Dateinamen
- `apksigner verify --print-certs`

Für HEAD `af77311...` wurde erfolgreich das Artefakt `flapamamaku-0.8.33-build-261007004` erzeugt.

## Docker / Runtime

Der Dockerfile startet derzeit `app.push_runtime:app`. Das ist kein separater Anwendungsstack: `push_runtime.py` importiert `app` direkt aus `.runtime` und ergänzt ausschließlich die gezielte Bereinigung bekannter Legacy-`push_tokens`-Trigger mit dem Fehlertext `wrong club_id`. Damit bleibt die integrierte Runtime die eigentliche FastAPI-App, während der aktuell funktionierende Push-Hotfix erhalten bleibt. Dieser Wrapper wird deshalb nicht auf `app.runtime:app` zurückgebaut, solange der Trigger-Hotfix noch als Startup-Schutz benötigt wird.

Der RC-Release-Workflow baut Docker Multi-Arch für `linux/amd64,linux/arm64` und verwendet ein unveränderliches SHA-basiertes Tag.

## Offene Punkte nach Code-/CI-Prüfung

Keine neue funktionale Phase-0–9-Code-Lücke wurde festgestellt, die ohne unnötiges Regressionsrisiko sofort geändert werden sollte.

Noch offen für die endgültige Freigabe sind ausschließlich Release-/Praxiskontrollen:

1. finales RC-Docker-Image auf der Ziel-Synology/Portainer-Umgebung starten,
2. bestehendes Datenvolume unverändert anbinden,
3. Login → App-Neustart → Session bleibt aktiv prüfen,
4. Logout → erneuter Login erforderlich prüfen,
5. Push mit echtem Gerät prüfen,
6. Vereinswechsel nur als Superadmin und Cross-Club-Isolation mit realen Vereinsdaten prüfen,
7. erzeugte APK als Update über die aktuell installierte App installieren, ohne Deinstallation,
8. nach erfolgreichem Praxistest den finalen Release-Commit/Tag und das eindeutige finale Docker-Testimage festhalten.

## Nicht geändert

- keine produktiven Daten gelöscht,
- keine Volumes gelöscht,
- keine destruktive Migration,
- kein Rückbau von Session, Secure Storage, Multi-Club, Firebase oder Push,
- Phase 10+ nicht begonnen.

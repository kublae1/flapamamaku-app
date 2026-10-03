# Phase 2 – Vereins-CMS Abnahmeprotokoll

**Arbeitsbranch:** `feature/masterplan-phase0-2-20261003`  
**Gegenstand:** ausschließlich Phase 2 des verbindlichen Masterplans.

## Ziel

Der Browser-Admin soll als zentrale Vereins-CMS-Oberfläche funktionieren, ohne dass ein Vereinsadministrator für normale Inhaltsänderungen Quellcode bearbeiten muss.

## Verbindliche CMS-Struktur

### Hauptnavigation

- News
- Termine
- Mitglieder
- Benutzer & Rechte
- Medien & Inhalte
- Push
- Verein & System

### Medien & Inhalte

Der Medienbereich trennt folgende Inhalte ausdrücklich:

- Startseite / Hauptbild (`hero`)
- Sujet nächstes Jahr (`sujet`)
- Vergangene Sujet (`archive`)
- Galerie · Einzelbilder (`gallery`)
- Fotoalben · Alben (`photos`)
- Dokumente (`documents`)
- Umfragen (`polls`)
- Links (`links`)
- WhatsApp (`whatsapp`)

## Erfüllte Bedienanforderungen

- Zentrale Formulare für News, Termine, Mitglieder, Benutzer/Rechte und App-Inhalte.
- Datei-/Bild-Uploads statt fest eingebauter Vereinsbild-Auswahl im PC-CMS.
- Vorhandene Bilder werden angezeigt und können verwaltet werden.
- Bildreihenfolge kann administriert werden.
- Visuelle Telefon-/App-Vorschau ist vorhanden.
- Löschen und andere destruktive Aktionen verwenden Bestätigungsdialoge.
- Vereinseinstellungen sind von der gewöhnlichen Inhaltsverwaltung getrennt.
- Rollen und Einzelberechtigungen sind getrennt administrierbar.
- Zentraler Statusbereich für Server-/Administrationsstatus ist vorhanden.

## Automatisierte Absicherung

`backend/tests/admin_cms_contract.py` prüft in CI, dass die verbindliche CMS-Struktur nicht unbeabsichtigt entfernt wird.

Die Datei `.github/workflows/phase0-2-gate.yml` führt aus:

1. statischen Phase-2-CMS-Vertragstest,
2. isolierten Phase-1-API-/Persistenzvertragstest,
3. `flutter analyze`,
4. `flutter test`.

## Abgrenzung

Nicht Teil dieser Phase sind neue fachliche Funktionen aus Phase 3 oder später, insbesondere der funktionale Ausbau der Termine, ein neues Sujet-Datenmodell, Multi-Tenant-Härtung oder neue Abrechnungsfunktionen.

## Technischer Abnahmestatus

Phase 2 ist **GETESTET**, sobald der vollständige `Phase 0-2 Gate` auf dem finalen Branch-Stand erfolgreich abgeschlossen ist. Die produktive Freigabe erfolgt erst nach Integration in `main` und erfolgreicher CI auf dem integrierten Stand.

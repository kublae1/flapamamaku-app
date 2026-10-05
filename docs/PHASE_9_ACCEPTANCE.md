# Phase 9 – Plattformverwaltung / Abrechnung

## Freigegebener Umfang

Phase 9 erweitert die getrennten Vereinsinstanzen um eine zentrale Plattformverwaltung. Phase 10 und später bleiben ausdrücklich ausserhalb dieses Pakets.

## Architektur

- Vereinsdaten bleiben pro Vereinsinstanz getrennt.
- Die zentrale Plattform besitzt eine eigene SQLite-Datenbank `platform.db`.
- Der Plattform-Superuser verwaltet nur Plattform-/Betriebsdaten, nicht heimlich die Vereinsdatenbanken.
- Die Plattform-Datenbank enthält Vereinsregister, Rechnungen, Zahlungsstatus, Sperrstatus, Superuser-Sitzungen und Audit-Protokoll.
- Das Vereinsbackend liest nur den Sperrstatus seiner eigenen `instance_id`.

## Superuser

- Der erste Superuser wird einmalig über die Plattform-Weboberfläche erstellt.
- Nach erfolgreichem Bootstrap ist eine zweite Ersteinrichtung gesperrt.
- Es werden keine Superuser-Passwörter oder Tokens im Repository gespeichert.
- Nicht angemeldete Zugriffe auf Plattform-Verwaltungsfunktionen liefern 401.

## Vereinsverwaltung

Der Superuser kann zentral:

- Vereine erfassen und bearbeiten,
- eindeutige `instance_id` und API-Adresse verwalten,
- Abrechnungs-E-Mail, Monatsgebühr, Rechnungstag und Zahlungsziel pflegen,
- automatische Sperre bei überfälliger Rechnung aktivieren,
- Vereine manuell sperren und wieder freigeben,
- den aktuellen Status aller Vereine in einer Übersicht sehen.

## Abrechnung

- Pro Verein und Monat wird höchstens eine Monatsrechnung erzeugt.
- Der automatische Abrechnungslauf wird periodisch ausgeführt und kann zusätzlich manuell gestartet werden.
- Rechnungen haben Nummer, Periode, Rechnungsdatum, Fälligkeit, Betrag, Währung und Status.
- Rechnungen können als PDF heruntergeladen und als bezahlt markiert werden.
- Bei aktivierter Auto-Sperre führt eine überfällige offene Rechnung zur automatischen Vereinssperre.
- Wurde ein Verein ausschliesslich automatisch wegen überfälliger Rechnungen gesperrt, wird er nach Begleichung der letzten überfälligen Rechnung automatisch wieder freigegeben.

## Softwareseitige Sperre

- Der Sperrstatus liegt zentral in der Plattform-Datenbank.
- Das Vereinsbackend prüft bei Requests seine eigene `instance_id`.
- Bei gesperrtem Verein bleiben Healthchecks erreichbar; Vereins-API und PC-Admin werden mit HTTP 423 blockiert.
- Es werden bei einer Sperre keine Vereinsdaten gelöscht oder verändert.

## Betrieb

Die Produktions-YAML startet zwei Dienste aus demselben signierten Backend-Image:

1. `flapamamaku-backend` auf lokalem Port 8087,
2. `flapamamaku-platform` auf lokalem Port 8091.

Beide verwenden das globale Docker-Volume `flapamamaku-platform-data`. Das Backend bindet dieses nur lesend ein. Die Plattform besitzt Schreibzugriff.

## Verbindliches Phase-9-Gate

Vor Merge nach `main` müssen mindestens erfolgreich sein:

- Python-Compile der Plattformmodule,
- Phase-9-End-to-End-Test,
- Superuser-Bootstrap und Login,
- drei Vereinsdatensätze in der Plattformverwaltung,
- automatische Rechnungsanlage,
- PDF-Erzeugung,
- manuelle Sperre und Freigabe,
- Sperrwirkung auf eine reale gestartete Vereinsbackend-Instanz,
- automatische Überfälligkeits-Sperre,
- automatische Freigabe nach Zahlung,
- Audit-Protokoll und SQLite-Integrität,
- Production-Compose-Validierung,
- Phase-6–8-Regressionsprüfungen,
- Flutter Analyze, Tests und Android-Release-APK,
- PR-Merge und anschliessende `main`-Validierung.

## Abgrenzung

Nicht Teil von Phase 9:

- Testbetrieb bis 10 Vereine,
- Skalierungsfreigabe für 10 Vereine,
- Version 1.0,
- Funktionen aus Phase 10 oder 11.

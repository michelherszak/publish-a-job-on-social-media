# Recruiting-Kernablauf – lokaler Implementierungsstand

Stand: 2. Oktober 2026. Der Nutzer hat UC-Z01 bis UC-Z11 zur Umsetzung freigegeben und die optionale Prüfrunde UC-Z12 zurückgestellt. Nutzenbewertungen, Zielbranche und wirtschaftlicher Pilotnachweis bleiben offen.

Der erste Durchlauf verwendet die vorhandene Kampagne als Stellenbedarf. Ein eigenes Stellenobjekt mit mehreren Kampagnen wird damit nicht beschlossen. Ansprechpartner sind berechtigte Firmen-Admins oder Bearbeiter derselben Firma; vorhandene Freigaberechte bleiben bestehen.

## Bedienung

Firmenteam → **Recruiting** → Stelle wählen. Bedarf und Zuständigkeiten speichern; über **Texte, Freigabe & Bewerbungsseite** das Briefing vervollständigen, Materialien erstellen, prüfen und die eigene Bewerbungsseite separat aktivieren. Der Bedarf lässt sich schon mit Stellentitel speichern; Arbeitsort ist vor Generierung nötig. Gewünschter Start, Vergütung und weitere unbekannte Angaben bleiben offen.

Im Briefing sind notwendige und lernbare Fähigkeiten getrennt. Vorgefüllte Vorteile lassen sich vollständig entfernen. Vor einer neuen Generierung bestätigt der Nutzer die geprüften Angaben sowie separat die bestehenden Kosten. Die Demo-Vorlagen ergänzen keine fehlenden Vorteile. Eine geänderte Briefingfassung verändert vorhandene Texte nicht; das Studio zeigt den Abgleichbedarf. Bei neu generierten Materialien sperrt die API eine Freigabe nach Briefingänderung bis zur ausdrücklich bestätigten erneuten Prüfung. Ältere Materialien ohne gespeicherten Briefingbezug werden als ungeprüft angezeigt; ihre bestehende manuelle Freigabe bleibt kompatibel. Wiederverwendete Texte sind immer ein neuer Draft ohne alte Freigabe.

Persönliche Rückmeldung, Terminvorschlag, Bewerberzusage und Gesprächsergebnis werden ausdrücklich manuell dokumentiert. Der Antwortentwurf bleibt nur im offenen Formular. Er wird weder versendet noch als Reaktion gezählt. Datum/Uhrzeit werden in der Browser-Zeitzone eingegeben und mit einem eindeutigen Zeitpunkt und Zeitzone gespeichert. Eine Zusage erfordert einen vorherigen Vorschlag. Verschieben erzeugt einen neuen Vorschlag, Absagen erhalten den Verlauf. Geführt/nicht erschienen lässt sich erst nach dem bestätigten Termin dokumentieren.

Eine selbst festgelegte Antwortfrist erzeugt bei neuen eigenen Bewerbungen eine Aufgabe. Existierende gespeicherte Fristen werden nicht rückwirkend ersetzt. Aufgabe, Frist und Zuständigkeit können mit nachvollziehbarem Ereignis geändert werden. Nur offene Aufgaben mit vergangener Frist erscheinen als überfällig. Lesen, Zuordnen oder Erinnern beantwortet keinen Kontakt.

Ein manueller Veröffentlichungsnachweis verlangt Freigabe, zuständige Erstreaktion und einen aktiven Bewerbungslink desselben Kanals/Variante. Ein Nachweislink ist optional. Die API ruft keinen Anbieter auf; Facebook-Anbieterbestätigungen bleiben im vorhandenen separaten Studio-Ablauf.

Pause/Abschluss deaktiviert die eigene Seite und alle MH-Anzeigenlinks. Bestehende externe Beiträge bleiben bestehen und sind separat zu prüfen. Aufbewahrte Kontakte lassen sich weiter beantworten. Eine abgeschlossene Suche wird als neuer Bedarf wiederverwendet; eine Pause lässt sich wieder öffnen, Seite und Links bleiben bis zur gesonderten Aktivierung deaktiviert. Wiederverwendung kopiert Briefing und Materialien, aber keine Bewerbungen, Termine, Links, Veröffentlichungsnachweise oder Freigaben und startet keine Generierung.

## Abnahmen und Belege

| Use Case / Kriterien | Umsetzung | Ausführbare Nachweise |
| --- | --- | --- |
| Z01-A1–A3 | Unvollständiger Bedarf, explizite Zuständigkeiten, Firmenzugriff, keine Generierung beim Speichern | `test_incomplete_need_is_saved_without_generation_or_fabricated_date`, `test_isolation_roles_owner_validation_csrf_and_optimistic_version` |
| Z02-A1–A3 | Muss-/Lernanforderungen, tatsächliche Arbeitszeiten, keine erfundene Vergütung/Benefits, verwerfbare Profilvorgaben | `test_material_snapshot_and_learnable_requirements_and_discarded_benefits`; bestehende KI-Tests; Assistent im Browser |
| Z03-A1–A4 | Vorhandene Token-/Rollback-/Idempotenzregeln plus gespeicherter Briefingbezug und sichtbarer erneuter Abgleich | `backend/test_ai.py`, `backend/test_billing.py`, Material-Snapshot-Test |
| Z04-A1–A3 | Bestehende interne Freigabe, Änderungswunsch, Rechte und Statusverlauf | `backend/test_security.py`, `backend/test_auth.py`; Snapshot-Test |
| Z05-A1–A4 | Export, eigene Firmenverbindung, separater Facebook-Ablauf plus manueller Veröffentlichungsnachweis | `backend/test_social.py`, `test_manual_publication_and_close_reuse_do_not_copy_contacts_or_charge` |
| Z06-A1–A4 | Vorhandenes mobiles Formular ohne Konto, verschlüsselte Speicherung, eindeutige Quittung, Fehler-/Datenschutzgates | `backend/test_tracking.py`, `frontend/src/Apply.tsx` |
| Z07-A1–A4 | Übernahme, lokaler Antwortentwurf, tatsächliche manuelle Rückmeldung, Erstreaktionszeit, Ereignisverlauf | `test_real_response_not_read_or_task_and_idempotent_evidence`, `test_concurrent_claim_has_one_winner`; Browserprüfung |
| Z08-A1–A3 | Vorschlag, echte manuell dokumentierte Zustimmung, Absage, Verschiebung und Ergebnis getrennt | `test_proposal_confirmation_reschedule_cancel_and_held_are_distinct`; Browserprüfung |
| Z09-A1–A3 | Sichtbare offene Fristen, firmengebundene Weitergabe, keine automatische Absage/Nachricht | `test_overdue_task_delegation_and_completion` |
| Z10-A1–A4 | UTC-Zeitraum, Quittungen, manuelle Ereignisse, reale Reaktionszeit, Aufwand/Begleitung, begründeter Vergleich | `test_effort_comparison_unknowns_range_and_duplicate`, Antwort-/Termintests; Tracking-Berichte |
| Z11-A1–A4 | Bewusster Abschluss, gesperrter Neueingang, unveränderte externe Posts, kontrollierte Kopie, Retention | Abschluss-/Wiederverwendungstest, `test_retention_erases_workflow_notes_and_keeps_anonymous_counts` |

Zusätzliche Kompatibilitätsprüfung: eine bereits gespeicherte Demo-Rollen-Datenbank ohne die neue Briefing-Spalte wird additiv migriert, ohne ihre Inhalte zu überschreiben.

Die neuen Tests stehen in `backend/test_recruiting.py` und verwenden ausschließlich temporäre Datenbanken und fiktive Kontakte. Die Tabelle beschreibt den lokalen manuellen Pilotmodus, keine externe Anbieterabnahme. Ein Versandfehler-Workflow ist hier nicht erforderlich, da dieser Ausbau keine persönlichen Nachrichten versendet. Integrierter Bewerberversand oder Kalender wären gesonderte Erweiterungen.

## Daten, Rechte und Kennzahlen

`backend/recruiting.py` ergänzt Bedarf, Bewerberfall, Ereignisse, manuelle Veröffentlichungen, Aufwand und Wiederverwendungsnachweis. Versionsprüfung unter SQLite-Transaktion verhindert stille konkurrierende Übernahmen. Ereignisse, Aufwand, manuelle Publikationen und Wiederverwendung haben eindeutige Anfrage-IDs. Persönliche Ereignisdetails und Fallnotizen werden verschlüsselt. Die ursprüngliche Aufbewahrungsfrist der eigenen Bewerbung löscht auch persönliche Fall-/Ereignisnotizen, Zuständigkeit, offene Frist und Termin; Abschluss verlängert die Frist nicht. Anonyme Quittungen und Ereignisarten/-zeiten bleiben für Auswertungen erhalten. Der Hintergrundbereiniger läuft jede Minute; Workflow-Lese-/Schreibzugriffe bereinigen zusätzlich vor der Ausgabe.

Nur echte berechtigte Firmenmitglieder lesen persönliche Bewerberdaten. Plattform-Admin, Kunde und Demo-Rollenvorschau erhalten keinen Recruiting-Zugriff. Geschützte Schreibaktionen einschließlich Aktivierung der Bewerbungsseite verlangen ein aktives bezahltes Abo für verwaltete Firmen. Kostenlose bestehende Demo-Firmen bleiben frei. Fremde Kampagnen liefern 404. Neue Tabellen folgen Firmen-/Kampagnenlöschung über Fremdschlüssel; Akteure werden bei Nutzerlöschung anonymisiert.

Auswertung: Eingänge nach tatsächlichem Eingangsdatum; erste Reaktionen für diese Eingangskohorte bis Periodenende; Gesprächsereignisse nach dokumentiertem Ereignisdatum. Vereinbart/gehalten zählen je Bewerbung/Ereignisart im Zeitraum, auch wenn später abgesagt. Der aktuelle Einzelstatus zeigt separat die gültige Terminvereinbarung. Linkaufrufe sind Requests und keine einzigartigen Personen. Fehlende Beobachtung wird als unbekannt angezeigt. Externe ATS-Quittungen zählen als Eingang, enthalten aber keine persönlichen Bewerberdaten für diesen Workflow. Manuelle Kanalmetriken und Anbieterberichte bleiben von Quittungen getrennt. Aufwand ist manuell erfasst; die Vergleichsdifferenz gilt nur für begründete Einträge und zieht Begleitung ab. Das ist kein kausaler MH-Wirkungsnachweis. Lernpunkte sind zusammengefasste stellenbezogene Beobachtungen ohne individuelle Bewerberdaten.

## HTML-Dashboard

`output/use-case-dashboard/index.html` enthält den letzten geprüften Stand eingebettet und funktioniert auch als Datei. `python3 output/use-case-dashboard/serve.py` startet nur auf `127.0.0.1:5190`, liefert ausschließlich Dashboard und Statusdaten und liest den Status alle fünf Sekunden neu. `docs/requirements/use_case_status.json` ist der auditierte Statuskatalog. Prüfsummen erkennen nachträgliche Änderungen verknüpfter Quellen und markieren die Prüfung als überholt; sie können keine fachliche Vollständigkeit selbst bestätigen. Neue Dateien müssen im Statuskatalog verknüpft und Statusänderungen nach Prüfung eingetragen werden. Browserbewertungen bleiben lokal und können als JSON exportiert werden; sie überschreiben keine Markdown-Bewertung oder Umsetzungsfreigabe. `output/use_case_status.before.json` bewahrt den Stand vor Umsetzung.

Produktiver Versand, externe KI-/Meta-Abnahme, vollständige Stripe-Testreise, öffentliches HTTPS und rechtliche/betriebliche Freigabe bleiben offen. UC-Z12 ist nicht implementiert.

## Finale Verifikation am 2. Oktober 2026

126 Tests bestanden: die sechs vorgeschriebenen Backend-Suiten plus Tracking, Social und Recruiting. Frontend-Build, SEO-/Header- und Sprachprüfung bestanden. Die zusätzliche Migration einer bestehenden Demo-Rollen-Datenbank ist geprüft. Sichtbare Browserprüfung mit ausschließlich fiktiven Kontakten: überfällige Erstreaktion, manuelle Rückmeldung, Terminvorschlag ohne Gesprächszählung und gesonderte Zustimmung mit einem vereinbarten, aber noch nicht geführten Gespräch. Nachweis: `../../output/screenshots/recruiting-results-local.jpg`. Keine echte Bewerbernachricht, Anbieteranfrage, Zahlung oder Veröffentlichung ausgeführt.

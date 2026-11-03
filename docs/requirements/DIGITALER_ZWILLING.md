# Digitaler Zwilling und Lösch-Batches

Stand: 02.10.2026. Der Nutzer hat das HTML-Interface und die Übergabe an einen **Projekt-Agenten mit Zugriff auf MH** beauftragt. Ein konkreter Lösch-Batch wurde damit noch nicht ausgewählt oder gestartet.

## Katalog und Architektur

Der Zwilling umfasst alle 31 Originalfälle aus `USE_CASES.md` und `USE_CASES_ZIELBILD_REVIEW.md`. Ergänzend werden 20 vorhandene Funktionsfälle als UC-I01–UC-I20 und fünf dokumentierte offene Betriebsaufgaben als UC-P01–UC-P05 geführt. Diese Ergänzungen sind eine nachträgliche Funktionssicht, keine ursprünglichen Nutzerbewertungen oder pauschale Umsetzungsfreigabe. Der vollständige Katalog mit Beschreibung, Lücken, Herkunft und Nachweisen steht in `use_case_status.json`.

Die Architektur steht oben: React/Vite-Oberflächen, zentrale FastAPI-API, Identität, Abo/Tokens, KI, Recruiting, Tracking, Social, E-Mail, SQLite, Qualität und Dashboard. Module filtern die zugeordneten Use Cases. Das API-Inventar wird ohne Import der Anwendung aus Python-Quelldateien gelesen; Tabellen aus CREATE-TABLE-Definitionen, nicht aus privaten Datenbanken. Die 23 NFA bleiben separate Querschnittsanforderungen und werden nicht als 23 weitere Use Cases gezählt. Gemeinsame Nachweisdateien zeigen Untersuchungsbedarf, keinen bewiesenen Aufrufgraphen.

## Bedienung

1. `python3 output/use-case-dashboard/serve.py` starten und http://127.0.0.1:5190 öffnen. `index.html` funktioniert auch allein als portabler Snapshot; direkte Agentenstarts benötigen den lokalen Server.
2. Pro Fall **Lösch-Prompt** lesen oder **Zum Lösch-Batch** wählen. Filter verändern die bestehende Auswahl nicht. Mehrfachauswahl ist möglich; **Alle angezeigten** betrifft genau den aktuellen Filter.
3. Optional einen zusätzlichen Änderungswunsch formulieren. **Gesamten Lösch-Batch prüfen** erstellt die verbindliche Gesamtvorschau. Auswahl und Zusatzwunsch sind danach bei jeder Änderung erneut zu prüfen.
4. Den vollständigen Auftrag lesen, die Beauftragung markieren und **Projekt-Agent starten** klicken. Vorher erfolgt keine Codeänderung. Es gibt einen Auftrag pro Batch, keine Einzelaufträge pro Fall.
5. Ausführungszustand, unabhängige Prüfungen und geänderte Quelldateien im gleichen Interface ansehen. Abbrechen beendet den laufenden lokalen Prozess einschließlich seiner Prozessgruppe; bereits erfolgte Änderungen werden nicht automatisch zurückgesetzt.

Eine Alternative ist die Desktop-Übergabe `codex://new?path=…&prompt=…`. Laut offizieller Dokumentation öffnet sie den Projektchat mit vorbereitetem Text, sendet ihn jedoch nicht automatisch: https://learn.chatgpt.com/docs/reference/commands. Die direkte Ausführung verwendet `codex exec` mit gespeicherter lokaler Anmeldung: https://learn.chatgpt.com/docs/non-interactive-mode. Die installierte CLI meldete in dieser Sitzung **Logged in using ChatGPT**. Modell und Konto-Einstellungen werden aus der lokalen Codex-Konfiguration übernommen; ein laufender Auftrag kann das Codex-Kontingent verbrauchen. Ein echter Agenten-Löschlauf wurde zur Abnahme bewusst nicht gestartet. Anmeldung, Anbieterzugang und automatisch geprüfte Freigaben können einen späteren Auftrag verhindern; das Interface meldet diesen Fehler.

## Ausführung und Grenzen

- Der lokale Server bindet ausschließlich 127.0.0.1. Host-Prüfung, exakte Origin, CSRF-Token, JSON-Body-Limit, feste Befehlsargumente ohne Shell und ein einziger aktiver Auftrag schützen den Start. Es gibt keinen Endpunkt für beliebige Befehle, Dateilesen oder private Protokolle.
- Der Browser übermittelt bekannte IDs, Zusatzwunsch und Quellfingerprint. Der Server generiert den Prompt. Ein zweiter Start desselben Auftrags erzeugt keinen zweiten Prozess. Quelländerungen nach der Vorschau blockieren den Start.
- Vor der Ausführung wird ausschließlich der freigegebene **Quellcode-/Dokumentbestand** unter `output/use-case-dashboard/runs/<ID>/backup/` gesichert. Private Konfiguration, Datenbanken, E-Mail-Outboxes, Credentials und Auth-Schlüssel sind ausgeschlossen. Dies ist kein produktives Datenbankbackup und kein automatischer Restore.
- Codex läuft im Workspace-Schreibsandbox mit automatischer Freigabeprüfung, ohne Umgehung des Sandboxes. Produktanbieter-Schlüssel werden nicht in die Prozessumgebung übernommen. Bestehende Daten, Zahlungen, Posts, Mails und Deployment sind ausdrücklich außerhalb des Löschauftrags. Der Prompt untersagt das Lesen privater Dateien und fordert die Erhaltung nicht ausgewählter Funktionen. Dies ist keine technische Garantie fachlicher Fehlerfreiheit des Agenten.
- Der Server prüft nach dem Agentenlauf unabhängig zwölf Backend-Suiten, Frontend-Build, SEO und Sprache. Ein erfolgreicher Prozess allein reicht nicht: alle Checks müssen bestehen und alle gewählten IDs müssen im Katalog als `removed` dokumentiert sein. Das bleibt eine lokale technische Prüfung; die fachliche Änderung ist anhand der gesicherten Quellen und geänderten Dateien zu prüfen.
- Laufdateien sind lokal und werden nicht über HTTP ausgeliefert. Browserstatus enthält ausgewählte IDs, Prompt, neutrale Ausführungszustände, Checks und Dateinamen; keine rohen Agenten-/Testprotokolle. Ein Serverneustart verwirft die Laufverwaltung im Speicher. Vorher laufende Agenten sind separat zu prüfen; Start eines zweiten Servers ersetzt keine laufende Ausführung.
- Automatische Aktualisierung liest alle fünf Sekunden den Katalog und den Quellenbestand. Geänderte, entfernte und neue Quellen markieren den bisherigen Abgleich als veraltet. **Das aktualisiert nicht automatisch die fachliche Umsetzungseinstufung.** Nach einer bewerteten Änderung Katalog/Prüfnachweise aktualisieren und `python3 output/use-case-dashboard/build.py` ausführen.

## Verifikation

Abnahme am 02.10.2026: 126 Produkt-Backend-Tests, 14 Dashboard-Tests, Frontend-Build, SEO und Sprache bestanden. Browserprüfung bestätigte Architekturfilter, zwei gesammelte Prompts, Gesamtvorschau und Startfreigabe. Der echte Start blieb unbetätigt; Testauswahl geleert.

`python3 -m unittest discover -s output/use-case-dashboard -p test_dashboard.py` prüft Katalogvollständigkeit, Datenabgrenzung, neue/geänderte Quellen, Prompt-Batching, Startschutz, Doppelstarts, unabhängige Checks, Quellsicherung und HTTP-Abgrenzung. Die Agentenausführung wird dabei durch einen lokalen Testdouble ersetzt. Die reguläre Produkt-Vollprüfung bleibt zusätzlich erforderlich; `npm run test:job-seo` prüft zusätzlich dynamische HTML-Auslieferung, Metadaten, Schema, Sitemap und Indexierungssperren mit fiktiven APIs.

Seit 07.10.2026 führt der Zwilling zusätzlich `npm run test:onboarding` als sechste Prüfgruppe aus: 38 Tests der echten Komponenten/Handler mit isolierten API-/Timer-/Navigationsdoubles; Sicherheits-/Zahlungsgates, Profileingaben, Zwischenspeichern/Fortsetzen, Erstellungs-Idempotenz und expliziter Abschluss. QR-Prüfungen umfassen die Website und das Benutzerkonto in der codierten Anbieter-/Kontokennung und der DE-/EN-Ansicht. Dies ersetzt keine echte Anbieter-Ende-zu-Ende-Abnahme.

Die Authenticator-Ergänzung prüft außerdem tatsächliches QR-Decoding, passende Konto-/TOTP-Parameter, manuelle Ausweichmöglichkeit, Fehlversuch und Entfernen des QR-/Schlüsselzustands nach Bestätigung.

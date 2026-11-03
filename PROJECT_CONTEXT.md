## Plattformvorschauen im Content Studio (08.10.2026)

Nutzer verlangt Instagram-/Meta-Look-and-feel in Preview; nachträglich ausdrücklich äußere `social-preview sp-*` Section beibehalten, transparent und ohne Rand. Neue gemeinsame SocialPreview-Komponente: Instagram-Feed mit Firmenkopf, Bild, dekorativen Aktionssymbolen und Caption; Meta als Facebook-Anzeigenkarte mit Haupttext vor Bild, Überschrift/Beschreibung und rein optischem Bewerbungsbereich. Story 9:16 mit Fortschrittsleiste, Firmenkopf und rein optischen Overlays, vollständigem Haupttext darunter. Keine erfundenen Likes/Reichweiten, Verifizierungszeichen, externen Kontohandles oder öffentlichen Domains. Äußere Section hat transparenten Hintergrund, border:0 und keinen Schatten; Beitragskarte selbst bildet die Plattform ab.

Feed/Story-Wahl bleibt mit bestehender Bildformatwahl synchron. Ausgewähltes Kampagnenbild und ungespeicherter Ausschnitt/Text werden direkt übernommen. Explizite A/B-Überschriften erhalten lokale Variantenwahl; Meta erkennt deutsche/englische Primary-Text-/Headline-/Description-Felder einschließlich mehrzeiliger Inhalte. Unbekanntes oder uneindeutiges Format bleibt vollständig als Text erhalten. Kurze Texte ungekürzt, lange/mehrzeilige Texte aufklappbar. Preview-Auswahl ändert keine gespeicherten Inhalte, Kampagnenstatus oder Tokens. Speichern/Billing/Freigaberegeln unverändert. Alte neutrale Preview-Stile entfernt, alle neuen Bedienelemente DE/EN.

Echte Browserprüfung mit vorhandener Nutzerkampagne/Bild: Variantenwechsel, Feed-Karten beider Plattformen, Story; transparente/rahmenlose äußere Section per DOM-Stil bestätigt. Nachweise output/content-studio-instagram-preview.png, output/content-studio-meta-preview.png und output/content-studio-story-preview.png. Keine API-Mutation, kein Verbrauch oder externe Veröffentlichung. Separater Prüftab geschlossen; Nutzertab beim Prüfen zuletzt Overview, dessen laufende Arbeit nicht überschrieben. Normale lokale Dienste unverändert. Visuelle Annäherung, kein offizieller Anbieter-Render oder Pixelgleichheitsversprechen; direkte Meta-Dokumentation hinter Login nicht öffentlich abrufbar.

Verifikation: 14 Digital-Dashboard-Tests, 106 vorgeschriebene Backend-Tests, 51 Komponenten-/Handler-Tests (fünf neue Vorschauprüfungen), finaler Build, SEO und vollständiges DE/EN bestanden. Neue Tests decken verlustfreie Varianten-/Meta-Feldverarbeitung, lokale Vorschauwechsel ohne ausgehende Aktionen, aktuelle ungespeicherte Texte/Bildausschnitte sowie Aufklappen kurzer mehrzeiliger Captions ab.

## Grüner Content-Studio-Hinweis vom Dashboard entfernt (08.10.2026)

Nutzer hinterfragt den verbleibenden Hinweis ohne Aktion. Gesamten grünen Bereich mit „MH Content Studio“, „Turn one briefing into campaign content.“ und Unterzeile aus Overview entfernt. Ausschließlich zugehörige Banner-/Kicker-/Orb-Stile und beide ungenutzten DE/EN-Übersetzungsschlüssel bereinigt; Content Studio und Kampagnenerstellung bleiben erhalten. Echte Dashboardansicht nach Hot-Reload geprüft; output/dashboard-without-banner.png. Vorher geöffnete Nutzerkampagne vollständig gespeichert, keine Änderungen verworfen; Nutzer-Tab auf Overview, bestehender Draft und 1.450 Tokens unverändert. Keine API-Mutation oder normaler Dienstneustart.

Verifikation: 106 vorgeschriebene Backend-, 46 bestehende Komponenten-/Handler- und 14 Dashboard-Tests sowie finaler Build, SEO und vollständiges DE/EN bestanden. Keine neuen Tests für die reversible Hinweisentfernung.

## Dashboard-Button „Create with MH“ entfernt (08.10.2026)

Nutzer erlaubt entweder Entfernen des Buttons im grünen Content-Studio-Hinweis oder direkten Einstieg in eine leere Kampagne. Gewählt: Button entfernen. Bestehender Briefing-Assistent/Erstellung bleibt an anderen Einstiegen erhalten; kein neuer leerer Datensatz, keine Änderung der Titelvalidierung. Nicht mehr benötigtes WandSparkles-Import und allein dafür genutzter DE/EN-Schlüssel entfernt. Echte Dashboardansicht ohne Button per Hot-Reload geprüft; Screenshot output/dashboard-without-create-button.png. Bestehender Draft und 1.450 Tokens unverändert; keine Kontoaktion oder Serverneustart.

Verifikation: 106 vorgeschriebene Backend-, 46 bestehende Komponenten-/Handler- und 14 Dashboard-Tests sowie Build, SEO und vollständiges DE/EN bestanden. Keine neuen Tests für das reversible Entfernen eines Buttons.

## Dashboard: Nächste Schritte statt Team Feed (08.10.2026)

Der Nutzer hat den vorgeschlagenen Ersatz des Team Feed durch eine kompakte Aufgabenkarte freigegeben. „Nächste Schritte“ leitet aus zugänglichen Kampagnen und Bearbeitungs-/Freigaberechten genau einen aktuellen Schritt pro Kampagne ab: offene Rückmeldungen, ausstehende Freigaben, vorhandene Entwürfe, leere Briefings. Aktueller Review-Status hat Vorrang vor alter Rückmeldung; Live erzeugt keine Aufgabe. Innerhalb gleicher Priorität stehen ältere Änderungen zuerst. Klick öffnet die zugehörige Kampagne im Content Studio zum Prüfen/Bearbeiten; er ändert keinen Status und verbraucht keine Tokens. Drei Aufgaben sichtbar, weitere aufklappbar. Ohne passende offene Aufgaben erscheint „Alles erledigt“. DE/EN folgen unverändert der Browsersprache.

Der ursprüngliche Aktivitätsverlauf mit den letzten fünf Einträgen bleibt direkt darunter standardmäßig geschlossen. Guthaben bleibt in der Sidebar. Echte Browserprüfung mit gespeichertem Draft: Aufgabenlink öffnet dessen Content Studio; Rückkehr zur Übersicht, Verlauf auf-/zugeklappt, 1.450 Tokens unverändert. Nachweis: output/dashboard-next-steps.png; Nutzer-Tab bleibt auf Overview. Keine API-Mutation, Zahlung, Erstellung oder externe Veröffentlichung ausgelöst; normale Dienste laufen weiter.

Verifikation: sechs vorgeschriebene Backend-Suiten (106 Tests), 46 Komponenten-/Handler-Tests einschließlich vier neuer Aufgabenprüfungen, Build, SEO und vollständiges DE/EN bestanden. Neue Prüfungen decken Priorität/Status, Rollen/Leerzustand, konkrete App-Navigation ohne Mutation und zugängliche weitere Aufgaben ab. Digitaler Zwilling aktualisiert; dessen 14 Tests bestanden.

## Guthaben in die linke Seitenleiste verschoben (08.10.2026)

Auf Nutzerwunsch liegt die kompakte Wallet-Karte jetzt in der linken Navigation unter Settings und über dem Benutzerkonto. Der bisherige Guthabenstreifen oberhalb des Hauptbereichs entfällt. Die Karte bleibt für verwaltete Firmenkonten auf allen Workspace-Seiten sichtbar, auch im Content Studio. Guthaben/Testkennzeichnung, bisher erlaubtes Aufladen und native aufklappbare Details bleiben erhalten; Buchungen sind nun unabhängig vom gewählten Bereich in denselben Details verfügbar. Inaktiv-Hinweis bleibt direkt sichtbar, Rollen-/Security-/Billinggates unverändert. Sidebar bei geöffneten Details oder kleinen Fensterhöhen scrollbar; Navigation/Konto können nicht durch Flex-Schrumpfen abgeschnitten werden. Bestehender schmaler Layoutwechsel bleibt erhalten.

Echte Browserprüfung: Dashboard mit 1.450 Tokens in Sidebar, Details zeigen ursprüngliche +1.500/−50-Buchungen, Studio zeigt weiterhin Sidebar-Guthaben, anschließend Overview mit geschlossenen Details. Keine Zahlung oder Tokenverwendung ausgelöst. Nachweis output/dashboard-sidebar-balance.png; Nutzer-Tab bleibt Dashboard. Normale Dienste unverändert. Vorgeschriebene sechs Backend-Suiten (106 Tests), bestehende 42 Komponenten-/Handler-Tests, Build, SEO und vollständiges DE/EN bestanden. Keine neuen Tests für die reversible Platzierungsänderung.

## Guthabenanzeige im Dashboard verkleinert (08.10.2026)

Auf Nutzerwunsch ersetzt die gemeinsame Wallet-Anzeige die große „YOUR COMPANY BALANCE“-Karte durch eine schmale Leiste: 16-px-Zahl, 13-px-Beschriftung, dezentes Testumgebungs-Badge und kleiner Aufladen-Textknopf. Die große Überschrift entfällt. Monatliche/gekaufte Aufteilung, Paketpreis, Testhinweis und bisherige Buchungen stehen im nativen, standardmäßig geschlossenen „Details & Verbrauch“ / „Details & usage“. Inaktive-Abo-Hinweise bleiben direkt sichtbar; Rollen-/Aufladenrechte, Guthaben, APIs und Buchungsregeln unverändert. Gemeinsame kompakte Darstellung auf bisherigen Wallet-Seiten; im Studio bleibt wie zuvor nur die dortige Kostenangabe. DE/EN, Live-Ansage des Guthabens und sichtbarer Tastaturfokus der Details bleiben erhalten.

Echte Dashboard-Prüfung: 1.450 Tokens, Aufladen erreichbar, Aufklappen zeigt Aufteilung und ursprüngliche +1.500/−50-Buchungen, wieder geschlossen. Kein Kauf, Verbrauch oder Kontowechsel ausgelöst. Nachweis: output/dashboard-compact-balance.png; Nutzer-Tab bleibt auf Overview. Frontend-Hot-Reload aktiv, normale Dienste unverändert.

Verifikation: vorgeschriebene sechs Backend-Suiten (106 Tests), bestehende 42 Komponenten-/Handler-Tests, Build, SEO und vollständiges DE/EN bestanden. Keine neuen Tests für diese reversible Darstellungsänderung. Digitaler Projektstand aktualisiert.

## Gespeichertes Briefing → Dashboard und lokale Testpakete (08.10.2026)

Nutzer möchte nach „Save brief & continue later“ das Dashboard erreichen und seine bestätigten Team-Testtokens ausprobieren. Tatsächlicher Browser zeigte bereits gespeichertes Briefing mit fehlgeschlagener OpenAI-Erstellung (kein Schlüssel); Wallet weiterhin 1.500 Tokens. Neuer Button DE/EN „Briefing speichern & zum Dashboard“ / „Save brief & go to dashboard“ speichert das bestehende Briefing und danach die firmengebundene Onboarding-Verschiebung. Additive `organizations.onboarding_deferred`, `POST /onboarding/defer` mit eigener campaign_id, `GET /onboarding.deferred` und App-Einstieg berücksichtigen den Aufschub dauerhaft. Abgesichertes Konto, Firmen-Admin ohne Demoansicht, aktives bezahltes Abo, Profil und eigenes gespeichertes Briefing bleiben Pflicht. Keine Tokenbuchung, keine falsche Review-/Onboarding-Abschlussmarkierung. Fehler navigieren nicht; Wiederholung verwendet gespeicherte Kampagne. Vollständiger Abschluss verlangt unverändert Review/Live mit Texten. `/onboarding` bleibt zum Fortsetzen erreichbar.

Optionales `POST /campaigns/{id}/generate?test_package=true` verwendet lokale Vorlagen mit denselben atomaren 50-Token-/Idempotenzregeln. Server verlangt verwaltetes Testkonto, sk_test-Konfiguration, lokale MH_PUBLIC_URL und Umgebung außerhalb production, zusätzlich weiterhin aktives bezahltes Abo, Guthaben, Firmen-/Stellen-/Statusgrenzen. Ohne KI-Schlüssel liefert Wallet generation_mode=local_test; Wizard/Studio/Dashboard nennen den lokalen Test ausdrücklich und senden die Option. Normaler Managed-Aufruf bleibt OpenAI; mit Schlüssel wird der echte KI-Weg angeboten. Kein stiller Providerersatz in Live/Produktion. Keine externe Datenübermittlung oder künstliche ai_usage-Zeile für Templates. Additive projects.generation_mode, History und Export-README erhalten die Kennzeichnung. Onboarding-Wallet aktualisiert im offenen Wizard sichtbar/fokusgesteuert ohne Überschreiben des Briefings.

Echter vorhandener Nutzer-Entwurf im Browser: Speicherknopf → Dashboard mit derselben Kampagne und 1.500 Tokens. Lokale Testerstellung im Content Studio nach ausdrücklicher 50-Testtoken-Bestätigung → gespeicherte Instagram-/Meta-Texte plus MH-Beschreibung, Draft, keine Freigabe/Veröffentlichung, 1.450 Tokens. Neuladen von /app bleibt beim Dashboard; Studio zeigt gespeicherte Inhalte und Testkennzeichnung. Nachweise: output/onboarding-saved-dashboard.png, output/onboarding-dashboard-test-tokens.png, output/local-test-campaign-package.png. Bestehende Firmen-/Briefingangaben unverändert; keine neue Kampagne, Zahlung, Mail oder künstliche Tokenzuteilung. Nutzer-Tab bleibt beim gespeicherten Paket im Studio. Normaler Frontend-/Backenddienst und Stripe-Listener laufen weiter; Backend für Änderungen neu gestartet. Kein tatsächlicher OpenAI-Aufruf verifiziert.

Verifikation: Vollprüfung 177 Backend-Tests in zwölf Suiten, 42 Komponenten-/Handler-Tests, Build, SEO, Job-SEO und vollständiges DE/EN bestanden. Vier neue Backend-Prüfungen: Aufschub/Session/MFA/Firmengrenzen/Profil-/Abo-/Rollengates; Testpaket/Export/keine KI-Nutzung/einmaliger Verbrauch/Rollback sowie Ausschluss Produktion/live/fremder Origin. Vier neue Komponentenchecks und erweiterter Speichercheck: fehlerhafte Speicherung/Verschiebung ohne Navigation, persistierter Dashboard-Einstieg, expliziter Testaufruf und beide Bestätigungen/DE/EN. Nach letzter Ergänzung des GET-Onboarding-Modus zusätzlich die verpflichtenden sechs Backend-Suiten erneut bestanden (106 Tests); 14 Digital-Dashboard-Tests bestanden. Weitergehende Provider-/Registrierungs-/Produktionsabnahme bleibt offen.

## Stripe-Rückkehr und bestätigter Team-Testkauf (08.10.2026)

Der Nutzer blieb nach tatsächlich bezahltem Team-Testcheckout bei „Choose Plan“. Echte Browserprüfung: abgesichertes Konto, `/onboarding` ohne Rückkehrparameter, nur Tarifauswahl/Statusknopf. Direkter lesender Stripe-Abgleich des passenden vorhandenen Checkouts: complete/paid/livemode=false. Der lokale Stripe-Listener lief nicht; MH hatte die zugehörigen Bestätigungen nicht erhalten. Vorhandenen Testlistener wieder gestartet, privates Signing-Secret geladen, Backend neu gestartet. Über offizielle Stripe-CLI ausschließlich die ursprünglichen genau zu diesem Checkout und seiner Rechnung gehörenden `checkout.session.completed`/`invoice.paid`-Ereignisse erneut zugestellt; beide Stripe-signiert mit HTTP 200 verarbeitet. Kein neuer Kauf, keine zweite Zahlung, kein synthetisches Event oder direkter Entitlement-Write. Tatsächliches Konto: Team/active/test, 1.500 Tokens, genau eine Rechnungsgutschrift. Nutzerbrowser wechselt zum Firmenprofil; Angaben dort nicht ausgefüllt/geändert. Nachweis: `output/onboarding-payment-confirmed.png` (echte Seite, leere Profilfelder). Regulärer Rechnungs-Versandauftrag entsteht nach bestehender Checkout-Zustimmung; vollständige Mailzustellung nicht neu geprüft.

Neue Checkout-Option `onboarding` wählt feste Success-/Cancel-Rückkehr `/onboarding?billing=...`; alte `/app?billing=success|cancelled` behalten ausschließlich diese zwei Werte im Onboarding-Redirect. `/billing/status` liefert firmengebundenen offenen Checkout samt Ablauf/geprüfter Stripe-URL. Billing zeigt bestehenden Tarif/Warteschritt statt erneutem Kauf, Wiederaufnahme/verantwortetem Verwerfen und klare Hinweise für bezahlte/abgelaufene/unbestätigte Buchung. Automatisches Prüfen endet nicht nach einer Minute; nur sichtbar und ohne parallele Abrufe, zusätzlich Fokus/Visibility. Bestätigter aktiver Serverstatus ruft direkt das Onboarding-Laden auf; ein geprüfter Weiter-Knopf hilft bei verzögerter Ansicht. Fehlgeschlagene Checkout-Erstellung bleibt wiederholbar. DE/EN, keine Browser-Freischaltung und unveränderte signierte Webhook-/Rechnungs-/Deduplizierungsregeln.

`./start.sh` startet mit privater Stripe-Testkonfiguration künftig den vorhandenen Listener vor den Servern. `stripe_test.listen --ready-file` meldet erst nach privatem Signing-Secret-Speichern Bereitschaft; Start lädt danach die Konfiguration neu. Keine Geheimnisse ausgegeben. Fehlende CLI/Bereitschaft oder späterer Listener-Abbruch beendet den gemeinsamen lokalen Lauf mit Meldung, Ctrl+C beendet alle drei Prozesse. Listener-Readiness/Redaktion mit isoliertem Prozessdouble und Shellsyntax geprüft; kein vollständiger Neustart des gemeinsamen Skripts im Nutzerbetrieb, um offene Profilangaben zu erhalten. Aktuell laufen Backend 8011, Frontend 5181 und separater echter Testlistener weiter.

Verifikation: 173 Backend-Tests (vier neue), 38 Komponenten-/Handler-Tests (vier neue), 14 Dashboard-Tests, Build, SEO, Job-SEO und vollständiges DE/EN bestanden. Tests prüfen feste Rückkehr, fremde Checkout-Abschirmung, keine Freischaltung allein durch bezahltes Providerobjekt, abgelaufene/fremde URLs, Readiness vor Secret-Laden, wartende/fehlgeschlagene Statusabfragen, Wiederaufnahme, manuellen Weiterweg und alte Redirects. Dieser konkrete Stripe-Testzahlungserfolg ist nun real bestätigt; Ablehnung/3D Secure/Radar/Verlängerung/Erstattung und vollständige Registrierung-/MFA-/Produktionsabnahme bleiben offen.

## Website und Benutzer im Authenticator-QR (08.10.2026)

Der Nutzer verlangt Website und Benutzer im QR/App-Eintrag. Die Anmelde-E-Mail bleibt der eindeutige Benutzername; der Anbieter enthält jetzt zusätzlich die serverseitig konfigurierte Website (`MH_PUBLIC_URL`, lokaler Standard `http://127.0.0.1:5181`). Lokal `MH · 127.0.0.1 (5181)`, später beispielsweise `MH · jobs.mh.example`. Label-Präfix und issuer-Parameter stimmen überein; der lokale Port steht in Klammern, damit der reservierte Doppelpunkt ausschließlich Anbieter und Konto trennt. Keine erfundene öffentliche Domain, keine Request-Host-Abhängigkeit, kein neues Geheimnis. SHA1/sechs Ziffern/30 Sekunden und alle MFA-/Recovery-Gates bleiben gleich. Wiederverbindung zeigt die aktuelle Kennzeichnung für denselben gespeicherten Schlüssel. Bereits importierte Authenticator-Einträge werden nicht automatisch umbenannt.

Backend liefert zusätzlich `website` in Setup/Reconnect. Frontend prüft Website-/Kontokennung vor QR-Erzeugung und zeigt volle Website-Adresse und Benutzerkonto ausdrücklich in DE/EN neben dem QR, inklusive manuellem Ausweichweg und Umbruch langer Angaben. Alte MH-Setup-Antworten ohne Website bleiben kompatibel. Ein zusätzlicher Backend-Test prüft konfigurierte Domain/lokalen Port/Konto, zwei zusätzliche Komponentenchecks prüfen unabhängiges Auslesen und Website-Mismatch sowie DE/EN. Separate isolierte Prüfung verbindet echte Backend-URI-Erzeugung mit echter Frontend-QR-Erzeugung und unabhängigem Decoder für vier Konfigurationen; sechs offizielle RFC-6238-Testwerte weiterhin korrekt. Ausschließlich öffentliche Testschlüssel/fiktive Konten, kein echter Nutzer-QR gelesen oder Konto geändert.

Verifikation: 169 Backend-Tests in zwölf Suiten, 34 Komponenten-/Handler-Tests, 14 Dashboard-Tests, Build, SEO, Job-SEO und DE/EN bestanden. Die erste Frontend-HTTP-Prüfung scheiterte an Sandbox-Portrechten; mit freigegebenen lokalen Testservern vollständig bestanden. Kein neuer Geräte-/Browser-E2E-Nachweis für diese Kennzeichnung. Beide normalen Dienste waren beendet; Backend mit vorhandener privater Konfiguration und Frontend auf 8011/5181 gestartet, Health und Auth-Seite liefern 200. Keine echte E-Mail, MFA-Einrichtung oder Veröffentlichung zum Test ausgelöst.

## Geprüfte Kontowiederherstellung bei Verlust von App und Codes (08.10.2026)

Der Nutzer hat die zuvor fehlende Wiederherstellung beauftragt. Neuer Einstieg in MFA-Abfrage und Passwort-Hilfe: „Authenticator und Wiederherstellungscodes verloren?“ → `/auth?action=recover`. Anfrage sendet einen einmaligen 60-Minuten-Link über den bestehenden Mailadapter. Ausdrückliche Postfachbestätigung, kein automatischer Linkverbrauch. Danach unabhängige menschliche Inhaberschaftsprüfung durch Platform Admin/vertrauenswürdigen Host-Operator; Postfach/Passwort allein reichen nicht. Keine echte Recovery-Mail oder Änderung eines Nutzerkontos zur Prüfung ausgelöst.

`backend/account_recovery.py` implementiert Request, Mailbox-Verify, Cancel, genehmigten Reset und Admin-Review. Additive `account_recoveries`-Tabelle, gehashte Links über auth_links, Konto-/E-Mail-/Passwort-/MFA-Fingerprint, Rate-Limits, CSRF, Status/Expiry/Replay-Prüfung und atomarer Verbrauch. Anonyme Anfragen können bestätigte/freigegebene Vorgänge nicht überschreiben; öffentliche Antwort bleibt auch bei SMTP-Ausfall generisch. System → Kontowiederherstellung (`AccountRecoveries.tsx`) zeigt bestätigte Anfragen. Freigabe verlangt exakte Konto-E-Mail, Vorgangsreferenz, unabhängige Prüfung und neuen eigenen TOTP des MFA-bestätigten Platform Admin. Selbstfreigabe/Firmenrollen/Demoansichten blockiert. Ablehnung ohne positive Prüfungsbestätigung möglich. Lokale bestehende Admins ohne MFA können sie im Review-Bereich einrichten.

Freigabe sendet einen 30-Minuten-Link und lässt Konto bis Verbrauch unverändert. Versandfehler bleibt wiederholbar; erneute bestätigte Freigabe ersetzt den alten Link. Kontoinhaber setzt selbst neues Passwort mit Bestätigung; alle Sessions/Einmal-Links sowie alte MFA-/Recovery-Codes werden ungültig. Kein automatischer Login. Neues `mfa_recovery_required` erzwingt bei jeder Rolle frischen QR und gültige Bestätigung; Flag wird erst dann entfernt. Zehn neue Recovery-Codes. Billing-/Firmen-/Abo-Daten unverändert. Anfrage insgesamt sieben Tage gültig. Zwei neue bilinguale E-Mail-Vorlagen in der Admin-Vorschau (nun sieben). Sechsstellige Eingabeboxen über gemeinsamen nebenwirkungsfreien Render-Helper für User/Admin.

Wenn alle Platform Admins ausgesperrt sind: `python3 -m backend.account_recovery list|approve|reject` auf autorisiertem Host. `approve/reject` benötigen case-id, Referenz, exakte E-Mail und explizites VERIFIED im Dialog; zuvor bestätigtes Postfach bleibt Pflicht. Hostzugriff ist diese Notfall-Vertrauensgrenze. CLI gibt keine Tokens/Geheimnisse aus, sendet nur Link und setzt keine Credentials direkt. Unabhängige Prüfung ist reale Betreiberaufgabe, keine automatisch behauptete Identitätsprüfung. Kein Ersatz der registrierten E-Mail bei verlorenem Postfach. AUTH_SETUP beschreibt Ablauf/zulässige Prüfungswege. Audit-Aufbewahrungsfrist/Supportorganisation vor öffentlichem Betrieb festlegen; Daten bleiben privat, Firmenlöschung entfernt zugehörige Anfragen.

Verifikation: 168 Backend-Tests (acht neue Recovery-Prüfungen), 32 Komponenten-/Handler-Tests (drei neue), 14 Dashboard-Tests, Build, SEO, Job-SEO und DE/EN bestanden. Echte Backend-/DB-Tests isoliert; Browserprüfung nur fiktive API mit Mailbox-/Adminfreigabe und mobilen Formularen. Keine echte Geräte-/Provider-E2E-Zusage. Nachweise: `output/account-recovery-request.jpg` (echte Seite/leeres Feld), `output/account-recovery-mailbox-review.jpg`, `output/account-recovery-admin-desktop.jpg`, `output/account-recovery-admin-mobile.jpg`, `output/account-recovery-reset-mobile.jpg` (fiktive Daten). Temporäre Dienste beendet/Viewport zurückgesetzt. Normales Backend mit vorhandener privater Konfiguration neu gestartet; sechs Routen, Health/Frontend und anonyme Admin-Sperre lesend geprüft. Beide Dienste laufen. Nutzerbrowser steht auf der neuen Recovery-Anfrage; eigenes Konto nicht zurückgesetzt.

## Sechs einzelne Authenticator-Ziffernfelder (08.10.2026)

Auf Nutzerwunsch ersetzt der gemeinsame SecurityPanel das große Feld durch sechs einzelne DE/EN-beschriftete Ziffernfelder: Einrichtung, normale MFA-Anmeldung und bestätigte QR-Wiederverbindung. Automatischer Fokus, Rücktaste/Pfeile/Home/End, vollständiges Einfügen und One-Time-Code-Autofill-Verarbeitung einschließlich führender Null. Unvollständige Codes sperren Bestätigung und werden zusätzlich im Submit-Handler blockiert. Kein automatischer Submit. Längere Recovery-Codes behalten ihre separate Texteingabe; Moduswechsel entfernt alte Werte/Fehler. MFA-Policy, Schlüssel und Backend unverändert.

Die Rückfrage zum permanenten QR wurde erklärt: QR enthält den MFA-Schlüssel. Während laufender Einrichtung bleibt er sichtbar bis zur Bestätigung; in einer lediglich per Passwort angemeldeten MFA-Abfrage wird er nicht freigegeben. Wiederöffnung benötigt weiterhin einen unbenutzten Recovery-Code. Der tatsächliche Nutzerbrowser zeigt nun die sechs leeren Felder, ohne Account-/Schlüssel-/Sitzungsänderung. Kein Recovery-Code vom Nutzer erhalten oder angefordert. Die früher offene Frage nach Verfügbarkeit bleibt ungeklärt.

Zwei zusätzliche Komponentenprüfungen testen Fokus/Korrektur/Unvollständigkeit sowie Paste/Autofill/führende Null ohne automatische Anmeldung. Browserprüfung mit fiktiver API: Tippen, Rücktaste, Paste, Recovery-Umschaltung, QR plus sechs Felder; 320-px-Ansicht ohne Überbreite. Nachweise: `output/authenticator-six-fields-desktop.jpg` (echte Seite, leere Felder), `output/authenticator-six-fields-mobile.jpg` und `output/authenticator-six-fields-qr-mobile.jpg` (fiktive Daten/öffentlicher Testschlüssel). Temporäre Vorschauprozesse beendet und Viewport zurückgesetzt. Normale Dienste bleiben unverändert.

Verifikation: 160 Backend-Tests, 29 Komponenten-/Handler-Tests, 14 Dashboard-Tests, Build, SEO, Job-SEO und DE/EN bestanden. Autofill-Verteilung im Komponentencheck geprüft; keine echte Geräte-/Provider-E2E-Abnahme. Frontend-Hot-Reload zeigt die Änderung bereits im Nutzerbrowser.

## QR zum Verbinden eines bestehenden Authenticators (07.10.2026)

Der Nutzer benötigt auch aus der normalen Code-Abfrage einen QR zum Verbinden seiner App. Der gemeinsame SecurityPanel bietet nun „Authenticator-App verbinden“ / „Connect authenticator app“. Bei bereits eingerichteter MFA verlangt dieser Weg zunächst einen unbenutzten MH-Wiederherstellungscode. Erst dann liefert POST /auth/mfa/reconnect den bestehenden, korrekt codierten MH-Setup-Schlüssel; Browser erzeugt den QR lokal. Anschließend verlangt die normale /auth/mfa/challenge einen Code aus der verbundenen App. Kein Passwort-/E-Mail-Bypass; ohne Recovery-Code bleibt eine separat geprüfte Kontowiederherstellung erforderlich. Nutzer wurde nur nach Vorhandensein eines Recovery-Codes gefragt, niemals nach dem Code selbst.

Der Endpoint verlangt vorhandene Session/CSRF, bestätigte E-Mail und gespeicherte MFA, sperrt Demoansichten, verbraucht Recovery atomar/kontogebunden und begrenzt Versuche auf fünf. Response bleibt no-store. Er richtet keinen neuen Schlüssel ein und schaltet die Sitzung nicht frei. Codebestätigung bleibt notwendig; Abbruch/Erfolg entfernen QR/Schlüssel aus Clientzustand. Zwei neue Backend-Tests prüfen fehlende/fremde/verwendete Codes, E-Mail/CSRF/Session/Rate-Limit und anschließende echte TOTP-Challenge. 27 Komponententests umfassen nun Reconnect, Fehler/Wiederholung, Doppelbetätigung und Abbruch; Sprachprüfung rendert den neuen Einstieg in DE/EN.

Browsernachweise mit ausschließlich fiktivem Konto/Test-Recovery-Code und öffentlichem Testschlüssel: `output/authenticator-reconnect-desktop.jpg`, `output/authenticator-reconnect-mobile.jpg`. Beide QRs unabhängig ausgelesen; Mobilansicht ohne horizontale Überbreite. Kein echtes Nutzerkonto/Authenticator verändert oder eingerichtet.

Verifikation: 160 Backend-Tests, 27 Komponententests, 14 Dashboard-Tests, Build, SEO, Job-SEO und DE/EN bestanden. Temporäre Vorschauprozesse beendet. Normales Backend auf 8011 mit bestehender privater Stripe-Testkonfiguration neu gestartet; Health/Route und anonymen Sessionstatus lesend geprüft. Neue Route ist lokal geladen. Frontend neu laden; Kundenschlüssel/Sitzungen/Daten nicht zurückgesetzt. Offene Rückfrage an Nutzer: Sind Wiederherstellungscodes noch vorhanden? Code nicht im Chat anfordern.

## Zwei-Faktor-Abfrage visuell vereinheitlicht (07.10.2026)

Der Nutzer hat ausdrücklich klargestellt: MFA behalten und die bisher übersehene Abfrage eines bereits eingerichteten Authenticators an die gemeinsame Gestaltung anpassen. `SecurityPanel` verwendet für E-Mail-Bestätigung, QR-Einrichtung, reguläre MFA-Abfrage und Recovery-Sicherung eine gemeinsame `auth-card`: grünes Icon, weiße/cremefarbene Karte, gleiche Typografie und Eingabefelder, dunkler grüner Hauptbutton sowie zurückhaltendes Abmelden. Die alten Challenge-Texte „SECURE YOUR ACCOUNT / Two-factor authentication / Enter the current code … or an unused recovery code.“ wurden ersetzt; DE „Anmeldung bestätigen“, EN „Confirm your sign-in“. Recovery ist eine explizite alternative Eingabe und wechselt zurück zur Authenticator-App; Moduswechsel leert Eingabe/alte Fehler. Normaler Code bleibt sechsstellig mit numerischer Tastatur/Autofill; Recovery erlaubt den vollständigen längeren Code.

Keine Backend-/MFA-Policy geändert, keine Schlüssel neu eingerichtet oder zurückgesetzt und kein Konto entsperrt. Drei nicht mehr verwendete Überschriften-/Textübersetzungen sowie das alte kombinierte Eingabelabel entfernt. 25 isolierte Komponententests umfassen nun gemeinsamen Aufbau aller Sicherheitszustände, DE/EN-Challenge und Recovery-Fehler/Wiederholung; Sprachprüfung rendert beide Eingabemodi. Desktop/mobile Browserprüfung ausschließlich mit fiktivem MFA-Testkonto: `output/authenticator-sign-in-desktop.jpg`, `output/authenticator-sign-in-mobile.jpg`.

Verifikation: 158 Backend-Tests, 25 Komponententests, 14 Dashboard-Tests, Build, SEO, Job-SEO und DE/EN bestanden. Mobile Recovery-Ansicht mit Texteingabe/100-Zeichen-Limit ebenfalls geprüft (`output/authenticator-recovery-mobile.jpg`); keine horizontale Überbreite. Temporäre Vorschauprozesse beendet, normale Server/Kundendaten unverändert. Nur Frontend neu laden; Backend unverändert.

## Einheitliche Authenticator-Einstiege (07.10.2026)

Auf Nutzerwunsch alle Einstiege geprüft, besonders `/app?billing=start`. Onboarding und Workspace verwenden bereits denselben `SecurityPanel` mit QR-Code und manueller Alternative. Anonyme Nutzer sehen zuerst die Anmeldung; nach Anmeldung und bestätigter E-Mail ist die QR-Einrichtung erreichbar. Bereits eingerichtete MFA verlangt ihren aktuellen Code/Recovery-Code, keinen neuen Einrichtungsschlüssel.

Die App zeigt fehlgeschlagene Statusprüfungen jetzt auch innerhalb der Kontosicherung und entfernt alte Fehler beim Wiederholen. Direkte Social-/Settings-Einstiege laden Team/Integration erst nach Kontosicherung. Der cremefarbene Seitenhintergrund wird auch am äußeren Seitenrand im Workspace-Einstieg angewandt. Fünf zusätzliche isolierte Komponententests prüfen normalen Einstieg, Billing-Start/-Success, Social-Einstieg sowie Anmeldung/Statusfehler/Wiederholung. Insgesamt 23 Onboarding-/Authenticator-Prüfungen. Desktop/mobile Browserprüfung des Billing-Einstiegs nutzt ausschließlich fiktives Konto und öffentlich bekannten Testschlüssel, beide Screenshots unabhängig decodiert: `output/authenticator-qr-billing.jpg`, `output/authenticator-qr-billing-mobile.jpg`. Keine reale Anmeldung, MFA-Einrichtung oder Zahlung vorgenommen.

Verifikation: alle 158 Backend-Tests, 23 Komponententests, 14 Dashboard-Tests sowie Build, SEO, Job-SEO und DE-/EN-Prüfung bestanden. Temporäre Vorschauprozesse beendet; normale lokale Server und Kundendaten unverändert. Frontend neu laden für die Korrekturen; keine weitere Backendänderung in diesem Schritt.

## Authenticator-Einrichtung per QR-Code (07.10.2026)

Der Nutzer hat einen QR-Code für die Authenticator-App verlangt; die bedingte Entfernung des Authenticator-Schritts ist nicht erforderlich, da er jetzt implementiert ist. Die bestehende E-Mail-/MFA-Sicherung bleibt erhalten. `frontend/src/authenticatorQr.ts` erzeugt mit der gebündelten QR-Bibliothek ein schwarz-weißes PNG-Datenbild vollständig im Browser. Kein externer QR-/Bilddienst, keine Otpauth-Navigationslinks und keine Browser-Storage-Ablage. Konto/Schlüssel/Issuer/Algorithmus/Ziffern/Periode werden vor Darstellung abgeglichen. Lokaler Ausweichweg ohne Kamera bleibt aufklappbar und öffnet sich bei QR-Fehler; sechsstelliger Bestätigungscode und Recovery-Sicherung bleiben erforderlich.

`backend/auth.py` codiert den MH-Kontonamen korrekt in der Setup-URI und liefert SHA1/sechs Stellen/30 Sekunden explizit. Setup bleibt durch Session/CSRF/E-Mail-Bestätigung/Rate-Limit geschützt, der ausstehende Schlüssel verschlüsselt und erst nach gültigem Code aktiv. Keine neue Route. Die Oberfläche verhindert schnelle doppelte Setup-Aktionen, hält die Einrichtung bei falschem Code und entfernt QR-/Schlüsselzustand nach Bestätigung. Bestehende Setup-URIs ohne explizite Parameter bleiben mit den gleichen Standards kompatibel. Backend neu starten und Frontend neu laden für die URI-Ergänzung.

Die Onboarding-Prüfung umfasst nun **18 Komponententests**, davon fünf neue QR-/MFA-Tests. Ein unabhängiger Decoder liest das tatsächlich erzeugte PNG und vergleicht die vollständige URI; Tests prüfen Fremdkonto/abweichende Parameter, Fallback, Fehler/Bestätigung, Recovery-Anzeige und normale MFA-Challenge. Ein zusätzlicher Backend-Test prüft Label-Codierung, denselben verschlüsselten Schlüssel und Bestätigung. Browserprüfung bei Desktop/390 px zeigt den QR; ein weiterer Decoder liest beide Screenshots korrekt. Alles ausschließlich fiktives Testkonto mit öffentlich bekanntem Testschlüssel, kein echtes Nutzerkonto/Authenticator eingerichtet. Nachweise: `output/authenticator-qr-preview.jpg`, `output/authenticator-qr-mobile.jpg`. Die temporären Vorschauprozesse sind beendet; normale Server/Kundendaten unverändert.

Neue Abhängigkeiten: qrcode 1.5.4 und Typen; jsqr 1.4.0 nur für Tests. npm meldete eine vorhandene source-map-js-Schwachstelle; kompatibles Update auf 1.2.2 behebt sie, anschließender Installationsaudit 0 gemeldete Schwachstellen. Kein vollständiges Sicherheitsaudit. Primäres URI-Format: https://github.com/google/google-authenticator/wiki/Key-Uri-Format.

Verifikation: **158 Backend-Tests**, **18 Onboarding-/Authenticator-Komponententests**, **14 Dashboard-Tests**, Frontend-Build, SEO, Job-SEO und DE-/EN-Prüfung bestanden. Desktop-/Mobil-QRs unabhängig ausgelesen und mit der fiktiven Setup-URI abgeglichen.

## Vereinfachtes Onboarding und automatisierte Ablaufprüfung (07.10.2026)

Der Nutzer hat eine Vereinfachung bei weitgehend erhaltener visueller Gestaltung sowie zusätzliche automatisierte Tests beauftragt. Die vier fachlichen Schritte bleiben erhalten: Konto absichern → bezahlten Tarif bestätigen → Firmenprofil → ersten Entwurf prüfen. Grün-/Creme-Gestaltung, klare Fortschrittskarten mit Icons/erledigten Schritten, große Aktionen und mobile Zweispalten-Fortschrittsanzeige ersetzen die uneinheitliche bisherige Darstellung. Sicherheitsgates, MFA, Webhook-Zahlungsfreigabe, Preise, Tokenverbrauch und ausdrückliche Erstellungs-/Faktenbestätigung bleiben unverändert.

`Billing onboarding` zeigt ausschließlich die nötige Tarifbuchung: drei Tarife, Monats-/Jahreswahl, Rechnungsland, explizite EU-/PDF-Zustimmungen, Nettopreis-/Steuerhinweise, Zahlungshinweise und Statusaktualisierung. Guthabenübersicht, Nachkäufe, Rechnungsverwaltung und Verlauf bleiben im normalen Workspace-Billing; sie sind im ersten Einstieg ausgeblendet. Checkout-Abbruch kann weiterhin verworfen werden. Buchung wartet jetzt auch auf den geladenen Kontostatus. Ladefehler haben einen direkten Wiederholen-Knopf; ein erfolgreicher Abruf entfernt alte Fehler.

Das Firmenprofil zeigt drei Pflichtangaben (Branche, Standort, kurze Beschreibung). Vorteile/Ton sind als optionale native Details erreichbar; vorbefüllte und zugeklappte Werte bleiben erhalten und werden ins Briefing übernommen. Aktualisierung überschreibt keine bearbeiteten Profileingaben; parallele/überholte Abrufe werden ignoriert. Aktionen sind gegen schnelle Doppelbetätigung gesperrt. Der erste Entwurf wird mit lesbaren Überschriften/Listen dargestellt; erneute Generierung nutzt die gespeicherte Kampagne und denselben Idempotenzschlüssel bei Fehlschlag. Kein automatisches Review/Abschließen. Überschriften erhalten beim Schrittwechsel den Tastaturfokus. Browser folgt weiterhin DE/EN; gespeicherte Kundentexte unverändert.

Neue `frontend/scripts/verify-onboarding.mjs` / `npm run test:onboarding`: **13 Komponententests** für Sicherheits-/Zahlungsgates, drei Pflichtantworten, optionale Werte, Fehler-/Doppeleingabe, Profilvorbelegung, Zwischenspeichern/Fortsetzen, Generierungs-Idempotenz, explizites Review/Abschluss, Laden/Wiederholen und reduzierte Tarifansicht samt Zustimmungen. Tatsächliche React-Komponenten/Handler laufen in einem deterministischen Hook-Testhost mit isolierten API-/Timer-/Navigationsdoubles; keine Browser- oder echte Anbieter-E2E-Zusage. Der digitale Zwilling führt den Test als sechste unabhängige Prüfgruppe mit aus.

Verifikation: **157 Backend-Tests**, **14 Dashboard-Tests**, **13 Onboarding-Komponententests**, Frontend-Build, SEO, Job-SEO und vollständige DE-/EN-Prüfung bestanden. Browserprüfung bei Desktop und 390 px mit fiktiver API bestätigt Profil, Zuklappen optionaler Eingaben, Vorbelegung, Speichern/Fortsetzen, fiktive Erstellung und ausdrücklichen Abschluss sowie die reine Tarifansicht. Screenshots: `output/onboarding-profile-desktop.jpg`, `output/onboarding-profile-mobile.jpg`, `output/onboarding-billing-desktop.jpg`. Keine reale Registrierung/MFA, Zahlung, E-Mail, KI-Anfrage oder Veröffentlichung ausgelöst; Kundendaten und normale lokale Server unverändert. Die temporären Vorschauprozesse wurden beendet. Frontend neu laden für die Änderung; Backend unverändert.

## Job-Board-SEO und Design für Handwerk/Pflege (05.10.2026)

Auf Nutzerwunsch ist das öffentliche Board auf Handwerk/Pflege ausgerichtet: klare MH-Grün-/Creme-Gestaltung, Suchfeld Beruf/Ort, echte GET-Filter/Pagination, Pflege-/Handwerk-Schnellsuche und Ausbildungsfilter, kompakte Arbeitgeber-/Stellenkarten. Andere Berufe bleiben auffindbar. Detailseiten zeigen Arbeitgeber, Ort, Beschäftigung, Arbeitsmodell und vorhandenen Gehaltstext zuerst; direkte und mobile Bewerbungsaktion ohne Konto/Pflicht-CV. Die feste Aktion wird bei sichtbarem Formular ausgeblendet. Optionaler Consent bleibt unter dem Bewerbungsbereich, ohne Tracking vor Zustimmung. Keine erfundenen Arbeitgeberversprechen, Bewertungen oder Fotos.

Der neue Node-Serverablauf liefert Board/Anzeigen als vollständiges HTML (React-Serverbundle `entry-jobs.tsx`) mit individueller Metabeschreibung, Canonical und Social-Vorschauen. Inhalte/Links sind ohne JavaScript lesbar, Absenden benötigt JavaScript; das Formular bleibt vor Initialisierung gesperrt und verwendet kein GET für Bewerberdaten. Client übernimmt öffentliche Anfangsdaten, lädt nicht erneut und erhält Serverinhalt bis zur Modulverfügbarkeit. Arbeitgeber-Landingpage lädt getrennt; feste Bildabmessungen, priorisiertes Detailbild und lazy Thumbnails. Echter HTTP-404 bei beendeten Anzeigen; 503/Retry-After bei API-Störung; keine veralteten gecachten Jobseiten. Bundle/Manifest werden nicht öffentlich ausgeliefert.

Indexierung setzt öffentlichen SITE_URL-Build, JOBS_INDEXABLE=1 und API test=false gemeinsam voraus; lokal bleibt noindex. Produktion braucht Node-SSR-Server plus HTTPS-/api-Reverse-Proxy und expliziten JOBS_API_ORIGIN. Vite-/Static-only-Betrieb bietet keine dynamische SEO-Auslieferung. Sitemap enthält aktuell offene Anzeigen; Filter bleiben noindex, Pagination hat Canonicals, Trackingparameter nicht. JobPosting nur auf geeigneten Einzelseiten: sichtbare Angaben, ursprüngliches published_at, optionale Frist, Beschäftigung, DE-Standort/Remote-Anforderung und directApply. Keine erfundenen numerischen Gehälter/Adressen/Logos. published_at wird bei erster expliziter Aktivierung gesetzt, nie durch Retry zurückgesetzt, nicht Teil des editierbaren Plans. Altfälle ohne verifiziertes Datum bekommen kein JobPosting bis erneuter expliziter Aktivierung. Kein öffentlicher Deployment-/Indexing-/Provideraufruf, keine Domain eingerichtet; Google Indexing API und Search Console bleiben offen. Kein gemessener Lighthouse-Höchstwert oder Rankingversprechen.

Verifikation: **157 Backend-Tests**, **14 Dashboard-Tests**, Frontend-Build, SEO, neue Job-SEO-Prüfung und vollständige DE-/EN-Prüfung bestanden. Browserprüfung mit fiktiven Teststellen bestätigt Pflege-Suche, Ausbildungsfilter, mobile Darstellung und erfolgreich gespeicherte Testbewerbung. Screenshots: `output/job-board-design-desktop.jpg`, `output/job-posting-design-mobile.jpg`. Testserver beendet; normale lokale Server unverändert. Backend neu starten und Browser neu laden für neue Schema-/API-Routen.

## Content Studio endet nach der MH-Stellenbeschreibung (05.10.2026)

Der Nutzer hat ausdrücklich alles **unter** „Job description on MH“ entfernen lassen. Diese aufklappbare Beschreibung mit Textbearbeitung/Speichern bleibt der letzte Studio-Abschnitt. Entfernt sind der anschließende Freigabe-/Exportblock, Jobportal-/Verbreitungsplanung samt lokalem Workflow, Bewerbungsseiten-/Trackinglinks, Meta-Publishing und Kommentare/Verlauf/Versionen. Zugehörige ungenutzte Studio-Imports, Props, Zustände, History-Abfragen, Download-/Kommentarhandler und CSS wurden entfernt. Keine Ersatzoberfläche angelegt; Portal-/Workflow-/Social-Backend, gespeicherte Konfigurationen, Bewerbungen und Historie bleiben erhalten. Frühere Angaben zu diesen Studio-Einstiegspunkten sind damit überholt. Analysen, Recruiting, Bilder, Instagram-/Meta-Texteditor und MH-Beschreibung bleiben erreichbar.

Verifikation: **156 Backend-Tests**, **14 Dashboard-Tests**, Frontend-Build, SEO und DE-/EN-Prüfung bestanden. Browserprüfung mit fiktiver Testfirma bestätigt beide Kanalansichten und die MH-Beschreibung als letzten Studio-Abschnitt; Screenshot: `output/content-studio-cleanup.jpg`. Keine Kundendaten oder externen Dienste verändert.

## Gemeinsamer lokaler Kampagnenablauf abgeschlossen (05.10.2026)

Der Nutzer hat nach dem Lückenabgleich **„Finish the workflow first“** beauftragt. Der bisherige Plan mit vorbereiteten Links wurde zu einem ausführbaren **lokalen Simulator-Ablauf** erweitert. Ein Firmen-Admin startet im Studio „MH aktivieren und lokalen Workflow starten“: MH wird aktiviert und Kanalaktionen für Instagram/Meta-Beiträge, Anzeigen und Retargeting werden ausgeführt. Die Oberfläche kennzeichnet alle Auslieferungsquittungen, Impressionen, Klicks und Kosten ausdrücklich als Simulation. **Echte Instagram-/Bild-/Ads-/Marketingadapter sind weiterhin nicht implementiert**; Domain und Meta-Konfiguration allein machen diesen Ablauf nicht live. Bestehendes explizites Facebook-Text-/Link-Publishing bleibt separat. Der Nutzer hat keine öffentliche Domain; keine echte Ausspielung/Ads-Buchung oder externe Besucherdatenübertragung wurde vorgenommen.

`backend/campaign_workflow.py` speichert unveränderliche freigegebene Texte, Feed-/Story-Bilddateien, Plan, Revisionen und Linkplatzierungen je Lauf. Ein expliziter aktueller Laufzeiger hält auch Wiederaufnahme älterer identischer Pakete korrekt. Wiederholter Start erhält Lauf-/Quittungs-IDs und Werbeende. Erfolgreiche Aktionen werden nicht erneut ausgeliefert; bekannte Ablehnungen haben höchstens drei Versuche, unklare Ergebnisse brauchen explizite Reconciliation. Instagram ohne Bild bleibt mit konkretem Hinweis blockiert; andere mögliche Aktionen und MH können weiterlaufen. SQLite-Transaktionen serialisieren den ausschließlich lokalen Simulator. Diese Implementierung enthält keine Netzwerkzustellung und keinen Live-Modus-Schalter; produktive Start/Retry/Simulationsendpunkte lehnen ab.

Das Kampagnenbudget umfasst beide Kanäle und Retargeting zusammen. Restbudget wird gleichmäßig auf geplante Anzeigenaktionen verteilt. Simulierte Kosten aller früheren Läufe bleiben abgezogen; Planänderung/erneuter Start verdoppeln kein Budget und verlängern keinen identischen Lauf. Ein Testschritt liefert höchstens 1 EUR, zehn Impressionen und einen Klick je berechtigter Anzeigenaktion. Quittungen sind idempotent, begrenzt und atomar; ungültige Quittungen rollen zurück. Budgetuntergrenzen respektieren bereits dokumentierte Testkosten. Reale Werbekosten und Kosten je Bewerbung bleiben unbekannt.

Die lokale Retargeting-Zielgruppe enthält nur nicht abgelaufene Marketing-Einwilligungen mit Lesesignal und ohne abgesendete Bewerbung. Erfolgreiche Bewerbung, Widerruf und Ablauf entfernen **diesen Besuch**, keine Erkennung über mehrere Besuche/Geräte. Kein Namen-/E-Mail-Export und keine echte Meta-Zielgruppe. Ohne berechtigte Besuche warten Retargeting-Aktionen. Zurückziehen/Abschluss/Ablauf, geänderte Inhalte/Pläne und inaktive kostenpflichtige Konten pausieren den Workflow. Werbedauer/Budget stoppt Anzeigen. Historische Testquittungen bleiben sichtbar; Wiederaufnahme erfordert bewusstes Starten.

Kanal-/Varianten-Kohorten ergänzen echte freiwillige Messung: Besuche, Lesesignale, Formularstart, abgesendete Bewerbungen und Bewerbungen nach Lesesignal. UI zeigt Besuch-zu-Bewerbung- und Lesesignal-zu-Bewerbung-Raten. Alte Tagesaggregate werden nicht nachträglich in Kanäle erfunden. Widerruf merkt die Browserauswahl jetzt **vor** jeder Netzwerkwartezeit; CSRF-geschützte Widerrufsanfrage nutzt Keepalive auch bei sofortigem Seitenwechsel. Kein Tracking vor freiwilliger Zustimmung.

Neue Dateien: `backend/campaign_workflow.py`, `backend/test_campaign_workflow.py`, `frontend/src/CampaignWorkflow.tsx`. Der digitale Zwilling bleibt bei 57 Fällen und prüft zwölf Backend-Suiten. Der Ablauf wird mit eigener fiktiver Testfirma/isolierter Datenbank und lokalem Mailmodus geprüft. Browser bestätigt Start mit vier Auslieferungsquittungen/zwei wartenden Retargeting-Aktionen, 2 EUR Testkosten aus demselben 150-EUR-Budget, Ad-Link → MH, Lesesignal → Zielgruppe 1, Bewerbung → Zielgruppe 0, kanalbezogene Conversion und Widerruf trotz sofortiger Navigation. Normale lokale Server wurden nicht gestoppt. Backend neu starten und Browser neu laden für neue Schema-/API-Routen.

Verifikation: **156 Backend-Tests**, **14 Dashboard-Tests**, Frontend-Build, SEO und vollständige DE-/EN-Prüfung bestanden. Browsernachweis: `output/campaign-workflow-preview.jpg` mit ausschließlich fiktiven Testdaten.

## Lokales Jobportal, Conversion und gemeinsames Werbebudget (05.10.2026)

Der Nutzer hat Deutschland als ersten Stellenmarkt, Bewerbungen direkt auf MH als Conversion, normale Instagram-/Facebook-Beiträge plus bezahlte Anzeigen und Retargeting bestätigt. Ein gemeinsames Budget gilt für beide Kanäle samt Retargeting. Es gibt **noch keine Domain**; der Nutzer hat ausdrücklich **zunächst lokale Umsetzung** gewählt. Der hinterlegte Vorschlag **150 EUR für 14 Tage** ist eine frei änderbare eigene Testannahme, kein Anbieter-Mindestpreis, keine Erfolgszusage und keine Ausgabenfreigabe. MH-Abo und Tokens bleiben separat.

`/jobs` und `/jobs/<id>` zeigen ausdrücklich aktivierte, intern freigegebene, offene und nicht abgelaufene DE-Stellen. Filter: Beruf/Suchwort, Ort, Firma, Beschäftigung und Arbeitsmodell; Pagination mit 24 Einträgen. Die gemeinsame MH-Beschreibung und ein optionales ausgewähltes Feed-Bild werden öffentlich; interne Briefings/Originalbilder bleiben privat. Bewerbung mit Name/E-Mail und optionaler Nachricht ohne Konto oder Pflicht-Lebenslauf. Alte `/apply`-Seiten bleiben kompatibel, benötigen für die neue Übersicht aber einen ausdrücklich gespeicherten DE-Portalplan. Abschluss, Zurückziehen und Fristablauf sperren Listing und neue Bewerbungen. Ablaufdatum gilt bis zum Tagesende Europe/Berlin.

`Jobportal & Verbreitung` im Content Studio ermöglicht dem echten Firmen-Admin Kontakt, Datenschutz, Speicherfrist, Filter, Ablaufdatum und gemeinsamen Werbeplan. Ungespeicherte Text-/Bild-/Planänderungen sperren Aktivierung; konkurrierende Plan-/Bildrevisionen werden geprüft. Das Aktivieren veröffentlicht nur die **lokale MH-Seite** und bereitet stabile Kanal-Links für Beitrag/Anzeige/Retargeting vor. Interner Status `Live` allein aktiviert weiterhin nichts. Keine automatische Meta-Veröffentlichung, Ads-Buchung, Zahlung oder Pixel-/Conversions-API-Übertragung. Bestehende explizite Facebook-Text-/Link-Publikation bleibt getrennt. HTTPS-Domain, verifizierte Anbieteranbindung, Instagram-Medienpublikation, Anzeigenkonto/Buchung und echte Retargeting-Ausspielung bleiben offen. Die Verlinkung normaler Instagram-Beiträge muss bei der späteren Integration anhand der Kontofunktionen geplant werden (Profil/Story statt vorausgesetzter Caption-Klickbarkeit).

Die Auswertung unterscheidet aggregierte Server-Seitenabrufe, Analyse-Einwilligungen, Lesesignale, Formularstarts, Bewerbungen aus zustimmenden Besuchen und alle tatsächlich gespeicherten Bewerbungen. **Lesesignal**: mindestens 30 aktive sichtbare Sekunden und 80 % sichtbare Textabschnitte nach freiwilliger Zustimmung; kein Beweis des Lesens, keine Bewerberbewertung. Schritte können übersprungen werden. Conversion entsteht beim erfolgreichen Speichern auf dem Server, nicht beim Klick/Redirect; Wiederholungen zählen nicht doppelt. Besuchsschritte gehören zur UTC-Besuchsstartkohorte, Gesamtbewerbungen zum tatsächlichen Eingangstag. Kein Versprechen eindeutiger Personen oder nachgewiesener Werbewirkung.

Analyse und Marketing sind getrennt und standardmäßig aus, mit gleichwertigen Ablehnen-/Erlauben-/Speichern-Knöpfen und Widerruf. Lesen/Bewerben ohne Zustimmung bleibt möglich. Nur Auswahl/Version werden 180 Tage lokal gespeichert; verschlüsselter Besuchstoken bleibt im Seitenspeicher. Temporäre Serverabläufe laufen nach 24 Stunden ab bzw. werden beim Widerruf entfernt; anonyme Tageszähler bleiben. Formularwerte gehen nicht in die Analyse. Marketing-Lesesignale sind **nur lokal**, keine echte Meta-Zielgruppe. Operative Bewerbungsspeicherung und aggregierte Request-Zählung werden separat behandelt. Produktions-Rechtsgrundlagen, Datenschutzhinweise und Providerregeln brauchen weiterhin Prüfung; Quellen/Abgrenzung siehe README.

Neue Module: `backend/job_portal.py`, `backend/test_job_portal.py`, `frontend/src/JobPortal.tsx`, `JobConsent.tsx`, `JobCampaign.tsx`, `job-portal.css`. Der digitale Zwilling enthält jetzt 57 Fälle und prüft elf Backend-Suiten. Alle neuen Oberflächentexte folgen DE/EN des Browsers; gespeicherte Texte bleiben unverändert. Backend neu starten und Browser neu laden, damit Tabellen und Routen verfügbar sind.

Verifikation: **146 Backend-Tests**, **14 Dashboard-Tests**, Frontend-Build, SEO und vollständige DE-/EN-Prüfung bestanden. Browserprüfung mit isolierter Datenbank/fiktiver Firma bestätigt Filter/Reset, Zustimmung, Lesesignal, Formularstart, gespeicherte Bewerbung, Auswertung mit jeweils 1, Widerruf, Planänderung/Speicherung und sechs vorbereitete Kanalaktionen ohne Ausgaben. Keine echte Anbieteraktion, Mail, Zahlung oder externe Veröffentlichung. Die bestehenden normalen lokalen Server wurden nicht beendet; Testserver verwenden getrennte Datenbanken, lokale Mailablage und fiktive Kontakte.

# MH Recruiting Workspace — project handoff

Last consolidated: 5 October 2026.

## Eigene Kampagnenbilder für Instagram und Meta (05.10.2026)

Der Nutzer hat Upload, Zuschnitt, Vorschau, gemeinsame Freigabe und Export eigener Kampagnenbilder zur Umsetzung bestätigt. Im Studio sind bis zu **sechs JPEG-/PNG-/WebP-Bilder pro Kampagne** möglich, jeweils höchstens 10 MiB, mindestens 100 px je Kante und höchstens 16 Megapixel; Animationen werden abgewiesen. Ein ausgewähltes Motiv gilt für Instagram und Meta. Feed (4:5) und Story (9:16) haben unabhängige Position-/Zoom-Ausschnitte und Vorschauen mit dem Kanaltext. Upload und Auswahl werden sofort gespeichert; Ausschnitte und bearbeitete Texte werden gemeinsam atomar gespeichert. Ungespeicherte Entwürfe bleiben beim Kampagnen-/Seitenwechsel erhalten; vor Freigabe und Export ist Speichern/Verwerfen nötig. Fotos sind optional und verbrauchen keine MH-Tokens; das Textpaket bleibt bei 50 Tokens.

`backend/campaign_images.py` speichert firmengebundene private Bilder in SQLite, normalisiert Orientierung und entfernt Metadaten einschließlich GPS. Sanitisiertes Original maximal 2400 px je Kante, JPG-Ausschnitte 1080×1350 und 1080×1920. Cookie-/CSRF-, Firmen-, Rollen-, Abo- und Recruiting-Schreibgates gelten; Kundenzugriff ist lesend. Review wird bei Bildänderungen wieder Draft; die Freigabe prüft `projects.image_revision`. Live-Bilder sind unveränderbar. Optimistische Bildrevision verhindert Überschreiben paralleler Änderungen; Text und Zuschnitt werden bei Konflikten gemeinsam zurückgerollt. Bildereignisse stehen im Verlauf, frühere Bilddateien werden nicht als Versionen archiviert. Firmenlöschung entfernt Bilder durch Kampagnen-Fremdschlüssel; Demoänderungen bleiben in der separaten Datenbank.

Der ZIP-Export enthält nur das gewählte Motiv als `images/feed-4x5.jpg` und `images/story-9x16.jpg` plus Auswahlmetadaten. Original/Galerie werden nicht exportiert. Die bestehende Facebook-Veröffentlichung sendet weiterhin ausschließlich Text und Link und erklärt dies in der Oberfläche. Eigene JPGs sind für manuelle Veröffentlichung gedacht. Direkte Bildveröffentlichung, Instagram-Publishing, Karussells, KI-Bilder und Anzeigenbuchung bleiben offen. Es wurden keine realen Anbieter-, Zahlungs-, Mail- oder Veröffentlichungsaktionen ausgelöst.

Verifikation: **137 Backend-Tests** (sechs Pflichtsuiten plus Tracking, Social, Recruiting und Kampagnenbilder), **14 Dashboard-Tests**, Frontend-Build, SEO und vollständige DE-/EN-Prüfung bestanden. Browserprüfung mit isolierter Datenbank/fiktivem Motiv bestätigt tatsächlichen Datei-Upload, beide Kanalvorschauen, unterschiedliche Ausschnitte, Entwurfserhalt beim Seitenwechsel und dauerhaft gemeinsames Speichern von Bild und Text nach Neuladen. `start.sh` prüft jetzt zusätzlich Pillow. Backend neu starten und Seite neu laden, damit Bildschema und neue Routen verfügbar sind.

## Content Studio: Instagram, Meta und gemeinsame MH-Zielseite (05.10.2026)

Der Nutzer hat das Studio auf **Instagram und Meta** begrenzt und den Kampagnen-Selector dort entfernen lassen. Die Kampagne wird über die Übersicht geöffnet und im Studio als fester Titel angezeigt. Der Assistent und das Onboarding bieten nur diese beiden Kanäle an; Landingpage und Paketbeschreibung entsprechen dem neuen Umfang. Neue Demo- und KI-Pakete enthalten genau `social`, `meta` und `jobAd`; der Preis bleibt 50 MH-Tokens. LinkedIn, XING und Videokonzept werden nicht mehr neu erstellt. Die bisherige automatische XING-Ergänzung beim Datenbankstart ist entfernt; vorhandene Inhalte werden nicht migriert oder gelöscht und bleiben in Exporten/gespeicherten Versionen erhalten.

Die Stellenanzeige war bisher als eigener Website-Format-Tab angelegt. Sie ist jetzt die **gemeinsame Stellenbeschreibung auf MH** und wird separat aufklappbar bearbeitet. Die vorhandene Bewerbungsseite nutzt weiterhin `jobAd` und wird erst nach interner Freigabe und ausdrücklicher Aktivierung öffentlich. Instagram und Meta können auf dieselbe MH-Seite verweisen. Eine öffentliche Stellenübersicht mit Filtern ist weiterhin nicht implementiert. Neue Anzeigenlinks bieten Instagram/Meta; vorhandene Facebook-Links bleiben kompatibel, und die ausdrückliche Facebook-Veröffentlichung akzeptiert auch Meta-Links. Dieser Ablauf ist nur im Meta-Tab sichtbar. Echte Veröffentlichung und Instagram-Medienpublikation bleiben in ihrem bisherigen Betriebs-/Verifikationsstatus.

Die Browsersprache gilt weiterhin für alle neuen Oberflächentexte. Lokale Browserprüfung mit fiktiven Daten bestätigt zwei Tabs, entfernten Selector, Tastaturwechsel und gemeinsames Speichern von Meta-Text/MH-Beschreibung. Keine Anmeldung mit Echtdaten, Zahlung, Mail oder externe Veröffentlichung wurde zur Prüfung ausgelöst. Verifikation: **129 Backend-Tests**, **14 Dashboard-Tests**, Frontend-Build, SEO und vollständige DE-/EN-Prüfung bestanden. Backend neu starten, damit neue Pakete den reduzierten Umfang nutzen.

## Aufräumen und vollständige UI-Sprachprüfung (05.10.2026)

Die Anwendung folgt weiterhin der ersten unterstützten Browsersprache (EN/DE, einschließlich regionaler Varianten); andere Sprachen fallen auf Englisch zurück. Die Auswahl erfolgt einmal pro Seitenaufruf. Ein Neuladen übernimmt eine geänderte Sprachreihenfolge, ohne laufende Formulare spontan umzuschalten. Öffentliche statische Vorberechnung bleibt Deutsch.

Die Sprachprüfung umfasst jetzt alle Produktbereiche: Landingpage, Anmeldung/Wiederherstellung/Einladungsannahme/MFA, Registrierung, Onboarding, Kunden/Firmenprofile, Kampagnen, Studio/Freigaben/Verlauf, Einstellungen/Rollen/Einladungen, Abrechnung/Tokenbuchungen, E-Mail-Vorschau, Recruiting, Bewerbungseingänge, öffentliche Bewerbungsseite und Facebook-Verbindung/-Veröffentlichung. Überschriften, API-Fehler, automatische Verlaufs-/Aktivitätstexte, Recruiting-Rückfragen, Downloadplanung und Browser-Metadaten sind ergänzt. Kommentare, Änderungswünsche und gespeicherte Kunden-/Bewerbertexte bleiben unverändert. Stripe Checkout und Kundenportal erhalten dieselbe DE-/EN-Sprache; ihre rechtlichen EU-/Steuer- und Zahlungsprüfungen bleiben erhalten. Anbieteraufrufe zur Prüfung werden ausschließlich simuliert.

Entfernt wurden 13 ungenutzte Python-Imports, 34 verwaiste CSS-Selektoren der früheren Studio-/Modal-/Diagrammansichten, neun alte Übersetzungseinträge und obsolete Tokenparameter/-Zustände aus der bereits Cookie-basierten Oberfläche. Der alte, in der separaten Einladungsansicht nicht erreichbare Benutzerformular-Zweig wurde entfernt. Alle Produktmodule haben weiterhin Aufrufer; direkt ausführbare Tests, Einrichtungs-/Startskripte und Dokumentation bleiben erhalten. TypeScript lehnt jetzt ungenutzte Imports, lokale Variablen und Parameter beim Build ab.

Verifikation: **128 Backend-Tests**, **14 Dashboard-Tests**, vollständige DE-/EN-Prüfung, Frontend-Build und SEO bestanden. Die Sprachprüfung kontrolliert außerdem alle statischen Übersetzungsschlüssel, sämtliche API-Fehlermeldungen und passende Platzhalter; sie rendert echte Komponenten mit fiktiven lokalen API-Zuständen. Browserprüfung bestätigte englische Landingpage und Anmeldung anhand der aktuellen Browsersprache. Backend für die geänderte Stripe-Sprachübergabe neu starten. Keine Zahlung, Mailzustellung oder externe Veröffentlichung wurde ausgelöst.

## Digitaler Zwilling und lokale Änderungsaufträge (02.10.2026)

Der Nutzer hat das HTML-Dashboard zum **digitalen Zwilling der gesamten Anwendung** erweitert beauftragt: Architektur ganz oben, alle Use Cases, je Fall ein Lösch-Prompt, gemeinsame Batch-Vorschau und Start über dasselbe Interface. Als Ziel wurde ausdrücklich **Projekt-Agent mit Zugriff auf diese Anwendung** gewählt. Der Auftrag erlaubt die Erstellung des Interfaces; er wählt noch keine Funktionen zur tatsächlichen Entfernung aus.

`output/use-case-dashboard/index.html` ist der portable HTML-Snapshot. `serve.py` stellt ihn auf http://127.0.0.1:5190 bereit und unterstützt jetzt explizite, geschützte lokale Agentenstarts. `template.html`, `style.css`, `app.js` und `build.py` sind die bearbeitbaren Quellen. `twin.py` liest ausschließlich den Quellbestand und erstellt Architektur-/API-Inventar und Lösch-Prompts ohne Import des Produkts oder private Datenbankzugriffe.

Der Katalog umfasst **56 Einträge**: 19 Bestand, zwölf Zielbild, 20 nachträglich ergänzte Funktionsfälle UC-I01–UC-I20 und fünf dokumentierte offene Betriebsaufgaben UC-P01–UC-P05. Aktuell: 45 lokal umgesetzt, fünf teilweise, sechs offen, null entfernt. Herkunft und Überschneidungen sind sichtbar. Die 23 NFA bleiben gesonderte Qualitätsanforderungen. API-Inventar: 85 aus dem Quelltext erkannte Routen; Tabellen werden aus Schema-Definitionen gelesen. Architekturmodule sind fachlich zugeordnet; gemeinsame Quelldateien sind Untersuchungshinweise, kein Aufrufgraph.

Die direkte Ausführung verwendet die vorhandene Codex-CLI mit gespeicherter ChatGPT-Anmeldung, Workspace-Schreibsandbox und automatischer Freigabeprüfung. Ein expliziter Start nach Gesamtprüfung sichert zuvor nur Quellcode/Dokumente; verändert nicht absichtlich bestehende Kunden-/Bewerber-/Abrechnungsdaten und führt keine Anbieter-, Mail-, Zahlungs- oder Veröffentlichungsaktion aus. Bekannte IDs, Quellfingerprint, Origin, CSRF und feste Befehle begrenzen die Startschnittstelle; ein unveränderter Batch läuft genau einmal und nur ein Auftrag gleichzeitig. Nach dem Agentenlauf prüft der Server die zehn Backend-Suiten, Build, SEO und Sprache unabhängig. Abbruch beendet die eigene Prozessgruppe, setzt vorhandene Änderungen nicht zurück. Private Laufdateien/Backups liegen unter `output/use-case-dashboard/runs/<ID>/` und sind nicht per HTTP abrufbar.

Verifikation: **126 Produkt-Backend-Tests**, **14 Dashboard-Tests** mit isoliertem Test-Agenten, Frontend-Build, SEO und Sprache bestanden. Browserprüfung bestätigte Architekturfilter, zweifaches Prompt-Batching, Gesamtvorschau und Startfreigabe; der echte Start wurde nicht gedrückt, die Testauswahl wurde geleert. Kein tatsächlicher Produkt-Use-Case wurde entfernt und kein realer Agenten-Löschlauf wurde zur Abnahme gestartet. Ein späterer echter Lauf kann an Anmeldung, Anbieterzugang oder Freigaben scheitern; Fehlerstatus ist vorgesehen. Details und Bedienung: `docs/requirements/DIGITALER_ZWILLING.md`.

## Recruiting-Zielbild und HTML-Dashboard (02.10.2026)

Der Nutzer hat nach Erstellung des Dashboards **UC-Z01 bis UC-Z11** zur Umsetzung freigegeben; UC-Z12 (optionale fachliche KI-Prüfrunde) bleibt zurückgestellt. Der Bewertungsbogen in `docs/requirements/USE_CASES_ZIELBILD_REVIEW.md` enthält weiterhin offene Nutzenbewertungen und fachliche Entscheidungen. Die Freigabe zur Programmierung ist kein gemessener Pilotnutzen.

`backend/recruiting.py` und `frontend/src/RecruitingWorkspace.tsx` ergänzen einen lokalen manuellen Kernablauf: Zuständigkeiten/offene Angaben, Muss-/Lernanforderungen und tatsächliche Arbeitszeiten, Briefingbezug der Texte, manuelle Publikationsnachweise, persönliche Bewerberreaktionen, Terminvorlage/Zusage/Ergebnis, offene Aufgaben/Fristen/Weitergabe, Aufwand/Ergebnisse und bewusster Abschluss/Wiederverwendung. Firmen-Admins und Bearbeiter finden den Ablauf unter **Recruiting**. Kontakt und Terminabsprachen erfolgen außerhalb von MH; ein Antwortentwurf wird nicht versendet und zählt nicht als Antwort. Neue persönliche Notizen werden verschlüsselt und teilen die ursprüngliche Bewerbungsfrist. Abschluss schaltet eigene Seite/Links ab, löscht keine externen Beiträge und kopiert bei Wiederverwendung keine Bewerberdaten oder Freigaben. Abo-/Token-/Freigabe- und Firmenrechte bleiben maßgeblich. Ältere Texte ohne Briefingbezug bleiben kompatibel und zeigen einen Prüfungshinweis.

Das gewünschte HTML-Dashboard wurde vor Produktänderungen bereitgestellt: `output/use-case-dashboard/index.html`, live unter http://127.0.0.1:5190 nach `python3 output/use-case-dashboard/serve.py`. Es umfasst 19 bestehende und zwölf Zielbild-Use-Cases, Umsetzungsnachweise, offene Lücken und lokale exportierbare Nutzerbewertungen. Statusquelle: `docs/requirements/use_case_status.json`; Snapshot vor Umsetzung: `output/use_case_status.before.json`. Die lokale Ansicht liest alle fünf Sekunden neu. Geänderte verknüpfte Dateien markieren den letzten Abgleich als überholt; neue Dateibelege müssen ergänzt werden. Das ist eine prüfbare Statusanzeige, keine automatische fachliche Abnahme.

Details, Abnahmekriterien und Grenzen: `docs/requirements/ZIELBILD_IMPLEMENTIERUNG.md`. Vollprüfung umfasst zusätzlich `backend/test_tracking.py`, `backend/test_social.py` und `backend/test_recruiting.py`. Browserprüfung verwendet nur eine getrennte Datenbank mit fiktiven Kontakten und lokalem Mailmodus. Kein echter Bewerberkontakt, keine Anbieteranfrage, Zahlung oder Veröffentlichung wurde zur Prüfung ausgelöst. Finale Verifikation: 126 Backend-Tests sowie Frontend-Build, SEO und Sprachprüfung bestanden; detaillierte Nachweise stehen im Dashboard-Statuskatalog.

This file is the main re-entry point for a future Codex session. Read it before making changes. It records what the user asked for, what exists, what remains a prototype, and what must happen next.

## Product objective

MH is a company-specific recruiting campaign workspace for small and growing businesses. A team creates a job briefing, produces channel-specific campaign drafts, edits and reviews them, approves content, exports assets, and records campaign metrics.

The commercial model combines a low monthly base price with MH tokens:

| Plan | Net monthly price | Included tokens | Editors | Included 50-token campaign packages |
| --- | ---: | ---: | ---: | ---: |
| Starter | €19 | 250 | 3 | 5 |
| Team | €69 | 1,500 | 10 | 30 |
| Scale | €149 | 4,000 | 25 | 80 |

Annual upfront prices are €190/€690/€1,490 with the same monthly token allotments. Token top-ups are one-time payments: 250 tokens for €12, 1,000 for €39, and 2,500 for €89. A new campaign draft costs 50 tokens for billing-managed accounts. Included tokens renew with a successfully paid monthly invoice or at each monthly anniversary during a paid annual term; unused included tokens expire. Purchased tokens remain separate, but are usable only while the subscription is active. There is no automatic top-up.

All published prices are net EUR amounts. Stripe Checkout displays applicable tax and collects tax IDs. The intended first market is companies with a registered office and billing address in one of the 27 EU member states.

## User journey

The public landing page at `/` leads the visitor through four explicit steps:

1. Understand the recruiting workflow.
2. Calculate expected campaign packages and editor seats.
3. Compare and select one of the three plans.
4. Create an account or sign in, then continue to billing.

The calculator recommends the cheapest plan with enough editor seats. The plan and calculator state persist in session storage. The user may download a plain-text planning summary. Selecting a plan does not itself create a purchase.

New customers use `/register` and continue to `/onboarding`: verify email, enroll admin TOTP and save recovery codes, pay through Stripe, fill the company profile, create a confirmed 50-token draft and mark it for review. Registration works without Stripe credentials and never charges a card. Existing company admins sign in at `/app` and open “Abo & Tokens.”

## Implemented application

### Recruiting workspace

- FastAPI backend with SQLite and a React/Vite frontend.
- Multi-tenant organization isolation on every company-scoped API operation.
- Roles: Platform Admin, Firmen Admin, User, and Kunde.
- Company profiles and reusable briefing defaults.
- Campaign lifecycle: Draft → Review → Live.
- Paid managed accounts use server-side OpenAI Responses for Instagram, Meta ad copy and the shared MH application-page description; demo accounts use local templates. Historical saved formats remain in history and exports.
- Content editing, comments, history, saved-version comparison, review requests, approval, ZIP export, SVG creative, and manually entered analytics.
- Platform Admin demo-role preview uses a separate demo database.
- Platform Admin can delete non-billing customer companies after reviewing affected record counts and entering the exact company name. Company users, sessions, campaigns, history, metrics, invitations and credentials are removed atomically. Customers with any billing account, order, ledger or invoice-delivery data cannot be deleted here; the UI explains that subscriptions and accounting evidence need separate review. This action never calls Stripe or cancels subscriptions.

Paid generation requires the centrally configured OpenAI key; without it the request fails with no MH-token deduction. No actual provider call has been verified yet. The current “Live” state does not publish to social platforms.

### Landing page and SEO

- Responsive German landing page with product preview, workflow, pricing, token explanation, calculator, FAQ, and clear calls to action.
- Pre-rendered landing HTML that hydrates in the browser.
- Descriptive title and meta description, Open Graph/Twitter metadata, favicon, and truthful WebPage/WebSite JSON-LD.
- Generated `robots.txt`, `sitemap.xml`, `/app/index.html`, `/register/index.html`, and a real HTTP 404 page.
- Login, registration, and error routes are `noindex`.
- A normal build remains `noindex`. A public build requires a valid public HTTPS `SITE_URL`; it then adds the canonical URL and an indexable sitemap.
- No fabricated reviews, customer claims, or social preview image are present.

### Registration and onboarding

- Cookie-only sessions (HttpOnly, SameSite=Lax; Secure in production), CSRF bound to authenticated sessions and exact-origin CORS. No frontend bearer token storage.
- Workspace startup uses `/auth/session`, which returns HTTP 200 with an anonymous state when signed out or expired. `/auth/me` and all protected resources still return 401 without valid authentication. The startup probe is deduplicated during React StrictMode and displays a loading state; connection failures remain visible rather than being silently treated as logout.
- Email verification, resending and password reset with hashed expiring single-use links; persistent rate limits, 15-character minimum passwords and stronger scrypt hashes. Password changes revoke sessions and preserve MFA.
- Mandatory TOTP for new company admins, encrypted seeds, single-use hashed recovery codes, replay protection and session rotation. Existing development demo users retain access. No bulk lockout migration of existing accounts.
- Local mail goes only to private `backend/mail_outbox/*.eml`. SMTP STARTTLS adapter exists but no real mail provider is connected. Local MFA encryption key is `backend/.auth.key`; it must remain private and be preserved with the database.
- Organization- and role-bound 48-hour invitations, seat reservations, revocation and atomic acceptance. Managed company admins cannot directly create users with an operator-chosen password.
- Resumable onboarding gates profile and reviewed generated draft completion on confirmed paid access. Paid drafts require configured OpenAI; demos remain deterministic.
- Production requires MH_ENV=production, HTTPS, SMTP mode, stable encryption key and disabled demo switcher. Production does not seed demo data.
- See AUTH_SETUP.md for local operation, setup, limits and remaining operator work.

### Stripe billing

- Stripe-hosted Checkout for monthly or annual subscriptions and one-time token packages.
- Checkout uses hosted-page UI with no phone collection or promotions and mandatory payment-method collection for subscriptions. The secure EU settings remain authoritative: billing address required, automatic tax and tax-ID collection enabled, card-only payment, existing Stripe Customer, server-owned order metadata and downstream subscription/payment metadata. The temporary Checkout Studio change that removed those fields was reverted on 29 September 2026 because it broke webhook order association and the EU VAT design. `STRIPE_INTEGRATION_TODO.md` is the source of truth for remaining setup.
- Card payment only at present.
- Stripe Tax automatic calculation and tax-ID collection.
- Required billing address and EU country selection in MH.
- Server-owned product catalogue and validation of Stripe price amount, currency, tax behavior, and recurrence before Checkout is created.
- Company-specific Stripe Customer, subscription, order, account, token ledger, and processed-event records.
- Verified webhook signatures with a five-minute tolerance and environment matching.
- Current Stripe objects are retrieved during webhook handling instead of trusting the event payload alone.
- Browser redirects never grant access or tokens.
- Initial included tokens are granted only after a valid paid subscription invoice; paid annual plans then refresh their included balance at each monthly anniversary.
- Token top-ups are granted exactly once from a valid completed payment Checkout.
- Idempotent checkout creation and idempotent campaign token debit.
- Atomic token consumption, including concurrent requests.
- Failed content generation rolls back token consumption.
- Refunds, disputes, non-EU billing addresses, or amount mismatches place the account on hold.
- Test and live billing accounts are separated by mode.
- Customer portal exposes invoice history, payment-method updates, and cancellation at period end. Plan changes and address changes are disabled.
- Platform Admins and demo-role previews cannot initiate billing.
- Editor-seat limits are enforced for billing-managed accounts.
- Seeded demo accounts without a billing account retain the previous free prototype behavior.

## Main code map

| Area | File |
| --- | --- |
| Backend API and recruiting workflow | `backend/main.py` |
| Private campaign photos, crops and export | `backend/campaign_images.py`, `backend/test_campaign_images.py` |
| Photo gallery and crop previews | `frontend/src/CampaignImages.tsx`, `frontend/src/campaign-images.css` |
| Stripe catalogue, checkout, webhooks, tokens | `backend/billing.py` |
| Authentication, email links, MFA, invitations, onboarding | `backend/auth.py` |
| Auth UI and guided onboarding | `frontend/src/Auth.tsx`, `frontend/src/Onboarding.tsx`, `frontend/src/Invitations.tsx` |
| Auth security tests | `backend/test_auth.py` |
| Security and tenant tests | `backend/test_security.py` |
| Billing and concurrency tests | `backend/test_billing.py` |
| Main workspace UI | `frontend/src/App.tsx` |
| Billing and registration UI | `frontend/src/Billing.tsx` |
| Public landing page | `frontend/src/Landing.tsx` |
| Billing styles | `frontend/src/billing.css` |
| Landing styles | `frontend/src/landing.css` |
| Shared frontend API base | `frontend/src/api.ts` |
| Route selection and hydration | `frontend/src/main.tsx` |
| Static production server | `frontend/scripts/serve.mjs` |
| SEO prerendering | `frontend/scripts/prerender.mjs` |
| SEO verification | `frontend/scripts/verify.mjs` |
| Detailed Stripe setup | `BILLING_SETUP.md` |

## Routes

| Route | Purpose | Indexing |
| --- | --- | --- |
| `/` | Public landing page | Public build only |
| `/register` | EU company account registration | Noindex |
| `/app` | Login and authenticated workspace | Noindex |
| `/auth` | Verification, recovery, invitation acceptance | Noindex |
| `/onboarding` | Guided security, billing, profile and draft setup | Noindex |
| `/billing/config` | Public payment availability and catalogue | API |
| `/billing/status` | Company-admin billing and token status | Authenticated API |
| `/billing/checkout` | Create/reuse Stripe Checkout | Authenticated API |
| `/billing/checkout/cancel` | Explicitly expire an open Checkout | Authenticated API |
| `/billing/portal` | Create Stripe customer-portal session | Authenticated API |
| `/billing/webhook` | Stripe webhook receiver | Signed server-to-server API |

## Local operation

Backend:

```sh
cd /Users/michelherszak/Programming/Python/MH
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8011
```

Frontend development server:

```sh
cd /Users/michelherszak/Programming/Python/MH/frontend
npm run dev -- --host 127.0.0.1 --port 5181 --strictPort
```

URLs:

- Landing page: `http://127.0.0.1:5181/`
- Registration: `http://127.0.0.1:5181/register`
- Workspace: `http://127.0.0.1:5181/app`
- Backend health: `http://127.0.0.1:8011/health`

The first backend start creates local demo credentials in `backend/demo_credentials.txt`. That file, SQLite databases, integration secrets, and local environment files are ignored and must remain private.

## Verification baseline

The last complete verification passed:

- Latest session-startup change: all 53 backend tests, frontend build and SEO checks passed. Browser inspection confirmed the anonymous login page renders with no console errors; protected `/auth/me` still returns 401 when anonymous or expired. The React DevTools notice remains an informational development message.

- 50 backend tests passed in the full regression run; a subsequent 15-test auth run passed including one new non-admin MFA regression (51 distinct tests total). Frontend build and SEO checks also passed, including private auth/onboarding routes. Browser inspection confirmed registration works with an unconfigured payment provider and recovery UI renders correctly. Real SMTP and Stripe payments remain untested.
- TypeScript and Vite production build.
- SEO verification for pre-rendered content, metadata, sitemap, robots rules, redirects, noindex routes, and HTTP 404 behavior.
- Browser inspection of the landing flow, mobile layout, plan persistence, login transition, and EU registration form.

Run the complete baseline after changes:

```sh
cd /Users/michelherszak/Programming/Python/MH
python3 -m unittest backend/test_security.py backend/test_billing.py backend/test_stripe_setup.py backend/test_auth.py backend/test_ai.py
cd frontend
npm run build
npm run test:seo
```

## Configuration and secrets

Stripe test credentials and nine actual test price IDs now exist only in private ignored `backend/.env.local` (mode 600), never in tracked source or frontend. Start from `backend/.env.example` for a new installation. The required values are:

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- Nine Stripe Price IDs for six subscription variants and three token packages
- `MH_PUBLIC_URL`

Live mode also fails closed until all of these explicit gates are enabled:

- `MH_ENV=production` with configured SMTP delivery and a stable MFA encryption key (AUTH_SETUP.md)
- `MH_STRIPE_LIVE_ENABLED=1`
- `MH_EU_RADAR_CONFIRMED=1`
- `MH_STRIPE_TAX_READY=1`
- `MH_PAID_PRODUCT_READY=1`
- `MH_DEMO_SWITCHER=0`

The last flag concerning product readiness is especially important: real AI quality and usage must be validated with the configured provider before enabling paid-product readiness.

## Current blockers and next work

The application is now connected to the user's Stripe test account. Nine test products/prices exist, the API runs with the private config, and the CLI forwarded a signed customer.updated event successfully (HTTP 200). A harmless Stripe test customer “MH webhook connection test” was created; no payment or subscription was made. Stripe Tax is pending and has no default tax code. The user has not configured Tax yet. HTTPS certificate verification now uses the additional certifi CA bundle; no TLS checks were disabled. Backend tests plus build/SEO passed. Current local listener diagnostic log is private `/private/tmp/mh-stripe-listener-ryam4etg.log`; it contains the signing secret and must not be printed or shared. Listener must remain running or be restarted for local testing. The supplied test key appeared in chat; ask the user to rotate it after setup and store the replacement only locally.

The next operator tasks are:

1. Keep the connected Stripe test environment and signed CLI listener running. No public domain is needed for local testing; HTTPS is needed for deployment.
2. For future setup/restarts use `python3 -m backend.stripe_test setup` and `python3 -m backend.stripe_test start`. Nine current prices already exist and are reused via lookup keys. CLI is installed. No actual payment test has run. See BILLING_SETUP.md for secret handling and key rotation.
3. Configure Stripe Tax with the real selling entity, address, product tax category, and actual tax registrations.
4. Configure and test the webhook endpoint using API version `2026-08-26.dahlia`.
5. Add and test Stripe Radar rules that block missing or non-EU billing addresses. Checkout itself cannot restrict its billing-country dropdown to the EU.
6. Run a real Stripe test-mode journey: successful card, decline, 3D Secure, cancellation, duplicate webhooks, renewal, failed renewal, top-up, refund, and EU/non-EU address.
7. Add truthful company details, contact information, legal notice, privacy policy, and contractual terms.
8. Connect and verify real SMTP delivery and sender DNS records; deploy the implemented email verification, password recovery, MFA and abuse controls with production settings. Define a manually verified recovery process for lost MFA with no recovery codes. Existing-account email verification migration requires separate planning.
9. Configure OpenAI API key/billing, confirm data-processing region and measure representative campaign quality and provider usage; see TOKEN_PRICING.md. The integration exists but has not been tested against a real provider.
10. Create a production database without seeded demo accounts, use a separate Stripe live environment, and deploy behind HTTPS with `/api` routed to FastAPI.

Do not mark the site or payments as live until those steps are completed.

## Design and product decisions to preserve

- German customer-facing language; plain explanations before technical terminology.
- Light cream and green design across the public landing page and authenticated workspace. The workspace theme lives in `frontend/src/workspace-theme.css`, imported after its base and billing styles.
- Registration email verification, paid Stripe invoice notification and German B2B invoice readiness are detailed in `INVOICE_SETUP.md`.
- Transparent pricing before paid actions.
- No surprise charges and no automatic token top-up.
- Purchased tokens and monthly included tokens are separate balances.
- Manual review and export remain core product capabilities.
- Customer data is scoped by organization and cross-tenant access returns 404.
- Do not claim automatic publishing, real AI generation, live payments, or completed tax/legal readiness before those capabilities are verified.

## Documentation hierarchy

1. `PROJECT_CONTEXT.md` — concise canonical state and re-entry point.
2. `BILLING_SETUP.md` — operational Stripe and EU-payment details.
3. `AUTH_SETUP.md` — authentication, onboarding and SMTP operations.
4. `README.md` — product capabilities, run commands, landing page, and SEO behavior.
5. Tests — executable source of truth for expected security and billing behavior.

When behavior changes, update this file in the same change so a future session does not rely on stale assumptions.

## Workspace visual theme update

The authenticated app now uses the landing page palette: cream background, white cards, dark green text and primary actions, and lime-green highlights. The theme is isolated in `frontend/src/workspace-theme.css`; the public landing page keeps its own `landing.css`. No billing, token, or auth behavior changed. After this visual change, 56 backend tests, the frontend production build, and SEO verification passed.

## E-Mail- und Rechnungsablauf (28.09.2026)

Der Bestätigungslink wird nach Registrierung automatisch versendet und beim Öffnen ohne zweiten Buttonklick verbraucht. Er belegt den Zugriff auf das Postfach, nicht die Identität. Für bezahlte Stripe-Abo- und Tokenrechnungen gibt es nun eine persistente, bei Webhook-Wiederholung erneut zustellbare E-Mail mit Link zum Stripe-PDF an den bestätigten Firmen-Admin. PDF-Zustimmung wird beim Checkout erfasst. Die Rechnung selbst erstellt Stripe; MH ändert keine finalisierten PDFs. Live-Checkout verlangt zusätzlich `MH_INVOICE_READY=1`, damit Ausstellerdaten, Steuer-ID, Rechnungsmuster und E-Rechnungsstrategie bewusst geprüft werden.

**Noch offen:** rechtlicher Name und vollständige Anschrift des deutschen Rechnungsausstellers, echte Steuernummer/USt-ID im Stripe-Konto, Stripe-Tax-Einrichtung, SMTP-Anbieter/DNS und realer Test von Zahlung, PDF und Zustellung. Ein Stripe-PDF ist keine strukturierte deutsche E-Rechnung. Siehe `INVOICE_SETUP.md`. Keine echte E-Mail oder Kartenzahlung wurde durch diese Änderung ausgelöst. Die vollständige Regression ergab 60 bestandene Backend-Tests; Frontend-Build und SEO-Prüfung bestanden ebenfalls.

## Gmail-Testversand (28.09.2026)

Der Nutzer hat `Michel.herszak@gmail.com` als vorläufigen Testabsender gewählt und kann ein Google-App-Passwort erstellen. `backend/gmail_test.py` bereitet SMTP über `smtp.gmail.com:587` mit STARTTLS vor, nimmt das App-Passwort im Terminal verdeckt entgegen, sendet genau eine Selbsttest-Mail und aktiviert SMTP erst bei Erfolg. Die nichtgeheimen Werte sind in der privaten `.env.local` vorbereitet; `MH_MAIL_MODE` steht derzeit weiter auf `local`, es wurde keine echte Mail versendet. Nie nach dem App-Passwort im Chat fragen. Siehe `AUTH_SETUP.md`. Drei No-Network-Tests in `backend/test_gmail.py` bestanden. Die vollständige Regression ergab 63 bestandene Backend-Tests; Frontend-Build und SEO-Prüfung bestanden ebenfalls.

## Token wallet and AI implementation update

Dashboard and studio now show available/monthly/purchased MH credits, refresh after actions and poll every 15 seconds. All company roles can read their own /tokens/wallet and ten latest ledger entries; no other company or platform/demo billing disclosure. Multiple top-ups accumulate and duplicate payments remain idempotent. Paid generation uses strict OpenAI JSON output, 4000 output-token cap, bounded input, store=false and usage records. Failed/incomplete calls roll back customer charges. See TOKEN_PRICING.md for measured-vs-estimated cost distinctions and operating limits. No real provider or payment test completed.

Verification for token/AI update: 56 offline backend tests passed; production frontend build and SEO checks passed. Additional targeted assertions verify one provider call/usage row per idempotent generation and wallet visibility for the customer role while billing-admin access remains denied. Backend restarted on port 8011 with private Stripe test configuration. OpenAI key is absent; no real paid AI request was made.

## Gmail-SMTP-Testbefund (28.09.2026)

`Michel.herszak@gmail.com` ist als Testabsender vorbereitet. Der echte Verbindungscheck zu `smtp.gmail.com:587` gelang bis einschließlich STARTTLS und SMTP-AUTH-Ankündigung. Die lokale Python-3.10-Standard-Zertifikatsdatei fehlte; `backend/gmail_test.py` und `backend/auth.py` nutzen nun das bereits deklarierte `certifi`-Paket für die TLS-Zertifikatsprüfung. Der verdeckt eingegebene 16-stellige Google-Code wurde von Gmail mit **SMTP 535** abgelehnt. Es wurde keine echte Mail versendet, kein Code gespeichert; `MH_MAIL_MODE=local` und `MH_SMTP_PASSWORD` fehlt weiterhin. Erforderlich ist ein frisches, von **demselben Google-Konto** generiertes App-Passwort. Es gehört ausschließlich in den lokalen verdeckten Eingabedialog, nie in Chat oder Logs. Nach erfolgreichem Selbsttest muss das Backend neu gestartet werden.

## Gmail-Test erfolgreich (28.09.2026)

Der Nutzer gab ein neues Google-App-Passwort ausschließlich über den verdeckten lokalen Dialog ein. SMTP-Anmeldung und `send_message` an `Michel.herszak@gmail.com` waren erfolgreich; der Code wurde mit Dateirechten 0600 in `backend/.env.local` gespeichert und `MH_MAIL_MODE=smtp` aktiviert. Der lokale Backend-Testserver wurde über `python3 -m backend.stripe_test start` neu gestartet (Port 8011). Die Zustellung im Gmail-Posteingang muss der Nutzer noch bestätigen; der SMTP-Erfolg allein beweist sie nicht. Der zuvor mit SMTP 535 abgelehnte Code ist überholt.

## Weitergabefähige Anforderungen (28.09.2026)

Unter `docs/requirements/` liegen zwei von Modulen/Epics getrennte, editierbare Spezifikationen: `USE_CASES.md` (UC-01 bis UC-19) und `NICHTFUNKTIONALE_ANFORDERUNGEN.md` (NFA-01 bis NFA-23). Die PDFs stehen separat unter `output/pdf/`; `docs/requirements/build_pdfs.py` erzeugt sie aus Markdown. Statusbezeichnungen trennen lokal implementierte Funktionen von extern ungetesteten und offenen Punkten. Der Katalog wurde am 28. September 2026 auf die neuen Monats- und Jahrespreise umgestellt.

## Drei-Tier-Wirtschaftlichkeitsvorschlag (28.09.2026)

`BUSINESS_CASE_3_TIERS_2026-09.md` beschreibt den nun im Produkt umgesetzten Katalog: Starter 19 €/Monat (250 Tokens), Team 69 € (1.500 Tokens), Scale 149 € (4.000 Tokens); Jahresvorauszahlung 190/690/1.490 € mit monatlicher Tokenzuteilung; Nachkäufe 250/1.000/2.500 Tokens für 12/39/89 €. Grundlage ist GPT-6 Sol als zu testender Qualitätskandidat, mit 0,15 € geplantem KI-Kostensatz je 50-Token-Kampagnenpaket. Bei 30 % Jahreszahlern, 8 neuen Firmen/Monat, 2,5 % Kündigung, 220 € CAC, 700 € Betrieb und 3.000 € Unternehmerlohn ergibt der Modellfall 45,01 € Deckungsbeitrag/Firma/Monat, monatlichen Break-even in Monat 19 und kumulative Kostendeckung in Monat 42. Diese Werte sind Annahmen, keine beobachteten Kennzahlen. Stripe-Testpreise sind eingerichtet; eine vollständige Testzahlung und Live-Freigabe stehen aus.

## Geführte Kampagnenerstellung (28.09.2026)

Workspace und Ersteinrichtung verwenden jetzt denselben `frontend/src/CampaignWizard.tsx`: Stelle → Profil & Angebot → Kanäle → Prüfen. Deutsche Hilfetexte, Firmenprofil-Vorbelegung, Feldvalidierung, optionale Angaben und direkte Änderungslinks unterstützen die Eingabe. Die Prüfung zeigt fehlende Angaben, den festen Paketumfang, bei Firmenkonten Guthaben und 50-Token-Verbrauch sowie eine ausdrückliche Bestätigung. Demo-Vorlagen sind als kostenlos gekennzeichnet; Plattform-Admins sehen keine fremden Guthaben und erhalten einen Hinweis auf die kontobezogenen Kosten.

„Briefing speichern & später fortsetzen“ speichert einen Draft ohne Generierung oder Tokenverbrauch; bestehende Abo-Schreibgates gelten weiterhin. Bei einem Generierungsfehler bleibt der Dialog mit Fehlermeldung geöffnet; bekannte Kampagnen-ID und Generierungs-Idempotenzschlüssel werden beim erneuten Versuch in derselben Sitzung wiederverwendet. Native Dialog-Semantik, Fokusführung, Schließen-/Reload-Warnung, echte Checkboxen und mobile Darstellung sind enthalten. Wechsel zwischen Studio-Kanälen warnt vor ungespeicherten Textänderungen. Briefingänderungen erzeugen weiterhin nicht automatisch neue Texte.

Der Paketumfang und das Backend bleiben unverändert: sechs Textformate inklusive Videokonzept, manuelle Prüfung/Freigabe und Export. Keine automatische Veröffentlichung und kein echter Provideraufruf durch diese Änderung. Grundlage der Formstruktur: GOV.UK Question pages und Check answers. Eine isolierte Browser-Fixture prüfte Pflichtfelder, Kanalauswahl, Kostenbestätigung, Speichern sowie die Darstellung bei 390 px. Die vollständige Backend-Regression bestand mit 66 Tests; Frontend-Build und SEO-Prüfung bestanden.

## Content Studio UX (29.09.2026)

`frontend/src/ContentStudio.tsx` und `content-studio.css` ersetzen die enge Drei-Spalten-Ansicht durch einen Kampagnenkopf, sechs zugängliche Format-Tabs, einen großen Texteditor und eine umschaltbare vollständige Textvorschau. Vorschau und Bearbeitung bleiben auf Mobilgeräten verfügbar. Keine erfundenen Plattform-Layouts oder Medienvorschau; „Live“ wird hier als „Freigegeben“ mit Hinweis auf die fehlende externe Veröffentlichung erklärt. Briefing, Neugenerierung und Verlauf sind aufklappbar, die primären Aktionen Speichern, Freigabe und Export klar getrennt.

Ungespeicherte Texte liegen pro Kampagne und Format im App-Speicher, bleiben beim Kanal-, Kampagnen- und Seitenwechsel erhalten und werden nicht im Browser-Storage persistiert. Gemeinsames Speichern, Änderungsmarkierungen, Zeichen-/Wortzählung, Kopieren sowie Cmd/Ctrl+S im Editor sind verfügbar. Seitenneuladen, Abmelden und Demo-Kontextwechsel warnen vor Verlust; bei Anmeldung/Abmeldung bzw. erfolgreichem Demo-Wechsel wird der Entwurfsspeicher geleert. Freigabe, Neugenerierung und Export sind bei ungespeicherten Änderungen der jeweiligen Kampagne deaktiviert. API-Schreib-/Rollengates bleiben maßgeblich.

Browserprüfung an einer isolierten Fixture: Kanalwechsel bewahrt Eingaben, Home-Taste navigiert korrekt, ungespeicherte Änderungen sperren Freigabe/Export, Speichern aktualisiert den Status, vollständige mobile Vorschau und Aktionsleiste bei 390 px. Grundlage: GOV.UK Tabs (https://design-system.service.gov.uk/components/tabs/). Keine echten Anbieteraufrufe, Zahlungen oder Veröffentlichungen ausgeführt.

Verifikation dieser Studio-Änderung: 66 Backend-Tests, finaler TypeScript/Vite-Build und SEO-Prüfung bestanden. Die temporäre Browser-Fixture wurde entfernt.

## Kundenlöschung und zusätzliche Härtung (29.09.2026)

Kundenlöschung in Customers verlangt den exakten Firmennamen und einen echten Plattform-Admin. Die API prüft CSRF/Session, blockiert sämtliche Firmen mit Abrechnungsdaten und entfernt freigegebene lokale Firmendaten atomar. Die vorher vorhandene automatische Stripe-Kundenlöschung wurde entfernt. Gelöschte Demo-Seed-Firmen werden nicht erneut angelegt; die Sitzungen gelöschter Nutzer werden widerrufen. Keine vorhandene Kundenfirma wurde zur Prüfung gelöscht; Tests verwenden temporäre Datenbanken.

`backend/security.py` begrenzt Request-Bodies vor Parsing auf 1 MiB einschließlich chunked Transfer; Stripe-Rohbytes bleiben unverändert. Neue Feld-/Anzahllimits verhindern übergroße Briefings und Content-Patches. Produktions-API-Dokumentation ist deaktiviert. API und statischer Frontend-Server erhalten Frame-/Permissions-Schutz; der Frontend-Server setzt zusätzlich eine CSP mit Skripthashes. Details und verbleibende Betriebsanforderungen stehen in AUTH_SETUP.md.

Nach ausdrücklicher Nutzerfreigabe wurde `npm audit --json` gegen die offizielle npm-Registry ausgeführt: 0 gemeldete Schwachstellen für den installierten Abhängigkeitsbaum. Python pip-audit ist nicht installiert; ein externer Python-Abhängigkeitsscan steht aus. Kein Penetrationstest und keine vollständige Produktionsfreigabe.

Abschlussprüfung: 73 Backend-Tests bestanden, Frontend-Build und SEO-/Security-Header-Prüfung bestanden. npm audit meldet 0 bekannte Schwachstellen. Der identifizierte lokale Testserver wurde mit der privaten bestehenden Testkonfiguration neu gestartet; `/health` antwortet erfolgreich und liefert `X-Frame-Options: DENY`. Keine tatsächliche Kundenlöschung, Zahlung oder externe Nachricht ausgelöst.

## E-Mail-Vorschau für Platform Admin (29.09.2026)

Unter System → E-Mail-Vorschau zeigt `frontend/src/EmailPreviews.tsx` Registrierung/E-Mail-Bestätigung, Passwort-Zurücksetzen, Einladung und Rechnungsbenachrichtigung mit fiktiven Beispieldaten. Desktop-/Mobilbreite sowie gerenderte Postfachansicht und unveränderter Klartext sind umschaltbar. Das tatsächliche Versandformat bleibt text/plain; keine neue HTML-Mailgestaltung und kein Versand wurden eingeführt.

`backend/mail_templates.py` enthält nebenwirkungsfreie gemeinsame Message-Builder für Vorschau und echten Versand. `GET /admin/email-previews` ist nur für echte Platform Admins ohne Demo-Rollenvorschau zugänglich, liefert no-store und verwendet keine echten Adressen, Tokens oder Rechnungslinks. Links sind in der UI nicht anklickbar; React rendert Text ohne HTML-Injektion. Die Rechnungsvorschau betrifft die Benachrichtigung, nicht das von Stripe erzeugte Rechnungs-PDF.

77 Backend-Tests bestanden, einschließlich Admin-Zugriffsschutz, Versandfreiheit der Vorschau und identischem Auth-Mailinhalt. Vier Ansichten und finale Darstellung wurden an einer temporären Browser-Fixture geprüft; diese wurde entfernt. Lokales Backend und Frontend wurden neu gestartet; der Vorschau-Endpunkt liefert anonym 401. Keine echte E-Mail versendet.

## Deutsch/Englisch nach Browsersprache (30.09.2026)

Die Bedienoberfläche folgt beim Laden der ersten unterstützten Sprache in `navigator.languages`: `de` einschließlich regionaler Varianten → Deutsch, `en` → Englisch; ohne unterstützte Präferenz → Englisch. `frontend/src/i18n.ts` und `translations.json` versorgen Landingpage, Anmeldung/Sicherheit, Registrierung, Onboarding, Kampagnen-Assistent, Content Studio, Adminbereiche und Billing mit lokal gespeicherten Übersetzungen. Datums-, Zahlen- und EUR-Formate sowie das HTML-Sprachattribut und clientseitige Seitentitel folgen der Auswahl. Die Sprache wird beim Seitenladen festgelegt; nach einer Änderung der Browsereinstellung neu laden. Es gibt keinen externen Übersetzungsdienst und keinen gespeicherten Sprach-Override.

Gespeicherte Firmen-, Briefing- und Kampagnentexte werden nicht übersetzt. E-Mail-Vorlagen sind seit der nachfolgenden Ergänzung ebenfalls zweisprachig. Interne Rollen-, Status-, Format- und Kanalwerte bleiben unverändert. Bekannte API-Fehlermeldungen werden in der Oberfläche übersetzt; unbekannte Servermeldungen bleiben im Original. Stripe-Checkout behält seine bisherige serverseitige Konfiguration. Das öffentliche Prerendering bleibt Deutsch; englische Clients mounten ihre übersetzte Ansicht ohne Hydration-Mismatch.

Verifikation: alle 77 Backend-Tests, finaler Frontend-Build, SEO-Prüfung und `npm run test:language` bestanden. Die Sprachprüfung rendert Landingpage, Assistent und Studio in beiden Sprachen und prüft Präferenzreihenfolge, Fallback, deutsches Prerendering, EUR-Formatierung und unveränderte/escaped Kundentexte. Sichtbare Chrome-Prüfung in der getrennten Testumgebung: englische Anmeldung als Firmen-Admin, vorhandene deutsche Testkampagne im englischen Studio, sechs Texte weiterhin gespeichert. Die lokale Testinstanz unter localhost:5182 nutzt eigene Daten und keinen echten Versand oder Zahlungsschlüssel.

## Zweisprachige E-Mail-Vorlagen (30.09.2026)

Registrierung, Passwort-Zurücksetzen, Einladungen und Rechnungsbenachrichtigungen verwenden gemeinsame deutsche/englische Vorlagen einschließlich Betreff und Content-Language. Die Oberfläche übermittelt ihre aufgelöste Browsersprache als Accept-Language; die Adminvorschau rendert genau diese Versandvorlagen. Die API berücksichtigt bei direkten Aufrufen regionale Varianten und Sprachgewichtungen. Ohne unterstützte Angabe bleiben bestehende Konten und Vorschauen Deutsch.

Die neue additive users.email_language-Spalte wird bei Registrierung, erfolgreicher Anmeldung, Einladungsannahme und Checkout gesetzt. Rechnungs-Webhooks verwenden die gespeicherte Sprache des bestätigten Empfängers, ohne Browserkontext zu benötigen. Passwort- und Bestätigungslinks folgen der aktuellen Anfrage, andernfalls der gespeicherten Empfängersprache. Einladungen verwenden die Browsersprache des Einladenden, da der Empfänger noch kein Konto hat. Bereits versendete Nachrichten und Stripe-Rechnungs-PDFs werden nicht geändert. Sicherheit, Linkgültigkeit und Zahlungsfreigabe bleiben unverändert.

Verifikation: 80 Backend-Tests, Frontend-Build, SEO- und Sprachprüfungen bestanden. Alle vier englischen Vorschauen wurden sichtbar in Chrome geprüft. Die isolierte Testumgebung localhost:5182/8012 wurde aktualisiert und neu gestartet; kein echter Mailversand und keine Zahlung ausgelöst.

## Anzeigenstatus-Benachrichtigungen (30.09.2026)

Jeder tatsächliche Statuswechsel über PATCH /campaigns/{id} erzeugt in derselben Transaktion persistente Versandaufträge für sämtliche bestätigten Nutzer der zugehörigen Firma (Firmen Admin, User und Kunde, einschließlich der handelnden Person). Draft → Review, Review → Draft bei Änderungswünschen und Review → Live werden unterstützt. Wiederholung desselben Status, reine Inhaltsänderungen, abgewiesene Aktionen und Demo-Rollenvorschauen erzeugen keine Benachrichtigung. Fremde Firmen und globale Plattform-Admins werden nicht als Empfänger aufgenommen.

backend/status_mail.py speichert je Statusereignis und Empfänger einen eindeutigen Auftrag mit eingefrorenem Anzeigen-/Firmennamen, altem/neuem Status, Akteur und Empfängersprache. Einzelne E-Mails verwenden die bestehende DE/EN-Kontosprache; Adressen werden nicht an andere Empfänger offengelegt. Die Vorlage enthält keine Anzeigeninhalte und erläutert die interne Bedeutung von Freigegeben/Approved. Auch bei Rückkehr zum Entwurf erhalten Kundenrollen die minimale Statusmitteilung; deren Zugriff auf Entwurfsinhalte bleibt weiterhin gesperrt.

Versand erfolgt erst nach Commit im Hintergrund. Ein gestarteter Server prüft die Warteschlange alle 30 Sekunden, wiederholt Fehler mit zunehmendem Abstand bis maximal einer Stunde und übernimmt liegengebliebene Zustellungen nach fünf Minuten. SMTP-Fehler setzen den gespeicherten Anzeigenstatus nicht zurück. Eine transaktionale Claim verhindert parallele Zustellungen desselben Auftrags; bereits bestätigter Versand wird nicht wiederholt. Ein Absturz nach SMTP-Annahme vor lokaler Bestätigung kann bei erneutem Versuch wie bei sonstiger SMTP-Zustellung trotzdem zu einer doppelten E-Mail führen. Vor jedem Versuch werden Firmenzugehörigkeit und bestätigte Mailadresse nochmals geprüft. Firmenlöschung entfernt zugehörige Warteschlangendaten über Fremdschlüssel-Kaskaden.

Die fünfte Vorlage „Statusänderung / Status change“ ist unter System → E-Mail-Vorschau sichtbar. 83 Backend-Tests, Build, SEO- und Sprachprüfungen bestanden; isolierte Chrome-Vorschau auf Deutsch geprüft. Die Testumgebung localhost:5182/8012 wurde aktualisiert. Kein tatsächlicher externer Versand wurde zu Testzwecken ausgelöst.

## Sichtbarkeit Abo & Tokens (30.09.2026)

Der System-Menüpunkt und die Abrechnungsseite werden ausschließlich für echte Firmen-Admins mit Firmenzuordnung ohne Demo-Rollenvorschau gerendert. Ein direkter ?billing-Aufruf oder ein Rollenwechsel führt andere Nutzer zur Übersicht, ohne Abrechnungsansicht oder deren Überschrift einzublenden. Auch Tokens aufladen verwendet diese Bedingung. Backend-Berechtigungen bleiben unverändert: Firmen-Admins dürfen Abrechnung verwalten; Plattform-Admins, User, Kunde und Demoansichten erhalten 403 auf Status/Checkout/Portal/Checkout-Abbruch.

Verifikation dieser Änderung: 84 Backend-Tests, Frontend-Build, SEO- und Sprachprüfungen bestanden. Sichtbare Testprüfung: Firmen-Admin sieht den Menüpunkt; Plattform-Admin erhält auch bei ?billing=1 nur die Übersicht ohne Abrechnungsanzeige.


## Facebook-Unternehmensseiten und Instagram-Vorbereitung (30.09.2026)

Jede Firma verbindet ihre eigene Facebook-Unternehmensseite über eine zentrale MH-Meta-App; später folgt ihr eigenes professionelles Instagram-Konto. Globale Plattform-Admins und Demo-Rollenvorschauen können keine Kundenverbindung herstellen oder veröffentlichen. Facebook ist lokal implementiert, **extern noch nicht verifiziert**: Firmen-Admin meldet über Facebook an und wählt eine tatsächlich autorisierte Seite; Firmen-Admins/Bearbeiter prüfen einen normalen Text-/Linkbeitrag und bestätigen den öffentlichen Versand ausdrücklich. Bestehende Abo-Schreibgates gelten. Keine bezahlte Werbung, Gruppenveröffentlichung oder eigener Bild-Upload. Der interne Status Live bleibt Freigegeben und veröffentlicht weiterhin nichts automatisch. Erst eine separate Veröffentlichungsaktion und gültige Anbieter-Beitrags-ID bestätigen den externen Beitrag.

`backend/social.py` enthält verschlüsselte, firmengebundene OAuth-/Seitendaten, sitzungsgebundenen einmaligen OAuth-State, Seitenauswahl und einen transaktional beanspruchten Versand pro Kampagne. Vorschauen laufen nach 20 Minuten ab und werden gegen Zielverbindung, Kampagne und aktiven Facebook-Bewerbungslink erneut geprüft. Timeout/unklare Antwort/Prozessabsturz führen zu keiner automatischen Wiederholung. Firmen-Admins können vorhandene Beiträge nach zwei Minuten über Meta nachträglich verifizieren; Zielseite und vollständiger Text müssen übereinstimmen. Verbindung entfernen löscht lokale Zugänge, aber keine Facebook-Beiträge oder Meta-App-Berechtigungen.

`frontend/src/SocialPublishing.tsx` zeigt unter Settings die eigene Meta-Verbindung und im Studio Vorschau, Bestätigung und Veröffentlichungsstatus; Texte sind DE/EN verfügbar. Legacy-Meta-Schlüsseleingabe ist in der UI ausgeblendet und wird nicht für den neuen Veröffentlichungsablauf verwendet. Instagram ist begonnen: optionale Rechte und Kontodiscovery über Instagram API with Facebook Login für ein mit der gewählten Seite verknüpftes professionelles Konto. Noch keine Instagram-Veröffentlichung; JPEG-/Video-Medienbereitstellung und Media-Container-Workflow bleiben offen. Die Agentur für Arbeit ist ausdrücklich ausgeschlossen.

**Noch nötig:** öffentliche HTTPS-Origin mit funktionierendem API-/Bewerbungsseitenrouting; zentrale Meta-App, App-Domain, Datenschutz-/Datenlöschungsangaben, exakte OAuth-Rücksprungadresse, gewählte unterstützte API-Version und passende Seitenrechte. App-Review/Advanced-Access/Business-Verifizierung vor beliebigen Kundenkonten im konkreten Meta-Anwendungsfall klären. Weder Domain noch Meta-App waren bei Umsetzung vorhanden; keine echte Meta-Anmeldung, Veröffentlichung oder Werbeausgabe ausgelöst. `META_SETUP.md` beschreibt Einrichtung, Abnahme und Grenzen. `python3 -m backend.meta_setup setup` speichert erst nach späterer Einrichtung die App-Daten im privaten lokalen Konfigurationsdialog; App-Secret bleibt verdeckt, alle bestehenden Konfigurationswerte bleiben erhalten. Keine Meta-Secrets in Chat oder Frontend.

Verifikation: 113 Backend-Tests einschließlich Tracking und Social bestanden; Frontend-Build, SEO- und Sprachprüfungen bestanden. Sichtbare Chrome-Prüfung an einer isolierten lokalen Fixture: fehlende Einrichtung sperrt Anmeldung/Versand, autorisierte Seite auswählbar, Vorschau mit Zielseite/Link, geänderter Text sperrt die alte Bestätigung, Checkbox erlaubt genau einen simulierten Versand und zeigt den bestätigten Status. Die temporäre Fixture und ihr Testserver wurden entfernt. Screenshots in `output/screenshots/facebook-setup-preview.jpg` und `facebook-local-test.jpg` zeigen ausschließlich fiktive Daten. Keine echte Meta-Verbindung oder Veröffentlichung verifiziert.

## Bestätigung des Firmenmodells und lokale Testansicht (30.09.2026)

Der Nutzer hat das Modell ausdrücklich zur Umsetzung bestätigt: Jeder Betrieb verbindet und nutzt seine eigene Unternehmensseite. Der bestehende Firmenablauf wurde in die isolierte Testumgebung localhost:5182/8012 übernommen; deren Backend wurde mit eigener Datenbank und lokalem Mailmodus neu gestartet. Keine echten Meta-/Stripe-/OpenAI-Zugänge wurden dort eingerichtet. Firmen-Admins sehen die eigene Seitenverbindung unter Einstellungen und das Firmenteam den separaten Facebook-Veröffentlichungsbereich im Studio. Die technische Liste fehlender zentraler Meta-App-Konfiguration wird in der Kundenoberfläche nicht mehr angezeigt; Betreiberdiagnose und Einrichtung bleiben in backend.meta_setup und META_SETUP.md.

Ein zusätzlicher Regressionstest verbindet zwei Firmen mit verschiedenen Seiten, verhindert eine fremde Seitenauswahl, veröffentlicht ausschließlich auf der Seite der ersten Firma und bestätigt, dass deren Trennung die zweite Firmenverbindung erhält. Alle 114 Backend-Tests, finaler Build sowie SEO- und Sprachprüfungen bestanden. Sichtbare Browserprüfung im tatsächlichen lokalen Firmenkonto bestätigt Einstellungen und Studio ohne neue Anbieteraufrufe. Screenshot: output/screenshots/company-meta-settings.jpg. Öffentliche HTTPS-Adresse, zentrale Meta-App/Freigaben und echte Facebook-Abnahme bleiben erforderlich; Instagram-Veröffentlichung bleibt ausstehend.

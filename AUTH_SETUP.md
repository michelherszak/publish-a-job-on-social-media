# Registrierung und Onboarding

## Ablauf

Tarifplanung → Registrierung → E-Mail bestätigen → Authenticator einrichten und Wiederherstellungscodes sichern → Stripe-Tarif buchen → bestätigter Zahlungs-Webhook → Firmenprofil → Briefing speichern und direkt zum Dashboard; alternativ erstes Textpaket (50 Tokens mit Bestätigung) → Text lesen und zur Prüfung markieren → Workspace.

Die Einrichtung kann nach späterer Anmeldung fortgesetzt werden. Teammitglieder werden in Settings per Einladung hinzugefügt. Eine Einladung gilt 48 Stunden, für genau eine E-Mail, Firma und Rolle. Die Person setzt ihr Passwort selbst. Firmen-Admins benötigen MFA. Kein automatischer Firmenbeitritt anhand der Maildomain. Offene Einladungen reservieren Bearbeiterplätze und lassen sich widerrufen; bei Annahme werden Tarif und Plätze erneut geprüft.

## Lokal testen

1. `http://127.0.0.1:5181/register` öffnen und ein neues Testfirmenkonto erstellen. Passwort: 15–128 Zeichen. Registrierung funktioniert auch ohne Stripe-Schlüssel; Zahlung und kostenpflichtige Funktionen bleiben bis zur Einrichtung gesperrt.
2. Die neueste Datei in `backend/mail_outbox/` mit einem Texteditor öffnen. Den enthaltenen Link im Browser öffnen und E-Mail ausdrücklich bestätigen. Nachrichten werden **lokal gespeichert, nicht tatsächlich versendet**. Dateien haben Berechtigung 600, der Ordner 700. Kein öffentlicher Mailabruf-Endpunkt. Diese Dateien enthalten private Einmal-Links und dürfen nicht geteilt werden.
3. Anmelden bzw. „Bestätigung prüfen“ im Onboarding wählen. „Authenticator einrichten“ wählen und den angezeigten QR-Code mit der Authenticator-App scannen. Ohne Kamera ist der Schlüssel unter „Einrichtung ohne Kamera“ erreichbar. MH verwendet zeitbasierte Codes mit sechs Stellen und 30 Sekunden. Aktuellen Code bestätigen und die zehn Wiederherstellungscodes im Passwortmanager sichern. Schlüssel und Codes gehören ausschließlich dem Kontoinhaber.
4. Stripe gemäß `BILLING_SETUP.md` verbinden. Tarif buchen, Firmenprofil ausfüllen und ersten Entwurf prüfen.

`/auth?action=forgot` fordert einen Passwort-Reset an; `/auth?action=resend` eine neue Bestätigung. Bei aktivierter MFA benötigt der Reset zusätzlich einen unbenutzten Wiederherstellungscode. Die Änderung widerruft alle Sitzungen, lässt MFA aktiv und meldet nicht automatisch an. „Authenticator-App verbinden“ zeigt nach Prüfung eines unbenutzten Wiederherstellungscodes den bestehenden Konto-QR. Danach muss ein Code aus der verbundenen App bestätigt werden. Bei verlorener Authenticator-App und fehlenden Codes startet `/auth?action=recover` den unten beschriebenen geprüften Betreiberprozess; es gibt keinen automatischen E-Mail-Bypass.

Start aus dem Projektordner, nach Installation von `backend/requirements.txt`:

```sh
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8011
```

Mit eingerichteter Stripe-Testkonfiguration stattdessen `python3 -m backend.stripe_test start`, damit `.env.local` geladen wird. Der normale Uvicorn-Befehl lädt diese Datei nicht automatisch.

## Gmail als lokaler Testanbieter

Für `Michel.herszak@gmail.com` sind SMTP-Host `smtp.gmail.com`, Port 587 mit STARTTLS, Absender und Benutzername in der privaten `backend/.env.local` vorbereitet. **Der Mailmodus ist nach erfolgreichem Selbsttest auf `smtp` gestellt.** Google verlangt für diesen SMTP-Weg ein eigenes App-Passwort bei aktivierter Bestätigung in zwei Schritten. Das normale Google-Passwort nicht verwenden; das App-Passwort niemals in den Chat eingeben.

1. Im eigenen Google-Konto unter https://myaccount.google.com/apppasswords ein App-Passwort nur für den MH-Test erstellen.
2. Im Projektordner in einem **eigenen Terminal** `python3 -m backend.gmail_test connect` ausführen. Die Eingabe ist verdeckt. Das Skript sendet genau eine Testmail an dasselbe Gmail-Konto und speichert das App-Passwort mit Dateiberechtigung 600 erst, wenn Google Anmeldung und Versand akzeptiert.
3. Danach das Backend mit `python3 -m backend.stripe_test start` neu starten. Anschließend eine neue Testregistrierung ausführen und die Bestätigungsmail prüfen. Für eine erneute Testregistrierung eine andere eigene Mailadresse oder einen Gmail-Plus-Alias verwenden.

Aktueller Testbefund: Ein neues Google-App-Passwort wurde im verdeckten lokalen Dialog akzeptiert, und Gmail nahm die Selbsttest-Mail an `Michel.herszak@gmail.com` an. `MH_MAIL_MODE=smtp` ist aktiv und der lokale Backend-Testserver wurde neu gestartet. Die tatsächliche Zustellung im Posteingang muss noch bestätigt werden.

Wenn die Anmeldung scheitert, bleibt `MH_MAIL_MODE=local`; die App sendet dann keine echten Mails. Das Skript testet nur den Versand, nicht die Zustellung im Posteingang. Google kann App-Passwörter nach einer Änderung des Google-Kontopassworts widerrufen. Gmail ist hier nur ein Testabsender, noch keine freigegebene produktive Versanddomain.

Offizielle Google-Hinweise: https://support.google.com/accounts/answer/185833 und https://support.google.com/mail/answer/7104828

## Sicherheitsverhalten

- HttpOnly-Cookies mit SameSite=Lax; im Produktionsmodus zusätzlich Secure. Keine akzeptierten Bearer-Sitzungen oder Sitzungstokens für JavaScript. Alte Browser-Speichertokens sind ungültig; erneut anmelden.
- CSRF-Schutz für alle verändernden Browseraufrufe inklusive Login und Registrierung; authentifizierte Änderungen binden den CSRF-Wert zusätzlich an die Sitzung. Webhooks behalten ihren unabhängigen Signaturschutz. Produktions-CORS erlaubt nur die Frontend-Origin.
- Zufällige Sitzungen und Einmal-Links werden als SHA-256-Hash gespeichert. Sitzungen: maximal acht Stunden, 30 Minuten Inaktivität. Login und erfolgreicher zweiter Faktor rotieren sie; Logout und Passwortänderung widerrufen sie.
- Neue Passwort-Hashes: scrypt N=131072, r=8, p=1, eigener Salt. Alte Demo-Hashes werden nach erfolgreichem Login aktualisiert.
- Bestätigung 60 Minuten, Reset 30 Minuten, Einladung 48 Stunden. Neuanforderung ersetzt den vorherigen Link. Verbrauch erfolgt atomar. Bei Versandfehler kann eine neue E-Mail angefordert werden.
- TOTP-Geheimnisse sind mit Fernet verschlüsselt. Wiederherstellungscodes sind gehasht, zufällig und einmalig; bereits verwendete TOTP-Zeitschritte werden abgewiesen.
- Persistente Ratenlimits schützen Anmeldung, Wiederherstellung, Bestätigung, MFA und Einladungen. Die Clientadresse stammt direkt vom Server. Beim Betrieb hinter einem Proxy dessen vertrauenswürdige Adressen ausdrücklich konfigurieren.
- Neue Konten bleiben vor E-Mail-Bestätigung und Admin-MFA für Workspace und Billing gesperrt. Bestehende lokale Demo-Konten bleiben nutzbar. Es erfolgt keine pauschale Sperrmigration bestehender Konten. Im Produktionsmodus benötigen alle Admin-Konten MFA; eine etwaige Bestandskunden-E-Mail-Migration muss separat geplant werden.

Der Bestätigungslink wird direkt nach Registrierung erstellt und beim Öffnen der `/auth`-Seite automatisch geprüft. Ein erneuter Login versendet nicht erneut; bei abgelaufenem Link gibt es „Neue Bestätigung anfordern“. Der Link beweist nur Zugriff auf das Postfach, keine amtliche Identität oder Vertretungsmacht.

## Echter Mailversand und Produktion

Der Adapter unterstützt SMTP mit verpflichtendem STARTTLS und Zertifikatsprüfung. Ein tatsächlicher Mailanbieter ist noch nicht angeschlossen. Anbieter und gewünschte EU-Region müssen zum Betrieb passen; die App kann die Region eines SMTP-Servers nicht bestätigen.

Serverseitig konfigurieren: `MH_MAIL_MODE=smtp`, `MH_MAIL_FROM`, `MH_SMTP_HOST`, `MH_SMTP_PORT=587`, `MH_SMTP_USER`, `MH_SMTP_PASSWORD`. Absenderdomain beim Anbieter verifizieren sowie SPF/DKIM/DMARC einrichten.

Für Produktion zusätzlich `MH_ENV=production`, echte HTTPS-Origin in `MH_PUBLIC_URL`, `MH_DEMO_SWITCHER=0` und stabilen Fernet-Key in `MH_AUTH_ENCRYPTION_KEY`. Schlüssel im Secret-Manager speichern, nicht im Chat oder Repository. Lokal wird bei erster MFA-Einrichtung `backend/.auth.key` mit Berechtigung 600 erzeugt. Bei einem Umzug müssen verschlüsselte MFA-Daten und Schlüssel erhalten bleiben; Schlüsselverlust macht die gespeicherten Geheimnisse unlesbar.

Frische Produktionsdatenbank verwenden. Im Produktionsmodus werden keine Demo-Firmen oder Demo-Nutzer erzeugt. API und Frontend auf derselben Site hinter HTTPS betreiben, idealerweise API unter `/api`. Der Produktionsstart verlangt HTTPS, SMTP-Modus, Verschlüsselungsschlüssel und deaktivierten Demo-Schalter. Live-Stripe verlangt zusätzlich Produktionsmodus und alle bisherigen Billing-Freigaben.

Tatsächliche Unternehmensangaben, Vertrags-/Datenschutztexte, Hostingkonfiguration und externe Stripe-Zahlungstests fehlen weiterhin. Eine Gmail-Selbsttest-Mail wurde über SMTP akzeptiert; der Posteingang und der komplette Registrierungsversand sind noch zu bestätigen.

## Prüfung

```sh
python3 -m unittest backend/test_security.py backend/test_billing.py backend/test_stripe_setup.py backend/test_auth.py
cd frontend
npm run build
npm run test:seo
```

Die Auth-Tests prüfen Cookies, CSRF, Sicherheitsgates, Linkablauf und Wiederholung, MFA-Verschlüsselung, Replay-Schutz, Codes, Session-Widerruf, Ratenlimits, Einladungen und Onboarding in isolierten Datenbanken. `/auth` und `/onboarding` sind nicht indexierbar.

Referenzen: [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), [Forgot Password](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html), [Multifactor Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html).

## Zusätzliche Härtung (29.09.2026)

- API-Anfragen sind vor JSON-Parsing auf 1 MiB begrenzt, einschließlich gestreamter/chunked Bodies. Die unveränderten Rohbytes bleiben für die Stripe-Signaturprüfung erhalten. Briefing-, Firmen- und Kanaltexte haben zusätzliche Feld-/Anzahllimits.
- API-Antworten verwenden Frame-Schutz und Permissions-Policy zusätzlich zu no-store/nosniff/no-referrer. Öffentliche Swagger-/OpenAPI-Endpunkte sind im Produktionsmodus deaktiviert.
- Der statische Frontend-Server setzt eine CSP mit ausschließlich eigenen Skripten und Hashes für beim Start eingelesene Inline-Skripte. Inline-Styles bleiben für bestehende React-Stile erlaubt; Inline-Skripte ohne passenden Hash und eval sind nicht erlaubt. Frames, Plugins und fremde Formularziele sind gesperrt. Im Produktionsbetrieb mit `NODE_ENV=production` sind API-Verbindungen auf dieselbe Origin begrenzt; `/api` muss am Reverse Proxy korrekt geroutet werden. Externe API-Origins erfordern eine bewusste CSP-Anpassung.
- Kundenlöschung ist ausschließlich für echte Plattform-Admins ohne Demo-Rollenvorschau möglich, verlangt den exakten Firmennamen im Request und verwendet die bestehenden Session-/CSRF-Prüfungen. Sie läuft in einer Datenbanktransaktion, widerruft betroffene Zugänge und sperrt Firmen mit Abrechnungsdaten. Sie führt keine Stripe-Aufrufe aus. Gelöschte Seed-Firmen werden beim Neustart nicht neu angelegt. Lokale Mail-Outbox-Dateien und Backups werden nicht automatisch gelöscht.

Vor öffentlichem Betrieb bleiben HTTPS-/Proxy-Konfiguration, Request-Timeouts und Rate-Limits am Ingress, Wiederherstellungstests für verschlüsselte Backups, Überwachung/Alarmierung und regelmäßige externe Abhängigkeitsprüfungen erforderlich. Die lokale Regression ist kein Penetrationstest und belegt keine vollständige Produktionssicherheit.

## Sprache der automatischen E-Mails

Registrierung, Passwort-Wiederherstellung, Einladungen und Rechnungsbenachrichtigungen sind Deutsch/Englisch verfügbar. Die Oberfläche sendet die ausgewählte Browsersprache an die API. Registrierung und erfolgreiche Anmeldung speichern sie am Konto; der Checkout aktualisiert sie ebenfalls. Spätere Rechnungsnachrichten verwenden die gespeicherte Empfängersprache. Einladungen folgen der Sprache des Einladenden; die Einladungsannahme speichert die eigene Sprache des neuen Nutzers. Bestehende Konten starten mit Deutsch. Die Adminvorschau verwendet dieselben Vorlagen, ohne Nachrichten zu versenden. Bereits zugestellte E-Mails und die von Stripe erstellten Rechnungs-PDFs bleiben unverändert. Nach einem Backend-Update den Server neu starten, damit die additive Sprachspalte angelegt wird.

## E-Mail bei Anzeigenstatuswechsel

Alle bestätigten Nutzer derselben Firma, einschließlich Kundenrolle und Auslöser, erhalten bei einem tatsächlichen Anzeigenstatuswechsel eine einzelne Nachricht in ihrer gespeicherten Kontosprache (DE/EN). Die E-Mail nennt Anzeige, Firma, bisherigen/neuen Status und Akteur und führt zum Workspace. Unbestätigte Adressen, fremde Firmen und Demo-Rollenvorschauen sind ausgeschlossen. Statusnachrichten enthalten keine Entwurfsinhalte.

Statusänderung und Versandauftrag werden atomar gespeichert. Hintergrundversand und ein alle 30 Sekunden laufender Wiederholungsprozess nutzen denselben lokalen/SMTP-Adapter. Fehler werden mit zunehmendem Abstand erneut versucht; der Status bleibt gespeichert. Bereits erfolgreich versendete Aufträge werden nicht wiederholt, wobei ein Prozessabsturz nach SMTP-Annahme vor Speicherung der Bestätigung eine doppelte Zustellung verursachen kann. Nach dem Update Backend neu starten; die zusätzliche Warteschlangentabelle wird automatisch angelegt. Die neue Vorlage ist ohne Versand in der Adminvorschau verfügbar.

## Onboarding-Oberfläche (07.10.2026)

Der Ablauf bleibt sicherheits- und zahlungsgesteuert. Die vereinfachte erste Tarifansicht enthält keine Nachkäufe oder Verwaltung; das Firmenprofil startet mit drei Pflichtangaben und aufklappbaren optionalen Vorteilen/Ton. Gespeicherte Briefings können ohne erneute Erstellung fortgesetzt werden; Abschluss verlangt weiter das ausdrückliche Prüfen des Entwurfs. Keine Änderung an MFA, Cookies, CSRF, Einmal-Links oder Backend-Freigaben. Zusätzliche isolierte Komponententests: `cd frontend && npm run test:onboarding`. Reale Provider-/Registrierungs-Ende-zu-Ende-Abnahme bleibt offen.

Seit 08.10.2026 führt Stripe Checkout direkt zum Onboarding zurück. Ein offener Checkout erhält einen sichtbaren Warteschritt; bestehende Buchung kann fortgesetzt oder ausdrücklich verworfen werden. Bestätigter Serverstatus wechselt direkt zum Firmenprofil, zusätzlich gibt es einen Weiter-Knopf. Signierte Stripe-Webhooks bleiben Voraussetzung; Rückkehrparameter allein schalten nichts frei. Der konkrete vom Nutzer bezahlte Team-Testcheckout wurde nach Wiederstart des ausgefallenen Listeners durch Wiederzustellung seiner echten Ereignisse bestätigt; Firmenprofil im echten Browser sichtbar. Das ist eine Abnahme dieses Zahlungserfolgs, keine vollständige Registrierung-/MFA-/Provider-/Produktionsabnahme.

## Authenticator-QR-Code (07.10.2026)

Der QR-Code wird mit der gebündelten `qrcode`-Bibliothek vollständig im Browser als PNG-Datenbild erzeugt. Kein externer QR-/Bilddienst, kein Downloadlink, keine Ablage im Browser-Storage. Der Inhalt ist die geschützte Setup-Antwort von `/auth/mfa/setup`: richtig codierter Anbieter inklusive Website, Anmelde-E-Mail als Benutzerkonto, derselbe ausstehende Schlüssel, SHA1, sechs Stellen, 30 Sekunden. Seit 08.10.2026 lautet der Issuer lokal `MH · 127.0.0.1 (5181)`; Label-Präfix und issuer-Parameter sind identisch. Die Website kommt ausschließlich aus der serverseitigen `MH_PUBLIC_URL` (lokaler Standard `http://127.0.0.1:5181`), niemals aus einem fremden Request-Host. Nach Domain-Konfiguration beispielsweise `MH · jobs.mh.example`. Authenticator-Apps haben kein standardisiertes separates Website-Feld: Die Website steht daher im Anbieterfeld. Der lokale Port wird ohne zusätzlichen Doppelpunkt in Klammern angezeigt. Die volle Website-Adresse und Benutzerkonto stehen zusätzlich unter dem QR, auch bei manueller Einrichtung. Wiederverbindung verwendet dieselbe Kennzeichnung und behält den vorhandenen Schlüssel.

Client prüft Übereinstimmung mit Website/Konto/Schlüssel und unterstützte Parameter vor Anzeige. Bereits ausgegebene MH-Setup-Antworten ohne Website sowie ohne explizite Algorithmus-/Ziffern-/Periodenparameter bleiben mit denselben Standardwerten kompatibel. Bereits importierte App-Einträge werden nicht automatisch umbenannt; die aktualisierte Kennzeichnung erscheint bei erneutem Import nach berechtigter Wiederverbindung. Keine Änderung bestehender Kontoschlüssel oder Sicherheitsgates.

Ohne Kamera bleibt manuelle Eingabe aufklappbar; bei lokalem QR-Fehler wird sie geöffnet. MFA wird erst mit gültigem Code bestätigt. Falscher Code erhält die Einrichtung, erfolgreicher Code entfernt QR/Schlüssel aus der Ansicht und zeigt einmalig Wiederherstellungscodes. Es wurde kein echtes Konto oder Authenticator auf dem Nutzergerät eingerichtet. Zusatzprüfungen decodieren das tatsächlich erzeugte Bild und prüfen Fehlversuche, Recovery-Anzeige und Fallback. Browsernachweise enthalten ausschließlich ein fiktives Testkonto und einen öffentlich bekannten Testschlüssel.

Backend neu starten und Frontend neu laden für die expliziten URI-Parameter. Das QR-Bild selbst erfordert keinen neuen Backenddienst. URI-Format: [Google Authenticator Key URI Format](https://github.com/google/google-authenticator/wiki/Key-Uri-Format).

Die gleiche QR-Einrichtung gilt im Onboarding und nach Workspace-Anmeldung, einschließlich `/app?billing=start`. Vor der Anmeldung wird kein QR erzeugt; eingerichtete MFA verlangt den vorhandenen Code statt einer erneuten Einrichtung. Direkte Settings-/Social-Einstiege warten ebenfalls auf vollständige Kontosicherung. Fehlgeschlagene Statusprüfungen bleiben sichtbar und wiederholbar. Fünf zusätzliche Einstiegs-/Anmeldungstests ergänzen die Komponentenprüfung auf 23 Tests; Billing-Browsernachweise mit fiktivem Konto: `output/authenticator-qr-billing.jpg`, `output/authenticator-qr-billing-mobile.jpg`.

## Einheitliche Sicherheitskarte (07.10.2026)

Auch die Abfrage bei bereits eingerichtetem Authenticator nutzt jetzt dieselbe Karte und Gestaltung wie E-Mail-Bestätigung, QR-Einrichtung und Recovery-Sicherung. „Anmeldung bestätigen / Confirm your sign-in“ ersetzt die bisherigen generischen Überschriften. „Wiederherstellungscode verwenden“ wechselt explizit in eine Texteingabe ohne Begrenzung auf sechs Zeichen; Rückwechsel zur Authenticator-App bleibt möglich. Moduswechsel leert Eingabe und alte Fehler. Keine Änderung an MFA-Pflicht, Backend-Bestätigung oder Schlüsseln. Komponentenprüfung: aktuell 25 Tests; DE/EN-Prüfung rendert beide Modi. Browsernachweise mit fiktivem Konto: `output/authenticator-sign-in-desktop.jpg`, `output/authenticator-sign-in-mobile.jpg`.

## QR für ein bereits eingerichtetes Konto (07.10.2026)

In der normalen Zwei-Faktor-Abfrage „Authenticator-App verbinden“ wählen → unbenutzten MH-Wiederherstellungscode ausschließlich dort eingeben → QR in der Authenticator-App scannen → aktuellen sechsstelligen Code bestätigen. Der verwendete Recovery-Code ist verbraucht, die übrigen bleiben gültig. POST `/auth/mfa/reconnect` gibt denselben verschlüsselten Kontoschlüssel zurück, richtet keine neue MFA ein und erteilt keine Sitzungsfreigabe. Account-/CSRF-/E-Mail-Prüfung und Rate-Limit bleiben erforderlich. Ohne Recovery-Code ist dieser Weg nicht verfügbar. Aktueller Komponentenstand: 29 Tests. Backend neu starten und Frontend neu laden für die neue Route.

## Sechsstellige Code-Eingabe (08.10.2026)

Einrichtung, normale Anmeldung und QR-Wiederverbindung verwenden sechs einzelne, in DE/EN beschriftete Ziffernfelder. Fokus rückt bei Eingabe weiter; Rücktaste korrigiert aktuelle/vorherige Ziffer, Pfeiltasten/Home/End navigieren. Vollständiges Einfügen und One-Time-Code-Autofill verteilen sechs Ziffern, einschließlich führender Null. Bestätigung bleibt ausdrücklich erforderlich; unvollständige Codes werden auch im Submit-Handler blockiert. Recovery-Codes bleiben in einem eigenen längeren Textfeld. Der QR bleibt während der laufenden Einrichtung bis zur Bestätigung sichtbar. Er enthält den MFA-Schlüssel und wird deshalb nicht in einer lediglich per Passwort authentifizierten normalen Code-Abfrage angezeigt; Wiederöffnung verlangt Recovery-Prüfung. Keine Kontoschlüssel oder Backendregeln geändert.

## Geprüfte Kontowiederherstellung bei Verlust aller Faktoren (08.10.2026)

1. In der MFA-Abfrage „Authenticator und Wiederherstellungscodes verloren?“ oder `/auth?action=recover` öffnen. E-Mail anfordern; unbekannte/ungeeignete Konten erhalten dieselbe öffentliche Antwort, auch bei SMTP-Fehler. Anforderung 3 pro Stunde pro IP/E-Mail, weitere IP-Grenze. Keine Kontoveränderung oder Sperre durch Anfrage.
2. Einmal-Link aus der Mail innerhalb einer Stunde öffnen und ausdrücklich bestätigen (kein automatischer Verbrauch durch bloßes Öffnen). Zugriff aufs bestehende bestätigte Postfach ist Pflicht. Prüfungsnummer mit dem eigenen MH-Betreiber abstimmen. Neue öffentliche Anfragen überschreiben keine bereits bestätigte/freigegebene Anfrage. Die gesamte Anfrage gilt sieben Tage.
3. Platform Admin → System → Kontowiederherstellung: unabhängig bekannte Firmen-/Kontaktunterlagen nutzen, z. B. Rückruf über eine bereits vor der Anfrage bekannte Kontaktmöglichkeit und Abgleich mit bestehenden Firmenunterlagen. Keine neuen, vom Anfragenden gelieferten Kontakte oder öffentlich sichtbaren Firmendaten allein als Identitätsbeweis akzeptieren. Diese Prüfung ist eine menschliche Betreiberaufgabe; MH bestätigt keine amtliche Identität automatisch. Keine Ausweisdateien/Geheimnisse im Review-Feld speichern, nur die Vorgangsreferenz. Bestätigtes Postfach allein reicht nicht.
4. Exakte Konto-E-Mail erneut eingeben, Prüfungsreferenz und ausdrückliche Bestätigung erfassen, Entscheidung mit neuem TOTP-Code des prüfenden Platform Admin bestätigen. Prüfer braucht eingerichtete MFA und MFA-bestätigte Session; bei lokalem Demo-Bestand kann er seinen eigenen Authenticator im Review-Bereich einrichten. Selbstfreigabe, Firmenrollen und Demo-Rollenvorschauen sind ausgeschlossen. Ablehnung braucht Referenz/E-Mail/TOTP, keine positive Inhaberschaftsbestätigung. Gespeichert werden Status, Zeiten, Prüfer und Referenz.
5. Freigabe sendet einen einmaligen 30-Minuten-Link über den vorhandenen Mailadapter. Bei Versandfehler bleibt die Freigabe sichtbar; erneuter Versand mit neuer TOTP-Bestätigung ersetzt den alten Link. Alte Session/Passwort/MFA bleiben bis tatsächlichem Verbrauch unverändert. Die Mail informiert über die bevorstehende Änderung; unerwartete Anfrage auf der verlinkten Seite abbrechen.
6. Kontoinhaber setzt selbst ein neues Passwort mit Bestätigung. Verbrauch atomar: alle Sitzungen und Einmal-Links widerrufen, alter MFA-Schlüssel/Pending-Schlüssel und Recovery-Codes ungültig, `mfa_recovery_required=1`. Kein automatischer Login. Neu anmelden → neuen QR scannen → sechsstelligen Code bestätigen → zehn neue Recovery-Codes sichern. MFA-Gate gilt bis Bestätigung auch für User/Kunde; dann wird das Recovery-Pflichtflag entfernt. Firmen-/Billing-/Abo-Daten werden nicht geändert.

Die Request-/Reset-Links sind gehasht, zweckgebunden und no-store. Anfrage ist zusätzlich an Konto-E-Mail, Passwort-Hash und MFA-Schlüssel gebunden; Änderungen dieser Faktoren machen alte Freigaben ungültig. Expiry, Replay, falscher Zweck, Ablehnung oder Abbruch sperren den Verbrauch. Gleichzeitige Verbräuche werden durch SQLite-Transaktionen serialisiert. Prüfungsdaten verbleiben in der privaten Datenbank; Firmenlöschung entfernt die zugehörigen Anfragen. Eine regelmäßige Audit-Aufbewahrungs-/Löschfrist muss vor öffentlichem Betrieb festgelegt werden.

### Wenn alle Platform Admins ausgesperrt sind

Der vertrauenswürdige Betreiber mit Zugriff auf den MH-Host kann **nach derselben unabhängigen Inhaberschaftsprüfung** die lokale Review-Freigabe nutzen. Kein öffentlicher Betreiber-Endpoint und kein Direktreset per CLI. Die E-Mail-Anfrage muss vorher bestätigt sein. Der Helfer lädt vorhandene private Mailkonfiguration ohne Ausgabe von Zugangsdaten. Nur auf dem autorisierten Host ausführen:

```sh
python3 -m backend.account_recovery list
python3 -m backend.account_recovery approve --case-id CASE_ID --reference VERIFIED_CASE_REFERENCE
python3 -m backend.account_recovery reject --case-id CASE_ID --reference CASE_REFERENCE
```

Der Dialog verlangt die bestätigte Konto-E-Mail und explizit `VERIFIED`. Er protokolliert den Host-Operator und die Referenz und sendet nur den einmaligen Link; das Passwort/MFA setzt weiterhin der Kontoinhaber selbst. Hostzugriff ist die Vertrauensgrenze dieser Notfallfunktion; Datei-/SSH-/Secret-Zugriff streng begrenzen. Ohne Zugriff auf das vorhandene Postfach bleibt diese Wiederherstellung gesperrt; keine Ersetzung der registrierten E-Mail über diesen Ablauf.

Neue Routen: `/auth/recovery/request`, `/verify`, `/cancel`, `/reset`; `/admin/account-recoveries` und `/{id}/review`. Backend neu starten für additive Schema-Erweiterung und Routen. Tests ausschließlich in isolierten Datenbanken/Komponenten und fiktiver Browser-API; keine echte Recovery-Mail oder Kontozurücksetzung zur Abnahme ausgelöst. Grundlage: [OWASP MFA Recovery](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html#resetting-mfa).

## Briefing speichern und Onboarding später fortsetzen (08.10.2026)

„Briefing speichern & zum Dashboard“ speichert zuerst die eigene Kampagne und dann über `/onboarding/defer` die firmengebundene Verschiebung. Voraussetzung bleiben abgesichertes Konto, Firmen-Admin ohne Demoansicht, bezahltes aktives Abo und abgeschlossenes Firmenprofil. Ein fehlgeschlagenes Speichern oder Verschieben navigiert nicht; Wiederholen nutzt denselben bereits gespeicherten Entwurf. Dieser Weg verbraucht keine Tokens und markiert weder Onboarding noch Kampagne als geprüft. Neue `/app`-Besuche akzeptieren den gespeicherten Aufschub; das Briefing bleibt unter Kampagnen/Content Studio und `/onboarding` fortsetzbar. `/onboarding/complete` verlangt unverändert den geprüften Entwurf.

Ohne OpenAI-Zugang bietet die lokale Stripe-Testumgebung ausdrücklich Testpakete aus Vorlagen für 50 Test-Tokens; Beschreibung, Button und gespeichertes Studio-Ergebnis kennzeichnen sie. Keine Datenübermittlung an OpenAI und keine simulierte KI-Verbrauchsmessung. Echter KI-Weg bleibt separat und verlangt weiterhin einen Schlüssel. Produktions-/Live-Konten sind von Testpaketen ausgeschlossen.

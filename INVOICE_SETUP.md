# E-Mail-Bestätigung und Rechnungsversand

Stand: 28. September 2026. Dies ist die technische Betriebsanleitung, keine steuerliche Freigabe.

## Implementierter Ablauf

1. Nach **Registrierung** erstellt MH einen auf 60 Minuten begrenzten Einmallink und sendet ihn an die angegebene Adresse. Beim Öffnen wird der Link automatisch per `/auth/verify-email` geprüft und verbraucht. Er bestätigt nur die Kontrolle über das E-Mail-Postfach, nicht die bürgerliche Identität oder Vertretungsberechtigung. Nach jeder späteren Anmeldung wird kein neuer Bestätigungslink gesendet.
2. Erst nach E-Mail-Bestätigung und Admin-MFA kann der neue Firmen-Admin einen Stripe Checkout starten. Die Person bestätigt, dass sie für eine EU-Firma bucht und eine PDF-Rechnung per E-Mail akzeptiert. Kartendaten gehen ausschließlich an Stripe. Checkout ist auf Kreditkarte, vollständige Rechnungsadresse, Steuerberechnung und Erfassung der USt-ID eingestellt.
3. Nur signierte Stripe-Webhooks in der passenden Test-/Live-Umgebung buchen Zahlungen und Tokens. Ein Browser-Redirect allein gewährt nichts. Abos erhalten Tokens bei `invoice.paid`; einmalige Tokenpakete bei bezahltem Checkout mit bezahlter Stripe-Rechnung. Doppelte Webhooks buchen nicht erneut.
4. Nach einer bestätigten bezahlten Rechnung legt MH einen Versandauftrag an und sendet dem bestätigten Firmen-Admin eine E-Mail mit einem HTTPS-Link auf **das von Stripe erzeugte Rechnungs-PDF**. Der Link ist kein eigenes Rechnungsdokument von MH. Fehlt das PDF oder scheitert SMTP, antwortet der Webhook mit Fehler und Stripe kann erneut zustellen. Die Tokenbuchung bleibt unabhängig davon idempotent. Bei Prozessabbruch unmittelbar nach erfolgreichem SMTP-Versand, aber vor lokaler Versandmarkierung, ist eine doppelte E-Mail möglich; die Rechnung selbst bleibt dieselbe.
5. Die Stripe-Kundenportal-Funktion `invoice_history` ermöglicht zusätzlich den Abruf der Rechnung.

Im lokalen Entwicklungsmodus landen Nachrichten als private `.eml`-Dateien in `backend/mail_outbox`. Es werden keine echten E-Mails versendet. Stripe-Testmodus führt keine echte Abbuchung aus.
Im Stripe-Testkonto und im Code sind jetzt die Monats- und Jahrespreise 19/69/149 € bzw. 190/690/1.490 € netto hinterlegt, außerdem Tokenpakete zu 12/39/89 €. Eine vollständige Testzahlung und rechtlich geprüfte Rechnung stehen noch aus. Bei längerem SMTP-Ausfall müssen ausstehende Webhook-Ereignisse nach Wiederherstellung gegebenenfalls erneut zugestellt werden.

## Vor dem ersten echten Verkauf nötig

### 1. Mailanbieter anschließen

Für lokale Tests ist das persönliche Gmail-Konto `Michel.herszak@gmail.com` vorbereitet; die verdeckte App-Passwort-Eingabe und Selbsttest-Mail laufen über `python3 -m backend.gmail_test connect`. Details in `AUTH_SETUP.md`. Bis zum erfolgreichen Test bleibt der Versand lokal. Für den späteren Firmenbetrieb einen passenden geschäftlichen Absender bestimmen.

Einen SMTP-Anbieter wählen, Absenderdomain nachweisen und SPF, DKIM und DMARC setzen. Serverseitig `MH_MAIL_MODE=smtp`, `MH_MAIL_FROM`, `MH_SMTP_HOST`, `MH_SMTP_PORT`, `MH_SMTP_USER` und `MH_SMTP_PASSWORD` konfigurieren. Zugangsdaten nie in Chat, Frontend oder Repository speichern. Eine Testregistrierung mit eigener Adresse durchführen und Zustellung, Spamordner, Linkablauf und Einmalverwendung prüfen.

### 2. Aussteller und Steuern in Stripe vollständig einrichten

Im Stripe-Konto die **tatsächliche** ausstellende deutsche Firma und ladungsfähige Anschrift, Rechnungs-/Supportkontakt, zutreffende Steuernummer **oder** USt-ID als auf Rechnungen sichtbare Standard-Steuerkennung, Rechnungsnummernformat und Logo/Branding hinterlegen. Stripe Tax benötigt die echte Niederlassungsadresse, passende Produktsteuerkategorie und nur tatsächlich vorhandene Steuerregistrierungen. Keine fremden oder erfundenen Daten eintragen. Für Auslandskunden die B2B-USt-ID und die vom Steuerberater bestätigte Steuerbehandlung einschließlich Reverse Charge prüfen.

Eine **echte Stripe-Testrechnung als PDF** prüfen: vollständiger Name und Anschrift von Aussteller und Empfänger, Steuerkennung des Ausstellers, Ausstellungsdatum, eindeutige fortlaufende Rechnungsnummer, Art und Umfang der Leistung, Leistungszeitraum, Entgelt, Steuersatz und Steuerbetrag bzw. erforderlicher Hinweis auf Steuerbefreiung/Steuerschuldnerschaft. Bei grenzüberschreitenden B2B-Leistungen können weitere Pflichtangaben gelten. Die Anwendung kann fehlende Stammdaten auf einem bereits finalisierten Stripe-PDF nicht nachträglich reparieren. Stripe dokumentiert, dass die Steuer-IDs nach Finalisierung nicht mehr geändert werden können.

### 3. Deutsche E-Rechnung beachten

Für **inländische B2B-Umsätze** ist ein einfaches PDF keine strukturierte E-Rechnung. Nach der BMF-FAQ kann eine sonstige Rechnung, etwa ein PDF per E-Mail, bis Ende 2026 mit Zustimmung des Empfängers verwendet werden. Bei Vorjahresumsatz bis 800.000 € kann die Übergangsfrist bis Ende 2027 gelten. Danach ist für betroffene inländische B2B-Umsätze ein EN-16931-konformes Format (z. B. XRechnung oder ZUGFeRD mit strukturierten Daten) erforderlich. Die jetzige Stripe-PDF-Strecke erzeugt **kein** solches Format. Vor Ablauf der jeweils zutreffenden Übergangsfrist einen E-Rechnungsdienst oder eine entsprechende Integration verbindlich wählen und prüfen. Auslandsfälle gesondert steuerlich beurteilen.

### 4. Stripe-Betrieb und Freigabe

Stripe Tax, EU-Radar-Regeln und Webhooks nach `BILLING_SETUP.md` vollständig konfigurieren. In Stripe automatische E-Mails für bezahlte Rechnungen/erfolgreiche Zahlungen mit dem MH-Mailversand abstimmen, damit Kunden keine doppelten Nachrichten bekommen. Der Betreiber muss prüfen, welches Konto als Rechnungsaussteller auf dem PDF erscheint. Ein Testkauf mit Abo, Verlängerung, Tokenpaket, 3D Secure, fehlgeschlagener Zahlung, Storno, Erstattung und EU-Auslandsadresse ist nötig. Bei Erstattung muss die Rechnungskorrektur bzw. Gutschrift steuerlich korrekt abgewickelt werden; das erledigt der jetzige Code nicht automatisch.

Erst nach dieser Prüfung `MH_INVOICE_READY=1` in der **Live-Serverkonfiguration** setzen. Das Flag sperrt Live-Checkout bis zur bewussten Freigabe, ersetzt aber weder die Prüfung der Rechnung noch die E-Rechnungsintegration. `MH_STRIPE_LIVE_ENABLED`, `MH_STRIPE_TAX_READY`, `MH_EU_RADAR_CONFIRMED` und die übrigen Live-Gates bleiben zusätzlich erforderlich. Weil Firmenanschrift, Steuerkennung und SMTP-Anbieter noch fehlen, ist der echte Workflow derzeit **nicht live**.

## Rechts- und Anbieterquellen

- § 14 UStG, Pflichtangaben und E-Rechnung: https://www.gesetze-im-internet.de/ustg_1980/__14.html
- § 14a UStG, ergänzende Hinweise für besondere Fälle: https://www.gesetze-im-internet.de/ustg_1980/__14a.html
- BMF-FAQ zur E-Rechnung und Übergangsfristen (Stand März 2026): https://www.bundesfinanzministerium.de/Content/DE/FAQ/e-rechnung.html
- Stripe, Aussteller- und Kunden-Steuer-IDs auf Rechnungen: https://docs.stripe.com/tax/invoicing/tax-ids
- Stripe, Rechnungen und Abo-Rechnungszyklen: https://docs.stripe.com/invoicing/overview

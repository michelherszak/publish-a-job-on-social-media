# MH: Stripe-Zahlungen für EU-Unternehmen

## Implementierter Ablauf

Landingpage → Tarifplanung → `/register` → Firmenkonto → `/onboarding` → E-Mail-Bestätigung und Admin-MFA → Stripe Checkout → bestätigter Webhook → Abo und Monatsguthaben. Bestehende Firmen-Admins erreichen „Abo & Tokens“ über das Menü. Plattform-Admins und Demo-Rollenvorschauen dürfen keine Zahlungen starten.

Der gemeinsame Katalog in `pricing_catalog.json` enthält Starter 19 EUR monatlich oder 190 EUR jährlich / 250 Tokens pro Monat / 3 Bearbeiter, Team 69 oder 690 EUR / 1.500 Tokens / 10 Bearbeiter sowie Scale 149 oder 1.490 EUR / 4.000 Tokens / 25 Bearbeiter. Jahresabos werden im Voraus bezahlt; Inklusivtokens erneuern sich monatlich innerhalb der bezahlten Laufzeit. Einmalkäufe: 250 Tokens für 12 EUR, 1.000 für 39 EUR, 2.500 für 89 EUR. Preise sind netto in EUR. Stripe Tax berechnet die tatsächlich anfallende Steuer im Checkout; USt-IDs werden dort gesammelt. Die Anwendung entscheidet nicht selbst über Reverse Charge.

Jeder neue Kampagnenentwurf kostet für verwaltete bezahlte Konten 50 Tokens; bezahlte Entwürfe verwenden die zentral konfigurierte OpenAI-Anbindung; Demo-Entwürfe sind lokale Vorlagen. Der Nutzer bestätigt den Verbrauch vorab. Technische Fehler rollen den Verbrauch zurück. Ein wiederholter Aufruf mit derselben `Idempotency-Key` belastet nicht erneut. Die bisherigen Demo-Konten ohne Billingkonto bleiben kostenlos. Registrierung und begonnene Buchung erzeugen ein verwaltetes Konto; ohne bezahlten Zeitraum sind Kampagnenänderungen gesperrt, Lesen und Exporte bleiben möglich.

## Sprache von Checkout und Kundenportal

Stripe Checkout und Kundenportal übernehmen DE/EN aus der Browsersprache, die die Oberfläche über `Accept-Language` an die API übermittelt. Auch der EU-/Nettopreis-Hinweis im Checkout und die Portalüberschrift werden entsprechend übersetzt. Sprache ändert weder Beträge noch Steuerberechnung oder Webhook-Entitlements. Lokal durch simulierte Anbieteraufrufe geprüft; echte Stripe-Abnahme bleibt offen. Backend nach diesem Update neu starten.

## Rechnungszustellung

Nach bezahlter und geprüfter Abo- oder Tokenrechnung verschickt MH eine Nachricht mit Link zum Stripe-Rechnungs-PDF an den bestätigten Firmen-Admin. Der Versandauftrag wird nach einem Mailfehler per Webhook-Wiederholung erneut versucht; Buchungen sind weiterhin idempotent. Die Zustimmung zum PDF-Versand wird beim Checkout eingeholt. Live-Checkout erfordert zusätzlich `MH_INVOICE_READY=1`; dieses Flag darf erst nach Prüfung echter Ausstellerdaten, Steuerkennung, einer vollständigen Stripe-Testrechnung, Mailzustellung und E-Rechnungsstrategie gesetzt werden. Die vollständige Checkliste und deutsche Übergangsfristen stehen in `INVOICE_SETUP.md`.

## Aktueller Teststand

Stripe ist im Testmodus verbunden. Die neun Stripe-Testprodukte/-preise sind angelegt; Testschlüssel, Preis-IDs und CLI-Webhook-Secret liegen ausschließlich in der privaten, ignorierten Datei `backend/.env.local` (Berechtigung 600). Der lokale Server lädt diese Konfiguration. Ein signiertes `customer.updated`-Testereignis wurde erfolgreich zugestellt (HTTP 200). Dafür wurde ein Testkunde namens „MH webhook connection test“ angelegt, ohne Zahlung oder Abo.

**08.10.2026:** Der Nutzer hat einen Team-Testcheckout abgeschlossen. Stripe-Status lesend geprüft: `complete`, `paid`, `livemode=false`. Der lokale Listener war beendet; MH blieb deshalb beim Tarifschritt. Listener wieder gestartet, privates Signing-Secret geladen und die beiden genau dieser bestehenden Buchung zugeordneten Ereignisse `checkout.session.completed` und `invoice.paid` über die offizielle Stripe-CLI erneut zugestellt. Beide signierten Zustellungen erhielten HTTP 200. MH zeigt aktives Team-Abo und 1.500 Tokens mit einer Rechnungs-Gutschrift; im echten Browser ist „Choose Plan“ abgeschlossen und das Firmenprofil offen. Kein neuer Kauf, keine zweite Zahlung, kein gefälschtes Event und kein direkter Datenbank-Entitlement-Write. Der ursprünglich dokumentierte fehlende vollständige Testcheckout ist damit für diesen Erfolgsfall erledigt.

Die frühere Tax-`pending`-Angabe beschreibt den damaligen Einrichtungsstand. API-Konfiguration `ready` allein bestätigt weiterhin keine vollständige Tax-/Radar-Abnahme. EU-/Nicht-EU-Fälle, Ablehnung, 3D Secure, Verlängerung, Erstattung und Produktionsrechnungen bleiben separat zu prüfen. Eine öffentliche Domain ist für den lokalen Test nicht nötig; Live-Zahlungen sind nicht freigegeben.

Python verwendet für Stripe HTTPS zusätzlich den vertrauenswürdigen `certifi`-CA-Bestand, da die lokale Python-Installation ohne diesen Zusatz die Zertifikatskette nicht prüfen konnte. Hostname- und Zertifikatsprüfung bleiben aktiviert. Die Backend-Tests sowie Frontend-Build und SEO-Prüfung wurden nach der Katalogumstellung erfolgreich ausgeführt.

Der CLI-Listener muss während des Tests weiterlaufen. `./start.sh` startet ihn mit vorhandener privater Stripe-Testkonfiguration jetzt vor Backend/Frontend, wartet auf die private Bereitschaftsmarkierung und lädt erst danach das gespeicherte Signing-Secret. Fehlende CLI/Bereitschaft oder späterer Listener-Abbruch beendet den gemeinsamen Start mit klarer Meldung. Ctrl+C beendet alle drei Dienste. Bei separatem Start weiterhin zuerst `python3 -m backend.stripe_test listen`, danach `python3 -m backend.stripe_test start`; ohne Listener kann eine bezahlte Buchung lokal unbestätigt bleiben. Den früher im Chat eingegebenen Testschlüssel in Stripe rotieren, den neuen ausschließlich lokal speichern. Es sind weiterhin keinerlei Live-Zahlungen aktiviert.

Checkout aus dem Onboarding erhält `/onboarding?billing=success` beziehungsweise `billing=cancelled` als feste Rückkehr. Alte `/app?billing=...`-Rückkehrlinks behalten diese zwei zulässigen Statuswerte beim Weiterleiten. `/billing/status` liefert ausschließlich den eigenen offenen Checkout (Tarif, Ablauf, geprüfte Stripe-URL), keine fremden Buchungen. Die Oberfläche zeigt einen Warteschritt mit vorhandener Buchung, Wiederaufnahme und ausdrücklichem Verwerfen; keine erneute Tarifbuchung nach einer Rückkehr. Sichtbare Seiten prüfen weiter automatisch, auch nach einer Minute und beim Fensterfokus. Erst der aktive, webhook-bestätigte Serverstatus führt unmittelbar zum Firmenprofil; ein Weiter-Knopf bietet denselben geprüften Weg bei verzögerter Ansicht. Browser-Erfolg selbst erteilt weiterhin keine Berechtigungen.

Bei einem verpassten lokalen Ereignis kann ein autorisierter Betreiber genau die echten zugehörigen Testereignisse mit `stripe events resend EVENT_ID` erneut an den laufenden Listener zustellen lassen. Keine generischen `stripe trigger`-Ereignisse zur Freischaltung realer Konten und keine neue Buchung als Reparatur. Event- und Rechnungs-Deduplizierung bleibt erhalten. Offizielle CLI: https://github.com/stripe/stripe-cli/wiki/events-resend-command.

## Schneller lokaler Teststart

Die offizielle Stripe CLI ist auf diesem Mac installiert. Alle Befehle aus `/Users/michelherszak/Programming/Python/MH` ausführen:

1. `stripe login`: im Browser das eigene Testkonto bzw. dieselbe Sandbox auswählen.
2. `python3 -m backend.stripe_test setup`: den Secret-Key dieser Testumgebung unsichtbar im Terminal eingeben. Der Assistent erstellt die neun passenden Testprodukte/-preise automatisch und verwendet vorhandene Preise bei erneutem Aufruf. Live-Schlüssel werden abgewiesen. Die Datei `backend/.env.local` wird atomar mit Berechtigung `600` gespeichert. API-Schlüssel niemals im Chat senden.
3. Bei bereits bestehender Testkonfiguration aktualisiert `python3 -m backend.stripe_test sync-prices` nur die neun Testpreise. `python3 -m backend.stripe_test verify` prüft Preise und Stripe-Tax-Status nur lesend. In einem zweiten Terminal `python3 -m backend.stripe_test listen` starten. Der Befehl leitet nur die benötigten Ereignisse weiter und speichert das wechselnde Webhook-Secret privat, ohne es auszugeben. Danach das Backend neu starten. Listener während des Tests offen lassen.
4. Im Stripe-Dashboard Stripe Tax mit den tatsächlichen Unternehmensdaten konfigurieren (siehe unten). Im Testmodus fließt kein echtes Geld.
5. `python3 -m backend.stripe_test start`: Backend starten; es lädt die lokale Konfiguration ohne Shell-Ausführung. Drittes Terminal: `cd frontend` und `npm run dev -- --host 127.0.0.1 --port 5181 --strictPort`, sofern die Website noch nicht läuft.
6. `http://127.0.0.1:5181/register?plan=starter` öffnen → neues Testfirmenkonto → E-Mail bestätigen und Authenticator einrichten (siehe `AUTH_SETUP.md`) → Starter buchen → EU-Rechnungsadresse und Testkarte `4242 4242 4242 4242`, zukünftiges Ablaufdatum, beliebige dreistellige CVC.
7. Nach der Rückkehr muss „Abo & Tokens“ ein aktives Starter-Abo und **250 Inklusivtokens** zeigen. Ein bestätigter Entwurf reduziert auf **200**. Die Erfolgsseite allein genügt nicht.

Ein Testschlüssel verbindet den Assistenten tatsächlich mit Stripe und legt dort ausschließlich Testprodukte/-preise an. Ohne diesen Zugang ist noch kein echter Zahlungsversuch möglich. Steuerkategorie und EU-Radar-Regeln bleiben kontospezifische Dashboard-Einstellungen; der Assistent bestätigt sie nicht automatisch.

## 1. Stripe-Testumgebung einrichten

1. Im eigenen Stripe-Konto die Testumgebung wählen. Sechs Preise anlegen: die drei Abopreise mit monatlicher Wiederholung und die drei Tokenpakete als Einmalkäufe. Währung EUR; Steuerverhalten **exclusive**; Mengen jeweils 1; keine Rabatte oder Testzeiträume. Der Server prüft Betrag, Währung und Wiederholungsintervall gegen seinen Katalog.
2. Stripe Tax im Konto für das tatsächliche Unternehmen konfigurieren: Geschäftsadresse, zutreffende Produktsteuerkategorie und tatsächliche Steuerregistrierungen. Die App verwendet `automatic_tax` und Tax-ID-Erfassung. Keine erfundenen Registrierungen eintragen.
3. `backend/.env.example` nach `backend/.env.local` kopieren, Dateiberechtigung `600` setzen. Test-Secret-Key (`sk_test_...`) und die neun `price_...`-IDs dort eintragen. Secrets bleiben ausschließlich auf dem Server.
4. Für lokale Webhooks die offizielle Stripe CLI über `python3 -m backend.stripe_test listen` nutzen. Der Helfer wählt die von MH unterstützten Ereignisse, leitet sie an `http://127.0.0.1:8011/billing/webhook` weiter und speichert das CLI-Webhook-Secret privat. Nicht mit einem Dashboard-Endpoint-Secret verwechseln. API und späterer Dashboard-Webhook sind auf **2026-08-26.dahlia** auszurichten.
5. Backend aus dem Projektverzeichnis mit exportierten Variablen starten:

```sh
set -a
source backend/.env.local
set +a
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8011
```

Die Konfiguration nicht in Terminalausgaben drucken. `/billing/config` liefert nur öffentliche Produktdaten, Länder, Test-/Live-Modus und Verfügbarkeit, niemals Schlüssel.

## 2. EU-Beschränkung auch in Stripe aktivieren

Die App akzeptiert nur die 27 EU-Ländercodes für Unternehmenssitz und Rechnungsland. Großbritannien, Schweiz, Norwegen und andere Nicht-EU-Länder werden abgewiesen. Die tatsächliche Stripe-Rechnungsadresse wird bei der Zahlungsbestätigung und auf jeder Abo-Rechnung erneut geprüft. Bei Abweichung wird kein Guthaben freigegeben und das Konto zur Prüfung gesperrt.

**Wichtig:** Gehostetes Stripe Checkout kann die Rechnungsland-Auswahl nicht über `billing_address_collection` auf die EU begrenzen. Die kundenseitige Auswahl kann dort verändert werden. Damit eine Nicht-EU-Adresse bereits vor einer erfolgreichen Abbuchung blockiert wird, müssen im verwendeten Stripe-Konto geeignete **Radar-Blockregeln** eingerichtet und mit Erst- und Folgezahlungen getestet sein (gegebenenfalls Radar for Fraud Teams erforderlich):

```text
Block if :billing_address_country: not in ('AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','GR','HU','IE','IT','LV','LT','LU','MT','NL','PL','PT','RO','SK','SI','ES','SE')
Block if is_missing(:billing_address_country:)
```

Syntax und Verfügbarkeit im eigenen Stripe-Dashboard prüfen; beide Regeln auf tatsächliche Zahlungsversuche und Verlängerungen testen. Das ist eine Einschränkung der **Rechnungsadresse**, nicht von Nationalität, Aufenthaltsort oder Kartenausgabeland. Kundendaten können ohne eigene Identitätsprüfung nicht als Unternehmensnachweis garantiert werden. Das Kundenportal erlaubt keine Rechnungsadressänderungen; solche Änderungen betreut der Betreiber.

Fehlerhafte Nicht-EU-Zahlungen, Erstattungen und Disputes sperren die Tokenverwendung. Der Betreiber prüft diese in Stripe, erstattet gegebenenfalls und beendet ein unzulässiges Abo. Diese externen Finanzaktionen werden nicht automatisch ausgeführt. Vor Aufhebung einer Sperre muss der Tokenbestand nach einer Erstattung nachvollziehbar korrigiert werden; nicht einfach das Hold-Feld löschen.

## 3. Webhook-Ereignisse

- `checkout.session.completed`, `checkout.session.async_payment_succeeded`
- `invoice.paid`, `invoice.payment_failed`
- `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`
- `customer.updated`
- `charge.refunded`, `charge.dispute.created`

Nur signierte Ereignisse (maximal 5 Minuten Zeitabweichung) in der passenden Test-/Live-Umgebung werden verarbeitet. Aktuelle Objekte werden nochmals aus Stripe gelesen. Ereignisse und Gutschriften sind separat dedupliziert. Eine erfolgreiche Browser-Weiterleitung erteilt nie Berechtigungen. Fehlgeschlagene Verarbeitung ergibt einen Fehlerstatus, damit Stripe erneut zustellt.

Die erste Tokenzuteilung erfolgt ausschließlich nach einer bezahlten Abo-Rechnung. Monatliche Abos erneuern sie nach jeder bezahlten Monatsrechnung; bei bezahlten Jahresabos erneuert die Anwendung sie an jedem Monatsstichtag innerhalb der Jahreslaufzeit. Ältere oder mehrfach zugestellte Rechnungen füllen nicht erneut auf. Gekaufte Tokens bleiben als getrenntes Guthaben bestehen, sind aber nur während eines aktiven bezahlten Abos nutzbar. Verbrauch verwendet zuerst Inklusivtokens. Es gibt kein automatisches Nachladen. Buchungen werden je Firma atomar ausgeführt.

## 4. Prüfung vor dem Livebetrieb

```sh
python3 -m unittest backend/test_security.py backend/test_billing.py backend/test_stripe_setup.py backend/test_auth.py
cd frontend
npm run build
npm run test:seo
```

Im Stripe-Testmodus anschließend eine vollständige Registrierung und Zahlung mit offiziellen Testkarten prüfen: Erfolg, Ablehnung, 3D Secure, abgebrochener Checkout, doppelte Webhook-Zustellung, Aboverlängerung, Zahlungsverzug, Kündigung, Tokenpaket, EU-/Nicht-EU-Rechnungsadresse und Erstattung. Nicht nur die Erfolgsseite ansehen: das Konto muss den Webhook-Status und genau eine Tokenbuchung zeigen. Abgebrochene Sessions können in „Abo & Tokens“ ausdrücklich verworfen werden; das beendet kein bezahltes Abo.

## 5. Live-Konfiguration

- `MH_ENV=production` und sichere Auth-/SMTP-Konfiguration gemäß `AUTH_SETUP.md` setzen.
- Öffentliche HTTPS-Domain und Server für `/billing/webhook` bereitstellen; `MH_PUBLIC_URL` auf die Frontend-Origin setzen. Im Frontend optional `VITE_API_URL` setzen; ohne Einstellung nutzt ein öffentliches Deployment `/api` und benötigt dafür einen Reverse Proxy zum Backend. CORS verwendet genau `MH_PUBLIC_URL`.
- Echte Preise, Live-Schlüssel und dazugehöriges Live-Webhook-Secret konfigurieren. Test- und Live-Datenbanken getrennt betreiben; dieselbe Datenbank darf nicht zwischen beiden Stripe-Umgebungen wechseln.
- `MH_DEMO_SWITCHER=0` setzen. Live-Datenbank ohne lokale Demo-Konten bereitstellen; die lokale Seed-/Demo-Installation ist kein fertiges produktives Hosting.
- Nach tatsächlich abgeschlossener Einrichtung `MH_EU_RADAR_CONFIRMED=1`, `MH_STRIPE_TAX_READY=1` und `MH_STRIPE_LIVE_ENABLED=1` setzen.
- `MH_PAID_PRODUCT_READY=1` erst setzen, wenn die bezahlten Funktionen zum veröffentlichten Angebot passen. Die OpenAI-Anbindung ist implementiert, benötigt aber noch einen Schlüssel und echte Qualitäts-/Verbrauchstests. Siehe TOKEN_PRICING.md.
- Unternehmens-/Kontaktangaben, Vertragsbedingungen und Datenschutzinformationen mit tatsächlichen Angaben vervollständigen. E-Mail-Verifizierung, MFA und Kontowiederherstellung sind implementiert; echten SMTP-Versand und Produktionskonfiguration gemäß `AUTH_SETUP.md` vor öffentlichem Start verbinden und testen.

Der Server lässt Live-Checkout erst mit diesen expliziten Einstellungen zu. Die Flags bestätigen organisatorische Einrichtung; sie ersetzen keine Prüfung der Regeln im Stripe-Konto. Ein Dashboard-Kundenportal wird auf Rechnungen, Zahlungsmittel und Kündigung zum Periodenende beschränkt. Tarifwechsel und Erstattungen benötigen vorerst Betreiberbetreuung.

## Quellen

- https://docs.stripe.com/api/checkout/sessions/create
- https://docs.stripe.com/webhooks
- https://docs.stripe.com/radar/rules/supported-attributes
- https://docs.stripe.com/radar/rules/reference
- https://docs.stripe.com/api/versioning

## Lokale Kampagnen-Testpakete (08.10.2026)

Nach verifiziertem Stripe-Testkauf und Firmenprofil kann das Briefing ohne Verbrauch gespeichert und das Dashboard geöffnet werden. Fehlt der OpenAI-Zugang, zeigt die lokale Umgebung ein ausdrücklich bezeichnetes Testpaket aus Vorlagen an. Das Frontend fordert es mit `POST /campaigns/{id}/generate?test_package=true` an. Der Server erlaubt dies ausschließlich einem verwalteten Testkonto mit vorhandener `sk_test_`-Konfiguration, lokaler `MH_PUBLIC_URL` und außerhalb von `MH_ENV=production`; aktives bezahltes Abo und 50 Tokens bleiben nötig. Normale Generation ohne diese Option ruft weiterhin OpenAI auf und fällt bei fehlendem Schlüssel ohne Verbrauch aus.

Die gleichen atomaren Buchungs-/Idempotenzregeln gelten für Testpakete. Keine KI-Usage-Zeile oder Provider-Anfrage wird simuliert; `generation_mode=local_test` bleibt am gespeicherten Paket und im Export vermerkt. Der aktuelle Team-Testkunde hat diesen lokalen Ablauf im echten Browser ausgeführt: 1.500 → 1.450 Test-Tokens, ein weiterhin unfreigegebener Draft. Keine weitere Stripe-Zahlung oder externe Veröffentlichung. Für KI-Qualität und echte Providerkosten ist weiterhin ein tatsächlicher OpenAI-Test erforderlich.

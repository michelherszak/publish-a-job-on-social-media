# MH End-to-End-Testbericht

Stand: 29. September 2026, lokale Testumgebung.

Dieser Bericht enthält keine Zugangsdaten, API-Schlüssel, Webhook-Secrets, MFA-Seeds oder Einmallinks.

## Bestanden

- Checkout-Konfiguration repariert: Hosted Checkout, servereigene Preise, Pflicht-Rechnungsadresse, Stripe Tax, USt-ID-Erfassung und Kartenzahlung.
- Sichere Zuordnung von Checkout Session, Stripe Customer, lokalem Auftrag und Produktmetadaten wiederhergestellt.
- `payment_method_collection=always` wird nur für Abos gesetzt; Tokenpakete erzeugen stattdessen eine Stripe-Rechnung.
- Erfolgs- und Abbruch-URLs verwenden die konfigurierte Server-Origin.
- Webhook-Signatur, Zeitfenster, Idempotenz, Objektabruf, Betragsprüfung, EU-Prüfung und Tokenbuchungen bestehen in Offline-Integrationstests.
- 75 Backend-Tests bestanden.
- Frontend-Produktionsbuild bestanden.
- SEO-Prüfung bestanden.
- Neun Stripe-Testpreise stimmen direkt mit dem lokalen Produktkatalog überein.
- Lokaler Stripe-Listener läuft; ein signiertes Testereignis wurde mit HTTP 200 verarbeitet.
- Sichtbarer Browser-Test der Registrierung mit fünf erfundenen Firmen abgeschlossen:
  - Mit EU-Bestätigung wurden Nordlicht Anlagenbau, Elbwerk Logistik und Hanseblick Gebäudetechnik angelegt und jeweils bis zur E-Mail-Bestätigungsseite geführt.
  - Ohne EU-Bestätigung wurden Mainbogen Pflege und Bergwald Software bereits durch die Pflichtfeldvalidierung im Browser blockiert.
  - Der Datenbankabgleich enthält exakt die drei erwarteten Firmenkonten; alle drei E-Mail-Adressen sind weiterhin unbestätigt.
  - Im lokalen Mail-Ausgang liegt für jedes der drei angelegten Konten genau eine Bestätigungsnachricht. Es wurde keine echte E-Mail versendet und kein Bestätigungslink geöffnet.
- Sichtbare Wiederholung im Cursor-Browser:
  - Rheinblick Maschinenbau und Alpenstern IT wurden mit EU-Bestätigung erfolgreich angelegt; Datenbank und lokaler Mail-Ausgang stimmen überein.
  - Weserland Pflege und Heidekreis Beratung wurden ohne EU-Bestätigung erneut im Browser blockiert und nicht angelegt.
  - Küstenkraft Gebäudeservice wurde trotz gesetzter EU-Bestätigung nicht angelegt: Die persistente Registrierungsbegrenzung reagierte erwartungsgemäß mit „Zu viele Registrierungen. Bitte später erneut versuchen.“ Diese Sicherheitsbegrenzung wurde für den Test nicht umgangen oder gelöscht.

## Fehlgeschlagen und repariert

- Checkout Studio hatte servereigene Order-Metadaten entfernt. Dadurch konnte der vorhandene Webhook den Auftrag nicht mehr finden und ein Billing-Test scheiterte. Metadaten und sichere Objektzuordnung sind wiederhergestellt; die Tests bestehen.
- Checkout Studio hatte Automatic Tax deaktiviert und die Rechnungsadresse optional gemacht. Das widersprach dem EU-B2B-Modell. Automatic Tax, Pflichtadresse und USt-ID-Erfassung sind wieder aktiv.
- Der lokale Stripe-CLI-Aufruf ohne Ereignisliste funktionierte mit Stripe CLI 1.52.0 nicht. Der neue Listener übergibt ausschließlich die zehn unterstützten Ereignisse und speichert sein wechselndes Secret privat.

## Extern blockiert

- Stripe Tax meldet `pending`.
- In Stripe fehlt der Standard-Produktsteuercode.
- Tatsächlicher Rechnungsaussteller, Geschäftsanschrift und zutreffende Steuerregistrierungen müssen im Stripe-Dashboard bestätigt werden.
- Die EU-Radar-Regeln sind noch nicht eingerichtet oder bestätigt.
- Für diese Schritte ist eine persönliche Stripe-Dashboard-Anmeldung einschließlich möglicher Zwei-Faktor-Bestätigung erforderlich.

## Noch nicht ausgeführt

- Reale E-Mail-Zustellung und MFA nach der nun bestandenen lokalen Registrierung.
- Erfolgreicher Starter-Checkout mit Stripe-Testkarte.
- Ablehnung und 3-D Secure.
- Abgebrochener Checkout.
- Verlängerung und fehlgeschlagene Verlängerung.
- Kündigung zum Periodenende.
- Token-Aufladung und Erstattung.
- EU- und Nicht-EU-Rechnungsadresse gegen echte Radar-Regeln.
- Reale Stripe-Rechnung und Zustellung.
- Realer OpenAI-Aufruf.

## KI-Prüfkriterien

Die KI wird nicht auf wortgleiche, deterministische Ausgaben getestet. Verbindlich geprüft werden:

- exakt sechs erforderliche Textfelder und gültiges JSON,
- keine zusätzlichen oder fehlenden Felder,
- begrenzte Eingabe und Ausgabe,
- keine doppelte Tokenbelastung bei Wiederholung,
- keine MH-Tokenbelastung bei Anbieterfehlern,
- protokollierte Modell-, Response- und Tokenwerte ohne Briefinginhalt,
- Kostenmessung mit festen repräsentativen Briefings,
- manuelle Qualitätsbewertung anhand derselben Briefings.

## Nächste Aktion

Im geöffneten Stripe-Dashboard anmelden und Stripe Tax mit echten Unternehmensdaten abschließen. Danach werden Status und Standard-Steuercode erneut direkt geprüft, bevor ein Test-Checkout gestartet wird.

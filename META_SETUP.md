# Facebook zuerst, Instagram anschließend

## Produktmodell und aktueller Stand

Jeder MH-Kunde verbindet seine **eigene Facebook-Unternehmensseite**. Später verbindet er sein eigenes professionelles Instagram-Konto. MH verwendet eine zentrale, vom Betreiber eingerichtete Meta-App; Kunden benötigen keine eigene Entwickler-App. Die Anmeldung findet bei Facebook statt. Kunden geben in MH weder ihr Facebook-Passwort noch einen Seiten-Token ein. FLH kann ein eigener Testbetrieb sein, ist aber nicht die gemeinsame Veröffentlichungsseite der Kunden.

Facebook ist lokal implementiert: Firmen-Admin verbindet eine Seite, Firmenteam erstellt eine Vorschau, bestätigt den vollständigen Beitrag und sendet ihn ausdrücklich. Der erste Umfang ist ein normaler Facebook-Seitenbeitrag mit **Text und Bewerbungslink**, ohne Übertragung der Kampagnenbilder, bezahlte Werbung oder Gruppenveröffentlichung. Meta kann selbst eine Linkvorschau darstellen; diese wird hier nicht zugesichert. Verbindung und interne Freigabe veröffentlichen nichts. Der interne Status `Live` bleibt „Freigegeben“; der separate Veröffentlichungsstatus wird erst nach Anbieterantwort gesetzt.

Instagram ist begonnen: optionale Berechtigungen, Erkennung des mit der Facebook-Seite verknüpften professionellen Kontos und Anzeige des Kontos. **Es gibt noch keine Instagram-Veröffentlichung.** Eigene Kampagnenbilder können bereits im Content Studio hochgeladen, für Feed/Story zugeschnitten und als JPEG exportiert werden. Für direkte Instagram-Veröffentlichung fehlen die öffentliche Medienbereitstellung und die bestätigte Veröffentlichung über Media-Container. SVG ist kein fertiges Instagram-Uploadformat. Diese erste Integration nutzt Instagram API **with Facebook Login**; das alternative Instagram Login ohne verknüpfte Facebook-Seite ist nicht implementiert.

**Es fehlt noch die öffentliche HTTPS-Adresse und eine Meta-App. Es wurde keine echte Meta-Anmeldung oder Veröffentlichung getestet.** Lokale Tests verwenden ausschließlich isolierte Daten und simulierte Anbieterantworten. Die Agentur für Arbeit ist nicht Bestandteil dieser Integration.

## Was der MH-Betreiber einrichten muss

1. Öffentliche HTTPS-Domain und Hosting für Frontend und Backend. `/api` muss an FastAPI weitergeleitet werden; `/jobs`, `/jobs/<id>`, `/r/<id>` und `/apply/<id>` müssen die vorhandenen Bewerbungsseiten bedienen. Produktionsauthentifizierung, Mailzustellung und rechtliche Angaben gemäß `AUTH_SETUP.md` vervollständigen. Die lokalen Startserver allein sind kein öffentliches Hosting.
2. Meta-Entwicklerkonto und eine Meta-App mit dem passenden Facebook-Login-/Seiten-Anwendungsfall. Im jeweiligen Dashboard prüfen, welcher Anwendungsfall diese Rechte unterstützt. Die App ist MH zugeordnet und nicht pro Kunde zu erstellen.
3. Tatsächliche App-Domain, Datenschutz-URL, Datenlöschungsanleitung sowie die exakte OAuth-Rücksprungadresse hinterlegen: normalerweise `https://<MH-Domain>/api/social/meta/callback`. MH akzeptiert nur dieselbe öffentliche Domain wie die App-Oberfläche. Keine beliebigen Weiterleitungsziele.
4. Berechtigungen für Facebook: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`. Für den optionalen Instagram-Anschluss zusätzlich `instagram_basic`, `instagram_content_publish`. Fehlende Facebook-Rechte verhindern die Verbindung; abgelehnte optionale Instagram-Rechte verhindern nicht die Facebook-Seitenauswahl.
5. Für Entwicklung zunächst einen eigenen berechtigten Testnutzer bzw. eine geeignete App-Rolle und dessen Testseite verwenden. Ein Beitrag kann auch dabei auf einer echten Seite öffentlich erscheinen. Vor Kundenzugang im Meta-Dashboard die erforderlichen App-Review-, Advanced-Access- und gegebenenfalls Business-Verifizierungsanforderungen erfüllen. Ein erfolgreicher Test mit dem App-Betreiber bestätigt keine Freigabe für beliebige Kundenkonten. Facebook-Login für Business kann je nach gewähltem App-Anwendungsfall weitere Dashboard-Konfiguration erfordern; beim echten Verbindungstest prüfen.
6. Eine aktuell unterstützte Graph-API-Version aus dem Meta-Dashboard ausdrücklich festlegen und vor Nutzung prüfen. MH erfindet keine Version und hat keinen impliziten Fallback.

Server-Konfiguration:

- `MH_PUBLIC_URL`: öffentliche Frontend-Origin ohne Pfad, beispielsweise `https://<MH-Domain>`.
- `MH_META_APP_ID`: ID der zentralen Meta-App.
- `MH_META_APP_SECRET`: ausschließlich im privaten Server-/Secret-Store.
- `MH_META_GRAPH_VERSION`: ausdrücklich gewählte unterstützte Version, im Format `vXX.0`.
- `MH_META_CALLBACK_URL`: exakt bei Meta eingetragene HTTPS-Adresse einschließlich `/api`, wenn der Proxy dieses Präfix verwendet.
- `MH_AUTH_ENCRYPTION_KEY`: stabiler Produktionsschlüssel für die vorhandene Verschlüsselung. Datenbank und Schlüssel zusammen sichern. Lokal wird die vorhandene private `backend/.auth.key` verwendet.

Nach Einrichtung der Domain und App kann der Betreiber im eigenen Terminal `python3 -m backend.meta_setup setup` ausführen. Das App-Secret wird verdeckt abgefragt. Die bestehende private `backend/.env.local` bleibt mit allen anderen Werten erhalten und wird atomar mit Dateirechten 0600 ersetzt. Das Skript ändert `MH_PUBLIC_URL`; deshalb nur mit der endgültig gewählten bzw. bewusst verwendeten Test-Origin ausführen. Es prüft das Format, kontaktiert Meta nicht und bestätigt weder App-Rechte noch Veröffentlichung. Mit `python3 -m backend.meta_setup status` nur den lokalen Einrichtungsstatus anzeigen. Keine Secrets in Chat, Dokumentation, Screenshots oder Frontend ablegen.

Backend nach Änderungen neu starten. In einer öffentlichen Umgebung die Konfiguration über den Hostinganbieter laden; `./start.sh` ist der lokale Startweg. HTTP-Zugriffsprotokolle und Proxy-Logging dürfen beim OAuth-Callback keine Query-Werte speichern, da die Rückleitung einen kurzlebigen Autorisierungscode enthält. MH selbst speichert diesen Code nicht.

## Was jeder Kundenbetrieb braucht

- Eine Facebook-Unternehmensseite und ein Facebook-Konto mit den nötigen Seitenverwaltungs-/Inhaltsrechten.
- Einen echten Firmen-Admin in MH, der unter **Settings → Eigene Unternehmensseite verbinden** über Facebook anmeldet und genau die eigene Seite auswählt. MH kann nicht anhand einer E-Mail-Adresse eine Seite auswählen.
- Für Instagram ein professionelles Instagram-Konto, das in diesem gewählten Integrationsweg mit der ausgewählten Facebook-Seite verknüpft ist.

Verbindungen sind pro Firma getrennt. Globale Plattform-Admins und Demo-Rollenvorschauen können keine Kundenverbindung herstellen oder veröffentlichen. Firmen-Admins verwalten die Verbindung; Firmen-Admins und Bearbeiter dürfen freigegebene Kampagnen veröffentlichen. Kundenrollen dürfen nicht veröffentlichen. Bestehende Abo-Schreibgates gelten auch hier. Entfernen einer Verbindung aus MH bleibt bei inaktivem Abo möglich; vorhandene Facebook-Beiträge bleiben erhalten. Das Entfernen löscht die lokal gespeicherten Meta-Zugänge, widerruft aber nicht die App-Berechtigungen bei Facebook; diese kann der Kunde zusätzlich in seinen Facebook-Einstellungen entfernen.

## Facebook-Veröffentlichung

1. Kampagne prüfen und intern freigeben.
2. MH-Bewerbungsseite einrichten und ausdrücklich aktivieren; einen aktiven Meta-Anzeigenlink (bestehende Facebook-Links bleiben kompatibel) für die Kampagne erstellen. Externe Bewerbungslinks werden vom bestehenden Backend unterstützt; der normale UI-Ablauf nutzt die MH-Seite. Externe Bewerbungsbestätigungen benötigen weiterhin einen verbundenen Empfänger gemäß bestehendem Tracking.
3. Im Studio unter Meta **eine** Textvariante wählen, prüfen und den passenden Anzeigenlink auswählen. MH ergänzt den Bewerbungslink.
4. „Veröffentlichung prüfen“ erzeugt eine eingefrorene Vorschau mit Zielseite. Anschließend Checkbox bestätigen und „Jetzt auf Facebook veröffentlichen“ wählen. Die Vorschau läuft nach 20 Minuten ab. Verbindung, Kampagne und Bewerbungslink werden vor Versand erneut geprüft.
5. Erst eine gültige Facebook-Beitrags-ID bestätigt die Veröffentlichung. MH zeigt Beitragslink und Zeit sowie einen Verlaufseintrag. Pro Kampagne wird in dieser ersten Version ein Facebook-Beitrag geführt. Wiederholtes Senden derselben bestätigten Veröffentlichung gibt das gespeicherte Ergebnis zurück; keine zweite Anzeige.

Die Seitentokens und zwischenzeitlich auswählbaren Seiten werden mit Fernet verschlüsselt. Browserantworten enthalten ausschließlich IDs, Namen und Status. OAuth-State ist zehn Minuten gültig, gehasht, einmalig sowie an Nutzer, Firma und MH-Sitzung gebunden. Zur Auswahl vorgemerkte Seiten bleiben höchstens 20 Minuten nutzbar. Der Verbindungsablauf setzt die Tokenlaufzeit konservativ auf die bei Meta erhaltene Autorisierungslaufzeit; Ablauf erfordert erneute Anmeldung. Es gibt keine automatische Token-Erneuerung.

### Fehler und unklare Ergebnisse

Ein ausdrücklicher, strukturierter Anbieterfehler wird als abgewiesen geführt; nach Prüfung kann eine neue Vorschau erstellt werden. Bei Timeout, Verbindungsabbruch, Serverfehler oder unbrauchbarer Erfolgsantwort kann Facebook den Beitrag bereits angelegt haben. MH zeigt „Ergebnis unklar“ und sendet **nicht automatisch erneut**. Ein Prozessabsturz nach Claim lässt den Status „wird veröffentlicht“ stehen; auch dieser Status sperrt einen zweiten Versand.

Firmen-Admins können nach zwei Minuten einen auf der ursprünglichen Seite vorhandenen Beitrag über dessen kombinierte Graph-Beitrags-ID `Seiten-ID_Beitrags-ID` nachträglich prüfen lassen. MH liest den Beitrag bei Meta und bestätigt ihn nur bei identischer ID, Zielseite und vollständigem Nachrichtentext. Wird kein passender Beitrag gefunden, bleibt der Status unklar. Eine Freigabe zum erneuten Senden nach nachgewiesenem Fehlschlag ist noch kein Self-Service-Ablauf; Betreiberprüfung ist erforderlich. Niemals allein aufgrund eines Zeitablaufs zurücksetzen.

## Echte Abnahme vor Freigabe für Kunden

- Eigene Testfirma und bewusst gewählte Testseite verbinden; Seitenliste, verweigerte Rechte, abgebrochene Anmeldung und Ablauf prüfen.
- Den tatsächlich bei Meta gewählten App-Anwendungsfall und Tokenaustausch prüfen. Nur eine echte Anbieterprüfung bestätigt die Verbindung.
- Öffentliche Bewerbungsseite aus einem anderen Gerät öffnen und eine Testbewerbung erfassen.
- Einen ausdrücklich freigegebenen Testbeitrag veröffentlichen, auf Facebook öffnen und den Bewerbungslink überprüfen.
- Doppelklick/Wiederholung, abgelaufene Verbindung und unklare Antwort anhand kontrollierter Tests prüfen.
- Erst danach Facebook als extern verifiziert bezeichnen. Instagram-Bildveröffentlichung bleibt bis zur nächsten Implementierung ausstehend.

Lokale Prüfung:

```sh
python3 -m unittest backend/test_security.py backend/test_billing.py backend/test_stripe_setup.py backend/test_auth.py backend/test_ai.py backend/test_gmail.py backend/test_tracking.py backend/test_social.py backend/test_recruiting.py backend/test_campaign_images.py
cd frontend
npm run build
npm run test:seo
npm run test:language
```

Quellen: [Offizielle Meta Facebook API](https://www.postman.com/meta/facebook/overview), [Autorisierte Facebook-Seiten](https://www.postman.com/meta/facebook/request/bqfxwbp/get-access-tokens-of-pages-you-manage), [Instagram API mit Facebook Login](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api?entity=request-23987686-bd5abaa1-8c39-49ee-97f1-cb2170fb0b7c), [Meta Pages API](https://developers.facebook.com/docs/pages-api/), [App Review](https://developers.facebook.com/docs/app-review/).

## Jobportal: lokale Vorbereitung (05.10.2026)

Der Veröffentlichungsplan im Content Studio aktiviert die lokale MH-Stelle und bereitet Instagram-/Meta-Links für normale Beiträge, bezahlte Anzeigen und Retargeting vor. Er veröffentlicht keinen Anbieterbeitrag, bucht keine Anzeige und sendet keine Besucherdaten an Meta. Ein gemeinsames Budget umfasst beide Kanäle samt Retargeting; 150 EUR/14 Tage ist ein frei änderbarer MH-Testvorschlag. Retargeting-Zustimmung zählt nur lokale Interessenssignale; eine echte Zielgruppe gibt es noch nicht. Die bestehende explizite Facebook-Veröffentlichung bleibt davon getrennt und sendet weiterhin Text und Link.

Der Nutzer hat noch keine Domain und ausdrücklich lokale Umsetzung gewählt. Für echte Ausspielung fehlen HTTPS, verifizierte Meta-App/Kundenverbindung, Instagram-Medienpublikation, Anzeigenkonto/-buchung und ein überprüfter, einwilligungsgebundener Marketingablauf. Instagram-Beiträge brauchen eine geeignete Profil-/Story-Verlinkung; die tatsächlichen Kontofunktionen müssen vor Ausspielung geprüft werden, statt einen klickbaren Caption-Link vorauszusetzen. Vor Aktivierung von Beschäftigungsanzeigen müssen die dann aktuellen Meta-Kategorie-/Zielgruppenregeln geprüft werden. Kein externer Push wird hier zugesichert.

## Gemeinsamer lokaler Workflow (05.10.2026)

`campaign_workflow.py` führt nun den gesamten lokalen Ablauf mit einem ausschließlich lokalen Anbieter-Simulator aus: unveränderliche Text-/Bildpakete, Kanalaktionen mit Testquittungen, begrenzte Wiederholungen und explizite Prüfung unklarer Ergebnisse, gemeinsames Budget mit idempotenten Testkosten und Besuchszielgruppe mit Bewerbungs-/Widerrufsausschluss. Simulationsdaten sind in Oberfläche und Bericht ausdrücklich gekennzeichnet. Keine simulierte Quittung bestätigt eine echte Veröffentlichung. Produktions-Start/Retry/Testauslieferung sind gesperrt; ein Live-Schalter existiert nicht.

Die echten Adapter für Instagram-/Bildpublikation, Anzeigenkonto/-buchung und Marketingereignisse sind weiterhin nicht implementiert. Domain/Hosting und verifizierte Meta-Verbindung allein aktivieren diesen Ablauf nicht. Die vorhandene echte Facebook-Text-/Link-Veröffentlichung bleibt ein separater, ausdrücklich bestätigter Ablauf. Vor späterer echter Ausspielung sind diese Adapter, Providerregeln, Kontofunktionen und Produktions-Datenschutzhinweise zu implementieren und mit geeigneten eigenen Testkonten zu verifizieren. Der lokale Simulator liefert kein belastbares Werbe-/Erfolgsergebnis.

# MH Recruiting Workspace - Use Cases

**Version:** 1.0 · **Stand:** 28. September 2026 · **Zweck:** Fachliche Übergabe unabhängig von Modulen und Epics.

## Leseschlüssel

Ein Use Case beschreibt ein Ziel aus Sicht eines Akteurs, seinen Auslöser, das beobachtbare Ergebnis und prüfbare Bedingungen. **Umgesetzt** bedeutet: im lokalen Prototyp vorhanden und automatisiert getestet, nicht produktiv freigegeben. **Teilweise** bedeutet: ein Teil des End-to-End-Ablaufs existiert, aber externe oder fachliche Nachweise fehlen. **Offen** bedeutet: noch nicht umgesetzt. Die Priorität P0 ist vor dem ersten echten Verkauf nötig; P1 gehört zum nutzbaren Pilot; P2 kann später folgen.

**Akteure:** Besucher, Firmen-Admin, Teammitglied (User), Kunde mit Leserechten, Plattform-Admin; externe Systeme: Stripe, E-Mail-Anbieter und KI-Anbieter. Ein Unternehmen ist ein getrenntes Mandantenkonto. **MH-Tokens** sind Produktguthaben, keine OpenAI-API-Tokens.

## Fachlicher Ablauf

Besucher versteht Angebot und Kosten → Firmen-Admin registriert EU-Unternehmen → bestätigt E-Mail → richtet MFA ein → bucht Abo per Stripe → vervollständigt Firmenprofil → erzeugt und prüft ersten Entwurf → lädt Team ein → bearbeitet, prüft und exportiert Kampagnen → verfolgt Guthaben, Rechnungen und manuell erfasste Kennzahlen.

### UC-01 Angebot verstehen und Tarif planen · P1 · Umgesetzt

**Akteur/Ziel:** Besucher möchte den Recruiting-Ablauf, Sitzplätze und Tokenverbrauch einschätzen.
**Auslöser:** Aufruf der öffentlichen Landingpage.
**Hauptablauf:** Besucher liest Ablauf und Preise, gibt erwartete Kampagnenpakete und Bearbeiterzahl ein, erhält eine Tarifempfehlung und kann einen Plan auswählen oder die Planung als Text herunterladen.
**Ergebnis/Abnahme:** Auswahl und Eingaben bleiben beim Wechsel zur Registrierung in der Sitzung erhalten; eine Auswahl löst weder Registrierung noch Zahlung aus. Preise und Tokenregeln sind vor dem Kauf sichtbar.
**Grenze:** Die Tarifempfehlung ist eine Planung, keine verbindliche Abrechnung.

### UC-02 EU-Firmenkonto registrieren · P0 · Umgesetzt

**Akteur/Ziel:** Firmen-Admin möchte ein neues Unternehmens- und persönliches Konto anlegen.
**Auslöser:** Formular auf `/register` absenden.
**Hauptablauf:** Firmenname, Name, geschäftliche E-Mail, Passwort und EU-Sitz/Rechnungsland eingeben; Unternehmensbestätigung abgeben. Das System legt getrennte Konten an und sendet einen Einmallink.
**Ergebnis/Abnahme:** Ohne gültige EU-Auswahl, Pflichtfelder und Passwort mit mindestens 15 Zeichen keine Registrierung. Registrierung allein belastet keine Karte und schaltet keine bezahlten Funktionen frei.
**Ausnahme:** Bereits vorhandene Adresse oder Mailversandfehler wird behandelt; eine neue Bestätigung kann angefordert werden.

### UC-03 E-Mail bestätigen · P0 · Teilweise extern verifiziert

**Akteur/Ziel:** Neuer Firmen-Admin weist Zugriff auf sein Postfach nach.
**Auslöser:** Klick auf den Bestätigungslink.
**Hauptablauf:** System prüft den 60 Minuten gültigen Einmallink, verbraucht ihn und führt zum nächsten Onboarding-Schritt.
**Ergebnis/Abnahme:** Abgelaufene, manipulierte oder bereits verwendete Links verifizieren nicht. Ein neuer Link macht den alten ungültig. Der Nachweis betrifft nur Postfachzugriff, nicht Identität oder Vertretungsmacht.
**Statusgrenze:** Gmail-SMTP-Selbsttest wurde akzeptiert; die komplette Registrierungsmail und Ankunft im Posteingang müssen noch geprüft werden.

### UC-04 Sicher anmelden und Admin-MFA einrichten · P0 · Umgesetzt

**Akteur/Ziel:** Firmen-Admin oder Teammitglied greift nur mit berechtigter Identität zu.
**Auslöser:** Anmeldung oder erste Admin-Einrichtung.
**Hauptablauf:** E-Mail/Passwort prüfen; Firmen-Admin registriert einen TOTP-Authenticator, bestätigt einen Code und sichert Wiederherstellungscodes. Neue Admins müssen E-Mail und MFA abschließen, bevor Workspace und Billing zugänglich sind.
**Ergebnis/Abnahme:** Sitzung wird bei erfolgreicher Anmeldung/MFA erneuert; wiederverwendeter TOTP-Schritt und verbrauchter Recovery-Code werden abgewiesen. Abmeldung und Passwortänderung widerrufen Sitzungen.

### UC-05 Konto wiederherstellen · P0 · Teilweise

**Akteur/Ziel:** Nutzer setzt ein vergessenes Passwort zurück.
**Auslöser:** Anforderung eines Reset-Links.
**Hauptablauf:** Zeitlich begrenzten Einmallink per E-Mail empfangen; bei bestehender MFA zusätzlich unbenutzten Wiederherstellungscode eingeben; neues Passwort setzen.
**Ergebnis/Abnahme:** Kein automatischer Login nach Reset; alte Sitzungen enden; MFA bleibt aktiv. Antworten verraten keine existierenden Konten.
**Offen:** Manuell geprüfter Betreiberprozess für verlorenen Authenticator **und** verlorene Recovery-Codes.

### UC-06 Onboarding fortsetzen · P0 · Umgesetzt

**Akteur/Ziel:** Neuer Firmen-Admin möchte nach Unterbrechung genau dort weitermachen, wo Voraussetzungen fehlen.
**Auslöser:** Anmeldung während einer unvollständigen Einrichtung.
**Hauptablauf:** System zeigt den nächsten Schritt: Sicherheit, Tarif, Firmenprofil oder ersten Entwurf. Nach bestätigter Zahlung folgen Profilfelder und ein bewusst bestätigter 50-Token-Entwurf, der gelesen und zur Prüfung markiert wird.
**Ergebnis/Abnahme:** Unbezahlte oder unsichere Konten überspringen keine Schranken; gespeicherte Zwischenschritte bleiben erhalten.

### UC-07 Monats- oder Jahresabo per Kreditkarte buchen · P0 · Teilweise

**Akteur/Ziel:** Firmen-Admin wählt einen Tarif und bezahlt ihn für sein EU-Unternehmen.
**Auslöser:** Auswahl von Starter, Team oder Scale mit monatlicher Zahlung oder jährlicher Vorauszahlung nach E-Mail- und MFA-Abschluss.
**Hauptablauf:** MH zeigt Preis, Zahlungsintervall, monatliche Inklusivtokens und Kündigungszeitpunkt an. Der Admin bestätigt EU-Rechnungsland und Unternehmensstatus, stimmt der PDF-Rechnung zu und bezahlt per Karte im Stripe Checkout. MH prüft den signierten Zahlungs-Webhook und aktiviert erst nach bezahlter Abo-Rechnung Tarif und Guthaben.
**Ergebnis/Abnahme:** Die Browser-Rückkehr allein aktiviert nichts. Fehlgeschlagene, unvollständige oder nicht passende Zahlungen gewähren keine Berechtigung. Betrag, Währung, Steuerverhalten und Monats- oder Jahresintervall entsprechen dem serverseitigen Katalog. Beim Monatsabo erneuern bezahlte Monatsrechnungen die Inklusivtokens; beim im Voraus bezahlten Jahresabo erneuern sie sich monatlich innerhalb der bezahlten Jahreslaufzeit. Nicht genutzte Inklusivtokens verfallen am Monatsstichtag. Kündigung wirkt zum Ende des bezahlten Monats oder Jahres.
**Statusgrenze:** Monats- und Jahrespreise sind im Stripe-Testkonto angelegt und die Webhook-Grundstrecke ist verbunden. Vollständige Testkäufe beider Intervalle, Stripe Tax, EU-Radar und Live-Freigabe fehlen.

### UC-08 Bezahlte Rechnung erhalten und abrufen · P0 · Teilweise

**Akteur/Ziel:** Firmen-Admin erhält eine nachvollziehbare Rechnung für Abo oder Tokenpaket.
**Auslöser:** Bestätigte bezahlte Stripe-Rechnung.
**Hauptablauf:** MH versendet eine Nachricht mit Link zum von Stripe erzeugten PDF; Rechnung bleibt zusätzlich im Stripe-Kundenportal abrufbar.
**Ergebnis/Abnahme:** Doppelte Webhooks erzeugen keine doppelte Tokenbuchung. Bei Mailfehler bleibt der Versand wiederholbar. Die Rechnung zeigt die rechtlich erforderlichen echten Aussteller-, Empfänger-, Leistungs- und Steuerangaben.
**Offen:** Ausstellerdaten, Stripe Tax, Musterrechnung, Zustelltest und Strategie für strukturierte deutsche B2B-E-Rechnungen. Stripe-PDF allein ist keine strukturierte E-Rechnung.

### UC-09 Tokenpaket nachkaufen · P0 · Teilweise

**Akteur/Ziel:** Firmen-Admin kauft zusätzliches Guthaben ohne neues Abo.
**Auslöser:** Auswahl eines Tokenpakets bei aktivem Abo.
**Hauptablauf:** Stripe-Einmalzahlung durchlaufen; MH addiert die Tokens erst nach geprüftem, bezahltem Checkout genau einmal zum gekauften Guthaben.
**Ergebnis/Abnahme:** Mehrere Käufe summieren sich; Wiederholung desselben Webhooks addiert nicht erneut. Keine automatische Aufladung. Gekaufte Tokens sind nur bei aktivem Abo nutzbar.
**Statusgrenze:** Logik getestet, echter Kartenversuch ausstehend.

### UC-10 Guthaben und Verbrauch nachvollziehen · P1 · Umgesetzt

**Akteur/Ziel:** Firmenmitglied sieht verfügbares, monatlich enthaltenes und gekauftes Guthaben.
**Auslöser:** Dashboard oder Bereich „Abo & Tokens“ öffnen.
**Hauptablauf:** System zeigt beide Guthabenarten, tatsächlich nutzbare Summe, Abo-Status, Laufzeitende und jüngste Buchungen; nach Kauf/Generierung wird aktualisiert.
**Ergebnis/Abnahme:** Monatliche Tokens werden zuerst verbraucht und bei bezahlter Verlängerung erneuert; nicht genutzte monatliche Tokens verfallen. Gekaufte Tokens bleiben getrennt gespeichert. Fremde Firmen können den Kontostand nicht sehen.

### UC-11 KI-Kampagnenpaket erzeugen · P1 · Teilweise

**Akteur/Ziel:** Berechtigtes Firmenmitglied erhält mehrere kanalbezogene Entwürfe aus einem Briefing.
**Auslöser:** Bestätigter Generierungsauftrag für eine Kampagne.
**Hauptablauf:** Rolle, Standort, Aufgaben, Anforderungen, Vorteile und Ton erfassen; vorab 50 MH-Tokens bestätigen; Backend ruft den zentral konfigurierten KI-Anbieter auf; Ergebnis wird versioniert gespeichert.
**Ergebnis/Abnahme:** Erfolgreicher Auftrag belastet genau 50 MH-Tokens, auch bei wiederholter Anfrage nur einmal. Technischer Fehler oder unvollständiges Ergebnis belastet kein MH-Guthaben. Ohne aktives Abo, ausreichende Tokens oder Anbieter-Konfiguration kein bezahlter Auftrag.
**Statusgrenze:** Anbindung und Mock-Tests vorhanden; realer Anbieteraufruf und Qualitäts-/Kostenmessung fehlen. Demo-Konten nutzen lokale Vorlagen.

### UC-12 Entwürfe bearbeiten und vergleichen · P1 · Umgesetzt

**Akteur/Ziel:** Teammitglied verbessert Inhalte vor der Freigabe.
**Auslöser:** Öffnen einer eigenen Kampagne.
**Hauptablauf:** Kanaltexte bearbeiten, speichern, kommentieren sowie Verlauf und gespeicherte Versionen vergleichen.
**Ergebnis/Abnahme:** Änderungen sind der berechtigten Person und Firma zugeordnet; Anzeigen/Bearbeiten/Exportieren verbrauchen keine weiteren MH-Tokens. Eine als „Live“ markierte Kampagne lässt sich nicht beliebig überschreiben.

### UC-13 Inhalt zur Prüfung geben und entscheiden · P1 · Umgesetzt

**Akteur/Ziel:** Berechtigte Person steuert Entwurf, Review und Freigabe.
**Auslöser:** Entwurf zur Prüfung einreichen oder Review bearbeiten.
**Hauptablauf:** Status Draft → Review → Live; Kommentare und Änderungswünsche hinzufügen; Entscheidung in Historie speichern.
**Ergebnis/Abnahme:** Rollenrechte gelten serverseitig. Kundenrolle sieht nur Review/Live; Plattform-Admin kann nicht stellvertretend Kampagnen genehmigen. „Live“ bedeutet interner Workflowstatus, keine Veröffentlichung.

### UC-14 Material exportieren und extern veröffentlichen · P1 · Umgesetzt für Export

**Akteur/Ziel:** Firma nimmt freigegebenes Material in ihre Kanäle mit.
**Auslöser:** ZIP oder SVG aus eigener Kampagne herunterladen.
**Hauptablauf:** System erstellt Kanaltexte/Assets für manuelle Weiterverwendung.
**Ergebnis/Abnahme:** Export nur mit Leserecht in derselben Firma; kein externer Post oder Ad-Start durch MH. Automatische Veröffentlichung ist **kein** aktueller Use Case.

### UC-15 Kampagnenkennzahlen erfassen · P1 · Umgesetzt für manuelle Daten

**Akteur/Ziel:** Firma dokumentiert Reichweite und Bewerbungen.
**Auslöser:** Manuelles Eintragen von Impressions, Klicks und Bewerbungszahlen.
**Hauptablauf:** Berechtigte Person erfasst Werte pro Kanal; Dashboard zeigt Summen und Statuszahlen.
**Ergebnis/Abnahme:** Kennzahlen sind als manuell erfasst erkennbar und nur innerhalb der Firma sichtbar. Es gibt noch keinen automatischen Import oder Attributionsnachweis.

### UC-16 Team einladen und Plätze verwalten · P1 · Umgesetzt

**Akteur/Ziel:** Firmen-Admin lädt Bearbeiter kontrolliert ein.
**Auslöser:** Einladung mit E-Mail und Rolle.
**Hauptablauf:** Rollen-/Firmen-gebundenen 48-Stunden-Link senden; offene Einladung reserviert einen Platz; eingeladene Person setzt ihr eigenes Passwort; Admin kann Einladung widerrufen.
**Ergebnis/Abnahme:** Platzlimit wird beim Versand und bei Annahme geprüft. Kein automatischer Firmenbeitritt anhand der Domain und keine vom Admin vorgegebenen Nutzerpasswörter.

### UC-17 Zahlungsmittel, Rechnungen und Kündigung verwalten · P0 · Teilweise

**Akteur/Ziel:** Firmen-Admin verwaltet das bestehende Abo selbst.
**Auslöser:** Öffnen des Stripe-Kundenportals.
**Hauptablauf:** Zahlungsmittel ändern, Rechnungen ansehen, Abo zum Ende des bezahlten Zeitraums kündigen.
**Ergebnis/Abnahme:** Künftige Tokenzuteilung folgt dem tatsächlichen Abo-/Rechnungsstatus; Kündigung wird transparent angezeigt. Tarifwechsel und Adressänderungen sind derzeit Betreiberfälle.
**Statusgrenze:** Portalintegration vorhanden; vollständiger Stripe-Testfall ausstehend.

### UC-18 Fehlzahlungen, Erstattungen und Sperren behandeln · P0 · Teilweise

**Akteur/Ziel:** Firma und Betreiber vermeiden ungedeckte Leistungen.
**Auslöser:** Fehlzahlung, Rückerstattung, Dispute, Nicht-EU-Rechnungsadresse oder Betragsabweichung.
**Hauptablauf:** System nimmt oder hält Berechtigungen gemäß verifiziertem Stripe-Status zurück und zeigt dem Admin einen handlungsfähigen Status.
**Ergebnis/Abnahme:** Keine neue Leistung aus ungeprüfter Zahlung; Tokenbuchungen bleiben prüfbar und idempotent. Rechnungskorrektur/Gutschrift und Supportablauf müssen vor Livebetrieb definiert werden.

### UC-19 Plattformbetrieb und Mandantentrennung · P0 · Teilweise

**Akteur/Ziel:** Plattform-Admin konfiguriert zentrale KI-Einstellungen und betreibt den Dienst ohne Einsicht in fremde Firmendaten über normale Firmenrollen.
**Auslöser:** Einrichtung, Support oder technischer Vorfall.
**Hauptablauf:** Zentrales KI-Modell/Schlüssel serverseitig verwalten; Gesundheits- und Fehlerzustand prüfen; Demo-Rollen nur lokal in separater Vorschau testen. Eine Kundenfirma kann der Plattform-Admin dauerhaft löschen, einschließlich Nutzer, Kampagnen und lokaler Abrechnung. Eine Stripe-Verknüpfung wird nur bei passender Zahlungskonfiguration vorher entfernt.
**Ergebnis/Abnahme:** Jede firmenbezogene API-Anfrage prüft Mandant und Rolle. Ein Zugriff auf eine fremde Kampagne liefert 404. Demo-Vorschau kann keine Zahlungen auslösen. Produktive Betriebsprozesse für Monitoring, Backup und Incident Response sind noch zu definieren.

## Vor Livebetrieb zu prüfen

1. **Tarife:** Starter 19 €/Monat oder 190 €/Jahr, Team 69 €/Monat oder 690 €/Jahr, Scale 149 €/Monat oder 1.490 €/Jahr, jeweils netto. Jahreszahlung erfolgt im Voraus; Monatsabos sind monatlich kündbar, Jahresabos zum Ende des bezahlten Jahres. Inklusivtokens erneuern sich in beiden Varianten monatlich. Eine vollständige Stripe-Testzahlung steht noch aus.
2. **Tokenwirtschaft:** 50 MH-Tokens je Kampagnenpaket; Top-ups 250/1.000/2.500 für 12/39/89 € netto. Vor Preisfreigabe für Livebetrieb müssen tatsächliche KI-Kosten, Nutzung, Support, Zahlungsgebühren und Zielmarge gemessen werden.
3. **Produktiver Versand:** Persönliches Gmail dient nur dem lokalen Test. Geschäftlicher Absender, Domain-Authentifizierung und EU-Datenverarbeitung sind offen.
4. **Rechnungen:** Rechtlicher Aussteller, Steuerkonfiguration, korrekte Testrechnung und strukturiertes E-Rechnungsformat sind offen.
5. **Livebetrieb:** Stripe-Testzahlungen, echter KI-Aufruf, Produktionshosting, Datenschutz-/Vertragstexte und Freigabeprozesse fehlen.

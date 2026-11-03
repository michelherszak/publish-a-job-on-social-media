# MH - Drei Tiers mit Token-Nachkauf: Wirtschaftlichkeitsfall

**Stand:** 28. September 2026. **Art:** Entscheidungsvorschlag und Szenariorechnung, keine beobachteten Umsätze. Alle Kundenpreise sind netto in EUR. Die interaktive Rechnung liegt zusätzlich in der Canvas-Datei `mh-pricing-business-case.canvas.tsx` des MH-Projekts.

## Meine Produktempfehlung

| Tarif | Monatlich, monatlich kündbar | Jahrespreis, im Voraus | MH-Tokens je bezahltem Monat | Kampagnenpakete à 50 Tokens | Bearbeiter |
| --- | ---: | ---: | ---: | ---: | ---: |
| Starter | 19 € | 190 € | 250 | 5 | 3 |
| Team | 69 € | 690 € | 1.500 | 30 | 10 |
| Scale | 149 € | 1.490 € | 4.000 | 80 | 25 |

Jahreszahlung reduziert nur den Grundpreis und gewährt Tokens weiterhin monatlich. Bei jährlicher Vorauszahlung endet eine Kündigung zum Ende des bezahlten Jahres; die Monatsvariante ist monatlich kündbar. Im Vertrag, Checkout und Kundenportal muss dies klar stehen. Die Jahresoption sollte erst aktiviert werden, wenn die technische Abrechnung und Erstattung geklärt sind.

**Nachkauf:** 250 Tokens für 12 € (5 Pakete, 2,40 €/Paket), 1.000 für 39 € (20 Pakete, 1,95 €/Paket), 2.500 für 89 € (50 Pakete, 1,78 €/Paket). Pakete addieren sich. Kein Auto-Nachkauf. Monatliche Tokens zuerst verbrauchen; gekaufte Tokens bleiben getrennt gespeichert und nur mit aktivem Abo nutzbar. Bearbeitung, Review und Export kosten keine weiteren MH-Tokens.

Dieser Preiskatalog ist seit 28. September 2026 in Landingpage, Checkout und Stripe-Testpreisen umgesetzt. Die Wirtschaftlichkeitsrechnung bleibt ein Szenario mit Annahmen, keine beobachtete Marge. Stripe Tax, vollständige Testzahlung und Live-Freigaben sind weiterhin separat zu prüfen.

## Warum dieses Modell

Die Wertgrenze ist ein **fertiges, prüfbares Recruiting-Kampagnenpaket**, nicht ein API-Token. Ein günstiger Starter reduziert die Einstiegshürde; Team und Scale finanzieren mehr Sitze, höhere Nutzung und Support. Nachkäufe erlauben Spitzenverbrauch, ohne den Tarifwechsel zu erzwingen. Die Nachkaufpreise liegen pro Paket höher als die effektiven Paketkosten großer Tarife, damit ein Upgrade sinnvoll bleibt.

Ich würde für die Hauptgenerierung **GPT-6 Sol** als Qualitätskandidaten testen. Die offizielle OpenAI-Dokumentation nennt 2 USD je Million Eingabe- und 10 USD je Million Ausgabetokens. Bei angenommenen 3.000 Eingabe- und 4.000 Ausgabetokens ergibt das 0,046 USD je Paket vor Aufschlägen. Für die Planung setze ich konservativ **0,15 € je erfolgreich erzeugtem Paket** an, inklusive Puffer für EU-Verarbeitung, Wiederholungen und Messunsicherheit. Die Umrechnung 1 USD = 1 EUR ist eine Modellannahme, kein aktueller Wechselkurs. Die Qualität des Modells für reale Briefings ist noch nicht geprüft; das Produkt verwendet derzeit ein anderes Standardmodell.

## Rechenannahmen

- Kundenmix: 50 % Starter, 35 % Team, 15 % Scale.
- 30 % Jahreszahler mit 10 statt 12 Monatsentgelten; die Rechnung verteilt die Erlöse auf zwölf Monate. Vorauszahlung ist kein zusätzlicher Gewinn.
- Durchschnittlich 60 % der enthaltenen Pakete werden genutzt.
- 25 % der Firmen kaufen pro Monat ein 250er-Nachkaufpaket.
- Variabler Stripe-/Billing-/Tax-Planungssatz: 3,2 % des Netto-Aboerlöses plus 0,25 € je Monatszahlung; 3,6 % plus 0,25 € bei Nachkauf. Jährliche fixe Kartengebühr anteilig durch zwölf. Das ist ein konservativer Mischsatz, keine zugesagte Stripe-Rechnung. Tatsächliche Gebühren hängen von Kartenmix, Steuerbasis, Vertrag und Produktnutzung ab.
- Weitere variable Support-/Betriebskosten je Firma/Monat: 3 € Starter, 8 € Team, 16 € Scale. Sie enthalten einen einfachen Supportpuffer, nicht individuelle Kampagnenberatung.
- Monatliche gemeinsame Betriebskosten: 700 € für Hosting, Backup, Monitoring, Mail und Verwaltungswerkzeuge. Unternehmerlohn: 3.000 €/Monat. Einmalige Startkosten: 5.000 €.

**Formel:** Deckungsbeitrag je Firma = anteiliger Aboerlös + erwarteter Nachkaufumsatz - Zahlungs-/Abrechnungsgebühren - KI-Kosten - variable Supportkosten. Aktive Firmen im Monat `m` = aktive Firmen des Vormonats × (1 - Churn) + neue Firmen. Monatliches Ergebnis = aktive Firmen × gemischter Deckungsbeitrag - 700 € - 3.000 € - Neukunden × CAC.

Der gemischte Nettoerlös beträgt **56,20 € je aktiver Firma und Monat**; nach variablen Kosten bleiben **45,01 € Deckungsbeitrag**. Der 250er-Nachkauf trägt für den Käufer modellhaft 10,57 € bei, nach Gebühren und fünf KI-Paketen.

## Break-even und drittes Jahr

| Szenario | Neue Firmen/Monat | CAC | Kündigung/Monat | Monatlicher Break-even | Kumulierte 5.000 € Startkosten und laufende Verluste gedeckt | Kumuliertes Ergebnis Ende Jahr 3 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Vorsichtig | 6 | 250 € | 3 % | Monat 29 | Monat 69 | -61.974 € |
| Basis | 8 | 220 € | 2,5 % | Monat 19 | Monat 42 | -18.994 € |
| Starkes Wachstum | 10 | 200 € | 2 % | Monat 15 | Monat 31 | +30.087 € |

**Basisfall:** Marketing kostet 8 × 220 € = 1.760 € monatlich; mit Betrieb und Unternehmerlohn sind 5.460 € pro Monat zu decken. Dafür sind rund **122 aktive Firmen** nötig. Nach zwölf Monaten stehen modellhaft 84, nach 24 Monaten 146 und nach 36 Monaten 191 aktive Firmen im Bestand. Das monatliche Ergebnis beträgt in Monat 36 rund **+3.154 €**. Die Anlaufverluste sind dann aber noch nicht vollständig verdient.

| Jahr im Basisfall | Nettoerlös | Deckungsbeitrag nach variablen Kosten | Betrieb + Lohn + Akquise | Operatives Ergebnis |
| --- | ---: | ---: | ---: | ---: |
| 1 | 32.046 € | 25.665 € | 65.520 € | -39.855 € |
| 2 | 80.192 € | 64.223 € | 65.520 € | -1.297 € |
| 3 | 115.724 € | 92.679 € | 65.520 € | +27.159 € |

Zuzüglich 5.000 € Startkosten beträgt das kumulierte Ergebnis nach drei Jahren rund **-18.994 €**. Der größte modellierte kumulierte Fehlbetrag liegt bei rund **50.000 €**. Das ist eine Ergebnis-/Finanzierungsgröße, keine präzise Cashflow-Prognose: Jahresvorauszahlungen verändern die Liquidität, erzeugen aber Leistungspflichten für Folgeperioden.

## Entscheidungsschwellen vor Preisfreigabe

1. Mit mindestens 30 realen Briefings Qualität, Ausgabetokens, Fehlerrate und Nacharbeit für GPT-6 Sol messen. Ohne Qualitätstest keinen Modellwechsel und keine Kostenbehauptung im Marketing.
2. Erste 20-30 zahlende Firmen nutzen, um tatsächliche Paketnutzung, Supportminuten, Nachkäufe und Kündigungen zu erheben. Den Kundenmix und Deckungsbeitrag danach neu rechnen.
3. Einen wiederholbaren Akquisekanal nachweisen. Für kumulierten Break-even innerhalb von drei Jahren zeigt das Modell eher **10 statt 8 neue Firmen pro Monat**, bei höchstens 200 € CAC und ungefähr 2 % monatlicher Kündigung.
4. Vor Stripe-Livegang Preise und Tokenmengen in Landingpage, Backend-Katalog, Stripe-Preisen, Rechnungen, Vertragsbedingungen und Tests synchron ändern. Jahreslogik benötigt zusätzliche Implementierung.
5. Rechtlichen Aussteller, Steuer-/E-Rechnungsprozess, produktiven Mailanbieter, Datenschutz und Produktionshosting klären. Diese Aufwände können den Fixkostenansatz erhöhen.

## Quellen der externen Preisdaten (abgerufen 28.09.2026)

- OpenAI, GPT-6 Sol: https://developers.openai.com/api/docs/models/gpt-6-sol
- OpenAI, regionale Datenverarbeitung und mögliche Aufschläge: https://developers.openai.com/api/docs/guides/your-data
- Stripe, EWR-Karten: https://stripe.com/de/pricing/local-payment-methods
- Stripe Billing: https://stripe.com/de/billing/pricing
- Stripe Tax: https://stripe.com/de/tax/pricing

Alle übrigen Preise, Kosten, Nutzungs- und Wachstumswerte sind ausdrücklich **Annahmen für diesen Case**. Gebühren können je nach Konto und Zahlungsart abweichen; die Anbieterpreise können sich ändern.

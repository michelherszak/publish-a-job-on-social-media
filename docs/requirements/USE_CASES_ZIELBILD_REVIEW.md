# MH – Use Cases für das Recruiting-Zielbild

**Version:** 0.2 · **Stand:** 2. Oktober 2026 · **Status:** UC-Z01 bis UC-Z11 zur Umsetzung freigegeben; Nutzenbewertungen bleiben offen. UC-Z12 zurückgestellt.

**Aktueller Stand:** Der Nutzer hat den Kernablauf nach Erstellung des HTML-Dashboards ausdrücklich beauftragt. Der erste lokale Ausbau nutzt manuellen Kontakt und manuell bestätigte Termine. [ZIELBILD_IMPLEMENTIERUNG.md](ZIELBILD_IMPLEMENTIERUNG.md) beschreibt Umsetzung, Nachweise und Grenzen. Die Use Cases unten bleiben die fachliche Bewertungsgrundlage; frühere Ist-Bezüge beschreiben den Ausgangspunkt vor diesem Ausbau und sind kein aktueller Statusbericht.

## 1. Zweck und Produktannahme

Dieses Dokument übersetzt die Diskussion über einen möglichen Neustart von MH in bewertbare Nutzerziele. Der vorgeschlagene Schwerpunkt ist ein Recruiting-Helfer für kleine EU-Betriebe mit wiederkehrendem Personalbedarf: vom geklärten Stellenangebot über freigegebene Materialien und eine einfache Bewerbung bis zum ersten Bewerbergespräch.

**Arbeitshypothese:** Ein Betrieb profitiert von weniger Vorbereitungsarbeit, kürzeren Wartezeiten und verlässlicher Bearbeitung eingehender Kontakte. Ob das sein wichtigstes Problem löst und ein dauerhaftes Abo rechtfertigt, ist noch zu prüfen. Branche, Betriebsgröße und Nutzungshäufigkeit sind offen. Handwerk und Pflege sind Gesprächskandidaten, keine bestätigten Zielmärkte.

Das Dokument dient zunächst der Entscheidung **behalten / ändern / im Pilot beobachten / später / verwerfen**. Eine positive Bewertung allein ist noch kein Auftrag zur Programmierung; die nachträgliche ausdrückliche Umsetzungsfreigabe für UC-Z01 bis UC-Z11 liegt inzwischen vor. Nach der Bewertung werden die ausgewählten Fälle fachlich freigegeben und erst danach in Umsetzungsschritte übersetzt.

### Verhältnis zum vorhandenen MH

- [USE_CASES.md](USE_CASES.md) dokumentiert den bisherigen Funktionskatalog. Die neuen IDs `UC-Z01` bis `UC-Z12` bezeichnen ausschließlich dieses Zielbild und überschreiben keine vorhandenen IDs.
- [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md) bleibt die maßgebliche Quelle für den aktuellen Produktstand. Der vorhandene Katalog vom 28. September ist eine Momentaufnahme; neuere Ergänzungen stehen im Projektkontext.
- Die Ist-Bezüge unten nennen vorhandene Ansatzpunkte, keine vollständige technische Abnahme. Besonders Bewerbungsbearbeitung, Aufgaben, Terminverwaltung und die fachliche Prüfrunde sind Erweiterungsvorschläge.
- Das bestehende EU-Firmenmodell mit monatlichen/jährlichen Abos und prepaid MH-Tokens bleibt gültig. Tarifänderungen werden hier nicht beschlossen.
- Bezahlte verwaltete Firmen benötigen für geschützte Schreibaktionen ein bezahltes aktives Abo. Bestehende kostenlose Demo-Konten bleiben davon getrennt. Öffentliche Bewerber benötigen kein Firmenkonto oder Abo.
- Bezahlte Kampagnengenerierung kostet derzeit 50 MH-Tokens, wird vorher bestätigt und ruft OpenAI auf, wenn konfiguriert. Fehler verbrauchen keine MH-Tokens; Demos verwenden Vorlagen. Ein echter Anbieteraufruf ist noch nicht verifiziert.
- Ein interner Status „Live“ bedeutet weiterhin Freigabe. Externe Veröffentlichung erfolgt durch eine separate ausdrückliche Aktion. Facebook ist lokal vorbereitet und extern unbestätigt; Instagram-Veröffentlichung ist offen.
- Öffentlicher Betrieb, Live-Zahlungen, produktiver Versand und rechtliche Freigaben sind keine Ergebnisse dieser Spezifikation. Gmail hat einen Selbsttest angenommen; der vollständige produktive Versand ist damit nicht nachgewiesen.

## 2. Akteure, Begriffe und Grenzen

| Akteur | Fachliche Aufgabe | Begrenzung |
| --- | --- | --- |
| Firmenverantwortliche Person | Personalbedarf, Stellenangebot und Zuständigkeiten klären; Freigaben erteilen | Bestehende MH-Rollen entscheiden über tatsächliche Rechte; fachliche Verantwortung ist keine neue technische Rolle |
| Bearbeiter | Materialien vorbereiten, Kontakte bearbeiten und nächste Schritte dokumentieren | Nur innerhalb der eigenen Firma und mit den erforderlichen Rechten |
| Interessent/Bewerber | Stelle verstehen, Kontakt aufnehmen und auf persönliche Rückmeldung reagieren | Keine Anmeldung im Firmen-Workspace; kein Zugriff auf andere Bewerbungen |
| Externer Mitwirkender | Optional bei Texten und Freigaben helfen | Kein automatisch firmenübergreifender Zugang; Bewerberdaten nicht automatisch sichtbar |
| Betreiber | Dienst und benötigte Anbieteranbindungen bereitstellen | Übernimmt keine Einstellungsentscheidung oder Kundenfreigabe |
| Anbieter | Optional KI, Veröffentlichung oder Nachrichtenzustellung unterstützen | Ein Auftrag oder eine Weiterleitung beweist noch keinen Erfolg beim Anbieter |

**Stelle:** der Personalbedarf und das zugehörige Angebot. **Kampagne:** die Materialien und Veröffentlichungen, die diesen Bedarf unterstützen. Eine Stelle kann mehrere Kampagnen benötigen. Ob Stelle und Kampagne eigenständige Objekte werden, entscheidet der Nutzer später; hier wird keine Datenbankstruktur vorgegeben.

**Kontakt/Bewerbung:** eine tatsächlich eingegangene Kontaktaufnahme, ohne automatisch bestätigte Eignung. **Gespräch vereinbart:** Termin und Zustimmung sind dokumentiert; ein versendeter Terminvorschlag genügt nicht. **Bearbeitet:** ein menschlicher nächster Schritt ist dokumentiert; Öffnen einer Bewerbung oder Erzeugen eines Antwortentwurfs genügt nicht.

Vorgeschlagene Bearbeitungszustände wie „neu“, „Rückmeldung ausstehend“ und „Gespräch vereinbart“ betreffen Bewerbungen. Sie verändern nicht die bestehenden Kampagnenzustände Draft → Review → Live.

### Bewusste Grenzen des ersten Zielbilds

- Keine automatische Bewerberbewertung, Rangfolge, Ablehnung oder Einstellungsentscheidung.
- Kein umfassendes Personalverwaltungssystem und keine automatische Gehalts- oder Benefits-Erfindung.
- Keine automatische Buchung bezahlter Werbung, keine garantierte Reichweite oder Einstellung.
- Kein Versand oder Post allein durch eine KI-Empfehlung, interne Freigabe oder fällige Aufgabe.
- Keine neue WhatsApp-, SMS-, Kalender- oder Jobportal-Anbindung als Voraussetzung; Export, manueller Kontakt und manuelle Terminbestätigung reichen im begleiteten Pilot.
- Keine automatische Integration mit der Agentur für Arbeit. Das bleibt außerhalb des bestehenden Projektumfangs.
- Kein eigener marktüblicher Mehrkunden-Agenturmodus in diesem Katalog. Ein solcher Zielkunde braucht eine gesonderte Bewertung.

## 3. Übersicht für die erste Bewertung

„Vorschlag“ ist eine Diskussionspriorität, keine bereits getroffene Entscheidung. „Zuerst“ bedeutet für einen vollständigen begleiteten Pilot erforderlich; Automatisierung kann dabei zunächst durch Menschen ersetzt werden.

| ID | Nutzerziel | Vorschlag | Frage zur Bewertung |
| --- | --- | --- | --- |
| UC-Z01 | Personalbedarf und Verantwortlichkeit klären | Zuerst | Wer kümmert sich tatsächlich um die Besetzung? |
| UC-Z02 | Ein konkretes, belegbares Stellenangebot erarbeiten | Zuerst | Welche Angaben fehlen heute und verursachen Rückfragen? |
| UC-Z03 | Ein verwendbares Recruiting-Paket vorbereiten | Zuerst | Welche Materialien werden wirklich gebraucht? |
| UC-Z04 | Inhalte prüfen und ausdrücklich freigeben | Zuerst | Wer entscheidet, und worauf wartet die Freigabe? |
| UC-Z05 | Freigegebene Inhalte gezielt veröffentlichen | Zuerst | Woher sollen die passenden Interessierten kommen? |
| UC-Z06 | Mobil und ohne Firmenkonto Kontakt aufnehmen | Zuerst | Wo brechen Interessierte die Bewerbung ab? |
| UC-Z07 | Neue Bewerbungen übernehmen und beantworten | Zuerst | Wer antwortet, und woran erkennt man das? |
| UC-Z08 | Ein Bewerbergespräch verbindlich vereinbaren | Zuerst | Was verhindert den Schritt vom Kontakt zum Gespräch? |
| UC-Z09 | Liegengebliebene Aufgaben erkennen und weitergeben | Im Pilot beobachten | Gehen Kontakte durch ausbleibende Bearbeitung verloren? |
| UC-Z10 | Aufwand und Ergebnisse nachvollziehen | Zuerst, einfache Erfassung | Welche Beobachtung verändert die nächste Kampagne? |
| UC-Z11 | Suche beenden und beim nächsten Bedarf wiederverwenden | Zuerst, einfacher Abschluss | Kommt der Betrieb beim nächsten Bedarf wieder? |
| UC-Z12 | Eine fachliche Prüfrunde zu Entwürfen konsultieren | Optional | Verbessert die Prüfrunde Entscheidungen ausreichend? |

Fachlicher Zusammenhang: UC-Z01 → UC-Z02 → UC-Z03 → UC-Z04 → UC-Z05 → UC-Z06 → UC-Z07 → UC-Z08. UC-Z09 begleitet die Arbeit. UC-Z10 liefert Rückmeldung für UC-Z11 und weitere Durchläufe. UC-Z12 ist eine optionale Hilfe vor UC-Z04.

## 4. Use Cases

### UC-Z01 – Personalbedarf und Verantwortlichkeit klären

**Alltagssituation:** Ein Auftrag kann nicht angenommen werden, weil Personal fehlt. Der Inhaber möchte die Suche anstoßen, ohne erst ein langes Formular fertigzustellen.

**Akteur / Ziel:** Firmenverantwortliche Person möchte einen nachvollziehbaren Personalbedarf mit zuständiger Person festhalten.

**Nutzenhypothese:** Die Suche beginnt früher; offene Entscheidungen und fehlende Angaben werden sichtbar.

**Auslöser / Voraussetzungen:** Es entsteht ein Besetzungsbedarf. Für das Speichern im bestehenden Workspace ist ein berechtigtes Firmenkonto mit geltendem Schreibzugang erforderlich.

**Hauptablauf:**
1. Nutzer nennt Tätigkeit, Standort, Umfang und gewünschten Start; noch Unbekanntes darf offen bleiben.
2. Der Assistent fragt nach fehlenden oder widersprüchlichen Kernangaben und hält sie als offene Punkte fest.
3. Nutzer bestimmt die verantwortliche Person und die Person für die erste Bewerberreaktion; dieselbe Person darf beides übernehmen.
4. Nutzer prüft die Zusammenfassung und speichert oder setzt später fort.

**Ergebnis:** Ein unvollständiger oder vollständiger Bedarf mit klarer Firmenzuordnung, Zuständigkeit und offenen Punkten ist gespeichert. Es wurden keine Inhalte erzeugt, veröffentlicht oder kostenpflichtige Aufträge gestartet.

**Abweichungen:** Bei Unterbrechung wird der letzte bestätigte Stand wieder aufgenommen. Ohne zuständige Person bleibt der Bedarf unvollständig. Ohne Schreibzugang erklärt MH den fehlenden Zugang und speichert keinen geschützten Auftrag.

**Abnahmekriterien:**
- **Z01-A1:** Ein Bedarf mit unbekanntem Startdatum lässt sich als unvollständig speichern und wieder öffnen; das Datum wird nicht erfunden.
- **Z01-A2:** Ein Nutzer einer fremden Firma kann den Bedarf weder lesen noch bearbeiten oder sich als Zuständiger eintragen.
- **Z01-A3:** Speichern allein erzeugt keinen MH-Tokenverbrauch und keine externe Aktion.

**Ist-Bezug:** Firmenprofile, Kampagnenbriefing und Speichern ohne Generierung existieren; gesonderte Zuständigkeit und Aufgabenlogik sind nicht durch diesen Bezug bestätigt.

**Bewertungsfrage / Entscheidung offen:** Braucht der Pilot ein eigenes Stellenobjekt oder reicht ein Briefing? Welche Mindestangaben und Zuständigkeiten sind wirklich nötig? **Abhängigkeiten:** Schreibzugang; Entscheidung D03.

### UC-Z02 – Ein konkretes, belegbares Stellenangebot erarbeiten

**Alltagssituation:** Der Betrieb sucht eine Fachkraft, hat aber nur die Beschreibung der letzten Stelle und einige allgemeine Aussagen über gute Zusammenarbeit.

**Akteur / Ziel:** Firmenverantwortliche Person und Bearbeiter möchten Aufgaben, notwendige Voraussetzungen und tatsächliche Vorteile verständlich festhalten.

**Nutzenhypothese:** Konkrete Informationen erleichtern passende Kontaktaufnahmen und verringern Nacharbeit an Anzeigen.

**Auslöser / Voraussetzungen:** UC-Z01 liegt vor; der Nutzer beginnt das Stellenbriefing. Es besteht Schreibzugang.

**Hauptablauf:**
1. MH übernimmt relevante Firmenangaben und kennzeichnet sie als zu bestätigen.
2. Nutzer beschreibt Aufgaben, Arbeitszeiten, Einsatzort, Beschäftigungsumfang und vorhandene Vergütungsinformationen.
3. Nutzer trennt notwendige Voraussetzungen von Fähigkeiten, die im Betrieb gelernt werden können.
4. MH fragt bei allgemeinen Aussagen nach Beispielen, etwa: Was bedeutet „flexibel“ konkret?
5. Nutzer bestätigt zutreffende Angaben, korrigiert Widersprüche und dokumentiert offene Fragen.

**Ergebnis:** Ein bestätigtes Stellenbriefing mit belegbaren Aussagen und offenen Punkten. Noch ungeklärte Angaben sind kein veröffentlichtes Versprechen.

**Abweichungen:** Unbekannte Vergütung wird nicht geschätzt. Widersprüchliche Arbeitszeiten werden zur Klärung markiert. Änderungen an Firmenstandards werden vor Übernahme bestätigt.

**Abnahmekriterien:**
- **Z02-A1:** Bei unbekannter Vergütung erscheint kein erfundener Betrag in Briefing oder späteren Entwürfen.
- **Z02-A2:** Muss- und lernbare Anforderungen bleiben erkennbar getrennt; neue Muss-Anforderungen werden nicht automatisch ergänzt.
- **Z02-A3:** Vorbelegte Vorteile können verworfen werden; eine verworfene Aussage darf nicht in neue Materialien übernommen werden.

**Ist-Bezug:** Firmenprofil und geführtes Briefing sind vorhanden. Die systematische Klärung unkonkreter Aussagen ist Zielverhalten, kein nachgewiesener Ist-Stand.

**Bewertungsfrage / Entscheidung offen:** Welche branchenspezifischen Fragen verändern die Qualität spürbar? Wann sollen fehlende Informationen die Weiterarbeit stoppen? **Abhängigkeiten:** UC-Z01; D01, D04.

### UC-Z03 – Ein verwendbares Recruiting-Paket vorbereiten

**Alltagssituation:** Die Angaben sind geklärt. Der Betrieb braucht Material für seine Website und die tatsächlich genutzten sozialen Kanäle.

**Akteur / Ziel:** Bearbeiter möchte zusammenpassende, editierbare Materialien auf Grundlage des bestätigten Briefings erhalten.

**Nutzenhypothese:** Weniger Schreibarbeit und widersprüchliche Angaben zwischen Kanälen.

**Auslöser / Voraussetzungen:** Nutzer fordert Entwürfe an. Briefing, vereinbarter Paketumfang und geschützter Zugang liegen vor. Bezahlte verwaltete Generierung benötigt ein aktives bezahltes Abo, ausreichend MH-Tokens und den konfigurierten KI-Anbieter.

**Hauptablauf:**
1. Nutzer prüft Briefingstand, gewünschte Formate und Paketumfang.
2. MH zeigt für verwaltete Konten den geltenden Verbrauch von 50 MH-Tokens pro Generierung; der Nutzer bestätigt ausdrücklich.
3. MH erstellt die Entwürfe und kennzeichnet sie als ungeprüft. Demo-Ergebnisse werden als Vorlagen gekennzeichnet.
4. Nutzer bearbeitet die Texte, speichert sie und bereitet die Freigabe vor. Das Einschalten einer Bewerbungsseite erfolgt separat.

**Ergebnis:** Gespeicherte Entwürfe mit Bezug auf den verwendeten Briefingstand, noch ohne Freigabe oder Veröffentlichung.

**Abweichungen:** Ohne Anbieter oder bei unvollständigem Ergebnis bleibt der Auftrag fehlgeschlagen und verbraucht keine MH-Tokens. Ein wiederholter identischer Auftrag belastet nicht erneut. Ein bewusst neuer Auftrag ist eine neue, vorher bestätigte Generierung. Ein Antwortentwurf für einen Bewerber ist kein Kampagnenpaket und erhält hier keinen neuen Preis.

**Abnahmekriterien:**
- **Z03-A1:** Fehlerhafte Generierung lässt Briefing und vorhandene Entwürfe erhalten und verändert das MH-Guthaben nicht.
- **Z03-A2:** Wiederholung desselben bestätigten Auftrags erzeugt keine doppelte Belastung.
- **Z03-A3:** Änderungen am Briefing verändern gespeicherte Texte nicht stillschweigend; Nutzer erkennt, dass eine erneute fachliche Prüfung nötig ist.
- **Z03-A4:** Erstellung und Speichern lösen weder Veröffentlichung noch Bewerbernachricht aus.

**Ist-Bezug:** Sechs Textformate, Bearbeitung, Versionsverlauf, Generierungsbestätigung und Tokenlogik existieren. Echte KI-Qualität und Anbieterkosten sind noch nicht nachgewiesen.

**Bewertungsfrage / Entscheidung offen:** Welche zwei oder drei Formate nutzt die erste Branche wirklich? Ein reduzierter zukünftiger Umfang muss separat bestätigt werden; derzeitige sechs Formate und 50-Token-Regel bleiben bestehen. **Abhängigkeiten:** UC-Z02; D05.

### UC-Z04 – Inhalte prüfen und ausdrücklich freigeben

**Alltagssituation:** Ein Bearbeiter hat Entwürfe vorbereitet. Die zuständige Person muss Aussagen über Aufgaben und Angebot vor der Verwendung bestätigen.

**Akteur / Ziel:** Eine nach bestehenden Rollen berechtigte Person möchte eine bestimmte gespeicherte Fassung freigeben oder Änderungen anfordern.

**Nutzenhypothese:** Rückfragen und falsche Versprechen werden vor der Veröffentlichung erkannt; Entscheidungen bleiben nachvollziehbar.

**Auslöser / Voraussetzungen:** Entwürfe aus UC-Z03 sind gespeichert und zur Prüfung gegeben. Zuständige Prüfer besitzen bestehende Freigaberechte. UC-Z12 kann optional vorher genutzt werden.

**Hauptablauf:**
1. Prüfer betrachtet vollständige Texte und das zugrunde liegende Briefing.
2. Prüfer kontrolliert Angaben, offene Punkte, Bewerbungsmöglichkeit und Ansprechpartner.
3. Prüfer fordert konkrete Änderungen an oder bestätigt die gespeicherte Fassung.
4. MH dokumentiert Entscheidung und Beteiligte und zeigt den nächsten Veröffentlichungs- oder Überarbeitungsschritt.

**Ergebnis:** Eine nachvollziehbare interne Freigabe oder ein konkreter Änderungsauftrag. Vorhandene Firmen-Admins und berechtigte User behalten ihre Freigaberechte; ein Vier-Augen-Prinzip wird hier nicht eingeführt.

**Abweichungen:** Ungespeicherte Änderungen müssen vor Freigabe geklärt werden. Eine nachträglich geänderte Fassung darf die alte Bestätigung nicht als eigene Veröffentlichungsbestätigung verwenden. Der Plattform-Admin und die Kundenrolle erteilen keine Kundenfreigabe.

**Abnahmekriterien:**
- **Z04-A1:** Freigeben allein veröffentlicht keinen Beitrag und versendet keine Bewerbernachricht; bestehende interne Statusbenachrichtigungen bleiben möglich.
- **Z04-A2:** Nach Änderungswunsch sind Kommentar, Akteur und Rückkehr zur Bearbeitung nachvollziehbar.
- **Z04-A3:** Nicht berechtigte Nutzer können auch außerhalb der Oberfläche keine Freigabe erteilen.

**Ist-Bezug:** Review, Freigabe, Änderungswünsche, Historie und interne Statusmails existieren. „Live“ bleibt interner Freigabestatus.

**Bewertungsfrage / Entscheidung offen:** Benötigt ein kleiner Betrieb überhaupt einen separaten Prüfer? Wie groß ist die heutige Wartezeit auf eine Entscheidung? **Abhängigkeiten:** UC-Z03; D03.

### UC-Z05 – Freigegebene Inhalte gezielt veröffentlichen

**Alltagssituation:** Die Anzeige ist freigegeben. Der Betrieb möchte sie auf seiner eigenen Seite oder über einen konkret gewählten externen Kanal verwenden.

**Akteur / Ziel:** Berechtigter Bearbeiter möchte den Inhalt am richtigen Ziel bereitstellen und wissen, ob die Veröffentlichung nachweisbar erfolgt ist.

**Nutzenhypothese:** Weniger Übertragungsarbeit und klare Unterscheidung zwischen fertig, exportiert und tatsächlich veröffentlicht.

**Auslöser / Voraussetzungen:** UC-Z04 ist abgeschlossen. Bewerbungsmöglichkeit, Ziel und Kontaktverantwortung sind geprüft. Für integrierte Veröffentlichung bestehen die nötigen Kundenberechtigungen und eine geprüfte Anbieteranbindung; für manuelle Verwendung genügt ein Export.

**Hauptablauf:**
1. Nutzer wählt Kanal und entweder Export/manuelle Veröffentlichung oder eine verfügbare integrierte Aktion.
2. Nutzer prüft Inhalt, zugehörige Firmen-Seite und funktionierenden Bewerbungslink.
3. Nutzer bestätigt die konkrete externe Aktion. Ein Export bestätigt nur die Bereitstellung des Materials.
4. Bei integriertem Versand zeigt MH das bestätigte Ergebnis oder den unklaren Status. Bei manueller Veröffentlichung dokumentiert der Nutzer Zeitpunkt und, soweit vorhanden, einen Nachweislink.
5. MH unterscheidet Anbieterbestätigung von manueller Dokumentation.

**Ergebnis:** Material ist exportiert, manuell dokumentiert oder durch den Anbieter bestätigt veröffentlicht; Herkunft und Sicherheit des Status sind erkennbar.

**Abweichungen:** Fehlende Verbindung sperrt die integrierte Aktion, bietet aber eine manuelle Alternative. Ein Timeout erzeugt keinen automatischen erneuten Post. Nach Text-, Ziel- oder Linkänderung ist eine neue Bestätigung erforderlich. Eine deaktivierte Bewerbungsseite verhindert deren Nutzung als Ziel einer neuen Veröffentlichung.

**Abnahmekriterien:**
- **Z05-A1:** Firmen A und B veröffentlichen ausschließlich auf ihrem jeweils autorisierten Ziel; fremde Seiten sind nicht auswählbar.
- **Z05-A2:** Ein Export wird nicht als nachgewiesener öffentlicher Beitrag angezeigt.
- **Z05-A3:** Ein unklarer Anbieterstatus bleibt als unklar erkennbar und führt nicht automatisch zu einem zweiten Beitrag.
- **Z05-A4:** Keine Aktion dieses Falls bucht bezahlte Werbung oder verspricht Reichweite.

**Ist-Bezug:** Export ist vorhanden. Separates Facebook-Publishing ist lokal implementiert und extern unbestätigt. Instagram-Veröffentlichung und weitere Anbieter sind daraus nicht ableitbar.

**Bewertungsfrage / Entscheidung offen:** Welche ein oder zwei Kanäle erreichen die erste Zielgruppe tatsächlich? Reicht ein manueller Pilot? **Abhängigkeiten:** UC-Z04; vorbereitete Bewerbungsmöglichkeit aus UC-Z06; D06.

### UC-Z06 – Mobil und ohne Firmenkonto Kontakt aufnehmen

**Alltagssituation:** Eine interessierte Person öffnet den Bewerbungslink auf dem Smartphone und möchte Kontakt aufnehmen, ohne erst ein umfangreiches Profil anzulegen.

**Akteur / Ziel:** Bewerber möchte die Stelle verstehen und eine minimale Bewerbung zuverlässig absenden.

**Nutzenhypothese:** Weniger Abbruch durch unnötige Schritte; bessere Sicht auf tatsächlich eingegangene Kontakte.

**Auslöser / Voraussetzungen:** Aufruf einer ausdrücklich aktivierten Bewerbungsseite für eine freigegebene, noch offene Stelle. Kontaktverantwortung und die freigegebenen Informations-/Aufbewahrungsregeln sind festgelegt. Dieser öffentliche Fall benötigt kein Firmenkonto und keine MH-Tokens des Bewerbers.

**Hauptablauf:**
1. Bewerber sieht Firma, Stelle, Standort, Angebot, Ansprechpartner und verständliche Hinweise zur Verarbeitung seiner Daten.
2. Bewerber gibt die für den Erstkontakt bestätigten Mindestangaben ein. Als Pilotvorschlag gelten Name, E-Mail und optional eine Nachricht; Telefon, Lebenslauf und Zusatzfragen sind separate Entscheidungen.
3. Bewerber prüft die Eingaben und sendet die Kontaktaufnahme bewusst ab.
4. MH speichert den Eingang und zeigt erst nach erfolgreicher Speicherung eine Bestätigung.
5. Der Eingang steht den berechtigten Personen der Firma zur Bearbeitung zur Verfügung. Eine Empfangsmail ist optional und erfordert eine gesonderte Versandentscheidung.

**Ergebnis:** Genau ein nachvollziehbarer Eingang für denselben Absendeversuch, der zur richtigen Firma und Stelle gehört. Eine Quellzuordnung wird nur vorgenommen, wenn ein gültiger passender Link vorliegt.

**Abweichungen:** Bei Eingabefehlern bleiben korrigierbare Felder erhalten. Bei unklarem Absendeergebnis wird nicht fälschlich Erfolg behauptet; eine Wiederholung desselben Versuchs erzeugt keinen zweiten Eingang. Eine geschlossene Seite nimmt keine neue Bewerbung an. Ohne Herkunftslink bleibt die Quelle unbekannt.

**Abnahmekriterien:**
- **Z06-A1:** Auf einem Smartphone ist der Erstkontakt ohne Firmenregistrierung möglich; Pflichtangaben sind erkennbar.
- **Z06-A2:** Zweimaliges Absenden desselben Versuchs erzeugt einen Eingang; eine tatsächlich neue Bewerbung wird nicht allein wegen gleicher E-Mail unterdrückt.
- **Z06-A3:** Eine Bestätigung erscheint erst nach gespeichertem Eingang; eine reine Klickzählung genügt nicht.
- **Z06-A4:** Fremde Firmen, Kundenleser und öffentliche Besucher erhalten keinen Zugriff auf persönliche Bewerbungsdaten.

**Ist-Bezug:** Gehostete Bewerbungsseiten, verschlüsselte Kontaktdaten, serverbestätigte Eingänge und Links existieren im Code. Produktive Abnahme, Aufbewahrungsfreigabe und der vollständige öffentliche Ablauf bleiben gesondert zu prüfen.

**Bewertungsfrage / Entscheidung offen:** Genügen diese Angaben für einen sinnvollen Erstkontakt in der Pilotbranche? Welche Rückmeldung soll der Bewerber wann erhalten? **Abhängigkeiten:** UC-Z02, UC-Z04; D03, D07, D08.

### UC-Z07 – Neue Bewerbungen übernehmen und beantworten

**Alltagssituation:** Drei Kontakte sind eingegangen. Eine zuständige Person soll erkennen, welche noch auf eine erste Antwort warten.

**Akteur / Ziel:** Berechtigter Bearbeiter möchte einen Eingang übernehmen und eine persönliche erste Reaktion dokumentieren.

**Nutzenhypothese:** Weniger verlorene Kontakte und kürzere tatsächliche Reaktionszeiten.

**Auslöser / Voraussetzungen:** Ein Eingang aus UC-Z06 liegt vor. Eine verantwortliche Person und die Berechtigung für persönliche Bewerbungsdaten sind festgelegt. Als ersten Kontaktweg schlägt der Pilot E-Mail oder manuell dokumentierten persönlichen Kontakt vor.

**Hauptablauf:**
1. Bearbeiter sieht neue Eingänge mit Stelle, Eingangszeit, Zuständigkeit und nächstem Schritt.
2. Bearbeiter übernimmt die Bearbeitung; andere berechtigte Personen erkennen die Übernahme.
3. Bearbeiter liest die Bewerbung und formuliert eine Antwort. Ein optionaler Textvorschlag ergänzt keine unbelegten Zusagen.
4. Bearbeiter prüft Empfänger und Inhalt und bestätigt den Versand oder dokumentiert einen tatsächlich erfolgten manuellen Kontakt.
5. MH hält Ergebnis, Zeitpunkt und nächste Aufgabe fest.

**Ergebnis:** Die Bewerbung hat eine zuständige Person und eine nachvollziehbare erste Reaktion oder weiterhin einen offenen/unklaren Versandstatus.

**Abweichungen:** Bei gleichzeitigem Übernehmen bleibt die Verantwortung eindeutig. Eine abgewiesene oder unklare Nachricht markiert die Bewerbung nicht als erfolgreich beantwortet. Externe Telefonate sind manuelle Angaben. Weitergabe an andere Nutzer einer Firma erfordert deren Bewerbungsrechte.

**Abnahmekriterien:**
- **Z07-A1:** Lesen, Übernehmen und Erzeugen eines Antwortentwurfs zählen nicht als erfolgte Antwort.
- **Z07-A2:** Bei gescheitertem Versand bleibt die Aufgabe offen; Entwurf und Bewerbung bleiben erhalten.
- **Z07-A3:** Wiederholte Bestätigung desselben Nachrichtenauftrags erzeugt keinen neuen fachlichen Auftrag; unklarer Versand wird vor einer Wiederholung geprüft. Eine mögliche doppelte SMTP-Zustellung wird nicht als technisch ausgeschlossen behauptet.
- **Z07-A4:** Akteur, Zeitpunkt und Nachweisart der ersten Reaktion sind sichtbar; personenbezogene Inhalte bleiben auf berechtigte Firmenmitglieder begrenzt.

**Ist-Bezug:** Bewerbungsliste und Versandbausteine existieren. Übernahme, persönliche Bewerberantworten, deren Workflow und Anbieterbestätigung sind neue vorgeschlagene Fähigkeiten.

**Bewertungsfrage / Entscheidung offen:** Wie reagieren Betriebe heute, und welcher Kontaktweg wird wirklich genutzt? Soll eine Antwortfunktion im Produkt entstehen oder zunächst manuell erprobt werden? **Abhängigkeiten:** UC-Z06; D03, D08, D09.

### UC-Z08 – Ein Bewerbergespräch verbindlich vereinbaren

**Alltagssituation:** Die zuständige Person möchte mit einem Bewerber sprechen. Ein gesendeter Terminvorschlag wurde aber noch nicht bestätigt.

**Akteur / Ziel:** Bearbeiter und Bewerber möchten einen gemeinsamen Termin mit klarem Ort oder Kontaktweg vereinbaren.

**Nutzenhypothese:** Weniger Hin-und-her und zuverlässige Unterscheidung zwischen Vorschlag und vereinbartem Gespräch.

**Auslöser / Voraussetzungen:** Der Bearbeiter entscheidet menschlich, ein Gespräch anzubieten. Ein vorhandener Kontakt und die nötigen Bewerbungsrechte liegen vor. Externe Kalenderintegration ist nicht erforderlich.

**Hauptablauf:**
1. Bearbeiter hält die Entscheidung zum Gespräch und einen oder mehrere Vorschläge mit Datum, Uhrzeit, Zeitzone und Ort/Kontaktweg fest.
2. Bearbeiter übermittelt die Vorschläge nach eigener Prüfung, integriert oder manuell.
3. Bewerber bestätigt einen Termin über den vereinbarten Kontaktweg; Bearbeiter dokumentiert die Bestätigung.
4. MH zeigt das Gespräch als vereinbart und hält die zuständige Person fest.
5. Nach dem Termin dokumentiert der Bearbeiter „stattgefunden“, „abgesagt“ oder „nicht erschienen“ und den nächsten menschlich gewählten Schritt.

**Ergebnis:** Ein nachweisbar vereinbarter Termin oder ein weiterhin offener Vorschlag, später ergänzt um das tatsächliche Ergebnis.

**Abweichungen:** Ohne Bestätigung bleibt das Gespräch vorgeschlagen. Bei Verschiebung wird die alte Vereinbarung nachvollziehbar ersetzt. Eine automatische Kandidatenauswahl, Absage oder ein Vertragsangebot ist kein Teil dieses Falls.

**Abnahmekriterien:**
- **Z08-A1:** Versenden eines Vorschlags erhöht nicht die Zahl vereinbarter oder tatsächlich geführter Gespräche.
- **Z08-A2:** Termin, Kontaktweg, Verantwortlicher und Bestätigung sind nachvollziehbar; Kalenderfreigaben werden nicht vorausgesetzt.
- **Z08-A3:** Eine Absage lässt den bisherigen Verlauf erhalten und entfernt den Termin aus der Liste bevorstehender Gespräche.

**Ist-Bezug:** Kein bestätigter Termin- oder Bewerberentscheidungsworkflow im bestehenden Recruiting-Kampagnenumfang; Erweiterungsvorschlag.

**Bewertungsfrage / Entscheidung offen:** Spart schon eine manuelle Terminübersicht Zeit oder braucht es später echte Kalenderintegration? **Abhängigkeiten:** UC-Z07; D10.

### UC-Z09 – Liegengebliebene Aufgaben erkennen und weitergeben

**Alltagssituation:** Eine zuständige Person ist abwesend; eine Freigabe oder Bewerberreaktion bleibt liegen.

**Akteur / Ziel:** Firmenverantwortliche Person möchte fällige Arbeit erkennen und an eine berechtigte Vertretung weitergeben.

**Nutzenhypothese:** Weniger verspätete Entscheidungen und unbeantwortete Kontakte.

**Auslöser / Voraussetzungen:** Ein offener nächster Schritt hat einen vereinbarten Termin überschritten oder eine Zuständigkeit fällt weg. Frist und mögliche Vertretungen sind firmenbezogen festgelegt. Es gilt keine automatisch erfundene branchenweite Antwortfrist.

**Hauptablauf:**
1. MH zeigt offene Aufgabe, Frist, zuständige Person und den Grund für die Fälligkeit.
2. Berechtigte Person prüft den tatsächlichen Stand und erledigt die Aufgabe, setzt begründet eine neue Frist oder übergibt sie.
3. Bei Übergabe übernimmt eine weiterhin berechtigte Vertretung den konkreten nächsten Schritt.
4. MH dokumentiert die Änderung und aktualisiert die offene Aufgabenliste.

**Ergebnis:** Die Aufgabe hat einen nachvollziehbaren Stand und eine gültige Verantwortung. Erinnerungen entscheiden nichts über Bewerber.

**Abweichungen:** Bereits erledigte Aufgaben erzeugen keine weitere Erinnerung. Ein ausgeschiedener Nutzer erhält keine neuen personenbezogenen Informationen. Eine fehlgeschlagene Erinnerungszustellung löscht die Aufgabe nicht. Ohne externe Benachrichtigung reicht im ersten Pilot eine sichtbare Aufgabenübersicht.

**Abnahmekriterien:**
- **Z09-A1:** Nur tatsächlich offene Aufgaben mit überschrittener Frist erscheinen als überfällig.
- **Z09-A2:** Übergabe funktioniert nur an berechtigte Personen derselben Firma und bleibt nachvollziehbar.
- **Z09-A3:** Erinnerung oder Fristablauf erzeugt weder automatische Bewerberabsage noch öffentliche Aktion.

**Ist-Bezug:** Interne Kampagnenstatusmails existieren. Aufgabenfristen, Vertretung und Bearbeitungserinnerungen sind eigenständige Erweiterungsvorschläge.

**Bewertungsfrage / Entscheidung offen:** Wie oft ist fehlende Nachverfolgung tatsächlich das Problem? Welche Frist ist realistisch, und welche Erinnerung wäre hilfreich statt störend? **Abhängigkeiten:** UC-Z01 und mindestens einer aus UC-Z04/07/08; D03, D09.

### UC-Z10 – Aufwand und Ergebnisse nachvollziehen

**Alltagssituation:** Nach zwei Wochen möchte der Betrieb wissen, ob der Ablauf Zeit spart und welcher Kanal zu Kontakten oder Gesprächen geführt hat.

**Akteur / Ziel:** Firmenverantwortliche Person möchte beobachteten Aufwand und Ergebnisse anhand nachvollziehbarer Daten beurteilen.

**Nutzenhypothese:** Entscheidungen über Kanäle und weitere Nutzung werden besser begründet.

**Auslöser / Voraussetzungen:** Regelmäßige Durchsicht oder Ende eines Pilotdurchlaufs. Erfassungszeitraum, Datenquellen und Definitionen sind vereinbart. Eine simple manuelle Erfassung ist für den Pilot zulässig.

**Hauptablauf:**
1. Nutzer wählt Stelle/Kampagne und Zeitraum.
2. MH zeigt vorhandene Linkaufrufe, bestätigte Bewerbungseingänge, dokumentierte erste Reaktionen und vereinbarte/geführte Gespräche; nicht verfügbare Werte bleiben als unbekannt erkennbar.
3. Nutzer ergänzt tatsächlichen Arbeitsaufwand, manuell bekannte Ergebnisse und gegebenenfalls externe Werbeausgaben; Datenherkunft bleibt sichtbar.
4. Nutzer beurteilt die Passung der Kontakte anhand selbst bestätigter stellenbezogener Kriterien und hält die Begründung fest. Es gibt keine automatische Eignungsbewertung.
5. Nutzer entscheidet über eine konkrete Veränderung beim nächsten Durchlauf.

**Ergebnis:** Eine nachvollziehbare Übersicht mit begrenzter Aussagekraft und einem dokumentierten Lernpunkt; kein automatisch behaupteter Wirksamkeitsnachweis.

**Abweichungen:** Fehlende externe Anbindung ist keine Nullzahl. Linkaufrufe können mehrfach oder automatisiert erfolgen und sind keine eindeutigen Personen. Ein unbekannter Ursprung wird keinem Kanal zugeschrieben. Ohne Vergleichsaufwand wird keine Zeitersparnis berechnet. Kleine Stichproben begründen keine sichere Kanalempfehlung.

**Abnahmekriterien:**
- **Z10-A1:** Kennzahlen unterscheiden Quelle, Zeitraum und unbekannte von tatsächlich null beobachteten Werten.
- **Z10-A2:** Klicks, Eingänge, vereinbarte Gespräche und geführte Gespräche werden getrennt ausgewiesen; Doppelerfassungen desselben nachgewiesenen Ereignisses zählen nicht doppelt.
- **Z10-A3:** Zeit bis zur ersten Reaktion verwendet tatsächliche Eingangs-/Reaktionszeiten und kennzeichnet manuelle Angaben; ein Entwurf ist keine Reaktion.
- **Z10-A4:** Zeitersparnis ist nur mit dokumentiertem Vergleich und Hinweis auf Begleitung/Unterschiede darstellbar; sie wird nicht automatisch MH allein zugeschrieben.

**Ist-Bezug:** Manuelle Kampagnenmetriken, Linkaufrufe und serverbestätigte Bewerbungsquittungen existieren. Reaktions-, Gesprächs- und Aufwandskennzahlen verlangen neue erfasste Ereignisse.

**Bewertungsfrage / Entscheidung offen:** Welche Kennzahl würde den Betrieb zu einer anderen Handlung bewegen? Welcher Erfassungsaufwand wird akzeptiert? **Abhängigkeiten:** UC-Z05/06; für weitere Kennzahlen UC-Z07/08; D11.

### UC-Z11 – Suche beenden und beim nächsten Bedarf wiederverwenden

**Alltagssituation:** Die Stelle ist besetzt oder die Suche wird unterbrochen. Einige Monate später entsteht ein ähnlicher Bedarf.

**Akteur / Ziel:** Firmenverantwortliche Person möchte die Suche bewusst schließen und bestätigte Arbeitsgrundlagen später wiederverwenden.

**Nutzenhypothese:** Weniger veraltete offene Anzeigen und weniger Wiederholungsarbeit beim nächsten Bedarf.

**Auslöser / Voraussetzungen:** Menschliche Entscheidung zur Besetzung, Pause oder Beendigung; später neuer Bedarf. Schreibzugang und Zuständigkeit liegen vor.

**Hauptablauf:**
1. Nutzer dokumentiert Abschlussgrund und prüft offene Bewerberreaktionen.
2. Nutzer beendet neue Kontaktaufnahme über die eigene Bewerbungsseite und erhält eine Liste weiterer öffentlicher Beiträge, die manuell oder durch separate bestätigte Anbieteraktionen geprüft werden müssen.
3. Vorhandene Bewerbungen folgen den zuvor festgelegten Aufbewahrungs-/Löschregeln; fachlicher Abschluss ersetzt diese Regeln nicht.
4. Bei neuem Bedarf übernimmt Nutzer Firmenangaben und geeignete Materialien in einen neuen Entwurf.
5. Nutzer prüft insbesondere Vergütung, Arbeitszeiten, Standort und Ansprechpartner erneut. Personenbezogene Bewerbungen werden nicht in die neue Suche kopiert.

**Ergebnis:** Die alte Suche hat einen sichtbaren Abschluss; ein neuer Bedarf beginnt mit geprüften Vorlagen und ohne alte Bewerberkontakte oder alte Freigaben.

**Abweichungen:** Schließen der eigenen Seite entfernt keinen bestehenden externen Beitrag. Unbeantwortete Kontakte bleiben zur menschlichen Bearbeitung sichtbar, soweit sie noch aufbewahrt werden dürfen. Eine wiederverwendete Textvorlage erfordert neue Prüfung vor Veröffentlichung.

**Abnahmekriterien:**
- **Z11-A1:** Nach Abschluss nimmt die eigene Seite keine neuen Kontakte an; vorhandene externe Beiträge werden nicht fälschlich als gelöscht ausgewiesen.
- **Z11-A2:** Wiederverwendung kopiert keine persönlichen Bewerbungsdaten und keine Veröffentlichungsbestätigung.
- **Z11-A3:** Wiederverwendung bestehender Angaben erzeugt nicht automatisch einen kostenpflichtigen Generierungsauftrag; eine neue Generierung wird separat bestätigt.
- **Z11-A4:** Ein fachlicher Abschluss und ein Datenlöschvorgang sind erkennbar unterschiedliche Vorgänge; die bestätigten Fristen gelten weiter.

**Ist-Bezug:** Firmenprofile, gespeicherte Texte und abschaltbare Bewerbungsseiten sind Ansatzpunkte. Durchgängiger Abschluss mit offenen Bewerberaufgaben und kontrollierter Wiederverwendung ist ein Zielvorschlag.

**Bewertungsfrage / Entscheidung offen:** Wie häufig tritt ähnlicher Bedarf auf? Welche Vorlagen sparen tatsächlich Arbeit? **Abhängigkeiten:** UC-Z06, UC-Z10; D07.

### UC-Z12 – Eine fachliche Prüfrunde zu Entwürfen konsultieren

**Alltagssituation:** Der Betrieb möchte vor der Freigabe wissen, welche Aussagen unklar sind und wie das Paket verbessert werden könnte.

**Akteur / Ziel:** Bearbeiter möchte begründete Hinweise und alternative Ideen aus mehreren fachlichen Perspektiven erhalten.

**Nutzenhypothese:** Relevante Schwächen werden früher sichtbar; konkrete Alternativen erleichtern die Verbesserung. Mehr Text oder mehrere Stimmen allein gelten nicht als Nutzen.

**Auslöser / Voraussetzungen:** Bestätigtes Briefing und gespeicherte Entwürfe liegen vor. Die optionale Prüfrunde ist fachlich freigegeben. Anbieter, Kosten, Datenumfang und Kundenbestätigung sind vor automatisierter Nutzung separat festgelegt.

**Hauptablauf:**
1. Nutzer wählt die konkrete Frage und das zu prüfende Material.
2. Rollen für Recruiting, Bewerberverständlichkeit und Kanal-/Umsetzungsqualität betrachten das Material. Sie sind fachliche Hilfen, keine realen prominenten Personen.
3. Jede Rolle benennt eine konkrete Stärke, eine relevante offene Frage oder Schwäche und eine begründete Alternative. Fakten, Annahmen und Zukunftsideen bleiben erkennbar getrennt.
4. Die Zusammenführung zeigt Übereinstimmung, tatsächliche Unterschiede und einen möglichen nächsten Versuch; sie erzwingt keinen Streit.
5. Nutzer übernimmt, bearbeitet oder verwirft Vorschläge. Geänderte Inhalte durchlaufen UC-Z04.

**Ergebnis:** Nachvollziehbare Empfehlungen und eine menschliche Entscheidung, ohne automatische Textänderung, Freigabe oder Veröffentlichung.

**Abweichungen:** Fehlende Fakten führen zu Rückfragen und nicht zu erfundenen Benefits. Ein gescheiterter Anbieteraufruf lässt vorhandene Materialien bestehen. Ohne sinnvollen Verbesserungsvorschlag darf die Prüfrunde das ausdrücklich sagen. Bewerberdaten sind kein Input dieses Falls.

**Abnahmekriterien:**
- **Z12-A1:** Jeder konkrete Einwand ist am Briefing oder Entwurf nachvollziehbar oder ausdrücklich als zu prüfende Annahme gekennzeichnet.
- **Z12-A2:** Empfehlungen behaupten weder authentische prominente Meinungen noch rechtliche Freigabe, garantierte Reichweite oder Bewerbereignung.
- **Z12-A3:** Ohne menschliche Übernahme bleiben gespeicherte Inhalte unverändert; Übernahme erteilt keine Freigabe.
- **Z12-A4:** Ein automatisierter Aufruf ist erst nach gesonderter Preis-/Verbrauchsentscheidung möglich; bestehende 50-Token-Kampagnenregeln werden nicht stillschweigend auf diesen neuen Fall übertragen.

**Ist-Bezug:** Die Gesprächsrollen wurden konzeptionell im Chat entwickelt. Eine produktintegrierte Prüfrunde ist nicht als implementiert bestätigt.

**Bewertungsfrage / Entscheidung offen:** Verbessert sie Material oder Entscheidungen spürbar gegenüber einer einzelnen guten Prüfung? Welche Hinweise übernimmt der Betrieb tatsächlich? **Abhängigkeiten:** UC-Z02/03; D12. Kein Pflichtschritt für UC-Z04.

## 5. Fachliche Entscheidungen vor einer Umsetzung

| ID | Entscheidung | Aktueller Stand / sinnvolle Klärung |
| --- | --- | --- |
| D01 | Erste Branche und typischer Betrieb | Offen; drei erreichbare Betriebe mit echtem Personalbedarf bestimmen |
| D02 | Wichtigster Engpass | Offen; letzten tatsächlichen Besetzungsfall beobachten und Warte-/Arbeitszeiten dokumentieren |
| D03 | Zuständigkeiten und Rechte | Bestehende Kampagnen-/Freigaberechte bleiben; neue Bewerbungs-/Aufgabenrechte, Vertretung und Ausscheiden ausdrücklich klären |
| D04 | Briefing-Mindestangaben | Branchenspezifisch klären; unbekannte Angaben zulassen, Bedingungen für Entwurf/Freigabe ausdrücklich unterscheiden |
| D05 | Zukünftiger Paketumfang | Offen; derzeit sechs Formate und 50 MH-Tokens pro Generierung bleiben maßgeblich |
| D06 | Pilotkanäle und Veröffentlichung | Ein bis zwei reale Wege wählen; Export/manuelle Veröffentlichung zulässig; integrierte Anbieter separat abnehmen |
| D07 | Datenumfang, Aufbewahrung, Löschung | Vor echten Bewerberdaten fachlich und rechtlich bestätigen; Abschluss darf keine unbeschlossene Aufbewahrung auslösen |
| D08 | Bewerberkontakt und Empfangsbestätigung | Mindestfelder und tatsächlich genutzten Kontaktweg wählen; erste Version kann manuell begleitet werden |
| D09 | Fristen und Erinnerungen | Nutzerbedarf und realistische Reaktionsfrist prüfen; keine pauschale automatische Absage |
| D10 | Terminbestätigung | Für Pilot manuell dokumentierbare Zustimmung; Kalenderintegration erst nach Bedarfsklärung |
| D11 | Kennzahlen und Erfolgskriterien | Vergleichsaufwand, Beobachtungszeitraum, menschliche Passungskriterien und mögliche Stoppkriterien vor Pilot vereinbaren |
| D12 | Fachliche Prüfrunde | Optional; Nutzen gegenüber Einzelprüfung sowie Anbieter, Datenumfang und Kosten getrennt bewerten |

## 6. Bewertungsbogen

Alle Felder bleiben absichtlich unbewertet. Fehlende Erkenntnisse werden als „unbekannt“ geführt, nicht als schlechte Bewertung. Ein Gefühl für den Nutzen und ein beobachteter Nutzerfall sind getrennte Angaben.

**Skalen für deine Bewertung:** Schmerz und Häufigkeit: 1 = gering/selten, 5 = stark/häufig. Erwarteter Nutzen: 1 = gering, 5 = hoch. Aufwand und Risiko: 1 = gering, 5 = hoch; zunächst grobe Einschätzung, keine technische Schätzung. Ein Summenscore entscheidet nicht automatisch über Freigabe.

| ID | Schmerz / Häufigkeit | Erwarteter Nutzen | Beobachteter Beleg / offene Frage | Aufwand / Risiko | Entscheidung / Begründung |
| --- | --- | --- | --- | --- | --- |
| UC-Z01 | Offen | Offen | Offen | Offen | Offen |
| UC-Z02 | Offen | Offen | Offen | Offen | Offen |
| UC-Z03 | Offen | Offen | Offen | Offen | Offen |
| UC-Z04 | Offen | Offen | Offen | Offen | Offen |
| UC-Z05 | Offen | Offen | Offen | Offen | Offen |
| UC-Z06 | Offen | Offen | Offen | Offen | Offen |
| UC-Z07 | Offen | Offen | Offen | Offen | Offen |
| UC-Z08 | Offen | Offen | Offen | Offen | Offen |
| UC-Z09 | Offen | Offen | Offen | Offen | Offen |
| UC-Z10 | Offen | Offen | Offen | Offen | Offen |
| UC-Z11 | Offen | Offen | Offen | Offen | Offen |
| UC-Z12 | Offen | Offen | Offen | Offen | Offen |

Zulässige Entscheidungen: **behalten**, **ändern**, **im Pilot beobachten**, **später**, **verwerfen**. Zusätzlich sind Datum, Entscheider und konkret vereinbarte Änderungen festzuhalten. „Behalten“ bestätigt den fachlichen Bedarf; „zur Umsetzung freigegeben“ ist ein späterer eigener Beschluss.

**Vorschlag für die erste Bewertungsrunde:** UC-Z02, UC-Z05 und UC-Z07 nebeneinander betrachten. Sie prüfen die drei unterschiedlichen Engpässe Angebot, Erreichen von Interessierten und Reaktion. Erst wenn der wichtigste Engpass klarer ist, sollte die erste Automatisierung festgelegt werden. UC-Z01/04/06/08/10/11 bleiben für einen vollständigen begleiteten Ablauf nötig, können im Pilot teilweise manuell durchgeführt werden.

## 7. Pilot zur Prüfung der Use Cases

**Vorschlag, noch zu bestätigen:** Drei Betriebe einer Branche werden jeweils bei einer realen Suche begleitet. Die Dienstleistung wird offengelegt; bezahlte Produktaktionen behalten bestehende Zugangs-/Kostenregeln. Echte Bewerberdaten und öffentliche Anbieteraktionen beginnen erst nach den jeweils nötigen Betriebsfreigaben. Eine Übung mit fiktiven Daten ist kein Beleg für Bewerbergewinnung oder Zahlungsbereitschaft.

Vor Beginn pro Betrieb festhalten:

- Letzter vergleichbarer Besetzungsfall, vorhandene Werkzeuge, bekannte Kosten und Arbeits-/Wartezeiten; Erinnerungsschätzungen kennzeichnen.
- Wichtigster vermuteter Engpass und die Use Cases, die ihn verbessern sollen.
- Zuständige Personen, tatsächlich genutzte Kanäle, erlaubter Datenumfang und Kontaktweg.
- Vereinbarter Beobachtungszeitraum, Zielgrößen und Kriterien für Änderung/Abbruch. Zahlen werden vorab gemeinsam gewählt, nicht nachträglich passend gemacht.

Während des Pilots erfassen:

- Zeit für Briefing, Entwürfe, Korrekturen, Freigabe und Veröffentlichung; Zeit der Begleitung getrennt von Betriebszeit.
- Bestätigte Eingänge, manuelle/integrationsbestätigte erste Reaktion und vereinbarte/tatsächlich geführte Gespräche.
- Fehlende Angaben, technische Ausfälle und konkrete Hilfestellungen, die ohne Begleitung liegen geblieben wären.
- Welche Änderungen der Betrieb übernimmt und welche Funktionen er selbst erneut verwendet.

Nach dem Pilot entscheiden:

- Welche Use Cases haben nachweisbar Arbeit oder Wartezeit reduziert?
- Wo lag der tatsächliche Engpass, und lag er außerhalb des Werkzeugs?
- Welche Unterstützung müsste dauerhaft als Dienstleistung angeboten werden?
- Würde der Betrieb beim nächsten Bedarf wiederkommen? Zustimmung im Gespräch, konkrete Kaufzusage, echte Zahlung und tatsächliche Wiederverwendung werden getrennt dokumentiert.
- Welche Annahme wurde widerlegt und welche Funktion wird deshalb geändert oder gestrichen?

Drei Betriebe erlauben Lernen über Abläufe, aber keine belastbare Verallgemeinerung für einen ganzen Markt.

## 8. Spätere Übersetzung in Code

Für jeden ausgewählten Use Case entsteht nach deiner Bewertung ein eigener Umsetzungsauftrag mit:

1. Bestätigter fachlicher Fassung und den zugehörigen Entscheidungen D01–D12.
2. Festgelegten Akteuren, Daten, erlaubten Zustandsänderungen und Zugriffsrechten.
3. Klarer Abgrenzung zu vorhandenen MH-Funktionen und externen, noch ungeprüften Anbietern.
4. Prüfszenarien aus den IDs `Zxx-Ax`, einschließlich Fehlerfällen und fremder Firmenzugriffe.
5. Vorher/nachher beschriebenem Nutzerverhalten und einer ausdrücklich vereinbarten Umsetzungsfreigabe.

Dieses Dokument legt keine Endpunkte, Datenbanktabellen, Frameworks, KI-Modelle oder technischen Epics fest. Die detaillierte technische Lösung folgt erst aus dem bewerteten Bedarf.

## 9. Grundlagen dieser Fassung

Die Zielannahmen stammen aus der Beiratsdiskussion in diesem Chat. Ist-Bezüge wurden mit [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md), [README.md](../../README.md), [BILLING_SETUP.md](../../BILLING_SETUP.md), [AUTH_SETUP.md](../../AUTH_SETUP.md), dem vorhandenen Use-Case-Katalog und ausgewählten Implementierungen für KI, Bewerbungstracking und Social Publishing abgeglichen. Das ist eine fachliche Arbeitsfassung; Marktbedarf, Nutzerwirkung, rechtliche Freigabe und produktiver Anbieterbetrieb sind damit nicht nachgewiesen.

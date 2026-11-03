# Weitergabe der MH-Anforderungen

Die fachlichen **Use Cases** und die **nichtfunktionalen Anforderungen** sind bewusst getrennt von Modul- und Epic-Planung dokumentiert:

- `USE_CASES.md`: 19 nummerierte Nutzerziele mit Akteur, Ablauf, Ergebnis, Priorität und Umsetzungsstatus.
- `NICHTFUNKTIONALE_ANFORDERUNGEN.md`: 23 nummerierte Qualitäts- und Betriebsanforderungen mit vorgeschlagener Abnahme und Ist-Stand.
- `USE_CASES_ZIELBILD_REVIEW.md`: zwölf vorgeschlagene Nutzerziele (`UC-Z01` bis `UC-Z12`) für einen Recruiting-Helfer vom Personalbedarf bis zum Bewerbergespräch, mit Fehlerfällen, Abnahmekriterien, offenen Entscheidungen und einem Bewertungsbogen. Zielbild vom 1. Oktober 2026; UC-Z01 bis UC-Z11 am 2. Oktober zur Umsetzung freigegeben, UC-Z12 zurückgestellt.
- `ZIELBILD_IMPLEMENTIERUNG.md`: aktueller lokaler manueller Kernablauf, Testnachweise und Grenzen.
- `use_case_status.json` und `../../output/use-case-dashboard/index.html`: geprüfter Umsetzungsstand und interaktiver HTML-Bewertungsbogen.
- `../../output/pdf/MH_Use_Cases.pdf` und `../../output/pdf/MH_Nichtfunktionale_Anforderungen.pdf`: lesbare Versionen für Weitergabe und Freigabe.

**Arbeitsregel:** Markdown ist die editierbare Quelle. PDFs werden mit `build_pdfs.py` daraus neu erzeugt und sind Momentaufnahmen. Für konkrete Umsetzung werden IDs (`UC-..`, `NFA-..`) in Tickets referenziert. Offene Produktentscheidungen sind noch keine Freigabe.

Die Dokumente enthalten bewusst keine Zugangsdaten. Der bisherige Funktions-/Qualitätskatalog und seine PDFs beziehen sich auf den 28. September 2026; der neue Zielbildkatalog ist eine separate Arbeitsfassung vom 1. Oktober 2026 und hat noch keinen PDF-Export. Den aktuellen Implementierungsstand beschreibt `../../PROJECT_CONTEXT.md`.

- `DIGITALER_ZWILLING.md`: Architektur, vollständiger 56-Fälle-Katalog, HTML-Interface und ausdrücklich gestartete lokale Lösch-Batches.

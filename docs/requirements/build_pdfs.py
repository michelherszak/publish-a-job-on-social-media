"""Render the two MH requirements specifications from their Markdown sources."""
from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, KeepTogether, PageTemplate, Paragraph, Spacer

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "docs" / "requirements"
OUT = ROOT / "output" / "pdf"
OUT.mkdir(parents=True, exist_ok=True)

FONT_DIR = Path("/System/Library/Fonts/Supplemental")
pdfmetrics.registerFont(TTFont("ArialMH", str(FONT_DIR / "Arial.ttf")))
pdfmetrics.registerFont(TTFont("ArialMHBold", str(FONT_DIR / "Arial Bold.ttf")))
pdfmetrics.registerFontFamily("ArialMH", normal="ArialMH", bold="ArialMHBold")

GREEN = colors.HexColor("#173C2E")
LIME = colors.HexColor("#B6D354")
INK = colors.HexColor("#20342C")
MUTED = colors.HexColor("#5D7066")

STYLES = {
    "title": ParagraphStyle("title", fontName="ArialMHBold", fontSize=19, leading=23, textColor=GREEN, spaceAfter=9 * mm),
    "h2": ParagraphStyle("h2", fontName="ArialMHBold", fontSize=12.5, leading=16, textColor=GREEN, spaceBefore=7 * mm, spaceAfter=3 * mm, keepWithNext=True),
    "h3": ParagraphStyle("h3", fontName="ArialMHBold", fontSize=10.3, leading=14, textColor=GREEN, spaceBefore=5 * mm, spaceAfter=2 * mm, keepWithNext=True),
    "body": ParagraphStyle("body", fontName="ArialMH", fontSize=9, leading=13.4, textColor=INK, spaceAfter=2.2 * mm, alignment=TA_LEFT),
    "meta": ParagraphStyle("meta", fontName="ArialMH", fontSize=8.2, leading=11, textColor=MUTED, spaceAfter=5 * mm),
    "bullet": ParagraphStyle("bullet", fontName="ArialMH", fontSize=8.8, leading=13, textColor=INK, leftIndent=6 * mm, firstLineIndent=-4 * mm, spaceAfter=1.6 * mm),
}


def inline(text: str) -> str:
    text = text.replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-")
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r'<font color="#174D3A">\1</font>', text)
    return text


def paragraphs(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    items = []
    buf = []
    first = True

    def flush():
        nonlocal first
        if buf:
            content = " ".join(buf).strip()
            items.append(Paragraph(inline(content), STYLES["meta" if first else "body"]))
            first = False
            buf.clear()

    for line in lines:
        s = line.strip()
        if not s:
            flush()
            continue
        if s.startswith("# "):
            flush()
            items.append(Paragraph(inline(s[2:]), STYLES["title"]))
            first = True
        elif s.startswith("## "):
            flush()
            items.append(Paragraph(inline(s[3:]), STYLES["h2"]))
        elif s.startswith("### "):
            flush()
            items.append(Paragraph(inline(s[4:]), STYLES["h3"]))
        elif re.match(r"^(?:- |\d+\. )", s):
            flush()
            body = re.sub(r"^(?:- |\d+\. )", "", s)
            items.append(Paragraph("• " + inline(body), STYLES["bullet"]))
        else:
            buf.append(s)
    flush()
    return items


def decorate(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(GREEN)
    canvas.rect(0, height - 17 * mm, width, 17 * mm, stroke=0, fill=1)
    canvas.setFillColor(LIME)
    canvas.rect(20 * mm, height - 17 * mm, 18 * mm, 1.2 * mm, stroke=0, fill=1)
    canvas.setFont("ArialMHBold", 8)
    canvas.setFillColor(colors.white)
    canvas.drawString(20 * mm, height - 10 * mm, "MH  /  PRODUKTANFORDERUNGEN")
    canvas.setStrokeColor(colors.HexColor("#D7E0D9"))
    canvas.line(20 * mm, 16 * mm, width - 20 * mm, 16 * mm)
    canvas.setFont("ArialMH", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(20 * mm, 11 * mm, "Stand: 28.09.2026  ·  Fachliche Übergabe")
    canvas.drawRightString(width - 20 * mm, 11 * mm, f"Seite {doc.page}")
    canvas.restoreState()


def render(source: str, target: str):
    doc = BaseDocTemplate(
        str(OUT / target), pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=24 * mm, bottomMargin=21 * mm,
        title=source.replace(".md", ""), author="MH Recruiting Workspace",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates(PageTemplate(id="standard", frames=frame, onPage=decorate))
    doc.build(paragraphs(SRC / source))
    print(OUT / target)


if __name__ == "__main__":
    render("USE_CASES.md", "MH_Use_Cases.pdf")
    render("NICHTFUNKTIONALE_ANFORDERUNGEN.md", "MH_Nichtfunktionale_Anforderungen.pdf")

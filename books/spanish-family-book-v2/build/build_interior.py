#!/usr/bin/env python3
"""Interior builder for 'Everyday English for Kids: A Spanish-English Activity Workbook'.

Parses the controlled Markdown subset in manuscript/ and produces a print PDF with
ReportLab (the Beyondwords skill's documented PDF dependency), plus a combined
manuscript and a page map for QA.

Trim: 8.5 x 11 in (KDP-supported large trim). No interior bleed. Mirrored margins:
inside 0.75 in, outside 0.6 in, top 0.7 in, bottom 0.65 in (exceeds KDP minimums for
24-300 pages: gutter >= 0.375/0.5 in, outside >= 0.25 in; verified 2026-10-11).

Markdown subset supported:
  # chapter title      ## section      ### activity
  [[image:file|caption|width_in]]   [[writespace:N]]   [[pagebreak]]
  [[tip]] ... [[/tip]]
  pipe tables (header + separator row), '- ' bullets, 'N. ' numbered items,
  indented (3-space) continuation lines, paragraphs, **bold**, *italic* / ES paragraphs.
"""
import json
import os
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as canvasmod
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph,
                                Spacer, Table, TableStyle, Image, KeepTogether,
                                PageBreak, Flowable)

ROOT = Path(__file__).resolve().parent.parent
MAN = ROOT / "manuscript"
ILL = ROOT / "illustrations"
EXP = ROOT / "exports"
QA = ROOT / "qa"
FONTS = ROOT / "fonts" / "static"

TITLE = "Everyday English for Kids"
SUBTITLE = "A Spanish-English Activity Workbook"
AUTHOR = "Lucas Oliver"

TRIM_W, TRIM_H = 8.5, 11.0
M_IN, M_OUT, M_TOP, M_BOT = 0.75, 0.6, 0.7, 0.65

NAVY = colors.HexColor("#1F3A5F")
CORAL = colors.HexColor("#E8574B")
YELLOW = colors.HexColor("#F6B93B")
BLUE = colors.HexColor("#4A90D9")
GREEN = colors.HexColor("#6AB04C")
CREAM = colors.HexColor("#FDF6E9")
MUTED = colors.HexColor("#5A6472")
LINE = colors.HexColor("#9AA7B8")
GRID = colors.HexColor("#D9D2C2")
HEADBG = colors.HexColor("#FDEEB3")
TIPBG = colors.HexColor("#EAF3FB")

CHAPTER_FILES = [
    "chapter-01-welcome.md",
    "chapter-02-everyday-words.md",
    "chapter-03-meeting-people.md",
    "chapter-04-school-and-home.md",
    "chapter-05-questions-and-sentences.md",
    "chapter-06-everyday-dialogues.md",
    "chapter-07-reading-practice.md",
    "chapter-08-review-and-answers.md",
]


def register_fonts():
    pdfmetrics.registerFont(TTFont("Nunito", str(FONTS / "Nunito-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("Nunito-Bold", str(FONTS / "Nunito-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("Nunito-XBd", str(FONTS / "Nunito-ExtraBold.ttf")))
    pdfmetrics.registerFont(TTFont("Nunito-It", str(FONTS / "Nunito-Italic.ttf")))
    pdfmetrics.registerFont(TTFont("Nunito-BdIt", str(FONTS / "Nunito-BoldItalic.ttf")))
    pdfmetrics.registerFont(TTFont("Baloo2-Bold", str(FONTS / "Baloo2-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("Baloo2-XBd", str(FONTS / "Baloo2-ExtraBold.ttf")))
    pdfmetrics.registerFontFamily("Nunito", normal="Nunito", bold="Nunito-Bold",
                                  italic="Nunito-It", boldItalic="Nunito-BdIt")


S = {}


TABLE_STYLE = None  # set in make_styles


def make_styles():
    global TABLE_STYLE
    S["body"] = ParagraphStyle("body", fontName="Nunito", fontSize=11.6, leading=16.4,
                               textColor=colors.HexColor("#23272E"), spaceAfter=7)
    S["es"] = ParagraphStyle("es", parent=S["body"], fontName="Nunito-It",
                             fontSize=10.8, leading=15.2, textColor=MUTED, spaceAfter=9)
    S["chapter"] = ParagraphStyle("chapter", fontName="Baloo2-XBd", fontSize=25,
                                  leading=30, textColor=NAVY, spaceAfter=4)
    S["section"] = ParagraphStyle("section", fontName="Baloo2-Bold", fontSize=15.5,
                                  leading=19, textColor=NAVY, spaceBefore=14,
                                  spaceAfter=6, keepWithNext=1)
    S["activity"] = ParagraphStyle("activity", fontName="Nunito-XBd", fontSize=12.2,
                                   leading=15.5, textColor=CORAL, spaceBefore=12,
                                   spaceAfter=4, keepWithNext=1)
    S["bullet"] = ParagraphStyle("bullet", parent=S["body"], leftIndent=16,
                                 bulletIndent=4, spaceAfter=3)
    S["item"] = ParagraphStyle("item", parent=S["body"], leftIndent=18,
                               firstLineIndent=-18, spaceAfter=3)
    S["sub"] = ParagraphStyle("sub", parent=S["body"], leftIndent=34, spaceAfter=2)
    S["caption"] = ParagraphStyle("caption", fontName="Nunito-It", fontSize=9.2,
                                  leading=12, textColor=MUTED, alignment=TA_CENTER,
                                  spaceBefore=3, spaceAfter=10)
    TABLE_STYLE = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADBG),
        ("GRID", (0, 0), (-1, -1), 0.6, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CREAM]),
    ])
    S["cell"] = ParagraphStyle("cell", fontName="Nunito", fontSize=10, leading=13,
                               textColor=colors.HexColor("#23272E"))
    S["cellb"] = ParagraphStyle("cellb", parent=S["cell"], fontName="Nunito-Bold")
    S["tip"] = ParagraphStyle("tip", fontName="Nunito", fontSize=10.2, leading=14,
                              textColor=NAVY)
    S["tipit"] = ParagraphStyle("tipit", parent=S["tip"], fontName="Nunito-It",
                                textColor=MUTED)
    S["boxlabel"] = ParagraphStyle("boxlabel", fontName="Nunito-Bold", fontSize=10,
                                   leading=13, textColor=colors.HexColor("#7A5A00"))
    S["toc"] = ParagraphStyle("toc", fontName="Nunito-Bold", fontSize=11.5, leading=20,
                              textColor=NAVY)
    S["tocdot"] = ParagraphStyle("tocdot", fontName="Nunito", fontSize=11.5, leading=20,
                                 textColor=LINE)
    S["title"] = ParagraphStyle("title", fontName="Baloo2-XBd", fontSize=34, leading=39,
                                textColor=NAVY, alignment=TA_CENTER)
    S["subtitle"] = ParagraphStyle("subtitle", fontName="Baloo2-Bold", fontSize=16,
                                   leading=21, textColor=CORAL, alignment=TA_CENTER)
    S["author"] = ParagraphStyle("author", fontName="Nunito-XBd", fontSize=13,
                                 leading=17, textColor=NAVY, alignment=TA_CENTER)
    S["small"] = ParagraphStyle("small", fontName="Nunito", fontSize=9.2, leading=13.2,
                                textColor=MUTED)
    S["smallc"] = ParagraphStyle("smallc", parent=S["small"], alignment=TA_CENTER)


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(t):
    t = esc(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", t)
    return t


class Marker(Flowable):
    """Records the current page number for a key during a build pass."""

    def __init__(self, key, sink):
        super().__init__()
        self.key = key
        self.sink = sink
        self.width = 0
        self.height = 0

    def wrap(self, aw, ah):
        return (0, 0)

    def draw(self):
        self.sink[self.key] = self.canv.getPageNumber()


class WriteLines(Flowable):
    def __init__(self, n, width):
        super().__init__()
        self.n = n
        self.width = width
        self.height = n * 0.38 * inch + 4

    def wrap(self, aw, ah):
        self.width = min(self.width, aw)
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        c.setStrokeColor(LINE)
        c.setLineWidth(0.8)
        for i in range(self.n):
            y = self.height - 6 - (i + 1) * 0.38 * inch + 0.19 * inch
            c.line(0, y, self.width, y)


def parse_table(lines):
    rows = []
    for ln in lines:
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        rows.append(cells)
    return rows[0], rows[2:]


def chapter_flowables(md_text, sink, content_width, image_checks):
    story = []
    lines = md_text.splitlines()
    i = 0
    first_chapter_marker = True
    while i < len(lines):
        ln = lines[i]
        st = ln.strip()
        if not st:
            i += 1
            continue
        if st.startswith("# "):
            if not first_chapter_marker:
                story.append(PageBreak())
            first_chapter_marker = False
            title = st[2:].strip()
            story.append(Marker("ch:" + title, sink))
            story.append(Paragraph(inline(title), S["chapter"]))
            story.append(Spacer(1, 2))
            bar = Table([[""]], colWidths=[content_width], rowHeights=[3])
            bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), YELLOW)]))
            story.append(bar)
            story.append(Spacer(1, 10))
            i += 1
            continue
        if st.startswith("## "):
            story.append(Paragraph(inline(st[3:].strip()), S["section"]))
            i += 1
            continue
        if st.startswith("### "):
            head = Paragraph(inline(st[4:].strip()), S["activity"])
            body = []
            i += 1
            while i < len(lines):
                nx = lines[i].strip()
                if not nx or nx.startswith("#"):
                    break
                before = len(body)
                if nx.startswith("[[image:"):
                    m = re.match(r"\[\[image:(.+?)\|(.+?)\|([\d.]+)\]\]", nx)
                    fname, cap, w = m.group(1), m.group(2), float(m.group(3))
                    path = ILL / fname
                    image_checks.append((fname, path.exists()))
                    if path.exists():
                        from PIL import Image as PILImage
                        with PILImage.open(path) as im:
                            pw, ph = im.size
                        body.append(KeepTogether([Image(str(path), width=w * inch,
                                                         height=w * ph / pw * inch),
                                                  Paragraph(inline(cap), S["caption"])]))
                    elif os.environ.get("BW_PROOF") == "1":
                        box = Table([[Paragraph(f"ART PENDING (proof mode): {fname}", S["cellb"])]],
                                    colWidths=[w * inch], rowHeights=[w * 0.56 * inch])
                        box.setStyle(TableStyle([
                            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#E5E0D5")),
                            ("BOX", (0, 0), (-1, -1), 1, LINE),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
                        body.append(KeepTogether([box, Paragraph(inline(cap), S["caption"])]))
                    else:
                        raise SystemExit(f"missing illustration: {path}")
                elif nx.startswith("[[writespace:"):
                    n = int(nx.split(":")[1].rstrip("]"))
                    body.append(Spacer(1, 4))
                    body.append(WriteLines(n, content_width))
                    body.append(Spacer(1, 6))
                elif nx == "[[tip]]":
                    inner = []
                    i += 1
                    while i < len(lines) and lines[i].strip() != "[[/tip]]":
                        inner.append(lines[i].strip())
                        i += 1
                    paras = []
                    for t in inner:
                        if not t:
                            continue
                        is_es = t.startswith("*") and t.endswith("*")
                        paras.append(Paragraph(inline(t.strip("*") if is_es else t),
                                               S["tipit"] if is_es else S["tip"]))
                    tbl = Table([[paras]], colWidths=[content_width])
                    tbl.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), TIPBG),
                        ("BOX", (0, 0), (-1, -1), 1.1, BLUE),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                        ("ROUNDEDCORNERS", [6, 6, 6, 6])]))
                    body.append(Spacer(1, 4))
                    body.append(tbl)
                    body.append(Spacer(1, 8))
                elif nx.startswith("|"):
                    tbl_lines = []
                    while i < len(lines) and lines[i].strip().startswith("|"):
                        tbl_lines.append(lines[i])
                        i += 1
                    header, rows = parse_table(tbl_lines)
                    ncols = len(header)
                    data = [[Paragraph(inline(c), S["cellb"]) for c in header]]
                    for r in rows:
                        r = (r + [""] * ncols)[:ncols]
                        data.append([Paragraph(inline(c), S["cell"]) for c in r])
                    tbl = Table(data, colWidths=[content_width / ncols] * ncols, repeatRows=1)
                    tbl.setStyle(TABLE_STYLE)
                    body.append(Spacer(1, 3))
                    body.append(tbl)
                    body.append(Spacer(1, 8))
                    continue
                else:
                    body.append(paragraph_for(nx, content_width))
                if len(body) == before:
                    break
                i += 1
            # keep whole activity on one page when it fits; else flow block-wise
            avail = (letter[1] - (M_TOP + M_BOT) * inch)
            try:
                h = head.wrap(content_width, avail)[1]
                for fl in body:
                    h += fl.wrap(content_width, avail)[1]
            except Exception:
                h = avail
            if h <= 0.86 * avail:
                story.append(KeepTogether([head] + body))
            else:
                story.append(KeepTogether([head] + body[:2]))
                story.extend(body[2:])
            continue
        if st.startswith("[[image:"):
            m = re.match(r"\[\[image:(.+?)\|(.+?)\|([\d.]+)\]\]", st)
            fname, cap, w = m.group(1), m.group(2), float(m.group(3))
            path = ILL / fname
            image_checks.append((fname, path.exists()))
            if not path.exists():
                if os.environ.get("BW_PROOF") != "1":
                    raise SystemExit(f"missing illustration: {path}")
                box = Table([[Paragraph(f"ART PENDING (proof mode): {fname}", S["cellb"])]],
                            colWidths=[w * inch], rowHeights=[w * 0.56 * inch])
                box.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#E5E0D5")),
                    ("BOX", (0, 0), (-1, -1), 1, LINE),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]))
                story.append(KeepTogether([box, Paragraph(inline(cap), S["caption"])]))
                i += 1
                continue
            from PIL import Image as PILImage
            with PILImage.open(path) as im:
                pw, ph = im.size
            h = w * ph / pw
            img = Image(str(path), width=w * inch, height=h * inch)
            block = [img, Paragraph(inline(cap), S["caption"])]
            story.append(KeepTogether(block))
            i += 1
            continue
        if st.startswith("[[writespace:"):
            n = int(st.split(":")[1].rstrip("]"))
            story.append(Spacer(1, 4))
            story.append(WriteLines(n, content_width))
            story.append(Spacer(1, 6))
            i += 1
            continue
        if st == "[[pagebreak]]":
            story.append(PageBreak())
            i += 1
            continue
        if st == "[[tip]]":
            inner = []
            i += 1
            while i < len(lines) and lines[i].strip() != "[[/tip]]":
                inner.append(lines[i].strip())
                i += 1
            i += 1
            paras = []
            for t in inner:
                if not t:
                    continue
                style = S["tipit"] if (t.startswith("*") and t.endswith("*")) else S["tip"]
                txt = t.strip("*") if style is S["tipit"] else t
                paras.append(Paragraph(inline(txt), style))
            tbl = Table([[paras]], colWidths=[content_width])
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), TIPBG),
                ("BOX", (0, 0), (-1, -1), 1.1, BLUE),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("ROUNDEDCORNERS", [6, 6, 6, 6]),
            ]))
            story.append(Spacer(1, 4))
            story.append(tbl)
            story.append(Spacer(1, 8))
            continue
        if st.startswith("|"):
            tbl_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                tbl_lines.append(lines[i])
                i += 1
            header, rows = parse_table(tbl_lines)
            ncols = len(header)
            data = [[Paragraph(inline(c), S["cellb"]) for c in header]]
            for r in rows:
                r = (r + [""] * ncols)[:ncols]
                data.append([Paragraph(inline(c), S["cell"]) for c in r])
            tbl = Table(data, colWidths=[content_width / ncols] * ncols, repeatRows=1)
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HEADBG),
                ("GRID", (0, 0), (-1, -1), 0.6, GRID),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CREAM]),
            ]))
            story.append(Spacer(1, 3))
            story.append(tbl)
            story.append(Spacer(1, 8))
            continue
        if st.startswith("- "):
            story.append(Paragraph(inline(st[2:]), S["bullet"], bulletText="•"))
            i += 1
            continue
        if re.match(r"^\d+\.\s", st):
            story.append(Paragraph(inline(st), S["item"]))
            i += 1
            while i < len(lines) and lines[i].startswith("   ") and lines[i].strip():
                story.append(Paragraph(inline(lines[i].strip()), S["sub"]))
                i += 1
            continue
        if st.startswith("Word box") or st.startswith("Mixed-up list") or st.startswith("Frame /"):
            tbl = Table([[Paragraph(inline(st), S["boxlabel"])]], colWidths=[content_width])
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF7DF")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#E4C868")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 6))
            i += 1
            continue
        story.append(paragraph_for(st, content_width))
        i += 1
    return story


def paragraph_for(st, content_width):
    if st.startswith("*") and st.endswith("*") and st.count("*") == 2:
        return Paragraph(inline(st.strip("*")), S["es"])
    if st.startswith("**") and ":**" in st[:40]:
        return Paragraph(inline(st), S["body"])
    return Paragraph(inline(st), S["body"])


def front_matter(sink, toc_pages, content_width):
    story = []
    # Title page
    story.append(Spacer(1, 1.1 * inch))
    story.append(Paragraph(esc(TITLE), S["title"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(esc(SUBTITLE), S["subtitle"]))
    story.append(Spacer(1, 18))
    hero = ILL / "hero-kids-waving.png"
    from PIL import Image as PILImage
    with PILImage.open(hero) as im:
        pw, ph = im.size
    w = 4.4
    story.append(Image(str(hero), width=w * inch, height=w * ph / pw * inch))
    story.append(Spacer(1, 16))
    story.append(Paragraph(esc(AUTHOR), S["author"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("For Spanish-speaking kids ages 8-12 learning English in the United States<br/>"
                           "<i>Para niños hispanohablantes de 8 a 12 años que aprenden inglés en los Estados Unidos</i>",
                           S["smallc"]))
    story.append(PageBreak())
    # Copyright page
    story.append(Spacer(1, 5.4 * inch))
    cp = [
        f"{TITLE}: {SUBTITLE}",
        f"Copyright © 2026 {AUTHOR}. All rights reserved.",
        "No part of this book may be reproduced without written permission from the author, except brief quotations in reviews.",
        "First edition, 2026. ISBN: not yet assigned (a free KDP ISBN or purchased ISBN may be added at title setup).",
        "Interior text and exercises are original. Text was drafted with AI assistance and revised by the author; illustrations were generated with AI image tools and reviewed by the author. Disclose AI-generated content where required by the retailer.",
        "Typography: Nunito and Baloo 2 (SIL Open Font License 1.1, (c) the font authors). Font license notices are kept in the project fonts directory.",
        "Print specification: 8.5 x 11 in trim, no interior bleed, mirrored margins (inside 0.75 in, outside 0.6 in).",
        "Manufactured for Amazon KDP paperback submission preparation. This file is a production proof, not a retail copy.",
    ]
    for line in cp:
        story.append(Paragraph(esc(line), S["small"]))
        story.append(Spacer(1, 4))
    story.append(PageBreak())
    # Table of contents
    story.append(Marker("ch:TOC", sink))
    story.append(Paragraph("Contents / Contenido", S["chapter"]))
    story.append(Spacer(1, 10))
    entries = toc_pages or {}
    for label, key in TOC_ENTRIES:
        pg = entries.get(key, "")
        row = Table([[Paragraph(esc(label), S["toc"]), Paragraph(str(pg), S["tocdot"])]],
                    colWidths=[content_width - 0.5 * inch, 0.5 * inch])
        row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E7E0D0")),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(row)
    story.append(PageBreak())
    return story


TOC_ENTRIES = [
    ("Chapter 1 · Welcome! / ¡Bienvenidos!", "ch:Chapter 1 · Welcome! / ¡Bienvenidos!"),
    ("Chapter 2 · Everyday Words / Palabras de todos los días", "ch:Chapter 2 · Everyday Words / Palabras de todos los días"),
    ("Chapter 3 · Meeting People / Conocer personas", "ch:Chapter 3 · Meeting People / Conocer personas"),
    ("Chapter 4 · School and Home / La escuela y la casa", "ch:Chapter 4 · School and Home / La escuela y la casa"),
    ("Chapter 5 · Questions and Sentences / Preguntas y oraciones", "ch:Chapter 5 · Questions and Sentences / Preguntas y oraciones"),
    ("Chapter 6 · Everyday Dialogues / Diálogos de todos los días", "ch:Chapter 6 · Everyday Dialogues / Diálogos de todos los días"),
    ("Chapter 7 · Reading Practice / Práctica de lectura", "ch:Chapter 7 · Reading Practice / Práctica de lectura"),
    ("Chapter 8 · Review and Answers / Repaso y respuestas", "ch:Chapter 8 · Review and Answers / Repaso y respuestas"),
    ("Answer Key / Clave de respuestas", "sec:answer-key"),
    ("Glossary / Glosario", "sec:glossary"),
]


class BookDoc(BaseDocTemplate):
    def __init__(self, path, **kw):
        super().__init__(path, pagesize=letter,
                         leftMargin=M_OUT * inch, rightMargin=M_OUT * inch,
                         topMargin=M_TOP * inch, bottomMargin=M_BOT * inch,
                         title=f"{TITLE}: {SUBTITLE}", author=AUTHOR,
                         subject="Bilingual Spanish-English children's activity workbook",
                         creator="Beyondwords workspace build (ReportLab)")
        fw = letter[0] - (M_IN + M_OUT) * inch
        fh = letter[1] - (M_TOP + M_BOT) * inch
        frame_odd = Frame(M_IN * inch, M_BOT * inch, fw, fh, id="odd",
                          leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        frame_even = Frame(M_OUT * inch, M_BOT * inch, fw, fh, id="even",
                           leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([
            PageTemplate(id="odd", frames=[frame_odd], onPage=self._deco),
            PageTemplate(id="even", frames=[frame_even], onPage=self._deco),
        ])

    def _deco(self, canv, doc):
        canv.saveState()
        if canv.getPageNumber() > 2:
            canv.setFont("Nunito", 9.2)
            canv.setFillColor(MUTED)
            canv.drawCentredString(letter[0] / 2, 0.38 * inch, str(canv.getPageNumber()))
            canv.setStrokeColor(colors.HexColor("#E7E0D0"))
            canv.setLineWidth(0.6)
            canv.line(M_OUT * inch, 0.62 * inch, letter[0] - M_OUT * inch, 0.62 * inch)
        canv.restoreState()

    def handle_pageBegin(self):
        super().handle_pageBegin()
        self._handle_nextPageTemplate("odd" if self.page % 2 == 1 else "even")


def inject_section_markers(story, sink):
    out = []
    for fl in story:
        if isinstance(fl, Paragraph) and fl.style is S["section"]:
            txt = fl.getPlainText()
            if txt.startswith("Answer Key"):
                out.append(Marker("sec:answer-key", sink))
            elif txt.startswith("Glossary"):
                out.append(Marker("sec:glossary", sink))
        out.append(fl)
    return out


def build(pass_toc=None):
    sink = {}
    image_checks = []
    content_width = letter[0] - (M_IN + M_OUT) * inch
    story = front_matter(sink, pass_toc, content_width)
    for fname in CHAPTER_FILES:
        md = (MAN / fname).read_text(encoding="utf-8")
        story += chapter_flowables(md, sink, content_width, image_checks)
    story = inject_section_markers(story, sink)
    out = QA / "interior-proof.pdf" if os.environ.get("BW_PROOF") == "1" else EXP / "interior-8.5x11.pdf"
    doc = BookDoc(str(out))
    doc.build(story)
    return sink, image_checks, out


def main():
    register_fonts()
    make_styles()
    EXP.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    proof = os.environ.get("BW_PROOF") == "1"
    sink1, checks, out = build(None)
    json.dump(sink1, open(QA / "pagemap-pass1.json", "w"), indent=1)
    sink2, checks2, out = build(sink1)
    pagemap = {"pages": sink2, "title": TITLE, "trim": [TRIM_W, TRIM_H], "proof": proof}
    json.dump(pagemap, open(QA / ("pagemap-proof.json" if proof else "pagemap.json"), "w"), indent=1)
    missing = [f for f, ok in checks2 if not ok]
    print("PDF:", out)
    print("pagemap:", json.dumps(sink2, indent=1))
    if missing:
        print("MISSING IMAGES:", missing)
        sys.exit(2)
    # combined manuscript
    combined = [f"# {TITLE}: {SUBTITLE}", f"**Author:** {AUTHOR}", ""]
    for fname in CHAPTER_FILES:
        combined.append((MAN / fname).read_text(encoding="utf-8").rstrip())
        combined.append("")
    (EXP / "manuscript-combined.md").write_text("\n".join(combined), encoding="utf-8")
    print("combined manuscript:", EXP / "manuscript-combined.md")


if __name__ == "__main__":
    main()

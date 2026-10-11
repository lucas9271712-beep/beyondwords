#!/usr/bin/env python3
"""Minimal, standards-shaped EPUB 3 builder (stdlib only) for the workbook text.

Reflowable ebook companion to the print edition. Illustrations are embedded; print-only
writing lines become a labelled note. Structural self-check runs at the end; EPUBCheck
is reported UNAVAILABLE when no Java runtime exists (it is not installed here).
"""
import html
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAN = ROOT / "manuscript"
ILL = ROOT / "illustrations"
EXP = ROOT / "exports"

CHAPTERS = [
    ("chapter-01-welcome.md", "Chapter 1 · Welcome! / ¡Bienvenidos!"),
    ("chapter-02-everyday-words.md", "Chapter 2 · Everyday Words / Palabras de todos los días"),
    ("chapter-03-meeting-people.md", "Chapter 3 · Meeting People / Conocer personas"),
    ("chapter-04-school-and-home.md", "Chapter 4 · School and Home / La escuela y la casa"),
    ("chapter-05-questions-and-sentences.md", "Chapter 5 · Questions and Sentences / Preguntas y oraciones"),
    ("chapter-06-everyday-dialogues.md", "Chapter 6 · Everyday Dialogues / Diálogos de todos los días"),
    ("chapter-07-reading-practice.md", "Chapter 7 · Reading Practice / Práctica de lectura"),
    ("chapter-08-review-and-answers.md", "Chapter 8 · Review and Answers / Repaso y respuestas"),
]

CSS = """
body { font-family: sans-serif; line-height: 1.45; margin: 5%; }
h1 { font-size: 1.5em; } h2 { font-size: 1.25em; } h3 { font-size: 1.1em; color: #B4443C; }
p.es { font-style: italic; color: #55606E; }
table { border-collapse: collapse; width: 100%; font-size: 0.92em; }
td, th { border: 1px solid #CCC4B4; padding: 4px 6px; vertical-align: top; }
th { background: #FDEEB3; }
figure { text-align: center; } figure img { max-width: 100%; }
figcaption { font-size: 0.85em; color: #55606E; font-style: italic; }
.tip { border: 1px solid #4A90D9; background: #EAF3FB; padding: 8px; border-radius: 6px; }
.wb { border: 1px solid #E4C868; background: #FFF7DF; padding: 6px; }
.writespace { font-style: italic; color: #55606E; }
"""


def esc(t):
    return html.escape(t, quote=False)


def inline(t):
    t = esc(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", t)
    return t


def md_to_html(md):
    out, lines, i = [], md.splitlines(), 0
    while i < len(lines):
        st = lines[i].strip()
        if not st:
            i += 1
            continue
        if st.startswith("# "):
            out.append(f"<h1>{inline(st[2:])}</h1>"); i += 1; continue
        if st.startswith("## "):
            out.append(f"<h2>{inline(st[3:])}</h2>"); i += 1; continue
        if st.startswith("### "):
            out.append(f"<h3>{inline(st[4:])}</h3>"); i += 1; continue
        if st.startswith("[[image:"):
            m = re.match(r"\[\[image:(.+?)\|(.+?)\|([\d.]+)\]\]", st)
            out.append(f'<figure><img src="images/{m.group(1)}" alt="{esc(m.group(2))}"/>'
                       f"<figcaption>{inline(m.group(2))}</figcaption></figure>")
            i += 1; continue
        if st.startswith("[[writespace:"):
            n = st.split(":")[1].rstrip("]")
            out.append(f'<p class="writespace">[Writing space: {n} lines in the print edition / '
                       f"Espacio de escritura: {n} líneas en la edición impresa]</p>")
            i += 1; continue
        if st == "[[pagebreak]]":
            i += 1; continue
        if st == "[[tip]]":
            inner = []
            i += 1
            while i < len(lines) and lines[i].strip() != "[[/tip]]":
                inner.append(lines[i].strip()); i += 1
            i += 1
            body = "".join(
                f'<p class="es">{inline(t.strip("*"))}</p>' if t.startswith("*") and t.endswith("*")
                else f"<p>{inline(t)}</p>" for t in inner if t)
            out.append(f'<div class="tip">{body}</div>'); continue
        if st.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head, body = rows[0], rows[2:]
            t = ["<table><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr>"]
            for r in body:
                t.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            t.append("</table>")
            out.append("".join(t)); continue
        if st.startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(f"<li>{inline(lines[i].strip()[2:])}</li>"); i += 1
            out.append("<ul>" + "".join(items) + "</ul>"); continue
        if re.match(r"^\d+\.\s", st):
            out.append(f"<p>{inline(st)}</p>"); i += 1
            while i < len(lines) and lines[i].startswith("   ") and lines[i].strip():
                out.append(f'<p style="margin-left:2em">{inline(lines[i].strip())}</p>'); i += 1
            continue
        if st.startswith("Word box") or st.startswith("Mixed-up list") or st.startswith("Frame /"):
            out.append(f'<p class="wb">{inline(st)}</p>'); i += 1; continue
        if st.startswith("*") and st.endswith("*") and st.count("*") == 2:
            out.append(f'<p class="es">{inline(st.strip("*"))}</p>'); i += 1; continue
        out.append(f"<p>{inline(st)}</p>"); i += 1
    return "\n".join(out)


def main():
    EXP.mkdir(parents=True, exist_ok=True)
    imgs = sorted({m.group(1) for f, _ in CHAPTERS
                   for m in re.finditer(r"\[\[image:(.+?)\|", (MAN / f).read_text(encoding="utf-8"))})
    chapters_html = []
    for idx, (fname, label) in enumerate(CHAPTERS, 1):
        body = md_to_html((MAN / fname).read_text(encoding="utf-8"))
        chapters_html.append((f"ch{idx:02d}.xhtml", label, body))

    opf_manifest = ['<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
                    '<item id="css" href="style.css" media-type="text/css"/>']
    opf_spine, opf_manifest_extra = [], []
    for i, (href, label, _) in enumerate(chapters_html, 1):
        opf_manifest.append(f'<item id="c{i}" href="{href}" media-type="application/xhtml+xml"/>')
        opf_spine.append(f'<itemref idref="c{i}"/>')
    for j, im in enumerate(imgs, 1):
        opf_manifest.append(f'<item id="i{j}" href="images/{im}" media-type="image/png"/>')

    nav_items = "".join(f'<li><a href="{h}">{esc(l)}</a></li>' for h, l, _ in chapters_html)
    nav = f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Contents</title><link rel="stylesheet" type="text/css" href="style.css"/></head>
<body><nav epub:type="toc"><h1>Contents / Contenido</h1><ol>{nav_items}</ol></nav></body></html>"""

    opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="uid">urn:uuid:everyday-english-for-kids-v1</dc:identifier>
<dc:title>Everyday English for Kids: A Spanish-English Activity Workbook</dc:title>
<dc:language>en</dc:language><dc:creator>Lucas Oliver</dc:creator>
<meta property="dcterms:modified">2026-10-11T00:00:00Z</meta>
</metadata>
<manifest>{''.join(opf_manifest)}</manifest>
<spine>{''.join(opf_spine)}</spine>
</package>"""

    container = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
</rootfiles></container>"""

    epub = EXP / "everyday-english-for-kids.epub"
    with zipfile.ZipFile(epub, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", container)
        z.writestr("OEBPS/content.opf", opf)
        z.writestr("OEBPS/style.css", CSS)
        z.writestr("OEBPS/nav.xhtml", nav)
        for href, label, body in chapters_html:
            doc = f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><head><title>{esc(label)}</title>
<link rel="stylesheet" type="text/css" href="style.css"/></head><body>{body}</body></html>"""
            z.writestr(f"OEBPS/{href}", doc)
        for im in imgs:
            z.write(ILL / im, f"OEBPS/images/{im}")

    # structural self-check
    import xml.etree.ElementTree as ET
    problems = []
    with zipfile.ZipFile(epub) as z:
        if z.read("mimetype").decode() != "application/epub+zip":
            problems.append("mimetype")
        if z.testzip() is not None:
            problems.append("crc")
        for n in z.namelist():
            if n.endswith((".xhtml", ".opf", ".xml")):
                try:
                    ET.fromstring(z.read(n))
                except Exception as e:
                    problems.append(f"{n}:{e}")
        names = z.namelist()
        for _, l, _ in []:
            pass
        for href, _, _ in chapters_html:
            if f"OEBPS/{href}" not in names:
                problems.append(href)
    print("EPUB:", epub, epub.stat().st_size, "bytes")
    print("structural self-check:", "PASS" if not problems else f"FAIL {problems}")
    print("EPUBCheck (independent validator): UNAVAILABLE (no Java runtime in this environment)")


if __name__ == "__main__":
    main()

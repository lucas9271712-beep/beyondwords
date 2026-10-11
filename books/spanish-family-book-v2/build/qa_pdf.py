#!/usr/bin/env python3
"""PDF production QA: geometry, fonts, text extraction, image DPI audit.
Uses pypdf (repo-documented) + PyMuPDF (QA-only renderer). Writes qa/pdf-checks.json."""
import json
import sys
from pathlib import Path

import pymupdf
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
QA = ROOT / "qa"
TRIM_W_PT, TRIM_H_PT = 8.5 * 72, 11.0 * 72
results = []


def check(name, ok, detail):
    results.append({"check": name, "result": "PASS" if ok else "FAIL", "detail": detail})


def main(pdf_path):
    pdf = Path(pdf_path)
    r = PdfReader(str(pdf))
    n = len(r.pages)
    box = r.pages[0].mediabox
    w, h = float(box.width), float(box.height)
    check("page size 8.5x11 in", abs(w - TRIM_W_PT) < 1 and abs(h - TRIM_H_PT) < 1,
          f"{w:.1f}x{h:.1f} pt across {n} pages")
    sizes = {(round(float(p.mediabox.width), 1), round(float(p.mediabox.height), 1)) for p in r.pages}
    check("uniform page size", len(sizes) == 1, str(sizes))

    fonts = set()
    for p in r.pages:
        res = p.get("/Resources") or {}
        f = res.get("/Font") or {}
        for k in f.keys():
            obj = f[k].get_object()
            fonts.add((obj.get("/BaseFont", "?"), str(obj.get("/Subtype"))))
    embedded = []
    for name, sub in fonts:
        for p in r.pages:
            res = p.get("/Resources") or {}
            f = res.get("/Font") or {}
            for k in f.keys():
                obj = f[k].get_object()
                if obj.get("/BaseFont") == name:
                    d = obj.get("/FontDescriptor")
                    if d is not None:
                        d = d.get_object()
                        embedded.append((name, bool(d.get("/FontFile2") or d.get("/FontFile") or d.get("/FontFile3"))))
    not_emb = sorted({nm for nm, e in embedded if not e})
    check("fonts embedded", embedded and not not_emb,
          f"{len({nm for nm, _ in embedded})} font objects; unembedded={not_emb}")

    doc = pymupdf.open(str(pdf))
    txt = "".join(doc[i].get_text() for i in range(doc.page_count))
    for ch in "áéíóúñ¿¡":
        if ch not in txt:
            check("spanish glyph extraction", False, f"missing {ch}")
            break
    else:
        check("spanish glyph extraction", True, "accents and inverted punctuation extract correctly")
    check("text extractable", len(txt) > 20000, f"{len(txt)} chars extracted")

    # image placement DPI audit
    low = []
    placed = 0
    for i in range(doc.page_count):
        for img in doc[i].get_image_info(xrefs=True):
            placed += 1
            bw = img["bbox"][2] - img["bbox"][0]
            bh = img["bbox"][3] - img["bbox"][1]
            px_w = img["width"]
            dpi = px_w / (bw / 72) if bw else 0
            if dpi < 299:
                low.append((i + 1, img["width"], img["height"], round(dpi)))
    check("placed images >= 300 effective dpi", placed > 0 and not low,
          f"{placed} placements; below 300 dpi: {low}")

    # blank page scan (text or image content)
    blanks = [i + 1 for i in range(doc.page_count)
              if not doc[i].get_text().strip() and not doc[i].get_images()]
    check("no accidental blank pages", not blanks, f"blank={blanks}")

    # overflow scan: any drawing/text beyond trim box
    over = []
    for i in range(doc.page_count):
        pg = doc[i]
        for b in pg.get_text("blocks"):
            x0, y0, x1, y1 = b[:4]
            if x0 < -1 or y0 < -1 or x1 > TRIM_W_PT + 1 or y1 > TRIM_H_PT + 1:
                over.append((i + 1, [round(v) for v in (x0, y0, x1, y1)]))
    check("no content outside trim", not over, f"overflow blocks={over[:6]}")

    QA.mkdir(exist_ok=True)
    json.dump(results, open(QA / "pdf-checks.json", "w"), indent=1)
    for res in results:
        print(f"{res['result']:4} {res['check']}: {res['detail'][:150]}")
    return 1 if any(res["result"] == "FAIL" for res in results) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else ROOT / "exports" / "interior-8.5x11.pdf"))

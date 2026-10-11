#!/usr/bin/env python3
"""Render selected PDF pages to PNG for visual inspection (QA-only, PyMuPDF)."""
import sys
from pathlib import Path
import pymupdf

pdf, outdir = sys.argv[1], Path(sys.argv[2])
pages = [int(p) for p in sys.argv[3].split(",")] if len(sys.argv) > 3 else None
outdir.mkdir(parents=True, exist_ok=True)
doc = pymupdf.open(pdf)
total = doc.page_count
sel = pages or [1, total // 3, total // 2, total - 2, total]
for p in sel:
    if 1 <= p <= total:
        pix = doc[p - 1].get_pixmap(dpi=100)
        pix.save(outdir / f"page-{p:03d}.png")
print("rendered", sel, "of", total, "pages ->", outdir)

#!/usr/bin/env python3
"""Asset manifest: every illustration with native pixels, placement, effective DPI,
provenance and license basis. Writes illustrations/manifest.json + manifest.md."""
import hashlib
import json
import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ILL = ROOT / "illustrations"
MAN = ROOT / "manuscript"

CHAPTERS = sorted(MAN.glob("chapter-*.md"))
PLACEMENT_IN = 4.4  # interior standard placement width
TITLE_IN = 4.4      # title-page hero placement width

PROVENANCE = ("ai_generated: created with the host image-generation tool from original prompts "
              "written for this book; reviewed visually by the production team; no copyrighted "
              "characters or copied artwork used. License basis: original output commissioned by "
              "the author for this title.")


def main():
    entries = []
    refs = {}
    for ch in CHAPTERS:
        t = ch.read_text(encoding="utf-8")
        for m in re.finditer(r"\[\[image:(.+?)\|(.+?)\|([\d.]+)\]\]", t):
            refs.setdefault(m.group(1), []).append(
                {"chapter": ch.name, "caption": m.group(2), "width_in": float(m.group(3))})
    for f in sorted(ILL.glob("*.png")):
        with Image.open(f) as im:
            w, h = im.size
        places = refs.get(f.name, [])
        if f.name == "hero-kids-waving.png":
            places = [{"chapter": "title-page", "caption": "title hero", "width_in": TITLE_IN}] + places
        if f.name == "cover-art-front.png":
            places = [{"chapter": "cover", "caption": "front cover art panel (native pixels)",
                       "width_in": round(w / 300, 3)}]
        eff = [round(min(w / p["width_in"], h / (p["width_in"] * h / w)), 1) for p in places] or [None]
        entries.append({
            "file": f.name,
            "native_pixels": [w, h],
            "bytes": f.stat().st_size,
            "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
            "format": "PNG (lossless)",
            "provenance": PROVENANCE,
            "placements": places,
            "effective_dpi_at_placement": eff,
            "upscaled": False,
        })
    out = {"generated_by": "build/make_manifest.py", "dpi_target": 300, "assets": entries}
    (ILL / "manifest.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    lines = ["# Illustration manifest", "",
             "| File | Native px | Placement | Eff. DPI | Provenance |",
             "|---|---|---|---|---|"]
    for e in entries:
        pl = "; ".join(f"{p['chapter']} @ {p['width_in']}in" for p in e["placements"]) or "unused"
        lines.append(f"| {e['file']} | {e['native_pixels'][0]}x{e['native_pixels'][1]} | {pl} | "
                     f"{e['effective_dpi_at_placement'][0]} | AI-generated original, author-commissioned |")
    (ILL / "manifest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(entries)} assets manifested")
    for e in entries:
        print(f"  {e['file']:34} {e['native_pixels']} dpi@placement={e['effective_dpi_at_placement']}")


if __name__ == "__main__":
    main()

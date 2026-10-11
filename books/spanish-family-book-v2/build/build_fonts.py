#!/usr/bin/env python3
"""Instantiate static weights from OFL variable fonts (Baloo 2, Nunito) for book layout.
Source: google/fonts (SIL OFL 1.1), fetched via api.github.com. Licenses kept beside fonts."""
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "fonts"
OUT = ROOT / "fonts" / "static"
OUT.mkdir(parents=True, exist_ok=True)

JOBS = [
    ("Nunito[wght].ttf", {"wght": 400}, "Nunito-Regular.ttf"),
    ("Nunito[wght].ttf", {"wght": 700}, "Nunito-Bold.ttf"),
    ("Nunito[wght].ttf", {"wght": 800}, "Nunito-ExtraBold.ttf"),
    ("Nunito-Italic[wght].ttf", {"wght": 400}, "Nunito-Italic.ttf"),
    ("Nunito-Italic[wght].ttf", {"wght": 700}, "Nunito-BoldItalic.ttf"),
    ("Baloo2[wght].ttf", {"wght": 700}, "Baloo2-Bold.ttf"),
    ("Baloo2[wght].ttf", {"wght": 800}, "Baloo2-ExtraBold.ttf"),
]
for src, axes, name in JOBS:
    f = TTFont(SRC / src)
    instancer.instantiateVariableFont(f, axes, inplace=True)
    f.save(OUT / name)
    print("wrote", OUT / name)

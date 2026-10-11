#!/usr/bin/env python3
"""Print wraparound + ebook cover compositor.

Geometry follows KDP 'Create a Paperback Cover' (kdp.amazon.com/en_US/help/topic/G201953020,
verified 2026-10-11):
  cover width  = 0.125 bleed + back trim + spine + front trim + 0.125 bleed
  cover height = trim height + 0.25
  spine = page_count * paper_thickness  (premium color 0.002347 in/page)
  spine text only above 79 pages; all text >= 0.125 in inside trim; barcode zone kept clear.

All typography is rasterized at 300 DPI from OFL fonts (sharp at print size); the
illustration panel is placed at its NATIVE pixel size (never upscaled) so its effective
DPI is >= 300. Backgrounds are flat vector-style shapes drawn at full resolution.
The recipe JSON in source-files/ is the editable source; rerunning this script
reproduces every file.
"""
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
ILL = ROOT / "illustrations"
COV = ROOT / "cover"
SRC = ROOT / "source-files"
FONTS = ROOT / "fonts" / "static"
DPI = 300
TRIM_W, TRIM_H, BLEED = 8.5, 11.0, 0.125
PAPER_THICKNESS = 0.002347  # premium color, white paper (KDP, verified 2026-10-11)

CREAM = (253, 246, 233)
NAVY = (31, 58, 95)
CORAL = (232, 87, 75)
YELLOW = (246, 185, 59)
BLUE = (74, 144, 217)
GREEN = (106, 176, 76)
INK = (35, 39, 46)

TITLE_LINES = ["Everyday English", "for Kids"]
SUBTITLE = "A Spanish-English Activity Workbook"
AUTHOR = "Lucas Oliver"
TAGLINE = "English - Spanish  ·  Ages 8-12  ·  Illustrated activities"
BLURB = ("A friendly first step into English for Spanish-speaking kids. Eight illustrated "
         "chapters build real vocabulary - greetings, colors, numbers, family, school, home, "
         "questions and everyday dialogues - with Say-it pronunciations made from Spanish sounds.")
BULLETS = [
    "46 bilingual activities with a complete answer key",
    "Say-it pronunciation help for Spanish speakers",
    "Short stories and dialogues in natural American English",
    "A family practice game in every chapter",
    "140+ word English-Spanish glossary",
]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def fit(draw, text, fname, max_w, start, min_size=24):
    size = start
    while size > min_size:
        f = font(fname, size)
        w = draw.textbbox((0, 0), text, font=f)[2]
        if w <= max_w:
            return f, w
        size -= 2
    return font(fname, min_size), draw.textbbox((0, 0), text, font=font(fname, min_size))[2]


def wrap_text(draw, text, fname, size, max_w):
    f = font(fname, size)
    out, line = [], ""
    for word in text.split():
        cand = (line + " " + word).strip()
        if draw.textbbox((0, 0), cand, font=f)[2] <= max_w:
            line = cand
        else:
            out.append(line)
            line = word
    out.append(line)
    return out, f


def autocrop(img, tol=14):
    """Crop near-uniform background margins (returns crop box); pixels kept are native."""
    px = img.load()
    w, h = img.size
    bg = px[2, 2]
    def diff(c):
        return abs(c[0] - bg[0]) + abs(c[1] - bg[1]) + abs(c[2] - bg[2]) > tol * 3
    x0, y0, x1, y1 = w, h, 0, 0
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            if diff(px[x, y]):
                x0, y0 = min(x0, x), min(y0, y)
                x1, y1 = max(x1, x), max(y1, y)
    pad = 6
    return (max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad))


def star(draw, cx, cy, r, col):
    import math
    pts = []
    for i in range(10):
        rad = r if i % 2 == 0 else r * 0.45
        a = math.pi / 5 * i - math.pi / 2
        pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    draw.polygon(pts, fill=col)


def rounded(draw, box, r, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def draw_art_panel(img, draw, art, cx, cy, max_w_px, max_h_px):
    """Place art at native pixels (downscale only if it exceeds the slot)."""
    aw, ah = art.size
    scale = min(1.0, max_w_px / aw, max_h_px / ah)
    w, h = int(aw * scale), int(ah * scale)
    placed = art if scale == 1.0 else art.resize((w, h), Image.LANCZOS)
    x, y = int(cx - w / 2), int(cy - h / 2)
    pad = 18
    rounded(draw, [x - pad, y - pad, x + w + pad, y + h + pad], 42, fill=(255, 255, 255),
            outline=NAVY, width=6)
    img.paste(placed, (x, y))
    return (x, y, w, h), scale


def compose_front(draw, img, art, W, H, inset):
    # decorative flat shapes (kept clear of the spine hinge at x=0)
    draw.ellipse([W - 620, -260, W + 180, 540], fill=YELLOW)
    draw.ellipse([W - 500, -140, W + 60, 420], fill=CREAM)
    draw.ellipse([W - 560, H - 560, W + 200, H + 200], fill=BLUE)
    draw.ellipse([W - 440, H - 440, W + 80, H + 80], fill=CREAM)
    # title
    y = int(H * 0.055)
    for line in TITLE_LINES:
        f, w = fit(draw, line, "Baloo2-ExtraBold.ttf", W - 2 * inset, 210)
        draw.text(((W - w) / 2, y), line, font=f, fill=NAVY)
        y += int(f.size * 1.02)
    # subtitle ribbon
    f, w = fit(draw, SUBTITLE, "Baloo2-Bold.ttf", W - 2 * inset - 120, 64)
    rh = int(f.size * 1.9)
    rx0, rx1 = (W - w) / 2 - 46, (W + w) / 2 + 46
    rounded(draw, [rx0, y + 10, rx1, y + 10 + rh], rh // 2, fill=CORAL)
    draw.text(((W - w) / 2, y + 10 + (rh - f.size) / 2 - 6), SUBTITLE, font=f, fill=(255, 255, 255))
    top_block_end = y + 10 + rh
    # author + tagline at bottom
    fa, wa = fit(draw, AUTHOR, "Baloo2-Bold.ttf", W - 2 * inset, 84)
    ft, wt = fit(draw, TAGLINE, "Nunito-Bold.ttf", W - 2 * inset, 40)
    bottom_start = H - int(H * 0.045) - ft.size - int(fa.size * 1.25)
    # art panel between
    slot_top, slot_bot = top_block_end + 40, bottom_start - 40
    # vector sunburst + star scatter behind the card (resolution-independent)
    ccx, ccy = W / 2, (slot_top + slot_bot) / 2
    draw.ellipse([ccx - 620, ccy - 620, ccx + 620, ccy + 620], fill=(250, 240, 214))
    for (sx, sy, r, col) in [(-760, -520, 62, YELLOW), (700, -620, 46, CORAL),
                             (820, 300, 56, GREEN), (-840, 380, 44, BLUE),
                             (-520, 700, 34, CORAL), (560, 760, 40, YELLOW)]:
        star(draw, ccx + sx, ccy + sy, r, col)
    for (sx, sy, r, col) in [(640, -300, 16, BLUE), (-660, -180, 14, GREEN),
                             (760, 60, 15, YELLOW), (-780, 40, 13, CORAL)]:
        draw.ellipse([ccx + sx - r, ccy + sy - r, ccx + sx + r, ccy + sy + r], fill=col)
    (x, yy, w2, h2), scale = draw_art_panel(img, draw, art, ccx, ccy,
                                            W - 2 * inset, slot_bot - slot_top)
    draw.text(((W - wa) / 2, bottom_start), AUTHOR, font=fa, fill=NAVY)
    draw.text(((W - wt) / 2, bottom_start + int(fa.size * 1.25)), TAGLINE, font=ft, fill=INK)
    return scale


def compose_back(draw, img, vignette, x0, x1, H):
    inset = int(0.55 * DPI)
    w_avail = (x1 - x0) - 2 * inset
    y = int(H * 0.09)
    f, w = fit(draw, "Hello!  Hola!", "Baloo2-ExtraBold.ttf", w_avail, 110)
    draw.text((x0 + inset, y), "Hello!  Hola!", font=f, fill=NAVY)
    y += int(f.size * 1.35)
    lines, fb = wrap_text(draw, BLURB, "Nunito-Bold.ttf", 34, w_avail)
    for ln in lines:
        draw.text((x0 + inset, y), ln, font=fb, fill=INK)
        y += int(fb.size * 1.42)
    y += 26
    for b in BULLETS:
        draw.ellipse([x0 + inset + 4, y + 12, x0 + inset + 22, y + 30], fill=CORAL)
        ls, fs = wrap_text(draw, b, "Nunito-Regular.ttf", 32, w_avail - 44)
        yy = y
        for ln in ls:
            draw.text((x0 + inset + 44, yy), ln, font=fs, fill=INK)
            yy += int(fs.size * 1.4)
        y = yy + 12
    # vignette (native crop, 300 dpi): landscape crop keeping the whole trio
    vx0, vy0, vx1, vy1 = 170, 120, 1210, 740
    v = vignette.crop((vx0, vy0, vx1, vy1))
    v.save(COV / "derived" / "back-vignette-crop.png")
    vs = v.width
    vx, vy = x0 + inset, y + 20
    rounded(draw, [vx - 12, vy - 12, vx + vs + 12, vy + v.height + 12], 36, fill=(255, 255, 255),
            outline=NAVY, width=5)
    img.paste(v, (vx, vy))
    cap = "Practice makes family time."
    fc, wc = fit(draw, cap, "Nunito-Italic.ttf", w_avail, 30)
    draw.text((vx, vy + v.height + 26), cap, font=fc, fill=(90, 100, 114))


def main():
    COV.mkdir(parents=True, exist_ok=True)
    SRC.mkdir(parents=True, exist_ok=True)
    pages = len(PdfReader(str(ROOT / "exports" / "interior-8.5x11.pdf")).pages)
    spine = pages * PAPER_THICKNESS
    wrap_w = 2 * BLEED + 2 * TRIM_W + spine
    wrap_h = TRIM_H + 2 * BLEED
    W, H = round(wrap_w * DPI), round(wrap_h * DPI)
    bx1 = round((BLEED + TRIM_W) * DPI)          # back panel right edge
    sx0, sx1 = bx1, round((BLEED + TRIM_W + spine) * DPI)
    fx0 = sx1                                     # front panel left edge

    art = Image.open(ILL / "cover-art-front.png").convert("RGB")
    art_box = autocrop(art)
    art = art.crop(art_box)
    (COV / "derived").mkdir(parents=True, exist_ok=True)
    art.save(COV / "derived" / "front-panel-art-crop.png")
    vignette = Image.open(ILL / "ch08-celebration-stars.png").convert("RGB")

    img = Image.new("RGB", (W, H), CREAM)
    draw = ImageDraw.Draw(img)
    # spine band flat navy (no spine text: spine narrower than legible safe text)
    draw.rectangle([sx0, 0, sx1, H], fill=NAVY)
    # back decorative corner
    draw.ellipse([ -320, -320, 520, 520], fill=GREEN)
    draw.ellipse([ -200, -200, 400, 400], fill=CREAM)
    compose_back(draw, img, vignette, 0, bx1, H)
    # barcode safe zone: clear rectangle lower-right of back panel (2.0 x 1.2 in)
    bz_w, bz_h = int(2.0 * DPI), int(1.2 * DPI)
    draw.rectangle([bx1 - int(0.4 * DPI) - bz_w, H - int(0.4 * DPI) - bz_h,
                    bx1 - int(0.4 * DPI), H - int(0.4 * DPI)], fill=CREAM)
    front_scale = compose_front(draw, img, art, W - fx0 - round(BLEED * DPI) + round(BLEED * DPI), H,
                                int(0.5 * DPI)) if False else None
    # front panel composed on its own canvas then pasted (keeps geometry simple)
    fw = W - fx0
    fimg = Image.new("RGB", (fw, H), CREAM)
    fdraw = ImageDraw.Draw(fimg)
    front_scale = compose_front(fdraw, fimg, art, fw, H, int(0.5 * DPI))
    img.paste(fimg, (fx0, 0))

    wrap_png = COV / "cover-wrap-300dpi.png"
    img.save(wrap_png, dpi=(DPI, DPI))
    img.save(COV / "cover-wrap-300dpi.pdf", "PDF", resolution=DPI)
    front = img.crop((fx0 + round(BLEED * DPI), round(BLEED * DPI),
                      fx0 + round(BLEED * DPI) + round(TRIM_W * DPI),
                      round(BLEED * DPI) + round(TRIM_H * DPI)))
    front.save(COV / "front-cover-print-reference.png", dpi=(DPI, DPI))

    # ebook cover 1600x2560
    EW, EH = 1600, 2560
    e = Image.new("RGB", (EW, EH), CREAM)
    ed = ImageDraw.Draw(e)
    ed.ellipse([EW - 420, -180, EW + 120, 360], fill=YELLOW)
    ed.ellipse([EW - 330, -90, EW + 30, 270], fill=CREAM)
    ed.ellipse([-180, EH - 360, 300, EH + 120], fill=BLUE)
    ed.ellipse([-90, EH - 270, 210, EH + 30], fill=CREAM)
    y = 120
    for line in TITLE_LINES:
        f, w = fit(ed, line, "Baloo2-ExtraBold.ttf", EW - 200, 150)
        ed.text(((EW - w) / 2, y), line, font=f, fill=NAVY)
        y += int(f.size * 1.02)
    f, w = fit(ed, SUBTITLE, "Baloo2-Bold.ttf", EW - 320, 46)
    rh = int(f.size * 1.9)
    rounded(ed, [(EW - w) / 2 - 34, y + 8, (EW + w) / 2 + 34, y + 8 + rh], rh // 2, fill=CORAL)
    ed.text(((EW - w) / 2, y + 8 + (rh - f.size) / 2 - 5), SUBTITLE, font=f, fill=(255, 255, 255))
    y += rh + 60
    (x, yy, w2, h2), escale = draw_art_panel(e, ed, art, EW / 2, y + (EH - y - 420) / 2,
                                             EW - 220, EH - y - 420)
    fa, wa = fit(ed, AUTHOR, "Baloo2-Bold.ttf", EW - 200, 62)
    ed.text(((EW - wa) / 2, EH - 250), AUTHOR, font=fa, fill=NAVY)
    ft, wt = fit(ed, TAGLINE, "Nunito-Bold.ttf", EW - 200, 30)
    ed.text(((EW - wt) / 2, EH - 160), TAGLINE, font=ft, fill=INK)
    e.save(COV / "ebook-cover-1600x2560.jpg", quality=92, dpi=(DPI, DPI))

    recipe = {
        "tool": "build/build_cover.py",
        "generated_for": {"title": "Everyday English for Kids: A Spanish-English Activity Workbook",
                          "author": AUTHOR},
        "spec": {"trim": [TRIM_W, TRIM_H], "bleed": BLEED, "dpi": DPI,
                 "paper": "premium color, white paper", "thickness_per_page": PAPER_THICKNESS,
                 "page_count": pages, "spine_inches": round(spine, 4),
                 "wrap_inches": [round(wrap_w, 4), round(wrap_h, 4)],
                 "wrap_pixels": [W, H], "spine_text": "none (spine too narrow for legible safe text)",
                 "barcode_zone": "kept clear, lower-right of back panel, 2.0 x 1.2 in",
                 "source": "KDP Create a Paperback Cover, verified 2026-10-11"},
        "panels": {"back": [0, bx1], "spine": [sx0, sx1], "front": [fx0, W]},
        "colors": {"cream": CREAM, "navy": NAVY, "coral": CORAL, "yellow": YELLOW,
                   "blue": BLUE, "green": GREEN},
        "fonts": ["Baloo2-ExtraBold.ttf", "Baloo2-Bold.ttf", "Nunito-Regular.ttf", "Nunito-Bold.ttf",
                  "Nunito-Italic.ttf"],
        "texts": {"title_lines": TITLE_LINES, "subtitle": SUBTITLE, "author": AUTHOR,
                  "tagline": TAGLINE, "blurb": BLURB, "bullets": BULLETS},
        "art": {"file": "illustrations/cover-art-front.png", "sha256": sha(ILL / "cover-art-front.png"),
                "native_px": list(art.size),
                "crop_pixels": [art_box[0], art_box[1], art_box[2] - art_box[0], art_box[3] - art_box[1]],
                "front_panel_scale": front_scale,
                "effective_dpi_at_placement": round(DPI / (front_scale or 1), 1)},
        "vignette": {"file": "illustrations/ch08-celebration-stars.png",
                     "sha256": sha(ILL / "ch08-celebration-stars.png"),
                     "crop_pixels": [170, 120, 1040, 620]},
    }
    (SRC / "cover-recipe.json").write_text(json.dumps(recipe, indent=1), encoding="utf-8")
    print(json.dumps(recipe["spec"], indent=1))
    print("front art scale:", front_scale, "-> effective dpi:", round(DPI / (front_scale or 1), 1))
    print("wrote:", wrap_png, COV / "cover-wrap-300dpi.pdf", COV / "ebook-cover-1600x2560.jpg")


if __name__ == "__main__":
    main()

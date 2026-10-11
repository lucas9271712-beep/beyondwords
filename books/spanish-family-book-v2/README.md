# Everyday English for Kids — A Spanish-English Activity Workbook

**Author:** Lucas Oliver · **Audience:** Spanish-speaking children ages 8–12 in the United States learning beginner English · **Buyer:** parents and caregivers in Spanish-speaking households
**Production workspace:** `beyondwords-projects/spanish-family-book-v2` (this folder, symlinked from the workspace root) and committed in-repo at `books/spanish-family-book-v2` for delivery; managed with the Beyondwords skill installed at `beyondwords/.agents/skills/beyondwords` (v1.1.0). The Beyondwords runtime store (`bwstore/`, SQLite) follows the repository convention of staying out of Git; its synced state (revision 31) is documented in `FINAL_QA_REPORT.md`.

## What this workspace is

A complete, reproducible production workspace for an illustrated bilingual activity workbook prepared for Amazon KDP paperback submission:

| Folder | Contents |
|---|---|
| `manuscript/` | The eight bilingual chapter sources (controlled Markdown subset) |
| `illustrations/` | Original AI-generated interior art + cover art (PNG, lossless) with `manifest.json` / `manifest.md` |
| `exports/` | Final deliverables: print interior PDF, combined manuscript, EPUB companion |
| `cover/` | Front-cover reference, full wraparound print PDF (300 DPI), 1600×2560 ebook cover |
| `source-files/` | Editable sources: `cover-recipe.json` (regenerates every cover file) |
| `fonts/` | OFL variable fonts (Baloo 2, Nunito, from google/fonts) + instantiated static weights + license notices |
| `build/` | Reproducible build & QA scripts (ReportLab, Pillow, pypdf; PyMuPDF used for QA rendering only) |
| `qa/` | Check outputs, page maps, rendered page images, proof PDF |
| `bwstore/` | Beyondwords versioned project store (SQLite). Project `93a89a95-ae86-470c-b3d2-70ff9e29b93c` |

## Reproducible build (all tools free)

```sh
pip install --user Pillow==12.3.0 reportlab==4.4.9 pypdf==6.19.0 fonttools pymupdf  # pymupdf = QA rendering only
python3 build/build_fonts.py      # instantiate static OFL weights from the variable fonts
python3 build/build_interior.py   # 2-pass build: exports/interior-8.5x11.pdf + qa/pagemap.json + exports/manuscript-combined.md
python3 build/build_cover.py      # needs the interior PDF for the verified page count -> cover/* + source-files/cover-recipe.json
python3 build/build_epub.py       # reflowable EPUB 3 companion -> exports/everyday-english-for-kids.epub
python3 build/qa_checks.py        # content checks -> qa/qa-results.json
python3 build/qa_pdf.py exports/interior-8.5x11.pdf   # geometry/font/text/image-DPI checks -> qa/pdf-checks.json
python3 build/render_pages.py exports/interior-8.5x11.pdf qa/render 1,5,20,40   # visual inspection renders
python3 build/make_manifest.py    # illustration manifest with native pixels and effective DPI
```

`BW_PROOF=1 python3 build/build_interior.py` builds a labelled layout proof (placeholder boxes for any
missing art) into `qa/interior-proof.pdf` without touching `exports/`.

## Print specification (KDP, verified against kdp.amazon.com on 2026-10-11)

- **Trim:** 8.5" × 11" (supported large trim; premium color + white paper allows 24–590 pages).
- **Interior bleed:** none (no artwork reaches the page edge); mirrored margins inside 0.75" / outside 0.6" / top 0.7" / bottom 0.65" — above KDP minima for every page-count band (gutter ≥ 0.375" up to 150 pp, ≥ 0.5" to 300 pp; outside ≥ 0.25").
- **Cover:** single PDF wrap = 0.125" bleed + back + spine + front + 0.125" bleed; height = trim + 0.25". Spine = pages × 0.002347" (premium color). No spine text (allowed only above 79 pages). Barcode zone kept clear on the back. All text ≥ 0.125" inside trim.
- **Ink/paper decision:** premium color on white paper. Standard color is unavailable below 72 pages and this book is shorter; premium color also gives the best illustration fidelity. US printing cost (large trim, 42–828 pp): $1.00 + $0.08/page → e.g. 46 pp = $4.68; minimum list at 60% royalty = print cost / 0.6.
- **Images:** placed at native pixels, effective 300+ DPI (audited with the skill's `publishing-check cover-art`: SUFFICIENT_DECLARED_NATIVE_PIXELS at 312.7 DPI for 4.4" placements).
- **Fonts:** Nunito + Baloo 2 (SIL OFL 1.1); embedded as subsets in the PDF; license notices kept in `fonts/`.

## Provenance and disclosure (honest labels)

- Text: drafted by the host AI from the owner's master brief, self-revised and QA-checked; stored in the Beyondwords project with `provenance: ai_generated` pending the owner's editorial review (then `ai_assisted`). KDP AI-disclosure answer for text: **YES** (generated, human-reviewed).
- Illustrations and cover art: AI-generated originals from original prompts; consistent character system (Maya, Leo, Nina, Sol); no copyrighted characters or copied artwork; recorded per asset in `illustrations/manifest.json`. KDP AI-disclosure answer for images: **YES**.
- Reviews stored in the project store are **model reviews, not independent human review** (`independent: false`). Human editorial, educational and visual review remain required before submission.

## Beyondwords project

Store: `bwstore/` (this environment). Project `93a89a95-ae86-470c-b3d2-70ff9e29b93c`. The revision-3 store referenced from the owner's Windows workspace (`C:\Users\User\Desktop\beyondwords-projects\spanish-family-book-v2`) does not exist in this sandbox clone; this store was initialized fresh here and every mutation used expected-revision chaining. The bundled text `edition` exporter rejects the `workbook` route by design ("visual routes need dedicated layout"), so the print PDF is produced by this workspace's ReportLab pipeline instead; that rejection is recorded in the QA report as expected behaviour, not a failure of the book.

## Status (2026-10-11)

**Complete.** 45-page illustrated interior PDF, 300-DPI wraparound cover at the verified page count, 1600×2560 ebook cover, EPUB companion, 16 original illustrations, all automated QA green (11/11 content, 8/8 PDF, cover pixel audits SUFFICIENT at 300 DPI). Store revision 31. Remaining gates are human: editorial/educational review, KDP Previewer run and physical proof — see `FINAL_QA_REPORT.md` and `exports/kdp-submission-checklist.md`.

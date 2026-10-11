#!/usr/bin/env python3
"""Content + file QA checks for the workbook. Writes qa/qa-results.json.
Every check reports PASS/FAIL/UNAVAILABLE honestly; nothing is marked passed without running."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAN = ROOT / "manuscript"
ILL = ROOT / "illustrations"
QA = ROOT / "qa"

CHAPTERS = [
    "chapter-01-welcome.md", "chapter-02-everyday-words.md", "chapter-03-meeting-people.md",
    "chapter-04-school-and-home.md", "chapter-05-questions-and-sentences.md",
    "chapter-06-everyday-dialogues.md", "chapter-07-reading-practice.md",
    "chapter-08-review-and-answers.md",
]

results = []


def check(name, ok, detail, kind="automated"):
    results.append({"check": name, "result": "PASS" if ok else "FAIL", "detail": detail, "kind": kind})
    return ok


def main():
    texts = {f: (MAN / f).read_text(encoding="utf-8") for f in CHAPTERS}

    # 1 files exist and nonzero
    ok = all((MAN / f).exists() and (MAN / f).stat().st_size > 0 for f in CHAPTERS)
    check("chapter files exist nonzero", ok,
          "; ".join(f"{f}:{(MAN / f).stat().st_size}B" for f in CHAPTERS))

    # 2 activity ids unique and key coverage
    act_re = re.compile(r"^### Activity (\d+\.\d+) ·", re.M)
    acts = {}
    for f, t in texts.items():
        for m in act_re.finditer(t):
            acts.setdefault(m.group(1), f)
    dup = [a for a in acts if len([m for m in act_re.finditer(texts[acts[a]]) if m.group(1) == a]) > 1]
    check("activity ids unique", not dup, f"{len(acts)} activities; duplicates={dup}")

    key_txt = texts["chapter-08-review-and-answers.md"]
    key_block = key_txt.split("## Answer Key / Clave de respuestas", 1)[1].split("## Glossary / Glosario", 1)[0]
    key_ids = set(re.findall(r"\*\*Activity (\d+\.\d+):\*\*", key_block))
    missing_keys = sorted(set(acts) - key_ids)
    check("every activity has an answer-key entry", not missing_keys,
          f"activities={len(acts)} keys={len(key_ids)} missing={missing_keys}")
    extra_keys = sorted(key_ids - set(acts))
    check("no orphan answer-key entries", not extra_keys, f"extra={extra_keys}")

    # 3 item-count agreement for closed-form activities
    problems = []
    for aid, fname in sorted(acts.items()):
        t = texts[fname]
        m = re.search(r"### Activity " + re.escape(aid) + r" ·.*?(?=\n### |\n## |\Z)", t, re.S)
        block = m.group(0)
        items = len(re.findall(r"^(\d+)\. ", block, re.M))
        km = re.search(r"\*\*Activity " + re.escape(aid) + r":\*\* (.+)", key_block)
        kline = km.group(1)
        if "will vary" in kline or "Self-check" in kline:
            continue
        kcount = len(re.findall(r"(?:^|,\s|)(\d+)[-– ]", kline))
        if items and kcount != items:
            problems.append(f"{aid}: items={items} key_entries={kcount}")
    check("closed-form item counts match key", not problems, "; ".join(problems) or "all closed activities match")

    # 4 spanish diacritics present, no mojibake
    moj = []
    for f, t in texts.items():
        for bad in ("Ã", "â€", "Â´", "ï¿½"):
            if bad in t:
                moj.append(f"{f}:{bad}")
    check("no mojibake", not moj, "; ".join(moj) or "clean utf-8")
    diac = all(ch in "".join(texts.values()) for ch in "áéíóúñ¿¡")
    check("spanish diacritics present", diac, "á é í ó ú ñ ¿ ¡ all present")

    # 5 image references resolve
    missing = []
    for f, t in texts.items():
        for m in re.finditer(r"\[\[image:(.+?)\|", t):
            if not (ILL / m.group(1)).exists():
                missing.append(f"{f}->{m.group(1)}")
    check("referenced illustrations exist", not missing, "; ".join(missing) or "all resolve")

    # 6 no placeholders / filler
    ph = []
    for f, t in texts.items():
        for bad in ("TODO", "Lorem", "FIXME", "XXX ", "placeholder"):
            if bad in t:
                ph.append(f"{f}:{bad}")
    check("no placeholder text", not ph, "; ".join(ph) or "none found")

    # 7 glossary alphabetical + count
    g = key_txt.split("## Glossary / Glosario", 1)[1]
    words = re.findall(r"^\| ([a-zA-Z][^|]*?) \|", g, re.M)
    words = [w for w in words if w not in ("English",)]
    lowered = [w.lower() for w in words]
    is_sorted = lowered == sorted(lowered)
    check("glossary alphabetical", is_sorted, f"{len(words)} entries; sorted={is_sorted}")

    # 8 bilingual instruction pairs: each activity has a spanish italic line
    noes = []
    for aid, fname in sorted(acts.items()):
        t = texts[fname]
        m = re.search(r"### Activity " + re.escape(aid) + r" ·.*?(?=\n### |\n## |\Z)", t, re.S)
        if not re.search(r"^\*[^*].+\*$", m.group(0), re.M):
            noes.append(aid)
    check("every activity has spanish instructions", not noes, f"missing={noes}")

    # 9 writespace directives sane
    ws = []
    for f, t in texts.items():
        for m in re.finditer(r"\[\[writespace:(\d+)\]\]", t):
            n = int(m.group(1))
            if not 1 <= n <= 8:
                ws.append(f"{f}:{n}")
    check("writespace line counts sane", not ws, "; ".join(ws) or "all 1-8 lines")

    QA.mkdir(exist_ok=True)
    json.dump(results, open(QA / "qa-results.json", "w"), indent=1)
    fails = [r for r in results if r["result"] == "FAIL"]
    for r in results:
        print(f"{r['result']:4} {r['check']}: {r['detail'][:160]}")
    print("TOTAL FAIL:", len(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

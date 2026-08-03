"""Run all corpus checks for one text. The verdict names its subject:
text id, word count, languages, witnesses, variant and error counts.
Exit 0 iff VERDICT OK. Zero words, zero witnesses, or zero languages FAIL —
a gate that checks nothing must not pass.

Usage: python run_checks.py <text-id>     e.g. ordinarium.confiteor
       python run_checks.py --all         every text under texts/
"""

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from checks.collate import collate
from checks.lint import lint_gloss, lint_parity, lint_text

CORPUS = Path(__file__).resolve().parent


def main(text_id: str) -> int:
    category, name = text_id.split(".", 1)
    text_path = CORPUS / "texts" / category / f"{name}.json"
    doc = json.loads(text_path.read_text(encoding="utf-8"))

    all_errors, all_warnings = [], []

    text_errors, n_words = lint_text(doc)
    all_errors += text_errors

    gloss_docs = []
    for gloss_path in sorted(CORPUS.glob(f"glosses/*/{text_id}.json")):
        gdoc = json.loads(gloss_path.read_text(encoding="utf-8"))
        gloss_docs.append(gdoc)
        all_errors += lint_gloss(gdoc, doc)
    all_errors += lint_parity(gloss_docs)
    langs = [g["lang"] for g in gloss_docs]
    if not langs:
        all_errors.append("no gloss layers found — refusing to pass on zero")

    witness_dir = CORPUS / "witnesses" / text_id
    coll_errors, coll_warnings, coll_stats = collate(doc, witness_dir)
    all_errors += coll_errors
    all_warnings += coll_warnings

    for w in all_warnings:
        print(f"WARN: {w}")
    for e in all_errors:
        print(f"ERROR: {e}")

    subject = (
        f"text={text_id} words={n_words} langs={','.join(langs) or '-'} "
        f"witnesses={coll_stats['witnesses']} variants={coll_stats['variants_adjudicated']}"
    )
    if all_errors:
        print(f"VERDICT FAIL {subject} errors={len(all_errors)} warnings={len(all_warnings)}")
        return 1
    print(f"VERDICT OK {subject} errors=0 warnings={len(all_warnings)}")
    return 0


def discover() -> list:
    ids = []
    for p in sorted(CORPUS.glob("texts/*/*.json")):
        ids.append(f"{p.parent.name}.{p.stem}")
    return ids


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: run_checks.py <text-id> | --all")
        sys.exit(2)
    if sys.argv[1] == "--all":
        ids = discover()
        if not ids:
            print("VERDICT FAIL no texts discovered under texts/ — refusing to pass on zero")
            sys.exit(1)
        rc = 0
        for tid in ids:
            rc |= main(tid)
        print(f"SUITE {'OK' if rc == 0 else 'FAIL'} texts={len(ids)}")
        sys.exit(rc)
    sys.exit(main(sys.argv[1]))

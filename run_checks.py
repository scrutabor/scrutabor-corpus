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
from checks.lexicon import (
    check_orphans,
    check_text_against_lexicon,
    lint_lemmata,
    lint_senses,
    load_lexicon,
)
from checks.lint import lint_analysis, lint_gloss, lint_parity, lint_text

CORPUS = Path(__file__).resolve().parent


def check_schema_versions() -> list[str]:
    """SCHEMA.md: schema_version is corpus-wide — every document carries the
    same number. Reads every document; zero documents is itself a failure."""
    versions = {}
    for path in sorted(CORPUS.glob("texts/*/*.json")) + sorted(
        CORPUS.glob("glosses/*/*.json")
    ) + sorted(CORPUS.glob("lexicon/*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        versions.setdefault(str(doc.get("schema_version")), []).append(
            str(path.relative_to(CORPUS))
        )
    if not versions:
        return ["no corpus documents found — refusing to pass on zero"]
    if len(versions) > 1:
        detail = "; ".join(f"{v}: {', '.join(ps)}" for v, ps in sorted(versions.items()))
        return [f"schema_version differs across the corpus — {detail}"]
    return []


def lexicon_suite(used_lemmas=None) -> int:
    """Global lexicon checks: shape, head orthography, language parity, and
    (given the set of lemmas every text uses) orphan entries. The per-text
    coverage/consistency half runs inside main()."""
    lemmata, langs, errors = load_lexicon(CORPUS)
    errors += lint_lemmata(lemmata)
    for lang, entries in sorted(langs.items()):
        errors += lint_senses(lang, entries, lemmata)
    if used_lemmas is not None:
        errors += check_orphans(lemmata, used_lemmas)
    for e in errors:
        print(f"ERROR: {e}")
    subject = f"lexicon entries={len(lemmata)} langs={','.join(sorted(langs)) or '-'}"
    if errors:
        print(f"VERDICT FAIL {subject} errors={len(errors)}")
        return 1
    print(f"VERDICT OK {subject} errors=0")
    return 0


def main(text_id: str) -> int:
    category, name = text_id.split(".", 1)
    text_path = CORPUS / "texts" / category / f"{name}.json"
    doc = json.loads(text_path.read_text(encoding="utf-8"))

    all_errors, all_warnings = [], []

    text_errors, n_words = lint_text(doc)
    all_errors += text_errors
    all_errors += lint_analysis(doc)
    all_errors += check_schema_versions()

    lemmata, _, lex_errors = load_lexicon(CORPUS)
    all_errors += lex_errors
    all_errors += check_text_against_lexicon(doc, lemmata)

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
        f"witnesses={coll_stats['witnesses']} variants={coll_stats['variants_adjudicated']} "
        f"lemmata={len(lemmata)}"
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
        used = set()
        for tid in ids:
            category, name = tid.split(".", 1)
            tdoc = json.loads((CORPUS / "texts" / category / f"{name}.json").read_text(encoding="utf-8"))
            for s in tdoc["segments"]:
                for w in s.get("words") or []:
                    used.add(w["lemma"])
        rc = lexicon_suite(used)
        for tid in ids:
            rc |= main(tid)
        print(f"SUITE {'OK' if rc == 0 else 'FAIL'} texts={len(ids)}")
        sys.exit(rc)
    # Single-text mode still runs the global lexicon shape checks (orphan
    # detection needs every text, so it is --all only).
    sys.exit(lexicon_suite(None) | main(sys.argv[1]))

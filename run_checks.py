"""Run all corpus checks for one text. The verdict names its subject:
text id, word count, languages, witnesses, variant and error counts.
Exit 0 iff VERDICT OK. Zero words, zero witnesses, or zero languages FAIL —
a gate that checks nothing must not pass.

Usage: python run_checks.py <text-id>     e.g. ordinarium.confiteor
       python run_checks.py --all         every text under texts/
"""

import json
import os
import sys
from pathlib import Path

from build_reader import store
from checks.addresses import check as check_addresses
from checks.apparatus import lint_apparatus_summary
from checks.capitals import check as check_capitals
from checks.citations import check as check_citation_titles
from checks.collate import collate
from checks.conventions import check as check_conventions
from checks.english import check as check_english
from checks.english import check_number as check_english_number
from checks.fusion import check as check_fusion
from checks.identity import check as check_identity
from checks.identity import check_against_history
from checks.incipit import check as check_incipit
from checks.lexicon import (
    check_derivative_homes,
    check_note_prose,
    check_orphans,
    check_paradigm,
    check_text_against_lexicon,
    lint_lemmata,
    lint_sense_parity,
    lint_senses,
    load_lexicon,
)
from checks.lint import (
    check_voices,
    duplicate_keys,
    lint_analysis,
    lint_gloss,
    lint_notes,
    lint_nulls,
    lint_parity,
    lint_rubrics,
    lint_text,
)
from checks.notes import check as check_notes
from checks.orthography import check as check_orthography
from checks.orthography import check_lexicon as check_orthography_lexicon
from checks.participation import check_doc as check_participation
from checks.polish import check as check_polish
from checks.rights import check as check_rights
from checks.rights import exposure as rights_exposure
from checks.rights import load as load_rights
from checks.syntax import check as check_syntax
from checks.syntax import coverage as syntax_coverage
from checks.transcription import check_transcriptions
from checks.uncertainty import check as check_uncertainty
from checks.uncertainty import exposure, readings, stored
from checks.vocalised import check as check_vocalised
from checks.witness_archive import check as check_witness_archive

# Before anything is written, not before anything is imported: the corpus
# prints Latin and Polish and the default encoding of a piped stdout is not
# always UTF-8.
sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

CORPUS = Path(__file__).resolve().parent


def check_schema_versions() -> list[str]:
    """SCHEMA.md: schema_version is corpus-wide — every document carries the
    same number. Reads every document; zero documents is itself a failure."""
    versions: dict[str, list[str]] = {}
    for path in sorted(CORPUS.glob("texts/*/*.json")) + sorted(CORPUS.glob("lexicon/*.json")):
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
    errors += check_paradigm(lemmata)
    if "en" in langs:
        errors += check_orthography_lexicon(langs["en"])
    for lang, entries in sorted(langs.items()):
        errors += lint_senses(lang, entries, lemmata)
    errors += lint_sense_parity(langs)
    if used_lemmas is not None:
        errors += check_orphans(lemmata, used_lemmas)
    for path in sorted(CORPUS.glob("lexicon/*.json")):
        data = json.loads(path.read_text())
        errors += check_derivative_homes(data)
        errors += check_note_prose(data)
    for e in errors:
        print(f"ERROR: {e}")
    subject = f"lexicon entries={len(lemmata)} langs={','.join(sorted(langs)) or '-'}"
    if errors:
        print(f"VERDICT FAIL {subject} errors={len(errors)}")
        return 1
    print(f"VERDICT OK {subject} errors=0")
    return 0


def main(text_id: str) -> int:
    text_path = store.path_of(CORPUS, text_id)
    # ONE document on disk, three in hand. The checks are each right about
    # their own job -- check_polish asks about one language and should keep
    # asking about one language -- so the seam is here (build_reader/store.py)
    # and not in twenty modules.
    doc, gloss_layers = store.load(CORPUS, text_id)

    all_errors, all_warnings = [], []

    text_errors, n_words = lint_text(doc)
    all_errors += text_errors
    all_errors += lint_analysis(doc)
    all_errors += lint_notes(doc)
    all_errors += lint_nulls(doc)
    all_errors += lint_rubrics(doc)
    # A word id is identity, not position. SCHEMA.md has said so all along and
    # nothing enforced it (checks/identity.py).
    all_errors += check_identity(doc)
    # The introit's repetition rubric names its OWN antiphon: the sentence was
    # written for the First Sunday and copied into two others that print a
    # different one (checks/incipit.py).
    all_errors += check_incipit(doc)
    # The typical edition drops the accent on a capital; this edition
    # restores it, and one text transcribed straight off a page image
    # would otherwise disagree with the eighty before it.
    all_errors += check_capitals(doc)
    voice_errors, attributed, n_verses = check_voices(doc)
    all_errors += voice_errors
    # Who the FAITHFUL answer with, which the Missale never says: derived
    # from the 1958 instruction and this text's own speakers, never stored
    # by hand (checks/participation.py).
    part_errors, participating = check_participation(doc)
    all_errors += part_errors
    # Agreement and government, checked against the edition's own syntax
    # (schema 0.13.0, checks/syntax.py). `syntax` counts what is declared;
    # a modifier with no head yet is work outstanding, not a failure.
    all_errors += check_syntax(doc)
    syn_declared, syn_total = syntax_coverage(doc)
    all_errors += duplicate_keys(text_path)
    all_errors += check_schema_versions()

    lemmata, _, lex_errors = load_lexicon(CORPUS)
    all_errors += lex_errors
    all_errors += check_text_against_lexicon(doc, lemmata)

    gloss_docs = []
    for _lang, gdoc in sorted(gloss_layers.items()):
        gloss_docs.append(gdoc)
        all_errors += lint_gloss(gdoc, doc)
        # The gloss line read AS POLISH: a preposition governing the case
        # beside it, a modifier agreeing with what it modifies, the divine
        # second person capitalised as the verse capitalises it.
        all_errors += check_polish(doc, gdoc)
        all_errors += check_notes(doc, gdoc)
        # A gloss that renders nothing must say why it renders nothing.
        all_errors += check_fusion(doc, gdoc)
        # The three gloss conventions the reading campaign settled.
        all_errors += check_conventions(doc, gdoc)
        # One edition, one spelling.
        all_errors += check_orthography(doc, gdoc)
        # A Polish preposition stranded at the end of a gloss is voiced by
        # the NEXT gloss, which no single-cell check can see.
        all_errors += check_vocalised(doc, gdoc)
        # English, where English can be checked exactly: a preposition
        # rendered twice, and a two-case preposition against its case.
        all_errors += check_english(doc, gdoc)
    all_errors += lint_parity(gloss_docs)
    langs = [g["lang"] for g in gloss_docs]
    if not langs:
        all_errors.append("no gloss layers found — refusing to pass on zero")

    witness_dir = CORPUS / "witnesses" / text_id
    all_errors += lint_apparatus_summary(witness_dir / "apparatus.json")
    transcription_errors, transcriptions_checked = check_transcriptions(witness_dir)
    all_errors += transcription_errors
    coll_errors, coll_warnings, coll_stats = collate(doc, witness_dir)
    all_errors += coll_errors
    all_warnings += coll_warnings

    for w in all_warnings:
        print(f"WARN: {w}")
    for e in all_errors:
        print(f"ERROR: {e}")

    corrigenda = (
        (f"corrigenda={coll_stats['corrigenda']} " if coll_stats.get("corrigenda") else "")
        + (f"orthographic={coll_stats['orthographic']} " if coll_stats.get("orthographic") else "")
        + (f"inflections={coll_stats['inflections']} " if coll_stats.get("inflections") else "")
        + (f"recensions={coll_stats['recensions']} " if coll_stats.get("recensions") else "")
        + (f"omissions={coll_stats['omissions']} " if coll_stats.get("omissions") else "")
        + (f"speakers={attributed}/{n_verses} " if n_verses else "")
        + (f"participation={participating} " if participating else "")
        + (f"syntax={syn_declared}/{syn_total}-declared " if syn_total else "")
        + (f"raw={transcriptions_checked} " if transcriptions_checked else "")
    )
    subject = (
        f"text={text_id} words={n_words} langs={','.join(langs) or '-'} "
        f"witnesses={coll_stats['witnesses']}"
        + (f"+{coll_stats['partial']}partial" if coll_stats.get("partial") else "")
        + f" variants={coll_stats['variants_adjudicated']} "
        f"{corrigenda}lemmata={len(lemmata)}"
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
            tdoc = store.load(CORPUS, tid)[0]
            for s in tdoc["segments"]:
                for w in s.get("words") or []:
                    used.add(w["lemma"])
        rc = lexicon_suite(used)
        for tid in ids:
            rc |= main(tid)
        # English number is checked ACROSS the corpus, not per text: with no
        # analyzer the only oracle is the corpus itself, and one gloss serving
        # both numbers of a lemma is only visible with every text in hand.
        pairs = []
        for tid in ids:
            category, name = tid.split(".", 1)
            pairs.append(
                (
                    store.load(CORPUS, tid)[0],
                    store.load(CORPUS, tid)[1]["en"],
                )
            )
        number_errors = check_english_number(pairs)
        for message in number_errors:
            print(f"ERROR: {message}")
        rc |= 1 if number_errors else 0
        # What the edition does not know, stated as a number rather than left
        # to be inferred from a silent default.
        corpus_docs = [t for t, _ in pairs]
        doubt_errors = check_uncertainty(corpus_docs)
        for message in doubt_errors:
            print(f"ERROR: {message}")
        rc |= 1 if doubt_errors else 0
        # Identity across TIME, which one snapshot cannot answer. Compared
        # against the base branch in CI and against HEAD locally.
        history_errors = check_against_history(CORPUS, os.environ.get("SCRUTABOR_BASE", "HEAD"))
        for message in history_errors:
            print(f"ERROR: {message}")
        rc |= 1 if history_errors else 0

        # A text id is the other half of every word's global address.
        address_errors = check_addresses(CORPUS, {d["id"] for d in corpus_docs})
        for message in address_errors:
            print(f"ERROR: {message}")
        rc |= 1 if address_errors else 0

        witness_errors = check_witness_archive(CORPUS)
        for message in witness_errors:
            print(f"ERROR: {message}")
        rc |= 1 if witness_errors else 0
        # One work, one title. The bibliography groups citations on the title
        # string, so this only shows up with the whole corpus in hand — two
        # correct spellings of one dictionary list it twice for the reader.
        cited = (
            corpus_docs
            + [g for _doc, layers in store.all_texts(CORPUS) for g in layers.values()]
            + [
                json.loads(p.read_text(encoding="utf-8"))
                for p in sorted(CORPUS.glob("lexicon/*.json"))
            ]
        )
        # What this edition may reproduce, counted rather than assumed. Every
        # cited work must say what it is (checks/rights.py).
        works, rights_errors = load_rights(CORPUS)
        rights_errors += check_rights(cited, works)
        for message in rights_errors:
            print(f"ERROR: {message}")
        rc |= 1 if rights_errors else 0

        title_errors = check_citation_titles(cited)
        for message in title_errors:
            print(f"ERROR: {message}")
        rc |= 1 if title_errors else 0
        wording = rights_exposure(cited, works)
        print(
            "RIGHTS wording sites — "
            + " ".join(f"{k}={v}" for k, v in sorted(wording.items()) if v)
        )
        attested = readings(corpus_docs)
        print(
            f"UNCERTAINTY exposure>={sum(exposure(d, attested) for d in corpus_docs)} "
            f"stored={sum(stored(d) for d in corpus_docs)}"
        )
        from checks.disputed import collect

        found = collect()
        n_tokens = sum(len(v) for v in found.values())
        print(
            f"SUITE {'OK' if rc == 0 else 'FAIL'} texts={len(ids)} "
            f"disputed={n_tokens}/{len(found)} forms"
        )
        sys.exit(rc)
    # Single-text mode still runs the global lexicon shape checks (orphan
    # detection needs every text, so it is --all only).
    sys.exit(lexicon_suite(None) | main(sys.argv[1]))

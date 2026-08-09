"""Lexicon checks: entry shape, orthography of dictionary heads, two-way
coverage against the texts, per-language parity, and lemmata-vs-morph
consistency (the lemma layer and the token layer must never disagree
silently — SCHEMA.md)."""

import json
import re

from .lint import BANNED_TERMS, MORPH_ENUMS, SPELLING_EXEMPT
from .normalize import ACCENTED_VOWELS, fold_ligatures, has_accent, strip_accents, syllable_count

LEMMATA_ENTRY_KEYS = {
    "head",
    "pos",
    "pos_alt",
    "gender",
    "gender_alt",
    "gender_pl",
    "decl",
    "conj",
    "analysis",
}
SENSE_ENTRY_KEYS = {"senses", "note", "derivatives", "analysis"}

# A head is dictionary punctuation plus word tokens; ending fragments ("-æ",
# "-a") and the deponent auxiliary carry no accent rules of their own.
HEAD_TOKEN_RE = re.compile(r"^[A-Za-zÁÉÍÓÚÝáéíóúýÆæŒœǼǽËë]+$")


def load_lexicon(corpus_dir):
    """Returns (lemmata_entries, {lang: entries}, errors). Missing files are
    errors — a corpus without a lexicon must not pass (SCHEMA.md 0.5.0)."""
    errors = []
    lemmata_path = corpus_dir / "lexicon" / "lemmata.json"
    if not lemmata_path.exists():
        return {}, {}, ["lexicon/lemmata.json missing"]
    lemmata = json.loads(lemmata_path.read_text(encoding="utf-8"))["entries"]
    langs = {}
    for p in sorted((corpus_dir / "lexicon").glob("*.json")):
        if p.name == "lemmata.json":
            continue
        doc = json.loads(p.read_text(encoding="utf-8"))
        langs[doc["lang"]] = doc["entries"]
    if not langs:
        errors.append("lexicon: no language files found — refusing to pass on zero")
    return lemmata, langs, errors


def _lint_head(lemma, head, errors):
    for token in re.split(r"[,\s]+", head):
        if not token or token.startswith("-"):
            continue
        if not HEAD_TOKEN_RE.match(token):
            errors.append(f"lexicon:{lemma}: charset violation in head token {token!r}")
            continue
        # The same exemptions the token layer grants (checks/lint.py), for the
        # same words and the same recorded reasons.
        if fold_ligatures(strip_accents(token)).lower() in SPELLING_EXEMPT:
            continue
        # A head is read by the same readers as the text and must be spelled
        # the same way. This rule is here because it was missing: eight heads
        # sat in the j-form after the orthography was reversed, two of them
        # half-converted (majéstas, maiestátis), and nothing complained.
        if "j" in token.lower():
            errors.append(
                f"lexicon:{lemma}: head token {token!r} spells the consonant with j — "
                "ORTHOGRAPHY.md prints i"
            )
        n, acc = syllable_count(token), has_accent(token)
        n_marks = sum(1 for ch in token if ch in ACCENTED_VOWELS)
        if n >= 3 and not acc:
            errors.append(f"lexicon:{lemma}: head token {token!r} has {n} syllables but no accent")
        if n <= 2 and acc:
            errors.append(
                f"lexicon:{lemma}: head token {token!r} has {n} syllables but carries an accent"
            )
        if n_marks > 1:
            errors.append(f"lexicon:{lemma}: head token {token!r} carries {n_marks} accents")


def lint_lemmata(entries):
    errors = []
    if not entries:
        errors.append("lexicon: zero lemmata entries — refusing to pass on zero")
        return errors
    for lemma, e in entries.items():
        unknown = set(e) - LEMMATA_ENTRY_KEYS
        if unknown:
            errors.append(f"lexicon:{lemma}: unknown keys {sorted(unknown)}")
        if not e.get("head"):
            errors.append(f"lexicon:{lemma}: missing head")
        else:
            _lint_head(lemma, e["head"], errors)
        if e.get("pos") not in MORPH_ENUMS["pos"]:
            errors.append(f"lexicon:{lemma}: pos={e.get('pos')!r} not in enum")
        if "pos_alt" in e and e["pos_alt"] not in MORPH_ENUMS["pos"]:
            errors.append(f"lexicon:{lemma}: pos_alt={e['pos_alt']!r} not in enum")
        for k in ("gender", "gender_alt", "gender_pl"):
            if k in e and e[k] not in MORPH_ENUMS["gender"]:
                errors.append(f"lexicon:{lemma}: {k}={e[k]!r} not in enum")
        if "decl" in e and e["decl"] not in range(1, 6):
            errors.append(f"lexicon:{lemma}: decl={e['decl']!r} out of range")
        if "conj" in e and e["conj"] not in range(1, 5):
            errors.append(f"lexicon:{lemma}: conj={e['conj']!r} out of range")
    return errors


def lint_senses(lang, entries, lemmata):
    errors = []
    banned = BANNED_TERMS.get(lang, [])
    for lemma, e in entries.items():
        unknown = set(e) - SENSE_ENTRY_KEYS
        if unknown:
            errors.append(f"lexicon:{lang}:{lemma}: unknown keys {sorted(unknown)}")
        senses = e.get("senses")
        if not senses or not all(isinstance(s, str) and s for s in senses):
            errors.append(f"lexicon:{lang}:{lemma}: senses must be 1+ nonempty strings")
        elif len(senses) > 4:
            errors.append(
                f"lexicon:{lang}:{lemma}: {len(senses)} senses — SCHEMA.md allows at most 4"
            )
        derivs = e.get("derivatives")
        if derivs is not None:
            if not derivs or not all(isinstance(d, str) and d for d in derivs):
                errors.append(f"lexicon:{lang}:{lemma}: derivatives must be 1+ nonempty strings")
            elif len(derivs) > 6:
                errors.append(
                    f"lexicon:{lang}:{lemma}: {len(derivs)} derivatives — "
                    "SCHEMA.md allows at most 6"
                )
        prose = " ".join(senses or []) + " " + " ".join(derivs or []) + " " + e.get("note", "")
        for pat in banned:
            if re.search(pat, prose, re.IGNORECASE):
                errors.append(
                    f"lexicon:{lang}:{lemma}: banned terminology/typography "
                    f"{pat!r} (TERMINOLOGY.md)"
                )
    missing = sorted(set(lemmata) - set(entries))
    extra = sorted(set(entries) - set(lemmata))
    if missing:
        errors.append(f"lexicon:{lang}: no entry for {missing}")
    if extra:
        errors.append(f"lexicon:{lang}: entries for unknown lemmas {extra}")
    return errors


def check_orphans(lemmata, used_lemmas):
    orphans = sorted(set(lemmata) - used_lemmas)
    if orphans:
        return [f"lexicon: orphan entries not used by any text: {orphans}"]
    return []


def check_text_against_lexicon(text_doc, lemmata):
    """Coverage + consistency for one text: every lemma has an entry, and the
    entry's paradigm facts agree with every token's morph."""
    errors = []
    tid = text_doc["id"]
    for seg in text_doc["segments"]:
        for w in seg.get("words") or []:
            lemma, morph, wid = w["lemma"], w["morph"], w["id"]
            e = lemmata.get(lemma)
            if e is None:
                errors.append(f"{tid}:{wid}: lemma {lemma!r} has no lexicon entry")
                continue
            if morph["pos"] not in {e.get("pos"), e.get("pos_alt")}:
                errors.append(
                    f"{tid}:{wid}: morph.pos={morph['pos']!r} but lexicon says {e.get('pos')!r}"
                )
            if morph["pos"] == "noun":
                if "decl" in morph and "decl" in e and morph["decl"] != e["decl"]:
                    errors.append(
                        f"{tid}:{wid}: morph.decl={morph['decl']} but lexicon says {e['decl']}"
                    )
                expected_gender = e.get("gender")
                if morph.get("number") == "pl" and "gender_pl" in e:
                    expected_gender = e["gender_pl"]
                # gender_alt: a second dictionary gender (dies m., f. for
                # appointed days) — either satisfies the check.
                allowed = {g for g in (expected_gender, e.get("gender_alt")) if g}
                if "gender" in morph and allowed and morph["gender"] not in allowed:
                    errors.append(
                        f"{tid}:{wid}: morph.gender={morph['gender']!r} "
                        f"but lexicon says {sorted(allowed)!r}"
                    )
            if (
                morph["pos"] == "verb"
                and "conj" in morph
                and "conj" in e
                and morph["conj"] != e["conj"]
            ):
                errors.append(
                    f"{tid}:{wid}: morph.conj={morph['conj']} but lexicon says {e['conj']}"
                )
    return errors

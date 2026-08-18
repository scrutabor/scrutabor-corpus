"""Lexicon checks: entry shape, orthography of dictionary heads, two-way
coverage against the texts, per-language parity, and lemmata-vs-morph
consistency (the lemma layer and the token layer must never disagree
silently — SCHEMA.md)."""

import json
import re

from .lint import BANNED_TERMS, MORPH_ENUMS, SPELLING_EXEMPT, lint_citations
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
SENSE_ENTRY_KEYS = {"senses", "note", "note_citations", "derivatives", "analysis"}

# A head is dictionary punctuation plus word tokens; ending fragments ("-æ",
# "-a") and the deponent auxiliary carry no accent rules of their own.
HEAD_TOKEN_RE = re.compile(r"^[A-Za-zÁÉÍÓÚÝáéíóúýÆæŒœǼǽËë\u0301]+$")

# A lemma note is rendered on a dictionary page, without the verse or prayer
# in which any one token occurs. Deictic prose therefore has no antecedent
# there and usually signals that occurrence-specific commentary leaked out of
# a gloss function. Explicit references such as "In Psalm 118:34" remain
# available when naming the context is genuinely useful.
CONTEXT_DEIXIS = {
    "pl": (
        r"\bw tym (?:wersecie|zdaniu|tekście|fragmencie|miejscu|psalmie|hymnie|kontekście)\b",
        r"\bw tej (?:modlitwie|pieśni|antyfonie|formule|frazie)\b",
        r"\btu(?:taj)?\s+(?:jednak|nie|o|oznacza|nazywa|odnosi|jest|ma)\b",
        r"\b(?:modlitwa|psalmista|werset|tekst)\s+(?:nazywa|prosi|mówi|wskazuje|odnosi|opisuje)\b",
        r"\b(?:prosi się|mówi się tu)\b",
    ),
    "en": (
        r"\bin this (?:verse|sentence|text|passage|place|psalm|hymn|prayer|"
        r"invocation|dialogue|context|antiphon|formula|phrase)\b",
        r"\bhere (?:it|the|this|that)\b",
        r"\bthe (?:prayer|psalmist|verse|text)\s+(?:calls|asks|says|names|"
        r"indicates|refers|describes)\b",
        r"\bthe \w+(?:\s+\w+){0,2}\s+(?:is|are) asked\b",
    ),
}


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
    derivative_homes = {}
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
            if isinstance(derivs, list) and all(isinstance(d, str) for d in derivs):
                for derivative in derivs:
                    display = re.sub(r"\s+\([^()]+\)$", "", derivative).casefold()
                    derivative_homes.setdefault(display, []).append(
                        (lemma, derivative, display != derivative.casefold())
                    )
        prose = " ".join(senses or []) + " " + " ".join(derivs or []) + " " + e.get("note", "")
        for pat in banned:
            if re.search(pat, prose, re.IGNORECASE):
                errors.append(
                    f"lexicon:{lang}:{lemma}: banned terminology/typography "
                    f"{pat!r} (TERMINOLOGY.md)"
                )
        note = e.get("note", "")
        if "note_citations" in e:
            if not note:
                errors.append(f"lexicon:{lang}:{lemma}: citations without a note")
            errors += lint_citations(e["note_citations"], f"lexicon:{lang}:{lemma}")
        for pat in CONTEXT_DEIXIS.get(lang, ()):
            if re.search(pat, note, re.IGNORECASE):
                errors.append(
                    f"lexicon:{lang}:{lemma}: context-dependent deixis {pat!r} — "
                    "move occurrence-specific prose to a gloss function or name the context"
                )
    for display, homes in sorted(derivative_homes.items()):
        if len(homes) > 1 and any(annotated for _, _, annotated in homes):
            locations = ", ".join(f"{lemma}: {raw!r}" for lemma, raw, _ in homes)
            errors.append(
                f"lexicon:{lang}: derivative {display!r} has duplicate homes "
                f"({locations}) — keep it at its direct home"
            )
    missing = sorted(set(lemmata) - set(entries))
    extra = sorted(set(entries) - set(lemmata))
    if missing:
        errors.append(f"lexicon:{lang}: no entry for {missing}")
    if extra:
        errors.append(f"lexicon:{lang}: entries for unknown lemmas {extra}")
    return errors


def lint_sense_parity(langs):
    """A citation supports a claim about the Latin word, not one rendering
    of that claim. Its presence and bibliographic metadata therefore agree
    exactly across language layers."""
    errors = []
    if len(langs) < 2:
        return errors
    ordered = sorted(langs.items())
    base_lang, base = ordered[0]
    for lang, entries in ordered[1:]:
        for lemma in sorted(set(base) & set(entries)):
            left = base[lemma].get("note_citations")
            right = entries[lemma].get("note_citations")
            if left != right:
                errors.append(f"lexicon: citation parity differs {base_lang} vs {lang} for {lemma}")
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


def check_derivative_homes(lex: dict) -> list[str]:
    """A derivative belongs to ONE lemma: the nearest Latin ancestor it descends from.

    Listing *oracja* under both `oratio` and `oro`, or *passion* under both
    `passio` and `patior`, tells the reader the word has two parents. 47 such
    listings had accumulated, every one the same shape — a derivative filed
    under both a verb and its own deverbal noun, or under a base and the
    compound it actually comes through (*receive* under `capio` as well as
    `recipio`).
    """
    home: dict[str, list[str]] = {}
    for lemma, entry in (lex.get("entries") or {}).items():
        for d in entry.get("derivatives") or []:
            form = d if isinstance(d, str) else d.get("form")
            home.setdefault(form, []).append(lemma)
    return [
        f"derivative {form!r} is listed under {len(ls)} lemmata ({', '.join(sorted(ls))}): "
        f"it belongs to the nearest ancestor only"
        for form, ls in sorted(home.items())
        if len(ls) > 1
    ]


def check_note_prose(lex: dict) -> list[str]:
    """The lexicon's notes answer to the edition's prose rule like every other page.

    The edition's no-semicolon rule was applied to the reader-facing strings
    and to 121 gloss documents, and the guard that keeps it reads
    `words[id].note`. The lexicon keeps its notes at `entries[lemma].note`, so
    72 of them were never swept — and the lexicon is vendored and rendered, so
    a reader met every one of them on a lemma page.
    """
    errors = []
    for lemma, entry in sorted((lex.get("entries") or {}).items()):
        # senses are checked on EVERY entry: gating them behind `note` would
        # have covered 329 of 878.
        for sense in entry.get("senses") or []:
            if ";" in sense:
                errors.append(
                    f"lexicon sense {sense!r} under {lemma!r} packs two senses into one string: "
                    f"the senses field is a LIST"
                )
        note = entry.get("note")
        if not note:
            continue
        if ";" in note:
            errors.append(f"lexicon note {lemma!r} uses a semicolon: use a full stop or an 'and'")
        if not note.rstrip().endswith((".", "?", "!", "”", '"', "’")):
            errors.append(f"lexicon note {lemma!r} does not end its sentence")
    return errors


# Every noun states its declension and every verb its conjugation, unless it is
# one of the words that has none to state. The irregulars are named here rather
# than inferred, because "no declension recorded" and "no declension exists"
# look identical in the data and mean opposite things — six nouns were simply
# missing theirs until 2026-08-17, indistinguishable from the Hebrew names
# beside them.
INDECLINABLE = {
    "Ierusalem",
    "Abel",
    "Abraham",
    "Ioseph",
    "Israel",
    "Melchisedech",
    "sabaoth",
    "seraphim",
    "nihil",  # indeclinable by nature
    "Iesus",
    "kyrie",  # Greek, declined on their own pattern
}
IRREGULAR_VERBS = {
    "sum",
    "eo",
    "fio",
    "volo",
    "memini",
    "prosum",
    "aufero",
    "offero",
    "perfero",  # compounds of fero
    "introeo",
    "praetereo",
    "transeo",  # compounds of eo
    "eleison",  # Greek imperative
}


def check_paradigm(lemmata: dict) -> list[str]:
    """A noun without a declension, or a verb without a conjugation, that is
    not one of the words which has none.

    Takes either the whole lemmata document or the entries mapping, because
    the loader hands over the latter and a reader of this file will reach for
    the former.
    """
    entries = lemmata.get("entries") if "entries" in lemmata else lemmata
    errors = []
    for name, entry in sorted((entries or {}).items()):
        pos = entry.get("pos")
        if pos == "noun" and "decl" not in entry and name not in INDECLINABLE:
            errors.append(
                f"lexicon:{name}: a noun with no declension recorded — add it, or name "
                f"the word in INDECLINABLE if it has none"
            )
        if pos == "verb" and "conj" not in entry and name not in IRREGULAR_VERBS:
            errors.append(
                f"lexicon:{name}: a verb with no conjugation recorded — add it, or name "
                f"the word in IRREGULAR_VERBS if it has none"
            )
    return errors

"""Mechanical corpus lint: schema shape, charset, orthography (ORTHOGRAPHY.md),
accent rules, cross-references, quoted forms, terminology, layer parity."""

import re

from .normalize import ACCENTED_VOWELS, fold_ligatures, has_accent, strip_accents, syllable_count

MORPH_ENUMS = {
    "pos": {"verb", "noun", "adj", "pron", "adv", "conj", "prep", "intj"},
    "case": {"nom", "gen", "dat", "acc", "abl", "voc"},
    "number": {"sg", "pl"},
    "gender": {"m", "f", "n"},
    "tense": {"pres", "impf", "fut", "perf", "plup", "futperf"},
    "mood": {"ind", "subj", "imp", "inf", "part"},
    "voice": {"act", "pass", "dep"},
    "degree": {"comp", "sup"},
    "governs": {"acc", "abl"},
}

FORM_RE = re.compile(r"^[A-Za-zÁÉÍÓÚÝáéíóúýÆæŒœǼǽËë]+$")
REF_RE = re.compile(r"\((w\d{3})\)")
QUOTE_REF_RE = re.compile(r"[„“]([^”“„]+)”\s*\((w\d{3})\)")

# Terminology contract (corpus/TERMINOLOGY.md): banned variants per language.
BANNED_TERMS = {
    "pl": [
        r"ablatiw",  # ablatiwus/ablatiwie/... -> ablativus/ablativie/...
        r"ablativ\w* środka",  # -> ablativus narzędzia (TERMINOLOGY.md)
        r"\bzgodn\w+ ze? „",  # agreement claim -> "zgadza się z „..."
    ],
    "en": ["„"],  # Polish low-opening quote in English text
}

# The corpus stores text, not typesetting. Polish does not leave a one-letter
# word at the end of a line, but binding it is the reader app's job: a
# non-breaking space here would travel into every consumer of this data and
# be invisible to whoever edits the file next.
LAYOUT_CHARS = {
    "\u00a0": "non-breaking space",
    "\u2007": "figure space",
    "\u202f": "narrow no-break space",
    "\u200b": "zero-width space",
    "\u00ad": "soft hyphen",
}

# True proper names, which alone keep their capital in a lemma key
# (SCHEMA.md); divine titles are lowercase common nouns. Grows as texts
# require — the Canon's two lists of saints added most of these.
PROPER_LEMMAS = {
    "Abel",
    "Abraham",
    "Agatha",
    "Agnes",
    "Alexander",
    "Anastasia",
    "Andreas",
    "Baptista",
    "Barnabas",
    "Bartholomaeus",
    "Caecilia",
    "Christus",
    "Chrysogonus",
    "Clemens",
    "Cletus",
    "Cornelius",
    "Cosmas",
    "Cyprianus",
    "Damianus",
    "Felicitas",
    "Iacobus",
    "Iesus",
    "Ignatius",
    "Ioannes",
    "Ioseph",
    "Laurentius",
    "Linus",
    "Lucia",
    "Marcellinus",
    "Maria",
    "Matthaeus",
    "Matthias",
    "Melchisedech",
    "Michael",
    "Paulus",
    "Perpetua",
    "Petrus",
    "Philippus",
    "Pilatus",
    "Pontius",
    "Simon",
    "Stephanus",
    "Thaddaeus",
    "Thomas",
    "Eva",
    "Xystus",
}

# Forms exempt from the SPELLING heuristics at the end of lint_text (the
# j-for-consonantal-i rules and the accent-versus-syllable rules). Nothing
# else is exempt, and each entry carries the reason it had to be.
#
#   eia — the interjection of the Salve Regína. Its i is genuinely vocalic,
#   so the rule that wants j (written for ejus, ejusdem…) has nothing to
#   catch here; and its ei is a diphthong, so the word has two syllables and
#   rightly carries no accent. The syllable counter knows only the au
#   diphthong, and teaching it ei would mis-count diéi, meis and their like.
#
# Keyed on the normalized spelling (accents stripped, ligatures expanded,
# lowercased) — the same `plain` the heuristics test.
# The books keep the glide spelled i in a few words where ORTHOGRAPHY.md
# would otherwise want j (Eia in the Salve Regina, allelúia). Only the
# SPELLING rule is waived: the syllable counter reads the glide correctly,
# so these words still answer to the accent rule like any other.
SPELLING_EXEMPT = {
    "eia": "the books print Eia, not Eja — the glide keeps its i here",
    "alleluia": "the books print allelúia, not allelúja",
}

# Who says a segment, and how loudly (SCHEMA.md, since 0.9.0). Both are
# READ from the sources, not remembered: the speaker from the witnesses'
# own markers (S. sacerdos, M. minister, V./R. versicle and response), the
# voice from the rubrics that say secreto, clara voce, elata aliquantulum
# voce. Optional while the attribution pass proceeds — a segment with no
# attribution says "not yet read", which is the honest state and the one
# the app must render as unmarked rather than guess.
SPEAKERS = {"sacerdos", "minister", "populus", "omnes", "schola"}
VOICES = {"clara", "submissa", "secreto", "cantus"}


def check_voices(doc):
    """Validate speaker/voice wherever present; report how much is read."""
    errors, attributed, verses = [], 0, 0
    for seg in doc["segments"]:
        speaker, voice = seg.get("speaker"), seg.get("voice")
        if seg.get("type") == "verse":
            verses += 1
            if speaker:
                attributed += 1
        elif speaker or voice:
            errors.append(
                f"{seg['id']}: only a verse segment has a speaker or a voice — "
                "a rubric is the edition's own framing, not anyone's words"
            )
        if speaker is not None and speaker not in SPEAKERS:
            errors.append(f"{seg['id']}: unknown speaker {speaker!r} (one of {sorted(SPEAKERS)})")
        if voice is not None and voice not in VOICES:
            errors.append(f"{seg['id']}: unknown voice {voice!r} (one of {sorted(VOICES)})")
    return errors, attributed, verses


# Provenance (SCHEMA.md, since 0.7.0). Witness ids are also valid sources;
# their grammar mirrors the witness directory names.
ANALYSIS_ENUMS = {
    "confidence": {"high", "medium", "low"},
    "review": {"pending", "accepted", "disputed"},
}
ANALYSIS_KEYS = {"confidence", "sources", "review"}
KNOWN_SOURCES = {"whitakers", "collatinus", "editorial", "treebank", "expert"}
SOURCE_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def check_analysis(obj, where):
    """Shape of one analysis object; the resolution order is
    word.analysis ?? analysis_defaults_words ?? analysis_defaults."""
    if not isinstance(obj, dict):
        return [f"{where}: analysis must be an object"]
    errors = [f"{where}: analysis missing {k}" for k in ANALYSIS_KEYS - set(obj)]
    errors += [f"{where}: analysis has unknown key {k!r}" for k in set(obj) - ANALYSIS_KEYS]
    for key, allowed in ANALYSIS_ENUMS.items():
        if key in obj and obj[key] not in allowed:
            errors.append(f"{where}: analysis.{key}={obj[key]!r} not in enum")
    sources = obj.get("sources")
    if sources is not None:
        if not isinstance(sources, list) or not sources:
            errors.append(f"{where}: analysis.sources must be a nonempty list")
        else:
            for s in sources:
                if not isinstance(s, str) or not SOURCE_RE.match(s):
                    errors.append(f"{where}: analysis source {s!r} malformed")
    return errors


def lint_analysis(doc):
    """Provenance layer of a text document: defaults well-formed, overrides
    well-formed and never redundantly restating the default they override."""
    errors = check_analysis(doc["analysis_defaults"], "analysis_defaults")
    defaults_words = doc.get("analysis_defaults_words")
    if defaults_words is not None:
        errors += check_analysis(defaults_words, "analysis_defaults_words")
        if defaults_words == doc["analysis_defaults"]:
            errors.append("analysis_defaults_words identical to analysis_defaults — drop it")
    word_default = defaults_words if defaults_words is not None else doc["analysis_defaults"]
    for seg in doc["segments"]:
        if "analysis" in seg:
            errors += check_analysis(seg["analysis"], seg["id"])
            if seg["analysis"] == doc["analysis_defaults"]:
                errors.append(f"{seg['id']}: analysis restates the default — drop it")
        for w in seg.get("words") or []:
            if "analysis" in w:
                errors += check_analysis(w["analysis"], w["id"])
                if w["analysis"] == word_default:
                    errors.append(f"{w['id']}: analysis restates the word default — drop it")
    return errors


def lint_text(doc):
    errors = []
    words = [w for s in doc["segments"] for w in s.get("words") or []]
    if not words:
        errors.append("no words in document — refusing to pass on zero")
        return errors, 0
    ids = [w["id"] for w in words]
    if len(ids) != len(set(ids)):
        errors.append("duplicate word ids")
    for w in words:
        wid, f = w["id"], w["form"]
        if not FORM_RE.match(f):
            errors.append(f"{wid}: charset violation in form {f!r}")
        lemma = w.get("lemma", "")
        if lemma and lemma[0].isupper() and lemma not in PROPER_LEMMAS:
            errors.append(f"{wid}: lemma {lemma!r} capitalized but not in proper-name list (SCHEMA.md)")
        for k, v in w["morph"].items():
            if k in MORPH_ENUMS and v not in MORPH_ENUMS[k]:
                errors.append(f"{wid}: morph.{k}={v!r} not in enum")
        m = w["morph"]
        if m.get("pos") == "verb" and m.get("mood") == "part":
            # Participles agree like nominals and have no person (SCHEMA.md).
            for req in ("case", "number", "gender", "tense", "voice"):
                if req not in m:
                    errors.append(f"{wid}: participle missing morph.{req}")
            if "person" in m:
                errors.append(f"{wid}: participle carries morph.person")
        elif m.get("pos") == "verb" and "case" in m:
            errors.append(f"{wid}: finite verb carries morph.case")
        plain = fold_ligatures(strip_accents(f)).lower()
        # u after q/g before a vowel is a glide, not a vowel (quia, sanguis) —
        # drop it before the vocalic-context tests.
        plain = re.sub(r"([qg])u(?=[aeiouy])", r"\1", plain)
        if plain in SPELLING_EXEMPT:
            # waive the spelling rules only; the accent check below still runs
            pass
        elif re.search(r"[aeouy]i[aeouy]", plain):
            errors.append(f"{wid}: {f!r} has i between vowels — ORTHOGRAPHY.md wants j (allowlist if genuine)")
        if plain not in SPELLING_EXEMPT and re.match(r"i[aeiouy]", plain):
            errors.append(f"{wid}: {f!r} starts i+vowel — ORTHOGRAPHY.md wants J (allowlist if genuine)")
        n, acc = syllable_count(f), has_accent(f)
        n_marks = sum(1 for ch in f if ch in ACCENTED_VOWELS)
        if n >= 3 and not acc:
            errors.append(f"{wid}: {f!r} has {n} syllables but no accent")
        if n <= 2 and acc:
            errors.append(f"{wid}: {f!r} has {n} syllables but carries an accent")
        if n_marks > 1:
            errors.append(f"{wid}: {f!r} carries {n_marks} accents")
    return errors, len(words)


def lint_gloss(doc, text_doc):
    errors = []
    lang = doc["lang"]
    words = {w["id"]: w for s in text_doc["segments"] for w in s.get("words") or []}
    seg_types = {s["id"]: s["type"] for s in text_doc["segments"]}
    gw = doc.get("words", {})
    missing = sorted(set(words) - set(gw))
    extra = sorted(set(gw) - set(words))
    if missing:
        errors.append(f"{lang}: no gloss for {missing}")
    if extra:
        errors.append(f"{lang}: gloss for unknown ids {extra}")

    banned = BANNED_TERMS.get(lang, [])

    def check_prose(where, prose):
        for pat in banned:
            # IGNORECASE: a capitalized sentence-initial variant is the same
            # banned term (proven necessary by mutation, 2026-08-03).
            if re.search(pat, prose, re.IGNORECASE):
                errors.append(f"{lang}:{where}: banned terminology/typography {pat!r} (TERMINOLOGY.md)")
        for ch, name in LAYOUT_CHARS.items():
            if ch in prose:
                errors.append(
                    f"{lang}:{where}: {name} in prose — layout belongs to the reader app"
                )

    for wid, entry in gw.items():
        if not entry.get("gloss"):
            errors.append(f"{lang}:{wid}: missing gloss")
        # function is OPTIONAL (contextual-only, SCHEMA.md 0.5.0) — omit the
        # key entirely; an empty string is an authoring error, not an omission.
        if "function" in entry and not entry["function"]:
            errors.append(f"{lang}:{wid}: empty function — omit the key instead")
        fn = entry.get("function", "")
        check_prose(wid, entry.get("gloss", "") + " " + fn)
        for ref in REF_RE.finditer(fn):
            if ref.group(1) not in words:
                errors.append(f"{lang}:{wid}: dangling cross-reference {ref.group(1)}")
        for qm in QUOTE_REF_RE.finditer(fn):
            quoted, rid = qm.groups()
            if rid in words and quoted != words[rid]["form"]:
                errors.append(
                    f"{lang}:{wid}: quoted {quoted!r} != form {words[rid]['form']!r} of {rid}"
                )
        # Reader-facing prose must be self-contained: the ONLY permitted id
        # reference is the quoted-form pattern above (the app renders it as a
        # link and hides the id). Bare ids ("Jak w004") are author shorthand
        # leaking to readers.
        remainder = QUOTE_REF_RE.sub("", fn)
        for bare in re.finditer(r"\bw\d{3}\b", remainder):
            errors.append(
                f"{lang}:{wid}: bare word-id {bare.group(0)!r} in reader-facing prose"
            )
    for sid, seg in doc.get("segments", {}).items():
        check_prose(sid, (seg.get("translation", "") or "") + " " + (seg.get("narrative", "") or ""))
        if sid not in seg_types:
            errors.append(f"{lang}: segment {sid} not in text document")
        elif "translation" in seg and seg_types[sid] != "verse":
            errors.append(f"{lang}:{sid}: translation on a non-verse segment")
        elif "narrative" in seg and seg_types[sid] != "rubric":
            errors.append(f"{lang}:{sid}: narrative on a non-rubric segment")
    return errors


def lint_parity(gloss_docs):
    errors = []
    if len(gloss_docs) < 2:
        return errors
    base = gloss_docs[0]
    base_fn = {wid for wid, e in base["words"].items() if "function" in e}
    for other in gloss_docs[1:]:
        if set(base["words"]) != set(other["words"]):
            errors.append(
                f"parity: word coverage differs {base['lang']} vs {other['lang']}: "
                f"{sorted(set(base['words']) ^ set(other['words']))}"
            )
        # A function note claims something about the Latin, which is
        # language-independent — presence must agree across languages.
        other_fn = {wid for wid, e in other["words"].items() if "function" in e}
        if base_fn != other_fn:
            errors.append(
                f"parity: function presence differs {base['lang']} vs {other['lang']}: "
                f"{sorted(base_fn ^ other_fn)}"
            )
        if set(base.get("segments", {})) != set(other.get("segments", {})):
            errors.append(f"parity: segment coverage differs {base['lang']} vs {other['lang']}")
        # The about paragraph introduces the Latin text — presence must
        # agree across languages (SCHEMA.md, since 0.8.0).
        if ("about" in base) != ("about" in other):
            errors.append(f"parity: about presence differs {base['lang']} vs {other['lang']}")
    for doc in gloss_docs:
        if "about" in doc and not str(doc["about"]).strip():
            errors.append(f"about: empty in {doc['lang']} — drop the key or write the paragraph")
    return errors

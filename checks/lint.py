"""Mechanical corpus lint: schema shape, charset, orthography (ORTHOGRAPHY.md),
accent rules, cross-references, quoted forms, terminology, layer parity."""

import json
import re
import unicodedata
from pathlib import Path

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
GLOSS_POSSESSIVES = {
    # A gloss may not render the possessive its neighbor token already
    # glosses: "discípulis suis" reads "to the disciples | His", never
    # "to His disciples | His". The word set is matched case-folded against
    # a neighbor whose whole gloss is the one possessive word.
    "en": {"my", "thy", "thine", "your", "our", "his", "her", "their", "its"},
    "pl": {
        "mój",
        "moja",
        "moje",
        "mojego",
        "mojej",
        "moich",
        "moim",
        "mego",
        "mych",
        "twój",
        "twoja",
        "twoje",
        "twojego",
        "twojej",
        "twoich",
        "twoim",
        "twego",
        "twych",
        "twym",
        "nasz",
        "nasza",
        "nasze",
        "naszego",
        "naszej",
        "naszych",
        "naszym",
        "wasz",
        "wasza",
        "wasze",
        "waszego",
        "waszej",
        "waszych",
        "ich",
        "jego",
        "jej",
        "swój",
        "swoja",
        "swoje",
        "swego",
        "swojej",
        "swoich",
        "swym",
        "swych",
    },
}

GLOSS_CONJUNCTIONS = {
    # The same fault as GLOSS_POSSESSIVES, one part of speech over: the
    # Last Gospel glossed "et veritátis" as "and truth" beside a "w186: and".
    "en": {"and", "or", "but", "nor"},
    "pl": {"i", "a", "oraz", "ani", "lecz", "ale"},
}

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
#   eia — the interjection of the Salve Regína. Its i is a glide between
#   vowels (E-ia, as normalize.py reads it), so the word has two syllables
#   and rightly carries no accent. (The spelling rule itself no longer
#   applies to it: since the orthography was reversed to i, there is
#   nothing here to catch.)
#
# Keyed on the normalized spelling (accents stripped, ligatures expanded,
# lowercased) — the same `plain` the heuristics test.
# Kept for the mechanism, now empty: since this edition prints the
# consonant as i throughout (ORTHOGRAPHY.md rule 2, reversed 2026-08-06),
# Eia and allelúia need no exemption — they were only ever exceptions to a
# j-rule that no longer exists.
SPELLING_EXEMPT: dict[str, str] = {}

# Who a narrative may be about. Naming one of these in the opening sentence
# is what lets a reader who lands mid-book know whose actions they are
# reading — which they do constantly, since every part is its own block.
NAMED_SUBJECT = re.compile(
    r"\b(priest|celebrant|server|servers|minister|ministers|deacon|people|faithful|choir|schola|Church|congregation)\b",
    re.IGNORECASE,
)

# Who says a segment, and how loudly (SCHEMA.md, since 0.9.0). Both are
# READ from the sources, not remembered: the speaker from the witnesses'
# own markers (S. sacerdos, M. minister, V./R. versicle and response), the
# voice from the rubrics that say secreto, clara voce, elata aliquantulum
# voce. Optional while the attribution pass proceeds — a segment with no
# attribution says "not yet read", which is the honest state and the one
# the app must render as unmarked rather than guess.
SPEAKERS = {"sacerdos", "minister", "populus", "omnes", "schola"}
VOICES = {"clara", "submissa", "secreto", "cantus"}


def duplicate_keys(path: Path) -> list[str]:
    """A JSON object may legally repeat a key, and every parser silently
    keeps the last — so a file can say two things at once and pass every
    check written against the parsed value. A writer that inserted where it
    meant to replace produced exactly that here, and nothing caught it.
    Read the raw text, and refuse it."""
    seen: list[str] = []

    def hook(pairs):
        counts: dict[str, int] = {}
        for key, _ in pairs:
            counts[key] = counts.get(key, 0) + 1
        for key, n in counts.items():
            if n > 1:
                seen.append(f"{path.name}: key {key!r} appears {n} times in one object")
        return dict(pairs)

    json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=hook)
    return seen


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


# A note cites its tokens as FORM at wNNN — the caps form and the id have to
# name the same word. They drift: word ids are renumbered whenever a text is
# re-segmented, and the prose keeps the old numbers, so by the time this was
# written 32 references pointed at other words and two at tokens that no
# longer existed. Multi-word citations name the last word (SANCTA SANCTÓRUM
# at w011-w012), and one form may carry several ids (ÓBTULI at w017 and w027).
NOTE_REF = re.compile(r"\b([^\Wa-z\d_]{3,}(?:[^\Wa-z\d_]|-)*)( at w\d+(?:[- ]?(?:and )?w\d+)*)")


def plain(word):
    """The comparison spelling: accents off, ligatures expanded, lowercase."""
    return fold_ligatures(strip_accents(word)).lower()


def lint_rubrics(doc):
    """Rubric Latin obeys the same orthography as the prayers it stands
    between. It is not tokenized, so the word-level spelling rule never sees
    it — and 43 j's sat in the rubrics for a day after the texts were
    reversed, iunctis manibus printed junctis two lines above Iesu."""
    errors = []
    for seg in doc["segments"]:
        if seg.get("type") != "rubric":
            continue
        for word in re.findall(r"[^\W\d_]+", seg.get("text") or ""):
            if "j" in word.lower():
                errors.append(
                    f"{seg['id']}: rubric spells {word!r} with j — ORTHOGRAPHY.md prints i"
                )
    return errors


def lint_notes(doc):
    """Every token a note cites exists and holds the form the note names.
    The comparison ignores accents and ligatures but NOT i against j, so a
    note left in the old orthography is caught too."""
    errors = []
    forms = {w["id"]: w["form"] for s in doc["segments"] for w in s.get("words") or []}
    for m in NOTE_REF.finditer(doc.get("notes") or ""):
        cited, tail = m.groups()
        ids = re.findall(r"w\d+", tail)
        missing = [i for i in ids if i not in forms]
        if missing:
            errors.append(f"notes: {cited} at {', '.join(missing)} — no such token")
            continue
        named = [plain(forms[i]) for i in ids]
        if plain(cited) not in named:
            errors.append(
                f"notes: {cited} at {', '.join(ids)} — those tokens are "
                f"{', '.join(forms[i] for i in ids)}"
            )
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
            errors.append(
                f"{wid}: lemma {lemma!r} capitalized but not in proper-name list (SCHEMA.md)"
            )
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
        if "j" in plain:
            errors.append(
                f"{wid}: {f!r} spells the consonant with j — ORTHOGRAPHY.md prints i, "
                "as the typical edition and the Pallottinum Ordo do"
            )
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

    poss = GLOSS_POSSESSIVES.get(lang, set())
    conj = GLOSS_CONJUNCTIONS.get(lang, set())
    for seg in text_doc["segments"]:
        ws = seg.get("words") or []
        for i, w in enumerate(ws):
            g = (gw.get(w["id"], {}).get("gloss") or "").strip()
            parts = [p.lower().rstrip(".,") for p in g.split()[:2]]
            if not parts:
                continue
            for j in (i - 1, i + 1):
                if j < 0 or j >= len(ws):
                    continue
                ng = (gw.get(ws[j]["id"], {}).get("gloss") or "").strip()
                if " " in ng or not ng:
                    continue
                key = ng.lower().rstrip(".,")
                if key in poss and key in parts and g.lower() != ng.lower():
                    errors.append(
                        f"{lang}: {w['id']} gloss {g!r} absorbs the possessive "
                        f"its neighbor {ws[j]['id']} glosses ({ng!r})"
                    )
                bare = (
                    unicodedata.normalize("NFD", w["form"])
                    .encode("ascii", "ignore")
                    .decode()
                    .lower()
                )
                # A token that FUSES the conjunction — mihíque, Patremque —
                # carries it inside itself and must gloss it: the neighbour's
                # own "and" is a second, separate conjunction (mihique ET
                # omnibus reads "both for me and for all").
                if (
                    key in conj
                    and key in parts
                    and g.lower() != ng.lower()
                    and not bare.endswith(("que", "ve"))
                ):
                    errors.append(
                        f"{lang}: {w['id']} gloss {g!r} absorbs the conjunction "
                        f"its neighbor {ws[j]['id']} glosses ({ng!r})"
                    )

    def check_narrative(where, prose):
        """A narrative sentence names its subject rather than opening with a
        pronoun. Two reasons, and the second decides it: a prayer book's
        rubrics say "the priest", not "he"; and a reader lands in the MIDDLE
        of this book constantly — every part is its own block and the Ordo
        jumps between them — so a sentence beginning "He goes on silently"
        has no antecedent anywhere in view.

        The NARRATIVE only. It was written over every prose field at first
        and caught the Last Gospel — "He was not the light, but was to bear
        witness of the light" — which is the Gospel talking about John, in a
        translation, where the pronoun is the text's own. A rule about our
        register has no business inside a rendering of someone else's words.

        English only: Polish carries the person in the verb and never states
        a subject pronoun here at all.
        """
        if lang != "en":
            return
        # The FIRST sentence has to name whoever it is about. Opening with
        # the pronoun is the obvious case ("He goes on silently"), but a
        # participle in front of it hides the same fault — "Bowing a little,
        # he takes both halves of the Host" tells a reader who has just
        # landed on this block exactly nothing about who is bowing.
        sentences = re.split(r"(?<=[.;])\s+", prose)
        first = sentences[0] if sentences else ""
        if re.search(r"\b(he|his|him)\b", first, re.IGNORECASE) and not NAMED_SUBJECT.search(first):
            errors.append(
                f"{lang}:{where}: narrative opens on a pronoun with no named subject "
                f"({first[:48]!r}) — name the priest"
            )
        for sentence in sentences:
            if re.match(r"^\W*(He|His)\b", sentence) or re.match(
                r"^\W*(Then|Now|Meanwhile|Here|Next|Again|Afterwards?)\b[^.]{0,24}\bhe\b",
                sentence,
            ):
                errors.append(
                    f"{lang}:{where}: narrative opens with a pronoun "
                    f"({sentence[:40]!r}) — name the priest"
                )

    def check_prose(where, prose):
        for pat in banned:
            # IGNORECASE: a capitalized sentence-initial variant is the same
            # banned term (proven necessary by mutation, 2026-08-03).
            if re.search(pat, prose, re.IGNORECASE):
                errors.append(
                    f"{lang}:{where}: banned terminology/typography {pat!r} (TERMINOLOGY.md)"
                )
        for ch, name in LAYOUT_CHARS.items():
            if ch in prose:
                errors.append(f"{lang}:{where}: {name} in prose — layout belongs to the reader app")

    # The introduction is the MOST read prose in the layer — it is what the
    # app puts behind the "about this prayer" button — and it was the one
    # piece never checked: `about` arrived in 0.8.0 and nothing added it
    # here, so a banned term walked into it while every gloss beside it was
    # being refused for the same word.
    check_prose("about", doc.get("about", "") or "")

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
            errors.append(f"{lang}:{wid}: bare word-id {bare.group(0)!r} in reader-facing prose")
    for sid, seg in doc.get("segments", {}).items():
        check_prose(
            sid, (seg.get("translation", "") or "") + " " + (seg.get("narrative", "") or "")
        )
        check_narrative(sid, seg.get("narrative", "") or "")
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

"""Mechanical corpus lint: schema shape, charset, orthography (ORTHOGRAPHY.md),
accent rules, cross-references, quoted forms, terminology, layer parity."""

import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

from .normalize import (
    ACCENTED_VOWELS,
    accented_syllable,
    fold_ligatures,
    has_accent,
    strip_accents,
    syllable_count,
)

MORPH_ENUMS = {
    "pos": {"verb", "noun", "adj", "pron", "adv", "conj", "prep", "intj"},
    "case": {"nom", "gen", "dat", "acc", "abl", "voc"},
    "number": {"sg", "pl"},
    "gender": {"m", "f", "n"},
    "tense": {"pres", "impf", "fut", "perf", "plup", "futperf"},
    # "ger" is the GERUND, a verbal noun: it takes a case and no person.
    # It entered with the Advent II epistle, at *in credéndo* — the first
    # one in the corpus, and the enum this schema had not yet needed.
    "mood": {"ind", "subj", "imp", "inf", "part", "ger"},
    "voice": {"act", "pass", "dep"},
    "degree": {"comp", "sup"},
    "governs": {"acc", "abl"},
}

FORM_RE = re.compile(r"^[A-Za-zÁÉÍÓÚÝáéíóúýÆæŒœǼǽËë\u0301]+$")
REF_RE = re.compile(r"\((w\d{3,})\)")
QUOTE_REF_RE = re.compile(r"[„“]([^”“„]+)”\s*\((w\d{3,})\)")

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
        r"\brozkaźnik\w*",  # -> tryb rozkazujący (TERMINOLOGY.md)
    ],
    "en": ["„"],  # Polish low-opening quote in English text
}

# A word gloss is already this edition's contextual reading. An explanation
# may explain that the bare Latin form admits another parse, but it may not
# then claim that the edition leaves the choice unresolved.
UNRESOLVED_READER_CLAIMS = {
    "pl": [
        r"wydanie nie rozstrzyga",
        r"(?:samo |to )?zdanie nie rozstrzyga",
        r"czasu i trybu (?:tu )?nie podano",
    ],
    "en": [
        r"this edition does not resolve",
        r"the sentence does not (?:resolve|determine)",
        r"tense and mood are left unclaimed",
    ],
}

# These openings make grammar itself the message even though the form row
# already renders the same structured facts.  A case or agreement term may
# still appear later when it unlocks a genuine ambiguity or translation
# difficulty; what is rejected is the old stock-note template.
REDUNDANT_EXPLANATION_OPENINGS = {
    "pl": [
        r"^(?:wołacz|mianownik|biernik|celownik) (?:jest|nazywa|pełni)",
        r"^dopełniacz liczby ",
        r"^(?:przymiotnik|imiesłów) zgadza się ",
        r"^tryb rozkazujący\.?$",
    ],
    "en": [
        r"^(?:the )?(?:vocative|nominative|accusative|dative) (?:is|names|serves)",
        r"^the genitive plural ",
        r"^(?:the )?(?:adjective|participle) agrees with ",
        r"^imperative mood\.?$",
    ],
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
    "Aaron", "Abba", "Abias", "Abiud", "Achaia", "Achaz", "Achim",
    "Aegyptus", "Alphaeus", "Aminadab", "Amon", "Anna", "Asa", "Aser",
    "Asia", "Azor", "Babylon", "Babylonius", "Bar", "Beniamin", "Booz",
    "Caesarea", "Capharnaum", "Cephas", "Chananaeus", "Cleophas", "Daniel",
    "David", "Decapolis", "Eleazar", "Eliacim", "Elisabeth", "Eliud", "Esron",
    "Evodia", "Ezechias", "Gad", "Genesareth", "Herodianus", "Hus", "Iechonias",
    "Ieremias", "Iericho", "Ioachim", "Ioatham", "Iob", "Iona", "Ioram",
    "Iosaphat", "Iosias", "Iscariotes", "Issachar", "Iuda", "Iudas", "Libanus",
    "Lucas", "Macedonia", "Magdalene", "Manasses", "Mathan", "Moyses", "Naasson",
    "Naim", "Nazareth", "Nephthali", "Obed", "Ophir", "Ozias", "Phares", "Rahab",
    "Roboam", "Ruben", "Ruth", "Sadoc", "Salathiel", "Salmon", "Salome", "Salomon",
    "Samaria", "Samaritanus", "Satan", "Sextus", "Sibylla", "Sidon", "Simeon",
    "Syntyche", "Tartarus", "Thamar", "Titus", "Tyrus", "Urias", "Zabulon",
    "Zachaeus", "Zara", "Zebedaeus", "Zorobabel",
    "Abilina",
    "Annas",
    "Caesar",
    "Caiphas",
    "Galilaea",
    "Herodes",
    "Ituraea",
    "Iudaea",
    "Lysanias",
    "Philippus",
    "Pilatus",
    "Pontius",
    "Tiberius",
    "Trachonitis",
    "Zacharias",
    "Bethania",
    "Emmanuel",
    "Elias",
    "Ierosolyma",
    "Iordanes",
    "Iudaeus",
    "Iacob",
    "Iesse",
    "Isaias",
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
    "Gabriel",
    "Iacobus",
    "Iesus",
    "Ierusalem",
    "Ignatius",
    "Isaac",
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
    "Parasceve",
    "Perpetua",
    "Petrus",
    "Polonia",
    "Simon",
    "Sion",
    "Stephanus",
    "Thaddaeus",
    "Thomas",
    "Eva",
    "Xystus",
    "Israel",
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
SPELLING_EXEMPT: dict[str, str] = {
    # The Hebrew name is conventionally written with the diaeresis that
    # marks the hiatus, but without a Latin stress acute (ORTHOGRAPHY.md 7).
    "israel": "indeclinable Hebrew name; diaeresis marks the hiatus",
    # The typical edition prints iísdem in the Preface of the Apostles
    # (p. 299). The two adjacent i's are a hiatus, so the apparent two-vowel
    # spelling has three syllables (i-ís-dem) and correctly marks the penult.
    "iisdem": "hiatus printed in MR 1962 p. 299: i-ís-dem",
}

# Forms exempt from the STRESS-POSITION rule — an accent standing further back
# than the antepenult, which Latin does not do. Keyed on the accented spelling
# lowercased, because the exemption is about where the mark sits and a key
# without it could not tell the two readings apart. Each entry says why, and
# an entry here is a question left open, not one answered: the rule it suspends
# is an invariant of the language.
#
# EMPTY, and that is the record: the one candidate this table ever held,
# indúimini (Advent I epistle, w054), turned out on inspection of the 600 dpi
# page image to be a transcription error — the typical edition prints
# induímini, the mark on the antepenult, exactly where the invariant says it
# must be. The transcription, the apparatus and the text were all corrected
# at the root (2026-08-19). A form that genuinely prints against this rule
# belongs here with its page named, and until one does, nothing is exempt.
STRESS_EXEMPT: dict[str, str] = {}

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
SPEAKERS = {"sacerdos", "ductor", "minister", "populus", "omnes", "schola"}
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
    errors, attributed, verses, verse_numbers = [], 0, 0, set()
    for seg in doc["segments"]:
        speaker, voice = seg.get("speaker"), seg.get("voice")
        if seg.get("type") == "verse":
            verses += 1
            if speaker:
                attributed += 1
            number = seg.get("verse")
            if number is not None:
                if not isinstance(number, int) or isinstance(number, bool) or number < 1:
                    errors.append(f"{seg['id']}: verse must be a positive integer")
                elif number in verse_numbers:
                    errors.append(f"{seg['id']}: duplicate verse number {number}")
                else:
                    verse_numbers.add(number)
        elif speaker or voice or "verse" in seg:
            errors.append(
                f"{seg['id']}: only a verse segment has a speaker, voice, or verse number — "
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
# The voices that may confirm a claim: the two analyzers, a treebank, a named
# expert, and this edition itself (SCHEMA.md). This set was written down when
# provenance was flipped and then read by nothing — the shape test below was
# the whole gate, so `morfeusz-for-latin` was a well-formed source name and
# passed locally, contradicted only by CI's network-clone agreement run
# (census, 2026-08-19). A vocabulary nobody consults is a comment.
KNOWN_SOURCES = frozenset(("whitakers", "collatinus", "editorial", "treebank", "expert"))
# Witness sigla are sources too, for the rubric and text-level claims a
# dictionary cannot speak to. These are the ones the corpus uses; a new witness
# cited as a source is one line here, like every other ruling in this package.
WITNESS_SOURCES = frozenset(("do", "mr", "mr-ritus-servandus"))
SOURCES = KNOWN_SOURCES | WITNESS_SOURCES
SOURCE_RE = re.compile(r"^[a-z][a-z0-9-]*$")

CITATION_KEYS = {"title", "locator", "url"}


def lint_citations(citations, where):
    """Reader-facing sources support one prose unit, never a detached
    bibliography. Every note names the work and an exact locator; a link is
    optional, but when present it must be a public HTTPS address."""
    if not isinstance(citations, list) or not citations:
        return [f"{where}: citations must be a nonempty list"]
    errors = []
    seen = set()
    for index, citation in enumerate(citations, 1):
        at = f"{where}:citation-{index}"
        if not isinstance(citation, dict):
            errors.append(f"{at}: citation must be an object")
            continue
        unknown = set(citation) - CITATION_KEYS
        if unknown:
            errors.append(f"{at}: unknown citation keys {sorted(unknown)}")
        for key in ("title", "locator"):
            if not isinstance(citation.get(key), str) or not citation[key].strip():
                errors.append(f"{at}: {key} must be a nonempty string")
        url = citation.get("url")
        if url is not None:
            parsed = urlparse(url) if isinstance(url, str) else None
            if not parsed or parsed.scheme != "https" or not parsed.netloc:
                errors.append(f"{at}: url must be an absolute HTTPS address")
        signature = json.dumps(citation, sort_keys=True, ensure_ascii=False)
        if signature in seen:
            errors.append(f"{at}: duplicate citation")
        seen.add(signature)
    return errors


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
                elif s not in SOURCES:
                    errors.append(
                        f"{where}: analysis source {s!r} is not a voice this edition "
                        f"knows ({', '.join(sorted(SOURCES))})"
                    )
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
# longer existed. Multi-word citations name the whole span (SANCTA SANCTÓRUM
# at w011-w012), and one form may carry several ids (ÓBTULI at w017 and w027).
UPPER_FORM = r"[A-ZÁÉÍÓÚÝÆŒǼË]+(?:-[A-ZÁÉÍÓÚÝÆŒǼË]+)?"
NOTE_REF = re.compile(
    rf"(?<!\w)({UPPER_FORM}(?:\s+(?:and\s+)?{UPPER_FORM}){{0,5}})"
    r"( at w\d+(?:[- ]?(?:and )?w\d+)*)"
)


def plain(word):
    """The comparison spelling: accents off, ligatures expanded, lowercase."""
    return fold_ligatures(strip_accents(word)).lower()


# The fields a reader meets on the page. Emptiness in one of them is a hole in
# the book: an empty gloss has been refused since the beginning, and an emptied
# `translation` passed every gate the corpus had (census, 2026-08-19).
READER_FACING = frozenset(
    ("translation", "gloss", "narrative", "about", "explanation", "title", "senses")
)


def _named_field(path: list[str]) -> str:
    """The field a path names, past the language key and the list index that
    hang off it: `s01.translation.pl` is a translation, `senses.[0]` a sense."""
    for step in reversed(path):
        if not step.startswith("[") and step not in ("pl", "en"):
            return step
    return ""


def lint_nulls(doc: dict, subject: str | None = None) -> list[str]:
    """A key whose value is null says nothing and hides that it says nothing —
    and so does one holding an empty string where a reader expects prose.

    Two rubric segments carried `"narrative": null` — written by a build script
    that copied a shape it did not need — and every check read straight past
    them, because a check that asks "is there a narrative" gets an answer either
    way. The merge round-trip found them, which is a fair advertisement for
    reading a document as a whole.

    It then read ONE LEVEL, over a document that has since become nested by
    language, which the census of 2026-08-19 took apart three ways:
    `translation.pl = null` passed green, `gloss.pl = null` came back as a
    TypeError from a check downstream rather than as a diagnosis, and
    `translation: ""` passed while the empty gloss beside it was refused. So
    the walk is now the whole document to any depth, and the emptiness rule
    stands beside it over the fields a reader is shown.

    Reads the document AS STORED, both gloss layers included: the split hands
    each check one language, and a null belongs to neither. `subject` names a
    document that has no id of its own — the lexicon files, whose `senses` and
    `note` are read by a reader like any other prose, and whose null note
    reached checks/lexicon.py as a TypeError for the same reason a null gloss
    reached this file as one.
    """
    errors = []
    tid = subject or doc.get("id", "?")

    def address(path: list[str]) -> str:
        return ".".join(path)

    def walk(node: object, path: list[str]) -> None:
        if node is None:
            errors.append(
                f"{tid}:{address(path)}: is null — a key that carries nothing is "
                f"removed, not left for a reader to interpret"
            )
        elif isinstance(node, dict):
            for key, value in node.items():
                walk(value, [*path, str(key)])
        elif isinstance(node, list):
            for index, item in enumerate(node):
                step = item["id"] if isinstance(item, dict) and "id" in item else f"[{index}]"
                walk(item, [*path, str(step)])
        elif isinstance(node, str) and not node.strip():
            field = _named_field(path)
            if field in READER_FACING:
                errors.append(
                    f"{tid}:{address(path)}: {field} is empty — a reader is shown this, "
                    f"and an unwritten one is left out rather than emptied"
                )

    for key, value in doc.items():
        walk(value, [str(key)])
    return errors


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
    word_default = doc.get("analysis_defaults_words") or doc.get("analysis_defaults", {})
    analyses = [
        w.get("analysis", word_default)
        for segment in doc["segments"]
        for w in segment.get("words") or []
    ]
    notes = doc.get("notes") or ""
    if re.search(r"\bmedium confidence\b", notes, re.IGNORECASE) and not any(
        analysis.get("confidence") == "medium" for analysis in analyses
    ):
        errors.append("notes: claims medium confidence but no word has that confidence")
    if re.search(
        r"\b(?:disputed review|marks? (?:the )?token disputed)\b", notes, re.IGNORECASE
    ) and not any(analysis.get("review") == "disputed" for analysis in analyses):
        errors.append("notes: claims a disputed token but no word is marked disputed")
    for m in NOTE_REF.finditer(notes):
        cited, tail = m.groups()
        endpoints = re.findall(r"w\d+", tail)
        if "-" in tail and len(endpoints) == 2:
            # A RANGE IS A STRETCH OF THE TEXT, not a stretch of the number
            # line. This counted from w005 to w008 arithmetically, which was
            # the same thing only for as long as ids happened to be
            # contiguous. They are minted now (SCHEMA.md), so a word inserted
            # inside a range takes the next free number and sits between its
            # neighbours — and arithmetic would then walk straight past it and
            # report four ids that do not exist. The array knows the order.
            order = [w["id"] for sg in doc["segments"] for w in sg.get("words") or []]
            first, last = endpoints
            if first in order and last in order and order.index(first) <= order.index(last):
                ids = order[order.index(first) : order.index(last) + 1]
            else:
                ids = endpoints
        else:
            ids = endpoints
        missing = [i for i in ids if i not in forms]
        if missing:
            errors.append(f"notes: {cited} at {', '.join(missing)} — no such token")
            continue
        cited_words = [plain(word) for word in cited.split() if word != "and"]
        named = [plain(forms[i]) for i in ids]
        matches = cited_words == named or (
            len(cited_words) == 1 and all(n == cited_words[0] for n in named)
        )
        if not ids or not matches:
            errors.append(
                f"notes: {cited} at {', '.join(ids)} — those tokens are "
                f"{', '.join(forms[i] for i in ids)}"
            )
    return errors


def stress_position(where: str, form: str) -> list[str]:
    """Latin stress falls on the penult or the antepenult, never before it.

    The one accent rule this edition can hold without knowing a single vowel
    quantity, and the census of 2026-08-19 found nothing holding it: the
    lexicon carried *pérhibeo, perhibére, pérhibui, pérhibitum* — the mark
    four syllables from the end, three times in one entry — for weeks, and
    every gate read past it, because the rules in force ask only whether an
    accent is present and whether there is exactly one.

    Used by the token layer (lint_text) and by the dictionary heads
    (checks/lexicon.py) against the same syllabifier, so that a head and the
    forms under it cannot be judged by two different counts.
    """
    if unicodedata.normalize("NFC", form).lower() in STRESS_EXEMPT:
        return []
    from_end = accented_syllable(form)
    if from_end is None or from_end <= 2:
        return []
    return [
        f"{where} accents the syllable {from_end + 1} from the end — Latin stress "
        f"reaches the antepenult and no further"
    ]


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
        elif m.get("pos") == "verb" and m.get("mood") == "ger":
            # A GERUND is a verbal noun: it takes a case, never a person, and
            # is neuter singular by nature. Checked apart from the finite verb
            # below, which forbids the very case a gerund must have.
            for req in ("case", "tense", "voice"):
                if req not in m:
                    errors.append(f"{wid}: gerund missing morph.{req}")
            if "person" in m:
                errors.append(f"{wid}: gerund carries morph.person")
        elif m.get("pos") == "verb":
            if "case" in m:
                errors.append(f"{wid}: finite verb carries morph.case")
            if "mood" not in m:
                errors.append(
                    f"{wid}: finite verb missing morph.mood — the contextual parse must choose"
                )
            # Eléison is a Greek aorist imperative printed in Latin letters;
            # the Latin tense enum deliberately cannot represent its aorist.
            elif "tense" not in m and w.get("lemma") != "eleison":
                errors.append(
                    f"{wid}: finite verb missing morph.tense — the contextual parse must choose"
                )
        plain = fold_ligatures(strip_accents(f)).lower()
        # u after q/g before a vowel is a glide, not a vowel (quia, sanguis) —
        # drop it before the vocalic-context tests.
        plain = re.sub(r"([qg])u(?=[aeiouy])", r"\1", plain)
        if plain in SPELLING_EXEMPT:
            continue
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
        errors += stress_position(f"{wid}: {f!r}", f)
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
        for pat in UNRESOLVED_READER_CLAIMS.get(lang, []):
            if re.search(pat, prose, re.IGNORECASE):
                errors.append(
                    f"{lang}:{where}: reader note leaves the edition unresolved — "
                    "state the contextual reading adopted by the gloss"
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
    if "about_citations" in doc:
        if not doc.get("about"):
            errors.append(f"{lang}:about: citations without an about paragraph")
        errors += lint_citations(doc["about_citations"], f"{lang}:about")

    for wid, entry in gw.items():
        if not entry.get("gloss"):
            errors.append(f"{lang}:{wid}: missing gloss")
        # explanation is OPTIONAL — omit the
        # key entirely; an empty string is an authoring error, not an omission.
        if "explanation" in entry and not entry["explanation"]:
            errors.append(f"{lang}:{wid}: empty explanation — omit the key instead")
        if "explanation_citations" in entry:
            if not entry.get("explanation"):
                errors.append(f"{lang}:{wid}: citations without an explanation")
            errors += lint_citations(entry["explanation_citations"], f"{lang}:{wid}")
        explanation = entry.get("explanation", "")
        check_prose(wid, entry.get("gloss", "") + " " + explanation)
        for pattern in REDUNDANT_EXPLANATION_OPENINGS.get(lang, []):
            if re.search(pattern, explanation, re.IGNORECASE):
                errors.append(
                    f"{lang}:{wid}: explanation merely restates structured grammar "
                    f"({pattern!r}) — omit it or explain why the distinction matters"
                )
        for ref in REF_RE.finditer(explanation):
            if ref.group(1) not in words:
                errors.append(f"{lang}:{wid}: dangling cross-reference {ref.group(1)}")
        for qm in QUOTE_REF_RE.finditer(explanation):
            quoted, rid = qm.groups()
            if rid in words and quoted != words[rid]["form"]:
                errors.append(
                    f"{lang}:{wid}: quoted {quoted!r} != form {words[rid]['form']!r} of {rid}"
                )
        # Reader-facing prose must be self-contained: the ONLY permitted id
        # reference is the quoted-form pattern above (the app renders it as a
        # link and hides the id). Bare ids ("Jak w004") are author shorthand
        # leaking to readers.
        remainder = QUOTE_REF_RE.sub("", explanation)
        for bare in re.finditer(r"\bw\d{3,}\b", remainder):
            errors.append(f"{lang}:{wid}: bare word-id {bare.group(0)!r} in reader-facing prose")
    for sid, seg in doc.get("segments", {}).items():
        check_prose(
            sid, (seg.get("translation", "") or "") + " " + (seg.get("narrative", "") or "")
        )
        check_narrative(sid, seg.get("narrative", "") or "")
        if "narrative_citations" in seg:
            if not seg.get("narrative"):
                errors.append(f"{lang}:{sid}: citations without a narrative")
            errors += lint_citations(seg["narrative_citations"], f"{lang}:{sid}")
        if "translation_citations" in seg:
            if not seg.get("translation"):
                errors.append(f"{lang}:{sid}: citations without a translation")
            errors += lint_citations(seg["translation_citations"], f"{lang}:{sid}:translation")
        if sid not in seg_types:
            errors.append(f"{lang}: segment {sid} not in text document")
        elif "translation" in seg and seg_types[sid] != "verse":
            errors.append(f"{lang}:{sid}: translation on a non-verse segment")
        elif "narrative" in seg and seg_types[sid] != "rubric":
            errors.append(f"{lang}:{sid}: narrative on a non-rubric segment")
    return errors

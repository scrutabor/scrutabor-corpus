"""Propose who says each verse segment, and how loudly, FROM THE SOURCES.

Two facts a missal makes visible on the page and this corpus could not
say: who is speaking, and whether it is said aloud. Both are recoverable
rather than remembered.

WHO comes from the witnesses' own markers. The Divinum Officium files
print S. (sacerdos), M. (minister), V. and R. (a versicle and its
response, the priest's voice and the answering one), O. (omnes); the
transcriptions strip them, and every witness header says so. Each witness
header also records the lines it was taken from, so a text's segments are
matched against exactly those lines and not against the whole book.

HOW LOUDLY comes from the rubrics the corpus already carries. A rubric
saying *secreto* governs what follows until another rubric lifts it;
*clara voce* and *intellegibili voce* restore the ordinary voice; *elata
aliquantulum voce* is the raised-but-not-full voice of Domine non sum
dignus. A text whose rubrics say nothing is left unattributed rather than
assumed — silence here means "not read yet", not "spoken aloud".

Run it to see the proposal, or with --write to apply it:

    python3 -m checks.attribute            # print
    python3 -m checks.attribute --write    # apply

It never guesses: a segment it cannot source stays empty, and the check
in run_checks reports the coverage so the gap is visible.

And it checks its own footing. A witness header's line range is written by
hand, and a stale one does not fail loudly — the markers simply run out,
and the rule that supplies the celebrant for text the Ordo leaves unmarked
supplies him for a line the Ordo marks M. Every text is therefore tested
against its own declared range before anything is proposed for it: one
that no longer holds its own words is REPORTED as UNSOURCED, keeps
whatever it already has, and is never written. See span_covers.
"""

import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

CORPUS = Path(__file__).resolve().parent.parent

# The archived sources mark the speaker: S. sacerdos, M. minister, V. and
# R. a versicle and its response, O. omnes. The markers come in both cases
# — the Ordo prints the priest's own Confiteor as a lowercase "v." — and
# lowercase is by far the commonest, so reading only capitals threw away
# 140 marked lines and left the most attributable text in the book blank.
MARKERS = {"S": "sacerdos", "M": "minister", "V": "sacerdos", "R": "minister", "O": "omnes"}

# Outside the Mass only "all" means anything. V. and R. mark priest and
# answer INSIDE the rite; in a prayer book they are the shape of a
# versicle, and S. and M. name officers a devotional prayer does not have
# — the Gloria Patri said on its own has no server saying its second half.
# What a prayer book can tell us is that a prayer is said together.
SPEAKER_MARKERS_ONLY = {"O"}

# Rubric phrases that set the voice, longest first so that "elata
# aliquantulum voce" is not read as the plain "voce".
VOICE_RUBRICS = [
    ("elata aliquantulum voce", "clara"),
    ("intellegibili voce", "clara"),
    ("intelligibili voce", "clara"),
    ("clara voce", "clara"),
    ("secreto", "secreto"),
    ("secrete", "secreto"),
]


# ---------------------------------------------------------------------------
# How loudly, from the rite's own law.
#
# Rubricae generales Missalis romani IX, n. 511 (transcribed in
# witnesses/raw/mr-rubricae-generales-ix.txt) lists what is said CLARA VOCE
# at low Mass and closes: "Cetera dicuntur secreto." So the list below is
# the exceptions, and the closing sentence supplies everything else — which
# is why a text absent from this table is secreto rather than unknown.
#
# This is what the rubrics inside our own texts could not give us: the
# Canon's silence is established once, in the law, and never repeated on
# the page.
#
# n. 512 defines the terms: what is said secreto he pronounces "ut ipsemet
# se audiat, et a circumstantibus non audiatur" — audible to himself, not
# to the bystanders — and its own use of submissa names the failure mode of
# clara voce: "neque tam submissa, ut a circumstantibus audiri non possit."
# So submissa in this table means a genuinely lowered voice (the Orate
# fratres Amen), never the rubrics' elata aliquantulum voce, which is a
# manner of clara: those words stand on the 511 list precisely so that the
# people catch them, and the manner lives in the rubric text on the page.
CLARA = "clara"
SECRETO = "secreto"
SUBMISSA = "submissa"

VOICE_RULINGS: dict[str, tuple[str, str]] = {
    # 511 a — the prayers at the foot of the altar, up to Oremus inclusive
    "ordinarium.introibo": (CLARA, "RG 511 a"),
    "ordinarium.iudica-me": (CLARA, "RG 511 a"),
    "ordinarium.adiutorium": (CLARA, 'RG 511 a — "ea quae sequuntur usque ad Oremus"'),
    "ordinarium.confiteor": (CLARA, "RG 511 a — confessio"),
    "ordinarium.misereatur": (CLARA, "RG 511 a"),
    "ordinarium.confiteor-sacerdotis": (CLARA, "RG 511 a — confessio"),
    "ordinarium.misereatur-tui": (CLARA, "RG 511 a"),
    "ordinarium.deus-tu-conversus": (CLARA, "RG 511 a"),
    # 511 a names two prayers as secret inside that same passage
    "ordinarium.aufer-a-nobis": (
        SECRETO,
        'RG 511 a — "orationes vero Aufer a nobis et Oramus te dicuntur '
        'secreto"; the same sentence puts the Oremus itself in the clara '
        "block (s02)",
    ),
    # 511 b, c, f, h — the sung ordinary and the preface
    "ordinarium.kyrie": (CLARA, "RG 511 b"),
    "ordinarium.gloria": (CLARA, "RG 511 c"),
    "ordinarium.credo": (CLARA, "RG 511 f — symbolum"),
    "ordinarium.praefatio-dialogus": (CLARA, "RG 511 h"),
    "ordinarium.praefatio-communis": (CLARA, "RG 511 h"),
    "ordinarium.sanctus": (CLARA, "RG 511 h"),
    # 511 i — from the Pater noster to the communion of the faithful
    "ordinarium.pater-noster": (CLARA, "RG 511 i — oratio dominica cum sua praefatione"),
    "ordinarium.pax-domini": (CLARA, "RG 511 i"),
    "ordinarium.agnus-dei": (CLARA, "RG 511 i"),
    "ordinarium.ecce-agnus-dei": (CLARA, "RG 511 i — formulae ad Communionem fidelium"),
    # 511 l — the dismissal, the blessing, the last gospel
    "ordinarium.ite-missa-est": (CLARA, "RG 511 l"),
    "ordinarium.benedictio": (CLARA, "RG 511 l"),
    "ordinarium.evangelium-ultimum": (CLARA, "RG 511 l"),
    # Cetera dicuntur secreto — the offertory, the whole Canon, the prayers
    # before and after communion, the Placeat
    "ordinarium.suscipe-sancte-pater": (SECRETO, "RG 511 — cetera"),
    "ordinarium.deus-qui-humanae": (SECRETO, "RG 511 — cetera"),
    "ordinarium.offerimus-tibi": (SECRETO, "RG 511 — cetera"),
    "ordinarium.in-spiritu-humilitatis": (SECRETO, "RG 511 — cetera"),
    "ordinarium.lavabo": (SECRETO, "RG 511 — cetera"),
    "ordinarium.suscipe-sancta-trinitas": (SECRETO, "RG 511 — cetera"),
    "ordinarium.te-igitur": (SECRETO, "RG 511 — Canon Missae secreto (cetera)"),
    "ordinarium.memento-vivorum": (SECRETO, "RG 511 — Canon Missae secreto (cetera)"),
    "ordinarium.communicantes": (SECRETO, "RG 511 — Canon Missae secreto (cetera)"),
    "ordinarium.hanc-igitur": (SECRETO, "RG 511 — Canon Missae secreto (cetera)"),
    "ordinarium.quam-oblationem": (SECRETO, "RG 511 — Canon Missae secreto (cetera)"),
    "ordinarium.qui-pridie": (SECRETO, "RG 511 — Canon Missae secreto (cetera)"),
    "ordinarium.simili-modo": (SECRETO, "RG 511 — Canon Missae secreto (cetera)"),
    "ordinarium.unde-et-memores": (SECRETO, "RG 511 — Canon Missae secreto (cetera)"),
    "ordinarium.supra-quae": (SECRETO, "RG 511 — Canon Missae secreto (cetera)"),
    "ordinarium.supplices-te-rogamus": (SECRETO, "RG 511 — Canon Missae secreto (cetera)"),
    "ordinarium.memento-defunctorum": (SECRETO, "RG 511 — Canon Missae secreto (cetera)"),
    "ordinarium.nobis-quoque": (SECRETO, "RG 511 — cetera; 511 i excepts the opening words (s02)"),
    "ordinarium.per-quem-haec-omnia": (SECRETO, "RG 511 — Canon Missae secreto (cetera)"),
    "ordinarium.per-ipsum": (SECRETO, "RG 511 — Canon Missae secreto (cetera)"),
    "ordinarium.libera-nos": (SECRETO, "RG 511 — cetera"),
    "ordinarium.haec-commixtio": (SECRETO, "RG 511 — cetera"),
    "ordinarium.qui-dixisti": (SECRETO, "RG 511 — cetera"),
    "ordinarium.fili-dei-vivi": (SECRETO, "RG 511 — cetera"),
    "ordinarium.perceptio-corporis": (SECRETO, "RG 511 — cetera"),
    "ordinarium.panem-caelestem": (SECRETO, "RG 511 — cetera"),
    "ordinarium.quid-retribuam": (SECRETO, "RG 511 — cetera"),
    "ordinarium.quod-ore-sumpsimus": (SECRETO, "RG 511 — cetera"),
    "ordinarium.corpus-tuum": (SECRETO, "RG 511 — cetera"),
    "ordinarium.placeat-tibi": (SECRETO, "RG 511 — cetera"),
    # The Proper of the pilot formulary. RG 511 names the chants and lessons
    # among the audible parts, while its closing rule governs the Secret.
    "proprium.dominica-i-adventus-introitus": (CLARA, "RG 511 b"),
    "proprium.dominica-i-adventus-collecta": (CLARA, "RG 511 d"),
    "proprium.dominica-i-adventus-epistola": (CLARA, "RG 511 e"),
    "proprium.dominica-i-adventus-graduale": (CLARA, "RG 511 e"),
    "proprium.dominica-i-adventus-alleluia": (CLARA, "RG 511 e"),
    "proprium.dominica-i-adventus-evangelium": (CLARA, "RG 511 e"),
    "proprium.dominica-i-adventus-offertorium": (CLARA, "RG 511 g"),
    "proprium.dominica-i-adventus-secreta": (SECRETO, "RG 511 — cetera"),
    "proprium.dominica-i-adventus-communio": (CLARA, "RG 511 i"),
    "proprium.dominica-i-adventus-postcommunio": (CLARA, "RG 511 i"),
}

# RG 511 governs every Proper by its liturgical genus, not only the first
# formulary entered into the corpus. The base delivery is the low Mass; the
# sung-form exception belongs to the independent, derived delivery layer.
PROPER_VOICE_RULINGS: dict[str, tuple[str, str]] = {
    "introitus": (CLARA, "RG 511 b"),
    "collecta": (CLARA, "RG 511 d"),
    "epistola": (CLARA, "RG 511 e"),
    "graduale": (CLARA, "RG 511 e"),
    "alleluia": (CLARA, "RG 511 e"),
    "tractus": (CLARA, "RG 511 e"),
    "sequentia": (CLARA, "RG 511 e"),
    "evangelium": (CLARA, "RG 511 e"),
    "lectio": (CLARA, "RG 511 e"),
    "offertorium": (CLARA, "RG 511 g"),
    "secreta": (SECRETO, "RG 511 — cetera"),
    "communio": (CLARA, "RG 511 i"),
    "postcommunio": (CLARA, "RG 511 i"),
}


def voice_ruling(doc: dict) -> tuple[str, str] | None:
    explicit = VOICE_RULINGS.get(doc["id"])
    if explicit or doc.get("category") != "proprium":
        return explicit
    return PROPER_VOICE_RULINGS.get(doc["id"].rsplit("-", 1)[-1])


# Segments whose voice differs from their text's, and why. These are the
# places the law names a few WORDS rather than a prayer.
# Answers the matcher cannot reach, because our text and the source line
# are not identical strings: the Suscipiat carries a "(vel meis)" variant
# in the source, and the two Deo gratias and the Gospel response live in
# files the Ordo calls in by reference. Each is marked in a witness — the
# Divinum Officium Ordo with R. and M., the hand missal with its own S:
# for the server — so these are readings, not guesses.
SPEAKER_RULINGS: dict[str, tuple[str, str]] = {
    "ordinarium.orate-fratres.s04": (
        "minister",
        'do marks it M. (the line carries a "vel meis" variant)',
    ),
    "ordinarium.ite-missa-est.s06": ("minister", "do marks the answer R. Deo grátias"),
    "ordinarium.evangelium-ultimum.s06": (
        "minister",
        "handmissal-eo marks it S:, the answer to the announcement",
    ),
    "ordinarium.evangelium-ultimum.s15": ("minister", "do marks the answer R. Deo grátias"),
}

VOICE_SEGMENT_RULINGS: dict[str, tuple[str, str]] = {
    # the conclusions the people answer, inside otherwise silent prayers
    "ordinarium.aufer-a-nobis.s02": (
        CLARA,
        'RG 511 a — "usque ad Oremus inclusive"; the mid-line rubric '
        "dicit secreto governs only what follows",
    ),
    "ordinarium.libera-nos.s12": (CLARA, "RG 511 i — Per omnia saecula saeculorum"),
    "ordinarium.libera-nos.s13": (CLARA, "RG 511 i — the answering Amen"),
    "ordinarium.per-ipsum.s08": (CLARA, "RG 511 i — Per omnia saecula saeculorum"),
    "ordinarium.per-ipsum.s09": (CLARA, "RG 511 i — the answering Amen"),
    # words the people are meant to catch: RG 511 i puts them among what is
    # said aloud, and the Ritus servandus gives the manner, elata
    # aliquantulum voce — a raised voice, not a full one
    "ordinarium.nobis-quoque.s02": (
        CLARA,
        "RG 511 i — verba Nobis quoque peccatoribus; the rubric's elata "
        "aliquantulum names the manner",
    ),
    "ordinarium.panem-caelestem.s04": (
        CLARA,
        "RG 511 i — Domine, non sum dignus; the rubric's elata aliquantulum names the manner",
    ),
    "ordinarium.panem-caelestem.s07": (CLARA, "RG 511 i — the second time"),
    "ordinarium.panem-caelestem.s10": (CLARA, "RG 511 i — the third time"),
    # The Pater noster is said aloud (511 i), but the priest answers his own
    # last petition under his breath, and the page says so where the law does
    # not reach: "Sacerdos secrete dicit:". The specific rubric governs.
    "ordinarium.pater-noster.s14": (SECRETO, "the text's own rubric — Sacerdos secrete dicit"),
    # the server answers aloud, and the priest is silent under him
    # 511 g names only the words Orate, fratres; the answer's ground is
    # plainer — it exists to be heard, and the priest waits on its
    # omnipotentem before he can continue
    "ordinarium.orate-fratres.s04": (CLARA, "an answer made to be heard; the priest waits on it"),
    "ordinarium.orate-fratres.s06": (
        SUBMISSA,
        "the text's own rubric — Sacerdos submissa voce dicit",
    ),
}

# Segments the law splits but our segmentation does not, so no single value
# is true of them. Left unattributed on purpose, with the reason here.
VOICE_UNSETTLED: dict[str, str] = {
    "ordinarium.orate-fratres.s02": (
        'RG 511 g names only the words "Orate, fratres" as said aloud, and the '
        'Ritus servandus has the priest continue "ut meum ac vestrum sacrificium" '
        "secreto. This segment holds both, so neither value is true of it; "
        "splitting the segment would renumber its words."
    ),
    # This dialogue exists only when the solemn kiss of peace is given. The
    # low-Mass list in RG 511 therefore cannot make it part of that prayer's
    # otherwise secret voice, and neither of the two witnesses names a volume.
    "ordinarium.qui-dixisti.s08": "solemn-only dialogue; no source names the voice",
    "ordinarium.qui-dixisti.s09": "solemn-only dialogue; no source names the voice",
}


def flatten(text: str) -> str:
    """Letters only, unaccented, u/v and i/j folded — enough to match a
    transcription against its own source across punctuation and accent
    conventions, not enough to match a different text."""
    s = unicodedata.normalize("NFD", text)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("æ", "ae").replace("Æ", "Ae").replace("œ", "oe").replace("Œ", "Oe")
    s = s.replace("j", "i").replace("J", "I").replace("v", "u").replace("V", "U")
    return re.sub(r"[^a-z]", "", s.lower())


def _indent(line: str) -> str:
    """The leading whitespace of a line. The pattern matches everywhere,
    including the empty string, so this never returns None — but saying so
    once is better than three unchecked .group(1) calls."""
    m = re.match(r"(\s*)", line)
    return m.group(1) if m else ""


SOURCE_FILE = re.compile(r"[\w./-]+\.txt", re.IGNORECASE)


def _path_values(header: str) -> list[str]:
    """The whole value of every ``path`` key in one witness header.

    A declaration is prose, and the longer ones wrap over several comment
    lines, so the value is joined before anything is read out of it.
    """
    values: list[str] = []
    current_key: str | None = None
    current_value: list[str] = []
    for line in header.splitlines():
        if not line.startswith("#"):
            break
        opened = re.match(r"#\s*([\w-]+):\s*(.*)", line)
        if opened:
            if current_key == "path":
                values.append(" ".join(current_value))
            current_key = opened.group(1)
            current_value = [opened.group(2)]
        elif current_key:
            current_value.append(line.lstrip("# ").strip())
    if current_key == "path":
        values.append(" ".join(current_value))
    return values


def declared_sources(header: str) -> list[str]:
    """Every local source FILE a witness header names, ranged or not.

    A witness may instead name printed pages — thirteen of them transcribe
    page images, ``printed page LIII (scan leaf 58)`` — and those have no
    archive here to be compared against. Naming a `.txt` is what says there is
    one, which is why the check that follows the ranges asks this first.
    """
    return [
        match.group(0) for value in _path_values(header) for match in SOURCE_FILE.finditer(value)
    ]


def _range_declarations(header: str) -> list[tuple[str, list[int]]]:
    """Source files and line numbers declared by one witness header.

    More than one source file may occur in that value (the dismissal and Last
    Gospel use both Ordo.txt and Prayers.txt), and the older singular spelling
    ``line N`` is valid too.
    """
    declarations: list[tuple[str, list[int]]] = []
    pattern = re.compile(
        r"([\w./-]+\.txt)(?:(?![\w./-]+\.txt).){0,240}?"
        r"\([^)]*\blines?\s+([\d,\s-]+)\)",
        re.IGNORECASE,
    )
    for value in _path_values(header):
        for match in pattern.finditer(value):
            numbers = [int(n) for n in re.findall(r"\d+", match.group(2))]
            if numbers:
                declarations.append((match.group(1), numbers))
    return declarations


def _declares_ranges(text_id: str) -> bool:
    """Whether a witness claims source lines, even if their syntax is bad."""
    wdir = CORPUS / "witnesses" / text_id
    return any(
        re.search(r"^#\s*path:.*\bline", wf.read_text(encoding="utf-8"), re.MULTILINE)
        for wf in sorted(wdir.glob("*.txt"))
    )


def _raw_archive_for(declared_path: str) -> Path | None:
    """Resolve one source path to the best matching local raw archive.

    The archive names add a source prefix (usually ``do-`` or ``mr-``),
    while the headers retain the upstream path. Punctuation-free stems are
    therefore the stable identity; a matching parent directory breaks ties.
    """
    source_path = Path(declared_path)
    source_key = re.sub(r"[^a-z0-9]", "", source_path.stem.lower())
    parent_key = re.sub(r"[^a-z0-9]", "", source_path.parent.name.lower())
    candidates: list[tuple[int, Path]] = []
    for candidate in sorted((CORPUS / "witnesses" / "raw").glob("*.txt")):
        candidate_key = re.sub(r"[^a-z0-9]", "", candidate.stem.lower())
        if source_key and source_key in candidate_key:
            parent_match = int(bool(parent_key and parent_key in candidate_key))
            candidates.append((parent_match, candidate))
    return max(candidates, key=lambda item: item[0])[1] if candidates else None


def witness_ranges(text_id: str) -> list[tuple[Path, int, int]]:
    """(raw file, first line, last line) for every declared source span."""
    out: list[tuple[Path, int, int]] = []
    wdir = CORPUS / "witnesses" / text_id
    if not wdir.is_dir():
        return out
    for wf in sorted(wdir.glob("*.txt")):
        header = wf.read_text(encoding="utf-8")
        # A comma-separated range is intentionally read as one enclosing
        # span.  It may include a rubric between the named lines; that is a
        # safe superset and avoids silently scanning the whole archive.
        for declared_path, numbers in _range_declarations(header):
            raw = _raw_archive_for(declared_path)
            if raw:
                out.append((raw, min(numbers), max(numbers)))
    return out


def marked_lines(text_id: str, mass: bool = True) -> list[tuple[str, str]]:
    """(speaker, flattened text) for the marked lines of this text's own
    span in the archived sources; falls back to every archive when a
    witness records no line range."""
    spans = witness_ranges(text_id)
    files: list[list[str]] = []
    if spans:
        for raw, first, last in spans:
            lines = raw.read_text(encoding="utf-8").splitlines()
            files.append(lines[max(0, first - 1) : last])
    elif not _declares_ranges(text_id):
        for raw in sorted((CORPUS / "witnesses" / "raw").glob("*.txt")):
            files.append(raw.read_text(encoding="utf-8").splitlines())
    out = []
    for lines in files:
        for line in lines:
            m = re.match(r"^([SMVROsmvro])\.\s+(.*)$", line.strip())
            if m and m.group(2).strip():
                marker = m.group(1).upper()
                if not mass and marker not in SPEAKER_MARKERS_ONLY:
                    continue
                out.append((MARKERS[marker], flatten(m.group(2))))
    return out


def span_covers(doc) -> bool:
    """Does the declared line range still contain the words transcribed from
    it?

    The range is written by hand — `path: … (lines 5, 11-12)` — and a source
    file that gains a line, or a transcription that reaches one line further
    than the header says, leaves it short. Nothing noticed, because a short
    range simply yields fewer markers, and the rule for a passage the Ordo
    leaves unmarked then supplies the celebrant. So the ONE line the Ordo
    marks `M.` becomes the priest's, silently, and `--write` puts it in the
    file: this was proposing sacerdos for *Ad Deum, qui lætíficat* — the
    server's answer, marked as the server's two lines below the declared
    range.

    A tool that writes editorial data has to know when it is out of its
    depth. The question is asked per SEGMENT, because that is the unit the
    alignment works in: a range that holds most of a text but stops one line
    short still leaves the last segment to be guessed at, and Pax Dómini —
    two lines, the second of them the server's — is exactly that shape.
    Comparison is by `flatten`, which folds accents, ligatures and i/j, so
    the transcription's own conventions do not count as a miss. One
    convention needs more than folding: the archived Ordo writes the name
    slots the missal prints as `N.` with markers of its own (`N.p` for the
    Pope, `N.b` for the bishop), and every transcription strips them as
    edition framing — declared in the witness headers. Their letters would
    otherwise land INSIDE a segment and break it in two, which is what
    Te ígitur did the moment its range was written down correctly.
    """
    spans = witness_ranges(doc["id"])
    if not spans:
        # A text that names no raw lines may use the deliberate whole-archive
        # fallback.  A text that *tries* to name them in unreadable syntax is
        # unsourced: malformed provenance must never buy the same trust as
        # verified provenance.
        return not _declares_ranges(doc["id"])
    span = ""
    for raw, first, last in spans:
        lines = raw.read_text(encoding="utf-8").splitlines()[max(0, first - 1) : last]
        # The archived Ordo interleaves directions and macro calls with the
        # words. Witness transcriptions strip both, so they cannot be allowed
        # to break an otherwise exact span. Inline parenthetical rubrics are
        # framing too. Keep unmarked continuation lines: several prayers run
        # across them.
        textual = []
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith("!!!"):
                line = stripped[3:]
                stripped = line.lstrip()
            if stripped.startswith(("!", "&", "#", "_", "wait")):
                continue
            line = re.sub(r"^[SMVROsmvro]\.\s*", "", line.strip())
            line = re.sub(r"\([^)]*\)", " ", line)
            line = re.sub(r"N\.[a-z]?\s+et\s+N\.[a-z]?", " ", line)
            line = re.sub(r"N\.[a-z]?", " ", line)
            line = re.sub(r"wait\d+", " ", line)
            textual.append(line)
        span += flatten(" ".join(textual))

    apparatus_entries = []
    source = doc.get("source") or (doc.get("editorial") or {}).get("source") or {}
    apparatus_pointer = source.get("apparatus")
    if apparatus_pointer:
        apparatus_path = CORPUS / apparatus_pointer
        if apparatus_path.is_file():
            apparatus_entries = json.loads(apparatus_path.read_text(encoding="utf-8")).get(
                "adjudicated", []
            )
    for seg in doc["segments"]:
        if seg.get("type") != "verse" or not seg.get("words"):
            continue
        keys = {""}
        for word in seg["words"]:
            form = flatten(word["form"])
            readings = {form}
            for entry in apparatus_entries:
                if (
                    entry.get("at") != word["id"]
                    or entry.get("class") != "orthography"
                    or flatten(entry.get("ours", "")) != form
                ):
                    continue
                readings.update(
                    flatten(reading)
                    for reading in entry.get("witnesses", {}).values()
                    if isinstance(reading, str) and reading
                )
            keys = {prefix + reading for prefix in keys for reading in readings}

        # Apparatus entries license their recorded witness readings, not an
        # arbitrary number of edits near the ruled word. Thus the established
        # Genetrice/Genitrice and negligentia/neglegentia spellings pass while
        # an unrelated one-letter typo still fails closed.
        if not any(key in span for key in keys):
            return False
    return True


def voice_of(doc, index: int) -> str | None:
    """The voice the nearest preceding rubric sets, if any says."""
    for seg in reversed(doc["segments"][:index]):
        if seg.get("type") != "rubric":
            continue
        rubric = flatten(seg.get("text", ""))
        for phrase, voice in VOICE_RUBRICS:
            if flatten(phrase) in rubric:
                return voice
    return None


def align_speakers(doc, lines) -> dict[str, str]:
    """Match the text's verse segments against the source's marked lines IN
    ORDER.

    Matching on content alone cannot read a dialogue that repeats itself:
    the Kyrie is nine invocations of two phrases, said alternately by
    priest and server, so "Kýrie, eléison" stands under both markers and a
    content match rightly refuses to choose. The order decides what the
    words cannot, and refusing to use it left the most obviously
    attributable text in the Mass unattributed."""
    seg_ids, seg_keys = [], []
    for seg in doc["segments"]:
        if seg.get("type") != "verse" or not seg.get("words"):
            continue
        seg_ids.append(seg["id"])
        seg_keys.append(flatten("".join(w["form"] for w in seg["words"])))
    line_keys = [line for _, line in lines]
    out: dict[str, str] = {}
    for a, b, n in difflib.SequenceMatcher(None, seg_keys, line_keys).get_matching_blocks():
        for i in range(n):
            out[seg_ids[a + i]] = lines[b + i][0]
    return out


def propose(doc, disagreements: list[str] | None = None) -> dict[str, dict]:
    is_mass = doc.get("category") in {"ordinarium", "proprium"}
    lines = marked_lines(doc["id"], mass=is_mass)
    positional = align_speakers(doc, lines)
    # If the declared range no longer holds this text's words, the markers
    # read out of it are the wrong markers, and the rule that supplies the
    # celebrant for unmarked text would be supplying him for text the book
    # marks otherwise. Propose only what was matched positionally, and let
    # main report the text.
    sourced = span_covers(doc)
    ruled = voice_ruling(doc)
    out: dict[str, dict] = {}
    for i, seg in enumerate(doc["segments"]):
        if seg.get("type") != "verse":
            continue
        words = seg.get("words") or []
        if not words:
            continue
        key = flatten("".join(w["form"] for w in words))
        proposal = {}
        ref_s = f"{doc['id']}.{seg['id']}"
        if ref_s in SPEAKER_RULINGS:
            proposal["speaker"] = SPEAKER_RULINGS[ref_s][0]
        elif seg["id"] in positional:
            proposal["speaker"] = positional[seg["id"]]
        else:
            hits = {speaker for speaker, line in lines if key and (key == line or key in line)}
            if len(hits) == 1:
                proposal["speaker"] = hits.pop()
            # …and only where the markers were actually read: `sourced`.
            # See span_covers — a stale range makes the markers run out,
            # and this rule would then hand the celebrant a line the book
            # marks otherwise.
            elif sourced and is_mass:
                # The Ordo prints the CELEBRANT's text unmarked and gives
                # every other voice a marker — S. and M., V. and R., O. for
                # all — as the archived source shows: the ministers'
                # Confiteor is M., the Suscipiat is M., the responses are R.
                # So unmarked text in the Mass is the priest's, and the
                # Ritus servandus agrees, naming sacerdos or celebrans as
                # the actor throughout its own prescriptions.
                #
                # A passage with no markers at all is not a passage this
                # rule cannot see — it is a passage with no other voice in
                # it, which is the strongest case of all: Aufer a nobis,
                # the Lavabo, Quid retribuam are the priest alone.
                proposal["speaker"] = "sacerdos"

        ref = f"{doc['id']}.{seg['id']}"
        # The law first, then what the text's own rubrics say. Where the two
        # disagree the law wins and the disagreement is REPORTED, because a
        # rubric read one way and a rubric read the other way is a finding,
        # not a detail to settle silently.
        from_rubric = voice_of(doc, i)
        if ref in VOICE_UNSETTLED:
            pass  # named in the table above: no single value is true of it
        elif ref in VOICE_SEGMENT_RULINGS:
            proposal["voice"] = VOICE_SEGMENT_RULINGS[ref][0]
        elif ruled:
            proposal["voice"] = ruled[0]
        elif from_rubric:
            proposal["voice"] = from_rubric

        if (
            disagreements is not None
            and from_rubric
            and "voice" in proposal
            and from_rubric != proposal["voice"]
        ):
            cite = (VOICE_SEGMENT_RULINGS.get(ref) or ruled or ("", "?"))[1]
            disagreements.append(
                f"{ref}: the text's rubric reads {from_rubric}, {cite} rules {proposal['voice']}"
            )
        if proposal:
            out[seg["id"]] = proposal
    return out


def main() -> None:
    write = "--write" in sys.argv
    total = attributed = voiced = 0
    disagreements: list[str] = []
    unsourced: list[str] = []
    for path in sorted((CORPUS / "texts").rglob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        stale = not span_covers(doc)
        if stale:
            unsourced.append(doc["id"])
        proposal = propose(doc, disagreements)
        verses = [s for s in doc["segments"] if s.get("type") == "verse" and s.get("words")]
        total += len(verses)
        attributed += sum(1 for p in proposal.values() if "speaker" in p)
        voiced += sum(1 for p in proposal.values() if "voice" in p)
        # A text whose declared range no longer holds its words is READ but
        # never WRITTEN. The proposal for it is still shown, because it is
        # what a person needs in order to fix the range; it is not applied,
        # because what is already in the file was written when the range was
        # right, and a run that quietly replaced it with a thinner reading
        # would lose the better one. Run without --write, mend the header,
        # and the text stops appearing here.
        if write and stale:
            continue
        if not write:
            if proposal:
                print(f"{doc['id']}")
                for sid, p in proposal.items():
                    print(f"   {sid:5} {p.get('speaker', '-'):10} {p.get('voice', '-')}")
            continue
        # Insert by TEXT, not by re-serializing: these documents are
        # hand-formatted (analysis blocks sit on one line) and a round trip
        # through json.dumps would reformat every file it touches, burying
        # two added fields in seventeen thousand changed lines.
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        # Two passes. The first learns which segments already carry a
        # speaker or a voice, because those lines come AFTER the "type"
        # line where a new one would be inserted — write in one pass and
        # every existing value gets a twin, which JSON accepts silently.
        # Words carry a morph "voice" of their own (act, pass, dep), and
        # some are written across several lines — so a key line counts as
        # the SEGMENT's only when it is indented exactly like the segment's
        # own "id". Matching on the name alone deletes verb voices.
        existing: dict[str, set[str]] = {}
        current, seg_indent = None, ""
        for line in lines:
            m = re.match(r'(\s*)"id": "(s\d+)",', line)
            if m:
                current, seg_indent = m.group(2), m.group(1)
            m_key = re.match(r'(\s*)"(speaker|voice)": "[a-z]+",', line)
            if current and m_key and m_key.group(1) == seg_indent:
                existing.setdefault(current, set()).add(m_key.group(2))

        out, current, seg_indent, changed = [], None, "", False
        for line in lines:
            m = re.match(r'(\s*)"id": "(s\d+)",', line)
            if m:
                current, seg_indent = m.group(2), m.group(1)
            m_key = re.match(r'(\s*)"(speaker|voice)": "[a-z]+",', line)
            if current and m_key and m_key.group(1) == seg_indent:
                key = m_key.group(2)
                value = (proposal.get(current) or {}).get(key)
                if value is None:
                    changed = True  # no longer proposed: drop the stale claim
                    continue
                replacement = f'{_indent(line)}"{key}": "{value}",\n'
                if replacement != line:
                    changed = True
                out.append(replacement)
                continue
            out.append(line)
            if current and re.match(r'\s*"type": "verse",', line):
                p_ = proposal.get(current) or {}
                for key in ("speaker", "voice"):
                    if key in p_ and key not in existing.get(current, set()):
                        out.append(f'{_indent(line)}"{key}": "{p_[key]}",\n')
                        changed = True
        if changed:
            path.write_text("".join(out), encoding="utf-8")
    for line in disagreements:
        print(f"DISAGREES  {line}")
    for text_id in unsourced:
        print(f"UNSOURCED  {text_id}: the declared line range no longer holds this text's words")
    verb = "applied" if write else "proposed"
    print(
        f"\n{verb} {attributed}/{total} speakers, {voiced}/{total} voices"
        f" ({len(disagreements)} rubric/law disagreements,"
        f" {len(unsourced)} texts with a stale line range)"
    )


if __name__ == "__main__":
    main()

"""Emit the reader edition. Deterministic, and verified against its source."""

from __future__ import annotations

import copy
import json
import unicodedata
from pathlib import Path
from typing import Any

from build_reader import bibliography, store

# The reader edition's OWN version. It moves when this file changes what it
# writes, which is a different event from the corpus changing what it stores —
# the manifest names both, so a consumer can tell the two apart.
# 4.0.0: the 3.2.0→3.3.0 step renamed the per-word `fn` key to `ex` — a
# breaking change that should have taken the major by this project's own
# policy, majored here — and this version adds the emitted normalization
# vectors, the `rs` retired-segment map, and the manifest's `normalization`
# entry.
# 4.1.0 adds the normalized bibliography catalogue and evidence graph.
# 4.2.0 splits its eager tables into manifest-declared catalogues, indexes,
# and independently loadable per-text slices for both the neutral core and
# every language package.
# 5.0.0 makes the bibliography index a compact source-to-text map and groups
# per-text uses by their shared edition, digital item, role and locator.
# 5.1.0 excludes exact citation attachments rejected by the audited evidence
# migration and reports the normalized-evidence denominator at build time.
# 5.2.0 adds manifest-declared, localized Mass-formulary assemblies. Their
# component list is authored by the corpus rather than rediscovered by apps.
# 5.3.0 adds one derived metrics resource so consumers share denominators.
SCHEMA = "5.3.0"
REGISTRY = Path(__file__).with_name("registry")

# WHAT A READER NEVER SEES, and what therefore never leaves the repository.
# Every name here is a decision, not an omission: the rule is that a field is
# dropped because a reader is never shown it, never because it is inconvenient.
DROP_DOC = {
    "schema_version",  # named once, in the manifest
    "ids",  # the mint and its tombstones: identity bookkeeping
    "notes",  # the editorial claims a reviewer reads in a diff
    "source",  # witness line ranges, which belong to the apparatus
}
# `analysis` is NOT dropped. It is what the word panel shows under the parse --
# confidence, review state, and which analyzers confirmed it -- and an edition
# that says "the system must know what it doesn't know" cannot ship the doubt
# and withhold the note of it. It is interned instead: 13 shapes carry 518 sites.
DROP_SEGMENT: set[str] = set()
DROP_WORD: set[str] = set()


def _compact(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=False)


def _record_array(values: list) -> str:
    """One logical record per line without paying the cost of full indentation."""
    if not values:
        return "[]\n"
    return "[\n" + ",\n".join(f"  {_compact(value)}" for value in values) + "\n]\n"


def _record_mapping(values: dict, indent: str = "  ") -> list[str]:
    items = list(values.items())
    lines = []
    for i, (key, value) in enumerate(items):
        comma = "," if i + 1 < len(items) else ""
        lines.append(f"{indent}{json.dumps(key, ensure_ascii=False)}:{_compact(value)}{comma}")
    return lines


def _artifact_json(artifact: dict) -> str:
    """A text header field and a segment per line: compact, but diffable."""
    header = [(key, value) for key, value in artifact.items() if key != "seg"]
    lines = ["{"]
    for key, value in header:
        lines.append(f"  {json.dumps(key)}:{_compact(value)},")
    lines.append('  "seg":[')
    rows = artifact["seg"]
    lines.extend(
        f"    {_compact(row)}{',' if i + 1 < len(rows) else ''}" for i, row in enumerate(rows)
    )
    lines.extend(["  ]", "}"])
    return "\n".join(lines) + "\n"


def _entries_json(entries: dict) -> str:
    """A dictionary header plus one complete lemma per diff line."""
    lines = ["{", '  "entries":{']
    lines.extend(_record_mapping(entries, "    "))
    lines.extend(["  }", "}"])
    return "\n".join(lines) + "\n"


def _calendar_json(payload: dict) -> str:
    lines = ["{", f'  "formularies":{_compact(payload["formularies"])},']
    lines.append(f'  "seasons":{_compact(payload["seasons"])},')
    lines.append('  "years":{')
    lines.extend(_record_mapping(payload["years"], "    "))
    lines.extend(["  }", "}"])
    return "\n".join(lines) + "\n"


def formulary_catalog(corpus: Path) -> dict:
    """Project authored assembly ids to the reader's slash-addressed texts."""
    formularies = []
    for authored in sorted(store.formularies(corpus), key=lambda value: value["order"]):
        formulary = {
            key: copy.deepcopy(value)
            for key, value in authored.items()
            if key != "formulary_schema"
        }
        for component in formulary["components"]:
            component["text"] = component["text"].replace(".", "/", 1)
        formularies.append(formulary)
    return {"schema_version": "1.0.0", "formularies": formularies}


def language_formulary_catalog(corpus: Path, language: str) -> dict:
    """Project localized titles without duplicating neutral assembly data."""
    return {
        "schema_version": "1.0.0",
        "language": language,
        "titles": [
            {"id": authored["id"], "title": authored["title"]}
            for authored in store.language_formularies(corpus, language)
        ],
    }


def corpus_metrics(corpus: Path, corpus_docs: list[tuple[dict, dict[str, dict]]]) -> dict:
    formularies = store.formularies(corpus)
    text_ids = [doc["id"] for doc, _glosses in corpus_docs]
    component_texts = {
        component["text"] for formulary in formularies for component in formulary["components"]
    }
    return {
        "schema_version": "1.0.0",
        "texts": {
            "total": len(text_ids),
            "proprium": sum(text_id.startswith("proprium.") for text_id in text_ids),
            "words": sum(
                len(segment.get("words") or [])
                for doc, _glosses in corpus_docs
                for segment in doc["segments"]
            ),
            "verse_segments": sum(
                segment.get("type") == "verse"
                for doc, _glosses in corpus_docs
                for segment in doc["segments"]
            ),
        },
        "languages": {
            language: {"texts": len(store.language_manifest(corpus, language)["texts"])}
            for language in store.language_ids(corpus)
        },
        "formularies": {
            "total": len(formularies),
            "observances": len({formulary["observance"] for formulary in formularies}),
            "component_uses": sum(len(formulary["components"]) for formulary in formularies),
            "unique_component_texts": len(component_texts),
        },
    }


def _concordance_json(payload: dict) -> str:
    latin = payload["latin"]
    lines = ["{", f'  "schema_version":{json.dumps(payload["schema_version"])},']
    lines.append('  "texts":[')
    lines.extend(
        f"    {_compact(value)}{',' if i + 1 < len(payload['texts']) else ''}"
        for i, value in enumerate(payload["texts"])
    )
    lines.extend(["  ],", '  "latin":{', '    "lemmata":{'])
    lines.extend(_record_mapping(latin["lemmata"], "      "))
    lines.extend(["    },", '    "forms":{'])
    lines.extend(_record_mapping(latin["forms"], "      "))
    lines.extend(["    }", "  }", "}"])
    return "\n".join(lines) + "\n"


def _language_concordance_json(payload: dict) -> str:
    lines = ["{", f'  "schema_version":{json.dumps(payload["schema_version"])},']
    lines.append(f'  "language":{json.dumps(payload["language"])},')
    lines.append('  "texts":[')
    lines.extend(
        f"    {_compact(value)}{',' if i + 1 < len(payload['texts']) else ''}"
        for i, value in enumerate(payload["texts"])
    )
    lines.extend(["  ],", '  "terms":{'])
    lines.extend(_record_mapping(payload["terms"], "    "))
    lines.extend(["  }", "}"])
    return "\n".join(lines) + "\n"


class RegistryStale(RuntimeError):
    """A source value has no stable reader-edition identity yet."""


class Table:
    """A corpus-wide table of repeated objects, addressed by index.

    Three layers repeat themselves hard enough to be worth this. 412 distinct
    parses carry 6,143 words and the fifty commonest carry two thirds of them;
    13 distinct analyses carry 518 sites -- 166 words, 130 segments and 222
    document defaults; 232 distinct citations carry 1,327 references. Written
    out at every site the parse alone was 44% of an authored text document --
    free in git, free after gzip, and not free in a phone's heap or in the
    bytes a page hands the browser.
    """

    def __init__(
        self, initial: list[dict] | None = None, *, locked: bool = False, label: str = "table"
    ) -> None:
        self.order: list[dict] = list(initial or [])
        self._index: dict[str, int] = {
            json.dumps(value, sort_keys=True, separators=(",", ":")): i
            for i, value in enumerate(self.order)
        }
        if len(self._index) != len(self.order):
            raise ValueError(f"{label} registry contains duplicate records")
        self._used: set[int] = set()
        self.locked = locked
        self.label = label

    def intern(self, value: dict) -> int:
        key = json.dumps(value, sort_keys=True, separators=(",", ":"))
        if key not in self._index:
            if self.locked:
                raise RegistryStale(
                    f"{self.label} registry is stale; run "
                    "python -m build_reader.update_registry and review the append"
                )
            self._index[key] = len(self.order)
            self.order.append(json.loads(key))
        index = self._index[key]
        self._used.add(index)
        return index

    def intern_all(self, values: list[dict]) -> list[int]:
        return [self.intern(v) for v in values]

    def edition(self) -> list[dict | None]:
        """Keep addresses stable while omitting records no active text reaches."""
        return [value if i in self._used else None for i, value in enumerate(self.order)]


def read_corpus(corpus: Path) -> list[tuple[dict, dict[str, dict]]]:
    """Every text with its gloss layers, in a stable order.

    Neutral cores and independently covered language layers are joined only in
    memory by the storage seam.
    """
    return store.all_texts(corpus)


def core_artifact(
    doc: dict,
    stored: dict,
    parses: Table,
    analyses: Table,
    citations: Table,
    projection: bibliography.ReaderCitationProjection | None = None,
) -> dict:
    """One language-neutral text and its shared reader-facing citations."""
    localization = stored.get("localization") or {}
    segments = []
    for segment in doc["segments"]:
        row: dict = {"id": segment["id"], "type": segment["type"]}
        for key, value in segment.items():
            if key in DROP_SEGMENT or key in ("id", "type", "words", "analysis"):
                continue
            row[key] = value
        if segment.get("analysis"):
            row["an"] = analyses.intern(segment["analysis"])

        words = segment.get("words") or []
        if words:
            cells = []
            for word in words:
                cell: dict = {"i": word["id"], "f": word["form"], "l": word["lemma"]}
                if word.get("post"):
                    cell["p"] = word["post"]
                cell["m"] = parses.intern(word["morph"])
                if word.get("head"):
                    cell["h"] = word["head"]
                if word.get("substantive"):
                    cell["s"] = True
                if word.get("analysis"):
                    cell["a"] = analyses.intern(word["analysis"])
                cells.append(cell)
            row["w"] = cells

        cited = (localization.get("narrative_citations") or {}).get(segment["id"])
        if cited and projection:
            cited = projection.citations(
                f"texts/{doc['id'].replace('.', '/', 1)}.json",
                ("localization", "narrative_citations", segment["id"]),
                cited,
            )
        if cited:
            row["nc"] = citations.intern_all(cited)
        if words:
            explanation_requirements = localization.get("explanations") or {}
            cited = {
                word["id"]: citations.intern_all(projected)
                for word in words
                if (requirement := explanation_requirements.get(word["id"]))
                and requirement.get("citations")
                and (
                    projected := projection.citations(
                        f"texts/{doc['id'].replace('.', '/', 1)}.json",
                        ("localization", "explanations", word["id"], "citations"),
                        requirement["citations"],
                    )
                    if projection
                    else requirement["citations"]
                )
            }
            if cited:
                row["ec"] = cited
        segments.append(row)

    artifact: dict = {"id": doc["id"]}
    for key, value in doc.items():
        if key in DROP_DOC or key in ("id", "segments", "status", "analysis_defaults"):
            continue
        if key == "analysis_defaults_words":
            continue
        artifact[key] = value
    artifact["st"] = doc["status"]
    artifact["ad"] = analyses.intern(doc["analysis_defaults"])
    if doc.get("analysis_defaults_words"):
        artifact["adw"] = analyses.intern(doc["analysis_defaults_words"])
    cited = localization.get("about_citations")
    if cited and projection:
        cited = projection.citations(
            f"texts/{doc['id'].replace('.', '/', 1)}.json",
            ("localization", "about_citations"),
            cited,
        )
    if cited:
        artifact["ac"] = citations.intern_all(cited)
    # Retired segment ids, so a shared `?s=` link outlives a merge or split:
    # the app resolves a retired id to the surviving segment and canonicalizes
    # the address. The mint itself stays behind with the rest of `ids`.
    if retired_segments := ((doc.get("ids") or {}).get("segments") or {}).get("retired"):
        artifact["rs"] = retired_segments
    # The same promise for a shared `?w=` link: a removed word no longer has
    # a panel to open, but it still leads to the surviving segment around it.
    if retired_words := (doc.get("ids") or {}).get("retired"):
        artifact["rw"] = retired_words
    artifact["seg"] = segments
    return artifact


def language_artifact(
    doc: dict,
    layer: dict,
    citations: Table,
    relationships: dict[str, str] | None = None,
    projection: bibliography.ReaderCitationProjection | None = None,
) -> dict:
    """One target language for one text, independently loadable."""
    rows = []
    for segment in doc["segments"]:
        localized = (layer.get("segments") or {}).get(segment["id"]) or {}
        row: dict = {"id": segment["id"]}
        if translation := localized.get("translation"):
            row["tr"] = translation
        cited = localized.get("translation_citations")
        if cited and projection:
            cited = projection.citations(
                f"languages/{layer['lang']}/texts/{doc['id'].replace('.', '/', 1)}.json",
                ("segments", segment["id"], "translation_citations"),
                cited,
            )
        if cited:
            row["tc"] = citations.intern_all(cited)
        site = f"{doc['id']}.{segment['id']}.{layer['lang']}"
        if relationship := (relationships or {}).get(site):
            row["tb"] = relationship
        if narrative := localized.get("narrative"):
            row["nr"] = narrative
        words = segment.get("words") or []
        if words:
            entries = layer.get("words") or {}
            row["g"] = [(entries.get(word["id"]) or {}).get("gloss", "") for word in words]
            for field, short in (("explanation", "ex"), ("note", "nt")):
                prose = {
                    word["id"]: (entries.get(word["id"]) or {}).get(field)
                    for word in words
                    if (entries.get(word["id"]) or {}).get(field)
                }
                if prose:
                    row[short] = prose
        rows.append(row)
    return {
        "id": doc["id"],
        "language": layer["lang"],
        "about": layer["about"],
        "seg": rows,
    }


def expand(
    artifact: dict,
    language_art: dict,
    parses: list,
    analyses: list,
    shared_citations: list,
    language_citations: list,
) -> tuple[dict, dict]:
    """Read a base text and one language artifact back into checking views.

    The inverse of `core_artifact` plus `language_artifact`, and the whole of
    `verify`'s method: rather
    than checking field against field -- which tests only the fields somebody
    remembered to list -- the edition is expanded and compared whole. A field
    added to the corpus and forgotten here fails as a difference, not as
    silence. The app carries this same operation in TypeScript.
    """
    doc: dict = {}
    layer: dict = {
        "text": artifact["id"],
        "lang": language_art["language"],
        "status": artifact["st"],
        "analysis_defaults": analyses[artifact["ad"]],
        "about": language_art["about"],
        "segments": {},
        "words": {},
    }
    for key, value in artifact.items():
        # `rs` is not copied back: its source (`ids`) is a declared drop, so
        # the round-trip cannot see it. `verify` compares it explicitly
        # against `ids.segments.retired` instead.
        if key in ("st", "ad", "adw", "ac", "seg", "rs", "rw"):
            continue
        doc[key] = value
    doc["status"] = artifact["st"]
    doc["analysis_defaults"] = analyses[artifact["ad"]]
    if "adw" in artifact:
        doc["analysis_defaults_words"] = analyses[artifact["adw"]]
    if cited := artifact.get("ac"):
        layer["about_citations"] = [shared_citations[i] for i in cited]

    segments = []
    localized_rows = {row["id"]: row for row in language_art["seg"]}
    for row in artifact["seg"]:
        localized = localized_rows[row["id"]]
        segment: dict = {}
        for key, value in row.items():
            if key in ("w", "ec", "nc", "an"):
                continue
            segment[key] = value
        if "an" in row:
            segment["analysis"] = analyses[row["an"]]
        bucket: dict = {}
        if "tr" in localized:
            bucket["translation"] = localized["tr"]
        if cited := localized.get("tc"):
            bucket["translation_citations"] = [language_citations[i] for i in cited]
        if "nr" in localized:
            bucket["narrative"] = localized["nr"]
        if cited := row.get("nc"):
            bucket["narrative_citations"] = [shared_citations[i] for i in cited]
        if bucket:
            layer["segments"][row["id"]] = bucket
        if "w" in row:
            words = []
            for position, cell in enumerate(row["w"]):
                word: dict = {"id": cell["i"], "form": cell["f"], "lemma": cell["l"]}
                if "p" in cell:
                    word["post"] = cell["p"]
                word["morph"] = parses[cell["m"]]
                if "h" in cell:
                    word["head"] = cell["h"]
                if cell.get("s"):
                    word["substantive"] = True
                if "a" in cell:
                    word["analysis"] = analyses[cell["a"]]
                words.append(word)
                entry: dict = {"gloss": localized["g"][position]}
                for field, short in (("explanation", "ex"), ("note", "nt")):
                    value = (localized.get(short) or {}).get(cell["i"])
                    if value:
                        entry[field] = value
                cited = (row.get("ec") or {}).get(cell["i"])
                if cited:
                    entry["explanation_citations"] = [shared_citations[i] for i in cited]
                layer["words"][cell["i"]] = entry
            segment["words"] = words
        segments.append(segment)
    doc["segments"] = segments
    return doc, layer


def lexicon_slice(
    corpus: Path,
    language: str | None = None,
    lemmas: set[str] | None = None,
    projection: bibliography.ReaderCitationProjection | None = None,
) -> dict:
    """The dictionary, or the part of it a given set of words reaches for.

    Sliced per text it duplicated: the same hundred common entries appear in
    every text, and the slices came to 52% of the whole edition. So the edition
    ships ONE dictionary, fetched once and kept. Slicing stays available for the
    units that must arrive self-sufficient — a day's proper is picked whole and
    should not need a second request to be read.
    """
    relative_path = (
        "lexicon/lemmata.json" if language is None else f"languages/{language}/lexicon.json"
    )
    source_path = corpus / relative_path
    entries = copy.deepcopy(json.loads(source_path.read_text(encoding="utf-8"))["entries"])
    if projection:
        for lemma, entry in entries.items():
            parts: tuple[str, ...]
            if language is None:
                container = entry.get("localization") or {}
                parts = ("entries", lemma, "localization", "note_citations")
            else:
                container = entry
                parts = ("entries", lemma, "note_citations")
            cited = container.get("note_citations")
            if not cited:
                continue
            projected = projection.citations(relative_path, parts, cited)
            if projected:
                container["note_citations"] = projected
            else:
                container.pop("note_citations", None)
    keep = sorted(lemmas) if lemmas is not None else sorted(entries)
    return {k: entries[k] for k in keep if k in entries}


def language_lexicon_differences(
    corpus_docs: list[tuple[dict, dict[str, dict]]],
    covered_texts: set[str],
    entries: dict,
    heads: dict,
) -> tuple[set[str], set[str]]:
    """Missing required senses and entries that have no neutral head.

    A language pack may cover only part of the corpus and its dictionary may
    grow ahead of that coverage. It must therefore contain every lemma used by
    its covered texts, not every lemma used by every language.
    """
    required = {
        word["lemma"]
        for doc, _ in corpus_docs
        if doc["id"] in covered_texts
        for segment in doc["segments"]
        for word in (segment.get("words") or [])
    }
    return required - set(entries), set(entries) - set(heads)


def _fold(value: str) -> str:
    """Casefold, decompose, strip combining marks — BEFORE ligature expansion.

    Order is the whole correctness of this function: ǽ (U+01FD) is a
    precomposed accented ligature, so an æ→ae replacement that runs first
    never sees it, and after decomposition a bare æ survives into the key.
    Ligatures themselves have no NFKD decomposition, so expanding them after
    the mark strip catches the plain and the formerly-accented ones alike.
    """
    stripped = "".join(
        char
        for char in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(char)
    )
    return stripped.replace("æ", "ae").replace("œ", "oe")


def normalize_latin(value: str) -> str:
    """A search key: case- and accent-insensitive, with typed-out ligatures."""
    return _fold(value)


def normalize_search(value: str) -> str:
    """A language-neutral, case-insensitive key for reader-entered text."""
    letters = _fold(value).replace("ł", "l")
    return " ".join("".join(char if char.isalnum() else " " for char in letters).split())


def tokenize_search(value: str) -> list[str]:
    normalized = normalize_search(value)
    return normalized.split() if normalized else []


# Hand-authored truth shared with every consumer of the edition. The pairs
# are EXPECTED outputs, not echoes of the implementation: this module's own
# tests assert normalize_latin/normalize_search against them, the emitted
# normalization.json carries them verbatim, and the app asserts its own
# normalizers against the vendored copy — so the two runtimes cannot drift
# apart silently again (the ǽ defect lived exactly in that gap).
NORMALIZATION_VECTORS: dict[str, list[list[str]]] = {
    "latin": [
        ["sǽcula", "saecula"],
        ["Sǽcula", "saecula"],
        ["quǽsumus", "quaesumus"],
        ["Quǽsumus", "quaesumus"],
        ["Galilǽæ", "galilaeae"],
        ["Iudǽi", "iudaei"],
        ["cælos", "caelos"],
        ["Æthíopum", "aethiopum"],
        ["fœ́deris", "foederis"],
        ["cœlum", "coelum"],
        ["DÓMINUS", "dominus"],
        ["María", "maria"],
        ["exsultávit", "exsultavit"],
        ["Iesu", "iesu"],
    ],
    "search": [
        ["In sǽcula sæculórum. Amen.", "in saecula saeculorum amen"],
        ["Quǽsumus, Dómine", "quaesumus domine"],
        ["Najświętsza Panno", "najswietsza panno"],
        ["ŁASKI pełna", "laski pelna"],
        ["Zdrowaś, Maryjo!", "zdrowas maryjo"],
        ["Pod Twoją obronę", "pod twoja obrone"],
        ["Sǽculo 12", "saeculo 12"],
    ],
}


def index(corpus_docs: list[tuple[dict, dict]], text_registry: list[str] | None = None) -> dict:
    """Lemma and normalized Latin-form postings over stable text addresses.

    A posting is `[text number, segment id, word id, position]`. The first
    three values are the stable address SCHEMA.md documents; the final value
    is derived search geometry. Forms point directly to occurrences rather
    than through lemmata, so phrase candidates can be ranked before any text
    document is opened.
    """
    active = [doc["id"] for doc, _ in corpus_docs]
    texts = list(text_registry or active)
    positions = {text_id: i for i, text_id in enumerate(texts)}
    missing = [text_id for text_id in active if text_id not in positions]
    if missing:
        raise RegistryStale(
            "text registry is stale; run python -m build_reader.update_registry "
            f"and review the append ({', '.join(missing[:3])})"
        )
    lemmata: dict[str, list[list]] = {}
    forms: dict[str, list[list]] = {}
    for doc, _glosses in corpus_docs:
        number = positions[doc["id"]]
        for segment in doc["segments"]:
            for position, word in enumerate(segment.get("words") or []):
                # The WORD ID, not its position. A posting is what a lemma page
                # turns into a link -- `/app/pl/<text>?w=<id>` -- and a position
                # is not an address: it moves the moment a word is inserted
                # before it, which is the one edit the mint exists to survive.
                # The first draft stored positions and would have produced a
                # concordance that drifted off its own words.
                posting = [number, segment["id"], word["id"], position]
                lemmata.setdefault(word["lemma"], []).append(posting)
                forms.setdefault(normalize_latin(word["form"]), []).append(posting)
    active_set = set(active)
    return {
        "schema_version": "2.0.0",
        "texts": [text_id if text_id in active_set else None for text_id in texts],
        "latin": {
            "lemmata": {k: lemmata[k] for k in sorted(lemmata)},
            "forms": {k: forms[k] for k in sorted(forms)},
        },
    }


def language_index(
    corpus_docs: list[tuple[dict, dict]], language: str, text_registry: list[str]
) -> dict:
    """Normalized target-language verse terms over stable segment addresses."""
    positions = {text_id: i for i, text_id in enumerate(text_registry)}
    covered = {doc["id"] for doc, glosses in corpus_docs if language in glosses}
    missing = sorted(covered - set(positions))
    if missing:
        raise RegistryStale(
            "text registry is stale; run python -m build_reader.update_registry "
            f"and review the append ({', '.join(missing[:3])})"
        )

    terms: dict[str, list[list]] = {}
    for doc, glosses in corpus_docs:
        layer = glosses.get(language)
        if layer is None:
            continue
        number = positions[doc["id"]]
        for segment in doc["segments"]:
            if segment["type"] != "verse":
                continue
            translation = (
                (layer.get("segments") or {}).get(segment["id"], {}).get("translation", "")
            )
            for position, term in enumerate(tokenize_search(translation)):
                terms.setdefault(term, []).append([number, segment["id"], position])
    return {
        "schema_version": "1.0.0",
        "language": language,
        "texts": [text_id if text_id in covered else None for text_id in text_registry],
        "terms": {term: terms[term] for term in sorted(terms)},
    }


# The span the calendar covers. Decision #6 fixed 2026-2100 for the shipped
# table; `temporale.year(n)` builds the year ENDING in n, so the last one has to
# be 2101 for the civil year 2100 to be complete to its final Saturday.
KALENDARIUM = range(2026, 2102)


def kalendarium() -> dict:
    """Every supported Roman-calendar day with a Mass of its own, 2026-2100.

    Explicit rather than derivable: decision #6 says apps never implement
    movable-feast logic, and three readers are coming. A row is
    `[date, formulary, season, class, position]`, the last three as indices
    into the vocabularies beside them, and `position` differs from `formulary`
    only where a feast or n. 18's transfer moved something.
    """
    from kalendarium.roman import year

    formularies: list[str] = []
    seasons: list[str] = []

    def ix(table: list[str], value: str) -> int:
        if value not in table:
            table.append(value)
        return table.index(value)

    years: dict[str, list] = {}
    for ending in KALENDARIUM:
        years[str(ending)] = [
            [
                d.when.isoformat(),
                ix(formularies, d.formulary),
                ix(seasons, d.season),
                d.dies_class,
                ix(formularies, d.position),
            ]
            for d in year(ending)
        ]
    return {"formularies": formularies, "seasons": seasons, "years": years}


def _registry_records(name: str) -> list:
    path = REGISTRY / f"{name}.json"
    if not path.exists():
        raise RegistryStale(
            f"{name} registry is missing; run python -m build_reader.update_registry"
        )
    values = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(values, list):
        raise ValueError(f"{path} must contain an array")
    return values


def update_registry(corpus: Path) -> dict[str, int]:
    """Append identities used by the corpus; never reorder or reuse one."""
    REGISTRY.mkdir(parents=True, exist_ok=True)

    def existing(name: str) -> list:
        path = REGISTRY / f"{name}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []

    parses = Table(existing("morphology"), label="morphology")
    analyses = Table(existing("analysis"), label="analysis")
    citations = Table(existing("citations"), label="citations")
    graph, language_graphs = bibliography.load(corpus)
    projection = bibliography.ReaderCitationProjection(corpus, graph, language_graphs)
    docs = read_corpus(corpus)
    for doc, glosses in docs:
        core_artifact(
            doc,
            store.core(corpus, doc["id"]),
            parses,
            analyses,
            citations,
            projection,
        )
        for layer in glosses.values():
            language_artifact(doc, layer, citations, projection=projection)

    texts = existing("texts")
    if len(set(texts)) != len(texts) or not all(isinstance(value, str) for value in texts):
        raise ValueError("text registry must contain unique string ids")
    known = set(texts)
    texts.extend(doc["id"] for doc, _ in docs if doc["id"] not in known)

    values = {
        "morphology": parses.order,
        "analysis": analyses.order,
        "citations": citations.order,
        "texts": texts,
    }
    changes: dict[str, int] = {}
    for name, records in values.items():
        before = len(existing(name))
        (REGISTRY / f"{name}.json").write_text(_record_array(records), encoding="utf-8")
        changes[name] = len(records) - before
    return changes


def emit(corpus: Path, out: Path) -> dict[str, Any]:
    """Write the whole reader edition. Returns what it wrote."""
    corpus_docs = read_corpus(corpus)
    evidence_graph, language_evidence = bibliography.load(corpus)
    evidence_errors = bibliography.validate(corpus, evidence_graph, language_evidence)
    if evidence_errors:
        raise ValueError("invalid bibliography graph: " + "; ".join(evidence_errors))
    projection = bibliography.ReaderCitationProjection(corpus, evidence_graph, language_evidence)
    neutral_evidence = {
        record["id"]: record
        for record in bibliography.public_text_evidence(evidence_graph)["texts"]
    }
    localized_evidence = {
        language: {
            record["id"]: record
            for record in bibliography.public_text_evidence(
                evidence_graph, language_evidence[language]
            )["texts"]
        }
        for language in language_evidence
    }
    parses = Table(_registry_records("morphology"), locked=True, label="morphology")
    analyses = Table(_registry_records("analysis"), locked=True, label="analysis")
    citation_registry = _registry_records("citations")
    shared_citations = Table(citation_registry, locked=True, label="citations")
    languages = store.language_ids(corpus)
    language_citations = {
        language: Table(citation_registry, locked=True, label="citations") for language in languages
    }
    translation_relationships = {
        language: store.translation_relationships(corpus, language) for language in languages
    }
    text_registry = _registry_records("texts")
    if len(set(text_registry)) != len(text_registry) or not all(
        isinstance(value, str) for value in text_registry
    ):
        raise ValueError("text registry must contain unique string ids")
    written: dict[str, Any] = {
        "texts": 0,
        "language_texts": 0,
        "formularies": 0,
        "evidence": 0,
        "bytes": 0,
    }
    neutral_evidence_paths: dict[str, str] = {}
    localized_evidence_paths: dict[str, dict[str, str]] = {language: {} for language in languages}

    (out / "texts").mkdir(parents=True, exist_ok=True)
    for doc, glosses in corpus_docs:
        artifact = core_artifact(
            doc,
            store.core(corpus, doc["id"]),
            parses,
            analyses,
            shared_citations,
            projection,
        )
        category, slug = doc["id"].split(".", 1)
        directory = out / "texts" / category
        directory.mkdir(parents=True, exist_ok=True)
        body = _artifact_json(artifact)
        (directory / f"{slug}.json").write_text(body, encoding="utf-8")
        written["texts"] += 1
        written["bytes"] += len(body.encode())
        if doc["id"] in neutral_evidence:
            evidence_path = f"bibliography/texts/{category}/{slug}.json"
            evidence_body = (
                json.dumps(neutral_evidence[doc["id"]], ensure_ascii=False, indent=1) + "\n"
            )
            destination = out / evidence_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(evidence_body, encoding="utf-8")
            neutral_evidence_paths[doc["id"]] = evidence_path
            written["evidence"] += 1
            written["bytes"] += len(evidence_body.encode())
        for language, layer in glosses.items():
            localized = language_artifact(
                doc,
                layer,
                language_citations[language],
                translation_relationships[language],
                projection,
            )
            directory = out / "languages" / language / "texts" / category
            directory.mkdir(parents=True, exist_ok=True)
            body = _artifact_json(localized)
            (directory / f"{slug}.json").write_text(body, encoding="utf-8")
            written["language_texts"] += 1
            written["bytes"] += len(body.encode())
            if doc["id"] in localized_evidence[language]:
                evidence_path = f"languages/{language}/bibliography/texts/{category}/{slug}.json"
                evidence_body = (
                    json.dumps(
                        localized_evidence[language][doc["id"]],
                        ensure_ascii=False,
                        indent=1,
                    )
                    + "\n"
                )
                destination = out / evidence_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(evidence_body, encoding="utf-8")
                localized_evidence_paths[language][doc["id"]] = evidence_path
                written["evidence"] += 1
                written["bytes"] += len(evidence_body.encode())

    # The three tables are written LAST because interning fills them as texts
    # are emitted, and a table written first would be the previous run's.
    (out / "tables").mkdir(parents=True, exist_ok=True)
    outputs = (
        ("tables/morphology.json", _record_array(parses.edition())),
        ("tables/analysis.json", _record_array(analyses.edition())),
        ("tables/citations.json", _record_array(shared_citations.edition())),
        ("concordance.json", _concordance_json(index(corpus_docs, text_registry))),
        (
            "lexicon/heads.json",
            _entries_json(lexicon_slice(corpus, projection=projection)),
        ),
        ("calendar.json", _calendar_json(kalendarium())),
        (
            "normalization.json",
            json.dumps(NORMALIZATION_VECTORS, ensure_ascii=False, indent=1) + "\n",
        ),
        (
            "formularies.json",
            json.dumps(formulary_catalog(corpus), ensure_ascii=False, indent=1) + "\n",
        ),
        (
            "metrics.json",
            json.dumps(corpus_metrics(corpus, corpus_docs), ensure_ascii=False, indent=1) + "\n",
        ),
        (
            "bibliography/catalog.json",
            json.dumps(
                bibliography.public_catalog(evidence_graph),
                ensure_ascii=False,
                indent=1,
            )
            + "\n",
        ),
        (
            "bibliography/index.json",
            json.dumps(bibliography.public_index(evidence_graph), ensure_ascii=False, indent=1)
            + "\n",
        ),
    )
    for name, body in outputs:
        (out / name).parent.mkdir(parents=True, exist_ok=True)
        (out / name).write_text(body, encoding="utf-8")
        written["bytes"] += len(body.encode())
    written["formularies"] = len(store.formularies(corpus))

    language_manifests = []
    for language in languages:
        source_manifest = store.language_manifest(corpus, language)
        covered = set(source_manifest["texts"])
        localized_outputs = (
            (
                f"languages/{language}/citations.json",
                _record_array(language_citations[language].edition()),
            ),
            (
                f"languages/{language}/lexicon.json",
                _entries_json(lexicon_slice(corpus, language, projection=projection)),
            ),
            (
                f"languages/{language}/concordance.json",
                _language_concordance_json(language_index(corpus_docs, language, text_registry)),
            ),
            (
                f"languages/{language}/formularies.json",
                json.dumps(
                    language_formulary_catalog(corpus, language),
                    ensure_ascii=False,
                    indent=1,
                )
                + "\n",
            ),
            (
                f"languages/{language}/bibliography/catalog.json",
                json.dumps(
                    bibliography.public_catalog_delta(evidence_graph, language_evidence[language]),
                    ensure_ascii=False,
                    indent=1,
                )
                + "\n",
            ),
            (
                f"languages/{language}/bibliography/index.json",
                json.dumps(
                    bibliography.public_index(evidence_graph, language_evidence[language]),
                    ensure_ascii=False,
                    indent=1,
                )
                + "\n",
            ),
        )
        for name, body in localized_outputs:
            (out / name).parent.mkdir(parents=True, exist_ok=True)
            (out / name).write_text(body, encoding="utf-8")
            written["bytes"] += len(body.encode())
        language_manifest = {
            "schema_version": SCHEMA,
            "corpus_schema": corpus_docs[0][0]["schema_version"],
            "language": language,
            "direction": source_manifest["direction"],
            "texts": [],
            "lexicon": f"languages/{language}/lexicon.json",
            "citations": f"languages/{language}/citations.json",
            "concordance": f"languages/{language}/concordance.json",
            "formularies": f"languages/{language}/formularies.json",
            "bibliography": {
                "catalog": f"languages/{language}/bibliography/catalog.json",
                "index": f"languages/{language}/bibliography/index.json",
            },
        }
        title_metadata = source_manifest.get("titles") or {}
        for doc, _ in corpus_docs:
            if doc["id"] not in covered:
                continue
            entry = {
                "id": doc["id"],
                "path": f"languages/{language}/texts/{doc['id'].replace('.', '/', 1)}.json",
            }
            if doc["id"] in localized_evidence_paths[language]:
                entry["evidence"] = localized_evidence_paths[language][doc["id"]]
            entry.update(title_metadata.get(doc["id"]) or {})
            language_manifest["texts"].append(entry)
        language_manifest_path = f"languages/{language}/manifest.json"
        body = json.dumps(language_manifest, ensure_ascii=False, indent=2) + "\n"
        (out / language_manifest_path).write_text(body, encoding="utf-8")
        written["bytes"] += len(body.encode())
        language_manifests.append(
            {
                "id": language,
                "direction": source_manifest["direction"],
                "path": language_manifest_path,
            }
        )

    manifest = {
        "schema_version": SCHEMA,
        "corpus_schema": corpus_docs[0][0]["schema_version"],
        "texts": [
            {
                "id": doc["id"],
                "path": f"texts/{doc['id'].replace('.', '/', 1)}.json",
                "title": doc["title"],
                **(
                    {"evidence": neutral_evidence_paths[doc["id"]]}
                    if doc["id"] in neutral_evidence_paths
                    else {}
                ),
            }
            for doc, _ in corpus_docs
        ],
        "languages": language_manifests,
        "bibliography": {
            "catalog": "bibliography/catalog.json",
            "index": "bibliography/index.json",
        },
        "base": {
            "concordance": "concordance.json",
            "calendar": "calendar.json",
            "lexicon": "lexicon/heads.json",
            "morphology": "tables/morphology.json",
            "analysis": "tables/analysis.json",
            "citations": "tables/citations.json",
            "normalization": "normalization.json",
            "formularies": "formularies.json",
            "metrics": "metrics.json",
        },
        "morphology": len(parses.order),
        "kalendarium": [KALENDARIUM.start, KALENDARIUM.stop - 1],
        "analyses": len(analyses.order),
        "citations": len(shared_citations.order),
        "bibliography_schema": bibliography.SCHEMA,
    }
    body = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    (out / "manifest.json").write_text(body, encoding="utf-8")
    written["bytes"] += len(body.encode())
    if projection_errors := projection.errors():
        raise ValueError("invalid reader citation projection: " + "; ".join(projection_errors))
    written["citation_projection"] = projection.counts()
    written["evidence_coverage"] = bibliography.evidence_coverage(
        corpus, evidence_graph, language_evidence
    )
    return written


def _project_glosses(
    doc: dict,
    glosses: dict[str, dict],
    projection: bibliography.ReaderCitationProjection,
) -> dict[str, dict]:
    """Apply the exact attachment decisions to the checking view."""
    projected = copy.deepcopy(glosses)
    neutral_path = f"texts/{doc['id'].replace('.', '/', 1)}.json"
    for language, layer in projected.items():
        fields: list[tuple[dict, str, tuple[str, ...], str]] = []
        fields.append((layer, "about_citations", ("localization", "about_citations"), neutral_path))
        for segment_id, segment in (layer.get("segments") or {}).items():
            fields.append(
                (
                    segment,
                    "narrative_citations",
                    ("localization", "narrative_citations", segment_id),
                    neutral_path,
                )
            )
            fields.append(
                (
                    segment,
                    "translation_citations",
                    ("segments", segment_id, "translation_citations"),
                    f"languages/{language}/texts/{doc['id'].replace('.', '/', 1)}.json",
                )
            )
        for word_id, word in (layer.get("words") or {}).items():
            fields.append(
                (
                    word,
                    "explanation_citations",
                    ("localization", "explanations", word_id, "citations"),
                    neutral_path,
                )
            )
        for container, field, parts, relative_path in fields:
            cited = container.get(field)
            if not cited:
                continue
            kept = projection.citations(relative_path, parts, cited)
            if kept:
                container[field] = kept
            else:
                container.pop(field, None)
    return projected


def _strip(doc: dict, glosses: dict) -> tuple[dict, dict]:
    """The corpus documents with the declared drops taken out.

    What is left is what the edition promises to carry, and `verify` compares
    the whole of it rather than a list of remembered fields.
    """
    kept_doc = {k: v for k, v in doc.items() if k not in DROP_DOC}
    kept_glosses = {
        lang: {k: v for k, v in layer.items() if k != "schema_version"}
        for lang, layer in glosses.items()
    }
    return kept_doc, kept_glosses


def verify(corpus: Path, out: Path) -> list[str]:
    """Read the edition back and hold it against the corpus it came from.

    Whole documents, not chosen fields. A compression nobody checks is a
    second, quieter edition of the same book -- and a compression checked
    field by field is one that stays honest only about the fields somebody
    thought to list. `expand` reverses the emitter and the result must equal
    what the corpus stores, minus what DROP_DOC says is left behind.
    """
    errors: list[str] = []
    parses = json.loads((out / "tables/morphology.json").read_text(encoding="utf-8"))
    analyses = json.loads((out / "tables/analysis.json").read_text(encoding="utf-8"))
    shared_citations = json.loads((out / "tables/citations.json").read_text(encoding="utf-8"))
    relationships = {
        language: store.translation_relationships(corpus, language)
        for language in store.language_ids(corpus)
    }
    evidence_graph, language_evidence = bibliography.load(corpus)
    projection = bibliography.ReaderCitationProjection(corpus, evidence_graph, language_evidence)
    for doc, glosses in read_corpus(corpus):
        path = out / "texts" / Path(*doc["id"].split(".")).with_suffix(".json")
        if not path.exists():
            errors.append(f"{doc['id']}: no artifact was written")
            continue
        artifact = json.loads(path.read_text(encoding="utf-8"))
        want_doc, want_glosses = _strip(doc, _project_glosses(doc, glosses, projection))
        # `ids` is a declared drop, so the whole-document comparison cannot
        # see the retirement maps; hold emitted `rs` and `rw` against the mint
        # directly, in both directions.
        want_retired = ((doc.get("ids") or {}).get("segments") or {}).get("retired") or {}
        if (artifact.get("rs") or {}) != want_retired:
            errors.append(
                f"{doc['id']}: retired segments differ — the corpus retires "
                f"{sorted(want_retired)} and the edition carries "
                f"{sorted(artifact.get('rs') or {})}"
            )
        want_retired_words = (doc.get("ids") or {}).get("retired") or {}
        if (artifact.get("rw") or {}) != want_retired_words:
            errors.append(
                f"{doc['id']}: retired words differ — the corpus retires "
                f"{sorted(want_retired_words)} and the edition carries "
                f"{sorted(artifact.get('rw') or {})}"
            )
        checked_doc = False
        for lang in sorted(glosses):
            language_path = (
                out
                / "languages"
                / lang
                / "texts"
                / Path(*doc["id"].split(".")).with_suffix(".json")
            )
            if not language_path.exists():
                errors.append(f"{doc['id']}:{lang}: no language artifact was written")
                continue
            language_art = json.loads(language_path.read_text(encoding="utf-8"))
            for row in language_art["seg"]:
                site = f"{doc['id']}.{row['id']}.{lang}"
                if row.get("tb") != relationships[lang].get(site):
                    errors.append(f"{site}: translation relationship was lost or changed")
            language_citations = json.loads(
                (out / "languages" / lang / "citations.json").read_text(encoding="utf-8")
            )
            got_doc, got_gloss = expand(
                artifact,
                language_art,
                parses,
                analyses,
                shared_citations,
                language_citations,
            )
            if not checked_doc and got_doc != want_doc:
                errors.append(f"{doc['id']}: {_first_difference(want_doc, got_doc, 'text')}")
            checked_doc = True
            if got_gloss != want_glosses[lang]:
                errors.append(
                    f"{doc['id']}: {_first_difference(want_glosses[lang], got_gloss, lang)}"
                )
    errors += verify_edition_artifacts(corpus, out, evidence_graph, projection)
    errors += projection.errors()
    return errors


def verify_edition_artifacts(
    corpus: Path,
    out: Path,
    evidence_graph: dict,
    projection: bibliography.ReaderCitationProjection,
) -> list[str]:
    """The artifacts the round-trip cannot see, held to their own contracts.

    The per-text expansion above proves the documents; it proves nothing
    about the concordances, the calendar, the lexicons, the vectors, or the
    manifest's own claims — an edition shipping empty indexes still expanded
    every text perfectly. Fault injection showed exactly that, so each
    artifact class is verified here: every posting resolves to the word or
    term it claims, every declared path exists, nothing undeclared ships,
    the neutral lexicon exactly covers the Latin words, each localized
    lexicon covers its package (and may grow ahead), and every declared
    calendar year is present and non-empty.
    """
    errors: list[str] = []
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))

    declared: set[str] = {"manifest.json"}
    declared.update(manifest["base"].values())
    declared.update(manifest["bibliography"].values())
    declared.update(entry["path"] for entry in manifest["texts"])
    declared.update(entry["evidence"] for entry in manifest["texts"] if "evidence" in entry)
    for language in manifest["languages"]:
        declared.add(language["path"])
        language_manifest = json.loads((out / language["path"]).read_text(encoding="utf-8"))
        declared.update(
            language_manifest[key] for key in ("lexicon", "citations", "concordance", "formularies")
        )
        declared.update(language_manifest["bibliography"].values())
        declared.update(entry["path"] for entry in language_manifest["texts"])
        declared.update(
            entry["evidence"] for entry in language_manifest["texts"] if "evidence" in entry
        )
    for name in sorted(declared):
        if not (out / name).is_file():
            errors.append(f"manifest: {name} is declared and not written")
    present = {str(p.relative_to(out)) for p in out.rglob("*.json")}
    for name in sorted(present - declared):
        errors.append(f"manifest: {name} was written and no manifest declares it")
    if errors:
        return errors  # unresolvable paths would only cascade below

    corpus_docs = read_corpus(corpus)
    texts_by_number: list[dict] = []
    words_by_text: list[dict[str, dict]] = []
    registry = json.loads((REGISTRY / "texts.json").read_text(encoding="utf-8"))
    by_id = {entry["id"]: entry for entry in manifest["texts"]}
    for text_id in registry:
        entry = by_id.get(text_id)
        artifact = (
            json.loads((out / entry["path"]).read_text(encoding="utf-8")) if entry else {"seg": []}
        )
        texts_by_number.append(artifact)
        words_by_text.append(
            {
                row["id"]: {
                    cell["i"]: (position, cell) for position, cell in enumerate(row.get("w") or [])
                }
                for row in artifact["seg"]
            }
        )

    concordance = json.loads((out / manifest["base"]["concordance"]).read_text(encoding="utf-8"))
    expected_concordance = index(corpus_docs, registry)
    if concordance != expected_concordance:
        errors.append(
            "concordance: " + _first_difference(expected_concordance, concordance, "emitted index")
        )
    if concordance["texts"] != registry:
        errors.append("concordance: its text table is not the registry — every posting shifts")
    if not concordance["latin"]["forms"] or not concordance["latin"]["lemmata"]:
        errors.append("concordance: the Latin index is empty — nothing is findable")
    for kind, wanted in (("forms", "f"), ("lemmata", "l")):
        for key, postings in concordance["latin"][kind].items():
            for number, sid, wid, position in postings:
                located = words_by_text[number].get(sid, {}).get(wid)
                if located is None:
                    errors.append(
                        f"concordance: {kind}[{key}] points at a missing word "
                        f"{concordance['texts'][number]}.{sid}.{wid}"
                    )
                    continue
                where, cell = located
                value = normalize_latin(cell[wanted]) if kind == "forms" else cell[wanted]
                if value != key or where != position:
                    errors.append(
                        f"concordance: {kind}[{key}] disagrees with "
                        f"{concordance['texts'][number]}.{sid}.{wid}"
                    )

    for language in manifest["languages"]:
        language_manifest = json.loads((out / language["path"]).read_text(encoding="utf-8"))
        localized = json.loads((out / language_manifest["concordance"]).read_text(encoding="utf-8"))
        expected_localized = language_index(corpus_docs, language["id"], registry)
        if localized != expected_localized:
            errors.append(
                f"{language['id']}: "
                + _first_difference(
                    expected_localized,
                    localized,
                    "emitted translation index",
                )
            )
        if not localized["terms"]:
            errors.append(f"{language['id']}: the translation index is empty")
        segments_by_number: list[dict[str, list[str]]] = []
        for text_id in registry:
            entry = next((e for e in language_manifest["texts"] if e["id"] == text_id), None)
            if entry is None:
                segments_by_number.append({})
                continue
            artifact = json.loads((out / entry["path"]).read_text(encoding="utf-8"))
            segments_by_number.append(
                {row["id"]: tokenize_search(row["tr"]) for row in artifact["seg"] if "tr" in row}
            )
        for term, postings in localized["terms"].items():
            for number, sid, position in postings:
                tokens = segments_by_number[number].get(sid)
                if tokens is None or position >= len(tokens) or tokens[position] != term:
                    errors.append(
                        f"{language['id']}: terms[{term}] disagrees with "
                        f"{localized['texts'][number]}.{sid}[{position}]"
                    )

    lemmata_in_use = {
        cell["l"]
        for text in texts_by_number
        for row in text["seg"]
        for cell in (row.get("w") or [])
    }
    heads = json.loads((out / manifest["base"]["lexicon"]).read_text(encoding="utf-8"))["entries"]
    expected_heads = lexicon_slice(corpus, projection=projection)
    if heads != expected_heads:
        errors.append("lexicon: " + _first_difference(expected_heads, heads, "emitted heads"))
    if set(heads) != lemmata_in_use:
        missing = sorted(lemmata_in_use - set(heads))[:3]
        dead = sorted(set(heads) - lemmata_in_use)[:3]
        errors.append(f"lexicon: heads and the words disagree — missing {missing}, unused {dead}")
    for language in manifest["languages"]:
        language_manifest = json.loads((out / language["path"]).read_text(encoding="utf-8"))
        entries = json.loads((out / language_manifest["lexicon"]).read_text(encoding="utf-8"))[
            "entries"
        ]
        expected_entries = lexicon_slice(corpus, language["id"], projection=projection)
        if entries != expected_entries:
            errors.append(
                f"{language['id']}: "
                + _first_difference(
                    expected_entries,
                    entries,
                    "emitted localized lexicon",
                )
            )
        covered_texts = {entry["id"] for entry in language_manifest["texts"]}
        missing_lemmas, unknown_lemmas = language_lexicon_differences(
            corpus_docs, covered_texts, entries, heads
        )
        if missing_lemmas:
            errors.append(
                f"{language['id']}: localized lexicon misses covered lemmas "
                f"{sorted(missing_lemmas)[:3]}"
            )
        if unknown_lemmas:
            errors.append(
                f"{language['id']}: localized lexicon has unknown lemmas "
                f"{sorted(unknown_lemmas)[:3]}"
            )

    calendar = json.loads((out / manifest["base"]["calendar"]).read_text(encoding="utf-8"))
    expected_calendar = kalendarium()
    if calendar != expected_calendar:
        errors.append(
            "calendar: " + _first_difference(expected_calendar, calendar, "emitted calendar")
        )
    first, last = manifest["kalendarium"]
    for year in range(first, last + 1):
        if not calendar.get("years", {}).get(str(year)):
            errors.append(f"calendar: declared year {year} is missing or empty")

    formularies = json.loads((out / manifest["base"]["formularies"]).read_text(encoding="utf-8"))
    expected_formularies = formulary_catalog(corpus)
    if formularies != expected_formularies:
        errors.append(
            "formularies: "
            + _first_difference(expected_formularies, formularies, "emitted assemblies")
        )
    if not formularies["formularies"]:
        errors.append("formularies: the assembly catalogue is empty")
    for language in manifest["languages"]:
        language_manifest = json.loads((out / language["path"]).read_text(encoding="utf-8"))
        localized = json.loads((out / language_manifest["formularies"]).read_text(encoding="utf-8"))
        expected_localized = language_formulary_catalog(corpus, language["id"])
        if localized != expected_localized:
            errors.append(
                f"{language['id']} formularies: "
                + _first_difference(
                    expected_localized,
                    localized,
                    "emitted localized assemblies",
                )
            )

    metrics = json.loads((out / manifest["base"]["metrics"]).read_text(encoding="utf-8"))
    expected_metrics = corpus_metrics(corpus, corpus_docs)
    if metrics != expected_metrics:
        errors.append("metrics: " + _first_difference(expected_metrics, metrics, "emitted metrics"))

    vectors = json.loads((out / manifest["base"]["normalization"]).read_text(encoding="utf-8"))
    if vectors != NORMALIZATION_VECTORS:
        errors.append("normalization: the emitted vectors are not the authored vectors")

    _, language_evidence = bibliography.load(corpus)
    expected_catalog = bibliography.public_catalog(evidence_graph)
    catalog = json.loads((out / manifest["bibliography"]["catalog"]).read_text(encoding="utf-8"))
    if catalog != expected_catalog:
        errors.append(
            "bibliography catalog: "
            + _first_difference(expected_catalog, catalog, "emitted catalog")
        )
    expected_index = bibliography.public_index(evidence_graph)
    index_artifact = json.loads(
        (out / manifest["bibliography"]["index"]).read_text(encoding="utf-8")
    )
    if index_artifact != expected_index:
        errors.append(
            "bibliography index: "
            + _first_difference(expected_index, index_artifact, "emitted index")
        )
    expected_texts = {
        record["id"]: record
        for record in bibliography.public_text_evidence(evidence_graph)["texts"]
    }
    declared_texts = {
        entry["id"]: entry["evidence"] for entry in manifest["texts"] if "evidence" in entry
    }
    if set(declared_texts) != set(expected_texts):
        errors.append(
            "text evidence: manifest coverage differs — "
            f"missing={sorted(set(expected_texts) - set(declared_texts))} "
            f"extra={sorted(set(declared_texts) - set(expected_texts))}"
        )
    for text_id, path in declared_texts.items():
        text_evidence = json.loads((out / path).read_text(encoding="utf-8"))
        if text_evidence != expected_texts[text_id]:
            errors.append(
                "text evidence: "
                + _first_difference(
                    expected_texts[text_id], text_evidence, f"emitted evidence.{text_id}"
                )
            )
    for language in manifest["languages"]:
        language_manifest = json.loads((out / language["path"]).read_text(encoding="utf-8"))
        expected_language_catalog = bibliography.public_catalog_delta(
            evidence_graph, language_evidence[language["id"]]
        )
        language_catalog = json.loads(
            (out / language_manifest["bibliography"]["catalog"]).read_text(encoding="utf-8")
        )
        if language_catalog != expected_language_catalog:
            errors.append(
                f"{language['id']} bibliography catalog: "
                + _first_difference(
                    expected_language_catalog,
                    language_catalog,
                    "emitted language bibliography catalog",
                )
            )
        expected_language_index = bibliography.public_index(
            evidence_graph, language_evidence[language["id"]]
        )
        language_index_artifact = json.loads(
            (out / language_manifest["bibliography"]["index"]).read_text(encoding="utf-8")
        )
        if language_index_artifact != expected_language_index:
            errors.append(
                f"{language['id']} bibliography index: "
                + _first_difference(
                    expected_language_index,
                    language_index_artifact,
                    "emitted language bibliography index",
                )
            )
        expected_language_texts = {
            record["id"]: record
            for record in bibliography.public_text_evidence(
                evidence_graph, language_evidence[language["id"]]
            )["texts"]
        }
        declared_language_texts = {
            entry["id"]: entry["evidence"]
            for entry in language_manifest["texts"]
            if "evidence" in entry
        }
        if set(declared_language_texts) != set(expected_language_texts):
            errors.append(
                f"{language['id']} text evidence: manifest coverage differs — "
                f"missing={sorted(set(expected_language_texts) - set(declared_language_texts))} "
                f"extra={sorted(set(declared_language_texts) - set(expected_language_texts))}"
            )
        for text_id, path in declared_language_texts.items():
            text_evidence = json.loads((out / path).read_text(encoding="utf-8"))
            if text_evidence != expected_language_texts[text_id]:
                errors.append(
                    f"{language['id']} text evidence: "
                    + _first_difference(
                        expected_language_texts[text_id],
                        text_evidence,
                        f"emitted language evidence.{text_id}",
                    )
                )
    return errors


def _first_difference(want: object, got: object, where: str) -> str:
    """Name the first place two structures part company, not merely that they do."""
    if isinstance(want, dict) and isinstance(got, dict):
        for key in sorted(set(want) | set(got)):
            if key not in want:
                return f"{where}.{key} was added by the edition"
            if key not in got:
                return f"{where}.{key} is missing from the edition"
            if want[key] != got[key]:
                return _first_difference(want[key], got[key], f"{where}.{key}")
    if isinstance(want, list) and isinstance(got, list):
        if len(want) != len(got):
            return f"{where}: {len(want)} entries became {len(got)}"
        for i, (a, b) in enumerate(zip(want, got, strict=True)):
            if a != b:
                return _first_difference(a, b, f"{where}[{i}]")

    def brief(value: object) -> str:
        return json.dumps(value, ensure_ascii=False)[:80]

    return f"{where}: {brief(want)} != {brief(got)}"

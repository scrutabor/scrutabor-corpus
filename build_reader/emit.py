"""Emit the reader edition. Deterministic, and verified against its source."""

from __future__ import annotations

import json
from pathlib import Path

# The reader edition's OWN version. It moves when this file changes what it
# writes, which is a different event from the corpus changing what it stores —
# the manifest names both, so a consumer can tell the two apart.
SCHEMA = "1.0.0"
LANGS = ("pl", "en")

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
# and withhold the note of it. It is interned instead: 9 shapes carry 499 uses.
DROP_SEGMENT: set[str] = set()
DROP_WORD: set[str] = set()


def _dumps(obj: object) -> str:
    """One way to write JSON, so a rebuild can be compared byte for byte."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=False)


class Table:
    """A corpus-wide table of repeated objects, addressed by index.

    Three layers repeat themselves hard enough to be worth this. 412 distinct
    parses carry 6,143 words and the fifty commonest carry two thirds of them;
    9 distinct analyses carry 499 words and 5 carry 130 segments; 232 distinct
    citations carry 1,327 references. Written out at every site the parse alone
    was 44% of an authored text document -- free in git, free after gzip, and
    not free in a phone's heap or in the bytes a page hands the browser.
    """

    def __init__(self) -> None:
        self.order: list[dict] = []
        self._index: dict[str, int] = {}

    def intern(self, value: dict) -> int:
        key = json.dumps(value, sort_keys=True, separators=(",", ":"))
        if key not in self._index:
            self._index[key] = len(self.order)
            self.order.append(json.loads(key))
        return self._index[key]

    def intern_all(self, values: list[dict]) -> list[int]:
        return [self.intern(v) for v in values]


def read_corpus(corpus: Path) -> list[tuple[dict, dict[str, dict]]]:
    """Every text with its gloss layers, in a stable order.

    One document on disk since 0.14.0. It is split here rather than read three
    ways, so everything below stayed as it was.
    """
    from build_reader import store

    return store.all_texts(corpus)


def text_artifact(
    doc: dict, glosses: dict[str, dict], parses: Table, analyses: Table, citations: Table
) -> dict:
    """One text, both languages, nothing a reader is not shown."""
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

        for lang in LANGS:
            gloss = glosses[lang]
            seg = (gloss.get("segments") or {}).get(segment["id"]) or {}
            for field, short in (("translation", "tr"), ("narrative", "nr")):
                if seg.get(field):
                    row.setdefault(short, {})[lang] = seg[field]
                cites = seg.get(f"{field}_citations")
                if cites:
                    row.setdefault(f"{short[0]}c", {})[lang] = citations.intern_all(cites)
            if words:
                entries = gloss.get("words") or {}
                row.setdefault("g", {})[lang] = [
                    (entries.get(w["id"]) or {}).get("gloss", "") for w in words
                ]
                for field, short in (("function", "fn"), ("note", "nt")):
                    notes = {
                        w["id"]: (entries.get(w["id"]) or {}).get(field)
                        for w in words
                        if (entries.get(w["id"]) or {}).get(field)
                    }
                    if notes:
                        row.setdefault(short, {})[lang] = notes
                cites = {
                    w["id"]: citations.intern_all(cited)
                    for w in words
                    if (cited := (entries.get(w["id"]) or {}).get("function_citations"))
                }
                if cites:
                    row.setdefault("fc", {})[lang] = cites
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
    artifact["about"] = {lang: glosses[lang]["about"] for lang in LANGS}
    about_citations = {
        lang: citations.intern_all(cited)
        for lang in LANGS
        if (cited := glosses[lang].get("about_citations"))
    }
    if about_citations:
        artifact["ac"] = about_citations
    artifact["seg"] = segments
    return artifact


def expand(artifact: dict, parses: list, analyses: list, citations: list) -> tuple[dict, dict]:
    """The artifact read back as the documents the corpus stores.

    The inverse of `text_artifact`, and the whole of `verify`'s method: rather
    than checking field against field -- which tests only the fields somebody
    remembered to list -- the edition is expanded and compared whole. A field
    added to the corpus and forgotten here fails as a difference, not as
    silence. The app carries this same function in TypeScript.
    """
    doc: dict = {}
    layers: dict[str, dict] = {
        lang: {
            "text": artifact["id"],
            "lang": lang,
            "status": artifact["st"],
            "analysis_defaults": analyses[artifact["ad"]],
            "segments": {},
            "words": {},
        }
        for lang in LANGS
    }
    for key, value in artifact.items():
        if key in ("st", "ad", "adw", "about", "ac", "seg"):
            continue
        doc[key] = value
    doc["status"] = artifact["st"]
    doc["analysis_defaults"] = analyses[artifact["ad"]]
    if "adw" in artifact:
        doc["analysis_defaults_words"] = analyses[artifact["adw"]]
    for lang in LANGS:
        layers[lang]["about"] = artifact["about"][lang]
        cited = (artifact.get("ac") or {}).get(lang)
        if cited:
            layers[lang]["about_citations"] = [citations[i] for i in cited]

    segments = []
    for row in artifact["seg"]:
        segment: dict = {}
        for key, value in row.items():
            if key in ("w", "g", "fn", "nt", "fc", "tr", "tc", "nr", "nc", "an"):
                continue
            segment[key] = value
        if "an" in row:
            segment["analysis"] = analyses[row["an"]]
        for lang in LANGS:
            bucket: dict = {}
            for field, short in (("translation", "tr"), ("narrative", "nr")):
                if lang in (row.get(short) or {}):
                    bucket[field] = row[short][lang]
                cited = (row.get(f"{short[0]}c") or {}).get(lang)
                if cited:
                    bucket[f"{field}_citations"] = [citations[i] for i in cited]
            if bucket:
                layers[lang]["segments"][row["id"]] = bucket
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
                for lang in LANGS:
                    entry: dict = {"gloss": row["g"][lang][position]}
                    for field, short in (("function", "fn"), ("note", "nt")):
                        value = ((row.get(short) or {}).get(lang) or {}).get(cell["i"])
                        if value:
                            entry[field] = value
                    cited = ((row.get("fc") or {}).get(lang) or {}).get(cell["i"])
                    if cited:
                        entry["function_citations"] = [citations[i] for i in cited]
                    layers[lang]["words"][cell["i"]] = entry
            segment["words"] = words
        segments.append(segment)
    doc["segments"] = segments
    return doc, layers


def lexicon_slice(corpus: Path, lemmas: set[str] | None = None) -> dict:
    """The dictionary, or the part of it a given set of words reaches for.

    Sliced per text it duplicated: the same hundred common entries appear in
    every text, and the slices came to 52% of the whole edition. So the edition
    ships ONE dictionary, fetched once and kept. Slicing stays available for the
    units that must arrive self-sufficient — a day's proper is picked whole and
    should not need a second request to be read.
    """
    heads = json.loads((corpus / "lexicon/lemmata.json").read_text(encoding="utf-8"))["entries"]
    keep = sorted(lemmas) if lemmas is not None else sorted(heads)
    out: dict = {"h": {}, "s": {}}
    for lang in LANGS:
        entries = json.loads((corpus / f"lexicon/{lang}.json").read_text(encoding="utf-8"))[
            "entries"
        ]
        out["s"][lang] = {k: entries[k] for k in keep if k in entries}
    out["h"] = {k: heads[k] for k in keep if k in heads}
    return out


def index(corpus_docs: list[tuple[dict, dict]]) -> dict:
    """Lemma to its occurrences, and surface form to its lemmas.

    A posting is `[text number, word id]`, which is exactly the compound
    address SCHEMA.md documents and exactly what a link needs. One file,
    queried in plain JavaScript, and it is what a lemma page and a search box
    both want, so neither needs the corpus itself.
    """
    texts = [doc["id"] for doc, _ in corpus_docs]
    postings: dict[str, list[list]] = {}
    forms: dict[str, set[str]] = {}
    for number, (doc, _glosses) in enumerate(corpus_docs):
        for segment in doc["segments"]:
            for word in segment.get("words") or []:
                # The WORD ID, not its position. A posting is what a lemma page
                # turns into a link -- `/app/pl/<text>?w=<id>` -- and a position
                # is not an address: it moves the moment a word is inserted
                # before it, which is the one edit the mint exists to survive.
                # The first draft stored positions and would have produced a
                # concordance that drifted off its own words.
                postings.setdefault(word["lemma"], []).append([number, word["id"]])
                forms.setdefault(word["form"].lower(), set()).add(word["lemma"])
    return {
        "t": texts,
        "l": {k: postings[k] for k in sorted(postings)},
        "f": {k: sorted(forms[k]) for k in sorted(forms)},
    }


# The span the calendar covers. Decision #6 fixed 2026-2100 for the shipped
# table; `temporale.year(n)` builds the year ENDING in n, so the last one has to
# be 2101 for the civil year 2100 to be complete to its final Saturday.
KALENDARIUM = range(2026, 2102)


def kalendarium() -> dict:
    """Every day of the temporal cycle that has a Mass of its own, 2026-2100.

    Explicit rather than derivable: decision #6 says apps never implement
    movable-feast logic, and three readers are coming. A row is
    `[date, formulary, season, class, position]`, the last three as indices
    into the vocabularies beside them, and `position` differs from `formulary`
    only where a feast or n. 18's transfer moved something.
    """
    from kalendarium.temporale import year

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
    return {"f": formularies, "s": seasons, "y": years}


def emit(corpus: Path, out: Path) -> dict[str, int]:
    """Write the whole reader edition. Returns what it wrote."""
    corpus_docs = read_corpus(corpus)
    parses, analyses, citations = Table(), Table(), Table()
    written = {"texts": 0, "bytes": 0}

    (out / "t").mkdir(parents=True, exist_ok=True)
    for doc, glosses in corpus_docs:
        artifact = text_artifact(doc, glosses, parses, analyses, citations)
        body = _dumps(artifact)
        (out / "t" / f"{doc['id']}.json").write_text(body, encoding="utf-8")
        written["texts"] += 1
        written["bytes"] += len(body.encode())

    # The three tables are written LAST because interning fills them as texts
    # are emitted, and a table written first would be the previous run's.
    for name, payload in (
        ("m", parses.order),
        ("a", analyses.order),
        ("c", citations.order),
        ("x", index(corpus_docs)),
        ("lex", lexicon_slice(corpus)),
        ("kal", kalendarium()),
    ):
        body = _dumps(payload)
        (out / f"{name}.json").write_text(body, encoding="utf-8")
        written["bytes"] += len(body.encode())

    manifest = {
        "schema_version": SCHEMA,
        "corpus_schema": corpus_docs[0][0]["schema_version"],
        "texts": [doc["id"] for doc, _ in corpus_docs],
        "langs": list(LANGS),
        "parses": len(parses.order),
        "kalendarium": [KALENDARIUM.start, KALENDARIUM.stop - 1],
        "analyses": len(analyses.order),
        "citations": len(citations.order),
    }
    body = _dumps(manifest)
    (out / "manifest.json").write_text(body, encoding="utf-8")
    written["bytes"] += len(body.encode())
    return written


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
    parses = json.loads((out / "m.json").read_text(encoding="utf-8"))
    analyses = json.loads((out / "a.json").read_text(encoding="utf-8"))
    citations = json.loads((out / "c.json").read_text(encoding="utf-8"))
    for doc, glosses in read_corpus(corpus):
        path = out / "t" / f"{doc['id']}.json"
        if not path.exists():
            errors.append(f"{doc['id']}: no artifact was written")
            continue
        artifact = json.loads(path.read_text(encoding="utf-8"))
        want_doc, want_glosses = _strip(doc, glosses)
        got_doc, got_glosses = expand(artifact, parses, analyses, citations)
        if got_doc != want_doc:
            errors.append(f"{doc['id']}: {_first_difference(want_doc, got_doc, 'text')}")
        for lang in LANGS:
            if got_glosses[lang] != want_glosses[lang]:
                errors.append(
                    f"{doc['id']}: {_first_difference(want_glosses[lang], got_glosses[lang], lang)}"
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

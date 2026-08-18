"""Emit the reader edition. Deterministic, and verified against its source."""

from __future__ import annotations

import json
from pathlib import Path

SCHEMA = "0.13.0"
LANGS = ("pl", "en")

# What a reader never sees, and what therefore never leaves the repository.
DROP_DOC = {
    "schema_version",
    "status",
    "notes",
    "source",
    "analysis_defaults",
    "analysis_defaults_words",
    "ids",
}
DROP_SEGMENT = {"analysis"}
DROP_WORD = {"analysis"}


def _dumps(obj: object) -> str:
    """One way to write JSON, so a rebuild can be compared byte for byte."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=False)


class Parses:
    """The corpus-wide parse table.

    412 distinct parses carry 6,143 words, and the fifty commonest carry two
    thirds of them. Writing the object out at every word is 44% of an authored
    text document — free in git, free after gzip, and not free in a phone's
    heap or in the bytes a page hands the browser.
    """

    def __init__(self) -> None:
        self.order: list[dict] = []
        self._index: dict[str, int] = {}

    def intern(self, morph: dict) -> int:
        key = json.dumps(morph, sort_keys=True, separators=(",", ":"))
        if key not in self._index:
            self._index[key] = len(self.order)
            self.order.append(json.loads(key))
        return self._index[key]


def read_corpus(corpus: Path) -> list[tuple[dict, dict[str, dict]]]:
    """Every text with its gloss layers, in a stable order."""
    out = []
    for path in sorted(corpus.glob("texts/*/*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        glosses = {
            lang: json.loads(
                (corpus / "glosses" / lang / f"{doc['id']}.json").read_text(encoding="utf-8")
            )
            for lang in LANGS
        }
        out.append((doc, glosses))
    return out


def text_artifact(doc: dict, glosses: dict[str, dict], parses: Parses) -> dict:
    """One text, both languages, nothing editorial."""
    segments = []
    for segment in doc["segments"]:
        row: dict = {"id": segment["id"], "type": segment["type"]}
        for key, value in segment.items():
            if key in DROP_SEGMENT or key in ("id", "type", "words"):
                continue
            row[key] = value

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
                cells.append(cell)
            row["w"] = cells

        for lang in LANGS:
            gloss = glosses[lang]
            seg = (gloss.get("segments") or {}).get(segment["id"]) or {}
            if seg.get("translation"):
                row.setdefault("tr", {})[lang] = seg["translation"]
            if seg.get("narrative"):
                row.setdefault("nr", {})[lang] = seg["narrative"]
            if words:
                entries = gloss.get("words") or {}
                row.setdefault("g", {})[lang] = [
                    (entries.get(w["id"]) or {}).get("gloss", "") for w in words
                ]
                notes = {
                    w["id"]: (entries.get(w["id"]) or {}).get("function")
                    for w in words
                    if (entries.get(w["id"]) or {}).get("function")
                }
                if notes:
                    row.setdefault("fn", {})[lang] = notes
        segments.append(row)

    artifact: dict = {"id": doc["id"]}
    for key, value in doc.items():
        if key in DROP_DOC or key in ("id", "segments"):
            continue
        artifact[key] = value
    artifact["about"] = {lang: glosses[lang]["about"] for lang in LANGS}
    artifact["seg"] = segments
    return artifact


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


def emit(corpus: Path, out: Path) -> dict[str, int]:
    """Write the whole reader edition. Returns what it wrote."""
    corpus_docs = read_corpus(corpus)
    parses = Parses()
    written = {"texts": 0, "bytes": 0}

    (out / "t").mkdir(parents=True, exist_ok=True)
    for doc, glosses in corpus_docs:
        artifact = text_artifact(doc, glosses, parses)
        body = _dumps(artifact)
        (out / "t" / f"{doc['id']}.json").write_text(body, encoding="utf-8")
        written["texts"] += 1
        written["bytes"] += len(body.encode())

    # The parse table is written LAST because interning fills it as texts are
    # emitted, and a table written first would be the previous run's.
    for name, payload in (
        ("m", parses.order),
        ("x", index(corpus_docs)),
        ("lex", lexicon_slice(corpus)),
    ):
        body = _dumps(payload)
        (out / f"{name}.json").write_text(body, encoding="utf-8")
        written["bytes"] += len(body.encode())

    manifest = {
        "schema_version": SCHEMA,
        "texts": [doc["id"] for doc, _ in corpus_docs],
        "langs": list(LANGS),
        "parses": len(parses.order),
    }
    body = _dumps(manifest)
    (out / "manifest.json").write_text(body, encoding="utf-8")
    written["bytes"] += len(body.encode())
    return written


def verify(corpus: Path, out: Path) -> list[str]:
    """Read the edition back and hold it against the corpus it came from.

    Word by word, gloss by gloss, translation by translation. A compression
    nobody checks is a second, quieter edition of the same book.
    """
    errors: list[str] = []
    parses = json.loads((out / "m.json").read_text(encoding="utf-8"))
    for doc, glosses in read_corpus(corpus):
        path = out / "t" / f"{doc['id']}.json"
        if not path.exists():
            errors.append(f"{doc['id']}: no artifact was written")
            continue
        art = json.loads(path.read_text(encoding="utf-8"))
        rows = {row["id"]: row for row in art["seg"]}
        for segment in doc["segments"]:
            row = rows.get(segment["id"])
            if row is None:
                errors.append(f"{doc['id']}:{segment['id']}: segment missing from the artifact")
                continue
            words = segment.get("words") or []
            cells = row.get("w") or []
            if len(words) != len(cells):
                errors.append(
                    f"{doc['id']}:{segment['id']}: {len(words)} words became {len(cells)}"
                )
                continue
            for word, cell in zip(words, cells, strict=True):
                if cell["f"] != word["form"] or cell["i"] != word["id"]:
                    errors.append(f"{doc['id']}:{word['id']}: form or id does not match")
                if parses[cell["m"]] != word["morph"]:
                    errors.append(f"{doc['id']}:{word['id']}: the interned parse does not match")
            for lang in LANGS:
                entries = glosses[lang].get("words") or {}
                want = [(entries.get(w["id"]) or {}).get("gloss", "") for w in words]
                got = (row.get("g") or {}).get(lang, [])
                if want != got:
                    errors.append(f"{doc['id']}:{segment['id']}:{lang}: glosses do not match")
                seg = (glosses[lang].get("segments") or {}).get(segment["id"]) or {}
                if seg.get("translation") and (row.get("tr") or {}).get(lang) != seg["translation"]:
                    errors.append(f"{doc['id']}:{segment['id']}:{lang}: translation does not match")
    return errors

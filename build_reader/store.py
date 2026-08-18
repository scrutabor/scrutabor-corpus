"""Reading the corpus, now that a text is one document.

The corpus keeps one document per text: the Latin, both gloss layers and an
editorial block, joined (build_reader/merge.py). Almost nothing that reads the
corpus wants it that way. The checks were written against three documents and
each of them is right about its own job — `check_polish(doc, gloss)` asks a
question about one language and should keep asking it about one language.

So this is the seam. `load()` gives back exactly what those callers have always
received, split out of the joined document in memory. Nothing on disk is split,
and no check had to be rewritten to change what is on disk — which is the only
reason a change this size could land without risking a philological regression.

The checks can migrate to the joined shape one at a time afterwards, or never:
the split is cheap and the seam is honest about what it is.
"""

from __future__ import annotations

import json
from pathlib import Path

from build_reader.merge import split


def text_ids(corpus: Path) -> list[str]:
    return [f"{p.parent.name}.{p.stem}" for p in sorted(corpus.glob("texts/*/*.json"))]


def path_of(corpus: Path, text_id: str) -> Path:
    category, name = text_id.split(".", 1)
    return corpus / "texts" / category / f"{name}.json"


def joined(corpus: Path, text_id: str) -> dict:
    """The document as it is stored."""
    return json.loads(path_of(corpus, text_id).read_text(encoding="utf-8"))


def load(corpus: Path, text_id: str) -> tuple[dict, dict[str, dict]]:
    """The text and its gloss layers, as every check still expects them."""
    return split(joined(corpus, text_id))


def all_texts(corpus: Path) -> list[tuple[dict, dict[str, dict]]]:
    return [load(corpus, text_id) for text_id in text_ids(corpus)]

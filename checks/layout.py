"""The house layout for corpus documents, applied instead of remembered.

A text is read in diffs more often than it is read whole. `json.dumps` with
indent=2 spreads one word over fourteen lines, so a changed accent becomes a
thirty-line hunk and a reviewer stops seeing what changed; the corpus is
therefore written with one WORD to a line, its morph and analysis inline, and
everything else ordinary indent-2 JSON.

That layout was kept by hand, and it had already slipped in three files —
two texts written back by some round-trip, and one carrying an escaped
apostrophe no editor typed. So it is a tool:

    python3 -m checks.layout            # rewrite every text and gloss
    python3 -m checks.layout --check    # fail if any file is not in layout

Formatting is byte-identical to what the corpus already held for 56 of its
59 texts, which is why it could be adopted without rewriting the corpus's
own history of decisions.
"""

import json
import sys
from pathlib import Path

CORPUS = Path(__file__).resolve().parent.parent

# Objects small enough that a reader wants them on the line they belong to
# rather than as a block of their own.
INLINE_KEYS = frozenset({"analysis_defaults", "analysis_defaults_words", "analysis"})

# A gloss document keys its segments and words by id rather than carrying the
# id inside them, so the "one word to a line" rule has to be stated for the
# MAP: every value under these keys goes on the line of its own key.
ENTRY_MAPS = frozenset({"segments", "words"})


def _flat(obj: object) -> str:
    """One line, spaced the way the corpus files are."""
    if isinstance(obj, dict):
        body = ", ".join(f"{json.dumps(k, ensure_ascii=False)}: {_flat(v)}" for k, v in obj.items())
        return "{ " + body + " }"
    if isinstance(obj, list):
        return "[" + ", ".join(_flat(v) for v in obj) + "]"
    return json.dumps(obj, ensure_ascii=False)


def render(obj: object, indent: int = 0, key: str | None = None) -> str:
    pad = " " * indent
    if key in INLINE_KEYS:
        return _flat(obj)
    if isinstance(obj, dict):
        # A WORD goes on one line: that is the whole point of this module.
        if "id" in obj and ("morph" in obj or "form" in obj):
            return _flat(obj)
        inline_values = key in ENTRY_MAPS
        items = [
            f"{pad}  {json.dumps(k, ensure_ascii=False)}: "
            + (_flat(v) if inline_values else render(v, indent + 2, k))
            for k, v in obj.items()
        ]
        return "{\n" + ",\n".join(items) + f"\n{pad}}}"
    if isinstance(obj, list):
        if not obj:
            return "[]"
        if all(not isinstance(v, dict | list) for v in obj):
            return _flat(obj)
        items = [f"{pad}  {render(v, indent + 2)}" for v in obj]
        return "[\n" + ",\n".join(items) + f"\n{pad}]"
    return json.dumps(obj, ensure_ascii=False)


def formatted(doc: object) -> str:
    return render(doc) + "\n"


def documents() -> list[Path]:
    """Every file this layout governs: the texts, and only the texts.

    Until 2026-08-19 this docstring promised the gloss layers and the lexicon
    too, and delivered neither: `glosses/` had not existed since schema 0.14.0
    joined it into the texts, so its glob matched nothing, and `lexicon/` was
    never globbed at all. The lexicon stays outside on purpose rather than by
    accident now — its three files keep ordinary indent-2 throughout, and
    adopting them here would rewrite three sealed, human-read files for no
    reader-visible gain. Witness apparatus files are likewise left alone —
    they are prose in JSON clothing and read better as blocks.
    """
    return sorted((CORPUS / "texts").rglob("*.json"))


def main(argv: list[str]) -> int:
    check = "--check" in argv
    off: list[str] = []
    for path in documents():
        original = path.read_text(encoding="utf-8")
        wanted = formatted(json.loads(original))
        if original == wanted:
            continue
        if check:
            off.append(str(path.relative_to(CORPUS)))
        else:
            path.write_text(wanted, encoding="utf-8")
    if check and off:
        print(f"{len(off)} file(s) not in the house layout — run python3 -m checks.layout:")
        for p in off:
            print(f"   {p}")
        return 1
    n = len(documents())
    print(f"layout OK ({n} files)" if check else f"formatted {n} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

"""One pinned text-only Ordo occurrence with two explicit inline rubrics."""

import hashlib
from copy import deepcopy

from .raw_binding import BindingError, BoundReading, _keys, _space

REVISION = "44667ff518b8ff1439780470828b39714f5306a2"
UPSTREAM = "web/www/missa/Latin/Ordo/Ordo.txt"
ARCHIVE_SHA = "a7f63e8030325b809f74dd4587c649bf8eb45cdd150fc9a2817fe2a1ed6a42e3"
CONTEXT_LINES = tuple(range(53, 62))
READING_LINES = (55, 56, 58)
RUBRICS = (
    (55, 11, 52, "(ei ascendens ad Altare, dicit secreto: )"),
    (58, 51, 78, "(Osculatur Altare in medio)"),
)
DECLARATION = UPSTREAM + " {inline-rubric-occurrence:53-61} (lines 55-56; line 58)"


def resolve_inline(text, headers, identity, binding, snapshot):
    """Bind exact source data only; return no performer or whole-line accessor."""
    if binding["revision"] != REVISION:
        raise BindingError("raw-reading-7 requires the pinned Latin revision")
    _, lines = snapshot._archive(binding["archive"], binding["revision"])
    archive = snapshot._registry["archives"][binding["archive"]]
    if archive["upstream"] != UPSTREAM or archive["sha256"] != ARCHIVE_SHA:
        raise BindingError("raw-reading-7 requires the exact retained Mass Ordo object")
    heading = binding["heading"]
    _keys(heading, {"line", "text"}, "raw-reading-7 heading")
    if type(heading["line"]) is not int or heading != {"line": 3, "text": "# Incipit"}:
        raise BindingError("raw-reading-7 requires the exact enclosing heading")
    if len(lines) < 61 or lines[2] != heading["text"]:
        raise BindingError("raw-reading-7 enclosing heading differs from source")
    context = binding["context"]
    if not isinstance(context, list) or len(context) != len(CONTEXT_LINES):
        raise BindingError("raw-reading-7 requires complete local source context")
    for item, number in zip(context, CONTEXT_LINES, strict=True):
        _keys(item, {"line", "text"}, "raw-reading-7 context")
        if type(item["line"]) is not int or item != {"line": number, "text": lines[number - 1]}:
            raise BindingError("raw-reading-7 context differs from exact physical lines")
    reading = binding["reading"]
    if not isinstance(reading, list) or len(reading) != len(READING_LINES):
        raise BindingError("raw-reading-7 requires exactly the ordered spoken lines")
    for item, number in zip(reading, READING_LINES, strict=True):
        _keys(item, {"line"}, "raw-reading-7 reading")
        if type(item["line"]) is not int or item["line"] != number:
            raise BindingError("raw-reading-7 requires exactly the ordered spoken lines")
    framing = binding["framing"]
    if not isinstance(framing, list) or len(framing) != len(RUBRICS):
        raise BindingError("raw-reading-7 requires exactly the two reviewed inline rubrics")
    for item, (number, start, end, literal) in zip(framing, RUBRICS, strict=True):
        _keys(item, {"line", "start", "end", "text", "kind", "reason"}, "raw-reading-7 framing")
        if (
            any(type(item[key]) is not int for key in ("line", "start", "end"))
            or (item["line"], item["start"], item["end"], item["text"])
            != (number, start, end, literal)
            or item["kind"] != "inline-parenthetical-rubric"
            or not isinstance(item["reason"], str)
            or not item["reason"].strip()
            or lines[number - 1][start:end] != literal
        ):
            raise BindingError("raw-reading-7 framing differs from a reviewed literal rubric")
    pieces = []
    for number in READING_LINES:
        original = lines[number - 1]
        if not original.startswith("v. "):
            raise BindingError("raw-reading-7 spoken line requires its literal v. prefix")
        exclusions = [row for row in framing if row["line"] == number]
        # Fixed reviewed offsets partition the whole original body. No regex strips
        # other parentheses, punctuation, words, branches or controls.
        clean = original
        for row in reversed(exclusions):
            clean = clean[: row["start"]] + clean[row["end"] :]
        pieces.append({"line": number, "raw": original, "text": clean[3:]})
    resolved = _space(" ".join(row["text"] for row in pieces))
    body = _space("\n".join(line for line in text.splitlines() if not line.startswith("#")))
    if headers.get("path") != [DECLARATION]:
        raise BindingError("witness path declarations differ from bound evidence")
    if not body or body != resolved:
        raise BindingError("transcription differs from its exact inline-rubric reading")
    source = {
        "contract": "raw-reading-7",
        "registry_version": snapshot._registry["version"],
        "binding_id": identity,
        "transcription_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "binding": binding,
        "archives": {binding["archive"]: archive},
        "resolved_extraction": {
            "heading": heading,
            "context": context,
            "framing": framing,
            "pieces": pieces,
            "text": resolved,
        },
    }
    return BoundReading((), resolved, deepcopy(source), ())

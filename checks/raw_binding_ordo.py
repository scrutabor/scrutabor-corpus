"""Closed literal Ordo selections, not a renderer or performer authority."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path

from .raw_binding import BindingError, BoundReading, _keys, _space, _unique

REVISION = "44667ff518b8ff1439780470828b39714f5306a2"
ARCHIVE_ID = "missa-ordo-44667ff"
ARCHIVE = {
    "upstream": "web/www/missa/Latin/Ordo/Ordo.txt",
    "revision": REVISION,
    "path": "witnesses/raw/missa-44667ff/Ordo/Ordo.txt",
    "sha256": "a7f63e8030325b809f74dd4587c649bf8eb45cdd150fc9a2817fe2a1ed6a42e3",
}
PROFILE_PATH = Path(__file__).with_name("main_ordo_profiles.json")
PROFILE_SHA256 = "407e16fe159ee95dba2f0724c58121572e5777a01fcb8eb0148fcc321c553940"
PROFILE_FIELDS = {
    "id",
    "text",
    "witness",
    "kind",
    "headings",
    "context",
    "reading",
    "path",
    "word_count",
    "body_sha256",
}
EDIT_FIELDS = {"start", "end", "text", "replacement", "kind", "reason"}
PREFIXES = {"v. ", "v.  ", "v.", "S. ", "M. ", "V. ", "R. ", "O. ", "!!!"}
LAVABO = "ordinarium.lavabo"


def _integer(value, minimum=1):
    if type(value) is not int or value < minimum:
        raise BindingError("raw-reading-10 requires integer coordinates, never booleans")


def _list(value, label, *, empty=False):
    if not isinstance(value, list) or (not empty and not value):
        raise BindingError(f"raw-reading-10 requires a complete {label} list")


def edited_line(raw, edits):
    """Partition one complete original line; apply only its explicit literal edits."""
    if not isinstance(raw, str) or not raw.strip() or "\n" in raw or "\r" in raw:
        raise BindingError("raw-reading-10 requires a complete physical text line")
    _list(edits, "edits", empty=True)
    cursor, pieces = 0, []
    for edit in edits:
        _keys(edit, EDIT_FIELDS, "raw-reading-10 edit")
        start, end = edit["start"], edit["end"]
        _integer(start, 0)
        _integer(end)
        if (
            not cursor <= start < end <= len(raw)
            or not isinstance(edit["text"], str)
            or raw[start:end] != edit["text"]
            or not isinstance(edit["reason"], str)
            or not edit["reason"].strip()
        ):
            raise BindingError("raw-reading-10 edit differs from its exact literal partition")
        literal, replacement, kind = edit["text"], edit["replacement"], edit["kind"]
        valid = False
        if kind == "literal-speaker-or-display-prefix":
            valid = start == 0 and literal in PREFIXES and replacement == ""
        elif kind == "standalone-cross":
            valid = literal == " + " and replacement == " "
        elif kind == "intra-word-cross-join":
            valid = (
                literal == " + "
                and replacement == ""
                and start > 0
                and end < len(raw)
                and raw[start - 1].isalpha()
                and raw[end].isalpha()
            )
        elif kind == "inline-rubric":
            valid = literal.startswith("(") and literal.endswith(")") and replacement == ""
        elif kind == "name-slot-not-selected":
            valid = literal in {"N.p", "N.b", " N. et N.", "N. et N. wait10"} and replacement == ""
        elif kind == "player-directive":
            valid = literal == "wait10" and replacement == ""
        elif kind == "alternative-not-selected":
            valid = literal == "(vel meis)" and replacement == ""
        if not valid:
            raise BindingError("raw-reading-10 unsupported literal framing operation")
        pieces.extend((raw[cursor:start], replacement))
        cursor = end
    pieces.append(raw[cursor:])
    return "".join(pieces)


def validate_profiles(data):
    """Validate typed closed DATA, independently of the authenticated file loader."""
    _keys(data, {"version", "revision", "archive", "profiles"}, "raw-reading-10 table")
    if type(data["version"]) is not int or data["version"] != 1:
        raise BindingError("raw-reading-10 unsupported profile table version")
    if data["revision"] != REVISION or data["archive"] != {"id": ARCHIVE_ID, **ARCHIVE}:
        raise BindingError("raw-reading-10 profile table has a different source identity")
    _list(data["profiles"], "profiles")
    result, witnesses, positions, pieces, edits = {}, set(), 0, 0, 0
    for profile in data["profiles"]:
        _keys(profile, PROFILE_FIELDS, "raw-reading-10 profile")
        text = profile["text"]
        if not isinstance(text, str) or not re.fullmatch(
            r"(?:ordinarium|orationes)\.[a-z0-9-]+", text
        ):
            raise BindingError("raw-reading-10 invalid profile text identity")
        identity = "main-ordo-" + text.replace(".", "-")
        name = "do-missa" if text == "orationes.pater-noster" else "do"
        witness = f"witnesses/{text}/{name}.txt"
        kind = (
            "literal-composite-not-macro-expansion"
            if text == LAVABO
            else "closed-literal-selection"
        )
        if (
            profile["id"] != identity
            or identity in result
            or profile["witness"] != witness
            or witness in witnesses
            or profile["kind"] != kind
        ):
            raise BindingError("raw-reading-10 duplicate or mismatched profile identity")
        _integer(profile["word_count"])
        if not isinstance(profile["body_sha256"], str) or not re.fullmatch(
            r"[0-9a-f]{64}", profile["body_sha256"]
        ):
            raise BindingError("raw-reading-10 invalid body digest")
        _list(profile["headings"], "headings")
        heading_numbers = []
        for heading in profile["headings"]:
            _keys(heading, {"line", "text"}, "raw-reading-10 heading")
            _integer(heading["line"])
            if not isinstance(heading["text"], str) or not heading["text"].startswith("#"):
                raise BindingError("raw-reading-10 requires a literal hash heading")
            heading_numbers.append(heading["line"])
        if heading_numbers != sorted(set(heading_numbers)):
            raise BindingError("raw-reading-10 duplicate or reordered headings")
        _list(profile["context"], "context")
        last = 0
        for block in profile["context"]:
            _keys(block, {"first", "last", "lines"}, "raw-reading-10 context")
            _integer(block["first"])
            _integer(block["last"])
            _list(block["lines"], "context lines")
            if (
                not last < block["first"] <= block["last"]
                or len(block["lines"]) != block["last"] - block["first"] + 1
                or any(
                    not isinstance(line, str) or "\n" in line or "\r" in line
                    for line in block["lines"]
                )
            ):
                raise BindingError("raw-reading-10 incomplete or overlapping context")
            last = block["last"]
        _list(profile["reading"], "reading")
        numbers, output = [], []
        for piece in profile["reading"]:
            _keys(piece, {"line", "raw", "edits"}, "raw-reading-10 reading")
            _integer(piece["line"])
            if not any(b["first"] <= piece["line"] <= b["last"] for b in profile["context"]):
                raise BindingError("raw-reading-10 reading lies outside its complete context")
            output.append(edited_line(piece["raw"], piece["edits"]))
            numbers.append(piece["line"])
            edits += len(piece["edits"])
        expected_order = [183, 22, 23] if text == LAVABO else sorted(numbers)
        if len(set(numbers)) != len(numbers) or numbers != expected_order:
            raise BindingError("raw-reading-10 repeated or reordered literal reading")
        declaration = (
            ARCHIVE["upstream"]
            + " {main-ordo:"
            + identity
            + "; "
            + kind
            + "} ("
            + "; ".join(f"line {number}" for number in numbers)
            + ")"
        )
        body = _space(" ".join(output))
        if (
            profile["path"] != declaration
            or len(body.split()) != profile["word_count"]
            or hashlib.sha256((body + "\n").encode()).hexdigest() != profile["body_sha256"]
        ):
            raise BindingError("raw-reading-10 literal reading or declaration differs")
        result[identity] = profile
        witnesses.add(witness)
        positions += profile["word_count"]
        pieces += len(numbers)
    if (len(result), positions, pieces, edits) != (49, 2199, 119, 195):
        raise BindingError("raw-reading-10 incomplete finite profile inventory")
    return result


def load_profiles():
    """No process-global cache or configurable expected digest."""
    try:
        raw = PROFILE_PATH.read_bytes()
        if hashlib.sha256(raw).hexdigest() != PROFILE_SHA256:
            raise BindingError("raw-reading-10 closed profile table SHA-256 mismatch")
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique)
    except (OSError, UnicodeError, ValueError) as error:
        raise BindingError(f"raw-reading-10 profile table: {error}") from error
    return validate_profiles(data)


def resolve_ordo(text, headers, identity, binding, snapshot) -> BoundReading:
    """Resolve one fixed text-only profile; never expose performer ranges."""
    profiles = load_profiles()
    if (
        binding["revision"] != REVISION
        or binding["profile"] != identity
        or identity not in profiles
        or binding["witness"] != profiles[identity]["witness"]
    ):
        raise BindingError("raw-reading-10 requires its exact profile, witness and revision")
    profile = profiles[identity]
    _, lines = snapshot._archive(ARCHIVE_ID, REVISION)
    archive = snapshot._registry["archives"][ARCHIVE_ID]
    if archive != ARCHIVE:
        raise BindingError("raw-reading-10 requires the complete pinned Mass Ordo object")
    for heading in profile["headings"]:
        number = heading["line"]
        if number > len(lines) or lines[number - 1] != heading["text"]:
            raise BindingError("raw-reading-10 heading differs from its physical source")
    for block in profile["context"]:
        if list(lines[block["first"] - 1 : block["last"]]) != block["lines"]:
            raise BindingError("raw-reading-10 context differs from its complete physical source")
    headings = {h["line"]: h["text"] for h in profile["headings"]}
    pieces = []
    for piece in profile["reading"]:
        number = piece["line"]
        if number > len(lines) or lines[number - 1] != piece["raw"]:
            raise BindingError("raw-reading-10 reading differs from its complete physical source")
        preceding = [n for n in range(1, number + 1) if lines[n - 1].startswith("#")]
        if not preceding or headings.get(preceding[-1]) != lines[preceding[-1] - 1]:
            raise BindingError("raw-reading-10 reading has a different enclosing heading")
        pieces.append({**piece, "text": edited_line(piece["raw"], piece["edits"])})
    reading = _space(" ".join(piece["text"] for piece in pieces))
    body = _space("\n".join(line for line in text.splitlines() if not line.startswith("#")))
    if headers.get("path") != [profile["path"]]:
        raise BindingError("witness path declarations differ from bound evidence")
    if not body or body != reading:
        raise BindingError("transcription differs from its exact closed Ordo reading")
    source = {
        "contract": "raw-reading-10",
        "registry_version": snapshot._registry["version"],
        "binding_id": identity,
        "transcription_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "binding": binding,
        "archives": {ARCHIVE_ID: archive},
        "profile": profile,
        "resolved_extraction": {"kind": profile["kind"], "pieces": pieces, "text": reading},
    }
    return BoundReading((), reading, deepcopy(source), ())

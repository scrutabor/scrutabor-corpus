"""Explicit, checksum-bound source spans without legacy filename inference.

Only witnesses registered here opt in. A reading plan is reviewed source data,
not an interpreter for upstream macros: reference lines are checked separately,
then the complete witness is compared with its ordered textual spans.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

REGISTRY = "witnesses/raw/bindings.json"


class BindingError(ValueError):
    """An explicit source claim cannot be verified; never try legacy fallback."""


@dataclass(frozen=True)
class BoundReading:
    spans: tuple[tuple[Path, int, int], ...]
    text: str


def _keys(value, required: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != required:
        raise BindingError(f"{label}: expected fields {sorted(required)}")


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise BindingError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _path(root: Path, name, prefix: str) -> Path:
    if not isinstance(name, str):
        raise BindingError("path must be a string")
    parts = PurePosixPath(name).parts
    if (
        not name.startswith(prefix + "/")
        or ".." in parts
        or "\\" in name
        or str(PurePosixPath(name)) != name
    ):
        raise BindingError(f"invalid confined path: {name}")
    path = root / name
    boundary = (root / prefix).resolve()
    if not boundary.is_relative_to(root.resolve()) or not path.resolve().is_relative_to(boundary):
        raise BindingError(f"path escapes {prefix}: {name}")
    return path


def _hex(value, length: int) -> bool:
    return isinstance(value, str) and re.fullmatch(rf"[0-9a-f]{{{length}}}", value) is not None


def load_registry(root: Path) -> dict:
    """Validate record identities even if a bound witness/marker was deleted."""
    path = root / REGISTRY
    if not path.exists():
        return {"version": 1, "archives": {}, "bindings": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique)
    except (OSError, UnicodeError, ValueError) as error:
        raise BindingError(f"invalid raw binding registry: {error}") from error
    _keys(data, {"version", "archives", "bindings"}, "registry")
    if type(data["version"]) is not int or data["version"] != 1:
        raise BindingError("unsupported raw binding version")
    if not isinstance(data["archives"], dict) or not isinstance(data["bindings"], dict):
        raise BindingError("archives and bindings must be objects")
    identities, local_paths = set(), set()
    for key, archive in data["archives"].items():
        _keys(archive, {"upstream", "revision", "path", "sha256"}, f"archive {key}")
        upstream = archive["upstream"]
        if (
            not isinstance(upstream, str)
            or not re.fullmatch(r"web/www/(?:missa|horas)/Latin/[A-Za-z0-9_./-]+\.txt", upstream)
            or ".." in PurePosixPath(upstream).parts
        ):
            raise BindingError(f"invalid upstream path: {upstream}")
        if not _hex(archive["revision"], 40) or not _hex(archive["sha256"], 64):
            raise BindingError(f"archive {key}: invalid revision or SHA-256")
        _path(root, archive["path"], "witnesses/raw")
        identity = (upstream, archive["revision"])
        if identity in identities or archive["path"] in local_paths:
            raise BindingError(f"duplicate archive identity or local path: {key}")
        identities.add(identity)
        local_paths.add(archive["path"])
    witnesses = set()
    for key, binding in data["bindings"].items():
        _keys(binding, {"witness", "revision", "evidence", "references", "reading"}, key)
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", key):
            raise BindingError(f"invalid binding ID: {key}")
        witness = _path(root, binding["witness"], "witnesses")
        if witness.is_relative_to(root / "witnesses/raw") or witness.suffix != ".txt":
            raise BindingError(f"not a witness path: {binding['witness']}")
        if not witness.is_file():
            raise BindingError(f"missing bound witness: {binding['witness']}")
        if binding["witness"] in witnesses:
            raise BindingError(f"duplicate witness binding: {binding['witness']}")
        witnesses.add(binding["witness"])
        if not _hex(binding["revision"], 40):
            raise BindingError(f"invalid binding revision: {key}")
        for field in ("evidence", "references", "reading"):
            if not isinstance(binding[field], list) or (
                field != "references" and not binding[field]
            ):
                raise BindingError(
                    f"{key}: {field} must be a {'nonempty ' if field != 'references' else ''}list"
                )
    return data


def _headers(text: str) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    key = None
    for line in text.splitlines():
        if not line.startswith("#"):
            break
        opened = re.match(r"#\s*([\w-]+):\s*(.*)", line)
        if opened:
            key = opened[1]
            values.setdefault(key, []).append(opened[2])
        elif key:
            values[key][-1] += " " + line.lstrip("# ").strip()
    return values


def _space(text: str) -> str:
    return " ".join(text.split())


def resolve_binding(witness: Path, root: Path) -> BoundReading | None:
    """Return a fully checked reading, None for legacy, or fail closed."""
    registry = load_registry(root)
    text = witness.read_text(encoding="utf-8")
    headers = _headers(text)
    markers = headers.get("raw-binding", [])
    relative = witness.relative_to(root).as_posix()
    matches = [key for key, item in registry["bindings"].items() if item["witness"] == relative]
    if not markers and not matches:
        return None
    if len(markers) != 1 or markers != matches:
        raise BindingError("raw-binding marker and registered witness identity disagree")
    binding = registry["bindings"][markers[0]]
    if headers.get("revision") != [binding["revision"]]:
        raise BindingError("witness revision differs from its raw binding")
    archives = registry["archives"]
    loaded: dict[str, tuple[Path, list[str]]] = {}

    def archive(key):
        if not isinstance(key, str) or key not in archives:
            raise BindingError(f"unknown archive: {key}")
        if key not in loaded:
            record = archives[key]
            if record["revision"] != binding["revision"]:
                raise BindingError(f"archive {key}: revision differs from binding")
            path = _path(root, record["path"], "witnesses/raw")
            try:
                data = path.read_bytes()
                lines = data.decode("utf-8").splitlines()
            except (OSError, UnicodeError) as error:
                raise BindingError(f"unreadable archive {key}: {error}") from error
            if hashlib.sha256(data).hexdigest() != record["sha256"]:
                raise BindingError(f"archive {key}: SHA-256 mismatch")
            loaded[key] = (path, lines)
        return loaded[key]

    def bounds(item):
        path, lines = archive(item["archive"])
        first, last = item["first"], item["last"]
        if type(first) is not int or type(last) is not int or not 1 <= first <= last <= len(lines):
            raise BindingError("invalid source line range")
        return path, lines, first, last

    expected_text: Counter = Counter()
    controls = {}
    declarations = []
    for item in binding["evidence"]:
        _keys(item, {"archive", "first", "last", "section", "section_line"}, "evidence")
        _, lines, first, last = bounds(item)
        section_line = item["section_line"]
        if (
            not isinstance(item["section"], str)
            or not item["section"]
            or type(section_line) is not int
            or not 1 <= section_line <= first
            or lines[section_line - 1] != f"[{item['section']}]"
            or any(line.startswith("[") for line in lines[section_line : first - 1])
        ):
            raise BindingError("source section does not match evidence")
        declarations.append(
            f"{archives[item['archive']]['upstream']} [{item['section']}] (lines {first}-{last})"
        )
        for number in range(first, last + 1):
            line = lines[number - 1].strip()
            coordinate = (item["archive"], number)
            if line.startswith(("&", "@")):
                if coordinate in controls:
                    raise BindingError("overlapping reference evidence")
                controls[coordinate] = line
            elif line and not line.startswith(("!", "[", "#", "_")):
                expected_text[coordinate] += 1
            elif line.startswith("[") and number != section_line:
                raise BindingError("evidence crosses a source section boundary")
    if headers.get("path") != ["; ".join(declarations)]:
        raise BindingError("witness path declarations differ from bound evidence")
    if any(count != 1 for count in expected_text.values()):
        raise BindingError("overlapping textual evidence")

    seen = set()
    for reference in binding["references"]:
        _keys(reference, {"archive", "line", "text", "target"}, "reference")
        key, number, target = reference["archive"], reference["line"], reference["target"]
        if not isinstance(key, str) or type(number) is not int or type(target) is not int:
            raise BindingError("invalid reference identity")
        coordinate = (key, number)
        if (
            coordinate in seen
            or coordinate not in controls
            or controls[coordinate] != reference["text"]
        ):
            raise BindingError("reference differs from source evidence")
        seen.add(coordinate)
        if not 0 <= target < len(binding["evidence"]):
            raise BindingError("invalid reference target")
        destination = binding["evidence"][target]
        directive = reference["text"]
        if directive.startswith("&"):
            valid = directive[1:] == destination["section"]
        else:
            origin = next(
                item
                for item in binding["evidence"]
                if item["archive"] == key and item["first"] <= number <= item["last"]
            )
            valid = (
                archives[destination["archive"]]["upstream"].endswith(
                    "/" + directive.removeprefix("@") + ".txt"
                )
                and destination["section"] == origin["section"]
            )
        if not valid:
            raise BindingError("reference points to a different source or section")
    if seen != set(controls):
        raise BindingError("incomplete source reference coverage")

    spans, output = [], []
    actual_text: Counter = Counter()
    for item in binding["reading"]:
        _keys(item, {"archive", "first", "last"}, "reading")
        path, lines, first, last = bounds(item)
        spans.append((path, first, last))
        for number in range(first, last + 1):
            coordinate = (item["archive"], number)
            if coordinate not in expected_text:
                raise BindingError("reading contains framing or lies outside textual evidence")
            actual_text[coordinate] += 1
            output.append(re.sub(r"^[SMVROsmvro]\.\s+", "", lines[number - 1].strip()))
    if actual_text != expected_text:
        raise BindingError("reading omits or repeats source text")
    reading = _space(" ".join(output))
    body = _space("\n".join(line for line in text.splitlines() if not line.startswith("#")))
    if not body or body != reading:
        raise BindingError("transcription differs from its exact ordered raw reading")
    return BoundReading(tuple(spans), reading)

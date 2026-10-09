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
from copy import deepcopy
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath

REGISTRY = "witnesses/raw/bindings.json"


class BindingError(ValueError):
    """An explicit source claim cannot be verified; never try legacy fallback."""


@dataclass(frozen=True)
class RawFragment:
    path: Path
    line: int
    start: int
    end: int
    raw: str
    text: str
    marker: str | None
    whole_line: bool
    partial_contract: bool = False
    binding_id: str | None = None
    marker_scope_verified: bool = True


@dataclass(frozen=True)
class BoundReading:
    spans: tuple[tuple[Path, int, int], ...]
    text: str
    source: dict
    fragments: tuple[RawFragment, ...] = ()


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
    path = _path(root, REGISTRY, "witnesses/raw")
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
        fields = {"witness", "revision", "evidence", "references", "reading"}
        if isinstance(binding, dict) and "contract" in binding:
            fields.add("contract")
            if binding["contract"] != "raw-reading-2":
                raise BindingError("unsupported per-binding contract")
        _keys(binding, fields, key)
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


class RawBindingSnapshot:
    """One validation run's registry and checked archive bytes.

    No process-global path cache: a new run always checks the current files.
    Raw paths may follow symlinks within their existing confinement boundary;
    transcript review has the separate, stricter no-symlink identity rule.
    Returned readings never share mutable objects with this snapshot.
    """

    def __init__(self, root: Path):
        self._root = root
        self._registry = deepcopy(load_registry(root))
        self._bindings = {item["witness"]: key for key, item in self._registry["bindings"].items()}
        self._loaded: dict[str, tuple[Path, tuple[str, ...]]] = {}

    def _archive(self, key: str, revision: str) -> tuple[Path, tuple[str, ...]]:
        archives = self._registry["archives"]
        if not isinstance(key, str) or key not in archives:
            raise BindingError(f"unknown archive: {key}")
        record = archives[key]
        if record["revision"] != revision:
            raise BindingError(f"archive {key}: revision differs from binding")
        if key not in self._loaded:
            path = _path(self._root, record["path"], "witnesses/raw")
            try:
                data = path.read_bytes()
                lines = tuple(data.decode("utf-8").splitlines())
            except (OSError, UnicodeError) as error:
                raise BindingError(f"unreadable archive {key}: {error}") from error
            if hashlib.sha256(data).hexdigest() != record["sha256"]:
                raise BindingError(f"archive {key}: SHA-256 mismatch")
            self._loaded[key] = (path, lines)
        return self._loaded[key]

    def resolve(self, witness: Path) -> BoundReading | None:
        return _resolve_binding(witness, self)


def resolve_binding(witness: Path, root: Path) -> BoundReading | None:
    """Return a fully checked reading, None for legacy, or fail closed."""
    return RawBindingSnapshot(root).resolve(witness)


def _resolve_binding(witness: Path, snapshot: RawBindingSnapshot) -> BoundReading | None:
    registry = snapshot._registry
    text = witness.read_text(encoding="utf-8")
    headers = _headers(text)
    markers = headers.get("raw-binding", [])
    relative = witness.relative_to(snapshot._root).as_posix()
    registered = snapshot._bindings.get(relative)
    matches = [registered] if registered is not None else []
    if not markers and not matches:
        return None
    if len(markers) != 1 or markers != matches:
        raise BindingError("raw-binding marker and registered witness identity disagree")
    binding = registry["bindings"][markers[0]]
    if headers.get("revision") != [binding["revision"]]:
        raise BindingError("witness revision differs from its raw binding")
    archives = registry["archives"]
    used_archives: set[str] = set()
    partial_contract = binding.get("contract") == "raw-reading-2"

    def bounds(item):
        path, lines = snapshot._archive(item["archive"], binding["revision"])
        used_archives.add(item["archive"])
        first, last = item["first"], item["last"]
        if type(first) is not int or type(last) is not int or not 1 <= first <= last <= len(lines):
            raise BindingError("invalid source line range")
        return path, lines, first, last

    def fragments(item, *, evidence):
        fields = {"archive", "first", "last"}
        if evidence:
            fields |= {"section", "section_line"}
        sliced = isinstance(item, dict) and "fragment" in item
        if sliced:
            if not partial_contract:
                raise BindingError("partial fragment requires raw-reading-2")
            fields.add("fragment")
        _keys(item, fields, "evidence" if evidence else "reading")
        path, lines, first, last = bounds(item)
        result = []
        for number in range(first, last + 1):
            line = lines[number - 1]
            prefix = re.match(r"^\s*([SMVROsmvro])\.\s+", line)
            marker = prefix[1] if prefix else None
            start, end = 0, len(line)
            if sliced:
                if first != last:
                    raise BindingError("fragment must name one physical line")
                fragment = item["fragment"]
                _keys(
                    fragment,
                    {"start", "end", "text", "marker", "reason"} if evidence else {"start", "end"},
                    "fragment",
                )
                start, end = fragment["start"], fragment["end"]
                if (
                    type(start) is not int
                    or type(end) is not int
                    or not 0 <= start < end <= len(line)
                ):
                    raise BindingError("invalid fragment coordinates")
                if (start and not line[start - 1].isspace()) or (
                    end < len(line) and not line[end].isspace()
                ):
                    raise BindingError("fragment splits a source token")
                if prefix and start not in (0, prefix.end()) and start < prefix.end():
                    raise BindingError("fragment splits a source marker")
                if prefix and start == 0 and end <= prefix.end():
                    raise BindingError("fragment has no text beyond its source marker")
                # Multiple marker-shaped clauses on one physical line have no
                # established scope model. Do not invent a performer context.
                if evidence and (
                    fragment["text"] != line[start:end]
                    or fragment["marker"] != marker
                    or not isinstance(fragment["reason"], str)
                    or not fragment["reason"].strip()
                ):
                    raise BindingError("fragment text, marker context or boundary reason differs")
            if partial_contract:
                tail = line[prefix.end() :] if prefix else line
                if re.search(r"(?:^|\s)[SMVROsmvro]\.\s+", tail):
                    raise BindingError("ambiguous inline source marker")
            raw = line[start:end]
            body = re.sub(r"^[SMVROsmvro]\.\s+", "", raw.strip()) if start == 0 else raw.strip()
            if sliced and not body:
                raise BindingError("empty textual fragment")
            result.append(
                RawFragment(
                    path,
                    number,
                    start,
                    end,
                    raw,
                    body,
                    marker,
                    not sliced,
                    partial_contract,
                    markers[0],
                    not partial_contract
                    or marker is None
                    or start == 0
                    or (prefix is not None and start == prefix.end()),
                )
            )
        return path, lines, first, last, result

    expected_text: Counter = Counter()
    controls = {}
    declarations = []
    expected_order = []
    for item in binding["evidence"]:
        _, lines, first, last, selected = fragments(item, evidence=True)
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
        extent = f"lines {first}-{last}"
        if "fragment" in item:
            extent = f"line {first}, chars {item['fragment']['start']}:{item['fragment']['end']}"
        declarations.append(
            f"{archives[item['archive']]['upstream']} [{item['section']}] ({extent})"
        )
        for fragment in selected:
            number = fragment.line
            line = lines[number - 1].strip()
            coordinate = (item["archive"], number, fragment.start, fragment.end)
            if line.startswith(("&", "@", "$")):
                if not fragment.whole_line or (item["archive"], number) in controls:
                    raise BindingError("overlapping reference evidence")
                controls[(item["archive"], number)] = line
            elif line and not line.startswith(("!", "[", "#", "_")):
                expected_text[coordinate] += 1
                expected_order.append(coordinate)
            elif line.startswith("[") and number != section_line:
                raise BindingError("evidence crosses a source section boundary")
    if headers.get("path") != ["; ".join(declarations)]:
        raise BindingError("witness path declarations differ from bound evidence")
    if any(count != 1 for count in expected_text.values()):
        raise BindingError("overlapping textual evidence")
    for index, a in enumerate(expected_order):
        if any(
            a[:2] == b[:2] and max(a[2], b[2]) < min(a[3], b[3])
            for b in expected_order[index + 1 :]
        ):
            raise BindingError("overlapping textual fragments")

    seen = set()
    for reference in binding["references"]:
        _keys(reference, {"archive", "line", "text", "target"}, "reference")
        key, number, target = reference["archive"], reference["line"], reference["target"]
        if not isinstance(key, str) or type(number) is not int or type(target) is not int:
            raise BindingError("invalid reference identity")
        reference_coordinate = (key, number)
        if (
            reference_coordinate in seen
            or reference_coordinate not in controls
            or controls[reference_coordinate] != reference["text"]
        ):
            raise BindingError("reference differs from source evidence")
        seen.add(reference_coordinate)
        if not 0 <= target < len(binding["evidence"]):
            raise BindingError("invalid reference target")
        destination = binding["evidence"][target]
        directive = reference["text"]
        # The pinned Mass renderer removes periods before expanding $ and &.
        # Exact directive bytes were checked above and remain in the source record.
        if (
            archives[key]["upstream"].startswith("web/www/missa/")
            and directive.startswith(("$", "&"))
            and not re.search(r"callpopup|rubrics", directive, re.IGNORECASE)
        ):
            directive = directive.replace(".", "")
        if directive.startswith("$"):
            source = archives[key]["upstream"]
            prayer_source = (
                "web/www/missa/Latin/Ordo/Prayers.txt"
                if source.startswith("web/www/missa/")
                else "web/www/horas/Latin/Psalterium/Common/Prayers.txt"
            )
            name = directive[1:]
            valid = (
                not name.startswith(("rubrica ", "Preces "))
                and name == destination["section"]
                and archives[destination["archive"]]["upstream"] == prayer_source
            )
        elif directive.startswith("&"):
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

    spans, output, actual_order = [], [], []
    resolved: list[RawFragment] = []
    actual_text: Counter = Counter()
    for item in binding["reading"]:
        path, lines, first, last, selected = fragments(item, evidence=False)
        if "fragment" not in item:
            spans.append((path, first, last))
        for fragment in selected:
            coordinate = (item["archive"], fragment.line, fragment.start, fragment.end)
            if coordinate not in expected_text:
                raise BindingError("reading contains framing or lies outside textual evidence")
            actual_text[coordinate] += 1
            actual_order.append(coordinate)
            output.append(fragment.text)
            if not fragment.marker_scope_verified and resolved:
                previous = resolved[-1]
                if (
                    previous.marker_scope_verified
                    and previous.path == fragment.path
                    and previous.line == fragment.line
                    and previous.end <= fragment.start
                    and lines[fragment.line - 1][previous.end : fragment.start].isspace()
                ):
                    fragment = replace(fragment, marker_scope_verified=True)
            resolved.append(fragment)
    if actual_text != expected_text:
        raise BindingError("reading omits or repeats source text")
    if partial_contract and actual_order != expected_order:
        raise BindingError("reading reorders textual fragments")
    reading = _space(" ".join(output))
    body = _space("\n".join(line for line in text.splitlines() if not line.startswith("#")))
    if not body or body != reading:
        raise BindingError("transcription differs from its exact ordered raw reading")
    source = {
        "contract": "raw-reading-2" if partial_contract else "raw-reading-1",
        "registry_version": registry["version"],
        "binding_id": markers[0],
        "transcription_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "binding": binding,
        "archives": {key: archives[key] for key in sorted(used_archives)},
    }
    if partial_contract:
        source["resolved_fragments"] = [
            {
                "path": f.path.relative_to(snapshot._root).as_posix(),
                "line": f.line,
                "start": f.start,
                "end": f.end,
                "raw": f.raw,
                "text": f.text,
                "marker": f.marker,
                "whole_line": f.whole_line,
                "marker_scope_verified": f.marker_scope_verified,
            }
            for f in resolved
        ]
    return BoundReading(
        () if partial_contract else tuple(spans), reading, deepcopy(source), tuple(resolved)
    )

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

# Lowercase initials are textual framing, not performer declarations.
TEXT_MARKER_CHARS = "DSMVROsmvro"

# raw-reading-8 closed record shapes; checks.raw_binding_common checks their values.
LITERAL_COMMON_SHAPE = {
    "selection": {"archive", "rank_heading", "rank", "rule_heading", "rule", "absent_heading"},
    "body": {"archive", "heading", "text", "cue"},
    "conclusion": {"archive", "heading", "formula", "amen"},
}
PREFIXED_RECORDS = {"formula", "amen"}


class BindingError(ValueError):
    """An explicit source claim cannot be verified; never try legacy fallback."""


@dataclass(frozen=True)
class RawFraming:
    start: int
    end: int
    text: str
    kind: str
    reason: str


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
    framing: tuple[RawFraming, ...] = ()


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
            or not re.fullmatch(
                r"(?:web/www/(?:missa|horas)|obsolete/missa)/Latin/[A-Za-z0-9_./-]+\.txt",
                upstream,
            )
            or (upstream.startswith("obsolete/") and str(PurePosixPath(upstream)) != upstream)
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
    ordo_profiles = None
    for key, binding in data["bindings"].items():
        fields = {"witness", "revision", "evidence", "references", "reading"}
        if isinstance(binding, dict) and "contract" in binding:
            fields.add("contract")
            if binding["contract"] not in (
                "raw-reading-2",
                "raw-reading-3",
                "raw-reading-4",
                "raw-reading-5",
                "raw-reading-6",
                "raw-reading-7",
                "raw-reading-8",
                "raw-reading-9",
                "raw-reading-10",
            ):
                raise BindingError("unsupported per-binding contract")
            if binding["contract"] == "raw-reading-3":
                fields.add("framing")
                if not isinstance(binding.get("framing"), list) or not binding["framing"]:
                    raise BindingError("raw-reading-3 requires nonempty explicit framing")
        if isinstance(binding, dict) and binding.get("contract") == "raw-reading-6":
            fields = {"witness", "revision", "contract", "template", "variant"}
        if isinstance(binding, dict) and binding.get("contract") == "raw-reading-7":
            fields = {
                "witness",
                "revision",
                "contract",
                "archive",
                "heading",
                "context",
                "reading",
                "framing",
            }
        if isinstance(binding, dict) and binding.get("contract") == "raw-reading-8":
            fields = {
                "witness",
                "revision",
                "contract",
                "profile",
                "selection",
                "body",
                "conclusion",
            }
        if isinstance(binding, dict) and binding.get("contract") == "raw-reading-9":
            fields = {"witness", "revision", "contract", "profile"}
        if isinstance(binding, dict) and binding.get("contract") == "raw-reading-10":
            fields = {"witness", "revision", "contract", "profile"}
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
        if binding.get("contract") == "raw-reading-6":
            _keys(
                binding["template"],
                {"archive", "section", "section_line", "line", "text", "placeholder"},
                "raw-reading-6 template",
            )
            _keys(
                binding["variant"],
                {
                    "archive",
                    "section",
                    "section_line",
                    "line",
                    "text",
                    "key",
                    "selector",
                    "replacement",
                },
                "raw-reading-6 variant",
            )
        if binding.get("contract") == "raw-reading-8":
            if not isinstance(binding["profile"], str):
                raise BindingError("raw-reading-8 profile must be a string")
            for role, shape in LITERAL_COMMON_SHAPE.items():
                _keys(binding[role], shape, f"raw-reading-8 {role}")
                if not isinstance(binding[role]["archive"], str):
                    raise BindingError(f"raw-reading-8 {role}: archive must be a string")
                for name in sorted(shape - {"archive", "absent_heading"}):
                    record = binding[role][name]
                    expected = (
                        {"line", "text", "prefix"} if name in PREFIXED_RECORDS else {"line", "text"}
                    )
                    _keys(record, expected, f"raw-reading-8 {role} {name}")
                    if type(record["line"]) is not int or any(
                        not isinstance(record[field], str) for field in expected - {"line"}
                    ):
                        raise BindingError(
                            "raw-reading-8 records require integer lines and strings"
                        )
            if not isinstance(binding["selection"]["absent_heading"], str):
                raise BindingError("raw-reading-8 selection: absent_heading must be a string")
        if binding.get("contract") == "raw-reading-9" and not isinstance(binding["profile"], str):
            raise BindingError("raw-reading-9 profile must be a string")
        if binding.get("contract") == "raw-reading-10" and not isinstance(binding["profile"], str):
            raise BindingError("raw-reading-10 profile must be a string")
        if binding.get("contract") == "raw-reading-10":
            from .raw_binding_ordo import REVISION as ORDO_REVISION
            from .raw_binding_ordo import load_profiles

            if ordo_profiles is None:
                ordo_profiles = load_profiles()
            profile = ordo_profiles.get(key)
            if (
                profile is None
                or binding["profile"] != key
                or binding["witness"] != profile["witness"]
                or binding["revision"] != ORDO_REVISION
            ):
                raise BindingError(
                    "raw-reading-10 requires its exact profile, witness and revision"
                )
        for field in (
            ()
            if binding.get("contract")
            in {
                "raw-reading-6",
                "raw-reading-7",
                "raw-reading-8",
                "raw-reading-9",
                "raw-reading-10",
            }
            else ("evidence", "references", "reading")
        ):
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


def _whole_v_text(line: str) -> bool:
    """One unframed lowercase-v textual line, not performer evidence."""
    if not line.startswith("v. "):
        return False
    body = line[3:]
    return (
        bool(body.strip())
        and not body.lstrip().startswith(("!", "[", "#", "_", "&", "@", "$"))
        and "~" not in line
        and re.search(r"(?:^|\s)[DSMVROdsmvro]\.\s+", body) is None
    )


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

    def _identity(self, witness: Path, headers: dict) -> tuple[str, dict] | None:
        markers = headers.get("raw-binding", [])
        relative = witness.relative_to(self._root).as_posix()
        registered = self._bindings.get(relative)
        matches = [registered] if registered is not None else []
        if not markers and not matches:
            return None
        if len(markers) != 1 or markers != matches:
            raise BindingError("raw-binding marker and registered witness identity disagree")
        binding = self._registry["bindings"][markers[0]]
        if headers.get("revision") != [binding["revision"]]:
            raise BindingError("witness revision differs from its raw binding")
        return markers[0], binding

    def inspect_contract(self, witness: Path) -> str | None:
        """Check the common identity without resolving a derived body."""
        identity = self._identity(witness, _headers(witness.read_text(encoding="utf-8")))
        return identity[1].get("contract", "raw-reading-1") if identity else None

    def resolve(self, witness: Path) -> BoundReading | None:
        return _resolve_binding(witness, self)


def _preface_variant(
    text: str, headers: dict, identity: str, binding: dict, snapshot: RawBindingSnapshot
) -> BoundReading:
    """One text-only Spiritu template with the Vigil's literal Rule assignment."""
    template, variant = binding["template"], binding["variant"]
    _keys(
        template,
        {"archive", "section", "section_line", "line", "text", "placeholder"},
        "raw-reading-6 template",
    )
    _keys(
        variant,
        {"archive", "section", "section_line", "line", "text", "key", "selector", "replacement"},
        "raw-reading-6 variant",
    )
    if binding["revision"] != "44667ff518b8ff1439780470828b39714f5306a2":
        raise BindingError("raw-reading-6 requires the pinned Latin revision")
    if (
        template["section"] != "Spiritu"
        or variant["section"] != "Rule"
        or any(
            type(item[field]) is not int
            for item in (template, variant)
            for field in ("section_line", "line")
        )
        or (template["section_line"], template["line"]) != (47, 49)
        or (variant["section_line"], variant["line"]) != (7, 11)
    ):
        raise BindingError("raw-reading-6 requires the exact Spiritu and Rule coordinates")
    if (variant["key"], variant["selector"], variant["replacement"], variant["text"]) != (
        "Prefatio",
        "Spiritu",
        "hodierna die",
        "Prefatio=Spiritu=hodierna die;",
    ):
        raise BindingError("raw-reading-6 variant must be the literal Spiritu rule")
    if (
        not isinstance(template["text"], str)
        or not _whole_v_text(template["text"])
        or template["placeholder"] != "* *"
        or template["text"].count("* *") != 1
        or template["text"].count("*") != 2
    ):
        raise BindingError("raw-reading-6 requires one literal * * placeholder in a v. text line")
    if template["archive"] == variant["archive"]:
        raise BindingError("raw-reading-6 requires two distinct archives")
    declarations, contributions, archives = [], {}, {}
    for role, item, upstream in (
        ("template", template, "web/www/missa/Latin/Ordo/Prefationes.txt"),
        ("variant", variant, "web/www/missa/Latin/Tempora/Pasc6-6r.txt"),
    ):
        path, lines = snapshot._archive(item["archive"], binding["revision"])
        record = snapshot._registry["archives"][item["archive"]]
        if record["upstream"] != upstream:
            raise BindingError("raw-reading-6 source role has the wrong upstream path")
        if (
            item["line"] > len(lines)
            or lines[item["section_line"] - 1] != f"[{item['section']}]"
            or any(line.startswith("[") for line in lines[item["section_line"] : item["line"] - 1])
            or lines[item["line"] - 1] != item["text"]
        ):
            raise BindingError(f"raw-reading-6 {role} differs from its exact source line")
        section_end = next(
            (number for number in range(item["line"], len(lines)) if lines[number].startswith("[")),
            len(lines),
        )
        section = lines[item["section_line"] : section_end]
        if role == "template" and [
            line for line in section if line.strip() and not line.startswith("!")
        ] != [item["text"]]:
            raise BindingError("raw-reading-6 requires one complete Spiritu template line")
        if role == "variant" and sum(line.startswith("Prefatio=") for line in section) != 1:
            raise BindingError("raw-reading-6 requires one Prefatio assignment in the Rule section")
        declarations.append(f"{upstream} [{item['section']}] (lines {item['line']}-{item['line']})")
        archives[item["archive"]] = record
        contributions[role] = {
            "path": path.relative_to(snapshot._root).as_posix(),
            "section": item["section"],
            "section_line": item["section_line"],
            "line": item["line"],
            "raw": item["text"],
        }
    if headers.get("path") != ["; ".join(declarations)]:
        raise BindingError("witness path declarations differ from bound evidence")
    reading = _space(template["text"][3:].replace("* *", variant["replacement"], 1))
    body = _space("\n".join(line for line in text.splitlines() if not line.startswith("#")))
    if not body or body != reading:
        raise BindingError("transcription differs from its exact derived preface reading")
    source = {
        "contract": "raw-reading-6",
        "registry_version": snapshot._registry["version"],
        "binding_id": identity,
        "transcription_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "binding": binding,
        "archives": {key: archives[key] for key in sorted(archives)},
        "resolved_composition": {
            **contributions,
            "operation": "replace-one-literal-placeholder",
            "remove_prefix": "v. ",
            "placeholder": "* *",
            "replacement": variant["replacement"],
            "text": reading,
        },
    }
    return BoundReading((), reading, deepcopy(source), ())


def resolve_binding(witness: Path, root: Path) -> BoundReading | None:
    """Return a fully checked reading, None for legacy, or fail closed."""
    return RawBindingSnapshot(root).resolve(witness)


def _resolve_binding(witness: Path, snapshot: RawBindingSnapshot) -> BoundReading | None:
    registry = snapshot._registry
    text = witness.read_text(encoding="utf-8")
    headers = _headers(text)
    identity = snapshot._identity(witness, headers)
    if identity is None:
        return None
    binding_id, binding = identity
    if binding.get("contract") == "raw-reading-6":
        return _preface_variant(text, headers, binding_id, binding, snapshot)
    if binding.get("contract") == "raw-reading-7":
        from .raw_binding_inline import resolve_inline

        return resolve_inline(text, headers, binding_id, binding, snapshot)
    if binding.get("contract") == "raw-reading-8":
        from .raw_binding_common import resolve_literal_common

        return resolve_literal_common(text, headers, binding_id, binding, snapshot)
    if binding.get("contract") == "raw-reading-9":
        from .raw_binding_mass_secrets import resolve_mass_secret

        return resolve_mass_secret(text, headers, binding_id, binding, snapshot)
    if binding.get("contract") == "raw-reading-10":
        from .raw_binding_ordo import resolve_ordo

        return resolve_ordo(text, headers, binding_id, binding, snapshot)
    markers = [binding_id]
    archives = registry["archives"]
    used_archives: set[str] = set()
    framed_contract = binding.get("contract") == "raw-reading-3"
    partial_contract = binding.get("contract") in {"raw-reading-2", "raw-reading-3"}
    boundary_contract = binding.get("contract") == "raw-reading-5"
    hash_contract = binding.get("contract") in {"raw-reading-4", "raw-reading-5"}
    if hash_contract and (binding["references"] or len(binding["evidence"]) != 1):
        raise BindingError(
            f"{binding['contract']} requires one evidence range without runtime references"
        )
    framing = {}
    framing_order = []
    for item in binding.get("framing", []):
        _keys(item, {"archive", "line", "start", "end", "text", "kind", "reason"}, "framing")
        _, lines = snapshot._archive(item["archive"], binding["revision"])
        number, start, end = item["line"], item["start"], item["end"]
        if (
            type(number) is not int
            or not 1 <= number <= len(lines)
            or type(start) is not int
            or type(end) is not int
        ):
            raise BindingError("invalid framing coordinates")
        line = lines[number - 1]
        if (
            not 0 < start < end == len(line)
            or end - start != 1
            or item["text"] != "~"
            or line[start:end] != item["text"]
            or item["kind"] != "terminal-continuation-tilde"
            or not (line[start - 1].isalpha() or line[start - 1] in ",.!?;:")
            or not isinstance(item["reason"], str)
            or not item["reason"].strip()
        ):
            raise BindingError("framing must assert one exact terminal continuation tilde")
        key = (item["archive"], number)
        if key in framing:
            raise BindingError("duplicate framing declaration")
        framing[key] = RawFraming(start, end, item["text"], item["kind"], item["reason"])
        framing_order.append((item["archive"], number, 0, len(line)))

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
            if hash_contract:
                fields |= {"heading", "branch", "context"}
                if boundary_contract:
                    fields.add("preceding_text")
        sliced = isinstance(item, dict) and "fragment" in item
        if sliced:
            if framed_contract:
                raise BindingError("raw-reading-3 framing requires whole physical lines")
            if not partial_contract:
                raise BindingError("partial fragment requires raw-reading-2")
            fields.add("fragment")
        _keys(item, fields, "evidence" if evidence else "reading")
        path, lines, first, last = bounds(item)
        result = []
        for number in range(first, last + 1):
            line = lines[number - 1]
            prefix = re.match(rf"^\s*([{TEXT_MARKER_CHARS}])\.\s+", line)
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
            # Nontext evidence is not a spoken marker context; slices remain strict.
            whole_rubric_evidence = (
                evidence
                and partial_contract
                and not sliced
                and line.startswith("!")
                and not line.startswith(("!*", "!!"))
            )
            if (partial_contract or hash_contract) and not whole_rubric_evidence:
                tail = line[prefix.end() :] if prefix else line
                if re.search(rf"(?:^|\s)[{TEXT_MARKER_CHARS}]\.\s+", tail):
                    raise BindingError("ambiguous inline source marker")
            raw = line[start:end]
            body = (
                re.sub(rf"^[{TEXT_MARKER_CHARS}]\.\s+", "", raw.strip())
                if start == 0
                else raw.strip()
            )
            applied = framing.get((item["archive"], number))
            if applied is not None:
                body = body[:-1]
            if (sliced or applied is not None) and not body:
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
                    (applied,) if applied is not None else (),
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
        if hash_contract:
            # Only the retained Mass Ordo's literal hash-space format is supported.
            # Context is asserted source data, not a claim about performer identity.
            if archives[item["archive"]]["upstream"] != "web/www/missa/Latin/Ordo/Ordo.txt":
                raise BindingError(f"{binding['contract']} supports only the Latin Mass Ordo")
            heading, branch, context = item["heading"], item["branch"], item["context"]
            _keys(heading, {"format", "text"}, "heading")
            _keys(branch, {"line", "text"}, "branch")
            if (
                not isinstance(item["section"], str)
                or re.fullmatch(r"[A-Za-z][A-Za-z0-9 -]*", item["section"]) is None
                or item["section"] != item["section"].strip()
                or heading["format"] != "hash-space"
                or heading["text"] != "# " + item["section"]
                or type(section_line) is not int
                or not 2 <= section_line < first - 1
                or lines[section_line - 1] != heading["text"]
                or type(branch["line"]) is not int
                or branch["line"] != section_line - 1
                or not isinstance(branch["text"], str)
                or re.fullmatch(r"!\*[A-Za-z][A-Za-z0-9&]*", branch["text"]) is None
                or lines[branch["line"] - 1] != branch["text"]
            ):
                raise BindingError("hash heading or adjacent branch differs from source evidence")
            context_end = first
            if boundary_contract:
                preceding = item["preceding_text"]
                _keys(preceding, {"line", "text", "marker"}, "preceding_text")
                if (
                    first != last
                    or type(preceding["line"]) is not int
                    or preceding["line"] != first - 1
                    or not isinstance(preceding["text"], str)
                    or preceding["text"] != lines[first - 2]
                    or preceding["marker"] != "v"
                    or not _whole_v_text(preceding["text"])
                    or not _whole_v_text(lines[first - 1])
                ):
                    raise BindingError("invalid adjacent whole-line spoken-text boundary")
                context_end = first - 1
                if context_end <= section_line + 1:
                    raise BindingError("spoken-text boundary requires a preceding rubric")
            if not isinstance(context, list) or len(context) != context_end - section_line - 1:
                raise BindingError("hash heading requires every intervening rubric line")
            for number, clause in enumerate(context, section_line + 1):
                _keys(clause, {"line", "text"}, "context")
                if (
                    type(clause["line"]) is not int
                    or clause["line"] != number
                    or not isinstance(clause["text"], str)
                    or lines[number - 1] != clause["text"]
                    or not clause["text"].startswith("!")
                    or clause["text"].startswith("!*")
                ):
                    raise BindingError("hash heading context differs from the exact rubric")
            # Hash/bracket headings and runtime branch controls govern boundaries;
            # none may intervene or be selected as (or silently skipped over) text.
            if any(line.startswith(("#", "[", "!*")) for line in lines[section_line:last]):
                raise BindingError("hash evidence crosses a heading or branch boundary")
            if any(
                not line.strip()
                or line.lstrip().startswith(("!", "[", "#", "_", "&", "@", "$"))
                or "~" in line
                for line in lines[first - 1 : last]
            ):
                raise BindingError(f"{binding['contract']} requires unframed whole textual lines")
        elif (
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
        if hash_contract:
            boundary = (
                f"; preceding-text:{item['preceding_text']['line']}" if boundary_contract else ""
            )
            declarations.append(
                f"{archives[item['archive']]['upstream']} "
                f"{{hash-space:{item['section']}@{section_line}; "
                f"branch:{branch['text']}@{branch['line']}{boundary}}} ({extent})"
            )
        else:
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

    if framed_contract:
        if any(coordinate not in expected_text for coordinate in framing_order):
            raise BindingError("framing is not fully selected textual evidence")
        indexes = [expected_order.index(coordinate) for coordinate in framing_order]
        if indexes != sorted(indexes):
            raise BindingError("framing declarations reorder source evidence")

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
            filename, separator, selector = directive.removeprefix("@").partition(":")
            valid = (
                bool(filename)
                and (
                    not separator
                    or (bool(selector) and ":" not in selector and selector == origin["section"])
                )
                and archives[destination["archive"]]["upstream"].endswith("/" + filename + ".txt")
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
            if framed_contract and "~" in fragment.text:
                raise BindingError("reading contains undeclared continuation framing")
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
    if (partial_contract or hash_contract) and actual_order != expected_order:
        raise BindingError("reading reorders textual fragments")
    reading = _space(" ".join(output))
    body = _space("\n".join(line for line in text.splitlines() if not line.startswith("#")))
    if not body or body != reading:
        raise BindingError("transcription differs from its exact ordered raw reading")
    source = {
        "contract": binding.get("contract", "raw-reading-1"),
        "registry_version": registry["version"],
        "binding_id": markers[0],
        "transcription_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "binding": binding,
        "archives": {key: archives[key] for key in sorted(used_archives)},
    }
    if partial_contract or hash_contract:
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
                **(
                    {
                        "framing": [
                            {
                                "start": c.start,
                                "end": c.end,
                                "text": c.text,
                                "kind": c.kind,
                                "reason": c.reason,
                            }
                            for c in f.framing
                        ]
                    }
                    if framed_contract
                    else {}
                ),
            }
            for f in resolved
        ]
    return BoundReading(
        () if partial_contract else tuple(spans), reading, deepcopy(source), tuple(resolved)
    )

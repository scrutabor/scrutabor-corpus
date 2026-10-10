"""Reproducible source identities, distinct from an editorial source review.

Pending evidence still has to identify real, unchanged files. A review binds
the complete claim and its dependencies; recomputing a file checksum alone
cannot preserve a reviewed claim after those dependencies change.
"""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlparse

from checks.apparatus import derived_summary
from checks.raw_binding import RawBindingSnapshot

SEGMENT_FIELDS = ("id", "type", "text", "verse", "speaker", "voice", "delivery", "parentheses")
WORD_FIELDS = ("id", "form", "pre", "post")
NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
TEXT_ID = re.compile(r"[a-z0-9-]+\.[a-z0-9-]+")
IDENTITY = re.compile(r"[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*")
DIGITAL_KINDS = {"scan", "born-digital"}
LATIN_SOURCE_ROLES = {
    "official_text",
    "corroborating_latin_witness",
    "direct_approved_print",
    "derived_digital_collation_aid",
}
SUPPLEMENT_ROLES = LATIN_SOURCE_ROLES | {"official_liturgical_context", "rubric_control"}


class BindingError(ValueError):
    """An evidence subject cannot be identified safely."""


def unique_json_keys(pairs: list[tuple[str, object]]) -> dict:
    """A later duplicate must not silently erase a conflicting source claim."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise BindingError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def digest(value: object) -> str:
    """Canonical JSON, preserving every string and array position."""
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def selected_text(doc: dict) -> dict:
    """The schema1.4 Latin/ritual subject, not its morphological annotation."""
    segments = []
    for segment in doc["segments"]:
        selected = {key: segment[key] for key in SEGMENT_FIELDS if key in segment}
        if "words" in segment:
            selected["words"] = [
                {key: word[key] for key in WORD_FIELDS if key in word} for word in segment["words"]
            ]
        segments.append(selected)
    return {"id": doc["id"], "segments": segments}


def transcript_digest(text: str) -> str:
    """Complete UTF-8 transcript, including headers; normalize only CR/CRLF."""
    return hashlib.sha256(text.replace("\r\n", "\n").replace("\r", "\n").encode()).hexdigest()


def _confined(root: Path, relative: str) -> Path:
    path = root / relative
    if (
        not path.resolve().is_relative_to(root.resolve())
        or path.resolve() != root.resolve() / relative
    ):
        raise BindingError(f"symlink or escaping evidence path: {relative}")
    if not path.is_file():
        raise BindingError(f"missing evidence file: {relative}")
    return path


def _text_id(value: object) -> str:
    if not isinstance(value, str) or not TEXT_ID.fullmatch(value):
        raise BindingError("invalid text identity")
    return value


def _json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_json_keys)
    if not isinstance(value, dict):
        raise BindingError(f"expected a JSON object: {path.name}")
    return value


def text_document(root: Path, text_id: str) -> dict:
    category, slug = _text_id(text_id).split(".", 1)
    doc = _json(_confined(root, f"texts/{category}/{slug}.json"))
    if doc.get("id") != text_id:
        raise BindingError("text file identity differs from its binding")
    return doc


def _headers(text: str, key: str) -> list[str]:
    # Duplicate identity/coverage headers are ambiguous, not last-value-wins.
    return re.findall(rf"^#\s*{key}:\s*([^\r\n]*)", text, flags=re.MULTILINE)


def _coverage(witness: dict, text: str, doc: dict) -> None:
    all_words = [word["id"] for segment in doc["segments"] for word in segment.get("words", [])]
    coverage = witness.get("coverage")
    if not isinstance(coverage, dict):
        raise BindingError("invalid witness coverage")
    kind = coverage.get("kind")
    if kind == "full" and set(coverage) == {"kind"}:
        covered = all_words
    elif kind == "words" and set(coverage) == {"kind", "words"}:
        covered = coverage["words"]
    elif kind == "segments" and set(coverage) == {"kind", "segments"}:
        ids = coverage["segments"]
        if not isinstance(ids, list) or not ids or any(not isinstance(s, str) for s in ids):
            raise BindingError("invalid segment coverage")
        selected = [segment for segment in doc["segments"] if segment["id"] in ids]
        if [segment["id"] for segment in selected] != ids:
            raise BindingError("unknown or out-of-order segment coverage")
        covered = [word["id"] for segment in selected for word in segment.get("words", [])]
    else:
        raise BindingError("invalid witness coverage kind or fields")
    if (
        not isinstance(covered, list)
        or not covered
        or any(not isinstance(word, str) for word in covered)
        or covered != [word for word in all_words if word in covered]
    ):
        raise BindingError("unknown, duplicate or out-of-order word coverage")
    headers = _headers(text, "covers")
    if not headers:
        if covered != all_words:
            raise BindingError("partial graph coverage requires a transcript covers header")
        return
    if len(headers) != 1 or not (span := re.fullmatch(r"(w\d+)\s*-\s*(w\d+)", headers[0])):
        raise BindingError("ambiguous or malformed transcript covers header")
    if span[1] not in all_words or span[2] not in all_words:
        raise BindingError("transcript coverage names unknown words")
    first, last = all_words.index(span[1]), all_words.index(span[2])
    if last < first or covered != all_words[first : last + 1] or covered == all_words:
        raise BindingError("graph and transcript coverage disagree")


def source_dependencies(witness: dict) -> dict:
    """Unknown inventory is not the same as a deliberately empty inventory."""
    value = witness.get("source_dependencies")
    if not isinstance(value, dict) or set(value) != {"uses", "raw_binding"}:
        raise BindingError("complete explicit source_dependencies declaration required")
    uses, raw = value["uses"], value["raw_binding"]
    if (
        not isinstance(uses, list)
        or any(not isinstance(item, str) or not IDENTITY.fullmatch(item) for item in uses)
        or uses != sorted(set(uses))
        or witness.get("use") in uses
    ):
        raise BindingError("supplemental uses must be sorted unique IDs excluding the primary")
    if raw is not None and (not isinstance(raw, str) or not NAME.fullmatch(raw)):
        raise BindingError("raw_binding must be a binding ID or null")
    return value


def _index(graph: dict, field: str) -> dict[str, dict]:
    values = graph.get(field)
    if not isinstance(values, list):
        raise BindingError(f"{field} must be an array")
    indexed = {}
    for value in values:
        if (
            not isinstance(value, dict)
            or not isinstance(value.get("id"), str)
            or not IDENTITY.fullmatch(value["id"])
        ):
            raise BindingError(f"invalid {field} identity")
        if value["id"] in indexed:
            raise BindingError(f"duplicate {field} identity: {value['id']}")
        indexed[value["id"]] = deepcopy(value)
    return indexed


def _lookup(index: dict[str, dict], key: object, label: str) -> dict:
    if not isinstance(key, str) or key not in index:
        raise BindingError(f"unknown {label}")
    return index[key]


def _source_address(address: object, doc: dict) -> None:
    if not isinstance(address, dict) or address.get("text") != doc["id"]:
        raise BindingError("source use and document must address the same text")
    kind = address.get("kind")
    expected = {
        "text": {"kind", "text"},
        "segment": {"kind", "text", "segment"},
        "word": {"kind", "text", "word"},
    }
    if not isinstance(kind, str) or kind not in expected or set(address) != expected[kind]:
        raise BindingError("invalid source use address")
    if kind == "segment" and address["segment"] not in [s["id"] for s in doc["segments"]]:
        raise BindingError("source use addresses an unknown segment")
    if kind == "word" and address["word"] not in [
        w["id"] for s in doc["segments"] for w in s.get("words", [])
    ]:
        raise BindingError("source use addresses an unknown word")


def _digital_provider(source: dict) -> bool:
    if source["work"]["id"] == "work.divinum-officium":
        return True
    url = urlparse(str(source["digital_item"].get("record_url", "")))
    return url.hostname in {"github.com", "raw.githubusercontent.com"} and (
        url.path.lower().startswith("/divinumofficium/divinum-officium/")
    )


class _SourceSnapshot:
    """Private, indexed graph snapshot shared only within one validation run."""

    def __init__(self, root: Path, graph: dict):
        self.root = root
        self.uses = _index(graph, "uses")
        self.works = _index(graph, "works")
        self.editions = _index(graph, "editions")
        self.items = _index(graph, "digital_items")
        self.witnesses = _index(graph, "witnesses")
        _index(graph, "collations")
        self.raw: RawBindingSnapshot | None = None

    def source(self, identifier: object, doc: dict, *, supplemental: bool = False) -> dict:
        use = _lookup(self.uses, identifier, "source use")
        _source_address(use.get("address"), doc)
        roles = SUPPLEMENT_ROLES if supplemental else LATIN_SOURCE_ROLES
        if not isinstance(use.get("role"), str) or use["role"] not in roles:
            raise BindingError("source use has an incompatible role")
        edition = _lookup(self.editions, use.get("edition"), "source edition")
        item = _lookup(self.items, use.get("digital_item"), "source digital item")
        if item.get("edition") != edition["id"]:
            raise BindingError("digital item belongs to another edition")
        if not isinstance(item.get("kind"), str) or item["kind"] not in DIGITAL_KINDS:
            raise BindingError("invalid digital item kind")
        work = _lookup(self.works, edition.get("work"), "source work")
        return {"use": use, "work": work, "edition": edition, "digital_item": item}

    def reading(self, path: Path):
        if self.raw is None:
            self.raw = RawBindingSnapshot(self.root)
        return self.raw.resolve(path)


def _witness_subject(
    root: Path, witness: dict, doc: dict, snapshot: _SourceSnapshot, *, reviewable: bool
) -> dict:
    name = witness.get("transcription")
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise BindingError("transcription must be a local witness name without a path or extension")
    text_id = _text_id(witness.get("text"))
    if doc.get("id") != text_id:
        raise BindingError("document and witness text differ")
    known = _lookup(snapshot.witnesses, witness.get("id"), "witness identity")
    if known.get("text") != text_id:
        raise BindingError("witness identity belongs to another text")
    path = _confined(root, f"witnesses/{text_id}/{name}.txt")
    text = path.read_text(encoding="utf-8")
    if _headers(text, "witness") != [name]:
        raise BindingError("transcription name and witness header disagree")
    _coverage(witness, text, doc)
    if witness.get("transcription_sha256") != transcript_digest(text):
        raise BindingError("transcription_sha256 differs from the complete bound transcript")
    primary = snapshot.source(witness.get("use"), doc)
    subject: dict = {
        "contract": "witness-identity-2",
        "witness": {key: value for key, value in witness.items() if key != "review"},
        "source_uses": {witness["use"]: primary},
        "selected_text": selected_text(doc),
    }
    if not reviewable and "source_dependencies" not in witness:
        return deepcopy(subject)
    declaration = source_dependencies(witness)
    for identifier in declaration["uses"]:
        source = snapshot.source(identifier, doc, supplemental=True)
        if source["edition"]["id"] != primary["edition"]["id"]:
            raise BindingError("supplemental source belongs to another edition")
        subject["source_uses"][identifier] = source
    if any(
        source["digital_item"]["kind"] == "born-digital" and not _digital_provider(source)
        for source in subject["source_uses"].values()
    ):
        raise BindingError("unsupported born-digital source requires its own evidence contract")
    reading = snapshot.reading(path)
    if (
        reading is not None
        and reading.source["transcription_sha256"] != witness["transcription_sha256"]
    ):
        raise BindingError("transcription changed while resolving its raw binding")
    raw = declaration["raw_binding"]
    if raw is None:
        if reading is not None or _digital_provider(primary):
            raise BindingError("source requires its explicit exact raw binding")
    else:
        if reading is None or reading.source["binding_id"] != raw:
            raise BindingError("declared raw binding differs from registered resolution")
        if not _digital_provider(primary):
            raise BindingError("raw binding requires the matching digital source provider")
        revision = reading.source["binding"]["revision"]
        if any(
            s["digital_item"].get("revision") != revision
            or s["digital_item"].get("kind") != "born-digital"
            for s in subject["source_uses"].values()
        ):
            raise BindingError("digital item revision or kind differs from raw binding")
        # A generic evidence hash need not name the first archive. Existing
        # digital uses identify either a contributing archive's complete bytes
        # or the complete ordered reading with one terminal LF. Both subjects
        # must come from this checked resolution, never an unrelated real file.
        evidence_hashes = {archive["sha256"] for archive in reading.source["archives"].values()} | {
            hashlib.sha256((reading.text + "\n").encode("utf-8")).hexdigest()
        }
        for source in subject["source_uses"].values():
            evidence = source["use"].get("evidence_sha256")
            if _digital_provider(source) and (
                not isinstance(evidence, str) or evidence not in evidence_hashes
            ):
                raise BindingError(
                    "digital evidence_sha256 identifies neither a bound archive "
                    "nor the complete resolved reading"
                )
    subject["raw_resolution"] = reading.source if reading is not None else None
    subject["contract"] = "witness-review-2"
    return deepcopy(subject)


def witness_subject(root: Path, witness: dict, graph: dict, doc: dict) -> dict:
    """Build a reviewable subject only from an explicit, fully resolved inventory."""
    return _witness_subject(root, witness, doc, _SourceSnapshot(root, graph), reviewable=True)


def collation_subject(root: Path, collation: dict, doc: dict, witnesses: dict) -> dict:
    """A public review subject may not contain unresolved identity-only witnesses."""
    return _collation_subject(root, collation, doc, witnesses, reviewable=True)


def _collation_subject(
    root: Path, collation: dict, doc: dict, witnesses: dict, *, reviewable: bool
) -> dict:
    identifier = collation.get("id")
    if not isinstance(identifier, str) or not IDENTITY.fullmatch(identifier):
        raise BindingError("invalid collation identity")
    text_id = _text_id(collation.get("text"))
    if doc.get("id") != text_id:
        raise BindingError("document and collation text differ")
    selected = selected_text(doc)
    if collation.get("selected_text_sha256") != digest(selected):
        raise BindingError("selected_text_sha256 differs from the current Latin/ritual subject")
    apparatus = _json(_confined(root, f"witnesses/{text_id}/apparatus.json"))
    if apparatus.get("text") != text_id:
        raise BindingError("apparatus belongs to another text")
    if collation.get("apparatus_sha256") != digest(apparatus):
        raise BindingError("apparatus_sha256 differs from the complete apparatus")
    entries = apparatus.get("adjudicated")
    if not isinstance(entries, list) or any(
        not isinstance(entry, dict)
        or not isinstance(entry.get("class"), str)
        or not entry["class"].strip()
        or not isinstance(entry.get("witnesses"), dict)
        or not entry["witnesses"]
        or any(
            not isinstance(k, str) or not isinstance(v, str) for k, v in entry["witnesses"].items()
        )
        for entry in entries
    ):
        raise BindingError("apparatus adjudicated must contain classified witness-reading objects")
    if digest(collation.get("apparatus")) != digest(derived_summary(apparatus)):
        raise BindingError("apparatus summary differs from the actual adjudicated entries")
    ids = collation.get("witnesses")
    if (
        not isinstance(ids, list)
        or len(ids) < 2
        or any(not isinstance(i, str) or i not in witnesses for i in ids)
        or len(set(ids)) != len(ids)
    ):
        raise BindingError("collation has an unbound or duplicate witness")
    for identifier in ids:
        bound = witnesses[identifier]
        if bound["witness"].get("text") != text_id or bound["witness"].get("id") != identifier:
            raise BindingError("collation witness identity or text differs")
        if digest(bound.get("selected_text")) != digest(selected):
            raise BindingError("collation and witness selected text differ")
    complete = all(witnesses[i].get("contract") == "witness-review-2" for i in ids)
    if reviewable and not complete:
        raise BindingError("reviewable collation requires complete witness source inventories")
    named = {witnesses[identifier]["witness"]["transcription"] for identifier in ids}
    omitted = {name for entry in entries for name in entry["witnesses"]} - named
    if omitted:
        raise BindingError(f"collation omits apparatus witness dependencies: {sorted(omitted)}")
    return deepcopy(
        {
            "contract": "collation-review-2" if complete else "collation-identity-2",
            "collation": {key: value for key, value in collation.items() if key != "review"},
            "witnesses": {identifier: witnesses[identifier] for identifier in ids},
        }
    )


def _review(record: dict, subject: dict, *, dependencies_reviewed: bool = True) -> None:
    review = record.get("review")
    if review == {"status": "pending"}:
        return
    if (
        not isinstance(review, dict)
        or set(review) != {"status", "sha256"}
        or review.get("status") != "reviewed"
    ):
        raise BindingError("review must be pending or an exact reviewed subject")
    if not dependencies_reviewed:
        raise BindingError("reviewed collation requires reviewed witness bindings")
    if subject.get("contract") not in {"witness-review-2", "collation-review-2"}:
        raise BindingError("review requires a complete source inventory")
    if review["sha256"] != digest(subject):
        raise BindingError("reviewed subject changed; re-review or mark pending explicitly")


def validate_bindings(root: Path, graph: dict) -> list[str]:
    """Validate current identities even while source adjudication is pending."""
    errors: list[str] = []
    docs, subjects, reviews = {}, {}, {}
    bound_files: set[tuple[str, str]] = set()
    try:
        snapshot = _SourceSnapshot(root, graph)
    except (ValueError, KeyError, TypeError) as exc:
        return [f"bibliography source identities: {exc}"]

    def doc(text_id):
        if text_id not in docs:
            docs[text_id] = text_document(root, text_id)
        return docs[text_id]

    for witness in graph.get("witnesses", []):
        try:
            key = (witness["text"], witness["transcription"])
            if key in bound_files:
                raise BindingError("multiple witness records bind the same transcript")
            bound_files.add(key)
            subject = _witness_subject(
                root, witness, doc(witness.get("text")), snapshot, reviewable=False
            )
            _review(witness, subject)
            subjects[witness["id"]] = subject
            reviews[witness["id"]] = witness["review"]["status"] == "reviewed"
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"bibliography witness {witness.get('id')}: {exc}")
    for collation in graph.get("collations", []):
        try:
            subject = _collation_subject(
                root, collation, doc(collation.get("text")), subjects, reviewable=False
            )
            _review(
                collation,
                subject,
                dependencies_reviewed=all(reviews[i] for i in collation["witnesses"]),
            )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"bibliography collation {collation.get('id')}: {exc}")
    return errors

"""Reproducible source identities, distinct from an editorial source review.

Pending evidence still has to identify real, unchanged files. A review binds
the complete claim and its dependencies; recomputing a file checksum alone
cannot preserve a reviewed claim after those dependencies change.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from checks.apparatus import derived_summary

SEGMENT_FIELDS = ("id", "type", "text", "verse", "speaker", "voice", "delivery", "parentheses")
WORD_FIELDS = ("id", "form", "pre", "post")
NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
TEXT_ID = re.compile(r"[a-z0-9-]+\.[a-z0-9-]+")


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


def witness_subject(root: Path, witness: dict, graph: dict, doc: dict) -> dict:
    """Read the exact declared file; never infer identity from an equal digest."""
    name = witness.get("transcription")
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise BindingError("transcription must be a local witness name without a path or extension")
    text_id = _text_id(witness.get("text"))
    path = _confined(root, f"witnesses/{text_id}/{name}.txt")
    text = path.read_text(encoding="utf-8")
    if _headers(text, "witness") != [name]:
        raise BindingError("transcription name and witness header disagree")
    _coverage(witness, text, doc)
    if witness.get("transcription_sha256") != transcript_digest(text):
        raise BindingError("transcription_sha256 differs from the complete bound transcript")
    uses = {use["id"]: use for use in graph["uses"]}
    use = uses.get(witness.get("use"))
    if use is None:
        raise BindingError("unknown witness source use")
    edition = next((e for e in graph["editions"] if e["id"] == use.get("edition")), None)
    item = next((i for i in graph["digital_items"] if i["id"] == use.get("digital_item")), None)
    if edition is None or item is None:
        raise BindingError("unknown witness edition or digital item")
    work = next((work for work in graph["works"] if work["id"] == edition.get("work")), None)
    if work is None:
        raise BindingError("unknown witness work")
    return {
        "contract": "witness-review-1",
        "witness": {key: value for key, value in witness.items() if key != "review"},
        "use": use,
        "work": work,
        "edition": edition,
        "digital_item": item,
        "selected_text": selected_text(doc),
    }


def collation_subject(root: Path, collation: dict, doc: dict, witnesses: dict) -> dict:
    text_id = _text_id(collation.get("text"))
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
        or not ids
        or any(not isinstance(i, str) or i not in witnesses for i in ids)
    ):
        raise BindingError("collation has an unbound witness")
    named = {witnesses[identifier]["witness"]["transcription"] for identifier in ids}
    omitted = {name for entry in entries for name in entry["witnesses"]} - named
    if omitted:
        raise BindingError(f"collation omits apparatus witness dependencies: {sorted(omitted)}")
    return {
        "contract": "collation-review-1",
        "collation": {key: value for key, value in collation.items() if key != "review"},
        "witnesses": {identifier: witnesses[identifier] for identifier in ids},
    }


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
    if review["sha256"] != digest(subject):
        raise BindingError("reviewed subject changed; re-review or mark pending explicitly")


def validate_bindings(root: Path, graph: dict) -> list[str]:
    """Validate current identities even while source adjudication is pending."""
    errors: list[str] = []
    docs, subjects, reviews = {}, {}, {}
    bound_files: set[tuple[str, str]] = set()

    def doc(text_id):
        if text_id not in docs:
            docs[text_id] = text_document(root, text_id)
        return docs[text_id]

    for witness in graph.get("witnesses", []):
        try:
            subject = witness_subject(root, witness, graph, doc(witness.get("text")))
            key = (witness["text"], witness["transcription"])
            if key in bound_files:
                raise BindingError("multiple witness records bind the same transcript")
            bound_files.add(key)
            _review(witness, subject)
            subjects[witness["id"]] = subject
            reviews[witness["id"]] = witness["review"]["status"] == "reviewed"
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"bibliography witness {witness.get('id')}: {exc}")
    for collation in graph.get("collations", []):
        try:
            subject = collation_subject(root, collation, doc(collation.get("text")), subjects)
            _review(
                collation,
                subject,
                dependencies_reviewed=all(reviews[i] for i in collation["witnesses"]),
            )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"bibliography collation {collation.get('id')}: {exc}")
    return errors

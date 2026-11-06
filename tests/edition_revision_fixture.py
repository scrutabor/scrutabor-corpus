"""Exact predecessors for historical edition fixtures.

Only the declared complete current file can be projected. A corrupt or
unrelated input is returned untouched for the historical comparison to reject.
The ordinary language checks and the current-edition assertions read live data.
"""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

PUBLISHED_FILES = json.loads(
    (Path(__file__).parent / "fixtures/edition-revision-history.json").read_bytes()
)
CAPTION_REVISION = json.loads(
    (Path(__file__).parent / "fixtures/ordinary-caption-revision.json").read_bytes()
)
CAPTION_FILES = CAPTION_REVISION["files"]
FILES = {
    relative: {"current": entry["current"], "previous": entry["previous"]}
    for relative, entry in PUBLISHED_FILES.items()
}
for _relative, _entry in CAPTION_FILES.items():
    FILES[_relative] = {
        "current": _entry["current"],
        "previous": PUBLISHED_FILES.get(_relative, _entry)["previous"],
    }
# The newest receipt: the reader review of the standalone prayers, on top of both older ones.
REVIEW_REVISION = json.loads(
    (Path(__file__).parent / "fixtures/prayer-review-revision.json").read_bytes()
)
REVIEW_FILES = REVIEW_REVISION["files"]
for _relative, _entry in REVIEW_FILES.items():
    FILES[_relative] = {
        "current": _entry["current"],
        "previous": FILES.get(_relative, _entry)["previous"],
    }
# The owner's decisions after that review, on top of all three.
OWNER_REVISION = json.loads(
    (Path(__file__).parent / "fixtures/owner-decisions-revision.json").read_bytes()
)
OWNER_FILES = OWNER_REVISION["files"]
for _relative, _entry in OWNER_FILES.items():
    FILES[_relative] = {
        "current": _entry["current"],
        "previous": FILES.get(_relative, _entry)["previous"],
    }
# The newest receipt: three printed wording witnesses enter the bibliography, on top of all four.
# It changes graph, bibliography, basis and provenance files only, never a language layer.
WITNESS_REVISION = json.loads(
    (Path(__file__).parent / "fixtures/witness-citations-revision.json").read_bytes()
)
WITNESS_FILES = WITNESS_REVISION["files"]
for _relative, _entry in WITNESS_FILES.items():
    FILES[_relative] = {
        "current": _entry["current"],
        "previous": FILES.get(_relative, _entry)["previous"],
    }


def _exact_inverse(entry, raw):
    assert hashlib.sha256(raw).hexdigest() == entry["current"]
    text = raw.decode("utf-8")
    for start, end, previous in reversed(entry["inverse"]):
        text = text[:start] + previous + text[end:]
    result = text.encode("utf-8")
    assert hashlib.sha256(result).hexdigest() == entry["previous"]
    return result


def before_caption_revision(relative, raw):
    """The exact published parent, independently of the older edition receipt."""
    entry = CAPTION_FILES.get(relative)
    if entry is None or hashlib.sha256(raw).hexdigest() != entry["current"]:
        return raw
    return _exact_inverse(entry, raw)


def before_review_revision(relative, raw):
    """The exact parent of the prayer reader-review receipt; anything else is returned untouched."""
    entry = REVIEW_FILES.get(relative)
    if entry is None or hashlib.sha256(raw).hexdigest() != entry["current"]:
        return raw
    return _exact_inverse(entry, raw)


def before_owner_revision(relative, raw):
    """The exact parent of the owner-decisions receipt; anything else is returned untouched."""
    entry = OWNER_FILES.get(relative)
    if entry is None or hashlib.sha256(raw).hexdigest() != entry["current"]:
        return raw
    return _exact_inverse(entry, raw)


def before_witness_revision(relative, raw):
    """The exact parent of the witness-citations receipt; anything else is returned untouched."""
    entry = WITNESS_FILES.get(relative)
    if entry is None or hashlib.sha256(raw).hexdigest() != entry["current"]:
        return raw
    return _exact_inverse(entry, raw)


def before_edition_revision(relative, raw):
    entry = FILES.get(relative)
    if entry is None or hashlib.sha256(raw).hexdigest() != entry["current"]:
        return raw
    result = before_witness_revision(relative, raw)
    result = before_owner_revision(relative, result)
    result = before_review_revision(relative, result)
    result = before_caption_revision(relative, result)
    if relative in PUBLISHED_FILES:
        result = _exact_inverse(PUBLISHED_FILES[relative], result)
    assert hashlib.sha256(result).hexdigest() == entry["previous"], relative
    return result


def read_predecessor(root, relative):
    return before_edition_revision(relative, (root / relative).read_bytes())


PUBLISHED_LAYER_CHANGES = json.loads(
    (Path(__file__).parent / "fixtures/edition-layer-revisions.json").read_bytes()
)
ABSENT = object()


def _composed_layer_changes():
    """Join exact adjacent values while preserving the four receipts in order."""
    result = deepcopy(PUBLISHED_LAYER_CHANGES)
    for relative, entry in [*CAPTION_FILES.items(), *REVIEW_FILES.items(), *OWNER_FILES.items()]:
        changes = result.setdefault(relative, [])
        for current in entry.get("changes", ()):
            previous = next((c for c in changes if c["path"] == current["path"]), None)
            if previous is None:
                changes.append(deepcopy(current))
                continue
            assert previous.get("after", ABSENT) == current.get("before", ABSENT), relative
            previous.pop("after", None)
            if "after" in current:
                previous["after"] = deepcopy(current["after"])
            if previous.get("before", ABSENT) == previous.get("after", ABSENT):
                changes.remove(previous)
        if not changes:
            del result[relative]
    return result


LAYER_CHANGES = _composed_layer_changes()


def before_edition_layer(layer):
    """Undo only matching declared fields on a copy; preserve all unlisted mutations."""
    return _undo_layer_changes(layer, LAYER_CHANGES)


REVIEW_LAYER_CHANGES = {
    relative: entry["changes"] for relative, entry in REVIEW_FILES.items() if entry.get("changes")
}


def before_review_layer(layer):
    """Undo only the prayer reader-review fields on a copy."""
    return _undo_layer_changes(layer, REVIEW_LAYER_CHANGES)


OWNER_LAYER_CHANGES = {
    relative: entry["changes"] for relative, entry in OWNER_FILES.items() if entry.get("changes")
}


def before_owner_layer(layer):
    """Undo only the owner-decision fields (the newest receipt) on a copy."""
    return _undo_layer_changes(layer, OWNER_LAYER_CHANGES)


def _undo_layer_changes(layer, declared):
    text = layer.get("text")
    language = layer.get("language", layer.get("lang"))
    if not isinstance(text, str) or not isinstance(language, str):
        return layer
    relative = f"languages/{language}/texts/{text.replace('.', '/', 1)}.json"
    changes = declared.get(relative, ())
    result = layer
    for change in changes:
        fields = change["path"]
        container = result
        for field in fields[:-1]:
            container = container.get(field) if isinstance(container, dict) else None
        if not isinstance(container, dict) or container.get(fields[-1], ABSENT) != change.get(
            "after", ABSENT
        ):
            continue
        if result is layer:
            result = deepcopy(layer)
            container = result
            for field in fields[:-1]:
                container = container[field]
        if "before" in change:
            container[fields[-1]] = deepcopy(change["before"])
        else:
            del container[fields[-1]]
    return result


def before_edition_object(relative, value):
    """Parsed counterpart for older graph, provenance and layer comparisons."""
    if relative not in FILES:
        return value
    if (
        relative.startswith("texts/")
        or "/texts/" in relative
        or relative.endswith("translation-provenance.json")
    ):
        from checks.layout import formatted

        raw = formatted(value).encode()
    else:
        raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    previous = before_edition_revision(relative, raw)
    return value if previous is raw else json.loads(previous)


def current_edition_value(relative, fields, previous):
    """A declared live expected value; never normalize the observed current value.

    The receipts are walked oldest first, so an exact old value advances through every later
    declared change of the same field; an undeclared value is returned as it came.
    """
    receipts = (
        PUBLISHED_LAYER_CHANGES.get(relative, ()),
        CAPTION_FILES.get(relative, {}).get("changes", ()),
        REVIEW_FILES.get(relative, {}).get("changes", ()),
        OWNER_FILES.get(relative, {}).get("changes", ()),
    )
    value, advanced = previous, False
    for changes in receipts:
        for change in changes:
            if change["path"] == list(fields) and change.get("before", ABSENT) == value:
                value, advanced = change.get("after", ABSENT), True
                break
    if not advanced:
        return previous
    return deepcopy(value) if value is not ABSENT else ABSENT


def _digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def current_edition_target_sha(text, language, segment, previous):
    """Advance only an enrolled translation's exact old target digest."""
    relative = f"languages/{language}/texts/{text.replace('.', '/', 1)}.json"
    for change in LAYER_CHANGES.get(relative, ()):
        if (
            change["path"] == ["segments", segment, "translation"]
            and "before" in change
            and "after" in change
            and _digest(change["before"]) == previous
        ):
            return _digest(change["after"])
    return previous


def before_edition_target_row(row):
    """Historical target identity only; retain every other row field and fault."""
    relative = f"languages/{row['language']}/texts/{row['text'].replace('.', '/', 1)}.json"
    for change in LAYER_CHANGES.get(relative, ()):
        if (
            change["path"] == ["segments", row["segment"], "translation"]
            and "before" in change
            and "after" in change
            and row.get("target_sha256") == _digest(change["after"])
        ):
            return {**deepcopy(row), "target_sha256": _digest(change["before"])}
    return row


def current_edition_caption(language, text, segment, words, previous):
    """A declared caption successor, selected by its exact old source span/value."""
    relative = f"languages/{language}/texts/{text.replace('.', '/', 1)}.json"
    changes = LAYER_CHANGES.get(relative, ())
    if not words:
        return None
    known = any(
        (
            change["path"] == ["words", words[0], "gloss"]
            and len(words) == 1
            and change.get("before", ABSENT) == previous
        )
        or (
            change["path"] == ["segments", segment, "alignments"]
            and any(
                group.get("words") == list(words) and group.get("gloss") == previous
                for group in change.get("before", ())
            )
        )
        for change in changes
    )
    if not known:
        return None
    groups = [
        group
        for change in changes
        if change["path"] == ["segments", segment, "alignments"]
        for group in change.get("after", ())
        if set(words) <= set(group.get("words", ())) and isinstance(group.get("gloss"), str)
    ]
    return deepcopy(groups[0]) if len(groups) == 1 else None

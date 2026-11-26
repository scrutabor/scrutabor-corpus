"""Exact predecessors for historical edition fixtures.

Only the declared complete current file can be projected. A corrupt or
unrelated input is returned untouched for the historical comparison to reject.
The ordinary language checks and the current-edition assertions read live data.
"""

import hashlib
import json
import shutil
from copy import deepcopy
from functools import cache
from pathlib import Path
from tempfile import TemporaryDirectory

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
# The reader review of the standalone prayers, on top of both older receipts.
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
# Three printed wording witnesses enter the bibliography, on top of all four older receipts.
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
# Source qualifications and attribution corrections follow the printed-witness receipt.
SOURCE_SCOPE_REVISION = json.loads(
    (Path(__file__).parent / "fixtures/source-scope-revision.json").read_bytes()
)
SOURCE_SCOPE_FILES = SOURCE_SCOPE_REVISION["files"]
for _relative, _entry in SOURCE_SCOPE_FILES.items():
    FILES[_relative] = {
        "current": _entry["current"],
        "previous": FILES.get(_relative, _entry)["previous"],
    }
RUBRIC_CAPTION_REVISION = json.loads(
    (Path(__file__).parent / "fixtures/rubric-caption-revision.json").read_bytes()
)
RUBRIC_CAPTION_FILES = RUBRIC_CAPTION_REVISION["files"]
for _relative, _entry in RUBRIC_CAPTION_FILES.items():
    if _relative in FILES:
        assert FILES[_relative]["current"] == _entry["previous"], _relative
    FILES[_relative] = {
        "current": _entry["current"],
        "previous": FILES.get(_relative, _entry)["previous"],
    }
READING_FILES = json.loads(
    (Path(__file__).parent / "fixtures/reading-language-revision.json").read_bytes()
)["files"]
COMMUNION_FILES = json.loads(
    (Path(__file__).parent / "fixtures/communion-readings-revision.json").read_bytes()
)["files"]
BIBLIOGRAPHY_FILES = json.loads(
    (Path(__file__).parent / "fixtures/bibliographic-source-revision.json").read_bytes()
)["files"]
GRATIA_FILES = json.loads(
    (Path(__file__).parent / "fixtures/gratia-explanation-revision.json").read_bytes()
)["files"]
for _revision in (READING_FILES, COMMUNION_FILES, BIBLIOGRAPHY_FILES, GRATIA_FILES):
    for _relative, _entry in _revision.items():
        if _relative in FILES:
            assert FILES[_relative]["current"] == _entry["previous"], _relative
        FILES[_relative] = {
            "current": _entry["current"],
            "previous": FILES.get(_relative, _entry)["previous"],
        }


def _exact_inverse(entry, raw):
    assert hashlib.sha256(raw).hexdigest() == entry["current"]
    text = raw.decode("utf-8")
    chunks = []
    position = 0
    for start, end, previous in entry["inverse"]:
        assert position <= start <= end <= len(text)
        chunks.extend((text[position:start], previous))
        position = end
    chunks.append(text[position:])
    result = "".join(chunks).encode("utf-8")
    assert hashlib.sha256(result).hexdigest() == entry["previous"]
    return result


def before_caption_revision(relative, raw):
    """The exact published parent, independently of the older edition receipt."""
    entry = CAPTION_FILES.get(relative)
    if entry is None:
        return raw
    raw = before_rubric_caption_revision(relative, raw)
    if hashlib.sha256(raw).hexdigest() != entry["current"]:
        return raw
    return _exact_inverse(entry, raw)


def before_review_revision(relative, raw):
    """Undo exact source-scope and prayer reader-review receipts, newest first."""
    raw = before_source_scope_revision(relative, raw)
    entry = REVIEW_FILES.get(relative)
    if entry is None or hashlib.sha256(raw).hexdigest() != entry["current"]:
        return raw
    return _exact_inverse(entry, raw)


def before_owner_revision(relative, raw):
    """Undo exact source-scope and owner-decisions receipts, newest first."""
    raw = before_source_scope_revision(relative, raw)
    entry = OWNER_FILES.get(relative)
    if entry is None or hashlib.sha256(raw).hexdigest() != entry["current"]:
        return raw
    return _exact_inverse(entry, raw)


def before_witness_revision(relative, raw):
    """Undo exact source-scope and witness-citations receipts, newest first."""
    raw = before_source_scope_revision(relative, raw)
    entry = WITNESS_FILES.get(relative)
    if entry is None or hashlib.sha256(raw).hexdigest() != entry["current"]:
        return raw
    return _exact_inverse(entry, raw)


def before_source_scope_revision(relative, raw):
    """Undo the source-scope receipt only for the complete exact declared input."""
    raw = before_rubric_caption_revision(relative, raw)
    entry = SOURCE_SCOPE_FILES.get(relative)
    if entry is None or hashlib.sha256(raw).hexdigest() != entry["current"]:
        return raw
    return _exact_inverse(entry, raw)


def before_gratia_revision(relative, raw):
    """Restore the preceding explanation only from the exact current language layer."""
    entry = GRATIA_FILES.get(relative)
    if entry is None or hashlib.sha256(raw).hexdigest() != entry["current"]:
        return raw
    return _exact_inverse(entry, raw)


def before_bibliography_revision(relative, raw):
    """Restore the preceding bibliography and its source readings when the input is exact."""
    raw = before_gratia_revision(relative, raw)
    entry = BIBLIOGRAPHY_FILES.get(relative)
    if entry is None or hashlib.sha256(raw).hexdigest() != entry["current"]:
        return raw
    return _exact_inverse(entry, raw)


@cache
def _bibliography_record_changes():
    root = Path(__file__).resolve().parents[1]
    changed = {}
    for relative in (
        "bibliography/graph.json",
        "languages/pl/bibliography.json",
        "languages/en/bibliography.json",
    ):
        current = (root / relative).read_bytes()
        previous = _exact_inverse(BIBLIOGRAPHY_FILES[relative], current)
        earlier, later = json.loads(previous), json.loads(current)
        for field, rows in later.items():
            if not isinstance(rows, list):
                continue
            old = {r["id"]: r for r in earlier[field] if isinstance(r, dict) and "id" in r}
            for row in rows:
                if not isinstance(row, dict) or "id" not in row:
                    continue
                identity = row["id"]
                if identity in old and row != old[identity]:
                    key = (field, identity)
                    assert key not in changed, key
                    changed[key] = (old[identity], row)
    return changed


def _bibliography_record(field, row, source, target, subject):
    transition = _bibliography_record_changes().get((field, row.get("id")))
    if transition is None:
        return row
    expected, result = transition[source], transition[target]
    if subject:
        assert field == "witnesses" and "review" not in row
        expected = {k: v for k, v in expected.items() if k != "review"}
        result = {k: v for k, v in result.items() if k != "review"}
    return deepcopy(result) if row == expected else row


def before_bibliography_record(field, row, *, subject=False):
    """The immediate predecessor of an exact row or a native witness subject."""
    return _bibliography_record(field, row, 1, 0, subject)


def current_bibliography_record(field, row, *, subject=False):
    """Advance an exact historical expectation without changing the observed input."""
    return _bibliography_record(field, row, 0, 1, subject)


def current_bibliography_fields(field, expected):
    """Advance a historical selection of fields only when every one matches its source."""
    pair = _bibliography_record_changes().get((field, expected.get("id")))
    if not pair or any(k not in pair[0] or pair[0][k] != v for k, v in expected.items()):
        return expected
    return {k: deepcopy(pair[1][k]) for k in expected if k in pair[1]}


def before_bibliography_records(value):
    """Restore whole enrolled records, preserving arbitrary changes elsewhere in a comparison."""
    fields = {
        "work": "works",
        "edition": "editions",
        "item": "digital_items",
        "use": "uses",
        "witness": "witnesses",
        "collation": "collations",
    }

    def visit(item, *, native=False):
        if isinstance(item, list):
            return [visit(child) for child in item]
        if not isinstance(item, dict):
            return item
        identity = item.get("id")
        if isinstance(identity, str):
            field = fields.get(identity.split(".", 1)[0])
            if field:
                previous = before_bibliography_record(field, item, subject=native)
                if previous is not item:
                    return previous
        witness_subject = item.get("contract") in {"witness-identity-2", "witness-review-2"}
        return {k: visit(v, native=witness_subject and k == "witness") for k, v in item.items()}

    return visit(value)


def current_bibliography_review(identifier, previous):
    """Advance a recorded review digest only from its exact enrolled predecessor."""
    field = "collations" if identifier.startswith("collation.") else "witnesses"
    pair = _bibliography_record_changes().get((field, identifier))
    if previous and pair and pair[0].get("review", {}).get("sha256") == previous:
        return pair[1]["review"]["sha256"]
    return previous


def _write_historical_input(root, historical_root, name):
    dest = historical_root / name
    if dest.exists():
        return
    dest.parent.mkdir(exist_ok=True, parents=True)
    raw = (root / name).read_bytes()
    if name in BIBLIOGRAPHY_FILES:
        raw = _exact_inverse(BIBLIOGRAPHY_FILES[name], raw)
    dest.write_bytes(raw)


@cache
def _bibliography_witness_roots():
    from build_reader.bibliography_bindings import _SourceSnapshot

    root = Path(__file__).resolve().parents[1]
    relative = "bibliography/graph.json"
    raw = (root / relative).read_bytes()
    earlier = json.loads(_exact_inverse(BIBLIOGRAPHY_FILES[relative], raw))
    later = json.loads(raw)
    directory = TemporaryDirectory(prefix="bibliographic-predecessor-")
    historical_root = Path(directory.name)
    # A raw resolver confines every path to its own edition, including the registry.
    shutil.copytree(root / "witnesses/raw", historical_root / "witnesses/raw")
    for name in BIBLIOGRAPHY_FILES:
        if name.startswith("witnesses/raw/"):
            (historical_root / name).write_bytes(
                _exact_inverse(BIBLIOGRAPHY_FILES[name], (root / name).read_bytes())
            )
    registry = json.loads((historical_root / "witnesses/raw/bindings.json").read_bytes())
    for binding in registry["bindings"].values():
        name = binding["witness"]
        _write_historical_input(root, historical_root, name)
    pairs = [
        (location, _SourceSnapshot(location, graph), {w["id"]: w for w in graph["witnesses"]})
        for location, graph in ((root, later), (historical_root, earlier))
    ]
    return directory, pairs


@cache
def _bibliography_subject_pair(identifier, reviewable):
    from build_reader.bibliography_bindings import _witness_subject, text_document

    _directory, (current, previous) = _bibliography_witness_roots()
    root, historical_root = current[0], previous[0]
    if identifier not in current[2] or identifier not in previous[2]:
        return None
    witness = previous[2][identifier]
    text = witness["text"]
    # Only the requested witness and its Latin text are needed beside the archive.
    for name in (
        f"witnesses/{text}/{witness['transcription']}.txt",
        "texts/" + text.replace(".", "/", 1) + ".json",
    ):
        _write_historical_input(root, historical_root, name)
    return tuple(
        _witness_subject(
            location,
            index[identifier],
            text_document(location, text),
            snapshot,
            reviewable=reviewable,
        )
        for location, snapshot, index in (current, previous)
    )


def before_bibliography_subject(value, *, reviewable=False):
    """Return the native predecessor only for the entire, exact later witness subject."""
    from build_reader.bibliography_bindings import BindingError

    identifier = value.get("witness", {}).get("id")
    if not identifier:
        return value
    try:
        pair = _bibliography_subject_pair(identifier, reviewable)
    except BindingError:
        # Either edition lacks the requested contract. It cannot prove this inverse.
        return value
    return deepcopy(pair[1]) if pair and value == pair[0] else value


def before_communion_revision(relative, raw):
    """Restore the wording before the antiphon, epistle and title corrections."""
    raw = before_bibliography_revision(relative, raw)
    entry = COMMUNION_FILES.get(relative)
    if entry is None or hashlib.sha256(raw).hexdigest() != entry["current"]:
        return raw
    return _exact_inverse(entry, raw)


def before_reading_revision(relative, raw):
    """Restore the edition preceding the general language revision."""
    raw = before_communion_revision(relative, raw)
    entry = READING_FILES.get(relative)
    if entry is None or hashlib.sha256(raw).hexdigest() != entry["current"]:
        return raw
    return _exact_inverse(entry, raw)


def before_reading_object(relative, value):
    """Return the preceding edition only for an exact, complete current document."""
    if not any(relative in files for files in (READING_FILES, COMMUNION_FILES, BIBLIOGRAPHY_FILES)):
        return value
    if "/texts/" in relative or relative.endswith("translation-provenance.json"):
        from checks.layout import formatted

        raw = formatted(value).encode()
    else:
        raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    previous = before_reading_revision(relative, raw)
    return value if previous is raw else json.loads(previous)


def before_reading_layer(layer):
    """Immediate predecessor of a complete authored language layer."""
    relative = f"languages/{layer['language']}/texts/{layer['text'].replace('.', '/', 1)}.json"
    return before_reading_object(relative, layer)


def before_rubric_caption_revision(relative, raw):
    """Restore the immediate predecessor of the rubric and caption corrections."""
    raw = before_reading_revision(relative, raw)
    entry = RUBRIC_CAPTION_FILES.get(relative)
    if entry is None or hashlib.sha256(raw).hexdigest() != entry["current"]:
        return raw
    return _exact_inverse(entry, raw)


def before_rubric_caption_layer(layer):
    """Reconstruct a layer's exact earlier comparison frame, if declared."""
    relative = f"languages/{layer['language']}/texts/{layer['text'].replace('.', '/', 1)}.json"
    if not any(
        relative in files
        for files in (
            RUBRIC_CAPTION_FILES,
            READING_FILES,
            COMMUNION_FILES,
            BIBLIOGRAPHY_FILES,
            GRATIA_FILES,
        )
    ):
        return layer
    from checks.layout import formatted

    raw = formatted(layer).encode("utf-8")
    previous = before_rubric_caption_revision(relative, raw)
    return layer if previous is raw else json.loads(previous)


def before_edition_revision(relative, raw):
    entry = FILES.get(relative)
    if entry is None or hashlib.sha256(raw).hexdigest() != entry["current"]:
        return raw
    result = before_source_scope_revision(relative, raw)
    result = before_witness_revision(relative, result)
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
    """Join exact adjacent values while preserving the receipts in order."""
    result = deepcopy(PUBLISHED_LAYER_CHANGES)
    for relative, entry in [
        *CAPTION_FILES.items(),
        *REVIEW_FILES.items(),
        *OWNER_FILES.items(),
        *SOURCE_SCOPE_FILES.items(),
        *RUBRIC_CAPTION_FILES.items(),
        *READING_FILES.items(),
        *COMMUNION_FILES.items(),
        *BIBLIOGRAPHY_FILES.items(),
        *GRATIA_FILES.items(),
    ]:
        if not entry.get("changes"):
            continue
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
SOURCE_SCOPE_LAYER_CHANGES = {
    relative: entry["changes"]
    for relative, entry in SOURCE_SCOPE_FILES.items()
    if entry.get("changes")
}
RUBRIC_CAPTION_LAYER_CHANGES = {
    relative: entry["changes"]
    for relative, entry in RUBRIC_CAPTION_FILES.items()
    if entry.get("changes")
}
READING_LAYER_CHANGES = {
    relative: entry["changes"] for relative, entry in READING_FILES.items() if entry.get("changes")
}
COMMUNION_LAYER_CHANGES = {
    relative: entry["changes"]
    for relative, entry in COMMUNION_FILES.items()
    if entry.get("changes")
}


BIBLIOGRAPHY_LAYER_CHANGES = {
    relative: entry["changes"]
    for relative, entry in BIBLIOGRAPHY_FILES.items()
    if entry.get("changes")
}


def before_review_layer(layer):
    """Undo source-scope and prayer reader-review fields on a historical comparison copy."""
    layer = _undo_layer_changes(layer, BIBLIOGRAPHY_LAYER_CHANGES)
    layer = _undo_layer_changes(layer, COMMUNION_LAYER_CHANGES)
    layer = _undo_layer_changes(layer, READING_LAYER_CHANGES)
    layer = _undo_layer_changes(layer, RUBRIC_CAPTION_LAYER_CHANGES)
    return _undo_layer_changes(
        _undo_layer_changes(layer, SOURCE_SCOPE_LAYER_CHANGES), REVIEW_LAYER_CHANGES
    )


OWNER_LAYER_CHANGES = {
    relative: entry["changes"] for relative, entry in OWNER_FILES.items() if entry.get("changes")
}


def before_owner_layer(layer):
    """Undo source-scope and owner-decision fields on a historical comparison copy."""
    layer = _undo_layer_changes(layer, BIBLIOGRAPHY_LAYER_CHANGES)
    layer = _undo_layer_changes(layer, COMMUNION_LAYER_CHANGES)
    layer = _undo_layer_changes(layer, READING_LAYER_CHANGES)
    layer = _undo_layer_changes(layer, RUBRIC_CAPTION_LAYER_CHANGES)
    return _undo_layer_changes(
        _undo_layer_changes(layer, SOURCE_SCOPE_LAYER_CHANGES), OWNER_LAYER_CHANGES
    )


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
        SOURCE_SCOPE_FILES.get(relative, {}).get("changes", ()),
        RUBRIC_CAPTION_FILES.get(relative, {}).get("changes", ()),
        READING_FILES.get(relative, {}).get("changes", ()),
        COMMUNION_FILES.get(relative, {}).get("changes", ()),
        BIBLIOGRAPHY_FILES.get(relative, {}).get("changes", ()),
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
    # Older comparisons begin at the composed predecessor. More recent ones can
    # begin at the immediately preceding wording of the same segment.
    for frame in (LAYER_CHANGES, READING_LAYER_CHANGES, COMMUNION_LAYER_CHANGES):
        for change in frame.get(relative, ()):
            if (
                change["path"] == ["segments", segment, "translation"]
                and "before" in change
                and "after" in change
                and _digest(change["before"]) == previous
            ):
                previous = _digest(change["after"])
                break
    return previous


def current_edition_provenance_row(row):
    """Advance a complete expected row whose translation classification changed."""
    receipt = RUBRIC_CAPTION_REVISION.get("target_rows", {}).get(row.get("site"))
    return deepcopy(receipt["after"]) if receipt and row == receipt["before"] else row


def before_edition_target_row(row):
    """Use an exact row receipt if its classification changed with the text."""
    receipt = RUBRIC_CAPTION_REVISION.get("target_rows", {}).get(row.get("site"))
    if receipt:
        return deepcopy(receipt["before"]) if row == receipt["after"] else row
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

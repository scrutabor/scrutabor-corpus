"""Exact English register successors, reversed only on historical comparison copies.

Future predictions read "will", future perfect and generalizing clauses read the
English present, eternity phrases read "forever", obsolete verb endings and
pronouns read contemporary English, and the Passion Sunday Introit sets the cause
apart from the unholy nation. Older exact comparisons first undo these declared
changes on a copy; every other byte and field must still match its oracle.
"""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from canon_consecration_successor_fixture import (
    before_canon_bytes,
    before_canon_layer_frame,
    before_canon_object,
)

from build_reader.bibliography_bindings import digest

DATA = json.loads(
    (Path(__file__).parent / "fixtures/english-register-2026-10-29.json").read_bytes()
)
FILES = DATA["files"]
ALLOWANCES = DATA["allowances"]
LAYERS = frozenset(relative for relative in FILES if relative.startswith("languages/en/texts/"))
LEDGER = "languages/en/translation-provenance.json"
# The English bibliography; the ledger is reached through the Perceptio chain head.
RECORDS = frozenset(relative for relative in FILES if relative not in LAYERS | {LEDGER})


def text_id(relative):
    return relative.removeprefix("languages/en/texts/").removesuffix(".json").replace("/", ".", 1)


PROSE = {
    (text_id(relative), operation["path"][1]): (operation["before"], operation["after"])
    for relative in sorted(LAYERS)
    for operation in FILES[relative]["object_inverse"]
    if operation["path"][0] == "segments" and operation["path"][2] == "translation"
}


def require(condition, diagnostic):
    if not condition:
        raise AssertionError(diagnostic)


def caption_operation(operation):
    """Word cards and alignment groups; segment prose and `about` stay outside a caption frame."""
    path = operation["path"]
    return path[0] == "words" or (path[0] == "segments" and path[2] == "alignments")


def inverse(rule, value, diagnostic, keep=None):
    result = deepcopy(value)
    for operation in reversed(rule["object_inverse"]):
        if keep is not None and not keep(operation):
            continue
        container = result
        for key in operation["path"][:-1]:
            container = container[key]
        key = operation["path"][-1]
        require(container[key] == operation["after"], diagnostic)
        container[key] = deepcopy(operation["before"])
    return result


def before_english_register_object(relative, value, diagnostic="English register comparison"):
    """Require the complete current object, then recover only the declared predecessor."""
    rule = FILES.get(relative)
    if rule is None:
        return value
    value = before_canon_object(relative, value, diagnostic)
    require(digest(value) == rule["after_canonical_sha256"], diagnostic)
    result = inverse(rule, value, diagnostic)
    require(digest(result) == rule["before_canonical_sha256"], diagnostic)
    return result


def before_english_register_frame(relative, value, project, diagnostic="English register frame"):
    """Undo caption changes; prose and `about` return only where they are exactly the successor.

    Any other prose value, including a prose fault, stays in the copy for its own oracle.
    """
    rule = FILES.get(relative)
    if rule is None:
        return value
    value = before_canon_layer_frame(value, diagnostic)
    if "after_caption_sha256" in rule:
        require(digest(project(value)) == rule["after_caption_sha256"], diagnostic)
        result = inverse(rule, value, diagnostic, caption_operation)
        require(digest(project(result)) == rule["before_caption_sha256"], diagnostic)
    else:
        result = deepcopy(value)
    for operation in rule["object_inverse"]:
        if caption_operation(operation):
            continue
        container = result
        for key in operation["path"][:-1]:
            container = container[key]
        key = operation["path"][-1]
        if container.get(key) == operation["after"]:
            container[key] = deepcopy(operation["before"])
    return result


def before_english_register_bytes(relative, raw, diagnostic="English register comparison bytes"):
    """Require every current byte, then restore only the declared earlier lines."""
    rule = FILES.get(relative)
    if rule is None:
        return raw
    raw = before_canon_bytes(relative, raw, diagnostic)
    require(hashlib.sha256(raw).hexdigest() == rule["after_raw_sha256"], diagnostic)
    result = raw
    for operation in reversed(rule["raw_inverse"]):
        after, before = operation["after"].encode(), operation["before"].encode()
        require(result.count(after) == operation["count"], diagnostic)
        result = result.replace(after, before, operation["count"])
    require(hashlib.sha256(result).hexdigest() == rule["before_raw_sha256"], diagnostic)
    require(digest(json.loads(result)) == rule["before_canonical_sha256"], diagnostic)
    return result


def before_english_register_layer(relative, value, diagnostic="English register layer"):
    """English text layers only; the ledger and records are reached through their own chains."""
    if relative not in LAYERS:
        return value
    return before_english_register_object(relative, value, diagnostic)


def before_english_register_layer_bytes(relative, raw, diagnostic="English register layer bytes"):
    if relative not in LAYERS:
        return raw
    return before_english_register_bytes(relative, raw, diagnostic)


def before_english_register_ledger(relative, value, diagnostic="English register ledger"):
    if relative != LEDGER:
        return value
    return before_english_register_object(relative, value, diagnostic)


def before_english_register_record_bytes(relative, raw, diagnostic="English register records"):
    """The English bibliography, whose newest earlier successor is Requiem."""
    if relative not in RECORDS:
        return raw
    return before_english_register_bytes(relative, raw, diagnostic)


def before_english_register_prose(text, translations):
    """Map exact current prose back to its predecessor; any other value reaches the old oracle."""
    result = dict(translations)
    for segment, value in translations.items():
        before, after = PROSE.get((text, segment), (None, None))
        if after is not None and value == after:
            result[segment] = before
    return result


def before_english_register_text_layer(layer, diagnostic="English register layer"):
    """The same exact layer inverse, addressed by the layer's own text and language."""
    if layer.get("language") != "en" or not isinstance(layer.get("text"), str):
        return layer
    relative = f"languages/en/texts/{layer['text'].replace('.', '/', 1)}.json"
    return before_english_register_layer(relative, layer, diagnostic)


def _reinsert_allowances(fixture, diagnostic):
    result = deepcopy(fixture)
    for item in reversed(ALLOWANCES["retired"]):
        if "record" in item:
            text = item["record"]["text"]
            require(all(row["text"] != text for row in result["records"]), diagnostic)
            index = min(item["record_index"], len(result["records"]))
            result["records"].insert(index, deepcopy(item["record"]))
            continue
        rows = [row for row in result["records"] if row["text"] == item["text"]]
        require(len(rows) == 1, diagnostic)
        fields = rows[0]["fields"]
        require(all(field["path"] != item["field"]["path"] for field in fields), diagnostic)
        fields.insert(min(item["field_index"], len(fields)), deepcopy(item["field"]))
    return result


def before_english_register_allowances(fixture, diagnostic="English register allowances"):
    """Require the complete current inventory, then re-insert the exact retired allowances."""
    require(digest(fixture) == ALLOWANCES["after_canonical_sha256"], diagnostic)
    result = _reinsert_allowances(fixture, diagnostic)
    require(digest(result) == ALLOWANCES["before_canonical_sha256"], diagnostic)
    return result


def before_english_register_allowance_frame(fixture, diagnostic="retired legacy allowance"):
    """Re-insert the exact retired allowances for an older inventory oracle.

    A reintroduced retired allowance is rejected here; every other difference stays in
    the copy and reaches the older oracle's own diagnostic.
    """
    return _reinsert_allowances(fixture, diagnostic)


CAPTIONS = {
    (row["text"], tuple(row["words"])): (row["before"], row["after"]) for row in DATA["captions"]
}


def english_register_caption_successor(language, text, words, pinned):
    """The exact current caption that supersedes a pinned predecessor caption, or None."""
    if language != "en":
        return None
    before, after = CAPTIONS.get((text, tuple(words)), (None, None))
    return after if pinned == before else None

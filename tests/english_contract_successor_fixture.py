"""Exact English contract successors, reversed only on historical comparison copies.

Eight contemporary prayer conclusions read "forever and ever", the Supplices
Communion clause reads "receive", four future captions read "will", and the
opening verse of Psalm 42 reads "set my cause apart from the unholy nation"
with one "my cause" caption. Older exact comparisons first undo these declared
changes on a copy; every other byte and field must still match its oracle.
"""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from foot_communion_successor_fixture import (
    before_foot_communion_bytes,
    before_foot_communion_layer_frame,
    before_foot_communion_object,
)
from reader_arrow_successor_fixture import before_arrow_bytes, before_arrow_object
from split_segment_uses_successor_fixture import before_split_uses_bytes, before_split_uses_object

from build_reader.bibliography_bindings import digest

DATA = json.loads(
    (Path(__file__).parent / "fixtures/english-contract-2026-10-29.json").read_bytes()
)
FILES = DATA["files"]
LAYERS = frozenset(relative for relative in FILES if relative.startswith("languages/en/texts/"))
RECORDS = frozenset(("languages/en/bibliography.json", "languages/en/translation-basis.json"))


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
    """Word cards and alignment groups; segment prose stays outside a caption frame."""
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
        if operation["before_exists"]:
            container[key] = deepcopy(operation["before"])
        else:
            del container[key]
    return result


def before_english_contract_object(relative, value, diagnostic="English contract comparison"):
    """Require the complete current object, then recover only the declared predecessor."""
    value = before_split_uses_object(relative, value)
    value = before_arrow_object(relative, value)
    rule = FILES.get(relative)
    if rule is None:
        return value
    value = before_foot_communion_object(relative, value, diagnostic)
    require(digest(value) == rule["after_canonical_sha256"], diagnostic)
    result = inverse(rule, value, diagnostic)
    require(digest(result) == rule["before_canonical_sha256"], diagnostic)
    return result


def before_english_contract_frame(relative, value, project, diagnostic="English contract frame"):
    """Undo caption changes; prose returns only where it is exactly the declared successor.

    Any other prose value, including a prose fault, stays in the copy for its own oracle.
    """
    rule = FILES.get(relative)
    if rule is None:
        return value
    value = before_foot_communion_layer_frame(value, diagnostic)
    if "after_caption_sha256" in rule:
        require(digest(project(value)) == rule["after_caption_sha256"], diagnostic)
        result = inverse(rule, value, diagnostic, caption_operation)
        require(digest(project(result)) == rule["before_caption_sha256"], diagnostic)
    else:
        result = deepcopy(value)
    for operation in rule["object_inverse"]:
        if caption_operation(operation):
            continue
        _, segment, field = operation["path"]
        assert field == "translation"
        row = result["segments"][segment]
        if row.get("translation") == operation["after"]:
            row["translation"] = operation["before"]
    return result


def before_english_contract_bytes(relative, raw, diagnostic="English contract comparison bytes"):
    """Require every current byte, then restore only the declared earlier lines."""
    raw = before_split_uses_bytes(relative, raw)
    raw = before_arrow_bytes(relative, raw)
    rule = FILES.get(relative)
    if rule is None:
        return raw
    raw = before_foot_communion_bytes(relative, raw, diagnostic)
    require(hashlib.sha256(raw).hexdigest() == rule["after_raw_sha256"], diagnostic)
    result = raw
    for operation in reversed(rule["raw_inverse"]):
        after, before = operation["after"].encode(), operation["before"].encode()
        require(result.count(after) == operation["count"], diagnostic)
        result = result.replace(after, before, operation["count"])
    require(hashlib.sha256(result).hexdigest() == rule["before_raw_sha256"], diagnostic)
    require(digest(json.loads(result)) == rule["before_canonical_sha256"], diagnostic)
    return result


def before_english_contract_layer(relative, value, diagnostic="English contract layer"):
    """English text layers only; the ledger and records are reached through their own chains."""
    if relative not in LAYERS:
        return value
    return before_english_contract_object(relative, value, diagnostic)


def before_english_contract_layer_bytes(relative, raw, diagnostic="English contract layer bytes"):
    if relative not in LAYERS:
        return raw
    return before_english_contract_bytes(relative, raw, diagnostic)


def before_english_contract_record_bytes(relative, raw, diagnostic="English contract records"):
    """The English bibliography and basis registry, whose newest earlier successor is Requiem."""
    if relative not in RECORDS:
        return raw
    return before_english_contract_bytes(relative, raw, diagnostic)


def before_english_contract_prose(text, translations):
    """Map exact current prose back to its predecessor; any other value reaches the old oracle."""
    result = dict(translations)
    for segment, value in translations.items():
        before, after = PROSE.get((text, segment), (None, None))
        if after is not None and value == after:
            result[segment] = before
    return result


def before_english_contract_text_layer(layer, diagnostic="English contract layer"):
    """The same exact layer inverse, addressed by the layer's own text and language."""
    if layer.get("language") != "en" or not isinstance(layer.get("text"), str):
        return layer
    relative = f"languages/en/texts/{layer['text'].replace('.', '/', 1)}.json"
    return before_english_contract_layer(relative, layer, diagnostic)

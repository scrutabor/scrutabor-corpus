"""English possessive sweep B3 successors, reversed only on historical comparison copies.

In 131 English layers of the second third of the proprium, 390 Latin nouns with their
postposed possessive (with an adjective or a conjunct of the same noun phrase where it
belongs to it) share one caption, such as `Your mercy` for `misericórdiam tuam`; the
grouped words keep their cards without a direct gloss. Older exact comparisons first
undo these declared groups on a copy; the caller keeps the actual current file.

Each inverse is a pure function of its input and never reads the working tree. A
declared group is undone only where it stands exactly as declared, once in its
segment, with every grouped word card exactly as declared (a layer frame, such as
the reader's expanded layer, may carry further card fields, but no direct gloss),
so the predecessor, and any earlier state an older inverse in the same chain has
produced, passes unchanged, and every other difference, including a fault, reaches
the older oracle and its own diagnostic.
"""

import json
from copy import deepcopy
from pathlib import Path

from checks.layout import formatted

DATA = json.loads(
    (Path(__file__).parent / "fixtures/possessive-sweep-b3-successor.json").read_bytes()
)
FILES = DATA["files"]
TEXTS = {rule["text"]: rule for rule in FILES.values()}
WORDS = {
    (rule["text"], word): change
    for rule in FILES.values()
    for change in rule["groups"]
    for word in change["group"]["words"]
}


def _restored_card(card, before):
    """A frame card with its earlier direct gloss back in its earlier place."""
    result = {}
    for key, value in before.items():
        if key == "gloss":
            result[key] = value
        elif key in card:
            result[key] = deepcopy(card[key])
    for key, value in card.items():
        result.setdefault(key, deepcopy(value))
    return result


def _undo(rule, value, frame=False):
    if not isinstance(value, dict):
        return value
    if not isinstance(value.get("segments"), dict) or not isinstance(value.get("words"), dict):
        return value
    result = None
    for change in reversed(rule["groups"]):
        current = value if result is None else result
        segment = current["segments"].get(change["segment"])
        groups = segment.get("alignments") if isinstance(segment, dict) else None
        if not isinstance(groups, list) or groups.count(change["group"]) != 1:
            continue
        cards = current["words"]
        if frame:
            if not all(
                isinstance(cards.get(word), dict) and "gloss" not in cards[word]
                for word in change["after_entries"]
            ):
                continue
        elif any(cards.get(word) != entry for word, entry in change["after_entries"].items()):
            continue
        if result is None:
            result = deepcopy(value)
        segment = result["segments"][change["segment"]]
        segment["alignments"].remove(change["group"])
        if not segment["alignments"] and not change["had_alignments_before"]:
            del segment["alignments"]
        for word, entry in change["before_entries"].items():
            card = result["words"][word]
            result["words"][word] = _restored_card(card, entry) if frame else deepcopy(entry)
    return value if result is None else result


def before_possessive_b3_object(relative, value):
    """A parsed layer without the declared groups; unlisted files pass unchanged."""
    rule = FILES.get(relative)
    if rule is None:
        return value
    return _undo(rule, value)


def before_possessive_b3_bytes(relative, raw):
    """Whole-file bytes in the house layout; any other input reaches the old oracle."""
    rule = FILES.get(relative)
    if rule is None:
        return raw
    try:
        value = json.loads(raw)
    except ValueError:
        return raw
    if not isinstance(value, dict) or formatted(value).encode("utf-8") != raw:
        return raw
    result = _undo(rule, value)
    return raw if result is value else formatted(result).encode("utf-8")


def layer_relative(layer):
    """A layer's file, from its own text and language (`lang` in the reader's expansion)."""
    language = (layer.get("language") or layer.get("lang")) if isinstance(layer, dict) else None
    text = layer.get("text") if isinstance(layer, dict) else None
    if not isinstance(language, str) or not isinstance(text, str):
        return None
    return f"languages/{language}/texts/{text.replace('.', '/', 1)}.json"


def before_possessive_b3_layer(layer):
    """The same exact inverse, addressed by a layer's own text and language."""
    relative = layer_relative(layer)
    if relative is None:
        return layer
    return before_possessive_b3_object(relative, layer)


def before_possessive_b3_layer_frame(layer):
    """A layer-shaped frame without the declared groups; card fields other than gloss stay."""
    rule = FILES.get(layer_relative(layer))
    if rule is None:
        return layer
    return _undo(rule, layer, frame=True)


def possessive_b3_groups(language, text):
    """Copies of the declared changes of one current English layer (none for others)."""
    rule = TEXTS.get(text) if language == "en" else None
    return deepcopy(rule["groups"]) if rule else []


def possessive_b3_group(language, text, words, caption):
    """The declared change whose group now realizes a pinned one-word caption, or None.

    Only the exact earlier single caption of a grouped word is superseded.
    """
    if language != "en" or len(words) != 1:
        return None
    change = WORDS.get((text, words[0]))
    if change is None or change["before_entries"][words[0]].get("gloss") != caption:
        return None
    return deepcopy(change)


def possessive_b3_caption(language, text, words, caption):
    """(words, caption) of a pinned site, with a superseded one-word caption replaced."""
    change = possessive_b3_group(language, text, words, caption)
    if change is None:
        return tuple(words), caption
    return tuple(change["group"]["words"]), change["group"]["gloss"]


def possessive_b3_realization(layer, words):
    """The caption that realizes exactly these words in a layer, or None."""
    found = [
        group.get("gloss")
        for segment in layer["segments"].values()
        for group in segment.get("alignments") or []
        if group["words"] == list(words)
    ]
    if len(words) == 1 and not any(
        words[0] in group["words"]
        for segment in layer["segments"].values()
        for group in segment.get("alignments") or []
    ):
        found.append(layer["words"].get(words[0], {}).get("gloss"))
    return found[0] if len(found) == 1 else None

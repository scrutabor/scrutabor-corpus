"""Bounded current fields and historical inverses of the Ascension Sunday texts."""

import json
from copy import deepcopy
from pathlib import Path

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures/post-ascension-fields.json").read_text(encoding="utf-8")
)


def value_at(document, keys):
    value = document
    for key in keys:
        value = value[key]
    return value


def restore_layer(layer, relative):
    """Reverse only exact named current fields; preserve every other field."""
    result = deepcopy(layer)
    for field in FIXTURE["language_changes"][relative]:
        parent = value_at(result, field["keys"][:-1])
        key = field["keys"][-1]
        assert (key in parent) is field["after_present"], "current field presence"
        if field["after_present"]:
            assert parent[key] == field["after"], "current field value"
        if field["before_present"]:
            parent[key] = deepcopy(field["before"])
        else:
            parent.pop(key, None)
    return result


def expected_row_successor(row, site=None):
    """Advance a historical expected row, never normalize an actual observation."""
    result = deepcopy(row)
    change = FIXTURE["verse_rows"].get(site if site is not None else row["site"])
    if change is not None:
        assert result == {key: change["before"][key] for key in result}, "historical expected row"
        result.update({key: change["after"][key] for key in result})
    return result

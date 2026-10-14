"""Reverse explicit preface revisions without hiding unrelated changes."""

from copy import deepcopy

SACRIFICE = [f"w{i:03d}" for i in range(21, 27)]
ALTERNATIVES = {
    "for Christ, our Passover, has been sacrificed",
    "for Christ, our Pasch, has been sacrificed",
    "when Christ, our Passover, has been sacrificed",
}


def restore_preface_transitions(layer, fixture):
    """Check each exact postimage, then restore only its named predecessor.

    Complete arrays protect member IDs, anchors, order and captions. The
    previously supported sacrifice wordings survive the inverse unchanged.
    Unlisted fields survive too, so the earlier whole-layer digest still
    rejects unrelated additions or alterations.
    """
    value = deepcopy(layer)
    assert value["text"] == fixture["text"]
    for row in fixture["transitions"]:
        parts = row["path"].split("/")[1:]
        parent = value
        for part in parts[:-1]:
            parent = parent[part.replace("~1", "/").replace("~0", "~")]
        key = parts[-1].replace("~1", "/").replace("~0", "~")
        assert (key in parent) == row["after_present"]
        before, after = deepcopy(row["before"]), deepcopy(row["after"])
        if row["path"] == "/segments/s01/alignments":
            actual = parent[key]
            chosen = [group for group in actual if group["words"] == SACRIFICE]
            assert len(chosen) == 1 and chosen[0]["gloss"] in ALTERNATIVES
            for groups in (before, after):
                group = next(group for group in groups if group["words"] == SACRIFICE)
                group["gloss"] = chosen[0]["gloss"]
        if row["after_present"]:
            assert parent[key] == after
        if row["before_present"]:
            parent[key] = before
        else:
            del parent[key]
    return value

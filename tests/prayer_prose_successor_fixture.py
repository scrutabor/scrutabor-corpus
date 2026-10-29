"""Exact prayer prose successors, reversed on comparison copies only."""

import json
from copy import deepcopy
from pathlib import Path

from requiem_successor_fixture import before_requiem_ledger

from build_reader.bibliography_bindings import digest

DATA = json.loads((Path(__file__).parent / "fixtures/prayer-prose-successors.json").read_bytes())
SITES = {
    "en": (
        "proprium.dominica-ii-post-pentecosten-postcommunio.s01.en",
        "orationes.anima-christi.s07.en",
        "orationes.anima-christi.s08.en",
        "orationes.anima-christi.s11.en",
        "orationes.anima-christi.s12.en",
    ),
    "pl": ("ordinarium.quod-ore-sumpsimus.s02.pl",),
}
BEFORE = {
    "en": "b58e95b122b19efb9c36338996d99ccc8e844039b48850a0d819156728f02321",
    "pl": "7bcbaa7be367500bd12867c9dcc6d9ece3441b595626d8090e7ff8acb7ee4860",
}
AFTER = {
    "en": "9afe6812733acba62399d5e5fd0f9d9e2fd9aeebcb00c2871194a6b0c0dba0fb",
    "pl": "471c3f6ec820bf49059aa1f0aa0a33ccf03af11b83aa390167a061837516da33",
}


def before_prayer_prose_ledger(relative, value, diagnostic="prayer prose ledger"):
    """Guard the complete native ledger, then unwind its exact rows on a copy."""
    assert relative in (
        "languages/en/translation-provenance.json",
        "languages/pl/translation-provenance.json",
    ), diagnostic
    value = before_requiem_ledger(relative, value, diagnostic)
    language = relative.split("/")[1]
    rule = DATA["ledgers"][language]
    assert rule["relative"] == relative, diagnostic
    assert rule["before_canonical_sha256"] == BEFORE[language], diagnostic
    assert rule["after_canonical_sha256"] == AFTER[language], diagnostic
    assert digest(value) == AFTER[language], diagnostic
    assert tuple(change["site"] for change in rule["rows"]) == SITES[language], diagnostic
    result = deepcopy(value)
    for change in rule["rows"]:
        before, after = change["before"], change["after"]
        assert before["site"] == after["site"] == change["site"], diagnostic
        assert before["language"] == after["language"] == language, diagnostic
        indices = [i for i, row in enumerate(value["sites"]) if row["site"] == change["site"]]
        assert indices == [change["ledger_index"]], diagnostic
        (index,) = indices
        assert value["sites"][index] == after, diagnostic
        assert before.keys() == after.keys(), diagnostic
        changed = {key for key in before if before[key] != after[key]}
        if language == "pl":
            assert changed == {"target_sha256", "review"}, diagnostic
            assert before["origin"] == after["origin"] == "own", diagnostic
            assert before["review"] == "internally-reviewed", diagnostic
        elif change["site"].startswith("orationes.anima-christi."):
            assert changed == {"target_sha256", "review"}, diagnostic
            assert before["origin"] == after["origin"] == "public-domain", diagnostic
            assert before["review"] == "internally-reviewed", diagnostic
        else:
            assert changed == {"target_sha256"}, diagnostic
            assert before["origin"] == after["origin"] == "working-unsettled", diagnostic
            assert before["review"] == "working", diagnostic
        assert after["review"] == "working", diagnostic
        assert before["familiar_core"] is after["familiar_core"] is False, diagnostic
        result["sites"][index] = deepcopy(before)
    assert digest(result) == BEFORE[language], diagnostic
    return result

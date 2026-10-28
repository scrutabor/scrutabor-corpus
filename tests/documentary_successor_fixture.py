"""Exact additional source and language inverses on comparison copies only."""

import json
from copy import deepcopy
from pathlib import Path

from anne_documentary_fixture import (
    before_anne_graph,
    before_anne_records,
    before_anne_registry,
)
from lateran_epistle_source_fixture import before_lateran_graph, before_lateran_registry
from lauda_sion_fixture import FIXTURE as LAUDA
from lauda_sion_fixture import SITES as LAUDA_SITES
from michael_gospel_source_fixture import before_michael_records, before_michael_registry
from rosary_gospel_source_fixture import before_rosary_graph, before_rosary_registry

from build_reader.bibliography_bindings import digest

DATA = json.loads(
    (Path(__file__).parent / "fixtures/documentary-successor-comparisons.json").read_bytes()
)


def before_additional_records(value):
    return before_michael_records(before_anne_records(value))


def before_additional_registry(value):
    return before_michael_registry(before_anne_registry(value))


def before_documentary_graph(value):
    return before_lateran_graph(
        before_rosary_graph(before_michael_records(before_anne_graph(value)))
    )


def before_documentary_registry(value):
    return before_lateran_registry(before_rosary_registry(before_additional_registry(value)))


LEDGER_FRAMES = {
    "languages/pl/translation-provenance.json": {
        "current": "7bcbaa7be367500bd12867c9dcc6d9ece3441b595626d8090e7ff8acb7ee4860",
        "before": "ee1185709cd01a70272dca47a011be2e2da0bd830f43e31da7d9c55e599ef73b",
    },
    "languages/en/translation-provenance.json": {
        "current": "3edc5c81782aa9ed44eab039d9e9a96529bc1b5a100bc2eaebfc9ab71ff525eb",
        "before": "81de755211f21fbd335525a4c8a57850f8e381f2788a66866c6cf3d1cf592474",
    },
}


AGENCY_EN_ROW = {
    "site": "proprium.assumptio-beatae-mariae-virginis-postcommunio.s01.en",
    "text": "proprium.assumptio-beatae-mariae-virginis-postcommunio",
    "segment": "s01",
    "language": "en",
    "familiar_core": False,
    "origin": "working-unsettled",
    "review": "working",
    "source_sha256": "71ac0007736a7cb9b41e4562cc6fdda51731b471830f4f959dea5d5b5d84475a",
    "target_sha256": "76166504f422490971ae795696252da168e8e4357ef43e9b015d432c2d24eb47",
}
AGENCY_EN_AFTER_TARGET = "5304dfc0cef8c7797f7eeff966a994655d14084de5d521d3dc9656b4c556a1b4"
AGENCY_EN_CURRENT = "b58e95b122b19efb9c36338996d99ccc8e844039b48850a0d819156728f02321"


def before_agency_ledger(relative, value, diagnostic="agency current ledger"):
    """Reverse one exact new target digest on an expected-side copy only."""
    assert relative in LEDGER_FRAMES, diagnostic
    if relative != "languages/en/translation-provenance.json":
        return deepcopy(value)
    assert digest(value) == AGENCY_EN_CURRENT, diagnostic
    indices = [i for i, row in enumerate(value["sites"]) if row["site"] == AGENCY_EN_ROW["site"]]
    assert len(indices) == 1, diagnostic
    (index,) = indices
    assert value["sites"][index] == {**AGENCY_EN_ROW, "target_sha256": AGENCY_EN_AFTER_TARGET}, (
        diagnostic
    )
    result = deepcopy(value)
    result["sites"][index] = deepcopy(AGENCY_EN_ROW)
    assert digest(result) == LEDGER_FRAMES[relative]["current"], diagnostic
    return result


def predecessor_ledger(relative, value, diagnostic="Lauda current ledger"):
    """Unwind exactly six Lauda rows on a guarded comparison copy, never native input."""
    assert relative in LEDGER_FRAMES, diagnostic
    value = before_agency_ledger(relative, value, diagnostic)
    rule = LEDGER_FRAMES[relative]
    assert rule["before"] == DATA["ledgers"][relative]["after_sha256"], diagnostic
    assert digest(value) == rule["current"], diagnostic
    assert len(LAUDA["ledger"]) == 6, diagnostic
    assert {row["site"] for row in LAUDA["ledger"]} == LAUDA_SITES, diagnostic
    language = relative.split("/")[1]
    changes = [row for row in LAUDA["ledger"] if row["after"]["language"] == language]
    assert len(changes) == (5 if language == "pl" else 1), diagnostic
    result = deepcopy(value)
    for change in changes:
        assert {
            key for key in change["before"] if change["before"][key] != change["after"][key]
        } == {"target_sha256"}, diagnostic
        indices = [i for i, row in enumerate(result["sites"]) if row["site"] == change["site"]]
        assert len(indices) == 1, diagnostic
        (index,) = indices
        assert result["sites"][index] == change["after"], diagnostic
        result["sites"][index] = deepcopy(change["before"])
    assert digest(result) == rule["before"], diagnostic
    return result


def before_language_successors(relative, value, diagnostic="exact Joachim target successor"):
    rule = DATA["ledgers"][relative]
    result = predecessor_ledger(relative, value, diagnostic)
    assert digest(result) == rule["after_sha256"], diagnostic
    for change in rule["rows"]:
        indices = [
            i for i, row in enumerate(result["sites"]) if row["site"] == change["after"]["site"]
        ]
        assert len(indices) == 1, diagnostic
        (index,) = indices
        assert result["sites"][index] == change["after"], diagnostic
        result["sites"][index] = deepcopy(change["before"])
    assert digest(result) == rule["before_sha256"], diagnostic
    return result

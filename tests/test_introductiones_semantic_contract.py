"""The emitted contract rejects known vocabulary used in the wrong semantic role."""

from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import introductiones as reader

ROOT = Path(__file__).resolve().parents[1]


def change_delivery(table, event, index, form, **values):
    next(e for e in table["events"] if e["id"] == event)["occurrences"][index][form].update(values)


FAULTS = {
    "greeting-low-server": lambda t: change_delivery(
        t, "collecta-introductio", 0, "lecta", speaker="minister"
    ),
    "greeting-sung-choir": lambda t: change_delivery(
        t, "collecta-introductio", 0, "cantu", speaker="schola"
    ),
    "response-low-priest": lambda t: change_delivery(
        t, "collecta-introductio", 1, "lecta", speaker="sacerdos"
    ),
    "response-sung-priest": lambda t: change_delivery(
        t, "collecta-introductio", 1, "cantu", speaker="sacerdos"
    ),
    "epistle-choir": lambda t: change_delivery(
        t, "epistola-annuntiatio", 0, "cantu", speaker="schola"
    ),
    "epistle-sung": lambda t: change_delivery(
        t, "epistola-annuntiatio", 0, "cantu", voice="cantus"
    ),
    "gospel-spoken": lambda t: change_delivery(
        t, "evangelium-annuntiatio", 0, "cantu", voice="clara"
    ),
    "wrong-known-before": lambda t: t["events"][0].update(before="secreta"),
    "wrong-known-order": lambda t: t["events"][0]["occurrences"].reverse(),
    "missing-occurrence": lambda t: t["events"][0]["occurrences"].pop(),
    "passion-known-wrong-unit": lambda t: t["passion"].update(
        units=["sequentia-sancti-evangelii-secundum-matthaeum"]
    ),
    "passion-choir": lambda t: t["passion"]["cantu"].update(speaker="schola"),
    "zero-chapter": lambda t: t["announcements"][0]["pericope"]["passages"][0].update(chapter=0),
}


@pytest.mark.parametrize("fault", list(FAULTS))
def test_emitted_semantic_mutation_rejects_then_pristine_passes(fault):
    pristine = reader.resource(ROOT)
    reader.validate(pristine)
    damaged = deepcopy(pristine)
    FAULTS[fault](damaged)
    assert damaged != pristine
    with pytest.raises(ValueError, match="introductiones:"):
        reader.validate(damaged)
    reader.validate(pristine)

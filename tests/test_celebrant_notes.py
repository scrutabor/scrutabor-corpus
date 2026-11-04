"""Rubrical descriptions identify the celebrant who performs the action."""

from pathlib import Path

import pytest
from test_requiem_body_contracts import ordo_note_pronoun_openings

from build_reader import store

ROOT = Path(__file__).resolve().parents[1]
PRIEST_NOTES = [
    "ordinarium.benedictio",
    "ordinarium.confiteor-sacerdotis",
    "ordinarium.ecce-agnus-dei",
    "ordinarium.evangelium-ultimum",
    "ordinarium.fili-dei-vivi",
    "ordinarium.haec-commixtio",
    "ordinarium.hanc-igitur",
    "ordinarium.memento-defunctorum",
    "ordinarium.per-ipsum",
    "ordinarium.placeat-tibi",
    "ordinarium.qui-pridie",
    "ordinarium.suscipe-sancte-pater",
    "proprium.commemoratio-omnium-fidelium-defunctorum-missa-i-sequentia",
]


@pytest.mark.parametrize("text", PRIEST_NOTES)
def test_note_names_the_celebrant_and_avoids_ambiguous_openings(text):
    about = store.raw_layer(ROOT, "en", text)["about"]
    assert "priest" in about.lower()
    assert ordo_note_pronoun_openings(about) == []

"""Keep the alternative reading legible in plain notes, without leaking IDs."""

from copy import deepcopy

import pytest
from test_dawn_postcommunio_nativity import load_case

from build_reader.layers import enrich_layer, expand_core
from checks import prose
from checks.lint import lint_gloss

NOTES = {
    "pl": (
        "Możliwy jest także mianownik, w którym „natális” zgadza się z „nóvitas”. "
        "Sam zapis nie rozstrzyga przypadku."
    ),
    "en": (
        "The form can also be a nominative agreeing with “nóvitas”. "
        "The spelling alone does not settle the case."
    ),
}


def require_note(core, layer, language):
    assert prose.check(layer) == [], "plain note prose"
    assert lint_gloss(enrich_layer(core, layer), expand_core(core)) == [], "reader terminology"
    assert layer["words"]["w007"]["note"] == NOTES[language], "alternative wording"


@pytest.mark.parametrize("language", ["pl", "en"])
def test_actual_alternative_note_is_plain_and_keeps_uncertainty(language):
    core, layers = load_case()
    require_note(core, layers[language], language)


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("fault", ["raw-id", "semicolon", "certainty"])
def test_note_guards_reject_the_individual_defect_and_recover(language, fault):
    core, layers = load_case()
    layer = layers[language]
    require_note(core, layer, language)
    snapshot = deepcopy(layer)
    note = layer["words"]["w007"]
    if fault == "raw-id":
        note["note"] += " (w006)"
        errors = prose.check(layer)
        assert len(errors) == 1 and "bare word-id" in errors[0]
    elif fault == "semicolon":
        note["note"] = note["note"].replace(". ", "; ", 1)
        errors = prose.check(layer)
        assert len(errors) == 1 and "uses a semicolon" in errors[0]
    else:
        note["note"] = "The nominative reading is impossible."
    with pytest.raises(
        AssertionError, match="alternative wording" if fault == "certainty" else "plain note prose"
    ):
        require_note(core, layer, language)
    note["note"] = snapshot["words"]["w007"]["note"]
    assert layer == snapshot
    require_note(core, layer, language)

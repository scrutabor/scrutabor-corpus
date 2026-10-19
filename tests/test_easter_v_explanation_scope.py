"""Optional contextual explanations declare their actual language coverage."""

from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import store
from checks.language_packs import check_core, check_layer

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "part,word_id",
    [("epistola", "w025"), ("introitus", "w028"), ("offertorium", "w027")],
)
def test_polish_context_explanation_has_explicit_language_scope(part, word_id):
    text_id = f"proprium.dominica-v-post-pascha-{part}"
    core = store.core(ROOT, text_id)
    layers = {language: store.raw_layer(ROOT, language, text_id) for language in ("en", "pl")}
    assert check_core(core) == []
    for language in ("en", "pl"):
        path = store.layer_path(ROOT, language, text_id)
        assert check_layer(core, layers[language], path) == []
    assert core["localization"]["explanations"][word_id] == {"languages": ["pl"]}
    assert layers["pl"]["words"][word_id]["explanation"].strip()
    assert "explanation" not in layers["en"]["words"][word_id]

    undeclared = deepcopy(core)
    del undeclared["localization"]["explanations"][word_id]
    errors = check_layer(undeclared, layers["pl"], store.layer_path(ROOT, "pl", text_id))
    assert errors == [
        f"pl:{text_id}: explanation topology differs — missing=[] extra=['{word_id}']"
    ]

    unsupported = deepcopy(core)
    unsupported["localization"]["explanations"][word_id] = {}
    errors = check_layer(unsupported, layers["en"], store.layer_path(ROOT, "en", text_id))
    assert errors == [
        f"en:{text_id}: explanation topology differs — missing=['{word_id}'] extra=[]"
    ]

"""Language-specific commentary keeps strict declared presence and shared duties."""

from copy import deepcopy
from pathlib import Path

import pytest

from checks.language_packs import check_core, check_layer


def subject(requirement):
    core = {
        "id": "proprium.test",
        "category": "proprium",
        "schema_version": "0.21.0",
        "localization": {"about": True, "explanations": {"w001": requirement}},
        "segments": [{"id": "s01", "type": "verse", "words": [{"id": "w001"}]}],
    }
    layers = {
        lang: {
            "schema_version": "0.21.0",
            "language": lang,
            "text": core["id"],
            "about": "Commentary.",
            "segments": {"s01": {"translation": "Prayer."}},
            "words": {"w001": {"gloss": "word"}},
        }
        for lang in ("en", "pl")
    }
    return core, layers


def layer_errors(core, layer):
    return check_layer(
        core, layer, Path("languages") / layer["language"] / "texts/proprium/test.json"
    )


def test_scoped_note_is_required_only_in_its_language():
    core, layers = subject({"languages": ["en"]})
    layers["en"]["words"]["w001"]["explanation"] = "English wording needs this note."
    assert check_core(core) == []
    assert all(layer_errors(core, layer) == [] for layer in layers.values())
    broken = deepcopy(layers["en"])
    del broken["words"]["w001"]["explanation"]
    assert any("topology differs" in error for error in layer_errors(core, broken))
    extra = deepcopy(layers["pl"])
    extra["words"]["w001"]["explanation"] = "Unrequested counterpart."
    assert any("topology differs" in error for error in layer_errors(core, extra))


@pytest.mark.parametrize("requirement", [{}, {"languages": ["en", "pl"]}])
def test_default_and_explicit_shared_notes_keep_bilingual_obligation(requirement):
    core, layers = subject(requirement)
    for layer in layers.values():
        assert any("topology differs" in error for error in layer_errors(core, layer))
        layer["words"]["w001"]["explanation"] = "A shared note."
        assert layer_errors(core, layer) == []


@pytest.mark.parametrize("languages", [[], "en", ["en", "en"], ["pl", "en"], ["fr"], [1], [None]])
def test_malformed_scopes_are_rejected(languages):
    core, _ = subject({"languages": languages})
    assert any("explanation languages" in error for error in check_core(core))


@pytest.mark.parametrize("structural", [{"ellipsis": "est"}, {"clause_head": "w001"}])
def test_structural_explanations_cannot_be_scoped_away(structural):
    core, _ = subject({"languages": ["en"]})
    core["segments"][0]["words"][0].update(structural)
    assert any("must cover en and pl" in error for error in check_core(core))


def test_scoped_citations_wait_for_a_language_projection_contract():
    core, _ = subject({"languages": ["en"], "citations": [{"source": "test"}]})
    assert any("language-scoped explanation citations" in error for error in check_core(core))


def test_malformed_clause_head_is_rejected_without_breaking_scope_validation():
    core, _ = subject({"languages": ["en"]})
    core["segments"][0]["words"][0]["clause_head"] = ["w001"]
    assert any("clausal complement" in error for error in check_core(core))

"""An understood participial subject is an explicit, constrained syntax claim."""

from pathlib import Path

import pytest

from build_reader.emit import Table, core_artifact, expand
from checks.language_packs import check_core, check_layer
from checks.syntax import check, coverage


def subject_ellipsis():
    return {
        "id": "proprium.example",
        "category": "proprium",
        "schema_version": "0.20.0",
        "localization": {"about": True, "explanations": {"w001": {}}},
        "segments": [
            {
                "id": "s01",
                "type": "verse",
                "words": [
                    {
                        "id": "w001",
                        "form": "pacíficans",
                        "lemma": "pacifico",
                        "morph": {
                            "pos": "verb",
                            "mood": "part",
                            "case": "nom",
                            "number": "sg",
                            "gender": "m",
                            "tense": "pres",
                            "voice": "act",
                        },
                        "ellipsis": "subject",
                    }
                ],
            }
        ],
    }


def test_subject_ellipsis_needs_no_invented_head_or_substantive():
    value = subject_ellipsis()
    assert check(value) == []
    assert check_core(value) == []
    assert coverage(value) == (1, 1)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("pos", "adj"),
        ("pos", "noun"),
        ("mood", "ind"),
        ("mood", "inf"),
        ("case", "acc"),
        ("case", "abl"),
        ("number", "dual"),
        ("gender", "common"),
        ("tense", "impf"),
        ("voice", "unknown"),
    ],
)
def test_subject_marker_cannot_waive_incompatible_morphology(field, value):
    fixture = subject_ellipsis()
    fixture["segments"][0]["words"][0]["morph"][field] = value
    assert any("fully specified nominative participle" in error for error in check(fixture))


@pytest.mark.parametrize("field", ["pos", "mood", "case", "number", "gender", "tense", "voice"])
def test_subject_marker_requires_each_morphological_feature(field):
    fixture = subject_ellipsis()
    fixture["segments"][0]["words"][0]["morph"].pop(field)
    assert any("fully specified nominative participle" in error for error in check(fixture))


@pytest.mark.parametrize("field,value", [("head", "w001"), ("substantive", True)])
def test_subject_marker_is_exclusive_of_other_syntax_claims(field, value):
    fixture = subject_ellipsis()
    fixture["segments"][0]["words"][0][field] = value
    assert any("cannot also carry" in error for error in check(fixture))


def test_subject_marker_requires_a_declared_explanation():
    fixture = subject_ellipsis()
    fixture["localization"].pop("explanations")
    assert any("requires a contextual explanation" in error for error in check_core(fixture))


def test_subject_marker_survives_the_actual_reader_codec():
    core = subject_ellipsis()
    core.update(
        status="draft",
        analysis_defaults={"confidence": "medium", "review": "pending", "sources": []},
    )
    parses, analyses, citations = Table(), Table(), Table()
    artifact = core_artifact(core, core, parses, analyses, citations)
    assert artifact["seg"][0]["w"][0]["el"] == "subject"
    language = {"language": "en", "about": "", "seg": [{"id": "s01", "g": [None]}]}
    expanded, _ = expand(artifact, language, parses.order, analyses.order, citations.order, [])
    assert expanded["segments"][0]["words"] == core["segments"][0]["words"]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_subject_explanation_cannot_disappear_from_a_language_package(language):
    core = subject_ellipsis()
    layer = {
        "schema_version": core["schema_version"],
        "language": language,
        "text": core["id"],
        "about": "A contextual syntax fixture.",
        "segments": {"s01": {"translation": "Making peace."}},
        "words": {"w001": {"gloss": "making peace", "explanation": "Its subject is understood."}},
    }
    path = Path(language) / "texts/proprium/example.json"
    assert check_layer(core, layer, path) == []
    del layer["words"]["w001"]["explanation"]
    assert any("explanation topology differs" in error for error in check_layer(core, layer, path))

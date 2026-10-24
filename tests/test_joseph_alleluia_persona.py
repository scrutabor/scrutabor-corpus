"""Joseph Alleluia human reference and its local protective construction."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.layers import expand_core
from checks import interlinear, prose
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.sancti-ioseph-opificis-alleluia"
CORE = "texts/" + TEXT.replace(".", "/", 1) + ".json"
GROUP = {
    "words": ["w024", "w025", "w026", "w027"],
    "anchor": "w026",
    "gloss": "zawsze bezpieczne pod twoją opieką",
}


EN_GROUPS = [
    {"words": ["w013", "w014"], "anchor": "w013", "gloss": "their protector"},
    {
        "words": ["w024", "w025", "w026", "w027"],
        "anchor": "w026",
        "gloss": "always safe under your protection",
    },
]


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def documents():
    return {
        "core": read(CORE),
        "layers": {language: read(f"languages/{language}/{CORE}") for language in ("pl", "en")},
        "sites": {
            language: next(
                row
                for row in read(f"languages/{language}/translation-provenance.json")["sites"]
                if row["site"] == f"{TEXT}.s01.{language}"
            )
            for language in ("pl", "en")
        },
    }


def assert_case(layer, language):
    translation = layer["segments"]["s01"]["translation"]
    wanted, rejected, gloss = (
        ("zawołają do mnie, wysłucham", "do Mnie", "mnie")
        if language == "pl"
        else ("they cry to me, I will hear", "to Me", "me")
    )
    require(
        wanted in translation and rejected not in translation,
        f"Joseph human-reference case: {language} prose",
    )
    require(
        layer["words"]["w008"].get("gloss") == gloss,
        f"Joseph human-reference case: {language} caption",
    )
    if language == "en":
        require(
            layer["words"]["w009"].get("gloss") == "I will hear"
            and layer["words"]["w012"].get("gloss") == "I will be",
            "Joseph English first person",
        )


def assert_group(layer):
    groups = layer["segments"]["s01"].get("alignments") or []
    require(
        groups == [GROUP] and all("gloss" not in layer["words"][word] for word in GROUP["words"]),
        "Joseph protective construction",
    )


def assert_en_group(layer):
    require(
        layer["segments"]["s01"].get("alignments") == EN_GROUPS
        and all("gloss" not in layer["words"][word] for word in GROUP["words"]),
        "Joseph English protective construction",
    )


def assert_roles(core):
    segment = core["segments"][0]
    require(
        segment["speaker"] == "sacerdos"
        and segment["voice"] == "clara"
        and segment["delivery"] == {"cantu": {"speaker": "schola", "voice": "cantus"}},
        "Joseph ritual roles are not the literary persona",
    )


def assert_site(core, layer, row, language):
    require(
        row["site"] == f"{TEXT}.s01.{language}"
        and row["text"] == TEXT
        and row["segment"] == "s01"
        and row["language"] == language
        and row["familiar_core"] is False
        and row["origin"] == "working-unsettled"
        and row["review"] == "working"
        and row["source_sha256"] == canonical_hash(source_payload(core["segments"][0]))
        and row["target_sha256"] == canonical_hash(layer["segments"]["s01"]["translation"]),
        f"Joseph provenance site: {language}",
    )


def test_actual_human_reference_group_roles_and_current_provenance(documents):
    core = documents["core"]
    assert_roles(core)
    assert_group(documents["layers"]["pl"])
    assert_en_group(documents["layers"]["en"])
    for language in ("pl", "en"):
        layer = documents["layers"][language]
        assert_case(layer, language)
        assert_site(core, layer, documents["sites"][language], language)
        assert interlinear.check(expand_core(core), layer) == []


@pytest.mark.parametrize("language", ("pl", "en"))
@pytest.mark.parametrize("surface", ("prose", "caption"))
def test_independent_case_mutants_are_rejected_and_healthy_layer_survives(
    documents, language, surface
):
    layer = documents["layers"][language]
    assert_case(layer, language)
    bad = deepcopy(layer)
    if surface == "prose":
        before, after = ("do mnie", "do Mnie") if language == "pl" else ("to me", "to Me")
        bad["segments"]["s01"]["translation"] = bad["segments"]["s01"]["translation"].replace(
            before, after
        )
    else:
        bad["words"]["w008"]["gloss"] = "Mnie" if language == "pl" else "Me"
    with pytest.raises(AssertionError) as caught:
        assert_case(bad, language)
    assert str(caught.value) == f"Joseph human-reference case: {language} {surface}"
    assert_case(layer, language)


def test_human_english_first_person_is_still_capitalized(documents):
    layer = documents["layers"]["en"]
    assert_case(layer, "en")
    bad = deepcopy(layer)
    bad["words"]["w009"]["gloss"] = "i will hear"
    with pytest.raises(AssertionError) as caught:
        assert_case(bad, "en")
    assert str(caught.value) == "Joseph English first person"
    assert_case(layer, "en")


@pytest.mark.parametrize("defect", ("wording", "anchor"))
def test_local_protective_construction_has_its_real_relation(documents, defect):
    layer = documents["layers"]["pl"]
    assert_group(layer)
    bad = deepcopy(layer)
    group = bad["segments"]["s01"]["alignments"][0]
    group["gloss" if defect == "wording" else "anchor"] = (
        "zawsze bezpieczne twoją opieką" if defect == "wording" else "w024"
    )
    with pytest.raises(AssertionError) as caught:
        assert_group(bad)
    assert str(caught.value) == "Joseph protective construction"
    assert_group(layer)


@pytest.mark.parametrize("language", ("pl", "en"))
@pytest.mark.parametrize("defect", ("missing", "duplicate", "noncontiguous"))
def test_real_interlinear_consumer_rejects_membership_damage(documents, language, defect):
    core, layer = expand_core(documents["core"]), documents["layers"][language]
    assert interlinear.check(core, layer) == []
    bad = deepcopy(layer)
    group_index = 0 if language == "pl" else 1
    if defect == "missing":
        del bad["segments"]["s01"]["alignments"][group_index]
    elif defect == "duplicate":
        bad["words"]["w024"]["gloss"] = "twoją" if language == "pl" else "your"
    else:
        bad["segments"]["s01"]["alignments"][group_index]["words"] = ["w024", "w026", "w027"]
    expected = (
        f"{TEXT}:s01:alignment-{group_index + 1}:{language}: "
        "aligned words must be contiguous and in source order"
        if defect == "noncontiguous"
        else f"{TEXT}:w024:{language}: expected exactly one direct gloss or alignment"
    )
    assert expected in interlinear.check(core, bad)
    assert interlinear.check(core, layer) == []


@pytest.mark.parametrize("mode", ("recited", "sung"))
def test_literary_persona_does_not_replace_actual_ritual_role(documents, mode):
    core = documents["core"]
    assert_roles(core)
    bad = deepcopy(core)
    if mode == "recited":
        bad["segments"][0]["speaker"] = "Ioseph"
    else:
        bad["segments"][0]["delivery"]["cantu"]["speaker"] = "Ioseph"
    with pytest.raises(AssertionError) as caught:
        assert_roles(bad)
    assert str(caught.value) == "Joseph ritual roles are not the literary persona"
    assert_roles(core)


@pytest.mark.parametrize("language", ("pl", "en"))
@pytest.mark.parametrize("defect", ("stale-target", "promoted-review"))
def test_current_hashes_do_not_promote_working_provenance(documents, language, defect):
    core, layer = documents["core"], documents["layers"][language]
    row = documents["sites"][language]
    assert_site(core, layer, row, language)
    bad = deepcopy(row)
    bad["target_sha256" if defect == "stale-target" else "review"] = (
        "0" * 64 if defect == "stale-target" else "reviewed"
    )
    with pytest.raises(AssertionError) as caught:
        assert_site(core, layer, bad, language)
    assert str(caught.value) == f"Joseph provenance site: {language}"
    assert_site(core, layer, row, language)


@pytest.mark.parametrize("defect", ("wording", "anchor"))
def test_english_local_group_preserves_protection_and_earlier_group(documents, defect):
    layer = documents["layers"]["en"]
    assert_en_group(layer)
    bad = deepcopy(layer)
    group = bad["segments"]["s01"]["alignments"][1]
    group["gloss" if defect == "wording" else "anchor"] = (
        "always safe under protection" if defect == "wording" else "w024"
    )
    with pytest.raises(AssertionError) as caught:
        assert_en_group(bad)
    assert str(caught.value) == "Joseph English protective construction"
    assert_en_group(layer)


@pytest.mark.parametrize("language", ("pl", "en"))
def test_persona_explanation_passes_native_prose_and_rejects_old_punctuation(documents, language):
    layer = documents["layers"][language]
    about = {
        "pl": "Alleluia formularza „Świętego Józefa Rzemieślnika” w Mszale Rzymskim z 1962 roku. "
        "Pierwszy werset przemawia w imieniu świętego Józefa. "
        "Drugi jest prośbą Kościoła skierowaną do niego.",
        "en": "The alleluia of the formulary “Saint Joseph the Worker” in the 1962 Roman Missal. "
        "The first verse speaks in Saint Joseph’s voice. "
        "The second is the Church’s prayer addressed to him.",
    }[language]
    assert prose.check(layer) == []
    assert layer["about"] == about
    bad = deepcopy(layer)
    before, after = (
        ("Józefa. Drugi", "Józefa; drugi")
        if language == "pl"
        else ("voice. The second", "voice; the second")
    )
    assert bad["about"].count(before) == 1
    bad["about"] = bad["about"].replace(before, after)
    assert prose.check(bad) == [
        f"{TEXT}:about.{language}: uses a semicolon — this edition's own prose has none. "
        "Use a full stop, or an 'and'"
    ]
    assert prose.check(layer) == [] and layer["about"] == about

"""Finite Lateran Postcommunion constructions and their unchanged boundaries."""

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.bibliography_bindings import selected_text
from build_reader.emit import Table, core_artifact, expand, language_artifact
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads(
    (ROOT / "tests/fixtures/lateran-postcommunion-successor.json").read_text(encoding="utf-8")
)
TEXT = FIXTURE["text"]
CORE = "texts/" + TEXT.replace(".", "/", 1) + ".json"
LAYERS = {language: f"languages/{language}/{CORE}" for language in ("pl", "en")}
LANGUAGES = ["pl", "en"]


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def documents():
    return {path: load(path) for path in (CORE, *LAYERS.values())}


def parent_at(doc, pointer):
    parts = pointer.split("/")[1:]
    for part in parts[:-1]:
        doc = doc[int(part)] if isinstance(doc, list) else doc[part]
    return doc, int(parts[-1]) if isinstance(doc, list) else parts[-1]


def historical_objects(documents):
    result = deepcopy(documents)
    for operation in reversed(FIXTURE["operations"]):
        parent, key = parent_at(result[operation["path"]], operation["pointer"])
        exists = key in parent if isinstance(parent, dict) else 0 <= key < len(parent)
        require(exists == operation["after"]["exists"], "successor field presence")
        if exists:
            require(parent[key] == operation["after"]["value"], "successor field value")
        if operation["before"]["exists"]:
            parent[key] = deepcopy(operation["before"]["value"])
        else:
            del parent[key]
    return result


def words(core):
    return {word["id"]: word for segment in core["segments"] for word in segment["words"]}


def assert_reading(core, wid):
    word = words(core)[wid]
    require(word["morph"]["case"] == "dat", "beneficiary dative reading")
    require(
        core["editorial"]["words"][wid]["analysis"]
        == {
            "confidence": "medium",
            "sources": ["editorial", "whitakers", "collatinus"],
            "review": "pending",
        },
        "dative remains a pending contextual reading",
    )


def assert_constructions(target, language):
    require(
        target["segments"]["s01"]["alignments"] == FIXTURE["groups"][language],
        "Lateran construction groups",
    )
    direct = {
        "pl": {"w009": "majestatowi", "w010": "Twojemu", "w013": "pomóż"},
        "en": {"w016": "as they plead", "w018": "what", "w027": "Through"},
    }
    for wid, caption in direct[language].items():
        require(target["words"][wid].get("gloss") == caption, "Lateran direct construction")


def assert_ledger(core, target, row, language):
    (segment,) = [segment for segment in core["segments"] if segment["id"] == row["segment"]]
    require(
        row["source_sha256"] == canonical_hash(source_payload(segment)), "ledger source identity"
    )
    require(
        row["target_sha256"] == canonical_hash(target["segments"][segment["id"]]["translation"]),
        "ledger target identity",
    )
    before = FIXTURE["ledger_before"][language][segment["id"]]
    expected = {**before, **FIXTURE["ledger_hash_successors"][language].get(segment["id"], {})}
    require(row == expected, "Lateran provenance has only declared hash successors")


def test_complete_historical_objects_survive_the_narrow_inverse(documents):
    snapshot = deepcopy(FIXTURE)
    restored = historical_objects(documents)
    assert {path: canonical_hash(value) for path, value in restored.items()} == (
        FIXTURE["historical_object_sha256"]
    )
    assert len(FIXTURE["operations"]) == 47
    assert len({(op["path"], op["pointer"]) for op in FIXTURE["operations"]}) == 47
    assert snapshot == FIXTURE


def test_selected_latin_ritual_and_all_ids_are_unchanged(documents):
    core = documents[CORE]
    assert canonical_hash(selected_text(core)) == FIXTURE["selected_latin_ritual_sha256"]
    assert list(words(core)) == [f"w{number:03}" for number in range(1, 49)]
    assert [(segment["id"], len(segment["words"])) for segment in core["segments"]] == [
        ("s01", 47),
        ("s02", 1),
    ]
    assert words(core)["w018"]["morph"]["case"] == "nom"
    assert words(core)["w020"]["head"] == "w019"


@pytest.mark.parametrize("wid", ["w019", "w020"])
def test_preferred_datives_are_not_promoted_to_certainty(documents, wid):
    assert_reading(documents[CORE], wid)


@pytest.mark.parametrize("language", LANGUAGES)
def test_possible_genitive_is_disclosed_once_in_each_language(documents, language):
    core, target = documents[CORE], documents[LAYERS[language]]
    assert core["localization"]["explanations"] == {"w019": {}}
    explanation = target["words"]["w019"]["explanation"]
    assert explanation == FIXTURE["explanations"][language]
    assert ("dopełniaczem" if language == "pl" else "can be genitive") in explanation
    assert "explanation" not in target["words"]["w020"]
    assert language_packs.check_core(core) == []
    assert language_packs.check_layer(core, target, ROOT / LAYERS[language]) == []


@pytest.mark.parametrize("language", LANGUAGES)
def test_all_96_memberships_are_once_only_without_zero_realizations(documents, language):
    core, target = documents[CORE], documents[LAYERS[language]]
    counts = Counter(wid for wid, entry in target["words"].items() if entry.get("gloss"))
    groups = target["segments"]["s01"]["alignments"]
    counts.update(wid for group in groups for wid in group["words"])
    assert counts == Counter(list(words(core)))
    assert all(group.get("gloss") and "reason" not in group for group in groups)
    assert (len(groups), sum(len(group["words"]) for group in groups)) == (
        (3, 8) if language == "pl" else (9, 25)
    )
    assert interlinear.check(expand_core(core), target) == []


@pytest.mark.parametrize("language", LANGUAGES)
def test_exact_short_constructions_preserve_actors_possessives_and_duration(documents, language):
    assert_constructions(documents[LAYERS[language]], language)


@pytest.fixture(scope="module")
def projections(documents):
    core = documents[CORE]
    doc = expand_core(core)
    parses, analyses, shared = Table(), Table(), Table()
    artifact = core_artifact(doc, core, parses, analyses, shared)
    result = {}
    for language in LANGUAGES:
        local = Table()
        layer = enrich_layer(core, documents[LAYERS[language]])
        localized = language_artifact(doc, layer, local)
        result[language] = expand(
            artifact, localized, parses.order, analyses.order, shared.order, local.order
        )
    return result


@pytest.mark.parametrize("language", LANGUAGES)
def test_scoped_reader_projection_keeps_doubt_prose_and_constructions(
    documents, projections, language
):
    doc, layer = projections[language]
    assert selected_text(doc) == selected_text(documents[CORE])
    for wid in ("w019", "w020"):
        assert words(doc)[wid]["analysis"] == documents[CORE]["editorial"]["words"][wid]["analysis"]
    assert layer["segments"] == documents[LAYERS[language]]["segments"]
    assert layer["words"] == documents[LAYERS[language]]["words"]


@pytest.mark.parametrize("language", LANGUAGES)
def test_actual_ledgers_keep_statuses_and_exact_source_target_relations(documents, language):
    ledger = load(f"languages/{language}/translation-provenance.json")
    rows = [row for row in ledger["sites"] if row["text"] == TEXT]
    assert [row["segment"] for row in rows] == ["s01", "s02"]
    for row in rows:
        assert_ledger(documents[CORE], documents[LAYERS[language]], row, language)


CAPTION_MUTANTS = [
    ("pl-majesty-case", "pl", "w009", "Majestatowi"),
    ("pl-help-government", "pl", "w013", "wspomóż"),
    ("en-supplication", "en", "w016", "as they pray"),
    ("en-relative", "en", "w018", "that which"),
    ("en-sentence-start", "en", "w027", "through"),
    ("en-possessive", "en", "group", "Your Lord"),
]


@pytest.mark.parametrize(
    "defect,language,wid,value", CAPTION_MUTANTS, ids=[row[0] for row in CAPTION_MUTANTS]
)
def test_construction_guards_reject_owned_mutants_and_restore(
    documents, defect, language, wid, value
):
    snapshot, fixture_snapshot = deepcopy(documents), deepcopy(FIXTURE)
    target = documents[LAYERS[language]]
    assert_constructions(target, language)
    broken = deepcopy(target)
    if wid == "group":
        (group,) = [g for g in broken["segments"]["s01"]["alignments"] if g["anchor"] == "w028"]
        assert group["gloss"] == "our Lord"
        group["gloss"] = value
        diagnostic = "Lateran construction groups"
    else:
        assert broken["words"][wid]["gloss"] != value
        broken["words"][wid]["gloss"] = value
        diagnostic = "Lateran direct construction"
    with pytest.raises(AssertionError) as caught:
        assert_constructions(broken, language)
    assert str(caught.value) == diagnostic
    assert_constructions(target, language)
    assert documents == snapshot
    assert fixture_snapshot == FIXTURE


@pytest.mark.parametrize("wid", ["w019", "w020"])
def test_reading_control_rejects_false_acceptance_without_rewriting_history(documents, wid):
    saved = deepcopy(documents)
    broken = deepcopy(documents[CORE])
    broken["editorial"]["words"][wid]["analysis"]["review"] = "accepted"
    with pytest.raises(AssertionError) as caught:
        assert_reading(broken, wid)
    assert str(caught.value) == "dative remains a pending contextual reading"
    assert_reading(documents[CORE], wid)
    assert documents == saved


@pytest.mark.parametrize(
    "language,defect",
    [(lang, flaw) for lang in LANGUAGES for flaw in ("missing", "duplicate")],
)
def test_membership_mutants_fail_the_actual_interlinear_check(documents, language, defect):
    saved = deepcopy(documents)
    broken = deepcopy(documents[LAYERS[language]])
    wid = "w019"
    if defect == "missing":
        group = next(g for g in broken["segments"]["s01"]["alignments"] if wid in g["words"])
        broken["segments"]["s01"]["alignments"].remove(group)
    else:
        broken["words"][wid]["gloss"] = "duplicate"
    message = f"{TEXT}:{wid}:{language}: expected exactly one direct gloss or alignment"
    assert message in interlinear.check(expand_core(documents[CORE]), broken)
    assert interlinear.check(expand_core(documents[CORE]), documents[LAYERS[language]]) == []
    assert documents == saved


@pytest.mark.parametrize("language", LANGUAGES)
def test_explanation_omission_fails_actual_localization_topology(documents, language):
    saved = deepcopy(documents)
    broken = deepcopy(documents[LAYERS[language]])
    del broken["words"]["w019"]["explanation"]
    message = f"{language}:{TEXT}: explanation topology differs — missing=['w019'] extra=[]"
    assert message in language_packs.check_layer(documents[CORE], broken, ROOT / LAYERS[language])
    assert (
        language_packs.check_layer(
            documents[CORE], documents[LAYERS[language]], ROOT / LAYERS[language]
        )
        == []
    )
    assert documents == saved


@pytest.mark.parametrize("language", LANGUAGES)
def test_stale_source_hash_cannot_retain_the_new_analysis(documents, language):
    saved = deepcopy(FIXTURE)
    before = FIXTURE["ledger_before"][language]["s01"]
    row = {**deepcopy(before), **FIXTURE["ledger_hash_successors"][language]["s01"]}
    assert row["source_sha256"] != before["source_sha256"]
    assert_ledger(documents[CORE], documents[LAYERS[language]], row, language)
    broken = deepcopy(row)
    broken["source_sha256"] = before["source_sha256"]
    with pytest.raises(AssertionError) as caught:
        assert_ledger(documents[CORE], documents[LAYERS[language]], broken, language)
    assert str(caught.value) == "ledger source identity"
    assert_ledger(documents[CORE], documents[LAYERS[language]], row, language)
    assert saved == FIXTURE

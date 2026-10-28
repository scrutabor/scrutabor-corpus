"""Two finite reviewed agency corrections; no general ban on converbs."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from documentary_successor_fixture import before_agency_ledger

from build_reader import store
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs
from checks.translation_provenance import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
THIRD = "proprium.dominica-iii-post-pentecosten-epistola"
ASSUMPTION = "proprium.assumptio-beatae-mariae-virginis-postcommunio"
GROUPS = {"pl": "po naszym krótkim cierpieniu", "en": "after our brief suffering"}
PERFECTS = {"pl": "udoskonali nas", "en": "will perfect us"}
RECEIVED = {"pl": "Przyjęliśmy", "en": "We have received"}
EN_PROSE = (
    "We have received, O Lord, the sacraments of salvation; grant, we beseech You, "
    "that through the merits and intercession of the Blessed Virgin Mary, who was "
    "taken up into heaven, we may be brought to the glory of the resurrection. "
    "Through our Lord Jesus Christ, Your Son, who lives and reigns with You in the "
    "unity of the Holy Spirit, God, forever and ever."
)


def load(text, language):
    return store.core(ROOT, text), store.raw_layer(ROOT, language, text)


def healthy(core, layer):
    assert language_packs.check_core(core) == []
    name = core["id"].split(".", 1)[1] + ".json"
    path = ROOT / "languages" / layer["language"] / "texts" / "proprium" / name
    assert language_packs.check_layer(core, layer, path) == []
    assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []


def meaning(core, layer):
    language = layer["language"]
    words = {w["id"]: w for s in core["segments"] for w in s["words"]}
    if core["id"] == THIRD:
        assert (words["w071"]["morph"]["case"], words["w071"]["morph"]["number"]) == ("acc", "pl")
        assert words["w072"]["morph"]["case"] == "nom"
        groups = [
            g for g in layer["segments"]["s01"]["alignments"] if set(g["words"]) & {"w070", "w071"}
        ]
        expected = {"words": ["w070", "w071"], "anchor": "w071", "gloss": GROUPS[language]}
        assert groups == [expected], "human suffering"
        assert all("gloss" not in layer["words"][w] for w in ("w070", "w071")), (
            "one suffering provider"
        )
        assert layer["words"]["w073"]["gloss"] == PERFECTS[language], "human recipients"
        assert layer["words"]["w062"]["gloss"] == {"pl": "nas", "en": "us"}[language]
        assert layer["words"]["w072"]["gloss"] == {"pl": "sam", "en": "Himself"}[language]
    else:
        assert core["id"] == ASSUMPTION
        assert (words["w001"]["morph"]["case"], words["w004"]["morph"]["case"]) == ("abl", "abl")
        assert words["w005"]["morph"]["mood"] == "imp"
        assert layer["words"]["w001"]["gloss"] == RECEIVED[language], "human reception"
        assert layer["words"]["w005"]["gloss"] == {"pl": "daj", "en": "grant"}[language]
        if language == "en":
            assert layer["segments"]["s01"]["translation"] == EN_PROSE, "human reception prose"


@pytest.mark.parametrize(
    "text,language",
    [(THIRD, "pl"), (THIRD, "en"), (ASSUMPTION, "pl"), (ASSUMPTION, "en")],
    ids=["third-pl", "third-en", "assumption-pl", "assumption-en"],
)
def test_reviewed_agency_has_real_native_and_literal_coverage(text, language):
    core, layer = load(text, language)
    healthy(core, layer)
    meaning(core, layer)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_suffering_actor_object_and_duplicate_provider_faults_restore(language):
    core, layer = load(THIRD, language)
    saved = deepcopy(layer)
    healthy(core, layer)
    meaning(core, layer)
    for fault in ("divine-suffering", "missing-recipient", "duplicate-provider"):
        try:
            group = next(
                g for g in layer["segments"]["s01"]["alignments"] if g["words"] == ["w070", "w071"]
            )
            if fault == "divine-suffering":
                group["gloss"] = {
                    "pl": "po Jego krótkim cierpieniu",
                    "en": "after His brief suffering",
                }[language]
            elif fault == "missing-recipient":
                layer["words"]["w073"]["gloss"] = {"pl": "udoskonali", "en": "will perfect"}[
                    language
                ]
            else:
                layer["words"]["w071"]["gloss"] = {"pl": "wycierpiawszy", "en": "after suffering"}[
                    language
                ]
                assert interlinear.check(expand_core(core), enrich_layer(core, layer))
            assert layer != saved
            with pytest.raises(AssertionError):
                meaning(core, layer)
        finally:
            layer.clear()
            layer.update(deepcopy(saved))
        assert layer == saved
        healthy(core, layer)
        meaning(core, layer)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_reception_converb_and_prose_faults_restore(language):
    core, layer = load(ASSUMPTION, language)
    saved = deepcopy(layer)
    healthy(core, layer)
    meaning(core, layer)
    prose_faults = ("old-prose", "comma-prose") if language == "en" else ()
    faults = ("old-converb", "wrong-actor", *prose_faults)
    for fault in faults:
        try:
            if fault == "old-converb":
                layer["words"]["w001"]["gloss"] = {"pl": "Przyjąwszy", "en": "Having received"}[
                    language
                ]
            elif fault == "wrong-actor":
                layer["words"]["w001"]["gloss"] = {"pl": "Przyjąłeś", "en": "You have received"}[
                    language
                ]
            elif fault == "old-prose":
                layer["segments"]["s01"]["translation"] = EN_PROSE.replace(
                    "We have received", "Having received", 1
                ).replace("salvation; grant", "salvation, grant", 1)
            else:
                layer["segments"]["s01"]["translation"] = EN_PROSE.replace(
                    "salvation; grant", "salvation, grant", 1
                )
            assert layer != saved
            healthy(core, layer)
            with pytest.raises(AssertionError):
                meaning(core, layer)
        finally:
            layer.clear()
            layer.update(deepcopy(saved))
        assert layer == saved
        healthy(core, layer)
        meaning(core, layer)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_correct_divine_and_Jesus_converb_controllers_are_kept(language):
    controls = [
        (
            "proprium.dominica-iv-post-pentecosten-secreta",
            "w006",
            {"pl": "przyjąwszy je", "en": "having received them"},
        ),
        (
            "proprium.dominica-xvi-post-pentecosten-evangelium",
            "w045",
            {"pl": "pochwyciwszy", "en": "having taken him"},
        ),
    ]
    for text, word, expected in controls:
        core, layer = load(text, language)
        healthy(core, layer)
        assert layer["words"][word]["gloss"] == expected[language]
        # The reviewed controller is God receiving offerings / Jesus taking the patient.
        words = {w["id"]: w for s in core["segments"] for w in s["words"]}
        controller = "w005" if word == "w006" else "w046"
        assert words[controller]["morph"]["mood"] in ("imp", "ind")
        assert not any(
            word in g["words"] for s in layer["segments"].values() for g in s.get("alignments", [])
        )


def test_exact_ledger_inverse_rejects_drift_and_restores_same_row():
    ledger = json.loads((ROOT / "languages/en/translation-provenance.json").read_text())
    (row,) = [r for r in ledger["sites"] if r["site"] == ASSUMPTION + ".s01.en"]
    core, layer = load(ASSUMPTION, "en")
    healthy(core, layer)
    meaning(core, layer)
    assert row["target_sha256"] == canonical_hash(layer["segments"]["s01"]["translation"])
    saved, whole = deepcopy(row), deepcopy(ledger)
    predecessor = before_agency_ledger("languages/en/translation-provenance.json", ledger)
    assert predecessor != ledger and ledger == whole
    for field, value in [
        ("source_sha256", "0" * 64),
        ("target_sha256", "0" * 64),
        ("origin", "own"),
        ("review", "approved"),
        ("familiar_core", True),
        ("extra", True),
        ("unrelated", True),
    ]:
        try:
            if field == "unrelated":
                ledger["agency_unrelated_control"] = value
            else:
                row[field] = value
            assert ledger != whole
            with pytest.raises(AssertionError, match=r"^agency current ledger(?:\n|$)"):
                before_agency_ledger("languages/en/translation-provenance.json", ledger)
        finally:
            ledger.pop("agency_unrelated_control", None)
            row.clear()
            row.update(deepcopy(saved))
        assert ledger == whole
        assert next(r for r in ledger["sites"] if r["site"] == row["site"]) is row
        restored = before_agency_ledger("languages/en/translation-provenance.json", ledger)
        assert restored == predecessor

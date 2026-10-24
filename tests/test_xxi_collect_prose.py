"""Keep the Collect's protection and devoted good action as distinct petitions."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.layers import enrich_layer, expand_core
from checks import interlinear
from checks import translation_provenance as provenance

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.dominica-xxi-post-pentecosten-collecta"
SITE = TEXT + ".s01.en"
RELATIVE = Path("texts/proprium/dominica-xxi-post-pentecosten-collecta.json")
PREFIX = (
    "Guard Your household, we beseech You, O Lord, with unceasing care, "
    "that under Your protection it may be free from all harm and "
)
PETITION = "be devoted to Your name in good deeds"
ENDING = (
    ". Through our Lord Jesus Christ, Your Son, who lives and reigns with You "
    "in the unity of the Holy Spirit, God, forever and ever."
)
PREDECESSOR = PREFIX + "serve You by good deeds" + ENDING


def load():
    core = json.loads((ROOT / RELATIVE).read_text(encoding="utf-8"))
    layer = json.loads((ROOT / "languages/en" / RELATIVE).read_text(encoding="utf-8"))
    return core, layer


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def assert_source(core):
    require(core["id"] == TEXT, "devotion source identity")
    words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    require(
        len(words) == 45
        and words["w001"]["lemma"] == "familia"
        and words["w001"]["morph"]["case"] == "acc"
        and words["w012"]["lemma"] == "tu"
        and words["w012"]["morph"]["case"] == "abl"
        and words["w013"]["lemma"] == "protego"
        and words["w013"]["morph"]["voice"] == "act"
        and words["w013"]["head"] == "w012",
        "devotion household and protector",
    )
    expected = {
        "w017": ("in", {"pos": "prep", "governs": "abl"}, "w019"),
        "w018": ("bonus", {"case": "abl", "number": "pl", "gender": "m"}, "w019"),
        "w019": ("actus", {"case": "abl", "number": "pl", "gender": "m"}, None),
        "w020": ("tuus", {"case": "dat", "number": "sg", "gender": "n"}, "w021"),
        "w021": ("nomen", {"case": "dat", "number": "sg", "gender": "n"}, None),
        "w022": ("sum", {"mood": "subj", "tense": "pres", "person": 3}, None),
        "w023": (
            "devoveo",
            {"case": "nom", "number": "sg", "gender": "f", "mood": "part"},
            "w022",
        ),
    }
    for wid, (lemma, morph, head) in expected.items():
        word = words[wid]
        require(
            word["lemma"] == lemma
            and all(word["morph"].get(k) == v for k, v in morph.items())
            and word.get("head") == head,
            "devotion complement and state",
        )


def assert_prose(core, layer):
    assert_source(core)
    require(layer["text"] == TEXT and layer["language"] == "en", "devotion target identity")
    # This is one known-reading control, not a general translation detector.
    require(
        layer["segments"]["s01"]["translation"] == PREFIX + PETITION + ENDING,
        "devotion, divine Name and good deeds in one present petition",
    )
    require(layer["segments"]["s02"]["translation"] == "Amen.", "devotion response retained")


def test_actual_complete_prose_and_localized_checking_view():
    core, layer = load()
    assert_prose(core, layer)
    localized = enrich_layer(core, layer)
    assert localized["segments"]["s01"]["translation"] == PREFIX + PETITION + ENDING
    assert localized["segments"]["s02"]["translation"] == "Amen."
    assert interlinear.check(expand_core(core), layer) == []
    assert layer["words"]["w023"]["gloss"] == "devoted"
    assert layer["words"]["w020"]["gloss"] == "to Your"
    assert layer["words"]["w021"]["gloss"] == "name"
    assert {"words": ["w012", "w013"], "anchor": "w013", "gloss": "with You protecting"} in layer[
        "segments"
    ]["s01"]["alignments"]


@pytest.mark.parametrize(
    "phrase",
    (
        "serve You by good deeds",
        "be devoted in good deeds",
        "honor Your name",
        "be devoted to our name in good deeds",
        "earn Your protection by good deeds",
        "was devoted to Your name in good deeds",
    ),
)
def test_semantic_regressions_fail_after_a_real_healthy_control(phrase):
    core, layer = load()
    saved = deepcopy(layer)
    assert_prose(core, layer)
    broken = deepcopy(layer)
    broken["segments"]["s01"]["translation"] = PREFIX + phrase + ENDING
    assert broken != layer
    with pytest.raises(AssertionError, match="devotion, divine Name and good deeds"):
        assert_prose(core, broken)
    assert_prose(core, layer)
    assert layer == saved


@pytest.mark.parametrize("defect", ("case", "possessive-head", "past-event", "protector"))
def test_source_dependencies_do_not_get_rewritten_to_fit_prose(defect):
    core, layer = load()
    saved = deepcopy(core)
    assert_prose(core, layer)
    broken = deepcopy(core)
    words = {w["id"]: w for s in broken["segments"] for w in s.get("words", [])}
    if defect == "case":
        words["w021"]["morph"]["case"] = "nom"
    elif defect == "possessive-head":
        words["w020"]["head"] = "w019"
    elif defect == "past-event":
        words["w022"]["morph"]["tense"] = "perf"
    else:
        words["w013"]["morph"]["voice"] = "pass"
    with pytest.raises(AssertionError, match=r"devotion (complement|household)"):
        assert_prose(broken, layer)
    assert_prose(core, layer)
    assert core == saved


@pytest.mark.parametrize("defect", (None, "old-target", "old-ledger", "promotion"))
def test_native_provenance_binds_the_actual_shipped_target(monkeypatch, defect):
    core, layer = load()
    assert_prose(core, layer)
    # Obtain actual generated contracts before narrowing this native check to
    # the one reviewed site. No invented source/version identity is supplied.
    actual = deepcopy(provenance.corpus_sites(ROOT)[SITE])
    recorded, errors = provenance.load(ROOT)
    assert errors == []
    row = deepcopy(recorded[SITE])
    assert actual["source_sha256"] == provenance.canonical_hash(
        provenance.source_payload(core["segments"][0])
    )
    assert actual["target_sha256"] == provenance.canonical_hash(
        layer["segments"]["s01"]["translation"]
    )
    assert row["origin"] == "working-unsettled"
    assert row["review"] == "working"
    assert row["familiar_core"] is False
    old_hash = provenance.canonical_hash(PREDECESSOR)
    assert old_hash != actual["target_sha256"]
    if defect == "old-target":
        actual["target_sha256"] = old_hash
    elif defect == "old-ledger":
        row["target_sha256"] = old_hash
    elif defect == "promotion":
        row["review"] = "internally-reviewed"
    monkeypatch.setattr(provenance, "corpus_sites", lambda _root: {SITE: actual})
    monkeypatch.setattr(provenance, "load", lambda _root: ({SITE: row}, []))
    errors, tally = provenance.check(ROOT)
    assert tally == {"working-unsettled": 1}
    expected = (
        []
        if defect is None
        else [
            SITE + ": unsettled origin cannot claim review=internally-reviewed"
            if defect == "promotion"
            else SITE + ": stale target_sha256"
        ]
    )
    assert errors == expected

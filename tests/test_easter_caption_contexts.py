"""Keep bounded Easter constructions grammatical without changing Latin."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from preface_transition_fixture import ALTERNATIVES

from checks.interlinear import check

ROOT = Path(__file__).resolve().parents[1]
EASTER = "proprium.dominica-resurrectionis-"
PASCHA = {
    EASTER + "epistola": 13,
    EASTER + "alleluia": 3,
    EASTER + "communio": 1,
    "ordinarium.praefatio-paschalis": 21,
    "ordinarium.praefatio-paschalis-in-die": 22,
    "ordinarium.praefatio-paschalis-in-nocte": 22,
}
MOVEMENT = [
    (EASTER + "sequentia", 48, "pójdzie przed wami", "fut", 3),
    (EASTER + "evangelium", 88, "idzie przed wami", "pres", 3),
    ("proprium.vigilia-paschalis-evangelium", 101, "idzie przed wami", "pres", 3),
    ("proprium.dominica-in-albis-alleluia", 9, "pójdę przed wami", "fut", 1),
]


def document(text, language=None):
    prefix = ROOT if language is None else ROOT / "languages" / language
    return json.loads((prefix / "texts" / (text.replace(".", "/") + ".json")).read_text())


def word_ids(first, last):
    return [f"w{n:03}" for n in range(first, last + 1)]


def assert_group(layer, words, gloss, segment="s01"):
    matches = [a for a in layer["segments"][segment].get("alignments", []) if a["words"] == words]
    assert len(matches) == 1, "one complete construction provider required"
    allowed = {gloss} if isinstance(gloss, str) else gloss
    assert matches[0]["gloss"] in allowed, "construction wording changed"
    assert all("gloss" not in layer["words"][w] for w in words), "duplicate word caption"


def test_complete_pauline_construction_inventory():
    found = {}
    for path in sorted((ROOT / "texts").glob("*/*.json")):
        core = json.loads(path.read_text())
        for segment in core["segments"]:
            words = segment.get("words", [])
            for index, word in enumerate(words):
                if word.get("lemma") != "pascha":
                    continue
                phrase = words[index : index + 5]
                if [w.get("lemma") for w in phrase] == [
                    "pascha",
                    "noster",
                    "immolo",
                    "sum",
                    "Christus",
                ]:
                    assert core["id"] not in found
                    found[core["id"]] = int(word["id"][1:])
    assert found == PASCHA


@pytest.mark.parametrize("text,first", PASCHA.items())
@pytest.mark.parametrize("language", ["pl", "en"])
def test_pascha_apposition_keeps_christ_as_subject(text, first, language):
    layer = document(text, language)
    words = word_ids(first, first + 4)
    gloss = (
        "Chrystus, nasza Pascha, został ofiarowany"
        if language == "pl"
        else "Christ, our Passover, has been sacrificed"
    )
    if language == "en" and text.startswith("ordinarium."):
        words = word_ids(first - 1, first + 4)
        gloss = ALTERNATIVES
    assert_group(layer, words, gloss)
    core = document(text)
    tokens = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    assert tokens[f"w{first:03}"]["morph"]["gender"] == "n"
    assert tokens[f"w{first + 4:03}"]["morph"]["case"] == "nom"
    assert check(core, layer) == []


@pytest.mark.parametrize("text,first,gloss,tense,person", MOVEMENT)
def test_going_before_keeps_person_and_tense(text, first, gloss, tense, person):
    layer, core = document(text, "pl"), document(text)
    assert_group(layer, word_ids(first, first + 1), gloss)
    word = next(
        w for s in core["segments"] for w in s.get("words", []) if w["id"] == f"w{first:03}"
    )
    assert word["lemma"] == "praecedo"
    assert word["morph"]["tense"] == tense
    assert word["morph"]["person"] == person
    assert check(core, layer) == []


def test_polish_reconciliation_and_distinct_neighbouring_government():
    seq = document(EASTER + "sequentia", "pl")
    assert seq["words"]["w011"]["gloss"] == "z Ojcem"
    sub = document("orationes.sub-tuum-praesidium", "pl")
    assert_group(sub, ["w033", "w034"], "z Twoim Synem", "s03")
    assert sub["words"]["w038"]["gloss"] == "Synowi"
    assert sub["words"]["w042"]["gloss"] == "Synowi"


def assert_communion_government(layer):
    assert [layer["words"][word]["gloss"] for word in ["w008", "w009", "w010"]] == [
        "ucztujmy",
        "z",
        "przaśnym chlebem",
    ], "feasting phrase requires matching Polish government"


def test_polish_feasting_parallel_clauses():
    assert_communion_government(document(EASTER + "communio", "pl"))
    epistle = document(EASTER + "epistola", "pl")["words"]
    for prep, noun, expected in [
        ("w021", "w022", "kwasem"),
        ("w025", "w026", "kwasem"),
        ("w031", "w032", "przaśnikami"),
    ]:
        assert epistle[prep]["gloss"] == "z"
        assert epistle[noun]["gloss"] == expected
    assert epistle["w020"]["gloss"] == "nie"
    assert epistle["w024"]["gloss"] == "ani"
    assert epistle["w030"]["gloss"] == "lecz"


def test_government_guard_rejects_old_case_after_changed_preposition():
    layer = document(EASTER + "communio", "pl")
    assert_communion_government(layer)
    broken = deepcopy(layer)
    broken["words"]["w010"]["gloss"] = "przaśnym chlebie"
    with pytest.raises(AssertionError, match="matching Polish government"):
        assert_communion_government(broken)
    assert_communion_government(layer)


def test_construction_guard_rejects_wrong_predicate_and_duplicate_caption():
    layer = document(EASTER + "alleluia", "pl")
    words, gloss = word_ids(3, 7), "Chrystus, nasza Pascha, został ofiarowany"
    assert_group(layer, words, gloss)
    broken = deepcopy(layer)
    next(a for a in broken["segments"]["s01"]["alignments"] if a["words"] == words)["gloss"] = (
        "Pascha nasza została ofiarowana"
    )
    with pytest.raises(AssertionError, match="construction wording"):
        assert_group(broken, words, gloss)
    duplicate = deepcopy(layer)
    duplicate["words"]["w004"]["gloss"] = "nasza"
    with pytest.raises(AssertionError, match="duplicate word caption"):
        assert_group(duplicate, words, gloss)
    assert_group(layer, words, gloss)


def test_cloth_senses_remain_general_and_context_is_local():
    for language, expected, forbidden in [
        ("pl", "chustę", "całun"),
        ("en", "the face cloth", "winding-sheet"),
    ]:
        entry = json.loads((ROOT / "languages" / language / "lexicon.json").read_text())["entries"][
            "sudarium"
        ]
        assert forbidden not in " ".join(entry["senses"])
        assert entry["senses"]
        layer = document(EASTER + "sequentia", language)
        assert layer["words"]["w041"]["gloss"] == expected
        assert "20" in layer["words"]["w041"]["explanation"]


def test_polish_pascha_gender_does_not_change_latin_gender():
    text = "proprium.corporis-christi-sequentia"
    layer = document(text, "pl")
    assert layer["words"]["w070"]["gloss"] == "nowa"
    core = document(text)
    words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    assert words["w070"]["morph"]["gender"] == "n"
    assert words["w071"]["morph"]["gender"] == "n"


@pytest.mark.parametrize(
    "text", ["ordinarium.praefatio-paschalis-in-die", "ordinarium.praefatio-paschalis-in-nocte"]
)
@pytest.mark.parametrize("wording", sorted(ALTERNATIVES))
def test_supported_preface_sacrifice_wording_remains_valid(text, wording):
    layer = document(text, "en")
    words = word_ids(21, 26)
    group = next(a for a in layer["segments"]["s01"]["alignments"] if a["words"] == words)
    group["gloss"] = wording
    assert_group(layer, words, ALTERNATIVES)
    assert check(document(text), layer) == []

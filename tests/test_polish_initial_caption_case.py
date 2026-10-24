"""Eleven reviewed Polish caption cases, with finite construction controls."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INITIALS = (
    (
        "assumptio-beatae-mariae-virginis-secreta",
        "ascendo",
        "subj",
        3,
        "niech się wzniesie",
        "Niech się wzniesie",
    ),
    ("beata-maria-virgo-regina-collecta", "concedo", "imp", 2, "spraw", "Spraw"),
    ("beata-maria-virgo-regina-secreta", "accipio", "imp", 2, "przyjmij", "Przyjmij"),
    ("beatae-mariae-virginis-a-rosario-secreta", "facio", "imp", 2, "spraw", "Spraw"),
    ("cathedra-sancti-petri-postcommunio", "laetifico", "subj", 3, "niech raduje", "Niech raduje"),
    (
        "commemoratio-omnium-fidelium-defunctorum-missa-ii-postcommunio",
        "praesto",
        "imp",
        2,
        "spraw",
        "Spraw",
    ),
    (
        "commemoratio-omnium-fidelium-defunctorum-missa-iii-postcommunio",
        "praesto",
        "imp",
        2,
        "spraw",
        "Spraw",
    ),
    ("corporis-christi-postcommunio", "facio", "imp", 2, "spraw", "Spraw"),
    (
        "dedicatio-archibasilicae-sanctissimi-salvatoris-secreta",
        "annuo",
        "imp",
        2,
        "przychyl się",
        "Przychyl się",
    ),
    (
        "sacratissimi-cordis-iesu-postcommunio",
        "praebeo",
        "subj",
        3,
        "niech udzielą",
        "Niech udzielą",
    ),
)
ASSUMPTION = INITIALS[0][0]
QUEEN = INITIALS[1][0]
ROSARY = "beatae-mariae-virginis-a-rosario-postcommunio"
KING = "d-n-iesu-christi-regis-postcommunio"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def load(slug, language="pl"):
    path = Path("texts/proprium") / f"{slug}.json"
    return (
        json.loads((ROOT / path).read_text(encoding="utf-8")),
        json.loads((ROOT / "languages" / language / path).read_text(encoding="utf-8")),
    )


def unit(layer, segment, span):
    """Read one exact realization, not infer its sentence case from prose."""
    groups = [
        group
        for group in layer["segments"][segment].get("alignments", [])
        if set(span) & set(group["words"])
    ]
    direct = [word for word in span if "gloss" in layer["words"][word]]
    if groups:
        require(
            len(groups) == 1 and groups[0]["words"] == list(span) and not direct,
            "caption realization unit",
        )
        group = groups[0]
        return {"kind": "group" if "gloss" in group else "zero", **group}
    require(len(span) == len(direct) == 1, "caption realization unit")
    return {"kind": "direct", "words": list(span), "gloss": layer["words"][span[0]]["gloss"]}


def assert_initial(core, layer, row):
    _, lemma, mood, person, _, expected = row
    first = next(segment for segment in core["segments"] if segment.get("words"))
    word = first["words"][0]
    require(first["id"] == "s01" and word["id"] == "w001", "reviewed Polish initial construction")
    require(
        (word["lemma"], word["morph"]["pos"], word["morph"]["mood"], word["morph"]["person"])
        == (lemma, "verb", mood, person),
        "reviewed Polish initial construction",
    )
    require(
        unit(layer, "s01", ("w001",)) == {"kind": "direct", "words": ["w001"], "gloss": expected},
        "reviewed Polish caption sentence onset",
    )


def assert_offering_subject(core, layer):
    assert_initial(core, layer, INITIALS[0])
    words = {word["id"]: word for word in core["segments"][0]["words"]}
    noun = words["w007"]
    require(
        noun["lemma"] == "oblatio"
        and {key: noun["morph"][key] for key in ("case", "gender", "number")}
        == {"case": "nom", "gender": "f", "number": "sg"},
        "reviewed offering subject context",
    )
    require(
        unit(layer, "s01", ("w007",)) == {"kind": "direct", "words": ["w007"], "gloss": "ofiara"},
        "reviewed interior caption case",
    )


@pytest.mark.parametrize("row", INITIALS, ids=[row[0] for row in INITIALS])
def test_actual_initial_predicate_caption(core_and_layer, row):
    assert_initial(*core_and_layer[row[0]], row)


@pytest.fixture(scope="module")
def core_and_layer():
    return {row[0]: load(row[0]) for row in INITIALS}


def test_delayed_offering_subject_does_not_carry_the_initial_capital(core_and_layer):
    assert_offering_subject(*core_and_layer[ASSUMPTION])


@pytest.mark.parametrize("row", INITIALS, ids=[row[0] for row in INITIALS])
def test_old_lowercase_predicate_is_rejected_and_inputs_restored(core_and_layer, row):
    core, layer = core_and_layer[row[0]]
    saved = deepcopy(layer)
    assert_initial(core, layer, row)
    broken = deepcopy(layer)
    broken["words"]["w001"]["gloss"] = row[4]
    assert broken != layer
    with pytest.raises(AssertionError) as caught:
        assert_initial(core, broken, row)
    assert str(caught.value) == "reviewed Polish caption sentence onset"
    assert_initial(core, layer, row)
    assert layer == saved


def test_displaced_subject_capital_is_rejected_and_inputs_restored(core_and_layer):
    core, layer = core_and_layer[ASSUMPTION]
    saved = deepcopy(layer)
    assert_offering_subject(core, layer)
    broken = deepcopy(layer)
    broken["words"]["w007"]["gloss"] = "Ofiara"
    with pytest.raises(AssertionError) as caught:
        assert_offering_subject(core, broken)
    assert str(caught.value) == "reviewed interior caption case"
    assert_offering_subject(core, layer)
    assert layer == saved


def test_real_grouped_opening_and_admitted_relative_capital():
    _, layer = load(ROSARY, "en")
    expected = {
        "kind": "group",
        "words": ["w001", "w002", "w003"],
        "anchor": "w002",
        "gloss": "Of Your most holy Mother",
    }
    assert unit(layer, "s01", ("w001", "w002", "w003")) == expected
    assert unit(layer, "s01", ("w024",))["gloss"] == "Who"
    broken = deepcopy(layer)
    broken["words"]["w001"]["gloss"] = "Of"
    with pytest.raises(AssertionError) as caught:
        unit(broken, "s01", ("w001", "w002", "w003"))
    assert str(caught.value) == "caption realization unit"
    assert unit(layer, "s01", ("w001", "w002", "w003")) == expected


def test_real_idiomatic_zero_is_not_a_displayed_sentence_word(core_and_layer):
    core, layer = core_and_layer[QUEEN]
    assert_initial(core, layer, INITIALS[1])
    assert unit(layer, "s01", ("w018",))["gloss"] == "obecnie"
    expected = {"kind": "zero", "words": ["w019"], "reason": "idiom"}
    assert unit(layer, "s01", ("w019",)) == expected
    broken = deepcopy(layer)
    broken["words"]["w019"]["gloss"] = "Obecnie"
    with pytest.raises(AssertionError) as caught:
        unit(broken, "s01", ("w019",))
    assert str(caught.value) == "caption realization unit"
    assert unit(layer, "s01", ("w019",)) == expected


def test_real_continued_relative_is_not_inferred_from_prose_case():
    core, layer = load(KING, "en")
    words = {word["id"]: word for word in core["segments"][0]["words"]}
    assert words["w022"]["lemma"] == "qui" and words["w024"]["morph"]["person"] == 3
    assert unit(layer, "s01", ("w015",))["gloss"] == "Him"
    assert unit(layer, "s01", ("w022",))["gloss"] == "who"
    changed = deepcopy(layer)
    # Scope control only, not permission to revise the continuous translation.
    changed["segments"]["s01"]["translation"] = "A future independent prose revision."
    assert unit(changed, "s01", ("w022",)) == unit(layer, "s01", ("w022",))


def test_finite_case_guard_does_not_lock_other_fields(core_and_layer):
    core, layer = core_and_layer[ASSUMPTION]
    assert_offering_subject(core, layer)
    changed = deepcopy(layer)
    changed["about"] = "A future contextual note."
    changed["segments"]["s01"]["translation"] = "A future independent prose revision."
    assert_offering_subject(core, changed)

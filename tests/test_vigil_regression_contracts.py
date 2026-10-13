"""Bounded Easter Vigil successors retain semantic and source safeguards."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import test_english_explanatory_order as explanatory
import test_english_register as register
import test_finite_sum_contexts as finite
import test_preface_contexts as contexts
import test_preface_english_constructions as constructions
import test_preface_english_possessives as possessives
import test_preface_source_roles as source
from vigil_preface_fixture import DATA, current_prose

from build_reader import store
from checks import english, interlinear

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("state", [False, True])
def test_colossians_event_and_state_both_realize_estis(state):
    doc, layers = store.load(ROOT, "proprium.vigilia-paschalis-epistola")
    doc, layer = deepcopy(doc), deepcopy(layers["en"])
    word = next(w for s in doc["segments"] for w in s["words"] if w["id"] == "w025")
    group = next(g for g in layer["segments"]["s01"]["alignments"] if "w025" in g["words"])
    if state:
        word["lemma"] = "mortuus"
        word["morph"] = {"pos": "adj", "case": "nom", "number": "pl", "gender": "m"}
        group["gloss"] = "For you are dead"
    explanatory.assert_construction(
        doc, layer, "s01", "w026", ["w025", "w026", "w027"], "w025", group["gloss"]
    )
    assert interlinear.check(doc, layer) == []
    assert english.check(doc, layer) == []


@pytest.mark.parametrize(
    "slug,members,anchor,gloss",
    [
        ("vigilia-paschalis-epistola", ["w025", "w026", "w027"], "w025", "For you have died"),
        ("vigilia-paschalis-evangelium", ["w079", "w080"], "w079", "for He has risen"),
    ],
)
@pytest.mark.parametrize("mutation", ["missing", "duplicated", "zero", "false-tense"])
def test_vigil_explanatory_source_units_cannot_disappear(slug, members, anchor, gloss, mutation):
    doc, layers = store.load(ROOT, "proprium." + slug)
    layer = deepcopy(layers["en"])
    groups = layer["segments"]["s01"]["alignments"]
    group = next(g for g in groups if g["words"] == members)
    if mutation == "missing":
        group["words"].pop()
    elif mutation == "duplicated":
        layer["words"][members[-1]]["gloss"] = "are"
    elif mutation == "zero":
        group["words"].pop()
        groups.append({"words": [members[-1]], "reason": "inflection"})
    else:
        group["gloss"] = "For you will die" if slug.endswith("epistola") else "for He will rise"
    with pytest.raises(AssertionError):
        explanatory.assert_construction(doc, layer, "s01", members[1], members, anchor, gloss)


@pytest.mark.parametrize("gloss", ["was crucified", "has been crucified"])
def test_earlier_smaller_passive_mapping_is_still_valid(gloss):
    doc, layers = store.load(ROOT, "proprium.vigilia-paschalis-evangelium")
    layer = deepcopy(layers["en"])
    groups = layer["segments"]["s01"]["alignments"]
    groups[:] = [g for g in groups if not set(g["words"]) & {f"w{n:03d}" for n in range(71, 76)}]
    groups.append({"words": ["w073", "w074"], "anchor": "w073", "gloss": gloss})
    groups.sort(key=lambda g: g["words"][0])
    for wid, value in {"w071": "Jesus", "w072": "who", "w075": "you seek"}.items():
        layer["words"][wid]["gloss"] = value
    finite.assert_reading(doc, layer, [73, 74], 73, {"was crucified", "has been crucified"})
    finite.assert_boundary(
        doc, layer, {71: ("Iesus", "Jesus"), 72: ("qui", "who"), 75: ("quaero", "you seek")}, []
    )
    assert english.check(doc, layer) == []


@pytest.mark.parametrize(
    "gloss",
    [
        "you seek Jesus, who will be crucified",
        "Jesus seeks you, who was crucified",
        "you seek Jesus, who crucified",
        "you seek, who was crucified",
    ],
)
def test_vigil_seek_subject_object_and_passive_are_protected(gloss):
    doc, layers = store.load(ROOT, "proprium.vigilia-paschalis-evangelium")
    layer = deepcopy(layers["en"])
    group = next(g for g in layer["segments"]["s01"]["alignments"] if "w075" in g["words"])
    group["gloss"] = gloss
    with pytest.raises(AssertionError):
        finite.assert_reading(
            doc,
            layer,
            [71, 72, 73, 74, 75],
            75,
            {"you seek Jesus, who was crucified", "you seek Jesus, who has been crucified"},
        )


VIGIL_ENDINGS = {
    "collecta": (
        "Through the same Jesus Christ, our Lord, Your Son, who, as God, "
        "lives and reigns with You in the unity of the Holy Spirit"
    ),
    "secreta": (
        "Through Jesus Christ, our Lord, Your Son, who, as God, "
        "lives and reigns with You in the unity of the Holy Spirit"
    ),
    "postcommunio": (
        "Through Jesus Christ, our Lord, Your Son, who, as God, "
        "lives and reigns with You in the unity of the same Holy Spirit"
    ),
}


@pytest.mark.parametrize("slug", VIGIL_ENDINGS)
def test_three_vigil_orations_keep_son_deity_and_same_referents(slug):
    _, layers = store.load(ROOT, "proprium.vigilia-paschalis-" + slug)
    prose = layers["en"]["segments"]["s01"]["translation"]
    assert register.conclusion_matches(prose, VIGIL_ENDINGS[slug], duration=slug != "secreta")
    if slug == "secreta":
        assert layers["en"]["segments"]["s02"]["translation"] == "forever and ever."
    if slug == "collecta":
        assert register.conclusion_matches(
            VIGIL_ENDINGS[slug].replace("the same", "this same") + " forever and ever.",
            VIGIL_ENDINGS[slug],
            duration=True,
        )


@pytest.mark.parametrize("slug", VIGIL_ENDINGS)
@pytest.mark.parametrize(
    "before,after",
    [
        ("Your Son", "Thy Son"),
        ("our Lord", "a lord"),
        ("as God", "as a god"),
        ("lives and reigns", "will live and reign"),
        ("Your Son", "Your servant"),
    ],
)
def test_vigil_conclusion_successor_does_not_relax_meaning(slug, before, after):
    expected = VIGIL_ENDINGS[slug]
    altered = expected.replace(before, after)
    assert altered != expected
    assert not register.conclusion_matches(altered + " forever and ever.", expected, duration=True)


@pytest.mark.parametrize("index", range(len(DATA["transitions"])))
def test_every_named_preface_transition_remains_exact(index):
    doc, layer = constructions.load("paschalis-in-nocte")
    row = DATA["transitions"][index]
    parts = row["path"].split("/")[1:]
    parent = layer
    for part in parts[:-1]:
        parent = parent[part]
    key = parts[-1]
    if not row["after_present"]:
        parent[key] = "duplicated source realization"
    elif isinstance(parent[key], list):
        parent[key][0]["words"].pop()
    else:
        parent[key] += " Source meaning changed."
    with pytest.raises(AssertionError):
        constructions.assert_protected(doc, layer, "paschalis-in-nocte")


@pytest.mark.parametrize(
    "mutation", ["about", "note", "unselected-gloss", "word-order", "extra-word"]
)
def test_preface_inverse_cannot_mask_unrelated_fields(mutation):
    doc, layer = constructions.load("paschalis-in-nocte")
    if mutation == "about":
        layer["about"] += " Changed."
    elif mutation == "note":
        layer["words"]["w006"]["explanation"] = "Unsupported source claim."
    elif mutation == "unselected-gloss":
        layer["words"]["w006"]["gloss"] = "unfitting"
    elif mutation == "word-order":
        layer["words"] = dict(reversed(list(layer["words"].items())))
    else:
        layer["words"]["w067"] = {"gloss": "additional sacred text"}
    with pytest.raises(AssertionError):
        constructions.assert_protected(doc, layer, "paschalis-in-nocte")


@pytest.mark.parametrize("mutation", ["source", "origin", "review", "target"])
def test_working_preface_hash_update_does_not_reseal_or_rebind(mutation):
    doc, layer = constructions.load("paschalis-in-nocte")
    record = next(
        r
        for r in json.loads((ROOT / "languages/en/translation-provenance.json").read_text())[
            "sites"
        ]
        if r["text"] == doc["id"]
    )
    if mutation == "source":
        record["source_sha256"] = "0" * 64
    elif mutation == "target":
        record["target_sha256"] = "0" * 64
    elif mutation == "origin":
        record["origin"] = "independent"
    else:
        record["review"] = "approved"
    with pytest.raises(AssertionError):
        constructions.assert_provenance(record, doc, layer, "paschalis-in-nocte")


@pytest.mark.parametrize(
    "gloss",
    [
        "will destroy our death by dying",
        "has destroyed their death by dying",
        "has destroyed our life by dying",
        "has destroyed our death after dying",
    ],
)
def test_possessive_complete_predicate_keeps_means_agency_and_object(gloss):
    site = next(s for s in possessives.SITES if s[0] == "paschalis-in-nocte" and s[2] == 37)
    doc, layer = possessives.load(site[0])
    group = next(g for g in layer["segments"]["s01"]["alignments"] if "w040" in g["words"])
    group["gloss"] = gloss
    with pytest.raises(AssertionError):
        possessives.assert_site(doc, layer, site)


@pytest.mark.parametrize("mutation", ["claim", "date", "decision", "apparatus-note"])
def test_new_source_claim_and_note_are_narrow_not_blanket_renewal(mutation):
    if mutation == "apparatus-note":
        data = json.loads(
            (ROOT / "witnesses/ordinarium.praefatio-paschalis-in-nocte/apparatus.json").read_text()
        )
        data["note"] += " This includes the expanded conclusion."
        with pytest.raises(AssertionError):
            source.check_readings(data, "paschalis-in-nocte")
    else:
        data = source.graph()
        value = source.use(data, "paschalis-in-nocte")
        if mutation == "claim":
            value["claim"] = value["claim"].replace("w001–w020", "w001–w066")
        elif mutation == "date":
            value["verified_on"] = "2026-10-04"
        else:
            value["decision_reason"] = value["decision_reason"].replace(
                "without granting", "granting"
            )
        with pytest.raises(AssertionError):
            source.check_primary(data, "paschalis-in-nocte")


def test_common_preface_closing_restores_only_the_fixed_formula():
    assert current_prose().endswith(
        "And therefore with Angels and Archangels, with Thrones and Dominions, "
        "and with all the host of the heavenly army, we sing the hymn of Your glory, "
        "evermore saying:"
    )
    assert "salutary" in current_prose() and "He Himself" in current_prose()
    assert "has destroyed our death by dying" in current_prose()


@pytest.mark.parametrize(
    "mutation", ["missing", "duplicate", "wrong-agent", "future", "missing-pascha"]
)
def test_polish_sacrifice_full_predicate_remains_complete(mutation):
    layer = json.loads(
        (ROOT / "languages/pl/texts/ordinarium/praefatio-paschalis-in-nocte.json").read_text()
    )
    group = next(g for g in layer["segments"]["s01"]["alignments"] if "w024" in g["words"])
    if mutation == "missing":
        group["words"].remove("w025")
    elif mutation == "duplicate":
        layer["words"]["w025"]["gloss"] = "został"
    elif mutation == "wrong-agent":
        group["gloss"] = "Chrystus, nasza Pascha, ofiarował"
    elif mutation == "future":
        group["gloss"] = "Chrystus, nasza Pascha, zostanie ofiarowany"
    else:
        group["gloss"] = "Chrystus został ofiarowany"
    with pytest.raises(AssertionError):
        contexts.assert_sacrifice(
            layer, [f"w{n:03d}" for n in range(22, 27)], "Chrystus, nasza Pascha, został ofiarowany"
        )


@pytest.mark.parametrize(
    "wid,key,value",
    [
        ("w071", "case", "nom"),
        ("w072", "case", "acc"),
        ("w075", "person", 3),
        ("w075", "number", "sg"),
    ],
)
def test_shared_seek_group_does_not_hide_source_roles(wid, key, value):
    doc, layers = store.load(ROOT, "proprium.vigilia-paschalis-evangelium")
    doc = deepcopy(doc)
    word = next(w for s in doc["segments"] for w in s["words"] if w["id"] == wid)
    assert word["morph"][key] != value
    word["morph"][key] = value
    with pytest.raises(AssertionError):
        finite.assert_boundary(
            doc, layers["en"], {}, [([71, 72, 73, 74, 75], 75, "you seek Jesus, who was crucified")]
        )

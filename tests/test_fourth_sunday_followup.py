"""Fourth Sunday caption relations and explicit proper/conclusion boundaries."""

import copy
import json
from pathlib import Path

import pytest

from checks.interlinear import check as providers
from checks.language_packs import check_layer
from checks.raw_binding import resolve_binding

ROOT = Path(__file__).resolve().parents[1]
P = "proprium.dominica-iv-post-epiphaniam-"
GROUPS = [
    ("epistola", "pl", 22, 25, 25, "Nie mów fałszywego świadectwa"),
    ("postcommunio", "pl", 10, 13, 12, "zawsze odnawiają niebieskimi pokarmami"),
    ("collecta", "en", 22, 30, 30, "with Your help we may overcome what we suffer for our sins"),
    ("evangelium", "en", 8, 12, 8, "His disciples followed Him"),
    ("evangelium", "en", 15, 16, 15, "a great tempest"),
    ("evangelium", "en", 30, 34, 30, "His disciples came to Him"),
    ("evangelium", "en", 44, 46, 44, "Jesus says to them"),
    ("evangelium", "en", 48, 51, 49, "are you fearful, you of little faith"),
    ("evangelium", "en", 61, 62, 61, "a great calm"),
    ("secreta", "en", 6, 9, 8, "the offered gift of this sacrifice"),
    ("secreta", "en", 10, 16, 15, "may always cleanse our frailty from all evil"),
    ("postcommunio", "en", 1, 2, 1, "Your gifts"),
    ("postcommunio", "en", 3, 8, 8, "may free us, O God, from earthly delights"),
    ("postcommunio", "en", 10, 13, 12, "always renew us with heavenly nourishment"),
    ("secreta", "en", 20, 21, 20, "our Lord"),
    ("secreta", "en", 24, 25, 24, "Your Son"),
    ("secreta", "en", 36, 39, 38, "forever and ever"),
    ("postcommunio", "en", 15, 16, 15, "our Lord"),
    ("postcommunio", "en", 19, 20, 19, "Your Son"),
    ("postcommunio", "en", 31, 34, 33, "forever and ever"),
]


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def documents(slug, language):
    rel = "texts/proprium/dominica-iv-post-epiphaniam-" + slug + ".json"
    return load(rel), load("languages/" + language + "/" + rel)


def group(layer, first, last, anchor, caption):
    ids = [f"w{n:03}" for n in range(first, last + 1)]
    found = [
        g
        for s in layer["segments"].values()
        for g in s.get("alignments", [])
        if set(g["words"]) & set(ids)
    ]
    assert found == [{"words": ids, "anchor": f"w{anchor:03}", "gloss": caption}]
    assert all("gloss" not in layer["words"][w] for w in ids)


@pytest.mark.parametrize("slug,language,first,last,anchor,caption", GROUPS)
def test_captions_preserve_clause_relations(slug, language, first, last, anchor, caption):
    core, layer = documents(slug, language)
    assert not providers(core, layer)
    path = (
        ROOT
        / "languages"
        / language
        / "texts/proprium"
        / ("dominica-iv-post-epiphaniam-" + slug + ".json")
    )
    assert not check_layer(core, layer, path)
    group(layer, first, last, anchor, caption)


@pytest.mark.parametrize("case", [GROUPS[3], GROUPS[10], GROUPS[13]])
@pytest.mark.parametrize("mutation", ["member", "anchor", "caption", "duplicate", "scalar"])
def test_caption_guard_rejects_changed_relation_or_provider(case, mutation):
    slug, language, first, last, anchor, caption = case
    _, layer = documents(slug, language)
    group(layer, first, last, anchor, caption)
    before = copy.deepcopy(layer)
    selected = next(
        g
        for s in layer["segments"].values()
        for g in s.get("alignments", [])
        if g["words"][0] == f"w{first:03}"
    )
    if mutation == "member":
        selected["words"].pop()
    elif mutation == "anchor":
        selected["anchor"] = f"w{first if anchor != first else last:03}"
    elif mutation == "caption":
        selected["gloss"] = "our frailty cleanses the offered gift"
    elif mutation == "duplicate":
        layer["segments"]["s01"]["alignments"].append(copy.deepcopy(selected))
    else:
        layer["words"][f"w{last:03}"]["gloss"] = "the recipient"
    with pytest.raises(AssertionError):
        group(layer, first, last, anchor, caption)
    group(before, first, last, anchor, caption)


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("mutation", ["note", "declaration"])
def test_why_note_has_two_language_layers(language, mutation):
    core, layer = documents("evangelium", language)
    path = (
        ROOT / "languages" / language / "texts/proprium/dominica-iv-post-epiphaniam-evangelium.json"
    )
    assert not check_layer(core, layer, path)
    assert layer["words"]["w047"]["explanation"]
    if mutation == "note":
        del layer["words"]["w047"]["explanation"]
    else:
        del core["localization"]["explanations"]["w047"]
    assert check_layer(core, layer, path)


def test_why_remains_a_neuter_accusative_pronoun_pending():
    doc, _ = documents("evangelium", "en")
    word = next(w for s in doc["segments"] for w in s["words"] if w["id"] == "w047")
    assert word["lemma"] == "quis"
    assert word["morph"] == {"pos": "pron", "case": "acc", "number": "sg", "gender": "n"}
    assert doc["editorial"]["words"]["w047"]["analysis"] == {
        "confidence": "high",
        "sources": ["editorial", "whitakers", "collatinus"],
        "review": "pending",
    }


@pytest.mark.parametrize("first,last", [(16, 17), (18, 19), (20, 21), (22, 25), (26, 27)])
def test_commandments_keep_shall_not_prediction_will(first, last):
    _, layer = documents("epistola", "en")
    selected = next(
        g for g in layer["segments"]["s01"]["alignments"] if g["words"][0] == f"w{first:03}"
    )
    assert selected["words"][-1] == f"w{last:03}"
    assert "shall not" in selected["gloss"] and "will" not in selected["gloss"]
    assert layer["words"]["w038"]["gloss"] == "You shall love"


@pytest.mark.parametrize("slug,body", [("secreta", 18), ("postcommunio", 13)])
def test_full_ending_is_declared_house_expansion_not_proper_page(slug, body):
    graph = load("bibliography/graph.json")
    witness = next(w for w in graph["witnesses"] if w["id"] == "witness." + P + slug + ".mr1962")
    assert witness["orthography_profile"] == "page-body-with-declared-house-expansion"
    assert witness["review"] == {"status": "pending"}
    assert (
        "use." + P + slug + ".expanded-conclusion.mr1962" in witness["source_dependencies"]["uses"]
    )
    raw = (ROOT / "witnesses" / (P + slug) / "mr.txt").read_text()
    assert f"{body} proper words" in raw and "house accents" in raw
    assert "not one continuous printing" in raw


@pytest.mark.parametrize("slug", ["collecta", "epistola", "evangelium", "secreta", "postcommunio"])
def test_exact_pinned_readings_resolve_with_original_body_and_formula(slug):
    witness = ROOT / "witnesses" / (P + slug) / "do.txt"
    resolved = resolve_binding(witness, ROOT)
    assert resolved.text
    body = " ".join(
        line for line in witness.read_text().splitlines() if line and not line.startswith("#")
    )
    assert resolved.text == body

"""The shared Secret retains its proper accidentals and declared ending boundaries."""

import json
from pathlib import Path

import pytest

from checks.collate import collate, load_witness
from checks.interlinear import check as check_interlinear
from checks.language_packs import check_layer
from checks.raw_binding import resolve_binding

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.dominica-iii-post-epiphaniam-secreta"
REL = "texts/proprium/dominica-iii-post-epiphaniam-secreta.json"
PROPER = (
    "Hæc hóstia, Dómine, quǽsumus, emúndet nostra delícta: et ad sacrifícium "
    "celebrándum, subditórum tibi córpora mentésque sanctíficet. Per Dóminum."
)
REUSES = [
    (
        "mr-quinquagesima",
        "quinquagesima.mr1962",
        134,
        55,
        "869d4b71c0ba05533e9c42abd53ec9db3d24110c1a095ac3a5ed7907f76979e3",
    ),
    (
        "mr-lent-iii",
        "lent-iii.mr1962",
        172,
        93,
        "873e24b97c4ee2f2ae57abdc8873f74387443e24b03cc3b5b7cc615d8c364103",
    ),
    (
        "mr-resumed",
        "resumed.mr1962",
        494,
        413,
        "6813dc2e9bb2a503cf21219e0197a8b560dffcfbfc3fbfb363e34d47eae5a72b",
    ),
]


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def child():
    return load(REL)


def graph():
    return load("bibliography/graph.json")


def test_every_direct_consumer_retains_the_same_secret():
    found = []
    for path in sorted((ROOT / "formularies").rglob("*.json")):
        for component in load(path.relative_to(ROOT)).get("components", []):
            if component.get("text") == TEXT:
                found.append((path.stem, component))
    expected = {
        "dominica-iii-in-quadragesima": "reference",
        "dominica-iii-post-epiphaniam": "proper",
        "dominica-iii-quae-superfuit-post-epiphaniam": "reference",
        "dominica-in-quinquagesima": "reference",
    }
    assert found == [
        (
            name,
            {"key": "secreta", "role": "secreta", "text": TEXT, "relation": relation},
        )
        for name, relation in sorted(expected.items())
    ]


@pytest.mark.parametrize("name,suffix,leaf,page,source_hash", REUSES)
def test_each_reuse_has_its_exact_body_cue_and_partial_source(
    name, suffix, leaf, page, source_hash
):
    meta, body = load_witness(ROOT / "witnesses" / TEXT / f"{name}.txt")
    expected = PROPER.replace("córpora mentésque", "córpora, mentésque")
    if name == "mr-quinquagesima":
        expected = expected.replace("quǽsumus,", "quǽsumus:")
    assert body == expected and len(body.split()) == 18
    assert meta["covers"] == "w001-w018"
    assert meta["location"] == f"printed p. {page}; leaf n{leaf} / PDF p. {leaf + 1}"
    use = next(u for u in graph()["uses"] if u["id"] == f"use.{TEXT}.{suffix}")
    assert use["evidence_sha256"] == source_hash
    assert use["locator"]["printed"] == f"p. {page}"
    assert use["locator"]["scan"] == f"leaf n{leaf} / PDF p. {leaf + 1}"
    assert use["address"] == {"kind": "text", "text": TEXT}
    assert use["role"] == "direct_approved_print"
    witness = next(w for w in graph()["witnesses"] if w["id"] == f"witness.{TEXT}.{name}")
    assert witness["use"] == use["id"]
    assert witness["coverage"] == {
        "kind": "words",
        "words": [f"w{i:03}" for i in range(1, 19)],
    }
    assert witness["review"] == {"status": "pending"}
    assert witness["source_dependencies"] == {"uses": [], "raw_binding": None}


def test_variants_do_not_rewrite_the_owning_proper_or_expand_the_cue():
    words = {w["id"]: w for s in child()["segments"] for w in s["words"]}
    assert (words["w004"]["form"], words["w004"]["post"]) == ("quǽsumus", ",")
    assert words["w014"]["form"] == "córpora" and "post" not in words["w014"]
    assert words["w018"]["form"] == "Dóminum" and "post" not in words["w018"]
    app = load(f"witnesses/{TEXT}/apparatus.json")["adjudicated"]
    selected = {e["at"]: e for e in app if e["at"] in {"w004", "w014", "w018"}}
    assert selected["w004"]["witnesses"] == {"mr-quinquagesima": "quǽsumus:"}
    assert selected["w014"]["witnesses"] == {r[0]: "córpora," for r in REUSES}
    assert selected["w018"]["witnesses"] == {r[0]: "Dóminum." for r in REUSES}
    assert collate(child(), ROOT / "witnesses" / TEXT)[:2] == ([], [])


def test_quiet_formula_audible_terminal_and_response_remain_distinct():
    s1, s2, s3 = child()["segments"]
    assert [w["id"] for w in s1["words"]] == [f"w{i:03}" for i in range(1, 34)]
    assert (s1["speaker"], s1["voice"]) == ("sacerdos", "secreto")
    assert [w["id"] for w in s2["words"]] == [f"w{i:03}" for i in range(34, 38)]
    assert (s2["speaker"], s2["voice"]) == ("sacerdos", "clara")
    assert s2["delivery"] == {"cantu": {"speaker": "sacerdos", "voice": "cantus"}}
    assert [(w["id"], w["form"]) for w in s3["words"]] == [("w038", "Amen")]
    assert (s3["speaker"], s3["voice"]) == ("minister", "clara")
    assert s3["delivery"] == {"cantu": {"speaker": "schola", "voice": "cantus"}}
    assert s3["participation"] == {
        "lecta": {"gradus": 1, "source": "DMS 31 a"},
        "cantu": {"gradus": 1, "source": "DMS 25 a"},
    }
    meta, _ = load_witness(ROOT / "witnesses" / TEXT / "mr.txt")
    assert "response marker alone does not name minister or schola" in meta["response-scope"]
    assert "Collect or Postcommunion" not in meta["response-scope"]


def test_reprints_stay_outside_the_composite_and_the_borrowed_loci_keep_their_pages():
    uses = {u["id"]: u for u in graph()["uses"]}
    witnesses = {w["id"]: w for w in graph()["witnesses"]}
    composite = witnesses[f"witness.{TEXT}.mr1962"]["source_dependencies"]["uses"]
    assert not {f"use.{TEXT}.{suffix}" for _, suffix, *_ in REUSES} & set(composite)
    pages = {
        "conclusion-terminal": "c8a123467dd47ace390100a021fdcdd61752a5c42635583b92d72cd636027f58",
        "oration-boundaries": "c03be5250068f8c9c262983bc7689a18d0180b88b0c4476d21fac383c8f07993",
    }
    for suffix, digest in pages.items():
        assert uses[f"use.{TEXT}.{suffix}.mr1962"]["evidence_sha256"] == digest


def test_the_pinned_digital_composite_retains_the_body_and_resolved_ending():
    result = resolve_binding(ROOT / "witnesses" / TEXT / "do.txt", ROOT)
    assert result is not None
    assert result.text.startswith("Hæc hóstia, Dómine, quǽsumus, emúndet nostra delícta: et,")
    assert result.text.endswith("Deus, per ómnia sǽcula sæculórum. Amen.")
    assert len(result.text.split()) == 38


@pytest.mark.parametrize("lang", ["pl", "en"])
def test_two_petitions_keep_both_objects_and_their_common_subject(lang):
    doc = child()
    words = {w["id"]: w for s in doc["segments"] for w in s["words"]}
    assert words["w001"]["morph"] == {
        "pos": "pron",
        "case": "nom",
        "number": "sg",
        "gender": "f",
    }
    for wid in ("w005", "w016"):
        assert words[wid]["morph"]["person"] == 3
        assert words[wid]["morph"]["number"] == "sg"
        assert words[wid]["morph"]["mood"] == "subj"
    assert words["w007"]["morph"]["case"] == "acc"
    assert words["w014"]["morph"]["case"] == "acc"
    assert words["w015"]["morph"]["case"] == "acc"
    assert words["w012"]["morph"]["case"] == "gen" and words["w012"]["substantive"] is True
    assert words["w013"]["morph"]["case"] == "dat"
    layer = load(f"languages/{lang}/{REL}")
    assert check_interlinear(doc, layer) == []
    assert check_layer(doc, layer, ROOT / f"languages/{lang}/{REL}") == []
    second = next(g for g in layer["segments"]["s01"]["alignments"] if g["words"][0] == "w012")
    assert second == {
        "words": [f"w{i:03}" for i in range(12, 17)],
        "anchor": "w012",
        "gloss": (
            "niech uświęci ciała i umysły poddanych Tobie"
            if lang == "pl"
            else "sanctify the bodies and minds of those subject to You"
        ),
    }
    assert layer["words"]["w006"]["gloss"] == ("nasze" if lang == "pl" else "our")
    assert layer["words"]["w007"]["gloss"] == ("przewinienia" if lang == "pl" else "offenses")
    assert layer["words"]["w008"]["gloss"] == ("i" if lang == "pl" else "and")
    assert layer["words"]["w009"]["gloss"] == ("do" if lang == "pl" else "for")

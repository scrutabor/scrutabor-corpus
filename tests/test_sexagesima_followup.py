"""Sexagesima source seams, grammatical relations and bounded reading aids."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import store
from build_reader.bibliography_bindings import digest, selected_text, transcript_digest
from checks import interlinear, raw_binding
from checks.collate import collate, load_witness
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
P = "proprium.dominica-in-sexagesima-"
MENTIOR = [
    (P + "epistola", "w201"),
    ("proprium.dominica-iii-post-pascha-introitus", "w030"),
    ("proprium.omnium-sanctorum-evangelium", "w099"),
]


def load(relative):
    return json.loads((ROOT / relative).read_bytes())


def words(doc):
    return {w["id"]: w for s in doc["segments"] for w in s.get("words", [])}


def analysis(doc, wid):
    editorial = doc["editorial"]
    default = editorial.get("analysis_defaults_words") or editorial["analysis_defaults"]
    return editorial.get("words", {}).get(wid, {}).get("analysis", default)


def layer(role, lang):
    return store.raw_layer(ROOT, lang, P + role)


def body(role, name):
    return load_witness(ROOT / "witnesses" / (P + role) / (name + ".txt"))[1]


def group(value, ids):
    return next(
        g for s in value["segments"].values() for g in s.get("alignments", []) if g["words"] == ids
    )


def assert_source_loci(graph, role):
    text = P + role
    witness = next(
        w for w in graph["witnesses"] if w["text"] == text and w["transcription"] == "mr"
    )
    expected = (
        ["gloria-and-repeat"]
        if role == "introitus"
        else ["conclusion-middle", "conclusion-rg115a", "conclusion-terminal"]
    )
    assert witness["source_dependencies"] == {
        "uses": sorted(f"use.{text}.{name}.mr1962" for name in expected),
        "raw_binding": None,
    }
    assert witness["orthography_profile"] == "exact-declared-composite"
    assert witness["review"] == {"status": "pending"}
    primary = next(u for u in graph["uses"] if u["id"] == f"use.{text}.mr1962")
    assert "does not print the complete expanded" in primary["claim"]
    leaves = {
        "gloria-and-repeat": 80,
        "conclusion-middle": 202,
        "conclusion-rg115a": 22,
        "conclusion-terminal": 305,
    }
    for name in expected:
        use = next(u for u in graph["uses"] if u["id"] == f"use.{text}.{name}.mr1962")
        assert use["locator"]["page_url"].endswith(f"/page/n{leaves[name]}/mode/1up")
        if name == "conclusion-terminal":
            assert use["locator"]["section"] == "Sung Nativity Preface dialogue"
            assert "not the speaker of the Collect response by itself" in use["claim"]


@pytest.mark.parametrize("role", ["introitus", "collecta", "secreta"])
def test_expansions_identify_all_separate_loci(role):
    graph = load("bibliography/graph.json")
    assert_source_loci(graph, role)
    doc = store.core(ROOT, P + role)
    witness = next(
        w for w in graph["witnesses"] if w["text"] == doc["id"] and w["transcription"] == "mr"
    )
    raw = (ROOT / "witnesses" / doc["id"] / "mr.txt").read_text()
    assert "# composite:" in raw
    assert witness["transcription_sha256"] == transcript_digest(raw)
    collation = next(c for c in graph["collations"] if c["text"] == doc["id"])
    assert collation["selected_text_sha256"] == digest(selected_text(doc))
    assert collation["review"] == {"status": "pending"}


@pytest.mark.parametrize("role", ["introitus", "collecta", "secreta"])
def test_removed_expansion_dependency_is_not_a_complete_inventory(role):
    good = load("bibliography/graph.json")
    assert_source_loci(good, role)
    bad = deepcopy(good)
    next(w for w in bad["witnesses"] if w["text"] == P + role and w["transcription"] == "mr")[
        "source_dependencies"
    ]["uses"].pop()
    with pytest.raises(AssertionError):
        assert_source_loci(bad, role)
    assert_source_loci(good, role)


def test_source_words_and_raw_digital_readings_remain_distinct():
    ep = store.core(ROOT, P + "epistola")
    assert "post" not in words(ep)["w045"]
    assert len(ep["segments"][0]["parentheses"]) == 3
    assert "scit:-" not in body("epistola", "mr")
    assert "scit:" in body("epistola", "mr")
    assert words(store.core(ROOT, P + "graduale"))["w012"]["post"] == "."
    assert "terram." in body("graduale", "mr") and "terram," in body("graduale", "do")
    gospel = store.core(ROOT, P + "evangelium")
    assert (words(gospel)["w206"]["form"], words(gospel)["w206"]["lemma"]) == (
        "áfferunt",
        "affero",
    )
    assert analysis(gospel, "w206") == {
        "confidence": "high",
        "sources": ["editorial", "whitakers", "collatinus"],
        "review": "pending",
    }
    for role in ("epistola", "graduale", "evangelium"):
        reading = raw_binding.resolve_binding(ROOT / "witnesses" / (P + role) / "do.txt", ROOT)
        assert reading is not None and reading.text == body(role, "do")
        assert collate(store.core(ROOT, P + role), ROOT / "witnesses" / (P + role))[:2] == ([], [])


def test_damascus_location_and_audierint_uncertainty_are_honest():
    ep = store.core(ROOT, P + "epistola")
    assert words(ep)["w202"]["morph"] == {
        "pos": "noun",
        "case": "loc",
        "gender": "f",
        "number": "sg",
        "decl": 2,
    }
    assert load("lexicon/lemmata.json")["entries"]["Damascus"]["gender"] == "f"
    assert analysis(ep, "w202")["sources"] == ["editorial"]
    assert analysis(ep, "w202")["review"] == "pending"
    gospel = store.core(ROOT, P + "evangelium")
    assert words(gospel)["w146"]["morph"]["mood"] == "ind"
    assert words(gospel)["w146"]["morph"]["tense"] == "futperf"
    assert analysis(gospel, "w146") == {
        "confidence": "medium",
        "sources": ["editorial", "collatinus"],
        "review": "pending",
    }
    for lang, phrase in [
        ("pl", "Wybór trybu pozostaje niepewny"),
        ("en", "The choice of mood remains uncertain"),
    ]:
        assert phrase in layer("evangelium", lang)["words"]["w146"]["explanation"]
        assert "Damásci" in layer("epistola", lang)["words"]["w202"]["explanation"]


@pytest.mark.parametrize(
    "role,wid,gender",
    [
        ("epistola", "w043", "n"),
        ("epistola", "w156", "n"),
        ("epistola", "w320", "n"),
        ("evangelium", "w089", "m"),
    ],
)
def test_local_pronoun_relations_have_explicit_gender(role, wid, gender):
    doc = store.core(ROOT, P + role)
    assert words(doc)[wid]["morph"]["gender"] == gender
    assert analysis(doc, wid)["review"] == "pending"


@pytest.mark.parametrize("text,wid", MENTIOR)
def test_mentior_is_fourth_without_other_morphology_changes(text, wid):
    doc = store.core(ROOT, text)
    found = words(doc)[wid]
    assert found["lemma"] == "mentior" and found["morph"]["conj"] == 4
    assert found["morph"]["voice"] == "dep"
    assert load("lexicon/lemmata.json")["entries"]["mentior"]["conj"] == 4
    assert analysis(doc, wid)["review"] == "pending"
    if wid == "w099":
        assert found["head"] == "w094"


@pytest.mark.parametrize(
    "lang,role,ids,caption",
    [
        ("pl", "epistola", ["w344", "w345", "w346"], "aby mnie policzkował"),
        ("en", "epistola", ["w344", "w345", "w346"], "to strike me"),
        ("pl", "tractus", ["w015", "w016"], "przed"),
        (
            "pl",
            "evangelium",
            ["w136", "w137", "w138", "w139"],
            "aby, wierząc, nie zostali zbawieni",
        ),
        (
            "en",
            "evangelium",
            ["w136", "w137", "w138", "w139"],
            "so that they may not be saved through believing",
        ),
        (
            "pl",
            "evangelium",
            ["w141", "w142", "w143", "w144"],
            "ci na skale to ci, którzy",
        ),
        (
            "en",
            "evangelium",
            ["w156", "w157", "w158", "w159"],
            "they believe for a while",
        ),
    ],
)
def test_complete_small_constructions_keep_their_relations(lang, role, ids, caption):
    target = layer(role, lang)
    assert group(target, ids)["gloss"] == caption
    assert interlinear.check(store.core(ROOT, P + role), target) == []
    if role == "tractus":
        assert target["words"]["w017"]["gloss"] == "łukiem"


@pytest.mark.parametrize("lang", ["pl", "en"])
@pytest.mark.parametrize(
    "text",
    [P + "epistola", P + "graduale", P + "evangelium", MENTIOR[1][0], MENTIOR[2][0]],
)
def test_changed_sources_reset_only_working_prose_observations(lang, text):
    doc = store.core(ROOT, text)
    ledger = load(f"languages/{lang}/translation-provenance.json")
    rows = {r["segment"]: r for r in ledger["sites"] if r["text"] == text}
    target = store.raw_layer(ROOT, lang, text)
    for segment in doc["segments"]:
        if segment["type"] != "verse":
            continue
        row = rows[segment["id"]]
        assert row["source_sha256"] == canonical_hash(source_payload(segment))
        assert row["target_sha256"] == canonical_hash(
            target["segments"][segment["id"]]["translation"]
        )
        assert row["review"] == "working"

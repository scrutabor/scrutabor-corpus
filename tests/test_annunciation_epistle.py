"""The Annunciation reading's exact constructions and source boundaries."""

import json
from pathlib import Path

import pytest

from build_reader import bibliography_bindings, store
from checks import interlinear, language_packs, raw_binding, syntax
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.annuntiatio-beatae-mariae-virginis-epistola"
PL = {12: "o znak", 18: "głębi", 21: "na", 22: "wysokości", 37: "domu", 46: "że", 73: "będzie jadł"}
EN = {
    17: "in",
    18: "the depth",
    19: "of hell",
    21: "in",
    22: "the height",
    34: "he said",
    38: "of David",
    57: "you",
    58: "a sign",
    60: "a virgin",
    73: "He will eat",
    75: "He may know how",
}
GROUPS = [
    ([2, 3], 2, "those days"),
    ([4, 5, 6], 4, "the Lord spoke"),
    ([10, 11, 12], 10, "ask for a sign for yourself"),
    ([15, 16], 15, "your God"),
    ([25, 26], 25, "Achaz said"),
    ([27, 28], 28, "I will not ask"),
    ([30, 31], 31, "I will not test"),
    ([39, 40, 41, 42], 42, "is it too little for you"),
    ([43, 44], 43, "to be troublesome"),
    ([47, 48], 47, "you are troublesome"),
    ([50, 51], 50, "to my God"),
    ([54, 55, 56], 54, "the Lord Himself will give"),
    ([66, 67, 68], 66, "His name will be called"),
]


@pytest.mark.parametrize(
    "language,number,gloss",
    [("pl", n, g) for n, g in PL.items()] + [("en", n, g) for n, g in EN.items()],
)
def test_direct_contextual_realizations(language, number, gloss):
    layer = store.raw_layer(ROOT, language, TEXT)
    assert layer["words"][f"w{number:03}"]["gloss"] == gloss


@pytest.mark.parametrize("members,anchor,gloss", GROUPS)
def test_minimal_english_group_has_exactly_one_provider(members, anchor, gloss):
    layer = store.raw_layer(ROOT, "en", TEXT)
    ids = [f"w{n:03}" for n in members]
    groups = [a for a in layer["segments"]["s01"]["alignments"] if set(ids) & set(a["words"])]
    assert groups == [{"words": ids, "anchor": f"w{anchor:03}", "gloss": gloss}]
    assert all("gloss" not in layer["words"][wid] for wid in ids)


def test_complete_provider_partition_and_retained_readings():
    core, layers = store.load(ROOT, TEXT)
    assert len(core["segments"]) == 1 and len(core["segments"][0]["words"]) == 80
    for language, direct, groups, members in [("pl", 74, 3, 6), ("en", 48, 13, 32)]:
        raw = store.raw_layer(ROOT, language, TEXT)
        assert interlinear.check(core, layers[language]) == []
        assert sum("gloss" in w for w in raw["words"].values()) == direct
        alignments = raw["segments"]["s01"]["alignments"]
        assert len(alignments) == groups and sum(len(a["words"]) for a in alignments) == members
        assert direct + members == 80
    pl = store.raw_layer(ROOT, "pl", TEXT)
    assert pl["words"]["w076"]["gloss"] == "odrzucić"
    assert pl["words"]["w015"]["gloss"] == "Boga"
    assert pl["words"]["w016"]["gloss"] == "twojego"
    assert store.raw_layer(ROOT, "en", TEXT)["words"]["w008"]["gloss"] == "Achaz"
    assert pl["about"].startswith("Epistoła ")
    assert store.raw_layer(ROOT, "en", TEXT)["about"].startswith("The Epistle ")


def test_omitted_subject_is_not_substantivization_or_false_agreement():
    raw = store.core(ROOT, TEXT)
    doc, _layers = store.load(ROOT, TEXT)
    word = raw["segments"][0]["words"][42]
    assert word == {
        "id": "w043",
        "form": "moléstos",
        "lemma": "molestus",
        "morph": {"pos": "adj", "case": "acc", "gender": "m", "number": "pl"},
        "ellipsis": "predicate",
    }
    assert doc["segments"][0]["words"][42]["analysis"]["review"] == "pending"
    assert syntax.check(doc) == [] and language_packs.check_core(raw) == []
    for language in ["pl", "en"]:
        layer = store.raw_layer(ROOT, language, TEXT)
        assert "vos" in layer["words"]["w043"]["explanation"]
        assert language_packs.check_layer(raw, layer, store.layer_path(ROOT, language, TEXT)) == []


def test_prose_and_working_provenance_are_not_rewritten_or_promoted():
    core = store.core(ROOT, TEXT)
    for language, digest in [
        ("pl", "50c8b572077ece348cd502b20492d7da13d67ada863285ce435560206ec9db86"),
        ("en", "e308b42e8dd6705227e2ec18e73ccc0f21c9827d5fdc34819605477b12013265"),
    ]:
        layer = store.raw_layer(ROOT, language, TEXT)
        assert canonical_hash(layer["segments"]["s01"]["translation"]) == digest
        provenance = json.loads(
            (ROOT / f"languages/{language}/translation-provenance.json").read_text()
        )
        sites = [s for s in provenance["sites"] if s["text"] == TEXT]
        assert len(sites) == 1
        site = sites[0]
        assert site["source_sha256"] == canonical_hash(source_payload(core["segments"][0]))
        assert site["target_sha256"] == digest
        assert (site["origin"], site["review"], site["familiar_core"]) == (
            "working-unsettled",
            "working",
            False,
        )


def test_exact_raw_chain_excludes_title_and_reference():
    bound = raw_binding.resolve_binding(ROOT / f"witnesses/{TEXT}/do.txt", ROOT)
    assert bound is not None
    assert len(bound.text.split()) == 80
    source = bound.source
    assert source["binding_id"] == "annunciation-epistle"
    binding = source["binding"]
    assert [(e["first"], e["last"], e["section_line"]) for e in binding["evidence"]] == [
        (18, 18, 17),
        (22, 22, 21),
        (46, 46, 43),
    ]
    assert [(r["line"], r["text"], r["target"]) for r in binding["references"]] == [
        (18, "@Commune/C10a", 1),
        (22, "@Tempora/Adv3-3", 2),
    ]
    assert [(r["first"], r["last"]) for r in binding["reading"]] == [(46, 46)]
    archives = source["archives"]
    assert len(archives) == 3
    assert [archives[e["archive"]]["upstream"] for e in binding["evidence"]] == [
        "web/www/missa/Latin/Sancti/03-25.txt",
        "web/www/horas/Latin/Commune/C10a.txt",
        "web/www/missa/Latin/Tempora/Adv3-3.txt",
    ]
    tokens = bound.text.split()
    assert (tokens[46], tokens[67], tokens[75]) == ("molesti", "ejus", "reprobare")


def test_exact_eleven_accidentals_and_pending_source_scope():
    graph = json.loads((ROOT / "bibliography/graph.json").read_text())
    doc = store.core(ROOT, TEXT)
    witnesses = [w for w in graph["witnesses"] if w["text"] == TEXT]
    assert len(witnesses) == 2
    subjects = {}
    for witness in witnesses:
        assert witness["review"] == {"status": "pending"}
        assert witness["coverage"] == {"kind": "full"}
        assert witness["source_dependencies"] == {
            "uses": [],
            "raw_binding": "annunciation-epistle" if witness["transcription"] == "do" else None,
        }
        subjects[witness["id"]] = bibliography_bindings.witness_subject(ROOT, witness, graph, doc)
    collations = [c for c in graph["collations"] if c["text"] == TEXT]
    assert len(collations) == 1 and collations[0]["review"] == {"status": "pending"}
    bibliography_bindings.collation_subject(ROOT, collations[0], doc, subjects)
    apparatus = json.loads((ROOT / f"witnesses/{TEXT}/apparatus.json").read_text())
    expected = [
        (14, "Dómino", "Dómino,", "punctuation"),
        (16, "tuo", "tuo,", "punctuation"),
        (28, "petam,", "petam", "punctuation"),
        (36, "ergo", "ergo,", "punctuation"),
        (47, "molésti", "molesti", "accent"),
        (59, "Ecce", "Ecce,", "punctuation"),
        (60, "virgo", "Virgo", "capitalization"),
        (61, "concípiet,", "concípiet", "punctuation"),
        (68, "eius", "ejus", "orthography"),
        (76, "reprobáre", "reprobare", "accent"),
        (77, "malum,", "malum", "punctuation"),
    ]
    assert [
        (e["at"], e["ours"], e["witnesses"]["do"], e["class"]) for e in apparatus["adjudicated"]
    ] == [(f"w{n:03}", a, b, c) for n, a, b, c in expected]
    assert apparatus["summary"] == {
        "entries": 11,
        "classes": ["accent", "capitalization", "orthography", "punctuation"],
    }
    use = next(u for u in graph["uses"] if u["id"] == witnesses[1]["use"])
    assert use["role"] == "direct_approved_print"
    assert use["locator"]["printed"] == "p. 495"
    assert "Benziger" in use["claim"] and "without" in use["claim"]
    assert "Benziger" in doc["editorial"]["source"]["method"]
    assert "80-word" in doc["editorial"]["notes"]

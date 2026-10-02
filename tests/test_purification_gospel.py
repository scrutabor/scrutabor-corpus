"""Purification Gospel: complete constructions and explicit clausal source syntax."""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from build_reader import store
from build_reader.bibliography_bindings import collation_subject, digest, witness_subject
from checks import english, interlinear, polish, raw_binding, syntax
from checks.collate import collate
from checks.punctuation import word_faces
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.purificatio-beatae-mariae-virginis-evangelium"
GROUPS = [
    ("pl", [82, 83], 83, "że nie ujrzy"),
    ("en", [5, 6, 7, 8, 9], 5, "the days of Mary’s purification were fulfilled"),
    ("en", [22, 23], 22, "it is written"),
    ("en", [32, 33, 34], 34, "shall be called holy to the Lord"),
    ("en", [41, 42], 41, "is said"),
    ("en", [54, 55], 55, "there was a man"),
    ("en", [62, 63], 62, "this man"),
    ("en", [71, 72], 71, "the Holy Spirit"),
    ("en", [77, 78], 78, "he had received a revelation"),
    ("en", [80, 81], 80, "the Holy Spirit"),
    ("en", [82, 83, 84], 83, "that he would not see"),
    ("en", [99, 100, 101, 102, 103], 99, "His parents were bringing in the Child Jesus"),
    ("en", [116, 117], 116, "his arms"),
    ("en", [125, 126], 125, "Your servant"),
    ("en", [129, 130], 129, "Your word"),
    ("en", [134, 135, 136], 134, "my eyes have seen"),
    ("en", [137, 138], 137, "Your salvation"),
    ("en", [151, 152], 151, "of Your people"),
]
DIRECT = [
    ("pl", 27, "że"),
    ("pl", 34, "będzie nazwane"),
    ("pl", 40, "tego, co"),
    ("pl", 49, "dwoje"),
    ("pl", 50, "piskląt"),
    ("pl", 85, "śmierci"),
    ("pl", 105, "postąpić"),
    ("en", 27, "that"),
    ("en", 44, "the Law"),
    ("en", 59, "name was"),
    ("en", 64, "was just"),
    ("en", 89, "the Christ"),
    ("en", 104, "to"),
    ("en", 105, "do"),
    ("en", 124, "You release"),
    ("en", 140, "You have prepared"),
    ("en", 148, "to the Gentiles"),
]


def wid(number):
    return f"w{number:03}"


@pytest.mark.parametrize("language,numbers,anchor,gloss", GROUPS)
def test_selected_complete_construction(language, numbers, anchor, gloss):
    # Selected-edition regression, not an assertion of exclusive grammar.
    raw = store.raw_layer(ROOT, language, TEXT)
    ids = [wid(number) for number in numbers]
    matches = [
        g for g in raw["segments"]["s01"].get("alignments", []) if set(g["words"]) & set(ids)
    ]
    assert matches == [{"words": ids, "anchor": wid(anchor), "gloss": gloss}]
    assert all("gloss" not in raw["words"][key] for key in ids)


@pytest.mark.parametrize("language,number,gloss", DIRECT)
def test_selected_direct_realization(language, number, gloss):
    assert store.raw_layer(ROOT, language, TEXT)["words"][wid(number)]["gloss"] == gloss


@pytest.mark.parametrize("language", ["pl", "en"])
def test_complete_provider_partition_and_contextual_dependencies(language):
    doc, layers = store.load(ROOT, TEXT)
    layer = layers[language]
    raw = store.raw_layer(ROOT, language, TEXT)
    assert len(doc["segments"]) == 1 and len(doc["segments"][0]["words"]) == 153
    assert interlinear.check(doc, layer) == []
    groups = raw["segments"]["s01"]["alignments"]
    assert (
        len(groups),
        sum(len(g["words"]) for g in groups),
        sum("gloss" in w for w in raw["words"].values()),
    ) == ((4, 8, 145) if language == "pl" else (17, 43, 110))

    def actual(first, last):
        return [
            value
            for n in range(first, last + 1)
            if (value := interlinear.effective_gloss(layer, wid(n)))
        ]

    if language == "pl":
        assert actual(82, 89) == [
            "że nie ujrzy",
            "on",
            "śmierci",
            "jeśli nie",
            "wcześniej",
            "ujrzy",
            "Chrystusa",
        ]
        assert actual(104, 108) == ["aby", "postąpić", "według", "przepisu", "Prawa"]
    else:
        assert actual(77, 89) == [
            "he had received a revelation",
            "from",
            "the Holy Spirit",
            "that he would not see",
            "death",
            "unless",
            "first",
            "he saw",
            "the Christ",
        ]
        assert actual(99, 112) == [
            "His parents were bringing in the Child Jesus",
            "to",
            "do",
            "according to",
            "the custom",
            "of the Law",
            "for",
            "Him",
            "also",
            "he",
        ]
    assert (polish.check(doc, layer) if language == "pl" else english.check(doc, layer)) == []


def test_internal_subject_is_not_governed_by_external_preposition():
    core = store.core(ROOT, TEXT)
    words = {w["id"]: w for w in core["segments"][0]["words"]}
    assert words["w039"]["clause_head"] == "w040" and "head" not in words["w039"]
    assert words["w039"]["morph"] == {"pos": "prep", "governs": "acc"}
    assert {k: words["w040"]["morph"][k] for k in ("case", "number", "gender")} == {
        "case": "nom",
        "number": "sg",
        "gender": "n",
    }
    assert words["w040"]["head"] == "w042"
    assert words["w041"]["head"] == "w040" and "substantive" not in words["w041"]
    assert syntax.check(store.load(ROOT, TEXT)[0]) == []
    assert all(
        core["editorial"]["words"][wid(n)]["analysis"]["review"] == "pending" for n in (39, 40, 41)
    )
    assert (
        " ".join(face.text for face in word_faces(core["segments"][0])[38:42])
        == "secúndum quod dictum est"
    )


@pytest.mark.parametrize("language", ["pl", "en"])
def test_working_prose_dependencies_and_localized_explanation(language):
    core = store.core(ROOT, TEXT)
    layer = store.raw_layer(ROOT, language, TEXT)
    assert core["localization"]["explanations"] == {"w039": {}, "w040": {}}
    for key in ("w039", "w040"):
        assert layer["words"][key]["explanation"].strip()
    records = json.loads((ROOT / f"languages/{language}/translation-provenance.json").read_text())[
        "sites"
    ]
    sites = [site for site in records if site["site"] == TEXT + ".s01." + language]
    assert len(sites) == 1
    site = sites[0]
    assert site["source_sha256"] == canonical_hash(source_payload(core["segments"][0]))
    assert (
        site["target_sha256"]
        == canonical_hash(layer["segments"]["s01"]["translation"])
        == (
            "4a3889550849bef5ae103d40855b4fc95826fc04f2cf9fd48986cd300f88328e"
            if language == "pl"
            else "78e54e6cee566541a429915db839afbc7099e0cb89aae8da7bd28b56fbbcf6c6"
        )
    )
    assert (site["origin"], site["review"], site["familiar_core"]) == (
        "working-unsettled",
        "working",
        False,
    )
    assert layer["about"].startswith("Ewangelia " if language == "pl" else "The Gospel ")


def test_exact_direct_source_and_true_accidentals():
    registry = json.loads((ROOT / "witnesses/raw/bindings.json").read_text())
    assert registry["bindings"]["purification-gospel"] == {
        "witness": f"witnesses/{TEXT}/do.txt",
        "revision": "44667ff518b8ff1439780470828b39714f5306a2",
        "evidence": [
            {
                "archive": "purification-day",
                "first": 193,
                "last": 193,
                "section": "Evangelium",
                "section_line": 190,
            }
        ],
        "references": [],
        "reading": [{"archive": "purification-day", "first": 193, "last": 193}],
    }
    archive = registry["archives"]["purification-day"]
    raw = (ROOT / archive["path"]).read_bytes()
    assert (
        hashlib.sha256(raw).hexdigest()
        == archive["sha256"]
        == "f149348ebd31599a32e17cccfc950d0f4eef24886d86bad6fd00bc3ef772520f"
    )
    lines = raw.decode().splitlines()
    assert len(lines) == 208 and lines[189] == "[Evangelium]" and lines[194] == "[Offertorium]"
    reading = raw_binding.resolve_binding(ROOT / f"witnesses/{TEXT}/do.txt", ROOT)
    assert reading is not None and reading.text == lines[192] and len(reading.text.split()) == 153
    ap = json.loads((ROOT / f"witnesses/{TEXT}/apparatus.json").read_text())
    assert ap["summary"] == {"entries": 13, "classes": ["accent", "orthography", "punctuation"]}
    assert [r["at"] for r in ap["adjudicated"]] == [
        wid(n) for n in (5, 12, 14, 16, 38, 47, 53, 57, 64, 101, 102, 103, 148)
    ]
    assert collate(store.load(ROOT, TEXT)[0], ROOT / "witnesses" / TEXT)[0] == []


def test_precise_print_identity_and_nonvacuous_pending_projection_inputs():
    graph = json.loads((ROOT / "bibliography/graph.json").read_text())
    core = store.core(ROOT, TEXT)
    uses = [use for use in graph["uses"] if use.get("address", {}).get("text") == TEXT]
    assert len(uses) == 2
    mr = next(use for use in uses if use["id"].endswith(".mr1962"))
    assert mr["role"] == "direct_approved_print" and "Benziger" in mr["claim"]
    assert mr["locator"] == {
        "printed": "p. 467",
        "scan": "leaf n548 / PDF p. 549",
        "page_url": "https://archive.org/details/missale-romanum-1962/page/n548/mode/1up",
    }
    assert (
        mr["evidence_sha256"] == "1d03b85122869acb77a773f78debebbc7c8f87bef4e0acc7088a77d6f8ecf9b6"
    )
    witnesses = [w for w in graph["witnesses"] if w["text"] == TEXT]
    assert len(witnesses) == 2 and {w["transcription"] for w in witnesses} == {"do", "mr"}
    subjects = {}
    for witness in witnesses:
        assert witness["review"] == {"status": "pending"}
        assert witness["source_dependencies"] == {
            "uses": [],
            "raw_binding": "purification-gospel" if witness["transcription"] == "do" else None,
        }
        subjects[witness["id"]] = witness_subject(ROOT, witness, graph, core)
    collations = [c for c in graph["collations"] if c["text"] == TEXT]
    assert len(collations) == 1 and collations[0]["review"] == {"status": "pending"}
    ap = json.loads((ROOT / f"witnesses/{TEXT}/apparatus.json").read_text())
    assert collations[0]["apparatus_sha256"] == digest(ap)
    assert (
        collation_subject(ROOT, collations[0], core, subjects)["contract"] == "collation-review-2"
    )
    assert "not the original transcription workflow" in core["editorial"]["source"]["method"]
    assert "before the Credo" in core["editorial"]["notes"]
    mr_text = (ROOT / f"witnesses/{TEXT}/mr.txt").read_text()
    assert "# historical-transcribed: 2026-08-31" in mr_text and "# transcribed:" not in mr_text


@pytest.mark.parametrize(
    "mode",
    ["will", "light", "articleless", "pl-larger-subject", "pl-older-temporal", "past-bringing"],
)
def test_valid_contextual_alternatives_are_not_blanket_guard_failures(mode):
    language = "pl" if mode.startswith("pl-") else "en"
    doc, layers = store.load(ROOT, TEXT)
    layer = copy.deepcopy(layers[language])
    groups = layer["segments"]["s01"].setdefault("alignments", [])
    # Isolate the alternative with coherent providers on both old and new data.
    chosen = [g for g in GROUPS if g[0] == language]
    if language == "en":
        groups[:] = []
    else:
        groups[:] = [g for g in groups if not set(g["words"]) & {"w082", "w083", "w084"}]
    for _, numbers, anchor, gloss in chosen:
        ids = [wid(n) for n in numbers]
        for key in ids:
            layer["words"][key].pop("gloss", None)
        groups.append({"words": ids, "anchor": wid(anchor), "gloss": gloss})
    for lang, number, gloss in DIRECT:
        if lang == language:
            layer["words"][wid(number)]["gloss"] = gloss
    if mode == "will":
        next(g for g in groups if "w032" in g["words"])["gloss"] = "will be called holy to the Lord"
    elif mode == "light":
        layer["words"]["w145"]["gloss"] = "a light"
    elif mode == "articleless":
        layer["words"]["w089"]["gloss"] = "Christ"
    elif mode == "pl-larger-subject":
        group = next(g for g in groups if "w082" in g["words"])
        group["words"].append("w084")
        group["gloss"] = "że on nie ujrzy"
        layer["words"]["w084"].pop("gloss")
    elif mode == "pl-older-temporal":
        assert [layer["words"][key]["gloss"] for key in ("w086", "w087")] == [
            "jeśli nie",
            "wcześniej",
        ]
    else:
        next(g for g in groups if "w099" in g["words"])["gloss"] = (
            "His parents brought in the Child Jesus"
        )
    assert interlinear.check(doc, layer) == []
    assert (polish.check(doc, layer) if language == "pl" else english.check(doc, layer)) == []

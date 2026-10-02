"""Purification Communion: reported promise and exact source-unit contracts."""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from build_reader import store
from build_reader.bibliography_bindings import (
    collation_subject,
    digest,
    witness_subject,
)
from checks import english, interlinear, polish, raw_binding
from checks.collate import collate
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.purificatio-beatae-mariae-virginis-communio"
GROUPS = [
    ("pl", [7, 8], 8, "że nie ujrzy"),
    ("en", [1, 2, 3], 2, "Simeon received an answer"),
    ("en", [5, 6], 5, "the Holy Spirit"),
    ("en", [7, 8, 9], 8, "that he would not see"),
]
BODY = (
    "Respónsum accépit Símeon a Spíritu Sancto, non visúrum se mortem, "
    "nisi vidéret Christum Dómini."
)


def wid(n):
    return f"w{n:03}"


def line(layer):
    return [g for n in range(1, 15) if (g := interlinear.effective_gloss(layer, wid(n)))]


@pytest.mark.parametrize("language,numbers,anchor,gloss", GROUPS)
def test_selected_construction(language, numbers, anchor, gloss):
    # A selected-edition regression, not the sole grammatical realization.
    raw = store.raw_layer(ROOT, language, TEXT)
    ids = [wid(n) for n in numbers]
    matches = [
        g for g in raw["segments"]["s01"].get("alignments", []) if set(g["words"]) & set(ids)
    ]
    assert matches == [{"words": ids, "anchor": wid(anchor), "gloss": gloss}]
    assert all("gloss" not in raw["words"][key] for key in ids)


@pytest.mark.parametrize(
    "language,number,gloss",
    [("pl", 10, "śmierci"), ("pl", 12, "ujrzy"), ("en", 13, "the Christ")],
)
def test_selected_direct_reading(language, number, gloss):
    assert store.raw_layer(ROOT, language, TEXT)["words"][wid(number)]["gloss"] == gloss


@pytest.mark.parametrize("language", ["pl", "en"])
def test_complete_target_line_and_provider_partition(language):
    doc, layers = store.load(ROOT, TEXT)
    raw = store.raw_layer(ROOT, language, TEXT)
    assert len(doc["segments"]) == 1 and len(doc["segments"][0]["words"]) == 14
    assert interlinear.check(doc, layers[language]) == []
    assert line(raw) == (
        [
            "Zapowiedź",
            "otrzymał",
            "Symeon",
            "od",
            "Ducha",
            "Świętego",
            "że nie ujrzy",
            "on",
            "śmierci",
            "zanim",
            "ujrzy",
            "Chrystusa",
            "Pańskiego",
        ]
        if language == "pl"
        else [
            "Simeon received an answer",
            "from",
            "the Holy Spirit",
            "that he would not see",
            "death",
            "unless",
            "he saw",
            "the Christ",
            "of the Lord",
        ]
    )
    groups = raw["segments"]["s01"]["alignments"]
    assert (
        sum("gloss" in w for w in raw["words"].values()),
        len(groups),
        sum(len(g["words"]) for g in groups),
    ) == ((12, 1, 2) if language == "pl" else (6, 3, 8))
    assert not any("reason" in g for g in groups)


def test_preserved_latin_relative_time_and_pending_fields():
    core = store.core(ROOT, TEXT)
    words = core["segments"][0]["words"]
    assert " ".join(w.get("pre", "") + w["form"] + w.get("post", "") for w in words) == BODY
    assert words[7]["morph"] == {
        "pos": "verb",
        "case": "acc",
        "gender": "m",
        "number": "sg",
        "tense": "fut",
        "voice": "act",
        "mood": "part",
        "conj": 2,
    }
    assert words[7]["head"] == "w009" and words[8]["morph"] == {
        "pos": "pron",
        "case": "acc",
        "number": "sg",
    }
    assert words[11]["morph"] == {
        "conj": 2,
        "mood": "subj",
        "number": "sg",
        "person": 3,
        "pos": "verb",
        "tense": "impf",
        "voice": "act",
    }
    assert core["editorial"]["words"]["w006"]["analysis"]["review"] == "pending"
    assert core["editorial"]["words"]["w008"]["analysis"]["review"] == "pending"


@pytest.mark.parametrize(
    "language,target",
    [
        ("pl", "98c3097e69225a5c19bb1b285dc6f634c5c45f70e8467975a52d3b5d4bfc334a"),
        ("en", "f0d7c2384f3815a6155156a3400f22b6614d90c6885e45642156b4a0392c4dd2"),
    ],
)
def test_unchanged_working_prose_and_dependencies(language, target):
    core = store.core(ROOT, TEXT)
    raw = store.raw_layer(ROOT, language, TEXT)
    records = json.loads((ROOT / f"languages/{language}/translation-provenance.json").read_text())[
        "sites"
    ]
    sites = [s for s in records if s["site"] == TEXT + ".s01." + language]
    assert len(sites) == 1
    site = sites[0]
    assert site["source_sha256"] == canonical_hash(source_payload(core["segments"][0]))
    assert site["target_sha256"] == canonical_hash(raw["segments"]["s01"]["translation"]) == target
    assert (site["origin"], site["review"], site["familiar_core"]) == (
        "working-unsettled",
        "working",
        False,
    )


@pytest.mark.parametrize(
    "language,prefix",
    [("pl", "Antyfona na Komunię formularza"), ("en", "The Communion antiphon of")],
)
def test_localized_role_and_complete_title(language, prefix):
    assert store.raw_layer(ROOT, language, TEXT)["about"].startswith(prefix)
    assert store.core(ROOT, TEXT)["title"] == "Respónsum accépit Símeon a Spíritu Sancto"


def test_direct_digital_source_plan():
    registry = json.loads((ROOT / "witnesses/raw/bindings.json").read_text())
    assert registry["bindings"]["purification-communion"] == {
        "witness": f"witnesses/{TEXT}/do.txt",
        "revision": "44667ff518b8ff1439780470828b39714f5306a2",
        "evidence": [
            {
                "archive": "purification-day",
                "first": 204,
                "last": 204,
                "section": "Communio",
                "section_line": 202,
            }
        ],
        "references": [],
        "reading": [{"archive": "purification-day", "first": 204, "last": 204}],
    }
    archive = registry["archives"]["purification-day"]
    raw = (ROOT / archive["path"]).read_bytes()
    assert (
        hashlib.sha256(raw).hexdigest()
        == archive["sha256"]
        == "f149348ebd31599a32e17cccfc950d0f4eef24886d86bad6fd00bc3ef772520f"
    )
    assert archive["upstream"] == "web/www/missa/Latin/Sancti/02-02.txt"
    lines = raw.decode().splitlines()
    assert len(lines) == 208
    assert (lines[201], lines[202], lines[203], lines[205]) == (
        "[Communio]",
        "!Luc 2:26",
        BODY,
        "[Postcommunio]",
    )
    reading = raw_binding.resolve_binding(ROOT / f"witnesses/{TEXT}/do.txt", ROOT)
    assert reading is not None and reading.text == BODY


def test_exact_printed_unit_not_same_incipit_procession():
    graph = json.loads((ROOT / "bibliography/graph.json").read_text())
    uses = [u for u in graph["uses"] if u.get("address", {}).get("text") == TEXT]
    assert len(uses) == 2
    mr = next(u for u in uses if u["id"].endswith(".mr1962"))
    assert mr["role"] == "direct_approved_print"
    assert mr["locator"] == {
        "printed": "p. 467",
        "scan": "leaf n548 / PDF p. 549",
        "page_url": "https://archive.org/details/missale-romanum-1962/page/n548/mode/1up",
    }
    assert (
        mr["evidence_sha256"] == "1d03b85122869acb77a773f78debebbc7c8f87bef4e0acc7088a77d6f8ecf9b6"
    )
    assert "Benziger" in mr["claim"] and "different unit" in mr["claim"]
    do = next(u for u in uses if u["id"].endswith(".do44667ff"))
    assert "body 204" in do["locator"]["section"] and "heading 202" in do["locator"]["section"]


def test_nonvacuous_witness_dependencies_and_pending_collation():
    graph = json.loads((ROOT / "bibliography/graph.json").read_text())
    core = store.core(ROOT, TEXT)
    witnesses = [w for w in graph["witnesses"] if w["text"] == TEXT]
    assert len(witnesses) == 2 and {w["transcription"] for w in witnesses} == {
        "do",
        "mr",
    }
    subjects = {}
    for witness in witnesses:
        kind = witness["transcription"]
        assert witness["review"] == {"status": "pending"}
        assert witness["source_dependencies"] == {
            "uses": [],
            "raw_binding": "purification-communion" if kind == "do" else None,
        }
        subjects[witness["id"]] = witness_subject(ROOT, witness, graph, core)
        assert subjects[witness["id"]]["contract"] == "witness-review-2"
    collations = [c for c in graph["collations"] if c["text"] == TEXT]
    assert len(collations) == 1
    collation = collations[0]
    assert collation["review"] == {"status": "pending"}
    apparatus = json.loads((ROOT / f"witnesses/{TEXT}/apparatus.json").read_text())
    assert apparatus["adjudicated"] == [] and apparatus["summary"] == {
        "entries": 0,
        "classes": [],
    }
    assert collation["apparatus_sha256"] == digest(apparatus)
    assert collation_subject(ROOT, collation, core, subjects)["contract"] == "collation-review-2"
    assert collate(store.load(ROOT, TEXT)[0], ROOT / "witnesses" / TEXT)[0] == []


def test_current_conformity_not_invented_genesis_or_expansion():
    core = store.core(ROOT, TEXT)
    assert "Benziger" in core["editorial"]["source"]["method"]
    assert "not the original transcription workflow" in core["editorial"]["source"]["method"]
    assert "different liturgical unit" in core["editorial"]["notes"]
    mr = (ROOT / f"witnesses/{TEXT}/mr.txt").read_text()
    assert "# historical-transcribed: 2026-08-31" in mr
    assert "# location: printed p. 467; leaf n548 / PDF p. 549" in mr
    assert "# description: Missale Romanum, Benziger Brothers" in mr
    assert "# transcribed:" not in mr


@pytest.mark.parametrize(
    "mode",
    [
        "polish-temporal-nie",
        "polish-three-member-subject",
        "english-articleless-title",
        "english-fronted-object",
        "english-temporal-before",
    ],
)
def test_legitimate_contextual_alternatives_are_not_general_guard_errors(mode):
    language = "pl" if mode.startswith("polish") else "en"
    doc, layers = store.load(ROOT, TEXT)
    layer = copy.deepcopy(layers[language])
    # Build a coherent synthetic base on either edition. These are positive
    # grammar/provider controls, not claims that the current edition is fixed.
    layer["segments"]["s01"]["alignments"] = []
    for lang, numbers, anchor, gloss in GROUPS:
        if lang != language:
            continue
        ids = [wid(n) for n in numbers]
        for key in ids:
            layer["words"][key].pop("gloss", None)
        layer["segments"]["s01"]["alignments"].append(
            {"words": ids, "anchor": wid(anchor), "gloss": gloss}
        )
    if language == "pl":
        layer["words"]["w010"]["gloss"] = "śmierci"
        layer["words"]["w012"]["gloss"] = "ujrzy"
    if mode == "polish-temporal-nie":
        layer["words"]["w012"]["gloss"] = "nie ujrzy"
    elif mode == "polish-three-member-subject":
        group = next(g for g in layer["segments"]["s01"]["alignments"] if "w007" in g["words"])
        group["words"].append("w009")
        group["gloss"] = "że on nie ujrzy"
        layer["words"]["w009"].pop("gloss")
    elif mode == "english-articleless-title":
        layer["words"]["w013"]["gloss"] = "Christ"
    elif mode == "english-fronted-object":
        group = next(g for g in layer["segments"]["s01"]["alignments"] if "w001" in g["words"])
        group["words"].remove("w001")
        group["gloss"] = "Simeon received"
        layer["words"]["w001"]["gloss"] = "An answer"
    else:
        layer["words"]["w011"]["gloss"] = "before"
    assert interlinear.check(doc, layer) == []
    assert (polish.check(doc, layer) if language == "pl" else english.check(doc, layer)) == []

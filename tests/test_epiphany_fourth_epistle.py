"""Bounded Fourth Sunday after Epiphany Epistle readings and source contracts."""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from build_reader import store
from build_reader.bibliography_bindings import digest, selected_text
from checks import english, interlinear, raw_binding
from checks.collate import collate, load_witness
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.dominica-iv-post-epiphaniam-epistola"
# Retained historical expectation; the contemporary prose has a separate digest.
PREVIOUS_EN_TARGET = "ebd28ff6d18e61c70838390e243558b7ccbbf513ed0179993616c2527df1432a"
GROUPS = [
    ([2, 3, 4], 4, "owe no one anything"),
    ([7, 8], 8, "love one another"),
    ([13, 14], 14, "has fulfilled the Law"),
    ([16, 17], 17, "You shall not commit adultery"),
    ([18, 19], 19, "you shall not kill"),
    ([20, 21], 21, "you shall not steal"),
    ([22, 23, 24, 25], 25, "you shall not bear false witness"),
    ([26, 27], 27, "you shall not covet"),
    ([30, 31], 31, "there is any"),
    ([39, 40], 39, "your neighbor"),
    ([45, 46, 47], 47, "does no evil"),
]


def wid(n):
    return f"w{n:03d}"


def line(layer, first=1, last=52):
    return [
        value
        for n in range(first, last + 1)
        if (value := interlinear.effective_gloss(layer, wid(n)))
    ]


@pytest.mark.parametrize("numbers,anchor,gloss", GROUPS)
def test_selected_english_construction(numbers, anchor, gloss):
    # Exact editorial regression, not a claim that every other wording is invalid.
    layer = store.raw_layer(ROOT, "en", TEXT)
    ids = [wid(n) for n in numbers]
    matches = [a for a in layer["segments"]["s01"]["alignments"] if set(ids) & set(a["words"])]
    assert matches == [{"words": ids, "anchor": wid(anchor), "gloss": gloss}]
    assert all("gloss" not in layer["words"][key] for key in ids)


@pytest.mark.parametrize(
    "language,number,gloss",
    [
        ("pl", 5, "oprócz tego"),
        ("pl", 6, "abyście"),
        ("pl", 8, "się miłowali"),
        ("en", 11, "loves"),
        ("en", 37, "it is summed up"),
        ("en", 44, "of one’s neighbor"),
    ],
)
def test_contextual_direct_realization(language, number, gloss):
    assert store.raw_layer(ROOT, language, TEXT)["words"][wid(number)]["gloss"] == gloss


def test_polish_exception_and_retained_solemn_inversions():
    layer = store.raw_layer(ROOT, "pl", TEXT)
    assert line(layer, 1, 8) == [
        "Bracia",
        "nikomu",
        "nic",
        "nie bądźcie dłużni",
        "oprócz tego",
        "abyście",
        "wzajemnie",
        "się miłowali",
    ]
    assert line(layer, 22, 25) == ["Nie mów fałszywego świadectwa"]
    assert line(layer, 43, 52) == [
        "Miłość",
        "bliźniego",
        "zła",
        "nie",
        "wyrządza",
        "Pełnią",
        "więc",
        "Prawa",
        "jest",
        "miłość",
    ]


def test_whole_english_dependencies_and_single_contributions():
    layer = store.raw_layer(ROOT, "en", TEXT)
    assert line(layer) == [
        "Brethren",
        "owe no one anything",
        "except",
        "to",
        "love one another",
        "for he who",
        "loves",
        "his neighbor",
        "has fulfilled the Law",
        "For",
        "You shall not commit adultery",
        "you shall not kill",
        "you shall not steal",
        "you shall not bear false witness",
        "you shall not covet",
        "and",
        "if",
        "there is any",
        "other",
        "commandment",
        "in",
        "this",
        "word",
        "it is summed up",
        "You shall love",
        "your neighbor",
        "as",
        "yourself",
        "Love",
        "of one’s neighbor",
        "does no evil",
        "The fulfilling",
        "therefore",
        "of the Law",
        "is",
        "love",
    ]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_complete_realization_partition(language):
    doc, layers = store.load(ROOT, TEXT)
    layer = layers[language]
    assert len(doc["segments"]) == 1 and len(doc["segments"][0]["words"]) == 52
    assert interlinear.check(doc, layer) == []
    groups = layer["segments"]["s01"].get("alignments", [])
    direct = sum("gloss" in w for w in layer["words"].values())
    assert (direct, len(groups), sum(len(a["words"]) for a in groups)) == (
        (48, 1, 4) if language == "pl" else (24, 12, 28)
    )
    assert not any("reason" in a for a in groups)
    assert len(line(layer)) == (49 if language == "pl" else 36)


def test_retained_old_group_and_separate_infinitival_marker():
    layer = store.raw_layer(ROOT, "en", TEXT)
    assert {"words": ["w009", "w010"], "anchor": "w009", "gloss": "for he who"} in layer[
        "segments"
    ]["s01"]["alignments"]
    assert layer["words"]["w006"]["gloss"] == "to"
    assert layer["words"]["w048"]["gloss"] == "The fulfilling"


@pytest.mark.parametrize(
    "language,label", [("pl", "Czytanie formularza"), ("en", "The Epistle of")]
)
def test_localized_about(language, label):
    assert store.raw_layer(ROOT, language, TEXT)["about"].startswith(label)


def test_contextual_neuter_does_not_invent_a_new_case_or_approval():
    core = store.core(ROOT, TEXT)
    word = core["segments"][0]["words"][2]
    assert word == {
        "id": "w003",
        "form": "quidquam",
        "lemma": "quisquam",
        "morph": {"case": "acc", "gender": "n", "number": "sg", "pos": "pron"},
    }
    assert core["editorial"]["words"]["w003"]["analysis"] == {
        "confidence": "high",
        "sources": ["editorial", "whitakers", "collatinus"],
        "review": "pending",
    }
    registry = json.loads((ROOT / "build_reader/registry/morphology.json").read_text())
    assert registry[189] == word["morph"]


def test_retained_legal_futures_and_deponent_meaning():
    words = store.core(ROOT, TEXT)["segments"][0]["words"]
    for n in [17, 19, 21, 25, 27, 38]:
        morph = words[n - 1]["morph"]
        assert (morph["mood"], morph["tense"], morph["person"], morph["number"]) == (
            "ind",
            "fut",
            2,
            "sg",
        )
    assert words[20]["morph"]["voice"] == "dep"
    assert words[46]["morph"]["voice"] == "dep"
    assert words[29]["lemma"] == "qui" and words[29]["morph"]["case"] == "nom"


@pytest.mark.parametrize(
    "language,target",
    [
        ("pl", "08d141a51ddf69484ad6a7db452257d7ec98b8dd90e941507d0aecab0b20f189"),
        ("en", "dc063648e6724fc0263d0fad4c5acfd672d91f1a3bd4dc19d19813dcb0c5e2db"),
    ],
)
def test_current_working_prose_source_dependency(language, target):
    core = store.core(ROOT, TEXT)
    layer = store.raw_layer(ROOT, language, TEXT)
    sites = json.loads((ROOT / f"languages/{language}/translation-provenance.json").read_text())[
        "sites"
    ]
    matched = [s for s in sites if s["site"] == TEXT + ".s01." + language]
    assert len(matched) == 1
    site = matched[0]
    assert (
        site["target_sha256"] == canonical_hash(layer["segments"]["s01"]["translation"]) == target
    )
    assert site["source_sha256"] == canonical_hash(source_payload(core["segments"][0]))
    assert site["origin"] == "working-unsettled" and site["review"] == "working"
    if language == "en":
        assert target != PREVIOUS_EN_TARGET


def test_literal_printed_colon_and_four_digital_accidentals():
    folder = ROOT / "witnesses" / TEXT
    bound = raw_binding.resolve_binding(folder / "do.txt", ROOT)
    _, digital = load_witness(folder / "do.txt")
    _, printed = load_witness(folder / "mr.txt")
    assert bound is not None and bound.text == digital
    assert len(digital.split()) == len(printed.split()) == 52
    words = store.core(ROOT, TEXT)["segments"][0]["words"]
    assert (
        words[18]["post"] == ":"
        and printed.split()[18] == "occídes:"
        and digital.split()[18] == "occídes,"
    )
    ap = json.loads((folder / "apparatus.json").read_text())
    assert {r["at"]: r["witnesses"]["do"] for r in ap["adjudicated"]} == {
        "w017": "adulterábis,",
        "w019": "occídes,",
        "w021": "furáberis,",
        "w025": "dices,",
    }
    assert ap["summary"] == {"entries": 4, "classes": ["punctuation"]}
    errors, _, stats = collate(store.load(ROOT, TEXT)[0], folder)
    assert errors == [] and stats["words"] == 52 and stats["witnesses"] == 2


def test_exact_raw_plan_has_only_the_direct_body():
    registry = json.loads((ROOT / "witnesses/raw/bindings.json").read_text())
    assert registry["bindings"]["epiphany-iv-epistle"] == {
        "witness": f"witnesses/{TEXT}/do.txt",
        "revision": "44667ff518b8ff1439780470828b39714f5306a2",
        "evidence": [
            {
                "archive": "epiphany-iv",
                "first": 22,
                "last": 22,
                "section": "Lectio",
                "section_line": 19,
            }
        ],
        "references": [],
        "reading": [{"archive": "epiphany-iv", "first": 22, "last": 22}],
    }
    ar = registry["archives"]["epiphany-iv"]
    raw = (ROOT / ar["path"]).read_bytes()
    assert (
        ar["sha256"]
        == hashlib.sha256(raw).hexdigest()
        == "fbc74053a33bcaafe98995fa4f4ea3a0a28e08116549057f8071757703f41ebe"
    )
    lines = raw.decode().splitlines()
    assert lines[18] == "[Lectio]" and lines[20] == "!Rom 13:8-10"
    assert len(lines[21].split()) == 52


def test_print_identity_boundary_and_current_not_historical_claim():
    core = store.core(ROOT, TEXT)
    meta, body = load_witness(ROOT / "witnesses" / TEXT / "mr.txt")
    assert (
        meta["description"] == "Missale Romanum, Benziger Brothers, New York, Editio iuxta typicam"
    )
    assert "historical-transcribed" in meta and "transcribed" not in meta
    assert "historical-recollated" in meta and "recollated" not in meta
    assert "current page conformity" in meta["verification-scope"]
    assert "Fourth Sunday" in meta["boundary"] and "p. 46" in meta["boundary"]
    assert len(body.split()) == 52 and "Amen" not in body
    assert "not original transcription genesis" in core["editorial"]["source"]["method"]
    assert "Benziger Brothers" in core["editorial"]["source"]["method"]
    assert "No conclusion, shared expansion or Amen" in core["editorial"]["notes"]
    assert "running header for the Fifth Sunday" in core["editorial"]["notes"]


def test_nonempty_graph_dependencies_and_pending_states():
    graph = json.loads((ROOT / "bibliography/graph.json").read_text())
    uses = [u for u in graph["uses"] if u.get("address", {}).get("text") == TEXT]
    witnesses = [w for w in graph["witnesses"] if w.get("text") == TEXT]
    collations = [c for c in graph["collations"] if c.get("text") == TEXT]
    assert (len(uses), len(witnesses), len(collations)) == (2, 2, 1)
    mr = next(u for u in uses if u["id"].endswith(".mr1962"))
    do = next(u for u in uses if u["id"].endswith(".do44667ff"))
    assert mr["role"] == "direct_approved_print" and "Benziger" in mr["claim"]
    assert (
        mr["evidence_sha256"] == "fddfc5942a9c7772130b1e5d335f34c01392d17b03ed9b2ea25aebb8f4451a60"
    )
    assert (
        do["evidence_sha256"] == "fbc74053a33bcaafe98995fa4f4ea3a0a28e08116549057f8071757703f41ebe"
    )
    assert "complete direct body 22" in do["locator"]["section"]
    for witness in witnesses:
        kind = witness["transcription"]
        assert witness["review"] == {"status": "pending"}
        assert witness["source_dependencies"] == {
            "uses": [],
            "raw_binding": "epiphany-iv-epistle" if kind == "do" else None,
        }
        raw = (ROOT / "witnesses" / TEXT / (kind + ".txt")).read_bytes()
        assert witness["transcription_sha256"] == hashlib.sha256(raw).hexdigest()
    ap = json.loads((ROOT / "witnesses" / TEXT / "apparatus.json").read_text())
    assert collations[0]["review"] == {"status": "pending"}
    assert collations[0]["apparatus_sha256"] == digest(ap)
    assert collations[0]["selected_text_sha256"] == digest(selected_text(store.core(ROOT, TEXT)))


def test_valid_smaller_fronted_dative_is_not_a_grammar_failure():
    doc, layers = store.load(ROOT, TEXT)
    layer = copy.deepcopy(layers["en"])
    group = next(a for a in layer["segments"]["s01"]["alignments"] if "w004" in a["words"])
    group.update(words=["w003", "w004"], gloss="owe anything")
    layer["words"]["w002"]["gloss"] = "to no man"
    assert interlinear.check(doc, layer) == [] and english.check(doc, layer) == []
    assert line(layer, 1, 8) == [
        "Brethren",
        "to no man",
        "owe anything",
        "except",
        "to",
        "love one another",
    ]


@pytest.mark.parametrize(
    "number,gloss",
    [
        (17, "Do not commit adultery"),
        (19, "do not kill"),
        (21, "do not steal"),
        (25, "do not bear false witness"),
        (27, "do not covet"),
    ],
)
def test_legal_future_can_be_rendered_as_a_prohibition(number, gloss):
    doc, layers = store.load(ROOT, TEXT)
    layer = copy.deepcopy(layers["en"])
    group = next(a for a in layer["segments"]["s01"]["alignments"] if wid(number) in a["words"])
    group["gloss"] = gloss
    assert interlinear.check(doc, layer) == [] and english.check(doc, layer) == []
    assert doc["segments"][0]["words"][number - 1]["morph"]["tense"] == "fut"
    assert interlinear.effective_gloss(layer, wid(number)) == gloss

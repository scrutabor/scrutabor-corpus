"""Proper bodies and expanded formulas keep their distinct source boundaries."""

import json
from pathlib import Path

import pytest

from build_reader import bibliography
from checks import raw_binding, transcription
from checks.collate import collate

ROOT = Path(__file__).resolve().parents[1]
CHRISTMAS = "nativitas-domini-in-die-introitus"
BAPTIST = "nativitas-sancti-ioannis-baptistae-evangelium"
BLOOD = "pretiosissimi-sanguinis-domini-nostri-iesu-christi"
PURIFICATION = "purificatio-beatae-mariae-virginis-collecta"
HEART = "sacratissimi-cordis-iesu-evangelium"
RAW = "web/www/missa/Latin/"


def core(name):
    return json.loads((ROOT / "texts/proprium" / f"{name}.json").read_bytes())


@pytest.mark.parametrize(
    "name,count,spans",
    [
        (
            CHRISTMAS,
            69,
            [
                (RAW + "Tempora/Nat30.txt", 18, 18),
                (RAW + "Tempora/Nat30.txt", 20, 20),
                (RAW + "Ordo/Prayers.txt", 13, 14),
                (RAW + "Tempora/Nat30.txt", 22, 22),
            ],
        ),
        (BAPTIST, 156, [(RAW + "Sancti/06-24.txt", 51, 51)]),
        (BLOOD + "-communio", 16, [(RAW + "Sancti/07-01.txt", 61, 61)]),
        (BLOOD + "-evangelium", 93, [(RAW + "Sancti/07-01.txt", 49, 49)]),
        (
            PURIFICATION,
            52,
            [
                (RAW + "Sancti/02-02.txt", 165, 165),
                (RAW + "Ordo/Prayers.txt", 112, 113),
            ],
        ),
        (HEART, 111, [(RAW + "Tempora/Pent02-5.txt", 54, 54)]),
    ],
)
def test_exact_ordered_digital_body_and_variants(name, count, spans):
    directory = ROOT / "witnesses" / ("proprium." + name)
    binding = raw_binding.resolve_binding(directory / "do.txt", ROOT)
    assert binding is not None
    registry = raw_binding.load_registry(ROOT)
    upstream = {a["path"]: a["upstream"] for a in registry["archives"].values()}
    assert [
        (upstream[p.relative_to(ROOT).as_posix()], first, last) for p, first, last in binding.spans
    ] == spans
    lexical = [word for word in binding.text.split() if any(c.isalpha() for c in word)]
    assert len(lexical) == count
    assert "Sequéntia" not in binding.text and "Léctio" not in binding.text
    assert transcription.check_transcriptions(directory) == ([], 1)
    assert collate(core(name), directory)[:2] == ([], [])


def test_christmas_expansion_preserves_each_component_once():
    words = core(CHRISTMAS)["segments"][0]["words"]
    assert len(words) == 69
    assert [w["id"] for w in words] == [f"w{n:03}" for n in range(1, 70)]
    assert [w["form"] for w in words[21:28]] == [
        "Cantáte",
        "Dómino",
        "cánticum",
        "novum",
        "quia",
        "mirabília",
        "fecit",
    ]
    assert [w["form"] for w in words[:21]] == [w["form"] for w in words[48:]]
    assert [len(words[:21]), len(words[21:28]), len(words[28:48]), len(words[48:])] == [
        21,
        7,
        20,
        21,
    ]
    assert (words[28]["form"], words[47]["form"]) == ("Glória", "Amen")


@pytest.mark.parametrize("location", ["core", "printed-use", "collation"])
def test_christmas_source_claim_matches_the_seven_word_psalm(location):
    document = core(CHRISTMAS)
    graph = json.loads((ROOT / "bibliography/graph.json").read_bytes())
    if location == "core":
        claim = document["editorial"]["source"]["method"]
    elif location == "printed-use":
        claim = next(
            u["claim"] for u in graph["uses"] if u["id"] == f"use.proprium.{CHRISTMAS}.mr1962"
        )
    else:
        claim = next(
            c["recension"] for c in graph["collations"] if c["text"] == "proprium." + CHRISTMAS
        )
    assert "21-word antiphon, seven-word psalm" in claim
    assert "eight-word" not in claim
    assert len(document["segments"][0]["words"][21:28]) == 7


def test_collect_body_conclusion_and_response_stay_distinct():
    document = core(PURIFICATION)
    words = [w for s in document["segments"] for w in s["words"]]
    assert len(words) == 52
    assert words[28]["form"] == "præsentári"
    assert [w["form"] for w in words[29:32]] == ["Per", "eúndem", "Dóminum"]
    assert [w["form"] for w in document["segments"][1]["words"]] == ["Amen"]
    graph = json.loads((ROOT / "bibliography/graph.json").read_bytes())
    witness = next(
        w
        for w in graph["witnesses"]
        if w["text"] == "proprium." + PURIFICATION and w["transcription"] == "mr"
    )
    dependencies = witness["source_dependencies"]["uses"]
    assert f"use.proprium.{PURIFICATION}.expanded-conclusion.mr1962" in dependencies
    assert f"use.proprium.{PURIFICATION}.same-lord-conclusion.mr1962" in dependencies
    assert f"use.proprium.{PURIFICATION}.oration-boundaries.mr1962" in dependencies
    assert witness["orthography_profile"] == "page-body-with-declared-house-expansion"


@pytest.mark.parametrize(
    "name",
    [
        CHRISTMAS,
        BAPTIST,
        BLOOD + "-communio",
        BLOOD + "-evangelium",
        PURIFICATION,
        HEART,
    ],
)
def test_source_identity_repair_does_not_promote_pending_review(name):
    tid = "proprium." + name
    graph = json.loads((ROOT / "bibliography/graph.json").read_bytes())
    witnesses = [w for w in graph["witnesses"] if w.get("text") == tid]
    assert len(witnesses) == 2
    assert all(w["review"] == {"status": "pending"} for w in witnesses)
    assert "Benziger" in core(name)["editorial"]["source"]["method"]
    row = next(t for t in bibliography.public_text_evidence(graph)["texts"] if t["id"] == tid)
    assert row["witnesses"] == [] and "collation" not in row


@pytest.mark.parametrize("suffix", ["expanded-doxology", "introit-expansion"])
def test_christmas_declares_its_printed_expansion_source(suffix):
    text = "proprium.nativitas-domini-in-die-introitus"
    graph = json.loads((ROOT / "bibliography/graph.json").read_bytes())
    witness = next(
        w for w in graph["witnesses"] if w["text"] == text and w["transcription"] == "mr"
    )
    assert f"use.{text}.{suffix}.mr1962" in witness["source_dependencies"]["uses"]

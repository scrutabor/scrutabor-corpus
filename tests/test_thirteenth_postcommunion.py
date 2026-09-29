"""The received mysteries and requested growth remain fully expressed."""

import json
from pathlib import Path

import pytest

from build_reader.bibliography_bindings import digest, selected_text
from checks.interlinear import check
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
NAME = "dominica-xiii-post-pentecosten-postcommunio"
TEXT = f"proprium.{NAME}"
GROUPS = [
    ("pl", 5, 10, 9, "prosimy, abyśmy coraz pełniej dostępowali wiecznego odkupienia"),
    ("en", 5, 10, 9, "we pray that we may advance toward a fuller share in eternal redemption"),
    ("en", 12, 13, 12, "our Lord"),
    ("en", 16, 17, 16, "Your Son"),
    ("en", 25, 26, 25, "of the Holy Spirit"),
]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def layer(language):
    return load(f"languages/{language}/texts/proprium/{NAME}.json")


@pytest.mark.parametrize("language,start,end,anchor,gloss", GROUPS)
def test_complete_construction(language, start, end, anchor, gloss):
    data = layer(language)
    ids = [f"w{number:03}" for number in range(start, end + 1)]
    assert {"words": ids, "anchor": f"w{anchor:03}", "gloss": gloss} in data["segments"]["s01"].get(
        "alignments", []
    )
    assert all(data["words"][word] == {} for word in ids)


@pytest.mark.parametrize("language,grouped", [("pl", 6), ("en", 12)])
def test_each_word_has_one_realization_and_amen_is_separate(language, grouped):
    core = load(f"texts/proprium/{NAME}.json")
    data = layer(language)
    ids = [word["id"] for segment in core["segments"] for word in segment["words"]]
    assert ids == [f"w{number:03}" for number in range(1, 33)]
    assert set(data["words"]) == set(ids)
    groups = data["segments"]["s01"].get("alignments", [])
    assert sum(len(group["words"]) for group in groups) == grouped
    assert all("reason" not in group for group in groups)
    assert check(core, data) == []
    assert data["segments"]["s02"] == {"translation": "Amen."}


@pytest.mark.parametrize("language", ["pl", "en"])
def test_provenance_binds_current_text_without_promoting_review(language):
    core = load(f"texts/proprium/{NAME}.json")
    sites = load(f"languages/{language}/translation-provenance.json")["sites"]
    site = next(s for s in sites if s["site"] == f"{TEXT}.s01.{language}")
    assert site["source_sha256"] == canonical_hash(source_payload(core["segments"][0]))
    assert site["target_sha256"] == canonical_hash(
        layer(language)["segments"]["s01"]["translation"]
    )
    assert (site["origin"], site["review"]) == ("working-unsettled", "working")


def test_polish_growth_preserves_the_familiar_conclusion():
    data = layer("pl")
    assert data["segments"]["s01"]["translation"] == (
        "Przyjąwszy, Panie, niebieskie sakramenty, prosimy, abyśmy coraz pełniej "
        "dostępowali wiecznego odkupienia. Przez Pana naszego Jezusa Chrystusa, "
        "Syna Twojego, który z Tobą żyje i króluje w jedności Ducha Świętego, "
        "Bóg, na wieki wieków."
    )
    assert [data["words"][f"w{number:03}"]["gloss"] for number in range(1, 5)] == [
        "Przyjąwszy",
        "Panie",
        "niebieskie",
        "sakramenty",
    ]


def test_english_preserves_plurality_progress_and_one_register():
    data = layer("en")
    assert data["segments"]["s01"]["translation"] == (
        "Lord, having received the heavenly mysteries, we pray that we may advance "
        "toward a fuller share in eternal redemption. Through our Lord Jesus Christ, "
        "Your Son, who lives and reigns with You in the unity of the Holy Spirit, "
        "God, forever and ever."
    )
    expected = {
        "w004": "sacraments",
        "w018": "who",
        "w019": "with You",
        "w020": "lives",
        "w022": "reigns",
        "w028": "for",
    }
    assert {key: data["words"][key]["gloss"] for key in expected} == expected


@pytest.mark.parametrize(
    "word,selected,raw",
    [
        ("w003", "cæléstibus", "cœléstibus"),
        ("w014", "Iesum", "Jesum"),
        ("w015", "Christum", "Christum,"),
        ("w018", "Qui", "qui"),
        ("w026", "Sancti,", "Sancti"),
    ],
)
def test_all_digital_accidentals_are_recorded(word, selected, raw):
    apparatus = load(f"witnesses/{TEXT}/apparatus.json")
    entry = next(e for e in apparatus["adjudicated"] if e["at"] == word)
    assert entry["ours"] == selected
    assert entry["witnesses"] == {"do": raw}


def test_expansion_is_distinct_from_the_printed_body_without_resealing():
    core = load(f"texts/proprium/{NAME}.json")
    assert "Benziger 1962" in core["editorial"]["source"]["method"]
    printed = (ROOT / "witnesses" / TEXT / "mr.txt").read_text(encoding="utf-8")
    assert "# description: Missale Romanum, Benziger 1962 (Editio iuxta typicam)" in printed
    assert "Rubricae generales 115 a" in printed
    assert "tuum, qui" in printed and "tuum: Qui" in printed
    graph = load("bibliography/graph.json")
    use = next(u for u in graph["uses"] if u["id"] == f"use.{TEXT}.expanded-conclusion.mr1962")
    assert use["address"] == {"kind": "segment", "text": TEXT, "segment": "s01"}
    assert use["role"] == "official_text"
    assert use["locator"]["printed"] == "p. xvii"
    assert use["locator"]["scan"] == "leaf n22 / PDF p. 23"
    assert use["locator"]["section"] == "Rubricae generales, 115 a"
    witnesses = [w for w in graph["witnesses"] if w["text"] == TEXT]
    assert len(witnesses) == 2
    assert all(w["review"] == {"status": "pending"} for w in witnesses)
    mr = next(w for w in witnesses if w["transcription"] == "mr")
    assert mr["orthography_profile"] == "exact-page-body-with-declared-expansion"
    collations = [c for c in graph["collations"] if c["text"] == TEXT]
    assert len(collations) == 1 and collations[0]["review"] == {"status": "pending"}


def test_selected_latin_ritual_and_pending_analyses_are_preserved():
    core = load(f"texts/proprium/{NAME}.json")
    assert (
        digest(selected_text(core))
        == "c3012abe0f63ff1f6dfbe3ea6af317e12b89c85b78464f05331895009ae620aa"
    )
    for word in ("w007", "w013"):
        assert core["editorial"]["words"][word]["analysis"]["review"] == "pending"

"""The received gifts, memorial command and assistance remain unambiguous."""

import json
from pathlib import Path

import pytest

from checks.interlinear import check
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
NAME = "dominica-xxii-post-pentecosten-postcommunio"
TEXT = f"proprium.{NAME}"
GROUPS = [
    ("pl", 3, 5, 4, "dary świętego misterium"),
    ("pl", 16, 20, 18, "przyniosło pomoc w naszej słabości"),
    ("en", 3, 5, 4, "the gifts of the sacred mystery"),
    ("en", 10, 15, 15, "You commanded us to do in remembrance of You"),
    ("en", 16, 20, 18, "may help us in our weakness"),
    ("en", 30, 31, 30, "of the Holy Spirit"),
    ("en", 33, 36, 35, "forever and ever"),
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


@pytest.mark.parametrize("language,grouped", [("pl", 8), ("en", 20)])
def test_every_word_keeps_one_realization_and_amen_stays_separate(language, grouped):
    core = load(f"texts/proprium/{NAME}.json")
    data = layer(language)
    ids = [word["id"] for segment in core["segments"] for word in segment["words"]]
    assert ids == [f"w{number:03}" for number in range(1, 38)]
    assert set(data["words"]) == set(ids)
    groups = data["segments"]["s01"].get("alignments", [])
    assert sum(len(group["words"]) for group in groups) == grouped
    assert all("reason" not in group for group in groups)
    assert check(core, data) == []
    assert data["segments"]["s02"] == {"translation": "Amen."}


def test_relative_does_not_require_absorption_into_the_command():
    assert layer("en")["words"]["w009"] == {"gloss": "what"}
    assert layer("pl")["words"]["w009"] == {"gloss": "to, co"}
    core = load(f"texts/proprium/{NAME}.json")
    word = next(w for w in core["segments"][0]["words"] if w["id"] == "w009")
    assert word["morph"] == {"pos": "pron", "case": "acc", "number": "pl", "gender": "n"}
    assert core["editorial"]["words"]["w009"]["analysis"]["review"] == "pending"


def test_english_has_plural_gifts_command_force_and_one_register():
    data = layer("en")
    assert data["segments"]["s01"]["translation"] == (
        "Lord, we have received the gifts of the sacred mystery, and we humbly pray "
        "that what You commanded us to do in remembrance of You may help us in our "
        "weakness. You live and reign with God the Father in the unity of the Holy "
        "Spirit, God, forever and ever."
    )
    expected = {"w007": "beseeching", "w021": "You who", "w022": "live", "w024": "reign"}
    assert {key: data["words"][key]["gloss"] for key in expected} == expected
    sites = load("languages/en/translation-provenance.json")["sites"]
    site = next(s for s in sites if s["site"] == f"{TEXT}.s01.en")
    assert site["origin"] == "working-unsettled"
    assert site["review"] == "working"
    assert site["target_sha256"] == canonical_hash(data["segments"]["s01"]["translation"])


def test_polish_continuous_prayer_and_direct_controls_are_preserved():
    data = layer("pl")
    assert data["segments"]["s01"]["translation"] == (
        "Przyjęliśmy, Panie, dary świętej tajemnicy, w pokorze błagając, aby to, co "
        "na Twoją pamiątkę nakazałeś nam czynić, posłużyło ku pomocy w naszej niemocy. "
        "Który żyjesz i królujesz z Bogiem Ojcem w jedności Ducha Świętego, Bóg, "
        "na wieki wieków."
    )
    assert [data["words"][f"w{number:03}"]["gloss"] for number in range(10, 16)] == [
        "na",
        "Twoją",
        "pamiątkę",
        "nam",
        "czynić",
        "nakazałeś",
    ]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_current_grammatical_source_is_bound_without_promoting_review(language):
    core = load(f"texts/proprium/{NAME}.json")
    sites = load(f"languages/{language}/translation-provenance.json")["sites"]
    site = next(s for s in sites if s["site"] == f"{TEXT}.s01.{language}")
    assert site["source_sha256"] == canonical_hash(source_payload(core["segments"][0]))
    assert site["target_sha256"] == canonical_hash(
        layer(language)["segments"]["s01"]["translation"]
    )
    assert site["origin"] == "working-unsettled"
    assert site["review"] == "working"


def test_digital_conclusion_punctuation_is_not_assigned_to_the_selected_latin():
    folder = ROOT / "witnesses" / TEXT
    digital = (folder / "do.txt").read_text(encoding="utf-8")
    printed = (folder / "mr.txt").read_text(encoding="utf-8")
    assert "cum Deo Patre, in unitáte" in digital
    assert "Latin/Ordo/Prayers.txt [Qui vivis]" in digital
    assert "cum Deo Patre in unitáte" in printed
    apparatus = load(f"witnesses/{TEXT}/apparatus.json")
    assert apparatus["summary"] == {"entries": 2, "classes": ["punctuation"]}
    entry = next(e for e in apparatus["adjudicated"] if e["at"] == "w027")
    assert entry["ours"] == "Patre"
    assert entry["witnesses"] == {"do": "Patre,"}
    core = load(f"texts/proprium/{NAME}.json")
    patre = next(w for w in core["segments"][0]["words"] if w["id"] == "w027")
    assert "post" not in patre


def test_expanded_conclusion_names_its_distinct_source_without_resealing():
    core = load(f"texts/proprium/{NAME}.json")
    assert (
        "Benziger 1962 Missale Romanum (Editio iuxta typicam)"
        in core["editorial"]["source"]["method"]
    )
    printed = (ROOT / "witnesses" / TEXT / "mr.txt").read_text(encoding="utf-8")
    assert "# description: Missale Romanum, Benziger 1962 (Editio iuxta typicam)" in printed
    graph = load("bibliography/graph.json")
    use = next(u for u in graph["uses"] if u["id"] == f"use.{TEXT}.expanded-conclusion.mr1962")
    assert use["address"] == {"kind": "segment", "text": TEXT, "segment": "s01"}
    assert use["role"] == "official_text"
    assert use["locator"]["printed"] == "p. xviii"
    assert use["locator"]["scan"] == "leaf n23 / PDF p. 24"
    assert use["locator"]["section"] == "Rubricae generales, 115 d"
    witnesses = [w for w in graph["witnesses"] if w["text"] == TEXT]
    assert len(witnesses) == 2
    assert all(w["review"] == {"status": "pending"} for w in witnesses)
    mr = next(w for w in witnesses if w["transcription"] == "mr")
    assert mr["orthography_profile"] == "exact-page-body-with-declared-expansion"
    collations = [c for c in graph["collations"] if c["text"] == TEXT]
    assert len(collations) == 1
    assert collations[0]["review"] == {"status": "pending"}

"""The sacred gift, owed service and increase in salvation retain their sense."""

import json
from pathlib import Path

import pytest

from build_reader.bibliography_bindings import digest, selected_text
from checks.interlinear import check
from checks.language_packs import check_layer
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
NAME = "sancti-laurentii-martyris-postcommunio"
TEXT = f"proprium.{NAME}"
GROUPS = [
    ("pl", 9, 13, 12, "w tym, co sprawujemy z obowiązku należnej służby"),
    ("pl", 19, 22, 21, "doświadczyli wzrostu zbawienia, którego udzielasz"),
    ("en", 1, 3, 3, "filled with the sacred gift"),
    ("en", 5, 7, 7, "we implore You, Lord"),
    ("en", 10, 13, 12, "we celebrate in fulfillment of the service we owe"),
    ("en", 17, 18, 17, "Your martyr"),
    ("en", 19, 22, 21, "we may experience as an increase in Your salvation"),
    ("en", 24, 25, 24, "our Lord"),
    ("en", 28, 29, 28, "Your Son"),
    ("en", 37, 38, 37, "of the Holy Spirit"),
]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def layer(language):
    return load(f"languages/{language}/texts/proprium/{NAME}.json")


@pytest.mark.parametrize("language,start,end,anchor,gloss", GROUPS)
def test_construction_has_one_complete_gloss(language, start, end, anchor, gloss):
    data = layer(language)
    ids = [f"w{number:03}" for number in range(start, end + 1)]
    assert {"words": ids, "anchor": f"w{anchor:03}", "gloss": gloss} in data["segments"]["s01"].get(
        "alignments", []
    )
    assert all("gloss" not in data["words"][word] for word in ids)


@pytest.mark.parametrize("language,grouped", [("pl", 9), ("en", 22)])
def test_complete_realization_and_distinct_response(language, grouped):
    core = load(f"texts/proprium/{NAME}.json")
    data = layer(language)
    ids = [w["id"] for s in core["segments"] for w in s["words"]]
    assert ids == [f"w{number:03}" for number in range(1, 45)]
    assert set(data["words"]) == set(ids)
    groups = data["segments"]["s01"].get("alignments", [])
    assert sum(len(g["words"]) for g in groups) == grouped
    assert all("reason" not in g for g in groups)
    assert check(core, data) == []
    assert check_layer(core, data, ROOT / f"languages/{language}/texts/proprium/{NAME}.json") == []
    assert data["segments"]["s02"] == {"translation": "Amen."}


def test_english_singular_gift_objective_increase_and_consistent_register():
    data = layer("en")
    assert data["segments"]["s01"]["translation"] == (
        "Filled with the sacred gift, we humbly ask You, Lord, that through the "
        "intercession of blessed Lawrence, Your martyr, we may find in what we "
        "celebrate as the service we owe You an increase in the salvation You "
        "give. Through our Lord Jesus Christ, Your Son, who lives and reigns "
        "with You in the unity of the Holy Spirit, God, forever and ever."
    )
    expected = {"w030": "who", "w031": "with You", "w032": "lives", "w034": "reigns"}
    assert {key: data["words"][key]["gloss"] for key in expected} == expected


def test_polish_increase_and_divine_source_keep_the_familiar_conclusion():
    data = layer("pl")
    assert data["segments"]["s01"]["translation"] == (
        "Nasyceni świętym darem, pokornie Cię, Panie, błagamy, abyśmy w tym, co "
        "sprawujemy z obowiązku należnej służby, za wstawiennictwem świętego "
        "Wawrzyńca, Twojego Męczennika, doświadczali wzrostu zbawienia, którego "
        "udzielasz. Przez Pana naszego Jezusa Chrystusa, Syna Twojego, który "
        "z Tobą żyje i króluje w jedności Ducha Świętego, Bóg, na wieki wieków."
    )
    assert data["words"]["w008"]["gloss"] == "abyśmy"


@pytest.mark.parametrize("language", ["pl", "en"])
def test_provenance_is_bound_without_new_acceptance(language):
    core = load(f"texts/proprium/{NAME}.json")
    site = next(
        s
        for s in load(f"languages/{language}/translation-provenance.json")["sites"]
        if s["site"] == f"{TEXT}.s01.{language}"
    )
    assert site["source_sha256"] == canonical_hash(source_payload(core["segments"][0]))
    assert site["target_sha256"] == canonical_hash(
        layer(language)["segments"]["s01"]["translation"]
    )
    assert (site["origin"], site["review"]) == ("working-unsettled", "working")


@pytest.mark.parametrize(
    "word,selected,raw",
    [
        ("w026", "Iesum", "Jesum"),
        ("w027", "Christum", "Christum,"),
        ("w030", "Qui", "qui"),
        ("w038", "Sancti,", "Sancti"),
    ],
)
def test_all_digital_accidentals_recorded(word, selected, raw):
    apparatus = load(f"witnesses/{TEXT}/apparatus.json")
    entry = next(e for e in apparatus["adjudicated"] if e["at"] == word)
    assert entry["ours"] == selected and entry["witnesses"] == {"do": raw}


def test_selected_latin_ritual_and_pending_analyses_unchanged():
    core = load(f"texts/proprium/{NAME}.json")
    assert digest(selected_text(core)) == (
        "374009352c7fa9e310a88503210925cc92cb3ae1a8cbe2d18ec9e268654f00c9"
    )
    assert {
        w
        for w, value in core["editorial"]["words"].items()
        if value["analysis"]["review"] == "pending"
    } == {"w003", "w004", "w005", "w014", "w025"}


def test_actual_postcommunion_locus_and_expansion_not_vigil_page():
    graph = load("bibliography/graph.json")
    uses = {
        u["id"].removeprefix(f"use.{TEXT}."): u
        for u in graph["uses"]
        if u["address"].get("text") == TEXT
    }
    proper = uses["mr1962"]
    assert proper["locator"]["printed"] == "p. 636"
    assert proper["locator"]["scan"] == "leaf n717 / PDF p. 718"
    assert proper["evidence_sha256"] == (
        "aac23f3f37427c8aff65a49bc0eaeb5ee9070032f741feb6ecd8c6249ee2eaf1"
    )
    assert proper["verified_on"] == "2026-08-31"
    expansion = uses["expanded-conclusion.mr1962"]
    assert expansion["locator"]["printed"] == "p. xvii"
    assert expansion["evidence_sha256"] == (
        "b511f3aa4016b387d2995b5089e15aa62593c04118052ef48dcc09352fcf769c"
    )
    for collection in ("witnesses", "collations"):
        records = [r for r in graph[collection] if r["text"] == TEXT]
        assert len(records) == (2 if collection == "witnesses" else 1)
        assert all(r["review"] == {"status": "pending"} for r in records)
    printed = (ROOT / f"witnesses/{TEXT}/mr.txt").read_text(encoding="utf-8")
    assert "Benziger 1962 (Editio iuxta typicam)" in printed
    assert "RG 115 a is unaccented" in printed and "tuum, qui" in printed

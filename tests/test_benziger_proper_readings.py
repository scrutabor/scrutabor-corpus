"""Printed readings and source boundaries in the Benziger proper of the Mass."""

import json
from pathlib import Path

import pytest

from checks.collate import collate

ROOT = Path(__file__).resolve().parents[1]
PRINT = "https://archive.org/details/missale-romanum-1962/page/n"
SUNDAY = "proprium.dominica-"
GOSPEL = SUNDAY + "vii-post-pentecosten-evangelium"
GRADUAL = SUNDAY + "xx-post-pentecosten-graduale"
INTROIT = SUNDAY + "x-post-pentecosten-introitus"
LESSON = SUNDAY + "iii-post-epiphaniam-epistola"
SIXTH_GOSPEL = SUNDAY + "vi-post-epiphaniam-evangelium"


def document(text):
    return json.loads((ROOT / "texts" / (text.replace(".", "/") + ".json")).read_text())


def witness(text, name="mr"):
    lines = (ROOT / "witnesses" / text / f"{name}.txt").read_text().splitlines()
    return " ".join(line for line in lines if line and not line.startswith("#")).split()


def apparatus(text):
    return json.loads((ROOT / "witnesses" / text / "apparatus.json").read_text())["adjudicated"]


@pytest.fixture(scope="module")
def sources():
    graph = json.loads((ROOT / "bibliography/graph.json").read_text())
    return (
        {row["id"]: row for row in graph["uses"]},
        {row["id"]: row for row in graph["witnesses"]},
    )


@pytest.mark.parametrize(
    "text,number,printed,selected",
    [
        (GOSPEL, 107, "cælórum.", "cælórum."),
        (GRADUAL, 14, "opportúno.", "opportúno."),
        (LESSON, 24, "fíeri", "fíeri"),
    ],
)
def test_stops_and_accents_in_the_printed_transcription(text, number, printed, selected):
    at = f"w{number:03d}"
    words = {w["id"]: w for s in document(text)["segments"] for w in s.get("words", [])}
    assert witness(text)[number - 1] == printed
    assert words[at]["form"] + words[at].get("post", "") == selected
    assert all("mr" not in row["witnesses"] for row in apparatus(text) if row["at"] == at)
    assert collate(document(text), ROOT / "witnesses" / text)[0] == []


def test_gradual_preserves_both_unaccented_capitals_and_the_verse_boundary():
    words = witness(GRADUAL)
    assert words[0] == "Oculi" and words[11:16] == ["in", "témpore", "opportúno.", "Aperis", "tu"]
    assert {
        (r["at"], r["witnesses"]["mr"]) for r in apparatus(GRADUAL) if "mr" in r["witnesses"]
    } == {("w001", "Oculi"), ("w015", "Aperis")}


def test_fieri_is_supported_by_both_settings(sources):
    uses, witnesses = sources
    main = f"use.{LESSON}.mr1962"
    resumed = f"use.{LESSON}.resumed.mr1962"
    assert uses[main]["locator"]["page_url"] == PRINT + "124/mode/1up"
    assert uses[resumed]["locator"]["page_url"] == PRINT + "493/mode/1up"
    assert uses[resumed]["address"]["word"] == "w024"
    witness_row = witnesses[f"witness.{LESSON}.mr1962"]
    assert witness_row["orthography_profile"] == "exact-page-image"
    assert witness_row["source_dependencies"]["uses"] == [resumed]


def test_cum_and_dum_are_attested_at_the_opening_and_reprise(sources):
    uses, witnesses = sources
    at = {"w001", "w067"}
    words = {
        w["id"]: w["form"] for seg in document(INTROIT)["segments"] for w in seg.get("words", [])
    }
    assert {key: words[key] for key in at} == {"w001": "Dum", "w067": "Dum"}
    assert [witness(INTROIT)[i] for i in (0, 66)] == ["Cum", "Cum"]
    assert [witness(INTROIT, "do")[i] for i in (0, 66)] == ["Dum", "Dum"]
    assert {
        (r["at"], r["ours"], r["witnesses"]["mr"], r["class"])
        for r in apparatus(INTROIT)
        if "mr" in r["witnesses"] and r["at"] in at
    } == {("w001", "Dum", "Cum", "substantive"), ("w067", "Dum", "Cum", "substantive")}
    assert uses[f"use.{INTROIT}.mr1962"]["locator"]["page_url"] == PRINT + "465/mode/1up"
    passages = {p["url"] for p in uses[f"use.{INTROIT}.do44667ff"]["locator"]["passages"]}
    prefix = (
        "https://github.com/DivinumOfficium/divinum-officium/blob/"
        "44667ff518b8ff1439780470828b39714f5306a2/web/www/missa/Latin/Tempora/Pent10-0.txt#L"
    )
    covered = set()
    for url in passages:
        if url.startswith(prefix):
            endpoints = [int(value) for value in url.removeprefix(prefix).split("-L")]
            covered.update(range(endpoints[0], endpoints[-1] + 1))
    assert {15, 19} <= covered
    formula = f"use.{INTROIT}.gloria-formula-and-repetition.mr1962"
    assert uses[formula]["address"]["word"] == "w047"
    assert uses[formula]["locator"]["page_url"] == PRINT + "80/mode/1up"
    witness_row = witnesses[f"witness.{INTROIT}.mr1962"]
    assert witness_row["source_dependencies"]["uses"] == [formula]
    assert witness_row["orthography_profile"] == "page-body-with-declared-house-expansion"
    assert collate(document(INTROIT), ROOT / "witnesses" / INTROIT)[2]["substantive_variants"] == 2


def test_normal_and_resumed_sixth_sunday_gospel_have_different_page_boundaries(sources):
    uses, witnesses = sources
    normal = f"use.{SIXTH_GOSPEL}.normal-proper.mr1962"
    phantom = f"use.{SIXTH_GOSPEL}.normal-proper-continuation.mr1962"
    assert uses[normal]["locator"]["printed"] == "p. 49"
    assert uses[normal]["locator"]["page_url"] == PRINT + "128/mode/1up"
    assert uses[f"use.{SIXTH_GOSPEL}.mr1962"]["locator"]["printed"] == "pp. 416–417"
    assert phantom not in uses
    assert witnesses[f"witness.{SIXTH_GOSPEL}.mr1962"]["source_dependencies"]["uses"] == [normal]


def test_corpus_christi_adds_the_response_to_the_printed_conclusion(sources):
    uses, witnesses = sources
    text = "proprium.corporis-christi-collecta"
    primary = f"use.{text}.mr1962"
    response = f"use.{text}.conclusion-rg115d.mr1962"
    assert uses[primary]["locator"]["printed"] == "p. 369"
    assert uses[response]["locator"]["page_url"] == PRINT + "23/mode/1up"
    assert uses[response]["address"] == {"kind": "word", "text": text, "word": "w046"}
    assert witness(text)[44:46] == ["sæculórum.", "Amen."]
    witness_row = witnesses[f"witness.{text}.mr1962"]
    assert witness_row["source_dependencies"]["uses"] == [response]
    assert witness_row["orthography_profile"] == "page-body-with-declared-house-expansion"

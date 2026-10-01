"""Printed continuations and formula references retain precise source boundaries."""

import json
import re

import pytest

from build_reader import bibliography
from checks.collate import collate, load_witness
from checks.layout import CORPUS, formatted

THOMAS = "sancti-thomae-apostoli-evangelium"
MATERNITY = "maternitas-beatae-mariae-virginis-secreta"
ALL_SAINTS = "omnium-sanctorum-secreta"
SUBJECTS = (THOMAS, MATERNITY, ALL_SAINTS)
LOCATIONS = (
    (THOMAS, "gospel-continuation", "w113", 522, "p. 441"),
    (THOMAS, "hand-wound-parallel", "w033", 416, "p. 335"),
    (MATERNITY, "conclusion-rg115b", "w021", 23, "p. xviii"),
    (MATERNITY, "conclusion-rg115a-base", "w021", 22, "p. xvii"),
    (ALL_SAINTS, "conclusion-rg115a", "w022", 22, "p. xvii"),
)
PAGE_DIGESTS = {
    22: "b511f3aa4016b387d2995b5089e15aa62593c04118052ef48dcc09352fcf769c",
    23: "db99d725287dbdb233ff9c22c94cd027ec6b5105f2f64817ec828778805ff132",
    416: "b92b3b4f88504afd6431f0a8ec80178f35efc2b72639c9cce26252c5b4688af9",
    522: "72d9f28c917d239d9ace19649ed1526b5faafc3d5795cbc2c46675fbfed1f0ad",
}


def graph():
    return json.loads((CORPUS / "bibliography/graph.json").read_bytes())


def core(name):
    return json.loads((CORPUS / "texts/proprium" / f"{name}.json").read_bytes())


@pytest.mark.parametrize("name,suffix,word,leaf,printed", LOCATIONS)
def test_source_reference_keeps_its_exact_locus(name, suffix, word, leaf, printed):
    tid = "proprium." + name
    use = next(u for u in graph()["uses"] if u["id"] == f"use.{tid}.{suffix}.mr1962")
    assert use["address"] == {"kind": "word", "text": tid, "word": word}
    assert use["locator"] == {
        "printed": printed,
        "scan": f"leaf n{leaf} / PDF p. {leaf + 1}",
        "page_url": f"https://archive.org/details/missale-romanum-1962/page/n{leaf}/mode/1up",
    }
    assert use["edition"] == "edition.missale-romanum.1962-typica"
    assert use["digital_item"] == "item.missale-romanum.1962-typica.ia"
    assert use["role"] == "direct_approved_print"
    assert use["decision"] == "RETAIN"
    assert use["evidence_sha256"] == PAGE_DIGESTS[leaf]


@pytest.mark.parametrize("name", SUBJECTS)
def test_source_description_identifies_the_actual_printing(name):
    use = next(u for u in graph()["uses"] if u["id"] == f"use.proprium.{name}.mr1962")
    assert use["role"] == "direct_approved_print"
    assert "Benziger" in use["claim"]
    assert "separately cited" in use["claim"]
    assert "complete 1962 liturgical component" not in use["claim"]
    assert use["decision"] == "RETAIN_WITH_CORRECTION"


@pytest.mark.parametrize("name", SUBJECTS)
def test_current_description_and_transcript_agree_on_printing(name):
    doc = core(name)
    assert "Benziger Brothers, New York, 1962" in doc["editorial"]["source"]["method"]
    assert "1962 typical-edition page image" not in doc["editorial"]["source"]["method"]
    meta, _ = load_witness(CORPUS / "witnesses" / ("proprium." + name) / "mr.txt")
    assert "Benziger Brothers, New York, 1962" in meta["description"]


@pytest.mark.parametrize("name", SUBJECTS)
def test_additional_loci_do_not_approve_source_review(name):
    data = graph()
    tid = "proprium." + name
    witnesses = [w for w in data["witnesses"] if w["text"] == tid]
    assert len(witnesses) == 2
    assert all(w["review"] == {"status": "pending"} for w in witnesses)
    collation = next(c for c in data["collations"] if c["text"] == tid)
    assert collation["review"] == {"status": "pending"}
    row = next(t for t in bibliography.public_text_evidence(data)["texts"] if t["id"] == tid)
    assert row["witnesses"] == [] and "collation" not in row


def test_printed_slip_and_occurrence_specific_correction_remain_distinct():
    folder = CORPUS / "witnesses" / ("proprium." + THOMAS)
    meta, body = load_witness(folder / "mr.txt")
    assert len(re.findall(r"\beis\b", body)) == 4
    assert len(meta["corrigenda"]) == 1
    printed, selected, reason = meta["corrigenda"][0]
    assert (printed, selected) == ("eis#3", "eius")
    assert "ejus" in reason
    raw = (folder / "mr.txt").read_text()
    assert "the body preserves eis" in raw
    assert "the body records 'eius'" not in raw
    words = {w["id"]: w for s in core(THOMAS)["segments"] for w in s["words"]}
    assert [words[w]["form"] for w in ("w014", "w028", "w033")] == ["eis", "eis", "eius"]
    assert (words["w113"]["form"], words["w126"]["form"]) == ("Dixit", "credidérunt")
    assert collate(core(THOMAS), folder)[:2] == ([], [])


@pytest.mark.parametrize("name", [MATERNITY, ALL_SAINTS])
def test_expanded_conclusion_has_one_formula_and_one_response(name):
    folder = CORPUS / "witnesses" / ("proprium." + name)
    _, body = load_witness(folder / "mr.txt")
    assert body.count("Amen") == 1
    assert body.count("per omnia sæcula sæculorum") == 1
    assert "n22/PDF23" in (folder / "mr.txt").read_text()
    assert collate(core(name), folder)[:2] == ([], [])


@pytest.mark.parametrize("name", SUBJECTS)
def test_pending_witness_describes_actual_print_or_composite(name):
    witness = next(
        w
        for w in graph()["witnesses"]
        if w["text"] == "proprium." + name and w["transcription"] == "mr"
    )
    assert "Benziger 1962" in witness["independence_basis"]
    assert "typical-edition page image" not in witness["independence_basis"]
    assert witness["review"] == {"status": "pending"}
    if name == THOMAS:
        assert witness["orthography_profile"] == "exact-page-image"
        assert "pp. 440–441" in witness["independence_basis"]
    else:
        assert witness["orthography_profile"] == "exact-page-body-with-declared-formula-expansion"
        assert "Composite" in witness["independence_basis"]
        assert "RG 115 a" in witness["independence_basis"]
        if name == MATERNITY:
            assert "RG 115 b" in witness["independence_basis"]


@pytest.mark.parametrize("name", SUBJECTS)
def test_source_only_core_description_keeps_canonical_layout(name):
    path = CORPUS / "texts/proprium" / f"{name}.json"
    assert path.read_text() == formatted(core(name))

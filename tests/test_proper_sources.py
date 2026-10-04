"""Every Proper text names the 1962 Missal page that prints it.

The reader shows a Proper text's sources from its normalized uses. A text without a
Missal use shows none, which is how the Advent chants and readings went without sources
after the legacy citations were withdrawn for direct verification.
"""

import json
import re
from pathlib import Path

import pytest

from checks.raw_binding import resolve_binding

ROOT = Path(__file__).resolve().parents[1]
MISSAL = "edition.missale-romanum.1962-typica"
PRINTS = {"official_text", "direct_approved_print"}
ADVENT_SOURCE_TEXTS = [
    f"proprium.dominica-{sunday}-adventus-{part}"
    for sunday in ("i", "ii", "iii", "iv")
    for part in (
        "introitus",
        "collecta" if sunday == "i" else "evangelium",
        "epistola",
        "graduale",
        "alleluia",
        "offertorium",
        "communio",
    )
]


def graph():
    return json.loads((ROOT / "bibliography/graph.json").read_text())


def propers():
    return sorted(f"proprium.{p.stem}" for p in (ROOT / "texts/proprium").glob("*.json"))


def printed(uses):
    return {
        u["address"].get("text")
        for u in uses
        if u["edition"] == MISSAL
        and u["role"] in PRINTS
        and u["address"]["kind"] == "text"
        and u["decision"] in {"RETAIN", "RETAIN_WITH_CORRECTION"}
    }


def test_every_proper_text_has_a_missal_page():
    missing = [t for t in propers() if t not in printed(graph()["uses"])]
    assert missing == []
    assert len(propers()) > 900


def test_the_check_sees_a_text_without_its_page():
    text = "proprium.dominica-i-adventus-introitus"
    uses = [u for u in graph()["uses"] if u["address"].get("text") != text]
    assert text not in printed(uses)


@pytest.mark.parametrize("decision", ["RETAIN", "RETAIN_WITH_CORRECTION"])
def test_retained_prints_count_as_sources(decision):
    use = {
        "edition": MISSAL,
        "role": "direct_approved_print",
        "address": {"kind": "text", "text": "proprium.example"},
        "decision": decision,
    }
    assert printed([use]) == {"proprium.example"}


@pytest.mark.parametrize("decision", ["REMOVE", "REPLACE", "UNVERIFIED_NO_DIRECT_EVIDENCE"])
def test_nonretained_prints_do_not_count_as_sources(decision):
    use = {
        "edition": MISSAL,
        "role": "direct_approved_print",
        "address": {"kind": "text", "text": "proprium.example"},
        "decision": decision,
    }
    assert printed([use]) == set()


@pytest.mark.parametrize("text", ADVENT_SOURCE_TEXTS)
def test_advent_pages_identify_the_direct_approved_print(text):
    # This scan is Benziger's Editio iuxta typicam, approved on its leaf n8.
    # These reviewed uses directly print the component, not promulgate it.
    use = next(use for use in graph()["uses"] if use["id"] == f"use.{text}.mr1962")
    assert use["edition"] == MISSAL
    assert use["role"] == "direct_approved_print"
    assert use["decision"] in {"RETAIN", "RETAIN_WITH_CORRECTION"}


def test_missal_page_locators_name_their_leaf():
    seen = 0
    for use in graph()["uses"]:
        locator = use["locator"]
        first = re.match(r"leaves? (n\d+)", locator.get("scan", ""))
        if use["edition"] != MISSAL or not first or "page_url" not in locator:
            continue
        assert f"/page/{first[1]}/" in locator["page_url"], use["id"]
        seen += 1
    assert seen > 40


JOHN_SECRET = "proprium.nativitas-sancti-ioannis-baptistae-secreta"


def test_baptist_secret_binds_the_actual_digital_body_and_conclusion():
    witness = ROOT / f"witnesses/{JOHN_SECRET}/do.txt"
    bound = resolve_binding(witness, ROOT)
    assert bound is not None
    assert bound.source["binding_id"] == "baptist-secret"
    assert [(first, last) for _, first, last in bound.spans] == [(57, 57), (120, 121)]
    assert "cécinit ad futúrum et adésse monstravit," in bound.text
    assert "nostrum Jesum Christum, Fílium tuum:" in bound.text
    assert "Spíritus Sancti Deus per" in bound.text
    assert "mónstravit" not in bound.text


def test_baptist_secret_declares_its_abbreviated_print_and_separate_expansion():
    sources = graph()
    uses = {u["id"]: u for u in sources["uses"]}
    printed_body = uses[f"use.{JOHN_SECRET}.mr1962"]
    assert printed_body["role"] == "direct_approved_print"
    assert printed_body["locator"]["printed"] == "p. 572"
    for source, raw in [("mr1962", None), ("do44667ff", "baptist-secret")]:
        witness = next(
            w for w in sources["witnesses"] if w["id"] == f"witness.{JOHN_SECRET}.{source}"
        )
        dependency = f"use.{JOHN_SECRET}.expanded-conclusion.{source}"
        dependencies = [dependency]
        if source == "mr1962":
            dependencies += [f"use.{JOHN_SECRET}.{suffix}.mr1962" for suffix in JOHN_RITUAL]
        assert witness["source_dependencies"] == {
            "uses": sorted(dependencies),
            "raw_binding": raw,
        }
        assert uses[dependency]["edition"] == uses[witness["use"]]["edition"]
        assert witness["review"] == {"status": "pending"}
    formula = uses[f"use.{JOHN_SECRET}.expanded-conclusion.mr1962"]
    assert formula["locator"]["scan"] == "leaf n23 / PDF p. 24"
    assert formula["role"] == "direct_approved_print"
    transcript = (ROOT / f"witnesses/{JOHN_SECRET}/mr.txt").read_text()
    assert "Qui tecum vivit. only" in transcript
    assert "house accents" in transcript


def test_baptist_secret_apparatus_quotes_original_accidentals_without_changing_latin():
    apparatus = json.loads((ROOT / f"witnesses/{JOHN_SECRET}/apparatus.json").read_bytes())
    entries = {entry["at"]: entry for entry in apparatus["adjudicated"]}
    for wid, selected, digital in [
        ("w017", "adfutúrum,", "ad futúrum"),
        ("w020", "monstrávit,", "monstravit,"),
        ("w023", "Iesum", "Jesum"),
        ("w024", "Christum", "Christum,"),
        ("w035", "Sancti,", "Sancti"),
        ("w036", "Deus,", "Deus"),
    ]:
        assert entries[wid]["ours"] == selected
        assert entries[wid]["witnesses"]["do"] == digital
    core = json.loads((ROOT / f"texts/{JOHN_SECRET.replace('.', '/')}.json").read_bytes())
    words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    assert len(words) == 40 and core["ids"]["retired"] == {"w016": "s01"}
    assert words["w020"]["form"] == "monstrávit"
    assert words["w023"]["form"] == "Iesum"
    assert words["w001"]["head"] == "w004"


JOHN_RITUAL = {
    "oration-boundaries": (
        37,
        "6c08d654bc198380aad5673bc6f06fdb44076acdfff67087e74aaf4943d23946",
    ),
    "secret-preface-transition": (
        304,
        "c8e1c105fbccab5b133d072bcdc255ff482824182be5e53597e5d2bfbb94e3ee",
    ),
    "secret-response-pattern": (
        305,
        "c8a123467dd47ace390100a021fdcdd61752a5c42635583b92d72cd636027f58",
    ),
    "secret-sung-delivery": (
        39,
        "c03be5250068f8c9c262983bc7689a18d0180b88b0c4476d21fac383c8f07993",
    ),
}


@pytest.mark.parametrize("suffix", JOHN_RITUAL)
def test_baptist_secret_ritual_uses_bind_each_actual_page(suffix):
    uses = {use["id"]: use for use in graph()["uses"]}
    use = uses[f"use.{JOHN_SECRET}.{suffix}.mr1962"]
    leaf, digest = JOHN_RITUAL[suffix]
    assert use["role"] == "rubric_control"
    assert use["locator"]["scan"] == f"leaf n{leaf} / PDF p. {leaf + 1}"
    assert use["locator"]["page_url"].endswith(f"/page/n{leaf}/mode/1up")
    assert use["evidence_sha256"] == digest


def test_baptist_secret_sources_distinguish_the_two_amens_and_seasonal_preface():
    uses = {use["id"]: use for use in graph()["uses"]}
    transition = uses[f"use.{JOHN_SECRET}.secret-preface-transition.mr1962"]
    response = uses[f"use.{JOHN_SECRET}.secret-response-pattern.mr1962"]
    assert transition["locator"]["printed"] == "p. 225"
    assert "Ordo Missae" in transition["locator"]["section"]
    assert "after the priest's subdued Amen" in transition["claim"]
    assert response["locator"]["printed"] == "p. 226"
    assert "de Nativitate Domini" in response["locator"]["section"]
    assert "not the seasonal Preface assigned to John's feast" in response["claim"]
    assert response["address"] == {
        "kind": "segment",
        "text": JOHN_SECRET,
        "segment": "s03",
    }


def test_baptist_secret_does_not_assign_the_audible_tail_to_every_secret():
    uses = {use["id"]: use for use in graph()["uses"]}
    quiet = uses[f"use.{JOHN_SECRET}.oration-boundaries.mr1962"]
    sung = uses[f"use.{JOHN_SECRET}.secret-sung-delivery.mr1962"]
    assert "For the final Secret" in quiet["claim"]
    assert "remains quiet until Per omnia" in quiet["claim"]
    assert quiet["verified_on"] == "2026-09-19"
    assert quiet["decision"] == "RETAIN_WITH_CORRECTION"
    assert "final Secret's Per omnia" in sung["claim"]
    assert "Missa cantata" in sung["claim"]

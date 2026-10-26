"""II Sunday proper pages declare their common expansions and digital framing."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from witness_header_fixture import expected_review

from build_reader import bibliography, store
from build_reader.bibliography_bindings import (
    collation_subject,
    digest,
    transcript_digest,
    witness_subject,
)
from checks.apparatus import derived_summary
from checks.collate import collate
from checks.raw_binding import resolve_binding

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "proprium.dominica-ii-post-pascha-"
NAMES = (
    "introitus",
    "collecta",
    "epistola",
    "alleluia",
    "evangelium",
    "offertorium",
    "secreta",
    "communio",
    "postcommunio",
)
EXPANDED = {
    "introitus": (20, 53, ["doxology.mr1962", "reprise-rubric.mr1962"]),
    "collecta": (24, 47, ["conclusion-rg115a-base.mr1962", "conclusion-rg115b.mr1962"]),
    "secreta": (14, 36, ["conclusion-rg115a.mr1962", "oration-boundaries.mr1962"]),
    "postcommunio": (15, 37, ["conclusion-rg115a.mr1962"]),
}
PAGES = {
    22: ("xvii", "b511f3aa4016b387d2995b5089e15aa62593c04118052ef48dcc09352fcf769c"),
    23: ("xviii", "db99d725287dbdb233ff9c22c94cd027ec6b5105f2f64817ec828778805ff132"),
    80: ("1", "215182ac2415d178917c183486c716ce352777a6084da024e7293a95649b60c7"),
}
LOCI = (
    ("introitus", "doxology.mr1962", 80, "w021", "direct_approved_print"),
    ("introitus", "reprise-rubric.mr1962", 80, "w041", "rubric_control"),
    ("collecta", "conclusion-rg115a-base.mr1962", 22, "w025", "direct_approved_print"),
    ("collecta", "conclusion-rg115b.mr1962", 23, "w026", "rubric_control"),
    ("secreta", "conclusion-rg115a.mr1962", 22, "w015", "direct_approved_print"),
    ("postcommunio", "conclusion-rg115a.mr1962", 22, "w016", "direct_approved_print"),
)


# These source subjects were reviewed; unrelated records remain pending.
ADOPTED_SOURCE_REVIEWS = {
    "witness.proprium.dominica-ii-post-pascha-secreta.do44667ff": (
        "0af23cd3110a81155b9f0df1d4d4868d8249bc7407147dcdc75524e48a72eae8"
    ),
    "witness.proprium.dominica-ii-post-pascha-secreta.mr1962": (
        "1855cf08d35ee9715677ab6e90ca592aab28f4e04fbb4200f2cea2f6d313c242"
    ),
    "collation.proprium.dominica-ii-post-pascha-secreta.mr1962-do44667ff": (
        "b6a9b30668653ba5b3c2bce23a7d9ad55418e50fc4b8880298540e710dc511f0"
    ),
}


def graph():
    return json.loads((ROOT / "bibliography/graph.json").read_bytes())


def use(data, name, suffix):
    return next(u for u in data["uses"] if u["id"] == "use." + PREFIX + name + "." + suffix)


@pytest.mark.parametrize("name", NAMES)
def test_nine_proper_uses_name_the_approved_print(name):
    entry = use(graph(), name, "mr1962")
    assert entry["role"] == "direct_approved_print"
    assert entry["edition"] == "edition.missale-romanum.1962-typica"
    assert entry["digital_item"] == "item.missale-romanum.1962-typica.ia"


@pytest.mark.parametrize("name", EXPANDED)
def test_expansion_is_not_claimed_as_a_complete_proper_page(name):
    data = graph()
    body, full, dependencies = EXPANDED[name]
    tid = PREFIX + name
    core = store.core(ROOT, tid)
    assert len([w for s in core["segments"] for w in s["words"]]) == full
    entry = use(data, name, "mr1962")
    assert "Benziger" in entry["claim"] and "not fully printed" in entry["claim"]
    assert f"{body}-word" in entry["claim"]
    assert "complete 1962 liturgical component" not in entry["claim"]
    witness = next(w for w in data["witnesses"] if w["text"] == tid and w["transcription"] == "mr")
    assert witness["orthography_profile"] == "page-body-with-declared-common-expansion"
    assert witness["source_dependencies"] == {
        "uses": sorted("use." + tid + "." + d for d in dependencies),
        "raw_binding": None,
    }
    transcript = (ROOT / "witnesses" / tid / "mr.txt").read_text()
    assert "# expansion:" in transcript and "# orthography: proper-page body" in transcript
    assert witness["transcription_sha256"] == transcript_digest(transcript)
    assert "exact printed accents" not in transcript
    assert "expan" in core["editorial"]["source"]["method"]
    assert "expan" in core["editorial"]["notes"]
    witness_subject(ROOT, witness, data, core)


@pytest.mark.parametrize("name,suffix,leaf,word,role", LOCI)
def test_common_sources_keep_exact_page_word_and_role(name, suffix, leaf, word, role):
    entry = use(graph(), name, suffix)
    printed, expected_hash = PAGES[leaf]
    assert entry["address"] == {"kind": "word", "text": PREFIX + name, "word": word}
    assert entry["locator"]["printed"] == "p. " + printed
    assert entry["locator"]["scan"] == f"leaf n{leaf} / PDF p. {leaf + 1}"
    assert entry["locator"]["page_url"].endswith(f"/page/n{leaf}/mode/1up")
    assert entry["evidence_sha256"] == expected_hash
    assert entry["role"] == role


def test_eundem_condition_and_100_common_words_are_bounded():
    data = graph()
    assert sum(full - body for body, full, _ in EXPANDED.values()) == 100
    collect = use(data, "collecta", "conclusion-rg115b.mr1962")
    assert "Filii tui" in collect["claim"] and "RG 115 a" in collect["claim"]
    for name in ("secreta", "postcommunio"):
        assert "no eundem" in use(data, name, "conclusion-rg115a.mr1962")["claim"]
    reprise = use(data, "introitus", "reprise-rubric.mr1962")
    assert "w041–w053" in reprise["claim"] and "does not print" in reprise["claim"]


def test_no_witness_or_collation_review_is_promoted():
    data = graph()
    witnesses = [w for w in data["witnesses"] if w["text"] in {PREFIX + n for n in NAMES}]
    collations = [c for c in data["collations"] if c["text"] in {PREFIX + n for n in NAMES}]
    assert len(witnesses) == 18 and len(collations) == 9

    def bounded_reviews(rows):
        for row in rows:
            expected = ADOPTED_SOURCE_REVIEWS.get(row["id"])
            if expected is not None:
                expected = expected_review(row["id"], expected)
            if expected is None:
                assert row["review"] == {"status": "pending"}, "pending evidence is not approval"
                continue
            assert row["review"] == {"status": "reviewed", "sha256": expected}, (
                "exact adopted source review"
            )
            doc = store.core(ROOT, row["text"])
            if row["id"].startswith("witness."):
                subject = witness_subject(ROOT, row, data, doc)
            else:
                subjects = {
                    w["id"]: witness_subject(ROOT, w, data, doc)
                    for w in data["witnesses"]
                    if w["id"] in row["witnesses"]
                }
                subject = collation_subject(ROOT, row, doc, subjects)
            assert digest(subject) == expected, "adopted source subject changed"

    assert set(ADOPTED_SOURCE_REVIEWS) <= {r["id"] for r in witnesses + collations}
    bounded_reviews(witnesses + collations)
    bad = deepcopy(witnesses)
    pending_row = next(r for r in bad if r["id"] not in ADOPTED_SOURCE_REVIEWS)
    pending_review = deepcopy(pending_row["review"])
    pending_row["review"] = {"status": "reviewed", "sha256": "0" * 64}
    assert bad != witnesses
    with pytest.raises(AssertionError, match=r"^pending evidence is not approval(?:\n|$)"):
        bounded_reviews(bad)
    pending_row["review"] = pending_review
    assert bad == witnesses
    bounded_reviews(bad)
    stale = deepcopy(witnesses)
    reviewed_row = next(r for r in stale if r["id"] in ADOPTED_SOURCE_REVIEWS)
    reviewed_review = deepcopy(reviewed_row["review"])
    reviewed_row["review"]["sha256"] = "0" * 64
    assert stale != witnesses
    with pytest.raises(AssertionError, match=r"^exact adopted source review(?:\n|$)"):
        bounded_reviews(stale)
    reviewed_row["review"] = reviewed_review
    assert stale == witnesses
    bounded_reviews(stale)
    bounded_reviews(witnesses + collations)
    texts = {PREFIX + n for n in NAMES}
    evidence = {r["id"]: r for r in bibliography.public_text_evidence(data)["texts"]}
    for text in texts:
        entry = evidence[text]
        expected_witnesses = [
            {
                key: row[key]
                for key in ("id", "text", "use", "role", "coverage", "independence_basis")
            }
            for row in sorted(witnesses, key=lambda row: row["id"])
            if row["text"] == text and row["id"] in ADOPTED_SOURCE_REVIEWS
        ]
        assert entry["witnesses"] == expected_witnesses
        expected_collations = [
            row for row in collations if row["text"] == text and row["id"] in ADOPTED_SOURCE_REVIEWS
        ]
        if expected_collations:
            assert len(expected_collations) == 1
            assert entry["collation"] == {
                key: expected_collations[0][key]
                for key in ("id", "text", "recension", "witnesses", "apparatus")
            }
        else:
            assert "collation" not in entry


def test_exact_terminal_tilde_disposition_retains_raw_pastor_stop():
    name = PREFIX + "evangelium"
    resolution = resolve_binding(ROOT / "witnesses" / name / "do.txt", ROOT)
    assert resolution.source["contract"] == "raw-reading-3"
    assert resolution.text.endswith("pastor.") and not resolution.text.endswith("~")
    assert len(resolution.fragments) == 1
    fragment = resolution.fragments[0]
    assert fragment.raw.endswith("pastor.~") and fragment.text.endswith("pastor.")
    framing = fragment.framing
    assert len(framing) == 1 and framing[0].text == "~"
    assert framing[0].kind == "terminal-continuation-tilde"
    assert framing[0].end == framing[0].start + 1 == len(fragment.raw)
    assert fragment.line == 39
    apparatus = json.loads((ROOT / "witnesses" / name / "apparatus.json").read_bytes())
    assert not any(e["at"] == "w109" for e in apparatus["adjudicated"])
    assert apparatus["summary"] == derived_summary(apparatus)
    assert apparatus["summary"]["entries"] == 9


def test_alleluia_exact_pair_explains_spelling_and_stop():
    apparatus = json.loads(
        (ROOT / "witnesses" / (PREFIX + "alleluia") / "apparatus.json").read_bytes()
    )
    entry = next(e for e in apparatus["adjudicated"] if e["at"] == "w010")
    assert (entry["ours"], entry["witnesses"]["do"], entry["class"]) == (
        "Allelúia.",
        "Allelúja",
        "orthography",
    )
    assert "i/j" in entry["ruling"] and "terminal full stop" in entry["ruling"]
    assert apparatus["summary"] == derived_summary(apparatus)


@pytest.mark.parametrize("name", NAMES)
def test_complete_neutral_collation_stays_exact(name):
    assert collate(store.core(ROOT, PREFIX + name), ROOT / "witnesses" / (PREFIX + name))[:2] == (
        [],
        [],
    )

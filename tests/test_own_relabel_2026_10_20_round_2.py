"""English and Polish provenance labels relabelled on 2026-10-20 (second round).

A site labelled `own` claims that its wording is the edition's own. For the sites pinned here that
claim cannot be shown from the edition's history: the first published wording reproduced or closely
followed wording that was already visible, or independent drafting cannot be demonstrated. They are
held as unsettled working wording until their basis is cited or they are redrafted. Segments whose
wording the Latin dictates (the six-word preface address with the Common Preface's short
conclusion, bare Alleluias, and the short speech headings and replies of the Passion) are trivial
and assert no wording basis. The Polish Introit doxology of Trinity Sunday, Corpus Christi and the
Sacred Heart is the traditional Glória Patri, cited from the page that carries
orationes.gloria-patri. The relabel changes no wording: each verse keeps the target hash it had
before (tests/fixtures/own-relabel-2026-10-20-round-2.json).
"""

import json
from collections import Counter
from copy import deepcopy
from functools import cache
from pathlib import Path

import pytest
from post_ascension_fixture import expected_row_successor
from provenance_successor_fixture import FIXTURE as SUCCESSOR

from build_reader import store
from checks import translation_basis
from checks.translation_provenance import (
    WORDING_BASIS,
    canonical_hash,
    check,
    corpus_sites,
    protected,
    wording_bases,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads(
    (ROOT / "tests/fixtures/own-relabel-2026-10-20-round-2.json").read_text(encoding="utf-8")
)
HISTORICAL_LABELS = FIXTURE["sites"]
LABELS = deepcopy(HISTORICAL_LABELS)
SUCCESSOR_SITES = set(LABELS) & set(SUCCESSOR["after_rows"])
assert len(SUCCESSOR_SITES) == 11
for _site in SUCCESSOR_SITES:
    _row = SUCCESSOR["after_rows"][_site]
    assert LABELS[_site] == {key: SUCCESSOR["before_rows"][_site][key] for key in LABELS[_site]}
    LABELS[_site].update({key: _row[key] for key in LABELS[_site]})
for _site in LABELS:
    LABELS[_site]["familiar_core"] = (
        SUCCESSOR["after_rows"].get(_site, {}).get("familiar_core", False)
    )
PRE_ASCENSION_LABELS = deepcopy(LABELS)
LABELS = {site: expected_row_successor(row, site) for site, row in LABELS.items()}
SITES = sorted(LABELS)
SAMPLE = FIXTURE["wording_sample"]
DOXOLOGY = FIXTURE["doxology_uses"]
COMMON_PREFACE = FIXTURE["common_preface_address"]
GLORIA_PATRI_USE = "use.pl.a37d7afa350c2273d2f6"
COUNTS = {
    "en": {"trivial": 22, "working-unsettled": 145},
    "pl": {"traditional": 3, "trivial": 38, "working-unsettled": 198},
}
RETAINED = {"RETAIN", "RETAIN_WITH_CORRECTION"}


@cache
def _ledger():
    rows = {}
    for language in ("en", "pl"):
        path = ROOT / f"languages/{language}/translation-provenance.json"
        rows.update({r["site"]: r for r in json.loads(path.read_text(encoding="utf-8"))["sites"]})
    return rows


def ledger():
    return deepcopy(_ledger())


@cache
def uses(language):
    path = ROOT / f"languages/{language}/bibliography.json"
    return tuple(json.loads(path.read_text(encoding="utf-8"))["uses"])


@cache
def basis_records(language):
    path = ROOT / f"languages/{language}/translation-basis.json"
    return tuple(json.loads(path.read_text(encoding="utf-8"))["records"])


@cache
def sites_in_corpus():
    return corpus_sites(ROOT)


def verse(site):
    text, segment, language = site.rsplit(".", 2)
    return store.raw_layer(ROOT, language, text)["segments"][segment]["translation"]


def rejects(check_fn, *args, message):
    """The control: the check raises AssertionError whose first line names the defect."""
    with pytest.raises(AssertionError) as caught:
        check_fn(*args)
    assert str(caught.value).splitlines()[0] == message


def assert_label(site, row):
    assert row["origin"] == LABELS[site]["origin"], "pinned origin"
    assert row["review"] == LABELS[site]["review"], "pinned review"
    assert row["familiar_core"] is LABELS[site]["familiar_core"], "familiar core"


def assert_wording_unchanged(site, row, target):
    assert row["target_sha256"] == LABELS[site]["target_sha256"], "unchanged wording"
    assert canonical_hash(target) == LABELS[site]["target_sha256"], "unchanged wording"


def covering_records(language, text, segment):
    return [
        r
        for r in basis_records(language)
        if text in r["texts"] and (r.get("segments") is None or segment in r["segments"])
    ]


def test_inventory():
    rows = ledger()
    assert len(SITES) == len(set(SITES)) == 406
    counts: dict[str, Counter[str]] = {}
    for site in SITES:
        text, segment, language = site.rsplit(".", 2)
        row = rows[site]
        assert (row["text"], row["segment"], row["language"]) == (text, segment, language)
        assert protected(text, language, segment) is LABELS[site]["familiar_core"]
        counts.setdefault(language, Counter())[HISTORICAL_LABELS[site]["origin"]] += 1
    assert {language: dict(c) for language, c in counts.items()} == COUNTS
    assert {LABELS[site]["review"] for site in SITES} == {"working"}
    assert len(SAMPLE) >= 40 and set(SAMPLE) <= set(SITES)
    assert {site.rsplit(".", 1)[1] for site in SAMPLE} == {"en", "pl"}
    assert {LABELS[site]["origin"] for site in SAMPLE} == {
        "working-unsettled",
        "trivial",
        "traditional",
    }


@pytest.mark.parametrize("site", SITES)
def test_the_label_is_pinned(site):
    assert_label(site, ledger()[site])


@pytest.mark.parametrize("site", SITES)
def test_an_own_claim_is_rejected(site):
    row = ledger()[site]
    row["origin"] = "own"
    rejects(assert_label, site, row, message="pinned origin")


@pytest.mark.parametrize("site", SITES)
def test_a_reviewed_claim_is_rejected(site):
    row = ledger()[site]
    row["review"] = "internally-reviewed"
    rejects(assert_label, site, row, message="pinned review")


@pytest.mark.parametrize("site", SITES)
def test_current_wording_matches_its_historical_or_exact_successor_hash(site):
    assert_wording_unchanged(site, ledger()[site], verse(site))


@pytest.mark.parametrize("damage", ["ledger", "verse"])
@pytest.mark.parametrize("site", SAMPLE)
def test_changed_wording_is_rejected(site, damage):
    row, target = ledger()[site], verse(site)
    if damage == "ledger":
        row["target_sha256"] = canonical_hash(target + " ")
    else:
        target = target.rstrip(".,:;?!") + ", alleluia."
        assert target != verse(site)
    rejects(assert_wording_unchanged, site, row, target, message="unchanged wording")


def test_the_ledger_and_the_basis_registry_accept_the_relabel():
    errors, _tally = check(ROOT)
    assert not [e for e in errors if any(site in e for site in SITES)]
    errors, _tally = translation_basis.check(ROOT)
    assert not [e for e in errors if any(site in e for site in SITES)]


@pytest.mark.parametrize("site", SITES)
def test_the_citation_state_matches_the_label(site):
    cited = sites_in_corpus()[site]["has_wording_citations"]
    origin = LABELS[site]["origin"]
    if origin == "trivial":
        assert cited is False
    elif origin == "traditional":
        assert cited is True


@pytest.mark.parametrize("site", sorted(DOXOLOGY))
def test_the_polish_introit_doxology_carries_its_scoped_basis(site):
    text, segment, language = site.rsplit(".", 2)
    assert language == "pl" and LABELS[site]["origin"] == "traditional"
    by_id = {u["id"]: u for u in uses("pl")}
    use, model = by_id[DOXOLOGY[site]], by_id[GLORIA_PATRI_USE]
    assert model["address"] == {
        "kind": "segment",
        "text": "orationes.gloria-patri",
        "segment": "s01",
    }
    assert use["role"] == WORDING_BASIS and use["decision"] in RETAINED
    assert use["address"] == {"kind": "segment", "text": text, "segment": segment}
    assert (use["edition"], use["digital_item"], use["locator"]) == (
        model["edition"],
        model["digital_item"],
        model["locator"],
    )
    assert use["claim"].endswith(f"„{verse(site)}”")
    gloria = [verse(f"orationes.gloria-patri.{s}.pl") for s in ("s01", "s02")]
    assert verse(site) == " ".join(gloria)
    cited_sites, cited_texts = wording_bases(list(by_id.values()), "pl")
    assert site in cited_sites and text not in cited_texts
    without = [u for u in by_id.values() if u["id"] != use["id"]]
    assert site not in wording_bases(without, "pl")[0]
    (record,) = covering_records("pl", text, segment)
    (gloria_record,) = covering_records("pl", "orationes.gloria-patri", "s01")
    assert record == {
        "texts": [text],
        "segments": [segment],
        "relationship": gloria_record["relationship"],
    }
    assert protected(text, "pl", segment) and ledger()[site]["familiar_core"] is True


@pytest.mark.parametrize("language", ["en", "pl"])
def test_the_common_preface_address_asserts_no_wording_basis(language):
    text, segment = "ordinarium.praefatio-communis", "s03"
    site = f"{text}.{segment}.{language}"
    assert LABELS[site]["origin"] == "trivial"
    by_id = {u["id"]: u for u in uses(language)}
    use = by_id[COMMON_PREFACE[language]]
    assert use["address"] == {"kind": "segment", "text": text, "segment": segment}
    assert use["role"] == WORDING_BASIS and use["decision"] == "REMOVE"
    assert use["decision_reason"].strip() and use["legacy_refs"]
    assert site not in wording_bases(list(by_id.values()), language)[0]
    assert [
        u for u in by_id.values() if u["address"] == use["address"] and u["decision"] in RETAINED
    ] == []
    assert covering_records(language, text, segment) == []
    assert sites_in_corpus()[site]["has_wording_citations"] is False


def test_successor_changes_only_three_passion_labels_and_eight_introit_flags():
    passion = {site for site in SUCCESSOR_SITES if "-evangelium.s" in site}
    introits = SUCCESSOR_SITES - passion
    assert passion == {
        f"proprium.dominica-ii-passionis-evangelium.{segment}.pl"
        for segment in ("s46", "s70", "s78")
    }
    assert len(introits) == 8 and all("-introitus." in site for site in introits)
    for site in passion:
        assert HISTORICAL_LABELS[site]["origin"] == "trivial"
        assert LABELS[site]["origin"] == "working-unsettled"
        assert LABELS[site]["familiar_core"] is False
    for site in introits:
        assert LABELS[site]["origin"] == HISTORICAL_LABELS[site]["origin"]
        assert LABELS[site]["familiar_core"] is True
    for site in SITES:
        assert (
            PRE_ASCENSION_LABELS[site]["target_sha256"] == HISTORICAL_LABELS[site]["target_sha256"]
        )
    current_counts = {
        language: dict(
            Counter(LABELS[site]["origin"] for site in SITES if site.endswith("." + language))
        )
        for language in ("en", "pl")
    }
    assert current_counts == {
        "en": {"trivial": 22, "working-unsettled": 145},
        "pl": {"traditional": 3, "trivial": 35, "working-unsettled": 201},
    }


@pytest.mark.parametrize("site", SITES)
def test_a_changed_protection_flag_is_rejected(site):
    row = ledger()[site]
    row["familiar_core"] = not row["familiar_core"]
    rejects(assert_label, site, row, message="familiar core")

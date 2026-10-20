"""English chant verses of the Ascension and of the Sunday after the Ascension held as
unsettled wording.

The Alleluia, Offertory and Communion of the Ascension and the Introit, Alleluia and Communion
of the Sunday after the Ascension were first published in wording that follows the Douay-Rheims
psalter or the Missal for the Laity closely, and were later revised in register. A revised
public-domain base is not the edition's own wording, so the six sites are held as unsettled
working wording until their basis is cited or they are redrafted. The relabel changes no
wording: each verse keeps the target hash it had while it was labelled `own`.
"""

import json
from copy import deepcopy
from functools import cache
from pathlib import Path

import pytest

from build_reader import store
from checks.translation_provenance import canonical_hash, check, protected

ROOT = Path(__file__).resolve().parents[1]

# Each site's target hash as recorded while it was labelled `own`.
WORDING = {
    "proprium.ascensio-domini-alleluia.s01.en": (
        "f514d7d16ff9d9fcec3758ec0e04734b91ff788524c1003d4d1681dec8b0a9ce"
    ),
    "proprium.ascensio-domini-offertorium.s01.en": (
        "15599049d282b89377d288ef96e861c5c2776673d511029c5206a81c8f6c6cde"
    ),
    "proprium.ascensio-domini-communio.s01.en": (
        "c084e8892712745c01de95de6945434da6359d14b04ca42706210a180f2316e9"
    ),
    "proprium.dominica-post-ascensionem-introitus.s01.en": (
        "4ca8691ee582db4aa9769c516898e52e84a7dc42fb47b048a590b66932d6ece3"
    ),
    "proprium.dominica-post-ascensionem-alleluia.s01.en": (
        "97a7ac7db8862e8d66fd13166ab058f012a482fdbb9072dd91629ec184c35005"
    ),
    "proprium.dominica-post-ascensionem-communio.s01.en": (
        "77231e17e8052796f84f138ce77fa8d2b894d12954671a859c15bcbc009f8097"
    ),
}
SITES = list(WORDING)


@cache
def _provenance():
    path = ROOT / "languages/en/translation-provenance.json"
    return {s["site"]: s for s in json.loads(path.read_text(encoding="utf-8"))["sites"]}


def provenance():
    return deepcopy(_provenance())


def verse(site):
    text, segment, language = site.rsplit(".", 2)
    return store.raw_layer(ROOT, language, text)["segments"][segment]["translation"]


def rejects(check_fn, *args, message):
    """The control: the check raises AssertionError whose first line names the defect."""
    with pytest.raises(AssertionError) as caught:
        check_fn(*args)
    assert str(caught.value).splitlines()[0] == message


def assert_unsettled(row):
    assert row["origin"] == "working-unsettled", "unsettled origin"
    assert row["review"] == "working", "working review"
    assert row["familiar_core"] is False, "familiar core"


def assert_wording_unchanged(site, row, target):
    assert row["target_sha256"] == WORDING[site], "unchanged wording"
    assert canonical_hash(target) == WORDING[site], "unchanged wording"


def test_inventory():
    sites = provenance()
    assert len(SITES) == len(set(SITES)) == 6
    for site in SITES:
        row = sites[site]
        assert (row["language"], row["segment"]) == ("en", "s01")
        assert site == f"{row['text']}.s01.en"
        assert not protected(row["text"], "en", "s01")


@pytest.mark.parametrize("site", SITES)
def test_the_site_is_held_as_unsettled_working_wording(site):
    assert_unsettled(provenance()[site])


def test_the_ledger_accepts_the_six_sites():
    errors, _tally = check(ROOT)
    assert not [e for e in errors if any(site in e for site in SITES)]


@pytest.mark.parametrize("site", SITES)
def test_an_own_claim_is_rejected(site):
    row = provenance()[site]
    row["origin"] = "own"
    rejects(assert_unsettled, row, message="unsettled origin")


@pytest.mark.parametrize("site", SITES)
def test_a_reviewed_claim_is_rejected(site):
    row = provenance()[site]
    row["review"] = "internally-reviewed"
    rejects(assert_unsettled, row, message="working review")


@pytest.mark.parametrize("site", SITES)
def test_the_relabel_changes_no_wording(site):
    assert_wording_unchanged(site, provenance()[site], verse(site))


@pytest.mark.parametrize("damage", ["ledger", "verse"])
@pytest.mark.parametrize("site", SITES)
def test_changed_wording_is_rejected(site, damage):
    row, target = provenance()[site], verse(site)
    if damage == "ledger":
        row["target_sha256"] = canonical_hash(target + " ")
    else:
        target = target.replace(", alleluia", ", alleluia, alleluia", 1)
        assert target != verse(site)
    rejects(assert_wording_unchanged, site, row, target, message="unchanged wording")

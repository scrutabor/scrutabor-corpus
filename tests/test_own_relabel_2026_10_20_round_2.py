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
from corpus_christi_epistle_fixture import expected_corpus_christi_epistle_row
from lauda_sion_fixture import SITES as LAUDA_SITES
from lauda_sion_fixture import predecessor_wording
from marian_chant_fixture import expected_marian_row
from pentecost_successor_fixture import expected_pentecost_row
from polish_reader_successor_fixture import before_polish_reader_wording
from post_ascension_fixture import expected_row_successor
from provenance_successor_fixture import FIXTURE as SUCCESSOR
from rosary_communion_fixture import (
    TEXT as ROSARY_TEXT,
)
from rosary_communion_fixture import (
    healthy_rosary,
    predecessor_rosary_wording,
    reviewed_rosary,
)
from test_pentecost_vigil_successors import expected_communion_row

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
LABELS = {site: expected_communion_row(row, site) for site, row in LABELS.items()}
LABELS = {site: expected_pentecost_row(row, site) for site, row in LABELS.items()}
LABELS = {site: expected_marian_row(row, site) for site, row in LABELS.items()}
LABELS = {site: expected_corpus_christi_epistle_row(row, site) for site, row in LABELS.items()}
VISITATION_SITE = "proprium.visitatio-beatae-mariae-virginis-offertorium.s01.en"
VISITATION_TARGET_BEFORE = "956755748d0c14fbda4b9055d5e2d904b626345888262a58fd94cea855f35039"
VISITATION_TARGET_AFTER = "98aa8cf65580a6d62c6572951ce9fb8f6f199cc2c9a74924a57e57fe57e24381"
assert LABELS[VISITATION_SITE]["target_sha256"] == VISITATION_TARGET_BEFORE
LABELS[VISITATION_SITE]["target_sha256"] = VISITATION_TARGET_AFTER
PRE_CORPUS_CHRISTI_CHANT_LABELS = deepcopy(LABELS)
CORPUS_CHRISTI_CHANT_TARGETS = {
    "proprium.corporis-christi-graduale.s01.en": (
        "37dceb6542dcda890f998f371c6dc6c2d1f961759f02302703d14c4d0565f7d8",
        "766cc925932279ca12893c8fb504b2869105ffedb0bac5abf857b1f3800ad036",
    ),
    "proprium.corporis-christi-graduale.s02.en": (
        "0007edff183c5e9ebd6498a26a76087804b7482375df2544a37dce0e43fc9c6a",
        "ebc843c521b6443e57bbf8bd5f0e4f196fc0a1556234206535633dad1ea7a7c8",
    ),
    "proprium.corporis-christi-sequentia.s01.en": (
        "668fb5dd6498f6575ea663ccee349d93640930a8858ad7b86dfae793841d7d69",
        "c09246318e6d36b93a93d7f1dfbc2b113d5b8d4b55671da83336be10ce26fd78",
    ),
    "proprium.corporis-christi-sequentia.s02.en": (
        "7608bbe750e91f5e212ef346d07608811647ff8c01aee79c84d0014fceaae067",
        "eff13d6d1c188a9bc8ae636c902fd70a820f0acdcc2dd6c74ebcfdf8fdb7ce67",
    ),
    "proprium.corporis-christi-sequentia.s03.en": (
        "70a2bf80ad1b5708ddf55607be80c200310a57beb314653e970655c7ad434329",
        "8a0a00cf1bbde90c9d34f00a209610f1e62e563b3c08ec128ed499cc304a021e",
    ),
    "proprium.corporis-christi-sequentia.s12.en": (
        "13963f01296ea1cf3e1a59ea05965dbd1e4322d939c2942cbb4a9fbae996aead",
        "2921c98f2f457c69a92f9056f2b950b9aea9e56e80b328e63c6ca58e4c3c0a00",
    ),
    "proprium.corporis-christi-sequentia.s13.en": (
        "e07ec269810fdaec02bb154435efe3990b9535ceafae84b79cca1c1f663764f5",
        "f32d1bb26ec12872b3a1fa8ae62f4a553ee363d3ba08368a64622bdbc2b610b4",
    ),
    "proprium.corporis-christi-sequentia.s19.en": (
        "ce649685973f811bad32dfef1c2877af1708a646e3c9b3f1dd7c2b7686eb04d0",
        "0925505d461c9df85710814a8625f81684773fca5c0e6931b1d02ab9cced6adf",
    ),
}
assert len(CORPUS_CHRISTI_CHANT_TARGETS) == 8
for _site, (_before, _after) in CORPUS_CHRISTI_CHANT_TARGETS.items():
    assert LABELS[_site]["target_sha256"] == _before
    LABELS[_site]["target_sha256"] = _after
PRE_JOSEPH_LABELS = deepcopy(LABELS)
JOSEPH_SITE = "proprium.sancti-ioseph-opificis-alleluia.s01.en"
JOSEPH_TARGET_BEFORE = "bc147f4ca9387fc9ebad464c97458bb11eeedc4dbc641cef1754dbbdfa89388d"
JOSEPH_TARGET_AFTER = "1a1ade2c0bfee9129296789b80faeeb2bae207f5d485d2ff677b23e4c7a665f6"
assert LABELS[JOSEPH_SITE]["target_sha256"] == JOSEPH_TARGET_BEFORE
LABELS[JOSEPH_SITE]["target_sha256"] = JOSEPH_TARGET_AFTER
# Contextual name successors do not rewrite the historical label snapshots.
CONTEXTUAL_NAME_TARGETS = {
    "proprium.immaculata-conceptio-tractus.s01.en": (
        "9b364c0745cba65972d229378eb14c584886fc4a9583ebb439f77a7860093408",
        "3e60063e3cf60615de9d5cb472f8c8dcff6a1d9ac229f8695c26a64bbf3330be",
    ),
    "proprium.nativitas-domini-in-aurora-communio.s01.en": (
        "8813ef0abe10d3a64eaeca0f5f85e89f1281b961a37ae29659fb2167e8a28da1",
        "280511f8739c983513ac7d33d0a64d73825cfbf33fb0476379abb861ff2fc93d",
    ),
}
assert len(CONTEXTUAL_NAME_TARGETS) == 2
for _site, (_before, _after) in CONTEXTUAL_NAME_TARGETS.items():
    assert LABELS[_site]["target_sha256"] == _before
# Only the exact created-saints capitalization targets supersede these snapshots.
ALL_SOULS_TARGETS = {
    "proprium.commemoratio-omnium-fidelium-defunctorum-missa-i-communio.s01.pl": [
        "c15112c551ab9d8ac7372cf7ad8d277106c23b0b791b17530cde1ab6737b1375",
        "36c490c9a65f7659a1269a6f862ea5f9013c8fbc688b9f5a4171900a2ecb1ae3",
    ],
    "proprium.commemoratio-omnium-fidelium-defunctorum-missa-i-communio.s01.en": [
        "3cd6cc3291e583a976cde17cc8aabf7e434733a4593d22a2be46ed0357d44776",
        "1d1bd4432537725e6e4bc222f4f11ab462f8a4c3724de20b1d623baf9b13686d",
    ],
}
assert len(ALL_SOULS_TARGETS) == 2
for _site, (_before, _after) in ALL_SOULS_TARGETS.items():
    assert LABELS[_site]["target_sha256"] == _before
# The revised Psalm 42 verse (set my cause apart) supersedes its snapshot by exact hash only.
PSALM_CAUSE_TARGETS = {
    "ordinarium.iudica-me.s03.en": (
        "3d612d204ce83e62468b5342f568d5c2aa567504284f2eb0e96c1b2dc13eb8ca",
        "d1ad04988c468c058133172e8e342df9e70b74f489aef1c3bd898aca0ecd9bee",
    ),
}
assert len(PSALM_CAUSE_TARGETS) == 1
for _site, (_before, _after) in PSALM_CAUSE_TARGETS.items():
    assert LABELS[_site]["target_sha256"] == _before
# The contemporary register prose supersedes its snapshot by exact hash only.
REGISTER_TARGETS = {
    "proprium.cathedra-sancti-petri-offertorium.s01.en": (
        "fee56bf468f348c13561128b76f8183269496bf040e36bd14f4671e4d48b66bc",
        "0834080900d5468a3367b01e7b0e35d27491cb682892d7a0c1d084f42e32709e",
    ),
    "proprium.corporis-christi-alleluia.s02.en": (
        "4da9be47197dfa68c7a93392eddae2c4658e15b1a76483c6959e0eecba18ed36",
        "8c5fb501d63c87e20e15f4eb4cea4db37765a29eb2652ac625bc68127f1bcef7",
    ),
    "proprium.corporis-christi-communio.s01.en": (
        "1015ab9338d118a2bd6eeab3486d43d16124d709609f447840cc872c0e694220",
        "95e0dfabf13b41eddb797918e02fe8f9d0d2cfa31e4348e148158201f50ff046",
    ),
    "proprium.nativitas-sancti-ioannis-baptistae-alleluia.s01.en": (
        "9c681ecbf04ebab3b312b23b65d4b4308ca24153362a372bf977201e387616f0",
        "dd46fdaccab18f8c5358ca03e2a697a6faad4953ded768528cc0cfe0b2120bda",
    ),
    "proprium.nativitas-sancti-ioannis-baptistae-communio.s01.en": (
        "98a2d2ad9eeb0abcb0b1dbf3c9b1f746b1f9e2c64d16948cf172fc3303384ba6",
        "6ac4256e7129bd53b645cf6c70d7cd8a9e0fdd0213e507d458588eea14bbf3ac",
    ),
    "proprium.omnium-sanctorum-communio.s01.en": (
        "dbc407d3328112b1a000626eafc1095a1281a4648809269c09fd19b7e681ab63",
        "05977bea3c1e89d8659fca289a072b46e2a28a76faf0f27143c8ce1562e04623",
    ),
    "proprium.sacratissimi-cordis-iesu-alleluia.s02.en": (
        "e9a31e3206052b9d2f2d05e9ae85950f61344c9b37bea88dbe11353b8f3f3541",
        "8429d410d766e35e6d017bd6eef98496788533eed972d22c3d5574c2e356aff6",
    ),
    "proprium.sacratissimi-cordis-iesu-introitus.s02.en": (
        "e6fc963a7de7d075b32d106a090d6c7c91e101b2bf61afc125f8ed8e88a292f2",
        "ccfe3c379d46c75ff2572e8866201104e9da01807142771a2581d81bf079cda9",
    ),
    "proprium.sancti-iacobi-apostoli-communio.s01.en": (
        "afb178d7825a762af0be6fc0a36448f4e40d946135a76cc91bea0dece5a67974",
        "3488c704976a17cba3180cdf80dd90fa2e9d778e0b9a9d5a218f3f8d659e5097",
    ),
}
assert len(REGISTER_TARGETS) == 9
for _site, (_before, _after) in REGISTER_TARGETS.items():
    assert LABELS[_site]["target_sha256"] == _before
EXACT_WORDING_TARGETS = {
    **REGISTER_TARGETS,
    **CONTEXTUAL_NAME_TARGETS,
    **ALL_SOULS_TARGETS,
    **PSALM_CAUSE_TARGETS,
}
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
    if site == f"{ROSARY_TEXT}.s01.en":
        current_core = store.core(ROOT, ROSARY_TEXT)
        current_layer = store.raw_layer(ROOT, "en", ROSARY_TEXT)
        healthy_rosary(current_core, current_layer)
        reviewed_rosary(current_core, current_layer)
        row, target = predecessor_rosary_wording(row, target)
    if site in LAUDA_SITES:
        row, target = predecessor_wording(site, row, target)
    row, target = before_polish_reader_wording(site, row, target)
    expected = LABELS[site]["target_sha256"]
    if site in EXACT_WORDING_TARGETS:
        before, expected = EXACT_WORDING_TARGETS[site]
        assert LABELS[site]["target_sha256"] == before, "predecessor wording"
    assert row["target_sha256"] == expected, "unchanged wording"
    assert canonical_hash(target) == expected, "unchanged wording"


def covering_records(language, text, segment):
    return [
        r
        for r in basis_records(language)
        if text in r["texts"] and (r.get("segments") is None or segment in r["segments"])
    ]


def test_inventory():
    rows = ledger()
    assert len(SITES) == len(set(SITES)) == 406
    assert {
        site
        for site in PRE_JOSEPH_LABELS
        if PRE_JOSEPH_LABELS[site] != PRE_CORPUS_CHRISTI_CHANT_LABELS[site]
    } == set(CORPUS_CHRISTI_CHANT_TARGETS)
    recovered = deepcopy(PRE_JOSEPH_LABELS)
    for site, (before, _after) in CORPUS_CHRISTI_CHANT_TARGETS.items():
        recovered[site]["target_sha256"] = before
    assert recovered == PRE_CORPUS_CHRISTI_CHANT_LABELS
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
    row, target = ledger()[site], verse(site)
    assert_wording_unchanged(site, row, target)
    if site in CORPUS_CHRISTI_CHANT_TARGETS:
        before, after = CORPUS_CHRISTI_CHANT_TARGETS[site]
        original = deepcopy(row)
        row["target_sha256"] = before
        assert row != original
        rejects(assert_wording_unchanged, site, row, target, message="unchanged wording")
        row["target_sha256"] = after
        assert row == original
        assert_wording_unchanged(site, row, target)
        assert_label(site, row)
    elif site in EXACT_WORDING_TARGETS:
        before, after = EXACT_WORDING_TARGETS[site]
        original = deepcopy(row)
        assert row["target_sha256"] == after
        try:
            row["target_sha256"] = before
            assert row != original
            rejects(assert_wording_unchanged, site, row, target, message="unchanged wording")
        finally:
            row["target_sha256"] = after
            assert row == original
            assert_wording_unchanged(site, row, target)
            assert_label(site, row)


def test_joseph_successor_changes_only_its_exact_wording_hash():
    assert set(LABELS) == set(PRE_JOSEPH_LABELS)
    assert [site for site in LABELS if LABELS[site] != PRE_JOSEPH_LABELS[site]] == [JOSEPH_SITE]
    recovered = deepcopy(LABELS)
    recovered[JOSEPH_SITE]["target_sha256"] = JOSEPH_TARGET_BEFORE
    assert recovered == PRE_JOSEPH_LABELS
    assert canonical_hash(verse(JOSEPH_SITE)) == JOSEPH_TARGET_AFTER
    assert_label(JOSEPH_SITE, ledger()[JOSEPH_SITE])


def test_joseph_predecessor_hash_is_rejected_without_promoting_the_label():
    row, target = ledger()[JOSEPH_SITE], verse(JOSEPH_SITE)
    assert_wording_unchanged(JOSEPH_SITE, row, target)
    before = deepcopy(row)
    before["target_sha256"] = JOSEPH_TARGET_BEFORE
    rejects(assert_wording_unchanged, JOSEPH_SITE, before, target, message="unchanged wording")
    assert_wording_unchanged(JOSEPH_SITE, row, target)
    assert_label(JOSEPH_SITE, row)


def test_visitation_predecessor_hash_is_rejected_and_same_row_recovers():
    assert HISTORICAL_LABELS[VISITATION_SITE]["target_sha256"] == VISITATION_TARGET_BEFORE
    row, target = ledger()[VISITATION_SITE], verse(VISITATION_SITE)
    original = deepcopy(row)
    assert_wording_unchanged(VISITATION_SITE, row, target)
    assert canonical_hash(target) == VISITATION_TARGET_AFTER
    row["target_sha256"] = VISITATION_TARGET_BEFORE
    assert canonical_hash(row) != canonical_hash(original)
    rejects(assert_wording_unchanged, VISITATION_SITE, row, target, message="unchanged wording")
    row["target_sha256"] = VISITATION_TARGET_AFTER
    assert canonical_hash(row) == canonical_hash(original)
    assert_wording_unchanged(VISITATION_SITE, row, target)
    assert_label(VISITATION_SITE, row)


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

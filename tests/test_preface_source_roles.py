"""Bind approved-print Preface uses to their actual scope and Easter leaves."""

import hashlib
import json
from copy import deepcopy

import pytest

from build_reader import bibliography
from build_reader.bibliography_bindings import (
    BindingError,
    digest,
    selected_text,
    witness_subject,
)
from checks.collate import load_witness
from checks.layout import CORPUS

EDITION = "edition.missale-romanum.1962-typica"
ITEM = "item.missale-romanum.1962-typica.ia"
PAGES = {
    "apostolorum": 378,
    "ascensionis": 371,
    "beatae-mariae-virginis-in-annuntiatione": 376,
    "beatae-mariae-virginis-in-assumptione": 376,
    "beatae-mariae-virginis-in-conceptione-immaculata": 376,
    "beatae-mariae-virginis-in-nativitate": 376,
    "beatae-mariae-virginis-in-transfixione": 376,
    "beatae-mariae-virginis-in-visitatione": 376,
    "beatae-mariae-virginis": 376,
    "communis": 379,
    "d-n-iesu-christi-regis": 373,
    "defunctorum": 380,
    "nativitatis": 365,
    "paschalis-in-die": 315,
    "paschalis-in-nocte": 315,
    "quadragesimae": 367,
    "sacratissimi-cordis-iesu": 372,
    "sanctae-crucis": 368,
    "sancti-ioseph-in-festivitate": 377,
    "sancti-ioseph-in-solemnitate": 377,
    "sanctissimae-trinitatis": 375,
    "spiritus-sancti": 374,
}
EASTER = ("paschalis-in-die", "paschalis-in-nocte")
APPLICATIONS = {
    "beatae-mariae-virginis-in-annuntiatione": "Annuntiatione",
    "beatae-mariae-virginis-in-assumptione": "Assumptione",
    "beatae-mariae-virginis-in-conceptione-immaculata": "Conceptione immaculata",
    "beatae-mariae-virginis-in-nativitate": "Nativitate",
    "beatae-mariae-virginis-in-transfixione": "Transfixione",
    "beatae-mariae-virginis-in-visitatione": "Visitatione",
    "beatae-mariae-virginis": "Festivitate",
    "sancti-ioseph-in-festivitate": "March 19 Festivitate",
    "sancti-ioseph-in-solemnitate": "May 1 Solemnitate",
}
N315 = "f08888fa336219d986f3e2ad9d01c10c8f809b95748f7280dc5e2b5e2c91ad5f"
N316 = "63022b76b0fb2fc62a65e467bd823ac303c71a13d43a6c3f27edd67b3d3f075e"
OLD_REASON = (
    "Locator corrected against the page image: the text is printed on the leaves now "
    "cited, from its opening to its end."
)
SELECTED = {
    "paschalis-in-die": "66ff4a7e965779b1be3bb7af0fff38174b453490a025a89c692d97b6625f5061",
    "paschalis-in-nocte": "2f7b01796bfff2a65ec4898d862338583588fdba78aa541b523e0ced8222e960",
}
BODIES = {
    "paschalis-in-die": "9eb5ddba307b7e50971e16f1d3d37e17a141b83f69291ee413fc51dc221a384e",
    "paschalis-in-nocte": "412a0064b18925851660dcd9e83262df7bac6339ec953dca4fb74c8563d3d315",
}
READINGS = {
    "paschalis-in-die": "1e3bea14f79bf014a8a99ddd7174dd8e4a15bd043f6990cbc0aca1745474fc5a",
    "paschalis-in-nocte": "85c9ad9e2d31aadb026d7c139a608a4f407a294202555ef1a4b9b7493c906bf7",
}
PROTECTED = {
    # Covers all Epiphany graph records, incl. the hand-rubric claim (lower-case præfationis).
    "epiphaniae": "0ca5659aa28670e3fbc1d86c9caaad4a4aeb2de76a7f19478d7ef884b85ca67a",
    "dialogus": "51dca28f78ac069bd61013ab1820537ed44c187853d57caf30916b7c1017a939",
}


def tid(slug):
    return "ordinarium.praefatio-" + slug


def graph():
    return json.loads((CORPUS / "bibliography/graph.json").read_text())


def core(slug):
    return json.loads((CORPUS / "texts/ordinarium" / f"praefatio-{slug}.json").read_text())


def use(data, slug, suffix="mr1962"):
    return next(u for u in data["uses"] if u["id"] == f"use.{tid(slug)}.{suffix}")


def mr(data, slug):
    return next(w for w in data["witnesses"] if w["id"] == f"witness.{tid(slug)}.mr1962")


def check_primary(data, slug):
    value = use(data, slug)
    assert value["role"] == "direct_approved_print"
    assert value["edition"] == EDITION and value["digital_item"] == ITEM
    assert value["decision"] == "RETAIN_WITH_CORRECTION"
    assert value["address"] == {"kind": "text", "text": tid(slug)}
    date = "2026-08-31"
    if slug in {"ascensionis", "nativitatis", "quadragesimae", "spiritus-sancti"}:
        date = "2026-09-12"
    if slug in {*EASTER, "communis", "sacratissimi-cordis-iesu"}:
        date = "2026-09-25"
    assert value["verified_on"] == date
    if slug in {*EASTER, "sacratissimi-cordis-iesu"}:
        assert OLD_REASON in value["decision_reason"]
    leaf = PAGES[slug]
    assert value["locator"] == {
        "printed": f"p. {leaf - 79}",
        "scan": f"leaf n{leaf} / PDF p. {leaf + 1}",
        "page_url": f"https://archive.org/details/missale-romanum-1962/page/n{leaf}/mode/1up",
    }
    claim = value["claim"]
    assert "approved Benziger printing" in claim
    if slug not in EASTER:
        assert "imported hand-position rubric is outside this use" in claim
        assert "complete 1962 liturgical component" not in claim
    else:
        assert "hand-position rubric" not in claim
        assert "w001-w020" in claim and "continues on p. 237" in claim
        assert value["evidence_sha256"] == N315
        choice = "in hac potissimum die" if slug.endswith("-die") else "in hac potissimum nocte"
        assert choice in claim
    if slug in APPLICATIONS:
        assert "same-page" in claim and APPLICATIONS[slug] in claim
    if slug == "sanctissimae-trinitatis":
        assert "semper ut ubique" in claim and "selected et" in claim


def check_easter(data, slug, doc):
    check_primary(data, slug)
    continuation = use(data, slug, "mr1962-p237")
    assert continuation["edition"] == EDITION and continuation["digital_item"] == ITEM
    assert continuation["role"] == "direct_approved_print"
    assert continuation["address"] == {"kind": "word", "text": tid(slug), "word": "w021"}
    assert continuation["locator"] == {
        "printed": "p. 237",
        "scan": "leaf n316 / PDF p. 317",
        "page_url": "https://archive.org/details/missale-romanum-1962/page/n316/mode/1up",
    }
    assert continuation["evidence_sha256"] == N316
    assert continuation["verified_on"] == "2026-10-04"
    assert continuation["decision"] == "RETAIN"
    assert "w021-w066" in continuation["claim"]
    assert "following Sanctus and Infra Actionem directions are outside" in continuation["claim"]
    witness = mr(data, slug)
    assert witness["source_dependencies"] == {"uses": [continuation["id"]], "raw_binding": None}
    assert witness["coverage"] == {"kind": "full"}
    assert witness["review"] == {"status": "pending"}
    assert not any(s["type"] == "rubric" for s in doc["segments"])
    assert digest(selected_text(doc)) == SELECTED[slug]
    words = [w for s in doc["segments"] for w in s.get("words", [])]
    assert len(words) == 66
    assert [(w["id"], w["form"]) for w in (words[19], words[20], words[-1])] == [
        ("w020", "prædicáre"),
        ("w021", "cum"),
        ("w066", "dicéntes"),
    ]


def check_protected(data, slug):
    records = {
        key: [r for r in data[key] if r.get("text", r.get("address", {}).get("text")) == tid(slug)]
        for key in ("uses", "witnesses", "collations")
    }
    assert digest(records) == PROTECTED[slug]


def check_readings(data, slug):
    without_rulings = deepcopy(data)
    for entry in without_rulings["adjudicated"]:
        entry.pop("ruling")
    assert digest(without_rulings) == READINGS[slug]
    assert data["summary"] == {
        "entries": 6,
        "classes": ["capital-accent", "orthography", "punctuation"],
    }
    for entry in data["adjudicated"]:
        if entry["at"] == "w048":
            assert entry["ruling"] == (
                "The lexical accent is restored in the working text under the edition's house "
                "convention; the witness's capital typography is recorded exactly."
            )
        else:
            assert entry["ruling"].startswith("The approved Benziger printing's ")


@pytest.mark.parametrize("slug", PAGES)
def test_preface_approved_print_role_and_bounded_scope(slug):
    check_primary(graph(), slug)


def test_preface_body_rubric_population_is_nonuniform():
    assert len(PAGES) == 22 and len(APPLICATIONS) == 9
    rubrics = {slug: [s for s in core(slug)["segments"] if s["type"] == "rubric"] for slug in PAGES}
    assert sum(len(value) for value in rubrics.values()) == 20
    assert {slug for slug, value in rubrics.items() if not value} == set(EASTER)
    assert all(value[0]["id"] == "s01" for value in rubrics.values() if value)
    assert all("disiungit manus" in value[0]["text"] for value in rubrics.values() if value)


@pytest.mark.parametrize("slug", EASTER)
def test_easter_both_actual_leaves_form_the_explicit_binding(slug):
    data, doc = graph(), core(slug)
    check_easter(data, slug, doc)
    subject = witness_subject(CORPUS, mr(data, slug), data, doc)
    assert set(subject["source_uses"]) == {
        f"use.{tid(slug)}.mr1962",
        f"use.{tid(slug)}.mr1962-p237",
    }
    assert subject["raw_resolution"] is None
    witnesses = [w for w in data["witnesses"] if w["text"] == tid(slug)]
    assert len(witnesses) == 2 and all(w["review"] == {"status": "pending"} for w in witnesses)
    collation = next(c for c in data["collations"] if c["text"] == tid(slug))
    assert collation["review"] == {"status": "pending"}
    projected = next(
        r for r in bibliography.public_text_evidence(data)["texts"] if r["id"] == tid(slug)
    )
    assert projected["witnesses"] == [] and "collation" not in projected


@pytest.mark.parametrize("slug", EASTER)
def test_easter_metadata_changes_do_not_rewrite_raw_body_or_readings(slug):
    folder = CORPUS / "witnesses" / tid(slug)
    meta, body = load_witness(folder / "mr.txt")
    assert hashlib.sha256(body.encode()).hexdigest() == BODIES[slug]
    assert "Editio iuxta typicam, Benziger Brothers, New York, 1962" in meta["description"]
    assert "w001-w020" in meta["boundary"] and "w021-w066" in meta["boundary"]
    assert "following Sanctus and Infra Actionem" in meta["boundary"]
    assert meta["transcribed"].startswith("2026-09-12")
    assert "source" in meta and meta["source"].endswith("missale-romanum-1962")
    assert "typical-edition" not in core(slug)["editorial"]["source"]["method"]
    check_readings(json.loads((folder / "apparatus.json").read_text()), slug)


@pytest.mark.parametrize("slug", PROTECTED)
def test_other_preface_source_units_remain_separate(slug):
    check_protected(graph(), slug)


@pytest.mark.parametrize("slug", PAGES)
def test_role_mutations_are_rejected_at_every_known_site(slug):
    data = graph()
    use(data, slug)["role"] = "official_text"
    with pytest.raises(AssertionError):
        check_primary(data, slug)


@pytest.mark.parametrize("slug", [s for s in PAGES if s not in EASTER])
def test_whole_component_scope_mutations_are_rejected(slug):
    data = graph()
    use(data, slug)["claim"] = (
        "The approved Benziger printing supplies the complete selected component."
    )
    with pytest.raises(AssertionError):
        check_primary(data, slug)


@pytest.mark.parametrize("slug", APPLICATIONS)
def test_shared_page_application_mutations_are_rejected(slug):
    data = graph()
    use(data, slug)["claim"] = use(data, slug)["claim"].replace(APPLICATIONS[slug], "Veneratione")
    with pytest.raises(AssertionError):
        check_primary(data, slug)


EASTER_MUTATIONS = (
    "combined-opening-locator",
    "missing-continuation",
    "missing-inventory",
    "empty-inventory",
    "wrong-hash",
    "wrong-printed",
    "wrong-scan",
    "wrong-url",
    "other-edition",
    "other-item",
    "unknown-word",
    "primary-repeated",
    "raw-invention",
    "renew-old-date",
    "renew-new-date",
    "reviewed",
    "partial-coverage",
    "wrong-continuation-role",
    "wrong-opening-hash",
    "imported-rubric-claim",
    "extra-dependency",
    "changed-latin",
    "added-ritual",
)


def mutate_easter(data, doc, slug, mutation):
    primary, continuation, witness = use(data, slug), use(data, slug, "mr1962-p237"), mr(data, slug)
    if mutation == "combined-opening-locator":
        primary["locator"]["printed"] = "pp. 236–237"
    elif mutation == "missing-continuation":
        data["uses"].remove(continuation)
    elif mutation == "missing-inventory":
        witness.pop("source_dependencies")
    elif mutation == "empty-inventory":
        witness["source_dependencies"]["uses"] = []
    elif mutation == "wrong-hash":
        continuation["evidence_sha256"] = N315
    elif mutation == "wrong-printed":
        continuation["locator"]["printed"] = "p. 291"
    elif mutation == "wrong-scan":
        continuation["locator"]["scan"] = "leaf n370 / PDF p. 371"
    elif mutation == "wrong-url":
        continuation["locator"]["page_url"] = primary["locator"]["page_url"]
    elif mutation == "other-edition":
        continuation["edition"] = "edition.divinum-officium-missa.44667ff"
        continuation["digital_item"] = "item.divinum-officium-missa.44667ff.github"
    elif mutation == "other-item":
        continuation["digital_item"] = "item.divinum-officium-missa.44667ff.github"
    elif mutation == "unknown-word":
        continuation["address"]["word"] = "w999"
    elif mutation == "primary-repeated":
        witness["source_dependencies"]["uses"].append(primary["id"])
    elif mutation == "raw-invention":
        witness["source_dependencies"]["raw_binding"] = "easter-preface"
    elif mutation == "renew-old-date":
        primary["verified_on"] = "2026-10-04"
    elif mutation == "renew-new-date":
        continuation["verified_on"] = "2026-09-25"
    elif mutation == "reviewed":
        witness["review"] = {"status": "reviewed", "sha256": "0" * 64}
    elif mutation == "partial-coverage":
        witness["coverage"] = {"kind": "words", "words": ["w021"]}
    elif mutation == "wrong-continuation-role":
        continuation["role"] = "official_text"
    elif mutation == "wrong-opening-hash":
        primary["evidence_sha256"] = N316
    elif mutation == "imported-rubric-claim":
        primary["claim"] += " It also supplies the hand-position rubric."
    elif mutation == "extra-dependency":
        witness["source_dependencies"]["uses"].append(f"use.{tid(slug)}.mr1962-p291")
    elif mutation == "changed-latin":
        doc["segments"][0]["words"][20]["form"] = "dum"
    elif mutation == "added-ritual":
        doc["segments"].append({"id": "s99", "type": "rubric", "text": "Deinde disiungit manus."})
    else:
        raise AssertionError(mutation)


@pytest.mark.parametrize("slug", EASTER)
@pytest.mark.parametrize("mutation", EASTER_MUTATIONS)
def test_easter_scope_and_identity_mutations_are_rejected(slug, mutation):
    data, doc = graph(), core(slug)
    mutate_easter(data, doc, slug, mutation)
    with pytest.raises((AssertionError, KeyError, StopIteration)):
        check_easter(data, slug, doc)


@pytest.mark.parametrize("slug", EASTER)
@pytest.mark.parametrize(
    "mutation,expected",
    [
        ("missing-continuation", "unknown source use"),
        ("missing-inventory", "complete explicit"),
        ("other-edition", "another edition"),
        ("unknown-word", "unknown word"),
        ("primary-repeated", "excluding the primary"),
        ("raw-invention", "declared raw binding differs"),
    ],
)
def test_easter_dependency_mutations_fail_the_binding_contract(slug, mutation, expected):
    data, doc = graph(), core(slug)
    mutate_easter(data, doc, slug, mutation)
    with pytest.raises(BindingError, match=expected):
        witness_subject(CORPUS, mr(data, slug), data, doc)


@pytest.mark.parametrize("slug", PROTECTED)
def test_unrelated_preface_mutations_are_not_absorbed(slug):
    data = graph()
    use(data, slug)["claim"] += " Changed."
    with pytest.raises(AssertionError):
        check_protected(data, slug)


@pytest.mark.parametrize("slug", EASTER)
@pytest.mark.parametrize("mutation", ("ours", "witness", "class", "ruling"))
def test_easter_apparatus_mutations_are_rejected(slug, mutation):
    data = json.loads((CORPUS / "witnesses" / tid(slug) / "apparatus.json").read_text())
    entry = data["adjudicated"][0]
    if mutation == "ours":
        entry["ours"] = "justum"
    elif mutation == "witness":
        entry["witnesses"]["do"] = "iustum"
    elif mutation == "class":
        entry["class"] = "substantive"
    else:
        entry["ruling"] = entry["ruling"].replace("approved Benziger printing", "typical edition")
    with pytest.raises(AssertionError):
        check_readings(data, slug)

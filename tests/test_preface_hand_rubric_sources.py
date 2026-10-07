"""Keep the Preface hand rubric separate from its prayer-body witnesses."""

import json
from copy import deepcopy

import pytest

from build_reader import bibliography
from build_reader.bibliography_bindings import BindingError, witness_subject
from checks.layout import CORPUS

SLUGS = (
    "apostolorum",
    "ascensionis",
    "beatae-mariae-virginis",
    "beatae-mariae-virginis-in-annuntiatione",
    "beatae-mariae-virginis-in-assumptione",
    "beatae-mariae-virginis-in-conceptione-immaculata",
    "beatae-mariae-virginis-in-nativitate",
    "beatae-mariae-virginis-in-transfixione",
    "beatae-mariae-virginis-in-visitatione",
    "communis",
    "d-n-iesu-christi-regis",
    "defunctorum",
    "epiphaniae",
    "nativitatis",
    "quadragesimae",
    "sacratissimi-cordis-iesu",
    "sanctae-crucis",
    "sancti-ioseph-in-festivitate",
    "sancti-ioseph-in-solemnitate",
    "sanctissimae-trinitatis",
    "spiritus-sancti",
)
EASTER = ("paschalis-in-die", "paschalis-in-nocte")
EDITION = "edition.missale-romanum.1962-typica"
ITEM = "item.missale-romanum.1962-typica.ia"
SUFFIX = ".hand-position-rubric.mr1962"
PAGE_HASH = "c8e1c105fbccab5b133d072bcdc255ff482824182be5e53597e5d2bfbb94e3ee"
RUBRIC = (
    "Deinde disiungit manus, et disiunctas tenet usque ad finem præfationis: "
    "qua finita, iterum iungit eas, et inclinatus dicit: Sanctus."
)


def tid(slug):
    return f"ordinarium.praefatio-{slug}"


def uid(slug):
    return f"use.{tid(slug)}{SUFFIX}"


def graph():
    return json.loads((CORPUS / "bibliography/graph.json").read_text())


def core(slug):
    return json.loads((CORPUS / "texts/ordinarium" / f"praefatio-{slug}.json").read_text())


def expected_use(slug):
    claim = (
        "The approved Benziger printing's Ordo Missae prints the hand-position "
        "rubric selected in s01, from Deinde disiungit manus through et inclinatus "
        "dicit: Sanctus. The following Benedictus sign-of-the-cross direction and "
        "the preceding dialogue directions are outside this use. This is ritual "
        "support for s01, not a body-text witness or proof of the corpus's historical "
        "import workflow. "
    )
    claim += "The selected rubric retains the printed lower-case præfationis."
    return {
        "id": uid(slug),
        "edition": EDITION,
        "digital_item": ITEM,
        "role": "rubric_control",
        "address": {"kind": "segment", "text": tid(slug), "segment": "s01"},
        "locator": {
            "printed": "p. 225",
            "scan": "leaf n304 / PDF p. 305",
            "section": (
                "Ordo Missae, lower-right final paragraph: Deinde disiungit manus through "
                "Sanctus; excluding Et cum dicit: Benedictus qui venit"
            ),
            "page_url": "https://archive.org/details/missale-romanum-1962/page/n304/mode/1up",
        },
        "claim": claim,
        "verified_on": "2026-10-04" if slug == "communis" else "2026-10-07",
        "decision": "RETAIN",
        "evidence_sha256": PAGE_HASH,
    }


def check_use(data, slug):
    matches = [u for u in data["uses"] if u["id"] == uid(slug)]
    assert matches == [expected_use(slug)]


def check_population(data, documents):
    assert len(SLUGS) == 21 and len(EASTER) == 2
    assert set(documents) == {tid(s) for s in (*SLUGS, *EASTER)}
    rubric_ids = set()
    for slug in (*SLUGS, *EASTER):
        rubrics = [s for s in documents[tid(slug)]["segments"] if s["type"] == "rubric"]
        if slug in EASTER:
            assert not rubrics
        else:
            assert rubrics == [{"id": "s01", "type": "rubric", "text": RUBRIC}]
            rubric_ids.add(tid(slug))
    uses = [u for u in data["uses"] if u["id"].endswith(SUFFIX)]
    assert len(uses) == 21
    assert {u["address"]["text"] for u in uses} == rubric_ids
    assert {u["id"] for u in uses} == {uid(s) for s in SLUGS}


def epiphany_inventory():
    return {
        "uses": [
            uid("epiphaniae"),
            f"use.{tid('epiphaniae')}.sung-continuation.mr1962",
            f"use.{tid('epiphaniae')}.sung-opening.mr1962",
        ],
        "raw_binding": None,
    }


def check_dependencies(data):
    ids = {tid(s) for s in SLUGS}
    witnesses = [w for w in data["witnesses"] if w["text"] in ids]
    collations = [c for c in data["collations"] if c["text"] in ids]
    assert len(witnesses) == 40 and len(collations) == 20
    assert all(r["review"] == {"status": "pending"} for r in witnesses + collations)
    assert not any(r["text"] == tid("communis") for r in witnesses + collations)
    unknown = []
    for witness in witnesses:
        if witness["transcription"] != "mr":
            assert not any(
                name.endswith(SUFFIX)
                for name in witness.get("source_dependencies", {}).get("uses", [])
            )
        elif witness["text"] == tid("epiphaniae"):
            assert witness["source_dependencies"] == epiphany_inventory()
        else:
            assert "source_dependencies" not in witness
            unknown.append(witness["text"])
    assert len(unknown) == 19


@pytest.mark.parametrize("slug", SLUGS)
def test_preface_rubric_has_its_own_exact_printed_source(slug):
    check_use(graph(), slug)


def test_hand_rubric_population_excludes_both_easter_bodies():
    documents = {
        doc["id"]: doc
        for path in (CORPUS / "texts/ordinarium").glob("praefatio-*.json")
        if path.stem != "praefatio-dialogus"
        for doc in [json.loads(path.read_text())]
    }
    check_population(graph(), documents)


def test_rubric_sources_do_not_complete_unknown_inventories_or_create_reviews():
    check_dependencies(graph())


def test_epiphany_rubric_is_additive_to_both_sung_page_dependencies():
    data = graph()
    witness = next(w for w in data["witnesses"] if w["id"] == f"witness.{tid('epiphaniae')}.mr1962")
    subject = witness_subject(CORPUS, witness, data, core("epiphaniae"))
    assert set(subject["source_uses"]) == {witness["use"], *epiphany_inventory()["uses"]}
    assert all(s["edition"]["id"] == EDITION for s in subject["source_uses"].values())
    assert subject["raw_resolution"] is None
    assert witness["review"] == {"status": "pending"}


@pytest.mark.parametrize("slug", SLUGS)
def test_rubric_projection_remains_context_not_a_latin_witness(slug):
    row = next(
        r for r in bibliography.public_text_evidence(graph())["texts"] if r["id"] == tid(slug)
    )
    matching = [g for g in row["source_groups"] if any(e["id"] == uid(slug) for e in g["entries"])]
    assert len(matching) == 1
    group = matching[0]
    assert group["role"] == "rubric_control" and group["edition"] == EDITION
    assert group["entries"] == [
        {
            "id": uid(slug),
            "address": {"kind": "segment", "segment": "s01"},
            "claim": expected_use(slug)["claim"],
        }
    ]
    assert row["witnesses"] == [] and "collation" not in row
    assert not any(k in group for k in ("evidence_sha256", "decision", "source_dependencies"))
    body = next(u for u in graph()["uses"] if u["id"] == f"use.{tid(slug)}.mr1962")
    assert body["role"] == "direct_approved_print" and "rubric" in body["claim"]


@pytest.mark.parametrize("slug", SLUGS)
def test_missing_rubric_source_is_rejected_at_every_consumer(slug):
    data = graph()
    data["uses"] = [u for u in data["uses"] if u["id"] != uid(slug)]
    with pytest.raises(AssertionError):
        check_use(data, slug)


@pytest.mark.parametrize(
    "mutation",
    (
        "wrong-hash",
        "wrong-page",
        "wrong-role",
        "wrong-text",
        "wrong-segment",
        "different-edition",
        "different-item",
        "overbroad-claim",
        "renewed-date",
        "rejected-use",
        "common-capitalization",
    ),
)
def test_source_claim_mutations_are_rejected(mutation):
    data = graph()
    slug = "communis" if mutation == "common-capitalization" else "epiphaniae"
    value = next(u for u in data["uses"] if u["id"] == uid(slug))
    if mutation == "wrong-hash":
        value["evidence_sha256"] = "0" * 64
    elif mutation == "wrong-page":
        value["locator"]["scan"] = "leaf n305 / PDF p. 306"
    elif mutation == "wrong-role":
        value["role"] = "direct_approved_print"
    elif mutation == "wrong-text":
        value["address"]["text"] = tid("communis")
    elif mutation == "wrong-segment":
        value["address"]["segment"] = "s02"
    elif mutation == "different-edition":
        value["edition"] = "edition.divinum-officium-missa.44667ff"
    elif mutation == "different-item":
        value["digital_item"] = "item.divinum-officium-missa.44667ff.github"
    elif mutation == "overbroad-claim":
        value["claim"] = "The page proves the full prayer and its historical import workflow."
    elif mutation == "renewed-date":
        value["verified_on"] = "2026-09-25"
    elif mutation == "rejected-use":
        value["decision"] = "REMOVE"
    else:
        value["claim"] = value["claim"].replace(
            "retains the printed lower-case præfationis.",
            "capitalizes Præfationis; the print has lower-case præfationis.",
        )
    with pytest.raises(AssertionError):
        check_use(data, slug)


@pytest.mark.parametrize(
    "mutation",
    (
        "drop-sung",
        "omit-rubric",
        "raw-invention",
        "complete-unknown",
        "common-witness",
        "common-collation",
        "approved-witness",
        "approved-collation",
        "do-dependency",
    ),
)
def test_dependency_and_pending_gap_mutations_are_rejected(mutation):
    data = graph()
    witness = next(w for w in data["witnesses"] if w["id"] == f"witness.{tid('epiphaniae')}.mr1962")
    if mutation == "drop-sung":
        witness["source_dependencies"]["uses"] = [uid("epiphaniae")]
    elif mutation == "omit-rubric":
        witness["source_dependencies"]["uses"].remove(uid("epiphaniae"))
    elif mutation == "raw-invention":
        witness["source_dependencies"]["raw_binding"] = "preface-rubric"
    elif mutation == "complete-unknown":
        unknown = next(
            w for w in data["witnesses"] if w["id"] == f"witness.{tid('apostolorum')}.mr1962"
        )
        unknown["source_dependencies"] = {"uses": [], "raw_binding": None}
    elif mutation == "common-witness":
        added = deepcopy(witness)
        added["text"] = tid("communis")
        data["witnesses"].append(added)
    elif mutation == "common-collation":
        added = deepcopy(next(c for c in data["collations"] if c["text"] == tid("epiphaniae")))
        added["text"] = tid("communis")
        data["collations"].append(added)
    elif mutation == "approved-witness":
        witness["review"] = {"status": "reviewed", "sha256": "0" * 64}
    elif mutation == "approved-collation":
        next(c for c in data["collations"] if c["text"] == tid("epiphaniae"))["review"] = {
            "status": "reviewed"
        }
    else:
        digital = next(
            w
            for w in data["witnesses"]
            if w["text"] == tid("epiphaniae") and w["transcription"] == "do"
        )
        digital["source_dependencies"] = {"uses": [uid("epiphaniae")], "raw_binding": None}
    with pytest.raises(AssertionError):
        check_dependencies(data)


@pytest.mark.parametrize("slug", EASTER)
def test_easter_verse_must_not_acquire_a_rubric_source(slug):
    data = graph()
    data["uses"].append(expected_use(slug))
    data["uses"].sort(key=lambda use: use["id"])
    documents = {tid(s): core(s) for s in (*SLUGS, *EASTER)}
    with pytest.raises(AssertionError):
        check_population(data, documents)


def test_cross_edition_rubric_dependency_fails_the_actual_binding_contract():
    data = graph()
    value = next(u for u in data["uses"] if u["id"] == uid("epiphaniae"))
    value["edition"] = "edition.divinum-officium-missa.44667ff"
    value["digital_item"] = "item.divinum-officium-missa.44667ff.github"
    witness = next(w for w in data["witnesses"] if w["id"] == f"witness.{tid('epiphaniae')}.mr1962")
    with pytest.raises(BindingError, match="another edition"):
        witness_subject(CORPUS, witness, data, core("epiphaniae"))

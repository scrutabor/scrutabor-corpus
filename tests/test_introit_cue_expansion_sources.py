"""Five Introits whose proper pages give the Gloria Patri and the repeat only as cues.

The approved Benziger printing prints the antiphon and psalm verse of the Introits of
St Michael (p. 684), the Twentieth Sunday after Pentecost (p. 407), Sts Peter and Paul
(p. 576), St Anne (p. 613) and All Saints (p. 718), then only ℣. Glória Patri. and a cue
for the repeated antiphon. Their controlling witnesses are described as the Third Sunday
of Lent's is: the full doxology comes from the Ordo Missae on p. 219, whose semper: the
selected text gives with the house comma, and the repetition from Rubricae generales 427
on p. xxix. Each transcript declares both expansions. A copy damaged in any one of these
facts fails that fact's own check, and the Lent III record passes the same checks.
"""

from copy import deepcopy
from functools import cache
from pathlib import Path

import pytest

from build_reader import bibliography
from build_reader.bibliography_bindings import text_document, witness_subject

ROOT = Path(__file__).resolve().parents[1]
EDITION = "edition.missale-romanum.1962-typica"
ITEM = "item.missale-romanum.1962-typica.ia"
PROFILE = "page-body-with-declared-house-expansion"
BASIS = (
    "Direct comparison with the identified Benziger 1962 proper page, with any separately "
    "declared printed formula/rubric expansions; historical preparation remains distinct "
    "from pending source review."
)
CLAIM = (
    "The cited proper passage prints this Introit’s antiphon and psalm verse, with "
    "abbreviated cues for the Gloria Patri and the repeated antiphon. The reader supplies "
    "the common doxology and the antiphon’s repetition in full. Those expansions are not "
    "printed in full at this locus."
)
GENERIC_CLAIM = (
    "The cited page image prints and identifies the complete 1962 liturgical component "
    "selected here; shared expansions are bounded in the witness record."
)
DOXOLOGY = (
    "The full Gloria Patri through Amen supplies words {first}–{last} after the "
    "proper's cue; the Ordo prints semper: where the selected text has the house comma."
)
EXPANSION = (
    "RG 427 prescribes antiphon, psalm, Gloria Patri and repeated antiphon; it supports "
    "this expansion of the printed cues."
)
REASON = (
    "Bounded directly read evidence from the approved Benziger printing; no witness or "
    "collation review is promoted."
)
ORDO = {
    "printed": "p. 219",
    "scan": "leaf n298 / PDF p. 299",
    "section": "Ordo Missae: Gloria Patri",
    "page_url": "https://archive.org/details/missale-romanum-1962/page/n298/mode/1up",
}
RUBRICS = {
    "printed": "p. xxix",
    "scan": "leaf n34 / PDF p. 35",
    "section": "Rubricae generales 427",
    "page_url": "https://archive.org/details/missale-romanum-1962/page/n34/mode/1up",
}
ORDO_IMAGE = "ee8d1c45f6cc759518ae59a1dd047dfa80033904ba5ce1799fbaa2334df9ee55"
RUBRICS_IMAGE = "7f1d0a363ab6d032183595433acb393de3e473dc34e95135467e0c7c1d5c9786"
GLORIA = (
    "Glória Patri, et Fílio, et Spirítui Sancto. Sicut erat in princípio, et nunc, et "
    "semper, et in sǽcula sæculórum. Amen."
)
ORTHOGRAPHY = (
    "# orthography: printed proper body with explicitly declared house-expanded formula; "
    "not a diplomatic full-page transcript"
)
NOTE = (
    "# note: the page prints the Gloria Patri and the repeated antiphon as cues only "
    "(℣. Glória Patri. {cue}); {g1}–{g2} expand the Gloria Patri from the Ordo, p. 219, "
    "leaf n298, with the house comma after semper where the Ordo prints semper:, and "
    "{r1}–{r2} repeat the antiphon under RG 427, p. xxix, leaf n34"
)
# slug, printed cue, first and last word of the Gloria Patri, first and last of the repeat
CASES = {
    "michael": (
        "dedicatio-sancti-michaelis-archangeli-introitus",
        "Benedícite.",
        ("w030", "w049", "w050", "w065"),
    ),
    "pentecost-xx": (
        "dominica-xx-post-pentecosten-introitus",
        "Omnia.",
        ("w039", "w058", "w059", "w087"),
    ),
    "all-saints": (
        "omnium-sanctorum-introitus",
        "Gaudeámus omnes.",
        ("w028", "w047", "w048", "w067"),
    ),
    "st-anne": (
        "sanctae-annae-matris-beatae-mariae-virginis-introitus",
        "Gaudeámus.",
        ("w031", "w050", "w051", "w070"),
    ),
    "peter-and-paul": (
        "sancti-petri-et-pauli-apostolorum-introitus",
        "Nunc scio.",
        ("w034", "w053", "w054", "w073"),
    ),
    "lent-iii-control": (
        "dominica-iii-in-quadragesima-introitus",
        "Oculi.",
        ("w038", "w057", "w058", "w081"),
    ),
}
FIVE = [key for key in CASES if key != "lent-iii-control"]


@cache
def graph() -> dict:
    return bibliography.load(ROOT)[0]


@cache
def core(key: str) -> dict:
    return text_document(ROOT, f"proprium.{CASES[key][0]}")


@cache
def transcript(key: str) -> str:
    path = ROOT / "witnesses" / f"proprium.{CASES[key][0]}" / "mr.txt"
    return path.read_text(encoding="utf-8")


def names(key: str) -> dict[str, str]:
    text = f"proprium.{CASES[key][0]}"
    return {
        "text": text,
        "witness": f"witness.{text}.mr1962",
        "primary": f"use.{text}.mr1962",
        "doxology": f"use.{text}.expanded-doxology.mr1962",
        "expansion": f"use.{text}.introit-expansion.mr1962",
    }


def records(evidence: dict, key: str) -> tuple[dict, dict, dict, dict]:
    name = names(key)
    uses = {use["id"]: use for use in evidence["uses"]}
    witnesses = {witness["id"]: witness for witness in evidence["witnesses"]}
    return (
        witnesses.get(name["witness"], {}),
        uses.get(name["primary"], {}),
        uses.get(name["doxology"], {}),
        uses.get(name["expansion"], {}),
    )


def problems(evidence: dict, key: str, doc: dict, text: str) -> list[str]:
    """Name every fact of the cue-expansion description that this copy does not state."""
    _, cue, (g1, g2, r1, r2) = CASES[key]
    name = names(key)
    witness, primary, doxology, expansion = records(evidence, key)
    found = []
    if (witness.get("orthography_profile"), witness.get("independence_basis")) != (PROFILE, BASIS):
        found.append("profile")
    inventory = {"uses": [name["doxology"], name["expansion"]], "raw_binding": None}
    if witness.get("source_dependencies") != inventory:
        found.append("inventory")
    address = {"kind": "text", "text": name["text"]}
    if (primary.get("claim"), primary.get("role"), primary.get("address")) != (
        CLAIM,
        "official_text",
        address,
    ):
        found.append("claim")
    common = {"edition": EDITION, "digital_item": ITEM, "decision": "RETAIN"}
    if {field: doxology.get(field) for field in (*common, "decision_reason")} != {
        **common,
        "decision_reason": REASON,
    } or (
        doxology.get("role"),
        doxology.get("address"),
        doxology.get("locator"),
        doxology.get("evidence_sha256"),
        doxology.get("claim"),
    ) != (
        "official_text",
        {"kind": "segment", "text": name["text"], "segment": "s01"},
        ORDO,
        ORDO_IMAGE,
        DOXOLOGY.format(first=g1, last=g2),
    ):
        found.append("doxology")
    if {field: expansion.get(field) for field in (*common, "decision_reason")} != {
        **common,
        "decision_reason": REASON,
    } or (
        expansion.get("role"),
        expansion.get("address"),
        expansion.get("locator"),
        expansion.get("evidence_sha256"),
        expansion.get("claim"),
    ) != ("rubric_control", address, RUBRICS, RUBRICS_IMAGE, EXPANSION):
        found.append("expansion")
    words = [word for segment in doc["segments"] for word in segment.get("words", [])]
    order = [word["id"] for word in words]
    shown = [word.get("pre", "") + word["form"] + word.get("post", "") for word in words]
    if any(identifier not in order for identifier in (g1, g2, r1, r2)) or (
        " ".join(shown[order.index(g1) : order.index(g2) + 1]) != GLORIA
        or order.index(r1) != order.index(g2) + 1
        or order[-1] != r2
        or shown[order.index(r1) :] != shown[: len(order) - order.index(r1)]
    ):
        found.append("ranges")
    lines = text.splitlines()
    note = NOTE.format(cue=cue, g1=g1, g2=g2, r1=r1, r2=r2)
    if [line for line in lines if line.startswith("# orthography:")] != [ORTHOGRAPHY] or (
        lines.count(note) != 1
    ):
        found.append("declaration")
    return found


def damage_profile(evidence: dict, doc: dict, text: str, key: str) -> str:
    records(evidence, key)[0]["orthography_profile"] = "exact-page-image"
    return text


def damage_inventory(evidence: dict, doc: dict, text: str, key: str) -> str:
    records(evidence, key)[0]["source_dependencies"]["uses"].pop()
    return text


def damage_claim(evidence: dict, doc: dict, text: str, key: str) -> str:
    records(evidence, key)[1]["claim"] = GENERIC_CLAIM
    return text


def damage_doxology(evidence: dict, doc: dict, text: str, key: str) -> str:
    _, _, (_, _, r1, r2) = CASES[key]
    records(evidence, key)[2]["claim"] = DOXOLOGY.format(first=r1, last=r2)
    return text


def damage_expansion(evidence: dict, doc: dict, text: str, key: str) -> str:
    records(evidence, key)[3]["locator"] = dict(ORDO)
    return text


def damage_ranges(evidence: dict, doc: dict, text: str, key: str) -> str:
    words = [word for segment in doc["segments"] for word in segment.get("words", [])]
    next(word for word in words if word["form"] == "semper")["post"] = ":"
    return text


def damage_declaration(evidence: dict, doc: dict, text: str, key: str) -> str:
    _, cue, (g1, g2, r1, r2) = CASES[key]
    note = NOTE.format(cue=cue, g1=g1, g2=g2, r1=r1, r2=r2)
    return "\n".join(line for line in text.splitlines() if line != note) + "\n"


DAMAGES = {
    "profile": damage_profile,
    "inventory": damage_inventory,
    "claim": damage_claim,
    "doxology": damage_doxology,
    "expansion": damage_expansion,
    "ranges": damage_ranges,
    "declaration": damage_declaration,
}


@pytest.mark.parametrize("key", list(CASES))
def test_the_cue_expansion_is_described_as_on_the_third_sunday_of_lent(key):
    assert problems(graph(), key, core(key), transcript(key)) == []


@pytest.mark.parametrize("damage", list(DAMAGES))
@pytest.mark.parametrize("key", FIVE)
def test_a_copy_damaged_in_one_fact_fails_that_check_alone(key, damage):
    evidence, doc = deepcopy(graph()), deepcopy(core(key))
    assert problems(evidence, key, doc, transcript(key)) == []
    text = DAMAGES[damage](evidence, doc, transcript(key), key)
    assert problems(evidence, key, doc, text) == [damage]


@pytest.mark.parametrize("key", list(CASES))
def test_the_inventory_binds_the_ordo_and_rubric_pages(key):
    name = names(key)
    witness = records(graph(), key)[0]
    subject = witness_subject(ROOT, witness, graph(), core(key))
    assert subject["contract"] == "witness-review-2"
    assert set(subject["source_uses"]) == {name["primary"], name["doxology"], name["expansion"]}
    assert subject["raw_resolution"] is None
    assert witness["review"] == {"status": "pending"}


@pytest.mark.parametrize("key", FIVE)
def test_the_reader_evidence_states_the_printed_scope(key):
    name = names(key)
    evidence = bibliography.public_text_evidence(graph())
    row = next(text for text in evidence["texts"] if text["id"] == name["text"])
    entries = {entry["id"]: entry for group in row["source_groups"] for entry in group["entries"]}
    _, _, (g1, g2, _, _) = CASES[key]
    assert entries[name["primary"]] == {
        "id": name["primary"],
        "address": {"kind": "text"},
        "claim": CLAIM,
    }
    assert entries[name["doxology"]] == {
        "id": name["doxology"],
        "address": {"kind": "segment", "segment": "s01"},
        "claim": DOXOLOGY.format(first=g1, last=g2),
    }
    assert entries[name["expansion"]] == {
        "id": name["expansion"],
        "address": {"kind": "text"},
        "claim": EXPANSION,
    }
    assert row["witnesses"] == [] and "collation" not in row

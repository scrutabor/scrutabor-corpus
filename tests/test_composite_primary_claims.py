"""A proper-page citation must not claim to print supplied common text."""

from pathlib import Path

import pytest

from build_reader import bibliography

ROOT = Path(__file__).resolve().parents[1]
CLAIMS = {
    "gloria_reprise": (
        "The cited proper passage prints this Introit’s antiphon and psalm verse, "
        "with abbreviated cues for the Gloria Patri and the repeated antiphon. "
        "The reader supplies the common doxology and the antiphon’s repetition "
        "in full. Those expansions are not printed in full at this locus."
    ),
    "reprise_only": (
        "The cited proper passage prints this Introit’s antiphon and psalm verse, "
        "with a cue for the repeated antiphon. The reader supplies the repetition "
        "in full, without a Gloria Patri. The repetition is not printed in full "
        "at this locus."
    ),
    "qui_vivis": (
        "The cited page prints this Postcommunion’s proper body and the "
        "abbreviated conclusion “Qui vivis”. The full conclusion follows "
        "Rubricae generales 115 d, with reader-supplied accentuation. Amen is "
        "shown separately as a response. The proper page does not print the "
        "full conclusion or that response."
    ),
}
GROUPS = {
    "gloria_reprise": (
        "dedicatio-sancti-michaelis-archangeli-introitus",
        "dominica-i-in-quadragesima-introitus",
        "dominica-i-post-epiphaniam-introitus",
        "dominica-ii-in-quadragesima-introitus",
        "dominica-iii-in-quadragesima-introitus",
        "dominica-infra-octavam-nativitatis-introitus",
        "dominica-iv-in-quadragesima-introitus",
        "dominica-xx-post-pentecosten-introitus",
        "epiphania-domini-introitus",
        "immaculata-conceptio-introitus",
        "nativitas-domini-in-aurora-introitus",
        "nativitas-domini-in-nocte-introitus",
        "omnium-sanctorum-introitus",
        "sancta-familia-introitus",
        "sanctae-annae-matris-beatae-mariae-virginis-introitus",
        "sancti-iacobi-apostoli-introitus",
        "sancti-ioannis-apostoli-et-evangelistae-introitus",
        "sancti-petri-et-pauli-apostolorum-introitus",
        "sancti-stephani-protomartyris-introitus",
        "sanctorum-innocentium-martyrum-introitus",
        "vigilia-nativitatis-introitus",
    ),
    "reprise_only": (
        "dominica-i-passionis-introitus",
        "dominica-ii-passionis-introitus",
        "feria-v-in-cena-domini-introitus",
    ),
    "qui_vivis": ("dominica-xxii-post-pentecosten-postcommunio",),
}


@pytest.fixture(scope="module")
def sources():
    graph, _ = bibliography.load(ROOT)
    evidence = bibliography.public_text_evidence(graph)
    return graph, {record["id"]: record for record in evidence["texts"]}


@pytest.mark.parametrize(
    "family,slug", [(family, slug) for family, slugs in GROUPS.items() for slug in slugs]
)
def test_composite_primary_claim_distinguishes_printed_scope(sources, family, slug):
    graph, by_id = sources
    text_id = f"proprium.{slug}"
    use_id = f"use.{text_id}.mr1962"
    uses = [use for use in graph["uses"] if use["id"] == use_id]
    assert len(uses) == 1
    assert uses[0]["claim"] == CLAIMS[family]
    assert uses[0]["address"] == {"kind": "text", "text": text_id}
    assert uses[0]["role"] == "official_text"
    entries = [
        entry
        for group in by_id[text_id]["source_groups"]
        for entry in group["entries"]
        if entry["id"] == use_id
    ]
    assert len(entries) == 1
    assert entries[0]["claim"] == CLAIMS[family]
    assert entries[0]["address"] == {"kind": "text"}

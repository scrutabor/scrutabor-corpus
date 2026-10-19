"""Easter IV/V source identities declare their actual common dependencies."""

from pathlib import Path

import pytest

from build_reader import bibliography
from build_reader.bibliography_bindings import (
    collation_subject,
    source_dependencies,
    text_document,
    witness_subject,
)

ROOT = Path(__file__).resolve().parents[1]
PARTS = (
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


@pytest.fixture(scope="module")
def sources():
    graph, _ = bibliography.load(ROOT)
    return graph


@pytest.mark.parametrize("sunday", ["iv", "v"])
@pytest.mark.parametrize("part", PARTS)
def test_easter_source_inventories_resolve(sources, sunday, part):
    text_id = f"proprium.dominica-{sunday}-post-pascha-{part}"
    records = [row for row in sources["witnesses"] if row["text"] == text_id]
    assert {row["id"] for row in records} == {
        f"witness.{text_id}.mr1962",
        f"witness.{text_id}.do44667ff",
    }
    supplements = []
    if part == "introitus":
        supplements = ["expanded-doxology", "introit-expansion"]
    elif part in {"collecta", "secreta", "postcommunio"}:
        supplements = ["expanded-conclusion", "oration-boundaries"]
    mr = next(row for row in records if row["id"].endswith(".mr1962"))
    assert source_dependencies(mr) == {
        "uses": [f"use.{text_id}.{suffix}.mr1962" for suffix in supplements],
        "raw_binding": None,
    }
    doc = text_document(ROOT, text_id)
    subjects = {row["id"]: witness_subject(ROOT, row, sources, doc) for row in records}
    assert all(row["contract"] == "witness-review-2" for row in subjects.values())
    mr_subject = subjects[mr["id"]]
    assert set(mr_subject["source_uses"]) == {mr["use"], *source_dependencies(mr)["uses"]}
    assert mr_subject["raw_resolution"] is None
    do = next(row for row in records if row["id"].endswith(".do44667ff"))
    assert subjects[do["id"]]["raw_resolution"] is not None
    collations = [row for row in sources["collations"] if row["text"] == text_id]
    assert len(collations) == 1
    assert collation_subject(ROOT, collations[0], doc, subjects)["contract"] == "collation-review-2"

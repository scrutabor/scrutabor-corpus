"""Composite witnesses bind their common wording and rubric dependencies."""

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
CASES = (
    ("immaculata-conceptio-introitus", ("expanded-doxology", "introit-expansion")),
    (
        "sancti-iacobi-apostoli-introitus",
        ("andrew-reprint", "expanded-doxology", "introit-expansion"),
    ),
    (
        "dominica-xxii-post-pentecosten-postcommunio",
        ("expanded-conclusion", "expanded-response", "oration-boundaries"),
    ),
)


@pytest.fixture(scope="module")
def sources():
    return bibliography.load(ROOT)[0]


@pytest.mark.parametrize("slug,supplements", CASES, ids=[row[0] for row in CASES])
def test_composite_source_dependencies_are_complete(sources, slug, supplements):
    text_id = f"proprium.{slug}"
    records = [row for row in sources["witnesses"] if row["text"] == text_id]
    mr = next(row for row in records if row["id"] == f"witness.{text_id}.mr1962")
    assert source_dependencies(mr) == {
        "uses": [f"use.{text_id}.{suffix}.mr1962" for suffix in supplements],
        "raw_binding": None,
    }
    if slug.endswith("introitus"):
        assert mr["orthography_profile"] == "page-body-with-declared-house-expansion"
        assert "reader comma after semper" in mr["independence_basis"]
    doc = text_document(ROOT, text_id)
    subjects = {row["id"]: witness_subject(ROOT, row, sources, doc) for row in records}
    assert all(row["contract"] == "witness-review-2" for row in subjects.values())
    bound = subjects[mr["id"]]
    assert set(bound["source_uses"]) == {mr["use"], *source_dependencies(mr)["uses"]}
    assert bound["raw_resolution"] is None
    if slug.endswith("postcommunio"):
        response = bound["source_uses"][f"use.{text_id}.expanded-response.mr1962"]["use"]
        assert response["role"] == "official_text"
        assert response["address"] == {"kind": "word", "text": text_id, "word": "w037"}
    collations = [row for row in sources["collations"] if row["text"] == text_id]
    assert len(collations) == 1
    assert collation_subject(ROOT, collations[0], doc, subjects)["contract"] == "collation-review-2"

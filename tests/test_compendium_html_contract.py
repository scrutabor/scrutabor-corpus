"""Exact Latin HTML assertions remain distinct from private-original verification."""

import copy
import json
from pathlib import Path

import pytest

from build_reader import paginated_documents, source_documents
from build_reader.bibliography import public_text_evidence
from build_reader.bibliography_bindings import transcript_digest, witness_subject

CORPUS = Path(__file__).resolve().parent.parent
FIXTURE = json.loads((Path(__file__).parent / "fixtures/compendium-html-claims.json").read_text())
CASES = [
    "orationes.actus-contritionis",
    "orationes.angele-dei",
    "orationes.anima-christi",
    "orationes.magnificat",
    "orationes.memorare",
    "orationes.symbolum-apostolorum",
    "orationes.te-deum",
]
DOCUMENT_MUTANTS = [
    "contract",
    "use",
    "digital_item",
    "sha256",
    "media_type",
    "section",
    "container_sha256",
    "reading_sha256",
    "extra",
    "missing",
    "duplicate",
    "field-type",
]
JOIN_MUTANTS = [
    "item-url",
    "item-sha",
    "item-kind",
    "item-edition",
    "work-id",
    "use-role",
    "use-address",
    "use-evidence",
    "use-claim",
    "use-locator",
    "use-edition",
    "item-scan-url",
]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@pytest.fixture
def case(tmp_path, request):
    expected = next(r for r in FIXTURE["cases"] if r["text"] == request.param)
    graph = json.loads((CORPUS / "bibliography/graph.json").read_text())
    witness = next(w for w in graph["witnesses"] if w["id"] == expected["witness_id"])
    graph["witnesses"] = [witness]
    graph["collations"] = []
    relative = "texts/" + expected["text"].replace(".", "/", 1) + ".json"
    target = tmp_path / relative
    target.parent.mkdir(parents=True)
    target.write_bytes((CORPUS / relative).read_bytes())
    doc = json.loads(target.read_text())
    relative = "witnesses/" + expected["text"] + "/compendium-2005.txt"
    transcript = tmp_path / relative
    transcript.parent.mkdir(parents=True)
    original = (CORPUS / relative).read_bytes()
    transcript.write_bytes(original)
    # Only the actual canonical core/transcript are copied, never a complete HTML original.
    assert not list(tmp_path.rglob("*.html"))
    yield tmp_path, graph, witness, doc, transcript, expected
    assert (CORPUS / relative).read_bytes() == original


def subject(case):
    root, graph, witness, doc, _, _ = case
    return witness_subject(root, witness, graph, doc)


def test_fixture_names_exactly_seven_witnesses_and_no_sub_tuum_upgrade():
    assert [row["text"] for row in FIXTURE["cases"]] == CASES
    assert sum(len(row["words"]) for row in FIXTURE["cases"]) == 460
    assert all(row["text"] != "orationes.sub-tuum-praesidium" for row in FIXTURE["cases"])
    assert FIXTURE["identity_assertion_not_runtime_original"] is True


@pytest.mark.parametrize("case", CASES, indirect=True)
def test_current_compendium_assertion_matches_exact_scope(case):
    _, _, witness, _, _, expected = case
    assert witness["coverage"] == expected["coverage"]
    assert witness["source_dependencies"]["documents"] == [expected["declaration"]]
    result = subject(case)
    assert result["document_resolution"] == {
        "contract": "compendium-html-identity-inventory-1",
        "documents": {expected["use"]["id"]: expected["declaration"]},
    }
    assert result["raw_resolution"] is None


@pytest.mark.parametrize("case", CASES, indirect=True)
def test_exact_literal_mutation_rejects_and_restores(case):
    _, _, witness, _, path, expected = case
    healthy = subject(case)
    before, digest = path.read_text(), witness["transcription_sha256"]
    literal = expected["reading"]
    changed = before.replace(literal, literal[0].swapcase() + literal[1:], 1)
    assert changed != before
    try:
        path.write_text(changed)
        witness["transcription_sha256"] = transcript_digest(changed)
        with pytest.raises(ValueError, match="compendium HTML literal transcript differs"):
            subject(case)
    finally:
        path.write_text(before)
        witness["transcription_sha256"] = digest
    assert subject(case) == healthy


@pytest.mark.parametrize("case", ["orationes.magnificat"], indirect=True)
@pytest.mark.parametrize("mutation", DOCUMENT_MUTANTS)
def test_declared_source_fields_reject_and_restore(case, mutation):
    _, _, witness, _, _, _ = case
    healthy = subject(case)
    documents = witness["source_dependencies"]["documents"]
    first = documents[0]
    before = copy.deepcopy(documents)
    try:
        if mutation == "extra":
            first["extra"] = "unbound"
        elif mutation == "missing":
            del first["container_sha256"]
        elif mutation == "duplicate":
            documents.append(copy.deepcopy(first))
        elif mutation == "field-type":
            first["section"] = True
        else:
            first[mutation] = "wrong"
        assert canonical(documents) != canonical(before)
        with pytest.raises(ValueError, match=r"compendium|paginated"):
            subject(case)
    finally:
        first.clear()
        first.update(before[0])
        documents[:] = [first]
    assert subject(case) == healthy


@pytest.mark.parametrize("case", ["orationes.symbolum-apostolorum"], indirect=True)
@pytest.mark.parametrize("mutation", JOIN_MUTANTS)
def test_exact_source_join_rejects_and_restores(case, mutation):
    _, graph, witness, _, _, _ = case
    healthy = subject(case)
    use = next(u for u in graph["uses"] if u["id"] == witness["use"])
    item = next(i for i in graph["digital_items"] if i["id"] == use["digital_item"])
    edition = next(e for e in graph["editions"] if e["id"] == use["edition"])
    work = next(w for w in graph["works"] if w["id"] == edition["work"])
    changes = {
        "item-url": (item, "record_url", "https://example.org/unrelated.html"),
        "item-sha": (item, "sha256", "0" * 64),
        "item-kind": (item, "kind", "scan"),
        "item-edition": (item, "edition", "edition.unrelated"),
        "item-scan-url": (item, "scan_url", "https://example.org/unrelated.pdf"),
        "work-id": (work, "id", "work.unrelated"),
        "use-role": (use, "role", "historical_wording_basis"),
        "use-address": (use, "address", {"kind": "text", "text": "orationes.angele-dei"}),
        "use-evidence": (use, "evidence_sha256", "0" * 64),
        "use-claim": (use, "claim", "The entire selected Creed is printed here."),
        "use-locator": (use, "locator", {"section": "Nicene Creed"}),
        "use-edition": (use, "edition", "edition.unrelated"),
    }
    record, field, value = changes[mutation]
    before = copy.deepcopy(record)
    try:
        record[field] = value
        assert canonical(record) != canonical(before)
        with pytest.raises(ValueError, match=r"compendium|source|edition|role|address"):
            subject(case)
    finally:
        record.clear()
        record.update(before)
    assert subject(case) == healthy


@pytest.mark.parametrize("case", CASES, indirect=True)
@pytest.mark.parametrize("mutation", ["coverage", "missing-word", "substantive-word"])
def test_coverage_and_selected_words_reject_and_restore(case, mutation):
    _, _, witness, doc, _, expected = case
    healthy = subject(case)
    old_coverage = copy.deepcopy(witness["coverage"])
    old_segments = copy.deepcopy(doc["segments"])
    try:
        if mutation == "coverage":
            witness["coverage"] = (
                {"kind": "full"}
                if old_coverage["kind"] != "full"
                else {"kind": "words", "words": expected["words"][:-1]}
            )
        else:
            segment = next(
                s
                for s in doc["segments"]
                if any(w["id"] == expected["words"][0] for w in s["words"])
            )
            if mutation == "missing-word":
                segment["words"][:] = [
                    w for w in segment["words"] if w["id"] != expected["words"][0]
                ]
            else:
                word = next(w for w in segment["words"] if w["id"] == expected["words"][0])
                word["form"] = "alienum"
        assert canonical([witness["coverage"], doc["segments"]]) != canonical(
            [old_coverage, old_segments]
        )
        with pytest.raises(ValueError, match=r"coverage|compendium"):
            subject(case)
    finally:
        witness["coverage"] = old_coverage
        doc["segments"][:] = old_segments
    assert subject(case) == healthy


@pytest.mark.parametrize("case", ["orationes.angele-dei"], indirect=True)
@pytest.mark.parametrize("header", ["source", "sha256"])
def test_transcript_source_header_rejects_and_restores(case, header):
    _, _, witness, _, path, _ = case
    healthy = subject(case)
    before, digest = path.read_text(), witness["transcription_sha256"]
    lines = before.splitlines()
    at = next(i for i, line in enumerate(lines) if line.startswith("# " + header + ":"))
    lines[at] = "# " + header + ": wrong"
    changed = "\n".join(lines) + "\n"
    try:
        path.write_text(changed)
        witness["transcription_sha256"] = transcript_digest(changed)
        with pytest.raises(ValueError, match="compendium HTML transcript source header differs"):
            subject(case)
    finally:
        path.write_text(before)
        witness["transcription_sha256"] = digest
    assert subject(case) == healthy


@pytest.mark.parametrize("case", CASES, indirect=True)
@pytest.mark.parametrize("mutation", ["missing", "scan-missing", "scan-empty"])
def test_known_html_inventory_cannot_be_withdrawn_or_disguised(case, mutation):
    _, graph, witness, _, _, _ = case
    healthy = subject(case)
    declaration = witness["source_dependencies"]
    before = copy.deepcopy(declaration)
    use = next(u for u in graph["uses"] if u["id"] == witness["use"])
    item = next(i for i in graph["digital_items"] if i["id"] == use["digital_item"])
    kind = item["kind"]
    try:
        if mutation.startswith("scan"):
            item["kind"] = "scan"
        if mutation == "scan-empty":
            declaration["documents"] = []
        else:
            del declaration["documents"]
        assert canonical([declaration, item["kind"]]) != canonical([before, kind])
        expected_error = (
            r"^paginated documents require a nonempty explicit inventory$"
            if mutation == "scan-empty"
            else r"unsupported born-digital|compendium"
        )
        with pytest.raises(ValueError, match=expected_error):
            subject(case)
    finally:
        declaration.clear()
        declaration.update(before)
        item["kind"] = kind
    assert subject(case) == healthy


@pytest.mark.parametrize(
    "case", ["orationes.magnificat", "orationes.symbolum-apostolorum"], indirect=True
)
def test_outside_partial_reading_does_not_expand_the_witness(case):
    _, _, witness, doc, _, expected = case
    healthy = subject(case)
    outside = next(
        w for s in doc["segments"] for w in s["words"] if w["id"] not in expected["words"]
    )
    before = outside["form"]
    try:
        outside["form"] = "alienum"
        changed = subject(case)
        assert changed["document_resolution"] == healthy["document_resolution"]
        assert changed["selected_text"] != healthy["selected_text"]
        assert witness["coverage"] == expected["coverage"]
    finally:
        outside["form"] = before
    assert subject(case) == healthy


@pytest.mark.parametrize("case", CASES, indirect=True)
def test_explicit_identity_does_not_promote_pending_review(case):
    _, graph, witness, _, _, _ = case
    before = copy.deepcopy(witness["review"])
    try:
        witness["review"] = {"status": "pending"}
        subject(case)
        assert witness["review"] == {"status": "pending"}
        evidence = next(
            t for t in public_text_evidence(graph)["texts"] if t["id"] == witness["text"]
        )
        assert evidence["witnesses"] == []
    finally:
        witness["review"] = before


PDF_CASES = [
    (
        "ordinarium.confiteor-sacerdotis",
        4,
        "2",
        "6f1ce1f0e66649f05c65f1f82c556dd5ab4bca009c315f7c5805e66c34bb59bf",
    ),
    (
        "ordinarium.confiteor",
        6,
        "4",
        "e554421da2c8241462b4f3d3bf46a64ee1f1a873362ff2623983da81ba3e07fe",
    ),
    (
        "ordinarium.evangelium-ultimum",
        28,
        "26",
        "35e0cbcd059bd4c45036267a76cbec2b7b4adb3cdab22f219b8bb6ed5ac98262",
    ),
    (
        "ordinarium.aufer-a-nobis",
        6,
        "4",
        "e554421da2c8241462b4f3d3bf46a64ee1f1a873362ff2623983da81ba3e07fe",
    ),
    (
        "ordinarium.praefatio-communis",
        16,
        "14",
        "81210742f30a43cf67289f1911557fac6e052b800304533b82d51a7658fe7187",
    ),
]


def pdf_fixture(pdf):
    text, page, printed, image = pdf
    record = {
        "contract": "paginated-pdf-1",
        "use": "use.fixture.pdf",
        "digital_item": "item.fixture.pdf",
        "sha256": "43e21a0356b4ab1641c8dfa3927d8e29b53f3b26f926b23080842d601e07d84d",
        "media_type": "application/pdf",
        "pdf_page": page,
        "printed": printed,
        "region": "left-half",
        "page_image_sha256": image,
    }
    source = {
        "use": {
            "address": {"text": text},
            "evidence_sha256": image,
            "role": "corroborating_latin_witness",
            "locator": {"section": text},
        },
        "digital_item": {
            "kind": "born-digital",
            "sha256": record["sha256"],
            "id": record["digital_item"],
            "record_url": "https://extraordinaryform.org/handmissals/HandMissalChant.pdf",
        },
    }
    return [record], {record["use"]: source}


@pytest.mark.parametrize("pdf", PDF_CASES, ids=["priest", "servers", "gospel", "aufer", "preface"])
def test_all_legacy_pdf_documents_keep_exact_old_resolution(pdf):
    records, sources = pdf_fixture(pdf)
    old = paginated_documents.resolve_documents(records, sources)
    assert source_documents.declarations(records) == paginated_documents.declarations(records)
    assert canonical(source_documents.resolve_documents(records, sources)) == canonical(old)


@pytest.mark.parametrize("pdf", PDF_CASES, ids=["priest", "servers", "gospel", "aufer", "preface"])
def test_legacy_pdf_errors_and_recovery_stay_exact(pdf):
    records, sources = pdf_fixture(pdf)
    healthy = source_documents.resolve_documents(records, sources)
    page = records[0]["pdf_page"]
    try:
        records[0]["pdf_page"] = True
        with pytest.raises(ValueError) as old:
            paginated_documents.resolve_documents(records, sources)
        with pytest.raises(ValueError) as new:
            source_documents.resolve_documents(records, sources)
        assert str(new.value) == str(old.value)
        assert "supported typeset PDF" in str(new.value)
    finally:
        records[0]["pdf_page"] = page
    assert source_documents.resolve_documents(records, sources) == healthy

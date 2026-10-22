"""Exact opt-in source identities do not establish performers or source approval."""

import hashlib
import json
import shutil
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.bibliography import public_text_evidence
from build_reader.bibliography_bindings import (
    _SourceSnapshot,
    _witness_subject,
    digest,
    transcript_digest,
    validate_bindings,
    witness_subject,
)
from checks import attribute, raw_binding, transcription, witness_archive

ROOT = Path(__file__).resolve().parents[1]
TEXT = "ordinarium.aufer-a-nobis"
KEY = "aufer-inline-rubrics"
REVISION = "44667ff518b8ff1439780470828b39714f5306a2"
ARCHIVE = "witnesses/raw/missa-44667ff/Ordo/Ordo.txt"
ARCHIVE_SHA = "a7f63e8030325b809f74dd4587c649bf8eb45cdd150fc9a2817fe2a1ed6a42e3"
PDF_SHA = "43e21a0356b4ab1641c8dfa3927d8e29b53f3b26f926b23080842d601e07d84d"
PAGE_SHA = "e554421da2c8241462b4f3d3bf46a64ee1f1a873362ff2623983da81ba3e07fe"
DECLARATION = (
    "web/www/missa/Latin/Ordo/Ordo.txt {inline-rubric-occurrence:53-61} (lines 55-56; line 58)"
)


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def files(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def make_source(tmp_path, mode):
    graph = json.loads((ROOT / "bibliography/graph.json").read_text())
    graph["witnesses"], graph["collations"] = [], []
    original = next(
        r for r in graph["uses"] if r["id"] == "use.ordinarium.praefatio-spiritus-sancti.do44667ff"
    )
    use = deepcopy(original)
    use.update(
        id=f"use.{TEXT}.fixture",
        address={"kind": "text", "text": TEXT},
        claim="Exact source identity assertion in an isolated test fixture.",
    )
    graph["uses"] = [use]
    name = "do-inline" if mode == "inline" else "eo-current"
    path = tmp_path / "witnesses" / TEXT / (name + ".txt")
    path.parent.mkdir(parents=True)
    old = ROOT / "witnesses" / TEXT / ("do.txt" if mode == "inline" else "handmissal-eo.txt")
    body = "\n".join(line for line in old.read_text().splitlines() if not line.startswith("#"))
    headers = f"# witness: {name}\n"
    declaration = {"uses": [], "raw_binding": None}
    registry = {"version": 1, "archives": {}, "bindings": {}}
    if mode == "inline":
        archive = ROOT / ARCHIVE
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == ARCHIVE_SHA
        (tmp_path / ARCHIVE).parent.mkdir(parents=True)
        shutil.copyfile(archive, tmp_path / ARCHIVE)
        lines = archive.read_text().splitlines()
        framing = [
            {
                "line": n,
                "start": start,
                "end": end,
                "text": literal,
                "kind": "inline-parenthetical-rubric",
                "reason": "Explicit source rubric, not spoken text.",
            }
            for n, start, end, literal in (
                (55, 11, 52, "(ei ascendens ad Altare, dicit secreto: )"),
                (58, 51, 78, "(Osculatur Altare in medio)"),
            )
        ]
        registry["archives"]["ordo"] = {
            "upstream": "web/www/missa/Latin/Ordo/Ordo.txt",
            "revision": REVISION,
            "path": ARCHIVE,
            "sha256": ARCHIVE_SHA,
        }
        registry["bindings"][KEY] = {
            "witness": str(path.relative_to(tmp_path)),
            "revision": REVISION,
            "contract": "raw-reading-7",
            "archive": "ordo",
            "heading": {"line": 3, "text": "# Incipit"},
            "context": [{"line": n, "text": lines[n - 1]} for n in range(53, 62)],
            "reading": [{"line": n} for n in (55, 56, 58)],
            "framing": framing,
        }
        declaration["raw_binding"] = KEY
        headers += f"# revision: {REVISION}\n# raw-binding: {KEY}\n# path: {DECLARATION}\n"
        use["evidence_sha256"] = ARCHIVE_SHA
    else:
        work = {
            "id": "work.hand-missal-fixture",
            "title": "Latin-English Hand Missal",
            "responsible": "ExtraordinaryForm.org",
        }
        edition = {
            "id": "edition.hand-missal-fixture.2025",
            "work": work["id"],
            "recension": "Revision 12/12/25",
            "title": "Latin-English Hand Missal",
            "publication_type": "missal",
            "authority": "reference_work",
            "languages": ["en", "la"],
            "rights": {"status": "unknown", "basis": "Test metadata does not grant reuse rights."},
        }
        item = {
            "id": "item.hand-missal-fixture.2025.pdf",
            "edition": edition["id"],
            "repository": "ExtraordinaryForm.org",
            "kind": "born-digital",
            "access": "open",
            "record_url": "https://extraordinaryform.org/handmissals/HandMissalChant.pdf",
            "sha256": PDF_SHA,
        }
        graph["works"].append(work)
        graph["editions"].append(edition)
        graph["digital_items"].append(item)
        use.update(
            edition=edition["id"],
            digital_item=item["id"],
            role="corroborating_latin_witness",
            locator={"section": "Aufer a nobis and Oramus te, PDF6/printed4, left half"},
            evidence_sha256=PAGE_SHA,
        )
        declaration["documents"] = [
            {
                "contract": "paginated-pdf-1",
                "use": use["id"],
                "digital_item": item["id"],
                "sha256": PDF_SHA,
                "media_type": "application/pdf",
                "pdf_page": 6,
                "printed": "4",
                "region": "left-half",
                "page_image_sha256": PAGE_SHA,
            }
        ]
    path.write_text(headers + body + "\n")
    put(tmp_path / raw_binding.REGISTRY, registry)
    witness = {
        "id": f"witness.{TEXT}.fixture",
        "text": TEXT,
        "transcription": name,
        "use": use["id"],
        "role": "derived_comparison",
        "coverage": {"kind": "full"},
        "orthography_profile": "1962 liturgical spelling, exact source accidentals",
        "independence_basis": "Fixture identity assertion, not an independence or source review.",
        "transcription_sha256": transcript_digest(path.read_text()),
        "source_dependencies": declaration,
        "review": {"status": "pending"},
    }
    graph["witnesses"] = [witness]
    target = tmp_path / "texts/ordinarium/aufer-a-nobis.json"
    target.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "texts/ordinarium/aufer-a-nobis.json", target)
    return {
        "root": tmp_path,
        "graph": graph,
        "doc": json.loads(target.read_text()),
        "witness": witness,
        "path": path,
        "registry": registry,
        "mode": mode,
    }


@pytest.fixture
def inline_source(tmp_path):
    return make_source(tmp_path, "inline")


@pytest.fixture
def pdf_source(tmp_path):
    return make_source(tmp_path, "pdf")


def healthy(source):
    assert validate_bindings(source["root"], source["graph"]) == []
    subject = witness_subject(source["root"], source["witness"], source["graph"], source["doc"])
    assert source["witness"]["review"] == {"status": "pending"}
    projected = public_text_evidence(source["graph"])["texts"][0]
    assert projected["witnesses"] == [] and "collation" not in projected
    return subject


@contextmanager
def restored(source):
    before = deepcopy(source)
    disk = files(source["root"])
    expected = healthy(source)
    try:
        yield
    finally:
        for relative, value in disk.items():
            (source["root"] / relative).write_bytes(value)
        source.clear()
        source.update(before)
        assert files(source["root"]) == disk
        assert healthy(source) == expected


def test_exact_pending_pdf_identity_does_not_claim_a_visual_or_source_review(pdf_source):
    subject = healthy(pdf_source)
    assert subject["raw_resolution"] is None
    document = subject["document_resolution"]["documents"][pdf_source["witness"]["use"]]
    assert document["sha256"] == PDF_SHA and document["page_image_sha256"] == PAGE_SHA
    assert document["pdf_page"] == 6 and document["printed"] == "4"
    assert document["region"] == "left-half"


def test_exact_pending_inline_identity_conveys_no_performer(inline_source, monkeypatch):
    source = inline_source
    subject = healthy(source)
    reading = raw_binding.resolve_binding(source["path"], source["root"])
    assert reading.spans == reading.fragments == () and len(reading.text.split()) == 42
    assert hashlib.sha256((reading.text + "\n").encode()).hexdigest() == (
        "2806c3806d24b874ecdd46af7fdc3c66b68d5ce33457b792dafb6362782948e6"
    )
    assert transcription.check_transcriptions(source["path"].parent) == ([], 1)
    assert witness_archive.check(source["root"]) == []
    monkeypatch.setattr(attribute, "CORPUS", source["root"])
    message = "inline-rubric evidence supports textual identity only"
    with pytest.raises(raw_binding.BindingError, match=message):
        attribute.witness_ranges(TEXT)
    actor = attribute._actor_sources(TEXT)
    assert actor.scope == "RAW_TEXT_ONLY" and actor.units == ()

    class TextOnly:
        source = reading.source

        @property
        def spans(self):
            pytest.fail("text-only inline reading reached performer spans")

        @property
        def fragments(self):
            pytest.fail("text-only inline reading reached performer fragments")

    monkeypatch.setattr(attribute, "resolve_binding", lambda path, root: TextOnly())
    with pytest.raises(raw_binding.BindingError, match=message):
        attribute._source_ranges(TEXT)
    assert attribute._actor_sources(TEXT).scope == "RAW_TEXT_ONLY"
    subject["raw_resolution"]["binding"]["reading"].clear()
    assert len(healthy(source)["raw_resolution"]["binding"]["reading"]) == 3


RAW_CASES = [
    ("missing-inventory", "complete explicit source_dependencies declaration required"),
    ("boolean-offset", "raw-reading-7 framing differs from a reviewed literal rubric"),
    ("sacred-word-exclusion", "raw-reading-7 framing differs from a reviewed literal rubric"),
    ("third-parenthesis", "raw-reading-7 requires exactly the two reviewed inline rubrics"),
    ("missing-rubric", "raw-reading-7 requires exactly the two reviewed inline rubrics"),
    ("empty-reason", "raw-reading-7 framing differs from a reviewed literal rubric"),
    ("duplicate-reading", "raw-reading-7 requires exactly the ordered spoken lines"),
    ("reordered-reading", "raw-reading-7 requires exactly the ordered spoken lines"),
    ("context-change", "raw-reading-7 context differs from exact physical lines"),
    ("missing-context", "raw-reading-7 requires complete local source context"),
    ("wrong-heading", "raw-reading-7 requires the exact enclosing heading"),
    ("refreshed-archive", "raw-reading-7 requires the exact retained Mass Ordo object"),
    ("wrong-provider", "raw-reading-7 requires the exact retained Mass Ordo object"),
    ("false-approved-role", "raw-reading-7 requires one derived digital source use"),
    ("body-word", "transcription differs from its exact inline-rubric reading"),
]


@pytest.mark.parametrize("mutation,message", RAW_CASES, ids=[r[0] for r in RAW_CASES])
def test_inline_mutations_reject_at_owned_checks_and_restore(inline_source, mutation, message):
    source = inline_source
    with restored(source):
        binding = source["registry"]["bindings"][KEY]
        if mutation == "missing-inventory":
            del source["witness"]["source_dependencies"]
        elif mutation == "boolean-offset":
            binding["framing"][0]["start"] = True
        elif mutation == "sacred-word-exclusion":
            binding["framing"][1].update(start=3, end=9, text="Orámus")
        elif mutation == "third-parenthesis":
            binding["framing"].append(deepcopy(binding["framing"][0]))
        elif mutation == "missing-rubric":
            binding["framing"].pop()
        elif mutation == "empty-reason":
            binding["framing"][0]["reason"] = " "
        elif mutation == "duplicate-reading":
            binding["reading"].append({"line": 58})
        elif mutation == "reordered-reading":
            binding["reading"].reverse()
        elif mutation == "context-change":
            binding["context"][0]["text"] = "R. Changed."
        elif mutation == "missing-context":
            binding["context"].pop()
        elif mutation == "wrong-heading":
            binding["heading"]["line"] = 4
        elif mutation == "refreshed-archive":
            path = source["root"] / ARCHIVE
            path.write_bytes(path.read_bytes() + b"\n# changed\n")
            source["registry"]["archives"]["ordo"]["sha256"] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
        elif mutation == "wrong-provider":
            source["registry"]["archives"]["ordo"]["upstream"] = (
                "web/www/missa/Latin/Ordo/Other.txt"
            )
        elif mutation == "false-approved-role":
            source["graph"]["uses"][0]["role"] = "direct_approved_print"
        elif mutation == "body-word":
            source["path"].write_text(
                source["path"].read_text().replace("iniquitátes", "iniquitátem")
            )
            source["witness"]["transcription_sha256"] = transcript_digest(
                source["path"].read_text()
            )
        else:
            raise AssertionError(mutation)
        put(source["root"] / raw_binding.REGISTRY, source["registry"])
        with pytest.raises(ValueError) as error:
            witness_subject(source["root"], source["witness"], source["graph"], source["doc"])
        assert str(error.value) == message
        diagnostic = f"bibliography witness {source['witness']['id']}: {message}"
        assert diagnostic in validate_bindings(source["root"], source["graph"])


LEGACY = [
    {
        "contract": "raw-reading-1",
        "witness": "witness.ordinarium.iube-domne-benedicere-in-passione.do44667ff",
        "path": "witnesses/ordinarium.iube-domne-benedicere-in-passione/do.txt",
        "raw_source_sha256": "5d44773de01285d4d0e780a7f6cd0d966d700e460d43805a6ff737434cdb66af",
        "witness_subject_sha256": (
            "f991d70b0e005791afaa7e62c31f689c5e5d1f916cbfd28c0a01ec0c8f3730aa"
        ),
    },
    {
        "contract": "raw-reading-2",
        "witness": "witness.proprium.dominica-ii-post-epiphaniam-graduale.do44667ff",
        "path": "witnesses/proprium.dominica-ii-post-epiphaniam-graduale/do.txt",
        "raw_source_sha256": "47f690000f4d71381a492c4ad69be913b409b9f5e48150dc8ee090e827f46366",
        "witness_subject_sha256": (
            "0a1eb7a45dfa094f5f7d23841f2307b38cb674ab7b6f059544d8a0cde9384a85"
        ),
    },
    {
        "contract": "raw-reading-3",
        "witness": "witness.ordinarium.praefatio-paschalis-in-nocte.do44667ff",
        "path": "witnesses/ordinarium.praefatio-paschalis-in-nocte/do.txt",
        "raw_source_sha256": "a8397cb8a6b49671e9433deb22b5f7bc49efcc6559475c2dab6a9e14bf63f5df",
        "witness_subject_sha256": (
            "8d50ecb80d3cb0a194233402d6315a849800b8d7df9bc6c0c5ab3e3eba274ebe"
        ),
    },
    {
        "contract": "raw-reading-4",
        "witness": "witness.ordinarium.munda-cor-meum.do44667ff",
        "path": "witnesses/ordinarium.munda-cor-meum/do.txt",
        "raw_source_sha256": "32863615a64f527fb24f5678f91889ff0984bc3c6d903a30243be5eed6a05cf7",
        "witness_subject_sha256": (
            "08748ad6f732771642722f3feedf6056442d48d7b6a8383b0596161e82a50e36"
        ),
    },
    {
        "contract": "raw-reading-5",
        "witness": "witness.ordinarium.iube-domine-benedicere.do44667ff",
        "path": "witnesses/ordinarium.iube-domine-benedicere/do.txt",
        "raw_source_sha256": "46d14cc9951b484e73fd74fc0bc96b6bd21c0c0f23a54061129060ed5407873e",
        "witness_subject_sha256": (
            "ea2795dd2bbda8caba5be2ef5ba36912ab20addb14ee93f065c283113ff9a41e"
        ),
    },
    {
        "contract": "raw-reading-6",
        "witness": "witness.ordinarium.praefatio-spiritus-sancti.do44667ff",
        "path": "witnesses/ordinarium.praefatio-spiritus-sancti/do.txt",
        "raw_source_sha256": "e17f3faa3d55c4f030ba08bfe1d5705f8f0b1ebdb49e9f1a22b742328023a410",
        "witness_subject_sha256": (
            "2a1e4a2d88d47f192a2b5325b56fbed97b93ae185a16b80e0808a41f478caf67"
        ),
    },
]


@pytest.mark.parametrize("row", LEGACY, ids=[r["contract"] for r in LEGACY])
def test_existing_raw_and_witness_subjects_keep_exact_bytes(row):
    graph = json.loads((ROOT / "bibliography/graph.json").read_text())
    witness = next(r for r in graph["witnesses"] if r["id"] == row["witness"])
    reading = raw_binding.resolve_binding(ROOT / row["path"], ROOT)
    assert reading.source["contract"] == row["contract"]
    assert digest(reading.source) == row["raw_source_sha256"]
    category, slug = witness["text"].split(".", 1)
    doc = json.loads((ROOT / "texts" / category / (slug + ".json")).read_text())
    subject = _witness_subject(ROOT, witness, doc, _SourceSnapshot(ROOT, graph), reviewable=False)
    assert digest(subject) == row["witness_subject_sha256"]


@pytest.mark.parametrize("mode", ["inline", "pdf"])
def test_old_review_hash_cannot_promote_either_new_inventory(tmp_path, mode):
    source = make_source(tmp_path, mode)
    with restored(source):
        source["witness"]["review"] = {"status": "reviewed", "sha256": "0" * 64}
        expected = (
            f"bibliography witness {source['witness']['id']}: "
            "reviewed subject changed; re-review or mark pending explicitly"
        )
        assert expected in validate_bindings(source["root"], source["graph"])


PDF_CASES = [
    ("missing-inventory", "unsupported born-digital source requires its own evidence contract"),
    ("same-count-use", "paginated documents must exactly inventory non-DO born-digital uses"),
    ("wrong-pdf", "paginated document differs from the supported typeset PDF and page"),
    ("wrong-region", "paginated document differs from the supported typeset PDF and page"),
    ("boolean-page", "paginated document differs from the supported typeset PDF and page"),
    ("wrong-page-image", "paginated document differs from the supported typeset PDF and page"),
    ("wrong-item", "paginated document source-use/item identity differs"),
    ("scan-workaround", "paginated documents must exactly inventory non-DO born-digital uses"),
    ("approved-print-role", "paginated document source-use/item identity differs"),
    ("duplicate-use", "paginated document use IDs must be sorted and unique"),
    (
        "extra-born-digital-use",
        "paginated documents must exactly inventory non-DO born-digital uses",
    ),
    ("borrow-raw-binding", "paginated documents cannot borrow a raw binding"),
]


@pytest.mark.parametrize("mutation,message", PDF_CASES, ids=[r[0] for r in PDF_CASES])
def test_paginated_document_mutations_reject_and_restore(pdf_source, mutation, message):
    source = pdf_source
    with restored(source):
        declaration = source["witness"]["source_dependencies"]
        document = declaration["documents"][0]
        use = source["graph"]["uses"][0]
        item = next(r for r in source["graph"]["digital_items"] if r["id"] == use["digital_item"])
        if mutation == "missing-inventory":
            del declaration["documents"]
        elif mutation == "same-count-use":
            document["use"] += ".foreign"
        elif mutation == "wrong-pdf":
            document["sha256"] = "0" * 64
        elif mutation == "wrong-region":
            document["region"] = "right-half"
        elif mutation == "boolean-page":
            document["pdf_page"] = True
        elif mutation == "wrong-page-image":
            document["page_image_sha256"] = "0" * 64
        elif mutation == "wrong-item":
            document["digital_item"] += ".foreign"
        elif mutation == "scan-workaround":
            item["kind"] = "scan"
        elif mutation == "approved-print-role":
            use["role"] = "direct_approved_print"
        elif mutation == "duplicate-use":
            declaration["documents"].append(deepcopy(document))
        elif mutation == "extra-born-digital-use":
            extra = deepcopy(use)
            extra["id"] += ".extra"
            source["graph"]["uses"].append(extra)
            declaration["uses"] = [extra["id"]]
        elif mutation == "borrow-raw-binding":
            declaration["raw_binding"] = "unsupported-document-raw-binding"
        else:
            raise AssertionError(mutation)
        with pytest.raises(ValueError) as error:
            witness_subject(source["root"], source["witness"], source["graph"], source["doc"])
        assert str(error.value) == message
        diagnostic = f"bibliography witness {source['witness']['id']}: {message}"
        assert diagnostic in validate_bindings(source["root"], source["graph"])

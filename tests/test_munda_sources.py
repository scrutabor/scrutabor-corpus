"""Munda's print, digital and short-ending evidence remain distinct and bounded."""

import copy
import json
import shutil
from pathlib import Path

import pytest

from build_reader import bibliography
from build_reader.bibliography_bindings import digest, selected_text, witness_subject
from checks.collate import collate
from checks.raw_binding import BindingError, resolve_binding

ROOT = Path(__file__).resolve().parents[1]
TEXT = "ordinarium.munda-cor-meum"
CORE = "texts/ordinarium/munda-cor-meum.json"
WITNESSES = f"witnesses/{TEXT}"
RAW = "witnesses/raw/missa-44667ff/Ordo/Ordo.txt"
REVISION = "44667ff518b8ff1439780470828b39714f5306a2"
RUBRIC = (
    "!Si vero Sacerdos sine Diacono et Subdiacono celebrat, delato libro ad aliud "
    "cornu Altaris, inclinatus in medio, junctis manibus dicit:"
)
DIGITAL_BODY = (
    "Munda cor meum ac lábia mea, omnípotens Deus, qui lábia Isaíæ Prophétæ cálculo "
    "mundásti igníto: ita me tua grata miseratióne dignáre mundáre, ut sanctum "
    "Evangélium tuum digne váleam nuntiáre. Per Christum, Dóminum nostrum. Amen."
)
ENDING_SOURCES = {
    "pl": (
        "edition.pamiatka-missyi-dla-ludu-katolickiego-1903",
        "item.pamiatka-missyi-dla-ludu-katolickiego-1903.sbc",
        "45",
        "PDF page 48",
        "ff084d288a3ac4d35664b4a228a2615368a4f25ec62b200f71bae7df7e46d200",
    ),
    "en": (
        "edition.the-missal-for-the-laity-1846",
        "item.missal-for-the-laity-1846.scan",
        "40",
        "PDF page 52",
        "12a39d07b85fecb8570e6bd741a4d49d0d726de47a81e359666728a35d7580ea",
    ),
}


def load(path, root=ROOT):
    return json.loads((root / path).read_text(encoding="utf-8"))


def write(root, path, value):
    destination = root / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def munda_rows(graph, key):
    return [r for r in graph[key] if r.get("text", r.get("address", {}).get("text")) == TEXT]


def assert_print_dependency(witness):
    assert witness["source_dependencies"] == {
        "uses": [f"use.{TEXT}.mr1962-ritual-boundary"],
        "raw_binding": None,
    }


def assert_ending_reference(graph, language_graph, language):
    rows = munda_rows(language_graph, "uses")
    assert len(rows) == 1
    use = rows[0]
    edition, item, printed, scan, evidence = ENDING_SOURCES[language]
    assert use["id"] == f"use.{language}.munda-cor-meum.short-conclusion"
    assert (use["edition"], use["digital_item"]) == (edition, item)
    assert use["address"] == {"kind": "segment", "text": TEXT, "segment": "s02"}
    assert use["role"] == "historical_wording_basis"
    assert use["decision"] == "RETAIN"
    assert use["locator"] == {"printed": printed, "scan": scan}
    assert use["evidence_sha256"] == evidence
    source_item = next(r for r in graph["digital_items"] if r["id"] == item)
    assert source_item["edition"] == edition


@pytest.fixture
def source_corpus(tmp_path):
    # A real one-text slice: no invented source reading, no full-corpus copying.
    for relative in (
        CORE,
        f"{WITNESSES}/mr.txt",
        f"{WITNESSES}/do.txt",
        f"{WITNESSES}/apparatus.json",
        RAW,
    ):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    registry = load("witnesses/raw/bindings.json")
    registry["archives"] = {"missa-ordo-44667ff": registry["archives"]["missa-ordo-44667ff"]}
    registry["bindings"] = {"munda-cor-meum-priest": registry["bindings"]["munda-cor-meum-priest"]}
    write(tmp_path, "witnesses/raw/bindings.json", registry)
    graph = load("bibliography/graph.json")
    for key in ("uses", "witnesses", "collations"):
        graph[key] = munda_rows(graph, key)
    write(tmp_path, "bibliography/graph.json", graph)
    return tmp_path


@pytest.mark.parametrize(
    "suffix,edition,item,role,evidence",
    [
        (
            "mr1962-body",
            "edition.missale-romanum.1962-typica",
            "item.missale-romanum.1962-typica.ia",
            "direct_approved_print",
            "ec6bcc03fe7879c158e34bc9c17e5e760d3659682b6a1c29c48473383a911f74",
        ),
        (
            "mr1962-ritual-boundary",
            "edition.missale-romanum.1962-typica",
            "item.missale-romanum.1962-typica.ia",
            "rubric_control",
            "f84bcc646cfc3b9908a50a4f86e3d1c0ee21738df7afd9230fd343b801f658ff",
        ),
        (
            "do44667ff-body",
            "edition.divinum-officium-missa.44667ff",
            "item.divinum-officium-missa.44667ff.github",
            "derived_digital_collation_aid",
            "a7f63e8030325b809f74dd4587c649bf8eb45cdd150fc9a2817fe2a1ed6a42e3",
        ),
    ],
)
def test_exact_source_identity_and_distinct_claim_boundaries(suffix, edition, item, role, evidence):
    graph = load("bibliography/graph.json")
    use = next(u for u in graph["uses"] if u["id"] == f"use.{TEXT}.{suffix}")
    assert (use["edition"], use["digital_item"], use["role"]) == (edition, item, role)
    assert use["evidence_sha256"] == evidence
    assert use["address"] == {"kind": "text", "text": TEXT}
    if suffix == "mr1962-body":
        assert use["locator"]["printed"] == "222"
        assert "solemn deacon context" in use["claim"]
        assert "priest reuse is established separately" in use["claim"]
        print_edition = next(e for e in graph["editions"] if e["id"] == edition)
        assert (print_edition["publisher"], print_edition["edition_statement"]) == (
            "Benziger Brothers",
            "Editio iuxta typicam",
        )
    elif suffix == "mr1962-ritual-boundary":
        assert use["locator"]["printed"] == "223"
        assert "Masses of the dead" in use["claim"]
        assert "blessing is not part of this text" in use["claim"]
    else:
        assert "not proof of an independent manuscript family" in use["claim"]


@pytest.mark.parametrize("transcription", ["mr", "do"])
def test_each_complete_witness_has_its_actual_source_inventory(source_corpus, transcription):
    graph = load("bibliography/graph.json", source_corpus)
    witness = next(w for w in graph["witnesses"] if w["transcription"] == transcription)
    if transcription == "mr":
        assert_print_dependency(witness)
    else:
        assert witness["source_dependencies"] == {
            "uses": [],
            "raw_binding": "munda-cor-meum-priest",
        }
    subject = witness_subject(source_corpus, witness, graph, load(CORE, source_corpus))
    assert subject["contract"] == "witness-review-2"


def test_exact_munda_priest_branch_selects_full_line_without_blessing():
    registry = load("witnesses/raw/bindings.json")
    binding = registry["bindings"]["munda-cor-meum-priest"]
    assert binding["contract"] == "raw-reading-4"
    assert binding["revision"] == REVISION
    assert binding["evidence"] == [
        {
            "archive": "missa-ordo-44667ff",
            "first": 121,
            "last": 121,
            "section": "Evangelium",
            "section_line": 119,
            "heading": {"format": "hash-space", "text": "# Evangelium"},
            "branch": {"line": 118, "text": "!*RnD"},
            "context": [{"line": 120, "text": RUBRIC}],
        }
    ]
    assert binding["references"] == []
    assert binding["reading"] == [{"archive": "missa-ordo-44667ff", "first": 121, "last": 121}]
    raw = (ROOT / RAW).read_text(encoding="utf-8").splitlines()
    assert raw[117:121] == ["!*RnD", "# Evangelium", RUBRIC, "v. " + DIGITAL_BODY]
    assert raw[121].startswith("v. Jube, Dómine, benedícere.")
    resolved = resolve_binding(ROOT / WITNESSES / "do.txt", ROOT)
    assert resolved is not None
    assert resolved.text == DIGITAL_BODY
    assert len(resolved.text.split()) == 34
    assert [(f.line, f.whole_line, f.raw) for f in resolved.fragments] == [
        (121, True, "v. " + DIGITAL_BODY)
    ]


def test_four_accidentals_are_explicit_without_substantive_normalization():
    apparatus = load(f"{WITNESSES}/apparatus.json")
    assert [(r["at"], r["ours"], r["witnesses"], r["class"]) for r in apparatus["adjudicated"]] == [
        ("w003", "meum,", {"do": "meum"}, "punctuation"),
        ("w012", "prophétæ", {"do": "Prophétæ"}, "capitalization"),
        ("w025", "evangélium", {"do": "Evangélium"}, "capitalization"),
        ("w031", "Christum", {"do": "Christum,"}, "punctuation"),
    ]
    graph = load("bibliography/graph.json")
    row = munda_rows(graph, "collations")[0]
    assert row["apparatus_sha256"] == digest(apparatus)
    assert row["selected_text_sha256"] == digest(selected_text(load(CORE)))
    assert collate(load(CORE), ROOT / WITNESSES)[:2] == ([], [])


def test_source_identity_does_not_promote_pending_review_or_universal_actors():
    graph = load("bibliography/graph.json")
    witnesses = munda_rows(graph, "witnesses")
    collations = munda_rows(graph, "collations")
    assert len(witnesses) == 2 and len(collations) == 1
    assert all(w["review"] == {"status": "pending"} for w in witnesses)
    assert collations[0]["review"] == {"status": "pending"}
    row = next(r for r in bibliography.public_text_evidence(graph)["texts"] if r["id"] == TEXT)
    assert row["witnesses"] == [] and "collation" not in row
    digital = next(w for w in witnesses if w["transcription"] == "do")
    assert digital["role"] == "derived_comparison"
    assert "not three witnesses" in digital["independence_basis"]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_historical_wording_basis_is_exact_short_ending_only(language):
    graph = load("bibliography/graph.json")
    assert_ending_reference(graph, load(f"languages/{language}/bibliography.json"), language)
    records = [
        r
        for r in load(f"languages/{language}/translation-basis.json")["records"]
        if TEXT in r["texts"]
    ]
    assert records == [{"texts": [TEXT], "segments": ["s02"], "relationship": "exact"}]


def test_missing_the_source_link_is_rejected_then_restored():
    graph = load("bibliography/graph.json")
    language_graph = load("languages/en/bibliography.json")
    original = copy.deepcopy(language_graph)
    assert_ending_reference(graph, language_graph, "en")
    munda_rows(language_graph, "uses")[0]["digital_item"] = "item.missal-for-laity-1846.scan"
    with pytest.raises(AssertionError):
        assert_ending_reference(graph, language_graph, "en")
    language_graph.clear()
    language_graph.update(original)
    assert_ending_reference(graph, language_graph, "en")


def test_importing_allusive_coal_into_exact_digital_transcript_is_rejected_then_restored(
    source_corpus,
):
    path = source_corpus / WITNESSES / "do.txt"
    original = path.read_bytes()
    assert resolve_binding(path, source_corpus).text == DIGITAL_BODY
    path.write_bytes(original.replace("cálculo".encode(), "carbóne".encode()))
    with pytest.raises(BindingError, match="transcription differs"):
        resolve_binding(path, source_corpus)
    path.write_bytes(original)
    assert resolve_binding(path, source_corpus).text == DIGITAL_BODY


def test_priest_reuse_dependency_cannot_be_silently_dropped():
    graph = load("bibliography/graph.json")
    witness = next(w for w in munda_rows(graph, "witnesses") if w["transcription"] == "mr")
    original = copy.deepcopy(witness)
    assert_print_dependency(witness)
    witness["source_dependencies"]["uses"] = []
    with pytest.raises(AssertionError):
        assert_print_dependency(witness)
    witness.clear()
    witness.update(original)
    assert_print_dependency(witness)

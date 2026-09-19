"""A real complete Gospel licenses attribution, not false source agreement.

The fixture selects MR1962, printed p.527, against the pinned Divinum Officium
05-01 Gospel. Its original digital file is MIT-licensed; see the corresponding
44667ff license in witnesses/raw. Every Latin word remains an individual token.
"""

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

from checks import attribute
from checks.attribution_alignment import align_unmarked_reading
from checks.collate import collate
from checks.raw_binding import REGISTRY, resolve_binding

FIXTURE = Path(__file__).parent / "fixtures/philip-james-attribution.json"
KEY = "philip-james-gospel"


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n"
        if isinstance(value, dict)
        else value,
        encoding="utf-8",
    )


@pytest.fixture
def reading(tmp_path, monkeypatch):
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    folder = tmp_path / "witnesses" / data["document"]["id"]
    save(folder / "mr.txt", data["mr_witness"])
    save(folder / "do.txt", data["do_witness"])
    save(folder / "apparatus.json", data["apparatus"])
    save(tmp_path / data["archive"]["path"], data["raw"])
    save(
        tmp_path / REGISTRY,
        {"version": 1, "archives": {KEY: data["archive"]}, "bindings": {KEY: data["binding"]}},
    )
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    return tmp_path, folder, data


def source_checks(root, folder, doc):
    assert resolve_binding(folder / "do.txt", root) is not None
    errors, warnings, stats = collate(doc, folder)
    assert errors == warnings == []
    return stats


def test_actual_219_words_and_distinct_evidence(reading):
    root, folder, data = reading
    doc = data["document"]
    words = doc["segments"][0]["words"]
    assert len(words) == 219 and all(len(word["form"].split()) == 1 for word in words)
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    stats = source_checks(root, folder, doc)
    assert stats["variants_adjudicated"] == 17
    assert stats["substantive_variants"] == 2
    assert stats["orthographic"] == 4
    assert not attribute.span_covers(doc)
    result = align_unmarked_reading(doc, root)
    assert result is not None
    assert result.witness_id == "do"
    assert result.witness_path == folder / "do.txt"
    assert result.source_path == root / data["archive"]["path"]
    assert result.source_line == 39
    assert result.source_sha256 == data["archive"]["sha256"]
    assert result.supporting_witnesses == ("mr",)
    assert len(result.words) == 219
    assert [word.word_id for word in result.words] == [word["id"] for word in words]
    assert result.substantive_variants == 2
    assert not result.literal_text_equal
    assert [
        (word.word_id, word.selected, word.source)
        for word in result.words
        if word.relation == "substantive"
    ] == [("w009", "turbétur", "turbátur"), ("w104", "cognoscétis", "cognoscátis")]
    assert [word.word_id for word in result.words if word.relation == "orthography"] == [
        "w005",
        "w079",
        "w121",
        "w203",
    ]
    # These are real grammatical variants, not spellings. This exact regression
    # does not pretend that generic collation can classify all Latin grammar.
    assert {
        entry["at"]: entry["class"]
        for entry in data["apparatus"]["adjudicated"]
        if entry["at"] in {"w009", "w104"}
    } == {"w009": "substantive", "w104": "substantive"}
    assert before == {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_compact_editorial_source_pointer(reading):
    root, _, data = reading
    doc = data["document"]
    doc["editorial"] = {"source": doc.pop("source")}
    assert align_unmarked_reading(doc, root) is not None


def test_attribution_does_not_borrow_pooled_markers(reading, monkeypatch):
    _, _, data = reading

    def forbidden(*args, **kwargs):
        pytest.fail("source-specific attribution called pooled marked_lines")

    monkeypatch.setattr(attribute, "marked_lines", forbidden)
    assert attribute.propose(data["document"]) == {"s01": {"speaker": "sacerdos", "voice": "clara"}}
    assert not attribute.span_covers(data["document"])


@pytest.mark.parametrize("at", ["w009", "w104"])
def test_each_exact_ruling_is_required(reading, at):
    root, folder, data = reading
    data["apparatus"]["adjudicated"] = [
        entry for entry in data["apparatus"]["adjudicated"] if entry["at"] != at
    ]
    save(folder / "apparatus.json", data["apparatus"])
    assert align_unmarked_reading(data["document"], root) is None


@pytest.mark.parametrize(
    "change", ["witness", "ours", "source", "duplicate", "empty", "span", "omission"]
)
def test_exact_source_specific_apparatus(reading, change):
    root, folder, data = reading
    entry = next(e for e in data["apparatus"]["adjudicated"] if e["at"] == "w009")
    if change == "witness":
        entry["witnesses"] = {"mr": "turbátur"}
    elif change == "ours":
        entry["ours"] = "turbétis"
    elif change == "source":
        entry["witnesses"]["do"] = "turbávit"
    elif change == "duplicate":
        data["apparatus"]["adjudicated"].append(copy.deepcopy(entry))
    elif change == "empty":
        entry["ruling"] = ""
    elif change == "span":
        entry.update({"class": "substantive-span", "through": "w009"})
    else:
        entry.update({"class": "omission", "witnesses": {"do": ""}})
    save(folder / "apparatus.json", data["apparatus"])
    assert align_unmarked_reading(data["document"], root) is None


@pytest.mark.parametrize("index", [8, 103, 104])
def test_unlicensed_selected_word(reading, index):
    root, _, data = reading
    data["document"]["segments"][0]["words"][index]["form"] = "alienum"
    assert align_unmarked_reading(data["document"], root) is None


@pytest.mark.parametrize(
    "change",
    ["raw", "body", "order", "length", "binding-marker", "binding-record", "support", "json"],
)
def test_input_drift_fails_closed(reading, change):
    root, folder, data = reading
    if change == "raw":
        save(root / data["archive"]["path"], data["raw"] + "\n")
    elif change == "body":
        save(folder / "do.txt", data["do_witness"].replace("turbátur", "turbávit"))
    elif change == "order":
        save(folder / "do.txt", data["do_witness"].replace("cor vestrum.", "vestrum cor."))
    elif change == "length":
        save(folder / "do.txt", data["do_witness"] + "Amen.\n")
    elif change == "binding-marker":
        save(folder / "do.txt", data["do_witness"].replace(f"# raw-binding: {KEY}\n", ""))
    elif change == "binding-record":
        registry = json.loads((root / REGISTRY).read_text())
        registry["bindings"] = {}
        save(root / REGISTRY, registry)
    elif change == "support":
        save(folder / "mr.txt", data["mr_witness"].replace("turbétur", "turbátur"))
    else:
        save(folder / "apparatus.json", "{")
    assert align_unmarked_reading(data["document"], root) is None


@pytest.mark.parametrize("witness", ["do", "mr"])
@pytest.mark.parametrize(
    "header",
    [
        "# covers: w001-w219\n",
        "# corrigendum: turbátur -> turbétur (a declared correction)\n",
        "# recension: -Amen (a declared removal)\n",
    ],
)
def test_partial_corrected_or_recensional_witnesses_are_ineligible(reading, witness, header):
    root, folder, data = reading
    path = folder / f"{witness}.txt"
    save(path, header + path.read_text())
    assert align_unmarked_reading(data["document"], root) is None


def test_support_must_be_one_whole_reading_not_pooled_loci(reading):
    root, folder, data = reading
    save(folder / "mr.txt", data["mr_witness"].replace("turbétur", "turbátur"))
    save(
        folder / "other.txt",
        data["mr_witness"]
        .replace("# witness: mr", "# witness: other")
        .replace("cognoscétis", "cognoscátis"),
    )
    for entry in data["apparatus"]["adjudicated"]:
        if entry["at"] == "w009":
            entry["witnesses"]["mr"] = "turbátur"
        elif entry["at"] == "w104":
            entry["witnesses"]["other"] = "cognoscátis"
    save(folder / "apparatus.json", data["apparatus"])
    source_checks(root, folder, data["document"])
    assert align_unmarked_reading(data["document"], root) is None


@pytest.mark.parametrize("change", ["marked", "multiline", "multispan"])
def test_valid_raw_binding_does_not_expand_the_attribution_scope(reading, change):
    root, folder, data = reading
    registry = json.loads((root / REGISTRY).read_text())
    raw = root / data["archive"]["path"]
    lines = data["raw"].splitlines(keepends=True)
    if change == "marked":
        lines[38] = "R. " + lines[38]
    else:
        first, last = lines[38].split(" ", 1)
        lines[38:39] = [first + "\n", last]
        binding = registry["bindings"][KEY]
        binding["evidence"][0]["last"] = 40
        binding["reading"][0]["last"] = 40
        if change == "multispan":
            binding["reading"] = [
                {"archive": KEY, "first": 39, "last": 39},
                {"archive": KEY, "first": 40, "last": 40},
            ]
        save(folder / "do.txt", data["do_witness"].replace("(lines 39-39)", "(lines 39-40)"))
    save(raw, "".join(lines))
    registry["archives"][KEY]["sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    save(root / REGISTRY, registry)
    source_checks(root, folder, data["document"])
    assert align_unmarked_reading(data["document"], root) is None


@pytest.mark.parametrize("change", ["category", "two-verses", "rubric", "empty", "pointer"])
def test_document_scope_is_narrow(reading, change):
    root, _, data = reading
    doc = data["document"]
    if change == "category":
        doc["category"] = "orationes"
    elif change == "two-verses":
        seg = doc["segments"][0]
        doc["segments"].append({"id": "s02", "type": "verse", "words": seg["words"][100:]})
        seg["words"] = seg["words"][:100]
    elif change == "rubric":
        doc["segments"].insert(0, {"id": "s00", "type": "rubric", "text": "Secreto"})
    elif change == "empty":
        doc["segments"][0]["words"] = []
    else:
        doc["source"]["apparatus"] = "witnesses/another/apparatus.json"
    assert align_unmarked_reading(doc, root) is None


@pytest.mark.parametrize("valid", [True, False])
def test_writer_distinguishes_alignment_from_unresolved_source(reading, monkeypatch, capsys, valid):
    root, folder, data = reading
    doc = data["document"]
    seg = doc["segments"][0]
    del seg["speaker"]
    del seg["voice"]
    path = root / "texts/proprium/gospel.json"
    save(path, doc)
    if not valid:
        save(folder / "do.txt", data["do_witness"].replace("turbátur", "turbávit"))
    protected = {p: p.read_bytes() for p in root.rglob("*") if p.is_file() and p != path}
    before = path.read_bytes()
    monkeypatch.setattr(sys, "argv", ["attribute", "--write"])
    attribute.main()
    output = capsys.readouterr().out
    after = json.loads(path.read_text())
    if valid:
        assert "ALIGNED " in output and "not literal source coverage" in output
        assert ":39; 2 substantive variants" in output and "UNSOURCED " not in output
        assert after["segments"][0].pop("speaker") == "sacerdos"
        assert after["segments"][0].pop("voice") == "clara"
        assert after == doc
    else:
        assert "UNSOURCED " in output and "ALIGNED " not in output
        assert path.read_bytes() == before
    assert protected == {p: p.read_bytes() for p in root.rglob("*") if p.is_file() and p != path}


def test_direct_coverage_does_not_invoke_alignment(reading, monkeypatch):
    _, _, data = reading
    monkeypatch.setattr(attribute, "span_covers", lambda doc: True)

    def forbidden(*args, **kwargs):
        pytest.fail("direct coverage unnecessarily invoked variant alignment")

    monkeypatch.setattr(attribute, "align_unmarked_reading", forbidden)
    assert attribute.propose(data["document"])["s01"]["speaker"] == "sacerdos"

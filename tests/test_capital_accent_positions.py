"""Capital-accent positions, corrected digital-accent entries and the Trinity Collect opening.

The class guard is mechanical: it checks where a changed acute sits, not whether a
ruling's prose is true or whether a transcription follows its page. The source
regressions pin the registered evidence and the established readings separately.
"""

import hashlib
import json
import shutil
import unicodedata
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import bibliography_bindings as bindings
from build_reader import store
from build_reader.layers import expand_core
from checks.apparatus import (
    DEPRECATED_ACCENT_RULING,
    capital_accent_issue,
    capital_accent_positions,
    derived_summary,
    lint_apparatus_summary,
)
from checks.collate import collate, corpus_tokens, load_witness

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads(
    (ROOT / "tests/fixtures/capital-accent-positions.json").read_text(encoding="utf-8")
)
TRINITY = FIXTURE["trinity_collect"]
LOWER = "changed acute on a lowercase letter"
UNCHANGED = "no changed acute on a capital"
UNALIGNED = "letters cannot align for a capital-accent comparison"
PAIRS = [
    ("capital-add", "Ángelis", "Angelis", None),
    ("capital-remove", "Angelis", "Ángelis", None),
    ("comma-coexists", "Ábraham,", "Abraham", None),
    ("case-coexists", "Ángelis", "angelis", None),
    ("diaeresis-outside-acute-scope", "Éphraim,", "Ephraïm,", None),
    ("literal-support", "Ídeo", "Ídeo", None),
    ("decomposed-acute", "A\u0301ngelis", "Angelis", None),
    ("corpus-christi-body", "Córporis", "Corporis", LOWER),
    ("corpus-christi-blood", "Sánguinis", "Sanguinis", LOWER),
    ("lent-ii", "Dóminum", "Dominum", LOWER),
    ("septuagesima", "Símile", "Simile", LOWER),
    ("former-trinity-pair", "Omnípotens", "Omnipotens", LOWER),
    ("mixed-case-lower-acute", "únitas:", "Unitas:", LOWER),
    ("accent-shifts-to-lower", "Ángelis", "Angélis", LOWER),
    ("capital-plus-lower-acute", "Ángélis", "Angelis", LOWER),
    ("comma-alone", "Ángelis,", "Ángelis", UNCHANGED),
    ("case-alone", "Angelis", "angelis", UNCHANGED),
    ("different-word", "Ángelis", "Homines", UNALIGNED),
]
DIGITAL = [
    pytest.param(row, id=f"{row['text']}-{row['at']}")
    for row in FIXTURE["digital_accent_corrections"]
]
COMMA = [
    pytest.param(row, id=f"{row['text']}-{row['at']}") for row in FIXTURE["comma_descriptions"]
]
COLLATIONS = [pytest.param(row, id=row["id"]) for row in FIXTURE["collations"]]
SUPPORT = [
    ("ordinarium.confiteor", 3, "w038", "handmissal-eo", "Ídeo"),
    ("ordinarium.confiteor-sacerdotis", 3, "w038", "handmissal-eo", "Ídeo"),
    ("ordinarium.evangelium-ultimum", 1, "w034", "handmissal-eo", "Ómnia"),
]


def control_entry(ours, reading, cls="capital-accent"):
    return {"at": "w001", "ours": ours, "witnesses": {"do": reading}, "class": cls, "ruling": "R."}


def write_apparatus(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def one_entry_apparatus(tmp_path, entry):
    value = {"adjudicated": [deepcopy(entry)]}
    value["summary"] = derived_summary(value)
    return write_apparatus(tmp_path / "apparatus.json", value)


def lower_acute_mutant(token):
    """The token with an acute added to its first unaccented lowercase vowel."""
    decomposed = unicodedata.normalize("NFD", token)
    for position, character in enumerate(decomposed):
        if character in "aeiouy" and decomposed[position + 1 : position + 2] != "\u0301":
            return decomposed[: position + 1] + "\u0301" + decomposed[position + 1 :]
    raise AssertionError(f"no unaccented lowercase vowel in {token!r}")


def apparatus_path(text):
    return ROOT / f"witnesses/{text}/apparatus.json"


def apparatus(text):
    return json.loads(apparatus_path(text).read_text(encoding="utf-8"))


def collation_row(text):
    return next(row for row in FIXTURE["collations"] if row["text"] == text)


def assert_faces(row):
    """Canonical face, digital transcript locus and pinned raw source line of one entry."""
    core = store.core(ROOT, row["text"])
    selected = bindings.digest(bindings.selected_text(core))
    assert selected == collation_row(row["text"])["selected_text_sha256"]
    tokens = corpus_tokens(expand_core(core))
    assert tokens[row["canonical_ordinal"] - 1] == (row["at"], row["ours"])
    path = ROOT / f"witnesses/{row['text']}/do.txt"
    _metadata, body = load_witness(path)
    assert len(body.split()) == len(tokens)
    assert body.split()[row["canonical_ordinal"] - 1] == row["do"]
    line = path.read_text(encoding="utf-8").splitlines()[row["do_line"] - 1]
    assert line.split()[row["do_word_in_line"] - 1] == row["do"]
    registry = json.loads((ROOT / "witnesses/raw/bindings.json").read_text(encoding="utf-8"))
    archive = registry["archives"][row["raw_archive"]]
    raw = (ROOT / archive["path"]).read_bytes()
    assert archive["sha256"] == row["raw_sha256"] == hashlib.sha256(raw).hexdigest()
    window = row["raw_context"].split()
    found = [
        number
        for number, text in enumerate(raw.decode("utf-8").split("\n"), 1)
        for start in range(len(text.split()))
        if text.split()[start : start + len(window)] == window
    ]
    assert found == [row["raw_line"]], "one exact context window in the pinned raw source"
    assert window[row["raw_word_in_context"] - 1] == row["do"]


@pytest.mark.parametrize(
    ("ours", "theirs", "expected"), [pytest.param(*pair[1:], id=pair[0]) for pair in PAIRS]
)
def test_unicode_pair_control_through_the_ordinary_apparatus_route(
    ours, theirs, expected, tmp_path
):
    assert capital_accent_issue(ours, theirs) == expected
    owned = [] if expected is None else [f"apparatus.adjudicated[0] witness 'do': {expected}"]
    assert lint_apparatus_summary(one_entry_apparatus(tmp_path, control_entry(ours, theirs))) == (
        owned
    )
    # The condition belongs to the class, not to the pair.
    accent = control_entry(ours, theirs, "accent")
    assert lint_apparatus_summary(one_entry_apparatus(tmp_path, accent)) == []
    if expected is None:
        mutant = lower_acute_mutant(ours)
        assert mutant != ours
        path = one_entry_apparatus(tmp_path, control_entry(mutant, theirs))
        assert lint_apparatus_summary(path) == [f"apparatus.adjudicated[0] witness 'do': {LOWER}"]
    assert lint_apparatus_summary(one_entry_apparatus(tmp_path, control_entry(ours, theirs))) == (
        owned
    )


@pytest.mark.parametrize("row", DIGITAL)
def test_digital_acute_on_a_lowercase_vowel_is_an_accent_entry(row, tmp_path):
    value = apparatus(row["text"])
    original = deepcopy(value)
    assert value["adjudicated"][row["index"]] == {
        "at": row["at"],
        "ours": row["ours"],
        "witnesses": {"do": row["do"]},
        "class": "accent",
        "ruling": FIXTURE["accent_correction_ruling"],
    }
    assert_faces(row)
    assert lint_apparatus_summary(apparatus_path(row["text"])) == []
    reclassified = deepcopy(value)
    reclassified["adjudicated"][row["index"]]["class"] = "capital-accent"
    reclassified["summary"] = derived_summary(reclassified)
    path = write_apparatus(tmp_path / "apparatus.json", reclassified)
    assert lint_apparatus_summary(path) == [
        f"apparatus.adjudicated[{row['index']}] witness 'do': {LOWER}"
    ]
    assert lint_apparatus_summary(write_apparatus(path, value)) == []
    assert value == original


def assert_comma_entry(row, value):
    assert value["adjudicated"][row["index"]] == {
        "at": row["at"],
        "ours": row["ours"],
        "witnesses": {"do": row["do"]},
        "class": "capital-accent",
        "ruling": row["ruling"],
    }, "comma description names both differences"


@pytest.mark.parametrize("row", COMMA)
def test_capital_acute_and_printed_comma_are_both_described(row):
    value = apparatus(row["text"])
    original = deepcopy(value)
    assert_comma_entry(row, value)
    printed = value["adjudicated"][row["mr_index"]]
    assert (printed["at"], printed["ours"], printed["class"]) == (
        row["at"],
        row["ours"],
        "capital-accent",
    )
    assert printed["witnesses"] == {"mr": row["mr"]}
    assert_faces(row)
    metadata, body = load_witness(ROOT / f"witnesses/{row['text']}/mr.txt")
    assert body.split()[row["canonical_ordinal"] - 1] == row["mr"]
    assert metadata["location"].startswith(f"printed {row['printed']};")
    assert row["ours"].endswith(",") and row["mr"].endswith(",") and not row["do"].endswith(",")
    # The guard accepts both readings and both rulings: it does not judge prose.
    assert capital_accent_issue(row["ours"], row["do"]) is None
    assert capital_accent_issue(row["ours"], row["mr"]) is None
    assert lint_apparatus_summary(apparatus_path(row["text"])) == []
    withdrawn = deepcopy(value)
    withdrawn["adjudicated"][row["index"]]["ruling"] = DEPRECATED_ACCENT_RULING
    assert capital_accent_positions(withdrawn) == [] == capital_accent_positions(value)
    with pytest.raises(AssertionError, match=r"^comma description names both differences"):
        assert_comma_entry(row, withdrawn)
    assert_comma_entry(row, value)
    assert value == original


def assert_trinity_source(directory):
    text = (directory / "mr.txt").read_text(encoding="utf-8")
    _metadata, body = load_witness(directory / "mr.txt")
    assert body.startswith(TRINITY["opening"]) and TRINITY["former_opening"] not in body, (
        "trinity opening follows the printed page"
    )
    header = [line for line in text.splitlines() if line.startswith("#")]
    assert header == [*TRINITY["preceding_header"], TRINITY["correction"]], (
        "trinity additive correction note"
    )
    value = json.loads((directory / "apparatus.json").read_text(encoding="utf-8"))
    assert all(entry["at"] != "w001" for entry in value["adjudicated"]), (
        "trinity phantom variant absent"
    )
    assert bindings.digest(value["adjudicated"]) == TRINITY["adjudicated_sha256"], (
        "trinity other records"
    )
    assert value["summary"] == derived_summary(value) == TRINITY["summary"], "trinity summary"


def test_trinity_collect_opening_binds_the_registered_page_evidence(tmp_path):
    text = TRINITY["text"]
    directory = ROOT / "witnesses" / text
    assert_trinity_source(directory)
    graph = json.loads((ROOT / "bibliography/graph.json").read_text(encoding="utf-8"))
    witness = next(row for row in graph["witnesses"] if row["id"] == TRINITY["witness"])
    use = next(row for row in graph["uses"] if row["id"] == TRINITY["use"])
    assert witness["use"] == use["id"] and witness["review"] == {"status": "pending"}
    assert use["evidence_sha256"] == TRINITY["evidence_sha256"]
    assert (use["locator"]["printed"], use["locator"]["scan"]) == (
        TRINITY["printed"],
        TRINITY["scan"],
    )
    current_mr = (directory / "mr.txt").read_text(encoding="utf-8")
    assert witness["transcription_sha256"] == TRINITY["transcription_sha256"]
    assert bindings.transcript_digest(current_mr) == TRINITY["transcription_sha256"]
    core = store.core(ROOT, text)
    snapshot = bindings._SourceSnapshot(ROOT, graph)
    subject = bindings._witness_subject(ROOT, witness, core, snapshot, reviewable=False)
    assert subject["source_uses"][use["id"]]["use"]["evidence_sha256"] == TRINITY["evidence_sha256"]
    doc = expand_core(core)
    assert corpus_tokens(doc)[0] == ("w001", TRINITY["opening"].split()[0])
    assert collate(doc, directory)[0] == []
    assert lint_apparatus_summary(directory / "apparatus.json") == []

    copy = tmp_path / text
    shutil.copytree(directory, copy)
    current_apparatus = json.loads((directory / "apparatus.json").read_text(encoding="utf-8"))
    former_mr = current_mr.replace("\n" + TRINITY["opening"], "\n" + TRINITY["former_opening"], 1)
    assert former_mr != current_mr
    phantom = deepcopy(current_apparatus)
    phantom["adjudicated"].insert(0, deepcopy(TRINITY["withdrawn_entry"]))
    phantom["summary"] = derived_summary(phantom)

    def put(transcript, value):
        (copy / "mr.txt").write_text(transcript, encoding="utf-8")
        write_apparatus(copy / "apparatus.json", value)

    unadjudicated = (
        "mr: UNADJUDICATED variant at w001: ours='Omnípotens' witness='Omnipotens' — "
        "record a ruling in apparatus.json or fix the text"
    )
    stale = (
        "apparatus entry w001/mr matches no variant this witness produces "
        "— stale ruling: delete it, or name the witness that does produce it"
    )
    guard = [f"apparatus.adjudicated[0] witness 'mr': {LOWER}"]
    put(former_mr, current_apparatus)
    assert collate(doc, copy)[0] == [unadjudicated]
    with pytest.raises(AssertionError, match=r"^trinity opening follows the printed page"):
        assert_trinity_source(copy)
    put(current_mr, phantom)
    assert collate(doc, copy)[0] == [stale]
    assert lint_apparatus_summary(copy / "apparatus.json") == guard
    with pytest.raises(AssertionError, match=r"^trinity phantom variant absent"):
        assert_trinity_source(copy)
    # The former pair agrees with itself: only the class guard and the pinned
    # reading of the page distinguish it from the corrected source.
    put(former_mr, phantom)
    assert collate(doc, copy)[0] == []
    assert lint_apparatus_summary(copy / "apparatus.json") == guard
    with pytest.raises(AssertionError, match=r"^trinity opening follows the printed page"):
        assert_trinity_source(copy)
    put(current_mr, current_apparatus)
    assert collate(doc, copy)[0] == []
    assert lint_apparatus_summary(copy / "apparatus.json") == []
    assert_trinity_source(copy)


def test_every_current_capital_accent_reading_passes_the_ordinary_guard():
    entries = readings = declared = 0
    support = []
    for path in sorted((ROOT / "witnesses").glob("*/apparatus.json")):
        assert lint_apparatus_summary(path) == [], path.parent.name
        raw = path.read_text(encoding="utf-8")
        declared += raw.count('"class": "capital-accent"')
        for index, entry in enumerate(json.loads(raw)["adjudicated"]):
            if entry["class"] != "capital-accent":
                continue
            entries += 1
            assert isinstance(entry["ours"], str) and entry["witnesses"]
            for witness, reading in entry["witnesses"].items():
                readings += 1
                assert capital_accent_issue(entry["ours"], reading) is None
                if reading == entry["ours"]:
                    support.append((path.parent.name, index, entry["at"], witness, reading))
    # Every declared row was read; none was skipped to pass.
    assert entries == declared and entries >= 295 and readings >= 401
    assert set(SUPPORT) <= set(support)
    corrected = [(row["text"], row["at"]) for row in FIXTURE["digital_accent_corrections"]]
    for text, at in [*corrected, (TRINITY["text"], "w001")]:
        assert all(
            entry["class"] != "capital-accent"
            for entry in apparatus(text)["adjudicated"]
            if entry["at"] == at
        )


@pytest.fixture(scope="module")
def sources():
    graph = json.loads((ROOT / "bibliography/graph.json").read_text(encoding="utf-8"))
    return graph, bindings._SourceSnapshot(ROOT, graph)


@pytest.mark.parametrize("row", COLLATIONS)
def test_affected_collation_binds_its_corrected_apparatus(row, sources):
    graph, snapshot = sources
    found = [record for record in graph["collations"] if record["id"] == row["id"]]
    assert len(found) == 1
    current = found[0]
    original = deepcopy(current)
    assert current["text"] == row["text"] and current["review"] == {"status": "pending"}
    value = apparatus(row["text"])
    assert current["apparatus"] == row["summary"] == derived_summary(value)
    assert current["apparatus_sha256"] == row["after_sha256"] == bindings.digest(value)
    core = store.core(ROOT, row["text"])
    selected = bindings.digest(bindings.selected_text(core))
    assert current["selected_text_sha256"] == row["selected_text_sha256"] == selected
    records = {r["id"]: r for r in graph["witnesses"] if r["id"] in current["witnesses"]}
    assert {key: bindings.digest(r) for key, r in records.items()} == row["witness_records_sha256"]
    witnesses = {
        key: bindings._witness_subject(ROOT, record, core, snapshot, reviewable=False)
        for key, record in records.items()
    }
    subject = bindings._collation_subject(ROOT, current, core, witnesses, reviewable=False)
    assert subject["collation"] == {k: v for k, v in current.items() if k != "review"}
    stale = deepcopy(current)
    stale["apparatus_sha256"] = row["before_sha256"]
    with pytest.raises(
        bindings.BindingError, match=r"^apparatus_sha256 differs from the complete apparatus$"
    ):
        bindings._collation_subject(ROOT, stale, core, witnesses, reviewable=False)
    if row["before_summary"] != row["summary"]:
        stale = deepcopy(current)
        stale["apparatus"] = row["before_summary"]
        with pytest.raises(
            bindings.BindingError,
            match=r"^apparatus summary differs from the actual adjudicated entries$",
        ):
            bindings._collation_subject(ROOT, stale, core, witnesses, reviewable=False)
    if TRINITY["witness"] in records:
        transcript = (ROOT / f"witnesses/{row['text']}/mr.txt").read_text(encoding="utf-8")
        record = deepcopy(records[TRINITY["witness"]])
        assert record["transcription_sha256"] == bindings.transcript_digest(transcript)
        assert record["transcription_sha256"] == TRINITY["transcription_sha256"]
        record["transcription_sha256"] = TRINITY["former_transcription_sha256"]
        with pytest.raises(
            bindings.BindingError,
            match=r"^transcription_sha256 differs from the complete bound transcript$",
        ):
            bindings._witness_subject(ROOT, record, core, snapshot, reviewable=False)
    assert bindings._collation_subject(ROOT, current, core, witnesses, reviewable=False) == subject
    assert current == original

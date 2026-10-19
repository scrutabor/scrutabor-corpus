"""The priest-alone blessing binds its own print, digital line and apparatus."""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from build_reader import bibliography
from build_reader.bibliography_bindings import (
    BindingError,
    collation_subject,
    digest,
    selected_text,
    transcript_digest,
    validate_bindings,
    witness_subject,
)
from checks.collate import collate, load_witness
from checks.raw_binding import resolve_binding

ROOT = Path(__file__).resolve().parents[2]
TEXT = "ordinarium.iube-domine-benedicere"
CORE = "texts/ordinarium/iube-domine-benedicere.json"
WITNESSES = f"witnesses/{TEXT}"
RAW = "witnesses/raw/missa-44667ff/Ordo/Ordo.txt"
REVISION = "44667ff518b8ff1439780470828b39714f5306a2"
ARCHIVE_SHA = "a7f63e8030325b809f74dd4587c649bf8eb45cdd150fc9a2817fe2a1ed6a42e3"
B_BODY = (
    "Iube, Dómine, benedícere. Dóminus sit in corde meo, et in lábiis meis: "
    "ut digne et competénter annúntiem Evangélium suum. Amen."
)


def read(root, relative):
    return json.loads((root / relative).read_text(encoding="utf-8"))


def rows(graph, field):
    return [
        row for row in graph[field] if row.get("text", row.get("address", {}).get("text")) == TEXT
    ]


def inventory(witness):
    assert witness["coverage"] == {"kind": "full"}
    assert witness["role"] == (
        "controlling" if witness["transcription"] == "mr" else "derived_comparison"
    )
    assert witness["source_dependencies"] == (
        {
            "uses": [
                f"use.{TEXT}.mr1962-ritual-boundary",
                f"use.{TEXT}.mr1962-ritual-voice",
            ],
            "raw_binding": None,
        }
        if witness["transcription"] == "mr"
        else {"uses": [], "raw_binding": "iube-domine-benedicere-priest"}
    )


def subjects(root, graph):
    doc = read(root, CORE)
    return {row["id"]: witness_subject(root, row, graph, doc) for row in rows(graph, "witnesses")}


def test_selected_twenty_words_keep_b_accidentals_and_three_priest_segments():
    doc = read(ROOT, CORE)
    assert [segment["id"] for segment in doc["segments"]] == ["s01", "s02", "s03"]
    assert [len(segment["words"]) for segment in doc["segments"]] == [3, 16, 1]
    words = [word for segment in doc["segments"] for word in segment["words"]]
    assert [word["id"] for word in words] == [f"w{i:03}" for i in range(1, 21)]
    assert " ".join(word["form"] + word.get("post", "") for word in words) == B_BODY
    for segment in doc["segments"]:
        assert (segment["speaker"], segment["voice"]) == ("sacerdos", "secreto")
        assert "participation" not in segment
        assert not segment.get("delivery")


def test_genuine_raw122_is_twenty_words_and_munda121_stays_separate(blessing_corpus):
    root = blessing_corpus
    raw = (root / RAW).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ARCHIVE_SHA
    lines = raw.decode("utf-8").splitlines()
    blessing = resolve_binding(root / WITNESSES / "do.txt", root)
    munda = resolve_binding(root / "witnesses/ordinarium.munda-cor-meum/do.txt", root)
    assert blessing is not None and munda is not None
    assert blessing.source["contract"] == "raw-reading-5"
    assert blessing.source["binding_id"] == "iube-domine-benedicere-priest"
    assert blessing.source["binding"]["revision"] == REVISION
    assert blessing.spans == ((root / RAW, 122, 122),)
    assert blessing.text == lines[121].removeprefix("v. ")
    assert len(blessing.text.split()) == 20
    assert munda.source["contract"] == "raw-reading-4"
    assert munda.spans == ((root / RAW, 121, 121),) and len(munda.text.split()) == 34
    evidence = blessing.source["binding"]["evidence"]
    assert len(evidence) == 1
    assert evidence[0]["preceding_text"] == {"line": 121, "text": lines[120], "marker": "v"}
    assert munda.text == lines[120].removeprefix("v. ")
    mr_body = load_witness(root / WITNESSES / "mr.txt")[1]
    assert mr_body == B_BODY
    assert [
        (i + 1, a, b)
        for i, (a, b) in enumerate(zip(mr_body.split(), blessing.text.split(), strict=True))
        if a != b
    ] == [(1, "Iube,", "Jube,"), (8, "meo,", "meo")]


@pytest.mark.parametrize(
    "suffix,role",
    [
        ("mr1962-body", "direct_approved_print"),
        ("mr1962-ritual-boundary", "rubric_control"),
        ("mr1962-ritual-voice", "rubric_control"),
        ("do44667ff-body", "derived_digital_collation_aid"),
    ],
)
def test_real_uses_keep_distinct_identity_role_and_exact_locus(suffix, role):
    graph = read(ROOT, "bibliography/graph.json")
    actual = rows(graph, "uses")
    assert {row["id"] for row in actual} == {
        f"use.{TEXT}.{name}"
        for name in (
            "mr1962-body",
            "mr1962-ritual-boundary",
            "mr1962-ritual-voice",
            "do44667ff-body",
        )
    }
    use = next(row for row in actual if row["id"] == f"use.{TEXT}.{suffix}")
    assert use["address"] == {"kind": "text", "text": TEXT} and use["role"] == role
    assert use["decision"] in {"RETAIN", "RETAIN_WITH_CORRECTION"}
    assert use["claim"].strip()
    if suffix.startswith("mr1962"):
        assert (use["edition"], use["digital_item"]) == (
            "edition.missale-romanum.1962-typica",
            "item.missale-romanum.1962-typica.ia",
        )
        if suffix == "mr1962-ritual-voice":
            assert use["locator"]["printed"] == "LIII"
            assert use["locator"]["scan"] == "IA leaf n58; one-based PDF page 59"
            assert use["locator"]["section"] == (
                "Ritus servandus VI.2; celebrant’s Gospel preparation"
            )
            assert use["locator"]["page_url"] == (
                "https://archive.org/details/missale-romanum-1962/page/n58/mode/1up"
            )
            assert use["evidence_sha256"] == (
                "2a36919facc2289b087996678556a69eede8d916177be3a461a6aa2ef7a6b434"
            )
        else:
            assert use["locator"]["printed"] == "223"
            assert use["locator"]["scan"] == "IA leaf n302; one-based PDF page 303"
            assert use["locator"]["page_url"] == (
                "https://archive.org/details/missale-romanum-1962/page/n302/mode/1up"
            )
            assert use["evidence_sha256"] == (
                "f84bcc646cfc3b9908a50a4f86e3d1c0ee21738df7afd9230fd343b801f658ff"
            )
    else:
        assert (use["edition"], use["digital_item"]) == (
            "edition.divinum-officium-missa.44667ff",
            "item.divinum-officium-missa.44667ff.github",
        )
        assert "line 122" in use["locator"]["section"]
        assert use["evidence_sha256"] == ARCHIVE_SHA


def test_two_actual_rulings_and_current_collation_digests(blessing_corpus):
    root = blessing_corpus
    doc, graph = read(root, CORE), read(root, "bibliography/graph.json")
    apparatus = read(root, f"{WITNESSES}/apparatus.json")
    assert [(r["at"], r["ours"], r["witnesses"], r["class"]) for r in apparatus["adjudicated"]] == [
        ("w001", "Iube,", {"do": "Jube,"}, "orthography"),
        ("w008", "meo,", {"do": "meo"}, "punctuation"),
    ]
    errors, warnings, stats = collate(doc, root / WITNESSES)
    assert errors == warnings == []
    assert (
        stats["words"],
        stats["witnesses"],
        stats["orthographic"],
        stats["variants_adjudicated"],
    ) == (20, 2, 1, 1)
    row = rows(graph, "collations")[0]
    assert row["id"] == f"collation.{TEXT}.mr1962-do44667ff"
    assert row["witnesses"] == [f"witness.{TEXT}.do44667ff", f"witness.{TEXT}.mr1962"]
    assert row["selected_text_sha256"] == digest(selected_text(doc))
    assert row["apparatus_sha256"] == digest(apparatus)
    assert row["apparatus"] == {"entries": 2, "classes": ["orthography", "punctuation"]}
    subject = collation_subject(root, row, doc, subjects(root, graph))
    assert subject["contract"] == "collation-review-2"


def test_current_source_subjects_are_real_without_permanent_pending_pin(blessing_corpus):
    root = blessing_corpus
    graph = read(root, "bibliography/graph.json")
    assert len(rows(graph, "witnesses")) == 2 and len(rows(graph, "collations")) == 1
    assert {row["id"] for row in rows(graph, "witnesses")} == {
        f"witness.{TEXT}.do44667ff",
        f"witness.{TEXT}.mr1962",
    }
    assert validate_bindings(root, graph) == []
    current = subjects(root, graph)
    for witness in rows(graph, "witnesses"):
        inventory(witness)
        transcript = root / WITNESSES / f"{witness['transcription']}.txt"
        assert witness["transcription_sha256"] == transcript_digest(
            transcript.read_text(encoding="utf-8")
        )
        assert current[witness["id"]]["contract"] == "witness-review-2"
        if witness["review"]["status"] == "reviewed":
            assert witness["review"]["sha256"] == digest(current[witness["id"]])
    # Exercise withholding on a copy; later genuinely reviewed source records are legal.
    pending = copy.deepcopy(graph)
    for field in ("witnesses", "collations"):
        for row in pending[field]:
            row["review"] = {"status": "pending"}
    assert validate_bindings(root, pending) == []
    projected = next(
        row for row in bibliography.public_text_evidence(pending)["texts"] if row["id"] == TEXT
    )
    assert projected["witnesses"] == [] and "collation" not in projected


@pytest.mark.parametrize("name", ["do44667ff", "mr1962"])
def test_fabricated_review_digest_rejects_exact_source_and_collation_then_restores(
    blessing_corpus, name
):
    root = blessing_corpus
    graph = read(root, "bibliography/graph.json")
    original = copy.deepcopy(graph)
    assert validate_bindings(root, graph) == []
    identifier = f"witness.{TEXT}.{name}"
    witness = next(row for row in graph["witnesses"] if row["id"] == identifier)
    # Intentionally invalid proof on a copy, not a source-review promotion.
    witness["review"] = {"status": "reviewed", "sha256": "0" * 64}
    assert validate_bindings(root, graph) == [
        f"bibliography witness {identifier}: reviewed subject changed; "
        "re-review or mark pending explicitly",
        f"bibliography collation collation.{TEXT}.mr1962-do44667ff: "
        "collation has an unbound or duplicate witness",
    ]
    assert validate_bindings(root, original) == []


@pytest.mark.parametrize(
    "at,fragment",
    [
        ("w001", "SUBSTANTIVE divergence at word 1 (w001)"),
        ("w008", "UNADJUDICATED variant at w008"),
    ],
)
def test_dropping_real_accidental_ruling_rejects_and_exactly_restores(
    blessing_corpus, at, fragment
):
    root = blessing_corpus
    path = root / WITNESSES / "apparatus.json"
    before = path.read_bytes()
    doc = read(root, CORE)
    assert collate(doc, root / WITNESSES)[:2] == ([], [])
    changed = json.loads(before)
    changed["adjudicated"] = [row for row in changed["adjudicated"] if row["at"] != at]
    path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
    try:
        errors, _, _ = collate(doc, root / WITNESSES)
        assert any(fragment in error for error in errors)
    finally:
        path.write_bytes(before)
    assert path.read_bytes() == before
    assert collate(doc, root / WITNESSES)[:2] == ([], [])


def test_complete_header_digest_rejects_changed_current_file_and_restores(blessing_corpus):
    root = blessing_corpus
    graph = read(root, "bibliography/graph.json")
    witness = next(row for row in graph["witnesses"] if row["transcription"] == "mr")
    path = root / WITNESSES / "mr.txt"
    before, doc = path.read_bytes(), read(root, CORE)
    original = witness_subject(root, witness, graph, doc)
    path.write_bytes(before.replace(b"# description:", b"# description: Changed header;", 1))
    try:
        with pytest.raises(BindingError, match="transcription_sha256 differs"):
            witness_subject(root, witness, graph, doc)
    finally:
        path.write_bytes(before)
    assert witness_subject(root, witness, graph, doc) == original


@pytest.mark.parametrize(
    "field,message",
    [
        ("selected_text_sha256", "current Latin/ritual subject"),
        ("apparatus_sha256", "complete apparatus"),
    ],
)
def test_null_draft_identity_is_not_a_valid_assembled_collation(blessing_corpus, field, message):
    root = blessing_corpus
    graph, doc = read(root, "bibliography/graph.json"), read(root, CORE)
    row = rows(graph, "collations")[0]
    original = copy.deepcopy(row)
    bound = subjects(root, graph)
    before = collation_subject(root, row, doc, bound)
    row[field] = None
    with pytest.raises(BindingError, match=message):
        collation_subject(root, row, doc, bound)
    row.clear()
    row.update(original)
    assert collation_subject(root, row, doc, bound) == before


@pytest.mark.parametrize("missing", ["mr1962-ritual-boundary", "mr1962-ritual-voice"])
def test_required_print_rubric_dependency_is_a_targeted_inventory_invariant(
    blessing_corpus, missing
):
    graph = read(blessing_corpus, "bibliography/graph.json")
    witness = next(row for row in graph["witnesses"] if row["transcription"] == "mr")
    before = copy.deepcopy(witness)
    inventory(witness)
    witness["source_dependencies"]["uses"].remove(f"use.{TEXT}.{missing}")
    with pytest.raises(AssertionError):
        inventory(witness)
    witness.clear()
    witness.update(before)
    inventory(witness)


@pytest.mark.parametrize("suffix", ["mr1962-ritual-boundary", "mr1962-ritual-voice"])
def test_changed_rubric_claim_changes_complete_source_and_collation_subjects(
    blessing_corpus, suffix
):
    root = blessing_corpus
    graph, doc = read(root, "bibliography/graph.json"), read(root, CORE)
    original = copy.deepcopy(graph)
    before = subjects(root, graph)
    row = rows(graph, "collations")[0]
    collation = collation_subject(root, row, doc, before)
    use = next(row for row in graph["uses"] if row["id"] == f"use.{TEXT}.{suffix}")
    use["claim"] += " Test claim change."
    changed = subjects(root, graph)
    assert digest(changed[f"witness.{TEXT}.mr1962"]) != digest(before[f"witness.{TEXT}.mr1962"])
    assert changed[f"witness.{TEXT}.do44667ff"] == before[f"witness.{TEXT}.do44667ff"]
    assert digest(collation_subject(root, row, doc, changed)) != digest(collation)
    assert subjects(root, original) == before
    assert collation_subject(root, original["collations"][0], doc, before) == collation


def test_current_apparatus_ruling_is_bound_not_only_its_reading_then_restores(blessing_corpus):
    root = blessing_corpus
    graph, doc = read(root, "bibliography/graph.json"), read(root, CORE)
    row, bound = rows(graph, "collations")[0], subjects(root, graph)
    before_subject = collation_subject(root, row, doc, bound)
    path = root / WITNESSES / "apparatus.json"
    before = path.read_bytes()
    changed = json.loads(before)
    changed["adjudicated"][0]["ruling"] += " Test ruling change."
    path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
    try:
        with pytest.raises(BindingError, match="complete apparatus"):
            collation_subject(root, row, doc, bound)
    finally:
        path.write_bytes(before)
    assert collation_subject(root, row, doc, bound) == before_subject


@pytest.mark.parametrize(
    "change,message",
    [
        ("munda-key", "declared raw binding differs"),
        ("munda-reading-hash", "neither a bound archive"),
        ("digital-revision", "revision or kind differs"),
    ],
)
def test_digital_subject_rejects_cross_prayer_or_revision_binding_and_restores(
    blessing_corpus, change, message
):
    root = blessing_corpus
    graph, doc = read(root, "bibliography/graph.json"), read(root, CORE)
    before = copy.deepcopy(graph)
    witness = next(row for row in graph["witnesses"] if row["transcription"] == "do")
    original = witness_subject(root, witness, graph, doc)
    if change == "munda-key":
        witness["source_dependencies"]["raw_binding"] = "munda-cor-meum-priest"
    elif change == "munda-reading-hash":
        munda = resolve_binding(root / "witnesses/ordinarium.munda-cor-meum/do.txt", root)
        use = next(row for row in graph["uses"] if row["id"] == witness["use"])
        use["evidence_sha256"] = hashlib.sha256((munda.text + "\n").encode()).hexdigest()
    else:
        item = next(
            row
            for row in graph["digital_items"]
            if row["id"] == "item.divinum-officium-missa.44667ff.github"
        )
        item["revision"] = "0" * 40
    with pytest.raises(BindingError, match=message):
        witness_subject(root, witness, graph, doc)
    graph = before
    witness = next(row for row in graph["witnesses"] if row["transcription"] == "do")
    assert witness_subject(root, witness, graph, doc) == original

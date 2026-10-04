"""Preserve the Secret's literal composite, dependencies and ritual boundaries."""

import hashlib
import json
from pathlib import Path

import pytest

from build_reader import bibliography, store
from build_reader.bibliography_bindings import BindingError, witness_subject
from checks import raw_binding
from checks.collate import collate, load_witness

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.dominica-vii-post-pentecosten-secreta"
FOLDER = ROOT / "witnesses" / TEXT
PREFIX = f"use.{TEXT}."
BODY = (
    "Deus, qui legálium differéntiam hostiárum uníus sacrifícii perfectióne sanxísti: "
    "áccipe sacrifícium a devótis tibi fámulis, et pari benedictióne, sicut múnera Abel, "
    "sanctífica; ut, quod sínguli obtulérunt ad maiestátis tuæ honórem, "
    "cunctis profíciat ad salútem."
)
FORMULA = (
    "Per Dominum nostrum Iesum Christum Filium tuum, qui tecum vivit et regnat in "
    "unitate Spiritus Sancti, Deus, per omnia sæcula sæculorum. Amen;"
)
PAGES = [
    ("mr1962", 462, "f2dcd76ad1929745b0835a63448a59d716726dcbc1fb68665c6194fd2bb1f706"),
    (
        "conclusion-rg115a.mr1962",
        22,
        "b511f3aa4016b387d2995b5089e15aa62593c04118052ef48dcc09352fcf769c",
    ),
    (
        "oration-boundaries.mr1962",
        37,
        "6c08d654bc198380aad5673bc6f06fdb44076acdfff67087e74aaf4943d23946",
    ),
    (
        "ordo-secret-order.mr1962",
        304,
        "c8e1c105fbccab5b133d072bcdc255ff482824182be5e53597e5d2bfbb94e3ee",
    ),
    (
        "ordo-secret-response.mr1962",
        305,
        "c8a123467dd47ace390100a021fdcdd61752a5c42635583b92d72cd636027f58",
    ),
]


def graph():
    return json.loads((ROOT / "bibliography/graph.json").read_text())


def use(data, suffix):
    return next(u for u in data["uses"] if u["id"] == PREFIX + suffix)


def witness(data, name):
    return next(w for w in data["witnesses"] if w["text"] == TEXT and w["transcription"] == name)


def assert_printed_bindings(data):
    # These original-page bindings are a content-specific control. A generic
    # schema cannot infer a missing source or the content of a checksum.
    for suffix, leaf, digest in PAGES:
        item = use(data, suffix)
        assert item["evidence_sha256"] == digest
        assert item["locator"]["page_url"] == (
            f"https://archive.org/details/missale-romanum-1962/page/n{leaf}/mode/1up"
        )
        assert item["edition"] == "edition.missale-romanum.1962-typica"
        assert item["digital_item"] == "item.missale-romanum.1962-typica.ia"
    assert witness(data, "mr")["source_dependencies"] == {
        "uses": sorted(PREFIX + suffix for suffix, _, _ in PAGES if suffix != "mr1962"),
        "raw_binding": None,
    }


def test_selected_proper_and_three_ritual_segments():
    segments = store.core(ROOT, TEXT)["segments"]
    assert [(s["id"], s["speaker"], s["voice"], len(s["words"])) for s in segments] == [
        ("s01", "sacerdos", "secreto", 51),
        ("s02", "sacerdos", "clara", 4),
        ("s03", "minister", "clara", 1),
    ]
    assert " ".join(w["form"] + w.get("post", "") for w in segments[0]["words"][:34]) == BODY
    assert " ".join(w["form"] for w in segments[1]["words"]) == "per ómnia sǽcula sæculórum"
    assert segments[2]["words"][0]["form"] == "Amen"


def test_literal_approved_print_composite_is_not_a_normalized_ending():
    meta, body = load_witness(FOLDER / "mr.txt")
    assert body == BODY + " " + FORMULA
    assert len(body.split()) == 56
    assert "Benziger 1962 approved edition iuxta typicam" in meta["description"]
    assert "proper's Per Dóminum cue is replaced" in meta["assembly"]
    assert "not two independent editions" in meta["assembly"]
    assert "does not print the full ending" in meta["note"]


def test_exact_raw_archive_reference_and_complete_resolution():
    registry = raw_binding.load_registry(ROOT)
    archive = registry["archives"]["pentecost-vii"]
    raw = (ROOT / archive["path"]).read_bytes()
    assert len(raw) == 3135
    assert (
        hashlib.sha256(raw).hexdigest()
        == archive["sha256"]
        == ("9cfeb0c8e239a739a62818cd6db3a74ce3d4034bc948bab1d39694be0b64d46f")
    )
    binding = registry["bindings"]["pentecost-vii-secret"]
    assert binding["references"] == [
        {"archive": "pentecost-vii", "line": 49, "text": "$Per Dominum", "target": 1}
    ]
    assert binding["reading"] == [
        {"archive": "pentecost-vii", "first": 48, "last": 48},
        {"archive": "prayers", "first": 96, "last": 97},
    ]
    resolved = raw_binding.resolve_binding(FOLDER / "do.txt", ROOT)
    assert resolved is not None
    meta, body = load_witness(FOLDER / "do.txt")
    assert resolved.text == body and len(body.split()) == 56
    assert body.split()[5:10] == ["unius", "sacrifícii", "perfectione", "sanxísti:", "accipe"]
    assert body.split()[37:42] == ["Jesum", "Christum,", "Fílium", "tuum:", "qui"]
    assert body.endswith("Spíritus Sancti Deus, per ómnia sǽcula sæculórum. Amen.")
    assert meta["raw-binding"] == "pentecost-vii-secret"


def test_each_source_has_its_actual_scope_and_page_binding():
    data = graph()
    assert_printed_bindings(data)
    assert use(data, "mr1962")["role"] == "direct_approved_print"
    assert "34-word body and abbreviated" in use(data, "mr1962")["claim"]
    assert use(data, "do44667ff")["role"] == "derived_digital_collation_aid"
    assert witness(data, "do")["source_dependencies"] == {
        "uses": [PREFIX + "conclusion-macro.do44667ff"],
        "raw_binding": "pentecost-vii-secret",
    }
    for suffix in ("conclusion-rg115a.mr1962", "conclusion-macro.do44667ff"):
        assert use(data, suffix)["address"] == {"kind": "word", "text": TEXT, "word": "w035"}
    assert use(data, "oration-boundaries.mr1962")["locator"]["section"] == "RG480-481"
    assert "not their concluding response" in use(data, "ordo-secret-order.mr1962")["claim"]
    assert "Christmas body is not selected" in use(data, "ordo-secret-response.mr1962")["claim"]


@pytest.mark.parametrize("mutation", ["missing-formula", "wrong-page"])
def test_exact_source_contract_catches_structurally_valid_false_dependencies(mutation):
    data = graph()
    assert_printed_bindings(data)
    if mutation == "missing-formula":
        witness(data, "mr")["source_dependencies"]["uses"].remove(
            PREFIX + "conclusion-rg115a.mr1962"
        )
    else:
        use(data, "ordo-secret-response.mr1962")["evidence_sha256"] = use(
            data, "ordo-secret-order.mr1962"
        )["evidence_sha256"]
    # Explicitly establish why the original-page contract above is necessary.
    assert witness_subject(ROOT, witness(data, "mr"), data, store.core(ROOT, TEXT))["contract"] == (
        "witness-review-2"
    )
    with pytest.raises(AssertionError):
        assert_printed_bindings(data)


def test_different_edition_dependency_is_not_an_independent_print_witness():
    data = graph()
    dependencies = witness(data, "mr")["source_dependencies"]["uses"]
    dependencies.append(PREFIX + "conclusion-macro.do44667ff")
    dependencies.sort()
    with pytest.raises(BindingError, match="supplemental source belongs to another edition"):
        witness_subject(ROOT, witness(data, "mr"), data, store.core(ROOT, TEXT))


def test_every_literal_difference_has_its_own_apparatus_reading():
    core = store.core(ROOT, TEXT)
    words = [w for s in core["segments"] for w in s["words"]]
    actual = []
    for name in ("do", "mr"):
        _, body = load_witness(FOLDER / f"{name}.txt")
        for word, raw in zip(words, body.split(), strict=True):
            selected = word["form"] + word.get("post", "")
            if selected != raw:
                actual.append((word["id"], name, selected, raw))
    apparatus = json.loads((FOLDER / "apparatus.json").read_text())
    declared = [
        (e["at"], name, e["ours"], raw)
        for e in apparatus["adjudicated"]
        for name, raw in e["witnesses"].items()
    ]
    assert sorted(actual) == sorted(declared)
    assert len(actual) == 18 and len({r[0] for r in actual}) == 17
    errors, warnings, stats = collate(core, FOLDER)
    assert errors == warnings == []
    assert stats["words"] == 56 and stats["witnesses"] == 2
    assert stats["variants_adjudicated"] == 16 and stats["orthographic"] == 2
    assert stats["substantive_variants"] == 0


@pytest.mark.parametrize("index", range(18))
def test_each_missing_apparatus_entry_is_rejected(tmp_path, index):
    for name in ("do.txt", "mr.txt", "apparatus.json"):
        (tmp_path / name).write_bytes((FOLDER / name).read_bytes())
    apparatus = json.loads((FOLDER / "apparatus.json").read_text())
    entry = apparatus["adjudicated"].pop(index)
    (tmp_path / "apparatus.json").write_text(json.dumps(apparatus, ensure_ascii=False))
    errors, _, _ = collate(store.core(ROOT, TEXT), tmp_path)
    witness_name = next(iter(entry["witnesses"]))
    assert any(entry["at"] in error and witness_name in error for error in errors), errors


def test_review_status_is_not_promoted_by_correcting_source_dependencies():
    data, languages = bibliography.load(ROOT)
    assert bibliography.validate(ROOT, data, languages) == []
    for name in ("do", "mr"):
        assert witness(data, name)["review"] == {"status": "pending"}
    collation = next(c for c in data["collations"] if c["text"] == TEXT)
    assert collation["review"] == {"status": "pending"}
    row = next(r for r in bibliography.public_text_evidence(data)["texts"] if r["id"] == TEXT)
    assert row["witnesses"] == [] and "collation" not in row

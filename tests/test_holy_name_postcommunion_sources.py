"""Bind the Postcommunion to its own pages, invocation and composite seams."""

import hashlib
import json
from pathlib import Path

import pytest

from build_reader import bibliography, store
from build_reader.bibliography_bindings import BindingError, witness_subject
from checks import raw_binding
from checks.collate import collate, load_witness
from checks.layout import CORPUS

TEXT = "proprium.sanctissimi-nominis-iesu-postcommunio"
FOLDER = CORPUS / "witnesses" / TEXT
PREFIX = f"use.{TEXT}."
PAGES = [
    ("mr1962", 114, "ab007486404889c449fddf69d8327921f4c712f9d58bea6579bafb458d15f773"),
    (
        "conclusion-rule.mr1962",
        22,
        "b511f3aa4016b387d2995b5089e15aa62593c04118052ef48dcc09352fcf769c",
    ),
    (
        "conclusion-selection.mr1962",
        23,
        "db99d725287dbdb233ff9c22c94cd027ec6b5105f2f64817ec828778805ff132",
    ),
    (
        "conclusion-middle.mr1962",
        202,
        "38c3d082c3cf4e7f82f87cf9f87595e62e3765cb625c1305005f1435cc985774",
    ),
    (
        "conclusion-terminal.mr1962",
        305,
        "c8a123467dd47ace390100a021fdcdd61752a5c42635583b92d72cd636027f58",
    ),
    (
        "oration-boundaries.mr1962",
        38,
        "a6d9b2554ebb911a8a6ae9ea6e6e5e882307bedeab8e326ae2f7ef602ec2fd7e",
    ),
    (
        "postcommunion-delivery.mr1962",
        39,
        "c03be5250068f8c9c262983bc7689a18d0180b88b0c4476d21fac383c8f07993",
    ),
]


def graph():
    return json.loads((CORPUS / "bibliography/graph.json").read_text())


def use(data, suffix):
    return next(u for u in data["uses"] if u["id"] == PREFIX + suffix)


def witness(data, name):
    return next(w for w in data["witnesses"] if w["text"] == TEXT and w["transcription"] == name)


def assert_dependencies(data):
    # A schema cannot read a page image; these are exact inspected fixtures.
    for suffix, leaf, digest in PAGES:
        value = use(data, suffix)
        assert value["evidence_sha256"] == digest
        assert value["locator"]["page_url"] == (
            f"https://archive.org/details/missale-romanum-1962/page/n{leaf}/mode/1up"
        )
        assert value["edition"] == "edition.missale-romanum.1962-typica"
        assert value["digital_item"] == "item.missale-romanum.1962-typica.ia"
    assert witness(data, "mr")["source_dependencies"] == {
        "uses": sorted(PREFIX + suffix for suffix, _, _ in PAGES if suffix != "mr1962"),
        "raw_binding": None,
    }


def test_body_and_expansion_are_not_one_continuous_printing():
    data = graph()
    assert_dependencies(data)
    assert len([u for u in data["uses"] if u["address"].get("text") == TEXT]) == 9
    for suffix, _, _ in PAGES:
        direct = suffix in {"mr1962", "conclusion-middle.mr1962", "conclusion-terminal.mr1962"}
        assert use(data, suffix)["role"] == (
            "direct_approved_print" if direct else "official_liturgical_context"
        )
    assert "does not print the complete expanded conclusion" in use(data, "mr1962")["claim"]
    for suffix in ("oration-boundaries.mr1962", "postcommunion-delivery.mr1962"):
        assert use(data, suffix)["address"] == {"kind": "segment", "text": TEXT, "segment": "s01"}
    assert "RG 505" in use(data, "oration-boundaries.mr1962")["claim"]
    assert "RG 511 i" in use(data, "postcommunion-delivery.mr1962")["claim"]
    assert "not the Secret's quiet-body" in use(data, "postcommunion-delivery.mr1962")["claim"]


def test_literal_printed_seams_do_not_change_the_selected_latin_or_delivery():
    core = store.core(CORPUS, TEXT)
    assert [(s["speaker"], s["voice"], len(s["words"])) for s in core["segments"]] == [
        ("sacerdos", "clara", 76),
        ("minister", "clara", 1),
    ]
    assert core["segments"][0]["delivery"]["cantu"] == {"speaker": "sacerdos", "voice": "cantus"}
    words = [w for s in core["segments"] for w in s["words"]]
    selected = " ".join(w["form"] + w.get("post", "") for w in words)
    meta, printed = load_witness(FOLDER / "mr.txt")
    assert len(printed.split()) == 77
    assert printed == selected.replace("Deus, per ómnia", "Deus. Per ómnia")
    assert printed.startswith("Omnípotens")
    assert "Editio iuxta typicam" in meta["description"]
    assert "w057–w072 from p. 123" in meta["composite"]
    assert "w073–w077 from p. 226" in meta["composite"]


def test_exact_postcommunion_call_and_raw_branch_are_bound():
    registry = raw_binding.load_registry(CORPUS)
    binding = registry["bindings"]["holy-name-postcommunion"]
    assert binding["references"] == [
        {"archive": "holy-name", "line": 69, "text": "$Per eumdem", "target": 1}
    ]
    assert binding["evidence"] == [
        {
            "archive": "holy-name",
            "first": 68,
            "last": 69,
            "section": "Postcommunio",
            "section_line": 67,
        },
        {
            "archive": "prayers",
            "first": 108,
            "last": 109,
            "section": "Per eumdem",
            "section_line": 107,
        },
    ]
    assert binding["reading"] == [
        {"archive": "holy-name", "first": 68, "last": 68},
        {"archive": "prayers", "first": 108, "last": 109},
    ]
    for name, digest in (
        ("holy-name", "3e2ca79322d0baa0f3dbd804f80d753507c2cc55367736b6dd1c04ecbd7f8c7b"),
        ("prayers", "7bf86beb01c170212fa07438de45b16b321f117013321400d65c2229c6624d9b"),
    ):
        archive = registry["archives"][name]
        assert (
            hashlib.sha256((CORPUS / archive["path"]).read_bytes()).hexdigest()
            == archive["sha256"]
            == digest
        )
    resolved = raw_binding.resolve_binding(FOLDER / "do.txt", CORPUS)
    assert resolved is not None and resolved.text == load_witness(FOLDER / "do.txt")[1]


@pytest.mark.parametrize("mutation", ["alias", "collect-call", "missing-invocation"])
def test_wrong_reference_is_rejected_even_when_the_conclusion_words_match(monkeypatch, mutation):
    registry = raw_binding.load_registry(CORPUS)
    binding = registry["bindings"]["holy-name-postcommunion"]
    assert raw_binding.resolve_binding(FOLDER / "do.txt", CORPUS) is not None
    header = (FOLDER / "do.txt").read_text()
    if mutation == "alias":
        prayers = (CORPUS / registry["archives"]["prayers"]["path"]).read_text().splitlines()
        assert prayers[107:109] == prayers[111:113]
        binding["evidence"][1].update(first=112, last=113, section="Per eundem", section_line=111)
        binding["reading"][1].update(first=112, last=113)
        header = header.replace("[Per eumdem] (lines 108-109)", "[Per eundem] (lines 112-113)")
    elif mutation == "collect-call":
        binding["references"][0]["line"] = 22
    else:
        binding["references"] = []
    files = {
        CORPUS / "witnesses/raw/bindings.json": json.dumps(registry).encode(),
        FOLDER / "do.txt": header.encode(),
    }
    read_text, read_bytes = Path.read_text, Path.read_bytes
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda p, *a, **k: files[p].decode() if p in files else read_text(p, *a, **k),
    )
    monkeypatch.setattr(Path, "read_bytes", lambda p: files[p] if p in files else read_bytes(p))
    with pytest.raises(raw_binding.BindingError):
        raw_binding.resolve_binding(FOLDER / "do.txt", CORPUS)


@pytest.mark.parametrize("mutation", ["missing-rule", "wrong-page-hash"])
def test_source_specific_contract_catches_structurally_valid_wrong_evidence(mutation):
    data = graph()
    assert_dependencies(data)
    if mutation == "missing-rule":
        witness(data, "mr")["source_dependencies"]["uses"].remove(
            PREFIX + "conclusion-selection.mr1962"
        )
    else:
        use(data, "conclusion-middle.mr1962")["evidence_sha256"] = use(
            data, "conclusion-terminal.mr1962"
        )["evidence_sha256"]
    assert (
        witness_subject(CORPUS, witness(data, "mr"), data, store.core(CORPUS, TEXT))["contract"]
        == "witness-review-2"
    )
    with pytest.raises(AssertionError):
        assert_dependencies(data)


def test_unrelated_edition_cannot_supply_a_composite_dependency():
    data = graph()
    target, other = use(data, "conclusion-middle.mr1962"), use(data, "conclusion.do44667ff")
    target["edition"], target["digital_item"] = other["edition"], other["digital_item"]
    with pytest.raises(BindingError, match="supplemental source belongs to another edition"):
        witness_subject(CORPUS, witness(data, "mr"), data, store.core(CORPUS, TEXT))


def test_apparatus_explains_every_literal_variant_and_no_invented_accent():
    core = store.core(CORPUS, TEXT)
    words = [w for s in core["segments"] for w in s["words"]]
    actual = []
    for name in ("mr", "do"):
        for word, raw in zip(words, load_witness(FOLDER / f"{name}.txt")[1].split(), strict=True):
            selected = word["form"] + word.get("post", "")
            if selected != raw:
                actual.append((word["id"], name, selected, raw))
    apparatus = json.loads((FOLDER / "apparatus.json").read_text())
    declared = [
        (e["at"], name, e["ours"], raw)
        for e in apparatus["adjudicated"]
        for name, raw in e["witnesses"].items()
    ]
    assert sorted(actual) == sorted(declared) and len(actual) == 10
    assert not any(entry["at"] == "w001" for entry in apparatus["adjudicated"])
    errors, warnings, stats = collate(core, FOLDER)
    assert errors == warnings == []
    assert stats["words"] == 77 and stats["variants_adjudicated"] == 5


@pytest.mark.parametrize("word", ["w072", "w073"])
def test_missing_literal_seam_is_rejected_by_actual_collation(tmp_path, word):
    for name in ("mr.txt", "do.txt", "apparatus.json"):
        (tmp_path / name).write_bytes((FOLDER / name).read_bytes())
    apparatus = json.loads((FOLDER / "apparatus.json").read_text())
    assert any(e["at"] == word for e in apparatus["adjudicated"])
    apparatus["adjudicated"] = [e for e in apparatus["adjudicated"] if e["at"] != word]
    (tmp_path / "apparatus.json").write_text(json.dumps(apparatus, ensure_ascii=False))
    errors, _, _ = collate(store.core(CORPUS, TEXT), tmp_path)
    assert any(word in error and "mr" in error for error in errors), errors


def test_source_repairs_do_not_certify_pending_reviews():
    data, languages = bibliography.load(CORPUS)
    assert bibliography.validate(CORPUS, data, languages) == []
    for name in ("mr", "do"):
        assert witness(data, name)["review"] == {"status": "pending"}
    assert next(c for c in data["collations"] if c["text"] == TEXT)["review"] == {
        "status": "pending"
    }
    row = next(r for r in bibliography.public_text_evidence(data)["texts"] if r["id"] == TEXT)
    assert row["witnesses"] == [] and "collation" not in row

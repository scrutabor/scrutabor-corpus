"""Preserve the Collect's real source boundaries and literal composite seams."""

import hashlib
import json
from pathlib import Path

import pytest

from build_reader import bibliography, store
from build_reader.bibliography_bindings import BindingError, witness_subject
from checks import raw_binding
from checks.collate import collate, load_witness
from checks.layout import CORPUS

TEXT = "proprium.sanctissimi-nominis-iesu-collecta"
FOLDER = CORPUS / "witnesses" / TEXT
PREFIX = f"use.{TEXT}."
PAGES = [
    ("mr1962", 113, "af86df236a2b37258b7c35e782c1fdf596c5434238d292b5bc344ad9f8ac0663"),
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
        "sung-orations.mr1962",
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


def assert_printed_dependencies(data):
    # These content-specific checks bind inspected page identities. A generic
    # schema cannot determine which words a page image actually contains.
    for suffix, leaf, digest in PAGES:
        item = use(data, suffix)
        assert item["evidence_sha256"] == digest
        assert (
            item["locator"]["page_url"]
            == f"https://archive.org/details/missale-romanum-1962/page/n{leaf}/mode/1up"
        )
        assert item["edition"] == "edition.missale-romanum.1962-typica"
        assert item["digital_item"] == "item.missale-romanum.1962-typica.ia"
    assert witness(data, "mr")["source_dependencies"] == {
        "uses": sorted(PREFIX + suffix for suffix, _, _ in PAGES if suffix != "mr1962"),
        "raw_binding": None,
    }


def test_separate_source_uses_do_not_claim_one_continuous_printing():
    data = graph()
    assert_printed_dependencies(data)
    assert len([u for u in data["uses"] if u["address"].get("text") == TEXT]) == 9
    for suffix in ("mr1962", "conclusion-middle.mr1962", "conclusion-terminal.mr1962"):
        assert use(data, suffix)["role"] == "direct_approved_print"
    for suffix in (
        "conclusion-rule.mr1962",
        "conclusion-selection.mr1962",
        "oration-boundaries.mr1962",
        "sung-orations.mr1962",
    ):
        assert use(data, suffix)["role"] == "official_liturgical_context"
    assert "does not print the complete expanded conclusion" in use(data, "mr1962")["claim"]
    for suffix in ("oration-boundaries.mr1962", "sung-orations.mr1962"):
        assert use(data, suffix)["address"] == {"kind": "segment", "text": TEXT, "segment": "s01"}
    assert "not the Secret's final" in use(data, "oration-boundaries.mr1962")["claim"]
    assert "not exclusive assignment of Amen" in use(data, "sung-orations.mr1962")["claim"]


def test_latin_and_ritual_are_not_rewritten_to_hide_the_printed_seam():
    core = store.core(CORPUS, TEXT)
    assert [(s["speaker"], s["voice"], len(s["words"])) for s in core["segments"]] == [
        ("sacerdos", "clara", 50),
        ("minister", "clara", 1),
    ]
    assert core["segments"][0]["delivery"]["cantu"] == {"speaker": "sacerdos", "voice": "cantus"}
    words = [w for s in core["segments"] for w in s["words"]]
    selected = " ".join(w["form"] + w.get("post", "") for w in words)
    meta, printed = load_witness(FOLDER / "mr.txt")
    assert printed == selected.replace("Deus, per ómnia", "Deus. Per ómnia")
    assert len(printed.split()) == 51
    assert "Editio iuxta typicam" in meta["description"]
    assert "not one continuous Holy Name printing" in meta["orthography"]
    assert "w031–w046 from p. 123" in meta["composite"]
    assert "w047–w051 from p. 226" in meta["composite"]


def test_exact_invoked_raw_section_not_equal_text_alias():
    registry = raw_binding.load_registry(CORPUS)
    binding = registry["bindings"]["holy-name-collect"]
    assert binding["references"] == [
        {"archive": "holy-name", "line": 22, "text": "$Per eumdem", "target": 1}
    ]
    assert binding["evidence"][1] == {
        "archive": "prayers",
        "first": 108,
        "last": 109,
        "section": "Per eumdem",
        "section_line": 107,
    }
    assert binding["reading"] == [
        {"archive": "holy-name", "first": 21, "last": 21},
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
    result = raw_binding.resolve_binding(FOLDER / "do.txt", CORPUS)
    assert result is not None and result.text == load_witness(FOLDER / "do.txt")[1]


def test_equal_reading_cannot_substitute_an_uninvoked_alias(monkeypatch):
    registry = raw_binding.load_registry(CORPUS)
    binding = registry["bindings"]["holy-name-collect"]
    assert raw_binding.resolve_binding(FOLDER / "do.txt", CORPUS) is not None
    prayers = (CORPUS / registry["archives"]["prayers"]["path"]).read_text().splitlines()
    assert prayers[107:109] == prayers[111:113]
    binding["evidence"][1].update(first=112, last=113, section="Per eundem", section_line=111)
    binding["reading"][1].update(first=112, last=113)
    header = (
        (FOLDER / "do.txt")
        .read_text()
        .replace("[Per eumdem] (lines 108-109)", "[Per eundem] (lines 112-113)")
    )
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
    with pytest.raises(
        raw_binding.BindingError, match="reference points to a different source or section"
    ):
        raw_binding.resolve_binding(FOLDER / "do.txt", CORPUS)


@pytest.mark.parametrize("mutation", ["missing-rule", "wrong-page-hash"])
def test_source_specific_contract_rejects_structurally_valid_false_claims(mutation):
    data = graph()
    assert_printed_dependencies(data)
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
        assert_printed_dependencies(data)


def test_valid_different_edition_item_pair_is_still_wrong_for_dependency():
    data = graph()
    target = use(data, "conclusion-middle.mr1962")
    other = use(data, "conclusion.do44667ff")
    target["edition"], target["digital_item"] = other["edition"], other["digital_item"]
    with pytest.raises(BindingError, match="supplemental source belongs to another edition"):
        witness_subject(CORPUS, witness(data, "mr"), data, store.core(CORPUS, TEXT))


def test_every_literal_variant_has_exactly_one_apparatus_record():
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
        (entry["at"], name, entry["ours"], raw)
        for entry in apparatus["adjudicated"]
        for name, raw in entry["witnesses"].items()
    ]
    assert sorted(actual) == sorted(declared) and len(actual) == 10
    errors, warnings, stats = collate(core, FOLDER)
    assert errors == warnings == []
    assert (
        stats["words"] == 51 and stats["variants_adjudicated"] == 4 and stats["orthographic"] == 6
    )


@pytest.mark.parametrize("word", ["w046", "w047"])
def test_missing_seam_is_rejected_by_collation(tmp_path, word):
    for name in ("mr.txt", "do.txt", "apparatus.json"):
        (tmp_path / name).write_bytes((FOLDER / name).read_bytes())
    apparatus = json.loads((FOLDER / "apparatus.json").read_text())
    assert any(entry["at"] == word for entry in apparatus["adjudicated"])
    apparatus["adjudicated"] = [entry for entry in apparatus["adjudicated"] if entry["at"] != word]
    (tmp_path / "apparatus.json").write_text(json.dumps(apparatus, ensure_ascii=False))
    errors, _, _ = collate(store.core(CORPUS, TEXT), tmp_path)
    assert any(word in error and "mr" in error for error in errors), errors


def test_source_correction_does_not_approve_pending_reviews():
    data, languages = bibliography.load(CORPUS)
    assert bibliography.validate(CORPUS, data, languages) == []
    for name in ("mr", "do"):
        assert witness(data, name)["review"] == {"status": "pending"}
    assert next(c for c in data["collations"] if c["text"] == TEXT)["review"] == {
        "status": "pending"
    }
    row = next(row for row in bibliography.public_text_evidence(data)["texts"] if row["id"] == TEXT)
    assert row["witnesses"] == [] and "collation" not in row

"""An explicit same-section source selector keeps its complete ordered chain."""

import hashlib
import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.bibliography_bindings import witness_subject
from checks import attribute
from checks.raw_binding import BindingError, load_registry, resolve_binding
from checks.transcription import check_transcriptions

CORPUS = Path(__file__).resolve().parents[1]
TEXT = "proprium.dominica-iv-adventus-secreta"
KEY = "do-proprium-dominica-iv-adventus-secreta"
REVISION = "44667ff518b8ff1439780470828b39714f5306a2"
REGISTRY = "witnesses/raw/bindings.json"
WITNESS = f"witnesses/{TEXT}/do.txt"
LITERAL = (
    "Sacrifíciis præséntibus, quǽsumus, Dómine, placátus inténde: ut et devotióni "
    "nostræ profíciant et salúti. Per Dóminum nostrum Jesum Christum, Fílium tuum: "
    "qui tecum vivit et regnat in unitáte Spíritus Sancti Deus, per ómnia sǽcula "
    "sæculórum. Amen."
)
ARCHIVES = {
    "do-tempora-adv4-0": (
        "web/www/missa/Latin/Tempora/Adv4-0.txt",
        "acd9154d762b5a2dfa5ea3bc07109ebeec253d5dfec635f9e49cbcd7bd3e2a74",
    ),
    "do-tempora-adv3-6": (
        "web/www/missa/Latin/Tempora/Adv3-6.txt",
        "6489f012b7daf41c9112ebacf99ea1177c6581fa609d3062405c68b1ee4063e3",
    ),
    "prayers": (
        "web/www/missa/Latin/Ordo/Prayers.txt",
        "7bf86beb01c170212fa07438de45b16b321f117013321400d65c2229c6624d9b",
    ),
}
EXPECTED = {
    "witness": WITNESS,
    "revision": REVISION,
    "contract": "raw-reading-2",
    "evidence": [
        {
            "archive": "do-tempora-adv4-0",
            "first": 54,
            "last": 54,
            "section": "Secreta",
            "section_line": 53,
        },
        {
            "archive": "do-tempora-adv3-6",
            "first": 115,
            "last": 116,
            "section": "Secreta",
            "section_line": 114,
        },
        {
            "archive": "prayers",
            "first": 96,
            "last": 97,
            "section": "Per Dominum",
            "section_line": 95,
        },
    ],
    "references": [
        {
            "archive": "do-tempora-adv4-0",
            "line": 54,
            "text": "@Tempora/Adv3-6:Secreta",
            "target": 1,
        },
        {"archive": "do-tempora-adv3-6", "line": 116, "text": "$Per Dominum", "target": 2},
    ],
    "reading": [
        {"archive": "do-tempora-adv3-6", "first": 115, "last": 115},
        {"archive": "prayers", "first": 96, "last": 97},
    ],
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(root, registry):
    (root / REGISTRY).write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def healthy(root):
    result = resolve_binding(root / WITNESS, root)
    assert result is not None
    assert result.text == LITERAL and len(result.text.split()) == 35
    assert result.spans == () and len(result.fragments) == 3
    assert result.source["contract"] == "raw-reading-2"
    assert set(result.source["archives"]) == set(ARCHIVES)
    return result


def test_actual_iv_advent_has_selector_proper_formula_and_response():
    registry = load_registry(CORPUS)
    assert registry["bindings"][KEY] == EXPECTED
    for key, (upstream, digest) in ARCHIVES.items():
        record = registry["archives"][key]
        assert (record["upstream"], record["revision"], record["sha256"]) == (
            upstream,
            REVISION,
            digest,
        )
        assert hashlib.sha256((CORPUS / record["path"]).read_bytes()).hexdigest() == digest
    result = healthy(CORPUS)
    assert result.source["binding"] == EXPECTED
    graph = read(CORPUS / "bibliography/graph.json")
    matches = [row for row in graph["witnesses"] if row["id"] == f"witness.{TEXT}.do44667ff"]
    assert len(matches) == 1
    witness = matches[0]
    assert witness["source_dependencies"] == {
        "uses": [
            f"use.{TEXT}.conclusion-macro.do44667ff",
            f"use.{TEXT}.proper-reference.do44667ff",
        ],
        "raw_binding": KEY,
    }
    doc = read(CORPUS / "texts/proprium/dominica-iv-adventus-secreta.json")
    subject = witness_subject(CORPUS, witness, graph, doc)
    assert set(subject["source_uses"]) == {witness["use"], *witness["source_dependencies"]["uses"]}
    assert subject["raw_resolution"] == result.source


@pytest.fixture
def source_fixture(tmp_path, monkeypatch):
    actual = load_registry(CORPUS)
    assert actual["bindings"][KEY] == EXPECTED
    registry = {
        "version": 1,
        "archives": {key: deepcopy(actual["archives"][key]) for key in ARCHIVES},
        "bindings": {KEY: deepcopy(EXPECTED)},
    }
    for relative in [WITNESS, *(row["path"] for row in registry["archives"].values())]:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CORPUS / relative, target)
    (tmp_path / REGISTRY).parent.mkdir(parents=True, exist_ok=True)
    save(tmp_path, registry)
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    pristine = healthy(tmp_path)
    try:
        yield tmp_path, registry
    finally:
        for relative, raw in before.items():
            target = tmp_path / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        restored = {
            p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()
        }
        assert restored == before
        assert healthy(tmp_path) == pristine


def test_actual_source_fixture_is_text_only_and_full_raw_order(source_fixture):
    root, _ = source_fixture
    assert check_transcriptions((root / WITNESS).parent) == ([], 1)
    doc = read(CORPUS / "texts/proprium/dominica-iv-adventus-secreta.json")
    assessment = attribute.assess(doc)
    assert not assessment.write_eligible and assessment.proposals == {}
    assert assessment.scope == "COMPOSITE_TEXT_ONLY"


BAD_SELECTORS = [
    "@Tempora/Adv3-6:Oratio",
    "@Tempora/Adv3-6:",
    "@:Secreta",
    "@Tempora/Adv3-6:Secreta:",
    "@Tempora/Adv3-6:Secreta:s/A/B/",
    "@Tempora/Adv3-6::Secreta",
    "@Tempora/Adv3-6: Secreta",
    "@Tempora/Adv3-6:secreta",
    "@Tempora/Adv3-6:Secreta;",
    "@Tempora/../Adv3-6:Secreta",
    "@Tempora/Adv3-6.txt:Secreta",
    "@Tempora/Adv4-0:Secreta",
]


def change_selector(root, registry, directive):
    record = registry["archives"]["do-tempora-adv4-0"]
    path = root / record["path"]
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[53] == "@Tempora/Adv3-6:Secreta"
    lines[53] = directive
    raw = ("\n".join(lines) + "\n").encode("utf-8")
    path.write_bytes(raw)
    record["sha256"] = hashlib.sha256(raw).hexdigest()
    registry["bindings"][KEY]["references"][0]["text"] = directive
    save(root, registry)


@pytest.mark.parametrize("directive", BAD_SELECTORS)
def test_foreign_missing_extra_or_substitution_selector_rejects(source_fixture, directive):
    root, registry = source_fixture
    # A test mutation, not a new source: refresh the fixture hash so the
    # exact source/reference comparison succeeds and the selector guard is reached.
    change_selector(root, registry, directive)
    with pytest.raises(BindingError, match="reference points to a different source or section"):
        resolve_binding(root / WITNESS, root)


@pytest.mark.parametrize(
    "fault",
    [
        "reference-text",
        "missing-reference",
        "wrong-target",
        "wrong-section",
        "read-selector",
        "reorder",
        "repeat-amen",
        "omit-amen",
    ],
)
def test_literal_reference_and_order_failures_recover(source_fixture, fault):
    root, registry = source_fixture
    binding = registry["bindings"][KEY]
    if fault == "reference-text":
        binding["references"][0]["text"] = "@Tempora/Adv3-6"
    elif fault == "missing-reference":
        binding["references"].pop(0)
    elif fault == "wrong-target":
        binding["references"][0]["target"] = 0
    elif fault == "wrong-section":
        binding["evidence"][1]["section"] = "Oratio"
    elif fault == "read-selector":
        binding["reading"].insert(0, {"archive": "do-tempora-adv4-0", "first": 54, "last": 54})
    elif fault == "reorder":
        binding["reading"].reverse()
    elif fault == "repeat-amen":
        binding["reading"].append({"archive": "prayers", "first": 97, "last": 97})
    else:
        binding["reading"][1]["last"] = 96
    save(root, registry)
    with pytest.raises(BindingError):
        resolve_binding(root / WITNESS, root)
    errors, count = check_transcriptions((root / WITNESS).parent)
    assert errors and count == 0


@pytest.mark.parametrize(
    "fault", ["missing-marker", "duplicate-marker", "wrong-revision", "wrong-path", "body"]
)
def test_real_witness_identity_and_literal_body_remain_required(source_fixture, fault):
    root, _ = source_fixture
    path = root / WITNESS
    text = path.read_text(encoding="utf-8")
    if fault == "missing-marker":
        text = text.replace("# raw-binding: " + KEY + "\n", "")
    elif fault == "duplicate-marker":
        text = "# raw-binding: " + KEY + "\n" + text
    elif fault == "wrong-revision":
        text = text.replace("# revision: " + REVISION, "# revision: " + "0" * 40)
    elif fault == "wrong-path":
        text = text.replace("[Secreta] (lines 54-54)", "[Secreta] (lines 53-54)", 1)
    else:
        text = text.replace("Jesum", "Iesum")
    path.write_text(text, encoding="utf-8")
    with pytest.raises(BindingError):
        resolve_binding(path, root)


def test_legacy_unqualified_same_section_branch_still_resolves(source_fixture):
    root, registry = source_fixture
    # Mechanical compatibility control on deliberately changed fixture bytes,
    # not a claim that the registered IV Advent original omits its selector.
    change_selector(root, registry, "@Tempora/Adv3-6")
    assert healthy(root).text == LITERAL

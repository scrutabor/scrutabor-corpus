"""Whole rubric evidence is retained, but cannot become selected prayer text."""

import hashlib
import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

from checks.raw_binding import BindingError, load_registry, resolve_binding
from checks.transcription import check_transcriptions

CORPUS = Path(__file__).resolve().parents[1]
TEXT = "proprium.nativitas-domini-in-aurora-secreta"
KEY = "do-proprium-nativitas-domini-in-aurora-secreta"
REGISTRY = "witnesses/raw/bindings.json"
WITNESS = f"witnesses/{TEXT}/do.txt"
WITNESS_SHA = "fec4284f303eab03a1aa2d0cbc285d9f16fe7e753588cd6c211547eb8da4bfd7"
SOURCE = "do-sancti-12-25m2"
RUBRIC = "!Pro S. Anastasia"
LITERAL = (
    "Múnera nostra, quǽsumus, Dómine, Nativitátis hodiérnæ mystériis "
    "apta provéniant, et pacem nobis semper infúndant: ut, sicut homo "
    "génitus idem refúlsit et Deus, sic nobis hæc terréna substántia "
    "cónferat, quod divínum est. Per eúndem Dóminum nostrum Jesum "
    "Christum Fílium tuum, qui tecum vivit et regnat in unitáte "
    "Spíritus Sancti, Deus, per ómnia sǽcula sæculórum. Amen. Accipe, "
    "quǽsumus, Dómine, múnera dignánter obláta: et, beátæ Anastásiæ "
    "Mártyris tuæ suffragántibus méritis, ad nostræ salútis auxílium "
    "proveníre concéde. Per Dóminum nostrum Jesum Christum, Fílium "
    "tuum: qui tecum vivit et regnat in unitáte Spíritus Sancti Deus, "
    "per ómnia sǽcula sæculórum. Amen."
)
ARCHIVES = {
    "do-sancti-12-25m2": {
        "upstream": "web/www/missa/Latin/Sancti/12-25m2.txt",
        "revision": "44667ff518b8ff1439780470828b39714f5306a2",
        "path": "witnesses/raw/do-44667ff/missa/Latin/Sancti/12-25m2.txt",
        "sha256": "15bf53749bf31e6b488a6d619dbfb09000e4227424819b752500e71ebfbfe1c5",
    },
    "prayers": {
        "upstream": "web/www/missa/Latin/Ordo/Prayers.txt",
        "revision": "44667ff518b8ff1439780470828b39714f5306a2",
        "path": "witnesses/raw/do-44667ff/missa/Latin/Ordo/Prayers.txt",
        "sha256": "7bf86beb01c170212fa07438de45b16b321f117013321400d65c2229c6624d9b",
    },
}
EXPECTED = {
    "witness": "witnesses/proprium.nativitas-domini-in-aurora-secreta/do.txt",
    "revision": "44667ff518b8ff1439780470828b39714f5306a2",
    "contract": "raw-reading-2",
    "evidence": [
        {
            "archive": "do-sancti-12-25m2",
            "first": 52,
            "last": 53,
            "section": "Secreta",
            "section_line": 51,
        },
        {
            "archive": "prayers",
            "first": 112,
            "last": 113,
            "section": "Per eundem",
            "section_line": 111,
        },
        {
            "archive": "do-sancti-12-25m2",
            "first": 56,
            "last": 58,
            "section": "Commemoratio Secreta",
            "section_line": 55,
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
        {"archive": "do-sancti-12-25m2", "line": 53, "text": "$Per eundem", "target": 1},
        {"archive": "do-sancti-12-25m2", "line": 58, "text": "$Per Dominum", "target": 3},
    ],
    "reading": [
        {"archive": "do-sancti-12-25m2", "first": 52, "last": 52},
        {"archive": "prayers", "first": 112, "last": 113},
        {"archive": "do-sancti-12-25m2", "first": 57, "last": 57},
        {"archive": "prayers", "first": 96, "last": 97},
    ],
}
SELECTED = [
    (
        "do-sancti-12-25m2",
        52,
        (
            "Múnera nostra, quǽsumus, Dómine, Nativitátis hodiérnæ mystériis "
            "apta provéniant, et pacem nobis semper infúndant: ut, sicut homo "
            "génitus idem refúlsit et Deus, sic nobis hæc terréna substántia "
            "cónferat, quod divínum est."
        ),
    ),
    (
        "prayers",
        112,
        (
            "r. Per eúndem Dóminum nostrum Jesum Christum Fílium tuum, qui "
            "tecum vivit et regnat in unitáte Spíritus Sancti, Deus, per "
            "ómnia sǽcula sæculórum."
        ),
    ),
    (
        "prayers",
        113,
        ("R. Amen."),
    ),
    (
        "do-sancti-12-25m2",
        57,
        (
            "Accipe, quǽsumus, Dómine, múnera dignánter obláta: et, beátæ "
            "Anastásiæ Mártyris tuæ suffragántibus méritis, ad nostræ salútis "
            "auxílium proveníre concéde."
        ),
    ),
    (
        "prayers",
        96,
        (
            "r. Per Dóminum nostrum Jesum Christum, Fílium tuum: qui tecum "
            "vivit et regnat in unitáte Spíritus Sancti Deus, per ómnia "
            "sǽcula sæculórum."
        ),
    ),
    (
        "prayers",
        97,
        ("R. Amen."),
    ),
]


def save(root, registry):
    (root / REGISTRY).write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def healthy(root):
    witness = root / WITNESS
    result = resolve_binding(witness, root)
    assert result is not None
    assert result.text == LITERAL and len(result.text.split()) == 95
    assert result.spans == () and len(result.fragments) == 6
    assert hashlib.sha256(witness.read_bytes()).hexdigest() == WITNESS_SHA
    fragments = []
    for archive, number, raw in SELECTED:
        marker = raw[0] if raw.startswith(("r. ", "R. ")) else None
        fragments.append(
            {
                "path": ARCHIVES[archive]["path"],
                "line": number,
                "start": 0,
                "end": len(raw),
                "raw": raw,
                "text": raw[3:] if marker else raw,
                "marker": marker,
                "whole_line": True,
                "marker_scope_verified": True,
            }
        )
    assert result.source == {
        "contract": "raw-reading-2",
        "registry_version": 1,
        "binding_id": KEY,
        "transcription_sha256": WITNESS_SHA,
        "binding": EXPECTED,
        "archives": ARCHIVES,
        "resolved_fragments": fragments,
    }
    assert result.source["binding"]["evidence"][2]["first"] == 56
    assert result.source["binding"]["evidence"][2]["last"] == 58
    assert all(
        fragment.path != root / ARCHIVES[SOURCE]["path"] or fragment.line != 56
        for fragment in result.fragments
    )
    assert "!Pro" not in result.text and "S. Anastasia" not in result.text
    return result


def test_actual_dawn_retains_rubric_and_both_complete_formulas():
    registry = load_registry(CORPUS)
    assert registry["bindings"][KEY] == EXPECTED
    for key, record in ARCHIVES.items():
        assert registry["archives"][key] == record
        assert (
            hashlib.sha256((CORPUS / record["path"]).read_bytes()).hexdigest() == (record["sha256"])
        )
    lines = (CORPUS / ARCHIVES[SOURCE]["path"]).read_text(encoding="utf-8").splitlines()
    assert lines[55] == RUBRIC
    healthy(CORPUS)


@pytest.fixture
def source_fixture(tmp_path):
    actual = load_registry(CORPUS)
    assert actual["bindings"][KEY] == EXPECTED
    assert all(actual["archives"][key] == record for key, record in ARCHIVES.items())
    registry = {
        "version": 1,
        "archives": deepcopy(ARCHIVES),
        "bindings": {KEY: deepcopy(EXPECTED)},
    }
    for relative in [WITNESS, *(record["path"] for record in ARCHIVES.values())]:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CORPUS / relative, target)
    (tmp_path / REGISTRY).parent.mkdir(parents=True, exist_ok=True)
    save(tmp_path, registry)
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    pristine = healthy(tmp_path)
    try:
        yield tmp_path, registry
    finally:
        for relative, raw in before.items():
            (tmp_path / relative).write_bytes(raw)
        restored = {
            p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()
        }
        assert restored == before
        assert healthy(tmp_path) == pristine


def test_disposable_dawn_has_exact_nontext_and_source_projection(source_fixture):
    root, _ = source_fixture
    healthy(root)
    assert check_transcriptions((root / WITNESS).parent) == ([], 1)


def change_line(root, registry, number, replacement, *, refresh=True):
    record = registry["archives"][SOURCE]
    path = root / record["path"]
    lines = path.read_text(encoding="utf-8").splitlines()
    lines[number - 1] = replacement
    raw = ("\n".join(lines) + "\n").encode("utf-8")
    path.write_bytes(raw)
    if refresh:
        record["sha256"] = hashlib.sha256(raw).hexdigest()
    save(root, registry)


def rejected(root, message):
    with pytest.raises(BindingError, match=message):
        resolve_binding(root / WITNESS, root)
    errors, count = check_transcriptions((root / WITNESS).parent)
    assert errors and count == 0


@pytest.mark.parametrize(
    "fault",
    ["unprefixed", "spliced", "indented", "branch", "escaped-bang", "spoken-line"],
)
def test_nonliteral_rubric_and_spoken_markers_keep_inline_guard(source_fixture, fault):
    root, registry = source_fixture
    replacement = {
        "unprefixed": "Pro S. Anastasia",
        "spliced": "Accipe. " + RUBRIC,
        "indented": " " + RUBRIC,
        "branch": "!*Pro S. Anastasia",
        "escaped-bang": "!!!Pro S. Anastasia",
        "spoken-line": SELECTED[3][2] + " S. Amen.",
    }[fault]
    change_line(root, registry, 57 if fault == "spoken-line" else 56, replacement)
    rejected(root, "ambiguous inline source marker")


def path_header(root, registry):
    declarations = []
    for item in registry["bindings"][KEY]["evidence"]:
        extent = f"lines {item['first']}-{item['last']}"
        if "fragment" in item:
            fragment = item["fragment"]
            extent = f"line {item['first']}, chars {fragment['start']}:{fragment['end']}"
        declarations.append(
            f"{registry['archives'][item['archive']]['upstream']} [{item['section']}] ({extent})"
        )
    witness = root / WITNESS
    lines = witness.read_text(encoding="utf-8").splitlines()
    indexes = [i for i, line in enumerate(lines) if line.startswith("# path: ")]
    assert len(indexes) == 1
    lines[indexes[0]] = "# path: " + "; ".join(declarations)
    witness.write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.mark.parametrize("start", [0, 5], ids=["whole-line-slice", "inner-slice"])
def test_sliced_rubric_evidence_is_not_the_whole_line_exception(source_fixture, start):
    root, registry = source_fixture
    binding = registry["bindings"][KEY]
    rubric = deepcopy(binding["evidence"][2])
    rubric.update(first=56, last=56)
    rubric["fragment"] = {
        "start": start,
        "end": len(RUBRIC),
        "text": RUBRIC[start:],
        "marker": None,
        "reason": "Deliberate rubric slice must not receive whole-line treatment.",
    }
    remainder = deepcopy(binding["evidence"][2])
    remainder["first"] = 57
    binding["evidence"][2:3] = [rubric, remainder]
    binding["references"][1]["target"] = 4
    save(root, registry)
    path_header(root, registry)
    rejected(root, "ambiguous inline source marker")


@pytest.mark.parametrize("mode", ["whole", "sliced", "marker-free"])
def test_rubric_cannot_be_forced_into_a_selected_reading(source_fixture, mode):
    root, registry = source_fixture
    item = {"archive": SOURCE, "first": 56, "last": 56}
    if mode == "sliced":
        item["fragment"] = {"start": 5, "end": len(RUBRIC)}
    if mode == "marker-free":
        change_line(root, registry, 56, "!Pro Anastasia")
    registry["bindings"][KEY]["reading"].insert(2, item)
    save(root, registry)
    message = (
        "reading contains framing or lies outside textual evidence"
        if mode == "marker-free"
        else "ambiguous inline source marker"
    )
    rejected(root, message)


@pytest.mark.parametrize("fault", ["checksum", "section"])
def test_rubric_exception_does_not_bypass_source_identity(source_fixture, fault):
    root, registry = source_fixture
    if fault == "checksum":
        change_line(root, registry, 56, RUBRIC + "!", refresh=False)
        message = "SHA-256 mismatch"
    else:
        registry["bindings"][KEY]["evidence"][2]["section"] = "Secreta"
        save(root, registry)
        message = "source section does not match evidence"
    rejected(root, message)

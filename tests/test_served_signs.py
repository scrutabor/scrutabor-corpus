"""The reader's text face has no glyph for the versicle and response signs (U+2123, U+211F).

Everything the reader serves therefore names a cue or a verse in words: a locator says *cues
Glória Patri. and Ecce.* or *Allelúia, allelúia, its verse Matth. 2, 2*, not the printed sign.
The witness transcriptions, which the reader does not serve, keep the signs as printed.
"""

import json
from pathlib import Path

import pytest

from build_reader.emit import emit

ROOT = Path(__file__).resolve().parents[1]
SIGNS = ("℣", "℟")


@pytest.fixture(scope="module")
def reader_edition(tmp_path_factory):
    out = tmp_path_factory.mktemp("served-signs") / "edition"
    emit(ROOT, out)
    return out


def signs_in(path):
    # Decode JSON first: an escaped sign needs the same glyph as a literal one.
    text = json.dumps(json.loads(path.read_text(encoding="utf-8")), ensure_ascii=False)
    return [sign for sign in SIGNS if sign in text]


def unsupported_files(edition, sign):
    return [
        path.relative_to(edition).as_posix()
        for path in sorted(edition.rglob("*.json"))
        if sign in signs_in(path)
    ]


def test_the_served_files_are_found(reader_edition):
    # Check emitted artifacts, not a manually maintained subset of inputs.
    assert len(list(reader_edition.rglob("*.json"))) > 3000
    for relative in (
        "manifest.json",
        "lexicon/heads.json",
        "formularies.json",
        "languages/en/manifest.json",
        "languages/en/lexicon.json",
        "languages/en/formularies.json",
        "languages/pl/manifest.json",
        "languages/pl/lexicon.json",
        "languages/pl/formularies.json",
    ):
        assert (reader_edition / relative).is_file(), relative


@pytest.mark.parametrize("sign", SIGNS)
def test_no_served_file_needs_a_sign_the_reader_face_lacks(reader_edition, sign):
    assert unsupported_files(reader_edition, sign) == []


@pytest.mark.parametrize("sign", SIGNS)
@pytest.mark.parametrize("escaped", [False, True])
@pytest.mark.parametrize(
    "relative",
    [
        "lexicon/heads.json",
        "languages/en/lexicon.json",
        "languages/pl/manifest.json",
        "languages/pl/formularies.json",
        "future/nested/artifact.json",
    ],
)
def test_sign_detection_reaches_nested_artifacts_and_escaped_json(
    tmp_path, sign, escaped, relative
):
    artifact = tmp_path / relative
    artifact.parent.mkdir(parents=True)
    artifact.write_text(
        json.dumps({"titles": [{"title": f"Test {sign}"}]}, ensure_ascii=escaped),
        encoding="utf-8",
    )
    assert unsupported_files(tmp_path, sign) == [relative]


def test_the_witnesses_keep_the_printed_signs():
    witness = ROOT / "witnesses" / "proprium.epiphania-domini-introitus" / "mr.txt"
    assert "℣. Glória Patri. Ecce." in witness.read_text(encoding="utf-8")

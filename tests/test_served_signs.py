"""The reader's text face has no glyph for the versicle and response signs (U+2123, U+211F).

Everything the reader serves therefore names a cue or a verse in words: a locator says *cues
Glória Patri. and Ecce.* or *Allelúia, allelúia, its verse Matth. 2, 2*, not the printed sign.
The witness transcriptions, which the reader does not serve, keep the signs as printed.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SIGNS = ("℣", "℟")
SERVED = [
    ROOT / "bibliography" / "graph.json",
    *sorted((ROOT / "languages").glob("*/bibliography.json")),
    *sorted((ROOT / "texts").rglob("*.json")),
    *sorted((ROOT / "languages").glob("*/texts/**/*.json")),
    *sorted((ROOT / "formularies").rglob("*.json")),
]


def signs_in(path):
    text = path.read_text(encoding="utf-8")
    return [sign for sign in SIGNS if sign in text]


def test_the_served_files_are_found():
    assert len(SERVED) > 3000
    assert all(path.is_file() for path in SERVED)


@pytest.mark.parametrize("sign", SIGNS)
def test_no_served_file_needs_a_sign_the_reader_face_lacks(sign):
    found = [path.relative_to(ROOT).as_posix() for path in SERVED if sign in signs_in(path)]
    assert found == []


def test_the_witnesses_keep_the_printed_signs():
    witness = ROOT / "witnesses" / "proprium.epiphania-domini-introitus" / "mr.txt"
    assert "℣. Glória Patri. Ecce." in witness.read_text(encoding="utf-8")

"""The psalm rendering is shared; the seasonal antiphon and doxology remain intact."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASE = "annuntiatio-beatae-mariae-virginis"
PSALM = "Z mojego serca popłynęło piękne słowo; głoszę Królowi moje dzieła."
ANTIPHON = (
    "Wszyscy bogaci ludu będą błagać o twoją przychylność. "
    "Za nią zostaną przyprowadzone Królowi dziewice. "
    "Jej towarzyszki zostaną przyprowadzone do Ciebie z radością i weselem."
)
DOXOLOGY = (
    "Chwała Ojcu i Synowi, i Duchowi Świętemu. "
    "Jak była na początku, teraz i zawsze, i na wieki wieków. Amen."
)


@pytest.mark.parametrize(
    "suffix,first,dico,alleluia",
    [
        ("introitus", 22, "w027", " Alleluja, alleluja."),
        ("extra-tempus-paschale-introitus", 20, "w025", ""),
    ],
)
def test_psalm_rendering_and_preserved_ritual_parts(suffix, first, dico, alleluia):
    name = f"{BASE}-{suffix}.json"
    layer = json.loads((ROOT / "languages/pl/texts/proprium" / name).read_text())
    core = json.loads((ROOT / "texts/proprium" / name).read_text())
    selected = core["segments"][0]["words"][first - 1 : first + 9]
    assert [word["lemma"] for word in selected] == [
        "eructo",
        "cor",
        "meus",
        "verbum",
        "bonus",
        "dico",
        "ego",
        "opus",
        "meus",
        "rex",
    ]
    assert layer["segments"]["s01"]["translation"] == " ".join(
        [ANTIPHON + alleluia, PSALM, DOXOLOGY, ANTIPHON + alleluia]
    )
    assert layer["words"][dico]["gloss"] == "głoszę"

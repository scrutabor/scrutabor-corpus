"""The 1903 Gloria witness is a partial basis, not the modern wording verbatim."""

import json
from pathlib import Path

import pytest

from build_reader import bibliography

ROOT = Path(__file__).resolve().parents[1]
TEXT = "ordinarium.gloria"
EDITION = "edition.pamiatka-missyi-dla-ludu-katolickiego-1903"
URL = "https://sbc.org.pl/dlibra/publication/337480/edition/318796/pamiatka-missyi-dla-ludu-katolickiego"

# Pamiątka Missyi (1903), printed p. 46 / PDF physical p. 49.
# These are bounded source observations, not a replacement of the prayer.
CASES = {
    "s04": (
        "use.pl.af90bee5fee85e68d016",
        "Na Gloria — trzy wezwania pochwalne",
        "Częściowy historyczny świadek brzmienia: „Chwalimy Cię. Błogosławimy Tobie. "
        "Cześć oddajemy Tobie.” Druk nie poświadcza odrębnego czwartego wezwania ani "
        "pełnego obecnego ciągu czterech zdań.",
        "Chwalimy Cię. Błogosławimy Cię. Wielbimy Cię. Wysławiamy Cię.",
    ),
    "s05": (
        "use.pl.7bddbbb0be4a2d33ce42",
        "Na Gloria — dziękczynienie",
        "Historyczny wariant dziękczynienia: „Dzięki składamy Tobie dla wielkiej "
        "chwały Twojej.” Obecne „bo wielka jest chwała Twoja” jest rewizją składni, "
        "nie dosłownym odczytem tej strony.",
        "Dzięki Ci składamy, bo wielka jest chwała Twoja.",
    ),
    "s10": (
        "use.pl.e2f3ce0c300bd37cd36b",
        "Na Gloria — prośba o przyjęcie modlitwy",
        "Historyczny wariant prośby: „Który gładzisz grzechy świata, przyjmij prośby "
        "nasze!” Druk ma liczbę mnogą „prośby” i formę „przyjmij”; nie poświadcza "
        "dokładnie obecnego „przyjm błaganie nasze”.",
        "Który gładzisz grzechy świata, przyjm błaganie nasze.",
    ),
    "s12": (
        "use.pl.114f8fbe0049a01aec06",
        "Na Gloria — trzykrotne „sam”",
        "Historyczny świadek trzykrotnego „sam”: „Boś ty sam Święty, Tyś sam Pan, "
        "Tyś sam Najwyższy, Jezu Chryste”. Druk przechodzi bez kropki po „Chryste” "
        "do „z Duchem świętym”; nie poświadcza dosłownie obecnego ciągu z „tylko Tyś”.",
        "Albowiem tylko Tyś jest święty. Tylko Tyś jest Panem. Tylko Tyś Najwyższy, Jezu Chryste.",
    ),
}


@pytest.fixture(scope="module")
def source_data():
    graph, packages = bibliography.load(ROOT)
    assert bibliography.validate(ROOT, graph, packages) == []
    evidence = bibliography.public_text_evidence(graph, packages["pl"])
    projected = [record for record in evidence["texts"] if record["id"] == TEXT]
    assert len(projected) == 1
    layer = json.loads((ROOT / "languages/pl/texts/ordinarium/gloria.json").read_text())
    return packages["pl"], projected[0], layer


@pytest.mark.parametrize("segment", ["s04", "s05", "s10", "s12"])
def test_partial_gloria_witness_keeps_exact_scope_and_current_prayer(segment, source_data):
    package, projected, layer = source_data
    use_id, section, claim, prayer = CASES[segment]
    uses = [use for use in package["uses"] if use["id"] == use_id]
    assert len(uses) == 1
    use = uses[0]
    assert use["edition"] == EDITION
    assert use["digital_item"] == "item.pamiatka-missyi-dla-ludu-katolickiego-1903.sbc"
    assert use["role"] == "historical_wording_basis"
    assert use["decision"] == "RETAIN_WITH_CORRECTION"
    assert use["address"] == {"kind": "segment", "text": TEXT, "segment": segment}
    assert use["claim"] == claim
    assert use["verified_on"] == "2026-10-26"
    assert use["locator"] == {
        "printed": "druk. s. 46",
        "scan": "PDF s. 49",
        "page_url": URL,
        "section": section,
    }
    assert layer["segments"][segment]["translation"] == prayer
    assert use["legacy_refs"] == [
        f"languages/pl/texts/ordinarium/gloria.json#/segments/{segment}/translation_citations/0"
    ]

    matches = [
        (group, entry)
        for group in projected["source_groups"]
        for entry in group["entries"]
        if entry["id"] == use_id
    ]
    assert len(matches) == 1
    group, entry = matches[0]
    assert group["locator"] == use["locator"]
    assert group["edition"] == EDITION
    assert group["role"] == "historical_wording_basis"
    assert group["verified_on"] == use["verified_on"]
    assert entry == {
        "id": use_id,
        "address": {"kind": "segment", "segment": segment},
        "claim": claim,
    }


# The Family Prayer-book (1839), printed pp. 65–66 / PDF physical pp. 96–97.
# The confession starts at the foot of the first page, not only on the second.
def test_english_gloria_confession_keeps_its_own_source_scope():
    graph, packages = bibliography.load(ROOT)
    assert bibliography.validate(ROOT, graph, packages) == []
    package = packages["en"]
    uses = [use for use in package["uses"] if use["id"] == "use.en.0524d8c62828c31becdd"]
    assert len(uses) == 1
    use = uses[0]
    assert use["address"] == {"kind": "segment", "text": TEXT, "segment": "s12"}
    assert use["edition"] == "edition.the-family-prayer-book-1839"
    assert use["digital_item"] == "item.family-prayer-book-1839.scan"
    assert use["role"] == "historical_wording_basis"
    assert use["decision"] == "RETAIN_WITH_CORRECTION"
    assert use["locator"]["printed"] == "pp. 65–66"
    assert use["locator"]["scan"] == "scan pp. 96–97"
    assert "Christ alone is holy, Lord and Most High" in use["claim"]
    assert "revision, not a verbatim transcription" in use["claim"]
    assert "right hand" not in use["claim"]
    layer = json.loads((ROOT / "languages/en/texts/ordinarium/gloria.json").read_text())
    assert layer["segments"]["s12"]["translation"] == (
        "For You alone are holy. You alone are Lord. You alone are Most High, Jesus Christ."
    )
    assert layer["segments"]["s13"]["translation"] == (
        "With the Holy Spirit in the glory of God the Father. Amen."
    )
    # The migrated inline citation is frozen historical evidence, not the reader source.
    assert layer["segments"]["s12"]["translation_citations"][0]["locator"] == "p. 66"
    evidence = bibliography.public_text_evidence(graph, package)
    texts = [record for record in evidence["texts"] if record["id"] == TEXT]
    assert len(texts) == 1
    matches = [
        (group, entry)
        for group in texts[0]["source_groups"]
        for entry in group["entries"]
        if entry["id"] == use["id"]
    ]
    assert len(matches) == 1
    group, entry = matches[0]
    assert group["locator"] == use["locator"]
    assert entry["address"] == {"kind": "segment", "segment": "s12"}
    assert entry["claim"] == use["claim"]

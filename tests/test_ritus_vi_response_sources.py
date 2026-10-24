"""The Epistle/Gospel response excerpts keep one real source and exact owned ranges."""

import json
import re
from pathlib import Path

import pytest

from checks import attribute, witness_archive
from checks.transcription import check_transcriptions

ROOT = Path(__file__).resolve().parents[1]
RAW = "mr-ritus-servandus-vi.txt"
ITEM = "https://archive.org/details/missale-romanum-1962"
TEXTS = ("ordinarium.deo-gratias-epistolae", "ordinarium.laus-tibi-christe")
RANGES = ((12, 14), (16, 16))
RESPONSES = ("Deo grátias.", "Laus tibi, Christe.")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def header(text, key):
    matches = re.findall(r"^# " + re.escape(key) + r": (.*)$", text, re.MULTILINE)
    require(len(matches) == 1, "single source metadata field")
    return matches[0]


def body(text):
    return "\n".join(line for line in text.splitlines() if not line.startswith("#")).strip()


def assert_excerpt(raw):
    require(header(raw, "source") == ITEM, "response excerpt manifestation")
    require(
        header(raw, "path") == "printed p. liii (LIII), scan leaf n58 / PDF p. 59",
        "response excerpt page identity",
    )
    require(
        "Benziger Brothers, New York, 1962, editio iuxta typicam" in header(raw, "description")
        and "Ritus servandus VI, 1–2" in raw,
        "response excerpt edition and sections",
    )
    require(
        header(raw, "historical-fetched")
        == "2026-08-11 (legacy declaration; original acquisition not reverified)"
        and "# fetched:" not in raw,
        "response excerpt acquisition honesty",
    )
    lines = raw.splitlines()
    require(
        "et respondetur a ministro: Deo grátias" in lines[13] and "respondeatur" not in lines[13],
        "printed Epistle response predicate",
    )
    require(
        lines[15].startswith("2. Locato missali in altari,")
        and "respondet: Laus tibi, Christe" in lines[15],
        "printed Gospel response paragraph",
    )
    require(
        "selected rubric excerpts, not complete continuous paragraphs" in raw
        and "# excerpt-scope:" in raw,
        "response excerpt scope honesty",
    )


def assert_witness(text, witness):
    index = TEXTS.index(text)
    require(header(witness, "source") == ITEM, "response witness manifestation")
    require(
        f"Ritus servandus VI, {index + 1} — the response" in header(witness, "description"),
        "response witness section",
    )
    first, last = RANGES[index]
    expected_numbers = [first] if first == last else [first, last]
    require(
        attribute._range_declarations(witness) == [("../raw/" + RAW, expected_numbers)],
        "response witness owned range",
    )
    require(body(witness) == RESPONSES[index], "unchanged fixed response body")


@pytest.fixture
def source_copy(tmp_path, monkeypatch):
    raw = tmp_path / "witnesses/raw" / RAW
    raw.parent.mkdir(parents=True)
    raw.write_bytes((ROOT / "witnesses/raw" / RAW).read_bytes())
    for text in TEXTS:
        folder = tmp_path / "witnesses" / text
        folder.mkdir()
        (folder / "mr.txt").write_bytes((ROOT / "witnesses" / text / "mr.txt").read_bytes())
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    return tmp_path


def assert_native(root):
    assert_excerpt((root / "witnesses/raw" / RAW).read_text(encoding="utf-8"))
    for index, text in enumerate(TEXTS):
        folder = root / "witnesses" / text
        assert_witness(text, (folder / "mr.txt").read_text(encoding="utf-8"))
        assert check_transcriptions(folder) == ([], 1)
        first, last = RANGES[index]
        assert attribute.witness_ranges(text) == [(root / "witnesses/raw" / RAW, first, last)]
        category, slug = text.split(".", 1)
        core = json.loads(
            (ROOT / "texts" / category / (slug + ".json")).read_text(encoding="utf-8")
        )
        assert attribute.span_covers(core)
        words = core["segments"][0]["words"]
        assert " ".join(w["form"] + w.get("post", "") for w in words) == RESPONSES[index]
    assert witness_archive.check(root) == []


def test_actual_excerpt_and_responses_pass_native_range_and_transcription_consumers(source_copy):
    assert_native(source_copy)


@pytest.mark.parametrize(
    "old,new,message",
    (
        (
            "# source: " + ITEM,
            "# source: https://archive.org/details/missale_romanum-1962",
            "response excerpt manifestation",
        ),
        ("printed p. liii (LIII)", "printed p. LVII", "response excerpt page identity"),
        (
            "et respondetur a ministro",
            "et respondeatur a ministro",
            "printed Epistle response predicate",
        ),
        ("2. Locato missali", "Locato missali", "printed Gospel response paragraph"),
        ("# historical-fetched:", "# fetched:", "single source metadata field"),
        (
            "selected rubric excerpts, not complete continuous paragraphs",
            "complete exact paragraphs",
            "response excerpt scope honesty",
        ),
    ),
)
def test_wrong_source_or_literal_reading_is_not_hidden_by_correct_response_words(
    source_copy, old, new, message
):
    assert_native(source_copy)
    raw = (source_copy / "witnesses/raw" / RAW).read_text(encoding="utf-8")
    assert raw.count(old) == 1
    broken = raw.replace(old, new)
    assert broken != raw
    with pytest.raises(AssertionError) as caught:
        assert_excerpt(broken)
    assert str(caught.value) == message
    assert_native(source_copy)


def test_gospel_witness_cannot_revert_to_the_epistle_section(source_copy):
    assert_native(source_copy)
    witness = (source_copy / "witnesses" / TEXTS[1] / "mr.txt").read_text(encoding="utf-8")
    broken = witness.replace("Ritus servandus VI, 2", "Ritus servandus VI, 1")
    assert broken != witness
    with pytest.raises(AssertionError) as caught:
        assert_witness(TEXTS[1], broken)
    assert str(caught.value) == "response witness section"
    assert_native(source_copy)


@pytest.mark.parametrize("defect", ("wrong-range", "missing-range", "response-word"))
def test_actual_transcription_consumer_rejects_owned_range_or_response_corruption(
    source_copy, defect
):
    assert_native(source_copy)
    folder = source_copy / "witnesses" / TEXTS[1]
    witness = folder / "mr.txt"
    saved = witness.read_bytes()
    text = saved.decode("utf-8")
    if defect == "wrong-range":
        broken = text.replace("(line 16)", "(line 14)")
        message = "mr.txt: transcription differs from its declared raw span near 'Laustibi,Christe'"
    elif defect == "missing-range":
        broken = text.replace(" (line 16)", "")
        message = (
            "mr.txt: names ../raw/" + RAW + " and declares no readable line range — nothing "
            "was compared, and a range is what says which lines this transcription stands on"
        )
    else:
        broken = text.replace("Laus tibi, Christe.", "Laus tibi, Deus.")
        message = "mr.txt: transcription differs from its declared raw span near 'Laustibi,Deus'"
    assert broken != text
    try:
        witness.write_text(broken, encoding="utf-8")
        errors, checked = check_transcriptions(folder)
        assert checked == 0
        assert message in errors
    finally:
        witness.write_bytes(saved)
    assert_native(source_copy)


def test_missing_raw_archive_is_rejected_even_when_the_witness_body_is_intact(source_copy):
    assert_native(source_copy)
    path = source_copy / "witnesses/raw" / RAW
    saved = path.read_bytes()
    path.unlink()
    try:
        errors, checked = check_transcriptions(source_copy / "witnesses" / TEXTS[1])
        assert checked == 0
        assert "mr.txt: declared raw source has no local archive: ../raw/" + RAW in errors
        assert any(
            "names archive(s) that do not exist" in error
            for error in witness_archive.check(source_copy)
        )
    finally:
        path.write_bytes(saved)
    assert_native(source_copy)

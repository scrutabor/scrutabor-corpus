"""Reader notes preserve material limits without exposing editorial decisions."""

import pytest
from test_bibliography_graph import CORPUS, sample

from build_reader.bibliography import public_text_evidence, validate


def test_reader_note_stays_with_its_language_and_use():
    graph, languages = sample()
    use = languages["pl"]["uses"][0]
    use["reader_note"] = "Druk zawiera tylko końcową prośbę."
    use["decision_reason"] = "Private verification record."
    assert validate(CORPUS, graph, languages) == []
    evidence = public_text_evidence(graph, languages["pl"])
    entry = evidence["texts"][0]["source_groups"][0]["entries"][0]
    assert entry["reader_note"] == use["reader_note"]
    assert entry["address"] == {"kind": "segment", "segment": "s01"}
    assert "decision_reason" not in entry
    assert public_text_evidence(graph, languages["en"])["texts"] == []


@pytest.mark.parametrize("value", [None, "", "  ", " padded ", 1, ["note"]])
def test_reader_note_rejects_missing_or_untyped_prose(value):
    graph, languages = sample()
    languages["pl"]["uses"][0]["reader_note"] = value
    assert any("reader_note" in error for error in validate(CORPUS, graph, languages))


def test_reader_note_cannot_cross_into_the_neutral_package():
    graph, languages = sample()
    graph["uses"][0]["reader_note"] = "A note in only one reader language."
    assert any("reader_note" in error for error in validate(CORPUS, graph, languages))

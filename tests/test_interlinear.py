"""Explicit interlinear alignments replace visible editorial placeholders."""

from checks.interlinear import check, effective_gloss

DOC = {
    "id": "t.future",
    "segments": [
        {
            "id": "s01",
            "type": "verse",
            "words": [
                {"id": "w1", "form": "est", "lemma": "sum", "morph": {"pos": "verb"}},
                {
                    "id": "w2",
                    "form": "futúrus",
                    "lemma": "sum",
                    "morph": {"pos": "verb"},
                },
                {"id": "w3", "form": "An", "lemma": "an", "morph": {"pos": "conj"}},
            ],
        }
    ],
}


def layer():
    return {
        "language": "pl",
        "segments": {
            "s01": {
                "translation": "Będzie?",
                "alignments": [
                    {"words": ["w1", "w2"], "anchor": "w2", "gloss": "będzie"},
                    {"words": ["w3"], "reason": "word-order"},
                ],
            }
        },
        "words": {"w1": {}, "w2": {}, "w3": {}},
    }


def test_shared_and_zero_realizations_cover_each_source_word_once():
    assert check(DOC, layer()) == []
    assert effective_gloss(layer(), "w1") == ""
    assert effective_gloss(layer(), "w2") == "będzie"
    assert effective_gloss(layer(), "w3") == ""


def test_a_direct_gloss_cannot_duplicate_an_alignment():
    data = layer()
    data["words"]["w1"]["gloss"] = "jest"
    assert any("exactly one" in error for error in check(DOC, data))


def test_realized_groups_are_contiguous_and_have_an_anchor():
    data = layer()
    data["segments"]["s01"]["alignments"][0] = {
        "words": ["w1", "w3"],
        "anchor": "w2",
        "gloss": "będzie",
    }
    errors = check(DOC, data)
    assert any("contiguous" in error for error in errors)
    assert any("anchor" in error for error in errors)


def test_zero_realization_requires_a_declared_reason():
    data = layer()
    del data["segments"]["s01"]["alignments"][1]["reason"]
    assert any("reason" in error for error in check(DOC, data))

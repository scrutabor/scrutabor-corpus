"""The edition must be able to say what it does not know."""

from copy import deepcopy

from checks.uncertainty import check, exposure, readings, stored


def word(wid, form, lemma, morph, **extra):
    return {"id": wid, "form": form, "lemma": lemma, "morph": morph, **extra}


def doc(words, analysis_defaults=None):
    return {
        "id": "t.t",
        "analysis_defaults": analysis_defaults
        or {"confidence": "high", "sources": ["editorial"], "review": "pending"},
        "segments": [{"id": "s01", "type": "verse", "words": words}],
    }


# A FUNCTION, not a module constant: these dicts get mutated by the tests that
# add an analysis block, and a shared list leaked that mutation into the next
# test — which the suite caught and running the test alone did not.
def ambiguous():
    return deepcopy(
        [
            word(
                "w1", "malo", "malum", {"pos": "noun", "case": "abl", "number": "sg", "gender": "n"}
            ),
            word(
                "w2", "malo", "malus", {"pos": "adj", "case": "abl", "number": "sg", "gender": "m"}
            ),
        ]
    )


def test_exposure_counts_only_what_nothing_forces():
    d = doc(ambiguous())
    assert exposure(d, readings([d])) == 2
    # a head settles the reading by agreement
    d2 = doc(
        [
            ambiguous()[0],
            word(
                "w2",
                "malo",
                "malus",
                {"pos": "adj", "case": "abl", "number": "sg", "gender": "m"},
                head="w1",
            ),
        ]
    )
    assert exposure(d2, readings([d2])) == 1


def test_a_form_attested_one_way_is_not_exposure():
    d = doc([word("w1", "Deus", "deus", {"pos": "noun", "case": "nom", "number": "sg"})])
    assert exposure(d, readings([d])) == 0


def test_stored_reads_the_default_as_well_as_the_word():
    d = doc(ambiguous())
    assert stored(d) == 0
    d["segments"][0]["words"][0]["analysis"] = {
        "confidence": "medium",
        "sources": ["editorial"],
        "review": "disputed",
    }
    assert stored(d) == 1


def test_exposure_without_any_stored_doubt_fails_the_build():
    d = doc(ambiguous())
    assert check([d])
    d["segments"][0]["words"][0]["analysis"] = {
        "confidence": "medium",
        "sources": ["editorial"],
        "review": "disputed",
    }
    assert check([d]) == []


def test_a_corpus_with_no_exposure_needs_no_stored_doubt():
    d = doc([word("w1", "Deus", "deus", {"pos": "noun", "case": "nom", "number": "sg"})])
    assert check([d]) == []


def test_stored_reads_the_joined_document_without_the_store_seam():
    # The 0.14.0 document keeps the analysis under `editorial`. Read straight
    # off disk this used to return zero — right in the suite only because
    # build_reader/store.py split the document first. No seam is trusted now.
    doc = {
        "editorial": {
            "analysis_defaults": {"confidence": "high", "review": "accepted"},
            "words": {"w002": {"analysis": {"confidence": "medium", "review": "disputed"}}},
        },
        "segments": [{"words": [{"id": "w001", "form": "a"}, {"id": "w002", "form": "b"}]}],
    }
    assert stored(doc) == 1

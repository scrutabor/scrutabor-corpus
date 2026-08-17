"""The English checks: only what is decidable without English morphology."""

from checks.english import check_doubled_preposition, check_two_case_prepositions


def doc(words):
    return {"id": "t.t", "segments": [{"id": "s01", "type": "verse", "words": words}]}


def gloss(pairs):
    return {"lang": "en", "words": {k: {"gloss": v} for k, v in pairs.items()}}


PREP = {"form": "de", "lemma": "de", "morph": {"pos": "prep"}, "id": "w1", "head": "w2"}
NOUN = {
    "form": "cælis",
    "lemma": "caelum",
    "morph": {"pos": "noun", "case": "abl", "number": "pl", "gender": "m"},
    "id": "w2",
}


def test_a_preposition_may_not_be_rendered_twice():
    # "Father from of heaven": de glossed from, caelis glossed of heaven
    assert check_doubled_preposition(doc([PREP, NOUN]), gloss({"w1": "from", "w2": "of heaven"}))
    assert check_doubled_preposition(doc([PREP, NOUN]), gloss({"w1": "from", "w2": "heaven"})) == []


def test_in_follows_the_case_it_governs():
    acc = {
        "form": "cælum",
        "lemma": "caelum",
        "morph": {"pos": "noun", "case": "acc", "number": "sg", "gender": "n"},
        "id": "w2",
    }
    prep = {"form": "in", "lemma": "in", "morph": {"pos": "prep"}, "id": "w1", "head": "w2"}
    assert check_two_case_prepositions(doc([prep, acc]), gloss({"w1": "in", "w2": "heaven"}))
    assert (
        check_two_case_prepositions(doc([prep, acc]), gloss({"w1": "into", "w2": "heaven"})) == []
    )
    abl = dict(acc, morph={"pos": "noun", "case": "abl", "number": "sg", "gender": "n"})
    assert check_two_case_prepositions(doc([prep, abl]), gloss({"w1": "in", "w2": "heaven"})) == []


def test_english_idiom_is_declared_not_guessed():
    from checks.english import IDIOM_RULINGS

    # one does not believe INTO God, and the corpus says so as data
    assert ("ordinarium.credo", "w002") in IDIOM_RULINGS
    assert ("psalmi.118-he", "w022") in IDIOM_RULINGS


def _noun(lemma, form, number, wid):
    return {
        "id": wid,
        "form": form,
        "lemma": lemma,
        "morph": {"pos": "noun", "case": "abl", "number": number, "gender": "n"},
    }


def _pair(glosses, words):
    doc = {"id": "t.t", "segments": [{"id": "s01", "type": "verse", "words": words}]}
    return doc, {"lang": "en", "words": {k: {"gloss": v} for k, v in glosses.items()}}


def test_one_english_gloss_may_not_serve_both_numbers():
    from checks.english import check_number

    words = [_noun("mens", "mente", "sg", "w1"), _noun("mens", "méntibus", "pl", "w2")]
    assert check_number([_pair({"w1": "mind", "w2": "minds"}, words)]) == []
    assert check_number([_pair({"w1": "mind", "w2": "mind"}, words)])


def test_a_declared_ruling_silences_the_english_number_check():
    from checks.english import ENGLISH_NUMBER_RULINGS, check_number

    assert "caelum" in ENGLISH_NUMBER_RULINGS
    words = [_noun("caelum", "cælo", "sg", "w1"), _noun("caelum", "cælis", "pl", "w2")]
    assert check_number([_pair({"w1": "heaven", "w2": "heaven"}, words)]) == []


def test_a_derivative_belongs_to_one_lemma():
    from checks.lexicon import check_derivative_homes

    lex = {"entries": {"oratio": {"derivatives": ["oration"]}, "oro": {"derivatives": ["orator"]}}}
    assert check_derivative_homes(lex) == []
    lex["entries"]["oro"]["derivatives"].append("oration")
    assert check_derivative_homes(lex)

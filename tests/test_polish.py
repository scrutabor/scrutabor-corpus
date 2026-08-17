"""The Polish checks: the mistakes a reader sees before an expert is ever found."""

from checks.polish import cases, check_divine_address, check_modifier_glosses, check_prepositions


def doc(words):
    return {"id": "t.t", "segments": [{"id": "s01", "type": "verse", "words": words}]}


def gloss(pairs, translation=None):
    out = {"lang": "pl", "words": {k: {"gloss": v} for k, v in pairs.items()}}
    if translation is not None:
        out["segments"] = {"s01": {"translation": translation}}
    return out


def test_morfeusz_reads_the_cases():
    assert "dat" in cases("Tobie")
    assert "dat" not in cases("Ciebie")
    assert "inst" in cases("słowem")
    assert "loc" in cases("słowie")


def test_preposition_must_govern_its_object():
    # ku Ciebie, which the Advent introit carried: ku takes the dative
    d = doc(
        [
            {"form": "Ad", "lemma": "ad", "morph": {"pos": "prep"}, "id": "w1", "head": "w2"},
            {
                "form": "te",
                "lemma": "tu",
                "morph": {"pos": "pron", "case": "acc", "number": "sg"},
                "id": "w2",
            },
        ]
    )
    assert check_prepositions(d, gloss({"w1": "ku", "w2": "Ciebie"}))
    assert check_prepositions(d, gloss({"w1": "do", "w2": "Ciebie"})) == []


def test_preposition_object_is_its_head_not_its_neighbour():
    # Per sanctissimae Eucharistiae INSTITUTIONEM: two genitives intervene
    d = doc(
        [
            {"form": "Per", "lemma": "per", "morph": {"pos": "prep"}, "id": "w1", "head": "w3"},
            {
                "form": "Eucharístiæ",
                "lemma": "eucharistia",
                "morph": {"pos": "noun", "case": "gen", "number": "sg", "gender": "f"},
                "id": "w2",
            },
            {
                "form": "institutiónem",
                "lemma": "institutio",
                "morph": {"pos": "noun", "case": "acc", "number": "sg", "gender": "f"},
                "id": "w3",
            },
        ]
    )
    assert (
        check_prepositions(d, gloss({"w1": "przez", "w2": "Eucharystii", "w3": "ustanowienie"}))
        == []
    )


def test_an_interjection_is_not_the_preposition_o():
    d = doc(
        [
            {"form": "O", "lemma": "o", "morph": {"pos": "intj"}, "id": "w1"},
            {
                "form": "clemens",
                "lemma": "clemens",
                "morph": {"pos": "adj", "case": "voc", "number": "sg", "gender": "f"},
                "id": "w2",
            },
        ]
    )
    assert check_prepositions(d, gloss({"w1": "O", "w2": "łaskawa"})) == []


def test_modifier_gloss_agrees_with_its_head_gloss():
    d = doc(
        [
            {
                "form": "ira",
                "lemma": "ira",
                "morph": {"pos": "noun", "case": "abl", "number": "sg", "gender": "f"},
                "id": "w1",
            },
            {
                "form": "tua",
                "lemma": "tuus",
                "morph": {"pos": "adj", "case": "abl", "number": "sg", "gender": "f"},
                "id": "w2",
                "head": "w1",
            },
        ]
    )
    assert check_modifier_glosses(d, gloss({"w1": "gniewu", "w2": "Twoją"}))
    assert check_modifier_glosses(d, gloss({"w1": "gniewu", "w2": "Twego"})) == []


def test_a_phrase_gloss_is_left_alone():
    # godna podziwu: the head is not the last word, so guessing invents errors
    d = doc(
        [
            {
                "form": "Mater",
                "lemma": "mater",
                "morph": {"pos": "noun", "case": "voc", "number": "sg", "gender": "f"},
                "id": "w1",
            },
            {
                "form": "admirábilis",
                "lemma": "admirabilis",
                "morph": {"pos": "adj", "case": "voc", "number": "sg", "gender": "f"},
                "id": "w2",
                "head": "w1",
            },
        ]
    )
    assert check_modifier_glosses(d, gloss({"w1": "Matko", "w2": "godna podziwu"})) == []


def test_divine_address_follows_its_own_verse():
    d = doc(
        [
            {
                "form": "tuum",
                "lemma": "tuus",
                "morph": {"pos": "adj", "case": "acc", "number": "sg", "gender": "n"},
                "id": "w1",
            },
        ]
    )
    assert check_divine_address(d, gloss({"w1": "twój"}, "ołtarz Twój, Panie"))
    assert check_divine_address(d, gloss({"w1": "Twój"}, "ołtarz Twój, Panie")) == []
    # and where the verse itself lowercases it — the priest, not God — nothing
    assert check_divine_address(d, gloss({"w1": "twoim"}, "I z duchem twoim.")) == []


def test_latin_plural_is_glossed_in_the_plural():
    from checks.polish import check_number

    d = doc(
        [
            {
                "form": "laudes",
                "lemma": "laus",
                "morph": {"pos": "noun", "case": "acc", "number": "pl", "gender": "f"},
                "id": "w1",
            },
        ]
    )
    assert check_number(d, gloss({"w1": "chwałę"}))
    assert check_number(d, gloss({"w1": "chwały"})) == []


def test_a_declared_ruling_silences_the_number_check():
    from checks.polish import NUMBER_RULINGS, check_number

    # omnia glossed with the Polish collective wszystko, declared as data
    assert ("ordinarium.credo", "w049") in NUMBER_RULINGS
    d = {
        "id": "ordinarium.credo",
        "segments": [
            {
                "id": "s01",
                "type": "verse",
                "words": [
                    {
                        "form": "ómnia",
                        "lemma": "omnis",
                        "morph": {"pos": "adj", "case": "nom", "number": "pl", "gender": "n"},
                        "id": "w049",
                    },
                ],
            }
        ],
    }
    assert check_number(d, gloss({"w049": "wszystko"})) == []


def _abs_doc():
    """dimíssis peccátis — a participle and its noun, both ablative, no preposition."""
    return doc(
        [
            {
                "form": "dimíssis",
                "lemma": "dimitto",
                "morph": {
                    "pos": "verb",
                    "mood": "part",
                    "case": "abl",
                    "number": "pl",
                    "gender": "n",
                },
                "id": "w1",
                "head": "w2",
            },
            {
                "form": "peccátis",
                "lemma": "peccatum",
                "morph": {"pos": "noun", "case": "abl", "number": "pl", "gender": "n"},
                "id": "w2",
            },
        ]
    )


def test_morfeusz_reads_the_case_of_a_participle():
    # pact and ppas decline like adjectives; without them every participle
    # gloss read as caseless and the ablative absolute went unchecked.
    assert "inst" in cases("odpuszczonymi")
    assert "inst" in cases("zwiastującym")
    assert "nom" in cases("odpuszczone")


def test_an_ablative_absolute_is_glossed_in_the_instrumental():
    from checks.polish import check_ablative_absolute

    assert (
        check_ablative_absolute(_abs_doc(), gloss({"w1": "odpuszczonymi", "w2": "grzechami"})) == []
    )
    # the nominative phrase this site used to carry
    assert check_ablative_absolute(_abs_doc(), gloss({"w1": "odpuszczone", "w2": "grzechy"}))


def test_an_ablative_absolute_may_not_import_a_preposition():
    from checks.polish import check_ablative_absolute

    # za wstawiennictwem Dziewicy: the Latin has no preposition to render
    assert check_ablative_absolute(
        _abs_doc(), gloss({"w1": "za wstawiennictwem", "w2": "grzechami"})
    )


def test_a_participle_governed_by_a_preposition_is_not_absolute():
    from checks.polish import check_ablative_absolute

    d = _abs_doc()
    d["segments"][0]["words"].append(
        {"form": "ab", "lemma": "ab", "morph": {"pos": "prep"}, "id": "w3", "head": "w2"}
    )
    assert check_ablative_absolute(d, gloss({"w1": "odpuszczone", "w2": "grzechy"})) == []


def _ut_doc(verb_form, mood="subj"):
    return doc(
        [
            {"form": "ut", "lemma": "ut", "morph": {"pos": "conj"}, "id": "w1"},
            {
                "form": verb_form,
                "lemma": "sum",
                "morph": {"pos": "verb", "mood": mood, "number": "pl"},
                "id": "w2",
            },
        ]
    )


def test_a_purpose_clause_takes_the_l_form():
    from checks.polish import check_purpose_clauses

    d = _ut_doc("simus")
    assert check_purpose_clauses(d, gloss({"w1": "abyśmy", "w2": "byli"})) == []
    # a second by particle, which stood in Libera nos
    assert check_purpose_clauses(d, gloss({"w1": "aby", "w2": "byśmy byli"}))
    # a niech jussive, which stood in both Suscipe prayers
    assert check_purpose_clauses(d, gloss({"w1": "aby", "w2": "niech będzie"}))
    # an imperative, which stood in Aufer a nobis and the Preface
    assert check_purpose_clauses(d, gloss({"w1": "aby", "w2": "racz"}))


def test_a_purpose_check_is_silent_where_ut_is_not_aby():
    from checks.polish import check_purpose_clauses

    # ut glossed as something other than a subordinator: nothing to enforce
    assert check_purpose_clauses(_ut_doc("simus"), gloss({"w1": "że", "w2": "niech będzie"})) == []


def _pair(mine, theirs, gender="n"):
    return doc(
        [
            {
                "form": "spirituále",
                "lemma": "spiritualis",
                "morph": {"pos": "adj", "case": "voc", "number": "sg", "gender": gender},
                "id": "w1",
                "head": "w2",
            },
            {
                "form": "Vas",
                "lemma": "vas",
                "morph": {"pos": "noun", "case": "voc", "number": "sg", "gender": gender},
                "id": "w2",
            },
        ]
    ), gloss({"w1": mine, "w2": theirs})


def test_morfeusz_reads_gender():
    from checks.polish import genders

    assert genders("naczynie") == frozenset({"n"})
    assert "m" in genders("duchowy")
    assert "n" in genders("duchowe")


def test_a_modifier_gloss_agrees_in_gender_and_number():
    from checks.polish import check_modifier_glosses

    d, g = _pair("duchowe", "naczynie")
    assert check_modifier_glosses(d, g) == []
    # duchowy over naczynie: the cases overlap, so only gender catches it
    d, g = _pair("duchowy", "naczynie")
    assert check_modifier_glosses(d, g)
    # and number, which nothing checked either. The pair has to be
    # unambiguous: Polish syncretism makes *naczynia* gen sg AND nom pl, and
    # the check is right to stay silent where the forms could stand together.
    d, g = _pair("duchowemu", "naczyniu")
    assert check_modifier_glosses(d, g) == []
    d, g = _pair("duchowemu", "naczyniom")
    assert check_modifier_glosses(d, g)

"""The prose a reader reads and the data a reader parses must agree."""

from checks.notes import check


def case(head, note, substantive=False):
    word = {
        "id": "w002",
        "form": "natum",
        "lemma": "nascor",
        "morph": {"pos": "verb", "mood": "part", "case": "acc", "number": "sg", "gender": "m"},
    }
    if substantive:
        word["substantive"] = True
    elif head:
        word["head"] = head
    doc = {
        "id": "t.t",
        "segments": [
            {
                "id": "s01",
                "words": [
                    {
                        "id": "w001",
                        "form": "Fílium",
                        "lemma": "filius",
                        "morph": {"pos": "noun", "case": "acc", "number": "sg", "gender": "m"},
                    },
                    word,
                    {
                        "id": "w003",
                        "form": "Deum",
                        "lemma": "deus",
                        "morph": {"pos": "noun", "case": "acc", "number": "sg", "gender": "m"},
                    },
                ],
            }
        ],
    }
    return doc, {"lang": "pl", "words": {"w002": {"explanation": note}}}


def test_the_note_and_the_head_must_name_the_same_word():
    assert check(*case("w001", "Zgadza się z „Fílium” (w001).")) == []
    assert check(*case("w003", "Zgadza się z „Fílium” (w001)."))


def test_a_note_may_name_several_words_in_apposition():
    # sperántibus agrees with Nobis AND fámulis, truthfully; the data records
    # one of them, and the check asks only that it be among those named.
    note = "Zgadza się z „Fílium” (w001) i „Deum” (w003)."
    assert check(*case("w001", note)) == []
    assert check(*case("w003", note)) == []


def test_a_note_may_reference_a_four_digit_word_id():
    doc, gloss = case("w1000", "Zgadza się z „Fílium” (w1000).")
    doc["segments"][0]["words"][0]["id"] = "w1000"
    assert check(doc, gloss) == []


def test_substantive_contradicts_any_agreement_claim():
    errors = check(*case(None, "Zgadza się z „Fílium” (w001).", substantive=True))
    assert errors and "substantive" in errors[0]


def test_english_notes_are_read_too():
    doc, gloss = case("w003", "Agrees with “Fílium” (w001).")
    gloss["lang"] = "en"
    assert check(doc, gloss)


def test_a_note_naming_no_id_asserts_nothing():
    assert check(*case("w003", "An accusative participle in apposition.")) == []


def parse(note, form, table_name):
    from checks import notes as N

    table = {"case": N.CASE_WORDS, "number": N.NUMBER_WORDS, "mood": N.MOOD_WORDS}[table_name]
    return N._parse_claim(note, form, table["en"])


def test_a_note_states_its_own_parse():
    assert parse("Ablative after “in” (w029).", "cælo", "case") == "abl"
    assert parse("Nominative plural agreeing with “inimíci”.", "mei", "number") == "pl"
    assert parse("An imperative addressed to the Lord.", "audi", "mood") == "imp"


def test_a_governed_case_is_not_a_claim_about_this_word():
    # "It governs three genitives" says nothing about mémores' own case
    assert parse("It governs three genitives: “passiónis”.", "mémores", "case") is None
    assert parse("Takes the dative “Patri” (w046).", "consubstantiálem", "case") is None
    assert parse("Takes an accusative of the person and an infinitive.", "precor", "mood") is None


def test_a_word_named_first_is_the_one_described():
    # the note is about viscéribus, not about adhǽreat
    assert parse("“Viscéribus” is read as a plural dative.", "adhǽreat", "number") is None


def test_a_syncretism_note_names_two_and_is_not_a_claim():
    assert parse("“Spíritus” can be nominative or genitive.", "Spíritus", "case") is None
    assert parse("“Deus” is the same in nominative and vocative.", "Deus", "case") is None


def test_the_check_reports_a_real_disagreement():
    from checks.notes import check

    doc = {
        "id": "t.t",
        "segments": [
            {
                "id": "s01",
                "words": [
                    {
                        "id": "w001",
                        "form": "cælo",
                        "lemma": "caelum",
                        "morph": {"pos": "noun", "case": "dat", "number": "sg", "gender": "n"},
                    }
                ],
            }
        ],
    }
    gloss = {"lang": "en", "words": {"w001": {"explanation": "Ablative after “in”."}}}
    errors = check(doc, gloss)
    assert errors and "case='abl'" in errors[0] and "'dat'" in errors[0]

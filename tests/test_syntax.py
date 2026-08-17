"""The syntax check: what it must catch, and what it must not mistake for an error."""

from checks.syntax import check, coverage


def doc(words, second=None):
    segments = [{"id": "s01", "type": "verse", "words": words}]
    if second is not None:
        segments.append({"id": "s02", "type": "verse", "words": second})
    return {"id": "t.t", "segments": segments}


def w(wid, form, pos, lemma="x", head=None, substantive=None, **morph):
    out = {"form": form, "lemma": lemma, "morph": {"pos": pos, **morph}, "id": wid}
    if head is not None:
        out["head"] = head
    if substantive is not None:
        out["substantive"] = substantive
    return out


NOUN = dict(case="gen", number="pl", gender="m")


def test_modifier_must_match_its_head():
    # aeterni against Patris: the error the litany carried, in miniature
    bad = doc(
        [
            w("w1", "Patris", "noun", **NOUN),
            w("w2", "ætérni", "adj", head="w1", case="gen", number="pl", gender="n"),
        ]
    )
    assert any("gender" in e for e in check(bad))
    good = doc(
        [
            w("w1", "Patris", "noun", **NOUN),
            w("w2", "ætérni", "adj", head="w1", **NOUN),
        ]
    )
    assert check(good) == []


def test_preposition_government():
    # in Domino marked dative, as De profundis carried it twice
    bad = doc(
        [
            w("w1", "in", "prep", lemma="in", head="w2"),
            w("w2", "Dómino", "noun", case="dat", number="sg", gender="m"),
        ]
    )
    assert any("takes the" in e for e in check(bad))
    good = doc(
        [
            w("w1", "in", "prep", lemma="in", head="w2"),
            w("w2", "Dómino", "noun", case="abl", number="sg", gender="m"),
        ]
    )
    assert check(good) == []


def test_relative_agrees_with_its_verb_in_number():
    # qui tollis: second person SINGULAR, so qui is singular
    bad = doc(
        [
            w("w1", "qui", "pron", lemma="qui", head="w2", case="nom", number="pl", gender="m"),
            w("w2", "tollis", "verb", lemma="tollo", person=2, number="sg", mood="ind"),
        ]
    )
    assert any("subject of" in e for e in check(bad))


def test_head_may_stand_in_another_segment():
    # Et ex Patre natum takes its head from the segment before
    d = doc(
        [w("w1", "Dóminum", "noun", case="acc", number="sg", gender="m")],
        [
            w(
                "w2",
                "natum",
                "verb",
                lemma="nascor",
                head="w1",
                mood="part",
                case="acc",
                number="sg",
                gender="m",
            )
        ],
    )
    assert check(d) == []


def test_personal_pronoun_lends_no_gender():
    # omnes nos accepimus: nos carries no gender, so only case and number bind
    d = doc(
        [
            w("w1", "nos", "pron", lemma="nos", case="nom", number="pl", gender=None),
            w("w2", "omnes", "adj", head="w1", case="nom", number="pl", gender="m"),
        ]
    )
    assert check(d) == []


def test_substantive_agrees_with_nothing():
    d = doc([w("w1", "infirmórum", "adj", substantive=True, **NOUN)])
    assert check(d) == []
    both = doc(
        [
            w("w1", "Salus", "noun", case="nom", number="sg", gender="f"),
            w("w2", "infirmórum", "adj", head="w1", substantive=True, **NOUN),
        ]
    )
    assert any("also carries a head" in e for e in check(both))


def test_substantival_participle_may_head_a_modifier():
    # omnium circumstantium: the participle is a noun here, not a finite verb
    d = doc(
        [
            w(
                "w1",
                "circumstántium",
                "verb",
                lemma="circumsto",
                substantive=True,
                mood="part",
                **NOUN,
            ),
            w("w2", "ómnium", "adj", head="w1", **NOUN),
        ]
    )
    assert check(d) == []


def test_coverage_counts_what_is_still_undeclared():
    d = doc(
        [
            w("w1", "Patris", "noun", **NOUN),
            w("w2", "ætérni", "adj", head="w1", **NOUN),
            w("w3", "sancti", "adj", **NOUN),
        ]
    )
    assert coverage(d) == (1, 2)


class TestGraphShape:
    """Agreement is symmetric, so the shape of the head graph needs its own rules."""

    def test_a_pair_naming_each_other_is_an_error(self) -> None:
        doc = {
            "id": "t",
            "segments": [
                {
                    "id": "s01",
                    "words": [
                        {
                            "id": "w1",
                            "form": "dignum",
                            "lemma": "dignus",
                            "morph": {"pos": "adj", "case": "nom", "number": "sg", "gender": "n"},
                            "head": "w2",
                        },
                        {
                            "id": "w2",
                            "form": "iustum",
                            "lemma": "iustus",
                            "morph": {"pos": "adj", "case": "nom", "number": "sg", "gender": "n"},
                            "head": "w1",
                        },
                    ],
                }
            ],
        }
        errors = check(doc)
        assert len(errors) == 2
        assert "name each other" in errors[0]

    def test_a_modifier_of_a_dependent_modifier_is_an_error(self) -> None:
        doc = {
            "id": "t",
            "segments": [
                {
                    "id": "s01",
                    "words": [
                        {
                            "id": "w1",
                            "form": "omnes",
                            "lemma": "omnis",
                            "morph": {"pos": "adj", "case": "nom", "number": "pl", "gender": "m"},
                            "head": "w2",
                        },
                        {
                            "id": "w2",
                            "form": "sancti",
                            "lemma": "sanctus",
                            "morph": {"pos": "adj", "case": "nom", "number": "pl", "gender": "m"},
                            "head": "w3",
                        },
                        {
                            "id": "w3",
                            "form": "viri",
                            "lemma": "vir",
                            "morph": {"pos": "noun", "case": "nom", "number": "pl", "gender": "m"},
                        },
                    ],
                }
            ],
        }
        errors = check(doc)
        assert len(errors) == 1
        assert "itself a" in errors[0] and "modifier of something else" in errors[0]


def test_a_declared_governs_must_match_the_object_it_heads() -> None:
    doc: dict = {
        "id": "t",
        "segments": [
            {
                "id": "s01",
                "words": [
                    {
                        "id": "w1",
                        "form": "in",
                        "lemma": "in",
                        "morph": {"pos": "prep", "governs": "abl"},
                        "head": "w2",
                    },
                    {
                        "id": "w2",
                        "form": "sǽcula",
                        "lemma": "saeculum",
                        "morph": {"pos": "noun", "case": "acc", "number": "pl", "gender": "n"},
                    },
                ],
            }
        ],
    }
    errors = check(doc)
    assert len(errors) == 1 and "declares governs" in errors[0]
    prep = doc["segments"][0]["words"][0]
    assert isinstance(prep, dict)
    prep["morph"]["governs"] = "acc"
    assert check(doc) == []

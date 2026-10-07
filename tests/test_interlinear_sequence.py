"""Glosses must compose into a line that can be read."""

from checks.interlinear_sequence import check


def doc(*words, posts=None):
    posts = posts or {}
    return {
        "id": "t.t",
        "segments": [
            {
                "id": "s01",
                "words": [
                    {
                        "id": f"w{i}",
                        "form": form,
                        "lemma": lemma,
                        "morph": morph,
                        "post": posts.get(i, ""),
                    }
                    for i, (form, lemma, morph) in enumerate(words, start=1)
                ],
            }
        ],
    }


def layer(language, glosses, alignments=None):
    words = {f"w{i}": {"gloss": g} for i, g in glosses.items() if g is not None}
    out = {"language": language, "words": words}
    out["segments"] = {"s01": {"alignments": alignments}} if alignments else {}
    for word_id in {w for a in alignments or [] for w in a["words"]}:
        out["words"].setdefault(word_id, {})
    return out


NOUN = {"pos": "noun"}
ADJ = {"pos": "adj"}
VERB = {"pos": "verb", "mood": "ind"}
PART = {"pos": "part"}

HOLY_SPIRIT = doc(("Spíritus", "spiritus", NOUN), ("Sancti", "sanctus", ADJ))
SPIRIT_HOLY = doc(("Sancti", "sanctus", ADJ), ("Spíritus", "spiritus", NOUN))


def test_split_holy_spirit_is_rejected_in_either_latin_order():
    assert check(HOLY_SPIRIT, layer("en", {1: "of the Spirit", 2: "Holy"}))
    assert check(SPIRIT_HOLY, layer("en", {1: "Holy", 2: "of the Spirit"}))


def test_holy_spirit_as_one_alignment_passes():
    shared = [{"words": ["w1", "w2"], "anchor": "w1", "gloss": "of the Holy Spirit"}]
    assert check(HOLY_SPIRIT, layer("en", {}, shared)) == []


def test_other_spirit_glosses_and_polish_order_are_not_flagged():
    assert check(HOLY_SPIRIT, layer("en", {1: "the spirit", 2: "of sanctification"})) == []
    assert check(HOLY_SPIRIT, layer("pl", {1: "Ducha", 2: "Świętego"})) == []


NON_EST = doc(("non", "non", PART), ("est", "sum", VERB))
NON_CREDAM = doc(("non", "non", PART), ("credam", "credo", VERB))


def test_not_before_an_auxiliary_is_rejected():
    assert check(NON_EST, layer("en", {1: "not", 2: "is"}))
    assert check(NON_CREDAM, layer("en", {1: "not", 2: "I will believe"}))
    assert check(NON_CREDAM, layer("en", {1: "not", 2: "there was"}))


def test_negation_aligned_with_its_verb_passes():
    shared = [{"words": ["w1", "w2"], "anchor": "w2", "gloss": "I will not believe"}]
    assert check(NON_CREDAM, layer("en", {}, shared)) == []
    assert check(NON_EST, layer("en", {1: "not", 2: "be"})) == []


NON_LAVABIS = doc(("Non", "non", PART), ("lavábis", "lavo", VERB))
NON_EST_OBLITUS = doc(("non", "non", PART), ("est", "sum", VERB), ("oblítus", "obliviscor", VERB))


def test_sentence_initial_not_and_archaic_auxiliaries_are_rejected():
    assert check(NON_EST, layer("en", {1: "Not", 2: "is"}))
    assert check(NON_LAVABIS, layer("en", {1: "Not", 2: "shalt Thou wash"}))
    assert check(NON_CREDAM, layer("en", {1: "not", 2: "thou wilt believe"}))


def test_not_before_a_group_that_begins_with_an_auxiliary_is_rejected():
    group = [{"words": ["w2", "w3"], "anchor": "w3", "gloss": "has forgotten"}]
    assert check(NON_EST_OBLITUS, layer("en", {1: "not"}, group))


def test_negation_inside_the_group_passes():
    group = [{"words": ["w1", "w2", "w3"], "anchor": "w3", "gloss": "He has not forgotten"}]
    assert check(NON_EST_OBLITUS, layer("en", {}, group)) == []
    capital = [{"words": ["w1", "w2"], "anchor": "w2", "gloss": "Thou shalt not wash"}]
    assert check(NON_LAVABIS, layer("en", {}, capital)) == []


BOWIEM = doc(
    ("méi", "meus", ADJ),
    ("étenim", "etenim", PART),
    ("univérsi", "universus", ADJ),
    posts={1: ":"},
)
ENIM = doc(("Pan", "dominus", NOUN), ("enim", "enim", PART))


def test_bowiem_cannot_open_a_clause():
    assert check(BOWIEM, layer("pl", {1: "moi", 2: "bowiem", 3: "wszyscy"}))
    assert check(doc(("étenim", "etenim", PART)), layer("pl", {1: "Bowiem"}))


def test_postpositive_bowiem_and_albowiem_pass():
    assert check(ENIM, layer("pl", {1: "Pan", 2: "bowiem"})) == []
    assert check(BOWIEM, layer("pl", {1: "moi", 2: "albowiem", 3: "wszyscy"})) == []

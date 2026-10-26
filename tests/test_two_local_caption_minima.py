"""Two known local constructions, not a global possessive or word-count rule."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from checks.interlinear import check, effective_gloss

ROOT = Path(__file__).resolve().parents[1]
SLUGS = ("evangelium-ultimum", "communicantes-in-ascensione-domini")
LATIN = {
    SLUGS[0]: (
        "Quotquot autem recepérunt eum dedit eis potestátem fílios Dei fíeri his qui credunt "
        "in nómine eius qui non ex sanguínibus neque ex voluntáte carnis neque ex voluntáte "
        "viri sed ex Deo nati sunt"
    ),
    SLUGS[1]: (
        "Communicántes et diem sacratíssimum celebrántes quo Dóminus noster unigénitus "
        "Fílius tuus unítam sibi fragilitátis nostræ substántiam in glóriæ tuæ déxtera collocávit"
    ),
}
CAPTIONS = {
    (SLUGS[0], "pl"): (
        "Ilu tylko | jednak | przyjęło | Go | dał | im | moc | synami | Boga | stać się | "
        "tym | którzy | wierzą | w | imię | Jego | którzy | nie | z | krwi | ani | z | woli | "
        "ciała | ani | z | woli | męża | lecz | z | Boga | narodzili się"
    ),
    (SLUGS[0], "en"): (
        "As many as | but | received | Him | He gave | them | power | sons | of God | "
        "to become | to those | who | believe | in | His name | who | not | of | blood | "
        "nor | of | the will | of the flesh | nor | of | the will | of man | but | of | God | "
        "were born"
    ),
    (SLUGS[1], "pl"): (
        "Trwamy we wspólnocie | i | obchodzimy najświętszy dzień | w którym | nasz Pan | "
        "Twój Jednorodzony Syn | naszą słabą naturę zjednoczoną z sobą | "
        "po prawicy Twojej chwały | umieścił"
    ),
    (SLUGS[1], "en"): (
        "We are in communion | and | celebrate the most sacred day | on which | our Lord | "
        "Your Only-begotten Son | our frail human nature united to Himself | "
        "at the right hand of Your glory | placed"
    ),
}


def subject(slug, language):
    relative = f"texts/ordinarium/{slug}.json"
    return json.loads((ROOT / relative).read_text()), json.loads(
        (ROOT / "languages" / language / relative).read_text()
    )


def alignment(layer, sid, wid):
    return next(a for a in layer["segments"][sid]["alignments"] if wid in a["words"])


def assert_local_caption(core, layer, slug, language):
    """Exact agreed local partition and complete context, not a naturalness parser."""
    sid, first, last = ("s10", 133, 165) if slug == SLUGS[0] else ("s01", 1, 21)
    source = next(s["words"] for s in core["segments"] if s["id"] == sid)
    words = [w for w in source if first <= int(w["id"][1:]) <= last]
    assert [w["id"] for w in words] == [f"w{i:03}" for i in range(first, last + 1)]
    assert [w["form"] for w in words] == LATIN[slug].split()
    assert check(core, layer) == []
    assert (
        " | ".join(gloss for w in words if (gloss := effective_gloss(layer, w["id"])))
        == CAPTIONS[slug, language]
    )
    if language == "en":
        expected = (
            [(["w147", "w148"], "w147", "His name")]
            if slug == SLUGS[0]
            else [
                (
                    [f"w{i:03}" for i in range(12, 17)],
                    "w016",
                    "our frail human nature united to Himself",
                ),
                (
                    [f"w{i:03}" for i in range(17, 21)],
                    "w020",
                    "at the right hand of Your glory",
                ),
            ]
        )
        for members, anchor, gloss in expected:
            touching = [
                a for a in layer["segments"][sid]["alignments"] if set(members) & set(a["words"])
            ]
            assert touching == [{"words": members, "anchor": anchor, "gloss": gloss}]
        if slug == SLUGS[1]:
            assert layer["words"]["w021"]["gloss"] == "placed"


@pytest.mark.parametrize(
    "slug,language",
    [
        pytest.param(SLUGS[0], "pl", id="last-gospel-pl"),
        pytest.param(SLUGS[0], "en", id="last-gospel-en"),
        pytest.param(SLUGS[1], "pl", id="ascension-pl"),
        pytest.param(SLUGS[1], "en", id="ascension-en"),
    ],
)
def test_complete_local_clause_and_minimal_partition(slug, language):
    assert_local_caption(*subject(slug, language), slug, language)


def test_name_possession_reversion_and_realization_faults_recover():
    slug, sid = SLUGS[0], "s10"
    core, layer = subject(slug, "en")
    snapshot = deepcopy((core, layer))
    assert_local_caption(core, layer, slug, "en")
    for kind in ("old-order", "wrong-possessor", "missing-name", "duplicate", "birth-tense"):
        changed = deepcopy(layer)
        group = alignment(changed, sid, "w147")
        if kind == "old-order":
            changed["segments"][sid]["alignments"].remove(group)
            changed["words"]["w147"]["gloss"] = "name"
            changed["words"]["w148"]["gloss"] = "His"
        elif kind == "wrong-possessor":
            group["gloss"] = "their name"
        elif kind == "missing-name":
            group["gloss"] = "His"
        elif kind == "duplicate":
            changed["words"]["w148"]["gloss"] = "His"
        else:
            alignment(changed, sid, "w164")["gloss"] = "are born"
        assert changed != layer
        with pytest.raises(AssertionError):
            assert_local_caption(core, changed, slug, "en")
        assert (core, layer) == snapshot
        assert_local_caption(core, layer, slug, "en")
    assert subject(slug, "en") == snapshot


def test_united_object_location_and_perfect_predicate_faults_recover():
    slug, sid = SLUGS[1], "s01"
    core, layer = subject(slug, "en")
    snapshot = deepcopy((core, layer))
    assert_local_caption(core, layer, slug, "en")
    for kind in (
        "old-clause",
        "wrong-reflexive",
        "lost-union",
        "wrong-glory",
        "tense",
        "duplicate",
    ):
        changed = deepcopy(layer)
        if kind == "old-clause":
            changed["segments"][sid]["alignments"][3:] = [
                {
                    "words": [f"w{i:03}" for i in range(12, 22)],
                    "anchor": "w021",
                    "gloss": (
                        "placed our frail human nature, united to Himself, "
                        "at the right hand of Your glory"
                    ),
                }
            ]
            del changed["words"]["w021"]["gloss"]
        elif kind == "wrong-reflexive":
            alignment(changed, sid, "w012")["gloss"] = "our frail human nature united to the Father"
        elif kind == "lost-union":
            alignment(changed, sid, "w012")["gloss"] = "our frail human nature"
        elif kind == "wrong-glory":
            alignment(changed, sid, "w017")["gloss"] = "at the right hand of His glory"
        elif kind == "tense":
            changed["words"]["w021"]["gloss"] = "places"
        else:
            changed["words"]["w012"]["gloss"] = "united"
        assert changed != layer
        with pytest.raises(AssertionError):
            assert_local_caption(core, changed, slug, "en")
        assert (core, layer) == snapshot
        assert_local_caption(core, layer, slug, "en")
    assert subject(slug, "en") == snapshot

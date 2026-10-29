"""Known Communicantes caption boundaries, not a universal word-order rule."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from checks.interlinear import check as check_interlinear

ROOT = Path(__file__).resolve().parents[1]


def subject(slug, language):
    rel = f"texts/ordinarium/{slug}.json"
    return json.loads((ROOT / rel).read_text()), json.loads(
        (ROOT / "languages" / language / rel).read_text()
    )


def group(core, layer, sid, members, anchor, glosses):
    """A known minimal span, all source members realized exactly once."""
    source = next(s["words"] for s in core["segments"] if s["id"] == sid)
    ids = [w["id"] for w in source]
    start = ids.index(members[0])
    assert ids[start : start + len(members)] == members
    matches = [a for a in layer["segments"][sid].get("alignments", []) if a["words"] == members]
    assert len(matches) == 1, f"missing complete {sid}/{members} group"
    actual = matches[0]
    assert actual["anchor"] == anchor
    assert actual["gloss"] in glosses
    for wid in members:
        assert "gloss" not in layer["words"][wid], f"duplicate direct gloss {wid}"
        assert sum(wid in a["words"] for a in layer["segments"][sid]["alignments"]) == 1
    return actual


def caption(core, layer, sid):
    source = next(s["words"] for s in core["segments"] if s["id"] == sid)
    groups = layer["segments"][sid].get("alignments", [])
    parts = []
    for word in source:
        matches = [a for a in groups if word["id"] in a["words"]]
        assert len(matches) <= 1
        if matches:
            assert "gloss" not in layer["words"][word["id"]]
            if word["id"] == matches[0]["words"][0]:
                parts.append(matches[0]["gloss"])
        else:
            parts.append(layer["words"][word["id"]]["gloss"])
    return " | ".join(parts)


PL_AID = {
    "byli bronieni pomocą Twojej opieki",
    "byli obwarowani pomocą Twojej opieki",
    "byli umocnieni pomocą Twojej opieki",
    "byli umocnieni wsparciem Twojej opieki",
}
EN_AID = {
    "we may be defended by the help of Your protection",
    "we may be strengthened by the aid of Your protection",
    "we may be fortified by the aid of Your protection",
}


def assert_known_caption(core, layer, language):
    """Complete-line relations at the two remediated children only."""
    ordinary = core["id"] == "ordinarium.communicantes"
    if ordinary and language == "en":
        assert layer["words"]["w001"]["gloss"] == "remaining in communion"
        group(core, layer, "s01", ["w003", "w004"], "w004", {"venerating the memory"})
        group(core, layer, "s01", ["w014", "w015"], "w014", {"our Lord"})
        group(
            core,
            layer,
            "s02",
            ["w022", "w023", "w024"],
            "w024",
            {"Spouse of the same Virgin", "Spouse of that same Virgin"},
        )
        group(
            core,
            layer,
            "s03",
            ["w026", "w027", "w028", "w029", "w030"],
            "w027",
            {"of Your blessed apostles and martyrs"},
        )
        group(core, layer, "s05", ["w060", "w061", "w062"], "w061", {"of all Your saints"})
        group(
            core,
            layer,
            "s05",
            ["w063", "w064", "w065"],
            "w064",
            {"through whose merits and prayers"},
        )
        aid = group(core, layer, "s05", ["w070", "w071", "w072", "w073"], "w072", EN_AID)
        group(core, layer, "s07", ["w077", "w078"], "w077", {"our Lord"})
        # Whose is the saints' antecedent; grant remains the Father's predicate.
        assert caption(core, layer, "s05") == (
            "and | of all Your saints | through whose merits and prayers | grant | that | in | "
            f"all things | {aid['gloss']}"
        )
        assert caption(core, layer, "s01") == (
            "remaining in communion | and | venerating the memory | first of all | "
            "of the glorious | ever | Virgin | Mary | Mother | of God | and | "
            "our Lord | Jesus | Christ"
        )
        assert caption(core, layer, "s02") in {
            "and | also | of blessed | Joseph | Spouse of the same Virgin",
            "and | also | of blessed | Joseph | Spouse of that same Virgin",
        }
        assert caption(core, layer, "s03").startswith(
            "and | of Your blessed apostles and martyrs | Peter | and | Paul |"
        )
    elif ordinary:
        aid = group(core, layer, "s05", ["w070", "w071", "w072", "w073"], "w072", PL_AID)
        assert caption(core, layer, "s05") == (
            "i | wszystkich | świętych | Twoich | których | zasługami | i modlitwami | spraw | "
            f"abyśmy | we | wszystkim | {aid['gloss']}"
        )
        # These formal Polish orders are valid counterexamples, not enforced EN symmetry.
        assert caption(core, layer, "s01").startswith(
            "trwając we wspólnocie | i | pamięć | czcząc | przede | wszystkim |"
        )
        assert caption(core, layer, "s02") == (
            "a | także | błogosławionego | Józefa | tejże | Dziewicy | Oblubieńca"
        )
    elif language == "pl":
        group(core, layer, "s01", ["w003", "w004", "w005"], "w005", {"obchodząc najświętszy dzień"})
        assert caption(core, layer, "s01") == (
            "trwając we wspólnocie | i | obchodząc najświętszy dzień | w którym | Pan | nasz"
        )
        assert caption(core, layer, "s03") == "Jezus | Chrystus | za | nas | został wydany"
        assert caption(core, layer, "s09").endswith("tej samej | Dziewicy | Oblubieńca")
    else:
        # Marked fronted for-us is defensible, and the perfect passive is realized once.
        assert caption(core, layer, "s03") == "Jesus | Christ | for | us | was handed over"
    if not ordinary:
        group(
            core,
            layer,
            "s03",
            ["w013", "w014"],
            "w014",
            {"został wydany"} if language == "pl" else {"was handed over"},
        )
        assert not check_interlinear(core, layer)


@pytest.mark.parametrize("slug", ["communicantes", "communicantes-in-cena-domini"])
@pytest.mark.parametrize("language", ["pl", "en"])
def test_actual_complete_caption_relations(slug, language):
    core, layer = subject(slug, language)
    assert_known_caption(core, layer, language)
    assert not check_interlinear(core, layer)


@pytest.mark.parametrize("language,alternatives", [("pl", PL_AID), ("en", EN_AID)])
def test_legitimate_passive_aid_readings_are_not_preference_failures(language, alternatives):
    core, layer = subject("communicantes", language)
    for value in alternatives:
        alternative = deepcopy(layer)
        aid = next(a for a in alternative["segments"]["s05"]["alignments"] if "w072" in a["words"])
        aid["gloss"] = value
        assert_known_caption(core, alternative, language)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_reverting_complete_group_or_duplicating_a_member_is_rejected(language):
    core, layer = subject("communicantes", language)
    changed = deepcopy(layer)
    aid = next(a for a in changed["segments"]["s05"]["alignments"] if "w072" in a["words"])
    aid["words"] = aid["words"][:-1]
    changed["words"]["w073"]["gloss"] = "pomocą" if language == "pl" else "by the help"
    with pytest.raises(AssertionError):
        assert_known_caption(core, changed, language)
    duplicate = deepcopy(layer)
    duplicate["words"]["w070"]["gloss"] = "opieki" if language == "pl" else "of protection"
    with pytest.raises(AssertionError):
        assert_known_caption(core, duplicate, language)
    assert check_interlinear(core, duplicate)


@pytest.mark.parametrize(
    "value",
    [
        "whose merits and prayers",
        "through the Father's merits and prayers",
        "through whose merits",
    ],
)
def test_intercession_agent_or_coordination_loss_is_rejected(value):
    core, layer = subject("communicantes", "en")
    changed = deepcopy(layer)
    relative = next(a for a in changed["segments"]["s05"]["alignments"] if "w063" in a["words"])
    relative["gloss"] = value
    with pytest.raises(AssertionError):
        assert_known_caption(core, changed, "en")


@pytest.mark.parametrize("language", ["pl", "en"])
def test_passive_subject_father_aid_or_outside_scope_loss_is_rejected(language):
    core, layer = subject("communicantes", language)
    wrong = (
        [
            "byli bronieni pomocą ich opieki",
            "oni bronili pomocą Twojej opieki",
            "byli bronieni Twoją opieką",
        ]
        if language == "pl"
        else [
            "they may be defended by the help of Your protection",
            "we may defend by Your help",
            "we may be defended by Your protection",
        ]
    )
    for value in wrong:
        changed = deepcopy(layer)
        aid = next(a for a in changed["segments"]["s05"]["alignments"] if "w072" in a["words"])
        aid["gloss"] = value
        with pytest.raises(AssertionError):
            assert_known_caption(core, changed, language)
    changed = deepcopy(layer)
    changed["words"]["w067"]["gloss"] = "a" if language == "pl" else "and"
    with pytest.raises(AssertionError):
        assert_known_caption(core, changed, language)

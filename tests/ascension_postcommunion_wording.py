"""Finite current constructions with exact historical expected-side preimages."""

from collections import Counter

POSTCOMMUNION = "proprium.ascensio-domini-postcommunio"


def ids(*numbers):
    return [f"w{number:03d}" for number in numbers]


def group(members, anchor, gloss):
    return {"words": members, "anchor": anchor, "gloss": gloss}


def words(doc):
    return {word["id"]: word for segment in doc["segments"] for word in segment["words"]}


def alignments(lay):
    return [g for segment in lay["segments"].values() for g in segment.get("alignments", [])]


# Current Postcommunion constructions; the historical tables in test_ascensio_domini_audit.py
# remain unchanged.
POSTCOMMUNION_PURPOSE = "we have received to partake of"
POSTCOMMUNION_EFFICACY = "we may obtain through unseen efficacy"
POSTCOMMUNION_FIRST_SENTENCE = (
    "Grant us, we beseech You, almighty and merciful God, that we may obtain the unseen "
    "fruit of what we have received to partake of in visible mysteries."
)
POSTCOMMUNION_HELP = (
    "The prayer contrasts reception in visible mysteries with the unseen effect sought here. "
    "What has been received remains what we ask to attain. "
    "Here “efficacy” means that unseen working."
)


def is_current_postcommunion_subject(row):
    return (row[1], row[2], row[3]) == ("en", POSTCOMMUNION, "w015")


def assert_postcommunion_subject(doc, lay, row):
    assert row == (
        "subject",
        "en",
        POSTCOMMUNION,
        "w015",
        "consequámur",
        "we may obtain",
        "may obtain",
    ), "subject historical caption"
    expected = group(ids(14, 15, 16), "w015", POSTCOMMUNION_EFFICACY)
    touching = [g for g in alignments(lay) if "w015" in g["words"]]
    assert touching == [expected], "subject caption"
    assert all("gloss" not in lay["words"][wid] for wid in expected["words"]), "subject caption"
    morph = words(doc)["w015"]["morph"]
    assert (morph["person"], morph["number"], morph["mood"], morph["voice"]) == (
        1,
        "pl",
        "subj",
        "dep",
    ), "subject Latin context"


def current_regroup_items(row):
    if row[:3] == ("sumenda", "en", POSTCOMMUNION):
        assert row[4] == [("w", "w012", "to be taken"), ("w", "w013", "we have received")], (
            "sumenda historical realization"
        )
        return [("g", ids(12, 13), "w013", POSTCOMMUNION_PURPOSE)]
    return row[4]


def current_verse_phrase(row):
    if row[:3] == ("sumenda", "en", POSTCOMMUNION):
        assert row[3] == "what we have received to be taken under visible mysteries.", (
            "sumenda historical verse"
        )
        return POSTCOMMUNION_FIRST_SENTENCE
    return row[3]


def assert_postcommunion_constructions(doc, lay):
    expected = {
        "pl": [
            group(ids(12, 13), "w013", "otrzymaliśmy do przyjęcia"),
            group(ids(14, 15, 16), "w015", "osiągnęli dzięki niewidzialnemu działaniu"),
        ],
        "en": [
            group(ids(12, 13), "w013", POSTCOMMUNION_PURPOSE),
            group(ids(14, 15, 16), "w015", POSTCOMMUNION_EFFICACY),
        ],
    }[lay["language"]]
    for segment in doc["segments"]:
        identifiers = [word["id"] for word in segment["words"]]
        groups = lay["segments"][segment["id"]].get("alignments", [])
        members = [wid for g in groups for wid in g["words"]]
        members += [wid for wid in identifiers if "gloss" in lay["words"][wid]]
        assert Counter(members) == Counter(identifiers), "postcommunion membership"
    body = set(ids(*range(1, 17)))
    selected = [g for g in alignments(lay) if body & set(g["words"])]
    assert selected == expected, "postcommunion constructions"
    assert all("gloss" not in lay["words"][wid] for g in expected for wid in g["words"]), (
        "postcommunion membership"
    )
    assert lay["words"]["w009"]["gloss"] == {"pl": "to, co", "en": "what"}[lay["language"]], (
        "postcommunion relative object"
    )

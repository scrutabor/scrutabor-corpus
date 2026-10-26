"""Two reviewed Postcommunion caption constructions and their actual predecessors."""

import json
from copy import deepcopy
from pathlib import Path
from typing import TypedDict

import pytest

from checks import interlinear

ROOT = Path(__file__).resolve().parents[1]


class CaptionCase(TypedDict):
    id: str
    text: str
    members: list[str]
    forms: list[str]
    anchor: str
    caption: str
    translation: str
    about: str
    word_details: dict[str, dict[str, str]]
    before_member_details: dict[str, dict[str, str]]


CASES: list[CaptionCase] = [
    {
        "id": "refecti-protection",
        "text": "proprium.refecti-cibo-potuque-postcommunio",
        "members": ["w016", "w017", "w018", "w019"],
        "forms": ["eius", "muniámur", "et", "précibus"],
        "anchor": "w017",
        "caption": "by his prayers we may also be protected",
        "translation": (
            "Refreshed with heavenly food and drink, we humbly beseech You, our God: "
            "may we also be protected by the prayers of the saint we commemorated "
            "when we received these gifts. Through our Lord Jesus Christ, Your Son, "
            "who lives and reigns with You in the unity of the Holy Spirit, God, "
            "forever and ever."
        ),
        "about": (
            "The saint commemorated at the reception of the heavenly gifts is also "
            "the one whose prayers are sought for our protection."
        ),
        "word_details": {
            "w016": {
                "explanation": (
                    "“His” points back to the saint identified by “whose.” The prayer "
                    "seeks protection for us through that saint’s prayers."
                )
            },
            "w017": {},
            "w018": {},
            "w019": {},
        },
        "before_member_details": {
            "w016": {
                "explanation": (
                    "“His” points back to the saint identified by “whose.” The prayer "
                    "seeks protection for us through that saint’s prayers."
                )
            },
            "w017": {},
            "w018": {},
            "w019": {},
        },
    },
    {
        "id": "philip-nourishment",
        "text": "proprium.sancti-philippi-nerii-postcommunio",
        "members": ["w001", "w002", "w003", "w004"],
        "forms": ["Cæléstibus", "Dómine", "pasti", "delíciis"],
        "anchor": "w003",
        "caption": "Nourished with heavenly delights, Lord",
        "translation": (
            "Lord, nourished with heavenly delights, we pray that, through the merits "
            "of blessed Philip, Your confessor, and by imitating him, we may always "
            "long for those same things through which we truly live. Through our Lord "
            "Jesus Christ, Your Son, who lives and reigns with You in the unity of "
            "the Holy Spirit, God, forever and ever."
        ),
        "about": (
            "After receiving heavenly nourishment, the community asks that Philip’s "
            "merits and its imitation of him may help it always to long for the "
            "heavenly things through which it truly lives."
        ),
        "word_details": {
            "w001": {
                "explanation": (
                    "Heavenly qualifies the delights with which the praying community "
                    "has been nourished. The intervening address to the Lord does not "
                    "break that connection."
                )
            },
            "w002": {},
            "w003": {},
            "w004": {},
        },
        "before_member_details": {
            "w001": {
                "gloss": "With heavenly",
                "explanation": (
                    "Heavenly qualifies the delights with which the praying community "
                    "has been nourished. The intervening address to the Lord does not "
                    "break that connection."
                ),
            },
            "w002": {"gloss": "Lord"},
            "w003": {"gloss": "nourished"},
            "w004": {"gloss": "delights"},
        },
    },
]


def inputs(row):
    address = row["text"].replace(".", "/", 1) + ".json"
    doc = json.loads((ROOT / "texts" / address).read_text(encoding="utf-8"))
    lay = json.loads((ROOT / "languages/en/texts" / address).read_text(encoding="utf-8"))
    return doc, lay


def assert_caption(doc, lay, row):
    forms = {w["id"]: w["form"] for s in doc["segments"] for w in s["words"]}
    assert [forms[w] for w in row["members"]] == row["forms"]
    touching = [
        g
        for g in lay["segments"]["s01"].get("alignments", [])
        if set(g["words"]) & set(row["members"])
    ]
    assert touching == [
        {"words": row["members"], "anchor": row["anchor"], "gloss": row["caption"]}
    ], "caption government"
    assert {w: lay["words"][w] for w in row["members"]} == row["word_details"]
    assert lay["segments"]["s01"]["translation"] == row["translation"]
    assert lay["about"] == row["about"]
    if row["id"] == "philip-nourishment":
        assert lay["words"]["w020"]["gloss"] == "we may long for"
    assert interlinear.check(doc, lay) == []


@pytest.mark.parametrize("row", CASES, ids=[r["id"] for r in CASES])
def test_reviewed_caption_and_unchanged_prose(row):
    assert_caption(*inputs(row), row)


@pytest.mark.parametrize("row", CASES, ids=[r["id"] for r in CASES])
def test_actual_predecessor_rejects_and_exact_caption_recovers(row):
    doc, original = inputs(row)
    assert_caption(doc, original, row)
    bad = deepcopy(original)
    groups = bad["segments"]["s01"]["alignments"]
    if row["id"] == "refecti-protection":
        next(g for g in groups if g["words"] == row["members"])["gloss"] = (
            "by his prayers may we also be protected"
        )
    else:
        groups[:] = [g for g in groups if not set(g["words"]) & set(row["members"])]
        for wid, details in row["before_member_details"].items():
            bad["words"][wid] = deepcopy(details)
    with pytest.raises(AssertionError, match="caption government"):
        assert_caption(doc, bad, row)
    assert_caption(doc, original, row)

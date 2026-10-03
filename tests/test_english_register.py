"""A prayer whose English prose is contemporary is contemporary throughout.

Owner decision 2026-09-28 (STYLE-EN): contemporary You/Your in own and working
translations, including prayer conclusions, interlinear glosses and word explanations,
without mixing registers inside one prayer. Texts whose prose still keeps the traditional
register (retained formulas and texts not yet revised) are outside this check.
"""

import json
import re
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARCHAIC = re.compile(
    r"\b(?:thou|thee|thy|thine|thyself|art|hast|hath|doth|dost|saith|didst|wouldst|shouldst|mayst"
    r"|mayest|mightest|canst|wilt|shalt|unto|whence|thence|wherefore|ye)\b|\b[a-z]+(?:eth|est)\b",
    re.I,
)
NOT_ARCHAIC = {
    "rest",
    "test",
    "best",
    "lest",
    "west",
    "east",
    "nest",
    "guest",
    "forest",
    "harvest",
    "manifest",
    "conquest",
    "request",
    "chest",
    "interest",
    "honest",
    "modest",
    "priest",
    "highest",
    "greatest",
    "least",
    "lowest",
    "eldest",
    "first",
    "last",
    "earnest",
    "protest",
    "detest",
    "holiest",
    "mightiest",
    "dearest",
    "purest",
    "truest",
    "nearest",
    "fairest",
    "brightest",
    "humblest",
    "wisest",
    "richest",
    "sweetest",
    "latest",
    "strongest",
    "deepest",
    "smallest",
    "worthiest",
    "gentlest",
    "kindest",
    "loveliest",
    "happiest",
    "shortest",
    "longest",
    "fullest",
    "finest",
    "oldest",
    "youngest",
    "everlasting",
    "nazareth",
    "elizabeth",
    "beth",
    "japheth",
    "seth",
    "behest",
    "bethlehem",
    "gethsemane",
    "breast",
    "tempest",
    "arrest",
    "invest",
    "suggest",
    "digest",
    "contest",
    "attest",
    "quest",
    "crest",
    "zest",
    "vest",
    "jest",
    "pest",
    "unrest",
    "lowliest",
    "feeblest",
    "fiercest",
    "gravest",
    "bitterest",
    "sorest",
    "hardest",
    "lightest",
    "darkest",
    "coldest",
    "tenderest",
}
GLORIA_PATRI_END = "As it was in the beginning, is now, and ever shall be, world without end."
# Saint John's Postcommunion keeps the conclusion of its recorded historical wording basis.
HISTORICAL_CONCLUSION = {"proprium.sancti-ioannis-apostoli-et-evangelistae-postcommunio"}
# "forever and ever" here; two reviewed prayers spell it "for ever and ever" as the Canon does
# (CANON-TERMINOLOGY); one spelling is an open owner question.
ENDINGS = (" forever and ever.", " for ever and ever.")
CONCLUSIONS = {
    "per dominum nostrum iesum christum filium tuum qui tecum vivit et regnat in unitate"
    " spiritus sancti deus": "Through our Lord Jesus Christ, Your Son, who lives and reigns"
    " with You in the unity of the Holy Spirit, God,",
    "per eundem dominum nostrum iesum christum filium tuum qui tecum vivit et regnat in unitate"
    " spiritus sancti deus": "Through the same Jesus Christ, our Lord, Your Son, who lives and"
    " reigns with You in the unity of the Holy Spirit, God,",
}


def archaic(text):
    return [m for m in ARCHAIC.findall(text or "") if m.lower() not in NOT_ARCHAIC]


def stale(text):
    rest = (text or "").replace(GLORIA_PATRI_END, "")
    return bool(archaic(text)) or "Ghost" in text or "world without end" in rest


def strings(value, path=()):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from strings(child, (*path, key))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from strings(child, (*path, i))


def norm(form):
    s = unicodedata.normalize("NFD", form.lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.replace("æ", "ae").replace("œ", "oe").strip(".,;:!?")


def layers():
    for path in sorted((ROOT / "languages/en/texts").glob("*/*.json")):
        yield json.loads(path.read_text())


def contemporary(doc):
    prose = " ".join(s.get("translation") or "" for s in doc["segments"].values())
    return not stale(prose)


def mixed_fields(doc):
    return [(path, value) for path, value in strings(doc) if stale(value)]


CONTEMPORARY = [doc["text"] for doc in layers() if contemporary(doc)]


def test_most_of_the_book_is_contemporary():
    assert len(CONTEMPORARY) > 700


@pytest.mark.parametrize("text", CONTEMPORARY)
def test_contemporary_prose_has_contemporary_word_help(text):
    category, name = text.split(".", 1)
    doc = json.loads((ROOT / "languages/en/texts" / category / f"{name}.json").read_text())
    assert mixed_fields(doc) == []


def test_the_check_sees_a_traditional_gloss_in_a_contemporary_prayer():
    doc = json.loads((ROOT / "languages/en/texts/ordinarium/gloria.json").read_text())
    assert contemporary(doc) and mixed_fields(doc) == []
    word = next(iter(doc["words"]))
    doc["words"][word]["gloss"] = "Thy"
    assert mixed_fields(doc) == [(("words", word, "gloss"), "Thy")]


def test_contemporary_orations_conclude_in_the_same_register():
    seen = 0
    for text in CONTEMPORARY:
        if text in HISTORICAL_CONCLUSION:
            continue
        category, name = text.split(".", 1)
        latin = json.loads((ROOT / "texts" / category / f"{name}.json").read_text())
        en = json.loads((ROOT / "languages/en/texts" / category / f"{name}.json").read_text())
        for seg in latin["segments"]:
            forms = " ".join(norm(w["form"]) for w in seg.get("words", []))
            prose = en["segments"].get(seg["id"], {}).get("translation") or ""
            for incipit, english in CONCLUSIONS.items():
                if forms.endswith(incipit + " per omnia saecula saeculorum"):
                    assert prose.endswith(tuple(english + e for e in ENDINGS)), (text, seg["id"])
                    seen += 1
                elif forms.endswith(incipit):
                    assert prose.endswith(english), (text, seg["id"])
                    seen += 1
    assert seen > 150

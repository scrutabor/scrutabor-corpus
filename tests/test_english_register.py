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

from checks import interlinear

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
# "forever and ever" is the contemporary standard. Keep legacy spacing detectable
# separately while unrevised texts still retain their recorded wording.
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


def test_king_gospel_distinguishes_jesus_and_pilate():
    path = "languages/en/texts/proprium/d-n-iesu-christi-regis-evangelium.json"
    words = json.loads((ROOT / path).read_bytes())["words"]
    assert words["w015"]["gloss"] == "yourself"
    assert words["w021"]["gloss"] == "you"
    # Pilate addresses Christ in these three occurrences.
    assert all(words[wid]["gloss"] == "You" for wid in ("w008", "w035", "w077"))
    # Jesus addresses Pilate, but this word begins a sentence.
    assert words["w080"]["gloss"] == "You"


def test_rosary_secret_conclusion_returns_to_the_son():
    path = "languages/en/texts/proprium/beatae-mariae-virginis-a-rosario-secreta.json"
    prose = json.loads((ROOT / path).read_bytes())["segments"]["s01"]["translation"]
    assert "His promises. He lives and reigns with You" in prose
    assert "His promises, who" not in prose
    assert "You live and reign" not in prose


def test_holy_cross_postcommunion_preserves_its_petition():
    name = "exaltatio-sanctae-crucis-postcommunio"
    core = json.loads((ROOT / f"texts/proprium/{name}.json").read_bytes())
    layer = json.loads((ROOT / f"languages/en/texts/proprium/{name}.json").read_bytes())
    body = core["segments"][0]["words"][:17]
    assert [w["lemma"] for w in body] == [
        "adsum",
        "nos",
        "dominus",
        "deus",
        "noster",
        "et",
        "qui",
        "sanctus",
        "crux",
        "laetor",
        "facio",
        "honor",
        "is",
        "quoque",
        "perpetuus",
        "defendo",
        "subsidium",
    ]
    prose = layer["segments"]["s01"]["translation"]
    assert prose.startswith(
        "Stand by us, O Lord our God, and also defend, with the unceasing aid of the "
        "holy Cross, those whom You make rejoice in its honor. Through our Lord"
    )
    assert "sacrament" not in prose
    assert layer["segments"]["s02"]["translation"] == "Amen."


def conclusion_matches(prose, english, *, duration):
    variants = (english,)
    if english.startswith("Through the same "):
        variants += (english.replace("Through the same ", "Through this same ", 1),)
    endings = ENDINGS if duration else ("",)
    return prose.endswith(tuple(variant + ending for variant in variants for ending in endings))


@pytest.mark.parametrize("determiner", ["the", "this"])
@pytest.mark.parametrize("duration", [False, True])
def test_eundem_keeps_both_contemporary_anaphoric_forms(determiner, duration):
    english = next(value for key, value in CONCLUSIONS.items() if " eundem " in key)
    prose = english.replace("Through the same ", f"Through {determiner} same ", 1)
    if duration:
        prose += " forever and ever."
    assert conclusion_matches(prose, english, duration=duration)


@pytest.mark.parametrize(
    "old,new",
    [
        ("Your Son", "Thy Son"),
        ("our Lord", "Lord"),
        ("who lives", "who will live"),
        ("the same", "another"),
    ],
)
def test_eundem_alternative_does_not_erase_register_or_meaning(old, new):
    english = next(value for key, value in CONCLUSIONS.items() if " eundem " in key)
    assert not conclusion_matches(
        english.replace(old, new) + " forever and ever.", english, duration=True
    )


def test_plain_dominum_does_not_acquire_an_unsupported_same():
    english = next(value for key, value in CONCLUSIONS.items() if " eundem " not in key)
    assert not conclusion_matches(
        english.replace("Through our", "Through this same") + " forever and ever.",
        english,
        duration=True,
    )


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
                    assert conclusion_matches(prose, english, duration=True), (text, seg["id"])
                    seen += 1
                elif forms.endswith(incipit):
                    assert conclusion_matches(prose, english, duration=False), (text, seg["id"])
                    seen += 1
    assert seen > 150


def test_baptist_secret_retains_due_honor_and_identifies_the_son_after_both_actions():
    name = "nativitas-sancti-ioannis-baptistae-secreta"
    core = json.loads((ROOT / f"texts/proprium/{name}.json").read_bytes())
    layer = json.loads((ROOT / f"languages/en/texts/proprium/{name}.json").read_bytes())
    words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    assert [words[w]["lemma"] for w in ["w008", "w009"]] == ["honor", "debeo"]
    prose = layer["segments"]["s01"]["translation"]
    assert "celebrating with due honor the birth of him" in prose
    assert (
        "both foretold the coming of the Savior of the world and made His presence known" in prose
    )
    assert "known: our Lord Jesus Christ, Your Son. He lives and reigns with You" in prose
    assert "You live and reign" not in prose
    # Plural altaria can name one altar; grammar alone must not force a rewrite.
    assert "Your altar with gifts" in prose and words["w004"]["morph"]["number"] == "pl"
    assert layer["segments"]["s02"]["translation"] == "forever and ever."
    assert layer["segments"]["s03"]["translation"] == "Amen."


@pytest.mark.parametrize(
    "segment,members,anchor,gloss",
    [
        ("s01", ["w006", "w007"], "w007", "his birth"),
        ("s01", ["w008", "w009"], "w008", "with due honor"),
        ("s01", ["w021", "w022"], "w021", "our Lord"),
        ("s01", ["w025", "w026"], "w025", "Your Son"),
        ("s01", ["w034", "w035"], "w034", "of the Holy Spirit"),
        ("s02", ["w037", "w038", "w039", "w040"], "w039", "forever and ever"),
    ],
)
def test_baptist_secret_natural_groups_keep_one_complete_realization(
    segment, members, anchor, gloss
):
    name = "nativitas-sancti-ioannis-baptistae-secreta"
    core = json.loads((ROOT / f"texts/proprium/{name}.json").read_bytes())
    layer = json.loads((ROOT / f"languages/en/texts/proprium/{name}.json").read_bytes())
    groups = layer["segments"][segment].get("alignments", [])
    assert {"words": members, "anchor": anchor, "gloss": gloss} in groups
    assert all("gloss" not in layer["words"][wid] for wid in members)
    assert layer["words"]["w001"]["gloss"] == "Your"
    assert layer["words"]["w003"]["gloss"] == "with gifts"
    assert interlinear.check(core, layer) == []


def test_baptist_postcommunion_keeps_its_valid_immediate_christ_relative():
    name = "nativitas-sancti-ioannis-baptistae-postcommunio"
    prose = json.loads((ROOT / f"languages/en/texts/proprium/{name}.json").read_bytes())[
        "segments"
    ]["s01"]["translation"]
    assert "Your Son, our Lord Jesus Christ, who lives and reigns with You" in prose

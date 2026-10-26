"""Short English litany captions preserve the Latin and retained traditional prose."""

import json
from copy import deepcopy
from pathlib import Path
from typing import TypedDict

import pytest

from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs
from checks.translation_provenance import canonical_hash

ROOT = Path(__file__).resolve().parents[1]


class CaptionCase(TypedDict):
    text: str
    segment: str
    words: list[str]
    forms: list[str]
    anchor: str
    caption: str
    predecessor: list[str]


CASES: list[CaptionCase] = [
    {
        "text": "litaniae.lauretanae",
        "segment": "s016",
        "words": ["w042", "w043"],
        "forms": ["Dei", "Génetrix"],
        "anchor": "w043",
        "caption": "Mother of God",
        "predecessor": ["of God", "Mother"],
    },
    {
        "text": "litaniae.lauretanae",
        "segment": "s064",
        "words": ["w166", "w167"],
        "forms": ["nostræ", "lætítiæ"],
        "anchor": "w167",
        "caption": "of our joy",
        "predecessor": ["our", "of gladness"],
    },
    {
        "text": "litaniae.lauretanae",
        "segment": "s116",
        "words": ["w304", "w305"],
        "forms": ["sacratíssimi", "Rosárii"],
        "anchor": "w305",
        "caption": "of the most holy Rosary",
        "predecessor": ["of the Most Holy", "the Rosary"],
    },
    {
        "text": "litaniae.lauretanae",
        "segment": "s130",
        "words": ["w354", "w355"],
        "forms": ["Dei", "Génetrix"],
        "anchor": "w355",
        "caption": "Mother of God",
        "predecessor": ["of God", "Mother"],
    },
    {
        "text": "litaniae.lauretanae",
        "segment": "s133",
        "words": ["w364", "w365"],
        "forms": ["fámulos", "tuos"],
        "anchor": "w364",
        "caption": "Your servants",
        "predecessor": ["servants", "Your"],
    },
    {
        "text": "litaniae.lauretanae",
        "segment": "s133",
        "words": ["w392", "w393"],
        "forms": ["Dóminum", "nostrum"],
        "anchor": "w392",
        "caption": "our Lord",
        "predecessor": ["Lord", "our"],
    },
    {
        "text": "litaniae.lauretanae",
        "segment": "s125",
        "words": ["w331"],
        "forms": ["nobis"],
        "anchor": "w331",
        "caption": "us",
        "predecessor": ["to us"],
    },
    {
        "text": "litaniae.sacratissimi-cordis-iesu",
        "segment": "s018",
        "words": ["w057", "w058"],
        "forms": ["Verbo", "Dei"],
        "anchor": "w057",
        "caption": "to the Word of God",
        "predecessor": ["Word", "of God"],
    },
    {
        "text": "litaniae.sacratissimi-cordis-iesu",
        "segment": "s044",
        "words": ["w164", "w165", "w166"],
        "forms": ["sibi", "bene", "complácuit"],
        "anchor": "w166",
        "caption": "was well pleased",
        "predecessor": ["to Himself", "well", "was well pleased"],
    },
    {
        "text": "litaniae.sacratissimi-cordis-iesu",
        "segment": "s046",
        "words": ["w175", "w176"],
        "forms": ["nos", "accépimus"],
        "anchor": "w176",
        "caption": "we have received",
        "predecessor": ["we", "we have received"],
    },
    {
        "text": "litaniae.sacratissimi-cordis-iesu",
        "segment": "s056",
        "words": ["w216", "w217"],
        "forms": ["peccátis", "nostris"],
        "anchor": "w216",
        "caption": "our sins",
        "predecessor": ["sins", "our"],
    },
    {
        "text": "litaniae.sacratissimi-cordis-iesu",
        "segment": "s060",
        "words": ["w230", "w231"],
        "forms": ["scélera", "nostra"],
        "anchor": "w230",
        "caption": "our offenses",
        "predecessor": ["offenses", "our"],
    },
    {
        "text": "litaniae.sacratissimi-cordis-iesu",
        "segment": "s068",
        "words": ["w258", "w259", "w260", "w261"],
        "forms": ["vita", "et", "resurréctio", "nostra"],
        "anchor": "w258",
        "caption": "our life and resurrection",
        "predecessor": ["life", "and", "resurrection", "our"],
    },
    {
        "text": "litaniae.sacratissimi-cordis-iesu",
        "segment": "s070",
        "words": ["w266", "w267", "w268", "w269"],
        "forms": ["pax", "et", "reconciliátio", "nostra"],
        "anchor": "w266",
        "caption": "our peace and reconciliation",
        "predecessor": ["peace", "and", "reconciliation", "our"],
    },
    {
        "text": "litaniae.sacratissimi-cordis-iesu",
        "segment": "s087",
        "words": ["w333", "w334"],
        "forms": ["cor", "nostrum"],
        "anchor": "w333",
        "caption": "our heart",
        "predecessor": ["heart", "our"],
    },
    {
        "text": "litaniae.sacratissimi-cordis-iesu",
        "segment": "s087",
        "words": ["w336", "w337"],
        "forms": ["Cor", "tuum"],
        "anchor": "w336",
        "caption": "Your Heart",
        "predecessor": ["Heart", "Your"],
    },
    {
        "text": "litaniae.sacratissimi-cordis-iesu",
        "segment": "s081",
        "words": ["w308"],
        "forms": ["nobis"],
        "anchor": "w308",
        "caption": "us",
        "predecessor": ["to us"],
    },
    {
        "text": "litaniae.sanctissimi-nominis-iesu",
        "segment": "s032",
        "words": ["w084", "w085"],
        "forms": ["futúri", "sǽculi"],
        "anchor": "w085",
        "caption": "of the age to come",
        "predecessor": ["to come", "of the age"],
    },
    {
        "text": "litaniae.sanctissimi-nominis-iesu",
        "segment": "s056",
        "words": ["w144", "w145"],
        "forms": ["Deus", "noster"],
        "anchor": "w144",
        "caption": "our God",
        "predecessor": ["God", "our"],
    },
    {
        "text": "litaniae.sanctissimi-nominis-iesu",
        "segment": "s058",
        "words": ["w149", "w150"],
        "forms": ["refúgium", "nostrum"],
        "anchor": "w149",
        "caption": "our refuge",
        "predecessor": ["refuge", "our"],
    },
    {
        "text": "litaniae.sanctissimi-nominis-iesu",
        "segment": "s072",
        "words": ["w184", "w185", "w186", "w187"],
        "forms": ["via", "et", "vita", "nostra"],
        "anchor": "w184",
        "caption": "our way and life",
        "predecessor": ["way", "and", "life", "our"],
    },
    {
        "text": "litaniae.sanctissimi-nominis-iesu",
        "segment": "s098",
        "words": ["w254", "w255"],
        "forms": ["ira", "tua"],
        "anchor": "w254",
        "caption": "Your wrath",
        "predecessor": ["wrath", "Your"],
    },
    {
        "text": "litaniae.sanctissimi-nominis-iesu",
        "segment": "s106",
        "words": ["w279", "w280"],
        "forms": ["inspiratiónum", "tuárum"],
        "anchor": "w279",
        "caption": "of Your inspirations",
        "predecessor": ["of inspirations", "Your"],
    },
    {
        "text": "litaniae.sanctissimi-nominis-iesu",
        "segment": "s108",
        "words": ["w286", "w287", "w288"],
        "forms": ["sanctæ", "Incarnatiónis", "tuæ"],
        "anchor": "w287",
        "caption": "of Your holy Incarnation",
        "predecessor": ["of holy", "of Incarnation", "Your"],
    },
    {
        "text": "litaniae.sanctissimi-nominis-iesu",
        "segment": "s110",
        "words": ["w293", "w294"],
        "forms": ["nativitátem", "tuam"],
        "anchor": "w293",
        "caption": "Your nativity",
        "predecessor": ["nativity", "Your"],
    },
    {
        "text": "litaniae.sanctissimi-nominis-iesu",
        "segment": "s112",
        "words": ["w299", "w300"],
        "forms": ["infántiam", "tuam"],
        "anchor": "w299",
        "caption": "Your infancy",
        "predecessor": ["infancy", "Your"],
    },
    {
        "text": "litaniae.sanctissimi-nominis-iesu",
        "segment": "s114",
        "words": ["w305", "w306", "w307"],
        "forms": ["diviníssimam", "vitam", "tuam"],
        "anchor": "w306",
        "caption": "Your most divine life",
        "predecessor": ["most divine", "life", "Your"],
    },
    {
        "text": "litaniae.sanctissimi-nominis-iesu",
        "segment": "s116",
        "words": ["w312", "w313"],
        "forms": ["labóres", "tuos"],
        "anchor": "w312",
        "caption": "Your labors",
        "predecessor": ["labors", "Your"],
    },
    {
        "text": "litaniae.sanctissimi-nominis-iesu",
        "segment": "s118",
        "words": ["w318", "w319", "w320", "w321"],
        "forms": ["agoníam", "et", "passiónem", "tuam"],
        "anchor": "w318",
        "caption": "Your agony and Passion",
        "predecessor": ["agony", "and", "Passion", "Your"],
    },
    {
        "text": "litaniae.sanctissimi-nominis-iesu",
        "segment": "s120",
        "words": ["w326", "w327", "w328", "w329"],
        "forms": ["crucem", "et", "derelictiónem", "tuam"],
        "anchor": "w326",
        "caption": "Your cross and abandonment",
        "predecessor": ["cross", "and", "dereliction", "Your"],
    },
    {
        "text": "litaniae.sanctissimi-nominis-iesu",
        "segment": "s122",
        "words": ["w334", "w335"],
        "forms": ["languóres", "tuos"],
        "anchor": "w334",
        "caption": "Your sufferings",
        "predecessor": ["sufferings", "Your"],
    },
    {
        "text": "litaniae.sanctissimi-nominis-iesu",
        "segment": "s124",
        "words": ["w340", "w341", "w342", "w343"],
        "forms": ["mortem", "et", "sepultúram", "tuam"],
        "anchor": "w340",
        "caption": "Your death and burial",
        "predecessor": ["death", "and", "burial", "Your"],
    },
    {
        "text": "litaniae.sanctissimi-nominis-iesu",
        "segment": "s126",
        "words": ["w348", "w349"],
        "forms": ["resurrectiónem", "tuam"],
        "anchor": "w348",
        "caption": "Your resurrection",
        "predecessor": ["resurrection", "Your"],
    },
    {
        "text": "litaniae.sanctissimi-nominis-iesu",
        "segment": "s128",
        "words": ["w354", "w355"],
        "forms": ["ascensiónem", "tuam"],
        "anchor": "w354",
        "caption": "Your ascension",
        "predecessor": ["ascension", "Your"],
    },
    {
        "text": "litaniae.sanctissimi-nominis-iesu",
        "segment": "s130",
        "words": ["w360", "w361", "w362", "w363"],
        "forms": ["sanctíssimæ", "Eucharístiæ", "institutiónem", "tuam"],
        "anchor": "w362",
        "caption": "Your institution of the Most Holy Eucharist",
        "predecessor": ["of the Most Holy", "the Eucharist", "institution", "Your"],
    },
    {
        "text": "litaniae.sanctissimi-nominis-iesu",
        "segment": "s132",
        "words": ["w368", "w369"],
        "forms": ["gáudia", "tua"],
        "anchor": "w368",
        "caption": "Your joys",
        "predecessor": ["joys", "Your"],
    },
    {
        "text": "litaniae.sanctissimi-nominis-iesu",
        "segment": "s134",
        "words": ["w374", "w375"],
        "forms": ["glóriam", "tuam"],
        "anchor": "w374",
        "caption": "Your glory",
        "predecessor": ["glory", "Your"],
    },
    {
        "text": "litaniae.sanctissimi-nominis-iesu",
        "segment": "s145",
        "words": ["w432", "w433", "w434", "w435"],
        "forms": ["diviníssimi", "tui", "amóris", "afféctum"],
        "anchor": "w435",
        "caption": "affection of Your most divine love",
        "predecessor": ["of most divine", "Your", "of love", "affection"],
    },
    {
        "text": "litaniae.sanctissimi-nominis-iesu",
        "segment": "s146",
        "words": ["w450", "w451", "w452"],
        "forms": ["Sancti", "Nóminis", "tui"],
        "anchor": "w451",
        "caption": "of Your holy Name",
        "predecessor": ["of the holy", "name", "Your"],
    },
    {
        "text": "litaniae.sanctissimi-nominis-iesu",
        "segment": "s146",
        "words": ["w477", "w478", "w479"],
        "forms": ["in", "sǽcula", "sæculórum"],
        "anchor": "w478",
        "caption": "forever and ever",
        "predecessor": ["for", "ages", "of ages"],
    },
    {
        "text": "litaniae.sanctissimi-nominis-iesu",
        "segment": "s091",
        "words": ["w234"],
        "forms": ["nobis"],
        "anchor": "w234",
        "caption": "us",
        "predecessor": ["to us"],
    },
    {
        "text": "litaniae.sanctissimi-nominis-iesu",
        "segment": "s137",
        "words": ["w386"],
        "forms": ["nobis"],
        "anchor": "w386",
        "caption": "us",
        "predecessor": ["to us"],
    },
]
CASE_IDS = [
    row["text"].split(".", 1)[1] + "-" + row["segment"] + "-" + row["words"][0] for row in CASES
]
TEXTS = [
    "litaniae.lauretanae",
    "litaniae.sacratissimi-cordis-iesu",
    "litaniae.sanctissimi-nominis-iesu",
]
PRESERVED = {
    "litaniae.lauretanae": ("106fa83f916db6c20334eb9287942ca2b478bd436323d4dc17d1b0bbf046ce50"),
    "litaniae.sacratissimi-cordis-iesu": (
        "474b827aad8a4f81dc52248e45606e08d4cced7dbd1cc9fb94c21e835d9fb0d6"
    ),
    "litaniae.sanctissimi-nominis-iesu": (
        "7f6b7b4b67f2cc120e945991a56568d09b6cee0c021698d10faca9f990631f7b"
    ),
}


def read(text, language=None):
    category, slug = text.split(".", 1)
    base = ROOT / ("languages/" + language + "/texts" if language else "texts")
    return json.loads((base / category / (slug + ".json")).read_text(encoding="utf-8"))


def case_documents(row):
    return read(row["text"]), read(row["text"], "en")


def checked_group(layer, row):
    matches = [
        g
        for g in layer["segments"][row["segment"]].get("alignments", [])
        if g["words"] == row["words"]
    ]
    assert len(matches) == 1, "reviewed litany realization"
    return matches[0]


def assert_case(core, layer, row):
    segment = next(s for s in core["segments"] if s["id"] == row["segment"])
    positions = {w["id"]: i for i, w in enumerate(segment["words"])}
    first = positions[row["words"][0]]
    actual_words = segment["words"][first : first + len(row["words"])]
    assert [w["id"] for w in actual_words] == row["words"], "Latin construction"
    assert [w["form"] for w in actual_words] == row["forms"], "Latin construction"
    if len(row["words"]) == 1:
        wid = row["words"][0]
        assert not any(
            wid in g["words"] for g in layer["segments"][row["segment"]].get("alignments", [])
        ), "reviewed litany realization"
        assert layer["words"][wid].get("gloss") == row["caption"], "reviewed litany realization"
    else:
        assert checked_group(layer, row) == {
            "words": row["words"],
            "anchor": row["anchor"],
            "gloss": row["caption"],
        }, "reviewed litany realization"
        assert all("gloss" not in layer["words"][w] for w in row["words"]), (
            "reviewed litany realization"
        )


def assert_generic(core, layer):
    doc, localized = expand_core(core), enrich_layer(core, layer)
    assert interlinear.check(doc, localized) == []
    assert (
        language_packs.check_layer(
            core, layer, ROOT / "languages/en/texts" / (core["id"].replace(".", "/", 1) + ".json")
        )
        == []
    )


def preserved_context(layer):
    """Only caption/gloss changes are excluded, not prose, citations or details."""
    return {
        **layer,
        "segments": {
            sid: {key: value for key, value in segment.items() if key != "alignments"}
            for sid, segment in layer["segments"].items()
        },
        "words": {
            wid: {key: value for key, value in word.items() if key != "gloss"}
            for wid, word in layer["words"].items()
        },
    }


def assert_preserved_context(text, layer):
    assert canonical_hash(preserved_context(layer)) == PRESERVED[text], (
        "retained litany prose and details"
    )


@pytest.mark.parametrize("row", CASES, ids=CASE_IDS)
def test_reviewed_litany_realization_matches_the_latin(row):
    core, layer = case_documents(row)
    snapshot = canonical_hash((core, layer))
    assert_case(core, layer, row)
    assert_generic(core, layer)
    assert canonical_hash((core, layer)) == snapshot


@pytest.mark.parametrize("row", CASES, ids=CASE_IDS)
def test_predecessor_realization_is_rejected_then_same_object_recovers(row):
    core, layer = case_documents(row)
    saved_core, saved_layer = deepcopy(core), deepcopy(layer)
    assert_case(core, layer, row)
    assert_generic(core, layer)
    if len(row["words"]) > 1:
        groups = layer["segments"][row["segment"]]["alignments"]
        groups.remove(checked_group(layer, row))
        if not groups:
            del layer["segments"][row["segment"]]["alignments"]
    for wid, caption in zip(row["words"], row["predecessor"], strict=True):
        layer["words"][wid]["gloss"] = caption
    assert canonical_hash((core, layer)) != canonical_hash((saved_core, saved_layer))
    # The predecessor is structurally complete; the reviewed language assertion rejects it.
    assert_generic(core, layer)
    with pytest.raises(AssertionError, match="reviewed litany realization"):
        assert_case(core, layer, row)
    core.clear()
    core.update(saved_core)
    layer.clear()
    layer.update(saved_layer)
    assert_case(core, layer, row)
    assert_generic(core, layer)
    assert canonical_hash((core, layer)) == canonical_hash((saved_core, saved_layer))


STRUCTURAL_CASES = [next(row for row in CASES if row["text"] == text) for text in TEXTS]
STRUCTURAL_DAMAGE = [
    ("duplicate-direct", "expected exactly one direct gloss or alignment"),
    ("outside-anchor", "anchor must name the source word carrying the gloss"),
    ("outside-word", "alignment names a word outside this segment"),
]


STRUCTURAL_PARAMETERS = [
    (row, damage, message) for row in STRUCTURAL_CASES for damage, message in STRUCTURAL_DAMAGE
]


@pytest.mark.parametrize(
    "row,damage,message",
    STRUCTURAL_PARAMETERS,
    ids=[row["text"] + "-" + damage for row, damage, _ in STRUCTURAL_PARAMETERS],
)
def test_real_interlinear_guard_rejects_damage_and_restores(row, damage, message):
    core, layer = case_documents(row)
    saved = deepcopy(layer)
    assert_generic(core, layer)
    group = checked_group(layer, row)
    if damage == "duplicate-direct":
        layer["words"][row["words"][0]]["gloss"] = "duplicate"
    elif damage == "outside-anchor":
        group["anchor"] = "w999"
    else:
        group["words"][1] = "w999"
    assert canonical_hash(layer) != canonical_hash(saved)
    errors = interlinear.check(expand_core(core), enrich_layer(core, layer))
    assert any(message in error and core["id"] in error for error in errors), errors
    layer.clear()
    layer.update(saved)
    assert_case(core, layer, row)
    assert_generic(core, layer)
    assert canonical_hash(layer) == canonical_hash(saved)


@pytest.mark.parametrize("text", TEXTS)
def test_all_retained_litany_prose_about_citations_and_details_stay_exact(text):
    assert_preserved_context(text, read(text, "en"))


@pytest.mark.parametrize("text", TEXTS)
def test_unrelated_continuous_change_is_rejected_then_same_object_recovers(text):
    layer = read(text, "en")
    saved = deepcopy(layer)
    assert_preserved_context(text, layer)
    layer["segments"]["s001"]["translation"] += " Changed."
    assert canonical_hash(layer) != canonical_hash(saved)
    with pytest.raises(AssertionError, match="retained litany prose and details"):
        assert_preserved_context(text, layer)
    layer.clear()
    layer.update(saved)
    assert_preserved_context(text, layer)
    assert canonical_hash(layer) == canonical_hash(saved)

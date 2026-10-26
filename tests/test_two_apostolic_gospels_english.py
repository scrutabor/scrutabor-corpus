"""Complete contemporary English of two apostolic Gospel readings.

Latin, human/divine addressees, source identity and unsettled working provenance
remain distinct. Local copy mutations must reject, then recover the same copy.
"""

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, NamedTuple

import pytest

from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs
from checks.english import check as check_english

ROOT = Path(__file__).resolve().parents[1]
P = "proprium."
NAMES = ("sancti-iacobi-apostoli-evangelium", "sancti-petri-et-pauli-apostolorum-evangelium")

PROSE = {
    "sancti-iacobi-apostoli-evangelium": (
        "At that time, the mother of the sons of Zebedee approached Jesus "
        "with her sons, worshiping Him and asking something of Him. He said "
        "to her, “What do you want?” She said to Him, “Say that these two "
        "sons of mine may sit, one at Your right hand and the other at Your "
        "left, in Your kingdom.” Jesus answered, “You do not know what you "
        "are asking. Can you drink the chalice that I am to drink?” They said "
        "to Him, “We can.” He said to them, “You will indeed drink My "
        "chalice; but to sit at My right or left hand is not Mine to give "
        "you, but it is for those for whom it has been prepared by My "
        "Father.”"
    ),
    "sancti-petri-et-pauli-apostolorum-evangelium": (
        "At that time, Jesus came to the district of Caesarea Philippi and "
        "asked His disciples, “Who do people say the Son of Man is?” They "
        "replied, “Some say John the Baptist, others Elijah, and others "
        "Jeremiah or one of the prophets.” Jesus said to them, “But who do "
        "you say I am?” Simon Peter answered, “You are the Christ, the Son of "
        "the living God.” Jesus answered him, “Blessed are you, Simon son of "
        "Jonah, for flesh and blood has not revealed this to you, but My "
        "Father who is in heaven. And I tell you: you are Peter, and on this "
        "rock I will build My Church, and the gates of hell will not prevail "
        "against it. And I will give you the keys of the kingdom of heaven. "
        "And whatever you bind on earth will also be bound in heaven, and "
        "whatever you loose on earth will also be loosed in heaven.”"
    ),
}
LATIN = {
    "sancti-iacobi-apostoli-evangelium": (
        "In illo témpore: Accéssit ad Iesum mater filiórum Zebedǽi cum fíliis "
        "suis, adórans, et petens áliquid ab eo. Qui dixit ei: Quid vis? Ait "
        "illi: Dic ut sédeant hi duo fílii mei, unus ad déxteram tuam, et "
        "unus ad sinístram in regno tuo. Respóndens autem Iesus, dixit: "
        "Nescítis quid petátis. Potéstis bíbere cálicem, quem ego bibitúrus "
        "sum? Dicunt ei: Póssumus. Ait illis: Cálicem quidem meum bibétis: "
        "sedére autem ad déxteram meam, vel sinístram, non est meum dare "
        "vobis, sed quibus parátum est a Patre meo."
    ),
    "sancti-petri-et-pauli-apostolorum-evangelium": (
        "In illo témpore: Venit Iesus in partes Cæsaréæ Philíppi, et "
        "interrogábat discípulos suos, dicens: Quem dicunt hómines esse "
        "Fílium hóminis? At illi dixérunt: Álii Ioánnem Baptístam, álii autem "
        "Elíam, álii vero Ieremíam, aut unum ex prophétis. Dicit illis Iesus: "
        "Vos autem quem me esse dícitis? Respóndens Simon Petrus, dixit: Tu "
        "es Christus Fílius Dei vivi. Respóndens autem Iesus, dixit ei: "
        "Beátus es, Simon Bar Iona: quia caro et sanguis non revelávit tibi, "
        "sed Pater meus, qui in cælis est. Et ego dico tibi, quia tu es "
        "Petrus, et super hanc petram ædificábo Ecclésiam meam, et portæ "
        "ínferi non prævalébunt advérsus eam. Et tibi dabo claves regni "
        "cælórum. Et quodcúmque ligáveris super terram, erit ligátum et in "
        "cælis: et quodcúmque sólveris super terram, erit solútum et in "
        "cælis."
    ),
}


class GroupCase(NamedTuple):
    key: str
    name: str
    words: tuple[str, ...]
    anchor: str
    gloss: str
    latin: tuple[str, ...]


GROUP_CASES: tuple[GroupCase, ...] = (
    GroupCase(
        "james-w011-w012",
        "sancti-iacobi-apostoli-evangelium",
        ("w011", "w012"),
        "w011",
        "her sons",
        ("fíliis", "suis"),
    ),
    GroupCase(
        "james-w031-w032",
        "sancti-iacobi-apostoli-evangelium",
        ("w031", "w032"),
        "w031",
        "my sons",
        ("fílii", "mei"),
    ),
    GroupCase(
        "james-w035-w036",
        "sancti-iacobi-apostoli-evangelium",
        ("w035", "w036"),
        "w035",
        "Your right hand",
        ("déxteram", "tuam"),
    ),
    GroupCase(
        "james-w042-w043",
        "sancti-iacobi-apostoli-evangelium",
        ("w042", "w043"),
        "w042",
        "Your kingdom",
        ("regno", "tuo"),
    ),
    GroupCase(
        "james-w044-w045",
        "sancti-iacobi-apostoli-evangelium",
        ("w044", "w045"),
        "w044",
        "But answering",
        ("Respóndens", "autem"),
    ),
    GroupCase(
        "james-w056-w057",
        "sancti-iacobi-apostoli-evangelium",
        ("w056", "w057"),
        "w056",
        "am to drink",
        ("bibitúrus", "sum"),
    ),
    GroupCase(
        "james-w063-w064-w065",
        "sancti-iacobi-apostoli-evangelium",
        ("w063", "w064", "w065"),
        "w063",
        "My chalice indeed",
        ("Cálicem", "quidem", "meum"),
    ),
    GroupCase(
        "james-w067-w068",
        "sancti-iacobi-apostoli-evangelium",
        ("w067", "w068"),
        "w067",
        "but to sit",
        ("sedére", "autem"),
    ),
    GroupCase(
        "james-w070-w071",
        "sancti-iacobi-apostoli-evangelium",
        ("w070", "w071"),
        "w070",
        "My right hand",
        ("déxteram", "meam"),
    ),
    GroupCase(
        "james-w074-w075",
        "sancti-iacobi-apostoli-evangelium",
        ("w074", "w075"),
        "w075",
        "that is not",
        ("non", "est"),
    ),
    GroupCase(
        "james-w081-w082",
        "sancti-iacobi-apostoli-evangelium",
        ("w081", "w082"),
        "w081",
        "is prepared",
        ("parátum", "est"),
    ),
    GroupCase(
        "james-w084-w085",
        "sancti-iacobi-apostoli-evangelium",
        ("w084", "w085"),
        "w084",
        "My Father",
        ("Patre", "meo"),
    ),
    GroupCase(
        "peter-w012-w013",
        "sancti-petri-et-pauli-apostolorum-evangelium",
        ("w012", "w013"),
        "w012",
        "His disciples",
        ("discípulos", "suos"),
    ),
    GroupCase(
        "peter-w042-w045",
        "sancti-petri-et-pauli-apostolorum-evangelium",
        ("w042", "w043", "w044", "w045"),
        "w045",
        "who do you say I am",
        ("quem", "me", "esse", "dícitis"),
    ),
    GroupCase(
        "peter-w054-w055",
        "sancti-petri-et-pauli-apostolorum-evangelium",
        ("w054", "w055"),
        "w054",
        "of the living God",
        ("Dei", "vivi"),
    ),
    GroupCase(
        "peter-w056-w057",
        "sancti-petri-et-pauli-apostolorum-evangelium",
        ("w056", "w057"),
        "w056",
        "And answering",
        ("Respóndens", "autem"),
    ),
    GroupCase(
        "peter-w061-w062",
        "sancti-petri-et-pauli-apostolorum-evangelium",
        ("w061", "w062"),
        "w061",
        "Blessed are you",
        ("Beátus", "es"),
    ),
    GroupCase(
        "peter-w070-w071",
        "sancti-petri-et-pauli-apostolorum-evangelium",
        ("w070", "w071"),
        "w071",
        "has not revealed",
        ("non", "revelávit"),
    ),
    GroupCase(
        "peter-w074-w075",
        "sancti-petri-et-pauli-apostolorum-evangelium",
        ("w074", "w075"),
        "w074",
        "My Father",
        ("Pater", "meus"),
    ),
    GroupCase(
        "peter-w093-w094",
        "sancti-petri-et-pauli-apostolorum-evangelium",
        ("w093", "w094"),
        "w093",
        "My Church",
        ("Ecclésiam", "meam"),
    ),
    GroupCase(
        "peter-w098-w099",
        "sancti-petri-et-pauli-apostolorum-evangelium",
        ("w098", "w099"),
        "w099",
        "will not prevail",
        ("non", "prævalébunt"),
    ),
    GroupCase(
        "peter-w113-w114",
        "sancti-petri-et-pauli-apostolorum-evangelium",
        ("w113", "w114"),
        "w113",
        "will be bound",
        ("erit", "ligátum"),
    ),
    GroupCase(
        "peter-w123-w124",
        "sancti-petri-et-pauli-apostolorum-evangelium",
        ("w123", "w124"),
        "w123",
        "will be loosed",
        ("erit", "solútum"),
    ),
)

SOURCE_HASHES = {
    "sancti-iacobi-apostoli-evangelium": (
        "e16993440a2cb2dca82b0a358de929d91ba3fbdd85f961aea922ab3149f9a095"
    ),
    "sancti-petri-et-pauli-apostolorum-evangelium": (
        "378ae82fe82af8e081e061c3e9a90fb4ad02417874fab9f84ebb76db7e5522d3"
    ),
}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def load(name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    core = json.loads((ROOT / f"texts/proprium/{name}.json").read_text())
    layer = json.loads((ROOT / f"languages/en/texts/proprium/{name}.json").read_text())
    return core, layer


def expected_groups(name: str) -> list[dict[str, Any]]:
    return [
        {"words": list(c.words), "anchor": c.anchor, "gloss": c.gloss}
        for c in GROUP_CASES
        if c.name == name
    ]


def verify(name: str, core: dict[str, Any], layer: dict[str, Any]) -> None:
    assert core["id"] == layer["text"] == P + name, "identity"
    assert [s["id"] for s in core["segments"]] == ["s01"], "source"
    words = core["segments"][0]["words"]
    assert " ".join(w["form"] + w.get("post", "") for w in words) == LATIN[name], "source"
    assert set(layer["words"]) == {w["id"] for w in words}, "coverage"
    assert layer["segments"]["s01"]["translation"] == PROSE[name], "prose"
    assert layer["segments"]["s01"]["alignments"] == expected_groups(name), "groups"
    members = [wid for g in expected_groups(name) for wid in g["words"]]
    assert len(members) == len(set(members)), "groups"
    for wid, entry in layer["words"].items():
        if wid in members:
            assert "gloss" not in entry, "members"
        else:
            assert isinstance(entry.get("gloss"), str) and entry["gloss"].strip(), "coverage"
    direct = {"w004": "came", "w019": "He"} if name == NAMES[0] else {"w046": "Answering"}
    for wid, expected in direct.items():
        assert layer["words"][wid]["gloss"] == expected, "caption"
    if name == NAMES[0]:
        assert layer["words"]["w006"]["gloss"] == "Jesus", "referent"
        assert layer["words"]["w048"]["gloss"] == "You do not know", "register"
        assert layer["words"]["w083"]["gloss"] == "by", "agent"
    else:
        for wid, expected in {
            "w015": "Who",
            "w029": "Elijah",
            "w040": "You",
            "w108": "And",
        }.items():
            assert layer["words"][wid]["gloss"] == expected, "register"
    assert layer["about"] == (
        "The Gospel reading of the formulary “Saint James the Apostle” in the 1962 Roman Missal."
        if name == NAMES[0]
        else "The Gospel reading of the formulary “Saints Peter and Paul, Apostles” "
        "in the 1962 Roman Missal."
    ), "about"


@pytest.mark.parametrize("name", NAMES, ids=("james", "peter-paul"))
def test_complete_gospel_english_and_product_checks(name: str) -> None:
    core, layer = load(name)
    verify(name, core, layer)
    doc, enriched = expand_core(core), enrich_layer(core, layer)
    assert interlinear.check(doc, enriched) == []
    assert check_english(doc, enriched) == []
    assert language_packs.check_core(core) == []
    assert (
        language_packs.check_layer(core, layer, ROOT / f"languages/en/texts/proprium/{name}.json")
        == []
    )


@pytest.mark.parametrize("case", GROUP_CASES, ids=[c.key for c in GROUP_CASES])
def test_small_groups_keep_exact_latin_and_one_realization(case: GroupCase) -> None:
    core, layer = load(case.name)
    words = {w["id"]: w for w in core["segments"][0]["words"]}
    assert tuple(words[w]["form"] for w in case.words) == case.latin
    ids = list(words)
    start = ids.index(case.words[0])
    assert ids[start : start + len(case.words)] == list(case.words)
    group = {"words": list(case.words), "anchor": case.anchor, "gloss": case.gloss}
    assert group in layer["segments"]["s01"]["alignments"]
    assert all("gloss" not in layer["words"][wid] for wid in case.words)
    assert len(case.words) <= (4 if case.key == "peter-w042-w045" else 3)


DAMAGES = (
    "opening-Jesus",
    "mother-sons",
    "father-agent",
    "prepared-tense",
    "human-you",
    "Elijah",
    "future",
    "blessed-subject",
    "earth-heaven",
    "anchor",
    "member",
    "duplicate",
    "direct-member",
    "kingdom-scope",
    "james-capital",
    "james-relative",
    "james-response",
    "james-infinitive",
    "peter-participle",
    "peter-response",
    "peter-question",
)


def damage_layer(damage: str, layer: dict[str, Any]) -> str:
    seg = layer["segments"]["s01"]
    groups = seg["alignments"]
    direct = {
        "james-capital": ("w004", "Came"),
        "james-relative": ("w019", "Who"),
        "peter-participle": ("w046", "answered"),
    }
    if damage in direct:
        wid, value = direct[damage]
        layer["words"][wid]["gloss"] = value
        return "caption"
    local = {
        "james-response": ("w044", "answering but"),
        "james-infinitive": ("w067", "to sit but"),
        "peter-response": ("w056", "answering And"),
        "peter-question": ("w042", "who do you say Me am"),
    }
    if damage in local:
        wid, value = local[damage]
        next(g for g in groups if wid in g["words"])["gloss"] = value
        return "groups"
    if damage == "opening-Jesus":
        seg["translation"] = seg["translation"].replace("approached Jesus", "approached him", 1)
        return "prose"
    if damage == "earth-heaven":
        seg["translation"] = seg["translation"].replace("bind on earth", "bind in heaven", 1)
        return "prose"
    if damage in {"father-agent", "Elijah"}:
        wid, value = ("w083", "from") if damage == "father-agent" else ("w029", "Elias")
        layer["words"][wid]["gloss"] = value
        return "agent" if damage == "father-agent" else "register"
    positions = {
        "mother-sons": ("w011", "His sons"),
        "prepared-tense": ("w081", "will be prepared"),
        "human-you": ("w061", "Blessed are You"),
        "future": ("w098", "shall not prevail"),
        "blessed-subject": ("w061", "Blessed are"),
    }
    if damage in positions:
        wid, value = positions[damage]
        next(g for g in groups if wid in g["words"])["gloss"] = value
    elif damage == "anchor":
        groups[0]["anchor"] = groups[0]["words"][1]
    elif damage == "member":
        groups[0]["words"].pop()
    elif damage == "duplicate":
        groups.append(deepcopy(groups[0]))
    elif damage == "direct-member":
        layer["words"][groups[0]["words"][0]]["gloss"] = "duplicate"
        return "members"
    elif damage == "kingdom-scope":
        next(g for g in groups if "w043" in g["words"])["words"] = ["w041", "w042"]
    else:
        raise ValueError(damage)
    return "groups"


@pytest.mark.parametrize("damage", DAMAGES)
def test_real_caption_or_prose_damage_rejects_and_same_copy_recovers(damage: str) -> None:
    peter = {
        "human-you",
        "Elijah",
        "future",
        "blessed-subject",
        "earth-heaven",
        "peter-participle",
        "peter-response",
        "peter-question",
    }
    name = NAMES[1] if damage in peter else NAMES[0]
    core, bad = load(name)
    saved = deepcopy(bad)
    verify(name, core, bad)
    try:
        expected = damage_layer(damage, bad)
        assert canonical(bad) != canonical(saved), "mutation must be real"
        with pytest.raises(AssertionError, match=expected):
            verify(name, core, bad)
    finally:
        bad.clear()
        bad.update(deepcopy(saved))
        assert canonical(bad) == canonical(saved)
        verify(name, core, bad)


def provenance_row(name: str) -> dict[str, Any]:
    data = json.loads((ROOT / "languages/en/translation-provenance.json").read_text())
    matches = [r for r in data["sites"] if r["site"] == P + name + ".s01.en"]
    assert len(matches) == 1
    return matches[0]


def verify_provenance(name: str, layer: dict[str, Any], row: dict[str, Any]) -> None:
    target = json.dumps(
        layer["segments"]["s01"]["translation"], ensure_ascii=False, separators=(",", ":")
    ).encode()
    expected = {
        "site": P + name + ".s01.en",
        "text": P + name,
        "segment": "s01",
        "language": "en",
        "familiar_core": False,
        "origin": "working-unsettled",
        "review": "working",
        "source_sha256": SOURCE_HASHES[name],
        "target_sha256": hashlib.sha256(target).hexdigest(),
    }
    assert canonical(row) == canonical(expected), "provenance"


@pytest.mark.parametrize("name", NAMES, ids=("james", "peter-paul"))
def test_target_digest_does_not_promote_origin_review_or_source(name: str) -> None:
    _, layer = load(name)
    verify_provenance(name, layer, provenance_row(name))


@pytest.mark.parametrize("name", NAMES, ids=("james", "peter-paul"))
@pytest.mark.parametrize("damage", ("target", "source", "origin", "review", "familiar"))
def test_provenance_damage_rejects_and_same_copy_recovers(name: str, damage: str) -> None:
    _, layer = load(name)
    bad = provenance_row(name)
    saved = deepcopy(bad)
    verify_provenance(name, layer, bad)
    field, value = {
        "target": ("target_sha256", "0" * 64),
        "source": ("source_sha256", "0" * 64),
        "origin": ("origin", "own"),
        "review": ("review", "accepted"),
        "familiar": ("familiar_core", True),
    }[damage]
    try:
        bad[field] = value
        assert canonical(bad) != canonical(saved), "mutation must be real"
        with pytest.raises(AssertionError, match="provenance"):
            verify_provenance(name, layer, bad)
    finally:
        bad.clear()
        bad.update(deepcopy(saved))
        assert canonical(bad) == canonical(saved)
        verify_provenance(name, layer, bad)


def test_revised_complete_prose_is_not_a_legacy_allowance() -> None:
    payload = json.loads((ROOT / "tests/fixtures/english-register-legacy.json").read_text())
    assert not {r["text"] for r in payload["records"]} & {P + n for n in NAMES}

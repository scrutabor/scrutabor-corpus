"""Literal regressions preserve complete, nonduplicated construction readings."""

import json

import pytest

from checks.layout import CORPUS

PASSION = "proprium/dominica-ii-passionis-evangelium"
GROUPS = (
    ("pl", "ordinarium/evangelium-ultimum", "s08", "w042 w043 w044", "w042", "nic nie powstało"),
    (
        "pl",
        "proprium/dominica-i-in-quadragesima-epistola",
        "s01",
        "w136 w137",
        "w137",
        "niemający nic",
    ),
    ("pl", PASSION, "s26", "w440 w441", "w441", "Nic nie odpowiadasz"),
    ("pl", PASSION, "s51", "w739 w740 w741", "w741", "Odbywszy zaś naradę"),
    ("pl", PASSION, "s55", "w823 w824", "w824", "nic nie odpowiedział"),
    ("pl", PASSION, "s73", "w974 w975", "w975", "nic nie osiągał"),
    (
        "pl",
        "proprium/dominica-iii-post-pentecosten-collecta",
        "s01",
        "w008 w009",
        "w009",
        "nic nie jest",
    ),
    (
        "pl",
        "proprium/dominica-iv-adventus-epistola",
        "s04",
        "w042 w043",
        "w043",
        "nie jestem świadom",
    ),
    (
        "pl",
        "proprium/nativitas-domini-in-die-evangelium",
        "s01",
        "w028 w029 w030",
        "w028",
        "nic nie powstało",
    ),
    ("en", "orationes/te-deum", "s26", "w166 w167", "w166", "this day"),
    ("en", PASSION, "s41", "w572 w573 w574", "w572", "But as he went out"),
    ("en", PASSION, "s48", "w707 w708 w709", "w707", "What is that to us?"),
    ("en", PASSION, "s49", "w721 w722", "w722", "he hanged himself"),
    ("en", PASSION, "s50", "w729 w730", "w730", "it is not lawful"),
    ("en", PASSION, "s50", "w731 w732", "w732", "to put them"),
    ("en", PASSION, "s50", "w736 w737 w738", "w738", "it is the price of blood"),
    ("en", PASSION, "s51", "w739 w740 w741", "w741", "Now after taking counsel"),
    ("en", PASSION, "s51", "w754 w755", "w754", "that field"),
    ("en", PASSION, "s51", "w761 w762", "w762", "up to"),
    ("en", PASSION, "s52", "w806 w807", "w807", "Are You"),
    ("en", PASSION, "s56", "w829 w830", "w830", "Do You not hear"),
    (
        "en",
        PASSION,
        "s56",
        "w831 w832 w833 w834 w835",
        "w834",
        "how much testimony they give against You",
    ),
    ("en", PASSION, "s57", "w837 w838", "w838", "He did not answer"),
    ("en", PASSION, "s57", "w848 w849 w850 w851", "w849", "Now during the feast day"),
    ("en", PASSION, "s57", "w868 w869 w870", "w868", "So when they had gathered"),
    ("en", PASSION, "s59", "w883 w884", "w883", "For he knew"),
    ("en", PASSION, "s59", "w890 w891 w892", "w890", "Now while he was sitting"),
    ("en", PASSION, "s59", "w898 w899", "w898", "his wife"),
    (
        "en",
        "proprium/sancti-matthaei-apostoli-et-evangelistae-evangelium",
        "s01",
        "w025 w026",
        "w025",
        "as He was at table",
    ),
    (
        "en",
        "proprium/transfiguratio-domini-evangelium",
        "s01",
        "w132 w133",
        "w132",
        "as they were descending",
    ),
)
DIRECT = (
    ("pl", PASSION, "w817", "był oskarżany"),
    ("pl", PASSION, "w834", "składają"),
    ("pl", PASSION, "w840", "na"),
    ("pl", PASSION, "w841", "żadne"),
    ("pl", PASSION, "w842", "słowo"),
    ("pl", PASSION, "w864", "znanego"),
    ("pl", PASSION, "w882", "Chrystusem"),
    ("pl", "proprium/dominica-i-passionis-evangelium", "w146", "niczym"),
    ("pl", "proprium/dominica-in-quinquagesima-epistola", "w069", "nie pomaga"),
    ("pl", "proprium/dominica-in-quinquagesima-evangelium", "w046", "nie zrozumieli"),
    ("pl", "proprium/dominica-in-sexagesima-epistola", "w297", "nie będę się chlubił"),
    ("pl", "proprium/dominica-infra-octavam-nativitatis-epistola", "w008", "nie różni się"),
    ("pl", "proprium/dominica-xviii-post-pentecosten-epistola", "w045", "nie brakuje"),
    ("pl", "proprium/omnium-sanctorum-graduale", "w007", "nic"),
    ("pl", "proprium/omnium-sanctorum-graduale", "w008", "nie brakuje"),
    ("pl", "proprium/dominica-iii-post-pentecosten-collecta", "w011", "nic"),
    ("pl", "proprium/dominica-iii-post-pentecosten-collecta", "w012", "święte"),
    ("en", PASSION, "w742", "they bought"),
    ("en", PASSION, "w790", "the field"),
    ("en", PASSION, "w791", "of the potter"),
    ("en", PASSION, "w824", "He answered"),
    ("en", PASSION, "w875", "me to release"),
    ("en", PASSION, "w893", "on"),
    ("en", PASSION, "w894", "the judgment seat"),
)


def layer(language, text):
    return json.loads((CORPUS / "languages" / language / "texts" / (text + ".json")).read_text())


@pytest.mark.parametrize("language,text,sid,words,anchor,gloss", GROUPS)
def test_whole_construction_realization(language, text, sid, words, anchor, gloss):
    value = layer(language, text)
    ids = words.split()
    actual = [g for g in value["segments"][sid].get("alignments", []) if set(ids) & set(g["words"])]
    assert actual == [{"words": ids, "anchor": anchor, "gloss": gloss}]
    assert all("gloss" not in value["words"][wid] for wid in ids)


@pytest.mark.parametrize("language,text,wid,gloss", DIRECT)
def test_direct_realization_and_valid_retained_ellipsis(language, text, wid, gloss):
    value = layer(language, text)
    assert value["words"][wid]["gloss"] == gloss
    assert not any(
        wid in g["words"] for s in value["segments"].values() for g in s.get("alignments", [])
    )

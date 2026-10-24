"""Preserve the Te Deum's prospective assumption and bounded reading help."""

import hashlib
import json
from pathlib import Path

import pytest

from checks.interlinear import check as check_interlinear
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
TEXT = "orationes/te-deum.json"
CLAUSE = {f"w{i:03}" for i in range(84, 93)}
PROTECTED = {
    "pl": "bf7b5106e488f51731d4e6924af060b8eb0fccca4f77fd5c3c2ac3a3b36c6496",
    "en": "a4a3d21b2ddbf0e8c12dfcdb7445a79b6c044bc0754e6807582da52b5cecd03d",
}


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def core():
    return read("texts/" + TEXT)


def layer(language):
    return read(f"languages/{language}/texts/" + TEXT)


def digest(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def tokens(document):
    return {w["id"]: w for s in document["segments"] for w in s.get("words", [])}


def test_liberandum_is_the_selected_gerund_not_an_agreeing_modifier():
    words = tokens(core())
    assert words["w085"]["head"] == "w086"
    assert words["w086"]["morph"] == {
        "pos": "verb",
        "number": "sg",
        "case": "acc",
        "gender": "n",
        "tense": "pres",
        "mood": "ger",
        "voice": "act",
        "conj": 1,
    }
    assert not {"head", "substantive", "ellipsis"} & words["w086"].keys()
    assert words["w087"]["head"] == "w084"
    assert words["w087"]["morph"] == {
        "pos": "verb",
        "number": "sg",
        "case": "nom",
        "gender": "m",
        "tense": "fut",
        "mood": "part",
        "voice": "act",
        "conj": 3,
    }


@pytest.mark.parametrize(
    "language,sid,members,anchor,gloss",
    [
        (
            "pl",
            "s13",
            ["w085", "w086", "w087", "w088"],
            "w087",
            "mając przyjąć człowieczeństwo dla wyzwolenia",
        ),
        (
            "en",
            "s13",
            ["w085", "w086", "w087", "w088"],
            "w087",
            "intending to assume human nature for deliverance",
        ),
        ("pl", "s14", ["w091", "w092"], "w092", "przed łonem Dziewicy"),
        ("en", "s14", ["w089", "w090"], "w090", "did not shrink from"),
        pytest.param(
            "pl",
            "s24",
            ["w149", "w150", "w151"],
            "w151",
            "Każdego dnia",
            id="pl-daily-distribution",
        ),
        pytest.param(
            "pl",
            "s18",
            ["w109", "w110", "w111", "w112"],
            "w110",
            "Wierzymy, że przyjdziesz jako Sędzia",
            id="pl-judge-role",
        ),
        pytest.param(
            "pl",
            "s21",
            ["w123", "w124", "w125", "w126", "w127", "w128", "w129", "w130"],
            "w124",
            "Spraw, byśmy w wiecznej chwale zostali zaliczeni do grona Twoich świętych",
            id="pl-eternal-glory",
        ),
        pytest.param(
            "pl",
            "s27",
            ["w185", "w186"],
            "w186",
            "Tobie",
            id="pl-trust-government",
        ),
    ],
)
def test_complete_prospective_predicate_and_governed_expression(
    language, sid, members, anchor, gloss
):
    value = layer(language)
    actual = [
        group
        for group in value["segments"][sid].get("alignments", [])
        if set(group["words"]) & set(members)
    ]
    assert actual == [{"words": members, "anchor": anchor, "gloss": gloss}]
    assert all("gloss" not in value["words"][wid] for wid in members)


@pytest.mark.parametrize(
    "language,expected",
    [
        ("pl", {"w084": "Ty", "w089": "nie", "w090": "wzdragałeś się"}),
        ("en", {"w084": "You", "w091": "the Virgin’s", "w092": "womb"}),
    ],
)
def test_subject_negation_and_possessive_have_one_realization(language, expected):
    value = layer(language)
    for wid, gloss in expected.items():
        assert value["words"][wid]["gloss"] == gloss
    counts = {wid: int("gloss" in value["words"][wid]) for wid in CLAUSE}
    groups = []
    for segment in core()["segments"]:
        for group in value["segments"][segment["id"]].get("alignments", []):
            if not set(group["words"]) & CLAUSE:
                continue
            groups.append(group)
            assert set(group["words"]) <= CLAUSE
            assert len(group["words"]) >= 2 and "reason" not in group
            ids = [w["id"] for w in segment.get("words", [])]
            start = ids.index(group["words"][0])
            assert ids[start : start + len(group["words"])] == group["words"]
            for wid in group["words"]:
                counts[wid] += 1
    assert len(groups) == 2
    assert counts == {wid: 1 for wid in CLAUSE}
    assert len(expected) + len(groups) == 5


@pytest.mark.parametrize("language", ["pl", "en"])
def test_alternative_is_localized_once_and_does_not_unsettle_future_active(language):
    neutral = core()
    analysis = neutral["editorial"]["words"]["w086"]["analysis"]
    assert (analysis["confidence"], analysis["review"]) == ("medium", "disputed")
    assert set(analysis["sources"]) == {"editorial", "collatinus"}
    assert set(neutral["localization"]["notes"]) & CLAUSE == {"w086"}
    value = layer(language)
    note = value["words"]["w086"]["note"]
    assert "hóminem" in note and "susceptúrus" in note
    if language == "pl":
        assert "Gerundium" in note and "gerundivum" in note and "domyślne" in note
        assert "jeszcze przyszłe" in value["words"]["w087"]["explanation"]
    else:
        assert "gerund after ad" in note and "gerundive" in note and "understood" in note
        assert "looks ahead" in value["words"]["w087"]["explanation"]
    assert "explanation" not in value["words"]["w086"]
    assert "note" not in value["words"]["w087"]
    for wid in ["w084", "w085", "w089", "w091", "w092"]:
        assert "explanation" not in value["words"][wid]
    assert {"w087", "w088", "w090"} <= neutral["localization"]["explanations"].keys()
    assert "w092" not in neutral["localization"]["explanations"]
    for wid in ["w087", "w088", "w090"]:
        assert value["words"][wid]["explanation"]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_all_twenty_eight_continuous_translations_and_citations_are_preserved(language):
    value = layer(language)
    assert len(value["segments"]) == 28
    protected = {
        sid: {
            "translation": segment["translation"],
            "translation_citations": segment["translation_citations"],
        }
        for sid, segment in value["segments"].items()
    }
    assert digest(protected) == PROTECTED[language]


def test_clause_latin_forms_and_punctuation_remain_exact():
    words = tokens(core())
    expected = [
        ("w084", "Tu", ","),
        ("w085", "ad", None),
        ("w086", "liberándum", None),
        ("w087", "susceptúrus", None),
        ("w088", "hóminem", ","),
        ("w089", "non", None),
        ("w090", "horruísti", None),
        ("w091", "Vírginis", None),
        ("w092", "úterum", "."),
    ]
    assert [(wid, words[wid]["form"], words[wid].get("post")) for wid in sorted(CLAUSE)] == (
        expected
    )


@pytest.mark.parametrize("language", ["pl", "en"])
def test_addressed_source_binding_is_unique_and_current(language):
    segment = next(segment for segment in core()["segments"] if segment["id"] == "s13")
    provenance = read(f"languages/{language}/translation-provenance.json")
    name = f"orationes.te-deum.s13.{language}"
    matches = [site for site in provenance["sites"] if site["site"] == name]
    assert len(matches) == 1
    assert matches[0]["source_sha256"] == canonical_hash(source_payload(segment))


@pytest.mark.parametrize("language", ["pl", "en"])
def test_whole_caption_layer_covers_the_actual_source_once(language):
    neutral, value = core(), layer(language)
    ids = [word["id"] for segment in neutral["segments"] for word in segment.get("words", [])]
    assert len(neutral["segments"]) == 28
    assert len(ids) == len(set(ids)) == 194
    assert set(value["words"]) == set(ids)
    assert set(value["segments"]) == {segment["id"] for segment in neutral["segments"]}
    assert check_interlinear(neutral, value) == []
    assert all(
        "gloss" in group and "reason" not in group
        for segment in value["segments"].values()
        for group in segment.get("alignments", [])
    )


@pytest.mark.parametrize(
    "language,wid,expected",
    [
        (
            "en",
            "w112",
            "The Latin addresses Christ in a passive construction. The caption recasts it "
            "actively as the praying community’s confession: “We believe.”",
        ),
        (
            "en",
            "w130",
            "The prayer asks that God’s servants be numbered among the saints "
            "in everlasting glory.",
        ),
        (
            "pl",
            "w112",
            "Konstrukcja bierna wyraża wiarę w to, że Chrystus przyjdzie jako Sędzia. "
            "Polskie „wierzymy, że…” oddaje ją w stronie czynnej.",
        ),
        (
            "pl",
            "w130",
            "Prosimy Boga, aby zaliczył nas do grona świętych w wiecznej chwale.",
        ),
    ],
)
def test_contextual_explanations_keep_their_reviewed_contemporary_wording(language, wid, expected):
    assert layer(language)["words"][wid]["explanation"] == expected


def test_polish_help_predicate_governs_its_reviewed_dative():
    words, value = tokens(core()), layer("pl")
    assert words["w118"]["lemma"] == "subvenio"
    assert words["w117"]["morph"]["case"] == "dat"
    expected = {"w116": "Twoim", "w117": "sługom", "w118": "przyjdź z pomocą"}
    assert {wid: value["words"][wid].get("gloss") for wid in expected} == expected
    assert not any(
        set(group["words"]) & expected.keys()
        for segment in value["segments"].values()
        for group in segment.get("alignments", [])
    )

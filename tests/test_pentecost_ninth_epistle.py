"""Bounded Ninth Sunday after Pentecost readings and source contracts."""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from build_reader import store
from build_reader.bibliography_bindings import digest, selected_text
from checks import english, interlinear, raw_binding
from checks.collate import collate, load_witness
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.dominica-ix-post-pentecosten-epistola"
GROUPS = [
    ([11, 12], 12, "become idolaters"),
    ([18, 19], 19, "it is written"),
    ([20, 21], 20, "The people sat down"),
    ([71, 72], 71, "they were written"),
    ([75, 76], 75, "our correction"),
    ([84, 85, 86], 85, "thinks he stands"),
    ([90, 91, 92, 93], 93, "Let no temptation take hold of you"),
    ([96, 97, 98, 99], 99, "but God is faithful"),
    ([101, 102], 102, "will not permit"),
    ([110, 111], 110, "will also bring about"),
]


def wid(number):
    return f"w{number:03}"


def line(layer, first=1, last=117):
    return [
        value
        for n in range(first, last + 1)
        if (value := interlinear.effective_gloss(layer, wid(n)))
    ]


@pytest.mark.parametrize("numbers,anchor,gloss", GROUPS)
def test_selected_english_construction(numbers, anchor, gloss):
    # Exact selected-edition regression, not exclusive grammar or authorship.
    layer = store.raw_layer(ROOT, "en", TEXT)
    ids = [wid(n) for n in numbers]
    matches = [a for a in layer["segments"]["s01"]["alignments"] if set(ids) & set(a["words"])]
    assert matches == [{"words": ids, "anchor": wid(anchor), "gloss": gloss}]
    assert all("gloss" not in layer["words"][key] for key in ids)


@pytest.mark.parametrize(
    "number,gloss",
    [
        (10, "Nor"),
        (28, "Nor"),
        (43, "Nor"),
        (54, "Nor"),
        (87, "let him take heed"),
        (95, "a human one"),
        (108, "you can bear"),
        (114, "a favorable outcome"),
    ],
)
def test_selected_direct_english_reading(number, gloss):
    assert store.raw_layer(ROOT, "en", TEXT)["words"][wid(number)]["gloss"] == gloss


def test_polish_exception_and_selected_patient_construction():
    layer = store.raw_layer(ROOT, "pl", TEXT)
    assert line(layer, 90, 117) == [
        "Pokusa",
        "was",
        "niech nie ogarnie",
        "inna niż",
        "ludzka",
        "Wierny",
        "zaś",
        "Bóg",
        "jest",
        "który",
        "nie",
        "dopuści",
        "abyście byli kuszeni",
        "ponad",
        "to",
        "co",
        "możecie znieść",
        "lecz",
        "sprawi",
        "także",
        "z",
        "pokusą",
        "wyjście",
        "abyście",
        "mogli",
        "wytrzymać",
    ]
    assert {"words": ["w103", "w104"], "anchor": "w104", "gloss": "abyście byli kuszeni"} in layer[
        "segments"
    ]["s01"]["alignments"]
    assert all("gloss" not in layer["words"][key] for key in ["w103", "w104"])


def test_external_dependencies_and_negation_once():
    layer = store.raw_layer(ROOT, "en", TEXT)
    assert line(layer, 10, 27) == [
        "Nor",
        "become idolaters",
        "as",
        "some",
        "of",
        "them",
        "as",
        "it is written",
        "The people sat down",
        "to eat",
        "and",
        "to drink",
        "and",
        "rose up",
        "to play",
    ]
    assert line(layer, 43, 53) == [
        "Nor",
        "let us tempt",
        "Christ",
        "as",
        "some",
        "of them",
        "tempted",
        "and",
        "by",
        "the serpents",
        "perished",
    ]
    assert line(layer, 64, 81) == [
        "These things",
        "however",
        "all",
        "as",
        "a type",
        "happened",
        "to them",
        "they were written",
        "however",
        "for",
        "our correction",
        "upon",
        "whom",
        "the ends",
        "of ages",
        "have come",
    ]
    assert line(layer, 82, 117) == [
        "Therefore",
        "he who",
        "thinks he stands",
        "let him take heed",
        "lest",
        "he fall",
        "Let no temptation take hold of you",
        "except",
        "a human one",
        "but God is faithful",
        "who",
        "will not permit",
        "you",
        "to be tempted",
        "beyond",
        "that",
        "which",
        "you can bear",
        "but",
        "will also bring about",
        "with",
        "the temptation",
        "a favorable outcome",
        "that",
        "you may be able",
        "to bear",
    ]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_complete_provider_partition_and_retained_groups(language):
    doc, layers = store.load(ROOT, TEXT)
    layer = layers[language]
    assert len(doc["segments"]) == 1 and len(doc["segments"][0]["words"]) == 117
    assert interlinear.check(doc, layer) == []
    groups = layer["segments"]["s01"]["alignments"]
    direct = sum("gloss" in w for w in layer["words"].values())
    assert (direct, len(groups), sum(len(g["words"]) for g in groups), len(line(layer))) == (
        (109, 4, 8, 113) if language == "pl" else (87, 12, 30, 99)
    )
    assert not any("reason" in g for g in groups)
    retained = (
        (["w003", "w004"], "w004", "pożądajmy")
        if language == "pl"
        else (["w002", "w003", "w004"], "w004", "Let us not lust after")
    )
    assert {"words": retained[0], "anchor": retained[1], "gloss": retained[2]} in groups
    assert {
        "words": ["w034", "w035"],
        "anchor": "w034",
        "gloss": "dopuścili się rozpusty" if language == "pl" else "committed fornication",
    } in groups


@pytest.mark.parametrize(
    "number,gender,case,registry_index",
    [
        (14, "m", "nom", 124),
        (31, "m", "nom", 124),
        (47, "m", "nom", 124),
        (57, "m", "nom", 124),
        (64, "n", "nom", 311),
        (106, "n", "acc", 189),
    ],
)
def test_contextual_gender_and_pending_observation(number, gender, case, registry_index):
    core = store.core(ROOT, TEXT)
    word = core["segments"][0]["words"][number - 1]
    assert word["morph"] == {
        "pos": "pron",
        "case": case,
        "number": "sg" if number == 106 else "pl",
        "gender": gender,
    }
    assert core["editorial"]["words"][wid(number)]["analysis"]["review"] == "pending"
    registry = json.loads((ROOT / "build_reader/registry/morphology.json").read_text())
    assert registry[registry_index] == word["morph"]


def test_retained_impersonal_deponent_and_jussive_parses():
    words = store.core(ROOT, TEXT)["segments"][0]["words"]
    assert words[17]["substantive"] is True
    assert (
        words[17]["morph"]["pos"] == "verb"
        and words[17]["morph"]["mood"] == "part"
        and words[17]["morph"]["voice"] == "pass"
    )
    assert words[33]["morph"]["voice"] == "dep"
    assert words[37]["morph"]["gender"] == "f" and words[38]["morph"]["gender"] == "f"
    assert words[54]["morph"]["mood"] == "subj" and words[54]["morph"]["tense"] == "perf"
    assert words[92]["morph"]["mood"] == "subj" and words[92]["morph"]["tense"] == "pres"
    assert words[101]["morph"]["voice"] == "dep" and words[101]["morph"]["tense"] == "fut"
    assert words[105]["form"] == "id" and "post" not in words[105]


@pytest.mark.parametrize(
    "language,label", [("pl", "Czytanie formularza"), ("en", "The Epistle of")]
)
def test_localized_about(language, label):
    assert store.raw_layer(ROOT, language, TEXT)["about"].startswith(label)


@pytest.mark.parametrize(
    "language,target",
    [
        ("pl", "eb271ff67e66ef192ac1d83d8b9d617cea74ce8f281f6416659eae6ea2b56e74"),
        ("en", "391d1809ad33f4af5f7a36885d07c3b03bcf553c21a1e510c6a01a7ae089f112"),
    ],
)
def test_unchanged_working_prose_and_current_source_dependency(language, target):
    core = store.core(ROOT, TEXT)
    layer = store.raw_layer(ROOT, language, TEXT)
    sites = json.loads((ROOT / f"languages/{language}/translation-provenance.json").read_text())[
        "sites"
    ]
    matches = [s for s in sites if s["site"] == TEXT + ".s01." + language]
    assert len(matches) == 1
    site = matches[0]
    assert site["source_sha256"] == canonical_hash(source_payload(core["segments"][0]))
    assert (
        site["target_sha256"] == canonical_hash(layer["segments"]["s01"]["translation"]) == target
    )
    assert (site["origin"], site["review"], site["familiar_core"]) == (
        "working-unsettled",
        "working",
        False,
    )


def test_exact_direct_raw_plan():
    registry = json.loads((ROOT / "witnesses/raw/bindings.json").read_text())
    assert registry["bindings"]["pentecost-ix-epistle"] == {
        "witness": f"witnesses/{TEXT}/do.txt",
        "revision": "44667ff518b8ff1439780470828b39714f5306a2",
        "evidence": [
            {
                "archive": "pentecost-ix",
                "first": 28,
                "last": 28,
                "section": "Lectio",
                "section_line": 25,
            }
        ],
        "references": [],
        "reading": [{"archive": "pentecost-ix", "first": 28, "last": 28}],
    }
    ar = registry["archives"]["pentecost-ix"]
    raw = (ROOT / ar["path"]).read_bytes()
    assert (
        hashlib.sha256(raw).hexdigest()
        == ar["sha256"]
        == "ea1d892229c27e1cfab8ce501b5b6b01152c941cca9a73e55a56832613227c65"
    )
    assert ar["upstream"] == "web/www/missa/Latin/Tempora/Pent09-0.txt"
    lines = raw.decode().splitlines()
    assert len(lines) == 57 and lines[24] == "[Lectio]" and lines[26] == "!1 Cor 10:6-13"
    assert len(lines[27].split()) == 117 and lines[29] == "[Graduale]"


def test_literal_witnesses_accidentals_and_current_identity():
    folder = ROOT / "witnesses" / TEXT
    dm, digital = load_witness(folder / "do.txt")
    mm, printed = load_witness(folder / "mr.txt")
    bound = raw_binding.resolve_binding(folder / "do.txt", ROOT)
    assert bound is not None and bound.text == digital
    assert len(digital.split()) == len(printed.split()) == 117
    assert digital.split()[81] == printed.split()[81] == "Itaque"
    core = store.core(ROOT, TEXT)
    assert core["segments"][0]["words"][81]["form"] == "Ítaque"
    assert mm["description"] == "Missale Romanum, Benziger Brothers, New York, Editio iuxta typicam"
    assert "historical-transcribed" in mm and "transcribed" not in mm
    assert "current complete-page conformity" in mm["verification-scope"]
    assert "p. 382" in mm["boundary"] and "p. 383" in mm["boundary"]
    assert dm["path"].endswith("[Lectio] (lines 28-28)")
    assert "not original transcription genesis" in core["editorial"]["source"]["method"]
    assert "No conclusion, shared expansion or response" in core["editorial"]["notes"]
    ap = json.loads((folder / "apparatus.json").read_text())
    assert {r["at"]: r["witnesses"] for r in ap["adjudicated"]} == {
        "w042": {"do": "mília."},
        "w082": {"mr": "Itaque", "do": "Itaque"},
        "w106": {"do": "id,"},
        "w116": {"do": "póssitis"},
    }
    errors, _, stats = collate(store.load(ROOT, TEXT)[0], folder)
    assert errors == [] and stats["words"] == 117 and stats["witnesses"] == 2


def test_nonempty_graph_scope_and_pending_dependencies():
    graph = json.loads((ROOT / "bibliography/graph.json").read_text())
    uses = [u for u in graph["uses"] if u.get("address", {}).get("text") == TEXT]
    witnesses = [w for w in graph["witnesses"] if w.get("text") == TEXT]
    collations = [c for c in graph["collations"] if c.get("text") == TEXT]
    assert (len(uses), len(witnesses), len(collations)) == (2, 2, 1)
    mr = next(u for u in uses if u["id"].endswith(".mr1962"))
    do = next(u for u in uses if u["id"].endswith(".do44667ff"))
    assert mr["role"] == "direct_approved_print" and "Benziger" in mr["claim"]
    assert (
        mr["evidence_sha256"] == "6e0012b27439368b42d4107d1a4aeae03e9b88e7c9f453518a795765d1f29ed4"
    )
    assert (
        do["evidence_sha256"] == "ea1d892229c27e1cfab8ce501b5b6b01152c941cca9a73e55a56832613227c65"
    )
    assert "complete direct body 28" in do["locator"]["section"]
    for witness in witnesses:
        kind = witness["transcription"]
        assert witness["review"] == {"status": "pending"}
        assert witness["source_dependencies"] == {
            "uses": [],
            "raw_binding": "pentecost-ix-epistle" if kind == "do" else None,
        }
        assert (
            witness["transcription_sha256"]
            == hashlib.sha256(
                (ROOT / "witnesses" / TEXT / (kind + ".txt")).read_bytes()
            ).hexdigest()
        )
    ap = json.loads((ROOT / "witnesses" / TEXT / "apparatus.json").read_text())
    assert collations[0]["review"] == {"status": "pending"}
    assert collations[0]["apparatus_sha256"] == digest(ap)
    assert collations[0]["selected_text_sha256"] == digest(selected_text(store.core(ROOT, TEXT)))


def alternative_layer(language):
    doc, layers = store.load(ROOT, TEXT)
    return doc, copy.deepcopy(layers[language])


@pytest.mark.parametrize("number", [10, 28, 43, 54])
def test_neither_remains_a_valid_negative_command(number):
    doc, layer = alternative_layer("en")
    layer["words"][wid(number)]["gloss"] = "Neither"
    assert interlinear.check(doc, layer) == [] and english.check(doc, layer) == []
    assert line(layer, number, number)[0] == "Neither"


def test_intransitive_heed_remains_valid():
    doc, layer = alternative_layer("en")
    layer["words"]["w087"]["gloss"] = "let him heed"
    assert interlinear.check(doc, layer) == [] and english.check(doc, layer) == []
    assert line(layer, 87, 89) == ["let him heed", "lest", "he fall"]


def test_polish_older_object_infinitive_can_preserve_the_patients():
    doc, layer = alternative_layer("pl")
    layer["segments"]["s01"]["alignments"] = [
        g for g in layer["segments"]["s01"]["alignments"] if "w104" not in g["words"]
    ]
    layer["words"]["w103"]["gloss"], layer["words"]["w104"]["gloss"] = "was", "kusić"
    assert interlinear.check(doc, layer) == []
    assert line(layer, 100, 108) == [
        "który",
        "nie",
        "dopuści",
        "was",
        "kusić",
        "ponad",
        "to",
        "co",
        "możecie znieść",
    ]


def test_solemn_narrative_inversion_remains_valid():
    doc, layer = alternative_layer("en")
    layer["segments"]["s01"]["alignments"] = [
        g for g in layer["segments"]["s01"]["alignments"] if "w020" not in g["words"]
    ]
    layer["words"]["w020"]["gloss"], layer["words"]["w021"]["gloss"] = "sat down", "the people"
    assert interlinear.check(doc, layer) == [] and english.check(doc, layer) == []
    assert line(layer, 20, 27) == [
        "sat down",
        "the people",
        "to eat",
        "and",
        "to drink",
        "and",
        "rose up",
        "to play",
    ]


def test_postverbal_also_is_not_a_generic_grammar_failure():
    doc, layer = alternative_layer("en")
    layer["segments"]["s01"]["alignments"] = [
        g for g in layer["segments"]["s01"]["alignments"] if "w110" not in g["words"]
    ]
    layer["words"]["w110"]["gloss"], layer["words"]["w111"]["gloss"] = "will bring about", "also"
    assert interlinear.check(doc, layer) == [] and english.check(doc, layer) == []
    assert line(layer, 109, 117) == [
        "but",
        "will bring about",
        "also",
        "with",
        "the temptation",
        "a favorable outcome",
        "that",
        "you may be able",
        "to bear",
    ]


def test_larger_faithful_negative_command_is_not_semantically_invalid():
    doc, layer = alternative_layer("en")
    group = next(g for g in layer["segments"]["s01"]["alignments"] if "w012" in g["words"])
    group.update(words=["w010", "w011", "w012"], gloss="Nor become idolaters")
    del layer["words"]["w010"]["gloss"]
    assert interlinear.check(doc, layer) == [] and english.check(doc, layer) == []
    assert line(layer, 10, 12) == ["Nor become idolaters"]

"""Bounded Holy Innocents Epistle readings and source contracts."""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from build_reader import store
from build_reader.bibliography_bindings import digest
from checks import english, interlinear, raw_binding
from checks.collate import collate, load_witness
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.sanctorum-innocentium-martyrum-epistola"
GROUPS = [
    ([18, 19], 18, "His name"),
    ([22, 23], 22, "of His Father"),
    ([26, 27], 26, "their foreheads"),
    ([35, 36], 35, "of many waters"),
    ([40, 41], 40, "of loud thunder"),
    ([50, 51], 50, "their harps"),
    ([55, 56], 55, "a new song"),
    ([77, 78], 77, "have been purchased"),
    ([98, 99], 98, "were purchased"),
    ([108, 109], 108, "their mouth"),
    ([110, 111, 112], 112, "was not found"),
]
DIRECT = {
    21: "the name",
    30: "a voice",
    34: "the voice",
    39: "the voice",
    46: "was like that",
    47: "of harpers",
    53: "they were singing",
    69: "the song",
    83: "those who",
    103: "to God",
    105: "to the Lamb",
}


def wid(n):
    return f"w{n:03d}"


def line(layer, first=1, last=120):
    return [
        value
        for n in range(first, last + 1)
        if (value := interlinear.effective_gloss(layer, wid(n)))
    ]


@pytest.mark.parametrize("numbers,anchor,gloss", GROUPS)
def test_chosen_minimal_english_group(numbers, anchor, gloss):
    layer = store.raw_layer(ROOT, "en", TEXT)
    ids = [wid(n) for n in numbers]
    matches = [a for a in layer["segments"]["s01"]["alignments"] if set(ids) & set(a["words"])]
    assert matches == [{"words": ids, "anchor": wid(anchor), "gloss": gloss}]
    assert all("gloss" not in layer["words"][key] for key in ids)


@pytest.mark.parametrize("number,gloss", DIRECT.items())
def test_contextual_english_direct_provider(number, gloss):
    assert store.raw_layer(ROOT, "en", TEXT)["words"][wid(number)]["gloss"] == gloss


@pytest.mark.parametrize(
    "number,gloss", [(69, "pieśni"), (70, "tylko"), (94, "za Barankiem"), (102, "jako pierwociny")]
)
def test_polish_government_and_exception(number, gloss):
    assert store.raw_layer(ROOT, "pl", TEXT)["words"][wid(number)]["gloss"] == gloss


def test_whole_polish_dependency_windows_preserve_nominatives_and_datives():
    layer = store.raw_layer(ROOT, "pl", TEXT)
    assert line(layer, 65, 75) == [
        "i",
        "nikt",
        "nie mógł",
        "śpiewać",
        "pieśni",
        "tylko",
        "owe",
        "sto",
        "czterdzieści",
        "cztery",
        "tysiące",
    ]
    assert line(layer, 92, 105) == [
        "Ci",
        "podążają",
        "za Barankiem",
        "dokądkolwiek",
        "pójdzie",
        "Ci",
        "wykupieni",
        "zostali",
        "spośród",
        "ludzi",
        "jako pierwociny",
        "Bogu",
        "i",
        "Barankowi",
    ]


def test_whole_english_line_retains_external_dependencies():
    layer = store.raw_layer(ROOT, "en", TEXT)
    expected = [
        "In",
        "those days",
        "I saw",
        "upon",
        "Mount",
        "Sion",
        "the Lamb",
        "standing",
        "and",
        "with",
        "Him",
        "one hundred",
        "forty",
        "four",
        "thousand",
        "having",
        "His name",
        "and",
        "the name",
        "of His Father",
        "written",
        "on",
        "their foreheads",
        "And",
        "I heard",
        "a voice",
        "from",
        "heaven",
        "like",
        "the voice",
        "of many waters",
        "and",
        "like",
        "the voice",
        "of loud thunder",
        "and",
        "the voice",
        "which",
        "I heard",
        "was like that",
        "of harpers",
        "playing",
        "on",
        "their harps",
        "And",
        "they were singing",
        "as it were",
        "a new song",
        "before",
        "the throne",
        "and",
        "before",
        "four",
        "living creatures",
        "and",
        "the elders",
        "and",
        "no one",
        "could",
        "sing",
        "the song",
        "except",
        "those",
        "one hundred",
        "forty",
        "four",
        "thousand",
        "who",
        "have been purchased",
        "from",
        "the earth",
        "These",
        "are",
        "those who",
        "with",
        "women",
        "have not been defiled",
        "for they are virgins",
        "These",
        "follow",
        "the Lamb",
        "wherever",
        "He goes",
        "These",
        "were purchased",
        "from among",
        "men",
        "firstfruits",
        "to God",
        "and",
        "to the Lamb",
        "and",
        "in",
        "their mouth",
        "was not found",
        "a lie",
        "for they are without blemish",
        "before",
        "the throne",
        "of God",
    ]
    assert line(layer) == expected


@pytest.mark.parametrize("language", ["pl", "en"])
def test_complete_provider_partition(language):
    doc, layers = store.load(ROOT, TEXT)
    layer = layers[language]
    assert len(doc["segments"]) == 1 and len(doc["segments"][0]["words"]) == 120
    assert interlinear.check(doc, layer) == []
    groups = layer["segments"]["s01"].get("alignments", [])
    direct = sum("gloss" in w for w in layer["words"].values())
    assert (direct, len(groups), sum(len(a["words"]) for a in groups)) == (
        (120, 0, 0) if language == "pl" else (85, 15, 35)
    )
    assert not any("reason" in a for a in groups)


def test_existing_english_constructions_are_preserved():
    layer = store.raw_layer(ROOT, "en", TEXT)
    groups = layer["segments"]["s01"]["alignments"]
    for numbers, anchor, gloss in [
        ([2, 3], 2, "those days"),
        ([86, 87, 88], 88, "have not been defiled"),
        ([89, 90, 91], 89, "for they are virgins"),
        ([114, 115, 116, 117], 117, "for they are without blemish"),
    ]:
        assert {"words": [wid(n) for n in numbers], "anchor": wid(anchor), "gloss": gloss} in groups


@pytest.mark.parametrize(
    "language,label", [("pl", "Czytanie formularza"), ("en", "The Epistle of")]
)
def test_localized_about(language, label):
    assert store.raw_layer(ROOT, language, TEXT)["about"].startswith(label)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_masculine_virgines_is_explained_without_changing_the_shared_head(language):
    core = store.core(ROOT, TEXT)
    word = next(w for w in core["segments"][0]["words"] if w["id"] == "w089")
    assert word["morph"] == {"pos": "noun", "case": "nom", "gender": "m", "number": "pl", "decl": 3}
    assert core["localization"]["explanations"]["w089"] == {}
    note = store.raw_layer(ROOT, language, TEXT)["words"]["w089"]["explanation"]
    assert note == (
        "Tutaj vírgines odnosi się do mężczyzn zachowujących dziewictwo. "
        "Łaciński rzeczownik virgo, zwykle żeński, ma także poświadczone użycie męskie."
        if language == "pl"
        else "Here virgines refers to men who remain virgins. "
        "The usually feminine noun virgo also has an attested masculine use."
    )


def test_illa_contextual_gender_is_complete_and_pending():
    core = store.core(ROOT, TEXT)
    word = next(w for w in core["segments"][0]["words"] if w["id"] == "w071")
    assert word == {
        "id": "w071",
        "form": "illa",
        "lemma": "ille",
        "morph": {"pos": "pron", "case": "nom", "number": "pl", "gender": "n"},
    }
    assert core["editorial"]["words"]["w071"]["analysis"]["review"] == "pending"


@pytest.mark.parametrize(
    "language,target",
    [
        ("pl", "3e26dcc0c6069a5c6b929a022456d0c37c17de602f5dc19bb106d25999273258"),
        ("en", "be117af05684db5ed1be0fc5b570688a09decdbe26583e304a9c5de20c8e569e"),
    ],
)
def test_unchanged_working_prose_and_current_source_dependency(language, target):
    core = store.core(ROOT, TEXT)
    layer = store.raw_layer(ROOT, language, TEXT)
    records = json.loads((ROOT / f"languages/{language}/translation-provenance.json").read_text())[
        "sites"
    ]
    matched = [r for r in records if r["site"] == TEXT + ".s01." + language]
    assert len(matched) == 1
    site = matched[0]
    assert (
        site["target_sha256"] == canonical_hash(layer["segments"]["s01"]["translation"]) == target
    )
    assert site["source_sha256"] == canonical_hash(source_payload(core["segments"][0]))
    assert site["origin"] == "working-unsettled" and site["review"] == "working"


def test_exact_direct_source_body_and_all_six_accidentals():
    folder = ROOT / "witnesses" / TEXT
    bound = raw_binding.resolve_binding(folder / "do.txt", ROOT)
    assert bound is not None
    _, body = load_witness(folder / "do.txt")
    assert bound.text == body and len(body.split()) == 120
    expected = {
        "w015": "quatuor",
        "w016": "mília,",
        "w019": "ejus,",
        "w023": "ejus",
        "w032": "cœlo,",
        "w075": "mília,",
    }
    ap = json.loads((folder / "apparatus.json").read_text())
    assert {r["at"]: r["witnesses"]["do"] for r in ap["adjudicated"]} == expected
    assert ap["summary"] == {"entries": 6, "classes": ["accent", "orthography"]}
    for key, token in expected.items():
        assert body.split()[int(key[1:]) - 1] == token
    errors, _, stats = collate(store.load(ROOT, TEXT)[0], folder)
    assert errors == [] and stats["words"] == 120 and stats["witnesses"] == 2


def test_exact_raw_plan_excludes_framing_and_inheritance():
    registry = json.loads((ROOT / "witnesses/raw/bindings.json").read_text())
    assert registry["bindings"]["holy-innocents-epistle"] == {
        "witness": f"witnesses/{TEXT}/do.txt",
        "revision": "44667ff518b8ff1439780470828b39714f5306a2",
        "evidence": [
            {
                "archive": "holy-innocents-gospel",
                "first": 34,
                "last": 34,
                "section": "Lectio",
                "section_line": 31,
            }
        ],
        "references": [],
        "reading": [{"archive": "holy-innocents-gospel", "first": 34, "last": 34}],
    }


def test_print_identity_and_current_observation_not_original_genesis():
    core = store.core(ROOT, TEXT)
    meta, body = load_witness(ROOT / "witnesses" / TEXT / "mr.txt")
    assert (
        meta["description"] == "Missale Romanum, Benziger Brothers, New York, Editio iuxta typicam"
    )
    assert "historical-transcribed" in meta and "transcribed" not in meta
    assert "current page conformity" in meta["verification-scope"]
    assert len(body.split()) == 120 and "Amen" not in body
    assert "Benziger Brothers" in core["editorial"]["source"]["method"]
    assert "not original transcription genesis" in core["editorial"]["source"]["method"]
    assert "without an abbreviated conclusion" in core["editorial"]["notes"]
    assert "not inherited" in core["editorial"]["notes"]


def test_nonvacuous_graph_dependencies_pending_and_evidence_identity():
    graph = json.loads((ROOT / "bibliography/graph.json").read_text())
    uses = [u for u in graph["uses"] if u.get("address", {}).get("text") == TEXT]
    witnesses = [w for w in graph["witnesses"] if w.get("text") == TEXT]
    collations = [c for c in graph["collations"] if c.get("text") == TEXT]
    assert (len(uses), len(witnesses), len(collations)) == (2, 2, 1)
    printed = next(u for u in uses if u["id"].endswith(".mr1962"))
    digital = next(u for u in uses if u["id"].endswith(".do44667ff"))
    assert printed["role"] == "direct_approved_print" and "Benziger" in printed["claim"]
    assert (
        printed["evidence_sha256"]
        == "a074d446cc3ce11efbab41c36b96ac9ce396e668e1989b9557ac0e647098cbaa"
    )
    assert (
        digital["evidence_sha256"]
        == "28f4f262a6e8471df524e2905b681b7b3a59485e37fea5c69060e34764533cd5"
    )
    assert "complete direct body 34" in digital["locator"]["section"]
    for witness in witnesses:
        kind = witness["transcription"]
        assert witness["review"] == {"status": "pending"}
        assert witness["source_dependencies"] == {
            "uses": [],
            "raw_binding": "holy-innocents-epistle" if kind == "do" else None,
        }
        raw = (ROOT / "witnesses" / TEXT / (kind + ".txt")).read_bytes()
        assert witness["transcription_sha256"] == hashlib.sha256(raw).hexdigest()
    ap = json.loads((ROOT / "witnesses" / TEXT / "apparatus.json").read_text())
    assert collations[0]["review"] == {"status": "pending"}
    assert collations[0]["apparatus_sha256"] == digest(ap)
    assert collations[0]["apparatus"] == ap["summary"]


@pytest.mark.parametrize(
    "gloss,include_lie",
    [
        ("was not found", False),
        ("there was not found", False),
        ("no lie was found", True),
        ("no lie has been found", True),
    ],
)
def test_legitimate_clause_alternatives_are_not_a_universal_order_rule(gloss, include_lie):
    doc, layers = store.load(ROOT, TEXT)
    layer = copy.deepcopy(layers["en"])
    group = next(a for a in layer["segments"]["s01"]["alignments"] if "w112" in a["words"])
    group["gloss"] = gloss
    if include_lie:
        group["words"].append("w113")
        del layer["words"]["w113"]["gloss"]
    assert interlinear.check(doc, layer) == []
    assert english.check(doc, layer) == []
    assert line(layer, 106, 113) == ["and", "in", "their mouth", gloss] + (
        [] if include_lie else ["a lie"]
    )

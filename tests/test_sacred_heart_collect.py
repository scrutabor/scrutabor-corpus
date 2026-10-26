"""Reviewed collect constructions and bounded preservation, not litany acceptance."""

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

from checks import interlinear, language_packs
from checks.collate import load_witness
from checks.translation_provenance import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
TEXT = "litaniae.sacratissimi-cordis-iesu"
RELATIVE = "texts/litaniae/sacratissimi-cordis-iesu.json"
MEMBERS = [f"w{i:03}" for i in range(339, 383)]
GROUPS = [
    (345, 347, 346, "of Your most beloved Son"),
    (357, 358, 358, "He offers to You"),
    (359, 362, 362, "and to those who ask for Your mercy"),
    (363, 366, 365, "be appeased and grant pardon"),
    (369, 373, 370, "of the same Jesus Christ, Your Son"),
    (374, 378, 376, "who lives and reigns with You"),
    (379, 381, 380, "forever and ever"),
]
CONTINUOUS = (
    "Almighty and eternal God, look upon the Heart of Thy most beloved Son and upon "
    "the praises and satisfaction which He offers Thee in the name of sinners; "
    "and to those who implore Thy mercy, be Thou appeased and grant forgiveness "
    "in the name of the same Jesus Christ, Thy Son, who lives and reigns with Thee "
    "for ever and ever. Amen."
)
CAPTION_UNITS = [
    "Almighty",
    "eternal",
    "God",
    "look",
    "upon",
    "the Heart",
    "of Your most beloved Son",
    "and",
    "upon",
    "praises",
    "and",
    "acts of reparation",
    "which",
    "in",
    "the name",
    "of sinners",
    "He offers to You",
    "and to those who ask for Your mercy",
    "be appeased and grant pardon",
    "in",
    "the name",
    "of the same Jesus Christ, Your Son",
    "who lives and reigns with You",
    "forever and ever",
    "Amen",
]


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def current():
    return read(RELATIVE), read("languages/en/" + RELATIVE)


def segment(core):
    return next(s for s in core["segments"] if s["id"] == "s089")


def scoped(core):
    return {"id": TEXT, "segments": [segment(core)]}


def group(layer, first):
    matches = [
        a for a in layer["segments"]["s089"]["alignments"] if a["words"][0] == f"w{first:03}"
    ]
    assert len(matches) == 1
    return matches[0]


def caption_units(core, layer):
    by_word = interlinear.alignment_by_word(layer)
    units = []
    for word in segment(core)["words"]:
        wid = word["id"]
        aligned = by_word.get(wid)
        if aligned:
            if wid == aligned["words"][0]:
                units.append(aligned["gloss"])
        else:
            units.append(layer["words"][wid]["gloss"])
    return units


def assert_reviewed_constructions(core, layer):
    words = {w["id"]: w for w in segment(core)["words"]}
    assert words["w353"]["morph"]["case"] == "acc"
    assert words["w353"]["morph"]["number"] == "pl"
    assert words["w353"]["morph"]["gender"] == "f"
    assert words["w350"]["lemma"] == "laus"
    assert words["w352"]["lemma"] == "satisfactio"
    assert words["w352"]["morph"]["number"] == "pl"
    assert words["w359"]["morph"]["case"] == "dat"
    assert words["w362"]["morph"]["case"] == "dat"
    assert words["w362"]["head"] == "w359"
    assert words["w360"]["morph"]["case"] == "acc"
    assert words["w365"]["morph"]["mood"] == "imp"
    assert words["w365"]["morph"]["person"] == 2
    assert words["w366"]["head"] == "w363"
    assert words["w366"]["morph"]["case"] == "nom"
    assert words["w366"]["morph"]["mood"] == "part"
    assert words["w366"]["morph"]["voice"] == "pass"
    assert layer["words"]["w352"]["gloss"] == "acts of reparation"
    assert group(layer, 359)["gloss"] == "and to those who ask for Your mercy"
    assert group(layer, 363)["gloss"] == "be appeased and grant pardon"
    assert "agrees with the God being addressed" in layer["words"]["w366"]["explanation"]
    assert layer["segments"]["s089"]["translation"] == CONTINUOUS
    assert caption_units(core, layer) == CAPTION_UNITS


@pytest.mark.parametrize("first,last,anchor,gloss", GROUPS)
def test_collect_minimal_groups(first, last, anchor, gloss):
    _, layer = current()
    actual = group(layer, first)
    assert actual == {
        "words": [f"w{i:03}" for i in range(first, last + 1)],
        "anchor": f"w{anchor:03}",
        "gloss": gloss,
    }
    assert all("gloss" not in layer["words"][wid] for wid in actual["words"])


def test_collect_44_tokens_have_25_realizations_without_zero_or_double_glosses():
    core, layer = current()
    assert layer["language"] == "en"
    assert [w["id"] for w in segment(core)["words"]] == MEMBERS
    groups = layer["segments"]["s089"]["alignments"]
    assert len(groups) == 7
    grouped = [wid for a in groups for wid in a["words"]]
    direct = [wid for wid in MEMBERS if layer["words"][wid].get("gloss")]
    assert len(grouped) == 26
    assert len(direct) == 18
    assert Counter(grouped + direct) == Counter(MEMBERS)
    assert all(a.get("gloss") and "reason" not in a for a in groups)
    assert interlinear.check(scoped(core), layer) == []
    assert len(caption_units(core, layer)) == 25


def test_collect_dative_beneficiaries_and_divine_appeasement_are_distinct():
    assert_reviewed_constructions(*current())


def test_complete_caption_line_is_contemporary_without_rewriting_protected_verse():
    core, layer = current()
    assert caption_units(core, layer) == CAPTION_UNITS
    assert not any(old in " ".join(CAPTION_UNITS) for old in ("Thy", "Thee", "Thou", "liveth"))
    assert layer["segments"]["s089"]["translation"] == CONTINUOUS
    assert "praises and satisfaction" in CONTINUOUS
    assert "for ever and ever" in CONTINUOUS
    assert "great goodness" not in CONTINUOUS


def test_selected_short_latin_conclusion_and_registered_transcript_are_preserved():
    core, _ = current()
    words = segment(core)["words"]
    forms = [w["form"] for w in words]
    assert forms[-9:] == [
        "qui",
        "tecum",
        "vivit",
        "et",
        "regnat",
        "in",
        "sǽcula",
        "sæculórum",
        "Amen",
    ]
    _, body = load_witness(ROOT / "witnesses" / TEXT / "enchiridion-1952.txt")
    assert body.endswith(
        "tu veniam concede placatus in nomine eiusdem Filii tui Iesu Christi, "
        "qui tecum vivit et regnat in sæcula saeculorum. Amen."
    )
    assert "unitate" not in " ".join(forms)
    assert core["localization"]["explanations"] == {"w366": {"languages": ["en"]}}
    without_topology = deepcopy(core)
    del without_topology["localization"]["explanations"]
    assert canonical_hash(without_topology) == (
        "35257d85aa0f1e75f3d5626f10eee590841a21f4a86394639f4657f41c911a5e"
    )


@pytest.mark.parametrize("language", ["en", "pl"])
def test_explanation_topology_is_english_only_and_polish_stays_unmodified(language):
    core, _ = current()
    layer = read(f"languages/{language}/" + RELATIVE)
    assert core["localization"]["explanations"] == {"w366": {"languages": ["en"]}}
    assert ("explanation" in layer["words"]["w366"]) == (language == "en")
    assert language_packs.check_layer(core, layer, ROOT / RELATIVE) == []


@pytest.mark.parametrize("damage", ["missing-declaration", "missing-explanation", "wrong-language"])
def test_real_explanation_topology_rejects_damage_then_restores(damage):
    core, layer = current()
    saved_core, saved_layer = deepcopy(core), deepcopy(layer)
    assert language_packs.check_layer(core, layer, ROOT / RELATIVE) == []
    if damage == "missing-declaration":
        del core["localization"]["explanations"]
    elif damage == "missing-explanation":
        del layer["words"]["w366"]["explanation"]
    else:
        core["localization"]["explanations"]["w366"]["languages"] = ["pl"]
    assert any(
        "explanation topology differs" in error
        for error in language_packs.check_layer(core, layer, ROOT / RELATIVE)
    )
    core.clear()
    core.update(saved_core)
    layer.clear()
    layer.update(saved_layer)
    assert language_packs.check_layer(core, layer, ROOT / RELATIVE) == []


def unrelated_english(layer):
    return {
        **layer,
        "segments": {k: v for k, v in layer["segments"].items() if k != "s089"},
        "words": {k: v for k, v in layer["words"].items() if k not in MEMBERS},
    }


CAPTION_SUCCESSORS: list[tuple[str, dict, dict[str, str]]] = [
    (
        "s018",
        {"words": ["w057", "w058"], "anchor": "w057", "gloss": "to the Word of God"},
        {"w057": "Word", "w058": "of God"},
    ),
    (
        "s044",
        {"words": ["w164", "w165", "w166"], "anchor": "w166", "gloss": "was well pleased"},
        {"w164": "to Himself", "w165": "well", "w166": "was well pleased"},
    ),
    (
        "s046",
        {"words": ["w175", "w176"], "anchor": "w176", "gloss": "we have received"},
        {"w175": "we", "w176": "we have received"},
    ),
    (
        "s056",
        {"words": ["w216", "w217"], "anchor": "w216", "gloss": "our sins"},
        {"w216": "sins", "w217": "our"},
    ),
    (
        "s060",
        {"words": ["w230", "w231"], "anchor": "w230", "gloss": "our offenses"},
        {"w230": "offenses", "w231": "our"},
    ),
    (
        "s068",
        {
            "words": ["w258", "w259", "w260", "w261"],
            "anchor": "w258",
            "gloss": "our life and resurrection",
        },
        {"w258": "life", "w259": "and", "w260": "resurrection", "w261": "our"},
    ),
    (
        "s070",
        {
            "words": ["w266", "w267", "w268", "w269"],
            "anchor": "w266",
            "gloss": "our peace and reconciliation",
        },
        {"w266": "peace", "w267": "and", "w268": "reconciliation", "w269": "our"},
    ),
    (
        "s087",
        {"words": ["w333", "w334"], "anchor": "w333", "gloss": "our heart"},
        {"w333": "heart", "w334": "our"},
    ),
    (
        "s087",
        {"words": ["w336", "w337"], "anchor": "w336", "gloss": "Your Heart"},
        {"w336": "Heart", "w337": "Your"},
    ),
]


def historical_english_for_collect_scope(layer: dict) -> dict:
    """Undo only the separately reviewed invocation captions in a checked copy."""
    projected = deepcopy(layer)
    for segment_id, expected, previous_glosses in CAPTION_SUCCESSORS:
        segment = projected["segments"][segment_id]
        groups = segment.get("alignments", [])
        matching = [g for g in groups if g.get("words") == expected["words"]]
        assert matching == [expected], "reviewed litany caption successor"
        groups.remove(matching[0])
        if not groups:
            del segment["alignments"]
        for wid, previous in previous_glosses.items():
            assert "gloss" not in projected["words"][wid], "reviewed litany caption successor"
            projected["words"][wid]["gloss"] = previous
    assert projected["words"]["w308"].get("gloss") == "us", "reviewed litany caption successor"
    projected["words"]["w308"]["gloss"] = "to us"
    return projected


def assert_preserved_english(layer):
    layer = historical_english_for_collect_scope(layer)
    assert len(unrelated_english(layer)["segments"]) == 88
    assert canonical_hash(unrelated_english(layer)) == (
        "cd29b72c8077e238793f35c93f374e13270a0cb3b2ebf3d42f0e393c79d4b196"
    )


def test_other_88_english_segments_words_and_metadata_are_unchanged():
    # This preservation pin records edit scope, not semantic acceptance of those segments.
    assert_preserved_english(current()[1])


def assert_preserved_polish(layer):
    assert canonical_hash(layer) == (
        "3813e50603bdffe875d5954d6f509cf5f6f3f5cba761264d68449d52515d0a3a"
    )


def test_entire_polish_layer_including_protected_collect_is_unchanged():
    assert_preserved_polish(read("languages/pl/" + RELATIVE))


def test_collect_provenance_is_revised_inherited_and_working_not_reapproved():
    _, layer = current()
    rows = read("languages/en/translation-provenance.json")["sites"]
    found = [r for r in rows if r["site"] == TEXT + ".s089.en"]
    assert len(found) == 1
    row = found[0]
    assert row["origin"] == "public-domain"
    assert row["review"] == "working"
    assert row["familiar_core"] is False
    assert (
        row["source_sha256"] == "74b2edb1f836c429976579038b6e43db804a99194caf24f556d485d73ac8e66a"
    )
    assert row["target_sha256"] == canonical_hash(layer["segments"]["s089"]["translation"])
    records = read("languages/en/translation-basis.json")["records"]
    relationships = [
        r["relationship"] for r in records if TEXT in r["texts"] and "s089" in r.get("segments", [])
    ]
    assert relationships == ["revised"]


def test_exact_historical_body_basis_and_redundant_parallel_have_separate_decisions():
    uses = {r["id"]: r for r in read("languages/en/bibliography.json")["uses"]}
    key = uses["use.en.897dfde6d62c069f81b8"]
    raccolta = uses["use.en.058b353ebe384515dd30"]
    expected_address = {"kind": "segment", "text": TEXT, "segment": "s089"}
    assert key["address"] == raccolta["address"] == expected_address
    assert key["role"] == "historical_wording_basis"
    assert key["decision"] == "RETAIN_WITH_CORRECTION"
    assert key["locator"] == {
        "printed": "pp. 262–263",
        "scan": "DJVU physical pages 275–276 (one-based)",
    }
    assert "Historical English basis for the revised collect body" in key["claim"]
    assert "appeasement" in key["claim"]
    assert "omits this source’s unity-of-the-Holy-Ghost clause" in key["claim"]
    assert "not a verbatim witness" in key["claim"]
    assert raccolta["decision"] == "REMOVE"
    assert "redundant" in raccolta["decision_reason"]
    assert raccolta["locator"] == {"printed": "p. 143", "scan": "PDF page 163 (one-based)"}
    assert (
        key["evidence_sha256"] == "65bcb7f8727fcbb5826b99fd5cef221f8b59ebad438a68c4b6179a46d653841a"
    )
    assert (
        raccolta["evidence_sha256"]
        == "c9809a19f94297b103f773e26129d932f4a0eaa99796e398155dc35a92e2fa7b"
    )
    for item, index in ((key, 0), (raccolta, 1)):
        assert item["legacy_refs"] == [
            "languages/en/" + RELATIVE + f"#/segments/s089/translation_citations/{index}"
        ]


@pytest.mark.parametrize(
    "damage",
    ["missing-direct", "dual-direct", "missing-group", "gap", "reorder", "anchor", "duplicate"],
)
def test_real_collect_alignment_rejects_damage_then_restores(damage):
    core, layer = current()
    saved = deepcopy(layer)
    assert interlinear.check(scoped(core), layer) == []
    if damage == "missing-direct":
        del layer["words"]["w344"]["gloss"]
    elif damage == "dual-direct":
        layer["words"]["w346"]["gloss"] = "of Son"
    elif damage == "missing-group":
        layer["segments"]["s089"]["alignments"].pop(0)
    elif damage == "gap":
        group(layer, 345)["words"][1] = "w348"
    elif damage == "reorder":
        group(layer, 345)["words"].reverse()
    elif damage == "anchor":
        group(layer, 345)["anchor"] = "w344"
    else:
        group(layer, 345)["words"].append("w347")
    assert interlinear.check(scoped(core), layer)
    layer.clear()
    layer.update(saved)
    assert interlinear.check(scoped(core), layer) == []


@pytest.mark.parametrize(
    "damage",
    [
        "goodness",
        "pleasure",
        "recipient",
        "appeasement-note",
        "participle-head",
        "long-ending",
        "relative",
        "agent",
    ],
)
def test_reviewed_real_collect_reading_rejects_damage_then_restores(damage):
    core, layer = current()
    saved_core, saved_layer = deepcopy(core), deepcopy(layer)
    assert_reviewed_constructions(core, layer)
    if damage == "goodness":
        layer["segments"]["s089"]["translation"] = CONTINUOUS.replace(
            "be Thou appeased and grant forgiveness", "in Thy great goodness grant forgiveness"
        )
    elif damage == "pleasure":
        layer["words"]["w352"]["gloss"] = "pleasures"
    elif damage == "recipient":
        group(layer, 359)["gloss"] = "and those who ask for Your mercy"
    elif damage == "appeasement-note":
        layer["words"]["w366"]["explanation"] = "The petitioners are appeased."
    elif damage == "participle-head":
        next(w for w in segment(core)["words"] if w["id"] == "w366")["head"] = "w359"
    elif damage == "long-ending":
        layer["segments"]["s089"]["translation"] = CONTINUOUS.replace(
            "with Thee for ever", "with Thee in the unity of the Holy Ghost for ever"
        )
    elif damage == "relative":
        next(w for w in segment(core)["words"] if w["id"] == "w353")["morph"]["gender"] = "m"
    else:
        group(layer, 363)["gloss"] = "He is appeased and grants pardon"
    with pytest.raises(AssertionError):
        assert_reviewed_constructions(core, layer)
    core.clear()
    core.update(saved_core)
    layer.clear()
    layer.update(saved_layer)
    assert_reviewed_constructions(core, layer)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_preservation_pins_reject_unrelated_edits_then_restore(language):
    layer = read(f"languages/{language}/" + RELATIVE)
    check = assert_preserved_polish if language == "pl" else assert_preserved_english
    saved = deepcopy(layer)
    check(layer)
    layer["segments"]["s001"]["translation"] += " Changed."
    with pytest.raises(AssertionError):
        check(layer)
    layer.clear()
    layer.update(saved)
    check(layer)

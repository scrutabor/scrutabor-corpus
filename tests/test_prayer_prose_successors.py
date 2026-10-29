"""Prayer prose ledger successors with finite English referents and healthy captions."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from english_possessive_successor_fixture import (
    before_short_possessive_bytes,
    before_short_possessive_caption_frame,
)
from prayer_prose_successor_fixture import AFTER, BEFORE, DATA, SITES, before_prayer_prose_ledger
from requiem_successor_fixture import before_requiem_bytes, before_requiem_ledger

from build_reader import store
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
POSTCOMMUNION = "proprium.dominica-ii-post-pentecosten-postcommunio"
ANIMA = "orationes.anima-christi"
CONCLUSION = (
    "Through our Lord Jesus Christ, Your Son, who lives and reigns with You in the "
    "unity of the Holy Spirit, God, forever and ever."
)
ADDRESS_CASES = (
    ("s07", "w028", 1, "Your"),
    ("s08", "w037", 8, "You."),
    ("s11", "w054", 5, "You,"),
    ("s12", "w060", 4, "You"),
    ("s12", "w058", 6, "Your"),
)
POSTCOMMUNION_FAULTS = (
    "old-dangling",
    "fruit-receives",
    "gifts-replace-salvation",
    "frequency-lost",
    "conclusion-addressee",
)
CONTEXT_FAULTS = (
    "petitioners-person",
    "growing-subject-case",
    "Jesus-vocative",
    "human-petitioner",
)
ROW_FAULTS = ("source", "target", "origin", "review", "familiar", "extra")
ALL_SITES = (*SITES["en"], *SITES["pl"])
LEDGER_CASES = [(site, fault) for site in ALL_SITES for fault in ROW_FAULTS]
WHOLE_LEDGER_CASES = [
    (language, fault)
    for language in ("pl", "en")
    for fault in ("unrelated-row", "top-level-extra", "duplicate-site", "missing-site")
]


def load(text, language="en"):
    return store.core(ROOT, text), store.raw_layer(ROOT, language, text)


def healthy(core, layer):
    assert language_packs.check_core(core) == []
    category, name = core["id"].split(".", 1)
    path = ROOT / "languages" / layer["language"] / "texts" / category / f"{name}.json"
    assert language_packs.check_layer(core, layer, path) == []
    assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []


def latin_context(core):
    text = core["id"]
    words = {w["id"]: w for segment in core["segments"] for w in segment.get("words", [])}
    assert [[key, word["form"]] for key, word in words.items()] == DATA["texts"][text]["words"], (
        "Latin prayer context"
    )
    if text == POSTCOMMUNION:
        assert len(words) == 35, "Latin prayer context"
        for word in ("w001", "w002", "w003"):
            assert words[word]["morph"]["case"] == "abl", "Latin prayer context"
        assert words["w001"]["head"] == words["w003"]["head"] == "w002", "Latin prayer context"
        assert words["w001"]["morph"]["voice"] == "pass", "Latin prayer context"
        assert words["w004"]["morph"]["person"] == 1, "Latin prayer context"
        assert words["w004"]["morph"]["number"] == "pl", "Latin prayer context"
        assert words["w005"]["morph"]["case"] == "voc", "Latin prayer context"
        assert words["w007"]["head"] == "w008", "Latin prayer context"
        assert words["w008"]["morph"]["case"] == "abl", "Latin prayer context"
        assert words["w009"]["morph"]["case"] == "gen", "Latin prayer context"
        assert words["w010"]["morph"]["mood"] == "subj", "Latin prayer context"
        assert words["w010"]["morph"]["number"] == "sg", "Latin prayer context"
        assert words["w013"]["morph"]["case"] == "nom", "Latin prayer context"
        assert words["w013"]["morph"]["number"] == "sg", "Latin prayer context"
        assert words["w011"]["morph"]["case"] == "gen", "Latin prayer context"
        assert words["w012"]["morph"]["case"] == "gen", "Latin prayer context"
        assert core["segments"][0]["speaker"] == "sacerdos", "Latin prayer context"
        assert core["segments"][1]["speaker"] == "minister", "Latin prayer context"
        assert core["segments"][0]["voice"] == core["segments"][1]["voice"] == "clara", (
            "Latin prayer context"
        )
        assert words["w021"]["morph"]["case"] == "nom", "Latin prayer context"
        for word in ("w023", "w025"):
            assert words[word]["morph"]["person"] == 3, "Latin prayer context"
    else:
        assert text == ANIMA and len(words) == 64, "Latin prayer context"
        assert words["w024"]["morph"]["case"] == "voc", "Latin prayer context"
        assert words["w025"]["morph"]["person"] == 2, "Latin prayer context"
        assert words["w026"]["form"] == "me", "Latin prayer context"
        expected = {"w028": "tua", "w037": "te", "w054": "te", "w058": "tuis", "w060": "te"}
        assert {key: words[key]["form"] for key in expected} == expected, "Latin prayer context"
    return words


def meaning(core, layer):
    words = latin_context(core)
    if core["id"] == POSTCOMMUNION:
        prose = layer["segments"]["s01"]["translation"]
        assert prose.startswith("Having received the sacred gifts, we beseech You, Lord, that "), (
            "received gifts have human controller"
        )
        assert "the fruit of our salvation may grow" in prose, "saving fruit is growing subject"
        assert "with our frequent participation in this mystery." in prose, (
            "frequency and mystery are retained"
        )
        assert prose.endswith(CONCLUSION), "Son and Father conclusion"
    else:
        assert core["id"] == ANIMA
        assert words["w024"]["form"] == "Iesu", "Christ is addressed"
        for segment, word, position, expected in ADDRESS_CASES:
            actual = layer["segments"][segment]["translation"].split()[position]
            assert actual == expected, f"direct divine case {word}"
            caption_layer = layer
            if word == "w058":
                relative = f"languages/en/texts/{ANIMA.replace('.', '/', 1)}.json"
                caption_layer = before_short_possessive_caption_frame(
                    relative, layer, f"direct divine caption {word}"
                )
            assert caption_layer["words"][word]["gloss"] == expected.rstrip(".,"), (
                f"direct divine caption {word}"
            )
    actual = {sid: segment["translation"] for sid, segment in layer["segments"].items()}
    assert actual == DATA["texts"][core["id"]]["segments_after"], "complete reviewed prose"


def restore(value, snapshot):
    value.clear()
    value.update(deepcopy(snapshot))


def native_ledger(language):
    ledger = json.loads((ROOT / DATA["ledgers"][language]["relative"]).read_bytes())
    for change in DATA["ledgers"][language]["rows"]:
        (row,) = [row for row in ledger["sites"] if row["site"] == change["site"]]
        core, layer = load(row["text"], language)
        healthy(core, layer)
        if language == "en":
            meaning(core, layer)
        (segment,) = [segment for segment in core["segments"] if segment["id"] == row["segment"]]
        assert row == change["after"]
        assert row["source_sha256"] == canonical_hash(source_payload(segment))
        assert row["target_sha256"] == canonical_hash(
            layer["segments"][row["segment"]]["translation"]
        )
    return ledger


@pytest.mark.parametrize("text", [POSTCOMMUNION, ANIMA], ids=["postcommunion", "anima"])
def test_reviewed_prose_has_native_and_complete_latin_context(text):
    core, layer = load(text)
    healthy(core, layer)
    meaning(core, layer)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_valid_reception_converb_controllers_remain(language):
    core, layer = load(POSTCOMMUNION, language)
    healthy(core, layer)
    words = latin_context(core)
    assert words["w004"]["morph"]["person"] == 1
    assert (
        layer["words"]["w001"]["gloss"] == {"pl": "Przyjąwszy", "en": "Having received"}[language]
    )
    assert layer["words"]["w004"]["gloss"] == {"pl": "prosimy", "en": "we beseech"}[language]
    assert not any(
        "w001" in group["words"]
        for segment in layer["segments"].values()
        for group in segment.get("alignments", [])
    )


@pytest.mark.parametrize("fault", POSTCOMMUNION_FAULTS)
def test_schema_valid_postcommunion_fault_is_rejected_and_recovers(fault):
    core, layer = load(POSTCOMMUNION)
    snapshot = deepcopy(layer)
    healthy(core, layer)
    meaning(core, layer)
    prose = layer["segments"]["s01"]["translation"]
    try:
        if fault == "old-dangling":
            changed = DATA["texts"][POSTCOMMUNION]["segments_before"]["s01"]
        elif fault == "fruit-receives":
            changed = prose.replace("Having received the sacred gifts, we", "We", 1).replace(
                "that the fruit", "that having received the sacred gifts, the fruit", 1
            )
        elif fault == "gifts-replace-salvation":
            changed = prose.replace("fruit of our salvation", "fruit of our gifts", 1)
        elif fault == "frequency-lost":
            changed = prose.replace("frequent participation", "participation", 1)
        else:
            assert fault == "conclusion-addressee"
            changed = prose.replace(
                "who lives and reigns with You", "You live and reign with Him", 1
            )
        layer["segments"]["s01"]["translation"] = changed
        assert layer != snapshot
        healthy(core, layer)
        with pytest.raises(AssertionError):
            meaning(core, layer)
    finally:
        restore(layer, snapshot)
    assert layer == snapshot
    healthy(core, layer)
    meaning(core, layer)


@pytest.mark.parametrize("fault", CONTEXT_FAULTS)
def test_latin_referent_fault_is_rejected_and_recovers(fault):
    text = POSTCOMMUNION if fault in CONTEXT_FAULTS[:2] else ANIMA
    core, layer = load(text)
    snapshot = deepcopy(core)
    healthy(core, layer)
    meaning(core, layer)
    words = {w["id"]: w for segment in core["segments"] for w in segment.get("words", [])}
    try:
        if fault == "petitioners-person":
            words["w004"]["morph"]["person"] = 2
        elif fault == "growing-subject-case":
            words["w013"]["morph"]["case"] = "acc"
        elif fault == "Jesus-vocative":
            words["w024"]["morph"]["case"] = "acc"
        else:
            assert fault == "human-petitioner"
            words["w026"]["form"] = "te"
        assert core != snapshot
        with pytest.raises(AssertionError, match=r"^Latin prayer context(?:\n|$)"):
            meaning(core, layer)
    finally:
        restore(core, snapshot)
    assert core == snapshot
    healthy(core, layer)
    meaning(core, layer)


@pytest.mark.parametrize(
    "segment,word,position,expected",
    ADDRESS_CASES,
    ids=["w028-Your", "w037-You", "w054-You", "w060-You", "w058-Your"],
)
def test_each_direct_divine_case_fault_recovers_same_segment(segment, word, position, expected):
    core, layer = load(ANIMA)
    record = layer["segments"][segment]
    snapshot = deepcopy(record)
    whole = deepcopy(layer)
    healthy(core, layer)
    meaning(core, layer)
    try:
        tokens = record["translation"].split()
        assert tokens[position] == expected
        tokens[position] = expected[0].lower() + expected[1:]
        record["translation"] = " ".join(tokens)
        assert layer != whole
        healthy(core, layer)
        with pytest.raises(AssertionError, match=rf"^direct divine case {word}(?:\n|$)"):
            meaning(core, layer)
    finally:
        restore(record, snapshot)
    assert layer["segments"][segment] is record
    assert layer == whole
    healthy(core, layer)
    meaning(core, layer)


def test_anima_formula_about_and_inherited_source_decisions_are_kept():
    core, layer = load(ANIMA)
    healthy(core, layer)
    meaning(core, layer)
    assert layer["segments"]["s13"]["translation"] == "for ever and ever. Amen."
    assert layer.get("about") == DATA["texts"][ANIMA]["about"]
    relationships = store.translation_relationships(ROOT, "en")
    assert all(
        relationships[f"{ANIMA}.{sid}.en"] == "revised" for sid in ("s07", "s08", "s11", "s12")
    )
    uses = json.loads((ROOT / "languages/en/bibliography.json").read_bytes())["uses"]
    decisions = {use["id"]: use["decision"] for use in uses}
    assert decisions["use.en.6cbf3a9a9e7a1bca2242"] == "RETAIN"
    assert decisions["use.en.709d513aee4248ad24fa"] == "REMOVE"


def test_exact_layer_and_ledger_byte_inverses_preserve_every_other_field():
    for relative, expected in DATA["unchanged"].items():
        actual_raw = (ROOT / relative).read_bytes()
        comparison_raw = before_requiem_bytes(relative, actual_raw)
        assert hashlib.sha256(comparison_raw).hexdigest() == expected
    for rule in DATA["texts"].values():
        actual_raw = (ROOT / rule["layer"]).read_bytes()
        raw = before_short_possessive_bytes(rule["layer"], actual_raw)
        assert hashlib.sha256(raw).hexdigest() == rule["after_sha256"]
        comparison = raw
        for operation in reversed(rule["operations"]):
            before = json.dumps(operation["before"], ensure_ascii=False).encode()
            after = json.dumps(operation["after"], ensure_ascii=False).encode()
            assert comparison.count(after) == 1
            comparison = comparison.replace(after, before, 1)
        assert hashlib.sha256(comparison).hexdigest() == rule["before_sha256"]
        if rule["layer"].endswith("/anima-christi.json"):
            assert len(raw) == len(comparison)
            differences = [
                (old, new) for old, new in zip(comparison, raw, strict=True) if old != new
            ]
            assert differences == [(ord("y"), ord("Y"))] * 5
        assert (ROOT / rule["layer"]).read_bytes() == actual_raw
    polish = DATA["polish_row_subject"]
    comparison = raw = (ROOT / polish["layer"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == polish["after_sha256"]
    for operation in reversed(polish["literal_operations"]):
        before, after = operation["before"].encode(), operation["after"].encode()
        assert comparison.count(after) == 1
        comparison = comparison.replace(after, before, 1)
    assert hashlib.sha256(comparison).hexdigest() == polish["before_sha256"]
    for ledger_rule in DATA["ledgers"].values():
        actual_raw = (ROOT / ledger_rule["relative"]).read_bytes()
        raw = before_requiem_bytes(ledger_rule["relative"], actual_raw)
        assert hashlib.sha256(raw).hexdigest() == ledger_rule["after_sha256"]
        comparison = raw
        for change in reversed(ledger_rule["rows"]):
            before, after = change["before_raw"].encode(), change["after_raw"].encode()
            assert json.loads(before) == change["before"] and json.loads(after) == change["after"]
            assert comparison.count(after) == 1
            comparison = comparison.replace(after, before, 1)
        assert hashlib.sha256(comparison).hexdigest() == ledger_rule["before_sha256"]


@pytest.mark.parametrize("site", ALL_SITES)
def test_each_working_row_binds_actual_native_source_and_target(site):
    language = site.rsplit(".", 1)[1]
    ledger = native_ledger(language)
    (row,) = [row for row in ledger["sites"] if row["site"] == site]
    assert row["review"] == "working" and row["familiar_core"] is False


@pytest.mark.parametrize(
    "site,fault", LEDGER_CASES, ids=[f"{site}-{fault}" for site, fault in LEDGER_CASES]
)
def test_exact_row_inverse_rejects_each_field_and_recovers_same_row(site, fault):
    language = site.rsplit(".", 1)[1]
    relative = DATA["ledgers"][language]["relative"]
    ledger = native_ledger(language)
    whole = deepcopy(ledger)
    (row,) = [row for row in ledger["sites"] if row["site"] == site]
    snapshot = deepcopy(row)
    expected = before_prayer_prose_ledger(relative, ledger)
    try:
        if fault in ("source", "target"):
            row[f"{fault}_sha256"] = "0" * 64
        elif fault == "origin":
            row["origin"] = "public-domain" if row["origin"] == "own" else "own"
        elif fault == "review":
            row["review"] = "internally-reviewed"
        elif fault == "familiar":
            row["familiar_core"] = True
        else:
            assert fault == "extra"
            row["unexpected"] = True
        assert ledger != whole
        with pytest.raises(AssertionError, match=r"^prayer prose ledger$"):
            before_prayer_prose_ledger(relative, ledger)
    finally:
        restore(row, snapshot)
    assert ledger == whole and any(value is row for value in ledger["sites"])
    assert before_prayer_prose_ledger(relative, ledger) == expected


@pytest.mark.parametrize(
    "language,fault",
    WHOLE_LEDGER_CASES,
    ids=[f"{language}-{fault}" for language, fault in WHOLE_LEDGER_CASES],
)
def test_whole_ledger_drift_is_rejected_and_recovers(language, fault):
    relative = DATA["ledgers"][language]["relative"]
    ledger = native_ledger(language)
    whole = deepcopy(ledger)
    expected = before_prayer_prose_ledger(relative, ledger)
    try:
        if fault == "unrelated-row":
            unrelated = next(row for row in ledger["sites"] if row["site"] not in ALL_SITES)
            unrelated["review"] = "expert-reviewed"
        elif fault == "top-level-extra":
            ledger["unexpected"] = True
        elif fault == "duplicate-site":
            selected = next(row for row in ledger["sites"] if row["site"] == SITES[language][0])
            ledger["sites"].append(deepcopy(selected))
        else:
            assert fault == "missing-site"
            ledger["sites"] = [row for row in ledger["sites"] if row["site"] != SITES[language][0]]
        assert ledger != whole
        with pytest.raises(AssertionError, match=r"^inherited ledger diagnostic$"):
            before_prayer_prose_ledger(relative, ledger, "inherited ledger diagnostic")
    finally:
        restore(ledger, whole)
    assert ledger == whole
    assert before_prayer_prose_ledger(relative, ledger) == expected


@pytest.mark.parametrize("language", ["pl", "en"])
def test_exact_row_inverse_preserves_complete_prior_ledger_and_native_input(language):
    relative = f"languages/{language}/translation-provenance.json"
    ledger = native_ledger(language)
    snapshot = deepcopy(ledger)
    comparison = before_prayer_prose_ledger(relative, ledger)
    assert comparison is not ledger and ledger == snapshot
    assert canonical_hash(before_requiem_ledger(relative, ledger)) == AFTER[language]
    assert canonical_hash(comparison) == BEFORE[language]

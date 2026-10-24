"""Source-bounded Precious Blood prayer and its complete bilingual reading."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import test_english_gloss_register as captions
import test_english_register as register

from build_reader import bibliography
from build_reader.bibliography_bindings import (
    collation_subject,
    digest,
    selected_text,
    validate_bindings,
    witness_subject,
)
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear
from checks.collate import collate, load_witness
from checks.translation_provenance import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "tests/fixtures/precious-blood-regression.json").read_text())
TEXT = DATA["text"]
RELATIVE = TEXT.replace(".", "/", 1) + ".json"


def read(path):
    return json.loads(path.read_text())


def layers():
    return (
        read(ROOT / "texts" / RELATIVE),
        read(ROOT / "languages/pl/texts" / RELATIVE),
        read(ROOT / "languages/en/texts" / RELATIVE),
    )


def complete_reading(core, pl, en):
    """Pin this adjudicated prayer, not a global rule about tense or translation."""
    assert [s["id"] for s in core["segments"]] == ["s01", "s02"]
    words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    assert list(words) == [f"w{i:03}" for i in range(1, 39)]
    assert words["w011"]["morph"]["number"] == "pl"
    assert words["w018"]["morph"]["number"] == "sg"
    assert words["w023"]["head"] == "w019"
    assert {k: words["w023"]["morph"][k] for k in ("case", "gender", "number")} == {
        "case": "gen",
        "gender": "f",
        "number": "sg",
    }
    assert words["w015"]["morph"]["mood"] == "subj"
    for wid in ("w026", "w028"):
        assert words[wid]["morph"]["person"] == 3
    assert pl["segments"]["s01"]["translation"] == DATA["pl_full_translation"]
    assert pl["words"]["w006"]["gloss"] == DATA["pl_gloss"]
    assert en["segments"]["s01"]["translation"] == DATA["en_full_translation"]
    assert en["segments"]["s01"]["alignments"] == DATA["en_groups"]
    assert en["words"]["w011"]["gloss"] == "the fountains"
    assert en["words"]["w024"]["gloss"] == "Who"
    assert en["words"]["w025"]["gloss"] == "with You"
    assert en["words"]["w026"]["gloss"] == "lives"
    assert en["words"]["w028"]["gloss"] == "reigns"
    for layer in (pl, en):
        assert set(layer["words"]) == set(words)
        assert layer["segments"]["s02"]["translation"] == "Amen."
        for group in layer["segments"]["s01"].get("alignments", []):
            assert group["anchor"] in group["words"]
            assert all("gloss" not in layer["words"][wid] for wid in group["words"])
        assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
    assert captions.diagnostics(TEXT, core, en) == []
    assert register.stale(en["segments"]["s01"]["translation"]) is False


def exact_source_inventory(graph):
    """An explicit inspected inventory is needed; hashes cannot infer its absence."""
    mr = next(w for w in graph["witnesses"] if w["id"] == DATA["mr_witness"]["id"])
    assert mr == DATA["mr_witness"], "complete Precious-Blood source inventory"
    use = next(u for u in graph["uses"] if u["id"] == DATA["new_conclusion_use"]["id"])
    assert use == DATA["new_conclusion_use"], "exact conclusion source"
    return mr


def test_whole_actual_text_preserves_latin_and_both_complete_language_readings():
    core, pl, en = layers()
    assert digest(selected_text(core)) == DATA["selected_latin_ritual_sha256"]
    complete_reading(core, pl, en)


def test_goal_phrase_allowance_is_exact_in_content_and_source_address():
    here = TEXT + ":s01:w019+w020+w021+w022+w023"
    phrase = "of water springing up to everlasting life"
    assert captions.class_diagnostics(here, phrase, "GOAL") == []
    for wrong in (
        "of water springing up for everlasting life",
        "of water springing up into everlasting life",
        "of water springing up",
        "to",
    ):
        assert captions.class_diagnostics(here, wrong, "GOAL")
    for elsewhere in (
        TEXT + ":s01:w020",
        "proprium.sacratissimi-cordis-iesu-epistola:s06:w136",
        "ordinarium.suscipe-sancte-pater:s02:w048+w049",
    ):
        assert captions.class_diagnostics(elsewhere, phrase, "GOAL")
        for previously_supported in ("to", "for", "for salvation"):
            assert captions.class_diagnostics(elsewhere, previously_supported, "GOAL") == []


def test_real_source_subject_resolves_proper_body_expansion_and_response_inventory():
    core, _, _ = layers()
    graph, _ = bibliography.load(ROOT)
    mr = exact_source_inventory(graph)
    assert validate_bindings(ROOT, graph) == []
    digital = next(w for w in graph["witnesses"] if w["id"] == DATA["do_witness_id"])
    subjects = {w["id"]: witness_subject(ROOT, w, graph, core) for w in (mr, digital)}
    assert all(s["contract"] == "witness-review-2" for s in subjects.values())
    assert set(subjects[mr["id"]]["source_uses"]) == {mr["use"], *mr["source_dependencies"]["uses"]}
    assert subjects[digital["id"]]["raw_resolution"]["binding"]["references"] == [
        {"archive": "precious-blood", "line": 65, "text": "$Qui tecum", "target": 1}
    ]
    row = next(c for c in graph["collations"] if c["id"] == DATA["collation_id"])
    bound = collation_subject(ROOT, row, core, subjects)
    assert bound["contract"] == "collation-review-2"
    assert mr["review"] == digital["review"] == row["review"] == {"status": "pending"}
    directory = ROOT / "witnesses" / TEXT
    meta, body = load_witness(directory / "mr.txt")
    for key, value in DATA["new_mr_headers"].items():
        assert meta[key] == value
    assert len(body.split()) == 38
    assert read(directory / "apparatus.json") == DATA["apparatus"]
    errors, warnings, stats = collate(expand_core(core), directory)
    assert errors == warnings == []
    assert (stats["witnesses"], stats["partial"], stats["words"]) == (2, 0, 38)


def test_prose_remains_working_and_has_no_refreshed_archaic_allowance():
    provenance = read(ROOT / "languages/en/translation-provenance.json")
    row = next(s for s in provenance["sites"] if s["site"] == TEXT + ".s01.en")
    assert row == DATA["en_provenance"]
    assert row["target_sha256"] == canonical_hash(DATA["en_full_translation"])
    assert row["origin"] == "working-unsettled" and row["review"] == "working"
    fixture = read(ROOT / "tests/fixtures/english-register-legacy.json")
    assert all(r["text"] != TEXT for r in fixture["records"])
    _, _, en = layers()
    assert not any(register.register_changes(en, register.ALLOWANCES).values())
    bad = deepcopy(en)
    bad["segments"]["s01"]["translation"] = DATA["before_frozen_prose"]
    assert register.register_changes(bad, register.ALLOWANCES)["new"]
    assert not any(register.register_changes(en, register.ALLOWANCES).values())


@pytest.mark.parametrize(
    "fault",
    [
        "singular-springs",
        "wrong-addressee",
        "wrong-person",
        "archaic",
        "wrong-water-head",
        "wrong-participle-case",
        "group-goal",
        "duplicate-member",
        "lowercase-conclusion",
        "pl-predicate",
    ],
)
def test_semantic_and_realization_mutants_reject_then_recover(fault):
    original = layers()
    complete_reading(*original)
    core, pl, en = deepcopy(original)
    target = en["segments"]["s01"]
    if fault == "singular-springs":
        target["translation"] = target["translation"].replace(
            "Savior’s fountains", "Savior’s fountain"
        )
    elif fault == "wrong-addressee":
        target["translation"] = target["translation"].replace(
            "He lives and reigns with You", "You live and reign with Him"
        )
    elif fault == "wrong-person":
        next(w for w in core["segments"][0]["words"] if w["id"] == "w026")["morph"]["person"] = 2
    elif fault == "archaic":
        target["translation"] = target["translation"].replace(
            "lives and reigns with You", "liveth and reigneth with Thee"
        )
    elif fault == "wrong-water-head":
        next(w for w in core["segments"][0]["words"] if w["id"] == "w023")["head"] = "w018"
    elif fault == "wrong-participle-case":
        next(w for w in core["segments"][0]["words"] if w["id"] == "w023")["morph"]["case"] = "nom"
    elif fault == "group-goal":
        target["alignments"][1]["gloss"] = "of water springing up for everlasting life"
        found = captions.diagnostics(TEXT, core, en)
        assert any(s.startswith("preposition:") for s in found)
    elif fault == "duplicate-member":
        en["words"]["w020"]["gloss"] = "to"
        assert interlinear.check(expand_core(core), enrich_layer(core, en))
    elif fault == "lowercase-conclusion":
        en["words"]["w024"]["gloss"] = "who"
    else:
        pl["segments"]["s01"]["translation"] = pl["segments"]["s01"]["translation"].replace(
            "zaczerpnęliśmy", "zaczerpniemy"
        )
    with pytest.raises(AssertionError):
        complete_reading(core, pl, en)
    complete_reading(*original)


@pytest.mark.parametrize("fault", ["missing-conclusion", "missing-response", "wrong-legal-source"])
def test_declared_source_inventory_mutants_reject_then_recover(fault):
    graph, _ = bibliography.load(ROOT)
    exact_source_inventory(graph)
    bad = deepcopy(graph)
    mr = next(w for w in bad["witnesses"] if w["id"] == DATA["mr_witness"]["id"])
    if fault == "missing-conclusion":
        mr["source_dependencies"]["uses"].remove(DATA["new_conclusion_use"]["id"])
    elif fault == "missing-response":
        mr["source_dependencies"]["uses"] = [DATA["new_conclusion_use"]["id"]]
    else:
        use = next(u for u in bad["uses"] if u["id"] == DATA["new_conclusion_use"]["id"])
        use["locator"]["section"] = "RG 115 d: conclusion directed to the Son"
    with pytest.raises(AssertionError):
        exact_source_inventory(bad)
    exact_source_inventory(graph)

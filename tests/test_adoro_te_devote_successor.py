"""Adoro te devote: the shared-file additions and their exact predecessors."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from adoro_te_devote_successor_fixture import (
    DATA,
    FILES,
    GRAPH,
    before_adoro_bytes,
    before_adoro_graph,
    before_adoro_object,
    render,
)
from canon_consecration_successor_fixture import before_canon_bytes
from caption_followups_successor_fixture import FILES as FOLLOWUPS
from caption_followups_successor_fixture import before_followups_bytes
from foot_communion_successor_fixture import (
    before_foot_communion_bytes,
    before_foot_communion_graph,
    before_foot_communion_object,
)

from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
TEXT = "orationes.adoro-te-devote"
CORE = "texts/orationes/adoro-te-devote.json"
CARDS = ["gustus", "latito", "memoriale", "pelicanus", "queo", "stilla", "tuto", "velo"]
LEDGERS = [f"languages/{language}/translation-provenance.json" for language in ("pl", "en")]
CHANGES = [
    (relative, index)
    for relative in sorted(FILES)
    for index in range(len(FILES[relative]["changes"]))
]
assert (len(FILES), len(CHANGES)) == (10, 100)
# The first and the last declared change of every file.
ENDS = sorted({(r, n) for r in FILES for n in (0, len(FILES[r]["changes"]) - 1)})


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(relative):
    return json.loads((ROOT / relative).read_bytes())


def previous(relative):
    return json.loads(before_adoro_bytes(relative, (ROOT / relative).read_bytes()))


def words():
    return [word for segment in load(CORE)["segments"] for word in segment.get("words", [])]


def inserted(relative, path):
    return [
        change["insert"]
        for change in FILES[relative]["changes"]
        if "insert" in change and change["path"] == path
    ]


def test_the_fixture_names_exactly_the_changed_files_and_pins_their_bytes():
    assert DATA["base"] == "8d54aed19eaef48cd639bc11bcef425be63e3a5c"
    counts = {relative: len(rule["changes"]) for relative, rule in FILES.items()}
    assert counts == {
        "bibliography/graph.json": 11,
        "build_reader/registry/morphology.json": 2,
        "build_reader/registry/texts.json": 1,
        "languages/en/lexicon.json": 9,
        "languages/en/manifest.json": 2,
        "languages/en/translation-provenance.json": 28,
        "languages/pl/lexicon.json": 9,
        "languages/pl/manifest.json": 2,
        "languages/pl/translation-provenance.json": 28,
        "lexicon/lemmata.json": 8,
    }
    for relative, rule in FILES.items():
        raw = (ROOT / relative).read_bytes()
        assert sha(raw) == rule["after_sha256"] != rule["before_sha256"], relative
        assert sha(before_adoro_bytes(relative, raw)) == rule["before_sha256"], relative
        assert render(rule["layout"], json.loads(raw)) == raw, relative


@pytest.mark.parametrize("relative", LEDGERS)
def test_ledger_rows_are_the_whole_new_text_after_the_act_of_contrition(relative):
    language = relative.split("/")[1]
    rows = inserted(relative, ["sites"])
    sids = [f"s{n:02d}" for n in range(1, 29)]
    assert [row["site"] for row in rows] == [f"{TEXT}.{sid}.{language}" for sid in sids]
    current = load(relative)["sites"]
    first = FILES[relative]["changes"][0]["index"]
    assert [change["index"] for change in FILES[relative]["changes"]] == list(
        range(first, first + 28)
    )
    assert current[first - 1]["site"].startswith("orationes.actus-contritionis.")
    assert not current[first + 28]["site"].startswith("orationes.actus-contritionis.")
    assert current[first : first + 28] == rows
    core = load(CORE)
    layer = load(f"languages/{language}/texts/orationes/adoro-te-devote.json")
    segments = {segment["id"]: segment for segment in core["segments"]}
    assert sorted(segments) == sids
    for row, sid in zip(rows, sids, strict=True):
        assert (row["text"], row["segment"], row["language"]) == (TEXT, sid, language)
        assert (row["origin"], row["review"], row["familiar_core"]) == ("own", "working", False)
        assert row["source_sha256"] == canonical_hash(source_payload(segments[sid]))
        assert row["target_sha256"] == canonical_hash(layer["segments"][sid]["translation"])
    assert not any(row["text"] == TEXT for row in previous(relative)["sites"])


def test_graph_records_are_the_new_text_uses_witnesses_and_collation():
    uses, witnesses, collations = (
        inserted(GRAPH, [name]) for name in ("uses", "witnesses", "collations")
    )
    assert (len(uses), len(witnesses), len(collations)) == (5, 5, 1)
    use_ids = [use["id"] for use in uses]
    assert all(use_id.startswith(f"use.{TEXT}.") for use_id in use_ids)
    assert all(use["address"] == {"kind": "text", "text": TEXT} for use in uses)
    assert [witness["use"] for witness in witnesses] == use_ids
    for witness in witnesses:
        assert witness["id"] == "witness." + witness["use"].removeprefix("use.")
        assert witness["text"] == TEXT
        raw = (ROOT / f"witnesses/{TEXT}/{witness['transcription']}.txt").read_bytes()
        assert sha(raw) == witness["transcription_sha256"]
    (collation,) = collations
    assert collation["id"].startswith(f"collation.{TEXT}.") and collation["text"] == TEXT
    graph = load(GRAPH)
    for collection, rows in (("uses", uses), ("witnesses", witnesses), ("collations", collations)):
        assert [row for row in graph[collection] if TEXT in row["id"]] == rows
        assert not any(TEXT in row["id"] for row in previous(GRAPH)[collection])


def test_lexicon_cards_and_lemmata_are_the_eight_new_headwords_the_text_uses():
    used = {word["lemma"] for word in words()}
    for relative in (
        "lexicon/lemmata.json",
        "languages/pl/lexicon.json",
        "languages/en/lexicon.json",
    ):
        keys = [change["key"] for change in FILES[relative]["changes"] if "key" in change]
        assert keys == CARDS, relative
        entries, older = load(relative)["entries"], previous(relative)["entries"]
        assert all(key in entries and key not in older for key in keys), relative
        assert set(keys) <= used
        assert [key for key in entries if key not in CARDS] == list(older), relative
    assert "sapio" in used


def test_sapio_senses_change_only_where_declared():
    polish = [c for c in FILES["languages/pl/lexicon.json"]["changes"] if "key" not in c]
    english = [c for c in FILES["languages/en/lexicon.json"]["changes"] if "key" not in c]
    assert polish == [
        {"path": ["entries", "sapio", "senses", 2], "before": "poznawać", "after": "smakować"}
    ]
    assert english == [
        {"path": ["entries", "sapio", "senses"], "index": 3, "insert": "to taste of, have a flavor"}
    ]
    pl_now, pl_then = (
        value["entries"]["sapio"]["senses"]
        for value in (load("languages/pl/lexicon.json"), previous("languages/pl/lexicon.json"))
    )
    assert pl_now[:2] + pl_now[3:] == pl_then[:2] + pl_then[3:] and len(pl_now) == len(pl_then)
    en_now, en_then = (
        value["entries"]["sapio"]["senses"]
        for value in (load("languages/en/lexicon.json"), previous("languages/en/lexicon.json"))
    )
    assert en_now[:3] == en_then and len(en_now) == 4


@pytest.mark.parametrize("language", ["pl", "en"])
def test_manifest_lists_and_titles_the_text_once(language):
    relative = f"languages/{language}/manifest.json"
    manifest, older = load(relative), previous(relative)
    assert manifest["texts"].count(TEXT) == 1 and TEXT not in older["texts"]
    position = manifest["texts"].index(TEXT)
    assert manifest["texts"][position - 1] == "orationes.actus-contritionis"
    assert [text for text in manifest["texts"] if text != TEXT] == older["texts"]
    assert manifest["titles"][TEXT]["title"] == "Adoro te devote"
    assert TEXT not in older["titles"]
    assert {key: value for key, value in manifest["titles"].items() if key != TEXT} == (
        older["titles"]
    )


def test_registries_append_the_text_and_its_two_new_parses():
    texts, older_texts = (
        load("build_reader/registry/texts.json"),
        previous("build_reader/registry/texts.json"),
    )
    assert texts == [*older_texts, TEXT]
    parses = load("build_reader/registry/morphology.json")
    older_parses = previous("build_reader/registry/morphology.json")
    added = inserted("build_reader/registry/morphology.json", [])
    assert parses == [*older_parses, *added] and len(added) == 2
    morphs = [word["morph"] for word in words()]
    for parse in added:
        assert parse in morphs and parse not in older_parses
        assert (parse["mood"], parse["voice"]) == ("part", "dep")


@pytest.mark.parametrize("relative", sorted(FILES))
def test_every_changed_file_inverts_to_its_exact_predecessor(relative):
    raw = (ROOT / relative).read_bytes()
    value = json.loads(raw)
    saved = deepcopy(value)
    previous_raw = before_adoro_bytes(relative, raw)
    older = before_adoro_object(relative, value)
    assert older == json.loads(previous_raw) and value == saved and older is not value
    assert render(FILES[relative]["layout"], older) == previous_raw
    assert before_adoro_bytes(relative, previous_raw) is previous_raw
    assert before_adoro_object(relative, older) is older, "a chain may reach it twice"
    assert before_adoro_bytes(relative, raw + b" ") == raw + b" "
    assert before_adoro_bytes(relative, b"not json") == b"not json"
    if relative == GRAPH:
        assert before_adoro_graph(value) == older
    assert (ROOT / relative).read_bytes() == raw, "the actual source is never rewritten"


def damage(value, change, how):
    """A copy where one declared change is missing, altered or moved."""
    damaged = deepcopy(value)
    if "insert" not in change:
        container, place = damaged, change["path"]
        for step in place[:-1]:
            container = container[step]
        container[place[-1]] = "fault" if how != "missing" else change["before"]
        return damaged
    container = damaged
    for step in change["path"]:
        container = container[step]
    if "key" in change:
        if how == "missing":
            del container[change["key"]]
        elif how == "altered":
            container[change["key"]] = {"fault": True}
        else:
            moved = container.pop(change["key"])
            container[change["key"] + "-moved"] = moved
        return damaged
    index = change["index"]
    if how == "missing":
        del container[index]
    elif how == "altered":
        container[index] = (
            {**container[index], "fault": True} if isinstance(container[index], dict) else "fault"
        )
    else:
        container.insert(index, container.pop(index - 1 if index else index + 1))
    return damaged


@pytest.mark.parametrize(("relative", "number"), ENDS)
@pytest.mark.parametrize("how", ["missing", "altered", "moved"])
def test_a_partial_or_altered_addition_stays_whole_for_the_older_oracle(relative, number, how):
    change = FILES[relative]["changes"][number]
    value = load(relative)
    damaged = damage(value, change, how)
    assert damaged != value
    assert before_adoro_object(relative, damaged) is damaged
    layout = FILES[relative]["layout"]
    raw = render(layout, damaged)
    assert before_adoro_bytes(relative, raw) is raw
    if relative == GRAPH:
        assert before_adoro_graph(damaged) is damaged


@pytest.mark.parametrize("relative", sorted(FILES))
def test_every_other_field_is_preserved_with_a_fault_elsewhere(relative):
    value = load(relative)
    older = previous(relative)
    faulty = deepcopy(value)
    if isinstance(faulty, list):
        faulty[0] = {"fault": True} if isinstance(faulty[0], dict) else "fault"
        expected = deepcopy(older)
        expected[0] = faulty[0]
    else:
        faulty["unexpected"] = True
        expected = {**deepcopy(older), "unexpected": True}
    result = before_adoro_object(relative, faulty)
    assert result == expected and result is not faulty


def test_unrelated_values_pass_through_untouched():
    relative = "languages/en/texts/orationes/pater-noster.json"
    raw = (ROOT / relative).read_bytes()
    value = json.loads(raw)
    assert relative not in FILES
    assert before_adoro_bytes(relative, raw) is raw
    assert before_adoro_object(relative, value) is value
    for new in (CORE, f"witnesses/{TEXT}/mr.txt"):
        assert new not in FILES
        assert before_adoro_bytes(new, (ROOT / new).read_bytes()) == (ROOT / new).read_bytes()


@pytest.mark.parametrize("relative", sorted(FILES))
def test_the_chain_entries_reach_this_predecessor_first(relative):
    """The foot of the altar and Canon entries treat the current file as its predecessor."""
    raw = (ROOT / relative).read_bytes()
    previous_raw = before_adoro_bytes(relative, raw)
    assert previous_raw != raw
    for entry in (before_foot_communion_bytes, before_canon_bytes):
        assert entry(relative, raw) == entry(relative, previous_raw)
    value = json.loads(raw)
    assert before_foot_communion_object(relative, value) == before_foot_communion_object(
        relative, json.loads(previous_raw)
    )


@pytest.mark.parametrize("relative", sorted(set(FILES) & set(FOLLOWUPS)))
def test_the_older_caption_successor_runs_after_this_one(relative):
    raw = (ROOT / relative).read_bytes()
    alone = before_followups_bytes(relative, raw)
    assert sha(alone) != FOLLOWUPS[relative]["before_sha256"], "the new rows are foreign to it"
    older = before_followups_bytes(relative, before_adoro_bytes(relative, raw))
    assert sha(older) == FOLLOWUPS[relative]["before_sha256"]


def test_the_graph_entry_reaches_this_predecessor_first():
    graph = load(GRAPH)
    saved = deepcopy(graph)
    assert before_foot_communion_graph(graph) == before_foot_communion_graph(previous(GRAPH))
    assert graph == saved

"""English possessive sweep B1: shared captions, kept controls and exact predecessors."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from possessive_sweep_b1_successor_fixture import (
    DATA,
    FILES,
    before_possessive_b1_bytes,
    before_possessive_b1_layer,
    before_possessive_b1_layer_frame,
    before_possessive_b1_object,
    possessive_b1_caption,
    possessive_b1_group,
    possessive_b1_groups,
    possessive_b1_realization,
)

from build_reader import store
from build_reader.layers import enrich_layer, expand_core
from checks import english, interlinear, interlinear_quality, prose

ROOT = Path(__file__).resolve().parents[1]
GROUPS = [(relative, change) for relative in sorted(FILES) for change in FILES[relative]["groups"]]
CONTROLS = DATA["controls"]
PROTECTED = DATA["protected_skipped"]
POSSESSIVES = frozenset({"meus", "tuus", "suus", "noster", "vester"})
DIAGNOSTIC = "possessive B1 caption"
assert (len(FILES), len(GROUPS), len(CONTROLS), len(PROTECTED)) == (43, 142, 11, 41)
assert sum(len(change["group"]["words"]) > 2 for _relative, change in GROUPS) == 19


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def core(text):
    return store.core(ROOT, text)


def layer(relative):
    return json.loads((ROOT / relative).read_bytes())


def segment_words(doc, segment):
    return next(row for row in doc["segments"] if row["id"] == segment)["words"]


def require(condition):
    if not condition:
        raise AssertionError(DIAGNOSTIC)


def assert_group(doc, value, change):
    """The declared shared caption stands once, alone over its words, on its exact cards."""
    group = change["group"]
    groups = interlinear.alignments_for(value, change["segment"])
    require(groups.count(group) == 1)
    touching = [row for row in groups if set(row["words"]) & set(group["words"])]
    require(touching == [group])
    for word, entry in change["after_entries"].items():
        require(value["words"].get(word) == entry and "gloss" not in entry)
    words = [word["id"] for word in segment_words(doc, change["segment"])]
    start = words.index(group["words"][0])
    require(words[start : start + len(group["words"])] == group["words"])


def test_successor_names_exactly_the_changed_files_and_pins_their_bytes():
    assert len({change["row"] for _relative, change in GROUPS}) == len(GROUPS)
    for relative, rule in FILES.items():
        assert relative == f"languages/en/texts/{rule['text'].replace('.', '/', 1)}.json"
        raw = (ROOT / relative).read_bytes()
        assert sha(raw) == rule["after_sha256"], relative
        assert rule["before_sha256"] != rule["after_sha256"]


@pytest.mark.parametrize(
    ("relative", "change"), GROUPS, ids=[f"row{change['row']}" for _r, change in GROUPS]
)
def test_shared_caption_covers_noun_and_its_agreeing_possessive(relative, change):
    rule = FILES[relative]
    doc = core(rule["text"])
    value = layer(relative)
    assert_group(doc, value, change)
    words = {word["id"]: word for word in segment_words(doc, change["segment"])}
    group = change["group"]
    assert [words[word]["form"] for word in group["words"]] == change["latin"]
    possessives = [word for word in group["words"] if words[word].get("lemma") in POSSESSIVES]
    assert possessives == [change["possessive"]]
    possessive = words[change["possessive"]]
    head = words[possessive["head"]]
    assert possessive["head"] in group["words"] and head["morph"]["pos"] == "noun"
    for feature in ("case", "number", "gender"):
        assert possessive["morph"][feature] == head["morph"][feature]
    assert words[group["anchor"]]["morph"]["pos"] == "noun"
    assert group["gloss"] == change["gloss"] and group["gloss"] == group["gloss"].strip()
    assert value["segments"][change["segment"]]["translation"] == change["translation"]
    for word, entry in change["before_entries"].items():
        assert entry.get("gloss"), "every grouped word had its own caption"
        assert {key: item for key, item in entry.items() if key != "gloss"} == (
            change["after_entries"][word]
        )


@pytest.mark.parametrize(
    ("relative", "change"), GROUPS, ids=[f"row{change['row']}" for _r, change in GROUPS]
)
def test_the_earlier_split_captions_are_rejected(relative, change):
    rule = FILES[relative]
    doc = core(rule["text"])
    value = layer(relative)
    saved = deepcopy(value)
    split = deepcopy(value)
    split["segments"][change["segment"]]["alignments"].remove(change["group"])
    for word, entry in change["before_entries"].items():
        split["words"][word] = deepcopy(entry)
    with pytest.raises(AssertionError, match=rf"^{DIAGNOSTIC}$"):
        assert_group(doc, split, change)
    wrong = deepcopy(value)
    groups = wrong["segments"][change["segment"]]["alignments"]
    groups[groups.index(change["group"])]["gloss"] += " also"
    with pytest.raises(AssertionError, match=rf"^{DIAGNOSTIC}$"):
        assert_group(doc, wrong, change)
    assert value == saved


def test_wordings_rejected_by_the_challenge_stay_rejected():
    rejected = {change["row"]: change for _relative, change in GROUPS if change["rejected_glosses"]}
    assert {row: change["rejected_glosses"] for row, change in rejected.items()} == {
        74: ["Your Body and Blood"],
        103: ["Your servants and handmaids"],
    }
    assert rejected[74]["gloss"] == "Body and Blood of Yours"
    assert rejected[103]["gloss"] == "of Your servants and handmaids"
    for relative, change in GROUPS:
        if not change["rejected_glosses"]:
            continue
        doc, value = core(FILES[relative]["text"]), layer(relative)
        assert_group(doc, value, change)
        for wrong in change["rejected_glosses"]:
            earlier = deepcopy(value)
            groups = earlier["segments"][change["segment"]]["alignments"]
            groups[groups.index(change["group"])]["gloss"] = wrong
            with pytest.raises(AssertionError, match=rf"^{DIAGNOSTIC}$"):
                assert_group(doc, earlier, change)
            # The earlier wording is not the declared group: it stays for the older oracle.
            kept = before_possessive_b1_object(relative, earlier)["segments"][change["segment"]]
            assert {**change["group"], "gloss": wrong} in kept["alignments"]
        previous = before_possessive_b1_object(relative, value)["segments"][change["segment"]]
        assert change["group"] not in previous.get("alignments", [])


@pytest.mark.parametrize("relative", sorted(FILES))
def test_every_touched_layer_stays_healthy(relative):
    text = FILES[relative]["text"]
    doc, value = core(text), store.raw_layer(ROOT, "en", text)
    assert interlinear.check(doc, value) == []
    assert prose.check(value) == []
    expanded, target = expand_core(doc), enrich_layer(doc, value)
    assert english.check(expanded, target) == []
    assert interlinear_quality.check(expanded, target) == []


@pytest.mark.parametrize("row", CONTROLS + PROTECTED, ids=lambda row: f"row{row['row']}")
def test_controls_and_protected_rows_stay_split(row):
    relative = f"languages/en/texts/{row['text'].replace('.', '/', 1)}.json"
    value = layer(relative)
    words = {word["id"]: word for word in segment_words(core(row["text"]), row["segment"])}
    for word, form, gloss in row["words"]:
        assert words[word]["form"] == form
        assert value["words"][word]["gloss"] == gloss
    grouped = {
        word
        for group in interlinear.alignments_for(value, row["segment"])
        for word in group["words"]
    }
    assert not grouped & {word for word, _form, _gloss in row["words"]}
    if row["kind"] == "PROTECTED_SKIPPED":
        assert relative not in FILES


@pytest.mark.parametrize("relative", sorted(FILES))
def test_every_changed_file_inverts_to_its_exact_predecessor(relative):
    rule = FILES[relative]
    raw = (ROOT / relative).read_bytes()
    value = json.loads(raw)
    saved = deepcopy(value)
    previous_raw = before_possessive_b1_bytes(relative, raw)
    assert sha(previous_raw) == rule["before_sha256"]
    previous = before_possessive_b1_object(relative, value)
    assert previous == json.loads(previous_raw) and value == saved and previous is not value
    assert before_possessive_b1_layer(value) == previous
    assert before_possessive_b1_layer_frame(value) == previous
    assert before_possessive_b1_bytes(relative, previous_raw) is previous_raw
    assert before_possessive_b1_object(relative, previous) is previous, "a chain may reach it twice"
    assert before_possessive_b1_bytes(relative, raw + b" ") == raw + b" "
    for _relative, change in [item for item in GROUPS if item[0] == relative]:
        assert change["group"] not in previous["segments"][change["segment"]].get("alignments", [])
        for word, entry in change["before_entries"].items():
            assert previous["words"][word] == entry


@pytest.mark.parametrize("relative", sorted(FILES))
def test_a_damaged_group_stays_for_the_older_oracle(relative):
    rule = FILES[relative]
    value = layer(relative)
    first = rule["groups"][0]
    damaged = deepcopy(value)
    groups = damaged["segments"][first["segment"]]["alignments"]
    groups[groups.index(first["group"])]["gloss"] += " also"
    result = before_possessive_b1_object(relative, damaged)
    assert (
        result["segments"][first["segment"]]["alignments"].count(
            {**first["group"], "gloss": first["group"]["gloss"] + " also"}
        )
        == 1
    )
    for change in rule["groups"][1:]:
        assert change["group"] not in result["segments"][change["segment"]].get("alignments", [])
    carded = deepcopy(value)
    carded["words"][first["group"]["words"][0]]["gloss"] = "fault"
    result = before_possessive_b1_object(relative, carded)
    assert first["group"] in result["segments"][first["segment"]]["alignments"]
    raw = (ROOT / relative).read_bytes()
    assert sha(before_possessive_b1_bytes(relative, raw)) == rule["before_sha256"]


def test_unrelated_values_pass_through_untouched():
    relative = "languages/en/texts/orationes/pater-noster.json"
    raw = (ROOT / relative).read_bytes()
    value = json.loads(raw)
    assert relative not in FILES
    assert before_possessive_b1_bytes(relative, raw) is raw
    assert before_possessive_b1_object(relative, value) is value
    assert before_possessive_b1_layer(value) is value
    polish = {"language": "pl", "text": "ordinarium.lavabo", "segments": {}, "words": {}}
    assert before_possessive_b1_layer(polish) is polish
    assert before_possessive_b1_layer_frame(polish) is polish
    assert before_possessive_b1_layer({"text": 1}) == {"text": 1}


def framed_words(rule):
    return {word for change in rule["groups"] for word in change["group"]["words"]}


@pytest.mark.parametrize("relative", sorted(FILES))
def test_frame_inverse_keeps_other_card_fields_and_leaves_a_direct_gloss(relative):
    rule = FILES[relative]
    value = layer(relative)
    framed = deepcopy(value)
    for change in rule["groups"]:
        for word in change["group"]["words"]:
            framed["words"][word]["projected"] = [word]
    result = before_possessive_b1_layer_frame(framed)
    previous = json.loads(before_possessive_b1_bytes(relative, (ROOT / relative).read_bytes()))
    for change in rule["groups"]:
        assert change["group"] not in result["segments"][change["segment"]].get("alignments", [])
        for word, entry in change["before_entries"].items():
            assert result["words"][word] == {**entry, "projected": [word]}
            assert list(result["words"][word])[: len(entry)] == list(entry)
    for card in result["words"].values():
        card.pop("projected", None)
    assert result == previous
    expanded = {key: item for key, item in framed.items() if key != "language"}
    expanded["lang"] = "en"
    assert before_possessive_b1_layer_frame(expanded)["words"] == {
        word: {**card, "projected": [word]} if word in framed_words(rule) else card
        for word, card in previous["words"].items()
    }
    first = rule["groups"][0]
    glossed = deepcopy(framed)
    glossed["words"][first["group"]["words"][0]]["gloss"] = "fault"
    kept = before_possessive_b1_layer_frame(glossed)
    assert first["group"] in kept["segments"][first["segment"]]["alignments"]
    assert before_possessive_b1_layer_frame(previous) is previous


def test_site_successors_supersede_only_an_exact_earlier_one_word_caption():
    for relative, change in GROUPS:
        text = FILES[relative]["text"]
        value = layer(relative)
        group = change["group"]
        assert possessive_b1_realization(value, group["words"]) == group["gloss"]
        assert possessive_b1_groups("en", text).count(change) == 1
        for word in group["words"]:
            before = change["before_entries"][word]["gloss"]
            assert possessive_b1_group("en", text, [word], before) == change
            assert possessive_b1_caption("en", text, (word,), before) == (
                tuple(group["words"]),
                group["gloss"],
            )
            assert possessive_b1_group("pl", text, [word], before) is None
            assert possessive_b1_group("en", text, [word], before + " also") is None
            assert possessive_b1_caption("en", text, [word], "other") == ((word,), "other")
            assert possessive_b1_realization(value, [word]) is None
    assert possessive_b1_groups("pl", "ordinarium.lavabo") == []
    assert possessive_b1_groups("en", "orationes.pater-noster") == []
    pater = layer("languages/en/texts/orationes/pater-noster.json")
    assert possessive_b1_realization(pater, ["w009"]) == "Your"

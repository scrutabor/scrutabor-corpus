"""Intercession captions, apposition heads and the Lawrence Gospel prose; exact predecessors."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from adoro_te_devote_successor_fixture import before_adoro_bytes
from canon_consecration_successor_fixture import before_canon_bytes
from caption_followups_successor_fixture import (
    DATA,
    FILES,
    before_followups_bytes,
    before_followups_core,
    before_followups_core_bytes,
    before_followups_layer,
    before_followups_object,
)
from foot_communion_successor_fixture import before_foot_communion_bytes

from build_reader import store
from checks import interlinear
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
CHANGES = [
    (relative, change) for relative in sorted(FILES) for change in FILES[relative]["changes"]
]
assert (len(FILES), len(CHANGES)) == (14, 29)
P = "proprium."
JOSEPH = P + "sancti-ioseph-sponsi-beatae-mariae-virginis-postcommunio"
# (text, word): (Latin form, caption, the caption line from the intercession participle on)
CAPTIONS = {
    (P + "sancti-bartholomaei-apostoli-postcommunio", "w009"): (
        "interveniénte",
        "through the intercession of",
        "through the intercession of | blessed | Bartholomew | Your Apostle",
    ),
    (P + "sancti-lucae-evangelistae-secreta", "w015"): (
        "interveniénte",
        "through the intercession of",
        "through the intercession of | Your blessed Evangelist | Luke",
    ),
    (P + "sancti-ioachim-confessoris-postcommunio", "w010"): (
        "intercedéntibus",
        "through the interceding",
        "through the interceding | merits | and | prayers | of blessed | Joachim",
    ),
    (JOSEPH, "w007"): (
        "intercedénte",
        "through the intercession",
        "through the intercession | for | us | of blessed | Joseph | Confessor",
    ),
    (JOSEPH, "w010"): (
        "beáto",
        "of blessed",
        "through the intercession | for | us | of blessed | Joseph | Confessor",
    ),
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(relative):
    return json.loads((ROOT / relative).read_bytes())


def segment(doc, sid):
    return next(row for row in doc["segments"] if row["id"] == sid)


def caption_line(doc, layer, sid):
    """The interlinear line in Latin order: a group's caption at its first word."""
    groups = interlinear.alignments_for(layer, sid)
    shown = []
    for word in segment(doc, sid)["words"]:
        group = next((g for g in groups if word["id"] in g["words"]), None)
        if group is not None:
            if group["words"][0] == word["id"]:
                shown.append(group["gloss"])
        elif layer["words"].get(word["id"], {}).get("gloss"):
            shown.append(layer["words"][word["id"]]["gloss"])
    return " | ".join(shown)


def kinds(kind):
    return [(r, c) for r, c in CHANGES if FILES[r]["kind"] == kind]


def test_the_fixture_names_exactly_the_changed_files_and_pins_their_bytes():
    assert DATA["base"] == "d08c558e6ca959515ea0c11fe7c5d4fd8eb3eb78"
    assert {rule["kind"] for rule in FILES.values()} == {"core", "layer", "ledger"}
    assert [len(kinds(kind)) for kind in ("core", "layer", "ledger")] == [8, 6, 15]
    for relative, rule in FILES.items():
        # The file as this successor left it: the newer declared successor is undone on a copy.
        raw = before_adoro_bytes(relative, (ROOT / relative).read_bytes())
        assert sha(raw) == rule["after_sha256"] != rule["before_sha256"], relative
        assert sha(before_followups_bytes(relative, raw)) == rule["before_sha256"], relative


@pytest.mark.parametrize(("relative", "change"), kinds("layer"), ids=lambda v: str(v)[-40:])
def test_english_captions_and_prose(relative, change):
    rule = FILES[relative]
    value, doc = load(relative), store.core(ROOT, rule["text"])
    path = change["path"]
    if path[-1] == "gloss":
        word = path[1]
        form, caption, line = CAPTIONS[(rule["text"], word)]
        assert value["words"][word]["gloss"] == change["after"] == caption
        latin = {w["id"]: w for w in segment(doc, "s01")["words"]}
        assert latin[word]["form"] == form and latin[word]["morph"]["case"] == "abl"
        grouped = {w for group in interlinear.alignments_for(value, "s01") for w in group["words"]}
        assert word not in grouped, "the card gloss is the caption"
        assert line in caption_line(doc, value, "s01")
    else:
        before, after = change["before"], change["after"]
        assert value["segments"]["s01"]["translation"] == after
        assert (
            before.replace("ministers to Me", "serves Me").replace("My minister", "My servant")
            == after
        )
        assert (after.count("serves Me"), after.count("My servant")) == (2, 1)
        assert "minister" not in after
        groups = interlinear.alignments_for(value, "s01")
        assert {"words": ["w061", "w062"], "anchor": "w061", "gloss": "My servant"} in groups
        communion = load(relative.replace("-evangelium", "-communio"))
        assert "there My servant also will be" in communion["segments"]["s01"]["translation"]


@pytest.mark.parametrize(("relative", "change"), kinds("core"), ids=lambda v: str(v)[-40:])
def test_each_modifier_agrees_with_the_nearest_following_noun(relative, change):
    doc = load(relative)
    words = segment(doc, change["path"][1]["id"])["words"]
    ids = [word["id"] for word in words]
    index = ids.index(change["path"][3]["id"])
    adjective = words[index]
    if adjective["lemma"] == "beatus":
        assert adjective["morph"]["pos"] == "adj"
    else:
        # The ablative-absolute participle agrees with its subject group as its adjective does.
        assert (adjective["lemma"], adjective["morph"]["mood"]) == ("intervenio", "part")
        assert words[index + 1]["lemma"] == "beatus"
        assert words[index + 1]["head"] == change["after"]
    assert adjective["head"] == change["after"]
    nouns = [word for word in words[index + 1 :] if word["morph"]["pos"] == "noun"]
    assert nouns[0]["id"] == change["after"]
    earlier = next(word for word in words if word["id"] == change["before"])
    for noun in (nouns[0], earlier):
        for feature in ("case", "number", "gender"):
            assert noun["morph"][feature] == adjective["morph"][feature], feature
    # The earlier head stays inside the same apposition group, after the new one.
    assert ids.index(change["before"]) > ids.index(change["after"])
    assert ids.index(change["before"]) - index <= 4


def test_the_change_counts_per_ruling_class():
    cores = kinds("core")
    assert len(cores) == 8
    lemmas = []
    for relative, change in cores:
        words = segment(load(relative), change["path"][1]["id"])["words"]
        lemmas += [w["lemma"] for w in words if w["id"] == change["path"][3]["id"]]
    assert sorted(lemmas) == ["beatus"] * 7 + ["intervenio"]
    assert sorted(CAPTIONS) == sorted(
        (FILES[r]["text"], c["path"][1]) for r, c in kinds("layer") if c["path"][-1] == "gloss"
    )


@pytest.mark.parametrize(("relative", "change"), kinds("ledger"), ids=lambda v: str(v)[-60:])
def test_ledger_hashes_are_recomputed_without_a_review_change(relative, change):
    site, field = change["path"][1]["site"], change["path"][2]
    rows = [row for row in load(relative)["sites"] if row["site"] == site]
    assert len(rows) == 1
    row = rows[0]
    assert (row["origin"], row["review"], row["familiar_core"]) == (
        "working-unsettled",
        "working",
        False,
    )
    text, sid, language = site.rsplit(".", 2)
    core = load(f"texts/{text.replace('.', '/', 1)}.json")
    layer = load(f"languages/{language}/texts/{text.replace('.', '/', 1)}.json")
    if field == "source_sha256":
        assert row[field] == change["after"] == canonical_hash(source_payload(segment(core, sid)))
        older = before_followups_core(deepcopy(core))
        assert change["before"] == canonical_hash(source_payload(segment(older, sid)))
    else:
        assert field == "target_sha256"
        target = layer["segments"][sid]["translation"]
        assert row[field] == change["after"] == canonical_hash(target)
        older = before_followups_layer(layer)["segments"][sid]["translation"]
        assert change["before"] == canonical_hash(older)


@pytest.mark.parametrize("relative", sorted(FILES))
def test_every_changed_file_inverts_to_its_exact_predecessor(relative):
    raw = (ROOT / relative).read_bytes()
    value = json.loads(raw)
    saved = deepcopy(value)
    previous_raw = before_followups_bytes(relative, raw)
    previous = before_followups_object(relative, value)
    assert previous == json.loads(previous_raw) and value == saved and previous is not value
    assert before_followups_bytes(relative, previous_raw) is previous_raw
    assert before_followups_object(relative, previous) is previous, "a chain may reach it twice"
    assert before_followups_bytes(relative, raw + b" ") == raw + b" "
    rule = FILES[relative]
    if rule["kind"] == "layer":
        assert before_followups_layer(value) == previous
        framed = {key: item for key, item in value.items() if key != "language"} | {"lang": "en"}
        assert before_followups_layer(framed)["words"] == previous["words"]
    if rule["kind"] == "core":
        assert before_followups_core(value) == previous
        assert before_followups_core_bytes(rule["text"], raw) == previous_raw
    assert (ROOT / relative).read_bytes() == raw, "the actual source is never rewritten"


@pytest.mark.parametrize("relative", sorted(FILES))
def test_a_damaged_field_stays_for_the_older_oracle(relative):
    rule = FILES[relative]
    first = rule["changes"][0]
    value = load(relative)
    damaged = deepcopy(value)
    container = damaged
    for step in first["path"][:-1]:
        if isinstance(step, dict):
            ((key, wanted),) = step.items()
            container = next(row for row in container if row.get(key) == wanted)
        else:
            container = container[step]
    container[first["path"][-1]] = "fault"
    result = before_followups_object(relative, damaged)
    container = result
    for step in first["path"][:-1]:
        if isinstance(step, dict):
            ((key, wanted),) = step.items()
            container = next(row for row in container if row.get(key) == wanted)
        else:
            container = container[step]
    assert container[first["path"][-1]] == "fault"


def test_unrelated_values_pass_through_untouched():
    relative = "languages/en/texts/orationes/pater-noster.json"
    raw = (ROOT / relative).read_bytes()
    value = json.loads(raw)
    assert relative not in FILES
    assert before_followups_bytes(relative, raw) is raw
    assert before_followups_object(relative, value) is value
    assert before_followups_layer(value) is value
    assert before_followups_layer({"text": 1}) == {"text": 1}
    core = store.core(ROOT, "orationes.pater-noster")
    assert before_followups_core(core) is core
    assert before_followups_core_bytes("orationes.pater-noster", b"{}") == b"{}"


@pytest.mark.parametrize("relative", sorted(FILES))
def test_the_chain_entries_reach_this_predecessor_first(relative):
    raw = (ROOT / relative).read_bytes()
    previous_raw = before_followups_bytes(relative, raw)
    assert previous_raw != raw
    for entry in (before_foot_communion_bytes, before_canon_bytes):
        assert entry(relative, raw) == entry(relative, previous_raw)

"""Contemporary English register: future, future perfect, eternity and obsolete forms.

Ordinary future predictions read "will". A future perfect or generalizing clause reads
the English present. Eternity phrases read "forever". Obsolete verb endings and pronouns
read contemporary English, and the Passion Sunday Introit asks God to "set my cause apart
from the unholy nation". Every revised prose segment, caption, `about` and source record is
pinned and bound to the native layer, its Latin context and the provenance ledger. The
Gloria Patri formula inside two Introit segments is unchanged. One control per class shows
that the earlier wording is rejected. The retired register allowances and the exact
predecessor of every changed file stay reachable for older comparisons, and drift is
rejected. A ledger row whose target is an earlier contemporary rewording no longer claims
its previous review.
"""

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
import test_english_register as register
from english_register_successor_fixture import (
    ALLOWANCES,
    DATA,
    FILES,
    before_english_register_allowances,
    before_english_register_bytes,
    before_english_register_object,
)

from build_reader import store
from build_reader.bibliography_bindings import digest
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs, prose
from checks.translation_provenance import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
LEDGER = "languages/en/translation-provenance.json"
LEGACY = "tests/fixtures/english-register-legacy.json"
PROSE = {(row["text"], row["segment"]): row for row in DATA["prose"]}
CAPTIONS = DATA["captions"]
ABOUT = {row["text"]: row for row in DATA["about"]}
RECORDS = DATA["records"]
GLORIA_PATRI = "As it was in the beginning, is now, and ever shall be, world without end. Amen."
SHALL = re.compile(r"\b[Ss]hall\b")
# The complete reviewed successor: 28 prose segments, 194 captions, one `about`, seven
# source-record fields, two ledger rows whose review becomes working and eight allowances.
assert (len(PROSE), len(CAPTIONS), len(ABOUT), len(RECORDS)) == (28, 194, 1, 7)
PINS_SHA256 = "e1bb5d2444a85f7f5de19cd63cb6c63990423298b0b5afcc30be898db9d313ca"
assert (
    digest(
        [
            [[row["text"], row["segment"], row["after"]] for row in DATA["prose"]],
            [[row["text"], row["words"], row["after"]] for row in CAPTIONS],
            [[row["text"], row["after"]] for row in DATA["about"]],
            [[row["use"], row["field"], row["after"]] for row in RECORDS],
        ]
    )
    == PINS_SHA256
)
REVIEW_MOVED = {"orationes.agimus-tibi-gratias.s03.en", "ordinarium.simili-modo.s13.en"}
assert len(DATA["earlier_rewordings"]) == 6
# One control per class: (text, segment) whose earlier wording is restored on a copy, and
# the diagnostic it must produce.
CONTROLS = {
    "future": ("proprium.d-n-iesu-christi-regis-graduale", "s01", "predictive shall"),
    "future-perfect": ("ordinarium.simili-modo", "s13", "future perfect shall"),
    "eternity": ("orationes.agimus-tibi-gratias", "s03", "legacy eternity spacing"),
    "archaic": ("proprium.corporis-christi-evangelium", "s02", "obsolete form"),
    "calque": ("proprium.dominica-i-passionis-introitus", "s01", "cause calque"),
}
CAPTION_CONTROL = ("proprium.d-n-iesu-christi-regis-communio", ["w001"])


def load(text):
    return store.core(ROOT, text), deepcopy(store.raw_layer(ROOT, "en", text))


def healthy(core, layer):
    assert language_packs.check_core(core) == []
    category, name = core["id"].split(".", 1)
    path = ROOT / "languages/en/texts" / category / f"{name}.json"
    assert language_packs.check_layer(core, layer, path) == []
    assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
    assert prose.check(layer) == []


def latin(core, segment_id):
    (segment,) = [segment for segment in core["segments"] if segment["id"] == segment_id]
    assert segment["type"] == "verse"
    return {word["id"]: word for word in segment["words"]}


def ledger():
    path = ROOT / LEDGER
    return {row["site"]: row for row in json.loads(path.read_bytes())["sites"]}


def uses():
    path = ROOT / "languages/en/bibliography.json"
    return {use["id"]: use for use in json.loads(path.read_bytes())["uses"]}


def caption(layer, segment, words):
    groups = [
        group
        for group in layer["segments"][segment].get("alignments", [])
        if set(group["words"]) & set(words)
    ]
    if len(words) == 1 and not groups:
        return layer["words"][words[0]].get("gloss")
    if len(groups) == 1 and groups[0]["words"] == list(words):
        return groups[0]["gloss"]
    return None


def prose_errors(row, value):
    """Classify a deviation from the pinned prose by the class the change corrected."""
    if value == row["after"]:
        return []
    if "for ever" in value and "for ever" not in row["after"]:
        return ["legacy eternity spacing"]
    if register.archaic(value) and not register.archaic(row["after"]):
        return ["obsolete form"]
    if len(SHALL.findall(value)) > len(SHALL.findall(row["after"])):
        return ["future perfect shall" if "future" not in row["classes"] else "predictive shall"]
    if "distinguish" in value or "not holy" in value:
        return ["cause calque"]
    return ["revised prose"]


def caption_errors(row, value):
    if value is None:
        return ["caption shape"]
    if value == row["after"]:
        return []
    if SHALL.search(value):
        return ["predictive shall" if "future" in row["classes"] else "future perfect shall"]
    return ["revised caption"]


@pytest.mark.parametrize("key", sorted(PROSE), ids=lambda key: f"{key[0]}.{key[1]}")
def test_revised_prose_is_pinned_and_binds_its_ledger_row(key):
    text, segment = key
    row = PROSE[key]
    core, layer = load(text)
    healthy(core, layer)
    assert latin(core, segment)
    value = layer["segments"][segment]["translation"]
    assert value == row["after"]
    assert prose_errors(row, value) == []
    assert row["before"].count(GLORIA_PATRI) == value.count(GLORIA_PATRI)
    assert len(SHALL.findall(value)) <= len(SHALL.findall(row["before"]))
    assert "for ever" not in value
    site = f"{text}.{segment}.en"
    ledger_row = ledger()[site]
    assert ledger_row["target_sha256"] == canonical_hash(value) == row["target_sha256_after"]
    assert row["target_sha256_before"] == canonical_hash(row["before"])
    assert (ledger_row["origin"], ledger_row["review"]) == (
        row["origin"],
        row["review_after"],
    )
    assert ledger_row["familiar_core"] is False
    assert (row["review_before"] != row["review_after"]) is (site in REVIEW_MOVED)
    if site in REVIEW_MOVED:
        assert (row["review_before"], row["review_after"]) == (
            "internally-reviewed",
            "working",
        )


@pytest.mark.parametrize("row", CAPTIONS, ids=lambda row: f"{row['text']}.{'+'.join(row['words'])}")
def test_revised_caption_is_pinned_with_its_latin_tense(row):
    core, layer = load(row["text"])
    words = latin(core, row["segment"])
    assert " ".join(words[word]["form"] for word in row["words"]) == row["latin"]
    morphs = [
        [
            words[word].get("morph", {}).get("tense"),
            words[word].get("morph", {}).get("mood"),
        ]
        for word in row["words"]
    ]
    assert morphs == row["latin_tense_mood"]
    value = caption(layer, row["segment"], row["words"])
    assert value == row["after"]
    assert caption_errors(row, value) == []
    assert not SHALL.search(value)
    if row["classes"] == ["future-perfect"]:
        assert ["futperf", "ind"] in morphs
    if row["classes"] == ["future"]:
        assert any(tense == "fut" or mood == "subj" for tense, mood in morphs)


@pytest.mark.parametrize("text", sorted({row["text"] for row in CAPTIONS}))
def test_every_revised_caption_layer_stays_healthy(text):
    core, layer = load(text)
    healthy(core, layer)


@pytest.mark.parametrize("entry", DATA["earlier_rewordings"], ids=lambda entry: entry["site"])
def test_earlier_reworded_rows_carry_a_working_review(entry):
    """A row whose target is the earlier contemporary rewording no longer claims its old review."""
    row = ledger()[entry["site"]]
    assert row["review"] == entry["review_after"]
    if row["target_sha256"] == entry["reworded_target_sha256"]:
        assert row["review"] == "working"
        assert entry["state"] in (
            "applied",
            "skipped: reworded row is not internally-reviewed",
        )
    else:
        assert row["target_sha256"] == entry["reviewed_target_sha256"]
        assert row["review"] == entry["review_before"]
        assert entry["state"] == "skipped: base does not carry the earlier rewording"


def test_about_reads_forever():
    for text, row in ABOUT.items():
        _, layer = load(text)
        assert layer["about"] == row["after"]
        assert "for ever" not in layer["about"]


def test_source_records_are_pinned():
    current = uses()
    for row in RECORDS:
        use = current[row["use"]]
        assert use[row["field"]] == row["after"], (row["use"], row["field"])
        assert use["role"] == "historical_wording_basis"
    corrected = current["use.en.13367d2da7395f0a9364"]
    assert corrected["decision"] == "RETAIN_WITH_CORRECTION"
    assert "“For ever and ever.”" in corrected["claim"]
    assert "normalization" in corrected["claim"]
    for identity in ("use.en.e0d2b52eaa17dc16e0ca", "use.en.d5500526890c50057d88"):
        assert "shall receive" not in current[identity]["decision_reason"]
        assert current[identity]["address"]["segment"] == "s04"


def test_current_quotations_of_revised_prose_name_the_current_wording():
    current = uses()
    quoted = 0
    for (text, segment), row in sorted(PROSE.items()):
        for use in current.values():
            if use["address"] != {"kind": "segment", "text": text, "segment": segment}:
                continue
            for field in ("claim", "decision_reason"):
                value = use.get(field) or ""
                assert row["before"] not in value, (use["id"], field)
                if "for current “" in value:
                    assert value.split("for current “", 1)[1].split("”.", 1)[0] == row["after"]
                    quoted += 1
    assert quoted == 2


def test_retired_allowances_restore_exactly_and_do_not_exempt_current_prose():
    raw = (ROOT / LEGACY).read_bytes()
    fixture = json.loads(raw)
    assert hashlib.sha256(raw).hexdigest() == ALLOWANCES["after_raw_sha256"]
    previous = before_english_register_allowances(fixture)
    assert digest(previous) == ALLOWANCES["before_canonical_sha256"]
    retired = []
    for item in ALLOWANCES["retired"]:
        if "record" in item:
            retired += [(item["record"]["text"], field) for field in item["record"]["fields"]]
        else:
            retired.append((item["text"], item["field"]))
    assert len(retired) == 8
    for text, field in retired:
        _, segment, kind = field["path"]
        assert kind == "translation"
        row = PROSE[(text, segment)]
        assert field["sha256"] == hashlib.sha256(row["before"].encode()).hexdigest()
        assert register.stale(row["before"]) and not register.stale(row["after"])
        assert tuple(field["path"]) not in register.LEGACY.get(text, {})
    with pytest.raises(AssertionError, match=r"^English register allowances$"):
        before_english_register_allowances(previous)


@pytest.mark.parametrize("kind", sorted(CONTROLS))
def test_earlier_wording_is_rejected_and_recovers(kind):
    text, segment, expected = CONTROLS[kind]
    row = PROSE[(text, segment)]
    assert row["classes"] == [kind]
    core, layer = load(text)
    snapshot = deepcopy(layer)
    try:
        layer["segments"][segment]["translation"] = row["before"]
        assert layer != snapshot
        healthy(core, layer)
        assert prose_errors(row, layer["segments"][segment]["translation"]) == [expected]
        if kind == "archaic":
            changes = register.register_changes(layer, register.ALLOWANCES)
            assert ("segments", segment, "translation") in changes["new"]
    finally:
        layer.clear()
        layer.update(deepcopy(snapshot))
    assert layer == snapshot
    assert prose_errors(row, layer["segments"][segment]["translation"]) == []
    assert not any(register.register_changes(layer, register.ALLOWANCES).values())


def test_predictive_shall_caption_is_rejected_and_recovers():
    text, words = CAPTION_CONTROL
    (row,) = [row for row in CAPTIONS if row["text"] == text and row["words"] == words]
    core, layer = load(text)
    snapshot = deepcopy(layer)
    try:
        layer["words"][words[0]]["gloss"] = row["before"]
        assert layer != snapshot
        healthy(core, layer)
        assert caption_errors(row, caption(layer, row["segment"], words)) == ["predictive shall"]
    finally:
        layer.clear()
        layer.update(deepcopy(snapshot))
    assert caption_errors(row, caption(layer, row["segment"], words)) == []


@pytest.mark.parametrize("relative", sorted(FILES))
def test_exact_predecessor_is_reachable_and_drift_is_rejected(relative):
    rule = FILES[relative]
    raw = (ROOT / relative).read_bytes()
    actual = json.loads(raw)
    saved = deepcopy(actual)
    previous = before_english_register_object(relative, actual)
    previous_raw = before_english_register_bytes(relative, raw)
    assert actual == saved and previous is not actual and previous != actual
    assert hashlib.sha256(raw).hexdigest() == rule["after_raw_sha256"]
    assert hashlib.sha256(previous_raw).hexdigest() == rule["before_raw_sha256"]
    assert json.loads(previous_raw) == previous
    with pytest.raises(AssertionError, match=r"^English register comparison$"):
        before_english_register_object(relative, previous)
    with pytest.raises(AssertionError, match=r"^English register comparison bytes$"):
        before_english_register_bytes(relative, raw + b" ")
    assert before_english_register_object(relative, actual) == previous
    assert (ROOT / relative).read_bytes() == raw

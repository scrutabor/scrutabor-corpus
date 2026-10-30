"""Contemporary English conclusions, future captions and the Psalm 42 cause clause.

Eight contemporary prayer conclusions read "forever and ever". The Supplices
Communion clause gives the generalizing future perfect as the English present
"receive", and four captions give ordinary future prediction with "will". The
opening verse of Psalm 42 asks God to "set my cause apart from the unholy
nation", and its caption reads "my cause" as one group. Each pin is bound to the
native layer, its Latin context and the provenance ledger; one control per
class shows that the earlier wording is rejected. The exact predecessor of every
changed file stays reachable for the older comparisons, and drift is rejected.
"""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from english_contract_successor_fixture import (
    FILES,
    before_english_contract_bytes,
    before_english_contract_object,
)
from english_register_successor_fixture import (
    before_english_register_bytes,
    before_english_register_ledger,
    before_english_register_object,
)
from foot_communion_successor_fixture import before_foot_communion_bytes

from build_reader import store
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs
from checks.translation_provenance import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
CONCLUSIONS = {
    "orationes.anima-christi": ("s13", "forever and ever. Amen."),
    "ordinarium.deus-qui-humanae": (
        "s02",
        "O God, who marvelously established the dignity of human nature and more marvelously"
        " renewed it, grant that through the mystery of this water and wine we may be sharers"
        " in the divinity of Him who deigned to become a partaker of our humanity, Jesus Christ,"
        " Your Son, our Lord, who, being God, lives and reigns with You in the unity of the"
        " Holy Spirit, forever and ever. Amen.",
    ),
    "ordinarium.per-ipsum": ("s08", "forever and ever."),
    "ordinarium.libera-nos": ("s12", "forever and ever."),
    "ordinarium.qui-dixisti": ("s06", "who, being God, live and reign forever and ever. Amen."),
    "ordinarium.fili-dei-vivi": (
        "s05",
        "who, being God, live and reign with the same God the Father and with the Holy Spirit"
        " forever and ever. Amen.",
    ),
    "ordinarium.perceptio-corporis": (
        "s04",
        "who, being God, live and reign with God the Father in the unity of the Holy Spirit"
        " forever and ever. Amen.",
    ),
    "ordinarium.corpus-tuum": ("s04", "who live and reign forever and ever. Amen."),
}
COMMUNION = (
    "ordinarium.supplices-te-rogamus",
    "s06",
    "receive the most holy Body and Blood of Your Son,",
)
PSALM = (
    "ordinarium.iudica-me",
    "s03",
    "Judge me, O God, and set my cause apart from the unholy nation. Deliver me from an"
    " unjust and deceitful man.",
)
PROSE = {**CONCLUSIONS, COMMUNION[0]: COMMUNION[1:], PSALM[0]: PSALM[1:]}
# (text, segment, Latin words, Latin tense, English caption)
FUTURES = (
    ("ordinarium.supplices-te-rogamus", "s06", ("w035",), "futperf", "will have received"),
    ("ordinarium.simili-modo", "s11", ("w050",), "fut", "will be shed"),
    (
        "proprium.dominica-ii-post-pentecosten-evangelium",
        "s01",
        ("w148",),
        "fut",
        "will taste",
    ),
    ("ordinarium.quid-retribuam", "s04", ("w023", "w024"), "fut", "I will be saved"),
)
COMMUNION_CARD = (
    "The form is future perfect, “will have received”. The same spelling could be the perfect"
    " subjunctive, “may have received”. The purpose clause settles the future perfect, which"
    " English prose gives as the present “receive”."
)
CAUSE_GROUP = {"words": ["w006", "w007"], "anchor": "w006", "gloss": "my cause"}
PSALM_CAPTION = (
    "Judge me God and set apart my cause from the nation not holy from the man unjust and"
    " deceitful deliver me"
)
PROVENANCE = {
    "orationes.anima-christi.s13.en": ("public-domain", "internally-reviewed"),
    "ordinarium.deus-qui-humanae.s02.en": ("working-unsettled", "working"),
    "ordinarium.per-ipsum.s08.en": ("public-domain", "internally-reviewed"),
    "ordinarium.libera-nos.s12.en": ("public-domain", "working"),
    "ordinarium.qui-dixisti.s06.en": ("public-domain", "internally-reviewed"),
    "ordinarium.fili-dei-vivi.s05.en": ("public-domain", "working"),
    "ordinarium.perceptio-corporis.s04.en": ("public-domain", "internally-reviewed"),
    "ordinarium.corpus-tuum.s04.en": ("public-domain", "internally-reviewed"),
    "ordinarium.supplices-te-rogamus.s06.en": ("public-domain", "internally-reviewed"),
    "ordinarium.iudica-me.s03.en": ("working-unsettled", "working"),
}
RELATIONSHIPS = {
    "ordinarium.per-ipsum.s02.en": "normalized",
    "ordinarium.per-ipsum.s06.en": "normalized",
    "ordinarium.per-ipsum.s08.en": "normalized",
    "ordinarium.per-ipsum.s09.en": "exact",
    "ordinarium.libera-nos.s12.en": "normalized",
    "orationes.anima-christi.s13.en": "normalized",
    "ordinarium.supplices-te-rogamus.s06.en": "revised",
}
RETAINED = {"RETAIN", "RETAIN_WITH_CORRECTION"}
# Source records whose claim or decision reason quotes the current English of the site.
QUOTED = {
    "ordinarium.per-ipsum": 1,
    "ordinarium.qui-dixisti": 2,
    "ordinarium.perceptio-corporis": 2,
    "ordinarium.corpus-tuum": 1,
    "ordinarium.supplices-te-rogamus": 1,
}


def load(text):
    return store.core(ROOT, text), deepcopy(store.raw_layer(ROOT, "en", text))


def healthy(core, layer):
    assert language_packs.check_core(core) == []
    category, name = core["id"].split(".", 1)
    path = ROOT / "languages/en/texts" / category / f"{name}.json"
    assert language_packs.check_layer(core, layer, path) == []
    assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []


def latin(core, segment_id):
    (segment,) = [segment for segment in core["segments"] if segment["id"] == segment_id]
    assert segment["type"] == "verse"
    return segment["words"]


def ledger():
    # The later English register successor is undone on a copy; its module pins the rest.
    relative = "languages/en/translation-provenance.json"
    current = before_english_register_ledger(relative, json.loads((ROOT / relative).read_bytes()))
    return {row["site"]: row for row in current["sites"]}


def register_uses():
    """English source records with the later register successor undone on a copy."""
    relative = "languages/en/bibliography.json"
    current = json.loads((ROOT / relative).read_bytes())
    return before_english_register_object(relative, current)["uses"]


def conclusion_errors(text, layer):
    segment, expected = CONCLUSIONS[text]
    prose = layer["segments"][segment]["translation"]
    if "for ever and ever" in prose:
        return ["legacy conclusion spacing"]
    ending = prose.removesuffix(" Amen.").removesuffix(".")
    if prose != expected or not ending.endswith("forever and ever"):
        return ["contemporary conclusion"]
    return []


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


def future_errors(layer, segment, words, expected):
    gloss = caption(layer, segment, words)
    if gloss is None:
        return ["future caption shape"]
    if gloss.split()[0] == "shall" or " shall " in f" {gloss} ":
        return ["predictive shall"]
    if gloss != expected:
        return ["future caption"]
    return []


def caption_line(core, layer, segment):
    groups = {group["anchor"]: group for group in layer["segments"][segment].get("alignments", [])}
    grouped = {word for group in groups.values() for word in group["words"]}
    line = []
    for word in latin(core, segment):
        if word["id"] in groups:
            line.append(groups[word["id"]]["gloss"])
        elif word["id"] not in grouped:
            line.append(layer["words"][word["id"]]["gloss"])
    return " ".join(line)


def cause_errors(core, layer):
    segment = PSALM[1]
    groups = layer["segments"][segment].get("alignments", [])
    if layer["words"]["w006"] or layer["words"]["w007"] or CAUSE_GROUP not in groups:
        return ["split cause caption"]
    if layer["words"]["w005"].get("gloss") != "set apart":
        return ["cause verb caption"]
    if caption_line(core, layer, segment) != PSALM_CAPTION:
        return ["cause caption line"]
    return []


@pytest.mark.parametrize("text", sorted(CONCLUSIONS))
def test_each_contemporary_conclusion_reads_forever_and_ever(text):
    core, layer = load(text)
    healthy(core, layer)
    segment, expected = CONCLUSIONS[text]
    forms = [word["form"] for word in latin(core, segment)]
    assert forms[-3:-1] == ["sǽcula", "sæculórum"] or forms[-2:] == ["sǽcula", "sæculórum"]
    assert layer["segments"][segment]["translation"] == expected
    assert conclusion_errors(text, layer) == []


@pytest.mark.parametrize("text", sorted(PROSE))
def test_revised_prose_binds_its_unchanged_ledger_labels(text):
    _, layer = load(text)
    segment, expected = PROSE[text]
    site = f"{text}.{segment}.en"
    row = ledger()[site]
    assert layer["segments"][segment]["translation"] == expected
    assert row["target_sha256"] == canonical_hash(expected)
    assert (row["origin"], row["review"]) == PROVENANCE[site]
    assert row["familiar_core"] is False


@pytest.mark.parametrize("text,segment,words,tense,expected", FUTURES, ids=[f[0] for f in FUTURES])
def test_future_prediction_captions_read_will(text, segment, words, tense, expected):
    core, layer = load(text)
    healthy(core, layer)
    by_id = {word["id"]: word for word in latin(core, segment)}
    verb = by_id[words[-1]]
    assert verb["morph"]["tense"] == tense and verb["morph"]["mood"] == "ind"
    assert caption(layer, segment, words) == expected
    assert future_errors(layer, segment, words, expected) == []


def test_communion_clause_prose_and_card_agree_on_the_future_perfect():
    text, segment, expected = COMMUNION
    core, layer = load(text)
    healthy(core, layer)
    (verb,) = [word for word in latin(core, segment) if word["id"] == "w035"]
    assert verb["form"] == "sumpsérimus" and verb["morph"]["tense"] == "futperf"
    assert layer["segments"][segment]["translation"] == expected
    assert layer["words"]["w035"] == {"gloss": "will have received", "explanation": COMMUNION_CARD}
    assert "shall" not in layer["words"]["w035"]["explanation"]


def test_psalm_cause_clause_and_caption_group():
    text, segment, expected = PSALM
    core, layer = load(text)
    healthy(core, layer)
    forms = [word["form"] for word in latin(core, segment)]
    assert forms[4:11] == ["discérne", "causam", "meam", "de", "gente", "non", "sancta"]
    assert layer["segments"][segment]["translation"] == expected
    assert layer["segments"][segment]["alignments"] == [CAUSE_GROUP]
    assert layer["words"]["w005"] == {"gloss": "set apart"}
    assert cause_errors(core, layer) == []


def test_normalized_conclusions_keep_a_retained_page_basis():
    relationships = store.translation_relationships(ROOT, "en")
    assert {site: relationships[site] for site in RELATIONSHIPS} == RELATIONSHIPS
    uses = register_uses()
    for text, segment in (("ordinarium.per-ipsum", "s08"), ("ordinarium.libera-nos", "s12")):
        retained = [
            use
            for use in uses
            if use["address"] == {"kind": "segment", "text": text, "segment": segment}
            and use["role"] == "historical_wording_basis"
            and use["decision"] in RETAINED
        ]
        assert len(retained) == 1
        assert "“For ever and ever.”" in retained[0]["claim"]
        assert "normalization" in retained[0]["claim"]


@pytest.mark.parametrize("text", sorted(PROSE))
def test_source_records_quote_the_current_wording(text):
    segment, expected = PROSE[text]
    uses = register_uses()
    quotes = 0
    for use in uses:
        if use["address"] != {"kind": "segment", "text": text, "segment": segment}:
            continue
        assert use["claim"] != "for ever and ever.", use["id"]
        for field in ("claim", "decision_reason"):
            value = use.get(field, "")
            if "for current “" in value:
                quoted = value.split("for current “", 1)[1].split("”.", 1)[0]
                assert quoted == expected, (use["id"], field)
                quotes += 1
            if use["decision"] in RETAINED and "current English reads “" in value:
                quoted = value.split("current English reads “", 1)[1].split("”", 1)[0]
                assert quoted == expected, (use["id"], field)
                quotes += 1
    assert quotes == QUOTED.get(text, 0)


@pytest.mark.parametrize("text", sorted(CONCLUSIONS))
def test_legacy_conclusion_spacing_is_rejected_and_recovers(text):
    core, layer = load(text)
    segment, expected = CONCLUSIONS[text]
    snapshot = deepcopy(layer)
    record = layer["segments"][segment]
    try:
        record["translation"] = expected.replace("forever and ever", "for ever and ever", 1)
        assert layer != snapshot
        healthy(core, layer)
        assert conclusion_errors(text, layer) == ["legacy conclusion spacing"]
    finally:
        record["translation"] = snapshot["segments"][segment]["translation"]
    assert layer == snapshot
    assert conclusion_errors(text, layer) == []


@pytest.mark.parametrize("text,segment,words,tense,expected", FUTURES, ids=[f[0] for f in FUTURES])
def test_predictive_shall_caption_is_rejected_and_recovers(text, segment, words, tense, expected):
    core, layer = load(text)
    snapshot = deepcopy(layer)
    old = expected.replace("will", "shall", 1).replace("shall have received", "shall receive")
    try:
        if len(words) == 1:
            layer["words"][words[0]]["gloss"] = old
        else:
            (group,) = [
                group
                for group in layer["segments"][segment]["alignments"]
                if group["words"] == list(words)
            ]
            group["gloss"] = old
        assert layer != snapshot
        healthy(core, layer)
        assert future_errors(layer, segment, words, expected) == ["predictive shall"]
    finally:
        layer.clear()
        layer.update(deepcopy(snapshot))
    assert future_errors(layer, segment, words, expected) == []


def test_split_cause_caption_is_rejected_and_recovers():
    text, segment, _ = PSALM
    core, layer = load(text)
    snapshot = deepcopy(layer)
    try:
        del layer["segments"][segment]["alignments"]
        layer["words"]["w006"] = {"gloss": "cause"}
        layer["words"]["w007"] = {"gloss": "my"}
        assert layer != snapshot
        healthy(core, layer)
        assert caption_line(core, layer, segment) != PSALM_CAPTION
        assert cause_errors(core, layer) == ["split cause caption"]
    finally:
        layer.clear()
        layer.update(deepcopy(snapshot))
    assert cause_errors(core, layer) == []


@pytest.mark.parametrize("relative", sorted(FILES))
def test_exact_predecessor_is_reachable_and_drift_is_rejected(relative):
    rule = FILES[relative]
    current = (ROOT / relative).read_bytes()
    # The later English register successor is undone first; its own module pins the rest.
    raw = before_english_register_bytes(relative, current)
    actual = json.loads(raw)
    saved = deepcopy(actual)
    previous = before_english_contract_object(relative, actual)
    previous_raw = before_english_contract_bytes(relative, raw)
    assert actual == saved and previous is not actual and previous != actual
    current_raw = before_foot_communion_bytes(relative, raw)
    assert hashlib.sha256(current_raw).hexdigest() == rule["after_raw_sha256"]
    assert hashlib.sha256(previous_raw).hexdigest() == rule["before_raw_sha256"]
    assert json.loads(previous_raw) == previous
    with pytest.raises(AssertionError, match=r"^English contract comparison$"):
        before_english_contract_object(relative, previous)
    with pytest.raises(AssertionError, match=r"^English contract comparison bytes$"):
        before_english_contract_bytes(relative, raw + b" ")
    assert before_english_contract_object(relative, actual) == previous
    assert (ROOT / relative).read_bytes() == current

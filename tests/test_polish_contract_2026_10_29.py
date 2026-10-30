"""Polish wording in nine Mass texts: prose, captions, one word note and one introduction."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from canon_consecration_successor_fixture import (
    before_canon_bytes,
    before_canon_layer,
    before_canon_object,
)
from polish_contract_fixture import (
    DATA,
    LEDGER,
    before_polish_contract_bytes,
    before_polish_contract_layer,
    before_polish_contract_ledger,
    current_polish_contract_value,
)

from build_reader import store
from build_reader.bibliography_bindings import digest
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs, prose, translation_provenance
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
GOSPEL = "proprium.dominica-ii-post-pentecosten-evangelium"
COMMUNICANTES = "ordinarium.communicantes"
QUID = "ordinarium.quid-retribuam"
QUAM = "ordinarium.quam-oblationem"
FILI = "ordinarium.fili-dei-vivi"
POSTCOMMUNION = "proprium.dominica-ii-post-pentecosten-postcommunio"
DEUS = "ordinarium.deus-qui-humanae"
ANDREW = "proprium.sancti-andreae-apostoli-alleluia"
SECRET = "proprium.dominica-ii-post-pentecosten-secreta"
TEXTS = (GOSPEL, COMMUNICANTES, QUID, QUAM, FILI, POSTCOMMUNION, DEUS, ANDREW, SECRET)

# (text, segment, exact clause in the adopted prose, wording it replaced)
PROSE = (
    (
        GOSPEL,
        "s01",
        "A pan rzekł do sługi: Wyjdź na drogi i opłotki, i zmuszaj do wejścia, "
        "aby mój dom się zapełnił.",
        "na drogi i pod płoty",
    ),
    (
        COMMUNICANTES,
        "s01",
        "Trwamy we wspólnocie i czcimy pamięć przede wszystkim chwalebnej Maryi, "
        "zawsze Dziewicy, Rodzicielki Boga i Pana naszego Jezusa Chrystusa,",
        "Pozostając we wspólnocie i czcząc pamięć",
    ),
    (QUID, "s02", "Co oddam Panu za wszystko, co mi wyświadczył?", "co mi oddał?"),
    (
        QUAM,
        "s03",
        "racz uczynić błogosławioną, uznaną, zatwierdzoną, rozumną i godną przyjęcia,",
        "ważną",
    ),
    (DEUS, "s02", "mieli udział w Bóstwie Jezusa Chrystusa, Twojego Syna,", "w bóstwie"),
)
# (text, word, Latin form, adopted direct caption)
CAPTIONS = (
    (GOSPEL, "w130", "sepes", "opłotki"),
    (GOSPEL, "w133", "intráre", "do wejścia"),
    (COMMUNICANTES, "w001", "Communicántes", "trwając we wspólnocie"),
    (QUAM, "w010", "ratam", "zatwierdzoną"),
    (FILI, "w047", "permíttas", "nie pozwól"),
    (POSTCOMMUNION, "w009", "mystérii", "w tajemnicy"),
    (POSTCOMMUNION, "w010", "crescat", "wzrastało"),
    (POSTCOMMUNION, "w013", "efféctus", "działanie"),
    (SECRET, "w006", "dicánda", "mająca być poświęcona"),
    (ANDREW, "w006", "in", "jako"),
)
# (text, segment, first word, last word, complete caption line)
LINES = (
    (
        GOSPEL,
        "s01",
        "w126",
        "w137",
        "Wyjdź na drogi i opłotki i przymuszaj do wejścia aby został zapełniony dom mój",
    ),
    (
        COMMUNICANTES,
        "s01",
        "w001",
        "w006",
        "trwając we wspólnocie i pamięć czcząc przede wszystkim",
    ),
    (
        FILI,
        "s04",
        "w035",
        "w047",
        "i spraw abym Twoich zawsze trwał przy przykazaniach i od Ciebie nigdy być odłączonym "
        "nie pozwól",
    ),
    (
        POSTCOMMUNION,
        "s01",
        "w001",
        "w013",
        "Przyjąwszy dary święte prosimy Panie aby przez częste uczestnictwo w tajemnicy "
        "wzrastało naszego zbawienia działanie",
    ),
    (SECRET, "s01", "w001", "w006", "Ofiara nas Panie Twojemu imieniu mająca być poświęcona"),
    (ANDREW, "s01", "w003", "w008", "Umiłował Andrzeja Pan jako woń słodyczy"),
)
ANDREW_NOTE = (
    "Z „odórem suavitátis” tworzy biblijny zwrot o ofierze miłej Bogu jak przyjemna woń "
    "(Ef 5, 2). Werset odnosi go do Andrzeja: Pan umiłował go jako taką ofiarę, dlatego „in” "
    "oddano tu przez „jako”, a cały zwrot przez „jako woń słodyczy”."
)
DEUS_ABOUT = "uczestnikami Bóstwa Chrystusa"


def load(text):
    return store.core(ROOT, text), store.raw_layer(ROOT, "pl", text)


def latin(core):
    return {w["id"]: w for segment in core["segments"] for w in segment.get("words", [])}


def healthy(core, layer):
    assert language_packs.check_core(core) == []
    path = store.layer_path(ROOT, "pl", core["id"])
    assert language_packs.check_layer(core, layer, path) == []
    assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
    assert prose.check(layer) == []


def caption_line(core, layer, segment, first, last):
    words = next(s["words"] for s in core["segments"] if s["id"] == segment)
    ids = [w["id"] for w in words]
    span = ids[ids.index(first) : ids.index(last) + 1]
    groups = layer["segments"][segment].get("alignments", [])
    parts = []
    for wid in span:
        (group,) = [g for g in groups if wid in g["words"]] or [None]
        if group is None:
            parts.append(layer["words"][wid]["gloss"])
        elif wid == group["words"][0] and "gloss" in group:
            assert set(group["words"]) <= set(span), "caption line boundary"
            parts.append(group["gloss"])
    return " ".join(parts)


def assert_contract(text, core, layer):
    """The adopted Polish reading of each declared site, read in its line."""
    words = latin(core)
    for t, segment, clause, old in PROSE:
        if t == text:
            translation = layer["segments"][segment]["translation"]
            assert translation.count(clause) == 1, "adopted Polish prose"
            assert old not in translation, "adopted Polish prose"
    for t, wid, form, gloss in CAPTIONS:
        if t == text:
            assert words[wid]["form"] == form, "Latin caption context"
            assert layer["words"][wid]["gloss"] == gloss, "adopted Polish caption"
            assert not any(
                wid in group["words"]
                for entry in layer["segments"].values()
                for group in entry.get("alignments", [])
            ), "adopted Polish caption"
    for t, segment, first, last, line in LINES:
        if t == text:
            assert caption_line(core, layer, segment, first, last) == line, (
                "adopted Polish caption line"
            )
    if text == ANDREW:
        note = layer["words"]["w006"]["explanation"]
        assert note == ANDREW_NOTE, "adopted Polish word note"
        assert "„jako woń słodyczy”" in note, "adopted Polish word note"
    if text == DEUS:
        assert DEUS_ABOUT in layer["about"] and "bóstw" not in layer["about"], (
            "adopted Polish introduction"
        )


@pytest.mark.parametrize("text", TEXTS)
def test_adopted_polish_wording_is_native_and_reads_in_its_line(text):
    core, layer = load(text)
    healthy(core, layer)
    assert_contract(text, core, layer)


@pytest.mark.parametrize("text,segment", [(row[0], row[1]) for row in PROSE])
def test_changed_prose_rows_bind_actual_source_and_target(text, segment):
    core, layer = load(text)
    ledger = json.loads((ROOT / LEDGER["relative"]).read_bytes())
    site = f"{text}.{segment}.pl"
    (row,) = [row for row in ledger["sites"] if row["site"] == site]
    (source,) = [s for s in core["segments"] if s["id"] == segment]
    assert row["source_sha256"] == canonical_hash(source_payload(source))
    assert row["target_sha256"] == canonical_hash(layer["segments"][segment]["translation"])
    (change,) = [change for change in LEDGER["rows"] if change["site"] == site]
    assert row == change["after"]
    before = change["before"]
    assert {key for key in before if before[key] != row[key]} == {"target_sha256"}
    assert translation_provenance.check(ROOT)[0] == []


@pytest.mark.parametrize(
    "text,fault",
    [
        (QUID, "prose"),
        (FILI, "caption"),
        (COMMUNICANTES, "caption"),
        (ANDREW, "note"),
    ],
    ids=["prose-oddal", "caption-nie-dopusc", "caption-zjednoczeni", "note-fragment"],
)
def test_previous_wording_is_valid_schema_but_rejected_and_recovers(text, fault):
    core, layer = load(text)
    saved, same_input = deepcopy(layer), layer
    healthy(core, layer)
    assert_contract(text, core, layer)
    try:
        if fault == "prose":
            entry = layer["segments"]["s02"]
            entry["translation"] = entry["translation"].replace("wyświadczył", "oddał")
            label = "adopted Polish prose"
        elif text == FILI:
            layer["words"]["w047"]["gloss"] = "nie dopuść"
            label = "adopted Polish caption"
        elif text == COMMUNICANTES:
            layer["words"]["w001"]["gloss"] = "zjednoczeni"
            label = "adopted Polish caption"
        else:
            layer["words"]["w006"]["explanation"] = (
                "Z odórem suavitátis: „jako słodką woń”, obraz osoby miłej Bogu."
            )
            label = "adopted Polish word note"
        assert layer != saved
        # The previous wording was valid product data; only this contract rejects it.
        healthy(core, layer)
        with pytest.raises(AssertionError, match=rf"^{label}(?:\n|$)"):
            assert_contract(text, core, layer)
    finally:
        layer.clear()
        layer.update(deepcopy(saved))
    assert layer is same_input and layer == saved
    healthy(core, layer)
    assert_contract(text, core, layer)


@pytest.mark.parametrize("rule", DATA["layers"], ids=lambda rule: rule["id"])
def test_exact_layer_inverse_restores_only_declared_fields(rule):
    path = ROOT / rule["relative"]
    raw = path.read_bytes()
    actual = json.loads(raw)
    saved = deepcopy(actual)
    current_raw = before_canon_bytes(rule["relative"], raw)
    assert hashlib.sha256(current_raw).hexdigest() == rule["after_raw_sha256"]
    assert digest(before_canon_layer(actual)) == rule["after_canonical_sha256"]
    before = before_polish_contract_layer(actual)
    before_raw = before_polish_contract_bytes(rule["relative"], raw)
    assert digest(before) == rule["before_canonical_sha256"]
    assert hashlib.sha256(before_raw).hexdigest() == rule["before_raw_sha256"]
    assert json.loads(before_raw) == before
    assert before is not actual and actual == saved and path.read_bytes() == raw
    for operation in rule["operations"]:
        assert (
            current_polish_contract_value(rule["text"], operation["pointer"], operation["before"])
            == operation["after"]
        )
    with pytest.raises(AssertionError, match=r"^Polish contract layer(?:\n|$)"):
        before_polish_contract_layer(before)
    with pytest.raises(AssertionError, match=r"^exact Polish contract bytes(?:\n|$)"):
        before_polish_contract_bytes(rule["relative"], before_raw)
    with pytest.raises(AssertionError, match=r"^exact Polish contract bytes(?:\n|$)"):
        before_polish_contract_bytes(rule["relative"], raw + b" ")


@pytest.mark.parametrize("rule", DATA["layers"], ids=lambda rule: rule["id"])
def test_unrelated_layer_change_cannot_hide_in_inverse(rule):
    actual = json.loads((ROOT / rule["relative"]).read_bytes())
    saved = deepcopy(actual)
    first, field = next(
        (sid, key)
        for sid, entry in actual["segments"].items()
        for key in ("translation", "narrative")
        if key in entry
    )
    try:
        actual["segments"][first][field] += " Extra."
        with pytest.raises(AssertionError, match=r"^Polish contract layer(?:\n|$)"):
            before_polish_contract_layer(actual)
    finally:
        actual.clear()
        actual.update(deepcopy(saved))
    assert digest(before_polish_contract_layer(actual)) == rule["before_canonical_sha256"]


def test_exact_ledger_inverse_restores_only_declared_rows():
    relative = LEDGER["relative"]
    raw = (ROOT / relative).read_bytes()
    actual = json.loads(raw)
    saved = deepcopy(actual)
    current = before_canon_object(relative, actual)
    current_raw = before_canon_bytes(relative, raw)
    assert hashlib.sha256(current_raw).hexdigest() == LEDGER["after_raw_sha256"]
    assert digest(current) == LEDGER["after_canonical_sha256"]
    before = before_polish_contract_ledger(relative, actual)
    before_raw = before_polish_contract_bytes(relative, raw)
    assert digest(before) == LEDGER["before_canonical_sha256"]
    assert hashlib.sha256(before_raw).hexdigest() == LEDGER["before_raw_sha256"]
    assert json.loads(before_raw) == before
    assert [
        i
        for i, pair in enumerate(zip(current["sites"], before["sites"], strict=True))
        if pair[0] != pair[1]
    ] == [change["index"] for change in LEDGER["rows"]]
    assert before is not actual and actual == saved and (ROOT / relative).read_bytes() == raw
    with pytest.raises(AssertionError, match=r"^Polish contract ledger(?:\n|$)"):
        before_polish_contract_ledger(relative, before)
    with pytest.raises(AssertionError, match=r"^exact Polish contract bytes(?:\n|$)"):
        before_polish_contract_bytes(relative, before_raw)
    other = "languages/en/translation-provenance.json"
    other_raw = (ROOT / other).read_bytes()
    other_value = json.loads(other_raw)
    assert before_polish_contract_ledger(other, other_value) is other_value
    assert before_polish_contract_bytes(other, other_raw) is other_raw


@pytest.mark.parametrize(
    "change,fault",
    [(change, fault) for change in LEDGER["rows"] for fault in ("target", "source", "order")],
    ids=lambda value: value["id"] if isinstance(value, dict) else value,
)
def test_current_ledger_drift_rejects_and_recovers(change, fault):
    relative = LEDGER["relative"]
    actual = json.loads((ROOT / relative).read_bytes())
    saved = deepcopy(actual)
    sites, index = actual["sites"], change["index"]
    row = sites[index]
    original, order = deepcopy(row), list(sites)
    expected = before_polish_contract_ledger(relative, actual)
    try:
        if fault == "order":
            sites[index], sites[index + 1] = sites[index + 1], sites[index]
        else:
            row[f"{fault}_sha256"] = "0" * 64
        assert actual != saved
        with pytest.raises(AssertionError, match=r"^Polish contract ledger(?:\n|$)"):
            before_polish_contract_ledger(relative, actual)
    finally:
        row.clear()
        row.update(original)
        sites[:] = order
    assert actual == saved
    assert before_polish_contract_ledger(relative, actual) == expected

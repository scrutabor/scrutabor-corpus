"""Lauda Sion's short constructions, unchanged controls and current reader inputs."""

import json
from copy import deepcopy

import pytest
from lauda_sion_fixture import (
    FIXTURE,
    ROOT,
    SITES,
    TEXT,
    current,
    native,
    predecessor_core,
    predecessor_layer,
    predecessor_wording,
)

from build_reader import emit, store
from build_reader.layers import enrich_layer, expand_core
from checks.translation_provenance import canonical_hash, source_payload

CASES = [
    pytest.param(
        "pl",
        "s02",
        ("w017", "w018", "w019"),
        "większy od | wszelkiej | chwały",
        id="pl-comparative",
    ),
    pytest.param(
        "pl",
        "s02",
        ("w020", "w021", "w022"),
        "i nie | zdołasz dostatecznie wysławić",
        id="pl-adequacy",
    ),
    pytest.param(
        "en", "s02", ("w020", "w021", "w022"), "nor can you praise enough", id="en-adequacy-keep"
    ),
    pytest.param("pl", "s04", ("w032",), "On", id="pl-passive-subject"),
    pytest.param("en", "s04", ("w032",), "He", id="en-passive-subject"),
    pytest.param(
        "pl", "s04", ("w034", "w035", "w036"), "stole świętej wieczerzy", id="pl-supper-dependency"
    ),
    pytest.param("pl", "s05", ("w049",), "radosne", id="pl-rejoicing-agreement"),
    pytest.param("pl", "s05", ("w051",), "piękne", id="pl-rejoicing-second-agreement"),
    pytest.param("pl", "s07", ("w070", "w071"), "nowa | Pascha", id="pl-pascha-keep"),
    pytest.param("pl", "s07", ("w074", "w075"), "Passze | dawnej", id="pl-result-government"),
    pytest.param(
        "en", "s08", ("w077", "w078"), "Newness drives away the old", id="en-antithesis-agency"
    ),
    pytest.param(
        "pl", "s12", ("w126", "w127", "w128"), "poza | porządkiem rzeczy", id="pl-beyond-government"
    ),
    pytest.param("pl", "s13", ("w132",), "pod względem znaków", id="pl-respect-signs"),
    pytest.param("pl", "s13", ("w136",), "pod względem rzeczywistości", id="pl-respect-reality"),
    pytest.param("en", "s13", ("w135", "w136"), "not | in reality", id="en-respect-keep"),
    pytest.param(
        "pl",
        "s16",
        ("w169", "w170", "w171"),
        "a Przyjęty nie zostaje zużyty",
        id="pl-received-polarity",
    ),
    pytest.param(
        "en",
        "s16",
        ("w169", "w170", "w171"),
        "and the One received is not consumed",
        id="en-received-polarity",
    ),
    pytest.param(
        "pl",
        "s18",
        ("w182", "w183", "w184", "w185", "w186"),
        "Śmiercią | jest | dla złych | życiem | dla dobrych",
        id="pl-predicate-and-recipients",
    ),
    pytest.param(
        "en",
        "s19",
        ("w205", "w206", "w207"),
        "as is covered by the whole",
        id="en-covering-argument",
    ),
    pytest.param("pl", "s19", ("w206",), "pod całością", id="pl-whole-government"),
    pytest.param(
        "pl",
        "s20",
        ("w217", "w218", "w219", "w220", "w221", "w222"),
        "ani | byt | ani | wielkość | tego, co oznaczone | nie pomniejsza się",
        id="pl-negative-concord",
    ),
    pytest.param(
        "en",
        "s20",
        ("w217", "w218", "w219", "w220", "w221", "w222"),
        "neither | state | nor | stature | of what is signified | is diminished",
        id="en-neither-countercontrol",
    ),
    pytest.param("pl", "s21", ("w226", "w227"), "stał się | pokarmem", id="pl-result-instrumental"),
    pytest.param("pl", "s21", ("w232", "w233"), "nie wolno rzucać", id="pl-prohibition-once"),
    pytest.param("en", "s21", ("w232", "w233"), "not to be cast", id="en-prohibition-keep"),
    pytest.param("pl", "s22", ("w244", "w245"), "jest dana | manna", id="pl-manna-agreement"),
    pytest.param("en", "s22", ("w244", "w245"), "manna is given", id="en-manna-patient"),
    pytest.param(
        "pl",
        "s23",
        ("w260", "w261", "w262", "w263"),
        "spraw, byśmy oglądali dobra",
        id="pl-causative-arguments",
    ),
    pytest.param(
        "en",
        "s23",
        ("w260", "w261", "w262", "w263"),
        "make us behold good things",
        id="en-causative-arguments",
    ),
    pytest.param("pl", "s24", ("w284",), "uczyń nas", id="pl-delayed-object"),
    pytest.param("en", "s24", ("w284",), "make us", id="en-delayed-object"),
    pytest.param(
        "pl",
        "s20",
        ("w208", "w209", "w210", "w211"),
        "Nie następuje żadne rozdzielenie rzeczywistości",
        id="pl-quantifier-group",
    ),
    pytest.param("pl", "s23", ("w248",), "Pasterzu", id="pl-direct-divine-title"),
    pytest.param("en", "s05", ("w046", "w047"), "let it ring out;", id="en-first-subject-boundary"),
    pytest.param(
        "en", "s05", ("w050", "w051"), "let it be fitting—", id="en-delayed-subject-boundary"
    ),
    pytest.param(
        "en",
        "s24",
        ("w269", "w270", "w271", "w272"),
        "know and can do all things",
        id="en-shared-object",
    ),
    pytest.param("pl", "s24", ("w288",), "Alleluja", id="pl-final-acclamation"),
]
GROUPS = [
    pytest.param(row, id=f"{row['language']}-{row['segment']}-{row['group']['words'][0]}")
    for row in FIXTURE["groups"]
]
HELPS = [
    pytest.param(
        "pl",
        "w017",
        (
            "Maior jest rodzaju męskiego i odnosi się do Zbawiciela z poprzedniej strofy. "
            "Łacina pomija podmiot i łącznik: „bo [On jest] większy od wszelkiej chwały”."
        ),
        id="pl-savior-reference",
    ),
    pytest.param(
        "pl",
        "w284",
        (
            "Łacina pozostawia „nas” domyślne. „Uczyń nas” łączy się z wcześniejszymi "
            "określeniami: Twoimi współbiesiadnikami, współdziedzicami i towarzyszami. "
            "„Świętych obywateli” określa współdziedziców i towarzyszy."
        ),
        id="pl-delayed-imperative",
    ),
    pytest.param(
        "en",
        "w050",
        (
            "The first two wishes concern praise. In the next two, “it” refers "
            "to “the rejoicing of the mind,” named afterward."
        ),
        id="en-delayed-subject",
    ),
    pytest.param(
        "en",
        "w284",
        (
            "Latin leaves “us” understood. “Make us” governs the earlier descriptions: "
            "Your table companions, fellow heirs and comrades. “Of the holy citizens” "
            "describes the fellow heirs and comrades."
        ),
        id="en-delayed-imperative",
    ),
]
STRUCTURAL = [
    pytest.param(language, fault, id=f"{language}-{fault}")
    for language in ("pl", "en")
    for fault in ("residual", "missing", "foreign", "anchor", "overlap")
]
INVERSE_FAULTS = [
    pytest.param(language, fault, id=f"{language}-{fault}")
    for language in ("pl", "en")
    for fault in ("caption", "prose", "extra")
]
ROW_FAULTS = [
    pytest.param(site, fault, id=f"{site}-{fault}")
    for site in sorted(SITES)
    for fault in ("predecessor-digest", "review", "target")
]
NOTE_FAULTS = [
    pytest.param(language, word, fault, id=f"{language}-{word}-{fault}")
    for language, word in (("en", "w050"), ("en", "w284"), ("pl", "w284"))
    for fault in ("declaration", "help", "scope")
]
FAULTS = [
    pytest.param("pl", "s04", "w032", "Go", id="pl-passive-case"),
    pytest.param("en", "s04", "w032", "Him", id="en-passive-case"),
    pytest.param("pl", "s05", "w049", "radosna", id="pl-adjective-gender"),
    pytest.param("pl", "s07", "w074", "Paschę", id="pl-governed-case"),
    pytest.param("en", "s08", "w077", "The old drives away newness", id="en-agent-patient"),
    pytest.param("pl", "s16", "w169", "a Przyjęty zostaje zużyty", id="pl-omitted-negative"),
    pytest.param("en", "s16", "w169", "and the One received is consumed", id="en-omitted-negative"),
    pytest.param("pl", "s20", "w222", "pomniejsza się", id="pl-concord"),
    pytest.param("en", "s20", "w222", "is not diminished", id="en-extra-negative"),
    pytest.param("pl", "s21", "w232", "nie nie wolno rzucać", id="pl-double-negative"),
    pytest.param("en", "s19", "w205", "as much as the whole is covered", id="en-reversed-argument"),
    pytest.param("pl", "s22", "w244", "jest dany", id="pl-manna-gender"),
    pytest.param("en", "s23", "w260", "make good things behold us", id="en-causative-reversal"),
    pytest.param(
        "pl", "s20", "w208", "Następuje żadne rozdzielenie rzeczywistości", id="pl-group-concord"
    ),
]


def load(language):
    return store.core(ROOT, TEXT), store.raw_layer(ROOT, language, TEXT)


def phrase(layer, segment, identifiers):
    wanted = set(identifiers)
    groups = layer["segments"][segment].get("alignments", [])
    out, consumed = [], set()
    for wid in identifiers:
        if wid in consumed:
            continue
        matches = [g for g in groups if wid in g["words"]]
        assert len(matches) <= 1, "Lauda contextual reading"
        if matches:
            group = matches[0]
            assert set(group["words"]) <= wanted, "Lauda contextual reading"
            out.append(group["gloss"])
            consumed.update(group["words"])
        else:
            out.append(layer["words"][wid]["gloss"])
    return " | ".join(out)


def contextual(layer, segment, identifiers, expected):
    assert phrase(layer, segment, identifiers) == expected, "Lauda contextual reading"


def literal_control(layer):
    for row in CASES:
        language, segment, identifiers, expected = row.values
        if language == layer["language"]:
            contextual(layer, segment, identifiers, expected)


def change_caption(layer, segment, wid, value):
    matches = [g for g in layer["segments"][segment].get("alignments", []) if wid in g["words"]]
    if matches:
        assert len(matches) == 1
        matches[0]["gloss"] = value
    else:
        layer["words"][wid]["gloss"] = value


@pytest.mark.parametrize("language", ["pl", "en"])
def test_complete_current_text_and_compact_roundtrip(language):
    core, layer = load(language)
    snapshot = deepcopy((core, layer))
    current(core, layer)
    literal_control(layer)
    assert layer == FIXTURE["after_layers"][language]
    assert predecessor_layer(core, layer) == FIXTURE["before_layers"][language]
    before_core = predecessor_core(core, layer)
    assert [source_payload(s) for s in core["segments"]] == [
        source_payload(s) for s in before_core["segments"]
    ]
    doc, localized = expand_core(core), enrich_layer(core, layer)
    tables = [emit.Table() for _ in range(4)]
    base = emit.core_artifact(doc, core, *tables[:3])
    target = emit.language_artifact(doc, localized, tables[3])
    wanted_core, wanted_layers = emit._strip(doc, {language: localized})
    assert emit.expand(base, target, *[t.order for t in tables]) == (
        wanted_core,
        wanted_layers[language],
    )
    assert (core, layer) == snapshot


@pytest.mark.parametrize("language,segment,identifiers,expected", CASES)
def test_contextual_relation_and_retained_countercontrol(language, segment, identifiers, expected):
    core, layer = load(language)
    native(core, layer)
    contextual(layer, segment, identifiers, expected)


@pytest.mark.parametrize("row", GROUPS)
def test_short_group_has_exact_members_anchor_and_single_realization(row):
    core, layer = load(row["language"])
    native(core, layer)
    group, segment = row["group"], row["segment"]
    words = next(s["words"] for s in core["segments"] if s["id"] == segment)
    ids = [w["id"] for w in words]
    start = ids.index(group["words"][0])
    assert ids[start : start + len(group["words"])] == group["words"]
    matches = [
        g for g in layer["segments"][segment]["alignments"] if set(g["words"]) & set(group["words"])
    ]
    assert matches == [group]
    assert all("gloss" not in layer["words"][w] for w in group["words"])


@pytest.mark.parametrize("language,segment,wid,wrong", FAULTS)
def test_real_semantic_fault_is_rejected_and_same_copy_recovers(language, segment, wid, wrong):
    core, layer = load(language)
    native(core, layer)
    saved = deepcopy(layer)
    literal_control(layer)
    try:
        change_caption(layer, segment, wid, wrong)
        assert layer != saved
        with pytest.raises(AssertionError, match=r"^Lauda contextual reading(?:\n|$)"):
            literal_control(layer)
    finally:
        layer.clear()
        layer.update(deepcopy(saved))
        assert layer == saved
        native(core, layer)
        literal_control(layer)


@pytest.mark.parametrize("language,fault", STRUCTURAL)
def test_current_native_group_fault_and_same_container_restoration(language, fault):
    core, layer = load(language)
    native(core, layer)
    saved = deepcopy(layer)
    group = next(g for g in layer["segments"]["s16"]["alignments"] if "w169" in g["words"])
    try:
        if fault == "residual":
            layer["words"]["w169"]["gloss"] = "not"
        elif fault == "missing":
            group["words"].remove("w169")
        elif fault == "foreign":
            group["words"].append("w172")
        elif fault == "anchor":
            group["anchor"] = "w172"
        else:
            layer["segments"]["s16"]["alignments"].append(deepcopy(group))
        assert layer != saved
        with pytest.raises(AssertionError, match=r"^Lauda native"):
            native(core, layer)
    finally:
        layer.clear()
        layer.update(deepcopy(saved))
        assert layer == saved
        native(core, layer)


@pytest.mark.parametrize("language,fault", INVERSE_FAULTS)
def test_historical_inverse_never_repairs_an_unadmitted_current_input(language, fault):
    core, layer = load(language)
    saved = deepcopy(layer)
    predecessor_layer(core, layer)
    try:
        if fault == "caption":
            layer["words"]["w001"]["gloss"] += " altered"
        elif fault == "prose":
            layer["segments"]["s01"]["translation"] += " altered"
        else:
            layer["about"] += " altered"
        with pytest.raises(AssertionError, match=r"^Lauda complete current layer$"):
            predecessor_layer(core, layer)
    finally:
        layer.clear()
        layer.update(deepcopy(saved))
        assert predecessor_layer(core, layer) == FIXTURE["before_layers"][language]


@pytest.mark.parametrize("site,fault", ROW_FAULTS)
def test_five_prose_bindings_preserve_source_and_status_and_reject_fault(site, fault):
    # Keep the historical test identity while also checking the EN s05 successor.
    language = site.rsplit(".", 1)[1]
    core, layer = load(language)
    current(core, layer)
    ledger = json.loads((ROOT / f"languages/{language}/translation-provenance.json").read_text())
    (row,) = [r for r in ledger["sites"] if r["site"] == site]
    segment = row["segment"]
    source = next(s for s in core["segments"] if s["id"] == segment)
    assert row["source_sha256"] == canonical_hash(source_payload(source))
    assert (row["origin"], row["review"], row["familiar_core"]) == (
        "working-unsettled",
        "working",
        False,
    )
    original = deepcopy(row)
    target = layer["segments"][segment]["translation"]
    before_row, before_target = predecessor_wording(site, row, target)
    assert canonical_hash(before_target) == before_row["target_sha256"]
    try:
        if fault == "predecessor-digest":
            row["target_sha256"] = before_row["target_sha256"]
        elif fault == "review":
            row["review"] = "internally-reviewed"
        else:
            target += " altered"
        with pytest.raises(AssertionError, match=r"^unchanged wording$"):
            predecessor_wording(site, row, target)
    finally:
        row.clear()
        row.update(deepcopy(original))
        predecessor_wording(site, row, layer["segments"][segment]["translation"])


@pytest.mark.parametrize("language,word,expected", HELPS)
def test_contextual_help_and_same_copy_recovery(language, word, expected):
    core, layer = load(language)
    native(core, layer)
    saved = deepcopy(layer)
    assert layer["words"][word]["explanation"] == expected
    try:
        layer["words"][word]["explanation"] = "An unrelated subject is meant."
        with pytest.raises(AssertionError, match=r"^Lauda contextual help(?:\n|$)"):
            assert layer["words"][word]["explanation"] == expected, "Lauda contextual help"
    finally:
        layer.clear()
        layer.update(deepcopy(saved))
        native(core, layer)
        assert layer["words"][word]["explanation"] == expected


@pytest.mark.parametrize("language,word,fault", NOTE_FAULTS)
def test_actual_explanation_topology_and_same_container_restoration(language, word, fault):
    core, layer = load(language)
    saved_core, saved_layer = deepcopy(core), deepcopy(layer)
    native(core, layer)
    try:
        if fault == "declaration":
            del core["localization"]["explanations"][word]
        elif fault == "help":
            del layer["words"][word]["explanation"]
        else:
            core["localization"]["explanations"][word]["languages"] = [
                "pl" if language == "en" else "en"
            ]
        with pytest.raises(AssertionError, match=r"^Lauda native language$"):
            native(core, layer)
    finally:
        core.clear()
        core.update(deepcopy(saved_core))
        layer.clear()
        layer.update(deepcopy(saved_layer))
        assert (core, layer) == (saved_core, saved_layer)
        native(core, layer)

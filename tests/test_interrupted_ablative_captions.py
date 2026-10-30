"""Compact captions for interrupted ablative constructions and their unchanged controls."""

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest
from dies_irae_caption_fixture import restore_dies_irae_layer
from gospel_delivery_fixture import current_sung_source_hash
from michael_secret_fixture import control_expectation, ledger_expectation, predecessor_documents
from opening_caption_fixture import restore_opening_layer
from possessive_sweep_b1_successor_fixture import before_possessive_b1_layer
from possessive_sweep_b2_successor_fixture import before_possessive_b2_layer
from possessive_sweep_b3_successor_fixture import before_possessive_b3_layer

from checks import interlinear, language_packs, prose
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads(
    (ROOT / "tests/fixtures/interrupted-ablative-captions.json").read_text(encoding="utf-8")
)
SUCCESSORS = json.loads(
    (ROOT / "tests/fixtures/interrupted-ablative-successors.json").read_text(encoding="utf-8")
)
CONSTRUCTIONS = FIXTURE["constructions"]
CONTROLS = FIXTURE["controls"]
LEDGER = FIXTURE["ledger"]
(ELLIPSIS,) = FIXTURE["glosses"]
(NOTE,) = FIXTURE["explanations"]
LANGUAGES = ["pl", "en"]
LAYER_FIELDS = {("words", "gloss"), ("words", "explanation"), ("segments", "alignments")}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def core_path(text):
    return "texts/" + text.replace(".", "/", 1) + ".json"


def layer_path(text, language):
    return f"languages/{language}/{core_path(text)}"


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def row_id(row):
    first = row["group"]["words"][0] if "group" in row else row.get("word") or row["span"][0]
    return f"{row['language']}-{row['text'].split('.', 1)[1]}-{first}"


def site_id(row):
    return row["site"].split(".", 1)[1]


TEXTS = sorted({row["text"] for row in [*CONSTRUCTIONS, *CONTROLS, ELLIPSIS, NOTE]})
PATHS = sorted(
    {core_path(text) for text in TEXTS}
    | {layer_path(text, language) for text in TEXTS for language in LANGUAGES}
)
TOUCHED_LAYERS = sorted({op["path"] for op in FIXTURE["operations"]} - set(map(core_path, TEXTS)))


@pytest.fixture(scope="module")
def documents():
    return {path: load(path) for path in PATHS}


def segment_words(core, segment):
    (found,) = [s for s in core["segments"] if s["id"] == segment]
    return [word["id"] for word in found["words"]]


def parent_at(doc, pointer):
    parts = pointer.split("/")[1:]
    for part in parts[:-1]:
        doc = doc[int(part)] if isinstance(doc, list) else doc[part]
    return doc, parts[-1]


def reviewed_predecessor_documents(documents):
    """Undo exact reviewed captions/prose before the immutable historical inverse."""
    result = deepcopy(documents)
    for path, layer in result.items():
        if path.startswith("languages/en/texts/"):
            layer = before_possessive_b2_layer(before_possessive_b3_layer(layer))
            layer = before_possessive_b1_layer(layer)
            result[path] = restore_opening_layer(restore_dies_irae_layer(layer))
    for operation in reversed(SUCCESSORS["operations"]):
        parent, key = parent_at(result[operation["path"]], operation["pointer"])
        require(
            (key in parent) == operation["after"]["exists"], "reviewed successor field presence"
        )
        if key in parent:
            require(parent[key] == operation["after"]["value"], "reviewed successor field value")
        if operation["before"]["exists"]:
            parent[key] = deepcopy(operation["before"]["value"])
        else:
            del parent[key]
    return result


def historical_objects(documents):
    result = predecessor_documents(reviewed_predecessor_documents(documents))
    for operation in reversed(FIXTURE["operations"]):
        parent, key = parent_at(result[operation["path"]], operation["pointer"])
        require((key in parent) == operation["after"]["exists"], "successor field presence")
        if operation["after"]["exists"]:
            require(parent[key] == operation["after"]["value"], "successor field value")
        if operation["before"]["exists"]:
            parent[key] = deepcopy(operation["before"]["value"])
        else:
            del parent[key]
    return result


def assert_construction(core, layer, row):
    group = row["group"]
    members = group["words"]
    order = segment_words(core, row["segment"])
    start = order.index(members[0])
    require(order[start : start + len(members)] == members, "contiguous construction")
    require(2 <= len(members) <= 5 and group["anchor"] in members, "compact construction")
    groups = layer["segments"][row["segment"]].get("alignments", [])
    touching = [g for g in groups if set(g["words"]) & set(members)]
    require(touching == [group], "compact construction")
    require(all("gloss" not in layer["words"][wid] for wid in members), "once-only construction")


def assert_ellipsis(layer, row):
    groups = layer["segments"][row["segment"]].get("alignments", [])
    require(not [g for g in groups if row["word"] in g["words"]], "explicit ellipsis gloss")
    require(layer["words"][row["word"]].get("gloss") == row["gloss"], "explicit ellipsis gloss")


def assert_note(core, layer, row):
    requirement = (core["localization"].get("explanations") or {}).get(row["word"])
    require(requirement == row["requirement"], "parenthesis note scope")
    entry = layer["words"][row["word"]]
    if layer["language"] in row["requirement"]["languages"]:
        require(entry.get("explanation") == row["explanation"], "parenthesis note")
    else:
        require("explanation" not in entry, "parenthesis note scope")


def assert_control(layer, row):
    row = control_expectation(row)
    groups = layer["segments"][row["segment"]].get("alignments", [])
    touching = [g for g in groups if set(g["words"]) & set(row["span"])]
    grouped = {wid for g in touching for wid in g["words"]}
    direct = {wid: layer["words"][wid].get("gloss") for wid in row["span"] if wid not in grouped}
    require(touching == row["groups"] and direct == row["direct"], f"unchanged {row['class']}")


def assert_ledger(core, layer, entry, row):
    if row["site"] == SUCCESSORS["ledger_before"]["site"]:
        require(row == SUCCESSORS["ledger_before"], "reviewed historical ledger identity")
        row = {**row, "target_sha256": SUCCESSORS["target_sha256"]}
    row = ledger_expectation(row)
    segment_id = row["site"].split(".")[-2]
    (segment,) = [s for s in core["segments"] if s["id"] == segment_id]
    require(
        entry["source_sha256"] == canonical_hash(source_payload(segment)), "ledger source identity"
    )
    require(
        entry["target_sha256"] == canonical_hash(layer["segments"][segment_id]["translation"]),
        "ledger target identity",
    )
    keys = ("origin", "review", "familiar_core", "source_sha256", "target_sha256")
    expected = {key: row[key] for key in keys}
    expected["source_sha256"] = current_sung_source_hash(
        row["site"].rsplit(".", 2)[0], segment_id, row["source_sha256"]
    )
    require({key: entry[key] for key in keys} == expected, "ledger status")


def test_keyed_operations_leave_latin_prose_and_provenance_alone():
    operations = FIXTURE["operations"]
    assert len(operations) == 165
    assert len({(op["path"], op["pointer"]) for op in operations}) == 165
    for op in operations:
        if op["path"].startswith("texts/"):
            assert op["pointer"] == "/localization"
        else:
            assert op["path"].startswith(("languages/pl/texts/", "languages/en/texts/"))
            kind = tuple(op["pointer"].split("/")[1::2])
            assert kind in LAYER_FIELDS
    assert len(TOUCHED_LAYERS) == 32


def test_complete_historical_objects_survive_the_narrow_inverse(documents):
    snapshot = deepcopy(FIXTURE)
    restored = historical_objects(documents)
    touched = {op["path"] for op in FIXTURE["operations"]}
    assert {path: canonical_hash(restored[path]) for path in sorted(touched)} == (
        FIXTURE["historical_object_sha256"]
    )
    assert snapshot == FIXTURE
    for text, stale in (
        ("orationes.memorare", "be mindful"),
        ("proprium.cathedra-sancti-petri-secreta", "of Church"),
        ("proprium.commemoratio-omnium-fidelium-defunctorum-missa-i-sequentia", "day"),
    ):
        broken = deepcopy(documents)
        path = layer_path(text, "en")
        broken[path]["words"]["w001"]["gloss"] = stale
        assert broken != documents
        try:
            with pytest.raises(
                AssertionError,
                match=(
                    r"^reviewed Dies irae whole predecessor layer$"
                    if text == "proprium.commemoratio-omnium-fidelium-defunctorum-missa-i-sequentia"
                    else r"^reviewed opening caption$"
                ),
            ):
                historical_objects(broken)
        finally:
            broken.clear()
            broken.update(deepcopy(documents))
            assert broken == documents
            recovered = historical_objects(broken)
            assert {p: canonical_hash(recovered[p]) for p in sorted(touched)} == (
                FIXTURE["historical_object_sha256"]
            )
    saved = deepcopy(documents)
    successors = deepcopy(SUCCESSORS)
    for path, pointer, value in (
        (
            "languages/en/texts/proprium/sacratissimi-cordis-iesu-collecta.json",
            "/segments/s01/translation",
            "stale reviewed prose",
        ),
        ("languages/en/texts/litaniae/lauretanae.json", "/segments/s016/alignments", None),
        ("languages/en/texts/litaniae/lauretanae.json", "/segments/s016/alignments", []),
    ):
        broken = deepcopy(documents)
        parent, key = parent_at(broken[path], pointer)
        if value is None:
            del parent[key]
        else:
            parent[key] = value
        assert broken != saved
        try:
            with pytest.raises(AssertionError, match="reviewed successor field"):
                historical_objects(broken)
        finally:
            broken.clear()
            broken.update(deepcopy(saved))
            assert broken == saved
            recovered = historical_objects(broken)
            assert {p: canonical_hash(recovered[p]) for p in sorted(touched)} == (
                FIXTURE["historical_object_sha256"]
            )
    broken = deepcopy(documents)
    path = "languages/en/texts/proprium/sacratissimi-cordis-iesu-collecta.json"
    broken[path]["about"] += " unrelated"
    assert broken != saved
    assert (
        canonical_hash(historical_objects(broken)[path])
        != FIXTURE["historical_object_sha256"][path]
    )
    broken.clear()
    broken.update(deepcopy(saved))
    assert broken == saved
    recovered = historical_objects(broken)
    assert {p: canonical_hash(recovered[p]) for p in sorted(touched)} == (
        FIXTURE["historical_object_sha256"]
    )
    assert documents == saved and successors == SUCCESSORS and snapshot == FIXTURE


def test_construction_inventory_is_compact_and_per_language():
    assert Counter(row["language"] for row in CONSTRUCTIONS) == {"pl": 13, "en": 21}
    assert max(len(row["group"]["words"]) for row in CONSTRUCTIONS) == 5
    assert len({row_id(row) for row in CONSTRUCTIONS}) == len(CONSTRUCTIONS)
    assert Counter(row["class"] for row in CONTROLS) == {
        "inflected order": 18,
        "compact group": 29,
        "qualified long group": 4,
        "long clause group": 4,
        "attributive phrase": 3,
        "coordinated ellipsis": 1,
        "parenthesis": 1,
        "external possessor": 1,
    }


@pytest.mark.parametrize("row", CONSTRUCTIONS, ids=row_id)
def test_compact_construction(documents, row):
    core = documents[core_path(row["text"])]
    assert_construction(core, documents[layer_path(row["text"], row["language"])], row)


def test_coordinated_ellipsis_names_its_noun_in_english(documents):
    assert_ellipsis(documents[layer_path(ELLIPSIS["text"], "en")], ELLIPSIS)
    core = documents[core_path(ELLIPSIS["text"])]
    word = next(w for s in core["segments"] for w in s["words"] if w["id"] == ELLIPSIS["word"])
    assert (word["form"], word["morph"]["case"], word["head"]) == ("futúris", "abl", "w015")


@pytest.mark.parametrize("language", LANGUAGES)
def test_parenthesis_note_is_polish_only(documents, language):
    core = documents[core_path(NOTE["text"])]
    layer = documents[layer_path(NOTE["text"], language)]
    assert_note(core, layer, NOTE)
    assert language_packs.check_core(core) == []
    path = ROOT / layer_path(NOTE["text"], language)
    assert language_packs.check_layer(core, layer, path) == []
    assert prose.check(layer) == []


@pytest.mark.parametrize("path", TOUCHED_LAYERS)
def test_every_touched_layer_has_once_only_memberships(documents, path):
    text = documents[path]["text"]
    core, layer = documents[core_path(text)], documents[path]
    counts = Counter(wid for wid, entry in layer["words"].items() if entry.get("gloss"))
    counts.update(
        wid
        for segment in layer["segments"].values()
        for group in segment.get("alignments", [])
        for wid in group["words"]
    )
    assert counts == Counter(w["id"] for s in core["segments"] for w in s.get("words", []))
    assert interlinear.check(core, layer) == []


@pytest.mark.parametrize("row", CONTROLS, ids=row_id)
def test_unchanged_control(documents, row):
    assert_control(documents[layer_path(row["text"], row["language"])], row)


@pytest.mark.parametrize("row", LEDGER, ids=site_id)
def test_ledger_keeps_status_and_exact_relations(documents, row):
    text = next(t for t in TEXTS if row["site"].startswith(f"{t}."))
    language = row["site"].rsplit(".", 1)[1]
    ledger = load(f"languages/{language}/translation-provenance.json")["sites"]
    (entry,) = [site for site in ledger if site["site"] == row["site"]]
    core, layer = documents[core_path(text)], documents[layer_path(text, language)]
    assert_ledger(core, layer, entry, row)
    if row["site"] == SUCCESSORS["ledger_before"]["site"]:
        saved = deepcopy(entry)
        broken = deepcopy(entry)
        try:
            broken["target_sha256"] = row["target_sha256"]
            assert broken != saved
            with pytest.raises(AssertionError, match="ledger target identity"):
                assert_ledger(core, layer, broken, row)
        finally:
            broken.clear()
            broken.update(deepcopy(saved))
            assert broken == saved
            assert_ledger(core, layer, broken, row)
        historical = deepcopy(row)
        historical["review"] = "expert-reviewed"
        assert historical != row
        with pytest.raises(AssertionError, match="reviewed historical ledger identity"):
            assert_ledger(core, layer, entry, historical)
        assert_ledger(core, layer, entry, row)


def construction(text, language, first):
    (row,) = [
        r
        for r in CONSTRUCTIONS
        if (r["text"], r["language"], r["group"]["words"][0]) == (text, language, first)
    ]
    return row


LITANY = "litaniae.lauretanae"
TENTH = "proprium.dominica-x-post-pentecosten-postcommunio"


def split_restored(layer, row):
    groups = layer["segments"][row["segment"]]["alignments"]
    groups.remove(row["group"])
    groups.extend(row["historical"]["groups"])
    groups.sort(key=lambda g: int(g["words"][0][1:]))
    for wid, gloss in row["historical"]["direct"].items():
        layer["words"][wid]["gloss"] = gloss


def caption_changed(layer, row):
    (group,) = [g for g in layer["segments"][row["segment"]]["alignments"] if g == row["group"]]
    group["gloss"] = "with divine You do not cease to restore sacraments"


def anchor_moved(layer, row):
    (group,) = [g for g in layer["segments"][row["segment"]]["alignments"] if g == row["group"]]
    group["anchor"] = group["words"][0]


def contained_group_restored(layer, row):
    groups = layer["segments"][row["segment"]]["alignments"]
    groups.insert(1, {"words": ["w009", "w010"], "anchor": "w010", "gloss": "You do not cease"})


def direct_gloss_duplicated(layer, row):
    layer["words"]["w010"]["gloss"] = "przestajesz"


MUTANTS = [
    ("split-restored", LITANY, "pl", "w382", split_restored, "compact construction"),
    ("caption-changed", TENTH, "en", "w007", caption_changed, "compact construction"),
    ("anchor-moved", TENTH, "en", "w012", anchor_moved, "compact construction"),
    ("contained-group-restored", TENTH, "en", "w007", contained_group_restored, None),
    ("direct-gloss-duplicated", TENTH, "pl", "w007", direct_gloss_duplicated, None),
]


@pytest.mark.parametrize(
    "defect,text,language,first,mutate,message", MUTANTS, ids=[m[0] for m in MUTANTS]
)
def test_construction_guard_rejects_owned_mutants_and_restores(
    documents, defect, text, language, first, mutate, message
):
    snapshot = deepcopy(documents)
    core, layer = documents[core_path(text)], documents[layer_path(text, language)]
    layer = before_possessive_b3_layer(layer)
    row = construction(text, language, first)
    assert_construction(core, layer, row)
    broken = deepcopy(layer)
    mutate(broken, row)
    assert broken != layer
    with pytest.raises(AssertionError) as caught:
        assert_construction(core, broken, row)
    if defect == "contained-group-restored":
        assert str(caught.value) == "compact construction"
        assert f"{text}:s01:alignment-2:en: w009 belongs to more than one alignment" in (
            interlinear.check(core, broken)
        )
    elif defect == "direct-gloss-duplicated":
        assert str(caught.value) == "once-only construction"
        assert f"{text}:w010:pl: expected exactly one direct gloss or alignment" in (
            interlinear.check(core, broken)
        )
    else:
        assert str(caught.value) == message
    assert_construction(core, layer, row)
    assert interlinear.check(core, layer) == []
    assert documents == snapshot


def test_stranded_ellipsis_is_rejected_and_restored(documents):
    snapshot = deepcopy(documents)
    layer = documents[layer_path(ELLIPSIS["text"], "en")]
    broken = deepcopy(layer)
    broken["words"][ELLIPSIS["word"]]["gloss"] = ELLIPSIS["historical"]
    with pytest.raises(AssertionError) as caught:
        assert_ellipsis(broken, ELLIPSIS)
    assert str(caught.value) == "explicit ellipsis gloss"
    assert_ellipsis(layer, ELLIPSIS)
    assert documents == snapshot


@pytest.mark.parametrize("defect", ["omitted", "widened", "semicolon"])
def test_parenthesis_note_mutants_fail_their_actual_checks(documents, defect):
    snapshot = deepcopy(documents)
    core = documents[core_path(NOTE["text"])]
    polish = documents[layer_path(NOTE["text"], "pl")]
    english = documents[layer_path(NOTE["text"], "en")]
    where = {lang: ROOT / layer_path(NOTE["text"], lang) for lang in LANGUAGES}
    broken_core, broken_pl = deepcopy(core), deepcopy(polish)
    if defect == "omitted":
        del broken_pl["words"][NOTE["word"]]["explanation"]
        message = f"pl:{NOTE['text']}: explanation topology differs — missing=['w002'] extra=[]"
        assert message in language_packs.check_layer(core, broken_pl, where["pl"])
        with pytest.raises(AssertionError) as caught:
            assert_note(core, broken_pl, NOTE)
        assert str(caught.value) == "parenthesis note"
    elif defect == "widened":
        broken_core["localization"]["explanations"][NOTE["word"]] = {}
        message = f"en:{NOTE['text']}: explanation topology differs — missing=['w002'] extra=[]"
        assert message in language_packs.check_layer(broken_core, english, where["en"])
        with pytest.raises(AssertionError) as caught:
            assert_note(broken_core, english, NOTE)
        assert str(caught.value) == "parenthesis note scope"
    else:
        entry = broken_pl["words"][NOTE["word"]]
        entry["explanation"] = entry["explanation"].replace("”. Wtrącenie", "”; wtrącenie", 1)
        assert entry["explanation"] != NOTE["explanation"]
        assert any("uses a semicolon" in error for error in prose.check(broken_pl))
    for language, layer in (("pl", polish), ("en", english)):
        assert_note(core, layer, NOTE)
        assert language_packs.check_layer(core, layer, where[language]) == []
    assert documents == snapshot


def control(cls):
    return next(row for row in CONTROLS if row["class"] == cls)


def regroup_span(layer, row):
    groups = layer["segments"][row["segment"]].setdefault("alignments", [])
    for wid in row["span"]:
        layer["words"][wid].pop("gloss", None)
    groups[:] = [g for g in groups if not set(g["words"]) & set(row["span"])]
    groups.append({"words": sorted(row["span"]), "anchor": row["span"][0], "gloss": "regrouped"})
    groups.sort(key=lambda g: int(g["words"][0][1:]))


def recaption_group(layer, row):
    (group,) = [g for g in layer["segments"][row["segment"]]["alignments"] if g == row["groups"][0]]
    group["gloss"] += " again"


CONTROL_CLASSES = [
    "inflected order",
    "attributive phrase",
    "coordinated ellipsis",
    "compact group",
    "qualified long group",
    "long clause group",
    "parenthesis",
    "external possessor",
]


@pytest.mark.parametrize("cls", CONTROL_CLASSES)
def test_control_guard_rejects_a_regrouped_or_recaptioned_control(documents, cls):
    snapshot = deepcopy(documents)
    row = control(cls)
    layer = documents[layer_path(row["text"], row["language"])]
    assert_control(layer, row)
    broken = deepcopy(layer)
    (recaption_group if row["groups"] else regroup_span)(broken, row)
    assert broken != layer
    with pytest.raises(AssertionError) as caught:
        assert_control(broken, row)
    assert str(caught.value) == f"unchanged {cls}"
    assert_control(layer, row)
    assert documents == snapshot


@pytest.mark.parametrize("field", ["source_sha256", "target_sha256", "review"])
def test_ledger_guard_rejects_a_stale_or_promoted_row(documents, field):
    row = LEDGER[0]
    text = next(t for t in TEXTS if row["site"].startswith(f"{t}."))
    language = row["site"].rsplit(".", 1)[1]
    core, layer = documents[core_path(text)], documents[layer_path(text, language)]
    entry = deepcopy(row)
    assert_ledger(core, layer, entry, row)
    entry[field] = "0" * 64 if field.endswith("sha256") else "expert-reviewed"
    with pytest.raises(AssertionError) as caught:
        assert_ledger(core, layer, entry, row)
    expected = {
        "source_sha256": "ledger source identity",
        "target_sha256": "ledger target identity",
        "review": "ledger status",
    }[field]
    assert str(caught.value) == expected
    assert_ledger(core, layer, deepcopy(row), row)

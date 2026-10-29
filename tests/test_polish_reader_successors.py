"""Selected Polish relations keep their source, referents and genuine native inputs."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import documentary_successor_fixture as documentary
import pytest
from polish_reader_successor_fixture import (
    DATA,
    RULE,
    before_apostles_role_comparison,
    before_polish_reader_bytes,
    before_polish_reader_core,
    before_polish_reader_ledger,
    before_polish_reader_wording,
)
from prayer_prose_successor_fixture import AFTER, BEFORE, before_prayer_prose_ledger
from requiem_successor_fixture import DATA as REQUIEM
from requiem_successor_fixture import before_requiem_bytes, before_requiem_ledger

from build_reader import emit, store
from build_reader.bibliography_bindings import digest
from checks import interlinear, translation_provenance
from checks.language_packs import check_core, check_layer
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
TEXTS = DATA["texts"]
GROUPS = DATA["groups"]
REFERENCES = DATA["divine_references"]
NOTE_CASES = DATA["cores"]
NOTE_FAULTS = [
    (case, fault)
    for case in NOTE_CASES
    for fault in ("missing-declaration", "en-leak", "extra-declaration")
]
GROUP_FAULTS = [
    (group, fault)
    for group in GROUPS
    for fault in ("duplicate-direct", "foreign-anchor", "missing-group")
]
LEDGER_FAULTS = [
    (change, fault)
    for change in RULE["rows"]
    for fault in ("target", "source", "origin", "review", "familiar", "order")
]
NATIVE_FAULTS = [
    (change, field)
    for change in RULE["rows"]
    for field in ("target", "source", "origin", "review", "familiar")
]


def read(relative, root=ROOT):
    return json.loads((root / relative).read_bytes())


def case_of(identity):
    return next(case for case in TEXTS if case["id"] == identity)


def subject(case):
    return store.core(ROOT, case["text"]), store.raw_layer(ROOT, "pl", case["text"])


def segment(core, identity):
    return next(row for row in core["segments"] if row["id"] == identity)


def group_of(layer, words):
    matches = [
        group
        for entry in layer["segments"].values()
        for group in entry.get("alignments", [])
        if group["words"] == words
    ]
    assert len(matches) == 1
    return matches[0]


def region_providers(source, layer, ids):
    groups = interlinear.alignments_for(layer, source["id"])
    shared = {word: group for group in groups for word in group["words"]}
    result = []
    for word in source["words"]:
        wid = word["id"]
        if wid not in ids:
            continue
        if wid in shared:
            group = shared[wid]
            assert set(group["words"]) <= set(ids), "Polish region boundary"
            if wid == group["words"][0]:
                result.append({key: group[key] for key in ("words", "anchor", "gloss")})
        else:
            result.append({"words": [wid], "gloss": layer["words"][wid]["gloss"]})
    return result


def assert_regions(case, core, layer):
    """The finite adopted readings are separate from general native shape validity."""
    assert core["id"] == layer["text"] == case["text"]
    assert interlinear.check(core, layer) == [], "Polish provider structure"
    for sid, signature in case["source_signatures"].items():
        assert canonical_hash(source_payload(segment(core, sid))) == signature, (
            "Polish source signature"
        )
    for region in case["regions"]:
        source = segment(core, region["segment"])
        ids = [word[0] for word in region["words"]]
        actual_words = [[w["id"], w["form"]] for w in source["words"] if w["id"] in ids]
        assert actual_words == region["words"], "Polish source word backmap"
        actual = region_providers(source, layer, ids)
        assert actual == region["providers"], "Polish adopted providers"
        assert [wid for provider in actual for wid in provider["words"]] == ids
    for wid, explanation in case["explanations"].items():
        assert layer["words"][wid]["explanation"] == explanation, "Polish contextual explanation"
    for sid, prose in case["prose"].items():
        assert layer["segments"][sid]["translation"] == prose, "Polish full prose"


def assert_postcommunion(layer):
    prose = layer["segments"]["s01"]["translation"]
    assert prose.startswith(
        "Niech święte spożycie Twego sakramentu, Panie, odnowi nas i, oczyściwszy "
        "z tego, co stare, sprawi, że dostąpimy udziału w zbawiennej tajemnicy. "
    ), "Polish prayer cause and participation"
    shared = group_of(layer, [f"w{number:03}" for number in range(12, 18)])
    assert shared["gloss"] == ("niech sprawi, że dostąpimy udziału w zbawczym misterium"), (
        "Polish participation caption"
    )
    assert layer["words"]["w007"]["gloss"] == "niech odnowi"


def assert_fear(layer, identity):
    for expected in GROUPS:
        if expected["case"] == identity:
            assert group_of(layer, expected["words"])["gloss"] == expected["gloss"], (
                "Polish selected fear construction"
            )
    if identity == "lent-tract":
        assert [
            layer["words"][wid]["gloss"] for wid in ("w054", "w057", "w062", "w068", "w069")
        ] == ["nocnego", "lecącej", "krążącej", "demona", "południowego"], (
            "Polish selected fear construction"
        )
        assert layer["words"]["w050"]["gloss"] == "nie"
        assert layer["words"]["w051"]["gloss"] == "ulękniesz się"
        assert layer["words"]["w067"]["gloss"] == "i"
    else:
        assert layer["words"]["w019"]["gloss"] == "nie"
        assert layer["words"]["w020"]["gloss"] == "będzie się lękał"


def assert_divine_references(layer):
    prose = layer["segments"]["s01"]["translation"]
    for reference in REFERENCES:
        assert layer["words"][reference["word"]]["gloss"] == reference["caption"], (
            "Polish divine caption referent"
        )
        assert prose.count(reference["prose_phrase"]) == 1, "Polish divine prose referent"
    for control in DATA["caption_controls"]:
        assert layer["words"][control["word"]]["gloss"] == control["gloss"], (
            "Polish human or reflexive control"
        )
    assert "Bo On wybawił mnie z sidła łowców" in prose
    assert "swoimi ramionami" in prose and "swoim Aniołom" in prose
    assert "swoją stopą" in prose


@pytest.mark.parametrize("case", TEXTS, ids=lambda case: case["id"])
def test_actual_polish_regions_keep_source_and_provider_backmap(case):
    core, layer = subject(case)
    path = store.layer_path(ROOT, "pl", case["text"])
    assert check_layer(core, layer, path) == []
    assert_regions(case, core, layer)
    assert (
        hashlib.sha256((ROOT / case["source"]).read_bytes()).hexdigest()
        == (case["source_raw_sha256"])
    )
    assert hashlib.sha256(path.read_bytes()).hexdigest() == case["layer_after_sha256"]
    if case["id"] == "lent-postcommunion":
        assert_postcommunion(layer)
    elif case["id"] == "lent-tract":
        assert_fear(layer, case["id"])
        assert_divine_references(layer)
    elif case["id"] == "all-souls-gradual":
        assert_fear(layer, case["id"])
    else:
        assert_andrew_relation(layer, case["id"])


@pytest.mark.parametrize("case", TEXTS, ids=lambda case: case["id"])
def test_exact_layer_inverses_keep_all_unselected_material(case):
    raw = (ROOT / case["layer"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == case["layer_after_sha256"]
    comparison = raw
    for operation in reversed(case["layer_inverse_operations"]):
        after, before = operation["after"].encode(), operation["before"].encode()
        assert comparison.count(after) == 1
        comparison = comparison.replace(after, before, 1)
    assert hashlib.sha256(comparison).hexdigest() == case["layer_before_sha256"]
    assert (ROOT / case["layer"]).read_bytes() == raw


@pytest.fixture(scope="module")
def complete_polish_reader(emitted_book):
    assert emit.verify(ROOT, emitted_book[0]) == []
    return emitted_book[0]


@pytest.mark.parametrize("case", TEXTS, ids=lambda case: case["id"])
@pytest.mark.usefixtures("complete_polish_reader")
def test_actual_complete_reader_fault_restores_same_artifact(reader_copy, case):
    relative = case["text"].replace(".", "/", 1)
    artifact = read(f"texts/{relative}.json", reader_copy)
    path = reader_copy / f"languages/pl/texts/{relative}.json"
    saved = path.read_bytes()
    localized = json.loads(saved)
    tables = [
        read("tables/morphology.json", reader_copy),
        read("tables/analysis.json", reader_copy),
        read("tables/citations.json", reader_copy),
        read("languages/pl/citations.json", reader_copy),
    ]
    core, layer = emit.expand(artifact, localized, *tables)
    assert_regions(case, core, layer)
    fault = case["artifact_fault"]
    source = segment(core, fault["segment"])
    ids = [word["id"] for word in source["words"]]
    start = ids.index(fault["words"][0])
    row = next(row for row in localized["seg"] if row["id"] == fault["segment"])
    if fault["kind"] == "group":
        selected = [g for g in row["a"] if g["s"] == start and g["n"] == len(fault["words"])]
        assert len(selected) == 1 and selected[0]["g"] == fault["expected_gloss"]
        locator = f"pl.segments.{fault['segment']}.alignments[{fault['alignment_index']}].gloss:"
    else:
        assert fault["kind"] == "direct" and row["g"][start] == fault["expected_gloss"]
        assert not any(g["s"] <= start < g["s"] + g["n"] for g in row.get("a", []))
        locator = f"pl.words.{fault['words'][0]}.gloss:"
    same_path = path
    try:
        if fault["kind"] == "group":
            selected[0]["g"] = fault["wrong_gloss"]
        else:
            row["g"][start] = fault["wrong_gloss"]
        path.write_text(json.dumps(localized, ensure_ascii=False), encoding="utf-8")
        assert path.read_bytes() != saved
        errors = emit.verify(ROOT, reader_copy)
        assert any(f"{case['text']}: {locator}" in error for error in errors)
    finally:
        path.write_bytes(saved)
    assert path is same_path and path.read_bytes() == saved
    assert emit.verify(ROOT, reader_copy) == []
    restored = read(f"languages/pl/texts/{relative}.json", reader_copy)
    assert_regions(case, *emit.expand(artifact, restored, *tables))


@pytest.mark.parametrize("fault", ["changed-cause", "old-endpoint"])
def test_postcommunion_keeps_cause_and_participation(fault):
    core, actual = subject(case_of("lent-postcommunion"))
    saved, same_input = deepcopy(actual), actual
    assert_postcommunion(actual)
    try:
        if fault == "changed-cause":
            text = actual["segments"]["s01"]["translation"]
            old = "sprawi, że dostąpimy"
            assert text.count(old) == 1
            actual["segments"]["s01"]["translation"] = text.replace(old, "sprawimy, że dostąpi", 1)
            label = "Polish prayer cause and participation"
        else:
            group_of(actual, [f"w{n:03}" for n in range(12, 18)])["gloss"] = (
                "niech sprawi, że przejdziemy do wspólnoty zbawczego misterium"
            )
            label = "Polish participation caption"
        assert actual != saved and interlinear.check(core, actual) == []
        with pytest.raises(AssertionError, match=rf"^{label}(?:\n|$)"):
            assert_postcommunion(actual)
    finally:
        actual.clear()
        actual.update(deepcopy(saved))
    assert actual is same_input and actual == saved
    assert_postcommunion(actual)


@pytest.mark.parametrize("fault", ["wrong-inflection", "neutral-affair", "bad-news-preposition"])
def test_selected_fear_relations_reject_and_recover(fault):
    identity = "all-souls-gradual" if fault == "bad-news-preposition" else "lent-tract"
    core, actual = subject(case_of(identity))
    saved, same_input = deepcopy(actual), actual
    assert_fear(actual, identity)
    try:
        if fault == "wrong-inflection":
            actual["words"]["w054"]["gloss"] = "nocnym"
        elif fault == "neutral-affair":
            group_of(actual, ["w060", "w061"])["gloss"] = "sprawy"
        else:
            group_of(actual, ["w016", "w017"])["gloss"] = "z wieści"
        assert actual != saved and interlinear.check(core, actual) == []
        with pytest.raises(AssertionError, match=r"^Polish selected fear construction(?:\n|$)"):
            assert_fear(actual, identity)
    finally:
        actual.clear()
        actual.update(deepcopy(saved))
    assert actual is same_input and actual == saved
    assert_fear(actual, identity)


@pytest.mark.parametrize("reference", REFERENCES, ids=lambda reference: reference["word"])
def test_each_divine_reference_stays_correct_in_both_surfaces(reference):
    core, actual = subject(case_of("lent-tract"))
    saved, same_input = deepcopy(actual), actual
    assert_divine_references(actual)
    for surface in ("prose", "caption"):
        try:
            if surface == "prose":
                text = actual["segments"]["s01"]["translation"]
                assert text.count(reference["prose_phrase"]) == 1
                actual["segments"]["s01"]["translation"] = text.replace(
                    reference["prose_phrase"], reference["lower_prose_phrase"], 1
                )
                label = "Polish divine prose referent"
            else:
                actual["words"][reference["word"]]["gloss"] = reference["caption"].lower()
                label = "Polish divine caption referent"
            assert actual != saved and interlinear.check(core, actual) == []
            with pytest.raises(AssertionError, match=rf"^{label}(?:\n|$)"):
                assert_divine_references(actual)
        finally:
            actual.clear()
            actual.update(deepcopy(saved))
        assert actual is same_input and actual == saved
        assert_divine_references(actual)


@pytest.mark.parametrize("fault", ["human-first-person", "divine-reflexive"])
def test_human_and_reflexive_controls_do_not_become_divine(fault):
    core, actual = subject(case_of("lent-tract"))
    saved, same_input = deepcopy(actual), actual
    assert_divine_references(actual)
    try:
        wid = "w028" if fault == "human-first-person" else "w087"
        current = actual["words"][wid]["gloss"]
        actual["words"][wid]["gloss"] = current[0].upper() + current[1:]
        assert actual != saved and interlinear.check(core, actual) == []
        with pytest.raises(AssertionError, match=r"^Polish human or reflexive control(?:\n|$)"):
            assert_divine_references(actual)
    finally:
        actual.clear()
        actual.update(deepcopy(saved))
    assert actual is same_input and actual == saved
    assert_divine_references(actual)


@pytest.mark.parametrize(
    "group,fault",
    GROUP_FAULTS,
    ids=[f"{group['id']}-{fault}" for group, fault in GROUP_FAULTS],
)
def test_native_short_group_fault_rejects_then_recovers(group, fault):
    core, actual = subject(case_of(group["case"]))
    saved, same_input = deepcopy(actual), actual
    assert interlinear.check(core, actual) == []
    try:
        current = group_of(actual, group["words"])
        if fault == "duplicate-direct":
            actual["words"][group["words"][0]]["gloss"] = current["gloss"]
            diagnostic = "expected exactly one direct gloss or alignment"
        elif fault == "foreign-anchor":
            current["anchor"] = "w999"
            diagnostic = "anchor must name the source word carrying the gloss"
        else:
            actual["segments"][group["segment"]]["alignments"].remove(current)
            if not actual["segments"][group["segment"]]["alignments"]:
                del actual["segments"][group["segment"]]["alignments"]
            diagnostic = "expected exactly one direct gloss or alignment"
        assert actual != saved
        assert any(diagnostic in message for message in interlinear.check(core, actual))
    finally:
        actual.clear()
        actual.update(deepcopy(saved))
    assert actual is same_input and actual == saved
    assert interlinear.check(core, actual) == []


def test_exact_polish_ledger_inverse_recovers_all_prior_frames():
    relative = RULE["relative"]
    raw = (ROOT / relative).read_bytes()
    actual = json.loads(raw)
    saved = deepcopy(actual)
    before = before_polish_reader_ledger(relative, actual)
    before_raw = before_polish_reader_bytes(relative, raw)
    assert digest(actual) == RULE["after_canonical_sha256"]
    assert hashlib.sha256(raw).hexdigest() == RULE["after_raw_sha256"]
    assert digest(before) == RULE["before_canonical_sha256"]
    assert hashlib.sha256(before_raw).hexdigest() == RULE["before_raw_sha256"]
    assert json.loads(before_raw) == before
    assert [
        i
        for i, pair in enumerate(zip(actual["sites"], before["sites"], strict=True))
        if pair[0] != pair[1]
    ] == [row["index"] for row in RULE["rows"]]
    with pytest.raises(AssertionError, match=r"^Polish reader current ledger(?:\n|$)"):
        before_polish_reader_ledger(relative, before)
    with pytest.raises(AssertionError, match=r"^exact Polish reader comparison bytes(?:\n|$)"):
        before_polish_reader_bytes(relative, before_raw)
    with pytest.raises(AssertionError, match=r"^exact Polish reader comparison bytes(?:\n|$)"):
        before_polish_reader_bytes(relative, raw + b" ")
    assert digest(before_requiem_ledger(relative, actual)) == AFTER["pl"]
    assert digest(before_prayer_prose_ledger(relative, actual)) == BEFORE["pl"]
    assert (
        digest(documentary.before_language_successors(relative, actual))
        == (documentary.DATA["ledgers"][relative]["before_sha256"])
    )
    assert (
        hashlib.sha256(before_requiem_bytes(relative, raw)).hexdigest()
        == (REQUIEM["raw"][relative]["before_sha256"])
    )
    assert before is not actual and actual == saved and (ROOT / relative).read_bytes() == raw
    other = "languages/en/translation-provenance.json"
    other_raw = (ROOT / other).read_bytes()
    other_value = json.loads(other_raw)
    assert before_polish_reader_ledger(other, other_value) is other_value
    assert before_polish_reader_bytes(other, other_raw) is other_raw


@pytest.mark.parametrize(
    "change,fault",
    LEDGER_FAULTS,
    ids=[f"{change['id']}-{fault}" for change, fault in LEDGER_FAULTS],
)
def test_current_ledger_drift_rejects_and_recovers_same_objects(change, fault):
    raw = (ROOT / RULE["relative"]).read_bytes()
    actual = json.loads(raw)
    saved, same_input = deepcopy(actual), actual
    sites, index = actual["sites"], change["index"]
    row = sites[index]
    original_row, original_order = deepcopy(row), list(sites)
    damaged = bytearray(raw)
    same_bytes = damaged
    assert json.dumps(actual, ensure_ascii=False, indent=2).encode() + b"\n" == raw
    expected = before_polish_reader_ledger(RULE["relative"], actual)
    expected_raw = before_polish_reader_bytes(RULE["relative"], raw)
    try:
        if fault == "order":
            sites[index], sites[index + 1] = sites[index + 1], sites[index]
        elif fault in ("target", "source"):
            row[f"{fault}_sha256"] = "0" * 64
        elif fault == "origin":
            row["origin"] = "own"
        elif fault == "review":
            row["review"] = "internally-reviewed"
        else:
            assert fault == "familiar"
            row["familiar_core"] = not row["familiar_core"]
        assert actual != saved
        damaged[:] = json.dumps(actual, ensure_ascii=False, indent=2).encode() + b"\n"
        assert json.loads(damaged) == actual
        # Complete comparison frames reject even metadata alternatives that a public
        # classification validator cannot decide, such as own versus working-unsettled.
        with pytest.raises(AssertionError, match=r"^Polish reader current ledger(?:\n|$)"):
            before_polish_reader_ledger(RULE["relative"], actual)
        with pytest.raises(AssertionError, match=r"^exact Polish reader comparison bytes(?:\n|$)"):
            before_polish_reader_bytes(RULE["relative"], damaged)
        assert actual is same_input and sites[index if fault != "order" else index + 1] is row
    finally:
        row.clear()
        row.update(deepcopy(original_row))
        sites[:] = original_order
        damaged[:] = raw
    assert actual is same_input and actual == saved and actual["sites"] is sites
    assert sites[index] is row and row == original_row
    assert damaged is same_bytes and bytes(damaged) == raw
    assert before_polish_reader_ledger(RULE["relative"], actual) == expected
    assert before_polish_reader_bytes(RULE["relative"], damaged) == expected_raw


@pytest.mark.parametrize(
    "change,field",
    NATIVE_FAULTS,
    ids=[f"{change['id']}-{field}" for change, field in NATIVE_FAULTS],
)
def test_native_provenance_sees_original_row_before_comparison(change, field, monkeypatch):
    relative, site = RULE["relative"], change["after"]["site"]
    raw = (ROOT / relative).read_bytes()
    ledger = json.loads(raw)
    saved_ledger = deepcopy(ledger)
    recorded, errors = translation_provenance.load(ROOT)
    assert errors == [] and recorded[site] == change["after"]
    saved_recorded = deepcopy(recorded)
    row = recorded[site]
    original = deepcopy(row)
    ledger["sites"][change["index"]] = row
    calls = []

    def actual_recorded_input(corpus):
        assert corpus == ROOT
        calls.append(recorded)
        return recorded, []

    monkeypatch.setattr(translation_provenance, "load", actual_recorded_input)
    assert translation_provenance.check(ROOT)[0] == []
    expected = before_polish_reader_ledger(relative, ledger)
    try:
        if field in ("target", "source"):
            row[f"{field}_sha256"] = "0" * 64
            diagnostic = f"{site}: stale {field}_sha256"
        elif field == "origin":
            row["origin"] = "public-domain"
            diagnostic = f"{site}: origin=public-domain requires a wording citation"
        elif field == "review":
            row["review"] = "internally-reviewed"
            diagnostic = f"{site}: unsettled origin cannot claim review=internally-reviewed"
        else:
            assert field == "familiar"
            row["familiar_core"] = not row["familiar_core"]
            diagnostic = f"{site}: stale or incorrect familiar_core"
        messages, _ = translation_provenance.check(ROOT)
        assert diagnostic in messages
        assert calls[-1] is recorded and recorded[site] is ledger["sites"][change["index"]] is row
        assert row != original
        # Only after the real current API has rejected this same damaged row
        # does the historical comparison entry inspect it.
        with pytest.raises(AssertionError, match=r"^Polish reader current ledger(?:\n|$)"):
            before_polish_reader_ledger(relative, ledger)
    finally:
        row.clear()
        row.update(deepcopy(original))
    assert recorded[site] is ledger["sites"][change["index"]] is row
    assert row == original and recorded == saved_recorded and ledger == saved_ledger
    assert translation_provenance.check(ROOT)[0] == []
    assert before_polish_reader_ledger(relative, ledger) == expected
    assert (ROOT / relative).read_bytes() == raw


def test_inflected_zero_alternative_is_valid_native_topology():
    case = case_of("lent-tract")
    core, actual = subject(case)
    saved, same_input = deepcopy(actual), actual
    assert_regions(case, core, actual)
    try:
        groups = actual["segments"]["s01"]["alignments"]
        index = next(i for i, group in enumerate(groups) if group["words"] == ["w052", "w053"])
        groups[index] = {"words": ["w052"], "reason": "inflection"}
        actual["words"]["w053"]["gloss"] = "strachu"
        assert actual != saved
        assert interlinear.check(core, actual) == []
        assert check_layer(core, actual, store.layer_path(ROOT, "pl", case["text"])) == []
        assert actual["segments"]["s01"]["translation"] == saved["segments"]["s01"]["translation"]
    finally:
        actual.clear()
        actual.update(deepcopy(saved))
    assert actual is same_input and actual == saved
    assert_regions(case, core, actual)


def assert_andrew_relation(layer, identity):
    if identity == "andrew-alleluia":
        assert layer["words"]["w006"]["gloss"] == "jako", "Polish adopted fragrance relation"
    elif identity == "apostles-preface":
        assert layer["segments"]["s04"]["translation"].endswith("jako zastępców w Twoim dziele."), (
            "Polish adopted pastoral role prose"
        )
        assert group_of(layer, ["w033", "w034", "w035"])["gloss"] == (
            "zastępcami w Twoim dziele"
        ), "Polish adopted pastoral role caption"
    else:
        assert identity == "andrew-secret"
        assert layer["words"]["w014"]["gloss"] == "którego", "Polish adopted relative referent"


@pytest.mark.parametrize(
    "fault", ["alleluia-preposition", "apostles-prose", "apostles-caption", "secret-relative"]
)
def test_admitted_andrew_relations_reject_predecessors_and_recover(fault):
    identity = {
        "alleluia-preposition": "andrew-alleluia",
        "apostles-prose": "apostles-preface",
        "apostles-caption": "apostles-preface",
        "secret-relative": "andrew-secret",
    }[fault]
    case = case_of(identity)
    core, actual = subject(case)
    saved, same_input = deepcopy(actual), actual
    assert_andrew_relation(actual, identity)
    try:
        if fault == "alleluia-preposition":
            actual["words"]["w006"]["gloss"] = "na"
            label = "Polish adopted fragrance relation"
        elif fault == "apostles-prose":
            actual["segments"]["s04"]["translation"] = DATA["apostles_wording"]["before_target"]
            label = "Polish adopted pastoral role prose"
        elif fault == "apostles-caption":
            group_of(actual, ["w033", "w034", "w035"])["gloss"] = "zastępcami Twojego dzieła"
            label = "Polish adopted pastoral role caption"
        else:
            actual["words"]["w014"]["gloss"] = "czyjej"
            label = "Polish adopted relative referent"
        assert actual != saved and interlinear.check(core, actual) == []
        assert check_layer(core, actual, ROOT / case["layer"]) == []
        with pytest.raises(AssertionError, match=rf"^{label}(?:\n|$)"):
            assert_andrew_relation(actual, identity)
    finally:
        actual.clear()
        actual.update(deepcopy(saved))
    assert actual is same_input and actual == saved
    assert_andrew_relation(actual, identity)
    assert_regions(case, core, actual)


@pytest.mark.parametrize("case", NOTE_CASES, ids=lambda case: case["id"])
def test_pl_only_notes_preserve_source_and_english(case):
    core = store.core(ROOT, case["text"])
    pl = store.raw_layer(ROOT, "pl", case["text"])
    english = store.raw_layer(ROOT, "en", case["text"])
    saved = deepcopy(core)
    assert check_core(core) == []
    assert check_layer(core, pl, store.layer_path(ROOT, "pl", case["text"])) == []
    assert check_layer(core, english, store.layer_path(ROOT, "en", case["text"])) == []
    assert core["localization"] == case["after_localization"]
    assert {wid for wid, entry in pl["words"].items() if "explanation" in entry} == {case["word"]}
    assert not any("explanation" in entry for entry in english["words"].values())
    comparison = before_polish_reader_core(core)
    assert comparison is not core and core == saved
    assert comparison["segments"] == core["segments"]
    assert digest(comparison) == case["before_canonical_sha256"]
    assert digest(core) == case["candidate_canonical_sha256"]
    raw = (ROOT / case["path"]).read_bytes()
    operation = case["raw_inverse_operation"]
    assert hashlib.sha256(raw).hexdigest() == case["candidate_sha256"]
    assert raw.count(operation["after"].encode()) == 1
    restored_raw = raw.replace(operation["after"].encode(), operation["before"].encode(), 1)
    assert hashlib.sha256(restored_raw).hexdigest() == case["before_sha256"]
    assert json.loads(restored_raw) == comparison
    for source in core["segments"]:
        if source["type"] == "verse":
            old_source = segment(comparison, source["id"])
            assert source_payload(source) == source_payload(old_source)
    other = store.core(ROOT, "ordinarium.sanctus")
    assert before_polish_reader_core(other) is other


@pytest.mark.parametrize(
    "case,fault",
    NOTE_FAULTS,
    ids=[f"{case['id']}-{fault}" for case, fault in NOTE_FAULTS],
)
def test_note_declaration_faults_reject_and_recover_same_core(case, fault):
    actual = store.core(ROOT, case["text"])
    pl = store.raw_layer(ROOT, "pl", case["text"])
    english = store.raw_layer(ROOT, "en", case["text"])
    saved, same_input = deepcopy(actual), actual
    pl_path = store.layer_path(ROOT, "pl", case["text"])
    en_path = store.layer_path(ROOT, "en", case["text"])
    assert check_core(actual) == []
    assert check_layer(actual, pl, pl_path) == check_layer(actual, english, en_path) == []
    try:
        if fault == "missing-declaration":
            del actual["localization"]["explanations"]
            expected = f"missing=[] extra=['{case['word']}']"
            errors = check_layer(actual, pl, pl_path)
        elif fault == "en-leak":
            actual["localization"]["explanations"][case["word"]]["languages"] = ["en", "pl"]
            expected = f"missing=['{case['word']}'] extra=[]"
            errors = check_layer(actual, english, en_path)
        else:
            assert fault == "extra-declaration"
            extra = next(
                w["id"]
                for s in actual["segments"]
                for w in s.get("words", [])
                if w["id"] != case["word"]
            )
            actual["localization"]["explanations"][extra] = {"languages": ["pl"]}
            expected = f"missing=['{extra}'] extra=[]"
            errors = check_layer(actual, pl, pl_path)
        assert actual != saved and check_core(actual) == []
        assert any(
            "explanation topology differs" in error and expected in error for error in errors
        )
        with pytest.raises(AssertionError, match=r"^Polish explanation declaration(?:\n|$)"):
            before_polish_reader_core(actual)
    finally:
        actual.clear()
        actual.update(deepcopy(saved))
    assert actual is same_input and actual == saved
    assert check_core(actual) == []
    assert check_layer(actual, pl, pl_path) == check_layer(actual, english, en_path) == []
    assert digest(before_polish_reader_core(actual)) == case["before_canonical_sha256"]


def test_apostles_comparison_keeps_unrelated_layer_faults():
    from test_preface_polish_case_contexts import assert_protected

    case = case_of("apostles-preface")
    core, actual = subject(case)
    saved, same_input = deepcopy(actual), actual
    comparison = before_apostles_role_comparison(actual)
    assert digest(actual) == DATA["apostles_layer"]["after_canonical_sha256"]
    assert digest(comparison) == DATA["apostles_layer"]["before_canonical_sha256"]
    assert comparison is not actual and actual == saved
    assert_protected(core, actual, "apostolorum")
    for fault in ("selected-role", "unrelated-choir"):
        try:
            if fault == "selected-role":
                group_of(actual, ["w033", "w034", "w035"])["gloss"] = "zastępcami Twojego dzieła"
                with pytest.raises(
                    AssertionError, match=r"^Polish Apostles role comparison(?:\n|$)"
                ):
                    before_apostles_role_comparison(actual)
            else:
                actual["segments"]["s05"]["translation"] += " Zmieniono."
                compared = before_apostles_role_comparison(actual)
                assert compared["segments"]["s05"] == actual["segments"]["s05"]
                assert digest(compared) != DATA["apostles_layer"]["before_canonical_sha256"]
            assert actual != saved and interlinear.check(core, actual) == []
            with pytest.raises(AssertionError):
                assert_protected(core, actual, "apostolorum")
        finally:
            actual.clear()
            actual.update(deepcopy(saved))
        assert actual is same_input and actual == saved
        assert_protected(core, actual, "apostolorum")
    other = store.raw_layer(ROOT, "en", case["text"])
    assert before_apostles_role_comparison(other) is other


def test_apostles_wording_inverse_keeps_original_current_row():
    from test_own_relabel_2026_10_20_round_2 import assert_wording_unchanged

    site = DATA["apostles_wording"]["site"]
    change = next(row for row in RULE["rows"] if row["after"]["site"] == site)
    recorded, errors = translation_provenance.load(ROOT)
    assert errors == []
    actual = recorded[site]
    saved, same_row = deepcopy(actual), actual
    core, layer = subject(case_of("apostles-preface"))
    target = layer["segments"]["s04"]["translation"]
    assert actual == change["after"] and interlinear.check(core, layer) == []
    assert_wording_unchanged(site, actual, target)
    comparison, old_target = before_polish_reader_wording(site, actual, target)
    assert comparison == change["before"] and comparison is not actual
    assert canonical_hash(old_target) == change["before"]["target_sha256"]
    assert actual is same_row and actual == saved
    for fault in ("target-text", "row-source"):
        try:
            damaged_target = target
            if fault == "target-text":
                damaged_target += " Zmieniono."
            else:
                actual["source_sha256"] = "0" * 64
            with pytest.raises(AssertionError, match=r"^unchanged wording(?:\n|$)"):
                assert_wording_unchanged(site, actual, damaged_target)
            assert actual is same_row and recorded[site] is actual
        finally:
            actual.clear()
            actual.update(deepcopy(saved))
        assert actual is same_row and actual == saved
        assert_wording_unchanged(site, actual, target)
    other_row = recorded["ordinarium.praefatio-apostolorum.s03.pl"]
    other = layer["segments"]["s03"]["translation"]
    row_result, target_result = before_polish_reader_wording(other_row["site"], other_row, other)
    assert row_result is other_row and target_result is other

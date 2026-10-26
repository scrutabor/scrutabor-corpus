"""Closed Vigil relations and real body/resource consumers.

The complete-resource fixtures require the real accepted26-route bindings;
missing work fails, never skips. Shape-only fixtures claim no sacred wording.
"""

import copy
import json
import shutil
from pathlib import Path

import pytest

from build_reader import commemorationes as reader
from build_reader import emit, store
from checks import commemorationes as checker
from kalendarium import commemorationes as producer
from kalendarium import weekday_vigil as vigil
from kalendarium.dismissal import canonical_inputs

ROOT = Path(store.__file__).resolve().parent.parent
ERROR = "commemorationes: resource differs from independent canonical reconstruction"


def shape(lower=False):
    # Tests only the kind/field helper, not an authored/body/source acceptance.
    return {
        "id": "shape-only" if lower else vigil.IMPEDED_ID,
        "rank": "ordinary",
        "occurrence": (
            {"kind": vigil.UNDER, "vigil": vigil.VIGIL, "month": 5, "day": 13}
            if lower
            else {"kind": vigil.IMPEDED, "vigil": vigil.VIGIL, "feasts": list(vigil.FEASTS)}
        ),
    }


@pytest.mark.parametrize(
    "damage",
    [
        "unknown-key",
        "foreign-vigil",
        "privileged",
        "extra-feast",
        "missing-feast",
        "unordered-feasts",
        "prefix",
        "first-class-feast",
        "foreign-lower-date",
        "boolean-day",
    ],
)
def test_actual_kind_helper_rejects_each_foreign_relation_and_recovers(damage):
    lower = damage in ("foreign-lower-date", "boolean-day")
    good = shape(lower)
    assert checker._vigil_kind_errors(good["id"], good, good["occurrence"]) == []
    bad = copy.deepcopy(good)
    rule = bad["occurrence"]
    if damage == "unknown-key":
        rule["transfer"] = "none"
        message = "exact named weekday Vigil occurrence fields required"
    elif damage == "foreign-vigil":
        rule["vigil"] = "vigilia-pentecostes"
        message = "exact named weekday Vigil occurrence fields required"
    elif damage == "privileged":
        bad["rank"] = "privileged"
        message = "weekday Vigil relations are ordinary, not privileged"
    elif damage in ("extra-feast", "missing-feast", "unordered-feasts", "first-class-feast"):
        if damage == "extra-feast":
            rule["feasts"].append("sancti-stephani-protomartyris")
        elif damage == "missing-feast":
            rule["feasts"].pop()
        elif damage == "unordered-feasts":
            rule["feasts"].reverse()
        else:
            rule["feasts"][0] = "sancti-ioseph-opificis"
        message = "exact two II-class Vigil-impeding feasts required"
    elif damage == "prefix":
        bad["text_prefix"] = "sanctae-petronillae"
        message = "exact impeded Vigil identity without text_prefix required"
    elif damage == "foreign-lower-date":
        rule["day"] = 6
        message = "lower commemoration is outside the26 Vigil dates"
    else:
        rule["day"] = True
        message = "lower commemoration is outside the26 Vigil dates"
    errors = checker._vigil_kind_errors(bad["id"], bad, rule)
    assert f"{bad['id']}: {message}" in errors
    assert checker._vigil_kind_errors(good["id"], good, good["occurrence"]) == []


@pytest.mark.parametrize("role", ["collecta", "secreta", "postcommunio"])
def test_actual_existing_vigil_orations_have_all_real_neutral_and_target_bodies(role):
    vigil._body(ROOT, f"proprium.dominica-v-post-pascha-{role}")


def copy_body(out, identity):
    address = identity.replace(".", "/", 1)
    paths = [f"texts/{address}.json"]
    for language in ("pl", "en"):
        paths += [
            f"languages/{language}/manifest.json",
            f"languages/{language}/texts/{address}.json",
        ]
    for relative in paths:
        target = out / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)


@pytest.mark.parametrize(
    "damage",
    [
        "neutral-id",
        "neutral-empty",
        "pl-declaration",
        "pl-manifest-type",
        "pl-identity",
        "pl-prose",
        "en-identity",
        "en-prose",
    ],
)
def test_real_copied_body_mutations_fail_before_emission_and_recover(tmp_path, damage):
    identity = vigil.VIGIL_ORATIONS[0]
    copy_body(tmp_path, identity)
    vigil._body(tmp_path, identity)
    address = identity.replace(".", "/", 1)
    if damage.startswith("neutral"):
        path = tmp_path / f"texts/{address}.json"
        message = "nonempty neutral body required"
    else:
        language = damage[:2]
        path = tmp_path / (
            f"languages/{language}/manifest.json"
            if "declaration" in damage or "manifest" in damage
            else f"languages/{language}/texts/{address}.json"
        )
        message = (
            f"declared {language} body required exactly once"
            if "declaration" in damage or "manifest" in damage
            else f"correctly identified {language} body required"
        )
    before = path.read_bytes()
    broken = json.loads(before)
    if damage == "neutral-id":
        broken["id"] = "proprium.sanctae-petronillae-collecta"
    elif damage == "neutral-empty":
        broken["segments"] = []
    elif damage == "pl-declaration":
        broken["texts"] = [text for text in broken["texts"] if text != identity]
    elif damage == "pl-manifest-type":
        broken["texts"] = identity  # string.count must not masquerade as a declaration list.
    elif damage.endswith("identity"):
        broken["language"] = "la"
    else:
        core = json.loads((tmp_path / f"texts/{address}.json").read_bytes())
        segment = next(s["id"] for s in core["segments"] if s.get("words"))
        broken["segments"][segment]["translation"] = " "
        message = f"{damage[:2]}/{segment} translation required"
    try:
        path.write_text(json.dumps(broken), encoding="utf-8")
        with pytest.raises(ValueError) as caught:
            vigil._body(tmp_path, identity)
        assert str(caught.value) == (f"commemorationes: required Vigil body {identity}: {message}")
    finally:
        path.write_bytes(before)
    vigil._body(tmp_path, identity)


@pytest.fixture(scope="module")
def complete():
    assert (ROOT / vigil.BINDINGS).is_file(), (
        "Vigil source-role bindings are not ready for integration"
    )
    errors, _ = checker.check(ROOT)
    assert errors == []
    forms, calendar = canonical_inputs(ROOT)
    table = producer.calendar_table(forms, calendar, corpus=ROOT)
    assert table == reader.expected(ROOT)
    return forms, calendar, table


def test_actual_complete_resource_has_only_the_source_selected_weekday_relations(complete):
    _forms, _calendar, table = complete
    oracle = json.loads((ROOT / "tests/fixtures/ascension-vigil-calendar.json").read_bytes())[
        "rows"
    ]
    binding = json.loads((ROOT / vigil.BINDINGS).read_bytes())
    lower = {(r["month"], r["day"]): r["commemoration"] for r in binding["routes"]}
    index = {entry["id"]: i for i, entry in enumerate(table["commemorations"])}
    collision_rows = [r for r in table["pairs"] if r[2] == index[vigil.IMPEDED_ID]]
    assert [[r[0], table["masses"][r[1]], r[4:]] for r in collision_rows] == [
        [row["vigil"], row["winner"], [0, 0, 1, vigil.VIGIL]]
        for row in oracle
        if row["winner"] != vigil.VIGIL
    ], "exact four weekday-Vigil collisions"
    found = []
    for row in oracle:
        if row["ordinary_case"] != "lower-date-required":
            continue
        month, day = map(int, row["vigil"][5:].split("-"))
        identity = lower[month, day]
        selected = [r for r in table["pairs"] if r[0] == row["vigil"] and r[2] == index[identity]]
        assert len(selected) == 1 and selected[0][4:] == [0, 0, 1, None]
        assert table["masses"][selected[0][1]] == vigil.VIGIL
        found += selected
    assert len(found) == 56
    petronilla = [
        r for r in table["pairs"] if r[0] == "2079-05-31" and r[2] == index["sancta-petronilla"]
    ]
    assert len(petronilla) == 1 and petronilla[0][4:] == [1, 1, 1, None]
    assert not any(r[4:7] == [2, 2, 1] for r in petronilla)


@pytest.mark.parametrize(
    "damage", ["missing-binding-file", "missing-whole-route", "wrong-role-target"]
)
def test_complete_binding_guard_rejects_missing_or_substituted_inputs_and_recovers(
    tmp_path, complete, damage
):
    _forms, _calendar, _table = complete
    forms = store.formularies(ROOT)
    docs = producer.authored(ROOT)
    good_docs = copy.deepcopy(docs)
    path = tmp_path / vigil.BINDINGS
    path.parent.mkdir(parents=True, exist_ok=True)
    value = json.loads((ROOT / vigil.BINDINGS).read_bytes())
    before = (ROOT / vigil.BINDINGS).read_bytes()
    path.write_bytes(before)
    targets = set(vigil.VIGIL_ORATIONS)
    targets.update(text for row in value["routes"] for text in row["orations"].values())
    for identity in targets:
        copy_body(tmp_path, identity)
    assert vigil.require_inputs(tmp_path, docs, forms, True)
    try:
        if damage == "missing-binding-file":
            path.unlink()  # This test's owned temporary copy only.
            message = "commemorationes: complete Ascension Vigil oration bindings required"
        elif damage == "missing-whole-route":
            docs = [d for d in docs if d["id"] != value["routes"][0]["commemoration"]]
            message = "commemorationes: Ascension Vigil requires ordinary orations for 04-29"
        else:
            identity = value["routes"][0]["commemoration"]
            value["routes"][0]["orations"]["collecta"] = "proprium.sanctae-petronillae-collecta"
            path.write_text(json.dumps(value), encoding="utf-8")
            message = f"commemorationes: {identity} differs from its source-role bindings"
        with pytest.raises(ValueError) as caught:
            vigil.require_inputs(tmp_path, docs, forms, True)
        assert str(caught.value) == message
    finally:
        path.write_bytes(before)
    assert vigil.require_inputs(tmp_path, good_docs, forms, True)


@pytest.fixture(scope="module")
def emitted(tmp_path_factory, complete):
    # Actual complete transport and bodies, not stand-in sacred text fixtures.
    out = tmp_path_factory.mktemp("weekday-vigil-reader")
    emit.emit(ROOT, out)
    manifest = json.loads((out / "manifest.json").read_bytes())
    assert reader.verify(ROOT, out, manifest, emit.SCHEMA) == []
    return out, manifest


@pytest.mark.parametrize("damage", ["drop-impeded", "drop-lower", "sunday-identity"])
def test_actual_reader_rejects_well_typed_semantic_resource_drift_and_recovers(emitted, damage):
    out, manifest = emitted
    assert reader.verify(ROOT, out, manifest, emit.SCHEMA) == []
    path = out / "commemorationes.json"
    before = path.read_bytes()
    table = json.loads(before)
    if damage == "drop-lower":
        selected = next(r for r in table["pairs"] if r[0] == "2026-05-13")
    else:
        selected = next(r for r in table["pairs"] if r[0] == "2079-05-31" and r[7] == vigil.VIGIL)
    if damage == "sunday-identity":
        selected[7] = "dominica-v-post-pascha"  # real same orations, wrong Mass identity.
    else:
        table["pairs"].remove(selected)
    producer.validate(table)  # deliberately well typed; full reconstruction must still reject.
    try:
        path.write_text(json.dumps(table), encoding="utf-8")
        assert reader.verify(ROOT, out, manifest, emit.SCHEMA) == [ERROR]
    finally:
        path.write_bytes(before)
    assert reader.verify(ROOT, out, manifest, emit.SCHEMA) == []

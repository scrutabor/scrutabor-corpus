"""The published Canon contract, tested through the actual artifact gate."""

import copy
import json
import shutil
from pathlib import Path

import pytest

from build_reader import bibliography, canon, emit, store
from checks.language_packs import check_manifests
from kalendarium import canon as selector

CORPUS = Path(__file__).resolve().parent.parent
BODY_IDS = sorted({text for bodies in selector.PROFILES.values() for text in bodies})


@pytest.fixture(scope="module")
def edition(tmp_path_factory):
    out = tmp_path_factory.mktemp("canon-reader")
    emit.emit(CORPUS, out)
    graph, languages = bibliography.load(CORPUS)
    projection = bibliography.ReaderCitationProjection(CORPUS, graph, languages)
    return out, graph, projection


@pytest.fixture
def change(edition):
    """Modify real emitted files, and restore each exact original byte string."""
    out, _, _ = edition
    saved = {}

    def mutate(name, value):
        path = out / name
        saved.setdefault(path, path.read_bytes())
        if value is None:
            path.unlink()
        else:
            path.write_text(
                value if isinstance(value, str) else json.dumps(value), encoding="utf-8"
            )

    yield mutate
    for path, data in saved.items():
        path.write_bytes(data)


def read(edition, name):
    return json.loads((edition[0] / name).read_text(encoding="utf-8"))


def errors(edition):
    out, graph, projection = edition
    return emit.verify_edition_artifacts(CORPUS, out, graph, projection)


def test_imports_are_the_actual_export():
    for module in (emit, canon, selector, store):
        assert Path(module.__file__).resolve().is_relative_to(CORPUS)


def test_full_artifact_and_round_trip_gates_accept_the_edition(edition):
    assert errors(edition) == []
    assert emit.verify(CORPUS, edition[0]) == []


def test_declared_version_shape_and_exact_body_package_closure(edition):
    manifest = read(edition, "manifest.json")
    table = read(edition, manifest["base"]["canon"])
    assert manifest["schema_version"] == "6.3.0"
    assert table["schema_version"] == "1.0.0"
    assert len(table["profiles"]) == 9 and len(BODY_IDS) == 14
    assert len(table["masses"]) == 113 and len(table["pairs"]) == 7610
    assert len({row[1] for row in table["pairs"]}) == 111
    assert set(table) == {"schema_version", "roles", "profiles", "masses", "pairs"}
    assert table == selector.calendar_table(store.formularies(CORPUS), emit.kalendarium())
    for prefix in ("", "languages/pl/", "languages/en/"):
        package = read(edition, prefix + "manifest.json")
        by_id = {entry["id"]: entry for entry in package["texts"]}
        for text in BODY_IDS:
            artifact = read(edition, by_id[text]["path"])
            assert artifact["id"] == text and artifact["seg"]
            if prefix:
                assert artifact["language"] == package["language"]


@pytest.mark.parametrize(
    "fault",
    [
        "missing-profile",
        "altered-profile",
        "swapped-role",
        "swapped-body",
        "removed-pair",
        "wrong-profile",
        "wrong-mass",
        "extra-pair",
        "duplicate-pair",
        "reordered-pairs",
        "bad-schema",
        "extra-field",
        "missing-role",
        "empty",
        "missing-pairs",
        "bad-row",
        "noncanonical-date",
        "impossible-date",
        "negative-mass",
        "large-mass",
        "negative-profile",
        "large-profile",
        "bool-mass",
        "float-mass",
        "string-mass",
        "bool-profile",
        "float-profile",
        "empty-masses",
        "empty-profiles",
        "non-array-pairs",
        "malformed-json",
        "null-json",
    ],
)
def test_real_malformed_table_is_rejected_by_the_full_artifact_gate(edition, change, fault):
    table = read(edition, "canon.json")
    row = table["pairs"][0]
    if fault == "bool-mass":
        row = next(row for row in table["pairs"] if row[1] in (0, 1))
    elif fault == "bool-profile":
        row = next(row for row in table["pairs"] if row[2] in (0, 1))
    if fault == "missing-profile":
        table["profiles"].pop()
    elif fault == "altered-profile":
        table["profiles"][0]["id"] = "invented"
    elif fault == "swapped-role":
        table["roles"][0], table["roles"][1] = table["roles"][1], table["roles"][0]
    elif fault == "swapped-body":
        texts = table["profiles"][0]["texts"]
        texts["communicantes"], texts["hanc-igitur"] = texts["hanc-igitur"], texts["communicantes"]
    elif fault == "removed-pair":
        table["pairs"].pop()
    elif fault == "wrong-profile":
        row[2] = (row[2] + 1) % len(table["profiles"])
    elif fault == "wrong-mass":
        row[1] = (row[1] + 1) % len(table["masses"])
    elif fault == "extra-pair":
        table["pairs"].append(["2026-01-02", 0, 0])
    elif fault == "duplicate-pair":
        table["pairs"].append(copy.deepcopy(row))
    elif fault == "reordered-pairs":
        table["pairs"].reverse()
    elif fault == "bad-schema":
        table["schema_version"] = "0.0.0"
    elif fault == "extra-field":
        table["fallback"] = "ordinary"
    elif fault == "missing-role":
        del table["profiles"][0]["texts"]["qui-pridie"]
    elif fault == "empty":
        table["pairs"] = []
    elif fault == "missing-pairs":
        del table["pairs"]
    elif fault == "bad-row":
        table["pairs"][0] = row[:2]
    elif fault == "noncanonical-date":
        row[0] = row[0].replace("-", "")
    elif fault == "impossible-date":
        row[0] = "2026-02-30"
    elif fault.endswith("mass"):
        row[1] = {
            "negative-mass": -1,
            "large-mass": len(table["masses"]),
            "bool-mass": bool(row[1]),
            "float-mass": float(row[1]),
            "string-mass": str(row[1]),
        }[fault]
    elif fault.endswith("profile"):
        row[2] = {
            "negative-profile": -1,
            "large-profile": len(table["profiles"]),
            "bool-profile": bool(row[2]),
            "float-profile": float(row[2]),
        }[fault]
    elif fault == "empty-masses":
        table["masses"] = []
    elif fault == "empty-profiles":
        table["profiles"] = []
    elif fault == "non-array-pairs":
        table["pairs"] = {}
    elif fault == "malformed-json":
        table = "{not JSON"
    elif fault == "null-json":
        table = "null"
    else:
        raise AssertionError(fault)
    if fault in {"bool-mass", "bool-profile", "float-mass", "float-profile"}:
        # Python's numeric equality alone would silently accept these rows.
        assert table == read(edition, "canon.json")
    change("canon.json", table)
    assert any(message.startswith("canon:") for message in errors(edition)), fault


@pytest.mark.parametrize("text", BODY_IDS)
@pytest.mark.parametrize("prefix", ["", "languages/pl/", "languages/en/"])
def test_each_actual_core_and_language_dependency_is_required(edition, change, text, prefix):
    path = f"{prefix}texts/{text.replace('.', '/', 1)}.json"
    change(path, None)
    assert any(path in message for message in errors(edition))


@pytest.mark.parametrize(
    "fault",
    [
        "no-resource",
        "wrong-resource",
        "no-file",
        "old-version",
        "undeclared-core",
        "duplicate-core",
        "wrong-core-path",
        "empty-core",
        "wrong-core-id",
        "no-pl-pack",
        "no-en-pack",
        "undeclared-en-body",
        "duplicate-pl-body",
        "wrong-language",
        "old-pack-version",
        "wrong-pack-language",
        "wrong-corpus-version",
        "missing-pl-manifest",
        "empty-pl-body",
        "empty-en-body",
        "null-base",
        "list-base",
    ],
)
def test_manifest_and_actual_dependency_identity_are_required(edition, change, fault):
    root = read(edition, "manifest.json")
    text = BODY_IDS[0]
    body = f"texts/{text.replace('.', '/', 1)}.json"
    if fault in {
        "no-resource",
        "wrong-resource",
        "old-version",
        "undeclared-core",
        "duplicate-core",
        "wrong-core-path",
        "no-pl-pack",
        "no-en-pack",
        "null-base",
        "list-base",
    }:
        if fault in {"null-base", "list-base"}:
            root["base"] = None if fault == "null-base" else []
        elif fault == "no-resource":
            del root["base"]["canon"]
        elif fault == "wrong-resource":
            root["base"]["canon"] = "calendar.json"
        elif fault == "old-version":
            root["schema_version"] = "5.8.0"
        elif fault == "undeclared-core":
            root["texts"] = [entry for entry in root["texts"] if entry["id"] != text]
        elif fault == "duplicate-core":
            root["texts"].append(next(entry for entry in root["texts"] if entry["id"] == text))
        elif fault == "wrong-core-path":
            next(entry for entry in root["texts"] if entry["id"] == text)["path"] = "elsewhere.json"
        else:
            language = "pl" if fault == "no-pl-pack" else "en"
            root["languages"] = [entry for entry in root["languages"] if entry["id"] != language]
        change("manifest.json", root)
    elif fault in {"empty-core", "wrong-core-id"}:
        artifact = read(edition, body)
        artifact["seg" if fault == "empty-core" else "id"] = (
            [] if fault == "empty-core" else "other"
        )
        change(body, artifact)
    elif fault in {"wrong-language", "empty-pl-body", "empty-en-body"}:
        language = "pl" if fault == "empty-pl-body" else "en"
        name = f"languages/{language}/" + body
        artifact = read(edition, name)
        artifact["language" if fault == "wrong-language" else "seg"] = (
            "pl" if fault == "wrong-language" else []
        )
        change(name, artifact)
    elif fault in {"no-file", "missing-pl-manifest"}:
        change("canon.json" if fault == "no-file" else "languages/pl/manifest.json", None)
    else:
        language = "pl" if fault == "duplicate-pl-body" else "en"
        name = f"languages/{language}/manifest.json"
        package = read(edition, name)
        if fault == "undeclared-en-body":
            package["texts"] = [entry for entry in package["texts"] if entry["id"] != text]
        elif fault == "duplicate-pl-body":
            package["texts"].append(
                next(entry for entry in package["texts"] if entry["id"] == text)
            )
        else:
            key, value = {
                "old-pack-version": ("schema_version", "5.8.0"),
                "wrong-pack-language": ("language", "pl"),
                "wrong-corpus-version": ("corpus_schema", "0.0.0"),
            }[fault]
            package[key] = value
        change(name, package)
    assert any(message.startswith("canon:") for message in errors(edition)), fault


@pytest.mark.parametrize(
    "path", ["lexicon/heads.json", "languages/pl/lexicon.json", "languages/en/lexicon.json"]
)
def test_existing_full_gate_proves_the_selected_bodies_lexical_closure(edition, change, path):
    lexicon = read(edition, path)
    artifact = read(edition, f"texts/{BODY_IDS[0].replace('.', '/', 1)}.json")
    lemma = next(cell["l"] for row in artifact["seg"] for cell in row.get("w", []) if cell.get("l"))
    assert lemma in lexicon["entries"]
    del lexicon["entries"][lemma]
    change(path, lexicon)
    assert any("lexicon" in message for message in errors(edition))


def test_bad_emitting_function_cannot_supply_its_own_expected_table(edition, tmp_path, monkeypatch):
    expected = read(edition, "canon.json")
    wrong = copy.deepcopy(expected)
    wrong["pairs"] = []
    monkeypatch.setattr(emit, "calendar_table", lambda *_: wrong)
    assert emit.calendar_table([], {}) == wrong
    assert canon.calendar_table(store.formularies(CORPUS), emit.kalendarium()) == expected
    out = tmp_path / "wrong-producer"
    emit.emit(CORPUS, out)
    assert json.loads((out / "canon.json").read_text(encoding="utf-8")) == wrong
    assert emit.verify(CORPUS, out)


@pytest.mark.parametrize("prefix", ["", "languages/pl/", "languages/en/"])
def test_selected_body_evidence_is_checked_by_the_existing_full_artifact_gate(
    edition, change, prefix
):
    package = read(edition, prefix + "manifest.json")
    entry = next(
        entry for entry in package["texts"] if entry["id"] in BODY_IDS and entry.get("evidence")
    )
    path = entry["evidence"]
    assert read(edition, path)
    change(path, {})
    assert any("evidence" in message for message in errors(edition))


def test_same_mass_different_profile_is_an_explicitly_injected_architectural_control():
    formularies = [{"id": "same", "calendar": {"key": "same"}}]
    calendar = {
        "formularies": ["same"],
        "years": {
            "2026": [
                ["2026-01-06", 0],
                ["2026-01-07", 0],
            ]
        },
    }
    table = selector.calendar_table(formularies, calendar)
    assert table["masses"] == ["same"]
    assert table["pairs"] == [["2026-01-06", 0, 3], ["2026-01-07", 0, 0]]
    actual = selector.calendar_table(store.formularies(CORPUS), emit.kalendarium())
    profiles_by_mass = {}
    for _, mass, profile in actual["pairs"]:
        profiles_by_mass.setdefault(mass, set()).add(profile)
    assert all(len(profiles) == 1 for profiles in profiles_by_mass.values())


def test_genuinely_partial_authored_package_round_trips_without_erasing_emitted_expectations(
    tmp_path,
):
    source = tmp_path / "partial-source"
    source.mkdir()
    for directory in (
        "texts",
        "languages",
        "formularies",
        "commemorationes",
        "ordo",
        "lexicon",
        "bibliography",
        "witnesses",
    ):
        shutil.copytree(CORPUS / directory, source / directory)
    omitted = "ordinarium.communicantes-in-ascensione-domini"
    manifest_path = source / "languages/en/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert omitted in manifest["texts"]
    manifest["texts"].remove(omitted)
    manifest.get("titles", {}).pop(omitted, None)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    layer_path = source / f"languages/en/texts/{omitted.replace('.', '/', 1)}.json"
    layer_path.unlink()
    provenance_path = source / "languages/en/translation-provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["sites"] = [row for row in provenance["sites"] if row["text"] != omitted]
    provenance_path.write_text(json.dumps(provenance, ensure_ascii=False), encoding="utf-8")
    assert check_manifests(source) == []
    # This omitted working body has no inline attachments or retained EN
    # wording uses; the neutral source and all other translations are unchanged.
    out = tmp_path / "partial-reader"
    written = emit.emit(source, out)
    assert written["language_texts"] == 2259  # 1130 complete bilingual bodies minus one.
    assert emit.verify(source, out) == []
    package_path = out / "languages/en/manifest.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    assert omitted not in {entry["id"] for entry in package["texts"]}
    assert not (out / f"languages/en/texts/{omitted.replace('.', '/', 1)}.json").exists()
    # An authored absence is allowed; corrupt output cannot invent one for
    # a DIFFERENT body that the actual partial source still declares.
    required = "ordinarium.communicantes-in-cena-domini"
    assert required in store.language_manifest(source, "en")["texts"]
    package["texts"] = [entry for entry in package["texts"] if entry["id"] != required]
    package_path.write_text(json.dumps(package, ensure_ascii=False), encoding="utf-8")
    graph, languages = bibliography.load(source)
    projection = bibliography.ReaderCitationProjection(source, graph, languages)
    errors = emit.verify_edition_artifacts(source, out, graph, projection)
    assert any(
        "canon:" in message and required.replace(".", "/", 1) in message for message in errors
    )

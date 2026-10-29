"""The Ascension Vigil keeps its source-specific assembly and shared contexts."""

import copy
import json
import shutil
from pathlib import Path

import pytest

from build_reader import emit, store
from checks import formularies, prose

ROOT = Path(__file__).resolve().parents[1]
ID = "vigilia-ascensionis"
PARENT = "formularies/temporale/vigilia-ascensionis.json"
ROLES = ("introitus", "collecta", "alleluia", "offertorium", "secreta", "communio", "postcommunio")
EXPECTED = [
    ("introitus", "proprium.dominica-v-post-pascha-introitus", "reference"),
    ("collecta", "proprium.dominica-v-post-pascha-collecta", "reference"),
    ("epistola", "proprium.sanctorum-simonis-et-iudae-apostolorum-epistola", "reference"),
    ("alleluia", "proprium.dominica-v-post-pascha-alleluia", "reference"),
    ("evangelium", "proprium.vigilia-ascensionis-evangelium", "proper"),
    ("offertorium", "proprium.dominica-v-post-pascha-offertorium", "reference"),
    ("secreta", "proprium.dominica-v-post-pascha-secreta", "reference"),
    ("praefatio", "ordinarium.praefatio-paschalis", "shared"),
    ("communio", "proprium.dominica-v-post-pascha-communio", "reference"),
    ("postcommunio", "proprium.dominica-v-post-pascha-postcommunio", "reference"),
]
ORDINARY = {
    "gloria": {"sunday": "unresolved", "not-sunday": "required"},
    "credo": {"sunday": "unresolved", "not-sunday": "omitted"},
}
TITLES = {"pl": "Wigilia Wniebowstąpienia Pańskiego", "en": "Vigil of the Ascension of the Lord"}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def expected_assembly(doc):
    """A bounded source-inventory regression, not a generic rubric interpreter."""
    assert doc["formulary_schema"] == "1.3.0"
    assert (doc["id"], doc["observance"], doc["calendar"]) == (ID, ID, {"key": ID, "default": True})
    assert (doc["collection"], doc["season"], doc["order"], doc["title"]) == (
        "temporale",
        "paschale",
        37,
        "In Vigilia Ascensionis",
    )
    assert doc["ordinary"] == ORDINARY
    assert doc["components"] == [
        {"key": role, "role": role, "text": text, "relation": relation}
        for role, text, relation in EXPECTED
    ]
    assert "variant" not in doc


def test_actual_parent_passes_native_catalogue_only_with_real_dependencies():
    doc = read(ROOT / PARENT)
    expected_assembly(doc)
    errors, counts = formularies.check(ROOT)
    assert errors == []
    assert counts["formularies"] > 0 and counts["components"] >= len(EXPECTED)
    # No invented calendar membership or mocked Gospel can satisfy this test.
    for _role, text, _relation in EXPECTED:
        neutral, layers = store.load(ROOT, text)
        assert neutral["id"] == text
        assert {"pl", "en"} <= set(layers)
        assert any(s.get("words") for s in neutral["segments"])
        for lang in ("pl", "en"):
            for segment in neutral["segments"]:
                if segment["type"] == "verse":
                    assert layers[lang]["segments"][segment["id"]]["translation"]


def test_actual_emitted_catalogues_and_metrics_preserve_exact_parent():
    doc = read(ROOT / PARENT)
    catalogue = emit.formulary_catalog(ROOT)
    assert catalogue["schema_version"] == "1.5.0"
    rows = catalogue["formularies"]
    matches = [row for row in rows if row["id"] == ID]
    assert len(matches) == 1
    assert "ordinary_omissions" not in doc
    projected = copy.deepcopy(doc)
    del projected["formulary_schema"]
    projected["ordinary_omissions"] = []
    for component in projected["components"]:
        component["text"] = component["text"].replace(".", "/", 1)
    assert matches[0] == projected
    ids = [r["id"] for r in rows]
    i = ids.index(ID)
    assert ids[i - 1 : i + 2] == ["dominica-v-post-pascha", ID, "ascensio-domini"]
    assert [r["order"] for r in rows] == list(range(len(rows)))
    for lang, title in TITLES.items():
        localized = emit.language_formulary_catalog(ROOT, lang)
        assert localized["schema_version"] == "1.2.0"
        assert localized["language"] == lang
        assert [r for r in localized["titles"] if r["id"] == ID] == [{"id": ID, "title": title}]
    metrics = emit.corpus_metrics(ROOT, store.all_texts(ROOT))
    assert metrics["formularies"]["total"] == len(rows)
    assert metrics["formularies"]["component_uses"] == sum(len(r["components"]) for r in rows)


@pytest.mark.parametrize(
    "change",
    [
        "wrong-epistle",
        "wrong-gospel",
        "missing-reference",
        "missing-communion",
        "wrong-preface",
        "role-order",
        "duplicate-part",
        "sunday-required",
    ],
)
def test_source_inventory_mutants_reject_and_original_recovers(change):
    original = read(ROOT / PARENT)
    expected_assembly(original)
    doc = copy.deepcopy(original)
    if change == "wrong-epistle":
        doc["components"][2]["text"] = "proprium.dominica-v-post-pascha-epistola"
    elif change == "wrong-gospel":
        doc["components"][4]["text"] = "proprium.ascensio-domini-evangelium"
    elif change == "missing-reference":
        doc["components"].pop(1)
    elif change == "missing-communion":
        doc["components"].pop(8)
    elif change == "wrong-preface":
        doc["components"][7]["text"] = "ordinarium.praefatio-ascensionis"
    elif change == "role-order":
        doc["components"][5], doc["components"][6] = doc["components"][6], doc["components"][5]
    elif change == "duplicate-part":
        doc["components"].append(copy.deepcopy(doc["components"][-1]))
    else:
        doc["ordinary"]["gloria"]["sunday"] = "required"
    with pytest.raises(AssertionError):
        expected_assembly(doc)
    expected_assembly(original)


@pytest.fixture
def installed_catalogue_copy(tmp_path):
    """Copy actual installed inputs, never fabricate a missing child or calendar key."""
    root = tmp_path / "corpus"
    for folder in ("formularies", "texts", "commemorationes"):
        source = ROOT / folder
        if source.exists():
            shutil.copytree(source, root / folder)
    for lang in ("pl", "en"):
        shutil.copytree(
            ROOT / "languages" / lang / "formularies", root / "languages" / lang / "formularies"
        )
    assert formularies.check(root)[0] == []
    return root


@pytest.mark.parametrize(
    "change,message",
    [
        ("order-collision", "unique contiguous range"),
        ("order-gap", "unique contiguous range"),
        ("duplicate-id", "duplicate formulary id"),
        ("duplicate-title", "duplicate localized formulary id"),
        ("duplicate-part", "duplicate component key"),
        ("role-order", "component order is not liturgical"),
        ("missing-child", "missing text"),
        ("foreign-calendar", "is not computed by the calendar"),
        ("own-reference", "own proper"),
        ("wrong-language", "id/language does not match its path"),
        ("wrong-title-parent", "missing titles"),
        ("missing-title", "missing titles"),
        ("ordinary-in-title", "ordinary belongs only to the neutral"),
    ],
)
def test_real_native_contract_mutants_reject_and_recover(installed_catalogue_copy, change, message):
    root = installed_catalogue_copy
    path = root / PARENT
    original = path.read_bytes()
    doc = json.loads(original)
    extra = None
    deleted = None
    changed_title = None
    if change == "order-collision":
        doc["order"] = read(root / "formularies/temporale/dominica-v-post-pascha.json")["order"]
    elif change == "order-gap":
        doc["order"] = max(d["order"] for d in store.formularies(root)) + 2
    elif change == "duplicate-id":
        extra = root / "formularies/temporale/vigilia-ascensionis-copy.json"
        write(extra, doc)
    elif change == "duplicate-title":
        # Sorts before the genuine title. A dict-only loader used to hide it.
        extra = root / "languages/pl/formularies/temporale/aa-vigil-title-copy.json"
        write(extra, read(root / "languages/pl/formularies/temporale/vigilia-ascensionis.json"))
    elif change == "duplicate-part":
        doc["components"].append(copy.deepcopy(doc["components"][-1]))
    elif change == "role-order":
        doc["components"][5], doc["components"][6] = doc["components"][6], doc["components"][5]
    elif change == "missing-child":
        p = root / "texts/proprium/vigilia-ascensionis-evangelium.json"
        deleted = (p, p.read_bytes())
        p.unlink()
    elif change == "foreign-calendar":
        doc["calendar"]["key"] = "unknown-vigil-key"
    elif change == "own-reference":
        doc["components"][4]["relation"] = "reference"
    else:
        p = root / "languages/pl/formularies/temporale/vigilia-ascensionis.json"
        changed_title = (p, p.read_bytes())
        title = json.loads(changed_title[1])
        if change == "wrong-language":
            title["language"] = "en"
        elif change == "wrong-title-parent":
            title["id"] = "another-vigil"
        elif change == "ordinary-in-title":
            title["ordinary"] = copy.deepcopy(ORDINARY)
        if change == "missing-title":
            p.unlink()
        else:
            write(p, title)
    write(path, doc)
    errors, _counts = formularies.check(root)
    assert any(message in e for e in errors), errors
    path.write_bytes(original)
    if extra is not None:
        extra.unlink()
    if deleted is not None:
        deleted[0].write_bytes(deleted[1])
    if changed_title is not None:
        changed_title[0].write_bytes(changed_title[1])
    assert formularies.check(root)[0] == []


@pytest.mark.parametrize("lang", ["pl", "en"])
@pytest.mark.parametrize("role", ROLES)
def test_seven_reused_contexts_name_both_formularies_without_body_replacement(lang, role):
    text = "proprium.dominica-v-post-pascha-" + role
    layer = store.raw_layer(ROOT, lang, text)
    if lang == "pl":
        expected = (
            role.capitalize()
            + " formularzy „5. Niedziela po Wielkanocy” i „Wigilia Wniebowstąpienia Pańskiego” "
            "w Mszale Rzymskim z 1962 roku."
        )
    else:
        expected = (
            "The "
            + role
            + " of the formularies “Fifth Sunday after Easter” and “Vigil of the Ascension "
            "of the Lord” in the 1962 Roman Missal."
        )
    assert layer["about"] == expected
    assert prose.check(layer) == []
    doc = read(ROOT / PARENT)
    part = next(c for c in doc["components"] if c["key"] == role)
    assert (part["text"], part["relation"]) == (text, "reference")
    original = read(ROOT / "formularies/temporale/dominica-v-post-pascha.json")
    assert next(c for c in original["components"] if c["key"] == role)["text"] == text


@pytest.mark.parametrize("lang", ["pl", "en"])
def test_context_own_prose_semicolon_rejects_but_source_translation_is_not_repunctuated(lang):
    text = "proprium.dominica-v-post-pascha-introitus"
    layer = store.raw_layer(ROOT, lang, text)
    assert prose.check(layer) == []
    broken = copy.deepcopy(layer)
    broken["about"] += "; extra"
    assert any("semicolon" in e for e in prose.check(broken))
    assert prose.check(layer) == []

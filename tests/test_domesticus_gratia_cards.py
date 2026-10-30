"""Shared meanings do not rewrite the grammar or sense of a local occurrence."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from anne_epistle_fixture import predecessor_layer
from possessive_sweep_b1_successor_fixture import before_possessive_b1_layer
from rosary_communion_fixture import (
    TEXT as ROSARY_TEXT,
)
from rosary_communion_fixture import (
    healthy_rosary,
    predecessor_rosary_layer,
    reviewed_rosary,
)

from build_reader import emit, store
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs
from checks.lexicon import (
    check_note_prose,
    check_text_against_lexicon,
    lint_lemmata,
    lint_senses,
    load_lexicon,
)
from checks.translation_provenance import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "tests/fixtures/domesticus-gratia-cards.json").read_text())
DOMESTIC = [pytest.param(row, id=row["case"]) for row in DATA["domesticus"]]
HEAD = {
    "head": "domésticus, -a, -um",
    "pos": "adj",
    "pos_alt": "noun",
    "localization": {"note": True},
}
NOTES = {
    "pl": "Przymiotnik deklinacji I i II. Użyty rzeczownikowo może oznaczać domownika.",
    "en": (
        "An adjective of the first and second declensions. "
        "Used as a noun, it can mean a household member."
    ),
}
GRATIA = {
    "senses": ["grace", "thanks", "favor, gift", "charm"],
    "derivatives": ["grace", "gracious", "gratis"],
}
PARSES = {
    "pentecost-xv": {"pos": "noun", "case": "acc", "gender": "m", "number": "pl", "decl": 2},
    "holy-family": {"case": "acc", "decl": 2, "gender": "f", "number": "sg", "pos": "adj"},
    "anne-dative": {"pos": "adj", "case": "dat", "gender": "m", "number": "pl"},
    "anne-nominative": {"pos": "adj", "case": "nom", "gender": "m", "number": "pl"},
    "thomas": {"case": "nom", "gender": "m", "number": "pl", "pos": "adj"},
}
FILES = {
    "neutral": "lexicon/lemmata.json",
    "pl": "languages/pl/lexicon.json",
    "en": "languages/en/lexicon.json",
}


def word_in(core, identity):
    return next(
        word
        for segment in core["segments"]
        for word in segment.get("words", [])
        if word["id"] == identity
    )


def unchanged_word(word, row):
    assert word == row["word"], "unchanged domesticus occurrence"
    assert word["morph"] == PARSES[row["case"]], "unchanged domesticus parse"


def exact_cards(heads, languages):
    assert heads["domesticus"] == HEAD, "exact domesticus card"
    for language in ("pl", "en"):
        assert languages[language]["domesticus"] == DATA["cards"][language]["domesticus"]
        assert languages[language]["domesticus"]["note"] == NOTES[language]
    assert languages["en"]["gratia"] == GRATIA, "exact English gratia senses"


@pytest.mark.parametrize("language", ["neutral", "pl", "en"])
def test_actual_cards_and_reader_word_help_are_exact(language):
    heads, languages, errors = load_lexicon(ROOT)
    assert errors == []
    exact_cards(heads, languages)
    expected = DATA["cards"][language]
    assert lint_lemmata({key: heads[key] for key in ("domesticus", "gratia")}) == []
    if language != "neutral":
        assert lint_senses(language, expected, {key: heads[key] for key in expected}) == []
        assert check_note_prose({"language": language, "entries": expected}) == []
    actual = emit.lexicon_slice(
        ROOT, None if language == "neutral" else language, {"domesticus", "gratia"}
    )
    assert actual == expected
    actual["domesticus"]["head" if language == "neutral" else "note"] = "changed copy"
    assert (
        emit.lexicon_slice(
            ROOT, None if language == "neutral" else language, {"domesticus", "gratia"}
        )
        == expected
    )


def test_all160_existing_contexts_keep_their_own_realizations():
    observed = []
    for path in sorted((ROOT / "texts").glob("*/*.json")):
        core = json.loads(path.read_text())
        for segment in core["segments"]:
            for word in segment.get("words", []):
                if word["lemma"] in {"domesticus", "gratia"}:
                    observed.append((core["id"], segment["id"], word["id"], word["lemma"]))
    rows = DATA["occurrences"]
    assert len(rows) == len(observed) == 160
    assert sum(row["word"]["lemma"] == "domesticus" for row in rows) == 5
    assert sorted(observed) == sorted(
        (r["text"], r["segment"], r["word"]["id"], r["word"]["lemma"]) for r in rows
    )
    for row in rows:
        core = store.core(ROOT, row["text"])
        assert word_in(core, row["word"]["id"]) == row["word"]
        for language in ("pl", "en"):
            layer = before_possessive_b1_layer(store.raw_layer(ROOT, language, row["text"]))
            assert occurrence_target(core, layer, row) == row["targets"][language]


@pytest.mark.parametrize("case", DOMESTIC)
@pytest.mark.parametrize("language", ["pl", "en"])
def test_all_five_domesticus_parses_pass_native_and_reader_unchanged(case, language):
    heads, _, errors = load_lexicon(ROOT)
    assert errors == []
    core = store.core(ROOT, case["text"])
    layer = store.raw_layer(ROOT, language, case["text"])
    snapshot = deepcopy((core, layer))
    word = word_in(core, case["word"]["id"])
    unchanged_word(word, case)
    if case["case"] == "holy-family":
        assert word["head"] == "w010"
        noun = word_in(core, "w010")
        assert noun["form"] == "vitam" and noun["morph"]["gender"] == "f"
        assert noun["morph"]["case"] == "acc" and noun["morph"]["number"] == "sg"
    elif case["case"] != "pentecost-xv":
        assert word["substantive"] is True
    assert language_packs.check_core(core) == []
    assert check_text_against_lexicon(core, heads) == []
    doc, localized = expand_core(core), enrich_layer(core, layer)
    assert interlinear.check(doc, localized) == []
    tables = [emit.Table() for _ in range(4)]
    base = emit.core_artifact(doc, core, *tables[:3])
    target = emit.language_artifact(doc, localized, tables[3])
    want, layers = emit._strip(doc, {language: localized})
    assert emit.expand(base, target, *[table.order for table in tables]) == (want, layers[language])
    assert (core, layer) == snapshot


@pytest.mark.parametrize("case", DOMESTIC)
@pytest.mark.parametrize("fault", ["pos", "gender", "decl-convention"])
def test_actual_token_faults_reject_and_restore_same_word(case, fault):
    heads, _, errors = load_lexicon(ROOT)
    assert errors == []
    core = store.core(ROOT, case["text"])
    pristine = deepcopy(core)
    word = word_in(core, case["word"]["id"])
    saved = deepcopy(word)
    unchanged_word(word, case)
    assert check_text_against_lexicon(core, heads) == []
    try:
        if fault == "pos":
            word["morph"]["pos"] = "verb"
        elif fault == "gender":
            word["morph"]["gender"] = "f" if saved["morph"]["gender"] == "m" else "m"
        else:
            word["morph"]["decl"] = 3 if "decl" in saved["morph"] else 2
        assert word != saved
        native = check_text_against_lexicon(core, heads)
        if fault == "pos":
            assert any(word["id"] in error and "morph.pos" in error for error in native)
        else:
            # Optional generic adjective facts cannot infer occurrence gender/declension.
            assert native == []
        with pytest.raises(AssertionError, match=r"^unchanged domesticus occurrence(?:\n|$)"):
            unchanged_word(word, case)
    finally:
        word.clear()
        word.update(saved)
    assert word_in(core, case["word"]["id"]) is word and core == pristine
    unchanged_word(word, case)
    assert check_text_against_lexicon(core, heads) == []


@pytest.mark.parametrize("fault", ["head", "gender", "decl", "pos_alt"])
def test_generic_card_cannot_reintroduce_the_old_noun_head(fault):
    heads, languages, errors = load_lexicon(ROOT)
    assert errors == []
    exact_cards(heads, languages)
    entry = heads["domesticus"]
    saved = deepcopy(entry)
    try:
        if fault == "head":
            entry["head"] = "domésticus, doméstici"
        elif fault == "gender":
            entry["gender"] = "m"
        elif fault == "decl":
            entry["decl"] = 2
        else:
            del entry["pos_alt"]
        assert entry != saved
        with pytest.raises(AssertionError, match=r"^exact domesticus card(?:\n|$)"):
            exact_cards(heads, languages)
        if fault == "pos_alt":
            core = store.core(ROOT, DATA["domesticus"][0]["text"])
            assert any("morph.pos" in error for error in check_text_against_lexicon(core, heads))
    finally:
        entry.clear()
        entry.update(saved)
    assert heads["domesticus"] is entry
    exact_cards(heads, languages)


@pytest.mark.parametrize("damage", ["neutral-requirement", "pl-note", "en-note"])
def test_actual_note_linkage_faults_restore_exact_files(tmp_path, damage):
    corpus = tmp_path / "lexicon"
    paths = {}
    for key, relative in FILES.items():
        doc = json.loads((ROOT / relative).read_text())
        doc["entries"] = {lemma: doc["entries"][lemma] for lemma in ("domesticus", "gratia")}
        path = corpus / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, ensure_ascii=False) + "\n")
        paths[key] = path
    saved = {key: path.read_bytes() for key, path in paths.items()}
    healthy = load_lexicon(corpus)
    assert healthy[2] == []
    key = "neutral" if damage == "neutral-requirement" else damage.split("-", 1)[0]
    changed = json.loads(paths[key].read_text())
    del changed["entries"]["domesticus"]["localization" if key == "neutral" else "note"]
    try:
        paths[key].write_text(json.dumps(changed, ensure_ascii=False) + "\n")
        expected = (
            [f"lexicon:{lang}:domesticus: note has no neutral requirement" for lang in ("en", "pl")]
            if key == "neutral"
            else [f"lexicon:{key}:domesticus: localized note is required"]
        )
        assert load_lexicon(corpus)[2] == expected
    finally:
        for name, raw in saved.items():
            paths[name].write_bytes(raw)
    assert {key: path.read_bytes() for key, path in paths.items()} == saved
    assert load_lexicon(corpus) == healthy


@pytest.mark.parametrize(
    "fault", ["grace", "thanks", "favor, gift", "charm", "derivative", "fifth"]
)
def test_english_gratia_preserves_prior_meanings_and_rejects_a_fifth_sense(fault):
    heads, languages, errors = load_lexicon(ROOT)
    assert errors == []
    entry = languages["en"]["gratia"]
    saved = deepcopy(entry)
    exact_cards(heads, languages)
    try:
        if fault == "derivative":
            entry["derivatives"].pop()
        elif fault == "fifth":
            entry["senses"].append("beauty")
        else:
            entry["senses"].remove(fault)
        assert entry != saved
        if fault == "fifth":
            assert any(
                "at most 4" in error
                for error in lint_senses("en", {"gratia": entry}, {"gratia": heads["gratia"]})
            )
        with pytest.raises(AssertionError, match=r"^exact English gratia senses(?:\n|$)"):
            exact_cards(heads, languages)
    finally:
        entry.clear()
        entry.update(saved)
    assert languages["en"]["gratia"] is entry
    exact_cards(heads, languages)


PROJECTION_HISTORY = {
    (
        "proprium.annuntiatio-beatae-mariae-virginis-evangelium",
        "en",
        "w038",
    ): {
        "core_sha256": "153c56e780f99966be6156a868dc371c45f86927c4561cc354e8a875610423f1",
        "layer_sha256": "967c1275a49f680d5648d6e4f0483ca8c14079eb8ffbfc4bfac20f5d18cbaa5b",
        "row_sha256": "ab2a385248925e730f2af4defe026846fa19be9f43e0644247d03be0b6808be0",
        "current": {
            "word": {},
            "alignments": [{"words": ["w038", "w039"], "anchor": "w039", "gloss": "full of grace"}],
        },
        "before": {"word": {"gloss": "of grace"}, "alignments": []},
        "before_sha256": "72245612935dac24f6948497d8f251a1a881f76b3f38cc0b740c233dcf2d9198",
    },
    (
        "proprium.beata-maria-virgo-regina-evangelium",
        "en",
        "w038",
    ): {
        "core_sha256": "11267b165be3f26502814c7dd81cf7216957f2409b506699ed5e7e0fdf8b2846",
        "layer_sha256": "656ac2a046cbee1d167175286a5b6ff42b3d239479e4d68c330ebe586865aa24",
        "row_sha256": "0513df09592f571722e38f8773e95f9fca618f95174fcf2d57d3bc927852c849",
        "current": {
            "word": {},
            "alignments": [{"words": ["w038", "w039"], "anchor": "w039", "gloss": "full of grace"}],
        },
        "before": {"word": {"gloss": "of grace"}, "alignments": []},
        "before_sha256": "72245612935dac24f6948497d8f251a1a881f76b3f38cc0b740c233dcf2d9198",
    },
    (
        "proprium.beatae-mariae-virginis-a-rosario-evangelium",
        "en",
        "w038",
    ): {
        "core_sha256": "479d4114206b1bfdf92e70b0b7172cff4faabead4a9114340171286836a9126a",
        "layer_sha256": "696587e5b4c857add3313c5ed0a09a0caf5ae2c2dcaa325b34439497fc503e8e",
        "row_sha256": "dc240378b3681da86abafc0e4fb7992425bfebd3b4da2590485b9c9495e846a7",
        "current": {
            "word": {},
            "alignments": [{"words": ["w038", "w039"], "anchor": "w039", "gloss": "full of grace"}],
        },
        "before": {"word": {"gloss": "of grace"}, "alignments": []},
        "before_sha256": "72245612935dac24f6948497d8f251a1a881f76b3f38cc0b740c233dcf2d9198",
    },
    (
        "proprium.dedicatio-sancti-michaelis-archangeli-epistola",
        "pl",
        "w055",
    ): {
        "core_sha256": "933499a955d990e673b24644d3b95591fbe24e2dcb0e2d3f0fdbd4d00bfab89a",
        "layer_sha256": "561330a6c8ecb041ff503fa942364ae2b85d8f0e46bd146717155ba566d9d3f3",
        "row_sha256": "e8f59dff0698249e42c971a6f7af3fa2460b0e9020da41212b13f24585ff813a",
        "current": {"word": {"gloss": "Łaska"}, "alignments": []},
        "before": {"word": {"gloss": "łaska"}, "alignments": []},
        "before_sha256": "f6641a8f228b057d400c8d42c156c8b73deb91a6df4aa8db8ebbaf1af3251c1a",
    },
    (
        "proprium.dedicatio-sancti-michaelis-archangeli-epistola",
        "en",
        "w055",
    ): {
        "core_sha256": "933499a955d990e673b24644d3b95591fbe24e2dcb0e2d3f0fdbd4d00bfab89a",
        "layer_sha256": "3f7f6fa6611070d4a94b73eca4b12c0124e23d6022d5fd0d6d9ea40406f903a6",
        "row_sha256": "e8f59dff0698249e42c971a6f7af3fa2460b0e9020da41212b13f24585ff813a",
        "current": {"word": {"gloss": "Grace"}, "alignments": []},
        "before": {"word": {"gloss": "grace"}, "alignments": []},
        "before_sha256": "92cc51deffc67d5adf16e3eb09fad36a4be8d46b4ede082f5bb4de01a303f912",
    },
}

PROJECTION_CASES = [
    pytest.param(text, language, word, id=f"{language}-{text.split('.', 1)[1]}-{word}")
    for text, language, word in PROJECTION_HISTORY
]
PROJECTION_FAULTS = [
    "caption",
    "representation",
    "prose",
    "about",
    "core",
    "fixture-missing",
    "fixture-wrong",
    "fixture-extra",
]


def current_projection_predecessor(core, layer, row, case):
    assert core.get("id") == layer.get("text") == row.get("text"), "shared projection subject"
    assert language_packs.check_core(core) == [], "current shared projection core shape"
    category, slug = core["id"].split(".", 1)
    path = ROOT / "languages" / layer["language"] / "texts" / category / (slug + ".json")
    errors = language_packs.check_layer(core, layer, path)
    assert errors == [], "current shared projection layer shape"
    doc, localized = expand_core(core), enrich_layer(core, layer)
    assert interlinear.check(doc, localized) == [], "current shared projection interlinear"
    tables = [emit.Table() for _ in range(4)]
    base = emit.core_artifact(doc, core, *tables[:3])
    target = emit.language_artifact(doc, localized, tables[3])
    want, layers = emit._strip(doc, {layer["language"]: localized})
    decoded = emit.expand(base, target, *[t.order for t in tables])
    assert decoded == (want, layers[layer["language"]])
    assert canonical_hash(core) == case["core_sha256"], "complete shared projection core"
    assert canonical_hash(layer) == case["layer_sha256"], "complete shared projection layer"
    assert canonical_hash(row) == case["row_sha256"], "complete shared projection fixture row"
    word = row["word"]["id"]
    current = {
        "word": deepcopy(layer["words"].get(word, {})),
        "alignments": [
            deepcopy(g)
            for g in layer["segments"][row["segment"]].get("alignments", [])
            if word in g["words"]
        ],
    }
    assert current == case["current"], "exact current shared projection"
    comparison = deepcopy(current)
    comparison["word"]["gloss"] = case["before"]["word"]["gloss"]
    if comparison["alignments"]:
        assert len(comparison["alignments"]) == 1
        assert comparison["alignments"].pop() == case["current"]["alignments"][0]
    assert comparison == case["before"], "exact shared projection inverse"
    assert canonical_hash(comparison) == case["before_sha256"], "complete prior shared projection"
    return comparison


def occurrence_target(core, layer, row):
    if row["text"] == ROSARY_TEXT:
        return rosary_shared_projection_predecessor(core, layer, row)
    key = (row["text"], layer["language"], row["word"]["id"])
    if key in PROJECTION_HISTORY:
        return current_projection_predecessor(core, layer, row, PROJECTION_HISTORY[key])
    comparison = layer
    if row["text"] == "proprium.sanctae-annae-matris-beatae-mariae-virginis-epistola":
        assert language_packs.check_core(core) == []
        category, slug = core["id"].split(".", 1)
        path = ROOT / "languages" / layer["language"] / "texts" / category / (slug + ".json")
        assert language_packs.check_layer(core, layer, path) == []
        doc, localized = expand_core(core), enrich_layer(core, layer)
        assert interlinear.check(doc, localized) == []
        tables = [emit.Table() for _ in range(4)]
        base = emit.core_artifact(doc, core, *tables[:3])
        target = emit.language_artifact(doc, localized, tables[3])
        want, layers = emit._strip(doc, {layer["language"]: localized})
        assert emit.expand(base, target, *[t.order for t in tables]) == (
            want,
            layers[layer["language"]],
        )
        comparison = predecessor_layer(layer)
    groups = [
        g
        for g in comparison["segments"][row["segment"]].get("alignments", [])
        if row["word"]["id"] in g["words"]
    ]
    return {"word": comparison["words"].get(row["word"]["id"], {}), "alignments": groups}


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("fault", ["group", "prose", "about"])
def test_anne_shared_projection_rejects_changed_current_layer_and_recovers(language, fault):
    text = "proprium.sanctae-annae-matris-beatae-mariae-virginis-epistola"
    row = next(r for r in DATA["occurrences"] if r["text"] == text and r["word"]["id"] == "w207")
    core, layer = store.core(ROOT, text), store.raw_layer(ROOT, language, text)
    saved_core, saved_layer = deepcopy(core), deepcopy(layer)
    healthy = occurrence_target(core, layer, row)
    assert healthy == row["targets"][language]
    try:
        if fault == "group":
            groups = [g for g in layer["segments"]["s01"]["alignments"] if "w207" in g["words"]]
            if groups:
                groups[0]["gloss"] += " changed"
            else:
                layer["words"]["w207"]["gloss"] += " changed"
        elif fault == "prose":
            layer["segments"]["s01"]["translation"] += " Added."
        else:
            layer["about"] += " Changed."
        assert layer != saved_layer and core == saved_core
        with pytest.raises(AssertionError, match=r"^Anne complete target layer$"):
            occurrence_target(core, layer, row)
    finally:
        layer.clear()
        layer.update(saved_layer)
    assert layer == saved_layer and core == saved_core
    assert occurrence_target(core, layer, row) == healthy


@pytest.mark.parametrize("text,language,word", PROJECTION_CASES)
def test_current_shared_projection_is_checked_before_its_historical_inverse(text, language, word):
    (row,) = [r for r in DATA["occurrences"] if r["text"] == text and r["word"]["id"] == word]
    core, layer = store.core(ROOT, text), store.raw_layer(ROOT, language, text)
    saved = deepcopy((core, layer, DATA))
    expected = "of grace" if word == "w038" else {"pl": "łaska", "en": "grace"}[language]
    assert row["targets"][language] == {"word": {"gloss": expected}, "alignments": []}
    assert occurrence_target(core, layer, row) == row["targets"][language]
    assert (core, layer, DATA) == saved


@pytest.mark.parametrize("text,language,word", PROJECTION_CASES)
@pytest.mark.parametrize("fault", PROJECTION_FAULTS)
def test_current_shared_projection_fault_rejects_and_restores_same_objects(
    text, language, word, fault
):
    (row,) = [r for r in DATA["occurrences"] if r["text"] == text and r["word"]["id"] == word]
    core, layer = store.core(ROOT, text), store.raw_layer(ROOT, language, text)
    saved_core, saved_layer, saved_row = deepcopy(core), deepcopy(layer), deepcopy(row)
    saved_data = deepcopy(DATA)
    healthy = occurrence_target(core, layer, row)
    assert healthy == row["targets"][language]
    message = "complete shared projection layer"
    try:
        if fault == "caption":
            groups = [
                g
                for g in layer["segments"][row["segment"]].get("alignments", [])
                if word in g["words"]
            ]
            if groups:
                groups[0]["gloss"] = "of grace"
            else:
                layer["words"][word]["gloss"] = row["targets"][language]["word"]["gloss"]
        elif fault == "representation":
            if word == "w038":
                layer["words"][word]["gloss"] = "of grace"
            else:
                layer["segments"][row["segment"]].setdefault("alignments", []).append(
                    {"words": [word], "anchor": word, "gloss": "Grace"}
                )
            message = "current shared projection layer shape"
        elif fault == "prose":
            layer["segments"][row["segment"]]["translation"] += " Added."
        elif fault == "about":
            layer["about"] += " Changed."
        elif fault == "core":
            core["editorial"]["notes"] += " Added."
            message = "complete shared projection core"
        else:
            if fault == "fixture-missing":
                del row["targets"][language]["word"]["gloss"]
            elif fault == "fixture-wrong":
                row["targets"][language]["word"]["gloss"] = "wrong"
            else:
                row["extra"] = True
            message = "complete shared projection fixture row"
        assert (core, layer, row) != (saved_core, saved_layer, saved_row)
        with pytest.raises(AssertionError, match=rf"^{message}(?:\n|$)"):
            occurrence_target(core, layer, row)
    finally:
        core.clear()
        core.update(saved_core)
        layer.clear()
        layer.update(saved_layer)
        row.clear()
        row.update(saved_row)
    assert core == saved_core and layer == saved_layer and saved_data == DATA
    assert (
        next(r for r in DATA["occurrences"] if r["text"] == text and r["word"]["id"] == word) is row
    )
    assert occurrence_target(core, layer, row) == healthy


ROSARY_SHARED_ROW_SHA256 = "d9821c8613f032ad13a33d77ab5704a5980004c4a9c869fcca99709cb9e64375"


def rosary_shared_projection_predecessor(core, layer, row):
    healthy_rosary(core, layer)
    doc, localized = expand_core(core), enrich_layer(core, layer)
    tables = [emit.Table() for _ in range(4)]
    base = emit.core_artifact(doc, core, *tables[:3])
    target = emit.language_artifact(doc, localized, tables[3])
    want, layers = emit._strip(doc, {layer["language"]: localized})
    assert emit.expand(base, target, *[table.order for table in tables]) == (
        want,
        layers[layer["language"]],
    )
    reviewed_rosary(core, layer)
    assert canonical_hash(row) == ROSARY_SHARED_ROW_SHA256, "complete Rosary shared fixture row"
    comparison = predecessor_rosary_layer(layer)
    groups = [
        group
        for group in comparison["segments"][row["segment"]].get("alignments", [])
        if row["word"]["id"] in group["words"]
    ]
    return {"word": comparison["words"].get(row["word"]["id"], {}), "alignments": groups}


@pytest.mark.parametrize("language", ["pl", "en"])
def test_rosary_shared_projection_validates_current_subject_before_comparison(language):
    (row,) = [r for r in DATA["occurrences"] if r["text"] == ROSARY_TEXT]
    core, layer = store.core(ROOT, ROSARY_TEXT), store.raw_layer(ROOT, language, ROSARY_TEXT)
    saved = deepcopy((core, layer, DATA))
    expected = {"pl": "wdziękowi", "en": "grace"}[language]
    assert row["targets"][language] == {"word": {"gloss": expected}, "alignments": []}
    assert occurrence_target(core, layer, row) == row["targets"][language]
    assert (core, layer, DATA) == saved


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize(
    "fault",
    [
        "group",
        "help",
        "prose",
        "about",
        "core",
        "fixture-missing",
        "fixture-wrong",
        "fixture-extra",
    ],
)
def test_rosary_shared_projection_fault_rejects_and_restores_same_objects(language, fault):
    (row,) = [r for r in DATA["occurrences"] if r["text"] == ROSARY_TEXT]
    core, layer = store.core(ROOT, ROSARY_TEXT), store.raw_layer(ROOT, language, ROSARY_TEXT)
    saved_core, saved_layer, saved_row = deepcopy(core), deepcopy(layer), deepcopy(row)
    saved_data = deepcopy(DATA)
    healthy = occurrence_target(core, layer, row)
    assert healthy == row["targets"][language]
    message = "complete Rosary layer"
    try:
        if fault == "group":
            (group,) = [g for g in layer["segments"]["s01"]["alignments"] if "w011" in g["words"]]
            group["gloss"] += " changed"
        elif fault == "help":
            layer["words"]["w011"]["explanation"] += " Changed."
        elif fault == "prose":
            layer["segments"]["s01"]["translation"] += " Added."
        elif fault == "about":
            layer["about"] += " Changed."
        elif fault == "core":
            core["editorial"]["notes"] += " Added."
            message = "complete Rosary core"
        else:
            if fault == "fixture-missing":
                del row["targets"][language]["word"]["gloss"]
            elif fault == "fixture-wrong":
                row["targets"][language]["word"]["gloss"] = "wrong"
            else:
                row["extra"] = True
            message = "complete Rosary shared fixture row"
        assert (core, layer, row) != (saved_core, saved_layer, saved_row)
        with pytest.raises(AssertionError, match=rf"^{message}(?:\n|$)"):
            occurrence_target(core, layer, row)
    finally:
        core.clear()
        core.update(saved_core)
        layer.clear()
        layer.update(saved_layer)
        row.clear()
        row.update(saved_row)
    assert core == saved_core and layer == saved_layer and saved_data == DATA
    assert next(r for r in DATA["occurrences"] if r["text"] == ROSARY_TEXT) is row
    assert occurrence_target(core, layer, row) == healthy

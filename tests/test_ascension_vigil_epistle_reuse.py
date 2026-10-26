"""The 94-word Ephesian lesson keeps its source and target-language relations."""

import copy
import json
from pathlib import Path

import pytest

from build_reader import bibliography, store
from build_reader.bibliography_bindings import digest, selected_text, validate_bindings
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, prose, syntax, translation_provenance
from checks.collate import collate

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.sanctorum-simonis-et-iudae-apostolorum-epistola"
SLUG = TEXT.split(".", 1)[1]
PL_PROSE = "77223ef5543160c948846586c007e6615949b1dd3053c09b4230498a24e58737"
EN_PROSE = "92fcfa1348372b7fb3b31b8818a93a5afe70dcafbaf60247b0c6080c8d0b2edb"
SOURCE = "4f6c45c457463736febb903fe31b1ceab0cb063bdcd505277a15bdfdaf5366ca"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def actual():
    core = store.core(ROOT, TEXT)
    layers = {lang: store.raw_layer(ROOT, lang, TEXT) for lang in ("pl", "en")}
    return core, layers


def words(core):
    return {word["id"]: word for word in core["segments"][0]["words"]}


def group(layer, first, last):
    ids = [f"w{i:03d}" for i in range(first, last + 1)]
    matches = [a for a in layer["segments"]["s01"]["alignments"] if a["words"] == ids]
    assert len(matches) == 1
    return matches[0]


REVIEWED_GROUPS: list[tuple[str, int, int, str, str, str]] = [
    ("pl", 17, 19, "w018", "wziął niewolę do niewoli", "PL captivity group"),
    ("pl", 28, 29, "w028", "jeśli nie to, że", "PL exceptive group"),
    ("en", 17, 19, "w018", "He led captivity captive", "EN captivity group"),
    ("en", 23, 25, "w025", "Now, “He ascended”", "EN topic group"),
    ("en", 26, 27, "w027", "what does it mean", "EN question group"),
    ("en", 30, 31, "w031", "He also descended", "EN descent group"),
    ("en", 39, 42, "w040", "is Himself also the One who", "EN identity group"),
    ("en", 53, 55, "w055", "some as apostles", "EN role group 053-055"),
    ("en", 56, 58, "w058", "others as prophets", "EN role group 056-058"),
    ("en", 59, 61, "w061", "others as evangelists", "EN role group 059-061"),
    ("en", 62, 64, "w064", "others as pastors", "EN role group 062-064"),
    ("en", 78, 79, "w078", "we all come together", "EN retained collective group"),
    ("en", 88, 89, "w088", "a mature man", "EN maturity group"),
]


def require_relation(condition, message):
    if not condition:
        raise AssertionError(message)


def reviewed_relations(core, layers):
    """Exact admitted-data pins, not a general native semantic oracle."""
    pl, en = layers["pl"], layers["en"]
    for lang, first, last, anchor, gloss, message in REVIEWED_GROUPS:
        members = [f"w{i:03d}" for i in range(first, last + 1)]
        matches = [
            a for a in layers[lang]["segments"]["s01"]["alignments"] if a["words"] == members
        ]
        require_relation(matches == [{"words": members, "anchor": anchor, "gloss": gloss}], message)
    require_relation(
        (pl["words"]["w039"]["gloss"], pl["words"]["w042"]["gloss"]) == ("sam", "Tym, który"),
        "PL emphatic identity",
    )
    for wid, expected in {
        "w055": "apostołami",
        "w058": "prorokami",
        "w061": "ewangelistami",
        "w064": "pasterzami",
        "w066": "nauczycielami",
        "w069": "świętych",
    }.items():
        require_relation(pl["words"][wid]["gloss"] == expected, f"PL role caption: {wid}")
    require_relation(
        (en["words"]["w065"]["gloss"], en["words"]["w066"]["gloss"]) == ("and", "teachers"),
        "EN pastors and teachers retained",
    )
    for wid, expected, message in [
        ("w013", "it says", "EN quotation subject"),
        ("w028", "except", "EN exceptive caption"),
        ("w037", "He who", "EN relative caption"),
        ("w047", "so that", "EN purpose conjunction"),
        ("w048", "He might fill", "EN purpose subject"),
        ("w071", "the work", "EN ministry work"),
        ("w092", "of maturity", "EN retained maturity caption"),
    ]:
        require_relation(en["words"][wid]["gloss"] == expected, message)
    for wid in ("w053", "w056"):
        require_relation(words(core)[wid]["morph"].get("gender") == "m", f"Latin gender: {wid}")


def test_current_lesson_relations_and_exact94_cards_per_language():
    core, layers = actual()
    doc, loaded = store.load(ROOT, TEXT)
    assert list(layers) == ["pl", "en"]
    assert len(core["segments"]) == 1
    assert list(words(core)) == [f"w{i:03d}" for i in range(1, 95)]
    assert len({w["lemma"] for w in words(core).values()}) == 65
    assert digest(selected_text(doc)) == SOURCE
    assert syntax.check(doc) == []
    reviewed_relations(core, layers)
    for lang, layer in layers.items():
        assert set(layer["words"]) == set(words(core))
        assert interlinear.check(doc, loaded[lang]) == []
        realized = [a for a in layer["segments"]["s01"]["alignments"] if "gloss" in a]
        assert len(realized) == (2 if lang == "pl" else 11)
        assert max(len(a["words"]) for a in realized) <= (3 if lang == "pl" else 4)
        assert core["localization"]["notes"] == ["w019", "w088"]
        assert all(layer["words"][w].get("note") for w in core["localization"]["notes"])


@pytest.mark.parametrize(
    "mutation",
    [
        "pl-captive",
        "pl-exceptive",
        "pl-ipse",
        "pl-role-capital",
        "en-topic",
        "en-roles",
        "en-purpose-subject",
        "en-relative-capital",
        "en-growth",
        "gender",
    ],
)
def test_one_mutant_per_reviewed_relation_rejects_and_recovers(mutation):
    core, layers = actual()
    reviewed_relations(core, layers)
    broken_core, broken = copy.deepcopy(core), copy.deepcopy(layers)
    if mutation == "pl-captive":
        group(broken["pl"], 17, 19)["gloss"] = "wyzwolił wszystkich jeńców"
    elif mutation == "pl-exceptive":
        group(broken["pl"], 28, 29)["gloss"] = "jak tylko"
    elif mutation == "pl-ipse":
        broken["pl"]["words"]["w039"]["gloss"] = "On"
    elif mutation == "pl-role-capital":
        broken["pl"]["words"]["w055"]["gloss"] = "Apostołami"
    elif mutation == "en-topic":
        group(broken["en"], 23, 25)["gloss"] = "This Now He ascended"
    elif mutation == "en-roles":
        group(broken["en"], 56, 58)["gloss"] = "others and Prophets"
    elif mutation == "en-purpose-subject":
        broken["en"]["words"]["w048"]["gloss"] = "might fill"
    elif mutation == "en-relative-capital":
        broken["en"]["words"]["w037"]["gloss"] = "He Who"
    elif mutation == "en-growth":
        group(broken["en"], 88, 89)["gloss"] = "man perfect"
    else:
        words(broken_core)["w053"]["morph"].pop("gender")
    expected = {
        "pl-captive": "PL captivity group",
        "pl-exceptive": "PL exceptive group",
        "pl-ipse": "PL emphatic identity",
        "pl-role-capital": "PL role caption: w055",
        "en-topic": "EN topic group",
        "en-roles": "EN role group 056-058",
        "en-purpose-subject": "EN purpose subject",
        "en-relative-capital": "EN relative caption",
        "en-growth": "EN maturity group",
        "gender": "Latin gender: w053",
    }[mutation]
    with pytest.raises(AssertionError) as caught:
        reviewed_relations(broken_core, broken)
    assert str(caught.value) == expected
    reviewed_relations(core, layers)


@pytest.mark.parametrize(
    "lang,word,reason",
    [
        ("pl", "w012", "idiom"),
        ("pl", "w054", "idiom"),
        ("en", "w005", "inflection"),
        ("en", "w012", "idiom"),
    ],
)
def test_legitimate_zero_is_preserved_and_undeclared_omission_rejects(lang, word, reason):
    core, layers = actual()
    layer = layers[lang]
    alignments = layer["segments"]["s01"]["alignments"]
    assert {"words": [word], "reason": reason} in alignments
    assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
    broken = copy.deepcopy(layer)
    broken["segments"]["s01"]["alignments"] = [a for a in alignments if a["words"] != [word]]
    assert interlinear.check(expand_core(core), enrich_layer(core, broken))
    assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []


def test_group_is_not_one_word_and_cannot_overlap_or_duplicate_direct_caption():
    core, layers = actual()
    layer = layers["en"]
    assert group(layer, 53, 55)["words"] == ["w053", "w054", "w055"]
    assert all(w in layer["words"] for w in group(layer, 53, 55)["words"])
    for corruption in ("direct", "overlap", "foreign"):
        broken = copy.deepcopy(layer)
        if corruption == "direct":
            broken["words"]["w054"]["gloss"] = "as"
        elif corruption == "overlap":
            broken["segments"]["s01"]["alignments"].append(
                {"words": ["w054", "w055"], "anchor": "w055", "gloss": "as apostles"}
            )
        else:
            group(broken, 53, 55)["words"][-1] = "w095"
        assert interlinear.check(expand_core(core), enrich_layer(core, broken))
    assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []


def test_both_prose_strings_working_states_and_no_protected_formula_reseal():
    core, layers = actual()
    for lang, expected in (("pl", PL_PROSE), ("en", EN_PROSE)):
        assert (
            translation_provenance.canonical_hash(layers[lang]["segments"]["s01"]["translation"])
            == expected
        )
        ledger = read(ROOT / "languages" / lang / "translation-provenance.json")
        row = next(r for r in ledger["sites"] if r["site"] == f"{TEXT}.s01.{lang}")
        assert (row["origin"], row["review"], row["familiar_core"]) == (
            "working-unsettled",
            "working",
            False,
        )
        assert not translation_provenance.protected(TEXT, lang, "s01")
        assert row["source_sha256"] == translation_provenance.canonical_hash(
            translation_provenance.source_payload(core["segments"][0])
        )
        assert row["target_sha256"] == expected
    for wid in ("w053", "w056"):
        analysis = core["editorial"]["words"][wid]["analysis"]
        assert analysis["review"] == "pending"
        assert "editorial" in analysis["sources"]
    assert layers["pl"]["words"]["w085"]["gloss"] == "Syna"
    assert layers["en"]["words"]["w085"]["gloss"] == "of the Son"
    assert layers["pl"]["words"]["w088"]["gloss"] == "męża"
    assert layers["pl"]["words"]["w089"]["gloss"] == "doskonałego"
    assert layers["pl"]["words"]["w092"]["gloss"] == "wieku"


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def test_actual_rows_native_provenance_stale_source_target_and_review_mutants(tmp_path):
    core, layers = actual()
    put(
        tmp_path / "bibliography/graph.json",
        {"schema_version": bibliography.SCHEMA, "uses": [], "migration": {"removals": []}},
    )
    core_path = tmp_path / f"texts/proprium/{SLUG}.json"
    put(core_path, core)
    for lang in ("pl", "en"):
        base = tmp_path / "languages" / lang
        put(base / f"texts/proprium/{SLUG}.json", layers[lang])
        put(
            base / "manifest.json",
            {
                "schema_version": core["schema_version"],
                "language": lang,
                "direction": "ltr",
                "texts": [TEXT],
            },
        )
        put(
            base / "bibliography.json",
            {"schema_version": bibliography.SCHEMA, "language": lang, "uses": []},
        )
        ledger = read(ROOT / "languages" / lang / "translation-provenance.json")
        ledger["sites"] = [r for r in ledger["sites"] if r["text"] == TEXT]
        put(base / "translation-provenance.json", ledger)
    store.clear_caches()
    assert translation_provenance.check(tmp_path)[0] == []
    broken = copy.deepcopy(core)
    words(broken)["w056"]["morph"].pop("gender")
    put(core_path, broken)
    assert any("stale source_sha256" in e for e in translation_provenance.check(tmp_path)[0])
    put(core_path, core)
    assert translation_provenance.check(tmp_path)[0] == []
    target_path = tmp_path / f"languages/en/texts/proprium/{SLUG}.json"
    broken = copy.deepcopy(layers["en"])
    broken["segments"]["s01"]["translation"] += " Added words."
    put(target_path, broken)
    assert any("stale target_sha256" in e for e in translation_provenance.check(tmp_path)[0])
    put(target_path, layers["en"])
    assert translation_provenance.check(tmp_path)[0] == []
    path = tmp_path / "languages/en/translation-provenance.json"
    ledger = read(path)
    ledger["sites"][0]["review"] = "internally-reviewed"
    put(path, ledger)
    assert any(
        "unsettled origin cannot claim review" in e
        for e in translation_provenance.check(tmp_path)[0]
    )
    ledger["sites"][0]["review"] = "working"
    put(path, ledger)
    assert translation_provenance.check(tmp_path)[0] == []
    store.clear_caches()


def test_source_chain_remains_pending_but_exact_and_mutations_reject():
    core, _ = actual()
    graph = read(ROOT / "bibliography/graph.json")
    graph["witnesses"] = [w for w in graph["witnesses"] if w["text"] == TEXT]
    graph["collations"] = [c for c in graph["collations"] if c["text"] == TEXT]
    assert len(graph["witnesses"]) == 2 and len(graph["collations"]) == 1
    assert all(
        r["review"] == {"status": "pending"} for r in graph["witnesses"] + graph["collations"]
    )
    use = next(u for u in graph["uses"] if u["id"] == f"use.{TEXT}.mr1962")
    assert use["role"] == "direct_approved_print"
    witness = next(w for w in graph["witnesses"] if w["id"] == f"witness.{TEXT}.mr1962")
    assert witness["source_dependencies"] == {"uses": [], "raw_binding": None}
    assert validate_bindings(ROOT, graph) == []
    broken = copy.deepcopy(graph)
    broken["witnesses"][0]["transcription_sha256"] = "0" * 64
    assert any("transcription_sha256 differs" in e for e in validate_bindings(ROOT, broken))
    assert validate_bindings(ROOT, graph) == []
    witness_dir = ROOT / "witnesses" / TEXT
    assert collate(expand_core(core), witness_dir)[0] == []
    corrupted = copy.deepcopy(core)
    words(corrupted)["w094"]["form"] = "Dei"
    assert collate(expand_core(corrupted), witness_dir)[0]
    assert collate(expand_core(core), witness_dir)[0] == []


@pytest.mark.parametrize("lang", ["pl", "en"])
def test_own_prose_no_semicolon_and_notes_keep_alternatives(lang):
    core, layers = actual()
    layer = enrich_layer(core, layers[lang])
    assert prose.check(layer) == []
    for field in ("about", "w019", "w088"):
        broken = copy.deepcopy(layer)
        if field == "about":
            broken["about"] += "; extra"
        else:
            broken["words"][field]["note"] += "; extra"
        where = "about" if field == "about" else f"{field}.note"
        assert prose.check(broken) == [
            f"{TEXT}:{where}.{lang}: uses a semicolon — "
            "this edition's own prose has none. Use a full stop, or an 'and'"
        ]
        assert prose.check(layer) == []
    assert prose.check(layer) == []
    assert "Perfectus" in layer["words"]["w088"]["note"]
    assert "aetas" in layer["words"]["w088"]["note"]
    # Translation punctuation is governed by the sacred text, not own prose.
    assert ";" in layer["segments"]["s01"]["translation"]


@pytest.mark.parametrize(
    "lang,first,last,anchor,gloss,message",
    REVIEWED_GROUPS,
    ids=[f"{row[0]}-{row[1]:03d}-{row[2]:03d}" for row in REVIEWED_GROUPS],
)
def test_legal_but_wrong_anchor_fails_only_its_admitted_relation(
    lang, first, last, anchor, gloss, message
):
    core, layers = actual()
    reviewed_relations(core, layers)
    assert interlinear.check(expand_core(core), enrich_layer(core, layers[lang])) == []
    broken = copy.deepcopy(layers)
    changed = group(broken[lang], first, last)
    assert changed["gloss"] == gloss and changed["anchor"] == anchor
    changed["anchor"] = next(wid for wid in changed["words"] if wid != anchor)
    # Structurally legal is not semantically adjudicated by the native checker.
    assert interlinear.check(expand_core(core), enrich_layer(core, broken[lang])) == []
    with pytest.raises(AssertionError) as caught:
        reviewed_relations(core, broken)
    assert str(caught.value) == message
    changed["anchor"] = anchor
    assert broken == layers
    reviewed_relations(core, broken)
    assert interlinear.check(expand_core(core), enrich_layer(core, broken[lang])) == []

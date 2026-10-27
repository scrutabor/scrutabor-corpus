"""Finite Munda wording and analysis controls, not general translation rules."""

import copy
import json
from pathlib import Path

import pytest

from checks.lint import MORPH_ENUMS
from checks.translation_provenance import REVIEWS, canonical_hash, check, source_payload

ROOT = Path(__file__).resolve().parents[1]
TEXT = "ordinarium.munda-cor-meum"
PATH = "texts/ordinarium/munda-cor-meum.json"
LATIN = (
    "Munda cor meum, ac lábia mea, omnípotens Deus, qui lábia Isaíæ prophétæ "
    "cálculo mundásti igníto: ita me tua grata miseratióne dignáre mundáre, "
    "ut sanctum evangélium tuum digne váleam nuntiáre. "
    "Per Christum Dóminum nostrum. Amen."
)
PROSE = {
    "pl": (
        "Oczyść moje serce i moje wargi, wszechmogący Boże, który oczyściłeś wargi "
        "proroka Izajasza rozżarzonym kamieniem. Tak też w Twoim łaskawym miłosierdziu "
        "racz oczyścić mnie, abym mógł godnie głosić Twoją świętą Ewangelię."
    ),
    "en": (
        "Cleanse my heart and my lips, almighty God, who cleansed the lips of the "
        "prophet Isaiah with a glowing stone. In the same way, be pleased to cleanse "
        "me through Your gracious mercy, so that I can proclaim Your holy Gospel worthily."
    ),
}
ENDINGS = {"pl": "Przez Chrystusa, Pana naszego. Amen.", "en": "Through Christ our Lord. Amen."}
GROUPS = {
    "pl": [
        (2, 3, 2, "moje serce"),
        (5, 6, 5, "moje wargi"),
        (11, 12, 11, "proroka Izajasza"),
        (13, 15, 14, "oczyściłeś rozżarzonym kamieniem"),
        (24, 26, 25, "Twoją świętą Ewangelię"),
    ],
    "en": [
        (2, 3, 2, "my heart"),
        (5, 6, 5, "my lips"),
        (11, 12, 11, "of the prophet Isaiah"),
        (13, 15, 14, "cleansed with a glowing stone"),
        (18, 20, 20, "through Your gracious mercy"),
        (21, 22, 21, "be pleased to cleanse"),
        (24, 26, 25, "Your holy Gospel"),
        (32, 33, 32, "our Lord"),
    ],
}
DIRECT = {
    "pl": {
        1: "Oczyść",
        4: "i",
        7: "wszechmogący",
        8: "Boże",
        9: "który",
        10: "wargi",
        16: "tak",
        17: "mnie",
        18: "Twoim",
        19: "łaskawym",
        20: "miłosierdziem",
        21: "racz",
        22: "oczyścić",
        23: "abym",
        27: "godnie",
        28: "mógł",
        29: "głosić",
        30: "Przez",
        31: "Chrystusa",
        32: "Pana",
        33: "naszego",
        34: "Amen",
    },
    "en": {
        1: "Cleanse",
        4: "and",
        7: "almighty",
        8: "God",
        9: "who",
        10: "the lips",
        16: "likewise",
        17: "me",
        23: "so that",
        27: "worthily",
        28: "I may be able",
        29: "to proclaim",
        30: "Through",
        31: "Christ",
        34: "Amen",
    },
}


def load(path, root=ROOT):
    return json.loads((root / path).read_text(encoding="utf-8"))


def layer(language, root=ROOT):
    return load(f"languages/{language}/{PATH}", root)


def write(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def assert_captions(target, language):
    expected = [
        {
            "words": [f"w{i:03}" for i in range(first, last + 1)],
            "anchor": f"w{anchor:03}",
            "gloss": gloss,
        }
        for first, last, anchor, gloss in GROUPS[language]
    ]
    actual = [g for s in target["segments"].values() for g in s.get("alignments", [])]
    assert actual == expected
    grouped = [wid for g in actual for wid in g["words"]]
    direct = {f"w{i:03}": gloss for i, gloss in DIRECT[language].items()}
    assert len(grouped) == len(set(grouped))
    assert set(grouped).isdisjoint(direct)
    assert set(grouped) | set(direct) == {f"w{i:03}" for i in range(1, 35)}
    assert set(target["words"]) == {f"w{i:03}" for i in range(1, 35)}
    for wid in grouped:
        assert "gloss" not in target["words"][wid]
    for wid, gloss in direct.items():
        assert target["words"][wid]["gloss"] == gloss


def test_finite_latin_segments_and_critical_syntax():
    core = load(PATH)
    assert [s["id"] for s in core["segments"]] == ["s01", "s02"]
    assert [len(s["words"]) for s in core["segments"]] == [29, 5]
    words = [w for s in core["segments"] for w in s["words"]]
    assert [w["id"] for w in words] == [f"w{i:03}" for i in range(1, 35)]
    assert " ".join(w["form"] + w.get("post", "") for w in words) == LATIN
    assert core["ids"] == {"next": 35, "segments": {"next": 3}}
    assert all((s["speaker"], s["voice"]) == ("sacerdos", "secreto") for s in core["segments"])
    by_id = {w["id"]: w for w in words}
    assert by_id["w011"]["morph"]["case"] == by_id["w012"]["morph"]["case"] == "gen"
    assert by_id["w013"]["lemma"] == "calculus"
    assert by_id["w015"]["lemma"] == "ignio"
    assert by_id["w015"]["head"] == "w013"
    assert {k: by_id["w015"]["morph"][k] for k in ("case", "mood", "voice")} == {
        "case": "abl",
        "mood": "part",
        "voice": "pass",
    }
    assert by_id["w021"]["lemma"] == "dignor"
    assert by_id["w021"]["morph"]["voice"] == "dep"
    assert by_id["w021"]["morph"]["mood"] == "imp"
    assert by_id["w028"]["morph"]["mood"] == "subj"
    assert by_id["w028"]["morph"]["person"] == 1
    assert by_id["w029"]["morph"]["mood"] == "inf"


@pytest.mark.parametrize("language", ["pl", "en"])
def test_complete_caption_constructions(language):
    assert_captions(layer(language), language)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_complete_continuous_prayer_keeps_stone_mercy_and_purpose(language):
    target = layer(language)
    assert target["segments"]["s01"]["translation"] == PROSE[language]
    assert target["segments"]["s02"]["translation"] == ENDINGS[language]


def test_localization_preserves_the_stated_uncertainty_not_an_added_heating_event():
    core = load(PATH)
    assert core["localization"] == {
        "about": True,
        "notes": ["w015"],
        "explanations": {
            "w013": {},
            "w014": {"languages": ["en"]},
            "w019": {},
            "w021": {"languages": ["en"]},
            "w028": {"languages": ["en"]},
        },
    }
    analysis = core["editorial"]["words"]["w015"]["analysis"]
    assert (analysis["confidence"], analysis["review"]) == ("medium", "disputed")
    for language in ("pl", "en"):
        target = layer(language)
        assert target["about"]
        assert target["words"]["w013"]["explanation"]
        assert target["words"]["w019"]["explanation"]
        assert target["words"]["w015"]["note"]
    assert "przymiotnik" in layer("pl")["words"]["w015"]["note"]
    assert "adjective" in layer("en")["words"]["w015"]["note"]
    assert "does not narrate a separate act of heating" in layer("en")["words"]["w015"]["note"]
    assert "does not claim" in layer("en")["words"]["w021"]["explanation"]
    assert "not as grateful" in layer("en")["words"]["w019"]["explanation"]
    english = layer("en")["words"]
    assert english["w014"]["explanation"] == (
        "The lips are the object of mundásti. Cálculo ... igníto names the glowing stone "
        "as the means of cleansing, with the verb placed between the noun and its modifier."
    )
    assert english["w028"]["explanation"] == (
        "Váleam expresses the ability sought in the purpose clause. Nuntiáre completes it, "
        "and the object of nuntiáre, sanctum evangélium tuum, comes earlier in the Latin."
    )
    assert english["w021"]["explanation"].endswith(
        " The earlier me is the object of mundáre, not the subject of this request."
    )


@pytest.mark.parametrize("lemma", ["calculus", "ignio"])
def test_two_new_lemma_links_retain_stone_and_heating_senses(lemma):
    neutral = load("lexicon/lemmata.json")["entries"][lemma]
    expected = {
        "calculus": (
            {"head": "cálculus, -i", "pos": "noun", "gender": "m", "decl": 2},
            ["kamyk", "kamień"],
            ["small stone", "counting stone", "calculation"],
        ),
        "ignio": (
            {"head": "ígnio, igníre, ignívi, ignítum", "pos": "verb", "conj": 4},
            ["rozpalać", "rozżarzać"],
            ["to set on fire", "to make red-hot"],
        ),
    }
    head, polish, english = expected[lemma]
    assert neutral == head
    assert load("languages/pl/lexicon.json")["entries"][lemma] == {"senses": polish}
    assert load("languages/en/lexicon.json")["entries"][lemma] == {"senses": english}


def assert_declared_lemma_pos(entry, words):
    assert words
    primary = entry.get("pos")
    assert isinstance(primary, str) and primary in MORPH_ENUMS["pos"]
    declared = {primary}
    if "pos_alt" in entry:
        secondary = entry["pos_alt"]
        assert isinstance(secondary, str) and secondary in MORPH_ENUMS["pos"]
        declared.add(secondary)
    assert all(word["morph"]["pos"] in declared for word in words)


@pytest.mark.parametrize("language", ["neutral", "pl", "en"])
def test_existing_lemma_links_resolve_complete_cards(language):
    words = [w for s in load(PATH)["segments"] for w in s["words"]]
    lemmas = {w["lemma"] for w in words} - {"calculus", "ignio"}
    assert lemmas == {
        "Christus",
        "Isaias",
        "ac",
        "amen",
        "cor",
        "deus",
        "digne",
        "dignor",
        "dominus",
        "ego",
        "evangelium",
        "gratus",
        "ita",
        "labium",
        "meus",
        "miseratio",
        "mundo",
        "noster",
        "nuntio",
        "omnipotens",
        "per",
        "propheta",
        "qui",
        "sanctus",
        "tuus",
        "ut",
        "valeo",
    }
    path = "lexicon/lemmata.json" if language == "neutral" else f"languages/{language}/lexicon.json"
    entries = load(path)["entries"]
    for lemma in sorted(lemmas):
        entry = entries[lemma]
        if language == "neutral":
            assert isinstance(entry["head"], str) and entry["head"].strip()
            assert_declared_lemma_pos(entry, [w for w in words if w["lemma"] == lemma])
        else:
            assert entry["senses"]
            assert all(isinstance(sense, str) and sense.strip() for sense in entry["senses"])


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize(
    "defect", ["coal", "oversized-group", "relative-subject", "mercy", "purpose", "dignare"]
)
def test_finite_caption_controls_reject_defect_and_accept_restoration(language, defect):
    target = layer(language)
    original = copy.deepcopy(target)
    assert_captions(target, language)
    groups = target["segments"]["s01"]["alignments"]
    if defect == "coal":
        group = next(g for g in groups if "w013" in g["words"])
        group["gloss"] = group["gloss"].replace("kamieniem", "węglem").replace("stone", "coal")
    elif defect == "oversized-group":
        groups[0]["words"].append("w004")
    elif defect == "relative-subject":
        target["words"]["w009"]["gloss"] = "on" if language == "pl" else "he"
    elif defect == "mercy":
        if language == "pl":
            target["words"]["w019"]["gloss"] = "wdzięcznym"
        else:
            group = next(g for g in groups if "w019" in g["words"])
            group["gloss"] = group["gloss"].replace("gracious", "grateful")
    elif defect == "purpose":
        target["words"]["w023"]["gloss"] = "ponieważ" if language == "pl" else "because"
    elif language == "pl":
        target["words"]["w021"]["gloss"] = "zasłużyłem"
    else:
        group = next(g for g in groups if "w021" in g["words"])
        group["gloss"] = "my merit allows me to cleanse myself"
    assert target != original
    try:
        with pytest.raises(AssertionError):
            assert_captions(target, language)
    finally:
        target.clear()
        target.update(original)
    assert target == original
    assert_captions(target, language)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_each_language_has_independent_body_and_exact_inherited_ending_provenance(language):
    core = load(PATH)
    target = layer(language)
    rows = [
        r
        for r in load(f"languages/{language}/translation-provenance.json")["sites"]
        if r["text"] == TEXT
    ]
    assert [r["segment"] for r in rows] == ["s01", "s02"]
    assert [r["origin"] for r in rows] == ["own", "public-domain"]
    for row, segment in zip(rows, core["segments"], strict=True):
        assert row["site"] == f"{TEXT}.{segment['id']}.{language}"
        assert row["language"] == language
        assert row["familiar_core"] is False
        assert row["review"] in REVIEWS
        assert row["source_sha256"] == canonical_hash(source_payload(segment))
        assert row["target_sha256"] == canonical_hash(
            target["segments"][segment["id"]]["translation"]
        )


@pytest.fixture
def provenance_corpus(tmp_path):
    graph = tmp_path / "bibliography/graph.json"
    graph.parent.mkdir(parents=True, exist_ok=True)
    graph.write_bytes((ROOT / "bibliography/graph.json").read_bytes())
    write(tmp_path, PATH, load(PATH))
    for language in ("pl", "en"):
        prefix = f"languages/{language}/"
        write(tmp_path, prefix + PATH, layer(language))
        for name, key in (
            ("manifest", "texts"),
            ("translation-provenance", "sites"),
            ("bibliography", "uses"),
        ):
            document = load(prefix + name + ".json")
            document[key] = (
                [TEXT]
                if name == "manifest"
                else [
                    r
                    for r in document[key]
                    if (r.get("text") if key == "sites" else r.get("address", {}).get("text"))
                    == TEXT
                ]
            )
            write(tmp_path, prefix + name + ".json", document)
    return tmp_path


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("field", ["source", "target"])
def test_real_provenance_check_rejects_staleness_and_accepts_restoration(
    provenance_corpus, language, field
):
    root = provenance_corpus
    assert check(root) == ([], {"own": 2, "public-domain": 2})
    path = PATH if field == "source" else f"languages/{language}/{PATH}"
    original = (root / path).read_bytes()
    changed = load(path, root)
    if field == "source":
        changed["segments"][0]["words"][12]["form"] = "carbóne"
    else:
        changed["segments"]["s01"]["translation"] += " Added claim."
    write(root, path, changed)
    errors, tally = check(root)
    assert sum(tally.values()) == 4
    assert any(f"{TEXT}.s01.{language}: stale {field}_sha256" == error for error in errors)
    (root / path).write_bytes(original)
    assert check(root) == ([], {"own": 2, "public-domain": 2})


@pytest.mark.parametrize("language", ["pl", "en"])
def test_real_provenance_check_rejects_removed_ending_basis_and_accepts_restoration(
    provenance_corpus, language
):
    root = provenance_corpus
    assert (root / "bibliography/graph.json").read_bytes() == (
        ROOT / "bibliography/graph.json"
    ).read_bytes()
    assert check(root) == ([], {"own": 2, "public-domain": 2})
    path = f"languages/{language}/bibliography.json"
    original = (root / path).read_bytes()
    document = load(path, root)
    assert [use["id"] for use in document["uses"]] == [
        f"use.{language}.munda-cor-meum.short-conclusion"
    ]
    use = document["uses"][0]
    assert use["role"] == "historical_wording_basis"
    assert use["decision"] in {"RETAIN", "RETAIN_WITH_CORRECTION"}
    assert use["address"] == {"kind": "segment", "text": TEXT, "segment": "s02"}
    assert not layer(language, root)["segments"]["s02"].get("translation_citations")
    use["decision"] = "REMOVE"
    use["decision_reason"] = "This fixture's sole ending basis is withheld."
    try:
        write(root, path, document)
        errors, tally = check(root)
        assert tally == {"own": 2, "public-domain": 2}
        assert errors == [
            f"{TEXT}.s02.{language}: origin=public-domain requires a wording citation"
        ]
    finally:
        (root / path).write_bytes(original)
    assert (root / path).read_bytes() == original
    assert check(root) == ([], {"own": 2, "public-domain": 2})


def test_lemma_link_accepts_declared_secondary_and_rejects_undeclared_pos():
    words = [{"morph": {"pos": "adj"}}]
    original_words = copy.deepcopy(words)
    entry = {"pos": "noun", "pos_alt": "adj"}
    original_entry = copy.deepcopy(entry)
    assert_declared_lemma_pos(entry, words)
    entry.pop("pos_alt")
    try:
        with pytest.raises(AssertionError):
            assert_declared_lemma_pos(entry, words)
    finally:
        entry.clear()
        entry.update(original_entry)
    assert entry == original_entry
    assert_declared_lemma_pos(entry, words)
    assert_declared_lemma_pos({"pos": "adj"}, words)
    with pytest.raises(AssertionError):
        assert_declared_lemma_pos(entry, [])
    assert words == original_words


@pytest.mark.parametrize(
    "entry",
    [
        {},
        {"pos": ""},
        {"pos": "adj", "pos_alt": ""},
        {"pos": "adj", "pos_alt": None},
        {"pos": "unlisted", "pos_alt": "adj"},
        {"pos": "adj", "pos_alt": "unlisted"},
        {"pos": "noun", "pos_alt": "adv"},
    ],
    ids=[
        "missing-primary",
        "empty-primary",
        "empty-secondary",
        "null-secondary",
        "unknown-primary",
        "unknown-secondary",
        "undeclared-context-pos",
    ],
)
def test_lemma_link_rejects_invalid_or_unrelated_declarations(entry):
    words = [{"morph": {"pos": "adj"}}]
    original = copy.deepcopy((entry, words))
    with pytest.raises(AssertionError):
        assert_declared_lemma_pos(entry, words)
    assert (entry, words) == original

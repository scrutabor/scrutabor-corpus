"""The complete Requiem bodies keep their recipients, wishes and word providers."""

import copy
import json
from pathlib import Path

import pytest

from build_reader import emit, store
from build_reader.layers import expand_core
from checks.interlinear import check as alignment_errors
from checks.language_packs import check_layer
from checks.lexicon import check_text_against_lexicon
from checks.participation_performance import publication_errors as agnus_errors
from checks.requiem_dismissal import publication_errors as dismissal_errors

CORPUS = Path(__file__).resolve().parents[1]
AGNUS = "ordinarium.agnus-dei-defunctorum"
DISMISSAL = "ordinarium.ite-missa-est-defunctorum"
TEXTS = [AGNUS, DISMISSAL]
LAYERS = [(text, language) for text in TEXTS for language in ("pl", "en")]
LINES = {
    AGNUS: [
        "Agnus Dei, qui tollis peccáta mundi: dona eis réquiem.",
        "Agnus Dei, qui tollis peccáta mundi: dona eis réquiem.",
        "Agnus Dei, qui tollis peccáta mundi: dona eis réquiem sempitérnam.",
    ],
    DISMISSAL: [
        "Dóminus vobíscum.",
        "Et cum spíritu tuo.",
        "Requiéscant in pace.",
        "Amen.",
    ],
}
ENGLISH_GROUPS = {
    AGNUS: [
        ("s01", ["w003", "w004"], "w004", "You who take away"),
        ("s02", ["w012", "w013"], "w013", "You who take away"),
        ("s03", ["w021", "w022"], "w022", "You who take away"),
        ("s03", ["w027", "w028"], "w027", "everlasting rest"),
    ],
    DISMISSAL: [
        ("s01", ["w001", "w002"], "w001", "The Lord be with you"),
        ("s02", ["w005", "w006"], "w005", "your spirit"),
    ],
}


def read(relative, root=CORPUS):
    return json.loads((root / relative).read_text(encoding="utf-8"))


def raw(text, language=None):
    relative = f"texts/{text.replace('.', '/', 1)}.json"
    return read(f"languages/{language}/{relative}" if language else relative)


def words(doc):
    return {word["id"]: word for segment in doc["segments"] for word in segment["words"]}


def guard(doc):
    return agnus_errors(doc) if doc["id"] == AGNUS else dismissal_errors(doc)


@pytest.mark.parametrize("text,count", [(AGNUS, 28), (DISMISSAL, 10)])
def test_complete_source_bodies_have_stable_verse_and_word_boundaries(text, count):
    core = raw(text)
    assert [segment["id"] for segment in core["segments"]] == [
        f"s{n:02}" for n in range(1, len(LINES[text]) + 1)
    ]
    assert [
        " ".join(word.get("pre", "") + word["form"] + word.get("post", "") for word in s["words"])
        for s in core["segments"]
    ] == LINES[text]
    assert list(words(core)) == [f"w{n:03}" for n in range(1, count + 1)]
    assert core["ids"] == {
        "next": count + 1,
        "segments": {"next": len(LINES[text]) + 1},
    }
    assert core["editorial"]["status"] == "working-edition"
    assert core["editorial"]["analysis_defaults"] == {
        "confidence": "high",
        "sources": ["editorial"],
        "review": "pending",
    }
    expanded = expand_core(core)
    for identity, word in words(expanded).items():
        analysis = word.get("analysis", expanded["analysis_defaults_words"])
        providers = ["editorial", "whitakers"]
        if (text, identity) != (DISMISSAL, "w002"):
            providers.append("collatinus")
        assert analysis == {"confidence": "high", "sources": providers, "review": "pending"}
    assert guard(core) == []


def test_agnus_addresses_the_lamb_and_petitions_for_them_with_third_only_everlasting():
    core = raw(AGNUS)
    rows = words(core)
    for start in (1, 10, 19):
        address = rows[f"w{start:03}"]
        assert address["lemma"] == "agnus"
        assert address["morph"] == {
            "pos": "noun",
            "case": "nom",
            "number": "sg",
            "gender": "m",
            "decl": 2,
        }
        assert rows[f"w{start + 3:03}"]["lemma"] == "tollo"
        assert rows[f"w{start + 3:03}"]["morph"] == {
            "pos": "verb",
            "person": 2,
            "number": "sg",
            "tense": "pres",
            "mood": "ind",
            "voice": "act",
            "conj": 3,
        }
        petition = rows[f"w{start + 6:03}"]
        assert petition["lemma"] == "dono"
        assert petition["morph"] == {
            "pos": "verb",
            "person": 2,
            "number": "sg",
            "tense": "pres",
            "mood": "imp",
            "voice": "act",
            "conj": 1,
        }
        recipient = rows[f"w{start + 7:03}"]
        assert recipient["lemma"] == "is"
        assert recipient["morph"] == {"pos": "pron", "case": "dat", "number": "pl"}
        assert rows[f"w{start + 8:03}"]["lemma"] == "requies"
    assert [
        (s["id"], w["id"])
        for s in core["segments"]
        for w in s["words"]
        if w["lemma"] == "sempiternus"
    ] == [("s03", "w028")]
    assert rows["w028"]["head"] == "w027"
    assert rows["w028"]["morph"] == {
        "pos": "adj",
        "case": "acc",
        "number": "sg",
        "gender": "f",
    }
    for language, caption in (("pl", "im"), ("en", "them")):
        layer = raw(AGNUS, language)
        assert [layer["words"][identity]["gloss"] for identity in ("w008", "w017", "w026")] == [
            caption
        ] * 3


def test_dismissal_keeps_human_greeting_addresses_and_plural_subjunctive_wish():
    core = raw(DISMISSAL)
    rows = words(core)
    assert rows["w002"]["lemma"] == "vos"
    assert rows["w002"]["morph"] == {"pos": "pron", "case": "abl", "number": "pl"}
    assert rows["w004"]["morph"] == {"pos": "prep", "governs": "abl"}
    assert rows["w004"]["head"] == rows["w006"]["head"] == "w005"
    assert rows["w006"]["morph"] == {
        "pos": "adj",
        "case": "abl",
        "number": "sg",
        "gender": "m",
    }
    assert rows["w007"]["lemma"] == "requiesco"
    assert rows["w007"]["morph"] == {
        "pos": "verb",
        "person": 3,
        "number": "pl",
        "tense": "pres",
        "mood": "subj",
        "voice": "act",
        "conj": 3,
    }
    assert rows["w008"]["head"] == "w009"
    assert rows["w008"]["morph"] == {"pos": "prep", "governs": "abl"}
    english = raw(DISMISSAL, "en")
    assert english["segments"]["s01"]["translation"] == "The Lord be with you."
    assert english["segments"]["s02"]["translation"] == "And with your spirit."
    assert english["words"]["w007"]["gloss"] == "May they rest"
    assert english["segments"]["s03"]["translation"] == "May they rest in peace."


@pytest.mark.parametrize("text", TEXTS)
def test_every_body_lemma_and_paradigm_has_both_language_entries(text):
    core = raw(text)
    heads = read("lexicon/lemmata.json")["entries"]
    assert check_text_against_lexicon(core, heads) == []
    used = {word["lemma"] for word in words(core).values()}
    for language in ("pl", "en"):
        entries = read(f"languages/{language}/lexicon.json")["entries"]
        assert used <= entries.keys()
        assert all(entries[lemma]["senses"] for lemma in used)


@pytest.mark.parametrize(
    "text,fault",
    [
        (AGNUS, "recipient-first"),
        (AGNUS, "recipient-second"),
        (AGNUS, "recipient-third"),
        (AGNUS, "eternity-missing"),
        (AGNUS, "eternity-first"),
        (DISMISSAL, "assertion"),
        (DISMISSAL, "ordinary-response"),
    ],
)
def test_source_owned_body_guard_rejects_wrong_requiem_reading_and_recovers(text, fault):
    good = raw(text)
    assert guard(good) == []
    bad = copy.deepcopy(good)
    damaged_input = bad
    try:
        if fault.startswith("recipient-"):
            identity = {
                "recipient-first": "w008",
                "recipient-second": "w017",
                "recipient-third": "w026",
            }[fault]
            words(bad)[identity]["form"] = "nobis"
        elif fault == "eternity-missing":
            bad["segments"][2]["words"].pop()
        elif fault == "eternity-first":
            bad["segments"][0]["words"].append(copy.deepcopy(bad["segments"][2]["words"][-1]))
        elif fault == "assertion":
            words(bad)["w007"]["form"] = "Requiéscunt"
        else:
            words(bad)["w010"]["form"] = "Deo"
        assert guard(bad)
    finally:
        bad.clear()
        bad.update(copy.deepcopy(good))
    assert bad is damaged_input
    assert bad == good
    assert guard(bad) == []
    # These finite recensions do not ban nobis or another prayer's different address.
    assert agnus_errors(raw("ordinarium.agnus-dei")) == []


@pytest.mark.parametrize("text,language", LAYERS)
def test_each_token_has_one_provider_and_only_the_declared_explanations(text, language):
    core, layer = raw(text), raw(text, language)
    path = CORPUS / f"languages/{language}/texts/{text.replace('.', '/', 1)}.json"
    assert check_layer(core, layer, path) == []
    actual = [
        (segment, group["words"], group["anchor"], group["gloss"])
        for segment, entry in layer["segments"].items()
        for group in entry.get("alignments", [])
    ]
    assert actual == (ENGLISH_GROUPS[text] if language == "en" else [])
    grouped = {word for _, members, _, _ in actual for word in members}
    direct = {word for word, entry in layer["words"].items() if "gloss" in entry}
    assert not grouped & direct and grouped | direct == words(core).keys()
    assert {word for word, entry in layer["words"].items() if "explanation" in entry} == set(
        core["localization"]["explanations"]
    )


@pytest.mark.parametrize("text,language", LAYERS)
@pytest.mark.parametrize("fault", ["missing", "duplicate", "placeholder"])
def test_actual_alignment_checker_rejects_missing_duplicate_and_marker_providers(
    text, language, fault
):
    core, good = raw(text), raw(text, language)
    assert alignment_errors(core, good) == []
    bad = copy.deepcopy(good)
    damaged_input = bad
    try:
        direct = next(word for word, entry in bad["words"].items() if "gloss" in entry)
        if fault == "missing":
            del bad["words"][direct]["gloss"]
        elif fault == "placeholder":
            bad["words"][direct]["gloss"] = "[DAT]"
        else:
            segment = next(
                s for s in core["segments"] if any(w["id"] == direct for w in s["words"])
            )
            bad["segments"][segment["id"]].setdefault("alignments", []).insert(
                0, {"words": [direct], "reason": "inflection"}
            )
        assert alignment_errors(core, bad)
    finally:
        bad.clear()
        bad.update(copy.deepcopy(good))
    assert bad is damaged_input
    assert bad == good
    assert alignment_errors(core, bad) == []


@pytest.mark.parametrize("text,language", LAYERS)
def test_explanation_topology_cannot_drop_a_declared_occurrence(text, language):
    core, good = raw(text), raw(text, language)
    path = CORPUS / f"languages/{language}/texts/{text.replace('.', '/', 1)}.json"
    assert check_layer(core, good, path) == []
    bad = copy.deepcopy(good)
    damaged_input = bad
    try:
        identity = next(iter(core["localization"]["explanations"]))
        del bad["words"][identity]["explanation"]
        assert any(
            "explanation topology differs" in error for error in check_layer(core, bad, path)
        )
    finally:
        bad.clear()
        bad.update(copy.deepcopy(good))
    assert bad is damaged_input
    assert bad == good
    assert check_layer(core, bad, path) == []


@pytest.mark.parametrize("text,language", LAYERS)
def test_actual_reader_preserves_every_word_actor_and_target_provider(reader_out, text, language):
    core, layer = raw(text), raw(text, language)
    relative = f"texts/{text.replace('.', '/', 1)}.json"
    artifact = read(relative, reader_out)
    language_artifact = read(f"languages/{language}/{relative}", reader_out)
    doc, expanded = emit.expand(
        artifact,
        language_artifact,
        read("tables/morphology.json", reader_out),
        read("tables/analysis.json", reader_out),
        read("tables/citations.json", reader_out),
        read(f"languages/{language}/citations.json", reader_out),
    )
    assert doc["segments"] == expand_core(core)["segments"]
    assert doc["status"] == "working-edition" and doc["analysis_defaults"]["review"] == "pending"
    assert doc["analysis_defaults_words"] == core["editorial"]["analysis_defaults_words"]
    assert expanded["words"] == layer["words"]
    assert expanded["segments"] == layer["segments"]
    assert expanded["about"] == layer["about"]
    assert alignment_errors(doc, expanded) == []
    manifest = read(f"languages/{language}/manifest.json", reader_out)
    assert [entry["path"] for entry in manifest["texts"] if entry["id"] == text] == [
        f"languages/{language}/{relative}"
    ]
    assert text in store.language_manifest(CORPUS, language)["texts"]

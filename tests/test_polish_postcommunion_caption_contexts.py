"""Finite Polish postcommunion constructions and their retained semantic payloads."""

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.layers import expand_core
from checks import interlinear
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
PETER = "cathedra-sancti-petri-postcommunio"
HEART = "sacratissimi-cordis-iesu-postcommunio"
CORPUS = "corporis-christi-postcommunio"
RETAINED = {
    PETER: (
        "s04",
        "6daa61300048a0cdb8d20c727f124deaf10888a2427ff471fbf84d5c764e62ff",
        "c76c729afe5795544ff11c6c3b265cf888675ea1dd23cfc544b4fb6b056ce738",
    ),
    HEART: (
        "s01",
        "92621d78a49e58620945536464c1420be71cd3bb51e68460f0430e3681a0a9ce",
        "3a914c38e646330c5a72c7ede9c7ed37161b6f3821f0ad5be688bccd2765f73d",
    ),
    CORPUS: (
        "s01",
        "da798e4c389a998ea383f740e5d5167a4bdf638a13c5b8ecf778d52bb7f23621",
        "1e21f05b0ee8dfde522648e667c3950a931f7ba5e1edf8016d68e06c4c1fbf3a",
    ),
}
JOY = {
    "words": ["w005", "w006", "w007", "w008"],
    "anchor": "w008",
    "gloss": "wieczną radością z Twojego Bóstwa",
}
EXPLANATION = (
    "„Quo” odnosi się do żaru („fervórem”). Zdanie z „discámus” wyraża zamierzony skutek: "
    "abyśmy dzięki temu żarowi nauczyli się gardzić tym, co ziemskie, i miłować to, co niebieskie."
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def load(slug):
    path = Path("texts/proprium") / f"{slug}.json"
    return tuple(
        json.loads((prefix / path).read_text(encoding="utf-8"))
        for prefix in (ROOT, ROOT / "languages/pl")
    )


def words(core):
    return {word["id"]: word for segment in core["segments"] for word in segment.get("words", [])}


def assert_context(slug, core, layer):
    indexed = words(core)
    if slug == PETER:
        segment = next(segment for segment in core["segments"] if segment["id"] == "s04")
        require(
            segment["words"][0]["id"] == "w044" and indexed["w044"]["lemma"] == "sanctifico",
            "Paul prayer opening context",
        )
        require(layer["words"]["w044"].get("gloss") == "Uświęceni", "Paul prayer caption onset")
    elif slug == HEART:
        require(
            indexed["w007"].get("substantive") and indexed["w007"]["morph"]["case"] == "nom",
            "holy gifts nominal subject",
        )
        require(
            layer["words"]["w006"].get("gloss") == "Twoje"
            and layer["words"]["w007"].get("gloss") == "święte dary",
            "holy gifts caption subject",
        )
        require(
            indexed["w009"]["lemma"] == "qui"
            and indexed["w009"]["morph"]["case"] == "abl"
            and indexed["w009"]["morph"]["gender"] == "m",
            "ardor instrumental relative",
        )
        require(
            (
                indexed["w015"]["morph"]["person"],
                indexed["w015"]["morph"]["number"],
                indexed["w015"]["morph"]["mood"],
            )
            == (1, "pl", "subj"),
            "learners first plural source",
        )
        require(
            layer["words"]["w009"].get("gloss") == "abyśmy dzięki niemu"
            and layer["words"]["w015"].get("gloss") == "nauczyli się",
            "learners first plural caption governor",
        )
        assert_note(core, layer)
    else:
        require(
            indexed["w008"]["lemma"] == "fruitio"
            and indexed["w008"]["morph"]["gender"] == "f"
            and indexed["w010"]["morph"]["gender"] == "f",
            "enjoyment relative source",
        )
        require(
            layer["segments"]["s01"].get("alignments") == [JOY]
            and all("gloss" not in layer["words"][word] for word in JOY["words"]),
            "enjoyment complete Polish construction",
        )
        require(
            layer["words"]["w010"].get("gloss") == "którą", "enjoyment feminine caption relative"
        )


def assert_note(core, layer):
    require(
        core["localization"].get("explanations") == {"w009": {"languages": ["pl"]}},
        "ardor explanation Polish-only scope",
    )
    require(
        layer["words"]["w009"].get("explanation") == EXPLANATION,
        "ardor relative-purpose explanation",
    )


def assert_retained(slug, core, layer, rows):
    segment, source_hash, target_hash = RETAINED[slug]
    source = next(item for item in core["segments"] if item["id"] == segment)
    require(
        canonical_hash(source_payload(source)) == source_hash,
        "retained Postcommunion semantic source",
    )
    require(
        canonical_hash(layer["segments"][segment]["translation"]) == target_hash,
        "retained Postcommunion prose",
    )
    text = "proprium." + slug
    require(
        [row for row in rows if row["site"] == f"{text}.{segment}.pl"]
        == [
            {
                "site": f"{text}.{segment}.pl",
                "text": text,
                "segment": segment,
                "language": "pl",
                "familiar_core": False,
                "origin": "working-unsettled",
                "review": "working",
                "source_sha256": source_hash,
                "target_sha256": target_hash,
            }
        ],
        "retained Postcommunion provenance state",
    )


@pytest.fixture(scope="module")
def documents():
    return {slug: load(slug) for slug in RETAINED}


@pytest.fixture(scope="module")
def provenance():
    return json.loads(
        (ROOT / "languages/pl/translation-provenance.json").read_text(encoding="utf-8")
    )["sites"]


@pytest.mark.parametrize("slug", tuple(RETAINED))
def test_actual_constructions_realize_every_position_once(documents, provenance, slug):
    core, layer = documents[slug]
    assert_context(slug, core, layer)
    assert_retained(slug, core, layer, provenance)
    expected = Counter(words(core).keys())
    actual = Counter(word for word, fields in layer["words"].items() if "gloss" in fields)
    actual.update(
        word
        for segment in layer["segments"].values()
        for group in segment.get("alignments", [])
        for word in group["words"]
    )
    assert actual == expected
    assert interlinear.check(expand_core(core), layer) == []


@pytest.mark.parametrize(
    "slug,word,value,message",
    (
        (PETER, "w044", "uświęceni", "Paul prayer caption onset"),
        (HEART, "w007", "święte", "holy gifts caption subject"),
        (HEART, "w009", "przez który", "learners first plural caption governor"),
        (HEART, "w015", "nauczyliśmy się", "learners first plural caption governor"),
        (CORPUS, "w010", "które", "enjoyment feminine caption relative"),
    ),
)
def test_real_copy_caption_mutants_fail_the_owned_guard(documents, slug, word, value, message):
    core, layer = documents[slug]
    saved = deepcopy(layer)
    assert_context(slug, core, layer)
    broken = deepcopy(layer)
    broken["words"][word]["gloss"] = value
    assert broken != layer
    with pytest.raises(AssertionError) as caught:
        assert_context(slug, core, broken)
    assert str(caught.value) == message
    assert_context(slug, core, layer)
    assert layer == saved


@pytest.mark.parametrize(
    "field,value", (("gloss", "wiecznym radowaniem się Bóstwa Twojego"), ("anchor", "w005"))
)
def test_group_does_not_hide_wrong_government_or_head(documents, field, value):
    core, layer = documents[CORPUS]
    assert_context(CORPUS, core, layer)
    broken = deepcopy(layer)
    broken["segments"]["s01"]["alignments"][0][field] = value
    with pytest.raises(AssertionError) as caught:
        assert_context(CORPUS, core, broken)
    assert str(caught.value) == "enjoyment complete Polish construction"
    assert_context(CORPUS, core, layer)


@pytest.mark.parametrize("defect", ("missing", "duplicate"))
def test_group_membership_is_checked_by_the_actual_checker(documents, defect):
    core, layer = documents[CORPUS]
    assert interlinear.check(expand_core(core), layer) == []
    broken = deepcopy(layer)
    if defect == "missing":
        broken["segments"]["s01"]["alignments"] = []
    else:
        broken["words"]["w005"]["gloss"] = "Bóstwa"
    assert (
        "proprium.corporis-christi-postcommunio:w005:pl: "
        "expected exactly one direct gloss or alignment"
        in interlinear.check(expand_core(core), broken)
    )
    assert interlinear.check(expand_core(core), layer) == []


@pytest.mark.parametrize("slug", tuple(RETAINED))
@pytest.mark.parametrize("defect", ("source", "prose", "origin", "review", "familiar_core"))
def test_caption_fix_cannot_promote_state_or_rewrite_semantics(documents, provenance, slug, defect):
    core, layer = documents[slug]
    assert_retained(slug, core, layer, provenance)
    changed_core, changed_layer, changed_rows = (
        deepcopy(core),
        deepcopy(layer),
        deepcopy(provenance),
    )
    segment = RETAINED[slug][0]
    if defect == "source":
        next(item for item in changed_core["segments"] if item["id"] == segment)["words"][0][
            "lemma"
        ] = "alius"
        message = "retained Postcommunion semantic source"
    elif defect == "prose":
        changed_layer["segments"][segment]["translation"] += " Inna treść."
        message = "retained Postcommunion prose"
    else:
        row = next(row for row in changed_rows if row["site"] == f"proprium.{slug}.{segment}.pl")
        row[defect] = {"origin": "own", "review": "expert-reviewed", "familiar_core": True}[defect]
        message = "retained Postcommunion provenance state"
    with pytest.raises(AssertionError) as caught:
        assert_retained(slug, changed_core, changed_layer, changed_rows)
    assert str(caught.value) == message
    assert_retained(slug, core, layer, provenance)


def test_unrelated_editorial_note_is_not_a_whole_core_lock(documents, provenance):
    core, layer = documents[HEART]
    changed = deepcopy(core)
    changed["editorial"]["notes"] = "A future contextual note."
    assert_context(HEART, changed, layer)
    assert_retained(HEART, changed, layer, provenance)


@pytest.mark.parametrize("defect", ("missing-note", "changed-note", "broadened-scope"))
def test_relative_purpose_note_has_exact_Polish_scope(documents, defect):
    core, layer = documents[HEART]
    assert_note(core, layer)
    changed_core, changed_layer = deepcopy(core), deepcopy(layer)
    if defect == "broadened-scope":
        changed_core["localization"]["explanations"]["w009"] = {}
        diagnostic = "ardor explanation Polish-only scope"
    else:
        if defect == "missing-note":
            del changed_layer["words"]["w009"]["explanation"]
        else:
            changed_layer["words"]["w009"]["explanation"] = "Quo is an extra ut."
        diagnostic = "ardor relative-purpose explanation"
    with pytest.raises(AssertionError) as caught:
        assert_note(changed_core, changed_layer)
    assert str(caught.value) == diagnostic
    assert_note(core, layer)


def test_Polish_note_does_not_require_or_supply_an_English_explanation(documents):
    assert_note(*documents[HEART])
    english = json.loads(
        (ROOT / "languages/en/texts/proprium" / f"{HEART}.json").read_text(encoding="utf-8")
    )
    assert "explanation" not in english["words"]["w009"]

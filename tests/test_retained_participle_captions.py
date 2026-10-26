"""Finite absolute constructions retain their agents and declared caption realizations."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.layers import expand_core
from checks import interlinear
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
XXI = "dominica-xxi-post-pentecosten-collecta"
EASTER = "dominica-v-post-pascha-collecta"
ALL = "omnium-sanctorum-secreta"
LATERAN = "dedicatio-archibasilicae-sanctissimi-salvatoris-secreta"
ADVENT = "dominica-i-adventus-collecta"
GROUPS = (
    (XXI, "pl", ("w012", "w013"), "w013", "przez Ciebie chroniona", ("przez Ciebie", "chroniona")),
    (XXI, "en", ("w012", "w013"), "w013", "with You protecting", ("by You", "being protected")),
    (EASTER, "pl", ("w012", "w013"), "w013", "za Twoim natchnieniem", ("za Twoim", "natchnieniem")),
    (
        EASTER,
        "pl",
        ("w018", "w019"),
        "w019",
        "pod Twoim kierownictwem",
        ("pod Twoim", "kierownictwem"),
    ),
)
RETAINED = {
    ("dedicatio-archibasilicae-sanctissimi-salvatoris-secreta", "en"): (
        "7fbdb76feab445fcd34a819e6bc4ea2d825fad82a6076f75c868dc85f19fe894",
        "4dcdab4d8a7212c575b6e5ae6ae6990c50f5daf7db80850babc794ef6f385475",
    ),
    ("dominica-i-adventus-collecta", "en"): (
        "1645edd94990daee5150864b08190e88611731c2845d881ad8dbb3bd592a020c",
        "f2d5a585232584b9f439c40de0f86230ee1fa4382de1f338a12484677f825fb6",
    ),
    ("dominica-v-post-pascha-collecta", "pl"): (
        "670030f1549406469e4f45d4802dea426493bb22a182c8567c754cec4c5b7317",
        "e63542282900c50217f3a838e56698e4b272b683b50309de77759b2daaf08dad",
    ),
    ("dominica-xxi-post-pentecosten-collecta", "en"): (
        "f5d9ca717613f1a6356098bcf52ab40f58bdf5cada03ac312cf513bae79c4532",
        "5fa682326d532b2e5ce2370b3fc2e12c64a91aaa908814926609a08a99280973",
    ),
    ("dominica-xxi-post-pentecosten-collecta", "pl"): (
        "f5d9ca717613f1a6356098bcf52ab40f58bdf5cada03ac312cf513bae79c4532",
        "661d04319248e8b9cfa607db90a6f61a6f52cc3ffc172f5222f2e692d7317b77",
    ),
    ("omnium-sanctorum-secreta", "en"): (
        "1413bc71e2a13cfcedc8722b1885de75b389abe02b18ef297e9e79babe9391c2",
        "0576730f5d828257a35b52f3e9ddd9563644802e588324d0050e206dc90f9d3f",
    ),
}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def load(stem, language):
    path = Path("texts/proprium") / f"{stem}.json"
    core = json.loads((ROOT / path).read_text(encoding="utf-8"))
    layer = json.loads((ROOT / "languages" / language / path).read_text(encoding="utf-8"))
    rows = json.loads(
        (ROOT / "languages" / language / "translation-provenance.json").read_text(encoding="utf-8")
    )["sites"]
    return core, layer, rows


def indexed(core):
    return {w["id"]: w for s in core["segments"] for w in s["words"]}


def assert_pair(core, pronoun, participle, lemma, voice="act"):
    words = indexed(core)
    agent, predicate = words[pronoun], words[participle]
    require(
        agent["lemma"] == "tu"
        and agent["morph"] == {"pos": "pron", "case": "abl", "number": "sg"}
        and predicate["lemma"] == lemma
        and predicate["head"] == pronoun
        and {
            k: predicate["morph"].get(k)
            for k in ("pos", "mood", "tense", "voice", "case", "gender", "number")
        }
        == dict(
            pos="verb", mood="part", tense="pres", voice=voice, case="abl", gender="m", number="sg"
        ),
        "absolute source agent and active meaning",
    )


def assert_group(core, layer, row):
    stem, language, members, anchor, gloss, _ = row
    require(
        (core["id"], layer["language"]) == ("proprium." + stem, language),
        "absolute subject identity",
    )
    lemma = "protego" if stem == XXI else ("inspiro" if members[0] == "w012" else "guberno")
    assert_pair(core, *members, lemma)
    expected = {"words": list(members), "anchor": anchor, "gloss": gloss}
    touching = [
        g for g in layer["segments"]["s01"].get("alignments", []) if set(g["words"]) & set(members)
    ]
    require(touching == [expected], "absolute caption realization")
    require(
        all("gloss" not in layer["words"][wid] for wid in members), "absolute once-only realization"
    )


def assert_control(stem, core, layer):
    require(layer["language"] == "en", "absolute control language")
    if stem in (ALL, LATERAN):
        first, second, lemma, predicate, voice = (
            ("w019", "w020", "miseror", "showing mercy", "dep")
            if stem == ALL
            else ("w015", "w016", "adiuvo", "helping", "act")
        )
        assert_pair(core, first, second, lemma, voice)
        require(
            not any(
                set(g["words"]) & {first, second}
                for g in layer["segments"]["s01"].get("alignments", [])
            ),
            "retained bare absolute",
        )
        require(
            (layer["words"][first].get("gloss"), layer["words"][second].get("gloss"))
            == ("You", predicate),
            "retained bare absolute",
        )
    else:
        assert_pair(core, "w014", "w016", "protego")
        assert_pair(core, "w018", "w019", "libero")
        group = {
            "words": ["w014", "w015", "w016"],
            "anchor": "w015",
            "gloss": "with You protecting, we may deserve",
        }
        touching = [
            g
            for g in layer["segments"]["s01"].get("alignments", [])
            if set(g["words"]) & set(group["words"])
        ]
        require(
            touching == [group] and all("gloss" not in layer["words"][w] for w in group["words"]),
            "retained interrupted absolute",
        )
        require(
            [layer["words"][w].get("gloss") for w in ("w017", "w018", "w019", "w020")]
            == ["to be rescued", "with You", "delivering", "to be saved"],
            "retained parallel passive complements",
        )


def assert_retained(stem, language, core, layer, rows):
    source_hash, target_hash = RETAINED[stem, language]
    segment = next(s for s in core["segments"] if s["id"] == "s01")
    require(
        canonical_hash(source_payload(segment)) == source_hash, "retained absolute semantic source"
    )
    require(
        canonical_hash(layer["segments"]["s01"]["translation"]) == target_hash,
        "retained absolute prose",
    )
    text = "proprium." + stem
    expected = dict(
        site=text + ".s01." + language,
        text=text,
        segment="s01",
        language=language,
        familiar_core=False,
        origin="working-unsettled",
        review="working",
        source_sha256=source_hash,
        target_sha256=target_hash,
    )
    require(
        [r for r in rows if r["site"] == expected["site"]] == [expected],
        "retained absolute provenance state",
    )


@pytest.mark.parametrize("row", GROUPS)
def test_actual_shared_phrases_have_one_consumer_realization(row):
    core, layer, rows = load(*row[:2])
    assert_group(core, layer, row)
    assert_retained(*row[:2], core, layer, rows)
    assert interlinear.check(expand_core(core), layer) == []
    for wid in row[2]:
        assert interlinear.effective_gloss(layer, wid) == (row[4] if wid == row[3] else "")


@pytest.mark.parametrize("stem", (ALL, LATERAN, ADVENT))
def test_legitimate_ungrouped_and_interrupted_controls(stem):
    core, layer, rows = load(stem, "en")
    assert_control(stem, core, layer)
    assert_retained(stem, "en", core, layer, rows)
    assert interlinear.check(expand_core(core), layer) == []


@pytest.mark.parametrize("row", GROUPS)
def test_undeclared_split_is_rejected_after_a_healthy_control(row):
    core, layer, _ = load(*row[:2])
    saved = deepcopy(layer)
    assert_group(core, layer, row)
    broken = deepcopy(layer)
    broken["segments"]["s01"]["alignments"] = [
        g for g in broken["segments"]["s01"]["alignments"] if not set(g["words"]) & set(row[2])
    ]
    if not broken["segments"]["s01"]["alignments"]:
        del broken["segments"]["s01"]["alignments"]
    for wid, gloss in zip(row[2], row[5], strict=True):
        broken["words"][wid]["gloss"] = gloss
    assert broken != layer
    assert interlinear.check(expand_core(core), broken) == []
    with pytest.raises(AssertionError) as caught:
        assert_group(core, broken, row)
    assert str(caught.value) == "absolute caption realization"
    assert_group(core, layer, row)
    assert layer == saved


@pytest.mark.parametrize("defect", ("patient", "anchor", "passive", "foreign-head"))
def test_agency_and_anchor_mutants_are_rejected(defect):
    row = GROUPS[1]
    core, layer, _ = load(*row[:2])
    saved = deepcopy((core, layer))
    assert_group(core, layer, row)
    broken_core, broken_layer = deepcopy((core, layer))
    group = next(
        g for g in broken_layer["segments"]["s01"]["alignments"] if g["words"] == list(row[2])
    )
    if defect == "patient":
        group["gloss"] = "with You being protected"
    elif defect == "anchor":
        group["anchor"] = "w012"
    elif defect == "passive":
        indexed(broken_core)["w013"]["morph"]["voice"] = "pass"
    else:
        indexed(broken_core)["w013"]["head"] = "w001"
    with pytest.raises(AssertionError) as caught:
        assert_group(broken_core, broken_layer, row)
    assert str(caught.value) == (
        "absolute caption realization"
        if defect in ("patient", "anchor")
        else "absolute source agent and active meaning"
    )
    assert_group(core, layer, row)
    assert (core, layer) == saved


@pytest.mark.parametrize("defect", ("duplicate", "missing", "noncontiguous"))
def test_actual_checker_rejects_membership_corruption(defect):
    row = GROUPS[1]
    core, layer, _ = load(*row[:2])
    assert interlinear.check(expand_core(core), layer) == []
    broken = deepcopy(layer)
    group = next(g for g in broken["segments"]["s01"]["alignments"] if g["words"] == list(row[2]))
    if defect == "duplicate":
        broken["words"]["w012"]["gloss"] = "by You"
    elif defect == "missing":
        broken["segments"]["s01"]["alignments"].remove(group)
    else:
        group["words"] = ["w012", "w014"]
        group["anchor"] = "w014"
    errors = interlinear.check(expand_core(core), broken)
    message = (
        "proprium."
        + XXI
        + ":s01:alignment-1:en: aligned words must be contiguous and in source order"
        if defect == "noncontiguous"
        else "proprium." + XXI + ":w012:en: expected exactly one direct gloss or alignment"
    )
    assert message in errors
    assert interlinear.check(expand_core(core), layer) == []


@pytest.mark.parametrize("stem,language", tuple(RETAINED))
@pytest.mark.parametrize("defect", ("source", "prose", "review"))
def test_caption_changes_cannot_rewrite_semantics_or_promote_state(stem, language, defect):
    core, layer, rows = load(stem, language)
    assert_retained(stem, language, core, layer, rows)
    changed_core, changed_layer, changed_rows = deepcopy((core, layer, rows))
    if defect == "source":
        indexed(changed_core)["w001"]["lemma"] = "alius"
        message = "retained absolute semantic source"
    elif defect == "prose":
        changed_layer["segments"]["s01"]["translation"] += " Another meaning."
        message = "retained absolute prose"
    else:
        next(r for r in changed_rows if r["site"] == "proprium." + stem + ".s01." + language)[
            "review"
        ] = "expert-reviewed"
        message = "retained absolute provenance state"
    with pytest.raises(AssertionError) as caught:
        assert_retained(stem, language, changed_core, changed_layer, changed_rows)
    assert str(caught.value) == message
    assert_retained(stem, language, core, layer, rows)


def test_unrelated_editorial_note_is_not_a_whole_file_lock():
    core, layer, rows = load(XXI, "en")
    changed = deepcopy(core)
    changed["editorial"]["notes"] = "A future independent editorial note."
    assert_group(changed, layer, GROUPS[1])
    assert_retained(XXI, "en", changed, layer, rows)

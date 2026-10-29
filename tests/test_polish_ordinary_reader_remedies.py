"""Three bounded Polish constructions survive the native reader projection.

Selected wording is a local regression fixture, not a universal translation
rule for subjunctives, repeated prepositions, or proficio.
"""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import emit
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads(
    (ROOT / "tests/fixtures/polish-ordinary-reader-remedies.json").read_text(encoding="utf-8")
)
DESTINATION = {
    "words": ["w014", "w015", "w016", "w017"],
    "anchor": "w016",
    "gloss": "na Twój ołtarz na wysokości",
}
HONOR = {"words": ["w044", "w045"], "anchor": "w045", "gloss": "ku czci"}
SALVATION = {"words": ["w048", "w049"], "anchor": "w049", "gloss": "ku zbawieniu"}
MUTANTS = (
    ("quod", "future", "Quod explicit petition"),
    ("quod", "prose", "Quod natural petition"),
    ("quod", "suffix", "Quod second petition retained"),
    ("quod", "review", "Quod current working row"),
    ("quod", "digest", "Quod current working row"),
    ("supplices", "height", "Supplices four-word destination"),
    ("supplices", "member", "Supplices four-word destination"),
    ("supplices", "duplicate", "Supplices once-only destination"),
    ("supplices", "presence", "Supplices separate presence phrase"),
    ("suscipe", "predicate", "Suscipe shared purpose predicate"),
    ("suscipe", "honor", "Suscipe short honor phrase"),
    ("suscipe", "beneficiary", "Suscipe beneficiaries and prayer"),
    ("suscipe", "salvation", "Suscipe parallel salvation"),
)


def load(case):
    spec = FIXTURE["cases"][case]
    relative = "texts/" + spec["text"].replace(".", "/", 1) + ".json"
    core = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    layer = json.loads((ROOT / "languages/pl" / relative).read_text(encoding="utf-8"))
    rows = json.loads(
        (ROOT / "languages/pl/translation-provenance.json").read_text(encoding="utf-8")
    )["sites"]
    row = next(r for r in rows if r["site"] == spec["text"] + ".s02.pl")
    return core, layer, row


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def addressed_groups(layer, members):
    return [
        group
        for group in layer["segments"]["s02"].get("alignments", [])
        if set(group["words"]) & set(members)
    ]


def native_reader(core, layer):
    doc, target = expand_core(core), enrich_layer(core, layer)
    require(language_packs.check_core(core) == [], "native core")
    require(
        language_packs.check_layer(
            core,
            layer,
            ROOT / "languages/pl/texts" / (core["id"].replace(".", "/", 1) + ".json"),
        )
        == [],
        "native target",
    )
    require(interlinear.check(doc, target) == [], "native target realization")
    parses, analyses, shared, local = emit.Table(), emit.Table(), emit.Table(), emit.Table()
    neutral = emit.core_artifact(doc, core, parses, analyses, shared)
    localized = emit.language_artifact(doc, target, local)
    received_core, received = emit.expand(
        neutral, localized, parses.order, analyses.order, shared.order, local.order
    )
    require(received_core["segments"] == doc["segments"], "reader source identity")
    require(received["words"] == target["words"], "reader independent word targets")
    for sid, segment in target["segments"].items():
        require(
            received["segments"][sid].get("alignments") == segment.get("alignments"),
            "reader alignment membership",
        )
    return received, localized


def assert_case(case, core, layer, row):
    spec = FIXTURE["cases"][case]
    require(core["id"] == layer["text"] == spec["text"], "bounded text identity")
    source = [w for s in core["segments"] for w in s.get("words", [])]
    words = {w["id"]: w for w in source}
    if case == "quod":
        require(
            words["w007"]["lemma"] == "capio"
            and words["w007"]["morph"]["mood"] == "subj"
            and words["w007"]["morph"]["person"] == 1
            and words["w007"]["morph"]["number"] == "pl"
            and layer["words"]["w007"]["gloss"] == "obyśmy przyjęli",
            "Quod explicit petition",
        )
        prose = layer["segments"]["s02"]["translation"]
        require(
            prose.startswith(
                "Spraw, Panie, abyśmy to, co przyjęliśmy ustami, przyjęli czystym sercem"
            ),
            "Quod natural petition",
        )
        before = spec["inverse"][1]["before"]
        require(
            prose.split(", a dar", 1)[1] == before.split(", a dar", 1)[1],
            "Quod second petition retained",
        )
        require(
            row == FIXTURE["quod_provenance"]["after"]
            and row["review"] == "working"
            and row["target_sha256"] == canonical_hash(prose),
            "Quod current working row",
        )
        require(
            row["source_sha256"]
            == canonical_hash(
                source_payload(next(s for s in core["segments"] if s["id"] == "s02"))
            ),
            "Quod unchanged source binding",
        )
    elif case == "supplices":
        require(
            [words[w]["lemma"] for w in DESTINATION["words"]]
            == ["in", "sublimis", "altare", "tuus"]
            and words["w014"]["morph"]["governs"] == "acc"
            and words["w018"]["morph"]["governs"] == "abl",
            "Supplices source destination and presence",
        )
        require(
            addressed_groups(layer, DESTINATION["words"]) == [DESTINATION],
            "Supplices four-word destination",
        )
        require(
            all("gloss" not in layer["words"][w] for w in DESTINATION["words"]),
            "Supplices once-only destination",
        )
        require(
            layer["words"]["w018"]["gloss"] == "przed"
            and layer["words"]["w019"]["gloss"] == "obliczem",
            "Supplices separate presence phrase",
        )
    else:
        require(
            words["w043"]["lemma"] == "proficio"
            and words["w043"]["morph"]["mood"] == "subj"
            and layer["words"]["w043"]["gloss"] == "służyła",
            "Suscipe shared purpose predicate",
        )
        require(addressed_groups(layer, HONOR["words"]) == [HONOR], "Suscipe short honor phrase")
        require(
            [layer["words"][w]["gloss"] for w in ("w041", "w042", "w046", "w047")]
            == ["aby", "im", "nam", "zaś"],
            "Suscipe beneficiaries and prayer",
        )
        require(
            addressed_groups(layer, SALVATION["words"]) == [SALVATION],
            "Suscipe parallel salvation",
        )

    require(canonical_hash(core) == spec["core_sha256"], "complete Latin source preserved")
    require(len(source) == spec["word_count"], "complete source denominator")
    received, artifact = native_reader(core, layer)
    if case in {"supplices", "suscipe"}:
        group = DESTINATION if case == "supplices" else HONOR
        require(
            [
                (w, interlinear.effective_gloss(received, w))
                for w in group["words"]
                if interlinear.effective_gloss(received, w)
            ]
            == [(group["anchor"], group["gloss"])],
            "reader shared caption once",
        )
        sequence = [w["id"] for w in next(s for s in core["segments"] if s["id"] == "s02")["words"]]
        start = sequence.index(group["words"][0])
        compact = {
            "s": start,
            "n": len(group["words"]),
            "a": sequence.index(group["anchor"]) - start,
            "g": group["gloss"],
        }
        emitted = next(s for s in artifact["seg"] if s["id"] == "s02")
        require([g for g in emitted["a"] if g["s"] == start] == [compact], "compact reader phrase")

    restored = deepcopy(layer)
    for change in spec["inverse"]:
        owner = restored
        for field in change["path"][:-1]:
            owner = owner[field]
        field = change["path"][-1]
        require(owner[field] == change["after"], "exact current inverse precondition")
        owner[field] = deepcopy(change["before"])
    require(
        canonical_hash(restored) == spec["before_layer_sha256"],
        "all outside Polish fields preserved",
    )


@pytest.mark.parametrize("case", ("quod", "supplices", "suscipe"))
def test_current_polish_ordinary_construction_survives_native_reader(case):
    assert_case(case, *load(case))


@pytest.mark.parametrize("case,fault,message", MUTANTS, ids=[f"{a}-{b}" for a, b, _ in MUTANTS])
def test_semantic_and_context_damage_is_rejected_and_same_copy_recovers(case, fault, message):
    core, layer, row = load(case)
    original = deepcopy((core, layer, row))
    assert_case(case, core, layer, row)
    try:
        if fault == "future":
            layer["words"]["w007"]["gloss"] = "przyjmiemy"
        elif fault == "prose":
            layer["segments"]["s02"]["translation"] = FIXTURE["cases"][case]["inverse"][1]["before"]
        elif fault == "suffix":
            current_prose = layer["segments"]["s02"]["translation"]
            layer["segments"]["s02"]["translation"] = current_prose.replace(
                "wiecznym lekarstwem", "doczesnym lekarstwem"
            )
        elif fault == "review":
            row["review"] = "internally-reviewed"
        elif fault == "digest":
            row["target_sha256"] = "0" * 64
        elif fault == "height":
            addressed_groups(layer, DESTINATION["words"])[0]["gloss"] = "na Twój ołtarz"
        elif fault == "member":
            addressed_groups(layer, DESTINATION["words"])[0]["words"].pop()
        elif fault == "duplicate":
            layer["words"]["w015"]["gloss"] = "na wysokości"
        elif fault == "presence":
            layer["words"]["w018"]["gloss"] = "na"
        elif fault == "predicate":
            layer["words"]["w043"]["gloss"] = "przyniosła"
        elif fault == "honor":
            addressed_groups(layer, HONOR["words"])[0]["gloss"] = "na cześć"
        elif fault == "beneficiary":
            layer["words"]["w046"]["gloss"] = "im"
        else:
            addressed_groups(layer, SALVATION["words"])[0]["gloss"] = "ku czci"
        with pytest.raises(AssertionError, match=message):
            assert_case(case, core, layer, row)
    finally:
        for target, saved in zip((core, layer, row), original, strict=True):
            target.clear()
            target.update(deepcopy(saved))
    assert (core, layer, row) == original
    assert_case(case, core, layer, row)


@pytest.mark.parametrize("case", ("quod", "supplices", "suscipe"))
def test_the_other_language_is_unchanged(case):
    spec = FIXTURE["cases"][case]
    path = ROOT / "languages/en/texts" / (spec["text"].replace(".", "/", 1) + ".json")
    assert canonical_hash(json.loads(path.read_text(encoding="utf-8"))) == spec["english_sha256"]

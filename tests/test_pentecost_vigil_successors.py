"""Selected Pentecost Vigil readings and source scope, with pending reviews.

Named wording examples are local editorial regressions, not universal
translation rules. Reader transport and provider coverage remain independent.
"""

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import bibliography, emit, store
from build_reader.bibliography_bindings import BindingError, witness_subject
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear
from checks.language_packs import check_layer
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "proprium.vigilia-pentecostes-"
TEXTS = (
    PREFIX + "introitus",
    PREFIX + "collecta",
    PREFIX + "epistola",
    PREFIX + "alleluia",
    PREFIX + "tractus",
    PREFIX + "evangelium",
    PREFIX + "offertorium",
    PREFIX + "secreta",
    "ordinarium.praefatio-spiritus-sancti",
    PREFIX + "communio",
    PREFIX + "postcommunio",
)
COMPOSITES = ("introitus", "collecta", "secreta", "postcommunio")
TRIVIAL_AMEN_SITES = frozenset(
    f"{PREFIX}{part}.{segment}.{language}"
    for part, segment in (("collecta", "s02"), ("secreta", "s03"), ("postcommunio", "s02"))
    for language in ("pl", "en")
)
READINGS = (
    pytest.param(
        "epistola", "pl", 44, 45, 44, "Jakim chrztem", "Jaki chrzest", id="baptism-government"
    ),
    pytest.param(
        "introitus", "pl", 2, 3, 2, "okażę się święty", "stanę się święty", id="manifested-holiness"
    ),
    pytest.param(
        "evangelium",
        "en",
        36,
        38,
        37,
        "it does not see Him",
        "He does not see Him",
        id="world-subject",
    ),
    pytest.param(
        "communio", "en", 4, 5, 4, "Jesus was saying", "Jesus will say", id="imperfect-speech"
    ),
    pytest.param(
        "communio",
        "en",
        23,
        27,
        23,
        "those who believed in Him were to receive",
        "those whom He believed were to receive",
        id="believers-receiving",
    ),
)


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def assert_row(row, segment, target, site):
    row_site = f"{row['text']}.{row['segment']}.{row['language']}"
    assert row["site"] == site == row_site, "current site identity"
    assert row["segment"] == segment["id"], "current segment identity"
    assert row["source_sha256"] == canonical_hash(source_payload(segment)), (
        "current source identity"
    )
    assert row["target_sha256"] == canonical_hash(target), "current target identity"
    origin = "working-unsettled"
    if site in TRIVIAL_AMEN_SITES:
        assert [(word["form"], word["lemma"], word["morph"]) for word in segment["words"]] == [
            ("Amen", "amen", {"pos": "intj"})
        ], "standalone Amen source"
        assert target == "Amen.", "standalone Amen target"
        assert row["familiar_core"] is False, "standalone Amen protection"
        origin = "trivial"
    assert (row["origin"], row["review"]) == (origin, "working"), "pending wording origin"


@pytest.mark.parametrize("text", TEXTS)
@pytest.mark.parametrize("language", ("pl", "en"))
def test_components_keep_complete_reader_and_provenance_transport(text, language):
    raw = store.core(ROOT, text)
    layer = store.raw_layer(ROOT, language, text)
    frozen = deepcopy((raw, layer))
    core, localized = expand_core(raw), enrich_layer(raw, layer)
    assert check_layer(raw, layer, store.layer_path(ROOT, language, text)) == []
    assert interlinear.check(core, localized) == []
    tables = [emit.Table() for _ in range(4)]
    encoded = emit.core_artifact(core, raw, *tables[:3])
    target = emit.language_artifact(core, localized, tables[3])
    decoded, translated = emit.expand(encoded, target, *[t.order for t in tables])
    expected, languages = emit._strip(core, {language: localized})
    assert (decoded, translated) == (expected, languages[language])
    if text == "ordinarium.praefatio-spiritus-sancti":
        assert_about(translated["about"], language)
        wrong_about = (
            translated["about"]
            .replace("Wigilii", "Niedzieli")
            .replace("Vigil of Pentecost", "Pentecost Sunday")
        )
        assert wrong_about != translated["about"]
        with pytest.raises(AssertionError, match=r"^displayed temporal variant(?:\n|$)"):
            assert_about(wrong_about, language)
        assert_about(translated["about"], language)
    rows = {
        r["segment"]: r
        for r in read(f"languages/{language}/translation-provenance.json")["sites"]
        if r["text"] == text
    }
    verses = [s for s in raw["segments"] if s["type"] == "verse"]
    assert verses and set(rows) == {s["id"] for s in verses}
    for segment in verses:
        row = rows[segment["id"]]
        target = layer["segments"][segment["id"]]["translation"]
        site = f"{text}.{segment['id']}.{language}"
        assert_row(row, segment, target, site)
        wrong_origin = "working-unsettled" if site in TRIVIAL_AMEN_SITES else "trivial"
        for field, value, message in (
            ("origin", wrong_origin, "pending wording origin"),
            ("review", "internally-reviewed", "pending wording origin"),
            ("source_sha256", "0" * 64, "current source identity"),
            ("target_sha256", "0" * 64, "current target identity"),
        ):
            bad = deepcopy(row)
            bad[field] = value
            assert bad != row
            with pytest.raises(AssertionError, match="^" + message + r"(?:\n|$)"):
                assert_row(bad, segment, target, site)
            assert_row(row, segment, target, site)
        if site in TRIVIAL_AMEN_SITES:
            bad_segment = deepcopy(segment)
            extra = deepcopy(bad_segment["words"][0])
            extra.update(id="w999", form="Allelúia", lemma="alleluia")
            bad_segment["words"].append(extra)
            bad = deepcopy(row)
            bad["source_sha256"] = canonical_hash(source_payload(bad_segment))
            assert bad_segment != segment and bad != row
            with pytest.raises(AssertionError, match=r"^standalone Amen source(?:\n|$)"):
                assert_row(bad, bad_segment, target, site)
            changed_target = "Amen. Alleluia."
            bad = deepcopy(row)
            bad["target_sha256"] = canonical_hash(changed_target)
            assert bad != row and changed_target != target
            with pytest.raises(AssertionError, match=r"^standalone Amen target(?:\n|$)"):
                assert_row(bad, segment, changed_target, site)
            assert_row(row, segment, target, site)
    assert (raw, layer) == frozen


def assert_reading(core, layer, first, last, anchor, gloss):
    ids = [f"w{i:03}" for i in range(first, last + 1)]
    source = [w["id"] for s in core["segments"] for w in s.get("words", [])]
    start = source.index(ids[0])
    assert source[start : start + len(ids)] == ids, "selected source span"
    groups = [
        g
        for s in layer["segments"].values()
        for g in s.get("alignments", [])
        if set(g["words"]) & set(ids)
    ]
    assert groups == [{"words": ids, "anchor": f"w{anchor:03}", "gloss": gloss}], (
        "selected contextual reading"
    )
    assert all("gloss" not in layer["words"][wid] for wid in ids), "single provider"
    assert [
        (wid, interlinear.effective_gloss(layer, wid))
        for wid in ids
        if interlinear.effective_gloss(layer, wid)
    ] == [(f"w{anchor:03}", gloss)], "visible contextual reading"


@pytest.mark.parametrize("part,language,first,last,anchor,gloss,wrong", READINGS)
def test_selected_reading_rejects_specific_semantic_counterexample(
    part, language, first, last, anchor, gloss, wrong
):
    core, layers = store.load(ROOT, PREFIX + part)
    layer = layers[language]
    frozen = deepcopy((core, layer))
    assert_reading(core, layer, first, last, anchor, gloss)
    damaged = deepcopy(layer)
    group = next(
        g
        for s in damaged["segments"].values()
        for g in s.get("alignments", [])
        if g.get("anchor") == f"w{anchor:03}"
    )
    group["gloss"] = wrong
    assert damaged != layer and wrong != gloss
    # Structural validity alone cannot decide the clause's referent or tense.
    assert interlinear.check(core, damaged) == []
    with pytest.raises(AssertionError, match=r"^selected contextual reading(?:\n|$)"):
        assert_reading(core, damaged, first, last, anchor, gloss)
    assert_reading(core, layer, first, last, anchor, gloss)
    assert (core, layer) == frozen


@pytest.mark.parametrize("damage", ("loss", "duplicate"))
def test_baptism_group_provider_errors_reach_the_actual_checker(damage):
    core, layers = store.load(ROOT, PREFIX + "epistola")
    layer = layers["pl"]
    frozen = deepcopy((core, layers))
    assert interlinear.check(core, layer) == []
    bad = deepcopy(layer)
    group = next(g for g in bad["segments"]["s01"]["alignments"] if "w044" in g["words"])
    if damage == "loss":
        group["words"].remove("w045")
    else:
        bad["words"]["w045"]["gloss"] = "chrztem"
    assert bad != layer
    errors = interlinear.check(core, bad)
    assert sum("w045" in e and "exactly one" in e for e in errors) == 1, "owned provider diagnostic"
    assert Counter(interlinear.check(core, layer)) == Counter()
    assert (core, layers) == frozen


def dependency_suffixes(part):
    if part == "introitus":
        return {"doxology", "reprise-rg427"}
    if part in {"collecta", "secreta", "postcommunio"}:
        return {
            "conclusion-middle",
            "conclusion-rg115a",
            "conclusion-rg115e",
            "conclusion-terminal",
            "oration-boundaries",
        }
    raise AssertionError("unsupported composite part")


def assert_composite(graph, part):
    text = PREFIX + part
    witness = next(w for w in graph["witnesses"] if w["id"] == f"witness.{text}.mr1962")
    expected = {f"use.{text}.{s}.mr1962" for s in dependency_suffixes(part)}
    assert witness["source_dependencies"] == {"uses": sorted(expected), "raw_binding": None}, (
        "complete composite dependency inventory"
    )
    primary = next(u for u in graph["uses"] if u["id"] == witness["use"])
    assert "not the whole contiguous expanded selected text" in primary["claim"], (
        "bounded proper page"
    )
    assert (
        primary["verified_on"] == "2026-09-12" and primary["decision"] == "RETAIN_WITH_CORRECTION"
    )
    assert witness["review"] == {"status": "pending"}
    subject = witness_subject(ROOT, witness, graph, store.core(ROOT, text))
    assert set(subject["source_uses"]) == expected | {primary["id"]}
    assert subject["raw_resolution"] is None
    projected = next(
        r for r in bibliography.public_text_evidence(graph)["texts"] if r["id"] == text
    )
    assert projected["witnesses"] == [] and "collation" not in projected
    return witness


@pytest.mark.parametrize("part", COMPOSITES)
def test_composite_expansion_and_cross_edition_controls(part):
    graph, _ = bibliography.load(ROOT)
    frozen = deepcopy(graph)
    witness = assert_composite(graph, part)
    with pytest.raises(AssertionError, match=r"^unsupported composite part$"):
        dependency_suffixes("unsupported-composite")
    for dependency_id in witness["source_dependencies"]["uses"]:
        bad = deepcopy(graph)
        changed = next(w for w in bad["witnesses"] if w["id"] == witness["id"])
        changed["source_dependencies"]["uses"].remove(dependency_id)
        assert bad != graph
        with pytest.raises(
            AssertionError, match=r"^complete composite dependency inventory(?:\n|$)"
        ):
            assert_composite(bad, part)
        assert_composite(graph, part)
        bad = deepcopy(graph)
        dependency = next(u for u in bad["uses"] if u["id"] == dependency_id)
        dependency["edition"] = "edition.divinum-officium-missa.44667ff"
        dependency["digital_item"] = "item.divinum-officium-missa.44667ff.github"
        assert bad != graph
        with pytest.raises(BindingError, match="supplemental source belongs to another edition"):
            witness_subject(ROOT, witness, bad, store.core(ROOT, PREFIX + part))
        assert_composite(graph, part)
    assert graph == frozen


@pytest.mark.parametrize("field", ("source_sha256", "target_sha256"))
def test_tract_rejects_stale_source_or_target_with_owned_assertion(field):
    core = store.core(ROOT, PREFIX + "tractus")
    layer = store.raw_layer(ROOT, "pl", core["id"])
    row = next(
        r
        for r in read("languages/pl/translation-provenance.json")["sites"]
        if r["text"] == core["id"]
    )
    frozen = deepcopy((core, layer, row))
    segment, target = core["segments"][0], layer["segments"]["s01"]["translation"]
    site = f"{core['id']}.{segment['id']}.pl"
    assert segment["words"][8]["post"] == "."
    assert "wszystkie ludy. Bo" in target
    assert_row(row, segment, target, site)
    bad = deepcopy(row)
    bad[field] = (
        "1b7992aabb14d60a9f0a77246d0914c190067ab33d2ed731f2a54428f511ab52"
        if field == "source_sha256"
        else "8d735510fae754c5cf0a8f94a151ca1594724e29100a43020ea34d65774f5d8e"
    )
    assert bad != row
    message = "current source identity" if field == "source_sha256" else "current target identity"
    with pytest.raises(AssertionError, match="^" + message + r"(?:\n|$)"):
        assert_row(bad, segment, target, site)
    assert_row(row, segment, target, site)
    assert (core, layer, row) == frozen


def assert_epistle_prose(pl, en):
    assert "rozprawiając o królestwie Bożym i przekonując słuchaczy" in pl, (
        "paired reasoning and persuasion"
    )
    assert "reasoning about the kingdom of God and persuading his listeners" in en, (
        "paired reasoning and persuasion"
    )
    assert "converted his listeners" not in en, "paired reasoning and persuasion"


def test_epistle_reasoning_and_persuading_are_both_present():
    _, layers = store.load(ROOT, PREFIX + "epistola")
    pl = layers["pl"]["segments"]["s01"]["translation"]
    en = layers["en"]["segments"]["s01"]["translation"]
    frozen = deepcopy(layers)
    assert_epistle_prose(pl, en)
    wrong = en.replace("persuading his listeners", "converted his listeners")
    assert wrong != en
    with pytest.raises(AssertionError, match=r"^paired reasoning and persuasion(?:\n|$)"):
        assert_epistle_prose(pl, wrong)
    assert_epistle_prose(pl, en)
    assert layers == frozen


def assert_about(about, language):
    span = (
        "od Wigilii Zesłania Ducha Świętego do następnej soboty włącznie"
        if language == "pl"
        else "from the Vigil of Pentecost through the following Saturday"
    )
    temporal = "„dnia dzisiejszego”" if language == "pl" else "“on this day.”"
    assert span in about and temporal in about, "displayed temporal variant"


HEADS = (
    ("illustratio", "illustrátio, illustratiónis", "illustrátio"),
    ("unitas", "únitas, unitátis", "únitas, -átis"),
    ("appareo", "appáreo, apparére, appárui, appáritum", "appáreo, apparére"),
    ("oblatio", "oblátio, oblatiónis", "oblátio, -ónis"),
)


def assert_head(card, head):
    assert card["head"] == head, "complete lexical head"


@pytest.mark.parametrize("lemma,head,old", HEADS, ids=[row[0] for row in HEADS])
def test_complete_heads_reach_reader_cards_without_changing_other_fields(lemma, head, old):
    cards = emit.lexicon_slice(ROOT, lemmas={lemma})
    localized = {language: emit.lexicon_slice(ROOT, language, {lemma}) for language in ("pl", "en")}
    frozen = deepcopy((cards, localized))
    assert set(cards) == {lemma}
    assert_head(cards[lemma], head)
    bad = deepcopy(cards[lemma])
    bad["head"] = old
    assert bad != cards[lemma]
    assert {k: v for k, v in bad.items() if k != "head"} == {
        k: v for k, v in cards[lemma].items() if k != "head"
    }
    with pytest.raises(AssertionError, match=r"^complete lexical head(?:\n|$)"):
        assert_head(bad, head)
    assert_head(cards[lemma], head)
    assert (cards, localized) == frozen
    assert emit.lexicon_slice(ROOT, lemmas={lemma}) == cards


def assert_baptism_ancestor(card):
    assert card["senses"] == ["to baptize"], "separate baptism noun ancestor"
    assert card["derivatives"] == ["baptize", "baptism (from baptísma)"], (
        "separate baptism noun ancestor"
    )


def test_baptism_noun_ancestor_is_not_silently_the_verb_route():
    card = emit.lexicon_slice(ROOT, "en", {"baptizo"})["baptizo"]
    frozen = deepcopy(card)
    assert_baptism_ancestor(card)
    bad = deepcopy(card)
    bad["derivatives"][1] = "baptism (from baptizáre)"
    assert bad != card
    with pytest.raises(AssertionError, match=r"^separate baptism noun ancestor(?:\n|$)"):
        assert_baptism_ancestor(bad)
    assert_baptism_ancestor(card)
    assert card == frozen


def expected_communion_row(row, site):
    """One exact wording-hash successor; retain all historical label fields."""
    after = deepcopy(row)
    if site == PREFIX + "communio.s01.en":
        assert (
            after["target_sha256"]
            == "b8d5ed58363b9494983189daf9183a78342ff52f444f71b28b978761dfeb5d30"
        ), "historical Communion target preimage"
        after["target_sha256"] = "d64fc6eb56ee7c01a97dff01a55c4709c2895c34008f927516ae81f0bae0c5d6"
    return after


def test_communion_target_overlay_requires_preimage_and_retains_siblings():
    fixture = read("tests/fixtures/own-relabel-2026-10-20-round-2.json")
    frozen = deepcopy(fixture)
    site = PREFIX + "communio.s01.en"
    before = deepcopy(fixture["sites"][site])
    after = expected_communion_row(before, site)
    assert after != before
    assert {k: v for k, v in after.items() if k != "target_sha256"} == {
        k: v for k, v in before.items() if k != "target_sha256"
    }
    actual = store.raw_layer(ROOT, "en", PREFIX + "communio")["segments"]["s01"]["translation"]
    assert after["target_sha256"] == canonical_hash(actual)
    bad = deepcopy(before)
    bad["target_sha256"] = "0" * 64
    with pytest.raises(AssertionError, match=r"^historical Communion target preimage(?:\n|$)"):
        expected_communion_row(bad, site)
    augmented = deepcopy(before)
    augmented["untouched"] = {"nested": ["retained"]}
    result = expected_communion_row(augmented, site)
    assert result["untouched"] == augmented["untouched"]
    result["untouched"]["nested"].append("independent result")
    assert augmented["untouched"] == {"nested": ["retained"]}
    assert expected_communion_row(before, site) == after
    assert fixture == frozen and before == fixture["sites"][site]

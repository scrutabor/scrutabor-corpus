"""Contextual Holy Innocents chant and source contracts, not universal grammar."""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from build_reader import store
from build_reader.bibliography_bindings import digest
from checks import english, interlinear, raw_binding
from checks.collate import collate, load_witness
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "proprium.sanctorum-innocentium-martyrum-"
ROLES = ["graduale", "offertorium"]
PROSE_HASHES = {
    ("graduale", "pl"): "a3da0f1b84fda175164723b480f34f9acac291802d0cd9d108970129e693ccdb",
    ("graduale", "en"): "145d518e4c042de83c10fbbb4dfd55323af6ee3079295bc59a12495da00a4ce3",
    ("offertorium", "pl"): "3234f7c4468b09fb46c20f1c355f7b9a8223f253218389e2f1eb4fee78f0100b",
    ("offertorium", "en"): "6085c5d08c92509fe846ebc7be8cdcc43498b2b8d1ec365f02821a82f16a1ec0",
}


def ordered(layer):
    return [gloss for wid in layer["words"] if (gloss := interlinear.effective_gloss(layer, wid))]


def english_contract(layer, role):
    expected = [
        "Our soul",
        "like",
        "a sparrow",
        "has been snatched",
        "from",
        "the snare",
        "of the fowlers",
        "The snare" if role == "graduale" else "the snare",
        "has been broken",
        "and",
        "we",
    ]
    line = ordered(layer)
    assert line[:11] == expected
    # Both temporal realizations are legitimate here, not a generic tense rule.
    assert line[11] in {"have been freed", "were freed"}
    assert line[12:] == (
        ["Our help is", "in", "the name", "of the Lord", "who", "made", "heaven", "and", "earth"]
        if role == "graduale"
        else []
    )


@pytest.mark.parametrize(
    "role,first", [(r, n) for r in ROLES for n in [1, 15]] + [("graduale", 17)]
)
def test_minimum_english_pair_has_one_provider(role, first):
    layer = store.raw_layer(ROOT, "en", PREFIX + role)
    ids = [f"w{first:03d}", f"w{first + 1:03d}"]
    matches = [a for a in layer["segments"]["s01"]["alignments"] if set(ids) & set(a["words"])]
    assert len(matches) == 1
    group = matches[0]
    assert group["words"] == ids and group["anchor"] == ids[0]
    assert group["gloss"] in (
        {"have been freed", "were freed"}
        if first == 15
        else {"Our soul" if first == 1 else "Our help is"}
    )
    assert all("gloss" not in layer["words"][wid] for wid in ids)


@pytest.mark.parametrize("role", ROLES)
def test_complete_english_line_keeps_every_external_dependent(role):
    doc, layers = store.load(ROOT, PREFIX + role)
    assert interlinear.check(doc, layers["en"]) == []
    english_contract(layers["en"], role)


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("gloss", ["were freed", "have been freed"])
def test_legitimate_passive_alternatives_do_not_duplicate_we(role, gloss):
    doc, layers = store.load(ROOT, PREFIX + role)
    layer = copy.deepcopy(layers["en"])
    group = next(
        a for a in layer["segments"]["s01"]["alignments"] if a["words"] == ["w015", "w016"]
    )
    group["gloss"] = gloss
    assert interlinear.check(doc, layer) == []
    assert english.check(doc, layer) == []
    english_contract(layer, role)


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("language", ["pl", "en"])
def test_complete_provider_partition_and_polish_inversion(role, language):
    doc, layers = store.load(ROOT, PREFIX + role)
    layer = layers[language]
    count = 26 if role == "graduale" else 16
    assert len(doc["segments"]) == 1 and len(doc["segments"][0]["words"]) == count
    assert interlinear.check(doc, layer) == []
    groups = layer["segments"]["s01"].get("alignments", [])
    direct = sum("gloss" in word for word in layer["words"].values())
    assert not any("reason" in group for group in groups)
    if language == "pl":
        assert direct == count and groups == []
        assert [layer["words"][f"w{n:03d}"]["gloss"] for n in [11, 12, 14, 15, 16]] == [
            "zerwane",
            "zostało",
            "my",
            "uwolnieni",
            "zostaliśmy",
        ]
    else:
        assert (direct, len(groups), sum(len(a["words"]) for a in groups)) == (
            (16, 5, 10) if role == "graduale" else (8, 4, 8)
        )
        for ids, gloss in [
            (["w005", "w006"], "has been snatched"),
            (["w011", "w012"], "has been broken"),
        ]:
            assert {"words": ids, "anchor": ids[0], "gloss": gloss} in groups


def test_polish_sentence_start_keeps_nominal_clause():
    layer = store.raw_layer(ROOT, "pl", PREFIX + "graduale")
    assert [layer["words"][f"w{n:03d}"]["gloss"] for n in range(17, 22)] == [
        "Pomoc",
        "nasza",
        "w",
        "imieniu",
        "Pana",
    ]


@pytest.mark.parametrize(
    "role,language,label",
    [
        ("graduale", "pl", "Graduał"),
        ("offertorium", "pl", "Antyfona na ofiarowanie"),
        ("graduale", "en", "The Gradual"),
        ("offertorium", "en", "The Offertory antiphon"),
    ],
)
def test_localized_about(role, language, label):
    assert store.raw_layer(ROOT, language, PREFIX + role)["about"].startswith(label + " ")


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("language", ["pl", "en"])
def test_prose_and_working_provenance_are_unchanged(role, language):
    text = PREFIX + role
    core = store.core(ROOT, text)
    layer = store.raw_layer(ROOT, language, text)
    target = canonical_hash(layer["segments"]["s01"]["translation"])
    assert target == PROSE_HASHES[role, language]
    records = json.loads(
        (ROOT / "languages" / language / "translation-provenance.json").read_text()
    )["sites"]
    site = next(x for x in records if x["site"] == text + ".s01." + language)
    assert site["source_sha256"] == canonical_hash(source_payload(core["segments"][0]))
    assert site["target_sha256"] == target
    assert (site["origin"], site["review"]) == ("working-unsettled", "working")


@pytest.mark.parametrize("role", ROLES)
def test_exact_source_body_and_inheritance(role):
    text = PREFIX + role
    path = ROOT / "witnesses" / text
    bound = raw_binding.resolve_binding(path / "do.txt", ROOT)
    assert bound is not None
    grad = role == "graduale"
    assert bound.source["binding_id"] == "holy-innocents-" + ("gradual" if grad else "offertory")
    assert len(bound.text.split()) == (26 if grad else 16)
    assert bound.text.split()[0] == "Anima"
    assert bound.text.split()[16:17] == (["adjutórium"] if grad else [])
    assert bound.text.split()[23:24] == (["cœlum"] if grad else [])
    binding = bound.source["binding"]
    expected_archives = {
        "holy-innocents-gospel": (
            "web/www/missa/Latin/Sancti/12-28.txt",
            "28f4f262a6e8471df524e2905b681b7b3a59485e37fea5c69060e34764533cd5",
        )
    }
    if not grad:
        expected_archives["holy-innocents-offertory-source"] = (
            "web/www/missa/Latin/Sancti/06-18t.txt",
            "76680e7683fade106dee4b5da48ce4f7fec074cfebe984b6d1118eebaeb6eab9",
        )
    assert {
        key: (row["upstream"], row["sha256"]) for key, row in bound.source["archives"].items()
    } == expected_archives
    assert binding["reading"] == [
        {
            "archive": "holy-innocents-gospel" if grad else "holy-innocents-offertory-source",
            "first": 38 if grad else 35,
            "last": 39 if grad else 35,
        }
    ]
    assert binding["references"] == (
        []
        if grad
        else [
            {"archive": "holy-innocents-gospel", "line": 64, "text": "@Sancti/06-18t", "target": 1}
        ]
    )
    assert len(binding["evidence"]) == (1 if grad else 2)
    assert [
        (e["section"], e["section_line"], e["first"], e["last"]) for e in binding["evidence"]
    ] == (
        [("Graduale", 36, 38, 39)]
        if grad
        else [("Offertorium", 63, 64, 64), ("Offertorium", 33, 35, 35)]
    )
    errors, _, stats = collate(store.load(ROOT, text)[0], path)
    assert errors == [] and stats["words"] == (26 if grad else 16)
    assert stats["witnesses"] == 2
    meta, mr = load_witness(path / "mr.txt")
    assert "Benziger" in meta["description"] and "Editio iuxta typicam" in meta["description"]
    assert "historical-transcribed" in meta and "transcribed" not in meta
    assert len(mr.split()) == (26 if grad else 16)
    assert mr.startswith("Anima ") and "Amen" not in mr


@pytest.mark.parametrize("role", ROLES)
def test_precise_source_claims_and_pending_are_nonvacuous(role):
    text = PREFIX + role
    graph = json.loads((ROOT / "bibliography/graph.json").read_text())
    uses = [r for r in graph["uses"] if r.get("address", {}).get("text") == text]
    witnesses = [r for r in graph["witnesses"] if r.get("text") == text]
    collations = [r for r in graph["collations"] if r.get("text") == text]
    assert (len(uses), len(witnesses), len(collations)) == (2, 2, 1)
    mr = next(r for r in uses if r["id"].endswith(".mr1962"))
    assert mr["role"] == "direct_approved_print" and "Benziger" in mr["claim"]
    assert mr["evidence_sha256"] == (
        "a074d446cc3ce11efbab41c36b96ac9ce396e668e1989b9557ac0e647098cbaa"
        if role == "graduale"
        else "16e6ed11378ac7377d9dac8e87f4e77a2fc3c7fd7184f2434c75d3a87fa59628"
    )
    digital = next(r for r in uses if r["id"].endswith(".do44667ff"))
    assert (
        digital["evidence_sha256"]
        == "28f4f262a6e8471df524e2905b681b7b3a59485e37fea5c69060e34764533cd5"
    )
    for witness in witnesses:
        assert witness["review"] == {"status": "pending"}
        expected = "holy-innocents-" + ("gradual" if role == "graduale" else "offertory")
        assert witness["source_dependencies"] == {
            "uses": [],
            "raw_binding": expected if witness["transcription"] == "do" else None,
        }
        raw = (ROOT / "witnesses" / text / (witness["transcription"] + ".txt")).read_bytes()
        assert witness["transcription_sha256"] == hashlib.sha256(raw).hexdigest()
    apparatus = json.loads((ROOT / "witnesses" / text / "apparatus.json").read_text())
    assert collations[0]["review"] == {"status": "pending"}
    assert collations[0]["apparatus_sha256"] == digest(apparatus)
    assert collations[0]["apparatus"] == apparatus["summary"]
    assert apparatus["summary"]["entries"] == (4 if role == "graduale" else 1)
    first = apparatus["adjudicated"][0]
    assert first["at"] == "w001" and first["witnesses"] == {"mr": "Anima", "do": "Anima"}
    core = store.core(ROOT, text)
    for field in [core["editorial"]["notes"], core["editorial"]["source"]["method"]]:
        assert "typical edition" not in field and "Transcribed from" not in field
    assert "no abbreviated conclusion" in core["editorial"]["notes"]

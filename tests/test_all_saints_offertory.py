"""Exact offertory reading, source boundaries and local realizations."""

from pathlib import Path

import pytest

from build_reader import bibliography, store
from checks import interlinear, raw_binding

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.omnium-sanctorum-offertorium"
WITNESS = ROOT / "witnesses" / TEXT
DEPENDENCY = "use." + TEXT + ".inherited-body.do44667ff"


@pytest.mark.parametrize(
    "word,gloss", [("w008", "nie"), ("w012", "niegodziwości"), ("w017", "umierać")]
)
def test_polish_predicate_realizations(word, gloss):
    assert store.raw_layer(ROOT, "pl", TEXT)["words"][word]["gloss"] == gloss


def test_english_finite_negation_and_postpositive_connector():
    layer = store.raw_layer(ROOT, "en", TEXT)
    groups = layer["segments"]["s01"]["alignments"]
    assert {"words": ["w008", "w009"], "anchor": "w009", "gloss": "will not touch"} in groups
    assert all("gloss" not in layer["words"][w] for w in ("w008", "w009"))
    assert layer["words"]["w019"]["gloss"] == "however"
    assert layer["words"]["w017"]["gloss"] == "to die"


@pytest.mark.parametrize("language,group_count", [("pl", 1), ("en", 2)])
def test_complete_providers_and_existing_seeming_construction(language, group_count):
    core = store.core(ROOT, TEXT)
    layer = store.raw_layer(ROOT, language, TEXT)
    assert len(core["segments"]) == 1 and len(core["segments"][0]["words"]) == 23
    assert interlinear.check(core, layer) == []
    groups = layer["segments"]["s01"]["alignments"]
    assert len(groups) == group_count
    expected = "wydawali się" if language == "pl" else "they seemed"
    assert {"words": ["w013", "w014"], "anchor": "w013", "gloss": expected} in groups


@pytest.mark.parametrize(
    "language,phrase", [("pl", "Antyfona na ofiarowanie"), ("en", "The offertory antiphon")]
)
def test_localized_component_label(language, phrase):
    assert store.raw_layer(ROOT, language, TEXT)["about"].startswith(phrase)


def test_exact_inherited_raw_reading_and_excluded_seasonal_ending():
    bound = raw_binding.resolve_binding(WITNESS / "do.txt", ROOT)
    assert bound is not None
    assert [(str(p.relative_to(ROOT)), a, b) for p, a, b in bound.spans] == [
        ("witnesses/raw/do-44667ff/horas/Latin/Commune/C3a-1.txt", 57, 57)
    ]
    assert len(bound.text.split()) == 23
    assert bound.text.split()[0] == "Justórum"
    assert bound.text.split()[-1] == "allelúja."


def test_two_exact_accidentals():
    import json

    apparatus = json.loads((WITNESS / "apparatus.json").read_bytes())
    assert apparatus["summary"] == {"entries": 2, "classes": ["orthography"]}
    assert [
        (v["at"], v["ours"], v["witnesses"]["do"], v["class"]) for v in apparatus["adjudicated"]
    ] == [
        ("w001", "Iustórum", "Justórum", "orthography"),
        ("w023", "allelúia.", "allelúja.", "orthography"),
    ]


def test_declared_inheritance_and_pending_source_reviews():
    graph, _ = bibliography.load(ROOT)
    assert not bibliography.validate(ROOT)
    witnesses = [w for w in graph["witnesses"] if w["text"] == TEXT]
    assert len(witnesses) == 2
    for witness in witnesses:
        assert witness["review"] == {"status": "pending"}
        assert witness["source_dependencies"] == {
            "uses": [],
            "raw_binding": "all-saints-offertory" if witness["transcription"] == "do" else None,
        }
    collation = next(c for c in graph["collations"] if c["text"] == TEXT)
    assert collation["review"] == {"status": "pending"}


@pytest.mark.parametrize("field", ["notes", "method"])
def test_both_source_descriptions_are_specific(field):
    editorial = store.core(ROOT, TEXT)["editorial"]
    value = editorial["notes"] if field == "notes" else editorial["source"]["method"]
    assert "Benziger" in value and "p. 719" in value
    assert "typical-edition" not in value
    assert "no expansion" in value.lower() or "no conclusion" in value.lower()


def test_selected_latin_and_pending_word_analyses_remain():
    core = store.core(ROOT, TEXT)
    words = {w["id"]: w for w in core["segments"][0]["words"]}
    assert words["w001"]["form"] == "Iustórum"
    assert words["w023"]["form"] == "allelúia"
    assert words["w017"]["morph"]["tense"] == "pres"
    assert core["editorial"]["status"] == "working-edition"
    assert all(
        core["editorial"]["words"][w]["analysis"]["review"] == "pending"
        for w in ("w002", "w011", "w013", "w015", "w018")
    )


def test_inherited_body_has_its_actual_office_edition_and_exact_item():
    graph, _ = bibliography.load(ROOT)
    use = next(u for u in graph["uses"] if u["id"] == DEPENDENCY)
    witness = next(
        w for w in graph["witnesses"] if w["text"] == TEXT and w["transcription"] == "do"
    )
    assert witness["use"] == DEPENDENCY
    reference = next(u for u in graph["uses"] if u["id"] == "use." + TEXT + ".do44667ff")
    assert reference["edition"] == "edition.divinum-officium-missa.44667ff"
    assert (
        reference["evidence_sha256"]
        == "b6e49964e28e5a136b4733ef923255e1c2a279e9818a21247e8315abc58e4112"
    )
    assert use["edition"] == "edition.divinum-officium-horae.44667ff"
    assert use["digital_item"] == "item.divinum-officium-horae.44667ff.doc3a-1"
    item = next(i for i in graph["digital_items"] if i["id"] == use["digital_item"])
    assert item["edition"] == use["edition"]
    assert item["record_url"] == (
        "https://raw.githubusercontent.com/DivinumOfficium/divinum-officium/"
        "44667ff518b8ff1439780470828b39714f5306a2/web/www/horas/Latin/Commune/C3a-1.txt"
    )
    assert item["sha256"] == "1d4af72b67c07b1ed3233615c2ea0a40eb5dfc27dd9e50ecfa569c51f711c48e"
    assert "inherited Latin Office-data antiphon" in (WITNESS / "do.txt").read_text()

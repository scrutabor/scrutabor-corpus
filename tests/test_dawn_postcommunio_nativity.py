"""Bind the Dawn postcommunion's selected birth-mystery reading and boundaries."""

from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

from checks import language_packs, translation_provenance

ROOT = Path(__file__).resolve().parent.parent
TEXT = "proprium.nativitas-domini-in-aurora-postcommunio"
RELATIVE = "texts/proprium/nativitas-domini-in-aurora-postcommunio.json"
PL_BODY = (
    "Niech zawsze odnawia nas, Panie, nowość tajemnicy Jego narodzin, gdyż Jego "
    "jedyne w swoim rodzaju Narodzenie usunęło dawny stan ludzkości. "
)
EN_BODY = (
    "May the newness of the mystery of His birth ever renew us, O Lord, for His "
    "unique Nativity has banished humanity’s old condition. "
)
PL_END = (
    "Przez tegoż Pana naszego Jezusa Chrystusa, Syna Twojego, który z Tobą żyje "
    "i króluje w jedności Ducha Świętego, Bóg, na wieki wieków."
)
EN_END = (
    "Through the same Jesus Christ, our Lord, Your Son, who lives and reigns with "
    "You in the unity of the Holy Spirit, God, forever and ever."
)
FIRST_PL = [f"w{number:03d}" for number in range(4, 8)]
FIRST_EN = [f"w{number:03d}" for number in range(1, 9)]
OBJECT = ["w012", "w013", "w014"]
RELATIVE_GROUP = ["w009", "w010", "w011"]
FORMS = [
    "Huius",
    "nos",
    "Dómine",
    "sacraménti",
    "semper",
    "nóvitas",
    "natális",
    "instáuret",
    "cuius",
    "Natívitas",
    "singuláris",
    "humánam",
    "répulit",
    "vetustátem",
    "Per",
    "eúndem",
    "Dóminum",
    "nostrum",
    "Iesum",
    "Christum",
    "Fílium",
    "tuum",
    "Qui",
    "tecum",
    "vivit",
    "et",
    "regnat",
    "in",
    "unitáte",
    "Spíritus",
    "Sancti",
    "Deus",
    "per",
    "ómnia",
    "sǽcula",
    "sæculórum",
    "Amen",
]


def load_case():
    core = json.loads((ROOT / RELATIVE).read_text(encoding="utf-8"))
    layers = {
        lang: json.loads((ROOT / "languages" / lang / RELATIVE).read_text(encoding="utf-8"))
        for lang in ("pl", "en")
    }
    return core, layers


def exact_group(layer, members, anchor, gloss):
    touching = [
        group
        for group in layer["segments"]["s01"].get("alignments", [])
        if set(group["words"]) & set(members)
    ]
    assert touching == [{"words": members, "anchor": anchor, "gloss": gloss}], (
        "local caption boundary"
    )
    assert all("gloss" not in layer["words"][word] for word in members), "no duplicate caption"


def require_dawn_reading(core, layers):
    segments = {segment["id"]: segment for segment in core["segments"]}
    words = [*segments["s01"]["words"], *segments["s04"]["words"]]
    assert len(words) == 37 and [word["form"] for word in words] == FORMS, "received Latin surface"
    by_id = {word["id"]: word for word in words}
    natalis = by_id["w007"]
    assert natalis["lemma"] == "natalis", "natal adjective identity"
    assert natalis["morph"] == {"pos": "adj", "case": "gen", "gender": "n", "number": "sg"}, (
        "selected genitive neuter adjective"
    )
    assert natalis["head"] == "w004", "birth adjective qualifies mystery"
    assert core["editorial"]["words"].get("w007", {}).get("analysis") == {
        "confidence": "medium",
        "sources": ["editorial", "whitakers", "collatinus"],
        "review": "pending",
    }, "uncertain editorial reading stays pending"
    assert by_id["w008"]["morph"]["mood"] == "subj", "renewal is a petition"
    assert by_id["w013"]["morph"]["tense"] == "perf", "banishing is completed"
    assert "w007" in core["localization"]["explanations"], "declared bilingual detail"
    assert core["localization"].get("notes") == ["w007"], "declared bilingual uncertainty note"
    pl, en = layers["pl"], layers["en"]
    assert pl["words"]["w001"]["gloss"] == "Jego", "personal Christ referent"
    assert pl["segments"]["s01"]["translation"] == PL_BODY + PL_END, (
        "Polish body and complete ending"
    )
    assert en["segments"]["s01"]["translation"] == EN_BODY + EN_END, (
        "English body and complete ending"
    )
    exact_group(pl, FIRST_PL, "w006", "nowość tajemnicy narodzin zawsze")
    exact_group(pl, OBJECT, "w013", "usunęło dawny stan ludzkości")
    exact_group(
        en, FIRST_EN, "w008", "May the newness of the mystery of His birth ever renew us, Lord"
    )
    exact_group(en, RELATIVE_GROUP, "w010", "for His unique Nativity")
    exact_group(en, OBJECT, "w013", "has banished humanity’s old condition")
    for layer in layers.values():
        for sid in ("s01", "s04"):
            member_ids = [word["id"] for word in segments[sid]["words"]]
            realized = [word for word in member_ids if "gloss" in layer["words"][word]]
            for group in layer["segments"][sid].get("alignments", []):
                assert set(group["words"]) <= set(member_ids), "segment-local caption"
                realized.extend(group["words"])
            assert Counter(realized) == Counter(member_ids), "complete principal caption coverage"
        detail = layer["words"]["w007"]
        assert detail.get("explanation") and "w004" in detail["explanation"], (
            "birth head explanation"
        )
        assert detail.get("note") and "nóvitas" in detail["note"], (
            "alternative remains visible in detail"
        )
        assert layer["segments"]["s04"]["translation"] == "Amen.", "response remains separate"


def test_real_dawn_layers_keep_selected_reading_and_native_contracts():
    core, layers = load_case()
    require_dawn_reading(core, layers)
    for lang, layer in layers.items():
        assert language_packs.check_layer(core, layer, ROOT / "languages" / lang / RELATIVE) == []


def test_actual_principal_provenance_binds_changed_source_without_promotion():
    core, layers = load_case()
    segment = next(segment for segment in core["segments"] if segment["id"] == "s01")
    for lang, layer in layers.items():
        ledger = json.loads(
            (ROOT / f"languages/{lang}/translation-provenance.json").read_text(encoding="utf-8")
        )
        row = next(row for row in ledger["sites"] if row["site"] == f"{TEXT}.s01.{lang}")
        assert row["familiar_core"] is False
        assert (row["origin"], row["review"]) == ("working-unsettled", "working")
        assert row["source_sha256"] == translation_provenance.canonical_hash(
            translation_provenance.source_payload(segment)
        )
        assert row["target_sha256"] == translation_provenance.canonical_hash(
            layer["segments"]["s01"]["translation"]
        )


MUTANTS = (
    ("nominative", "selected genitive neuter adjective"),
    ("feminine", "selected genitive neuter adjective"),
    ("wrong-head", "birth adjective qualifies mystery"),
    ("accepted", "uncertain editorial reading stays pending"),
    ("high-confidence", "uncertain editorial reading stays pending"),
    ("missing-whitakers", "uncertain editorial reading stays pending"),
    ("missing-collatinus", "uncertain editorial reading stays pending"),
    ("indicative", "renewal is a petition"),
    ("present-banishing", "banishing is completed"),
    ("old-demonstrative", "personal Christ referent"),
    ("sacrament-born", "English body and complete ending"),
    ("its-nativity", "local caption boundary"),
    ("PL-whole-clause", "local caption boundary"),
    ("EN-overrun", "local caption boundary"),
    ("duplicate", "no duplicate caption"),
    ("no-explanation", "birth head explanation"),
    ("no-alternative", "alternative remains visible in detail"),
    ("undeclared-note", "declared bilingual uncertainty note"),
    ("wrong-Latin", "received Latin surface"),
    ("ending-lost", "Polish body and complete ending"),
)


@pytest.mark.parametrize(("mutation", "message"), MUTANTS)
def test_semantic_and_boundary_mutants_are_rejected_with_recovery(mutation, message):
    core, layers = load_case()
    require_dawn_reading(core, layers)
    healthy_core, healthy_layers = deepcopy(core), deepcopy(layers)
    words = {word["id"]: word for segment in core["segments"] for word in segment.get("words", [])}
    if mutation == "nominative":
        words["w007"]["morph"]["case"] = "nom"
    elif mutation == "feminine":
        words["w007"]["morph"]["gender"] = "f"
    elif mutation == "wrong-head":
        words["w007"]["head"] = "w006"
    elif mutation in ("accepted", "high-confidence"):
        key, value = ("review", "accepted") if mutation == "accepted" else ("confidence", "high")
        core["editorial"]["words"]["w007"]["analysis"][key] = value
    elif mutation.startswith("missing-"):
        provider = mutation.removeprefix("missing-")
        core["editorial"]["words"]["w007"]["analysis"]["sources"].remove(provider)
    elif mutation == "indicative":
        words["w008"]["morph"]["mood"] = "ind"
    elif mutation == "present-banishing":
        words["w013"]["morph"]["tense"] = "pres"
    elif mutation == "old-demonstrative":
        layers["pl"]["words"]["w001"]["gloss"] = "Tego"
    elif mutation == "sacrament-born":
        layers["en"]["segments"]["s01"]["translation"] = layers["en"]["segments"]["s01"][
            "translation"
        ].replace("mystery of His birth", "birth of this Sacrament")
    elif mutation == "its-nativity":
        layers["en"]["segments"]["s01"]["alignments"][1]["gloss"] = "for its unique Nativity"
    elif mutation in ("PL-whole-clause", "EN-overrun"):
        lang = "pl" if mutation == "PL-whole-clause" else "en"
        group = layers[lang]["segments"]["s01"]["alignments"][0]
        group["words"] = FIRST_EN[:] if lang == "pl" else [*FIRST_EN, "w009"]
    elif mutation == "duplicate":
        layers["pl"]["words"]["w005"]["gloss"] = "zawsze"
    elif mutation == "no-explanation":
        del layers["pl"]["words"]["w007"]["explanation"]
    elif mutation == "no-alternative":
        del layers["en"]["words"]["w007"]["note"]
    elif mutation == "undeclared-note":
        del core["localization"]["notes"]
    elif mutation == "wrong-Latin":
        words["w007"]["form"] = "nativitátis"
    else:
        layers["pl"]["segments"]["s01"]["translation"] = PL_BODY.rstrip()
    with pytest.raises(AssertionError, match=message):
        require_dawn_reading(core, layers)
    require_dawn_reading(healthy_core, healthy_layers)
    restored_core, restored_layers = load_case()
    assert restored_core == healthy_core and restored_layers == healthy_layers

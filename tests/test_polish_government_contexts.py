"""Polish government in eight exact Latin constructions and their retained controls.

These are addressed phrases, not a rule to replace Latin datives or prepositions
throughout the corpus. A repaired caption does not change full prose or its origin.
"""

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs
from checks.translation_provenance import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
CC = "proprium.corporis-christi-"

# id, text, segment, members, Latin forms, lemmas, target captions, former captions, anchor
SITES = (
    (
        "alma-help-dative",
        "orationes.alma-redemptoris-mater",
        "s02",
        ("w012",),
        ("succúrre",),
        ("succurro",),
        ("pomóż",),
        ("wspomóż",),
        None,
    ),
    (
        "suscipe-goal",
        "ordinarium.suscipe-sancte-pater",
        "s02",
        ("w050", "w051", "w052"),
        ("in", "vitam", "ætérnam"),
        ("in", "vita", "aeternus"),
        ("na", "życie", "wieczne"),
        ("na", "życia", "wiecznego"),
        None,
    ),
    (
        "corpus-food",
        CC + "introitus",
        "s01",
        ("w003", "w004", "w005"),
        ("ex", "ádipe", "fruménti"),
        ("ex", "adeps", "frumentum"),
        ("najlepszą pszenicą",),
        ("z", "tłustością", "pszenicy"),
        "w004",
    ),
    (
        "corpus-food-reprise",
        CC + "introitus",
        "s05",
        ("w045", "w046", "w047"),
        ("ex", "ádipe", "fruménti"),
        ("ex", "adeps", "frumentum"),
        ("najlepszą pszenicą",),
        ("z", "tłustością", "pszenicy"),
        "w046",
    ),
    (
        "corpus-rejoice",
        CC + "introitus",
        "s02",
        ("w016", "w017", "w018", "w019"),
        ("Exsultáte", "Deo", "adiutóri", "nostro"),
        ("exsulto", "deus", "adiutor", "noster"),
        ("Radujcie się", "Bogiem", "Wspomożycielem", "naszym"),
        ("Radujcie się", "Bogu", "Wspomożycielowi", "naszemu"),
        None,
    ),
    (
        "corpus-holy",
        CC + "offertorium",
        "s01",
        ("w010", "w011", "w012", "w013"),
        ("sancti", "erunt", "Deo", "suo"),
        ("sanctus", "sum", "deus", "suus"),
        ("święci", "będą", "dla Boga", "swojego"),
        ("święci", "będą", "Bogu", "swojemu"),
        None,
    ),
    (
        "corpus-negated-object",
        CC + "offertorium",
        "s01",
        ("w015", "w016", "w017", "w018"),
        ("non", "pólluent", "nomen", "eius"),
        ("non", "polluo", "nomen", "is"),
        ("nie", "zbezczeszczą", "imienia", "Jego"),
        ("nie", "zbezczeszczą", "imię", "Jego"),
        None,
    ),
    (
        "pentecost-xi-rejoice",
        "proprium.dominica-xi-post-pentecosten-alleluia",
        "s01",
        ("w003", "w004", "w005", "w006"),
        ("Exsultáte", "Deo", "adiutóri", "nostro"),
        ("exsulto", "deus", "adiutor", "noster"),
        ("Radujcie się", "Bogiem", "Wspomożycielem", "naszym"),
        ("Radujcie się", "Bogu", "Wspomożycielowi", "naszemu"),
        None,
    ),
)


def path_of(text, language=None):
    category, slug = text.split(".", 1)
    prefix = ROOT if language is None else ROOT / "languages" / language
    return prefix / "texts" / category / f"{slug}.json"


def load(text, language=None):
    return json.loads(path_of(text, language).read_text(encoding="utf-8"))


def healthy(core, layer):
    assert language_packs.check_core(core) == []
    assert language_packs.check_layer(core, layer, path_of(core["id"], "pl")) == []
    assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []


def exact_construction(core, layer, row):
    name, text, segment, members, forms, lemmas, expected, _, anchor = row
    message = f"Polish government: {name}"
    assert core["id"] == text and layer["text"] == text, message
    source = next(s for s in core["segments"] if s["id"] == segment)["words"]
    selected = [w for w in source if w["id"] in members]
    assert tuple(w["id"] for w in selected) == members, message
    assert tuple(w["form"] for w in selected) == forms, message
    assert tuple(w["lemma"] for w in selected) == lemmas, message
    if name == "alma-help-dative":
        words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
        assert selected[0]["morph"]["mood"] == "imp", message
        assert words["w013"]["morph"]["case"] == "dat", message
        assert words["w013"]["head"] == "w017", message
        assert words["w017"]["morph"]["case"] == "dat", message
        assert layer["words"]["w013"]["gloss"] == "upadającemu", message
        assert layer["words"]["w017"]["gloss"] == "ludowi", message
    elif name == "suscipe-goal":
        assert selected[0]["morph"]["governs"] == "acc", message
        assert selected[0]["head"] == selected[2]["head"] == members[1], message
        assert [w["morph"]["case"] for w in selected[1:]] == ["acc", "acc"], message
    elif name in ("corpus-food", "corpus-food-reprise"):
        assert selected[0]["morph"]["governs"] == "abl", message
        assert selected[0]["head"] == anchor, message
        assert [w["morph"]["case"] for w in selected[1:]] == ["abl", "gen"], message
    elif name in ("corpus-rejoice", "pentecost-xi-rejoice"):
        assert selected[0]["morph"]["mood"] == "imp", message
        assert [w["morph"]["case"] for w in selected[1:]] == ["dat", "dat", "dat"], message
        assert selected[3]["head"] == members[2], message
    elif name == "corpus-holy":
        assert selected[0]["morph"]["case"] == "nom", message
        assert selected[0]["head"] == "w001", message
        assert selected[1]["morph"]["tense"] == "fut", message
        assert [w["morph"]["case"] for w in selected[2:]] == ["dat", "dat"], message
        assert selected[3]["head"] == members[2], message
    else:
        assert name == "corpus-negated-object", message
        assert selected[1]["morph"]["tense"] == "fut", message
        assert [w["morph"]["case"] for w in selected[2:]] == ["acc", "gen"], message
    groups = [
        g
        for g in layer["segments"][segment].get("alignments", [])
        if set(g["words"]) & set(members)
    ]
    if anchor is None:
        assert not groups, message
        assert tuple(layer["words"][wid].get("gloss") for wid in members) == expected, message
    else:
        assert groups == [{"words": list(members), "anchor": anchor, "gloss": expected[0]}], message
        assert all("gloss" not in layer["words"][wid] for wid in members), message


@pytest.mark.parametrize("row", SITES, ids=[row[0] for row in SITES])
def test_contextual_government_rejects_predecessor_and_recovers(row):
    core, layer = load(row[1]), load(row[1], "pl")
    healthy(core, layer)
    exact_construction(core, layer, row)
    original = deepcopy(layer)
    changed = deepcopy(layer)
    members, former, anchor = row[3], row[7], row[8]
    faults = (
        ("predecessor",)
        if anchor is None
        else (
            "predecessor",
            "anchor",
            "missing-member",
            "duplicate-direct-caption",
        )
    )
    for fault in faults:
        try:
            if anchor is None or fault == "predecessor":
                if anchor is not None:
                    groups = changed["segments"][row[2]]["alignments"]
                    groups[:] = [g for g in groups if g["words"] != list(members)]
                    if not groups:
                        del changed["segments"][row[2]]["alignments"]
                for wid, gloss in zip(members, former, strict=True):
                    changed["words"][wid]["gloss"] = gloss
            else:
                group = next(
                    g
                    for g in changed["segments"][row[2]]["alignments"]
                    if g["words"] == list(members)
                )
                if fault == "anchor":
                    group["anchor"] = members[0]
                elif fault == "missing-member":
                    group["words"].pop()
                else:
                    changed["words"][members[0]]["gloss"] = "z"
            assert canonical_hash(changed) != canonical_hash(original)
            with pytest.raises(AssertionError, match=re.escape(f"Polish government: {row[0]}")):
                exact_construction(core, changed, row)
        finally:
            changed.clear()
            changed.update(deepcopy(original))
        assert changed == original
        healthy(core, changed)
        exact_construction(core, changed, row)
    assert layer == original


def test_distinct_prepositions_and_recipient_datives_stay_distinct():
    controls = (
        ("ordinarium.ecce-agnus-dei", ("w068", "w069", "w070"), ("na", "żywot", "wieczny")),
        ("ordinarium.haec-commixtio", ("w015", "w016", "w017"), ("ku", "żywotowi", "wiecznemu")),
        ("ordinarium.panem-caelestem", ("w067", "w068", "w069"), ("na", "żywot", "wieczny")),
        ("ordinarium.quid-retribuam", ("w033", "w034", "w035"), ("na", "żywot", "wieczny")),
        (
            "proprium.pretiosissimi-sanguinis-domini-nostri-iesu-christi-postcommunio",
            ("w020", "w021", "w022"),
            ("ku", "życiu", "wiecznemu"),
        ),
        (
            "proprium.sancti-laurentii-martyris-evangelium",
            ("w044", "w045", "w046"),
            ("na", "życie", "wieczne"),
        ),
        (
            "proprium.dominica-in-albis-introitus",
            ("w015", "w016", "w017"),
            ("w Bogu", "Wspomożycielu", "naszym"),
        ),
        (CC + "introitus", ("w020", "w021", "w022"), ("wykrzykujcie", "Bogu", "Jakuba")),
        (
            "proprium.dominica-xi-post-pentecosten-alleluia",
            ("w007", "w008", "w009"),
            ("wykrzykujcie", "Bogu", "Jakuba"),
        ),
        (CC + "offertorium", ("w007",), ("Bogu",)),
    )
    for text, members, expected in controls:
        layer = load(text, "pl")
        assert tuple(layer["words"][wid]["gloss"] for wid in members) == expected


def test_caption_repairs_preserve_prose_origin_and_embedded_gloria():
    ledger = json.loads((ROOT / "languages/pl/translation-provenance.json").read_text("utf-8"))
    targets = {
        (
            "orationes.alma-redemptoris-mater",
            "s02",
        ): "10406e5e7d288669e0f6ed3610e750f5084968bd4752ac2e75897d90ed9c982f",
        (
            "ordinarium.suscipe-sancte-pater",
            "s02",
        ): "76f3d6a6d2cd750e18c4504ceaea8e16e3ec7f7ba8e50bb62aa69d082e1d306b",
        (
            CC + "introitus",
            "s01",
        ): "a276287cc2956096da4842f186ee94cc9df3dd4b90a8186a007446b87736e298",
        (
            CC + "introitus",
            "s02",
        ): "9b540079cd05f9599692d8ed283aa009f3244df00f97fa4518f044989332f900",
        (
            CC + "introitus",
            "s05",
        ): "a276287cc2956096da4842f186ee94cc9df3dd4b90a8186a007446b87736e298",
        (
            CC + "offertorium",
            "s01",
        ): "13433be5fa6115c4472491be2dded2033db3f18acfdc797cd80e5dfe352dd4c3",
        (
            "proprium.dominica-xi-post-pentecosten-alleluia",
            "s01",
        ): "71fc8d5f24f5229eae6947312c27d027e4c2c1d8ca80cab3653460fbf30a87ab",
    }
    assert set(targets) == {(row[1], row[2]) for row in SITES}
    for (text, segment), target in targets.items():
        layer = load(text, "pl")
        (entry,) = [r for r in ledger["sites"] if r["site"] == f"{text}.{segment}.pl"]
        assert (entry["origin"], entry["review"], entry["familiar_core"]) == (
            "working-unsettled",
            "working",
            False,
        )
        assert entry["target_sha256"] == target
        assert canonical_hash(layer["segments"][segment]["translation"]) == target
    layer = load(CC + "introitus", "pl")
    assert layer["segments"]["s03"]["translation"] == (
        "Chwała Ojcu i Synowi, i Duchowi Świętemu. Jak była na początku, "
        "teraz i zawsze, i na wieki wieków. Amen."
    )
    assert [layer["words"][f"w{n:03}"]["gloss"] for n in range(23, 43)] == [
        "Chwała",
        "Ojcu",
        "i",
        "Synowi",
        "i",
        "Duchowi",
        "Świętemu",
        "Jak",
        "była",
        "na",
        "początku",
        "i",
        "teraz",
        "i",
        "zawsze",
        "i",
        "na",
        "wieki",
        "wieków",
        "Amen",
    ]

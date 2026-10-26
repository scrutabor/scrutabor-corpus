"""The explicit saint-name set rejects unrelated invented names."""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from checks import lint

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("text", "word_id", "lemma"),
    [
        ("proprium.sancti-pii-v-collecta", "w014", "Pius"),
        ("proprium.sancti-stanislai-collecta", "w007", "Stanislaus"),
        ("proprium.sancti-gregorii-nazianzeni-collecta", "w008", "Gregorius"),
        (
            "proprium.sancti-antonini-collecta",
            "w002",
            "Antoninus",
        ),
        (
            "proprium.sanctorum-nerei-achillei-domitillae-et-pancratii-collecta",
            "w006",
            "Nereus",
        ),
        (
            "proprium.sanctorum-nerei-achillei-domitillae-et-pancratii-collecta",
            "w007",
            "Achilleus",
        ),
        (
            "proprium.sanctorum-nerei-achillei-domitillae-et-pancratii-collecta",
            "w008",
            "Domitilla",
        ),
        (
            "proprium.sanctorum-nerei-achillei-domitillae-et-pancratii-collecta",
            "w010",
            "Pancratius",
        ),
        (
            "proprium.sancti-roberti-bellarmino-collecta",
            "w013",
            "Robertus",
        ),
        (
            "proprium.sancti-bonifatii-martyris-collecta",
            "w008",
            "Bonifatius",
        ),
        (
            "proprium.sancti-paschalis-baylon-collecta",
            "w004",
            "Paschalis",
        ),
        (
            "proprium.sancti-ubaldi-collecta",
            "w011",
            "Ubaldus",
        ),
        (
            "proprium.sancti-venantii-martyris-collecta",
            "w006",
            "Venantius",
        ),
        (
            "proprium.sancti-petri-caelestini-collecta",
            "w005",
            "Caelestinus",
        ),
        (
            "proprium.sancti-bernardini-senensis-collecta",
            "w005",
            "Bernardinus",
        ),
        ("proprium.sancti-bedae-venerabilis-collecta", "w006", "Beda"),
        (
            "proprium.sancti-augustini-cantuariensis-collecta",
            "w003",
            "Angli",
        ),
        (
            "proprium.sanctae-mariae-magdalenae-de-pazzis-collecta",
            "w007",
            "Magdalena",
        ),
        (
            "proprium.sancti-felicis-i-papae-collecta",
            "w010",
            "Felix",
        ),
        (
            "proprium.sanctae-angelae-mericiae-collecta",
            "w006",
            "Angela",
        ),
        (
            "proprium.sanctorum-marcellini-petri-et-erasmi-collecta",
            "w011",
            "Erasmus",
        ),
    ],
)
def test_saint_name_entry_is_exact_and_does_not_admit_unknown_names(
    text, word_id, lemma, monkeypatch
):
    path = ROOT / "texts" / (text.replace(".", "/", 1) + ".json")
    raw = path.read_bytes()
    doc = json.loads(raw)
    original = copy.deepcopy(doc)
    words = [word for segment in doc["segments"] for word in segment["words"]]
    selected = next(word for word in words if word["id"] == word_id)
    assert selected["lemma"] == lemma
    names = lint.PROPER_LEMMAS.copy()

    def proper_errors(candidate):
        errors, count = lint.lint_text(candidate)
        assert count == len(words)
        return [error for error in errors if "capitalized but not in proper-name list" in error]

    def diagnostic(name):
        return f"{word_id}: lemma {name!r} capitalized but not in proper-name list (SCHEMA.md)"

    assert proper_errors(doc) == []
    with monkeypatch.context() as patch:
        patch.setattr(lint, "PROPER_LEMMAS", names - {lemma})
        assert proper_errors(doc) == [diagnostic(lemma)]
    assert names == lint.PROPER_LEMMAS
    assert proper_errors(doc) == []

    wrong = copy.deepcopy(doc)
    target = next(
        word for segment in wrong["segments"] for word in segment["words"] if word["id"] == word_id
    )
    target["lemma"] = "Ficticius"
    assert "Ficticius" not in lint.PROPER_LEMMAS
    assert proper_errors(wrong) == [diagnostic("Ficticius")]
    assert proper_errors(doc) == []
    assert doc == original
    assert path.read_bytes() == raw
    assert names == lint.PROPER_LEMMAS


@pytest.mark.parametrize("wrong_lemma", ["ErasmusX", "ERASMUS"])
def test_june_martyr_name_keeps_exact_spelling(wrong_lemma):
    text = "proprium.sanctorum-marcellini-petri-et-erasmi-collecta"
    path = ROOT / "texts" / (text.replace(".", "/", 1) + ".json")
    raw = path.read_bytes()
    doc = json.loads(raw)
    words = [word for segment in doc["segments"] for word in segment["words"]]
    selected = next(word for word in words if word["id"] == "w011")
    assert selected["lemma"] == "Erasmus"
    selected["lemma"] = wrong_lemma
    errors, count = lint.lint_text(doc)
    assert count == 43
    assert wrong_lemma not in lint.PROPER_LEMMAS
    proper = [e for e in errors if "capitalized but not in proper-name list" in e]
    assert proper == [
        f"w011: lemma {wrong_lemma!r} capitalized but not in proper-name list (SCHEMA.md)"
    ]
    assert path.read_bytes() == raw


def test_june_martyr_name_reuses_parse_and_appends_text_addresses():
    text = "proprium.sanctorum-marcellini-petri-et-erasmi-collecta"
    path = ROOT / "texts" / (text.replace(".", "/", 1) + ".json")
    doc = json.loads(path.read_bytes())
    words = [word for segment in doc["segments"] for word in segment["words"]]
    selected = next(word for word in words if word["id"] == "w011")
    assert selected["form"] == "Erásmi" and selected["lemma"] == "Erasmus"
    expected = {"pos": "noun", "case": "gen", "number": "sg", "gender": "m", "decl": 2}

    def canonical(value):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    registry = ROOT / "build_reader" / "registry"
    morphology = json.loads((registry / "morphology.json").read_bytes())
    texts = json.loads((registry / "texts.json").read_bytes())
    assert canonical(selected["morph"]) == canonical(expected)
    assert canonical(morphology[54]) == canonical(expected)
    # Stable addresses precede the exact newly authored text order.
    assert len(texts) == 1219
    assert hashlib.sha256(canonical(texts[:1156]).encode()).hexdigest() == (
        "c1d9f8a2b0354062fd6aaa09fd0d62028908848d2eb7e7f123225d3dc687f6de"
    )
    assert texts[1156:] == [
        "proprium.haec-hostia-secreta",
        "proprium.laudis-tibi-secreta",
        "proprium.oblatis-muneribus-secreta",
        "proprium.refecti-cibo-potuque-postcommunio",
        "proprium.refectione-sancta-postcommunio",
        "proprium.sacro-munere-postcommunio",
        "proprium.sanctae-angelae-mericiae-collecta",
        "proprium.sanctae-angelae-mericiae-postcommunio",
        "proprium.sanctae-angelae-mericiae-secreta",
        "proprium.sanctae-catharinae-senensis-collecta",
        "proprium.sanctae-catharinae-senensis-postcommunio",
        "proprium.sanctae-catharinae-senensis-secreta",
        "proprium.sanctae-mariae-magdalenae-de-pazzis-collecta",
        "proprium.sanctae-monicae-collecta",
        "proprium.sancti-antonini-collecta",
        "proprium.sancti-antonini-postcommunio",
        "proprium.sancti-athanasii-collecta",
        "proprium.sancti-athanasii-postcommunio",
        "proprium.sancti-athanasii-secreta",
        "proprium.sancti-augustini-cantuariensis-collecta",
        "proprium.sancti-augustini-cantuariensis-postcommunio",
        "proprium.sancti-augustini-cantuariensis-secreta",
        "proprium.sancti-bedae-venerabilis-collecta",
        "proprium.sancti-bedae-venerabilis-postcommunio",
        "proprium.sancti-bedae-venerabilis-secreta",
        "proprium.sancti-bernardini-senensis-collecta",
        "proprium.sancti-bonifatii-martyris-collecta",
        "proprium.sancti-bonifatii-martyris-postcommunio",
        "proprium.sancti-felicis-i-papae-collecta",
        "proprium.sancti-gregorii-nazianzeni-collecta",
        "proprium.sancti-gregorii-nazianzeni-postcommunio",
        "proprium.sancti-gregorii-nazianzeni-secreta",
        "proprium.sancti-gregorii-vii-collecta",
        "proprium.sancti-ioannis-baptistae-de-la-salle-collecta",
        "proprium.sancti-paschalis-baylon-collecta",
        "proprium.sancti-petri-caelestini-collecta",
        "proprium.sancti-petri-martyris-collecta",
        "proprium.sancti-petri-martyris-postcommunio",
        "proprium.sancti-petri-martyris-secreta",
        "proprium.sancti-philippi-nerii-collecta",
        "proprium.sancti-philippi-nerii-postcommunio",
        "proprium.sancti-philippi-nerii-secreta",
        "proprium.sancti-pii-v-collecta",
        "proprium.sancti-roberti-bellarmino-collecta",
        "proprium.sancti-roberti-bellarmino-postcommunio",
        "proprium.sancti-roberti-bellarmino-secreta",
        "proprium.sancti-stanislai-collecta",
        "proprium.sancti-stanislai-postcommunio",
        "proprium.sancti-stanislai-secreta",
        "proprium.sancti-tui-secreta",
        "proprium.sancti-ubaldi-collecta",
        "proprium.sancti-ubaldi-postcommunio",
        "proprium.sancti-venantii-martyris-collecta",
        "proprium.sancti-venantii-martyris-postcommunio",
        "proprium.sancti-venantii-martyris-secreta",
        "proprium.sanctorum-alexandri-eventii-theoduli-et-iuvenalis-collecta",
        "proprium.sanctorum-alexandri-eventii-theoduli-et-iuvenalis-postcommunio",
        "proprium.sanctorum-marcellini-petri-et-erasmi-collecta",
        "proprium.sanctorum-nerei-achillei-domitillae-et-pancratii-collecta",
        "proprium.sanctorum-nerei-achillei-domitillae-et-pancratii-postcommunio",
        "proprium.sanctorum-nerei-achillei-domitillae-et-pancratii-secreta",
        "proprium.super-has-hostias-secreta",
        "proprium.vigilia-ascensionis-evangelium",
    ]
    assert all(
        texts.count(text) == 1
        for text in [
            "proprium.sanctae-angelae-mericiae-postcommunio",
            "proprium.sanctae-angelae-mericiae-secreta",
            "proprium.sanctorum-marcellini-petri-et-erasmi-collecta",
        ]
    )

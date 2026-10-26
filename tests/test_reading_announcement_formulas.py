"""The 26 printed reading announcements are complete, witnessed and bound to their readings.

Each formula is one single-segment Ordinary text whose Latin is the heading the 1962 Benziger
editio iuxta typicam prints over a reading. The fixture names, for every formula, the readings
of this corpus that print it; the Last Gospel's existing announcement serves the one Initium
of St John. The Polish layer, the lexicon, the witnesses and the evidence graph are checked
here as a whole, with in-memory mutants that prove the checks see a defect.
"""

from __future__ import annotations

import copy
import json
import re
from collections import Counter
from pathlib import Path

from build_reader import store
from checks.collate import collate
from checks.language_packs import check_layer
from checks.lexicon import INDECLINABLE
from checks.lint import PROPER_LEMMAS, lint_text
from checks.raw_binding import resolve_binding
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads(
    (ROOT / "tests/fixtures/reading-announcement-formulas.json").read_text(encoding="utf-8")
)
FORMULAS = {formula["text"]: formula for formula in FIXTURE["formulas"]}

LATIN = {
    "ordinarium.lectio-actuum-apostolorum": "Léctio Áctuum Apostolórum",
    "ordinarium.lectio-epistolae-beati-petri-apostoli": "Léctio Epístolæ beáti Petri Apóstoli",
    "ordinarium.lectio-epistolae-beati-iacobi-apostoli": "Léctio Epístolæ beáti Iacóbi Apóstoli",
    "ordinarium.lectio-epistolae-beati-ioannis-apostoli": (
        "Léctio Epístolæ beáti Ioánnis Apóstoli"
    ),
    "ordinarium.lectio-epistolae-beati-pauli-apostoli-ad-corinthios": (
        "Léctio Epístolæ beáti Pauli Apóstoli ad Corínthios"
    ),
    "ordinarium.lectio-epistolae-beati-pauli-apostoli-ad-romanos": (
        "Léctio Epístolæ beáti Pauli Apóstoli ad Romános"
    ),
    "ordinarium.lectio-epistolae-beati-pauli-apostoli-ad-ephesios": (
        "Léctio Epístolæ beáti Pauli Apóstoli ad Ephésios"
    ),
    "ordinarium.lectio-epistolae-beati-pauli-apostoli-ad-colossenses": (
        "Léctio Epístolæ beáti Pauli Apóstoli ad Colossénses"
    ),
    "ordinarium.lectio-epistolae-beati-pauli-apostoli-ad-galatas": (
        "Léctio Epístolæ beáti Pauli Apóstoli ad Gálatas"
    ),
    "ordinarium.lectio-epistolae-beati-pauli-apostoli-ad-philippenses": (
        "Léctio Epístolæ beáti Pauli Apóstoli ad Philippénses"
    ),
    "ordinarium.lectio-epistolae-beati-pauli-apostoli-ad-hebraeos": (
        "Léctio Epístolæ beáti Pauli Apóstoli ad Hebrǽos"
    ),
    "ordinarium.lectio-epistolae-beati-pauli-apostoli-ad-thessalonicenses": (
        "Léctio Epístolæ beáti Pauli Apóstoli ad Thessalonicénses"
    ),
    "ordinarium.lectio-epistolae-beati-pauli-apostoli-ad-titum": (
        "Léctio Epístolæ beáti Pauli Apóstoli ad Titum"
    ),
    "ordinarium.lectio-libri-sapientiae": "Léctio libri Sapiéntiæ",
    "ordinarium.lectio-libri-apocalypsis-beati-ioannis-apostoli": (
        "Léctio libri Apocalýpsis beáti Ioánnis Apóstoli"
    ),
    "ordinarium.lectio-libri-iudith": "Léctio libri Iudith",
    "ordinarium.lectio-libri-machabaeorum": "Léctio libri Machabæórum",
    "ordinarium.lectio-isaiae-prophetae": "Léctio Isaíæ Prophétæ",
    "ordinarium.lectio-ezechielis-prophetae": "Léctio Ezechiélis Prophétæ",
    "ordinarium.lectio-malachiae-prophetae": "Léctio Malachíæ Prophétæ",
    "ordinarium.initium-sancti-evangelii-secundum-matthaeum": (
        "Inítium sancti Evangélii secúndum Matthǽum"
    ),
    "ordinarium.passio-domini-nostri-iesu-christi-secundum-matthaeum": (
        "Pássio Dómini nostri Iesu Christi secúndum Matthǽum"
    ),
    "ordinarium.sequentia-sancti-evangelii-secundum-matthaeum": (
        "Sequéntia sancti Evangélii secúndum Matthǽum"
    ),
    "ordinarium.sequentia-sancti-evangelii-secundum-lucam": (
        "Sequéntia sancti Evangélii secúndum Lucam"
    ),
    "ordinarium.sequentia-sancti-evangelii-secundum-ioannem": (
        "Sequéntia sancti Evangélii secúndum Ioánnem"
    ),
    "ordinarium.sequentia-sancti-evangelii-secundum-marcum": (
        "Sequéntia sancti Evangélii secúndum Marcum"
    ),
}

CLASS_TEXTS = {
    "lectio-epistolae-pauli": 9,
    "lectio-epistolae-apostoli": 3,
    "lectio-actuum": 1,
    "lectio-libri": 4,
    "lectio-prophetae": 3,
    "initium": 1,
    "passio": 1,
    "sequentia": 4,
}
CLASS_READINGS = {
    "lectio-epistolae-pauli": 62,
    "lectio-epistolae-apostoli": 11,
    "lectio-actuum": 7,
    "lectio-libri": 18,
    "lectio-prophetae": 5,
    "initium": 1,
    "passio": 1,
    "sequentia": 100,
}
GOSPEL_CLASSES = {"initium", "passio", "sequentia"}

NEW_LEMMATA = {
    "lectio": {"head": "léctio, lectiónis", "pos": "noun", "gender": "f", "decl": 3},
    "epistola": {"head": "epístola, -æ", "pos": "noun", "gender": "f", "decl": 1},
    "sequentia": {"head": "sequéntia, -æ", "pos": "noun", "gender": "f", "decl": 1},
    "apocalypsis": {"head": "apocalýpsis, apocalýpsis", "pos": "noun", "gender": "f", "decl": 3},
    "Corinthius": {"head": "Corínthius, -a, -um", "pos": "adj"},
    "Ephesius": {"head": "Ephésius, -a, -um", "pos": "adj"},
    "Colossensis": {"head": "Colossénsis, Colossénsis", "pos": "noun", "gender": "m", "decl": 3},
    "Philippensis": {
        "head": "Philippénsis, Philippénsis",
        "pos": "noun",
        "gender": "m",
        "decl": 3,
    },
    "Thessalonicensis": {
        "head": "Thessalonicénsis, Thessalonicénsis",
        "pos": "noun",
        "gender": "m",
        "decl": 3,
    },
    "Galata": {"head": "Gálata, Gálatæ", "pos": "noun", "gender": "m", "decl": 1},
    "Iudith": {"head": "Iudith", "pos": "noun", "gender": "f"},
    "Machabaeus": {"head": "Machabǽus, -i", "pos": "noun", "gender": "m", "decl": 2},
    "Ezechiel": {"head": "Ezéchiel, Ezechiélis", "pos": "noun", "gender": "m", "decl": 3},
    "Malachias": {"head": "Malachías, Malachíæ", "pos": "noun", "gender": "m", "decl": 1},
}

SAPIENTIAE_PAGES = {"25": 104, "526": 607, "584": 665, "664": 745}


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def core_path(text_id):
    category, slug = text_id.split(".", 1)
    return f"texts/{category}/{slug}.json"


def layer_path(language, text_id):
    category, slug = text_id.split(".", 1)
    return f"languages/{language}/texts/{category}/{slug}.json"


def words(doc):
    return [word for segment in doc["segments"] for word in segment.get("words") or []]


def latin(doc):
    return " ".join(word["form"] + word.get("post", "") for word in words(doc))


def header(path, key):
    """Header value of one witness key, continuation lines joined."""
    values, current = [], None
    for line in (ROOT / path).read_text(encoding="utf-8").splitlines():
        if not line.startswith("#"):
            break
        opened = re.match(r"#\s*([\w-]+):\s*(.*)", line)
        if opened:
            current = opened[1]
            if current == key:
                values.append(opened[2])
        elif current == key:
            values[-1] += "\n" + line.lstrip("# ").strip()
    return values


def body(path):
    return [
        line
        for line in (ROOT / path).read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]


def test_the_26_formulas_and_their_latin():
    assert list(FORMULAS) == list(LATIN)
    total = 0
    for text_id, expected in LATIN.items():
        doc = load(core_path(text_id))
        assert doc["id"] == text_id
        assert doc["title"] == expected
        assert latin(doc) == expected  # no closing full stop, no cross
        assert FORMULAS[text_id]["latin"] == expected
        assert len(words(doc)) == FORMULAS[text_id]["words"]
        total += len(words(doc))
    assert total == 137


def test_classes_and_readings_follow_the_printed_headings():
    assert Counter(f["class"] for f in FIXTURE["formulas"]) == CLASS_TEXTS
    readings = Counter()
    seen = []
    for formula in FIXTURE["formulas"]:
        gospel = formula["class"] in GOSPEL_CLASSES
        assert formula["cross_in_margin"] is (gospel and formula["class"] != "passio")
        assert formula["representative"]["reading"] in {r["text"] for r in formula["readings"]}
        for reading in formula["readings"]:
            assert (ROOT / core_path(reading["text"])).is_file()
            assert reading["text"].endswith("-evangelium" if gospel else "-epistola")
            assert reading.get("printed") != formula["latin"]  # recorded only when it differs
            seen.append(reading["text"])
        readings[formula["class"]] += len(formula["readings"])
    assert readings == CLASS_READINGS
    reused = FIXTURE["reused"]
    seen += [r["text"] for r in reused["readings"]]
    assert len(seen) == len(set(seen)) == 206
    assert reused["readings"] == [
        {
            "text": "proprium.nativitas-domini-in-die-evangelium",
            "leaf": 100,
            "printed_page": "21",
            "printed": "Inítium sancti Evangélii secúndum Ioánnem",
        }
    ]


def test_core_fields_are_those_of_a_spoken_ordinary_heading():
    for text_id in LATIN:
        doc = load(core_path(text_id))
        assert (doc["category"], doc["section"], doc["variant"], doc["sung"]) == (
            "ordinarium",
            "missa-catechumenorum",
            "missae",
            False,
        )
        (segment,) = doc["segments"]
        assert segment["id"] == "s01" and segment["type"] == "verse"
        assert (segment["speaker"], segment["voice"]) == ("sacerdos", "clara")
        assert "participation" not in segment and "delivery" not in segment
        assert doc["ids"] == {"next": len(segment["words"]) + 1, "segments": {"next": 2}}
        assert [w["id"] for w in segment["words"]] == [
            f"w{n:03d}" for n in range(1, len(segment["words"]) + 1)
        ]
        source = doc["editorial"]["source"]
        assert source["witnesses"] == f"witnesses/{text_id}/"
        assert source["apparatus"] == f"witnesses/{text_id}/apparatus.json"
        localization = doc["localization"]
        assert localization["about"] is True
        assert "about_citations" not in localization
        expected = {"w003": {}} if text_id == "ordinarium.lectio-libri-sapientiae" else None
        assert localization.get("explanations") == expected


def test_the_new_lemmata_and_their_registrations():
    lemmata = load("lexicon/lemmata.json")["entries"]
    senses = load("languages/pl/lexicon.json")["entries"]
    for lemma, entry in NEW_LEMMATA.items():
        assert lemmata[lemma] == entry
        assert senses[lemma]["senses"]
        if lemma[0].isupper():
            assert lemma in PROPER_LEMMAS
    assert "Iudith" in INDECLINABLE
    used = {w["lemma"] for text_id in LATIN for w in words(load(core_path(text_id)))}
    assert set(NEW_LEMMATA) <= used
    # Existing entries are reused, not duplicated under another spelling.
    for lemma in ("romanus", "Hebraeus", "actus", "liber_volumen", "sapientia", "propheta"):
        assert lemma in used and lemma in lemmata


def test_witnesses_transcribe_the_representative_print_and_name_the_other_readings():
    for text_id, formula in FORMULAS.items():
        directory = f"witnesses/{text_id}"
        rep = formula["representative"]
        assert body(f"{directory}/mr.txt") == [rep["printed"]]
        assert header(f"{directory}/mr.txt", "location") == [
            f"printed p. {rep['printed_page']}; IA leaf n{rep['leaf']} / "
            f"one-based PDF p. {rep['leaf'] + 1}"
        ]
        (also,) = header(f"{directory}/mr.txt", "also-printed")
        named = re.findall(r"(proprium\.[a-z0-9-]+), leaf n(\d+), p\. (\w+)", also)
        others = [r for r in formula["readings"] if r["text"] != rep["reading"]]
        assert named == [(r["text"], str(r["leaf"]), r["printed_page"]) for r in others]
        bound = resolve_binding(ROOT / directory / "do.txt", ROOT)
        assert bound is not None  # the DO heading line is an exact registered reading
        assert len(body(f"{directory}/do.txt")) == 1
        apparatus = load(f"{directory}/apparatus.json")
        assert apparatus["text"] == text_id
        merged, _ = store.load(ROOT, text_id)
        errors, warnings, stats = collate(merged, ROOT / directory)
        assert (errors, warnings) == ([], [])
        assert stats["witnesses"] == 3


def test_the_restored_capital_accent_is_declared_against_all_three_witnesses():
    apparatus = load("witnesses/ordinarium.lectio-actuum-apostolorum/apparatus.json")
    assert [e for e in apparatus["adjudicated"] if e["at"] == "w002"] == [
        {
            "at": "w002",
            "ours": "Áctuum",
            "witnesses": {"mr": "Actuum", "do": "Actuum", "vatican1962": "Actuum"},
            "class": "capital-accent",
            "ruling": (
                "The Benziger page, Vatican page and pinned digital heading set the capital "
                "without its acute (Actuum). Retain the house form Áctuum: three syllables, "
                "stressed first, under ORTHOGRAPHY.md rule 4."
            ),
        }
    ]


def test_the_polish_layer_is_complete_and_its_provenance_current():
    manifest = load("languages/pl/manifest.json")["texts"]
    rows = {row["site"]: row for row in load("languages/pl/translation-provenance.json")["sites"]}
    glosses = 0
    for text_id in LATIN:
        assert text_id in manifest
        core = load(core_path(text_id))
        layer = load(layer_path("pl", text_id))
        assert layer["text"] == text_id and layer["about"].strip()
        translation = layer["segments"]["s01"]["translation"]
        assert translation.strip() and "alignments" not in layer["segments"]["s01"]
        assert list(layer["words"]) == [w["id"] for w in words(core)]
        assert all(entry["gloss"].strip() for entry in layer["words"].values())
        glosses += len(layer["words"])
        row = rows[f"{text_id}.s01.pl"]
        assert (row["origin"], row["review"], row["familiar_core"]) == ("own", "working", False)
        assert row["source_sha256"] == canonical_hash(source_payload(core["segments"][0]))
        assert row["target_sha256"] == canonical_hash(translation)
    assert glosses == 137
    explained = load(layer_path("pl", "ordinarium.lectio-libri-sapientiae"))["words"]["w003"]
    assert explained["explanation"].strip()


def test_each_text_binds_its_print_and_its_digital_heading_in_the_graph():
    uses = {use["id"]: use for use in load("bibliography/graph.json")["uses"]}
    for text_id, formula in FORMULAS.items():
        rep = formula["representative"]
        printed = uses[f"use.{text_id}.mr1962"]
        assert (printed["edition"], printed["digital_item"], printed["role"]) == (
            "edition.missale-romanum.1962-typica",
            "item.missale-romanum.1962-typica.ia",
            "direct_approved_print",
        )
        assert printed["address"] == {"kind": "text", "text": text_id}
        assert printed["locator"]["printed"] == rep["printed_page"]
        assert printed["locator"]["page_url"].endswith(f"/page/n{rep['leaf']}/mode/1up")
        digital = uses[f"use.{text_id}.do44667ff"]
        assert digital["role"] == "derived_digital_collation_aid"
        assert digital["edition"] == "edition.divinum-officium-missa.44667ff"
        assert digital["address"] == {"kind": "text", "text": text_id}
    text_id = "ordinarium.lectio-libri-sapientiae"
    for printed, leaf in SAPIENTIAE_PAGES.items():
        use = uses[f"use.{text_id}.w003.mr1962-p{printed}"]
        assert use["role"] == "official_liturgical_context"
        assert use["address"] == {"kind": "word", "text": text_id, "word": "w003"}
        assert use["locator"]["page_url"].endswith(f"/page/n{leaf}/mode/1up")


def test_controls_the_last_gospel_announcement_and_deo_gratias_are_unchanged():
    gospel = load("texts/ordinarium/evangelium-ultimum.json")
    s05 = next(s for s in gospel["segments"] if s["id"] == "s05")
    assert [(w["id"], w["form"] + w.get("post", "")) for w in s05["words"]] == [
        ("w007", "Inítium"),
        ("w008", "sancti"),
        ("w009", "Evangélii"),
        ("w010", "secúndum"),
        ("w011", "Ioánnem."),
    ]
    assert (s05["speaker"], s05["voice"]) == ("sacerdos", "clara")
    polish = load("languages/pl/texts/ordinarium/evangelium-ultimum.json")
    assert polish["segments"]["s05"]["translation"] == "Początek świętej Ewangelii według Jana."
    assert [polish["words"][w]["gloss"] for w in ("w007", "w008", "w009", "w010", "w011")] == [
        "Początek",
        "świętej",
        "Ewangelii",
        "według",
        "Jana",
    ]
    deo = load("texts/ordinarium/deo-gratias-epistolae.json")
    assert latin(deo) == "Deo grátias."
    assert deo["ids"] == {"next": 3, "segments": {"next": 2}}


def test_mutants_are_seen_by_the_checks_they_rely_on():
    text_id = "ordinarium.lectio-epistolae-beati-pauli-apostoli-ad-romanos"
    merged, _ = store.load(ROOT, text_id)
    wrong = copy.deepcopy(merged)
    wrong["segments"][0]["words"][6]["form"] = "Románis"
    errors, _, _ = collate(wrong, ROOT / f"witnesses/{text_id}")
    assert any("SUBSTANTIVE divergence" in error for error in errors)

    actuum, _ = store.load(ROOT, "ordinarium.lectio-actuum-apostolorum")
    bare = copy.deepcopy(actuum)
    bare["segments"][0]["words"][1]["form"] = "Actuum"
    assert lint_text(actuum)[0] == []
    assert "w002: 'Actuum' has 3 syllables but no accent" in lint_text(bare)[0]

    core = load(core_path(text_id))
    layer = load(layer_path("pl", text_id))
    assert check_layer(core, layer, ROOT / layer_path("pl", text_id)) == []
    missing = copy.deepcopy(layer)
    del missing["words"]["w004"]
    assert check_layer(core, missing, ROOT / layer_path("pl", text_id))

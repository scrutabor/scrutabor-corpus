"""The English layer of the reading-announcement headings, pinned.

The 1962 Missal announces each Epistle and Gospel with a short heading (Léctio Epístolæ beáti
Pauli Apóstoli ad Romános, Sequéntia sancti Evangélii secúndum Lucam). Each of the 26 heading
texts carries one English verse, which is the heading as a reader says it and, like the Latin,
has no closing full stop. The verse is also the text's English title, and the interlinear line
reads the verse in Latin order with every Latin word realized once. The register is anchored on
the Last Gospel's heading, "The beginning of the holy Gospel according to John.", which is held
here as a control. Mutated copies show that each pin fails on the defect it names.
"""

import json
from collections.abc import Callable
from copy import deepcopy

import pytest

from checks.interlinear import check as check_alignment
from checks.language_packs import check_layer
from checks.layout import CORPUS
from checks.translation_provenance import canonical_hash, source_payload

LEMMA_JSON = CORPUS / "lexicon" / "lemmata.json"
EN = CORPUS / "languages" / "en"
HEADING_TITLES = ("Léctio ", "Sequéntia ", "Inítium ", "Pássio ")

PAULINE = {
    "corinthios": "the Corinthians",
    "romanos": "the Romans",
    "ephesios": "the Ephesians",
    "colossenses": "the Colossians",
    "galatas": "the Galatians",
    "philippenses": "the Philippians",
    "hebraeos": "the Hebrews",
    "thessalonicenses": "the Thessalonians",
    "titum": "Titus",
}

# slug -> the interlinear realizations in Latin order; None marks a word realized by a group.
LINES: dict[str, tuple[str | None, ...]] = {
    "lectio-actuum-apostolorum": ("A reading", "from the Acts", "of the Apostles"),
    **{
        f"lectio-epistolae-beati-{slug}-apostoli": (
            "A reading",
            "from the Epistle",
            "of blessed",
            name,
            "the Apostle",
        )
        for slug, name in (("petri", "Peter"), ("iacobi", "James"), ("ioannis", "John"))
    },
    **{
        f"lectio-epistolae-beati-pauli-apostoli-ad-{slug}": (
            "A reading",
            "from the Epistle",
            "of blessed",
            "Paul",
            "the Apostle",
            "to",
            people,
        )
        for slug, people in PAULINE.items()
    },
    "lectio-libri-sapientiae": ("A reading", "from the book", "of Wisdom"),
    "lectio-libri-apocalypsis-beati-ioannis-apostoli": (
        "A reading",
        "from the book",
        "of Revelation",
        "of blessed",
        "John",
        "the Apostle",
    ),
    "lectio-libri-iudith": ("A reading", "from the book", "of Judith"),
    "lectio-libri-machabaeorum": ("A reading", "from the book", "of the Maccabees"),
    **{
        f"lectio-{slug}-prophetae": ("A reading", f"from {name}", "the Prophet")
        for slug, name in (
            ("isaiae", "Isaiah"),
            ("ezechielis", "Ezekiel"),
            ("malachiae", "Malachi"),
        )
    },
    "initium-sancti-evangelii-secundum-matthaeum": (
        "The beginning",
        "of the holy",
        "Gospel",
        "according to",
        "Matthew",
    ),
    "passio-domini-nostri-iesu-christi-secundum-matthaeum": (
        "The Passion",
        None,
        None,
        "Jesus",
        "Christ",
        "according to",
        "Matthew",
    ),
    **{
        f"sequentia-sancti-evangelii-secundum-{slug}": (
            "The continuation",
            "of the holy",
            "Gospel",
            "according to",
            name,
        )
        for slug, name in (
            ("matthaeum", "Matthew"),
            ("lucam", "Luke"),
            ("ioannem", "John"),
            ("marcum", "Mark"),
        )
    },
}
GROUPS = {
    "passio-domini-nostri-iesu-christi-secundum-matthaeum": [
        {"words": ["w002", "w003"], "anchor": "w002", "gloss": "of our Lord"}
    ]
}
VERSES = {
    "lectio-actuum-apostolorum": "A reading from the Acts of the Apostles",
    "lectio-epistolae-beati-petri-apostoli": (
        "A reading from the Epistle of blessed Peter the Apostle"
    ),
    "lectio-epistolae-beati-iacobi-apostoli": (
        "A reading from the Epistle of blessed James the Apostle"
    ),
    "lectio-epistolae-beati-ioannis-apostoli": (
        "A reading from the Epistle of blessed John the Apostle"
    ),
    **{
        f"lectio-epistolae-beati-pauli-apostoli-ad-{slug}": (
            f"A reading from the Epistle of blessed Paul the Apostle to {people}"
        )
        for slug, people in PAULINE.items()
    },
    "lectio-libri-sapientiae": "A reading from the book of Wisdom",
    "lectio-libri-apocalypsis-beati-ioannis-apostoli": (
        "A reading from the book of Revelation of blessed John the Apostle"
    ),
    "lectio-libri-iudith": "A reading from the book of Judith",
    "lectio-libri-machabaeorum": "A reading from the book of the Maccabees",
    "lectio-isaiae-prophetae": "A reading from Isaiah the Prophet",
    "lectio-ezechielis-prophetae": "A reading from Ezekiel the Prophet",
    "lectio-malachiae-prophetae": "A reading from Malachi the Prophet",
    "initium-sancti-evangelii-secundum-matthaeum": (
        "The beginning of the holy Gospel according to Matthew"
    ),
    "passio-domini-nostri-iesu-christi-secundum-matthaeum": (
        "The Passion of our Lord Jesus Christ according to Matthew"
    ),
    "sequentia-sancti-evangelii-secundum-matthaeum": (
        "The continuation of the holy Gospel according to Matthew"
    ),
    "sequentia-sancti-evangelii-secundum-lucam": (
        "The continuation of the holy Gospel according to Luke"
    ),
    "sequentia-sancti-evangelii-secundum-ioannem": (
        "The continuation of the holy Gospel according to John"
    ),
    "sequentia-sancti-evangelii-secundum-marcum": (
        "The continuation of the holy Gospel according to Mark"
    ),
}
SLUGS = sorted(LINES)
EXPLANATION = (
    "lectio-libri-sapientiae",
    "w003",
    "The missal sets this heading over readings from Proverbs, Ecclesiasticus and the Song of "
    "Songs as well as from the book of Wisdom itself, so “Wisdom” here is wider than the title "
    "of one book.",
)
SENSES = {
    "lectio": {"senses": ["reading", "lesson"], "derivatives": ["lection", "lectionary"]},
    "epistola": {"senses": ["letter, epistle"], "derivatives": ["epistle", "epistolary"]},
    "sequentia": {"senses": ["continuation", "sequence (chant)"], "derivatives": ["sequence"]},
    "apocalypsis": {"senses": ["revelation", "Apocalypse"], "derivatives": ["apocalypse"]},
    "Corinthius": {"senses": ["Corinthian"]},
    "Ephesius": {"senses": ["Ephesian"]},
    "Colossensis": {"senses": ["Colossian"]},
    "Philippensis": {"senses": ["Philippian"]},
    "Thessalonicensis": {"senses": ["Thessalonian"]},
    "Galata": {"senses": ["Galatian"]},
    "Iudith": {"senses": ["Judith"]},
    "Machabaeus": {"senses": ["Maccabee"]},
    "Ezechiel": {"senses": ["Ezekiel"]},
    "Malachias": {"senses": ["Malachi"]},
}
ANCHOR = {
    "translation": "The beginning of the holy Gospel according to John.",
    "glosses": ("The beginning", "of the holy", "Gospel", "according to", "John"),
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def core(slug):
    return load(CORPUS / "texts" / "ordinarium" / f"{slug}.json")


def layer(slug):
    return load(EN / "texts" / "ordinarium" / f"{slug}.json")


def realized_line(core_doc, layer_doc):
    """The visible interlinear line in Latin order: direct glosses and each group's caption."""
    groups = {
        word_id: group
        for segment in layer_doc["segments"].values()
        for group in segment.get("alignments") or []
        for word_id in group["words"]
    }
    out = []
    for segment in core_doc["segments"]:
        for word in segment["words"]:
            gloss = (layer_doc["words"].get(word["id"]) or {}).get("gloss")
            group = groups.get(word["id"])
            if gloss is not None:
                out.append(gloss)
            elif group is not None and group.get("anchor") == word["id"]:
                out.append(group["gloss"])
    return out


def heading_findings(slug, core_doc, layer_doc):
    """Every way the English layer of one heading can leave its pinned state."""
    findings = []
    segments = layer_doc.get("segments") or {}
    if list(segments) != ["s01"]:
        return [f"{slug}: segments {list(segments)}"]
    verse = segments["s01"].get("translation")
    if verse != VERSES[slug]:
        findings.append(f"{slug}: verse {verse!r}")
    if isinstance(verse, str) and verse[-1:] in {".", "!", "?", ",", ";", ":"}:
        findings.append(f"{slug}: the verse closes with {verse[-1]!r}, the Latin with none")
    latin = [word["id"] for word in core_doc["segments"][0]["words"]]
    if len(latin) != len(LINES[slug]):
        findings.append(f"{slug}: {len(latin)} Latin words against {len(LINES[slug])} pinned")
    direct = tuple((layer_doc["words"].get(w) or {}).get("gloss") for w in latin)
    if direct != LINES[slug]:
        findings.append(f"{slug}: direct glosses {direct}")
    if segments["s01"].get("alignments", []) != GROUPS.get(slug, []):
        findings.append(f"{slug}: groups {segments['s01'].get('alignments')}")
    if " ".join(realized_line(core_doc, layer_doc)) != VERSES[slug]:
        findings.append(f"{slug}: the interlinear line does not read the verse")
    findings += check_alignment(core_doc, layer_doc)
    about = layer_doc.get("about")
    if not isinstance(about, str) or not about.strip() or ";" in about:
        findings.append(f"{slug}: about {about!r}")
    if any(
        "explanation" in entry and (slug, word_id) != EXPLANATION[:2]
        for word_id, entry in layer_doc["words"].items()
    ):
        findings.append(f"{slug}: an explanation outside the declared site")
    return findings


def manifest_findings(manifest):
    findings = []
    for slug in SLUGS:
        text_id = f"ordinarium.{slug}"
        if text_id not in manifest["texts"]:
            findings.append(f"{text_id}: not published")
        if (manifest.get("titles") or {}).get(text_id) != {"title": VERSES[slug]}:
            findings.append(f"{text_id}: title {(manifest.get('titles') or {}).get(text_id)!r}")
    return findings


def lexicon_findings(lexicon, lemmata):
    findings = []
    for lemma, entry in SENSES.items():
        if lexicon.get(lemma) != entry:
            findings.append(f"{lemma}: {lexicon.get(lemma)!r}")
        if "localization" in lemmata.get(lemma, {}) or lemma not in lemmata:
            findings.append(f"{lemma}: neutral entry missing or requiring a note")
    return findings


def provenance_findings(rows, layers):
    findings = []
    for slug in SLUGS:
        segment = core(slug)["segments"][0]
        site = f"ordinarium.{slug}.s01.en"
        verse = layers[slug]["segments"]["s01"]["translation"]
        wanted = {
            "site": site,
            "text": f"ordinarium.{slug}",
            "segment": "s01",
            "language": "en",
            "familiar_core": False,
            "origin": "own",
            "review": "working",
            "source_sha256": canonical_hash(source_payload(segment)),
            "target_sha256": canonical_hash(verse),
        }
        if rows.get(site) != wanted:
            findings.append(f"{site}: {rows.get(site)!r}")
        if "translation_citations" in layers[slug]["segments"]["s01"]:
            findings.append(f"{site}: an own verse carries a wording citation")
    return findings


def anchor_findings(anchor_core, anchor_layer):
    segment = next(s for s in anchor_core["segments"] if s["id"] == "s05")
    glosses = tuple(
        (anchor_layer["words"].get(word["id"]) or {}).get("gloss") for word in segment["words"]
    )
    findings = []
    if anchor_layer["segments"]["s05"].get("translation") != ANCHOR["translation"]:
        findings.append(f"s05: {anchor_layer['segments']['s05'].get('translation')!r}")
    if glosses != ANCHOR["glosses"]:
        findings.append(f"s05 glosses: {glosses}")
    return findings


def test_the_pins_cover_every_heading_text_of_the_ordinary():
    found = {
        path.stem
        for path in (CORPUS / "texts" / "ordinarium").glob("*.json")
        if load(path)["title"].startswith(HEADING_TITLES)
    }
    assert found == set(SLUGS) == set(VERSES)
    assert len(SLUGS) == 26


@pytest.mark.parametrize("slug", SLUGS)
def test_heading_layer_is_pinned(slug):
    core_doc, layer_doc = core(slug), layer(slug)
    assert heading_findings(slug, core_doc, layer_doc) == []
    path = EN / "texts" / "ordinarium" / f"{slug}.json"
    assert check_layer(core_doc, layer_doc, path) == []


def test_gloss_counts():
    words = sum(len(core(slug)["segments"][0]["words"]) for slug in SLUGS)
    direct = sum(1 for slug in SLUGS for entry in layer(slug)["words"].values() if "gloss" in entry)
    grouped = sum(
        len(group["words"])
        for slug in SLUGS
        for group in layer(slug)["segments"]["s01"].get("alignments") or []
    )
    assert (words, direct, grouped) == (137, 135, 2)
    assert words == sum(len(line) for line in LINES.values())


def test_peter_heading_explains_which_detail_is_not_specified():
    about = layer("lectio-epistolae-beati-petri-apostoli")["about"]
    assert (
        "It names the Apostle without specifying which of his two Epistles is being read. "
        "The 1962 Roman Missal uses it over readings from both." in about
    )


def test_the_wisdom_heading_explains_the_books_it_announces():
    slug, word_id, text = EXPLANATION
    assert layer(slug)["words"][word_id]["explanation"] == text
    assert set(core(slug)["localization"]["explanations"]) == {word_id}
    for book in ("Proverbs", "Ecclesiasticus", "Song of Songs", "Wisdom"):
        assert book in text


def test_the_new_lemmata_have_their_english_senses():
    assert lexicon_findings(load(EN / "lexicon.json")["entries"], load(LEMMA_JSON)["entries"]) == []


def test_manifest_publishes_each_heading_under_its_verse():
    assert manifest_findings(load(EN / "manifest.json")) == []


def test_provenance_rows_bind_the_latin_and_the_verse():
    rows = {row["site"]: row for row in load(EN / "translation-provenance.json")["sites"]}
    assert provenance_findings(rows, {slug: layer(slug) for slug in SLUGS}) == []


def test_last_gospel_heading_is_the_unchanged_anchor():
    anchor_core = load(CORPUS / "texts" / "ordinarium" / "evangelium-ultimum.json")
    anchor_layer = load(EN / "texts" / "ordinarium" / "evangelium-ultimum.json")
    assert anchor_findings(anchor_core, anchor_layer) == []
    assert LINES["initium-sancti-evangelii-secundum-matthaeum"][:-1] == ANCHOR["glosses"][:-1]
    for slug in SLUGS:
        if slug.startswith("sequentia-"):
            assert LINES[slug][1:-1] == ANCHOR["glosses"][1:-1]


MUTATIONS: dict[str, Callable[[dict], object]] = {
    "verse": lambda doc: doc["segments"]["s01"].update(translation="A reading from Romans"),
    "closing stop": lambda doc: doc["segments"]["s01"].update(
        translation=doc["segments"]["s01"]["translation"] + "."
    ),
    "dropped gloss": lambda doc: doc["words"]["w001"].pop("gloss"),
    "doubled realization": lambda doc: doc["segments"]["s01"].update(
        alignments=[{"words": ["w001", "w002"], "anchor": "w001", "gloss": "A reading from the"}]
    ),
    "missing about": lambda doc: doc.update(about=""),
    "stray explanation": lambda doc: doc["words"]["w001"].update(explanation="A reading."),
}


@pytest.mark.parametrize("mutation", sorted(MUTATIONS))
@pytest.mark.parametrize(
    "slug",
    [
        "lectio-epistolae-beati-pauli-apostoli-ad-romanos",
        "passio-domini-nostri-iesu-christi-secundum-matthaeum",
        "sequentia-sancti-evangelii-secundum-lucam",
    ],
)
def test_a_damaged_heading_is_rejected(slug, mutation):
    core_doc, layer_doc = core(slug), layer(slug)
    assert heading_findings(slug, core_doc, layer_doc) == []
    mutant = deepcopy(layer_doc)
    MUTATIONS[mutation](mutant)
    assert heading_findings(slug, core_doc, mutant)


def test_a_damaged_title_sense_or_provenance_row_is_rejected():
    luke = "sequentia-sancti-evangelii-secundum-lucam"
    manifest = deepcopy(load(EN / "manifest.json"))
    manifest["titles"][f"ordinarium.{luke}"] = {
        "title": "A reading from the holy Gospel according to Luke"
    }
    assert manifest_findings(manifest)
    lexicon = deepcopy(load(EN / "lexicon.json")["entries"])
    lexicon["sequentia"]["senses"] = ["sequence"]
    assert lexicon_findings(lexicon, load(LEMMA_JSON)["entries"])
    rows = {row["site"]: row for row in load(EN / "translation-provenance.json")["sites"]}
    layers = {slug: layer(slug) for slug in SLUGS}
    layers[luke]["segments"]["s01"]["translation"] += "."
    assert provenance_findings(rows, layers)


def test_the_control_anchor_detects_a_changed_last_gospel_heading():
    anchor_core = load(CORPUS / "texts" / "ordinarium" / "evangelium-ultimum.json")
    anchor_layer = load(EN / "texts" / "ordinarium" / "evangelium-ultimum.json")
    mutant = deepcopy(anchor_layer)
    mutant["segments"]["s05"]["translation"] = "The beginning of the Gospel according to John."
    assert anchor_findings(anchor_core, mutant)
    mutant = deepcopy(anchor_layer)
    mutant["words"]["w008"]["gloss"] = "of holy"
    assert anchor_findings(anchor_core, mutant)

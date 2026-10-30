"""Caption case, conclusion formulas and future tenses in Polish and English word captions.

Captions follow the target-language sentence as it is read continuously: a Polish or English
caption is capitalized only at a real sentence start or for a divine pronoun, title or proper
name, and the relative of a prayer conclusion that continues its English sentence reads
"who". An ablative absolute with a pronoun subject (te miseránte) takes one Polish caption in
the words of the prayer. English futures read "will" where the Latin states a promise,
prediction or consequence; a Latin future perfect or present subjunctive in a general clause
reads as an English present. A second-person verb whose subject is only its ending carries the
pronoun, and destítuo with an ablative of separation reads "deprive of". The Corpus Christi and
Sacred Heart Secrets end with the contemporary conclusion formula. In the Seven Sorrows Secret
the possessor, the companions and the intercession of one ablative absolute have separate
English captions with a note on the delayed head noun.

Every pinned caption is checked with the Latin word it renders, one in-memory mutant per
diagnostic class must fail its class, and the restored documents must pass again.
"""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from anne_epistle_fixture import opening_case
from english_register_successor_fixture import english_register_caption_successor
from possessive_sweep_b1_successor_fixture import possessive_b1_group
from possessive_sweep_b2_successor_fixture import possessive_b2_group
from possessive_sweep_b4_successor_fixture import possessive_b4_group
from rosary_communion_fixture import rosary_opening_case

from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs
from checks.translation_provenance import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
P = "proprium."


def path_of(text, language=None):
    category, name = text.split(".", 1)
    prefix = ROOT if language is None else ROOT / "languages" / language
    return prefix / "texts" / category / f"{name}.json"


def load(text, language=None):
    return json.loads(path_of(text, language).read_text(encoding="utf-8"))


def latin(core):
    return {w["id"]: w for s in core["segments"] for w in s.get("words", [])}


def caption(layer, segment, ids):
    """The caption that realizes exactly these words, or None when they are not one unit."""
    for group in layer["segments"][segment].get("alignments", []):
        if group["words"] == list(ids):
            return group.get("gloss")
        if set(ids) & set(group["words"]):
            return None
    if len(ids) != 1:
        return None
    return layer["words"][ids[0]].get("gloss")


# (language, text, segment, words, anchor or None, caption, Latin forms)
CAPTIONS = (
    (
        "pl",
        P + "omnium-sanctorum-secreta",
        "s01",
        ("w019", "w020"),
        "w020",
        "za Twoim zmiłowaniem",
        ("te", "miseránte"),
    ),
    (
        "pl",
        P + "dominica-xxii-post-pentecosten-epistola",
        "s01",
        ("w007",),
        None,
        "Ten, który",
        ("qui",),
    ),
    (
        "pl",
        P + "purificatio-beatae-mariae-virginis-evangelium",
        "s01",
        ("w133",),
        None,
        "albowiem",
        ("Quia",),
    ),
    (
        "pl",
        P + "purificatio-beatae-mariae-virginis-evangelium",
        "s01",
        ("w145",),
        None,
        "światłość",
        ("Lumen",),
    ),
    (
        "pl",
        P + "purificatio-beatae-mariae-virginis-tractus",
        "s01",
        ("w043",),
        None,
        "albowiem",
        ("Quia",),
    ),
    (
        "pl",
        P + "purificatio-beatae-mariae-virginis-tractus",
        "s01",
        ("w055",),
        None,
        "światłość",
        ("Lumen",),
    ),
    (
        "pl",
        P + "exaltatio-sanctae-crucis-postcommunio",
        "s01",
        ("w008",),
        None,
        "świętego",
        ("sanctæ",),
    ),
    (
        "pl",
        P + "nativitas-domini-in-aurora-postcommunio",
        "s01",
        ("w004", "w005", "w006", "w007"),
        "w006",
        "nowość tajemnicy narodzin zawsze",
        ("sacraménti", "semper", "nóvitas", "natális"),
    ),
    ("pl", P + "dominica-i-adventus-collecta", "s01", ("w009",), None, "z", ("ab",)),
    (
        "pl",
        P + "dominica-iii-in-quadragesima-postcommunio",
        "s01",
        ("w014",),
        None,
        "dajesz",
        ("tríbuis",),
    ),
    (
        "pl",
        P + "immaculatum-cor-beatae-mariae-virginis-postcommunio",
        "s01",
        ("w001",),
        None,
        "Boskimi",
        ("Divínis",),
    ),
    ("en", P + "corporis-christi-communio", "s01", ("w012",), None, "He comes", ("véniat",)),
    ("en", P + "corporis-christi-communio", "s01", ("w014",), None, "whoever", ("quicúmque",)),
    ("en", P + "corporis-christi-communio", "s01", ("w015",), None, "eats", ("manducáverit",)),
    ("en", P + "corporis-christi-communio", "s01", ("w018",), None, "drinks", ("bíberit",)),
    ("en", P + "corporis-christi-communio", "s01", ("w023",), None, "will be", ("erit",)),
    ("en", P + "corporis-christi-evangelium", "s03", ("w050",), None, "will live", ("vivet",)),
    ("en", P + "corporis-christi-evangelium", "s06", ("w073",), None, "will live", ("vivet",)),
    (
        "en",
        P + "sancti-iacobi-apostoli-evangelium",
        "s01",
        ("w066",),
        None,
        "you will drink",
        ("bibétis",),
    ),
    (
        "en",
        P + "corporis-christi-secreta",
        "s01",
        ("w031", "w032"),
        "w031",
        "of the Holy Spirit",
        ("Spíritus", "Sancti"),
    ),
    (
        "en",
        P + "corporis-christi-secreta",
        "s02",
        ("w034", "w035", "w036", "w037"),
        "w036",
        "forever and ever",
        ("per", "ómnia", "sǽcula", "sæculórum"),
    ),
    (
        "en",
        P + "sacratissimi-cordis-iesu-secreta",
        "s01",
        ("w037", "w038"),
        "w037",
        "of the Holy Spirit",
        ("Spíritus", "Sancti"),
    ),
    (
        "en",
        P + "sacratissimi-cordis-iesu-secreta",
        "s02",
        ("w040", "w041", "w042", "w043"),
        "w042",
        "forever and ever",
        ("per", "ómnia", "sǽcula", "sæculórum"),
    ),
    (
        "en",
        P + "dominica-ii-post-pentecosten-collecta",
        "s01",
        ("w015", "w016"),
        "w016",
        "of Your guidance",
        ("tua", "gubernatióne"),
    ),
    (
        "en",
        P + "dominica-ii-post-pentecosten-collecta",
        "s01",
        ("w017",),
        None,
        "You deprive",
        ("destítuis",),
    ),
    (
        "en",
        P + "dominica-ii-post-pentecosten-collecta",
        "s01",
        ("w023",),
        None,
        "You establish",
        ("instítuis",),
    ),
    (
        "en",
        P + "septem-dolorum-beatae-mariae-virginis-secreta",
        "s01",
        ("w022",),
        None,
        "her",
        ("suo",),
    ),
    (
        "en",
        P + "septem-dolorum-beatae-mariae-virginis-secreta",
        "s01",
        ("w023", "w024", "w025", "w026", "w027"),
        "w027",
        "and of her holy companions beneath the Cross",
        ("suorúmque", "sub", "Cruce", "Sanctórum", "consórtium"),
    ),
    (
        "en",
        P + "septem-dolorum-beatae-mariae-virginis-secreta",
        "s01",
        ("w028", "w029", "w030"),
        "w030",
        "through the multiplied, most loving intercession",
        ("multiplicáto", "piíssimo", "intervéntu"),
    ),
)

# (language, text, word, quoted forms the note must contain, declared languages)
NOTES = (
    ("pl", P + "epiphania-domini-secreta", "w017", ("„quod”", "„Ten, który”"), ["pl"]),
    (
        "en",
        P + "septem-dolorum-beatae-mariae-virginis-secreta",
        "w030",
        ("“Intervéntu”", "“suo” (w022)"),
        ["en"],
    ),
)

LATERAN = P + "dedicatio-archibasilicae-sanctissimi-salvatoris-postcommunio"

# Conclusion relatives whose English caption continues its sentence (one word per text).
CONTINUING = {
    "d-n-iesu-christi-regis-collecta": "w027",
    "d-n-iesu-christi-regis-secreta": "w028",
    "dedicatio-sancti-michaelis-archangeli-secreta": "w031",
    "dominica-ii-post-epiphaniam-collecta": "w028",
    "dominica-ii-post-epiphaniam-postcommunio": "w027",
    "dominica-ii-post-epiphaniam-secreta": "w018",
    "dominica-ii-post-pentecosten-collecta": "w031",
    "dominica-ii-post-pentecosten-postcommunio": "w021",
    "dominica-ii-post-pentecosten-secreta": "w025",
    "dominica-iii-post-pentecosten-collecta": "w039",
    "dominica-iii-post-pentecosten-postcommunio": "w019",
    "dominica-iii-post-pentecosten-secreta": "w020",
    "dominica-in-quinquagesima-collecta": "w024",
    "dominica-in-quinquagesima-postcommunio": "w022",
    "dominica-in-septuagesima-collecta": "w028",
    "dominica-in-septuagesima-postcommunio": "w025",
    "dominica-iv-post-epiphaniam-postcommunio": "w021",
    "dominica-iv-post-epiphaniam-secreta": "w026",
    "dominica-iv-post-pentecosten-collecta": "w027",
    "dominica-iv-post-pentecosten-postcommunio": "w018",
    "dominica-iv-post-pentecosten-secreta": "w023",
    "dominica-ix-post-pentecosten-collecta": "w027",
    "dominica-ix-post-pentecosten-postcommunio": "w020",
    "dominica-ix-post-pentecosten-secreta": "w026",
    "dominica-v-post-epiphaniam-collecta": "w027",
    "dominica-v-post-epiphaniam-postcommunio": "w022",
    "dominica-v-post-epiphaniam-secreta": "w024",
    "dominica-v-post-pentecosten-collecta": "w036",
    "dominica-v-post-pentecosten-postcommunio": "w025",
    "dominica-v-post-pentecosten-secreta": "w032",
    "dominica-vi-post-epiphaniam-collecta": "w025",
    "dominica-vi-post-epiphaniam-postcommunio": "w021",
    "dominica-vi-post-epiphaniam-secreta": "w019",
    "dominica-vi-post-pentecosten-postcommunio": "w023",
    "dominica-vi-post-pentecosten-secreta": "w035",
    "dominica-vii-post-pentecosten-collecta": "w028",
    "dominica-vii-post-pentecosten-postcommunio": "w026",
    "dominica-viii-post-pentecosten-collecta": "w032",
    "dominica-viii-post-pentecosten-postcommunio": "w023",
    "dominica-x-post-pentecosten-collecta": "w032",
    "dominica-x-post-pentecosten-postcommunio": "w024",
    "dominica-x-post-pentecosten-secreta": "w027",
    "dominica-xi-post-pentecosten-collecta": "w037",
    "dominica-xi-post-pentecosten-postcommunio": "w026",
    "dominica-xi-post-pentecosten-secreta": "w026",
    "dominica-xii-post-pentecosten-collecta": "w035",
    "dominica-xii-post-pentecosten-postcommunio": "w023",
    "dominica-xii-post-pentecosten-secreta": "w025",
    "dominica-xiii-post-pentecosten-collecta": "w029",
    "dominica-xiii-post-pentecosten-secreta": "w025",
    "dominica-xiv-post-pentecosten-collecta": "w033",
    "dominica-xiv-post-pentecosten-postcommunio": "w022",
    "dominica-xiv-post-pentecosten-secreta": "w025",
    "dominica-xix-post-pentecosten-collecta": "w029",
    "dominica-xix-post-pentecosten-postcommunio": "w025",
    "dominica-xix-post-pentecosten-secreta": "w021",
    "dominica-xv-post-pentecosten-collecta": "w028",
    "dominica-xv-post-pentecosten-postcommunio": "w029",
    "dominica-xv-post-pentecosten-secreta": "w019",
    "dominica-xvi-post-pentecosten-collecta": "w025",
    "dominica-xvi-post-pentecosten-postcommunio": "w028",
    "dominica-xvi-post-pentecosten-secreta": "w025",
    "dominica-xvii-post-pentecosten-collecta": "w023",
    "dominica-xvii-post-pentecosten-postcommunio": "w021",
    "dominica-xvii-post-pentecosten-secreta": "w026",
    "dominica-xviii-post-pentecosten-collecta": "w023",
    "dominica-xviii-post-pentecosten-postcommunio": "w024",
    "dominica-xviii-post-pentecosten-secreta": "w033",
    "dominica-xx-post-pentecosten-collecta": "w028",
    "dominica-xx-post-pentecosten-postcommunio": "w021",
    "dominica-xx-post-pentecosten-secreta": "w021",
    "dominica-xxi-post-pentecosten-collecta": "w031",
    "dominica-xxi-post-pentecosten-postcommunio": "w020",
    "dominica-xxi-post-pentecosten-secreta": "w023",
    "dominica-xxii-post-pentecosten-collecta": "w029",
    "dominica-xxii-post-pentecosten-secreta": "w027",
    "dominica-xxiii-post-pentecosten-collecta": "w026",
    "dominica-xxiii-post-pentecosten-postcommunio": "w022",
    "dominica-xxiii-post-pentecosten-secreta": "w023",
    "dominica-xxiv-post-pentecosten-collecta": "w025",
    "dominica-xxiv-post-pentecosten-postcommunio": "w028",
    "dominica-xxiv-post-pentecosten-secreta": "w034",
    "exaltatio-sanctae-crucis-collecta": "w034",
    "exaltatio-sanctae-crucis-postcommunio": "w025",
    "exaltatio-sanctae-crucis-secreta": "w039",
    "immaculatum-cor-beatae-mariae-virginis-collecta": "w037",
    "immaculatum-cor-beatae-mariae-virginis-postcommunio": "w034",
    "immaculatum-cor-beatae-mariae-virginis-secreta": "w030",
    "maternitas-beatae-mariae-virginis-collecta": "w038",
    "maternitas-beatae-mariae-virginis-postcommunio": "w028",
    "maternitas-beatae-mariae-virginis-secreta": "w028",
    "nativitas-beatae-mariae-virginis-collecta": "w031",
    "nativitas-beatae-mariae-virginis-secreta": "w035",
    "nativitas-sancti-ioannis-baptistae-collecta": "w034",
    "nativitas-sancti-ioannis-baptistae-postcommunio": "w022",
    "omnium-sanctorum-collecta": "w032",
    "omnium-sanctorum-postcommunio": "w023",
    "omnium-sanctorum-secreta": "w029",
    "pretiosissimi-sanguinis-domini-nostri-iesu-christi-collecta": "w049",
    "pretiosissimi-sanguinis-domini-nostri-iesu-christi-secreta": "w033",
    "sacratissimi-cordis-iesu-collecta": "w039",
    "sanctae-annae-matris-beatae-mariae-virginis-collecta": "w036",
    "sanctae-annae-matris-beatae-mariae-virginis-postcommunio": "w032",
    "sanctae-annae-matris-beatae-mariae-virginis-secreta": "w036",
    "sancti-bartholomaei-apostoli-collecta": "w036",
    "sancti-bartholomaei-apostoli-postcommunio": "w027",
    "sancti-bartholomaei-apostoli-secreta": "w028",
    "sancti-iacobi-apostoli-collecta": "w029",
    "sancti-iacobi-apostoli-postcommunio": "w024",
    "sancti-iacobi-apostoli-secreta": "w031",
    "sancti-ioachim-confessoris-collecta": "w034",
    "sancti-ioachim-confessoris-postcommunio": "w045",
    "sancti-ioachim-confessoris-secreta": "w040",
    "sancti-ioseph-sponsi-beatae-mariae-virginis-postcommunio": "w026",
    "sancti-ioseph-sponsi-beatae-mariae-virginis-secreta": "w042",
    "sancti-laurentii-martyris-collecta": "w025",
    "sancti-laurentii-martyris-secreta": "w025",
    "sancti-lucae-evangelistae-collecta": "w029",
    "sancti-lucae-evangelistae-secreta": "w033",
    "sancti-matthaei-apostoli-et-evangelistae-collecta": "w026",
    "sancti-matthaei-apostoli-et-evangelistae-postcommunio": "w030",
    "sancti-matthaei-apostoli-et-evangelistae-secreta": "w024",
    "sancti-matthiae-apostoli-collecta": "w028",
    "sancti-matthiae-apostoli-postcommunio": "w027",
    "sancti-matthiae-apostoli-secreta": "w029",
    "sancti-petri-et-pauli-apostolorum-collecta": "w032",
    "sancti-petri-et-pauli-apostolorum-postcommunio": "w019",
    "sancti-petri-et-pauli-apostolorum-secreta": "w025",
    "sanctorum-philippi-et-iacobi-apostolorum-collecta": "w027",
    "sanctorum-philippi-et-iacobi-apostolorum-postcommunio": "w020",
    "sanctorum-philippi-et-iacobi-apostolorum-secreta": "w027",
    "sanctorum-simonis-et-iudae-apostolorum-collecta": "w035",
    "sanctorum-simonis-et-iudae-apostolorum-postcommunio": "w031",
    "sanctorum-simonis-et-iudae-apostolorum-secreta": "w026",
    "transfiguratio-domini-collecta": "w047",
    "transfiguratio-domini-postcommunio": "w027",
    "transfiguratio-domini-secreta": "w026",
    "visitatio-beatae-mariae-virginis-collecta": "w031",
    "visitatio-beatae-mariae-virginis-postcommunio": "w025",
    "visitatio-beatae-mariae-virginis-secreta": "w035",
}

# These continuing relatives now share one short caption with their verbs.
GROUPED_CONTINUING = {
    "dominica-ii-post-pentecosten-secreta": (("w025", "w026", "w027", "w028", "w029"), "w027"),
    "sacratissimi-cordis-iesu-collecta": (("w039", "w040", "w041", "w042", "w043"), "w041"),
    "sancti-bartholomaei-apostoli-collecta": (("w036", "w037", "w038", "w039", "w040"), "w038"),
    "sancti-matthiae-apostoli-collecta": (("w028", "w029", "w030", "w031", "w032"), "w030"),
}

# Direct-address conclusions whose English rendering starts its own sentence.
OPENING_GROUPS = (
    ("corporis-christi-collecta", ("w030", "w031", "w032", "w033"), "w031"),
    ("corporis-christi-postcommunio", ("w019", "w020", "w021", "w022"), "w020"),
    ("sacratissimi-cordis-iesu-postcommunio", ("w021", "w022", "w023", "w024"), "w022"),
)

# Sentence-opening captions keep their individually reviewed form of address.
OPENING = (
    (P + "dominica-i-adventus-collecta", "w021", "You"),
    (P + "pretiosissimi-sanguinis-domini-nostri-iesu-christi-postcommunio", "w024", "Who"),
    (P + "dominica-xxii-post-pentecosten-postcommunio", "w021", "You who"),
    (P + "sancti-ioseph-sponsi-beatae-mariae-virginis-collecta", "w019", "You"),
    (P + "septem-dolorum-beatae-mariae-virginis-collecta", "w043", "You"),
    (P + "septem-dolorum-beatae-mariae-virginis-postcommunio", "w023", "You"),
    (P + "septem-dolorum-beatae-mariae-virginis-secreta", "w038", "You"),
    (P + "beatae-mariae-virginis-a-rosario-postcommunio", "w024", "You"),
    (P + "commemoratio-omnium-fidelium-defunctorum-missa-i-collecta", "w023", "You"),
    (P + "commemoratio-omnium-fidelium-defunctorum-missa-i-postcommunio", "w023", "You"),
)


def caption_diagnostics(row, core, layer):
    language, text, segment, ids, anchor, expected, forms = row
    where = f"{language}:{text}:{'+'.join(ids)}"
    found = []
    words = latin(core)
    if tuple(words[w]["form"] for w in ids if w in words) != forms:
        found.append(f"latin:{where}")
    actual = caption(layer, segment, ids)
    if actual != expected:
        found.append(f"caption:{where}: {actual!r}")
    if anchor is not None:
        (group,) = [
            g for g in layer["segments"][segment].get("alignments", []) if g["words"] == list(ids)
        ] or [None]
        if group is None or group.get("anchor") != anchor:
            found.append(f"group:{where}: anchor")
        if any("gloss" in layer["words"].get(w, {}) for w in ids):
            found.append(f"group:{where}: a member keeps its own caption")
    return found


def note_diagnostics(row, core, layer):
    language, text, wid, quoted, languages = row
    where = f"{language}:{text}:{wid}"
    note = layer["words"].get(wid, {}).get("explanation") or ""
    found = [f"note:{where}: {q}" for q in quoted if q not in note]
    declared = (core.get("localization") or {}).get("explanations", {}).get(wid)
    if declared != {"languages": languages}:
        found.append(f"declaration:{where}: {declared!r}")
    return found


def conclusion_relatives(core):
    """Latin nominative singular qui followed by tecum, vivis, vivit or cum Deo/Patre."""
    for segment in core["segments"]:
        ws = segment.get("words", [])
        for i, w in enumerate(ws):
            m = w["morph"]
            if w["lemma"] != "qui" or m.get("case") != "nom" or m.get("number") != "sg":
                continue
            nxt = [x["form"].lower() for x in ws[i + 1 : i + 3]]
            if nxt[:1] in (["tecum"], ["vivis"], ["vivit"]) or (
                nxt[:1] == ["cum"] and nxt[1:2] in (["deo"], ["patre"])
            ):
                yield segment["id"], w["id"]


def relative_caption(layer, segment, wid):
    """Resolve the actual caption, refusing duplicate or residual realizations."""
    groups = [g for g in layer["segments"][segment].get("alignments", []) if wid in g["words"]]
    if not groups:
        return layer["words"].get(wid, {}).get("gloss")
    if len(groups) != 1:
        return None
    group = groups[0]
    if group["words"][0] != wid or any(
        "gloss" in layer["words"].get(w, {}) for w in group["words"]
    ):
        return None
    return group.get("gloss")


def who_diagnostics(text, core, layer):
    """A conclusion relative continuing its English sentence carries a lowercase caption."""
    found = []
    for segment, wid in conclusion_relatives(core):
        prose = layer["segments"][segment].get("translation") or ""
        continues = ", who liv" in prose and ". Who liv" not in prose
        gloss = relative_caption(layer, segment, wid)
        if continues and not (
            isinstance(gloss, str) and (gloss == "who" or gloss.startswith("who "))
        ):
            found.append(f"who:{text}:{wid}: {gloss!r}")
    return found


def english_layers():
    for path in sorted((ROOT / "languages" / "en" / "texts").glob("*/*.json")):
        yield f"{path.parent.name}.{path.stem}"


@pytest.mark.parametrize("row", CAPTIONS, ids=lambda r: f"{r[0]}-{r[1][len(P) :]}-{r[3][0]}")
def test_pinned_caption_and_its_latin(row):
    assert caption_diagnostics(row, load(row[1]), load(row[1], row[0])) == []


@pytest.mark.parametrize("row", NOTES, ids=lambda r: f"{r[0]}-{r[1][len(P) :]}-{r[2]}")
def test_note_names_the_hidden_relation_and_is_declared_for_its_language(row):
    assert note_diagnostics(row, load(row[1]), load(row[1], row[0])) == []


@pytest.mark.parametrize("name,wid", sorted(CONTINUING.items()))
def test_continuing_conclusion_relative_is_lowercase(name, wid):
    text = P + name
    core, layer = load(text), load(text, "en")
    assert (latin(core)[wid]["lemma"], latin(core)[wid]["form"].lower()) == ("qui", "qui")
    (segment,) = [s for s, w in conclusion_relatives(core) if w == wid]
    assert ", who liv" in layer["segments"][segment]["translation"]
    if name in GROUPED_CONTINUING:
        members, anchor = GROUPED_CONTINUING[name]
        assert members[0] == wid
        assert tuple(latin(core)[w]["form"].lower() for w in members) == (
            "qui",
            "tecum",
            "vivit",
            "et",
            "regnat",
        )
        expected = "who lives and reigns with You"
        touching = [
            g for g in layer["segments"][segment]["alignments"] if set(g["words"]) & set(members)
        ]
        assert touching == [{"words": list(members), "anchor": anchor, "gloss": expected}]
    else:
        expected = "who"
        assert not any(wid in g["words"] for g in layer["segments"][segment].get("alignments", []))
    assert relative_caption(layer, segment, wid) == expected


@pytest.mark.parametrize(
    "name,members,anchor", OPENING_GROUPS, ids=[row[0] for row in OPENING_GROUPS]
)
def test_direct_address_conclusion_starts_its_english_sentence(name, members, anchor):
    core, layer = load(P + name), load(P + name, "en")
    (segment,) = [s for s, w in conclusion_relatives(core) if w == members[0]]
    words = latin(core)
    assert tuple(words[w]["form"].lower() for w in members) == ("qui", "vivis", "et", "regnas")
    assert words[members[1]]["morph"]["person"] == words[members[3]]["morph"]["person"] == 2
    assert ". You live and reign " in layer["segments"][segment]["translation"]
    row = (
        "en",
        P + name,
        segment,
        members,
        anchor,
        "You live and reign",
        tuple(words[w]["form"] for w in members),
    )
    assert caption_diagnostics(row, core, layer) == []
    saved = deepcopy(layer)
    group = next(g for g in layer["segments"][segment]["alignments"] if g["words"] == list(members))
    for wrong in ("who live and reign", "Who live and reign"):
        try:
            group["gloss"] = wrong
            assert layer != saved
            assert caption_diagnostics(row, core, layer) == [
                f"caption:en:{P + name}:{'+'.join(members)}: {wrong!r}"
            ]
        finally:
            group["gloss"] = "You live and reign"
            assert layer == saved
            assert caption_diagnostics(row, core, layer) == []


@pytest.mark.parametrize(
    "text,wid,expected", OPENING, ids=[f"{t[len(P) :]}-{w}" for t, w, _ in OPENING]
)
def test_conclusion_relative_at_an_english_sentence_start_keeps_its_capital(text, wid, expected):
    core, layer = load(text), load(text, "en")
    (segment,) = [s for s, w in conclusion_relatives(core) if w == wid]
    assert layer["words"][wid]["gloss"] == expected
    assert ", who liv" not in layer["segments"][segment]["translation"]
    if expected == "You":
        words = next(s["words"] for s in core["segments"] if s["id"] == segment)
        index = next(i for i, word in enumerate(words) if word["id"] == wid)
        clause = words[index : index + 4]
        assert tuple(word["form"].lower() for word in clause) == ("qui", "vivis", "et", "regnas")
        assert clause[1]["morph"]["person"] == clause[3]["morph"]["person"] == 2
        assert ". You live and reign " in layer["segments"][segment]["translation"]
        assert not any(wid in g["words"] for g in layer["segments"][segment].get("alignments", []))
        row = ("en", text, segment, (wid,), None, "You", (clause[0]["form"],))
        assert caption_diagnostics(row, core, layer) == []
        saved = deepcopy(layer)
        for wrong in ("who", "Who"):
            try:
                layer["words"][wid]["gloss"] = wrong
                assert layer != saved
                assert caption_diagnostics(row, core, layer) == [
                    f"caption:en:{text}:{wid}: {wrong!r}"
                ]
            finally:
                layer["words"][wid]["gloss"] = expected
                assert layer == saved
                assert caption_diagnostics(row, core, layer) == []


def test_no_conclusion_caption_capitalizes_a_continuing_relative():
    found = []
    for text in english_layers():
        found += who_diagnostics(text, load(text), load(text, "en"))
    assert found == []
    assert len(CONTINUING) == 140
    assert len(OPENING) == 10
    assert len(GROUPED_CONTINUING) == 4
    assert len(OPENING_GROUPS) == 3


def test_lateran_prose_matches_its_caption_and_ledger():
    layer = load(LATERAN, "en")
    prose = layer["segments"]["s01"]["translation"]
    assert "in physical space" in prose and "material space" not in prose
    group = caption(layer, "s01", ("w021", "w022", "w023"))
    assert group == "gains in physical space"
    ledger = json.loads((ROOT / "languages/en/translation-provenance.json").read_text("utf-8"))
    (row,) = [r for r in ledger["sites"] if r["site"] == f"{LATERAN}.s01.en"]
    assert row["target_sha256"] == canonical_hash(prose)
    assert (row["origin"], row["review"], row["familiar_core"]) == (
        "working-unsettled",
        "working",
        False,
    )


# Finite contextual Advent case decisions, including lowercase counterexamples.
_CASE_ROWS = json.loads(
    (ROOT / "tests/fixtures/caption-opening-cases.json").read_text(encoding="utf-8")
)
assert set(_CASE_ROWS) == {"advent", "first_openings"}
ADVENT_CAPTIONS = tuple(
    (language, text, segment, tuple(words), anchor, gloss, tuple(forms))
    for language, text, segment, words, anchor, gloss, forms in _CASE_ROWS["advent"]
)
assert len(ADVENT_CAPTIONS) == 40

# Exact contextual first-opening decisions and retained Canon continuations.
FIRST_OPENING_CAPTIONS = tuple(
    (language, text, segment, tuple(words), anchor, gloss, tuple(forms), tuple(wrong))
    for language, text, segment, words, anchor, gloss, forms, wrong in map(
        rosary_opening_case, _CASE_ROWS["first_openings"]
    )
)
assert len(FIRST_OPENING_CAPTIONS) == 289
del _CASE_ROWS

TEXTS = sorted(
    {(row[1], row[0]) for row in CAPTIONS + ADVENT_CAPTIONS} | {(row[1], row[0]) for row in NOTES}
)


@pytest.mark.parametrize("text,language", TEXTS, ids=[f"{lang}-{t}" for t, lang in TEXTS])
def test_touched_layers_pass_the_product_validators(text, language):
    core, layer = load(text), load(text, language)
    assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
    assert language_packs.check_core(core) == []
    assert language_packs.check_layer(core, layer, path_of(text, language)) == []


def set_caption(segment, ids, value):
    def mutate(core, layer):
        for group in layer["segments"][segment].get("alignments", []):
            if group["words"] == list(ids):
                group["gloss"] = value
                return
        layer["words"][ids[0]]["gloss"] = value

    return mutate


def split_group(segment, ids, values):
    def mutate(core, layer):
        groups = layer["segments"][segment]["alignments"]
        groups[:] = [g for g in groups if g["words"] != list(ids)]
        if not groups:
            del layer["segments"][segment]["alignments"]
        for wid, value in zip(ids, values, strict=True):
            layer["words"][wid]["gloss"] = value

    return mutate


def drop_note(wid):
    def mutate(core, layer):
        del layer["words"][wid]["explanation"]

    return mutate


def row_of(language, text, first):
    (row,) = [r for r in CAPTIONS if (r[0], r[1], r[3][0]) == (language, text, first)]
    return row


def move_anchor(segment, ids, anchor):
    def mutate(core, layer):
        for group in layer["segments"][segment]["alignments"]:
            if group["words"] == list(ids):
                group["anchor"] = anchor

    return mutate


def member_caption(wid, value):
    def mutate(core, layer):
        layer["words"][wid]["gloss"] = value

    return mutate


def latin_form(wid, value):
    def mutate(core, layer):
        latin(core)[wid]["form"] = value

    return mutate


ALL_SAINTS = row_of("pl", P + "omnium-sanctorum-secreta", "w019")
GOSPEL = row_of("en", P + "corporis-christi-evangelium", "w050")
# kind: (pinned row, mutation, the diagnostic classes it must produce)
MUTANTS = {
    "capital": (
        row_of("pl", P + "purificatio-beatae-mariae-virginis-tractus", "w043"),
        set_caption("s01", ("w043",), "Albowiem"),
        ("caption",),
    ),
    "split": (
        ALL_SAINTS,
        split_group("s01", ("w019", "w020"), ("Ty", "litując się")),
        ("caption", "group"),
    ),
    "anchor": (ALL_SAINTS, move_anchor("s01", ("w019", "w020"), "w019"), ("group",)),
    "member": (ALL_SAINTS, member_caption("w019", "Ty"), ("group",)),
    "latin": (GOSPEL, latin_form("w050", "vivit"), ("latin",)),
    "future": (GOSPEL, set_caption("s03", ("w050",), "shall live"), ("caption",)),
    "formula": (
        row_of("en", P + "corporis-christi-secreta", "w034"),
        set_caption("s02", ("w034", "w035", "w036", "w037"), "world without end"),
        ("caption",),
    ),
    "person": (
        row_of("en", P + "dominica-ii-post-pentecosten-collecta", "w017"),
        set_caption("s01", ("w017",), "forsake"),
        ("caption",),
    ),
}


@pytest.mark.parametrize("kind", sorted(MUTANTS))
def test_caption_mutant_fails_its_class_and_restores(kind):
    row, mutate, expected = MUTANTS[kind]
    core, layer = load(row[1]), load(row[1], row[0])
    saved = deepcopy(core), deepcopy(layer)
    assert caption_diagnostics(row, core, layer) == []
    mutate(core, layer)
    found = caption_diagnostics(row, core, layer)
    assert found and {item.split(":", 1)[0] for item in found} == set(expected), found
    core, layer = saved
    assert caption_diagnostics(row, core, layer) == []


def test_note_mutant_fails_and_restores():
    row = NOTES[1]
    core, layer = load(row[1]), load(row[1], row[0])
    saved = deepcopy(layer)
    drop_note(row[2])(core, layer)
    assert note_diagnostics(row, core, layer)
    assert note_diagnostics(row, core, saved) == []
    undeclared = deepcopy(core)
    del undeclared["localization"]["explanations"][row[2]]
    assert [d for d in note_diagnostics(row, undeclared, saved) if d.startswith("declaration:")]


def test_who_mutant_fails_and_restores():
    for name in ("d-n-iesu-christi-regis-collecta", "dominica-ii-post-pentecosten-secreta"):
        wid, text = CONTINUING[name], P + name
        core, layer = load(text), load(text, "en")
        (segment,) = [s for s, w in conclusion_relatives(core) if w == wid]
        groups = [g for g in layer["segments"][segment].get("alignments", []) if wid in g["words"]]
        holder = groups[0] if groups else layer["words"][wid]
        saved, before = deepcopy(layer), holder["gloss"]
        assert who_diagnostics(text, core, layer) == []
        for wrong in (before[0].upper() + before[1:], ""):
            try:
                holder["gloss"] = wrong
                assert layer != saved
                assert who_diagnostics(text, core, layer) == [f"who:{text}:{wid}: {wrong!r}"]
            finally:
                holder["gloss"] = before
                assert layer == saved
                assert who_diagnostics(text, core, layer) == []
        if groups:
            try:
                layer["words"][wid]["gloss"] = "Who"
                assert layer != saved
                assert who_diagnostics(text, core, layer) == [f"who:{text}:{wid}: None"]
            finally:
                del layer["words"][wid]["gloss"]
                assert layer == saved
                assert who_diagnostics(text, core, layer) == []


def test_lateran_ledger_mutant_fails_and_restores():
    layer = load(LATERAN, "en")
    prose = layer["segments"]["s01"]["translation"]
    stale = prose.replace("physical space", "material space")
    ledger = json.loads((ROOT / "languages/en/translation-provenance.json").read_text("utf-8"))
    (row,) = [r for r in ledger["sites"] if r["site"] == f"{LATERAN}.s01.en"]
    assert row["target_sha256"] != canonical_hash(stale)
    assert row["target_sha256"] == canonical_hash(prose)


@pytest.mark.parametrize("row", ADVENT_CAPTIONS, ids=lambda r: f"{r[0]}-{r[1][len(P) :]}-{r[3][0]}")
def test_advent_contextual_case_rejects_mutation_and_restores(row):
    core, layer = load(row[1]), load(row[1], row[0])
    saved = deepcopy(layer)
    assert caption_diagnostics(row, core, layer) == []
    expected = row[5]
    wrong = expected[0].swapcase() + expected[1:]
    assert wrong != expected
    try:
        set_caption(row[2], row[3], wrong)(core, layer)
        assert layer != saved
        assert caption_diagnostics(row, core, layer) == [
            f"caption:{row[0]}:{row[1]}:{'+'.join(row[3])}: {wrong!r}"
        ]
    finally:
        set_caption(row[2], row[3], expected)(core, layer)
        assert layer == saved
        assert caption_diagnostics(row, core, layer) == []


@pytest.mark.parametrize(
    "row",
    FIRST_OPENING_CAPTIONS,
    ids=lambda r: f"{r[0]}-{r[1]}-{r[2]}-{r[3][0]}",
)
def test_first_opening_caption_rejects_predecessor_and_restores(row):
    core, layer = load(row[1]), load(row[1], row[0])
    assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
    assert language_packs.check_core(core) == []
    assert language_packs.check_layer(core, layer, path_of(row[1], row[0])) == []
    row = opening_case(row, core, layer)
    if row[1] == P + "assumptio-beatae-mariae-virginis-postcommunio":
        # Preserve the historical case/ID; only its expected wording has a successor.
        before, after = {
            "pl": ("Przyjąwszy", "Przyjęliśmy"),
            "en": ("Having received", "We have received"),
        }[row[0]]
        assert row[2:] == ("s01", ("w001",), None, before, ("Sumptis",), (before.lower(),))
        row = (*row[:5], after, row[6], (*row[7], before, after[0].lower() + after[1:]))
    elif row[:2] == ("pl", P + "commemoratio-omnium-fidelium-defunctorum-missa-i-secreta"):
        # The original opening case stays immutable; its expected caption has a successor.
        assert row[2:] == ("s01", ("w001",), None, "Ofiary", ("Hóstias",), ("ofiary",))
        row = (*row[:5], "Na ofiary", row[6], (*row[7], "Ofiary", "na ofiary"))
    elif row[:2] == ("pl", "ordinarium.communicantes"):
        # The original continuation case stays immutable; its caption has a successor.
        assert row[2:] == (
            "s01",
            ("w001",),
            None,
            "zjednoczeni",
            ("Communicántes",),
            ("Zjednoczeni",),
        )
        after = "trwając we wspólnocie"
        row = (*row[:5], after, row[6], (*row[7], "zjednoczeni", after[0].upper() + after[1:]))
    successor = english_register_caption_successor(row[0], row[1], row[3], row[5])
    if successor is not None:
        # The opening case stays immutable; its expected caption has a register successor.
        row = (*row[:5], successor, row[6], (*row[7], row[5], successor[0].lower() + successor[1:]))
    change = possessive_b1_group(row[0], row[1], row[3], row[5])
    if change is not None:
        # The opening case stays immutable; its word now shares the possessive's caption.
        group, gloss = change["group"], change["group"]["gloss"]
        wrong = (*row[7], row[5], gloss[0].lower() + gloss[1:])
        row = (*row[:3], tuple(group["words"]), group["anchor"], gloss)
        row = (*row, tuple(change["latin"]), wrong)
    change = possessive_b2_group(row[0], row[1], row[3], row[5])
    if change is not None:
        # The opening case stays immutable; its word now shares the possessive's caption.
        group, gloss = change["group"], change["group"]["gloss"]
        wrong = (*row[7], row[5], gloss[0].lower() + gloss[1:])
        row = (*row[:3], tuple(group["words"]), group["anchor"], gloss)
        row = (*row, tuple(change["latin"]), wrong)
    change = possessive_b4_group(row[0], row[1], row[3], row[5])
    if change is not None:
        # The opening case stays immutable; its word now shares the possessive's caption.
        group, gloss = change["group"], change["group"]["gloss"]
        wrong = (*row[7], row[5], gloss[0].lower() + gloss[1:])
        row = (*row[:3], tuple(group["words"]), group["anchor"], gloss)
        row = (*row, tuple(change["latin"]), wrong)
    saved = deepcopy(layer)
    pin = row[:7]
    assert caption_diagnostics(pin, core, layer) == []
    for wrong in row[7]:
        assert wrong != row[5]
        try:
            set_caption(row[2], row[3], wrong)(core, layer)
            assert canonical_hash(layer) != canonical_hash(saved)
            assert caption_diagnostics(pin, core, layer) == [
                f"caption:{row[0]}:{row[1]}:{'+'.join(row[3])}: {wrong!r}"
            ]
        finally:
            set_caption(row[2], row[3], row[5])(core, layer)
            assert layer == saved
            assert caption_diagnostics(pin, core, layer) == []
            assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
            assert language_packs.check_core(core) == []
            assert language_packs.check_layer(core, layer, path_of(row[1], row[0])) == []


# Explicit target-sentence decisions; the two Lauds comparatives continue after a comma.
DOXOLOGY_CAPTIONS = tuple(
    (language, text, segment, tuple(words), anchor, gloss, tuple(forms), tuple(wrong))
    for language, text, segment, words, anchor, gloss, forms, wrong in json.loads(
        (ROOT / "tests/fixtures/doxology-caption-boundaries.json").read_text(encoding="utf-8")
    )
)
assert len(DOXOLOGY_CAPTIONS) == 276
assert len({(r[1], r[2], r[3][0]) for r in DOXOLOGY_CAPTIONS}) == 276
assert sum(bool(r[7]) for r in DOXOLOGY_CAPTIONS) == 34


@pytest.mark.parametrize("row", DOXOLOGY_CAPTIONS, ids=lambda r: f"{r[0]}-{r[1]}-{r[2]}-{r[3][0]}")
def test_doxology_caption_boundary_rejects_wrong_initial_and_recovers(row):
    core, layer = load(row[1]), load(row[1], row[0])
    saved = deepcopy(layer)
    pin = row[:7]
    if row[4] is None:
        assert not any(
            set(group["words"]) & set(row[3])
            for group in layer["segments"][row[2]].get("alignments", [])
        )
    assert caption_diagnostics(pin, core, layer) == []
    assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
    assert language_packs.check_core(core) == []
    assert language_packs.check_layer(core, layer, path_of(row[1], row[0])) == []
    for wrong in row[7]:
        assert wrong != row[5]
        try:
            set_caption(row[2], row[3], wrong)(core, layer)
            assert layer != saved
            assert caption_diagnostics(pin, core, layer) == [
                f"caption:{row[0]}:{row[1]}:{'+'.join(row[3])}: {wrong!r}"
            ]
            with pytest.raises(AssertionError):
                assert caption_diagnostics(pin, core, layer) == []
        finally:
            set_caption(row[2], row[3], row[5])(core, layer)
            assert layer == saved
            assert caption_diagnostics(pin, core, layer) == []
            assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
            assert language_packs.check_core(core) == []
            assert language_packs.check_layer(core, layer, path_of(row[1], row[0])) == []


@pytest.mark.parametrize("language", ["pl", "en"])
def test_anne_and_rosary_opening_comparisons_reject_current_fault_and_recover(language):
    subjects = (
        P + "sanctae-annae-matris-beatae-mariae-virginis-epistola",
        P + "beatae-mariae-virginis-a-rosario-communio",
    )
    for text in subjects:
        core, layer = load(text), load(text, language)
        (original,) = [r for r in FIRST_OPENING_CAPTIONS if (r[0], r[1]) == (language, text)]
        assert language_packs.check_core(core) == []
        assert language_packs.check_layer(core, layer, path_of(text, language)) == []
        assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
        row = opening_case(original, core, layer)
        assert caption_diagnostics(row[:7], core, layer) == []
        saved_core, saved_layer = deepcopy(core), deepcopy(layer)
        try:
            set_caption(row[2], row[3], "control")(core, layer)
            assert core == saved_core and layer != saved_layer
            assert language_packs.check_layer(core, layer, path_of(text, language)) == []
            assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
            assert caption_diagnostics(row[:7], core, layer) == [
                f"caption:{language}:{text}:{'+'.join(row[3])}: 'control'"
            ]
            with pytest.raises(AssertionError, match=r"^composition opening caption(?:\n|$)"):
                assert caption_diagnostics(row[:7], core, layer) == [], (
                    "composition opening caption"
                )
        finally:
            layer.clear()
            layer.update(saved_layer)
        assert core == saved_core and layer == saved_layer
        assert language_packs.check_layer(core, layer, path_of(text, language)) == []
        assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
        assert opening_case(original, core, layer) == row
        assert caption_diagnostics(row[:7], core, layer) == []

"""Polish captions give mereor and mereo a natural Polish government at these sites.

Each row is one exact construction, not a rule for every merit word. An infinitival
complement is realized with być godnym and the infinitive, or with zasłużyć na where the
Polish recasts the infinitive as a noun. A direct or relative object takes na. The Latin
person, number and tense stay visible in the Polish verb. The familiar Regina caeli formula
and two constructions that already read naturally are kept as controls.
"""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from checks.interlinear import check as check_alignment

ROOT = Path(__file__).resolve().parents[1]
P = "proprium."

# id, text, segment, class,
# verb (id, form, lemma, person, number, tense, mood),
# Latin complement words (id, form, lemma, morph key, morph value),
# expected Polish realizations: (word, gloss) or ((group words), anchor, gloss).
# The realization containing the verb is the governor; the others are its complement.
SITES = (
    (
        "annunciation-secret",
        P + "annuntiatio-beatae-mariae-virginis-secreta",
        "s01",
        "infinitive",
        ("w027", "mereámur", "mereor", 1, "pl", "pres", "subj"),
        (("w028", "perveníre", "pervenio", "mood", "inf"),),
        (("w027", "byli godni"), ("w028", "dojść")),
    ),
    (
        "assumption-collect",
        P + "assumptio-beatae-mariae-virginis-collecta",
        "s01",
        "infinitive",
        ("w027", "mereámur", "mereor", 1, "pl", "pres", "subj"),
        (
            ("w026", "glóriæ", "gloria", "case", "gen"),
            ("w028", "esse", "sum", "mood", "inf"),
            ("w029", "consórtes", "consors", "case", "nom"),
        ),
        (("w026", "chwały"), ("w027", "byli godni"), ("w028", "być"), ("w029", "uczestnikami")),
    ),
    (
        "queenship-collect",
        P + "beata-maria-virgo-regina-collecta",
        "s01",
        "infinitive",
        ("w025", "mereámur", "mereor", 1, "pl", "pres", "subj"),
        (("w024", "cónsequi", "consequor", "mood", "inf"),),
        (("w024", "osiągnąć"), ("w025", "byli godni")),
    ),
    (
        "baptism-collect",
        P + "commemoratio-baptismatis-domini-collecta",
        "s01",
        "infinitive",
        ("w021", "mereámur", "mereor", 1, "pl", "pres", "subj"),
        (("w020", "reformári", "reformo", "voice", "pass"),),
        (("w020", "zostać odnowieni"), ("w021", "byli godni")),
    ),
    (
        "lateran-secret",
        P + "dedicatio-archibasilicae-sanctissimi-salvatoris-secreta",
        "s01",
        "infinitive",
        ("w018", "mereámur", "mereor", 1, "pl", "pres", "subj"),
        (("w017", "perveníre", "pervenio", "mood", "inf"),),
        (("w017", "dojść"), ("w018", "byli godni")),
    ),
    (
        "advent-i-collect",
        P + "dominica-i-adventus-collecta",
        "s01",
        "infinitive",
        ("w015", "mereámur", "mereor", 1, "pl", "pres", "subj"),
        (
            ("w017", "éripi", "eripio", "voice", "pass"),
            ("w020", "salvári", "salvo", "voice", "pass"),
        ),
        (
            (("w014", "w015", "w016"), "w015", "pod Twoją ochroną zasłużyli"),
            ("w017", "na wyrwanie"),
            ("w020", "na zbawienie"),
        ),
    ),
    (
        "advent-ii-collect",
        P + "dominica-ii-adventus-collecta",
        "s01",
        "infinitive",
        ("w018", "mereámur", "mereor", 1, "pl", "pres", "subj"),
        (("w017", "servíre", "servio", "mood", "inf"),),
        (("w017", "służyć"), ("w018", "byli godni")),
    ),
    (
        "christmas-octave-sunday-collect",
        P + "dominica-infra-octavam-nativitatis-collecta",
        "s01",
        "infinitive",
        ("w016", "mereámur", "mereor", 1, "pl", "pres", "subj"),
        (("w019", "abundáre", "abundo", "mood", "inf"),),
        (("w016", "byli godni"), (("w017", "w018", "w019"), "w019", "obfitować w dobre uczynki")),
    ),
    (
        "pentecost-xiii-collect",
        P + "dominica-xiii-post-pentecosten-collecta",
        "s01",
        "infinitive",
        ("w013", "mereámur", "mereor", 1, "pl", "pres", "subj"),
        (("w014", "ássequi", "adsequor", "mood", "inf"),),
        (("w013", "byli godni"), ("w014", "osiągnąć"), ("w015", "to, co")),
    ),
    (
        "pentecost-xvi-secret",
        P + "dominica-xvi-post-pentecosten-secreta",
        "s01",
        "infinitive",
        ("w015", "mereámur", "mereor", 1, "pl", "pres", "subj"),
        (
            ("w016", "esse", "sum", "mood", "inf"),
            ("w017", "partícipes", "particeps", "case", "nom"),
        ),
        (("w015", "byli godni"), ("w016", "być"), ("w017", "uczestnikami")),
    ),
    (
        "exaltation-collect",
        P + "exaltatio-sanctae-crucis-collecta",
        "s01",
        "object",
        ("w025", "mereámur", "mereor", 1, "pl", "pres", "subj"),
        (("w022", "prǽmia", "praemium", "case", "acc"),),
        (("w022", "na nagrody"), ("w025", "zasłużyli")),
    ),
    (
        "exaltation-secret",
        P + "exaltatio-sanctae-crucis-secreta",
        "s01",
        "infinitive",
        ("w023", "merúimus", "mereo", 1, "pl", "perf", "ind"),
        (("w022", "adoráre", "adoro", "mood", "inf"),),
        (("w022", "czcić"), ("w023", "byliśmy godni")),
    ),
    (
        "christmas-octave-collect",
        P + "in-octava-nativitatis-collecta",
        "s01",
        "infinitive",
        ("w023", "merúimus", "mereo", 1, "pl", "perf", "ind"),
        (("w026", "suscípere", "suscipio", "mood", "inf"),),
        (("w023", "byliśmy godni"), ("w024", "Sprawcę"), ("w026", "przyjąć")),
    ),
    (
        "christmas-night-postcommunion",
        P + "nativitas-domini-in-nocte-postcommunio",
        "s01",
        "infinitive",
        ("w022", "mereámur", "mereor", 1, "pl", "pres", "subj"),
        (("w023", "perveníre", "pervenio", "mood", "inf"),),
        (
            (
                ("w020", "w021", "w022", "w023", "w024"),
                "w022",
                "zasłużyli, by dojść do Jego wspólnoty",
            ),
        ),
    ),
    (
        "holy-family-postcommunion",
        P + "sancta-familia-postcommunio",
        "s01",
        "infinitive",
        ("w033", "mereámur", "mereor", 1, "pl", "pres", "subj"),
        (("w032", "récipi", "recipio", "voice", "pass"),),
        (("w032", "na przyjęcie"), ("w033", "zasłużyli")),
    ),
    (
        "anne-collect",
        P + "sanctae-annae-matris-beatae-mariae-virginis-collecta",
        "s01",
        "infinitive",
        ("w016", "mererétur", "mereor", 3, "sg", "impf", "subj"),
        (("w015", "éffici", "efficio", "voice", "pass"), ("w014", "mater", "mater", "case", "nom")),
        (("w014", "matką"), ("w015", "stać się"), ("w016", "była godna")),
    ),
    (
        "anne-postcommunion",
        P + "sanctae-annae-matris-beatae-mariae-virginis-postcommunio",
        "s01",
        "infinitive",
        ("w023", "mereámur", "mereor", 1, "pl", "pres", "subj"),
        (("w022", "perveníre", "pervenio", "mood", "inf"),),
        (("w022", "dojść"), ("w023", "byli godni")),
    ),
    (
        "joachim-postcommunion",
        P + "sancti-ioachim-confessoris-postcommunio",
        "s01",
        "infinitive",
        ("w036", "mereámur", "mereor", 1, "pl", "pres", "subj"),
        (
            ("w035", "esse", "sum", "mood", "inf"),
            ("w034", "partícipes", "particeps", "case", "nom"),
        ),
        (("w034", "uczestnikami"), ("w035", "być"), ("w036", "byli godni")),
    ),
    (
        "joachim-secret",
        P + "sancti-ioachim-confessoris-secreta",
        "s01",
        "infinitive",
        ("w027", "mereámur", "mereor", 1, "pl", "pres", "subj"),
        (("w026", "cónsequi", "consequor", "mood", "inf"),),
        (("w026", "otrzymać"), ("w027", "byli godni"), ("w028", "odpuszczenie")),
    ),
    (
        "philip-james-secret",
        P + "sanctorum-philippi-et-iacobi-apostolorum-secreta",
        "s01",
        "object",
        ("w018", "merémur", "mereor", 1, "pl", "pres", "ind"),
        (("w017", "quæ", "qui", "case", "acc"),),
        (("w017", "na które"), ("w018", "zasługujemy")),
    ),
    (
        "seven-sorrows-communion",
        P + "septem-dolorum-beatae-mariae-virginis-communio",
        "s01",
        "object",
        ("w009", "meruérunt", "mereo", 3, "pl", "perf", "ind"),
        (("w011", "palmam", "palma", "case", "acc"),),
        (("w009", "zasłużyły na"), ("w010", "męczeństwa"), ("w011", "palmę")),
    ),
    (
        "aufer",
        "ordinarium.aufer-a-nobis",
        "s04",
        "infinitive",
        ("w014", "mereámur", "mereor", 1, "pl", "pres", "subj"),
        (("w016", "introíre", "introeo", "mood", "inf"),),
        ((("w013", "w014", "w015"), "w014", "z czystymi umysłami byli godni"), ("w016", "wejść")),
    ),
    (
        "peter-martyr-collect",
        "proprium.sancti-petri-martyris-collecta",
        "s01",
        "infinitive",
        ("w021", "méruit", "mereo", 3, "sg", "perf", "ind"),
        (("w022", "obtinére", "obtineo", "mood", "inf"),),
        ((("w019", "w020", "w021", "w022"), "w021", "zasłużył na otrzymanie palmy męczeństwa"),),
    ),
    (
        "athanasius-collect",
        "proprium.sancti-athanasii-collecta",
        "s01",
        "infinitive",
        ("w020", "méruit", "mereo", 3, "sg", "perf", "ind"),
        (("w021", "famulári", "famulor", "mood", "inf"),),
        ((("w018", "w019", "w020", "w021"), "w020", "zasłużył na to, by godnie Tobie służyć"),),
    ),
    (
        "gregory-nazianzen-collect",
        "proprium.sancti-gregorii-nazianzeni-collecta",
        "s01",
        "infinitive",
        ("w022", "mereámur", "mereor", 1, "pl", "pres", "subj"),
        (("w021", "habére", "habeo", "mood", "inf"),),
        ((("w021", "w022"), "w022", "byli godni mieć"),),
    ),
    (
        "paschal-baylon-collect",
        "proprium.sancti-paschalis-baylon-collecta",
        "s01",
        "infinitive",
        ("w033", "mereámur", "mereor", 1, "pl", "pres", "subj"),
        (("w032", "percípere", "percipio", "mood", "inf"),),
        (
            (
                ("w029", "w030", "w031", "w032", "w033"),
                "w033",
                "tak też my byli godni jej przyjęcia",
            ),
        ),
    ),
    (
        "peter-celestine-collect",
        "proprium.sancti-petri-caelestini-collecta",
        "s01",
        "infinitive",
        ("w031", "mereámur", "mereor", 1, "pl", "pres", "subj"),
        (
            ("w023", "despícere", "despicio", "mood", "inf"),
            ("w029", "perveníre", "pervenio", "mood", "inf"),
        ),
        (("w031", "byli godni"), ("w023", "wzgardzić"), ("w029", "dojść")),
    ),
    (
        "angela-merici-collect",
        "proprium.sanctae-angelae-mericiae-collecta",
        "s01",
        "infinitive",
        ("w028", "mereámur", "mereor", 1, "pl", "pres", "subj"),
        (("w027", "pérfrui", "perfruor", "mood", "inf"),),
        (
            (
                ("w026", "w027", "w028", "w029"),
                "w028",
                "byli godni w pełni cieszyć się wiecznymi radościami",
            ),
        ),
    ),
)

# The same row shape for constructions that were already natural, and the protected formula.
CONTROLS = (
    (
        "regina-caeli",
        "orationes.regina-caeli",
        "s02",
        "protected",
        ("w007", "meruísti", "mereo", 2, "sg", "perf", "ind"),
        (("w008", "portáre", "porto", "mood", "inf"),),
        (("w006", "którego"), ("w007", "zasłużyłaś"), ("w008", "nosić")),
    ),
    (
        "requiem-tract",
        P + "commemoratio-omnium-fidelium-defunctorum-missa-i-tractus",
        "s01",
        "retained",
        ("w015", "mereántur", "mereor", 3, "pl", "pres", "subj"),
        (
            ("w016", "evádere", "evado", "mood", "inf"),
            ("w023", "pérfrui", "perfruor", "mood", "inf"),
        ),
        (
            ("w015", "niech zasłużą"),
            ("w016", "na uniknięcie"),
            (
                ("w020", "w021", "w022", "w023"),
                "w023",
                "na radowanie się szczęściem wiecznej światłości",
            ),
        ),
    ),
    (
        "palm-sunday-collect",
        P + "dominica-ii-passionis-collecta",
        "s01",
        "retained",
        ("w030", "mereámur", "mereor", 1, "pl", "pres", "subj"),
        (
            ("w025", "habére", "habeo", "mood", "inf"),
            ("w029", "consórtia", "consortium", "case", "acc"),
        ),
        (
            (
                ("w022", "w023", "w024", "w025", "w026", "w027", "w028", "w029", "w030"),
                "w030",
                "byli godni zarówno czerpać naukę z Jego cierpliwości, "
                "jak i uczestniczyć w Jego zmartwychwstaniu",
            ),
        ),
    ),
)

LABELS = {
    "infinitive": "Polish mereri",
    "object": "Polish mereri",
    "protected": "protected Regina caeli formula",
    "retained": "retained mereri control",
}

# id, site or control id, realized word or group anchor, wrong value, owned message.
# Each wrong value is the defect of its class at that site: the bare infinitive government
# restored, Polish na dropped, or the Latin person, number or tense lost.
MUTANTS = (
    ("annunciation-secret-bare", "annunciation-secret", "w027", "zasłużyli", "governor"),
    ("assumption-collect-bare", "assumption-collect", "w027", "zasłużyli", "governor"),
    ("assumption-collect-dative", "assumption-collect", "w026", "chwale", "complement"),
    ("queenship-collect-bare", "queenship-collect", "w025", "zasłużyli", "governor"),
    ("queenship-collect-person", "queenship-collect", "w025", "była godna", "governor"),
    ("baptism-collect-bare", "baptism-collect", "w021", "zasłużyli", "governor"),
    ("lateran-secret-bare", "lateran-secret", "w018", "zasłużyli", "governor"),
    ("advent-i-collect-bare", "advent-i-collect", "w017", "zostać wyrwanymi", "complement"),
    ("advent-i-collect-na", "advent-i-collect", "w020", "zbawienie", "complement"),
    ("advent-ii-collect-bare", "advent-ii-collect", "w018", "zasłużyli", "governor"),
    (
        "christmas-octave-sunday-collect-bare",
        "christmas-octave-sunday-collect",
        "w016",
        "zasłużyli",
        "governor",
    ),
    ("pentecost-xiii-collect-bare", "pentecost-xiii-collect", "w013", "zasłużyli", "governor"),
    ("pentecost-xvi-secret-bare", "pentecost-xvi-secret", "w015", "zasłużyli", "governor"),
    ("exaltation-collect-na", "exaltation-collect", "w022", "nagrody", "complement"),
    ("exaltation-secret-bare", "exaltation-secret", "w023", "zasłużyliśmy", "governor"),
    ("exaltation-secret-perfect", "exaltation-secret", "w023", "byli godni", "governor"),
    (
        "christmas-octave-collect-bare",
        "christmas-octave-collect",
        "w023",
        "zasłużyliśmy",
        "governor",
    ),
    (
        "christmas-octave-collect-perfect",
        "christmas-octave-collect",
        "w023",
        "byli godni",
        "governor",
    ),
    (
        "christmas-night-postcommunion-bare",
        "christmas-night-postcommunion",
        "w022",
        "zasłużyli dojść do Jego wspólnoty",
        "governor",
    ),
    (
        "holy-family-postcommunion-bare",
        "holy-family-postcommunion",
        "w032",
        "zostać przyjęci",
        "complement",
    ),
    (
        "holy-family-postcommunion-na",
        "holy-family-postcommunion",
        "w032",
        "przyjęcie",
        "complement",
    ),
    ("anne-collect-bare", "anne-collect", "w016", "zasłużyła", "governor"),
    ("anne-collect-person", "anne-collect", "w016", "byli godni", "governor"),
    ("anne-postcommunion-bare", "anne-postcommunion", "w023", "zasłużyli", "governor"),
    ("joachim-postcommunion-bare", "joachim-postcommunion", "w036", "zasłużyli", "governor"),
    ("joachim-secret-bare", "joachim-secret", "w027", "zasłużyli", "governor"),
    ("philip-james-secret-na", "philip-james-secret", "w017", "które", "complement"),
    ("philip-james-secret-mood", "philip-james-secret", "w018", "zasłużyli", "governor"),
    ("seven-sorrows-communion-na", "seven-sorrows-communion", "w009", "zasłużyły", "governor"),
    (
        "seven-sorrows-communion-number",
        "seven-sorrows-communion",
        "w009",
        "zasłużyła na",
        "governor",
    ),
    ("aufer-bare", "aufer", "w014", "z czystymi umysłami zasłużyli", "governor"),
    ("regina-caeli-worthy", "regina-caeli", "w007", "byłaś godna", "governor"),
    ("requiem-tract-bare", "requiem-tract", "w016", "uniknąć", "complement"),
    (
        "palm-sunday-collect-bare",
        "palm-sunday-collect",
        "w030",
        "zasłużyli zarówno czerpać naukę z Jego cierpliwości, "
        "jak i uczestniczyć w Jego zmartwychwstaniu",
        "governor",
    ),
    (
        "peter-martyr-bare",
        "peter-martyr-collect",
        "w021",
        "zasłużył otrzymać palmę męczeństwa",
        "governor",
    ),
    ("athanasius-bare", "athanasius-collect", "w020", "zasłużył godnie Tobie służyć", "governor"),
    ("gregory-nazianzen-bare", "gregory-nazianzen-collect", "w022", "zasłużyli mieć", "governor"),
    (
        "paschal-baylon-bare",
        "paschal-baylon-collect",
        "w033",
        "tak też my zasłużyli ją przyjąć",
        "governor",
    ),
    ("peter-celestine-bare", "peter-celestine-collect", "w031", "zasłużyli", "governor"),
    (
        "angela-merici-bare",
        "angela-merici-collect",
        "w028",
        "zasłużyli w pełni cieszyć się wiecznymi radościami",
        "governor",
    ),
)

# text, word, Latin forms the Polish note must quote, note.
EXPLANATIONS = (
    (
        P + "dominica-i-adventus-collecta",
        "w015",
        ("mereámur", "éripi", "salvári", "te", "protegénte"),
        "Po „ut” czasownik „mereámur” łączy się z dwoma bezokolicznikami strony biernej, "
        "„éripi” i „salvári”: „abyśmy zasłużyli na wyrwanie … i na zbawienie”. Rozdziela on "
        "słowa „te” i „protegénte”, które razem znaczą „pod Twoją ochroną”.",
    ),
    (
        P + "nativitas-domini-in-nocte-postcommunio",
        "w022",
        ("mereámur", "perveníre", "consórtium"),
        "Po „ut” czasownik „mereámur” łączy się z „perveníre”: „abyśmy zasłużyli, by dojść”. "
        "Oba słowa stoją między „ad eius” a „consórtium”, które razem znaczą „do Jego wspólnoty”.",
    ),
    (
        P + "sancta-familia-postcommunio",
        "w033",
        ("mereámur", "récipi"),
        "Po „ut” czasownik „mereámur” łączy się z bezokolicznikiem strony biernej „récipi”: "
        "„abyśmy zasłużyli na przyjęcie”, czyli na to, byśmy zostali przyjęci do wiecznych "
        "przybytków.",
    ),
)

ROWS = {row[0]: row for row in (*SITES, *CONTROLS)}


def document(text, language=None):
    prefix = ROOT if language is None else ROOT / "languages" / language
    return json.loads(
        (prefix / "texts" / (text.replace(".", "/", 1) + ".json")).read_text(encoding="utf-8")
    )


@pytest.fixture(scope="module")
def documents():
    return {row[1]: (document(row[1]), document(row[1], "pl")) for row in ROWS.values()}


def realization(layer, segment, word):
    groups = [
        group
        for group in layer["segments"][segment].get("alignments", [])
        if word in group["words"]
    ]
    if groups:
        (group,) = groups
        return (tuple(group["words"]), group.get("anchor"), group.get("gloss"))
    return (word, layer["words"][word].get("gloss"))


def members(item):
    return item[0] if isinstance(item[0], tuple) else (item[0],)


def assert_site(core, layer, row):
    _, text, segment_id, kind, verb, complements, expected = row
    label = LABELS[kind]
    assert core["id"] == layer["text"] == text and layer["language"] == "pl"
    (segment,) = [segment for segment in core["segments"] if segment["id"] == segment_id]
    words = {word["id"]: word for word in segment["words"]}
    morph = words[verb[0]]["morph"]
    identity = (
        words[verb[0]]["form"],
        words[verb[0]]["lemma"],
        *(morph.get(key) for key in ("person", "number", "tense", "mood")),
    )
    assert identity == verb[1:], "Latin mereri identity"
    for word, form, lemma, key, value in complements:
        assert (words[word]["form"], words[word]["lemma"], words[word]["morph"].get(key)) == (
            form,
            lemma,
            value,
        ), "Latin mereri identity"
    (governor,) = [item for item in expected if verb[0] in members(item)]
    assert realization(layer, segment_id, verb[0]) == governor, f"{label} governor"
    for item in expected:
        if item is governor:
            continue
        assert realization(layer, segment_id, members(item)[0]) == item, f"{label} complement"
    assert check_alignment(core, layer) == [], "once-only Polish realization"


@pytest.mark.parametrize("row", SITES, ids=[row[0] for row in SITES])
def test_mereri_site_has_natural_polish_government(documents, row):
    assert_site(*documents[row[1]], row)


@pytest.mark.parametrize("row", CONTROLS, ids=[row[0] for row in CONTROLS])
def test_retained_controls_are_unchanged(documents, row):
    assert_site(*documents[row[1]], row)


def test_regina_caeli_formula_stays_protected():
    provenance = json.loads(
        (ROOT / "languages/pl/translation-provenance.json").read_text(encoding="utf-8")
    )
    sites = {site["site"]: site for site in provenance["sites"]}
    assert sites["orationes.regina-caeli.s02.pl"]["familiar_core"] is True
    assert sites["orationes.regina-caeli.s02.pl"]["origin"] == "traditional"
    for row in SITES:
        assert sites[f"{row[1]}.{row[2]}.pl"]["familiar_core"] is False


def set_realization(layer, segment, word, value):
    groups = [
        group
        for group in layer["segments"][segment].get("alignments", [])
        if word in group["words"]
    ]
    if groups:
        (group,) = groups
        previous, group["gloss"] = group["gloss"], value
    else:
        previous, layer["words"][word]["gloss"] = layer["words"][word]["gloss"], value
    return previous


@pytest.mark.parametrize(
    "mutant_id,row_id,word,wrong,part", MUTANTS, ids=[mutant[0] for mutant in MUTANTS]
)
def test_each_defect_fails_its_owned_assertion_and_restores(
    documents, mutant_id, row_id, word, wrong, part
):
    row = ROWS[row_id]
    core, layer = documents[row[1]]
    assert_site(core, layer, row)
    broken = deepcopy(layer)
    previous = set_realization(broken, row[2], word, wrong)
    assert previous != wrong, mutant_id
    with pytest.raises(AssertionError) as caught:
        assert_site(core, broken, row)
    assert str(caught.value).splitlines()[0] == f"{LABELS[row[3]]} {part}"
    set_realization(broken, row[2], word, previous)
    assert broken == layer
    assert_site(core, broken, row)


def test_inventory_covers_every_mereri_occurrence():
    assert [len(SITES), len(CONTROLS), len(MUTANTS)] == [28, 3, 40]
    assert [row[3] for row in SITES].count("infinitive") == 25
    assert [row[3] for row in SITES].count("object") == 3
    adjudicated = {(row[1], row[2], row[4][0]) for row in (*SITES, *CONTROLS)}
    assert len(adjudicated) == 31
    occurrences = set()
    for path in sorted((ROOT / "texts").glob("*/*.json")):
        core = json.loads(path.read_text(encoding="utf-8"))
        for segment in core["segments"]:
            for word in segment.get("words") or []:
                if word["lemma"] in {"mereo", "mereor"}:
                    occurrences.add((core["id"], segment["id"], word["id"]))
    assert occurrences == adjudicated


@pytest.mark.parametrize("text,word,forms,note", EXPLANATIONS, ids=[e[0] for e in EXPLANATIONS])
def test_hidden_infinitive_has_a_local_polish_explanation(text, word, forms, note):
    core, layer = document(text), document(text, "pl")
    requirement = core["localization"]["explanations"][word]
    assert "pl" in requirement.get("languages", ["en", "pl"])
    assert layer["words"][word]["explanation"] == note
    for form in forms:
        assert f"„{form}”" in note
    latin = {w["form"] for segment in core["segments"] for w in segment["words"]}
    assert set(forms) <= latin

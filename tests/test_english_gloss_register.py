"""Contemporary register of English interlinear captions in texts with traditional prose.

The prose of most of these texts keeps an inherited register; their interlinear captions use
contemporary English. A pronoun or possessive of God or Christ reads You/Your, and one
of a human or creaturely addressee (Mary, the angel, Sion, the disciples, the mother of the
sons of Zebedee) reads you/your. A second-person verb whose Latin subject is a relative or an
expressed tu keeps only the verb (who live, You give); one whose subject is only the ending
carries the pronoun (you will receive, You deprive). A third-person present ends in -s, a
perfect reads has + participle. The conclusion and doxology prepositions of in/per saecula
saeculorum read "for", a goal reads "to" or "for", and no caption uses "unto".

Every realization is pinned with the Latin word it renders, the legacy register fixture no
longer lists any corrected field, and the register detector excludes exactly four words that
only look like archaic endings (closest, farthest, furthest, teeth) while still flagging real
archaic forms. One in-memory mutant per diagnostic class must fail that class, and the
restored documents must pass again.
"""

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
import test_english_register as register
from lauda_sion_fixture import TEXT as LAUDA_TEXT
from lauda_sion_fixture import predecessor_core, predecessor_layer
from possessive_sweep_b1_successor_fixture import possessive_b1_caption

from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs
from checks.english import check as check_english

ROOT = Path(__file__).resolve().parents[1]
P = "proprium."

# text: (segment, words, caption, class, Latin lemma, Latin parse) for each realization.
# V3_PHRASE and DUR_PHRASE pin complete grouped conclusions and durations.
# Classes: D divine pronoun/possessive; H human pronoun/possessive; N dative noun; V2 a
# second-person verb with an expressed subject captioned apart; V2D/V2H a second-person verb
# whose caption carries the subject, the ending alone or an expressed subject absorbed into the
# group (divine/human); V3 third-person present; P3 third-person perfect; DUR the preposition
# of in/per saecula saeculorum; GOAL a preposition of goal or purpose; ART a noun whose article
# replaces a supplied possessive.
SITES = {
    "litaniae.lauretanae": (("s133", ("w364", "w365"), "Your servants", "D", "tuus", "acc pl"),),
    "litaniae.sacratissimi-cordis-iesu": (
        ("s042", ("w153",), "dwells", "V3", "habito", "3sg pres ind"),
        ("s052", ("w201",), "You", "D", "tu", "acc sg"),
        ("s074", ("w282",), "You", "D", "tu", "abl sg"),
        ("s076", ("w290",), "You", "D", "tu", "abl sg"),
        ("s087", ("w336", "w337"), "Your Heart", "D", "tuus", "acc sg"),
    ),
    "litaniae.sanctissimi-nominis-iesu": (
        ("s098", ("w254", "w255"), "Your wrath", "D", "tuus", "abl sg"),
        ("s106", ("w279", "w280"), "of Your inspirations", "D", "tuus", "gen pl"),
        ("s108", ("w286", "w287", "w288"), "of Your holy Incarnation", "D", "tuus", "gen sg"),
        ("s110", ("w293", "w294"), "Your nativity", "D", "tuus", "acc sg"),
        ("s112", ("w299", "w300"), "Your infancy", "D", "tuus", "acc sg"),
        ("s114", ("w305", "w306", "w307"), "Your most divine life", "D", "tuus", "acc sg"),
        ("s116", ("w312", "w313"), "Your labors", "D", "tuus", "acc pl"),
        ("s118", ("w318", "w319", "w320", "w321"), "Your agony and Passion", "D", "tuus", "acc sg"),
        (
            "s120",
            ("w326", "w327", "w328", "w329"),
            "Your cross and abandonment",
            "D",
            "tuus",
            "acc sg",
        ),
        ("s122", ("w334", "w335"), "Your sufferings", "D", "tuus", "acc pl"),
        ("s124", ("w340", "w341", "w342", "w343"), "Your death and burial", "D", "tuus", "acc sg"),
        ("s126", ("w348", "w349"), "Your resurrection", "D", "tuus", "acc sg"),
        ("s128", ("w354", "w355"), "Your ascension", "D", "tuus", "acc sg"),
        (
            "s130",
            ("w360", "w361", "w362", "w363"),
            "Your institution of the Most Holy Eucharist",
            "D",
            "tuus",
            "acc sg",
        ),
        ("s132", ("w368", "w369"), "Your joys", "D", "tuus", "acc pl"),
        ("s134", ("w374", "w375"), "Your glory", "D", "tuus", "acc sg"),
        ("s145", ("w417",), "said", "V2", "dico", "2sg perf ind"),
        ("s145", ("w420",), "you will receive", "V2H", "accipio", "2pl fut ind"),
        ("s145", ("w423",), "you will find", "V2H", "invenio", "2pl fut ind"),
        ("s145", ("w427",), "to you", "H", "vos", "dat pl"),
        (
            "s145",
            ("w432", "w433", "w434", "w435"),
            "affection of Your most divine love",
            "D",
            "tuus",
            "gen sg",
        ),
        ("s145", ("w437",), "You", "D", "tu", "acc sg"),
        ("s145", ("w446",), "Your", "D", "tuus", "abl sg"),
        ("s146", ("w450", "w451", "w452"), "of Your holy Name", "D", "tuus", "gen sg"),
        ("s146", ("w464", "w465"), "of Your guidance", "D", "tuus", "abl sg"),
        ("s146", ("w466",), "You deprive", "V2D", "destituo", "2sg pres ind"),
        ("s146", ("w470",), "of Your", "D", "tuus", "gen sg"),
        ("s146", ("w472",), "You establish", "V2D", "instituo", "2sg pres ind"),
        ("s146", ("w474",), "live", "V2", "vivo", "2sg pres ind"),
        ("s146", ("w476",), "reign", "V2", "regno", "2sg pres ind"),
        ("s146", ("w477", "w478", "w479"), "forever and ever", "DUR_PHRASE", "in", "prep acc"),
    ),
    "orationes.angelus-domini": (
        ("s01", ("w004",), "to Mary", "N", "Maria", "dat sg"),
        ("s05", ("w045",), "to me", "H", "ego", "dat sg"),
        ("s05", ("w048",), "your", "H", "tuus", "acc sg"),
        ("s13", ("w133",), "Your", "D", "tuus", "acc sg"),
        ("s13", ("w145",), "Your", "D", "tuus", "gen sg"),
    ),
    "orationes.pater-noster": (
        ("s01", ("w004",), "are", "V2", "sum", "2sg pres ind"),
        ("s02", ("w009",), "Your", "D", "tuus", "nom sg"),
        ("s03", ("w012",), "Your", "D", "tuus", "nom sg"),
        ("s04", ("w015",), "Your", "D", "tuus", "nom sg"),
    ),
    "ordinarium.pater-noster": (
        ("s05", ("w014",), "are", "V2", "sum", "2sg pres ind"),
        ("s06", ("w019",), "Your", "D", "tuus", "nom sg"),
        ("s07", ("w022",), "Your", "D", "tuus", "nom sg"),
        ("s08", ("w025",), "Your", "D", "tuus", "nom sg"),
    ),
    "ordinarium.suscipe-sancte-pater": (
        ("s02", ("w014",), "Your", "D", "tuus", "nom sg"),
        ("s02", ("w016",), "to You", "D", "tu", "dat sg"),
        ("s02", ("w050",), "for", "GOAL", "in", "prep acc"),
        ("s02", ("w048", "w049"), "for salvation", "GOAL", "salus", "acc sg"),
    ),
    P + "assumptio-beatae-mariae-virginis-secreta": (
        ("s01", ("w003",), "You", "D", "tu", "acc sg"),
        ("s01", ("w022",), "You", "D", "tu", "acc sg"),
        ("s01", ("w030", "w031"), "Your Son", "D", "tuus", "acc sg"),
        (
            "s01",
            ("w032", "w033", "w034", "w035", "w036"),
            "who lives and reigns with You",
            "D",
            "tu",
            "abl sg",
        ),
        (
            "s01",
            ("w032", "w033", "w034", "w035", "w036"),
            "who lives and reigns with You",
            "V3_PHRASE",
            "vivo",
            "3sg pres ind",
        ),
        (
            "s01",
            ("w032", "w033", "w034", "w035", "w036"),
            "who lives and reigns with You",
            "V3_PHRASE",
            "regno",
            "3sg pres ind",
        ),
    ),
    P + "corporis-christi-alleluia": (
        ("s02", ("w015",), "eats", "V3", "manduco", "3sg pres ind"),
        ("s02", ("w019",), "drinks", "V3", "bibo", "3sg pres ind"),
        ("s02", ("w024",), "abides", "V3", "maneo", "3sg pres ind"),
    ),
    P + "corporis-christi-collecta": (
        ("s01", ("w007", "w008"), "of Your Passion", "D", "tuus", "gen sg"),
        ("s01", ("w010",), "have left", "V2", "relinquo", "2sg perf ind"),
        ("s01", ("w015", "w016", "w017", "w018"), "of Your Body and Blood", "D", "tuus", "gen sg"),
        ("s01", ("w023", "w024"), "of Your redemption", "D", "tuus", "gen sg"),
        (
            "s01",
            ("w030", "w031", "w032", "w033"),
            "You live and reign",
            "V2_PHRASE",
            "vivo",
            "2sg pres ind",
        ),
        (
            "s01",
            ("w030", "w031", "w032", "w033"),
            "You live and reign",
            "V2_PHRASE",
            "regno",
            "2sg pres ind",
        ),
    ),
    P + "corporis-christi-communio": (
        ("s01", ("w002",), "you eat", "V2H", "manduco", "2pl fut ind"),
        ("s01", ("w007",), "you drink", "V2H", "bibo", "2pl fut ind"),
        ("s01", ("w010",), "you will proclaim", "V2H", "annuntio", "2pl fut ind"),
    ),
    P + "corporis-christi-evangelium": (
        ("s02", ("w020",), "eats", "V3", "manduco", "3sg pres ind"),
        ("s02", ("w024",), "drinks", "V3", "bibo", "3sg pres ind"),
        ("s02", ("w029",), "abides", "V3", "maneo", "3sg pres ind"),
        ("s03", ("w046",), "eats", "V3", "manduco", "3sg pres ind"),
        ("s06", ("w070",), "eats", "V3", "manduco", "3sg pres ind"),
    ),
    P + "corporis-christi-graduale": (
        ("s01", ("w004",), "You", "D", "tu", "abl sg"),
        ("s01", ("w008",), "You", "D", "tu", "nom sg"),
        ("s01", ("w009",), "give", "V2", "do", "2sg pres ind"),
        ("s02", ("w015", "w016"), "You open", "V2D", "aperio", "2sg pres ind"),
        ("s02", ("w017", "w018"), "Your hand", "D", "tuus", "acc sg"),
        ("s02", ("w020",), "fill", "V2", "impleo", "2sg pres ind"),
    ),
    P + "corporis-christi-introitus": (("s03", ("w039",), "for", "DUR", "in", "prep acc"),),
    P + "corporis-christi-postcommunio": (
        ("s01", ("w005", "w006"), "of Your divinity", "D", "tuus", "gen sg"),
        (
            "s01",
            ("w011", "w012", "w013", "w014", "w015"),
            "of Your precious Body and Blood",
            "D",
            "tuus",
            "gen sg",
        ),
        (
            "s01",
            ("w019", "w020", "w021", "w022"),
            "You live and reign",
            "V2_PHRASE",
            "vivo",
            "2sg pres ind",
        ),
        (
            "s01",
            ("w019", "w020", "w021", "w022"),
            "You live and reign",
            "V2_PHRASE",
            "regno",
            "2sg pres ind",
        ),
    ),
    P + "corporis-christi-secreta": (
        ("s01", ("w001", "w002"), "To Your Church", "D", "tuus", "dat sg"),
        ("s01", ("w022", "w023"), "Your Son", "D", "filius", "acc sg"),
        (
            "s01",
            ("w024", "w025", "w026", "w027", "w028"),
            "who lives and reigns with You",
            "D",
            "vivo",
            "3sg pres ind",
        ),
    ),
    P + "corporis-christi-sequentia": (
        ("s01", ("w003",), "the Savior", "ART", "salvator", "acc sg"),
        ("s01", ("w005",), "the Leader", "ART", "dux", "acc sg"),
        ("s02", ("w013",), "you can", "V2H", "possum", "2sg pres ind"),
        (
            "s02",
            ("w020", "w021", "w022"),
            "nor can you praise enough",
            "V2H",
            "sufficio",
            "2sg pres ind",
        ),
        ("s23", ("w254",), "You", "D", "tu", "nom sg"),
        ("s23", ("w259",), "You", "D", "tu", "nom sg"),
        ("s24", ("w267",), "You", "D", "tu", "nom sg"),
        ("s24", ("w270",), "know", "V2", "scio", "2sg pres ind"),
        ("s24", ("w272",), "can do", "V2", "valeo", "2sg pres ind"),
        ("s24", ("w275",), "feed", "V2", "pasco", "2sg pres ind"),
        ("s24", ("w278",), "Your", "D", "tuus", "acc pl"),
        ("s12", ("w118", "w119"), "you do not comprehend", "V2H", "capio", "2sg pres ind"),
        ("s12", ("w121", "w122"), "you do not see", "V2H", "video", "2sg pres ind"),
    ),
    P + "dominica-ii-post-epiphaniam-introitus": (
        ("s01", ("w042",), "for", "DUR", "in", "prep acc"),
    ),
    P + "dominica-ii-post-pentecosten-secreta": (
        ("s01", ("w004", "w005"), "to Your name", "D", "tuus", "dat sg"),
        ("s01", ("w023", "w024"), "Your Son", "D", "tuus", "acc sg"),
        (
            "s01",
            ("w025", "w026", "w027", "w028", "w029"),
            "who lives and reigns with You",
            "D",
            "tu",
            "abl sg",
        ),
        (
            "s01",
            ("w025", "w026", "w027", "w028", "w029"),
            "who lives and reigns with You",
            "V3_PHRASE",
            "vivo",
            "3sg pres ind",
        ),
        (
            "s01",
            ("w025", "w026", "w027", "w028", "w029"),
            "who lives and reigns with You",
            "V3_PHRASE",
            "regno",
            "3sg pres ind",
        ),
    ),
    P + "dominica-iii-post-epiphaniam-introitus": (
        ("s01", ("w038",), "for", "DUR", "in", "prep acc"),
    ),
    P + "pretiosissimi-sanguinis-domini-nostri-iesu-christi-postcommunio": (
        (
            "s01",
            ("w019", "w020", "w021", "w022", "w023"),
            "of water springing up to everlasting life",
            "GOAL",
            "in",
            "prep acc",
        ),
        ("s01", ("w025",), "with You", "D", "tu", "abl sg"),
        ("s01", ("w026",), "lives", "V3", "vivo", "3sg pres ind"),
        ("s01", ("w028",), "reigns", "V3", "regno", "3sg pres ind"),
        ("s01", ("w034",), "for", "DUR", "per", "prep acc"),
    ),
    P + "pretiosissimi-sanguinis-domini-nostri-iesu-christi-tractus": (
        ("s01", ("w001",), "Has graced", "P3", "gratifico", "3sg perf ind"),
        ("s01", ("w022",), "has superabounded", "P3", "superabundo", "3sg perf ind"),
        ("s01", ("w038",), "has set forth", "P3", "propono", "3sg perf ind"),
    ),
    P + "sacratissimi-cordis-iesu-collecta": (
        ("s01", ("w006", "w007"), "of Your Son", "D", "tuus", "gen sg"),
        ("s01", ("w015", "w016"), "are pleased to bestow", "V2", "dignor", "2sg pres ind"),
        ("s01", ("w037", "w038"), "Your Son", "D", "tuus", "acc sg"),
        (
            "s01",
            ("w039", "w040", "w041", "w042", "w043"),
            "who lives and reigns with You",
            "D",
            "tu",
            "abl sg",
        ),
        (
            "s01",
            ("w039", "w040", "w041", "w042", "w043"),
            "who lives and reigns with You",
            "V3_PHRASE",
            "vivo",
            "3sg pres ind",
        ),
        (
            "s01",
            ("w039", "w040", "w041", "w042", "w043"),
            "who lives and reigns with You",
            "V3_PHRASE",
            "regno",
            "3sg pres ind",
        ),
        (
            "s01",
            ("w049", "w050", "w051", "w052"),
            "forever and ever",
            "DUR_PHRASE",
            "per",
            "prep acc",
        ),
    ),
    P + "sacratissimi-cordis-iesu-epistola": (("s06", ("w136",), "to", "GOAL", "in", "prep acc"),),
    P + "sacratissimi-cordis-iesu-introitus": (
        ("s02", ("w024",), "befits", "V3", "decet", "3sg pres ind"),
        ("s03", ("w042",), "for", "DUR", "in", "prep acc"),
    ),
    P + "sacratissimi-cordis-iesu-postcommunio": (
        ("s01", ("w006", "w007"), "Your holy gifts", "D", "tuus", "nom pl"),
        ("s01", ("w010", "w011", "w012"), "of Your most sweet Heart", "D", "tuus", "gen sg"),
        (
            "s01",
            ("w021", "w022", "w023", "w024"),
            "You live and reign",
            "V2_PHRASE",
            "vivo",
            "2sg pres ind",
        ),
        (
            "s01",
            ("w021", "w022", "w023", "w024"),
            "You live and reign",
            "V2_PHRASE",
            "regno",
            "2sg pres ind",
        ),
        (
            "s01",
            ("w033", "w034", "w035", "w036"),
            "forever and ever",
            "DUR_PHRASE",
            "per",
            "prep acc",
        ),
    ),
    P + "sacratissimi-cordis-iesu-secreta": (
        ("s01", ("w007", "w008", "w009"), "of Your beloved Son", "D", "tuus", "gen sg"),
        ("s01", ("w015",), "to You", "D", "tu", "dat sg"),
        ("s01", ("w028", "w029"), "Your Son", "D", "filius", "acc sg"),
        (
            "s01",
            ("w030", "w031", "w032", "w033", "w034"),
            "who lives and reigns with You",
            "D",
            "vivo",
            "3sg pres ind",
        ),
    ),
    P + "sancti-bartholomaei-apostoli-collecta": (
        (
            "s01",
            ("w011", "w012", "w013", "w014"),
            "of Your blessed Apostle Bartholomew",
            "D",
            "tuus",
            "gen sg",
        ),
        ("s01", ("w016",), "bestowed", "V2", "tribuo", "2sg perf ind"),
        ("s01", ("w018", "w019"), "to Your Church", "D", "tuus", "dat sg"),
        ("s01", ("w034", "w035"), "Your Son", "D", "tuus", "acc sg"),
        (
            "s01",
            ("w036", "w037", "w038", "w039", "w040"),
            "who lives and reigns with You",
            "D",
            "tu",
            "abl sg",
        ),
        (
            "s01",
            ("w036", "w037", "w038", "w039", "w040"),
            "who lives and reigns with You",
            "V3_PHRASE",
            "vivo",
            "3sg pres ind",
        ),
        (
            "s01",
            ("w036", "w037", "w038", "w039", "w040"),
            "who lives and reigns with You",
            "V3_PHRASE",
            "regno",
            "3sg pres ind",
        ),
        (
            "s01",
            ("w046", "w047", "w048", "w049"),
            "forever and ever",
            "DUR_PHRASE",
            "per",
            "prep acc",
        ),
    ),
    P + "sancti-iacobi-apostoli-evangelium": (
        ("s01", ("w023",), "do you want", "V2H", "volo", "2sg pres ind"),
        ("s01", ("w035", "w036"), "Your right hand", "D", "tuus", "acc sg"),
        ("s01", ("w042", "w043"), "Your kingdom", "D", "tuus", "abl sg"),
    ),
    P + "sancti-matthiae-apostoli-collecta": (
        ("s01", ("w005", "w006"), "of Your Apostles", "D", "tuus", "gen pl"),
        ("s01", ("w008",), "joined", "V2", "socio", "2sg perf ind"),
        ("s01", ("w014", "w015", "w016", "w017"), "of Your mercy toward us", "D", "tuus", "gen sg"),
        ("s01", ("w026", "w027"), "Your Son", "D", "tuus", "acc sg"),
        (
            "s01",
            ("w028", "w029", "w030", "w031", "w032"),
            "who lives and reigns with You",
            "D",
            "tu",
            "abl sg",
        ),
        (
            "s01",
            ("w028", "w029", "w030", "w031", "w032"),
            "who lives and reigns with You",
            "V3_PHRASE",
            "vivo",
            "3sg pres ind",
        ),
        (
            "s01",
            ("w028", "w029", "w030", "w031", "w032"),
            "who lives and reigns with You",
            "V3_PHRASE",
            "regno",
            "3sg pres ind",
        ),
        (
            "s01",
            ("w038", "w039", "w040", "w041"),
            "forever and ever",
            "DUR_PHRASE",
            "per",
            "prep acc",
        ),
    ),
    P + "sancti-petri-et-pauli-apostolorum-evangelium": (
        ("s01", ("w037",), "Says", "V3", "dico", "3sg pres ind"),
        ("s01", ("w051",), "are", "V2", "sum", "2sg pres ind"),
    ),
    P + "visitatio-beatae-mariae-virginis-offertorium": (
        ("s01", ("w016",), "you remain", "V2H", "permaneo", "2sg pres ind"),
    ),
}

# (text, segment, first word, last word, the captions the reader composes in Latin order).
LINES = (
    (
        P + "corporis-christi-graduale",
        "s02",
        "w015",
        "w023",
        ("You open", "Your hand", "and", "fill", "every", "living creature", "with blessing"),
    ),
    (
        "litaniae.sanctissimi-nominis-iesu",
        "s146",
        "w462",
        "w479",
        (
            "for",
            "never",
            "of Your guidance",
            "You deprive",
            "those whom",
            "in",
            "steadfastness",
            "of Your",
            "love",
            "You establish",
            "who",
            "live",
            "and",
            "reign",
            "forever and ever",
        ),
    ),
    (
        "litaniae.sanctissimi-nominis-iesu",
        "s145",
        "w416",
        "w427",
        (
            "who",
            "said",
            "ask",
            "and",
            "you will receive",
            "seek",
            "and",
            "you will find",
            "knock",
            "and",
            "will be opened",
            "to you",
        ),
    ),
    (
        P + "corporis-christi-communio",
        "s01",
        "w001",
        "w011",
        (
            "As often as",
            "you eat",
            "Bread",
            "this",
            "and",
            "Chalice",
            "you drink",
            "death",
            "of the Lord",
            "you will proclaim",
            "until",
        ),
    ),
    (
        "ordinarium.suscipe-sancte-pater",
        "s02",
        "w043",
        "w052",
        ("that", "me", "and", "them", "may avail", "for salvation", "for", "life", "eternal"),
    ),
    (
        P + "pretiosissimi-sanguinis-domini-nostri-iesu-christi-postcommunio",
        "s01",
        "w018",
        "w037",
        (
            "a fountain",
            "of water springing up to everlasting life",
            "Who",
            "with You",
            "lives",
            "and",
            "reigns",
            "in",
            "the unity",
            "of the Holy Spirit",
            "God",
            "for",
            "all",
            "ages",
            "of ages",
        ),
    ),
    (
        P + "corporis-christi-secreta",
        "s01",
        "w017",
        "w028",
        ("Through", "our Lord", "Jesus Christ", "Your Son", "who lives and reigns with You"),
    ),
    (
        P + "corporis-christi-sequentia",
        "s24",
        "w267",
        "w280",
        (
            "You",
            "who",
            "all things",
            "know",
            "and",
            "can do",
            "who",
            "us",
            "feed",
            "here",
            "mortals",
            "Your",
            "there",
            "table companions",
        ),
    ),
    (
        "orationes.pater-noster",
        "s01",
        "w001",
        "w006",
        ("Our Father", "who", "are", "in", "the heavens"),
    ),
    (
        "orationes.angelus-domini",
        "s05",
        "w044",
        "w048",
        ("be it done", "to me", "according to", "word", "your"),
    ),
)

# Fields whose only detector hits were closest, farthest, furthest or teeth.
FALSE_POSITIVES = ("closest", "farthest", "furthest", "teeth")
FALSE_POSITIVE_FIELDS = (
    (
        P + "annuntiatio-beatae-mariae-virginis-extra-tempus-paschale-introitus",
        ["segments", "s01", "translation"],
    ),
    (
        P + "annuntiatio-beatae-mariae-virginis-extra-tempus-paschale-introitus",
        ["words", "w012", "explanation"],
    ),
    (
        P + "annuntiatio-beatae-mariae-virginis-extra-tempus-paschale-introitus",
        ["words", "w012", "gloss"],
    ),
    (
        P + "annuntiatio-beatae-mariae-virginis-extra-tempus-paschale-introitus",
        ["words", "w061", "explanation"],
    ),
    (
        P + "annuntiatio-beatae-mariae-virginis-extra-tempus-paschale-introitus",
        ["words", "w061", "gloss"],
    ),
    (P + "annuntiatio-beatae-mariae-virginis-introitus", ["segments", "s01", "translation"]),
    (P + "annuntiatio-beatae-mariae-virginis-introitus", ["words", "w012", "explanation"]),
    (P + "annuntiatio-beatae-mariae-virginis-introitus", ["words", "w012", "gloss"]),
    (P + "annuntiatio-beatae-mariae-virginis-introitus", ["words", "w063", "explanation"]),
    (P + "annuntiatio-beatae-mariae-virginis-introitus", ["words", "w063", "gloss"]),
    (P + "annuntiatio-beatae-mariae-virginis-tractus", ["segments", "s01", "translation"]),
    (P + "annuntiatio-beatae-mariae-virginis-tractus", ["words", "w054", "gloss"]),
    (P + "dominica-iii-post-epiphaniam-evangelium", ["segments", "s01", "translation"]),
    (P + "dominica-iii-post-epiphaniam-evangelium", ["words", "w196", "gloss"]),
    (P + "dominica-xix-post-pentecosten-evangelium", ["segments", "s01", "translation"]),
    (P + "dominica-xix-post-pentecosten-evangelium", ["words", "w190", "gloss"]),
    (P + "nativitas-sancti-ioannis-baptistae-epistola", ["segments", "s01", "translation"]),
    (
        P + "sanctae-annae-matris-beatae-mariae-virginis-epistola",
        ["segments", "s01", "translation"],
    ),
    (P + "sanctae-annae-matris-beatae-mariae-virginis-epistola", ["words", "w008", "gloss"]),
    (
        P + "sanctae-annae-matris-beatae-mariae-virginis-evangelium",
        ["segments", "s01", "translation"],
    ),
    (P + "sanctae-annae-matris-beatae-mariae-virginis-evangelium", ["words", "w117", "gloss"]),
    (P + "sancti-stephani-protomartyris-epistola", ["segments", "s01", "translation"]),
    (P + "sancti-stephani-protomartyris-epistola", ["words", "w056", "gloss"]),
)
# Real archaic forms the detector must keep flagging, including one that shares a stem.
GENUINE = ("knowest", "eateth", "liveth", "dwelleth", "closeth", "Thy", "Thee", "art")

DIVINE = re.compile(r"\bYour?\b")
HUMAN = re.compile(r"\b(?:you|your|me)\b")
ANY_YOU = re.compile(r"\byou\b", re.I)


def path_of(text, language=None):
    category, name = text.split(".", 1)
    base = ROOT / ("languages/" + language + "/texts" if language else "texts")
    return base / category / f"{name}.json"


def load(text, language=None):
    value = json.loads(path_of(text, language).read_text(encoding="utf-8"))
    if text == LAUDA_TEXT and language in (None, "en"):
        core = json.loads(path_of(text).read_text(encoding="utf-8"))
        layer = json.loads(path_of(text, "en").read_text(encoding="utf-8"))
        return predecessor_core(core, layer) if language is None else predecessor_layer(core, layer)
    return value


def latin(core):
    return {w["id"]: w for s in core["segments"] for w in s.get("words", [])}


def parse(word):
    m = word["morph"]
    if m.get("pos") == "verb":
        return f"{m.get('person')}{m.get('number')} {m.get('tense')} {m.get('mood')}"
    if m.get("pos") == "prep":
        return f"prep {m.get('governs')}"
    return f"{m.get('case')} {m.get('number')}"


def realization(layer, segment, words):
    """The caption of a word or group and the layer path that holds it."""
    groups = layer["segments"][segment].get("alignments", [])
    for index, group in enumerate(groups):
        if group["words"] == list(words):
            return group.get("gloss", ""), ("segments", segment, "alignments", index, "gloss")
        if set(words) & set(group["words"]):
            return None, None
    if len(words) != 1:
        return None, None
    return layer["words"][words[0]].get("gloss", ""), ("words", words[0], "gloss")


def flagged(value, not_archaic):
    return [m for m in register.ARCHAIC.findall(value or "") if m.lower() not in not_archaic]


def composed(core, layer, segment, first, last):
    words = next(s["words"] for s in core["segments"] if s["id"] == segment)
    ids = [w["id"] for w in words]
    window = ids[ids.index(first) : ids.index(last) + 1]
    groups = {g["words"][0]: g for g in layer["segments"][segment].get("alignments", [])}
    out, i = [], 0
    while i < len(window):
        group = groups.get(window[i])
        if group:
            if group.get("gloss"):
                out.append(group["gloss"])
            i += len(group["words"])
        else:
            out.append(layer["words"][window[i]]["gloss"])
            i += 1
    return tuple(out)


def class_diagnostics(where, caption, kind):
    found = []
    if kind == "D" and (not DIVINE.search(caption) or HUMAN.search(caption)):
        found.append(f"referent:{where}: divine referent needs You/Your, not {caption!r}")
    if kind == "H" and (not HUMAN.search(caption) or DIVINE.search(caption)):
        found.append(f"referent:{where}: human referent needs lowercase, not {caption!r}")
    if kind == "N" and (not caption.startswith("to ") or ANY_YOU.search(caption)):
        found.append(f"referent:{where}: dative noun needs 'to', not {caption!r}")
    if kind == "ART" and (not caption.startswith("the ") or ANY_YOU.search(caption)):
        found.append(f"article:{where}: the article replaces the possessive, not {caption!r}")
    if kind == "V2" and ANY_YOU.search(caption):
        found.append(f"person:{where}: the Latin subject is expressed, not {caption!r}")
    if kind in ("V2D", "V2H"):
        if not ANY_YOU.search(caption):
            found.append(f"person:{where}: the subject is only the ending, {caption!r}")
        elif kind == "V2D" and not re.search(r"\bYou\b", caption):
            found.append(f"referent:{where}: divine subject needs You, not {caption!r}")
        elif kind == "V2H" and not re.search(r"\byou\b", caption):
            found.append(f"referent:{where}: human subject needs you, not {caption!r}")
    if kind == "V3" and not re.search(r"\w+s$", caption):
        found.append(f"person:{where}: third-person present needs -s, not {caption!r}")
    if kind == "P3" and not caption.lower().startswith("has "):
        found.append(f"person:{where}: third-person perfect needs has, not {caption!r}")
    if kind == "DUR" and caption != "for":
        found.append(f"preposition:{where}: in/per saecula saeculorum reads for, not {caption!r}")
    if kind == "V2_PHRASE" and caption != "You live and reign":
        found.append(f"conclusion-address:{where}: direct divine address {caption!r}")
    if kind == "V3_PHRASE" and caption != "who lives and reigns with You":
        found.append(f"conclusion-person:{where}: third-person conclusion {caption!r}")
    if kind == "DUR_PHRASE" and caption != "forever and ever":
        found.append(f"duration-phrase:{where}: complete duration needs forever and ever")
    if kind == "GOAL":
        allowed = ("to", "for", "for salvation")
        if where == (
            P + "pretiosissimi-sanguinis-domini-nostri-iesu-christi-postcommunio"
            ":s01:w019+w020+w021+w022+w023"
        ):
            allowed = ("of water springing up to everlasting life",)
        if caption not in allowed:
            found.append(f"preposition:{where}: unsupported goal realization {caption!r}")
    return found


def diagnostics(text, core, layer):
    """Class-tagged departures from the pinned contemporary realizations of one text."""
    found = []
    words = latin(core)
    for segment, ids, caption, kind, lemma, analysis in SITES.get(text, ()):
        ids, caption = possessive_b1_caption("en", text, ids, caption)
        where = f"{text}:{segment}:{'+'.join(ids)}"
        anchor = next((w for w in ids if words.get(w, {}).get("lemma") == lemma), None)
        if anchor is None or parse(words[anchor]) != analysis:
            found.append(f"latin:{where}: expected {lemma} {analysis}")
        actual, _ = realization(layer, segment, ids)
        if actual != caption:
            found.append(f"caption:{where}: {actual!r}")
        if actual is None:
            continue
        if flagged(actual, register.NOT_ARCHAIC) or "Ghost" in actual:
            found.append(f"register:{where}: {actual!r}")
        found += class_diagnostics(where, actual, kind)
    for line_text, segment, first, last, expected in LINES:
        if line_text == text:
            line = composed(core, layer, segment, first, last)
            if line != expected:
                found.append(f"line:{text}:{segment}: {line}")
    return found


def fixture_diagnostics(payload):
    """No corrected field and no false-positive-only field may remain a legacy allowance."""
    listed = {
        (record["text"], tuple(field["path"]))
        for record in payload["records"]
        for field in record["fields"]
    }
    found = []
    for text, rows in SITES.items():
        layer = load(text, "en")
        for segment, ids, _, _, _, _ in rows:
            _, path = realization(layer, segment, ids)
            if (text, path) in listed:
                found.append(f"fixture:{text}:{path}: corrected field still listed")
    for text, path in FALSE_POSITIVE_FIELDS:
        if (text, tuple(path)) in listed:
            found.append(f"fixture:{text}:{path}: false-positive field still listed")
    return found


def field(text, path):
    value = load(text, "en")
    for key in path:
        value = value[key]
    return value


def precision_diagnostics(not_archaic):
    """The detector excludes exactly the four false positives and still sees real forms."""
    found = []
    for word in FALSE_POSITIVES:
        if flagged(word, not_archaic):
            found.append(f"precision:{word}: still flagged")
    for word in GENUINE:
        if not flagged(word, not_archaic):
            found.append(f"precision:{word}: real archaic form not flagged")
    for text, path in FALSE_POSITIVE_FIELDS:
        value = field(text, path)
        if not any(re.search(rf"\b{w}\b", value, re.I) for w in FALSE_POSITIVES):
            found.append(f"precision:{text}:{path}: no false positive left to exclude")
        if flagged(value, not_archaic):
            found.append(f"precision:{text}:{path}: {flagged(value, not_archaic)}")
    return found


TEXTS = sorted(SITES)


@pytest.mark.parametrize("text", TEXTS)
def test_pinned_contemporary_realizations(text):
    assert diagnostics(text, load(text), load(text, "en")) == []


@pytest.mark.parametrize("text", TEXTS)
def test_touched_layers_pass_the_product_validators(text):
    core, layer = load(text), load(text, "en")
    doc, enriched = expand_core(core), enrich_layer(core, layer)
    assert interlinear.check(doc, enriched) == []
    assert check_english(doc, enriched) == []
    assert language_packs.check_core(core) == []
    assert language_packs.check_layer(core, layer, path_of(text, "en")) == []


def test_corrected_fields_left_the_legacy_register_fixture():
    assert fixture_diagnostics(register.LEGACY_PAYLOAD) == []


def test_register_detector_excludes_exactly_the_four_false_positives():
    assert set(FALSE_POSITIVES) <= register.NOT_ARCHAIC
    assert precision_diagnostics(register.NOT_ARCHAIC) == []


def set_caption(segment, ids, value):
    def mutate(core, layer):
        for group in layer["segments"][segment].get("alignments", []):
            if group["words"] == list(ids):
                group["gloss"] = value
                return
        layer["words"][ids[0]]["gloss"] = value

    return mutate


def set_person(word, person):
    def mutate(core, layer):
        latin(core)[word]["morph"]["person"] = person

    return mutate


LITANY = "litaniae.sanctissimi-nominis-iesu"
GRADUALE = P + "corporis-christi-graduale"
MUTANTS = {
    "caption": (
        P + "sancti-bartholomaei-apostoli-collecta",
        set_caption("s01", ("w016",), "granted"),
    ),
    "referent": (
        "orationes.pater-noster",
        set_caption("s02", ("w009",), "your"),
    ),
    "person": (LITANY, set_caption("s146", ("w466",), "forsake")),
    "article": (
        P + "corporis-christi-sequentia",
        set_caption("s01", ("w003",), "your Savior"),
    ),
    "preposition": (
        P + "corporis-christi-introitus",
        set_caption("s03", ("w039",), "to"),
    ),
    "register": (LITANY, set_caption("s146", ("w474",), "livest")),
    "latin": (LITANY, set_person("w466", 3)),
    "line": (GRADUALE, set_caption("s02", ("w022",), "living creatures")),
    "conclusion-address": (
        P + "corporis-christi-collecta",
        set_caption("s01", ("w030", "w031", "w032", "w033"), "who live and reign"),
    ),
    "conclusion-person": (
        P + "assumptio-beatae-mariae-virginis-secreta",
        set_caption(
            "s01",
            ("w032", "w033", "w034", "w035", "w036"),
            "who live and reign with You",
        ),
    ),
    "duration-phrase": (
        P + "sacratissimi-cordis-iesu-collecta",
        set_caption("s01", ("w049", "w050", "w051", "w052"), "forever"),
    ),
}


@pytest.mark.parametrize("kind", sorted(MUTANTS))
def test_mutant_fails_its_class_and_restores(kind):
    text, mutate = MUTANTS[kind]
    core, layer = load(text), load(text, "en")
    originals = deepcopy(core), deepcopy(layer)
    assert diagnostics(text, core, layer) == []
    try:
        mutate(core, layer)
        assert json.dumps((core, layer), sort_keys=True) != json.dumps(originals, sort_keys=True), (
            "mutation must change its copy"
        )
        found = diagnostics(text, core, layer)
        assert any(item.startswith(kind + ":") for item in found), found
        assert {item.split(":", 1)[0] for item in found} <= {kind, "caption", "line"}, found
        if kind == "line":
            assert {item.split(":", 1)[0] for item in found} == {"line"}, found
        if kind == "line":
            assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
    finally:
        core.clear()
        core.update(originals[0])
        layer.clear()
        layer.update(originals[1])
        assert diagnostics(text, core, layer) == []


@pytest.mark.parametrize(
    "text,path",
    [
        (LITANY, ["words", "w466", "gloss"]),
        (P + "corporis-christi-secreta", ["segments", "s01", "alignments", 6, "gloss"]),
        (P + "sancti-stephani-protomartyris-epistola", ["words", "w056", "gloss"]),
    ],
)
def test_fixture_mutant_fails_and_restores(text, path):
    payload = deepcopy(register.LEGACY_PAYLOAD)
    assert fixture_diagnostics(payload) == []
    payload["records"].append({"text": text, "fields": [{"path": path, "sha256": "0" * 64}]})
    found = fixture_diagnostics(payload)
    assert found and all(item.startswith(f"fixture:{text}:") for item in found), found
    payload["records"].pop()
    assert fixture_diagnostics(payload) == []


@pytest.mark.parametrize(
    "change",
    [
        ("remove", "teeth"),
        ("remove", "closest"),
        ("add", "knowest"),
        ("add", "thy"),
    ],
)
def test_precision_mutant_fails_and_restores(change):
    action, word = change
    allowed = set(register.NOT_ARCHAIC)
    assert precision_diagnostics(allowed) == []
    if action == "remove":
        allowed.discard(word)
    else:
        allowed.add(word)
    found = precision_diagnostics(allowed)
    assert found and all(item.startswith("precision:") for item in found), found
    assert any(word.lower() in item.lower() for item in found), found
    assert precision_diagnostics(set(register.NOT_ARCHAIC)) == []

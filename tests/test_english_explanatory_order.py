"""Contextual explanatory constructions; no universal ban on direct English for."""

from functools import cache
from pathlib import Path

import pytest

from build_reader import store
from checks import english, interlinear, interlinear_quality, lint

ROOT = Path(__file__).resolve().parents[1]

TEXTS = [
    "orationes.magnificat",
    "ordinarium.praefatio-defunctorum",
    "ordinarium.praefatio-paschalis-in-die",
    "ordinarium.praefatio-paschalis-in-nocte",
    "ordinarium.praefatio-sanctissimae-trinitatis",
    "ordinarium.qui-pridie",
    "ordinarium.simili-modo",
    "proprium.annuntiatio-beatae-mariae-virginis-evangelium",
    "proprium.assumptio-beatae-mariae-virginis-evangelium",
    "proprium.beata-maria-virgo-regina-evangelium",
    "proprium.beatae-mariae-virginis-a-rosario-evangelium",
    "proprium.commemoratio-omnium-fidelium-defunctorum-missa-i-epistola",
    "proprium.commemoratio-omnium-fidelium-defunctorum-missa-i-evangelium",
    "proprium.commemoratio-omnium-fidelium-defunctorum-missa-ii-epistola",
    "proprium.commemoratio-omnium-fidelium-defunctorum-missa-iii-epistola",
    "proprium.corporis-christi-epistola",
    "proprium.corporis-christi-sequentia",
    "proprium.dedicatio-archibasilicae-sanctissimi-salvatoris-evangelium",
    "proprium.dedicatio-sancti-michaelis-archangeli-epistola",
    "proprium.dedicatio-sancti-michaelis-archangeli-evangelium",
    "proprium.dominica-i-adventus-epistola",
    "proprium.dominica-i-in-quadragesima-epistola",
    "proprium.dominica-i-in-quadragesima-evangelium",
    "proprium.dominica-i-passionis-epistola",
    "proprium.dominica-i-post-epiphaniam-epistola",
    "proprium.dominica-ii-adventus-epistola",
    "proprium.dominica-ii-adventus-evangelium",
    "proprium.dominica-ii-in-quadragesima-epistola",
    "proprium.dominica-ii-passionis-evangelium",
    "proprium.dominica-ii-post-pascha-epistola",
    "proprium.dominica-iii-adventus-introitus",
    "proprium.dominica-iii-in-quadragesima-epistola",
    "proprium.dominica-iii-post-epiphaniam-epistola",
    "proprium.dominica-iii-post-pascha-epistola",
    "proprium.dominica-in-quinquagesima-epistola",
    "proprium.dominica-in-quinquagesima-evangelium",
    "proprium.dominica-in-septuagesima-epistola",
    "proprium.dominica-in-septuagesima-evangelium",
    "proprium.dominica-in-sexagesima-epistola",
    "proprium.dominica-infra-octavam-nativitatis-communio",
    "proprium.dominica-iv-adventus-epistola",
    "proprium.dominica-iv-in-quadragesima-communio",
    "proprium.dominica-iv-in-quadragesima-epistola",
    "proprium.dominica-iv-in-quadragesima-evangelium",
    "proprium.dominica-iv-post-epiphaniam-epistola",
    "proprium.dominica-iv-post-pascha-epistola",
    "proprium.dominica-iv-post-pascha-evangelium",
    "proprium.dominica-iv-post-pentecosten-epistola",
    "proprium.dominica-iv-post-pentecosten-evangelium",
    "proprium.dominica-pentecostes-evangelium",
    "proprium.dominica-v-post-pascha-epistola",
    "proprium.dominica-v-post-pascha-evangelium",
    "proprium.dominica-v-post-pentecosten-epistola",
    "proprium.dominica-vi-post-epiphaniam-epistola",
    "proprium.dominica-vi-post-pentecosten-epistola",
    "proprium.dominica-vi-post-pentecosten-evangelium",
    "proprium.dominica-vii-post-pentecosten-epistola",
    "proprium.dominica-viii-post-pentecosten-epistola",
    "proprium.dominica-viii-post-pentecosten-evangelium",
    "proprium.dominica-xi-post-pentecosten-epistola",
    "proprium.dominica-xii-post-pentecosten-epistola",
    "proprium.dominica-xii-post-pentecosten-evangelium",
    "proprium.dominica-xiii-post-pentecosten-epistola",
    "proprium.dominica-xiv-post-pentecosten-epistola",
    "proprium.dominica-xiv-post-pentecosten-evangelium",
    "proprium.dominica-xix-post-pentecosten-evangelium",
    "proprium.dominica-xv-post-pentecosten-epistola",
    "proprium.dominica-xx-post-pentecosten-evangelium",
    "proprium.dominica-xxi-post-pentecosten-introitus",
    "proprium.dominica-xxii-post-pentecosten-epistola",
    "proprium.dominica-xxii-post-pentecosten-evangelium",
    "proprium.dominica-xxiii-post-pentecosten-epistola",
    "proprium.dominica-xxiii-post-pentecosten-evangelium",
    "proprium.dominica-xxiv-post-pentecosten-evangelium",
    "proprium.epiphania-domini-evangelium",
    "proprium.exaltatio-sanctae-crucis-epistola",
    "proprium.feria-v-in-cena-domini-epistola",
    "proprium.feria-v-in-cena-domini-evangelium",
    "proprium.immaculatum-cor-beatae-mariae-virginis-epistola",
    "proprium.nativitas-domini-in-die-epistola",
    "proprium.nativitas-domini-in-nocte-evangelium",
    "proprium.nativitas-sancti-ioannis-baptistae-communio",
    "proprium.pretiosissimi-sanguinis-domini-nostri-iesu-christi-epistola",
    "proprium.pretiosissimi-sanguinis-domini-nostri-iesu-christi-evangelium",
    "proprium.purificatio-beatae-mariae-virginis-epistola",
    "proprium.sacratissimi-cordis-iesu-evangelium",
    "proprium.sanctae-annae-matris-beatae-mariae-virginis-epistola",
    "proprium.sancti-andreae-apostoli-epistola",
    "proprium.sancti-andreae-apostoli-evangelium",
    "proprium.sancti-ioachim-confessoris-epistola",
    "proprium.sancti-ioseph-sponsi-beatae-mariae-virginis-communio",
    "proprium.sancti-ioseph-sponsi-beatae-mariae-virginis-epistola",
    "proprium.sancti-ioseph-sponsi-beatae-mariae-virginis-extra-tempus-paschale-communio",
    "proprium.sancti-laurentii-martyris-epistola",
    "proprium.sancti-lucae-evangelistae-epistola",
    "proprium.sancti-lucae-evangelistae-evangelium",
    "proprium.sancti-matthaei-apostoli-et-evangelistae-evangelium",
    "proprium.sancti-matthiae-apostoli-epistola",
    "proprium.sancti-matthiae-apostoli-evangelium",
    "proprium.sancti-stephani-protomartyris-evangelium",
    "proprium.sanctissimae-trinitatis-epistola",
    "proprium.sanctissimi-nominis-iesu-epistola",
    "proprium.sanctorum-innocentium-martyrum-epistola",
    "proprium.sanctorum-innocentium-martyrum-evangelium",
    "proprium.transfiguratio-domini-epistola",
    "proprium.vigilia-nativitatis-evangelium",
    "proprium.vigilia-paschalis-epistola",
    "proprium.vigilia-paschalis-evangelium",
    "proprium.visitatio-beatae-mariae-virginis-epistola",
    "proprium.visitatio-beatae-mariae-virginis-evangelium",
]

CONSTRUCTIONS = [
    (TEXTS[0], "s03", "w019", ["w018", "w019"], "w018", "for behold"),
    (TEXTS[1], "s05", "w045", ["w044", "w045", "w046"], "w046", "For to Your faithful"),
    (TEXTS[2], "s01", "w028", ["w027", "w028"], "w027", "For He Himself"),
    (TEXTS[3], "s01", "w028", ["w027", "w028"], "w027", "For He Himself"),
    (TEXTS[4], "s05", "w047", ["w046", "w047"], "w046", "For what"),
    (TEXTS[5], "s11", "w041", ["w039", "w040", "w041"], "w040", "For this is"),
    (TEXTS[6], "s11", "w034", ["w032", "w033", "w034"], "w033", "For this is"),
    (TEXTS[7], "s01", "w068", ["w067", "w068"], "w067", "for you have found"),
    (TEXTS[8], "s01", "w036", ["w035", "w036"], "w035", "For behold"),
    (TEXTS[8], "s01", "w087", ["w086", "w087"], "w086", "for behold"),
    (TEXTS[9], "s01", "w068", ["w067", "w068"], "w067", "for you have found"),
    (TEXTS[10], "s01", "w068", ["w067", "w068"], "w067", "for you have found"),
    (TEXTS[12], "s01", "w029", ["w028", "w029"], "w028", "For as"),
    (TEXTS[13], "s01", "w027", ["w026", "w027"], "w026", "for unless"),
    (TEXTS[15], "s01", "w003", ["w002", "w003"], "w002", "For I"),
    (TEXTS[15], "s03", "w064", ["w063", "w064"], "w063", "For as often as"),
    (TEXTS[15], "s06", "w107", ["w106", "w107"], "w106", "For he who"),
    (TEXTS[16], "s06", "w055", ["w054", "w055", "w056"], "w054", "For a solemn day"),
    (TEXTS[17], "s01", "w130", ["w129", "w130", "w131", "w132"], "w129", "For the Son of Man came"),
    (TEXTS[18], "s01", "w045", ["w044", "w045", "w046", "w047"], "w047", "for the time is near"),
    (
        TEXTS[19],
        "s01",
        "w097",
        ["w095", "w096", "w097", "w098", "w099", "w100"],
        "w095",
        "For occasions of sin must come",
    ),
    (TEXTS[19], "s01", "w181", ["w180", "w181"], "w180", "for I say"),
    (TEXTS[20], "s02", "w012", ["w011", "w012"], "w011", "For now"),
    (TEXTS[21], "s01", "w011", ["w010", "w011"], "w010", "For He says"),
    (TEXTS[22], "s01", "w085", ["w083", "w084", "w085"], "w083", "For it is written"),
    (TEXTS[22], "s01", "w151", ["w149", "w150", "w151"], "w149", "for it is written"),
    (TEXTS[23], "s01", "w037", ["w036", "w037"], "w036", "For if"),
    (TEXTS[24], "s01", "w042", ["w041", "w042"], "w041", "For I say"),
    (TEXTS[24], "s01", "w072", ["w071", "w072"], "w071", "For as"),
    (TEXTS[25], "s04", "w057", ["w056", "w057"], "w056", "For I say"),
    (TEXTS[26], "s09", "w106", ["w104", "w105", "w106"], "w105", "For this is he"),
    (TEXTS[27], "s01", "w028", ["w027", "w028"], "w027", "For you know"),
    (TEXTS[27], "s01", "w038", ["w036", "w037", "w038"], "w037", "For this is"),
    (
        TEXTS[27],
        "s01",
        "w093",
        ["w092", "w093", "w094", "w095", "w096"],
        "w094",
        "For God has not called us",
    ),
    (TEXTS[28], "s11", "w139", ["w138", "w139", "w140", "w141"], "w138", "for their eyes were"),
    (TEXTS[28], "s60", "w907", ["w906", "w907"], "w906", "for many things"),
    (TEXTS[28], "s82", "w1252", ["w1251", "w1252"], "w1251", "for He said"),
    (TEXTS[29], "s01", "w059", ["w058", "w059"], "w058", "For you were"),
    (TEXTS[30], "s01", "w015", ["w014", "w015"], "w014", "for the Lord"),
    (TEXTS[30], "s05", "w071", ["w070", "w071"], "w070", "for the Lord"),
    (TEXTS[31], "s01", "w059", ["w058", "w059", "w060"], "w060", "For know this"),
    (TEXTS[31], "s01", "w088", ["w086", "w087", "w088"], "w086", "for because of these things"),
    (TEXTS[31], "s01", "w101", ["w100", "w101"], "w100", "For you were"),
    (TEXTS[31], "s01", "w114", ["w113", "w114"], "w113", "for the fruit"),
    (TEXTS[32], "s01", "w045", ["w043", "w044", "w045"], "w043", "For it is written"),
    (TEXTS[32], "s01", "w065", ["w064", "w065", "w066"], "w066", "for in doing this"),
    (TEXTS[33], "s01", "w117", ["w115", "w116", "w117"], "w116", "For this is"),
    (TEXTS[34], "s01", "w125", ["w123", "w124", "w125"], "w123", "For in part"),
    (TEXTS[35], "s01", "w025", ["w024", "w025"], "w024", "For He will be delivered"),
    (TEXTS[36], "s01", "w071", ["w070", "w071"], "w070", "For I do not want"),
    (TEXTS[37], "s01", "w235", ["w234", "w235"], "w234", "For many"),
    (TEXTS[38], "s01", "w010", ["w009", "w010"], "w009", "For you bear it"),
    (TEXTS[38], "s01", "w311", ["w310", "w311"], "w310", "for the truth"),
    (
        TEXTS[39],
        "s01",
        "w013",
        ["w011", "w012", "w013", "w014", "w015", "w016", "w017"],
        "w011",
        "for those who sought the Child’s life have died",
    ),
    (
        TEXTS[40],
        "s04",
        "w040",
        ["w039", "w040", "w041", "w042", "w043"],
        "w042",
        "For I am conscious of nothing against myself",
    ),
    (TEXTS[41], "s01", "w012", ["w011", "w012"], "w011", "for there"),
    (TEXTS[42], "s01", "w036", ["w035", "w036"], "w035", "For these"),
    (TEXTS[42], "s01", "w052", ["w051", "w052", "w053"], "w053", "for Mount Sinai"),
    (TEXTS[42], "s01", "w084", ["w082", "w083", "w084"], "w082", "For it is written"),
    (
        TEXTS[42],
        "s01",
        "w141",
        ["w140", "w141", "w142", "w143", "w144", "w145"],
        "w142",
        "for the son of the bondwoman will not be an heir",
    ),
    (TEXTS[43], "s01", "w072", ["w071", "w072"], "w071", "for He Himself"),
    (TEXTS[44], "s01", "w010", ["w009", "w010"], "w009", "for he who"),
    (TEXTS[45], "s01", "w024", ["w023", "w024"], "w023", "For of His own will"),
    (TEXTS[45], "s01", "w055", ["w054", "w055"], "w054", "For the anger"),
    (TEXTS[46], "s01", "w043", ["w042", "w043"], "w042", "for if"),
    (TEXTS[46], "s01", "w123", ["w122", "w123", "w124"], "w124", "For He will not speak"),
    (TEXTS[47], "s01", "w025", ["w024", "w025"], "w024", "For to emptiness"),
    (TEXTS[47], "s01", "w053", ["w052", "w053"], "w052", "For we know"),
    (TEXTS[48], "s01", "w140", ["w139", "w140"], "w139", "For amazement"),
    (
        TEXTS[49],
        "s01",
        "w139",
        ["w138", "w139", "w140", "w141", "w142"],
        "w138",
        "For the ruler of this world is coming",
    ),
    (TEXTS[50], "s01", "w030", ["w029", "w030"], "w029", "for he beheld"),
    (TEXTS[52], "s01", "w036", ["w035", "w036"], "w035", "For he who"),
    (TEXTS[53], "s01", "w105", ["w103", "w104", "w105"], "w103", "For from you"),
    (TEXTS[53], "s01", "w139", ["w138", "w139"], "w138", "For they themselves"),
    (TEXTS[55], "s01", "w043", ["w042", "w043"], "w042", "for some"),
    (TEXTS[56], "s01", "w009", ["w008", "w009"], "w008", "for as"),
    (TEXTS[56], "s01", "w029", ["w028", "w029"], "w028", "For when"),
    (TEXTS[56], "s01", "w071", ["w070", "w071"], "w070", "For the wages"),
    (TEXTS[57], "s01", "w011", ["w010", "w011"], "w010", "For if"),
    (TEXTS[57], "s01", "w024", ["w023", "w024"], "w023", "For all who"),
    (TEXTS[57], "s01", "w033", ["w032", "w033", "w034"], "w034", "For you did not receive"),
    (TEXTS[57], "s01", "w051", ["w050", "w051", "w052"], "w052", "For the Spirit Himself"),
    (
        TEXTS[58],
        "s01",
        "w043",
        ["w042", "w043", "w044", "w045"],
        "w045",
        "for you will no longer be able",
    ),
    (TEXTS[59], "s01", "w030", ["w029", "w030"], "w029", "For I delivered"),
    (TEXTS[59], "s01", "w100", ["w099", "w100"], "w099", "For I"),
    (TEXTS[60], "s01", "w039", ["w038", "w039"], "w038", "for the letter"),
    (TEXTS[61], "s01", "w016", ["w015", "w016"], "w015", "For I say"),
    (TEXTS[62], "s01", "w097", ["w096", "w097"], "w096", "For if"),
    (TEXTS[63], "s01", "w010", ["w009", "w010"], "w009", "For the flesh"),
    (TEXTS[63], "s01", "w019", ["w018", "w019"], "w018", "for these things"),
    (TEXTS[64], "s01", "w014", ["w013", "w014"], "w013", "for either"),
    (TEXTS[64], "s01", "w159", ["w158", "w159", "w160"], "w158", "For all these things"),
    (TEXTS[64], "s01", "w164", ["w163", "w164", "w165", "w166"], "w163", "For your Father knows"),
    (TEXTS[65], "s01", "w192", ["w191", "w192"], "w191", "For many"),
    (TEXTS[66], "s01", "w080", ["w079", "w080"], "w079", "For each one"),
    (TEXTS[66], "s01", "w103", ["w102", "w103"], "w102", "For what"),
    (TEXTS[66], "s01", "w136", ["w135", "w136", "w137"], "w135", "for at the appointed time"),
    (TEXTS[67], "s01", "w034", ["w033", "w034"], "w033", "for he was beginning"),
    (TEXTS[68], "s01", "w017", ["w016", "w017", "w018"], "w018", "for You have made"),
    (TEXTS[68], "s01", "w078", ["w077", "w078", "w079"], "w079", "for You have made"),
    (
        TEXTS[69],
        "s01",
        "w051",
        ["w050", "w051", "w052", "w053", "w054"],
        "w050",
        "For God is my witness",
    ),
    (TEXTS[70], "s01", "w040", ["w039", "w040", "w041"], "w041", "for You do not regard"),
    (TEXTS[71], "s01", "w016", ["w015", "w016"], "w015", "For many"),
    (TEXTS[72], "s01", "w056", ["w055", "w056"], "w055", "For she was saying"),
    (
        TEXTS[72],
        "s01",
        "w105",
        ["w103", "w104", "w105", "w106", "w107"],
        "w106",
        "for the girl is not dead",
    ),
    (TEXTS[73], "s01", "w073", ["w072", "w073"], "w072", "For there will be"),
    (
        TEXTS[73],
        "s01",
        "w118",
        ["w117", "w118", "w119", "w120", "w121"],
        "w117",
        "For false christs and false prophets will arise",
    ),
    (TEXTS[73], "s01", "w157", ["w156", "w157"], "w156", "For as"),
    (TEXTS[74], "s01", "w027", ["w026", "w027"], "w026", "For we have seen"),
    (TEXTS[74], "s01", "w069", ["w068", "w069"], "w068", "for thus"),
    (TEXTS[74], "s01", "w087", ["w085", "w086", "w087"], "w085", "for from you"),
    (TEXTS[75], "s01", "w003", ["w002", "w003", "w004"], "w004", "For have this in mind"),
    (TEXTS[76], "s01", "w013", ["w012", "w013"], "w012", "For each one"),
    (TEXTS[76], "s01", "w055", ["w054", "w055"], "w054", "For I"),
    (TEXTS[76], "s01", "w116", ["w115", "w116"], "w115", "For as often as"),
    (TEXTS[76], "s01", "w159", ["w158", "w159"], "w158", "For he who"),
    (TEXTS[77], "s01", "w176", ["w175", "w176"], "w175", "For He knew"),
    (TEXTS[77], "s01", "w234", ["w233", "w234"], "w233", "For an example"),
    (TEXTS[78], "s01", "w052", ["w051", "w052", "w053"], "w051", "For my spirit"),
    (TEXTS[79], "s01", "w061", ["w060", "w061"], "w060", "For to which"),
    (TEXTS[80], "s01", "w133", ["w132", "w133"], "w132", "for behold"),
    (TEXTS[81], "s01", "w007", ["w006", "w007"], "w006", "for you will go ahead"),
    (TEXTS[82], "s01", "w037", ["w036", "w037"], "w036", "For if"),
    (
        TEXTS[83],
        "s01",
        "w029",
        ["w028", "w029", "w030", "w031", "w032", "w033"],
        "w028",
        "for that Sabbath day was great",
    ),
    (TEXTS[84], "s01", "w051", ["w050", "w051"], "w050", "For He Himself is"),
    (
        TEXTS[85],
        "s01",
        "w016",
        ["w015", "w016", "w017", "w018", "w019", "w020"],
        "w015",
        "for that Sabbath day was great",
    ),
    (
        TEXTS[85],
        "s05",
        "w093",
        ["w091", "w092", "w093", "w094"],
        "w091",
        "For these things were done",
    ),
    (TEXTS[86], "s01", "w125", ["w124", "w125"], "w124", "for all"),
    (TEXTS[89], "s01", "w027", ["w026", "w027"], "w026", "for he has done"),
    (TEXTS[90], "s01", "w011", ["w010", "w011"], "w010", "for that which"),
    (TEXTS[91], "s01", "w059", ["w058", "w059"], "w058", "For He heard"),
    (TEXTS[92], "s01", "w011", ["w010", "w011"], "w010", "for that which"),
    (
        TEXTS[93],
        "s01",
        "w030",
        ["w029", "w030", "w031", "w032", "w033"],
        "w032",
        "for God loves a cheerful giver",
    ),
    (TEXTS[94], "s01", "w081", ["w080", "w081"], "w080", "For we take forethought"),
    (
        TEXTS[95],
        "s01",
        "w105",
        ["w103", "w104", "w105", "w106"],
        "w103",
        "for the laborer is worthy",
    ),
    (TEXTS[96], "s01", "w078", ["w077", "w078", "w079"], "w079", "For I have not come"),
    (TEXTS[97], "s01", "w089", ["w087", "w088", "w089"], "w087", "For it is written"),
    (TEXTS[98], "s01", "w091", ["w090", "w091", "w092"], "w090", "For My yoke"),
    (TEXTS[99], "s01", "w109", ["w108", "w109"], "w108", "For I say"),
    (TEXTS[100], "s02", "w018", ["w017", "w018"], "w017", "For who"),
    (TEXTS[101], "s01", "w082", ["w081", "w082"], "w081", "For no"),
    (TEXTS[102], "s01", "w090", ["w089", "w090", "w091"], "w089", "for they are virgins"),
    (
        TEXTS[102],
        "s01",
        "w116",
        ["w114", "w115", "w116", "w117"],
        "w117",
        "for they are without blemish",
    ),
    (TEXTS[103], "s01", "w031", ["w029", "w030", "w031"], "w029", "For it will happen"),
    (TEXTS[104], "s01", "w022", ["w021", "w022"], "w021", "For He received"),
    (TEXTS[105], "s01", "w055", ["w054", "w055"], "w054", "for that which"),
    (
        TEXTS[105],
        "s01",
        "w073",
        ["w072", "w073", "w074", "w075"],
        "w075",
        "for He Himself will save",
    ),
    (TEXTS[106], "s01", "w026", ["w025", "w026"], "w025", "For you are dead"),
    (TEXTS[107], "s01", "w024", ["w023", "w024"], "w023", "For an angel"),
    (TEXTS[107], "s01", "w069", ["w068", "w069"], "w068", "for I know"),
    (TEXTS[107], "s01", "w080", ["w079", "w080"], "w079", "for He is risen"),
    (TEXTS[108], "s01", "w044", ["w043", "w044"], "w043", "For now"),
    (TEXTS[108], "s01", "w101", ["w100", "w101", "w102"], "w100", "for your voice"),
    (TEXTS[109], "s01", "w068", ["w067", "w068"], "w067", "For behold"),
]

RETAINED = [
    (
        TEXTS[11],
        "s01",
        "w022",
        [
            {
                "words": ["w021", "w022", "w023"],
                "anchor": "w021",
                "gloss": "for the trumpet will sound",
            }
        ],
        None,
    ),
    (
        TEXTS[11],
        "s01",
        "w032",
        [{"words": ["w031", "w032"], "anchor": "w031", "gloss": "for it is necessary"}],
        None,
    ),
    (
        TEXTS[14],
        "s01",
        "w027",
        [{"words": ["w026", "w027", "w028"], "anchor": "w026", "gloss": "for their works"}],
        None,
    ),
    (
        TEXTS[28],
        "s20",
        "w285",
        [{"words": ["w284", "w285"], "anchor": "w284", "gloss": "For all"}],
        None,
    ),
    (
        TEXTS[28],
        "s59",
        "w884",
        [{"words": ["w883", "w884"], "anchor": "w883", "gloss": "For he knew"}],
        None,
    ),
    (TEXTS[28], "s70", "w961", [], "then"),
    (
        TEXTS[51],
        "s01",
        "w076",
        [{"words": ["w075", "w076", "w077"], "anchor": "w077", "gloss": "for the Father Himself"}],
        None,
    ),
    (
        TEXTS[54],
        "s01",
        "w014",
        [
            {
                "words": ["w013", "w014", "w015"],
                "anchor": "w013",
                "gloss": "for we were buried together",
            }
        ],
        None,
    ),
    (
        TEXTS[54],
        "s01",
        "w039",
        [{"words": ["w038", "w039"], "anchor": "w039", "gloss": "for if"}],
        None,
    ),
    (
        TEXTS[54],
        "s01",
        "w069",
        [{"words": ["w068", "w069"], "anchor": "w069", "gloss": "for whoever"}],
        None,
    ),
    (
        TEXTS[54],
        "s01",
        "w104",
        [{"words": ["w103", "w104"], "anchor": "w103", "gloss": "for the death"}],
        None,
    ),
    (
        TEXTS[87],
        "s01",
        "w003",
        [{"words": ["w002", "w003"], "anchor": "w002", "gloss": "For with the heart"}],
        None,
    ),
    (
        TEXTS[87],
        "s01",
        "w014",
        [{"words": ["w013", "w014", "w015"], "anchor": "w013", "gloss": "For Scripture says"}],
        None,
    ),
    (
        TEXTS[87],
        "s01",
        "w024",
        [{"words": ["w023", "w024", "w025"], "anchor": "w025", "gloss": "For there is no"}],
        None,
    ),
    (
        TEXTS[87],
        "s01",
        "w041",
        [{"words": ["w040", "w041", "w042"], "anchor": "w040", "gloss": "For everyone who"}],
        None,
    ),
    (
        TEXTS[87],
        "s01",
        "w088",
        [{"words": ["w087", "w088", "w089"], "anchor": "w089", "gloss": "For Isaiah says"}],
        None,
    ),
    (
        TEXTS[88],
        "s01",
        "w025",
        [{"words": ["w024", "w025"], "anchor": "w024", "gloss": "for they were"}],
        None,
    ),
]


@cache
def reading(text):
    return store.load(ROOT, text)


def assert_construction(doc, layer, sid, particle, members, anchor, gloss):
    segment = next(s for s in doc["segments"] if s["id"] == sid)
    ids = [w["id"] for w in segment["words"]]
    start = ids.index(members[0])
    assert ids[start : start + len(members)] == members
    assert next(w for w in segment["words"] if w["id"] == particle)["lemma"] == "enim"
    found = [
        g for g in layer["segments"][sid].get("alignments", []) if set(g["words"]) & set(members)
    ]
    assert found == [{"words": members, "anchor": anchor, "gloss": gloss}]
    assert all("gloss" not in layer["words"][wid] for wid in members)
    assert not interlinear.check(doc, layer)


@pytest.mark.parametrize("text,sid,particle,members,anchor,gloss", CONSTRUCTIONS)
def test_contextual_explanatory_construction(text, sid, particle, members, anchor, gloss):
    doc, layers = reading(text)
    assert_construction(doc, layers["en"], sid, particle, members, anchor, gloss)


@pytest.mark.parametrize("text,sid,particle,groups,direct", RETAINED)
def test_retained_explanatory_realization(text, sid, particle, groups, direct):
    doc, layers = reading(text)
    en = layers["en"]
    assert [
        g for g in en["segments"][sid].get("alignments", []) if particle in g["words"]
    ] == groups
    assert en["words"][particle].get("gloss") == direct
    assert not interlinear.check(doc, en)


@pytest.mark.parametrize("text", sorted({row[0] for row in CONSTRUCTIONS + RETAINED}))
def test_explanatory_readings_pass_language_checks(text):
    doc, layers = reading(text)
    en = layers["en"]
    assert not interlinear.check(doc, en)
    assert not english.check(doc, en)
    assert not interlinear_quality.check(doc, en)
    assert not lint.lint_gloss(en, doc)


def test_colossians_state_retains_separate_zero_copula():
    doc, layers = reading("proprium.vigilia-paschalis-epistola")
    en = layers["en"]
    word = next(w for s in doc["segments"] for w in s.get("words", []) if w["id"] == "w025")
    assert word["lemma"] == "mortuus" and word["morph"]["pos"] == "adj"
    assert {"words": ["w027"], "reason": "inflection"} in en["segments"]["s01"]["alignments"]
    assert "gloss" not in en["words"]["w027"]


def test_transfiguration_anacoluthon_keeps_its_explanation():
    doc, layers = reading("proprium.transfiguratio-domini-epistola")
    en = layers["en"]
    word = next(w for s in doc["segments"] for w in s.get("words", []) if w["id"] == "w021")
    assert word["lemma"] == "accipio"
    assert word["morph"]["mood"] == "part" and word["morph"]["tense"] == "pres"
    assert en["words"]["w021"]["explanation"] == (
        "The participle opens a sentence whose main verb never comes (an anacoluthon): "
        "it describes Christ, who received honor and glory from God the Father. "
        "The verbs “est”, “complácui” and “audíte” belong to the quoted voice. "
        "No separate word expresses its subject."
    )

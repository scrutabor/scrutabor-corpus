"""Keep reviewed Polish relative captions local to their actual sentence boundaries."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Finite reviewed addresses, not a rule for every Latin qui or punctuation mark.
LOWERCASE_RELATIVES = (
    ("orationes.agimus-tibi-gratias", "s03", "w010", "Qui"),
    ("ordinarium.corpus-tuum", "s04", "w028", "Qui"),
    ("ordinarium.deus-qui-humanae", "s02", "w036", "Qui"),
    ("ordinarium.fili-dei-vivi", "s05", "w048", "Qui"),
    ("ordinarium.libera-nos", "s10", "w064", "Qui"),
    ("ordinarium.perceptio-corporis", "s04", "w034", "Qui"),
    ("ordinarium.qui-dixisti", "s06", "w031", "Qui"),
    ("proprium.annuntiatio-beatae-mariae-virginis-collecta", "s01", "w038", "Qui"),
    ("proprium.annuntiatio-beatae-mariae-virginis-postcommunio", "s01", "w034", "Qui"),
    ("proprium.annuntiatio-beatae-mariae-virginis-secreta", "s01", "w038", "Qui"),
    ("proprium.ascensio-domini-collecta", "s01", "w031", "Qui"),
    ("proprium.ascensio-domini-postcommunio", "s01", "w024", "Qui"),
    ("proprium.ascensio-domini-secreta", "s01", "w032", "Qui"),
    ("proprium.assumptio-beatae-mariae-virginis-collecta", "s01", "w038", "Qui"),
    ("proprium.assumptio-beatae-mariae-virginis-postcommunio", "s01", "w028", "Qui"),
    ("proprium.assumptio-beatae-mariae-virginis-secreta", "s01", "w032", "Qui"),
    ("proprium.beata-maria-virgo-regina-collecta", "s01", "w033", "Qui"),
    ("proprium.beata-maria-virgo-regina-postcommunio", "s01", "w031", "Qui"),
    ("proprium.beata-maria-virgo-regina-secreta", "s01", "w027", "Qui"),
    ("proprium.beatae-mariae-virginis-a-rosario-collecta", "s01", "w042", "Qui"),
    ("proprium.cathedra-sancti-petri-collecta", "s04", "w026", "Qui"),
    ("proprium.cathedra-sancti-petri-epistola", "s01", "w041", "qui"),
    ("proprium.cathedra-sancti-petri-postcommunio", "s04", "w029", "Qui"),
    ("proprium.cathedra-sancti-petri-secreta", "s05", "w030", "Qui"),
    ("proprium.commemoratio-baptismatis-domini-postcommunio", "s01", "w032", "Qui"),
    ("proprium.commemoratio-baptismatis-domini-secreta", "s01", "w029", "Qui"),
    ("proprium.commemoratio-omnium-fidelium-defunctorum-missa-i-secreta", "s01", "w030", "Qui"),
    ("proprium.commemoratio-omnium-fidelium-defunctorum-missa-ii-collecta", "s01", "w023", "Qui"),
    (
        "proprium.commemoratio-omnium-fidelium-defunctorum-missa-ii-postcommunio",
        "s01",
        "w025",
        "Qui",
    ),
    ("proprium.commemoratio-omnium-fidelium-defunctorum-missa-ii-secreta", "s01", "w030", "Qui"),
    ("proprium.commemoratio-omnium-fidelium-defunctorum-missa-iii-collecta", "s01", "w045", "Qui"),
    (
        "proprium.commemoratio-omnium-fidelium-defunctorum-missa-iii-postcommunio",
        "s01",
        "w043",
        "Qui",
    ),
    ("proprium.commemoratio-omnium-fidelium-defunctorum-missa-iii-secreta", "s01", "w040", "Qui"),
    ("proprium.d-n-iesu-christi-regis-secreta", "s01", "w028", "Qui"),
    ("proprium.dedicatio-archibasilicae-sanctissimi-salvatoris-collecta", "s01", "w044", "Qui"),
    ("proprium.dedicatio-archibasilicae-sanctissimi-salvatoris-postcommunio", "s01", "w034", "Qui"),
    ("proprium.dedicatio-archibasilicae-sanctissimi-salvatoris-secreta", "s01", "w026", "Qui"),
    ("proprium.dedicatio-sancti-michaelis-archangeli-collecta", "s01", "w034", "Qui"),
    ("proprium.dedicatio-sancti-michaelis-archangeli-postcommunio", "s01", "w025", "Qui"),
    ("proprium.dedicatio-sancti-michaelis-archangeli-secreta", "s01", "w031", "Qui"),
    ("proprium.dominica-i-in-quadragesima-collecta", "s01", "w030", "Qui"),
    ("proprium.dominica-i-in-quadragesima-postcommunio", "s01", "w025", "Qui"),
    ("proprium.dominica-i-in-quadragesima-secreta", "s01", "w026", "Qui"),
    ("proprium.dominica-i-passionis-collecta", "s01", "w027", "Qui"),
    ("proprium.dominica-i-passionis-postcommunio", "s01", "w021", "Qui"),
    ("proprium.dominica-i-passionis-secreta", "s01", "w023", "Qui"),
    ("proprium.dominica-i-post-epiphaniam-collecta", "s01", "w028", "Qui"),
    ("proprium.dominica-i-post-epiphaniam-postcommunio", "s01", "w025", "Qui"),
    ("proprium.dominica-i-post-epiphaniam-secreta", "s01", "w017", "Qui"),
    ("proprium.dominica-ii-in-quadragesima-collecta", "s01", "w032", "Qui"),
    ("proprium.dominica-ii-in-quadragesima-secreta", "s01", "w021", "Qui"),
    ("proprium.dominica-ii-passionis-collecta", "s01", "w039", "Qui"),
    ("proprium.dominica-ii-passionis-postcommunio", "s01", "w021", "Qui"),
    ("proprium.dominica-ii-passionis-secreta", "s01", "w027", "Qui"),
    ("proprium.dominica-ii-post-epiphaniam-collecta", "s01", "w028", "Qui"),
    ("proprium.dominica-ii-post-epiphaniam-postcommunio", "s01", "w027", "Qui"),
    ("proprium.dominica-ii-post-epiphaniam-secreta", "s01", "w018", "Qui"),
    ("proprium.dominica-ii-post-pascha-collecta", "s01", "w033", "Qui"),
    ("proprium.dominica-ii-post-pascha-postcommunio", "s01", "w023", "Qui"),
    ("proprium.dominica-ii-post-pascha-secreta", "s01", "w022", "Qui"),
    ("proprium.dominica-ii-post-pentecosten-collecta", "s01", "w031", "Qui"),
    ("proprium.dominica-ii-post-pentecosten-postcommunio", "s01", "w021", "Qui"),
    ("proprium.dominica-ii-post-pentecosten-secreta", "s01", "w025", "Qui"),
    ("proprium.dominica-iii-in-quadragesima-collecta", "s01", "w022", "Qui"),
    ("proprium.dominica-iii-in-quadragesima-postcommunio", "s01", "w024", "Qui"),
    ("proprium.dominica-iii-post-epiphaniam-collecta", "s01", "w023", "Qui"),
    ("proprium.dominica-iii-post-epiphaniam-postcommunio", "s01", "w022", "Qui"),
    ("proprium.dominica-iii-post-epiphaniam-secreta", "s01", "w024", "Qui"),
    ("proprium.dominica-iii-post-pentecosten-collecta", "s01", "w039", "Qui"),
    ("proprium.dominica-iii-post-pentecosten-postcommunio", "s01", "w019", "Qui"),
    ("proprium.dominica-iii-post-pentecosten-secreta", "s01", "w020", "Qui"),
    ("proprium.dominica-in-albis-collecta", "s01", "w024", "Qui"),
    ("proprium.dominica-in-albis-postcommunio", "s01", "w029", "Qui"),
    ("proprium.dominica-in-albis-secreta", "s01", "w024", "Qui"),
    ("proprium.dominica-in-quinquagesima-collecta", "s01", "w024", "Qui"),
    ("proprium.dominica-in-quinquagesima-graduale", "s01", "w004", "qui"),
    ("proprium.dominica-in-quinquagesima-postcommunio", "s01", "w022", "Qui"),
    ("proprium.dominica-in-septuagesima-collecta", "s01", "w028", "Qui"),
    ("proprium.dominica-in-septuagesima-postcommunio", "s01", "w025", "Qui"),
    ("proprium.dominica-in-sexagesima-collecta", "s01", "w002", "qui"),
    ("proprium.dominica-in-sexagesima-collecta", "s01", "w027", "Qui"),
    ("proprium.dominica-in-sexagesima-epistola", "s01", "w193", "qui"),
    ("proprium.dominica-in-sexagesima-secreta", "s01", "w017", "Qui"),
    ("proprium.dominica-infra-octavam-nativitatis-postcommunio", "s01", "w021", "Qui"),
    ("proprium.dominica-infra-octavam-nativitatis-secreta", "s01", "w029", "Qui"),
    ("proprium.dominica-iv-adventus-epistola", "s05", "w064", "qui"),
    ("proprium.dominica-iv-in-quadragesima-collecta", "s01", "w023", "Qui"),
    ("proprium.dominica-iv-in-quadragesima-postcommunio", "s01", "w027", "Qui"),
    ("proprium.dominica-iv-post-epiphaniam-collecta", "s01", "w038", "Qui"),
    ("proprium.dominica-iv-post-epiphaniam-postcommunio", "s01", "w021", "Qui"),
    ("proprium.dominica-iv-post-epiphaniam-secreta", "s01", "w026", "Qui"),
    ("proprium.dominica-iv-post-pentecosten-collecta", "s01", "w027", "Qui"),
    ("proprium.dominica-iv-post-pentecosten-postcommunio", "s01", "w018", "Qui"),
    ("proprium.dominica-iv-post-pentecosten-secreta", "s01", "w023", "Qui"),
    ("proprium.dominica-ix-post-pentecosten-collecta", "s01", "w027", "Qui"),
    ("proprium.dominica-ix-post-pentecosten-postcommunio", "s01", "w020", "Qui"),
    ("proprium.dominica-ix-post-pentecosten-secreta", "s01", "w026", "Qui"),
    ("proprium.dominica-pentecostes-collecta", "s01", "w031", "Qui"),
    ("proprium.dominica-post-ascensionem-collecta", "s01", "w025", "Qui"),
    ("proprium.dominica-post-ascensionem-evangelium", "s01", "w019", "qui"),
    ("proprium.dominica-post-ascensionem-postcommunio", "s01", "w020", "Qui"),
    ("proprium.dominica-post-ascensionem-secreta", "s01", "w020", "Qui"),
    ("proprium.dominica-resurrectionis-collecta", "s01", "w030", "Qui"),
    ("proprium.dominica-v-post-epiphaniam-collecta", "s01", "w027", "Qui"),
    ("proprium.dominica-v-post-epiphaniam-postcommunio", "s01", "w022", "Qui"),
    ("proprium.dominica-v-post-epiphaniam-secreta", "s01", "w024", "Qui"),
    ("proprium.dominica-v-post-pentecosten-collecta", "s01", "w036", "Qui"),
    ("proprium.dominica-v-post-pentecosten-postcommunio", "s01", "w025", "Qui"),
    ("proprium.dominica-v-post-pentecosten-secreta", "s01", "w032", "Qui"),
    ("proprium.dominica-vi-post-epiphaniam-collecta", "s01", "w025", "Qui"),
    ("proprium.dominica-vi-post-epiphaniam-postcommunio", "s01", "w021", "Qui"),
    ("proprium.dominica-vi-post-epiphaniam-secreta", "s01", "w019", "Qui"),
    ("proprium.dominica-vi-post-pentecosten-collecta", "s01", "w040", "Qui"),
    ("proprium.dominica-vi-post-pentecosten-postcommunio", "s01", "w023", "Qui"),
    ("proprium.dominica-vi-post-pentecosten-secreta", "s01", "w035", "Qui"),
    ("proprium.dominica-vii-post-pentecosten-collecta", "s01", "w028", "Qui"),
    ("proprium.dominica-vii-post-pentecosten-postcommunio", "s01", "w026", "Qui"),
    ("proprium.dominica-vii-post-pentecosten-secreta", "s01", "w042", "Qui"),
    ("proprium.dominica-viii-post-pentecosten-collecta", "s01", "w032", "Qui"),
    ("proprium.dominica-viii-post-pentecosten-postcommunio", "s01", "w023", "Qui"),
    ("proprium.dominica-viii-post-pentecosten-secreta", "s01", "w037", "Qui"),
    ("proprium.dominica-x-post-pentecosten-collecta", "s01", "w032", "Qui"),
    ("proprium.dominica-x-post-pentecosten-postcommunio", "s01", "w024", "Qui"),
    ("proprium.dominica-x-post-pentecosten-secreta", "s01", "w027", "Qui"),
    ("proprium.dominica-xi-post-pentecosten-collecta", "s01", "w037", "Qui"),
    ("proprium.dominica-xi-post-pentecosten-postcommunio", "s01", "w026", "Qui"),
    ("proprium.dominica-xi-post-pentecosten-secreta", "s01", "w026", "Qui"),
    ("proprium.dominica-xii-post-pentecosten-collecta", "s01", "w035", "Qui"),
    ("proprium.dominica-xii-post-pentecosten-postcommunio", "s01", "w023", "Qui"),
    ("proprium.dominica-xii-post-pentecosten-secreta", "s01", "w025", "Qui"),
    ("proprium.dominica-xiii-post-pentecosten-collecta", "s01", "w029", "Qui"),
    ("proprium.dominica-xiii-post-pentecosten-postcommunio", "s01", "w018", "Qui"),
    ("proprium.dominica-xiii-post-pentecosten-secreta", "s01", "w025", "Qui"),
    ("proprium.dominica-xiv-post-pentecosten-collecta", "s01", "w033", "Qui"),
    ("proprium.dominica-xiv-post-pentecosten-postcommunio", "s01", "w022", "Qui"),
    ("proprium.dominica-xiv-post-pentecosten-secreta", "s01", "w025", "Qui"),
    ("proprium.dominica-xix-post-pentecosten-collecta", "s01", "w029", "Qui"),
    ("proprium.dominica-xix-post-pentecosten-postcommunio", "s01", "w025", "Qui"),
    ("proprium.dominica-xix-post-pentecosten-secreta", "s01", "w021", "Qui"),
    ("proprium.dominica-xv-post-pentecosten-collecta", "s01", "w028", "Qui"),
    ("proprium.dominica-xv-post-pentecosten-postcommunio", "s01", "w029", "Qui"),
    ("proprium.dominica-xv-post-pentecosten-secreta", "s01", "w019", "Qui"),
    ("proprium.dominica-xvi-post-pentecosten-collecta", "s01", "w025", "Qui"),
    ("proprium.dominica-xvi-post-pentecosten-epistola", "s01", "w093", "qui"),
    ("proprium.dominica-xvi-post-pentecosten-postcommunio", "s01", "w028", "Qui"),
    ("proprium.dominica-xvi-post-pentecosten-secreta", "s01", "w025", "Qui"),
    ("proprium.dominica-xvii-post-pentecosten-collecta", "s01", "w023", "Qui"),
    ("proprium.dominica-xvii-post-pentecosten-communio", "s01", "w017", "qui"),
    ("proprium.dominica-xvii-post-pentecosten-epistola", "s01", "w057", "qui"),
    ("proprium.dominica-xvii-post-pentecosten-postcommunio", "s01", "w021", "Qui"),
    ("proprium.dominica-xvii-post-pentecosten-secreta", "s01", "w026", "Qui"),
    ("proprium.dominica-xviii-post-pentecosten-collecta", "s01", "w023", "Qui"),
    ("proprium.dominica-xviii-post-pentecosten-evangelium", "s01", "w110", "qui"),
    ("proprium.dominica-xviii-post-pentecosten-postcommunio", "s01", "w024", "Qui"),
    ("proprium.dominica-xviii-post-pentecosten-secreta", "s01", "w033", "Qui"),
    ("proprium.dominica-xx-post-pentecosten-collecta", "s01", "w028", "Qui"),
    ("proprium.dominica-xx-post-pentecosten-postcommunio", "s01", "w021", "Qui"),
    ("proprium.dominica-xx-post-pentecosten-secreta", "s01", "w021", "Qui"),
    ("proprium.dominica-xxi-post-pentecosten-collecta", "s01", "w031", "Qui"),
    ("proprium.dominica-xxi-post-pentecosten-postcommunio", "s01", "w020", "Qui"),
    ("proprium.dominica-xxi-post-pentecosten-secreta", "s01", "w023", "Qui"),
    ("proprium.dominica-xxii-post-pentecosten-collecta", "s01", "w029", "Qui"),
    ("proprium.dominica-xxii-post-pentecosten-secreta", "s01", "w027", "Qui"),
    ("proprium.dominica-xxiii-post-pentecosten-collecta", "s01", "w026", "Qui"),
    ("proprium.dominica-xxiii-post-pentecosten-epistola", "s01", "w059", "qui"),
    ("proprium.dominica-xxiii-post-pentecosten-postcommunio", "s01", "w022", "Qui"),
    ("proprium.dominica-xxiii-post-pentecosten-secreta", "s01", "w023", "Qui"),
    ("proprium.dominica-xxiv-post-pentecosten-collecta", "s01", "w025", "Qui"),
    ("proprium.dominica-xxiv-post-pentecosten-postcommunio", "s01", "w028", "Qui"),
    ("proprium.dominica-xxiv-post-pentecosten-secreta", "s01", "w034", "Qui"),
    ("proprium.epiphania-domini-collecta", "s01", "w035", "Qui"),
    ("proprium.epiphania-domini-evangelium", "s01", "w090", "qui"),
    ("proprium.epiphania-domini-postcommunio", "s01", "w021", "Qui"),
    ("proprium.epiphania-domini-secreta", "s01", "w030", "Qui"),
    ("proprium.exaltatio-sanctae-crucis-collecta", "s01", "w002", "qui"),
    ("proprium.exaltatio-sanctae-crucis-collecta", "s01", "w034", "Qui"),
    ("proprium.exaltatio-sanctae-crucis-postcommunio", "s01", "w025", "Qui"),
    ("proprium.exaltatio-sanctae-crucis-secreta", "s01", "w039", "Qui"),
    ("proprium.feria-v-in-cena-domini-postcommunio", "s01", "w025", "Qui"),
    ("proprium.feria-v-in-cena-domini-secreta", "s01", "w031", "Qui"),
    ("proprium.immaculata-conceptio-collecta", "s01", "w002", "qui"),
    ("proprium.immaculata-conceptio-collecta", "s01", "w014", "qui"),
    ("proprium.immaculata-conceptio-collecta", "s01", "w043", "Qui"),
    ("proprium.immaculata-conceptio-postcommunio", "s01", "w028", "Qui"),
    ("proprium.immaculata-conceptio-secreta", "s01", "w042", "Qui"),
    ("proprium.immaculatum-cor-beatae-mariae-virginis-collecta", "s01", "w004", "qui"),
    ("proprium.immaculatum-cor-beatae-mariae-virginis-collecta", "s01", "w037", "Qui"),
    ("proprium.immaculatum-cor-beatae-mariae-virginis-postcommunio", "s01", "w034", "Qui"),
    ("proprium.immaculatum-cor-beatae-mariae-virginis-secreta", "s01", "w030", "Qui"),
    ("proprium.in-octava-nativitatis-collecta", "s01", "w033", "Qui"),
    ("proprium.in-octava-nativitatis-postcommunio", "s01", "w028", "Qui"),
    ("proprium.in-octava-nativitatis-secreta", "s01", "w022", "Qui"),
    ("proprium.maternitas-beatae-mariae-virginis-collecta", "s01", "w038", "Qui"),
    ("proprium.maternitas-beatae-mariae-virginis-postcommunio", "s01", "w028", "Qui"),
    ("proprium.maternitas-beatae-mariae-virginis-secreta", "s01", "w028", "Qui"),
    ("proprium.nativitas-beatae-mariae-virginis-collecta", "s01", "w031", "Qui"),
    ("proprium.nativitas-beatae-mariae-virginis-secreta", "s01", "w035", "Qui"),
    ("proprium.nativitas-domini-in-aurora-collecta", "s01", "w033", "Qui"),
    ("proprium.nativitas-domini-in-aurora-collecta", "s03", "w072", "Qui"),
    ("proprium.nativitas-domini-in-aurora-postcommunio", "s01", "w023", "Qui"),
    ("proprium.nativitas-domini-in-aurora-postcommunio", "s03", "w060", "Qui"),
    ("proprium.nativitas-domini-in-aurora-secreta", "s01", "w040", "Qui"),
    ("proprium.nativitas-domini-in-aurora-secreta", "s03", "w081", "Qui"),
    ("proprium.nativitas-domini-in-die-collecta", "s01", "w029", "Qui"),
    ("proprium.nativitas-domini-in-die-secreta", "s01", "w023", "Qui"),
    ("proprium.nativitas-sancti-ioannis-baptistae-collecta", "s01", "w034", "Qui"),
    ("proprium.nativitas-sancti-ioannis-baptistae-postcommunio", "s01", "w022", "Qui"),
    ("proprium.nativitas-sancti-ioannis-baptistae-secreta", "s01", "w027", "Qui"),
    ("proprium.omnium-sanctorum-collecta", "s01", "w032", "Qui"),
    ("proprium.omnium-sanctorum-postcommunio", "s01", "w023", "Qui"),
    ("proprium.omnium-sanctorum-secreta", "s01", "w029", "Qui"),
    ("proprium.pretiosissimi-sanguinis-domini-nostri-iesu-christi-collecta", "s01", "w049", "Qui"),
    ("proprium.pretiosissimi-sanguinis-domini-nostri-iesu-christi-secreta", "s01", "w033", "Qui"),
    ("proprium.purificatio-beatae-mariae-virginis-collecta", "s01", "w038", "Qui"),
    ("proprium.purificatio-beatae-mariae-virginis-postcommunio", "s01", "w034", "Qui"),
    ("proprium.purificatio-beatae-mariae-virginis-secreta", "s01", "w027", "Qui"),
    ("proprium.sacratissimi-cordis-iesu-collecta", "s01", "w039", "Qui"),
    ("proprium.sancta-familia-secreta", "s01", "w032", "Qui"),
    ("proprium.sanctae-annae-matris-beatae-mariae-virginis-collecta", "s01", "w036", "Qui"),
    ("proprium.sanctae-annae-matris-beatae-mariae-virginis-postcommunio", "s01", "w032", "Qui"),
    ("proprium.sanctae-annae-matris-beatae-mariae-virginis-secreta", "s01", "w036", "Qui"),
    ("proprium.sancti-andreae-apostoli-collecta", "s01", "w032", "Qui"),
    ("proprium.sancti-andreae-apostoli-postcommunio", "s01", "w030", "Qui"),
    ("proprium.sancti-andreae-apostoli-secreta", "s01", "w029", "Qui"),
    ("proprium.sancti-bartholomaei-apostoli-collecta", "s01", "w036", "Qui"),
    ("proprium.sancti-bartholomaei-apostoli-postcommunio", "s01", "w027", "Qui"),
    ("proprium.sancti-bartholomaei-apostoli-secreta", "s01", "w028", "Qui"),
    ("proprium.sancti-iacobi-apostoli-collecta", "s01", "w029", "Qui"),
    ("proprium.sancti-iacobi-apostoli-postcommunio", "s01", "w024", "Qui"),
    ("proprium.sancti-iacobi-apostoli-secreta", "s01", "w031", "Qui"),
    ("proprium.sancti-ioachim-confessoris-collecta", "s01", "w034", "Qui"),
    ("proprium.sancti-ioachim-confessoris-postcommunio", "s01", "w045", "Qui"),
    ("proprium.sancti-ioachim-confessoris-secreta", "s01", "w040", "Qui"),
    ("proprium.sancti-ioannis-apostoli-et-evangelistae-collecta", "s01", "w026", "Qui"),
    ("proprium.sancti-ioannis-apostoli-et-evangelistae-postcommunio", "s01", "w027", "Qui"),
    ("proprium.sancti-ioannis-apostoli-et-evangelistae-secreta", "s01", "w022", "Qui"),
    ("proprium.sancti-ioseph-opificis-collecta", "s01", "w034", "Qui"),
    ("proprium.sancti-ioseph-opificis-postcommunio", "s01", "w024", "Qui"),
    ("proprium.sancti-ioseph-opificis-secreta", "s01", "w027", "Qui"),
    ("proprium.sancti-ioseph-sponsi-beatae-mariae-virginis-postcommunio", "s01", "w026", "Qui"),
    ("proprium.sancti-ioseph-sponsi-beatae-mariae-virginis-secreta", "s01", "w042", "Qui"),
    ("proprium.sancti-laurentii-martyris-collecta", "s01", "w025", "Qui"),
    ("proprium.sancti-laurentii-martyris-postcommunio", "s01", "w030", "Qui"),
    ("proprium.sancti-laurentii-martyris-secreta", "s01", "w025", "Qui"),
    ("proprium.sancti-lucae-evangelistae-collecta", "s01", "w029", "Qui"),
    ("proprium.sancti-lucae-evangelistae-postcommunio", "s01", "w032", "Qui"),
    ("proprium.sancti-lucae-evangelistae-secreta", "s01", "w033", "Qui"),
    ("proprium.sancti-marci-evangelistae-collecta", "s01", "w029", "Qui"),
    ("proprium.sancti-marci-evangelistae-postcommunio", "s01", "w028", "Qui"),
    ("proprium.sancti-marci-evangelistae-secreta", "s01", "w036", "Qui"),
    ("proprium.sancti-matthaei-apostoli-et-evangelistae-collecta", "s01", "w026", "Qui"),
    ("proprium.sancti-matthaei-apostoli-et-evangelistae-postcommunio", "s01", "w030", "Qui"),
    ("proprium.sancti-matthaei-apostoli-et-evangelistae-secreta", "s01", "w024", "Qui"),
    ("proprium.sancti-matthiae-apostoli-collecta", "s01", "w028", "Qui"),
    ("proprium.sancti-matthiae-apostoli-postcommunio", "s01", "w027", "Qui"),
    ("proprium.sancti-matthiae-apostoli-secreta", "s01", "w029", "Qui"),
    ("proprium.sancti-petri-et-pauli-apostolorum-collecta", "s01", "w032", "Qui"),
    ("proprium.sancti-petri-et-pauli-apostolorum-postcommunio", "s01", "w019", "Qui"),
    ("proprium.sancti-petri-et-pauli-apostolorum-secreta", "s01", "w025", "Qui"),
    ("proprium.sancti-stephani-protomartyris-collecta", "s01", "w029", "Qui"),
    ("proprium.sancti-stephani-protomartyris-postcommunio", "s01", "w022", "Qui"),
    ("proprium.sancti-stephani-protomartyris-secreta", "s01", "w026", "Qui"),
    ("proprium.sancti-thomae-apostoli-collecta", "s01", "w029", "Qui"),
    ("proprium.sancti-thomae-apostoli-postcommunio", "s01", "w025", "Qui"),
    ("proprium.sancti-thomae-apostoli-secreta", "s01", "w033", "Qui"),
    ("proprium.sanctissimae-trinitatis-collecta", "s01", "w039", "Qui"),
    ("proprium.sanctissimi-nominis-iesu-collecta", "s01", "w037", "Qui"),
    ("proprium.sanctissimi-nominis-iesu-postcommunio", "s01", "w063", "Qui"),
    ("proprium.sanctissimi-nominis-iesu-secreta", "s01", "w046", "Qui"),
    ("proprium.sanctorum-innocentium-martyrum-collecta", "s01", "w038", "Qui"),
    ("proprium.sanctorum-innocentium-martyrum-postcommunio", "s01", "w026", "Qui"),
    ("proprium.sanctorum-innocentium-martyrum-secreta", "s01", "w027", "Qui"),
    ("proprium.sanctorum-philippi-et-iacobi-apostolorum-collecta", "s01", "w027", "Qui"),
    ("proprium.sanctorum-philippi-et-iacobi-apostolorum-postcommunio", "s01", "w020", "Qui"),
    ("proprium.sanctorum-philippi-et-iacobi-apostolorum-secreta", "s01", "w027", "Qui"),
    ("proprium.sanctorum-simonis-et-iudae-apostolorum-collecta", "s01", "w002", "qui"),
    ("proprium.sanctorum-simonis-et-iudae-apostolorum-collecta", "s01", "w035", "Qui"),
    ("proprium.sanctorum-simonis-et-iudae-apostolorum-postcommunio", "s01", "w031", "Qui"),
    ("proprium.sanctorum-simonis-et-iudae-apostolorum-secreta", "s01", "w026", "Qui"),
    ("proprium.transfiguratio-domini-collecta", "s01", "w047", "Qui"),
    ("proprium.transfiguratio-domini-postcommunio", "s01", "w027", "Qui"),
    ("proprium.transfiguratio-domini-secreta", "s01", "w026", "Qui"),
    ("proprium.vigilia-nativitatis-collecta", "s01", "w028", "Qui"),
    ("proprium.vigilia-nativitatis-postcommunio", "s01", "w025", "Qui"),
    ("proprium.vigilia-paschalis-collecta", "s01", "w037", "Qui"),
    ("proprium.vigilia-paschalis-postcommunio", "s01", "w023", "Qui"),
    ("proprium.vigilia-paschalis-secreta", "s01", "w028", "Qui"),
    ("proprium.vigilia-pentecostes-collecta", "s01", "w035", "Qui"),
    ("proprium.vigilia-pentecostes-postcommunio", "s01", "w021", "Qui"),
    ("proprium.vigilia-pentecostes-secreta", "s01", "w020", "Qui"),
    ("proprium.visitatio-beatae-mariae-virginis-collecta", "s01", "w031", "Qui"),
    ("proprium.visitatio-beatae-mariae-virginis-postcommunio", "s01", "w025", "Qui"),
    ("proprium.visitatio-beatae-mariae-virginis-secreta", "s01", "w035", "Qui"),
)

INITIAL_CAPITALS = (
    ("litaniae.sanctissimi-nominis-iesu", "s146", "w473", "Qui"),
    ("ordinarium.qui-pridie-in-cena-domini", "s01", "w001", "Qui"),
    ("ordinarium.qui-pridie", "s02", "w001", "Qui"),
    ("proprium.dominica-xvii-post-pentecosten-epistola", "s01", "w068", "Qui"),
    ("proprium.nativitas-domini-in-die-epistola", "s01", "w106", "Qui"),
)

# Relatives whose continuous Polish prose opens a separate sentence at the clause. The 29
# oration conclusions (CONCLUSION_BOUNDARIES) follow that sentence with a capital caption;
# the XVIII Epistle relative keeps its lowercase caption beside the prose sentence "On też".
ADJUDICATED_BOUNDARIES = (
    ("proprium.beatae-mariae-virginis-a-rosario-postcommunio", "s01", "w024", "Qui"),
    ("proprium.beatae-mariae-virginis-a-rosario-secreta", "s01", "w028", "Qui"),
    ("proprium.commemoratio-baptismatis-domini-collecta", "s01", "w022", "Qui"),
    ("proprium.commemoratio-omnium-fidelium-defunctorum-missa-i-collecta", "s01", "w023", "Qui"),
    (
        "proprium.commemoratio-omnium-fidelium-defunctorum-missa-i-postcommunio",
        "s01",
        "w023",
        "Qui",
    ),
    ("proprium.corporis-christi-collecta", "s01", "w030", "Qui"),
    ("proprium.corporis-christi-postcommunio", "s01", "w019", "Qui"),
    ("proprium.d-n-iesu-christi-regis-collecta", "s01", "w027", "Qui"),
    ("proprium.d-n-iesu-christi-regis-postcommunio", "s01", "w022", "Qui"),
    ("proprium.dominica-i-adventus-collecta", "s01", "w021", "Qui"),
    ("proprium.dominica-ii-adventus-collecta", "s01", "w019", "Qui"),
    ("proprium.dominica-iii-adventus-collecta", "s01", "w016", "Qui"),
    ("proprium.dominica-infra-octavam-nativitatis-collecta", "s01", "w020", "Qui"),
    ("proprium.dominica-iv-adventus-collecta", "s01", "w026", "Qui"),
    ("proprium.dominica-xviii-post-pentecosten-epistola", "s01", "w055", "qui"),
    ("proprium.dominica-xxii-post-pentecosten-postcommunio", "s01", "w021", "Qui"),
    ("proprium.feria-v-in-cena-domini-collecta", "s01", "w043", "Qui"),
    ("proprium.nativitas-domini-in-die-postcommunio", "s01", "w022", "Qui"),
    ("proprium.nativitas-domini-in-nocte-collecta", "s01", "w026", "Qui"),
    ("proprium.nativitas-domini-in-nocte-postcommunio", "s01", "w025", "Qui"),
    ("proprium.nativitas-domini-in-nocte-secreta", "s01", "w027", "Qui"),
    (
        "proprium.pretiosissimi-sanguinis-domini-nostri-iesu-christi-postcommunio",
        "s01",
        "w024",
        "Qui",
    ),
    ("proprium.sacratissimi-cordis-iesu-postcommunio", "s01", "w021", "Qui"),
    ("proprium.sancta-familia-collecta", "s01", "w027", "Qui"),
    ("proprium.sancta-familia-postcommunio", "s01", "w034", "Qui"),
    ("proprium.sancti-ioseph-sponsi-beatae-mariae-virginis-collecta", "s01", "w019", "Qui"),
    ("proprium.septem-dolorum-beatae-mariae-virginis-collecta", "s01", "w043", "Qui"),
    ("proprium.septem-dolorum-beatae-mariae-virginis-postcommunio", "s01", "w023", "Qui"),
    ("proprium.septem-dolorum-beatae-mariae-virginis-secreta", "s01", "w038", "Qui"),
    ("proprium.vigilia-nativitatis-secreta", "s01", "w019", "Qui"),
)

ROSARY_POSTCOMMUNION = "proprium.beatae-mariae-virginis-a-rosario-postcommunio"
EPISTLE_XVIII = "proprium.dominica-xviii-post-pentecosten-epistola"
CONCLUSION_BOUNDARIES = tuple(case for case in ADJUDICATED_BOUNDARIES if case[0] != EPISTLE_XVIII)

RELATIVES = (
    [(case, "który") for case in LOWERCASE_RELATIVES]
    + [(case, "Który") for case in INITIAL_CAPITALS]
    + [
        (case, "Który" if case in CONCLUSION_BOUNDARIES else "który")
        for case in ADJUDICATED_BOUNDARIES
    ]
)
MARK_SECRET = "proprium.sancti-marci-evangelistae-secreta"


def case_id(case):
    text, segment, word, _ = case
    return f"{text}-{segment}-{word}"


def document(text, language=None):
    prefix = ROOT if language is None else ROOT / "languages" / language
    return json.loads((prefix / "texts" / (text.replace(".", "/") + ".json")).read_text())


@pytest.fixture(scope="module")
def documents():
    texts = sorted({case[0] for case, _ in RELATIVES})
    return {text: (document(text), document(text, "pl")) for text in texts}


def assert_relative(core, layer, case, expected):
    text, sid, wid, form = case
    assert core["id"] == layer["text"] == text
    assert layer["language"] == "pl"
    (segment,) = [segment for segment in core["segments"] if segment["id"] == sid]
    (word,) = [word for word in segment["words"] if word["id"] == wid]
    assert (word["form"], word["lemma"], word["morph"]) == (
        form,
        "qui",
        {"pos": "pron", "case": "nom", "number": "sg", "gender": "m"},
    )
    assert not any(wid in group["words"] for group in layer["segments"][sid].get("alignments", []))
    assert layer["words"][wid]["gloss"] == expected, "Polish relative caption case"


def test_finite_relative_inventory_and_familiar_boundary():
    assert [
        len(group) for group in (LOWERCASE_RELATIVES, INITIAL_CAPITALS, ADJUDICATED_BOUNDARIES)
    ] == [293, 5, 30]
    assert len({case[:3] for case, _ in RELATIVES}) == 328
    assert sum(expected == "który" for _, expected in RELATIVES) == 294
    assert sum(expected == "Który" for _, expected in RELATIVES) == 34
    assert len(CONCLUSION_BOUNDARIES) == 29
    provenance = json.loads((ROOT / "languages/pl/translation-provenance.json").read_text())
    sites = {site["site"]: site for site in provenance["sites"]}
    for text, sid, _, _ in (*LOWERCASE_RELATIVES, *ADJUDICATED_BOUNDARIES):
        assert sites[f"{text}.{sid}.pl"]["familiar_core"] is False
    assert sites["litaniae.sanctissimi-nominis-iesu.s146.pl"]["familiar_core"] is True


@pytest.mark.parametrize("case,expected", RELATIVES, ids=[case_id(case) for case, _ in RELATIVES])
def test_reviewed_relative_caption(documents, case, expected):
    assert_relative(*documents[case[0]], case, expected)


def find_case(text, word):
    matches = [
        (case, expected) for case, expected in RELATIVES if case[0] == text and case[2] == word
    ]
    assert len(matches) == 1
    return matches[0]


CAPTION_CONTROLS = [
    ("proprium.sancti-marci-evangelistae-collecta", "w029", "Który"),
    ("ordinarium.libera-nos", "w064", "Który"),
    ("litaniae.sanctissimi-nominis-iesu", "w473", "który"),
    ("ordinarium.qui-pridie-in-cena-domini", "w001", "który"),
    ("proprium.nativitas-domini-in-die-epistola", "w106", "który"),
    ("proprium.beatae-mariae-virginis-a-rosario-postcommunio", "w024", "który"),
    ("proprium.dominica-xviii-post-pentecosten-epistola", "w055", "Który"),
]


@pytest.mark.parametrize(
    "text,word,wrong",
    CAPTION_CONTROLS,
    ids=[f"{text}-{word}" for text, word, _ in CAPTION_CONTROLS],
)
def test_case_guard_rejects_only_the_changed_caption(documents, text, word, wrong):
    case, expected = find_case(text, word)
    core, layer = documents[text]
    assert_relative(core, layer, case, expected)
    broken = deepcopy(layer)
    broken["words"][word]["gloss"] = wrong
    with pytest.raises(AssertionError) as caught:
        assert_relative(core, broken, case, expected)
    assert str(caught.value).splitlines()[0] == "Polish relative caption case"
    assert_relative(core, layer, case, expected)


def previous_word(core, word):
    words = [
        word
        for segment in core["segments"]
        if segment["type"] == "verse"
        for word in segment["words"]
    ]
    (index,) = [index for index, item in enumerate(words) if item["id"] == word]
    assert index > 0
    return words[index - 1]


def test_latin_colon_does_not_decide_polish_sentence_boundary(documents):
    for text, word in [
        ("proprium.sancti-marci-evangelistae-collecta", "w029"),
        ("proprium.beatae-mariae-virginis-a-rosario-postcommunio", "w024"),
    ]:
        case, expected = find_case(text, word)
        core, layer = documents[text]
        assert previous_word(core, word)["post"] == ":"
        assert_relative(core, layer, case, expected)
    mark = documents["proprium.sancti-marci-evangelistae-collecta"][1]
    rosary = documents["proprium.beatae-mariae-virginis-a-rosario-postcommunio"][1]
    assert "Syna Twojego, który z Tobą" in mark["segments"]["s01"]["translation"]
    assert ". Który żyjesz" in rosary["segments"]["s01"]["translation"]


def test_latin_period_does_not_decide_polish_sentence_boundary(documents):
    for text, word in [
        ("ordinarium.libera-nos", "w064"),
        ("proprium.dominica-xvii-post-pentecosten-epistola", "w068"),
    ]:
        case, expected = find_case(text, word)
        core, layer = documents[text]
        assert previous_word(core, word)["post"] == "."
        assert_relative(core, layer, case, expected)
    libera = documents["ordinarium.libera-nos"][1]
    epistle = documents["proprium.dominica-xvii-post-pentecosten-epistola"][1]
    assert libera["segments"]["s08"]["translation"].endswith("Syna,")
    assert libera["segments"]["s10"]["translation"].startswith("który,")
    assert ". On jest błogosławiony" in epistle["segments"]["s01"]["translation"]


def assert_conclusion_prose_boundary(core, layer, case):
    assert_relative(core, layer, case, "Który")
    _, sid, wid, _ = case
    (segment,) = [segment for segment in core["segments"] if segment["id"] == sid]
    assert segment["speaker"] == "sacerdos"
    assert previous_word(core, wid)["post"] == ":"
    (index,) = [index for index, word in enumerate(segment["words"]) if word["id"] == wid]
    following = segment["words"][index + 1]["form"]
    assert following in {"vivis", "tecum"}
    phrase = ". Który żyjesz " if following == "vivis" else ". Który z Tobą żyje "
    assert phrase in layer["segments"][sid]["translation"], "Polish prose conclusion boundary"


@pytest.mark.parametrize(
    "case", CONCLUSION_BOUNDARIES, ids=[case_id(case) for case in CONCLUSION_BOUNDARIES]
)
def test_conclusion_caption_preserves_separate_prose_boundary(documents, case):
    assert_conclusion_prose_boundary(*documents[case[0]], case)


def assert_epistle_caption_and_prose(core, layer, case):
    assert case == (EPISTLE_XVIII, "s01", "w055", "qui")
    assert_relative(core, layer, case, "który")
    assert previous_word(core, "w055")["post"] == ","
    (segment,) = [segment for segment in core["segments"] if segment["id"] == "s01"]
    words = {word["id"]: word for word in segment["words"]}
    assert segment["speaker"] == "sacerdos"
    assert (words["w056"]["form"], words["w056"]["lemma"], words["w056"]["morph"]) == (
        "et",
        "et",
        {"pos": "conj"},
    )
    assert words["w057"]["form"] == "confirmábit"
    assert not any(
        "w056" in group["words"] for group in layer["segments"]["s01"].get("alignments", [])
    )
    assert layer["words"]["w056"]["gloss"] == "też", "Epistle additive caption"
    assert ". On też utwierdzi was" in layer["segments"]["s01"]["translation"], (
        "Epistle prose sentence boundary"
    )


def test_epistle_relative_and_additive_caption_preserve_prose_sentence(documents):
    case, expected = find_case(EPISTLE_XVIII, "w055")
    assert expected == "który"
    assert_epistle_caption_and_prose(*documents[EPISTLE_XVIII], case)


BOUNDARY_CONTROLS = [
    (
        "conclusion-prose-capital",
        ROSARY_POSTCOMMUNION,
        "w024",
        "translation",
        ". Który ",
        ". który ",
        "Polish prose conclusion boundary",
    ),
    (
        "conclusion-prose-period",
        ROSARY_POSTCOMMUNION,
        "w024",
        "translation",
        ". Który ",
        ", Który ",
        "Polish prose conclusion boundary",
    ),
    (
        "epistle-additive",
        EPISTLE_XVIII,
        "w055",
        "gloss",
        "też",
        "i",
        "Epistle additive caption",
    ),
    (
        "epistle-prose-capital",
        EPISTLE_XVIII,
        "w055",
        "translation",
        ". On też ",
        ". on też ",
        "Epistle prose sentence boundary",
    ),
    (
        "epistle-prose-period",
        EPISTLE_XVIII,
        "w055",
        "translation",
        ". On też ",
        ", On też ",
        "Epistle prose sentence boundary",
    ),
]


@pytest.mark.parametrize(
    "defect,text,word,field,before,after,message",
    BOUNDARY_CONTROLS,
    ids=[control[0] for control in BOUNDARY_CONTROLS],
)
def test_boundary_guard_rejects_only_the_changed_field(
    documents, defect, text, word, field, before, after, message
):
    case, expected = find_case(text, word)
    assert expected == ("Który" if text == ROSARY_POSTCOMMUNION else "który")
    core, layer = documents[text]
    saved = deepcopy(layer)
    verify = (
        assert_conclusion_prose_boundary
        if text == ROSARY_POSTCOMMUNION
        else assert_epistle_caption_and_prose
    )
    verify(core, layer, case)
    broken = deepcopy(layer)
    if field == "gloss":
        assert defect == "epistle-additive"
        assert broken["words"]["w056"]["gloss"] == before
        broken["words"]["w056"]["gloss"] = after
    else:
        assert field == "translation"
        phrase = broken["segments"]["s01"]["translation"]
        assert phrase.count(before) == 1
        broken["segments"]["s01"]["translation"] = phrase.replace(before, after, 1)
    with pytest.raises(AssertionError) as caught:
        verify(core, broken, case)
    assert str(caught.value).splitlines()[0] == message
    verify(core, layer, case)
    assert layer == saved


def assert_mark_petition(core, layer):
    assert core["id"] == layer["text"] == MARK_SECRET
    assert layer["language"] == "pl"
    words = {word["id"]: word for segment in core["segments"] for word in segment["words"]}
    assert words["w011"]["lemma"] == "ut"
    assert words["w021"]["lemma"] == "intercessio"
    assert words["w021"]["morph"]["case"] == "nom"
    assert words["w019"]["morph"]["case"] == "acc"
    assert words["w028"]["head"] == "w019"
    assert (words["w027"]["lemma"], words["w027"]["morph"]) == (
        "reddo",
        {
            "conj": 3,
            "mood": "subj",
            "number": "sg",
            "person": 3,
            "pos": "verb",
            "tense": "pres",
            "voice": "act",
        },
    )
    assert layer["words"]["w011"]["gloss"] == "aby"
    assert layer["words"]["w021"]["gloss"] == "wstawiennictwo"
    assert not any(
        "w027" in group["words"] for group in layer["segments"]["s01"].get("alignments", [])
    )
    assert layer["words"]["w027"]["gloss"] == "uczyniło", "Mark petition keeps subjunctive request"


def test_mark_intercession_remains_a_petition(documents):
    assert_mark_petition(*documents[MARK_SECRET])


def test_mark_petition_guard_rejects_future_caption(documents):
    core, layer = documents[MARK_SECRET]
    assert_mark_petition(core, layer)
    broken = deepcopy(layer)
    broken["words"]["w027"]["gloss"] = "uczyni"
    with pytest.raises(AssertionError) as caught:
        assert_mark_petition(core, broken)
    assert str(caught.value).splitlines()[0] == "Mark petition keeps subjunctive request"
    assert_mark_petition(core, layer)

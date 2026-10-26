"""Closed Compendium HTML identity assertions, not private-original verification."""

import hashlib
import re
from copy import deepcopy
from typing import TypedDict

from checks.normalize import substantive

CONTRACT = "compendium-html-1"
ORIGINAL_SHA = "a35594fda5cf56333ff59388de407e152f5cd41e012d68e34f2bf75bbfa691a8"
ITEM = "item.compendium-of-the-catechism-2005.html"
EDITION = "edition.compendium-of-the-catechism-of-the-catholic-church"
WORK = "work.compendium-of-the-catechism-of-the-catholic-church"
URL = "https://www.vatican.va/archive/compendium_ccc/documents/archive_2005_compendium-ccc_en.html"
FIELDS = {
    "contract",
    "use",
    "digital_item",
    "sha256",
    "media_type",
    "section",
    "container_sha256",
    "reading_sha256",
}


class Scope(TypedDict):
    use: str
    witness: str
    address: dict
    claim: str
    section: str
    container: str
    coverage: dict
    words: list[str]
    reading: str


# These seven literal scopes assert previously inspected source identities.
# The complete modern publication is not shipped or read by this module.
# Sub tuum has no graph witness here; its separate source claim is not upgraded.
SCOPES: dict[str, Scope] = {
    "orationes.actus-contritionis": {
        "use": "use.orationes.actus-contritionis.compendium-2005",
        "witness": "witness.orationes.actus-contritionis.compendium-2005",
        "address": {"kind": "text", "text": "orationes.actus-contritionis"},
        "claim": "The complete 52-word Latin prayer and its printed boundary in this section.",
        "section": "APPENDIX / A) COMMON PRAYERS / Actus contritionis",
        "container": ("e27ba4945af6172526256295dd6ab3fd92f31437470c23a1a0274647386ef9c1"),
        "coverage": {"kind": "full"},
        "words": [
            "w001",
            "w002",
            "w003",
            "w004",
            "w005",
            "w006",
            "w007",
            "w008",
            "w009",
            "w010",
            "w011",
            "w012",
            "w013",
            "w014",
            "w015",
            "w016",
            "w017",
            "w018",
            "w019",
            "w020",
            "w021",
            "w022",
            "w023",
            "w024",
            "w025",
            "w026",
            "w027",
            "w028",
            "w029",
            "w030",
            "w031",
            "w032",
            "w033",
            "w034",
            "w035",
            "w036",
            "w037",
            "w038",
            "w039",
            "w040",
            "w041",
            "w042",
            "w043",
            "w044",
            "w045",
            "w046",
            "w047",
            "w048",
            "w049",
            "w050",
            "w051",
            "w052",
        ],
        "reading": "Deus meus, ex toto corde pænitet me "
        "ómnium meórum peccatórum, éaque "
        "detéstor, quia peccándo, non solum "
        "pœnas a te iuste statútas proméritus "
        "sum, sed præsértim quia offéndi te, "
        "summum bonum, ac dignum qui super "
        "ómnia diligáris. Ídeo fírmiter "
        "propóno, adiuvánte grátia tua, de "
        "cétero me non peccatúrum peccandíque "
        "occasiónes próximas fugitúrum. "
        "Amen.",
    },
    "orationes.angele-dei": {
        "use": "use.orationes.angele-dei.compendium-2005",
        "witness": "witness.orationes.angele-dei.compendium-2005",
        "address": {"kind": "text", "text": "orationes.angele-dei"},
        "claim": "The complete 17-word Latin prayer and its printed boundary in this section.",
        "section": "APPENDIX / A) COMMON PRAYERS / Angele Dei",
        "container": ("99a21c413cd38034b29a382159ad9e88af798fee6594770889078817c1b61529"),
        "coverage": {"kind": "full"},
        "words": [
            "w001",
            "w002",
            "w003",
            "w004",
            "w005",
            "w006",
            "w007",
            "w008",
            "w009",
            "w010",
            "w011",
            "w012",
            "w013",
            "w014",
            "w015",
            "w016",
            "w017",
        ],
        "reading": "Ángele Dei, qui custos es mei, me, tibi "
        "commíssum pietáte supérna, illúmina, "
        "custódi, rege et gubérna. Amen.",
    },
    "orationes.anima-christi": {
        "use": "use.orationes.anima-christi.compendium-2005",
        "witness": "witness.orationes.anima-christi.compendium-2005",
        "address": {"kind": "text", "text": "orationes.anima-christi"},
        "claim": "The complete 64-word Latin prayer and its printed boundary in this section.",
        "section": "APPENDIX / A) COMMON PRAYERS / Anima Christi",
        "container": ("56ac7916bb4b409dcdc8dea80de150e03302a980e2d0bcbdfc6a436429e93aa9"),
        "coverage": {"kind": "full"},
        "words": [
            "w001",
            "w002",
            "w003",
            "w004",
            "w005",
            "w006",
            "w007",
            "w008",
            "w009",
            "w010",
            "w011",
            "w012",
            "w013",
            "w014",
            "w015",
            "w016",
            "w017",
            "w018",
            "w019",
            "w020",
            "w021",
            "w022",
            "w023",
            "w024",
            "w025",
            "w026",
            "w027",
            "w028",
            "w029",
            "w030",
            "w031",
            "w032",
            "w033",
            "w034",
            "w035",
            "w036",
            "w037",
            "w038",
            "w039",
            "w040",
            "w041",
            "w042",
            "w043",
            "w044",
            "w045",
            "w046",
            "w047",
            "w048",
            "w049",
            "w050",
            "w051",
            "w052",
            "w053",
            "w054",
            "w055",
            "w056",
            "w057",
            "w058",
            "w059",
            "w060",
            "w061",
            "w062",
            "w063",
            "w064",
        ],
        "reading": "Ánima Christi, sanctífica me. Corpus "
        "Christi, salva me. Sanguis Christi, "
        "inébria me. Aqua láteris Christi, lava "
        "me. Pássio Christi, confórta me. O bone "
        "Iesu, exáudi me. Intra tua vúlnera "
        "abscónde me. Ne permíttas me separári a "
        "te. Ab hoste malígno defénde me. In hora "
        "mortis meæ voca me. Et iube me veníre ad "
        "te, ut cum Sanctis tuis laudem te in "
        "sæcula sæculórum. Amen",
    },
    "orationes.magnificat": {
        "use": "use.orationes.magnificat.compendium-2005",
        "witness": "witness.orationes.magnificat.compendium-2005",
        "address": {"kind": "word", "text": "orationes.magnificat", "word": "w090"},
        "claim": "The complete Latin doxology only, w090–w109 "
        "from Gloria Patri through Amen; not the "
        "preceding canticle recension.",
        "section": "APPENDIX / A) COMMON PRAYERS / Magnificat",
        "container": ("f0eb968837f98ec840ecb191f8caf5df57048be0b67ebfcccb4ed63bda2c3577"),
        "coverage": {
            "kind": "words",
            "words": [
                "w090",
                "w091",
                "w092",
                "w093",
                "w094",
                "w095",
                "w096",
                "w097",
                "w098",
                "w099",
                "w100",
                "w101",
                "w102",
                "w103",
                "w104",
                "w105",
                "w106",
                "w107",
                "w108",
                "w109",
            ],
        },
        "words": [
            "w090",
            "w091",
            "w092",
            "w093",
            "w094",
            "w095",
            "w096",
            "w097",
            "w098",
            "w099",
            "w100",
            "w101",
            "w102",
            "w103",
            "w104",
            "w105",
            "w106",
            "w107",
            "w108",
            "w109",
        ],
        "reading": "Glória Patri et Fílio et Spirítui Sancto. "
        "Sicut erat in princípio, et nunc et semper, "
        "et in sæcula sæculórum. Amen.",
    },
    "orationes.memorare": {
        "use": "use.orationes.memorare.compendium-2005",
        "witness": "witness.orationes.memorare.compendium-2005",
        "address": {"kind": "text", "text": "orationes.memorare"},
        "claim": "The complete 53-word Latin prayer and its printed boundary in this section.",
        "section": "APPENDIX / A) COMMON PRAYERS / Memorare",
        "container": ("f9f0b418ad90fe13797029229b9d6797ec06bc5d6be2b5f9ae247d95c45dfa6e"),
        "coverage": {"kind": "full"},
        "words": [
            "w001",
            "w002",
            "w003",
            "w004",
            "w005",
            "w006",
            "w007",
            "w008",
            "w009",
            "w010",
            "w011",
            "w012",
            "w013",
            "w014",
            "w015",
            "w016",
            "w017",
            "w018",
            "w019",
            "w020",
            "w021",
            "w022",
            "w023",
            "w024",
            "w025",
            "w026",
            "w027",
            "w028",
            "w029",
            "w030",
            "w031",
            "w032",
            "w033",
            "w034",
            "w035",
            "w036",
            "w037",
            "w038",
            "w039",
            "w040",
            "w041",
            "w042",
            "w043",
            "w044",
            "w045",
            "w046",
            "w047",
            "w048",
            "w049",
            "w050",
            "w051",
            "w052",
            "w053",
        ],
        "reading": "Memoráre, o piíssima Virgo María, non esse "
        "audítum a sæculo, quemquam ad tua curréntem "
        "præsídia, tua implorántem auxília, tua "
        "peténtem suffrágia, esse derelíctum. Ego tali "
        "animátus confidéntia, ad te, Virgo Vírginum, "
        "Mater, curro, ad te vénio, coram te gemens "
        "peccátor assísto. Noli, Mater Verbi, verba mea "
        "despícere; sed áudi propítia et exáudi. Amen.",
    },
    "orationes.symbolum-apostolorum": {
        "use": "use.orationes.symbolum-apostolorum.compendium-2005",
        "witness": ("witness.orationes.symbolum-apostolorum.compendium-2005"),
        "address": {"kind": "word", "text": "orationes.symbolum-apostolorum", "word": "w001"},
        "claim": "The Latin Creed only through w060, "
        "vivos et mortuos, before Et in "
        "Spiritum Sanctum; not the selected "
        "final group beginning Credo.",
        "section": "The Profession of the Christian Faith / The Creed / Symbolum Apostolicum",
        "container": ("ee5c6b389c45aaf3fc6476a3c002bb123fa535f5442010e75c86de61632fd8e2"),
        "coverage": {
            "kind": "words",
            "words": [
                "w001",
                "w002",
                "w003",
                "w004",
                "w005",
                "w006",
                "w007",
                "w008",
                "w009",
                "w010",
                "w011",
                "w012",
                "w013",
                "w014",
                "w015",
                "w016",
                "w017",
                "w018",
                "w019",
                "w020",
                "w021",
                "w022",
                "w023",
                "w024",
                "w025",
                "w026",
                "w027",
                "w028",
                "w029",
                "w030",
                "w031",
                "w032",
                "w033",
                "w034",
                "w035",
                "w036",
                "w037",
                "w038",
                "w039",
                "w040",
                "w041",
                "w042",
                "w043",
                "w044",
                "w045",
                "w046",
                "w047",
                "w048",
                "w049",
                "w050",
                "w051",
                "w052",
                "w053",
                "w054",
                "w055",
                "w056",
                "w057",
                "w058",
                "w059",
                "w060",
            ],
        },
        "words": [
            "w001",
            "w002",
            "w003",
            "w004",
            "w005",
            "w006",
            "w007",
            "w008",
            "w009",
            "w010",
            "w011",
            "w012",
            "w013",
            "w014",
            "w015",
            "w016",
            "w017",
            "w018",
            "w019",
            "w020",
            "w021",
            "w022",
            "w023",
            "w024",
            "w025",
            "w026",
            "w027",
            "w028",
            "w029",
            "w030",
            "w031",
            "w032",
            "w033",
            "w034",
            "w035",
            "w036",
            "w037",
            "w038",
            "w039",
            "w040",
            "w041",
            "w042",
            "w043",
            "w044",
            "w045",
            "w046",
            "w047",
            "w048",
            "w049",
            "w050",
            "w051",
            "w052",
            "w053",
            "w054",
            "w055",
            "w056",
            "w057",
            "w058",
            "w059",
            "w060",
        ],
        "reading": "Credo in Deum Patrem omnipoténtem, "
        "Creatorem cæli et terræ, et in "
        "Iesum Christum, Filium Eius "
        "unicum, Dominum nostrum, qui "
        "concéptus est de Spíritu Sancto, "
        "natus ex Maria Virgine, passus sub "
        "Póntio Piláto, crucifixus, "
        "mórtuus, et sepúltus, descéndit ad "
        "ínferos, tértia die resurréxit a "
        "mórtuis, ascéndit ad cælos, sedet "
        "ad déxteram Dei Patris "
        "omnipoténtis, inde ventúrus est "
        "iudicáre vivos et mórtuos.",
    },
    "orationes.te-deum": {
        "use": "use.orationes.te-deum.compendium-2005",
        "witness": "witness.orationes.te-deum.compendium-2005",
        "address": {"kind": "text", "text": "orationes.te-deum"},
        "claim": "The complete 194-word Latin prayer and its printed boundary in this section.",
        "section": "APPENDIX / A) COMMON PRAYERS / Te Deum",
        "container": ("ab5056bb32ecfff8ebb491c119ba7018879aa7efed85185832eefd661a0e1105"),
        "coverage": {"kind": "full"},
        "words": [
            "w001",
            "w002",
            "w003",
            "w004",
            "w005",
            "w006",
            "w007",
            "w008",
            "w009",
            "w010",
            "w011",
            "w012",
            "w013",
            "w014",
            "w015",
            "w016",
            "w017",
            "w018",
            "w019",
            "w020",
            "w021",
            "w022",
            "w023",
            "w024",
            "w025",
            "w026",
            "w027",
            "w028",
            "w029",
            "w030",
            "w031",
            "w032",
            "w033",
            "w034",
            "w035",
            "w036",
            "w037",
            "w038",
            "w039",
            "w040",
            "w041",
            "w042",
            "w043",
            "w044",
            "w045",
            "w046",
            "w047",
            "w048",
            "w049",
            "w050",
            "w051",
            "w052",
            "w053",
            "w054",
            "w055",
            "w056",
            "w057",
            "w058",
            "w059",
            "w060",
            "w061",
            "w062",
            "w063",
            "w064",
            "w065",
            "w066",
            "w067",
            "w068",
            "w069",
            "w070",
            "w071",
            "w072",
            "w073",
            "w074",
            "w075",
            "w076",
            "w077",
            "w078",
            "w079",
            "w080",
            "w081",
            "w082",
            "w083",
            "w084",
            "w085",
            "w086",
            "w087",
            "w088",
            "w089",
            "w090",
            "w091",
            "w092",
            "w093",
            "w094",
            "w095",
            "w096",
            "w097",
            "w098",
            "w099",
            "w100",
            "w101",
            "w102",
            "w103",
            "w104",
            "w105",
            "w106",
            "w107",
            "w108",
            "w109",
            "w110",
            "w111",
            "w112",
            "w113",
            "w114",
            "w115",
            "w116",
            "w117",
            "w118",
            "w119",
            "w120",
            "w121",
            "w122",
            "w123",
            "w124",
            "w125",
            "w126",
            "w127",
            "w128",
            "w129",
            "w130",
            "w131",
            "w132",
            "w133",
            "w134",
            "w135",
            "w136",
            "w137",
            "w138",
            "w139",
            "w140",
            "w141",
            "w142",
            "w143",
            "w144",
            "w145",
            "w146",
            "w147",
            "w148",
            "w149",
            "w150",
            "w151",
            "w152",
            "w153",
            "w154",
            "w155",
            "w156",
            "w157",
            "w158",
            "w159",
            "w160",
            "w161",
            "w162",
            "w163",
            "w164",
            "w165",
            "w166",
            "w167",
            "w168",
            "w169",
            "w170",
            "w171",
            "w172",
            "w173",
            "w174",
            "w175",
            "w176",
            "w177",
            "w178",
            "w179",
            "w180",
            "w181",
            "w182",
            "w183",
            "w184",
            "w185",
            "w186",
            "w187",
            "w188",
            "w189",
            "w190",
            "w191",
            "w192",
            "w193",
            "w194",
        ],
        "reading": "Te Deum laudámus: te Dóminum confitémur. Te "
        "ætérnum Patrem, omnis terra venerátur. tibi "
        "omnes ángeli, tibi cæli et univérsæ potestátes: "
        "tibi chérubim et séraphim incessábili voce "
        "proclámant: Sanctus, Sanctus, Sanctus, Dóminus "
        "Deus Sábaoth. Pleni sunt cæli et terra "
        "maiestátis glóriæ tuæ. Te gloriósus apostolórum "
        "chorus, te prophetárum laudábilis númerus, te "
        "mártyrum candidátus laudat exércitus. Te per "
        "orbem terrárum sancta confitétur Ecclésia, "
        "Patrem imménsæ maiestátis; venerándum tuum "
        "verum et únicum Fílium; Sanctum quoque "
        "Paráclitum Spíritum. Tu rex glóriæ, Christe. Tu "
        "Patris sempitérnus es Fílius. Tu, ad liberándum "
        "susceptúrus hóminem, non horruísti Vírginis "
        "úterum. Tu, devícto mortis acúleo, aperuísti "
        "credéntibus regna cælórum. Tu ad déxteram Dei "
        "sedes, in glória Patris. Iudex créderis esse "
        "ventúrus. Te ergo quæsumus, tuis fámulis "
        "súbveni, quos pretióso sánguine redemísti. "
        "Ætérna fac cum sanctis tuis in glória numerári. "
        "Salvum fac pópulum tuum, Dómine, et bénedic "
        "hereditáti tuæ. Et rege eos, et extólle illos "
        "usque in ætérnum. Per síngulos dies benedícimus "
        "te; et laudámus nomen tuum in sæculum, et in "
        "sæculum sæculi. Dignáre, Dómine, die isto sine "
        "peccáto nos custodíre. Miserére nostri, Dómine, "
        "miserére nostri. Fiat misericórdia tua, Dómine, "
        "super nos, quemádmodum sperávimus in te. In te, "
        "Dómine, sperávi: non confúndar in ætérnum.",
    },
}


def declarations(value):
    """One explicit, closed inventory; never infer a missing document."""
    if not isinstance(value, list) or len(value) != 1:
        raise ValueError("compendium HTML requires one explicit document")
    record = value[0]
    if not isinstance(record, dict) or set(record) != FIELDS:
        raise ValueError("compendium HTML declaration has unexpected fields")
    if any(not isinstance(record[key], str) or not record[key] for key in FIELDS):
        raise ValueError("compendium HTML declaration fields must be nonempty strings")
    if record["contract"] != CONTRACT:
        raise ValueError("compendium HTML contract differs")
    return deepcopy(value)


def resolve_documents(value, sources, *, witness, doc, transcript):
    """Assert exact source, literal reading and coverage; do not open the original."""
    records = declarations(value)
    record = records[0]
    if set(sources) != {record["use"]}:
        raise ValueError("compendium HTML must exactly inventory its source use")
    if (
        not isinstance(witness, dict)
        or not isinstance(doc, dict)
        or not isinstance(transcript, str)
    ):
        raise ValueError("compendium HTML requires witness, document and transcript")
    if not isinstance(doc.get("id"), str):
        raise ValueError("compendium HTML text identity must be a string")
    scope = SCOPES.get(doc.get("id"))
    if scope is None:
        raise ValueError("compendium HTML text is unsupported")
    expected = {
        "contract": CONTRACT,
        "use": scope["use"],
        "digital_item": ITEM,
        "sha256": ORIGINAL_SHA,
        "media_type": "text/html",
        "section": scope["section"],
        "container_sha256": scope["container"],
        "reading_sha256": hashlib.sha256((scope["reading"] + "\n").encode()).hexdigest(),
    }
    if record != expected:
        raise ValueError("compendium HTML source assertion differs")
    source = sources[record["use"]]
    use, item, edition, work = (source[key] for key in ("use", "digital_item", "edition", "work"))
    if (
        use.get("id") != scope["use"]
        or use.get("edition") != EDITION
        or use.get("digital_item") != ITEM
        or use.get("role") != "official_text"
        or use.get("address") != scope["address"]
        or use.get("claim") != scope["claim"]
        or use.get("locator") != {"section": scope["section"]}
        or use.get("evidence_sha256") != ORIGINAL_SHA
        or item.get("id") != ITEM
        or item.get("edition") != EDITION
        or item.get("kind") != "born-digital"
        or item.get("record_url") != URL
        or item.get("sha256") != ORIGINAL_SHA
        or "scan_url" in item
        or edition.get("id") != EDITION
        or edition.get("work") != WORK
        or work.get("id") != WORK
    ):
        raise ValueError("compendium HTML source-use/item identity differs")
    if (
        witness.get("id") != scope["witness"]
        or witness.get("text") != doc.get("id")
        or witness.get("use") != scope["use"]
        or witness.get("transcription") != "compendium-2005"
        or witness.get("coverage") != scope["coverage"]
    ):
        raise ValueError("compendium HTML witness identity or coverage differs")
    words = [word for segment in doc["segments"] for word in segment.get("words", [])]
    if scope["coverage"]["kind"] != "full":
        words = [word for word in words if word["id"] in scope["words"]]
    if [word["id"] for word in words] != scope["words"]:
        raise ValueError("compendium HTML selected word coverage differs")
    if substantive(" ".join(word["form"] for word in words)) != substantive(scope["reading"]):
        raise ValueError("compendium HTML selected substantive reading differs")
    for key, expected_header in (("source", URL), ("sha256", ORIGINAL_SHA)):
        headers = re.findall(rf"^#\s*{key}:\s*([^\r\n]*)", transcript, flags=re.MULTILINE)
        if headers != [expected_header]:
            raise ValueError("compendium HTML transcript source header differs")
    body = " ".join(
        line.strip()
        for line in transcript.splitlines()
        if line.strip() and not line.startswith("#")
    )
    if body != scope["reading"]:
        raise ValueError("compendium HTML literal transcript differs")
    return {
        "contract": "compendium-html-identity-inventory-1",
        "documents": {record["use"]: deepcopy(record)},
    }

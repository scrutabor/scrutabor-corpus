"""Two ministerial bodies retain their distinct Latin, realizations and evidence."""

import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from build_reader import bibliography, store
from build_reader.bibliography_bindings import (
    BindingError,
    collation_subject,
    digest,
    selected_text,
    transcript_digest,
    validate_bindings,
    witness_subject,
)
from checks import attribute
from checks.collate import collate, load_witness
from checks.language_packs import check_core, check_layer
from checks.raw_binding import BindingError as RawBindingError
from checks.raw_binding import resolve_binding
from checks.translation_basis import check as check_basis
from checks.translation_provenance import REVIEWS, canonical_hash, corpus_sites, source_payload
from checks.translation_provenance import check as check_provenance

ROOT = Path(__file__).resolve().parents[1]
TEXTS = {
    "ordinary": "ordinarium.iube-domne-benedicere",
    "palm": "ordinarium.iube-domne-benedicere-in-passione",
}
WORDS = [f"w{i:03}" for i in range(1, 29)]
SEGMENTS = ["s01", "s02", "s03", "s04"]
RAW = "witnesses/raw/do-44667ff/missa/Latin/Tempora/Quad6-0r.txt"
ARCHIVE = "do-tempora-quad6-0r"
BINDING = "do-ordinarium-iube-domne-benedicere-in-passione"
REVISION = "44667ff518b8ff1439780470828b39714f5306a2"
ARCHIVE_SHA = "5ef21bb1bb36d0be7bd01d872bd1142013a21e5a0718b28562c54a7b2bff97be"
WORD_FIELDS = (
    "id",
    "form",
    "lemma",
    "morph",
    "pre",
    "post",
    "head",
    "clause_head",
    "substantive",
    "ellipsis",
)
# Each row is form, lemma, complete morphology, following punctuation and head.
# The Ordinary is the base table. Only five Palm rows differ.
LATIN_ROWS = [
    (
        "Iube",
        "iubeo",
        {
            "pos": "verb",
            "mood": "imp",
            "tense": "pres",
            "voice": "act",
            "person": 2,
            "number": "sg",
            "conj": 2,
        },
        ",",
        None,
    ),  # w001
    (
        "domne",
        "dominus",
        {"pos": "noun", "case": "voc", "number": "sg", "gender": "m", "decl": 2},
        ",",
        None,
    ),  # w002
    (
        "benedícere",
        "benedico",
        {"pos": "verb", "mood": "inf", "tense": "pres", "voice": "act", "conj": 3},
        ".",
        None,
    ),  # w003
    (
        "Dóminus",
        "dominus",
        {"pos": "noun", "case": "nom", "number": "sg", "gender": "m", "decl": 2},
        None,
        None,
    ),  # w004
    (
        "sit",
        "sum",
        {
            "pos": "verb",
            "mood": "subj",
            "tense": "pres",
            "voice": "act",
            "person": 3,
            "number": "sg",
        },
        None,
        None,
    ),  # w005
    ("in", "in", {"pos": "prep", "governs": "abl"}, None, "w007"),  # w006
    (
        "corde",
        "cor",
        {"pos": "noun", "case": "abl", "number": "sg", "gender": "n", "decl": 3},
        None,
        None,
    ),  # w007
    (
        "tuo",
        "tuus",
        {"pos": "adj", "case": "abl", "number": "sg", "gender": "n"},
        ",",
        "w007",
    ),  # w008
    ("et", "et", {"pos": "conj"}, None, None),  # w009
    ("in", "in", {"pos": "prep", "governs": "abl"}, None, "w011"),  # w010
    (
        "lábiis",
        "labium",
        {"pos": "noun", "case": "abl", "number": "pl", "gender": "n", "decl": 2},
        None,
        None,
    ),  # w011
    (
        "tuis",
        "tuus",
        {"pos": "adj", "case": "abl", "number": "pl", "gender": "n"},
        ":",
        "w011",
    ),  # w012
    ("ut", "ut", {"pos": "conj"}, None, None),  # w013
    ("digne", "digne", {"pos": "adv"}, None, None),  # w014
    ("et", "et", {"pos": "conj"}, None, None),  # w015
    ("competénter", "competenter", {"pos": "adv"}, None, None),  # w016
    (
        "annúnties",
        "annuntio",
        {
            "pos": "verb",
            "mood": "subj",
            "tense": "pres",
            "voice": "act",
            "person": 2,
            "number": "sg",
            "conj": 1,
        },
        None,
        None,
    ),  # w017
    (
        "evangélium",
        "evangelium",
        {"pos": "noun", "case": "acc", "number": "sg", "gender": "n", "decl": 2},
        None,
        None,
    ),  # w018
    (
        "suum",
        "suus",
        {"pos": "adj", "case": "acc", "number": "sg", "gender": "n"},
        ":",
        "w018",
    ),  # w019
    ("in", "in", {"pos": "prep", "governs": "abl"}, None, "w021"),  # w020
    (
        "nómine",
        "nomen",
        {"pos": "noun", "case": "abl", "number": "sg", "gender": "n", "decl": 3},
        None,
        None,
    ),  # w021
    (
        "Patris",
        "pater",
        {"pos": "noun", "case": "gen", "number": "sg", "gender": "m", "decl": 3},
        ",",
        None,
    ),  # w022
    ("et", "et", {"pos": "conj"}, None, None),  # w023
    (
        "Fílii",
        "filius",
        {"pos": "noun", "case": "gen", "number": "sg", "gender": "m", "decl": 2},
        ",",
        None,
    ),  # w024
    ("et", "et", {"pos": "conj"}, None, None),  # w025
    (
        "Spíritus",
        "spiritus",
        {"pos": "noun", "case": "gen", "number": "sg", "gender": "m", "decl": 4},
        None,
        None,
    ),  # w026
    (
        "Sancti",
        "sanctus",
        {"pos": "adj", "case": "gen", "number": "sg", "gender": "m"},
        ".",
        "w026",
    ),  # w027
    ("Amen", "amen", {"pos": "intj"}, ".", None),  # w028
]
PALM_ROWS = {
    7: (
        "córdibus",
        "cor",
        {"pos": "noun", "case": "abl", "number": "pl", "gender": "n", "decl": 3},
        None,
        None,
    ),
    8: (
        "vestris",
        "vester",
        {"pos": "adj", "case": "abl", "number": "pl", "gender": "n"},
        ",",
        "w007",
    ),
    12: (
        "vestris",
        "vester",
        {"pos": "adj", "case": "abl", "number": "pl", "gender": "n"},
        ",",
        "w011",
    ),
    17: (
        "annuntiétis",
        "annuntio",
        {
            "pos": "verb",
            "mood": "subj",
            "tense": "pres",
            "voice": "act",
            "person": 2,
            "number": "pl",
            "conj": 1,
        },
        None,
        None,
    ),
    18: (
        "Evangélium",
        "evangelium",
        {"pos": "noun", "case": "acc", "number": "sg", "gender": "n", "decl": 2},
        None,
        None,
    ),
}

DIRECT = {
    "pl": {
        "6": "w",
        "9": "i",
        "10": "na",
        "13": "abyś",
        "14": "godnie",
        "15": "i",
        "16": "należycie",
        "17": "głosił",
        "20": "w",
        "21": "imię",
        "22": "Ojca",
        "23": "i",
        "24": "Syna",
        "25": "i",
        "26": "Ducha",
        "27": "Świętego",
        "28": "Amen",
    },
    "en": {
        "6": "in",
        "9": "and",
        "10": "on",
        "13": "so that",
        "20": "in",
        "21": "the name",
        "22": "of the Father",
        "23": "and",
        "24": "of the Son",
        "25": "and",
        "28": "amen",
    },
}
GROUPS = {
    "pl": [
        ("s01", [1, 2, 3], 1, "Udziel, księże, błogosławieństwa"),
        ("s02", [4, 5], 5, "Niech Pan będzie"),
        ("s02", [7, 8], 7, "twoim sercu"),
        ("s02", [11, 12], 11, "twoich ustach"),
        ("s02", [18, 19], 18, "Jego Ewangelię"),
    ],
    "en": [
        ("s01", [1, 2, 3], 3, "Please give your blessing, sir"),
        ("s02", [4, 5], 5, "may the Lord be"),
        ("s02", [7, 8], 7, "your heart"),
        ("s02", [11, 12], 11, "your lips"),
        ("s02", [14, 15, 16, 17], 17, "you may worthily and fittingly proclaim"),
        ("s02", [18, 19], 18, "His Gospel"),
        ("s03", [26, 27], 26, "of the Holy Spirit"),
    ],
}
PROSE = {
    "ordinary-pl": {
        "s01": "Udziel, księże, błogosławieństwa.",
        "s02": (
            "Niech Pan będzie w twoim sercu i na twoich ustach, abyś godnie i "
            "należycie głosił Jego Ewangelię:"
        ),
        "s03": "w imię Ojca i Syna, i Ducha Świętego.",
        "s04": "Amen.",
    },
    "ordinary-en": {
        "s01": "Please give your blessing, sir.",
        "s02": (
            "May the Lord be in your heart and on your lips, so that you may "
            "proclaim His Gospel worthily and fittingly:"
        ),
        "s03": "in the name of the Father, and of the Son, and of the Holy Spirit.",
        "s04": "Amen.",
    },
    "palm-pl": {
        "s01": "Udziel, księże, błogosławieństwa.",
        "s02": (
            "Niech Pan będzie w waszych sercach i na waszych ustach, abyście godnie "
            "i należycie głosili Jego Ewangelię:"
        ),
        "s03": "w imię Ojca i Syna, i Ducha Świętego.",
        "s04": "Amen.",
    },
    "palm-en": {
        "s01": "Please give your blessing, sir.",
        "s02": (
            "May the Lord be in your hearts and on your lips, so that you may "
            "proclaim His Gospel worthily and fittingly:"
        ),
        "s03": "in the name of the Father, and of the Son, and of the Holy Spirit.",
        "s04": "Amen.",
    },
}
CRITICAL_NOTES = {
    "ordinary-pl": {
        "w002": (
            "„Domne” jest skróconą formą zwrotu do ludzkiego adresata. Tutaj "
            "adresatem jest celebrans, dlatego w przekładzie pojawia się „księże”, "
            "a nie wezwanie do Boga."
        ),
        "w019": (
            "Ewangelia jest tutaj Ewangelią Pana. „Suum” odnosi się do „Dominus”, a "
            "nie do osoby, która będzie ją głosić."
        ),
        "w028": (
            "„Amen” potwierdza poprzedzające błogosławieństwo. W tym miejscu "
            "wypowiada je celebrans."
        ),
    },
    "ordinary-en": {
        "w002": (
            "Domne respectfully addresses the celebrant. The following Dominus "
            "names the divine Lord."
        ),
        "w019": "His refers to the Lord, not to the deacon who proclaims the Gospel.",
        "w028": "The missal includes this Amen in the celebrant’s response.",
    },
    "palm-pl": {
        "w002": (
            "„Domne” jest skróconą formą zwrotu do ludzkiego adresata. Tutaj "
            "adresatem jest celebrans, dlatego w przekładzie pojawia się „księże”, "
            "a nie wezwanie do Boga."
        ),
        "w019": (
            "Ewangelia jest tutaj Ewangelią Pana. „Suum” odnosi się do „Dominus”, a "
            "nie do osób, które będą ją głosić."
        ),
        "w028": (
            "„Amen” potwierdza poprzedzające błogosławieństwo. W tym miejscu "
            "odpowiadają nim duchowni, którzy poprosili o błogosławieństwo."
        ),
    },
    "palm-en": {
        "w002": (
            "Domne respectfully addresses the celebrant. The following Dominus "
            "names the divine Lord."
        ),
        "w019": "His refers to the Lord, not to the ministers who proclaim the Gospel.",
        "w028": "The rubric assigns this Amen to the ministers receiving the blessing.",
    },
}

TITLES = {
    "ordinary-pl": "Prośba diakona i błogosławieństwo przed Ewangelią",
    "palm-pl": "Prośba i błogosławieństwo przed śpiewem Męki Pańskiej",
    "ordinary-en": "Request and blessing before the Gospel",
    "palm-en": "Request and blessing before the Passion",
}
WITNESSES = [
    ("ordinary", "mr", "mr1962", "controlling"),
    ("ordinary", "vatican1962", "vatican1962", "approved_corroboration"),
    ("palm", "vatican1962", "vatican1962", "controlling"),
    ("palm", "mr-partial", "mr1962-partial", "approved_corroboration"),
    ("palm", "do", "do44667ff", "derived_comparison"),
]
RULINGS = {
    "ordinary": [
        ("w008", "tuo,", {"vatican1962": "tuo"}, "punctuation"),
        ("w018", "evangélium", {"vatican1962": "Evangélium"}, "capitalization"),
        ("w020", "in", {"vatican1962": "In"}, "capitalization"),
    ],
    "palm": [
        ("w001", "Iube,", {"do": "Jube,"}, "orthography"),
        ("w008", "vestris,", {"do": "vestris"}, "punctuation"),
        ("w012", "vestris,", {"do": "vestris:"}, "punctuation"),
        ("w018", "Evangélium", {"mr-partial": "evangélium"}, "capitalization"),
        ("w020", "in", {"do": "In"}, "capitalization"),
    ],
}
LATIN_CASES = [(kind, number) for kind in TEXTS for number in range(1, 29)]
LATIN_IDS = [f"{kind}-w{number:03}" for kind, number in LATIN_CASES]
LAYER_CASES = [(kind, language) for kind in TEXTS for language in ("pl", "en")]
LAYER_IDS = [f"{kind}-{language}" for kind, language in LAYER_CASES]
CAPTION_CASES = [
    (kind, language, number) for kind, language in LAYER_CASES for number in range(1, 29)
]
CAPTION_IDS = [f"{kind}-{language}-w{number:03}" for kind, language, number in CAPTION_CASES]
SITE_CASES = [(kind, language, sid) for kind, language in LAYER_CASES for sid in SEGMENTS]
SITE_IDS = [f"{kind}-{language}-{sid}" for kind, language, sid in SITE_CASES]


def read(root, relative):
    return json.loads((root / relative).read_text(encoding="utf-8"))


def core_path(kind):
    return f"texts/{TEXTS[kind].replace('.', '/', 1)}.json"


def core(kind, root=ROOT):
    return store.core(root, TEXTS[kind])


def layer(kind, language, root=ROOT):
    return store.raw_layer(root, language, TEXTS[kind])


def words(doc):
    return [word for segment in doc["segments"] for word in segment["words"]]


def expected_word(kind, number):
    form, lemma, morph, post, head = (
        PALM_ROWS.get(number, LATIN_ROWS[number - 1]) if kind == "palm" else LATIN_ROWS[number - 1]
    )
    result = {"id": f"w{number:03}", "form": form, "lemma": lemma, "morph": copy.deepcopy(morph)}
    if post is not None:
        result["post"] = post
    if head is not None:
        result["head"] = head
    return result


def assert_latin(doc, kind, number):
    wid = f"w{number:03}"
    found = [(s, w) for s in doc["segments"] for w in s["words"] if w["id"] == wid]
    assert len(found) == 1, f"latin-coverage:{kind}:{wid}"
    segment, word = found[0]
    sid = "s01" if number <= 3 else "s02" if number <= 19 else "s03" if number <= 27 else "s04"
    assert segment["id"] == sid, f"latin-segment:{kind}:{wid}"
    actual = {key: word[key] for key in WORD_FIELDS if key in word}
    assert actual == expected_word(kind, number), f"latin:{kind}:{wid}"


def expected_groups(kind, language):
    groups = copy.deepcopy(GROUPS[language])
    if kind == "palm":
        groups[2] = (*groups[2][:3], "waszych sercach" if language == "pl" else "your hearts")
        if language == "pl":
            groups[3] = (*groups[3][:3], "waszych ustach")
    return [
        (sid, {"words": [f"w{i:03}" for i in members], "anchor": f"w{anchor:03}", "gloss": gloss})
        for sid, members, anchor, gloss in groups
    ]


def expected_direct(kind, language):
    result = {f"w{int(number):03}": gloss for number, gloss in DIRECT[language].items()}
    if kind == "palm" and language == "pl":
        result.update(w013="abyście", w017="głosili")
    return result


def assert_caption(doc, target, kind, language, number):
    wid = f"w{number:03}"
    source_sid = next(s["id"] for s in doc["segments"] if any(w["id"] == wid for w in s["words"]))
    direct = "gloss" in target["words"].get(wid, {})
    groups = [
        (sid, group)
        for sid, segment in target["segments"].items()
        for group in segment.get("alignments", [])
        if wid in group["words"]
    ]
    assert int(direct) + len(groups) == 1, f"coverage:{kind}:{language}:{wid}"
    expected = expected_direct(kind, language)
    if wid in expected:
        assert direct and not groups, f"direct:{kind}:{language}:{wid}"
        assert target["words"][wid]["gloss"] == expected[wid], f"caption:{kind}:{language}:{wid}"
    else:
        selected = [(sid, g) for sid, g in expected_groups(kind, language) if wid in g["words"]]
        assert len(selected) == 1
        assert groups == selected and groups[0][0] == source_sid, f"caption:{kind}:{language}:{wid}"
        ids = [w["id"] for s in doc["segments"] if s["id"] == source_sid for w in s["words"]]
        group = groups[0][1]
        first = ids.index(group["words"][0])
        assert ids[first : first + len(group["words"])] == group["words"]
        assert group["anchor"] in group["words"]
        assert "reason" not in group


def scoped_rows(graph, field, kind):
    return [
        row
        for row in graph[field]
        if row.get("text", row.get("address", {}).get("text")) == TEXTS[kind]
    ]


def bound_subjects(root, graph, kind):
    return {
        row["id"]: witness_subject(root, row, graph, core(kind, root))
        for row in scoped_rows(graph, "witnesses", kind)
    }


@pytest.fixture
def ministry_corpus(tmp_path, monkeypatch):
    def write(relative, value):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def copy_file(relative):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)

    # Exact actual integrated data only. No fallback to private draft files.
    for kind, text in TEXTS.items():
        copy_file(core_path(kind))
        shutil.copytree(ROOT / "witnesses" / text, tmp_path / "witnesses" / text)
        for language in ("pl", "en"):
            copy_file(f"languages/{language}/{core_path(kind)}")
    copy_file(RAW)
    raw = read(ROOT, "witnesses/raw/bindings.json")
    raw["archives"] = {ARCHIVE: raw["archives"][ARCHIVE]}
    raw["bindings"] = {BINDING: raw["bindings"][BINDING]}
    write("witnesses/raw/bindings.json", raw)
    graph = read(ROOT, "bibliography/graph.json")
    for field in ("uses", "witnesses", "collations"):
        graph[field] = [
            row
            for row in graph[field]
            if row.get("text", row.get("address", {}).get("text")) in TEXTS.values()
        ]
    write("bibliography/graph.json", graph)
    for language in ("pl", "en"):
        base = f"languages/{language}"
        for name, field in (
            ("manifest", "texts"),
            ("translation-provenance", "sites"),
            ("bibliography", "uses"),
        ):
            doc = read(ROOT, f"{base}/{name}.json")
            if field == "texts":
                assert all(doc[field].count(text) == 1 for text in TEXTS.values())
                doc[field] = [text for text in doc[field] if text in TEXTS.values()]
                doc["titles"] = {text: doc["titles"][text] for text in doc[field]}
            else:
                doc[field] = [
                    row
                    for row in doc[field]
                    if row.get("text", row.get("address", {}).get("text")) in TEXTS.values()
                ]
            write(f"{base}/{name}.json", doc)
        basis = read(ROOT, f"{base}/translation-basis.json")
        basis["records"] = [
            {**row, "texts": [text for text in row["texts"] if text in TEXTS.values()]}
            for row in basis["records"]
            if set(row["texts"]) & set(TEXTS.values())
        ]
        write(f"{base}/translation-basis.json", basis)
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    return tmp_path


@pytest.mark.parametrize("kind,number", LATIN_CASES, ids=LATIN_IDS)
def test_every_latin_row_is_the_adopted_form_and_parse(kind, number):
    assert_latin(core(kind), kind, number)


@pytest.mark.parametrize("kind", TEXTS)
def test_four_segments_preserve_actor_boundaries_and_nonspoken_cross(kind):
    doc = core(kind)
    assert doc["id"] == TEXTS[kind]
    assert [s["id"] for s in doc["segments"]] == SEGMENTS
    source = doc["editorial"]["source"]
    assert source["witnesses"] == f"witnesses/{TEXTS[kind]}/"
    assert source["apparatus"] == f"witnesses/{TEXTS[kind]}/apparatus.json"
    assert source["method"].strip()
    assert [len(s["words"]) for s in doc["segments"]] == [3, 16, 8, 1]
    assert [w["id"] for w in words(doc)] == WORDS
    assert [s["speaker"] for s in doc["segments"]] == [
        "minister",
        "sacerdos",
        "sacerdos",
        "sacerdos" if kind == "ordinary" else "minister",
    ], f"actors:{kind}"
    assert all(s["type"] == "verse" for s in doc["segments"])
    for segment in doc["segments"]:
        assert not {"voice", "delivery", "participation"} & set(segment), f"ritual:{kind}"
    assert all(
        "+" not in str(w.get(key, "")) for w in words(doc) for key in ("form", "pre", "post")
    )


@pytest.mark.parametrize("kind", TEXTS)
def test_human_request_divine_subject_and_purpose_referents_stay_distinct(kind):
    by_id = {w["id"]: w for w in words(core(kind))}
    assert (by_id["w002"]["form"], by_id["w002"]["morph"]["case"]) == ("domne", "voc")
    assert (by_id["w004"]["form"], by_id["w004"]["morph"]["case"]) == ("Dóminus", "nom")
    assert by_id["w001"]["morph"]["mood"] == "imp"
    assert by_id["w003"]["morph"]["mood"] == "inf" and "ellipsis" not in by_id["w003"]
    assert (by_id["w005"]["morph"]["person"], by_id["w005"]["morph"]["number"]) == (3, "sg")
    recipient = "sg" if kind == "ordinary" else "pl"
    assert (by_id["w017"]["morph"]["person"], by_id["w017"]["morph"]["number"]) == (2, recipient)
    assert by_id["w017"]["morph"]["mood"] == "subj"
    assert by_id["w007"]["morph"]["number"] == recipient
    assert by_id["w008"]["lemma"] == ("tuus" if kind == "ordinary" else "vester")
    assert by_id["w012"]["lemma"] == by_id["w008"]["lemma"]
    assert by_id["w008"]["head"] == "w007" and by_id["w012"]["head"] == "w011"
    assert (by_id["w018"]["morph"]["case"], by_id["w018"]["morph"]["number"]) == ("acc", "sg")
    assert by_id["w019"]["head"] == "w018"
    assert by_id["w019"]["morph"] == {"pos": "adj", "case": "acc", "number": "sg", "gender": "n"}


@pytest.mark.parametrize("kind,language,number", CAPTION_CASES, ids=CAPTION_IDS)
def test_every_source_word_has_its_one_contextual_realization(kind, language, number):
    assert_caption(core(kind), layer(kind, language), kind, language, number)


@pytest.mark.parametrize("kind,language", LAYER_CASES, ids=LAYER_IDS)
def test_complete_ordered_language_records_and_exact_group_contract(kind, language):
    doc, target = core(kind), layer(kind, language)
    assert check_core(doc) == []
    assert list(target["words"]) == WORDS, f"word-records:{kind}:{language}"
    assert check_layer(doc, target, store.layer_path(ROOT, language, TEXTS[kind])) == []
    actual = [
        (sid, group)
        for sid, seg in target["segments"].items()
        for group in seg.get("alignments", [])
    ]
    assert actual == expected_groups(kind, language)
    assert target["about"].strip()


@pytest.mark.parametrize("kind,language,sid", SITE_CASES, ids=SITE_IDS)
def test_each_whole_prose_segment_preserves_its_adopted_assertions(kind, language, sid):
    assert (
        layer(kind, language)["segments"][sid]["translation"] == PROSE[f"{kind}-{language}"][sid]
    ), f"prose:{kind}:{language}:{sid}"


@pytest.mark.parametrize("kind,language", LAYER_CASES, ids=LAYER_IDS)
def test_minimal_notes_keep_human_divine_and_amen_referents_clear(kind, language):
    target = layer(kind, language)
    for wid, expected in CRITICAL_NOTES[f"{kind}-{language}"].items():
        assert target["words"][wid]["explanation"] == expected, (
            f"referent-note:{kind}:{language}:{wid}"
        )


@pytest.mark.parametrize("kind,language", LAYER_CASES, ids=LAYER_IDS)
def test_new_manifest_titles_are_distinct_and_not_priest_alone_aliases(kind, language):
    manifest = read(ROOT, f"languages/{language}/manifest.json")
    assert manifest["texts"].count(TEXTS[kind]) == 1
    assert manifest["titles"][TEXTS[kind]] == {"title": TITLES[f"{kind}-{language}"]}
    assert TEXTS[kind] != "ordinarium.iube-domine-benedicere"


@pytest.mark.parametrize(
    "kind,name,suffix,role", WITNESSES, ids=[f"{k}-{n}" for k, n, _, _ in WITNESSES]
)
def test_actual_witness_coverage_and_subject_are_not_review_stamps(
    ministry_corpus, kind, name, suffix, role
):
    root = ministry_corpus
    graph = read(root, "bibliography/graph.json")
    candidates = scoped_rows(graph, "witnesses", kind)
    row = next(r for r in candidates if r["id"] == f"witness.{TEXTS[kind]}.{suffix}")
    assert row["transcription"] == name and row["role"] == role
    assert row["use"] == f"use.{TEXTS[kind]}.{suffix}-body"
    use = next(r for r in graph["uses"] if r["id"] == row["use"])
    assert use["address"] == {"kind": "text", "text": TEXTS[kind]}
    assert use["decision"] in {"RETAIN", "RETAIN_WITH_CORRECTION"}
    if name == "do":
        assert (use["edition"], use["digital_item"], use["role"]) == (
            "edition.divinum-officium-missa.44667ff",
            "item.divinum-officium-missa.44667ff.github",
            "derived_digital_collation_aid",
        )
        assert use["evidence_sha256"] == ARCHIVE_SHA
    elif name == "vatican1962":
        assert (use["edition"], use["digital_item"]) == (
            "edition.missale-romanum.1962-vatican-joseph-bearing",
            "item.missale-romanum.1962-vatican-joseph-bearing.ia",
        )
        assert use["role"] == (
            "corroborating_latin_witness" if kind == "ordinary" else "official_text"
        )
        assert use["locator"]["printed"] == ("219" if kind == "ordinary" else "136")
    else:
        assert (use["edition"], use["digital_item"]) == (
            "edition.missale-romanum.1962-typica",
            "item.missale-romanum.1962-typica.ia",
        )
        assert use["role"] == (
            "direct_approved_print" if kind == "ordinary" else "corroborating_latin_witness"
        )
        assert use["locator"]["printed"] == ("222" if kind == "ordinary" else "139")
    expected = {"kind": "words", "words": WORDS[3:18]} if name == "mr-partial" else {"kind": "full"}
    assert row["coverage"] == expected, f"witness-coverage:{kind}:{name}"
    transcript = root / "witnesses" / TEXTS[kind] / f"{name}.txt"
    assert row["transcription_sha256"] == transcript_digest(transcript.read_text(encoding="utf-8"))
    subject = witness_subject(root, row, graph, core(kind, root))
    assert subject["contract"] == "witness-review-2"
    if row["review"]["status"] == "reviewed":
        assert row["review"]["sha256"] == digest(subject)
    else:
        assert row["review"] == {"status": "pending"}
    if name == "do":
        assert row["source_dependencies"] == {"uses": [], "raw_binding": BINDING}
    else:
        prefix = "vatican1962" if name == "vatican1962" else "mr1962"
        dependencies = [f"use.{TEXTS[kind]}.{prefix}-ritual-boundary"]
        if kind == "ordinary" and name == "mr":
            dependencies.append(f"use.{TEXTS[kind]}.mr1962-requiem-boundary")
            requiem = next(r for r in graph["uses"] if r["id"] == dependencies[-1])
            assert requiem["role"] == "rubric_control" and requiem["locator"]["printed"] == "223"
        assert row["source_dependencies"] == {"uses": sorted(dependencies), "raw_binding": None}


@pytest.mark.parametrize("kind", TEXTS)
def test_selected_latin_and_full_partial_collation_are_genuinely_bound(ministry_corpus, kind):
    root = ministry_corpus
    graph, doc = read(root, "bibliography/graph.json"), core(kind, root)
    directory = root / "witnesses" / TEXTS[kind]
    apparatus = read(root, f"witnesses/{TEXTS[kind]}/apparatus.json")
    assert [
        (r["at"], r["ours"], r["witnesses"], r["class"]) for r in apparatus["adjudicated"]
    ] == RULINGS[kind]
    errors, warnings, stats = collate(doc, directory)
    assert errors == warnings == []
    assert (stats["words"], stats["witnesses"], stats["partial"]) == (
        28,
        2,
        0 if kind == "ordinary" else 1,
    )
    rows = scoped_rows(graph, "collations", kind)
    assert len(rows) == 1
    row = rows[0]
    suffix = "mr1962-vatican1962" if kind == "ordinary" else "vatican1962-mr1962-do44667ff"
    assert row["id"] == f"collation.{TEXTS[kind]}.{suffix}"
    expected_ids = sorted(
        f"witness.{TEXTS[kind]}.{suffix}" for k, _, suffix, _ in WITNESSES if k == kind
    )
    assert row["witnesses"] == expected_ids
    assert row["selected_text_sha256"] == digest(selected_text(doc))
    assert row["apparatus_sha256"] == digest(apparatus)
    subject = collation_subject(root, row, doc, bound_subjects(root, graph, kind))
    assert subject["contract"] == "collation-review-2"


def test_actual_palm_raw_span_actor_sequence_and_literal_cross(ministry_corpus):
    root = ministry_corpus
    raw = (root / RAW).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ARCHIVE_SHA
    lines = raw.decode("utf-8").splitlines()
    assert lines[239] == "[Munda Cor Passionis]"
    assert lines[240].startswith("Munda cor meum ") and len(lines[240].split()) == 34
    reading = resolve_binding(root / "witnesses" / TEXTS["palm"] / "do.txt", root)
    assert reading is not None
    assert reading.source["contract"] == "raw-reading-1" and reading.source["binding_id"] == BINDING
    assert reading.source["binding"]["revision"] == REVISION
    assert reading.source["binding"]["evidence"] == [
        {
            "archive": ARCHIVE,
            "first": 242,
            "last": 244,
            "section": "Munda Cor Passionis",
            "section_line": 240,
        }
    ]
    assert reading.source["binding"]["reading"] == [{"archive": ARCHIVE, "first": 242, "last": 244}]
    assert reading.source["binding"]["references"] == []
    assert reading.spans == ((root / RAW, 242, 244),)
    expected = " ".join(
        (
            lines[241].removeprefix("D. "),
            lines[242].removeprefix("S. "),
            lines[243].removeprefix("D. "),
        )
    )
    assert reading.text == expected
    assert len([token for token in reading.text.split() if any(c.isalpha() for c in token)]) == 28
    assert reading.text.count("+") == 1 and "Fílii, + et Spíritus" in reading.text
    assert load_witness(root / "witnesses" / TEXTS["palm"] / "do.txt")[1] == reading.text
    marked = attribute.marked_lines(TEXTS["palm"], mass=True)
    assert marked == [
        (actor, attribute.flatten(line[3:]))
        for actor, line in zip(("minister", "sacerdos", "minister"), lines[241:244], strict=True)
    ], "actual-palm-D-S-D"


@pytest.mark.parametrize("kind,language,sid", SITE_CASES, ids=SITE_IDS)
def test_each_provenance_site_is_current_without_approval_inheritance(
    ministry_corpus, kind, language, sid
):
    root = ministry_corpus
    site = f"{TEXTS[kind]}.{sid}.{language}"
    rows = read(root, f"languages/{language}/translation-provenance.json")["sites"]
    found = [r for r in rows if r["site"] == site]
    assert len(found) == 1
    row, current = found[0], corpus_sites(root)[site]
    assert (row["text"], row["segment"], row["language"]) == (TEXTS[kind], sid, language)
    assert row["origin"] == (
        "traditional" if sid == "s03" else "trivial" if sid == "s04" else "own"
    ), f"origin:{kind}:{language}:{sid}"
    assert row["review"] in REVIEWS
    assert row["familiar_core"] is (sid == "s03")
    assert row["familiar_core"] == current["familiar_core"]
    assert row["source_sha256"] == current["source_sha256"]
    assert row["target_sha256"] == current["target_sha256"]
    assert current["has_wording_citations"] is (sid == "s03")


def test_all_sixteen_provenance_and_four_basis_sites_pass_real_helpers(ministry_corpus):
    root = ministry_corpus
    errors, tally = check_provenance(root)
    assert errors == [] and sum(tally.values()) == 16
    assert set(corpus_sites(root)) == {
        f"{TEXTS[kind]}.{sid}.{language}" for kind, language, sid in SITE_CASES
    }
    assert check_basis(root) == ([], {"normalized": 2, "revised": 2})
    assert validate_bindings(root, read(root, "bibliography/graph.json")) == []


@pytest.mark.parametrize("kind", TEXTS)
def test_pending_copy_withholds_source_acceptance_even_with_current_digests(ministry_corpus, kind):
    root = ministry_corpus
    graph = read(root, "bibliography/graph.json")
    for field in ("witnesses", "collations"):
        for row in graph[field]:
            row["review"] = {"status": "pending"}
    assert validate_bindings(root, graph) == []
    item = next(
        row for row in bibliography.public_text_evidence(graph)["texts"] if row["id"] == TEXTS[kind]
    )
    assert item["witnesses"] == [] and "collation" not in item


@pytest.mark.parametrize("change", ["drop-cross", "include-preceding-Munda"])
def test_raw_action_sign_and_preceding_spoken_boundary_reject_and_restore(ministry_corpus, change):
    root = ministry_corpus
    witness = root / "witnesses" / TEXTS["palm"] / "do.txt"
    registry = root / "witnesses/raw/bindings.json"
    originals = {path: path.read_bytes() for path in (witness, registry)}
    original = resolve_binding(witness, root)
    assert original is not None
    try:
        if change == "drop-cross":
            lines = originals[witness].decode("utf-8").splitlines(keepends=True)
            headers = [line for line in lines if line.startswith("#")]
            body = [line for line in lines if not line.startswith("#")]
            assert "".join(body).count(" + ") == 1
            changed = [line if line.startswith("#") else line.replace(" + ", " ") for line in lines]
            assert [line for line in changed if line.startswith("#")] == headers
            assert " + " not in "".join(line for line in changed if not line.startswith("#"))
            witness.write_text("".join(changed), encoding="utf-8")
        else:
            doc = json.loads(originals[registry])
            for field in ("evidence", "reading"):
                assert doc["bindings"][BINDING][field][0]["first"] == 242
                doc["bindings"][BINDING][field][0]["first"] = 241
            registry.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
            # A stale header must reject before testing the deeper text boundary.
            with pytest.raises(
                RawBindingError, match=r"^witness path declarations differ from bound evidence$"
            ):
                resolve_binding(witness, root)
            text = originals[witness].decode("utf-8")
            old_header = (
                "# path: web/www/missa/Latin/Tempora/Quad6-0r.txt "
                "[Munda Cor Passionis] (lines 242-244)"
            )
            assert text.splitlines().count(old_header) == 1
            witness.write_text(
                text.replace(old_header, old_header.replace("242-244", "241-244"), 1),
                encoding="utf-8",
            )
        with pytest.raises(
            RawBindingError, match=r"^transcription differs from its exact ordered raw reading$"
        ):
            resolve_binding(witness, root)
    finally:
        for path, content in originals.items():
            path.write_bytes(content)
    assert all(path.read_bytes() == content for path, content in originals.items())
    restored = resolve_binding(witness, root)
    assert (
        restored is not None
        and restored.text == original.text
        and restored.source == original.source
    )


def test_partial_benziger_cannot_become_full_by_changing_graph_label(ministry_corpus):
    root = ministry_corpus
    graph = read(root, "bibliography/graph.json")
    row = next(r for r in graph["witnesses"] if r["transcription"] == "mr-partial")
    original = copy.deepcopy(row)
    baseline = witness_subject(root, row, graph, core("palm", root))
    row["coverage"] = {"kind": "full"}
    with pytest.raises(BindingError, match="graph and transcript coverage disagree"):
        witness_subject(root, row, graph, core("palm", root))
    row.clear()
    row.update(original)
    assert witness_subject(root, row, graph, core("palm", root)) == baseline


def test_repaired_morphology_hashes_do_not_replace_owned_latin_assertion(ministry_corpus):
    root = ministry_corpus
    source_path = core_path("palm")
    ledger_paths = [
        f"languages/{language}/translation-provenance.json" for language in ("pl", "en")
    ]
    originals = {
        relative: (root / relative).read_bytes() for relative in [source_path, *ledger_paths]
    }
    assert check_provenance(root)[0] == []
    doc = core("palm", root)
    assert_latin(doc, "palm", 17)
    word = next(w for w in words(doc) if w["id"] == "w017")
    word["morph"]["number"] = "sg"
    segment = next(s for s in doc["segments"] if s["id"] == "s02")
    changed_hash = canonical_hash(source_payload(segment))
    (root / source_path).write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    try:
        errors = check_provenance(root)[0]
        assert (
            set(errors)
            == {f"{TEXTS['palm']}.s02.{language}: stale source_sha256" for language in ("pl", "en")}
            and len(errors) == 2
        )
        for relative in ledger_paths:
            original_ledger = json.loads(originals[relative])
            ledger = copy.deepcopy(original_ledger)
            matching = [
                row
                for row in ledger["sites"]
                if row["text"] == TEXTS["palm"] and row["segment"] == "s02"
            ]
            assert len(matching) == 1
            matching[0]["source_sha256"] = changed_hash
            (root / relative).write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")
            assert read(root, relative) == ledger
            expected = copy.deepcopy(original_ledger)
            next(row for row in expected["sites"] if row["site"] == matching[0]["site"])[
                "source_sha256"
            ] = changed_hash
            assert ledger == expected
        assert check_provenance(root)[0] == []
        with pytest.raises(AssertionError, match="latin:palm:w017"):
            assert_latin(core("palm", root), "palm", 17)
    finally:
        for relative, data in originals.items():
            (root / relative).write_bytes(data)
    assert all((root / relative).read_bytes() == data for relative, data in originals.items())
    assert check_provenance(root)[0] == []
    assert_latin(core("palm", root), "palm", 17)

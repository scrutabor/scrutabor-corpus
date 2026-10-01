"""Exact postcommunion source boundaries, expansion and unpromoted evidence."""

import json
from pathlib import Path

import pytest

from build_reader import bibliography, store
from checks import attribute, raw_binding

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.purificatio-beatae-mariae-virginis-postcommunio"
WITNESS = ROOT / "witnesses" / TEXT
PREFIX = "use." + TEXT + "."


def test_exact_body_conclusion_and_separate_response():
    core = store.core(ROOT, TEXT)
    segments = core["segments"]
    words = [w for s in segments for w in s["words"]]
    assert [(s["id"], s["speaker"], len(s["words"])) for s in segments] == [
        ("s01", "sacerdos", 47),
        ("s02", "minister", 1),
    ]
    assert [w["id"] for w in words] == [f"w{i:03}" for i in range(1, 49)]
    assert " ".join(w["form"] for w in words[:26]) == (
        "Quǽsumus Dómine Deus noster ut sacrosáncta mystéria quæ pro reparatiónis nostræ "
        "munímine contulísti intercedénte beáta María semper Vírgine et præsens nobis "
        "remédium esse fácias et futúrum"
    )
    assert " ".join(w["form"] for w in words[26:47]) == (
        "Per Dóminum nostrum Iesum Christum Fílium tuum Qui tecum vivit et regnat in "
        "unitáte Spíritus Sancti Deus per ómnia sǽcula sæculórum"
    )
    assert words[47]["form"] == "Amen"


def test_exact_raw_evidence_reference_and_reading_plan():
    registry = json.loads((ROOT / "witnesses/raw/bindings.json").read_bytes())
    assert registry["bindings"]["purification-postcommunion"] == {
        "witness": f"witnesses/{TEXT}/do.txt",
        "revision": "44667ff518b8ff1439780470828b39714f5306a2",
        "evidence": [
            {
                "archive": "purification-day",
                "first": 207,
                "last": 208,
                "section": "Postcommunio",
                "section_line": 206,
            },
            {
                "archive": "prayers",
                "first": 96,
                "last": 97,
                "section": "Per Dominum",
                "section_line": 95,
            },
        ],
        "references": [
            {"archive": "purification-day", "line": 208, "text": "$Per Dominum", "target": 1}
        ],
        "reading": [
            {"archive": "purification-day", "first": 207, "last": 207},
            {"archive": "prayers", "first": 96, "last": 97},
        ],
    }


def test_resolved_raw_words_exclude_heading_reference_and_prefixes():
    reading = raw_binding.resolve_binding(WITNESS / "do.txt", ROOT)
    assert reading is not None
    assert [(str(p.relative_to(ROOT)), a, b) for p, a, b in reading.spans] == [
        ("witnesses/raw/do-44667ff/missa/Latin/Sancti/02-02.txt", 207, 207),
        ("witnesses/raw/do-44667ff/missa/Latin/Ordo/Prayers.txt", 96, 97),
    ]
    words = reading.text.split()
    assert len(words) == 48
    assert words[1] == "Dómine,"
    assert words[23] == "fácias"
    assert words[26:34] == [
        "Per",
        "Dóminum",
        "nostrum",
        "Jesum",
        "Christum,",
        "Fílium",
        "tuum:",
        "qui",
    ]
    assert words[41:43] == ["Sancti", "Deus,"]
    assert words[-1] == "Amen."


@pytest.mark.parametrize("field", ["notes", "method"])
def test_both_core_source_descriptions_distinguish_expansion(field):
    editorial = store.core(ROOT, TEXT)["editorial"]
    value = editorial["notes"] if field == "notes" else editorial["source"]["method"]
    assert "Benziger" in value and "p. 468" in value
    assert "115 a" in value and "expand" in value
    assert "1962 typical edition" not in value


def test_mr_header_is_expanded_not_diplomatic():
    text = (WITNESS / "mr.txt").read_text()
    assert "# description: Missale Romanum, Benziger 1962 (Editio iuxta typicam)" in text
    assert "# expansion: printed p. 468 has only the body and Per Dóminum." in text
    assert "w027–w047 and the textual Amen w048" in text
    assert "tuum, qui" in text and 'final "Amen;"' in text
    assert "house accents, ligatures, tuum: Qui" in text


@pytest.mark.parametrize("transcription", ["mr", "do"])
def test_exact_declared_dependencies_and_pending_review(transcription):
    graph, _ = bibliography.load(ROOT)
    witness = next(
        w for w in graph["witnesses"] if w["text"] == TEXT and w["transcription"] == transcription
    )
    if transcription == "mr":
        expected = {
            "uses": [PREFIX + "conclusion-rg115a.mr1962", PREFIX + "oration-boundaries.mr1962"],
            "raw_binding": None,
        }
        assert witness["orthography_profile"] == "page-body-with-declared-expanded-conclusion"
    else:
        expected = {
            "uses": [PREFIX + "conclusion-macro.do44667ff"],
            "raw_binding": "purification-postcommunion",
        }
    assert witness["source_dependencies"] == expected
    assert witness["review"] == {"status": "pending"}


@pytest.mark.parametrize(
    "suffix,scope",
    [
        ("mr1962", "26-word body (w001–w026)"),
        ("conclusion-rg115a.mr1962", "w027–w048"),
        ("conclusion-macro.do44667ff", "21 conclusion words w027–w047"),
    ],
)
def test_separate_actual_source_scopes(suffix, scope):
    graph, _ = bibliography.load(ROOT)
    use = next(u for u in graph["uses"] if u["id"] == PREFIX + suffix)
    assert use["address"] == {"kind": "text", "text": TEXT}
    assert scope in use["claim"]
    if suffix == "mr1962":
        assert "not directly printed on this page" in use["claim"]
        assert use["locator"]["scan"] == "leaf n549 / PDF p. 550"
    elif suffix == "conclusion-rg115a.mr1962":
        assert use["role"] == "official_text"
        assert use["locator"]["scan"] == "leaf n22 / PDF p. 23"
        assert use["evidence_sha256"] == (
            "b511f3aa4016b387d2995b5089e15aa62593c04118052ef48dcc09352fcf769c"
        )
    else:
        assert "heading 95, conclusion 96, response 97" in use["locator"]["section"]
        assert use["evidence_sha256"] == (
            "7bf86beb01c170212fa07438de45b16b321f117013321400d65c2229c6624d9b"
        )


def test_all_six_accidentals_have_exact_readings():
    apparatus = json.loads((WITNESS / "apparatus.json").read_bytes())
    assert [
        (e["at"], e["ours"], e["witnesses"]["do"], e["class"]) for e in apparatus["adjudicated"]
    ] == [
        ("w002", "Dómine", "Dómine,", "punctuation"),
        ("w024", "fácias,", "fácias", "punctuation"),
        ("w030", "Iesum", "Jesum", "orthography"),
        ("w031", "Christum", "Christum,", "punctuation"),
        ("w034", "Qui", "qui", "capitalization"),
        ("w042", "Sancti,", "Sancti", "punctuation"),
    ]


def test_ritual_locator_and_actual_response_proposal():
    graph, _ = bibliography.load(ROOT)
    use = next(u for u in graph["uses"] if u["id"] == PREFIX + "oration-boundaries.mr1962")
    assert "preface opening dialogue" in use["locator"]["section"]
    core, _ = store.load(ROOT, TEXT)
    assert attribute.propose(core) == {
        "s01": {"speaker": "sacerdos", "voice": "clara"},
        "s02": {"speaker": "minister", "voice": "clara"},
    }


def test_pending_evidence_remains_withheld_from_reader():
    graph, languages = bibliography.load(ROOT)
    assert bibliography.validate(ROOT, graph, languages) == []
    collation = next(c for c in graph["collations"] if c["text"] == TEXT)
    assert collation["review"] == {"status": "pending"}
    projection = next(
        t for t in bibliography.public_text_evidence(graph)["texts"] if t["id"] == TEXT
    )
    assert projection["witnesses"] == [] and "collation" not in projection

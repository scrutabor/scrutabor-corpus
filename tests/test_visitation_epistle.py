"""The Visitation Epistle retains its source body and complete local readings."""

import json
from pathlib import Path

import pytest

from build_reader import bibliography, emit
from build_reader.layers import enrich_layer, expand_core
from checks import attribute, interlinear, raw_binding, transcription
from checks.collate import collate
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
NAME = "visitatio-beatae-mariae-virginis-epistola"
TEXT = "proprium." + NAME
REL = f"proprium/{NAME}.json"


def subject(language):
    return json.loads((ROOT / "texts" / REL).read_bytes()), json.loads(
        (ROOT / f"languages/{language}/texts" / REL).read_bytes()
    )


@pytest.mark.parametrize(
    "language,groups,direct",
    [
        (
            "pl",
            [(["w014", "w015"], "i do młodego jelenia"), (["w061", "w062"], "dał się słyszeć")],
            103,
        ),
        (
            "en",
            [
                (["w009", "w010"], "is like"),
                (["w014", "w015"], "and a young deer"),
                (["w061", "w062"], "has been heard"),
                (["w094", "w095", "w096"], "let your voice sound"),
            ],
            98,
        ),
    ],
)
def test_every_complete_construction_has_one_provider(language, groups, direct):
    core, layer = subject(language)
    assert len(core["segments"]) == 1 and len(core["segments"][0]["words"]) == 107
    assert interlinear.check(core, layer) == []
    actual = layer["segments"]["s01"]["alignments"]
    assert actual == [{"words": words, "anchor": words[0], "gloss": text} for words, text in groups]
    assert sum("gloss" in w for w in layer["words"].values()) == direct
    for words, _ in groups:
        assert all("gloss" not in layer["words"][wid] for wid in words)


@pytest.mark.parametrize(
    "language,expected",
    [
        ("pl", {"w017": "on sam", "w034": "pośpiesz się"}),
        (
            "en",
            {
                "w005": "on",
                "w013": "a roe deer",
                "w017": "he himself",
                "w046": "is past",
                "w048": "is gone",
                "w103": "is sweet",
                "w107": "is beautiful",
            },
        ),
    ],
)
def test_contextual_direct_glosses(language, expected):
    _, layer = subject(language)
    for wid, text in expected.items():
        assert layer["words"][wid]["gloss"] == text


@pytest.mark.parametrize("language,prefix", [("pl", "Epistoła "), ("en", "The Epistle ")])
def test_local_reading_names_and_provenance(language, prefix):
    core, layer = subject(language)
    assert layer["about"].startswith(prefix)
    prose = layer["segments"]["s01"]["translation"]
    if language == "en":
        assert "a roe and a young deer" in prose
        assert "a fawn of the deer" not in prose
    provenance = json.loads(
        (ROOT / f"languages/{language}/translation-provenance.json").read_bytes()
    )
    entry = next(s for s in provenance["sites"] if s["site"] == TEXT + ".s01." + language)
    assert entry["source_sha256"] == canonical_hash(source_payload(core["segments"][0]))
    assert entry["target_sha256"] == canonical_hash(prose)
    assert (entry["origin"], entry["review"], entry["familiar_core"]) == (
        "working-unsettled",
        "working",
        False,
    )


def test_exact_digital_body_excludes_announcement_and_response():
    core, _ = subject("en")
    directory = ROOT / "witnesses" / TEXT
    binding = raw_binding.resolve_binding(directory / "do.txt", ROOT)
    assert binding is not None
    assert [(p.relative_to(ROOT).as_posix(), first, last) for p, first, last in binding.spans] == [
        ("witnesses/raw/do-Sancti-07-02.txt", 19, 19)
    ]
    raw = (ROOT / "witnesses/raw/do-Sancti-07-02.txt").read_text().splitlines()[18]
    assert binding.text == raw
    assert len(raw.split()) == 107 and raw.split()[42] == "Jam"
    assert raw.split()[85] == "petra,"
    assert "Léctio" not in binding.text and "Amen" not in binding.text
    assert transcription.check_transcriptions(directory) == ([], 1)
    assert collate(core, directory)[:2] == ([], [])


def test_selected_printed_reading_and_digital_variants_are_distinct():
    core, _ = subject("en")
    words = core["segments"][0]["words"]
    assert (words[42]["form"], words[85]["form"]) == ("Iam", "petræ")
    app = json.loads((ROOT / "witnesses" / TEXT / "apparatus.json").read_bytes())
    assert [v["at"] for v in app["adjudicated"]] == [
        "w001",
        "w008",
        "w013",
        "w016",
        "w028",
        "w043",
        "w048",
        "w086",
        "w103",
    ]
    spelling = next(v for v in app["adjudicated"] if v["at"] == "w043")
    case = next(v for v in app["adjudicated"] if v["at"] == "w086")
    assert (spelling["ours"], spelling["witnesses"], spelling["class"]) == (
        "Iam",
        {"do": "Jam"},
        "orthography",
    )
    assert case["class"] == "substantive"
    assert "Benziger" in core["editorial"]["source"]["method"]


def test_source_specific_attribution_keeps_the_full_reading():
    core, _ = subject("en")
    literal, alignment = attribute._coverage(core)
    assert literal is False and alignment is not None
    assert len(alignment.words) == 107
    assert alignment.source_line == 19 and alignment.supporting_witnesses == ("mr",)
    assert alignment.substantive_variants == 1
    assert (alignment.words[42].relation, alignment.words[85].relation) == (
        "orthography",
        "substantive",
    )
    assert attribute.propose(core) == {"s01": {"speaker": "sacerdos", "voice": "clara"}}


@pytest.mark.parametrize("language", ["pl", "en"])
def test_full_reader_projection_keeps_constructions_and_analysis(language):
    core, layer = subject(language)
    doc, localized = expand_core(core), enrich_layer(core, layer)
    tables = [emit.Table() for _ in range(4)]
    base = emit.core_artifact(doc, core, *tables[:3])
    translated = emit.language_artifact(doc, localized, tables[3])
    read_core, read_language = emit.expand(base, translated, *[t.edition() for t in tables])
    expected_core, expected_languages = emit._strip(doc, {language: localized})
    assert read_core == expected_core and read_language == expected_languages[language]
    segment = read_core["segments"][0]
    assert (segment["speaker"], segment["voice"]) == ("sacerdos", "clara")
    assert segment["words"][60]["analysis"]["review"] == "pending"


def test_pending_source_reviews_are_not_projected_as_accepted():
    graph = json.loads((ROOT / "bibliography/graph.json").read_bytes())
    witnesses = [w for w in graph["witnesses"] if w.get("text") == TEXT]
    assert len(witnesses) == 2 and all(w["review"]["status"] == "pending" for w in witnesses)
    evidence = bibliography.public_text_evidence(graph)
    row = next(t for t in evidence["texts"] if t["id"] == TEXT)
    assert row["witnesses"] == [] and "collation" not in row

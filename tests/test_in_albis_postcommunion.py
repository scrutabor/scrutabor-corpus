"""Exact postcommunion constructions and bounded source dependencies."""

import json
from pathlib import Path

import pytest

from build_reader import store
from build_reader.layers import expand_core
from checks import interlinear
from checks.raw_binding import resolve_binding
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.dominica-in-albis-postcommunio"
GROUPS = {
    "pl": [
        (["w010", "w011", "w012"], "w012", "ochrony naszego odnowienia"),
        (["w018", "w019"], "w019", "uczynił"),
    ],
    "en": [
        (["w003", "w004"], "w003", "our God"),
        (["w010", "w011"], "w010", "our restoration’s"),
        (["w015", "w016", "w017"], "w017", "a present remedy for us"),
        (["w018", "w019"], "w019", "You may make"),
        (["w023", "w024"], "w023", "our Lord"),
        (["w027", "w028"], "w027", "Your Son"),
        (["w036", "w037"], "w036", "of the Holy Spirit"),
    ],
}
EN_PROSE = (
    "We ask You, Lord our God, to make the most holy mysteries, which You have "
    "bestowed to safeguard our restoration, a remedy for us both now and in the future. "
    "Through our Lord Jesus Christ, Your Son, who lives and reigns with You in the unity "
    "of the Holy Spirit, God, for ever and ever."
)
PL_PROSE = (
    "Prosimy, Panie, Boże nasz, abyś przenajświętsze tajemnice, których udzieliłeś dla "
    "osłony naszego odnowienia, uczynił dla nas lekarstwem zarówno obecnym, jak i przyszłym. "
    "Przez Pana naszego Jezusa Chrystusa, Syna Twojego, który z Tobą żyje i króluje "
    "w jedności Ducha Świętego, Bóg, na wieki wieków."
)


def graph():
    return json.loads((ROOT / "bibliography/graph.json").read_text())


def test_exact_source_words_roles_and_pending_relative_gender():
    doc = store.core(ROOT, TEXT)
    assert [len(s["words"]) for s in doc["segments"]] == [42, 1]
    words = [w for s in doc["segments"] for w in s["words"]]
    assert [w["id"] for w in words] == [f"w{i:03}" for i in range(1, 44)]
    assert [w["form"] for w in words[20:23]] == ["futúrum", "Per", "Dóminum"]
    assert words[7]["morph"] == {"pos": "pron", "case": "acc", "number": "pl", "gender": "n"}
    assert doc["editorial"]["words"]["w008"]["analysis"] == {
        "confidence": "high",
        "sources": ["editorial", "whitakers", "collatinus"],
        "review": "pending",
    }
    assert expand_core(doc)["segments"][0]["words"][7]["analysis"]["review"] == "pending"
    assert [(s["speaker"], s["voice"]) for s in doc["segments"]] == [
        ("sacerdos", "clara"),
        ("minister", "clara"),
    ]
    assert words[-1]["form"] == "Amen"


@pytest.mark.parametrize("lang", ["pl", "en"])
def test_complete_minimal_groups_and_every_card(lang):
    doc, layer = store.core(ROOT, TEXT), store.raw_layer(ROOT, lang, TEXT)
    assert interlinear.check(doc, layer) == []
    assert len(layer["words"]) == 43
    assert sum("gloss" in w for w in layer["words"].values()) == (38 if lang == "pl" else 28)
    expected = [
        {"words": ids, "anchor": anchor, "gloss": gloss} for ids, anchor, gloss in GROUPS[lang]
    ]
    assert layer["segments"]["s01"]["alignments"] == expected
    assert not layer["segments"]["s02"].get("alignments")
    for ids, _, _ in GROUPS[lang]:
        assert all("gloss" not in layer["words"][wid] for wid in ids)


def test_direct_roles_time_and_bestowal_remain_complete():
    pl, en = [store.raw_layer(ROOT, lang, TEXT) for lang in ("pl", "en")]
    assert {
        w: pl["words"][w]["gloss"]
        for w in ["w005", "w008", "w009", "w014", "w015", "w016", "w017", "w020", "w021"]
    } == {
        "w005": "abyś",
        "w008": "których",
        "w009": "jako",
        "w014": "zarówno",
        "w015": "obecnym",
        "w016": "dla nas",
        "w017": "lekarstwem",
        "w020": "jak i",
        "w021": "przyszłym",
    }
    assert {
        w: en["words"][w]["gloss"]
        for w in [
            "w006",
            "w007",
            "w009",
            "w012",
            "w013",
            "w014",
            "w020",
            "w021",
            "w030",
            "w031",
            "w033",
            "w038",
            "w039",
        ]
    } == {
        "w006": "most holy",
        "w007": "mysteries",
        "w009": "as",
        "w012": "safeguard",
        "w013": "You have bestowed",
        "w014": "both",
        "w020": "and",
        "w021": "a future one",
        "w030": "with You",
        "w031": "lives",
        "w033": "reigns",
        "w038": "God",
        "w039": "through",
    }


@pytest.mark.parametrize("lang,prose", [("pl", PL_PROSE), ("en", EN_PROSE)])
def test_prose_is_complete_and_response_separate(lang, prose):
    layer = store.raw_layer(ROOT, lang, TEXT)
    assert layer["segments"]["s01"]["translation"] == prose
    assert layer["segments"]["s02"]["translation"] == "Amen."
    assert layer["about"].startswith(
        "Modlitwa po Komunii" if lang == "pl" else "The prayer after Communion"
    )


@pytest.mark.parametrize("lang", ["pl", "en"])
def test_current_hashes_do_not_promote_working_provenance(lang):
    doc, layer = store.core(ROOT, TEXT), store.raw_layer(ROOT, lang, TEXT)
    sites = json.loads((ROOT / f"languages/{lang}/translation-provenance.json").read_text())[
        "sites"
    ]
    selected = [s for s in sites if s["text"] == TEXT]
    assert len(selected) == 2
    for s in selected:
        segment = next(x for x in doc["segments"] if x["id"] == s["segment"])
        assert s["source_sha256"] == canonical_hash(source_payload(segment))
        assert s["target_sha256"] == canonical_hash(layer["segments"][s["segment"]]["translation"])
        assert s["review"] == "working"
        assert s["origin"] == ("working-unsettled" if s["segment"] == "s01" else "trivial")


def test_raw_binding_uses_own_postcommunion_reference_and_full_response():
    root = ROOT / "witnesses" / TEXT
    resolved = resolve_binding(root / "do.txt", ROOT)
    assert resolved is not None
    registry = json.loads((ROOT / "witnesses/raw/bindings.json").read_text())
    b = registry["bindings"]["in-albis-postcommunion"]
    assert b["evidence"] == [
        {
            "archive": "in-albis-day",
            "first": 53,
            "last": 54,
            "section": "Postcommunio",
            "section_line": 52,
        },
        {
            "archive": "prayers",
            "first": 96,
            "last": 97,
            "section": "Per Dominum",
            "section_line": 95,
        },
    ]
    assert b["references"] == [
        {"archive": "in-albis-day", "line": 54, "text": "$Per Dominum.", "target": 1}
    ]
    assert b["reading"] == [
        {"archive": "in-albis-day", "first": 53, "last": 53},
        {"archive": "prayers", "first": 96, "last": 97},
    ]
    tokens = resolved.text.split()
    assert len(tokens) == 43 and tokens[-1] == "Amen."
    assert tokens[24] == "Jesum" and tokens[25] == "Christum," and tokens[28] == "qui"


def test_expanded_witness_scope_and_both_core_claims_are_honest():
    doc = store.core(ROOT, TEXT)
    assert "21-word" in doc["editorial"]["notes"]
    assert "Per Dóminum." in doc["editorial"]["notes"]
    assert (
        "RG" not in doc["editorial"]["source"]["method"]
        or "115" in doc["editorial"]["source"]["method"]
    )
    assert "Rubricae generales 115 a" in doc["editorial"]["source"]["method"]
    mr = (ROOT / "witnesses" / TEXT / "mr.txt").read_text()
    assert "# description: Missale Romanum, Benziger 1962 (Editio iuxta typicam)" in mr
    assert "w022–w042" in mr and "Amen w043" in mr
    assert "tuum, qui" in mr and "tuum: Qui" in mr
    assert "not as claims that p. 335 directly prints all 43 words" in mr
    assert "# transcribed: 2026-09-12" in mr


@pytest.mark.parametrize("name", ["mr", "do"])
def test_all_witness_dependencies_are_explicit_and_pending(name):
    g = graph()
    w = next(w for w in g["witnesses"] if w["text"] == TEXT and w["transcription"] == name)
    prefix = "use." + TEXT + "."
    assert w["review"] == {"status": "pending"}
    assert w["coverage"] == {"kind": "full"}
    assert w["source_dependencies"] == (
        {
            "uses": [prefix + "conclusion-rg115a.mr1962", prefix + "oration-boundaries.mr1962"],
            "raw_binding": None,
        }
        if name == "mr"
        else {
            "uses": [prefix + "conclusion-macro.do44667ff"],
            "raw_binding": "in-albis-postcommunion",
        }
    )
    uses = {u["id"]: u for u in g["uses"]}
    assert "21-word body (w001–w021)" in uses[prefix + "mr1962"]["claim"]
    assert "w022–w042" in uses[prefix + "conclusion-rg115a.mr1962"]["locator"]["section"]
    assert "response 97" in uses[prefix + "conclusion-macro.do44667ff"]["locator"]["section"]


@pytest.mark.parametrize(
    "wid,ours,theirs,kind",
    [
        ("w002", "Dómine", "Dómine,", "punctuation"),
        ("w019", "fácias,", "fácias", "punctuation"),
        ("w025", "Iesum", "Jesum", "orthography"),
        ("w026", "Christum", "Christum,", "punctuation"),
        ("w029", "Qui", "qui", "capitalization"),
        ("w037", "Sancti,", "Sancti", "punctuation"),
    ],
)
def test_each_exact_accidental_is_retained(wid, ours, theirs, kind):
    app = json.loads((ROOT / "witnesses" / TEXT / "apparatus.json").read_text())
    assert len(app["adjudicated"]) == 6
    entry = next(e for e in app["adjudicated"] if e["at"] == wid)
    assert (entry["ours"], entry["witnesses"], entry["class"]) == (ours, {"do": theirs}, kind)
    assert "typical edition" not in entry["ruling"]

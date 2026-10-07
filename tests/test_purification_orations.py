"""Purification Collect and Secret: contextual readings, register and sources."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import bibliography, store
from build_reader.bibliography_bindings import collation_subject, witness_subject
from checks import english, interlinear, polish
from checks.raw_binding import resolve_binding
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
DAY = "proprium.purificatio-beatae-mariae-virginis-"
COLLECT, SECRET = DAY + "collecta", DAY + "secreta"
CONCLUSION_EN = (
    "Through our Lord Jesus Christ, Your Son, who lives and reigns with You in the unity of the "
    "Holy Spirit, God,"
)
LINES = {
    (COLLECT, "en"): [
        "Almighty",
        "eternal",
        "God",
        "Your majesty",
        "as suppliants",
        "we beseech",
        "that",
        "as",
        "Your only-begotten Son",
        "this",
        "day",
        "with",
        "the substance of our flesh",
        "in",
        "the temple",
        "was",
        "presented",
        "so",
        "us",
        "may You cause",
        "to be presented to You with purified minds",
        "Through",
        "this same Jesus Christ, our Lord",
        "Your Son",
        "who lives and reigns with You",
        "in",
        "the unity",
        "of the Holy Spirit",
        "God",
        "forever and ever",
        "Amen",
    ],
    (SECRET, "en"): [
        "Graciously hear",
        "Lord",
        "our prayers",
        "and",
        "that",
        "worthy",
        "may be",
        "the gifts",
        "which",
        "before the eyes",
        "of Your",
        "majesty",
        "we offer",
        "the help",
        "to us",
        "of Your",
        "loving-kindness",
        "bestow",
        "Through",
        "our Lord",
        "Jesus Christ",
        "Your Son",
        "who lives and reigns with You",
        "in",
        "the unity",
        "of the Holy Spirit",
        "God",
        "forever and ever",
        "Amen",
    ],
}
GROUPS = {
    COLLECT: [
        ([4, 5], 4, "Your majesty"),
        ([10, 11, 12], 11, "Your only-begotten Son"),
        ([16, 17, 18], 18, "the substance of our flesh"),
        ([26, 27, 28, 29], 29, "to be presented to You with purified minds"),
        ([31, 32, 33, 34, 35], 32, "this same Jesus Christ, our Lord"),
        ([36, 37], 36, "Your Son"),
        ([38, 39, 40, 41, 42], 40, "who lives and reigns with You"),
        ([45, 46], 45, "of the Holy Spirit"),
        ([48, 49, 50, 51], 50, "forever and ever"),
    ],
    SECRET: [
        ([3, 4], 3, "our prayers"),
        ([21, 22], 21, "our Lord"),
        ([23, 24], 23, "Jesus Christ"),
        ([25, 26], 25, "Your Son"),
        ([27, 28, 29, 30, 31], 29, "who lives and reigns with You"),
        ([34, 35], 34, "of the Holy Spirit"),
        ([37, 38, 39, 40], 39, "forever and ever"),
    ],
}
ARCHAIC = ("Thy", "Thee", "Thou", "liveth", "reigneth", "Holy Ghost", "world without end")


def wid(n):
    return f"w{n:03}"


def line(doc, layer):
    groups = [g for s in layer["segments"].values() for g in s.get("alignments", [])]
    membership = {w: g for g in groups for w in g["words"]}
    out = []
    for segment in doc["segments"]:
        for word in segment.get("words", []):
            group = membership.get(word["id"])
            if group is None or group.get("anchor") == word["id"]:
                out.append(interlinear.effective_gloss(layer, word["id"]))
    return out


@pytest.mark.parametrize("text", [COLLECT, SECRET])
def test_selected_english_line(text):
    doc, layers = store.load(ROOT, text)
    assert not interlinear.check(doc, layers["en"])
    assert line(doc, layers["en"]) == LINES[(text, "en")]


@pytest.mark.parametrize("text", [COLLECT, SECRET])
def test_selected_english_groups(text):
    # The dative of præsentári, separated from it by the ablative, is regrouped;
    # possessives, the genitive of *carnis* and the conclusion are grouped where the
    # English line needs them (the line criterion of 2026-10-07).
    _, layers = store.load(ROOT, text)
    groups = [g for s in layers["en"]["segments"].values() for g in s.get("alignments", [])]
    assert groups == [
        {"words": [wid(n) for n in numbers], "anchor": wid(anchor), "gloss": gloss}
        for numbers, anchor, gloss in GROUPS[text]
    ]


@pytest.mark.parametrize("text", [COLLECT, SECRET])
def test_one_english_register_in_each_prayer(text):
    doc, layers = store.load(ROOT, text)
    layer = layers["en"]
    prose = " ".join(s["translation"] for s in layer["segments"].values())
    glosses = " ".join(line(doc, layer))
    assert not [form for form in ARCHAIC if form in prose or form in glosses]


def test_secret_conclusion_matches_this_mass_and_current_provenance():
    secret = store.raw_layer(ROOT, "en", SECRET)["segments"]
    assert secret["s01"]["translation"].endswith(CONCLUSION_EN)
    assert secret["s02"]["translation"] == "forever and ever."
    postcommunion = store.raw_layer(ROOT, "en", DAY + "postcommunio")["segments"]["s01"][
        "translation"
    ]
    assert CONCLUSION_EN in postcommunion
    data = json.loads((ROOT / "languages/en/translation-provenance.json").read_text())
    core = store.core(ROOT, SECRET)
    for segment in core["segments"][:2]:
        site = next(s for s in data["sites"] if s["site"] == f"{SECRET}.{segment['id']}.en")
        assert (site["origin"], site["review"]) == ("working-unsettled", "working")
        assert site["target_sha256"] == canonical_hash(secret[segment["id"]]["translation"])
        assert site["source_sha256"] == canonical_hash(source_payload(segment))


def test_one_spelling_of_the_conclusion_in_this_mass():
    proses = {
        part: " ".join(
            s["translation"] for s in store.raw_layer(ROOT, "en", DAY + part)["segments"].values()
        )
        for part in ("collecta", "secreta", "postcommunio")
    }
    assert all("forever and ever" in prose for prose in proses.values())
    assert not any("for ever and ever" in prose for prose in proses.values())
    data = json.loads((ROOT / "languages/en/translation-provenance.json").read_text())
    collect = store.raw_layer(ROOT, "en", COLLECT)["segments"]["s01"]["translation"]
    site = next(s for s in data["sites"] if s["site"] == f"{COLLECT}.s01.en")
    assert site["target_sha256"] == canonical_hash(collect)


def test_secret_polish_pietas_uses_the_card_and_prose_term():
    layer = store.raw_layer(ROOT, "pl", SECRET)
    assert layer["words"]["w018"]["gloss"] == "dobroci"
    assert "Twojej dobroci" in layer["segments"]["s01"]["translation"]
    doc, layers = store.load(ROOT, SECRET)
    mutated = deepcopy(layers["pl"])
    mutated["words"]["w018"]["gloss"] = "miłości"
    assert not interlinear.check(doc, mutated)
    assert not polish.check(doc, mutated)


def test_collect_same_lord_rubric_is_a_rubric_control():
    graph, _ = bibliography.load(ROOT)
    use = next(u for u in graph["uses"] if u["id"] == f"use.{COLLECT}.same-lord-conclusion.mr1962")
    assert use["role"] == "rubric_control"
    assert use["address"] == {"kind": "word", "text": COLLECT, "word": "w031"}
    assert use["locator"]["section"] == "Rubricae generales 115 b"


@pytest.mark.parametrize("language,prefix", [("pl", "Sekreta formularza"), ("en", "The Secret of")])
def test_localized_secret_about(language, prefix):
    assert store.raw_layer(ROOT, language, SECRET)["about"].startswith(prefix)


def test_exact_secret_raw_plan():
    bound = resolve_binding(ROOT / "witnesses" / SECRET / "do.txt", ROOT)
    assert bound is not None and bound.source["binding_id"] == "purification-secret"
    plan = bound.source["binding"]
    assert plan["evidence"] == [
        {
            "archive": "purification-day",
            "first": 199,
            "last": 200,
            "section": "Secreta",
            "section_line": 198,
        },
        {
            "archive": "prayers",
            "first": 96,
            "last": 97,
            "section": "Per Dominum",
            "section_line": 95,
        },
    ]
    assert plan["references"] == [
        {"archive": "purification-day", "line": 200, "text": "$Per Dominum", "target": 1}
    ]
    tokens = bound.text.split()
    assert len(tokens) == 41 and tokens[12] == "majestátis" and tokens[22] == "Jesum"
    assert tokens[-1] == "Amen."


def test_secret_pending_dependencies_mirror_the_collect():
    graph, _ = bibliography.load(ROOT)
    for text in (COLLECT, SECRET):
        core = store.core(ROOT, text)
        witnesses = {w["transcription"]: w for w in graph["witnesses"] if w["text"] == text}
        assert witnesses["do"]["source_dependencies"] == {
            "uses": [f"use.{text}.expanded-conclusion.do44667ff"],
            "raw_binding": "purification-" + ("collect" if text == COLLECT else "secret"),
        }
        assert (
            f"use.{text}.expanded-conclusion.mr1962"
            in witnesses["mr"]["source_dependencies"]["uses"]
        )
        subjects = {w["id"]: witness_subject(ROOT, w, graph, core) for w in witnesses.values()}
        collation = next(c for c in graph["collations"] if c["text"] == text)
        assert collation["review"] == {"status": "pending"}
        assert (
            collation_subject(ROOT, collation, core, subjects)["contract"] == "collation-review-2"
        )


@pytest.mark.parametrize(
    "use",
    [
        f"use.{COLLECT}.mr1962",
        f"use.{COLLECT}.expanded-conclusion.mr1962",
        f"use.{SECRET}.mr1962",
        f"use.{SECRET}.expanded-conclusion.mr1962",
    ],
)
def test_benziger_pages_are_an_approved_print(use):
    graph, _ = bibliography.load(ROOT)
    record = next(u for u in graph["uses"] if u["id"] == use)
    assert record["edition"] == "edition.missale-romanum.1962-typica"
    assert record["role"] == "direct_approved_print"


def test_secret_identity_and_declared_expansion():
    graph, _ = bibliography.load(ROOT)
    mr = next(u for u in graph["uses"] if u["id"] == f"use.{SECRET}.mr1962")
    assert "Benziger Brothers 1962 Editio iuxta typicam" in mr["claim"]
    header = (ROOT / "witnesses" / SECRET / "mr.txt").read_text()
    assert "typical edition" not in header and "local-archive:" not in header
    assert "declared house-expanded conclusion" in header
    apparatus = json.loads((ROOT / "witnesses" / SECRET / "apparatus.json").read_text())
    assert [(e["at"], e["class"]) for e in apparatus["adjudicated"]] == [
        ("w013", "orthography"),
        ("w023", "orthography"),
        ("w024", "punctuation"),
        ("w027", "capitalization"),
        ("w035", "punctuation"),
    ]


def test_mixed_register_passes_generic_checks_but_not_this_file():
    doc, layers = store.load(ROOT, SECRET)
    layer = deepcopy(layers["en"])
    layer["segments"]["s01"]["translation"] = layer["segments"]["s01"]["translation"].replace(
        CONCLUSION_EN,
        "Through our Lord Jesus Christ, Thy Son, who liveth and reigneth with Thee in the unity of "
        "the Holy Ghost, God,",
    )
    son = next(g for g in layer["segments"]["s01"]["alignments"] if g["anchor"] == "w025")
    son["gloss"] = "Thy Son"
    assert not interlinear.check(doc, layer)
    assert not english.check(doc, layer)
    prose = " ".join(s["translation"] for s in layer["segments"].values())
    assert [form for form in ARCHAIC if form in prose]


def test_legitimate_spelling_alternative_remains_valid():
    doc, layers = store.load(ROOT, SECRET)
    layer = deepcopy(layers["en"])
    layer["segments"]["s02"]["translation"] = "for ever and ever."
    assert not interlinear.check(doc, layer)
    assert not english.check(doc, layer)

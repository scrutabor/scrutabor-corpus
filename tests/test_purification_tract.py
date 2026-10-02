"""Purification Tract contextual readings and exact source boundaries."""

from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import bibliography, store
from build_reader.bibliography_bindings import collation_subject, witness_subject
from checks import english, interlinear, polish
from checks.raw_binding import resolve_binding
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.purificatio-beatae-mariae-virginis-tractus"
GROUPS = [
    ([35, 36], 35, "Your servant"),
    ([39, 40], 39, "Your word"),
    ([44, 45, 46], 44, "my eyes have seen"),
    ([47, 48], 47, "Your salvation"),
    ([61, 62], 61, "of Your people"),
]
LINES = {
    "pl": [
        "Teraz",
        "uwalniasz",
        "sługę",
        "Twego",
        "Panie",
        "według",
        "słowa",
        "Twego",
        "w",
        "pokoju",
        "Albowiem",
        "ujrzały",
        "oczy",
        "moje",
        "zbawienie",
        "Twoje",
        "Które",
        "przygotowałeś",
        "przed",
        "obliczem",
        "wszystkich",
        "ludów",
        "Światłość",
        "ku",
        "objawieniu",
        "poganom",
        "i",
        "chwałę",
        "ludu",
        "Twego",
        "Izraela",
    ],
    "en": [
        "Now",
        "You release",
        "Your servant",
        "Lord",
        "according to",
        "Your word",
        "in",
        "peace",
        "For",
        "my eyes have seen",
        "Your salvation",
        "which",
        "You have prepared",
        "before",
        "the face",
        "of all",
        "peoples",
        "a light",
        "for",
        "revelation",
        "to the Gentiles",
        "and",
        "glory",
        "of Your people",
        "Israel",
    ],
}


@pytest.mark.parametrize("language", ["pl", "en"])
def test_selected_complete_line_and_provider_partition(language):
    doc, layers = store.load(ROOT, TEXT)
    layer = layers[language]
    assert not interlinear.check(doc, layer)
    words = doc["segments"][0]["words"]
    groups = layer["segments"]["s01"].get("alignments", [])
    membership = {wid: group for group in groups for wid in group["words"]}
    line = []
    for word in words:
        wid = word["id"]
        group = membership.get(wid)
        if group is None or group.get("anchor") == wid:
            line.append(interlinear.effective_gloss(layer, wid))
    assert line == LINES[language]
    assert len(words) == 31 and len(line) == (31 if language == "pl" else 25)
    assert len(groups) == (0 if language == "pl" else 5)
    assert sum("gloss" in v for v in layer["words"].values()) == (31 if language == "pl" else 20)


@pytest.mark.parametrize("numbers,anchor,gloss", GROUPS)
def test_selected_minimal_group(numbers, anchor, gloss):
    _, layers = store.load(ROOT, TEXT)
    layer = layers["en"]
    ids = [f"w{i:03}" for i in numbers]
    groups = [g for g in layer["segments"]["s01"].get("alignments", []) if g["words"] == ids]
    assert len(groups) == 1
    assert groups[0] == {"words": ids, "anchor": f"w{anchor:03}", "gloss": gloss}
    assert all("gloss" not in layer["words"].get(wid, {}) for wid in ids)


@pytest.mark.parametrize(
    "wid,gloss",
    [("w034", "You release"), ("w050", "You have prepared"), ("w058", "to the Gentiles")],
)
def test_selected_direct_realization(wid, gloss):
    _, layers = store.load(ROOT, TEXT)
    assert layers["en"]["words"][wid]["gloss"] == gloss


def test_retained_latin_objects_and_complete_stable_ids():
    core = store.core(ROOT, TEXT)
    words = {w["id"]: w for w in core["segments"][0]["words"]}
    assert list(words) == [f"w{i:03}" for i in range(33, 64)]
    assert core["ids"]["retired"] == {f"w{i:03}": "s01" for i in range(1, 33)}
    assert (words["w049"]["lemma"], words["w049"]["morph"]["case"]) == ("qui", "acc")
    assert words["w050"]["morph"]["person"] == 2
    assert words["w050"]["morph"]["tense"] == "perf"
    assert words["w055"]["morph"]["case"] == "acc"
    assert words["w058"]["morph"]["case"] == "gen"
    assert words["w058"]["post"] == ","
    assert words["w044"]["morph"]["number"] == "pl"


@pytest.mark.parametrize("language,prefix", [("pl", "Trakt "), ("en", "The Tract ")])
def test_localized_about(language, prefix):
    assert store.raw_layer(ROOT, language, TEXT)["about"].startswith(prefix)


def test_recipient_prose_and_unpromoted_current_dependency():
    core = store.core(ROOT, TEXT)
    en = store.raw_layer(ROOT, "en", TEXT)
    prose = en["segments"]["s01"]["translation"]
    assert prose == (
        "Now You let Your servant depart, Lord, according to Your word, in peace; "
        "for my eyes have seen Your salvation, which You have prepared before the "
        "face of all peoples: a light for revelation to the Gentiles, and the "
        "glory of Your people Israel."
    )
    import json

    data = json.loads((ROOT / "languages/en/translation-provenance.json").read_text())
    sites = [s for s in data["sites"] if s["site"] == TEXT + ".s01.en"]
    assert len(sites) == 1
    site = sites[0]
    assert (site["origin"], site["review"]) == ("working-unsettled", "working")
    assert site["target_sha256"] == canonical_hash(prose)
    assert site["source_sha256"] == canonical_hash(source_payload(core["segments"][0]))


def test_exact_direct_tract_raw_plan():
    bound = resolve_binding(ROOT / "witnesses" / TEXT / "do.txt", ROOT)
    assert bound is not None
    binding = bound.source["binding"]
    assert bound.source["binding_id"] == "purification-tract"
    assert binding["evidence"] == [
        {
            "archive": "purification-day",
            "first": 185,
            "last": 188,
            "section": "Tractus",
            "section_line": 180,
        }
    ]
    assert binding["reading"] == [{"archive": "purification-day", "first": 185, "last": 188}]
    assert binding["references"] == []
    assert len(bound.text.split()) == 31
    assert bound.text.startswith("Nunc dimíttis") and bound.text.endswith("plebis tuæ Israël.")
    assert "Suscépimus" not in bound.text and "V." not in bound.text


def test_nonempty_pending_witness_and_collation_dependencies():
    graph, _ = bibliography.load(ROOT)
    core = store.core(ROOT, TEXT)
    witnesses = [w for w in graph["witnesses"] if w["text"] == TEXT]
    collations = [c for c in graph["collations"] if c["text"] == TEXT]
    assert len(witnesses) == 2 and {w["transcription"] for w in witnesses} == {"do", "mr"}
    assert len(collations) == 1
    subjects = {}
    for witness in witnesses:
        assert witness["review"] == {"status": "pending"}
        assert witness["source_dependencies"] == {
            "uses": [],
            "raw_binding": "purification-tract" if witness["transcription"] == "do" else None,
        }
        subjects[witness["id"]] = witness_subject(ROOT, witness, graph, core)
    assert collations[0]["review"] == {"status": "pending"}
    assert (
        collation_subject(ROOT, collations[0], core, subjects)["contract"] == "collation-review-2"
    )


def test_exact_printed_identity_and_current_not_historical_genesis():
    graph, _ = bibliography.load(ROOT)
    uses = [u for u in graph["uses"] if u.get("address", {}).get("text") == TEXT]
    assert len(uses) == 2
    mr = next(u for u in uses if u["id"].endswith(".mr1962"))
    assert mr["role"] == "direct_approved_print"
    assert mr["locator"] == {
        "printed": "p. 467",
        "scan": "leaf n548 / PDF p. 549",
        "page_url": "https://archive.org/details/missale-romanum-1962/page/n548/mode/1up",
    }
    assert mr["evidence_sha256"] == (
        "1d03b85122869acb77a773f78debebbc7c8f87bef4e0acc7088a77d6f8ecf9b6"
    )
    assert "Editio iuxta typicam" in mr["claim"]
    assert "not original transcription genesis" in mr["claim"]
    assert all(u["verified_on"] == "2026-09-19" for u in uses)
    header = (ROOT / "witnesses" / TEXT / "mr.txt").read_text()
    assert "# historical-transcribed: 2026-09-19 from directly viewed page images" in header
    assert "# verification-scope: current whole-body conformity" in header
    method = store.core(ROOT, TEXT)["editorial"]["source"]["method"]
    assert "not the original transcription workflow" in method
    assert "direct digital [Tractus]" in method


def test_exact_comma_apparatus_not_a_typical_edition_claim():
    import json

    apparatus = json.loads((ROOT / "witnesses" / TEXT / "apparatus.json").read_text())
    assert apparatus["summary"] == {"entries": 1, "classes": ["punctuation"]}
    assert len(apparatus["adjudicated"]) == 1
    entry = apparatus["adjudicated"][0]
    assert (entry["at"], entry["ours"], entry["witnesses"], entry["class"]) == (
        "w058",
        "géntium,",
        {"do": "géntium"},
        "punctuation",
    )
    assert "Benziger Brothers 1962 Editio iuxta typicam" in entry["ruling"]
    assert "typical-edition" not in entry["ruling"]


@pytest.mark.parametrize(
    "mode",
    [
        "dismiss",
        "literary-dismiss",
        "simple-perfect",
        "article-retained",
        "polish-inversion",
    ],
)
def test_legitimate_variants_are_not_generic_grammar_errors(mode):
    doc, layers = store.load(ROOT, TEXT)
    layer = deepcopy(layers["pl" if mode == "polish-inversion" else "en"])
    if mode in ("dismiss", "literary-dismiss"):
        layer["words"]["w034"]["gloss"] = (
            "You dismiss" if mode == "dismiss" else "Thou dost dismiss"
        )
    elif mode == "simple-perfect":
        segment = layer["segments"]["s01"]
        groups = segment.setdefault("alignments", [])
        matches = [g for g in groups if g.get("anchor") == "w044"]
        if matches:
            group = matches[0]
        else:
            ids = ["w044", "w045", "w046"]
            group = {"words": ids, "anchor": "w044"}
            groups.append(group)
            for wid in ids:
                layer["words"][wid].pop("gloss", None)
        group["gloss"] = "my eyes saw"
    elif mode == "article-retained":
        segment = layer["segments"]["s01"]
        segment["translation"] = segment["translation"].replace(
            "for revelation to", "for the revelation to"
        )
    assert not interlinear.check(doc, layer)
    checker = polish if mode == "polish-inversion" else english
    assert not checker.check(doc, layer)

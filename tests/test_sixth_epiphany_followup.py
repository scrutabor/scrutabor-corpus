"""Sixth Epiphany petitions and parables retain agents, objects and source scopes."""

import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.bibliography_bindings import digest, selected_text
from checks import attribute, interlinear
from checks.language_packs import check_core, check_layer
from checks.punctuation import word_faces
from checks.raw_binding import BindingError, resolve_binding
from checks.transcription import check_transcriptions
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "proprium.dominica-vi-post-epiphaniam-"
ROLES = {
    "collecta": 39,
    "epistola": 177,
    "evangelium": 102,
    "secreta": 33,
    "postcommunio": 35,
}
SELECTED = {
    "collecta": "91282207c534fb4e6df09382ef9c2043b139f518a73483b6c8a5a4397c6ca687",
    "epistola": "93c5bcbb1a0af2fa619d3aff44b6ec86da0c42817dfec37380535c928f4551f3",
    "evangelium": "6c44cddc2423f5801130625ec1a212ebfd0126a1793ca3857874d7e678b59102",
    "secreta": "216cfdc047d05807953fc9892bb51ea5df36bb1d9e218b382dacf3cbad225b35",
    "postcommunio": "b486eff9076dd911e374ec75762b923d28761968be657f77adcef623c01f0213",
}
GROUPS = [
    ("collecta", "pl", 7, 8, 8, "rozważając to, co rozumne,"),
    ("collecta", "pl", 9, 17, 15, "wypełniali to, co Tobie miłe, i słowami, i czynami"),
    ("collecta", "en", 6, 8, 8, "always meditating on what is reasonable,"),
    (
        "collecta",
        "en",
        9,
        17,
        15,
        "we may carry out what is pleasing to You, both in words and in deeds",
    ),
    ("epistola", "pl", 37, 41, 37, "wiedząc, bracia umiłowani przez Boga,"),
    ("epistola", "pl", 42, 43, 42, "o waszym wybraniu"),
    ("epistola", "pl", 47, 50, 48, "nie przyszła do was"),
    ("epistola", "pl", 76, 81, 78, "staliście się naśladowcami naszymi oraz Pana"),
    ("epistola", "en", 106, 109, 106, "the word of the Lord has been spread abroad"),
    (
        "epistola",
        "en",
        119,
        129,
        128,
        "your faith, which is directed toward God, has spread everywhere",
    ),
    ("epistola", "en", 140, 142, 142, "report about us"),
    ("epistola", "en", 143, 147, 145, "what our coming to you was like"),
    ("evangelium", "pl", 15, 18, 18, "które człowiek wziął i posiał"),
    ("evangelium", "pl", 58, 61, 61, "który kobieta wzięła i ukryła"),
    ("evangelium", "pl", 63, 65, 64, "trzech miarach mąki"),
    ("evangelium", "en", 58, 61, 61, "which a woman took and hid"),
    ("evangelium", "en", 63, 65, 64, "three measures of flour"),
    ("evangelium", "en", 67, 69, 67, "the whole was leavened"),
    ("secreta", "pl", 1, 3, 3, "Ta ofiara nas"),
    ("secreta", "en", 1, 6, 5, "May this offering, O God, we beseech You, cleanse us"),
    ("postcommunio", "pl", 1, 4, 3, "Nakarmieni niebieskimi rozkoszami, Panie,"),
    (
        "postcommunio",
        "pl",
        6,
        13,
        13,
        "abyśmy zawsze pragnęli tego samego, przez co prawdziwie żyjemy",
    ),
    ("postcommunio", "en", 1, 4, 3, "Nourished by heavenly delights, O Lord,"),
    (
        "postcommunio",
        "en",
        6,
        13,
        13,
        "that we may always desire those same things by which we truly live",
    ),
]


def load(path):
    return json.loads((ROOT / path).read_text())


def core(role):
    return load(f"texts/proprium/dominica-vi-post-epiphaniam-{role}.json")


def layer(role, language):
    return load(f"languages/{language}/texts/proprium/dominica-vi-post-epiphaniam-{role}.json")


@pytest.mark.parametrize("role,language,start,end,anchor,gloss", GROUPS)
def test_coherent_construction(role, language, start, end, anchor, gloss):
    data = layer(role, language)
    ids = [f"w{n:03}" for n in range(start, end + 1)]
    assert {"words": ids, "anchor": f"w{anchor:03}", "gloss": gloss} in data["segments"]["s01"][
        "alignments"
    ]
    assert all("gloss" not in data["words"][wid] for wid in ids)


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("language", ["pl", "en"])
def test_complete_latin_realization_topology_and_pending_rows(role, language):
    doc, data = core(role), layer(role, language)
    assert sum(len(s["words"]) for s in doc["segments"]) == ROLES[role]
    assert digest(selected_text(doc)) == SELECTED[role]
    assert check_core(doc) == []
    assert (
        check_layer(
            doc,
            data,
            ROOT / f"languages/{language}/texts/proprium/dominica-vi-post-epiphaniam-{role}.json",
        )
        == []
    )
    assert interlinear.check(doc, data) == []
    sites = {
        s["segment"]: s
        for s in load(f"languages/{language}/translation-provenance.json")["sites"]
        if s["text"] == PREFIX + role
    }
    assert set(sites) == {s["id"] for s in doc["segments"]}
    for seg in doc["segments"]:
        row = sites[seg["id"]]
        assert row["source_sha256"] == canonical_hash(source_payload(seg))
        assert row["target_sha256"] == canonical_hash(data["segments"][seg["id"]]["translation"])
        assert row["review"] == "working" and row["familiar_core"] is False


def test_local_morphology_confidence_and_explanations():
    for role, identifier, case in [
        ("collecta", "w009", "nom"),
        ("postcommunio", "w010", "acc"),
    ]:
        doc = core(role)
        word = next(w for s in doc["segments"] for w in s["words"] if w["id"] == identifier)
        assert word["morph"] == {
            "pos": "pron",
            "case": case,
            "number": "pl",
            "gender": "n",
        }
        assert doc["editorial"]["words"][identifier]["analysis"] == {
            "confidence": "high",
            "sources": ["editorial", "whitakers", "collatinus"],
            "review": "pending",
        }
    doc = core("evangelium")
    word = next(w for w in doc["segments"][0]["words"] if w["id"] == "w030")
    assert word["morph"] == {
        "pos": "verb",
        "mood": "ind",
        "tense": "futperf",
        "voice": "act",
        "person": 3,
        "number": "sg",
        "conj": 3,
    }
    assert doc["editorial"]["words"]["w030"]["analysis"] == {
        "confidence": "medium",
        "sources": ["editorial", "whitakers", "collatinus"],
        "review": "pending",
    }
    for role, identifier in [("collecta", "w012"), ("evangelium", "w030")]:
        assert core(role)["localization"]["explanations"] == {identifier: {}}
        for language in ("pl", "en"):
            assert layer(role, language)["words"][identifier]["explanation"]


def test_precise_targets_and_no_duplicate_conjunction():
    data = layer("epistola", "en")
    assert [data["words"][w]["gloss"] for w in ("w117", "w118")] == ["but", "also"]
    assert "the hope in our Lord" in data["segments"]["s01"]["translation"]
    assert layer("epistola", "pl")["words"]["w143"]["gloss"] == "jaki"
    assert layer("evangelium", "pl")["words"]["w034"]["gloss"] == "jarzyn"
    assert layer("evangelium", "en")["words"]["w034"]["gloss"] == "garden vegetables"
    assert (
        "He did not speak to them without parables"
        in layer("evangelium", "en")["segments"]["s01"]["translation"]
    )
    assert layer("postcommunio", "en")["segments"]["s01"]["translation"].startswith(
        "Nourished by heavenly delights, O Lord, we beseech You "
        "that we may always desire those same things by which we truly live."
    )
    doc = core("epistola")
    faces = {f.id: f.text for f in word_faces(doc["segments"][0])}
    assert faces["w167"] == "(quem" and faces["w170"] == "mórtuis)"


@pytest.mark.parametrize("role,body", [("collecta", 17), ("secreta", 11), ("postcommunio", 13)])
def test_abbreviated_proper_and_expanded_conclusion_are_distinct(role, body):
    graph = load("bibliography/graph.json")
    main = next(u for u in graph["uses"] if u["id"] == "use." + PREFIX + role + ".mr1962")
    assert main["role"] == "direct_approved_print"
    assert (
        f"{body}-word body and short Per Dominum cue, not the complete conclusion" in main["claim"]
    )
    expanded = next(
        u
        for u in graph["uses"]
        if u["id"] == "use." + PREFIX + role + ".expanded-conclusion.mr1962"
    )
    assert expanded["locator"]["section"] == "RG115a"
    assert "21-word" in expanded["claim"] and "22 words in total" in expanded["claim"]
    witness = next(
        w for w in graph["witnesses"] if w["id"] == "witness." + PREFIX + role + ".mr1962"
    )
    assert witness["review"] == {"status": "pending"}
    assert expanded["id"] in witness["source_dependencies"]["uses"]


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("change", ["reading", "body", "reference", "archive"])
def test_exact_raw_evidence_rejects_incomplete_or_corrupt_input(
    tmp_path, monkeypatch, role, change
):
    original = load("witnesses/raw/bindings.json")
    key, binding = next(
        (k, v)
        for k, v in original["bindings"].items()
        if v["witness"] == f"witnesses/{PREFIX + role}/do.txt"
    )
    archives = {
        span["archive"]
        for field in ("evidence", "references", "reading")
        for span in binding[field]
    }
    registry = {
        "version": original["version"],
        "archives": {k: original["archives"][k] for k in archives},
        "bindings": {key: deepcopy(binding)},
    }
    for name in [a["path"] for a in registry["archives"].values()] + [binding["witness"]]:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    registry_path = tmp_path / "witnesses/raw/bindings.json"
    registry_path.write_text(json.dumps(registry))
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    path = tmp_path / binding["witness"]
    assert resolve_binding(path, tmp_path) is not None
    assert check_transcriptions(path.parent) == ([], 1)
    pristine_registry = deepcopy(registry)
    pristine_files = {
        tmp_path / name: (tmp_path / name).read_bytes()
        for name in [a["path"] for a in registry["archives"].values()] + [binding["witness"]]
    }
    if change == "reading":
        registry["bindings"][key]["reading"][-1]["last"] -= 1
    elif change == "body":
        path.write_text(path.read_text() + "\nNeighboring text.\n")
    elif change == "reference":
        if registry["bindings"][key]["references"]:
            registry["bindings"][key]["references"][0]["text"] = "$Qui vivis"
        else:
            registry["bindings"][key]["evidence"][0]["section"] = "Oratio"
    else:
        archive = tmp_path / next(iter(registry["archives"].values()))["path"]
        archive.write_bytes(archive.read_bytes() + b"\n")
    registry_path.write_text(json.dumps(registry))
    with pytest.raises(BindingError):
        resolve_binding(path, tmp_path)
    assert check_transcriptions(path.parent)[0]
    for target, content in pristine_files.items():
        target.write_bytes(content)
    registry_path.write_text(json.dumps(pristine_registry))
    assert resolve_binding(path, tmp_path) is not None
    assert check_transcriptions(path.parent) == ([], 1)

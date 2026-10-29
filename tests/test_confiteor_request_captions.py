"""The two requests preserve their addressees, complement and singular beneficiary."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import store
from build_reader.emit import Table, core_artifact, expand, language_artifact
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT / "tests/fixtures/confiteor-request-captions.json").read_text())
ROWS = FIXTURE["rows"]


def prose_digest(layer):
    selected = {
        "about": layer["about"],
        "segments": {
            sid: {k: v for k, v in row.items() if k in ("translation", "narrative")}
            for sid, row in layer["segments"].items()
        },
    }
    return hashlib.sha256(
        json.dumps(selected, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def reader(core, raw):
    """Exercise the actual compact producer/expander; no copied projection."""
    doc, layer = expand_core(core), enrich_layer(core, raw)
    assert language_packs.check_core(core) == [], "native core"
    path = ROOT / "languages" / raw["language"] / "texts"
    path = path / (core["id"].replace(".", "/", 1) + ".json")
    assert language_packs.check_layer(core, raw, path) == [], "native layer"
    assert interlinear.check(doc, layer) == [], "native realization"
    parses, analyses, shared, local = Table(), Table(), Table(), Table()
    neutral = core_artifact(doc, core, parses, analyses, shared)
    localized = language_artifact(doc, layer, local)
    back, received = expand(
        neutral, localized, parses.order, analyses.order, shared.order, local.order
    )
    assert back["segments"] == doc["segments"]
    assert received["words"] == layer["words"]
    assert received["segments"] == layer["segments"]
    assert received["about"] == layer["about"]
    return received


def request(row, core, raw):
    received = reader(core, raw)
    segment = next(s for s in core["segments"] if s["id"] == "s06")
    words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    assert core["id"] == row["text"]
    assert " ".join(w["form"] + w.get("post", "") for w in segment["words"]) == row["latin_request"]
    assert segment["speaker"] == row["speaker"]
    assert words["w039"]["lemma"] == "precor"
    assert words["w039"]["morph"]["person"] == 1
    assert words["w039"]["morph"]["voice"] == "dep"
    assert {k: words["w060"][k] for k in ("form", "lemma", "morph")} == FIXTURE[
        "request_infinitive"
    ]
    assert [words[w]["form"] for w in ("w058", "w059")] == row["source_addressee"]
    assert words["w058"]["morph"]["case"] == "acc"
    assert words["w059"]["morph"]["case"] == "voc"
    assert words["w061"]["morph"]["governs"] == "abl" and words["w061"]["head"] == "w062"
    assert words["w062"]["morph"] == {"pos": "pron", "case": "abl", "number": "sg"}
    assert words["w063"]["morph"]["governs"] == "acc" and words["w063"]["head"] == "w064"

    def gloss(wid):
        return interlinear.effective_gloss(received, wid)

    assert gloss("w060") == "o modlitwę", "Polish request complement"
    assert [gloss(w) for w in ("w061", "w062")] == ["za", "mnie"], "singular speaker beneficiary"
    assert [gloss(w) for w in ("w058", "w059")] == row["polish_addressee"], "human addressee"
    assert [gloss(w) for w in ("w063", "w064", "w065", "w066")] == ["do", "Pana", "Boga", "naszego"]
    assert gloss("w039") == "błagam"
    assert words["w037"]["post"] == "." and gloss("w038") == "Przeto", "new Polish sentence"
    assert prose_digest(raw) == prose_digest(received) == row["polish_prose_sha256"]


@pytest.mark.parametrize("row", ROWS, ids=[r["text"] for r in ROWS])
def test_actual_request_and_valid_neighboring_forms_reach_the_reader(row):
    core = store.core(ROOT, row["text"])
    raw = store.raw_layer(ROOT, "pl", row["text"])
    request(row, core, raw)
    # The earlier confession still uses the dative; no broad case/infinitive rewrite.
    words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    assert words["w022"]["morph"]["case"] == "dat"
    assert interlinear.effective_gloss(raw, "w022") == row["first_confession_addressee"]
    english = reader(core, store.raw_layer(ROOT, "en", row["text"]))
    assert interlinear.effective_gloss(english, "w060") == "to pray"
    assert interlinear.effective_gloss(english, "w059") == row["english_vocative"]


@pytest.mark.parametrize("row", ROWS, ids=[r["text"] for r in ROWS])
@pytest.mark.parametrize(
    "word,bad,label",
    [
        ("w060", "modlić się", "Polish request complement"),
        ("w062", "nas", "singular speaker beneficiary"),
        ("w038", "przeto", "new Polish sentence"),
    ],
    ids=["predecessor-infinitive", "wrong-beneficiary", "predecessor-capital"],
)
def test_local_faults_fail_at_their_meaning_and_exact_restoration_recovers(row, word, bad, label):
    core = store.core(ROOT, row["text"])
    raw = store.raw_layer(ROOT, "pl", row["text"])
    saved = deepcopy(raw)
    request(row, core, raw)
    raw["words"][word]["gloss"] = bad
    assert raw != saved
    # These remain structurally valid captions: the bounded semantic check must reject them.
    assert interlinear.check(expand_core(core), enrich_layer(core, raw)) == []
    with pytest.raises(AssertionError, match=label):
        request(row, core, raw)
    raw.clear()
    raw.update(deepcopy(saved))
    assert raw == saved
    request(row, core, raw)

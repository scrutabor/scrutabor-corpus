"""Polish modal constructions preserve person, scope and complete coverage."""

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.layers import enrich_layer, expand_core
from checks.interlinear import check as check_interlinear
from checks.language_packs import check_layer
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
GROUPS = [
    ("dominica-iii-post-epiphaniam-epistola", "s01", ["w024", "w025"], "w025", "jest możliwe"),
    (
        "dominica-xxi-post-pentecosten-introitus",
        "s01",
        ["w009", "w010", "w011"],
        "w010",
        "nie ma nikogo, kto",
    ),
    (
        "dominica-xxi-post-pentecosten-introitus",
        "s01",
        ["w070", "w071", "w072"],
        "w071",
        "nie ma nikogo, kto",
    ),
    ("dominica-xxiv-post-pentecosten-evangelium", "s01", ["w134", "w135"], "w135", "jest możliwe"),
    (
        "septem-dolorum-beatae-mariae-virginis-sequentia",
        "s06",
        ["w053", "w054"],
        "w054",
        "mógłby nie",
    ),
]


def load(name):
    core = json.loads((ROOT / f"texts/proprium/{name}.json").read_text())
    path = ROOT / f"languages/pl/texts/proprium/{name}.json"
    return core, json.loads(path.read_text()), path


@pytest.mark.parametrize("name,sid,words,anchor,gloss", GROUPS)
def test_minimal_modal_groups_preserve_every_member(name, sid, words, anchor, gloss):
    core, layer, path = load(name)
    alignments = layer["segments"][sid]["alignments"]
    assert {"words": words, "anchor": anchor, "gloss": gloss} in alignments
    segment = next(s for s in core["segments"] if s["id"] == sid)
    covered = [w["id"] for w in segment["words"] if "gloss" in layer["words"][w["id"]]]
    covered += [wid for group in alignments for wid in group["words"]]
    assert Counter(covered) == Counter(w["id"] for w in segment["words"])
    assert not check_layer(core, layer, path)
    assert not check_interlinear(expand_core(core), enrich_layer(core, layer))


@pytest.mark.parametrize("name,sid,words,anchor,gloss", GROUPS)
@pytest.mark.parametrize("mutation", ["missing-member", "duplicate-gloss"])
def test_broken_modal_membership_is_rejected(name, sid, words, anchor, gloss, mutation):
    core, layer, _ = load(name)
    broken = deepcopy(layer)
    group = next(g for g in broken["segments"][sid]["alignments"] if g["words"] == words)
    if mutation == "missing-member":
        group["words"].remove(words[0])
    else:
        broken["words"][words[0]]["gloss"] = "powtórzone"
    assert check_interlinear(expand_core(core), enrich_layer(core, broken))


def test_possitis_person_depends_on_its_polish_construction():
    core, layer, path = load("dominica-xxi-post-pentecosten-epistola")
    words = {w["id"]: w for s in core["segments"] for w in s["words"]}
    for conjunction, modal in [("w014", "w015"), ("w048", "w049")]:
        assert layer["words"][conjunction]["gloss"] == "abyście"
        assert layer["words"][modal]["gloss"] == "mogli"
    assert layer["words"]["w084"]["gloss"] == "moglibyście"
    for wid in ["w015", "w049", "w084"]:
        assert words[wid]["lemma"] == "possum"
        assert words[wid]["morph"]["person"] == 2
        assert words[wid]["morph"]["number"] == "pl"
        assert words[wid]["morph"]["mood"] == "subj"
    assert not check_layer(core, layer, path)


def test_sorrows_negation_scope_preserves_the_contemplation_and_provenance():
    core, layer, _ = load("septem-dolorum-beatae-mariae-virginis-sequentia")
    wording = layer["segments"]["s06"]["translation"]
    assert wording == (
        "Któż mógłby się nie zasmucić, wpatrując się w Matkę Chrystusa, bolejącą wraz z Synem?"
    )
    assert layer["words"]["w055"]["gloss"] == "smucić się"
    assert layer["words"]["w058"]["gloss"] == "widząc"
    segment = next(s for s in core["segments"] if s["id"] == "s06")
    provenance = json.loads((ROOT / "languages/pl/translation-provenance.json").read_text())
    site = next(s for s in provenance["sites"] if s["text"] == core["id"] and s["segment"] == "s06")
    assert site["target_sha256"] == canonical_hash(wording)
    assert site["source_sha256"] == canonical_hash(source_payload(segment))
    assert (site["origin"], site["review"]) == ("working-unsettled", "working")

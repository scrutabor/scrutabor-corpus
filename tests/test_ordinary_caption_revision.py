"""Published predecessors and live sentence-opening/response contracts are distinct."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from edition_revision_fixture import (
    CAPTION_FILES,
    CAPTION_REVISION,
    PUBLISHED_FILES,
    before_caption_revision,
    before_edition_revision,
    before_owner_revision,
    before_review_revision,
)

from build_reader import emit, store
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs

ROOT = Path(__file__).resolve().parents[1]
RESPONSES = (
    ("ordinarium.deo-gratias-epistolae", "s01", ("w001", "w002")),
    ("ordinarium.evangelium-ultimum", "s15", ("w188", "w189")),
    ("ordinarium.ite-missa-est", "s06", ("w010", "w011")),
    ("ordinarium.ite-missa-est-paschale", "s06", ("w010", "w011")),
)


def case_changes():
    rows = []
    for relative, entry in CAPTION_FILES.items():
        for change in entry["changes"]:
            before, after = change.get("before"), change.get("after")
            if isinstance(before, str) and isinstance(after, str):
                assert after == before[0].upper() + before[1:]
                rows.append((relative, change["path"], before, after))
            elif change["path"][-1] == "alignments" and before is not None:
                assert len(before) == len(after)
                for index, (old, new) in enumerate(zip(before, after, strict=True)):
                    if old != new:
                        assert old["words"] == new["words"] and old["anchor"] == new["anchor"]
                        assert new["gloss"] == old["gloss"][0].upper() + old["gloss"][1:]
                        rows.append(
                            (
                                relative,
                                [*change["path"], index, "gloss"],
                                old["gloss"],
                                new["gloss"],
                            )
                        )
    return rows


CAPITALS = case_changes()


def at(value, fields):
    for field in fields:
        value = value[field]
    return value


def require_capital(layer, fields, expected):
    assert at(layer, fields) == expected, "current sentence opening"


def test_scope_and_published_parent_are_exact():
    assert CAPTION_REVISION["parent"] == "fb7e951df27da0df40ce44a3b403161d935fd1dd"
    assert len(CAPTION_FILES) == 72
    assert len(CAPITALS) == 128
    assert len(RESPONSES) == 4
    assert sum(len(e["changes"]) for e in CAPTION_FILES.values()) == 140
    assert len(set(CAPTION_FILES) & set(PUBLISHED_FILES)) == 19
    assert all(
        c["path"][0] == "words" or c["path"][-1] == "alignments"
        for e in CAPTION_FILES.values()
        for c in e["changes"]
    )


@pytest.mark.parametrize("relative", sorted(CAPTION_FILES))
def test_exact_previous_published_bytes_and_older_receipts(relative):
    live = (ROOT / relative).read_bytes()
    # Later receipts (the prayer reader review, then the owner decisions) may sit on top;
    # undo them exactly first, newest first.
    raw = before_review_revision(relative, before_owner_revision(relative, live))
    entry = CAPTION_FILES[relative]
    assert hashlib.sha256(raw).hexdigest() == entry["current"]
    published = before_caption_revision(relative, raw)
    assert hashlib.sha256(published).hexdigest() == entry["previous"]
    assert published != raw
    assert before_caption_revision(relative, published) is published
    assert before_caption_revision(relative, raw + b" ") == raw + b" "
    old = json.loads(published)
    current = json.loads(raw)
    assert {s: v["translation"] for s, v in old["segments"].items() if "translation" in v} == {
        s: v["translation"] for s, v in current["segments"].items() if "translation" in v
    }
    if relative in PUBLISHED_FILES:
        assert hashlib.sha256(published).hexdigest() == PUBLISHED_FILES[relative]["current"]
        assert (
            hashlib.sha256(before_edition_revision(relative, live)).hexdigest()
            == (PUBLISHED_FILES[relative]["previous"])
        )
    else:
        assert before_edition_revision(relative, live) == published
    assert (ROOT / relative).read_bytes() == live


@pytest.mark.parametrize("relative", sorted(CAPTION_FILES))
def test_complete_current_caption_layers_reach_reader_without_historical_projection(relative):
    parts = relative.split("/")
    language, text = parts[1], parts[3] + "." + Path(parts[4]).stem
    core, layer = store.core(ROOT, text), store.raw_layer(ROOT, language, text)
    doc, target = expand_core(core), enrich_layer(core, layer)
    assert language_packs.check_core(core) == []
    assert language_packs.check_layer(core, layer, ROOT / relative) == []
    assert interlinear.check(doc, target) == []
    parses, analyses, shared, local = emit.Table(), emit.Table(), emit.Table(), emit.Table()
    neutral = emit.core_artifact(doc, core, parses, analyses, shared)
    localized = emit.language_artifact(doc, target, local)
    received_core, received = emit.expand(
        neutral, localized, parses.order, analyses.order, shared.order, local.order
    )
    assert received_core["segments"] == doc["segments"]
    assert received["words"] == target["words"]
    for sid, segment in target["segments"].items():
        assert received["segments"][sid].get("alignments") == segment.get("alignments")


@pytest.mark.parametrize("relative,fields,before,after", CAPITALS)
def test_current_opening_rejects_old_case_then_recovers(relative, fields, before, after):
    layer = json.loads((ROOT / relative).read_bytes())
    require_capital(layer, fields, after)
    saved = deepcopy(layer)
    at(layer, fields[:-1])[fields[-1]] = before
    with pytest.raises(AssertionError, match="current sentence opening"):
        require_capital(layer, fields, after)
    layer = saved
    require_capital(layer, fields, after)


def response(core, layer, segment, members):
    doc, target = expand_core(core), enrich_layer(core, layer)
    assert language_packs.check_layer(core, layer, store.layer_path(ROOT, "en", core["id"])) == []
    assert interlinear.check(doc, target) == [], "current response realization"
    expected = {"words": list(members), "anchor": members[1], "gloss": "Thanks be to God"}
    touching = [
        group
        for group in target["segments"][segment].get("alignments", [])
        if set(group["words"]) & set(members)
    ]
    assert touching == [expected], "current complete response"
    assert all("gloss" not in layer["words"][w] for w in members)
    words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    assert words[members[0]]["lemma"] == "deus"
    assert words[members[0]]["morph"]["case"] == "dat"
    assert words[members[1]]["lemma"] == "gratia"
    assert words[members[1]]["morph"]["number"] == "pl"
    parses, analyses, shared, local = emit.Table(), emit.Table(), emit.Table(), emit.Table()
    neutral = emit.core_artifact(doc, core, parses, analyses, shared)
    localized = emit.language_artifact(doc, target, local)
    _, received = emit.expand(
        neutral, localized, parses.order, analyses.order, shared.order, local.order
    )
    assert received["segments"][segment]["alignments"] == target["segments"][segment]["alignments"]
    assert [interlinear.effective_gloss(received, w) for w in members] == ["", "Thanks be to God"]


@pytest.mark.parametrize("text,segment,members", RESPONSES)
def test_live_response_groups_roundtrip_and_reject_corruption(text, segment, members):
    core, layer = store.core(ROOT, text), store.raw_layer(ROOT, "en", text)
    saved = deepcopy(layer)
    response(core, layer, segment, members)
    for fault in ("lowercase", "wrong-anchor", "duplicate", "missing", "split"):
        layer = deepcopy(saved)
        group = layer["segments"][segment]["alignments"][0]
        if fault == "lowercase":
            group["gloss"] = "thanks be to God"
        elif fault == "wrong-anchor":
            group["anchor"] = members[0]
        elif fault == "duplicate":
            layer["words"][members[0]]["gloss"] = "To God"
        else:
            del layer["segments"][segment]["alignments"]
            if fault == "split":
                layer["words"][members[0]]["gloss"] = "to God"
                layer["words"][members[1]]["gloss"] = "thanks"
        with pytest.raises(AssertionError):
            response(core, layer, segment, members)
    response(core, saved, segment, members)

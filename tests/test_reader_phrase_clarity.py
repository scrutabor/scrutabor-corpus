"""Reader captions respect the span of each possessive and preserve the Latin cards."""

import hashlib
import json
from pathlib import Path

import pytest
from edition_revision_fixture import FILES, before_edition_revision

from build_reader import store
from checks import interlinear

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests/fixtures/reader-phrase-captions.json").read_bytes())


@pytest.mark.parametrize(("lang", "text", "sid", "words", "anchor", "gloss"), CASES)
def test_phrase_is_read_once_over_its_own_latin(lang, text, sid, words, anchor, gloss):
    layer = store.raw_layer(ROOT, lang, text)
    entries = interlinear.alignments_for(layer, sid)
    overlapping = [group for group in entries if set(group["words"]).intersection(words)]
    assert overlapping == [{"words": words, "anchor": anchor, "gloss": gloss}]
    assert all("gloss" not in layer["words"][word] for word in words)
    assert interlinear.check(store.core(ROOT, text), layer) == []


@pytest.mark.parametrize("relative", sorted(FILES))
def test_declared_changes_reproduce_the_former_edition_and_reject_corruption(relative):
    raw = (ROOT / relative).read_bytes()
    record = FILES[relative]
    assert hashlib.sha256(raw).hexdigest() == record["current"]
    prior = before_edition_revision(relative, raw)
    assert hashlib.sha256(prior).hexdigest() == record["previous"]
    assert before_edition_revision(relative, prior) is prior
    bad = raw + b" "
    assert bad != raw
    assert before_edition_revision(relative, bad) is bad


def test_repeated_confiteor_does_not_attach_mea_to_the_wrong_culpa():
    for text in ("ordinarium.confiteor", "ordinarium.confiteor-sacerdotis"):
        doc = store.core(ROOT, text)
        layer = store.raw_layer(ROOT, "en", text)
        segment = next(s for s in doc["segments"] if s["id"] == "s05")
        tokens = [
            (w["form"].lower(), layer["words"][w["id"]].get("gloss")) for w in segment["words"]
        ]
        assert tokens[:4] == [("mea", "my"), ("culpa", "fault")] * 2

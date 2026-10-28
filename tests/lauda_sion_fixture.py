"""Exact current Lauda Sion inputs and bounded historical comparison copies."""

import json
from copy import deepcopy
from pathlib import Path

from build_reader import store
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs, polish, prose
from checks.english import check as english_check
from checks.translation_provenance import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.corporis-christi-sequentia"
FIXTURE = json.loads((ROOT / "tests/fixtures/lauda-sion-remedy.json").read_text())
# Complete object hashes confine the historical comparison to these inputs.
FRAMES = {
    "core_before": "1e8695ec5d2686fb646d011f4190ca1ec0658df2dfb5f551f9088ba92aa59289",
    "core_after": "539b94fbaf88d1f0b439ff16303e36a3862ce9f7fbd7e45e7c08ecd755082cd0",
    "pl": {
        "before": "4bf84b0c8319de012dba106dafa5196801d28a5fcc3a4b5ed8ef5223d288b5ca",
        "after": "8ea21d550d1ed79fd3698868981ef6d6f646d2041de15c97b82ad4aad2980223",
    },
    "en": {
        "before": "0c3ef83c26871b7003969720000f513b81c63f04a78566b4f7e9f44b97773186",
        "after": "5c8c4d74cef6f8a7d1504396f51f63ca95712d5ddaa2fb689808ff4a59d39422",
    },
}
SITES = {f"{TEXT}.{segment}.pl" for segment in ("s03", "s05", "s07", "s10", "s13")} | {
    f"{TEXT}.s05.en"
}


def native(core, layer):
    assert language_packs.check_core(core) == [], "Lauda native core"
    assert (
        language_packs.check_layer(core, layer, store.layer_path(ROOT, layer["language"], TEXT))
        == []
    ), "Lauda native language"
    doc, localized = expand_core(core), enrich_layer(core, layer)
    assert interlinear.check(doc, localized) == [], "Lauda native coverage"
    assert prose.check(layer) == [], "Lauda native prose"
    if layer["language"] == "en":
        assert english_check(doc, localized) == [], "Lauda native English"
    else:
        assert polish.check(doc, localized) == [], "Lauda native Polish"


def current(core, layer):
    native(core, layer)
    assert core["id"] == layer["text"] == TEXT, "Lauda current identity"
    assert canonical_hash(core) == FRAMES["core_after"], "Lauda complete core"
    assert canonical_hash(layer) == FRAMES[layer["language"]]["after"], (
        "Lauda complete current layer"
    )


def predecessor_layer(core, layer):
    """Validate real current input first; return an exact comparison-only copy."""
    current(core, layer)
    language = layer["language"]
    restored = deepcopy(layer)
    for operation in reversed(FIXTURE["operations"]):
        if operation["language"] != language:
            continue
        value = restored
        for key in operation["path"][:-1]:
            value = value[key]
        key = operation["path"][-1]
        if operation.get("remove"):
            assert key not in value, "Lauda inverse removed gloss"
            value[key] = deepcopy(operation["before"])
        else:
            assert value[key] == operation["after"], "Lauda exact inverse field"
            if operation.get("add"):
                del value[key]
            else:
                value[key] = deepcopy(operation["before"])
    assert canonical_hash(restored) == FRAMES[language]["before"], (
        "Lauda complete predecessor layer"
    )
    return restored


def predecessor_core(core, layer):
    current(core, layer)
    restored = deepcopy(core)
    for operation in reversed(FIXTURE["core_operations"]):
        value = restored
        for key in operation["path"][:-1]:
            value = value[key]
        key = operation["path"][-1]
        assert value[key] == operation["after"], "Lauda exact declaration inverse"
        del value[key]
    assert canonical_hash(restored) == FRAMES["core_before"], "Lauda complete predecessor core"
    return restored


def predecessor_wording(site, row, target):
    """The six prose successors retain the existing historical label assertions."""
    assert site in SITES, "unchanged wording"
    language = site.rsplit(".", 1)[1]
    core, layer = store.core(ROOT, TEXT), store.raw_layer(ROOT, language, TEXT)
    current(core, layer)
    (operation,) = [r for r in FIXTURE["ledger"] if r["site"] == site]
    segment = operation["after"]["segment"]
    assert row == operation["after"], "unchanged wording"
    assert target == layer["segments"][segment]["translation"], "unchanged wording"
    assert canonical_hash(target) == row["target_sha256"], "unchanged wording"
    assert operation["after"]["language"] == language, "unchanged wording"
    before = FIXTURE["before_layers"][language]["segments"][segment]["translation"]
    assert canonical_hash(before) == operation["before"]["target_sha256"], "unchanged wording"
    return deepcopy(operation["before"]), before

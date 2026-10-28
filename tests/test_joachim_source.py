"""A direct Common text binding is not an executed feast-selection claim."""

import hashlib
import json
import shutil
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

import pytest
import witness_header_fixture as headers
from chant_fragment_fixture import before_chant_graph, before_chant_registry
from documentary_successor_fixture import before_language_successors
from lateran_epistle_source_fixture import before_lateran_graph, before_lateran_registry
from rosary_gospel_source_fixture import before_rosary_graph, before_rosary_registry
from test_main_ordo_registrations import before_exaltation_comparison

from build_reader.bibliography import public_text_evidence
from build_reader.bibliography_bindings import (
    BindingError,
    digest,
    validate_bindings,
    witness_subject,
)
from build_reader.layers import expand_core
from checks.apparatus import capital_accent_positions
from checks.collate import collate
from checks.raw_binding import (
    BindingError as RawBindingError,
)
from checks.raw_binding import (
    RawBindingSnapshot,
    load_registry,
    resolve_binding,
)

ROOT = Path(__file__).resolve().parents[1]
F = json.loads((ROOT / "tests/fixtures/joachim-source.json").read_text())
TEXT = "proprium.sancti-ioachim-confessoris-epistola"
REGISTRY = "witnesses/raw/bindings.json"
GRAPH = "bibliography/graph.json"
CURRENT_LEDGER_PREDECESSORS = {
    "languages/pl/translation-provenance.json": {
        "after_value_sha256": "d9ffe7d688ce9ba513e1c5f36b5b79c89d9419fbb59731511473cf324538ec0b",
        "before_value_sha256": "fcf387406346b15f30c19bb3c27c9f430687ef7e738a8af5d8752eb01fd52745",
        "rows": [
            {
                "before": {
                    "site": "proprium.annuntiatio-beatae-mariae-virginis-evangelium.s01.pl",
                    "text": "proprium.annuntiatio-beatae-mariae-virginis-evangelium",
                    "segment": "s01",
                    "language": "pl",
                    "familiar_core": False,
                    "origin": "working-unsettled",
                    "review": "working",
                    "source_sha256": (
                        "e293d21193cb63bd417401a9727c4fb27a0fb9e4742ade70ded946dea839dd4c"
                    ),
                    "target_sha256": (
                        "16127203dd761b2579b3c3b078879294ccd596c6d29c6405b0bcd0f15cb72156"
                    ),
                },
                "after": {
                    "site": "proprium.annuntiatio-beatae-mariae-virginis-evangelium.s01.pl",
                    "text": "proprium.annuntiatio-beatae-mariae-virginis-evangelium",
                    "segment": "s01",
                    "language": "pl",
                    "familiar_core": False,
                    "origin": "working-unsettled",
                    "review": "working",
                    "source_sha256": (
                        "b58632c63a29a5c7fc234c527f1a34cb86124b1e553c4d2d2e3b71d37ef8d946"
                    ),
                    "target_sha256": (
                        "b8ad1ab50d9c71e73b516ea482a80c0d2b3784f1f4300e3692629647ffe31fe3"
                    ),
                },
            },
            {
                "before": {
                    "site": "proprium.beata-maria-virgo-regina-evangelium.s01.pl",
                    "text": "proprium.beata-maria-virgo-regina-evangelium",
                    "segment": "s01",
                    "language": "pl",
                    "familiar_core": False,
                    "origin": "working-unsettled",
                    "review": "working",
                    "source_sha256": (
                        "85d3d5f9b0d38ddedc634d2f1a049b54dacbbf07953417c42f4ebc1d0aad1e58"
                    ),
                    "target_sha256": (
                        "71cf8b8e6d36fa5305ce80626b4edd6c2626ab95cd47cb82f4bb76202f305233"
                    ),
                },
                "after": {
                    "site": "proprium.beata-maria-virgo-regina-evangelium.s01.pl",
                    "text": "proprium.beata-maria-virgo-regina-evangelium",
                    "segment": "s01",
                    "language": "pl",
                    "familiar_core": False,
                    "origin": "working-unsettled",
                    "review": "working",
                    "source_sha256": (
                        "fd17edb317d73fc2672186fb51b465dfbb06c71ad96a2c3efea4f2388861b2d3"
                    ),
                    "target_sha256": (
                        "24c913dfdac06e1a319f2f3717ddbd9c977cbe584ea516b5b78abed60161f5f6"
                    ),
                },
            },
            {
                "before": {
                    "site": "proprium.beatae-mariae-virginis-a-rosario-evangelium.s01.pl",
                    "text": "proprium.beatae-mariae-virginis-a-rosario-evangelium",
                    "segment": "s01",
                    "language": "pl",
                    "familiar_core": False,
                    "origin": "working-unsettled",
                    "review": "working",
                    "source_sha256": (
                        "3880df2edc12b8b4219b336b8e421357259bfbf2ff13be3a7a000a4fcc65fdd3"
                    ),
                    "target_sha256": (
                        "16127203dd761b2579b3c3b078879294ccd596c6d29c6405b0bcd0f15cb72156"
                    ),
                },
                "after": {
                    "site": "proprium.beatae-mariae-virginis-a-rosario-evangelium.s01.pl",
                    "text": "proprium.beatae-mariae-virginis-a-rosario-evangelium",
                    "segment": "s01",
                    "language": "pl",
                    "familiar_core": False,
                    "origin": "working-unsettled",
                    "review": "working",
                    "source_sha256": (
                        "86d74a23902a109831eeb1fbcec44656dcd8ba731e87ff842884b6443863f1b7"
                    ),
                    "target_sha256": (
                        "b8ad1ab50d9c71e73b516ea482a80c0d2b3784f1f4300e3692629647ffe31fe3"
                    ),
                },
            },
            {
                "before": {
                    "site": "proprium.dominica-xxiv-post-pentecosten-evangelium.s01.pl",
                    "text": "proprium.dominica-xxiv-post-pentecosten-evangelium",
                    "segment": "s01",
                    "language": "pl",
                    "familiar_core": False,
                    "origin": "working-unsettled",
                    "review": "working",
                    "source_sha256": (
                        "2c95a576aaeaec41217c9c970d129664c25a126713ac9dbfe47134fc9c794254"
                    ),
                    "target_sha256": (
                        "bc5d99be24fb266a756d9b43f06dad32e1efbcbed72f6cb7c1904b34a15697ef"
                    ),
                },
                "after": {
                    "site": "proprium.dominica-xxiv-post-pentecosten-evangelium.s01.pl",
                    "text": "proprium.dominica-xxiv-post-pentecosten-evangelium",
                    "segment": "s01",
                    "language": "pl",
                    "familiar_core": False,
                    "origin": "working-unsettled",
                    "review": "working",
                    "source_sha256": (
                        "2c95a576aaeaec41217c9c970d129664c25a126713ac9dbfe47134fc9c794254"
                    ),
                    "target_sha256": (
                        "4e8892540d3150ebe4a5de4eb37cf173a857a113f000b701c38d48209e984e20"
                    ),
                },
            },
            {
                "before": {
                    "site": "proprium.nativitas-domini-in-aurora-graduale.s01.pl",
                    "text": "proprium.nativitas-domini-in-aurora-graduale",
                    "segment": "s01",
                    "language": "pl",
                    "familiar_core": False,
                    "origin": "working-unsettled",
                    "review": "working",
                    "source_sha256": (
                        "8a3c0942ae1ef4be868cdcbb2df9608ed492c2163f06c27c83b430be721c1801"
                    ),
                    "target_sha256": (
                        "491a9a630a7f62cbe0999eb9c242b6b34ff33573ab637a82680e73479e0cfbec"
                    ),
                },
                "after": {
                    "site": "proprium.nativitas-domini-in-aurora-graduale.s01.pl",
                    "text": "proprium.nativitas-domini-in-aurora-graduale",
                    "segment": "s01",
                    "language": "pl",
                    "familiar_core": False,
                    "origin": "working-unsettled",
                    "review": "working",
                    "source_sha256": (
                        "5b0d2b7af8df2d37ace98a317f9fcc88cb935c222fe4eca33ed50fa916eb902f"
                    ),
                    "target_sha256": (
                        "491a9a630a7f62cbe0999eb9c242b6b34ff33573ab637a82680e73479e0cfbec"
                    ),
                },
            },
            {
                "before": {
                    "site": "proprium.septem-dolorum-beatae-mariae-virginis-sequentia.s11.pl",
                    "text": "proprium.septem-dolorum-beatae-mariae-virginis-sequentia",
                    "segment": "s11",
                    "language": "pl",
                    "familiar_core": False,
                    "origin": "working-unsettled",
                    "review": "working",
                    "source_sha256": (
                        "2b259455c503c95dfbad7f04569c87644045f3415353f44bf0014b32e8cae5f7"
                    ),
                    "target_sha256": (
                        "308d590d9b1c97ef5e60a8ea929e1387de91dbb04efaf3b1214f751872be58fa"
                    ),
                },
                "after": {
                    "site": "proprium.septem-dolorum-beatae-mariae-virginis-sequentia.s11.pl",
                    "text": "proprium.septem-dolorum-beatae-mariae-virginis-sequentia",
                    "segment": "s11",
                    "language": "pl",
                    "familiar_core": False,
                    "origin": "working-unsettled",
                    "review": "working",
                    "source_sha256": (
                        "494d83215bf818a7611197e465c5491e2361c235c6eec92149c1b0928f9fed28"
                    ),
                    "target_sha256": (
                        "308d590d9b1c97ef5e60a8ea929e1387de91dbb04efaf3b1214f751872be58fa"
                    ),
                },
            },
        ],
    },
    "languages/en/translation-provenance.json": {
        "after_value_sha256": "f7cf876220888f042e9c736ce0c5731e299b06edfae933b3297449cd4f578399",
        "before_value_sha256": "9ec59f19ddb314d143acbc3b5af0b5930824ee634cacac9b8052058c30c924ac",
        "rows": [
            {
                "before": {
                    "site": "proprium.annuntiatio-beatae-mariae-virginis-evangelium.s01.en",
                    "text": "proprium.annuntiatio-beatae-mariae-virginis-evangelium",
                    "segment": "s01",
                    "language": "en",
                    "familiar_core": False,
                    "origin": "working-unsettled",
                    "review": "working",
                    "source_sha256": (
                        "e293d21193cb63bd417401a9727c4fb27a0fb9e4742ade70ded946dea839dd4c"
                    ),
                    "target_sha256": (
                        "860ed75d5b56fb59860a25c9e43b77cd39df85f532e1545c69daaca7ca77e1f4"
                    ),
                },
                "after": {
                    "site": "proprium.annuntiatio-beatae-mariae-virginis-evangelium.s01.en",
                    "text": "proprium.annuntiatio-beatae-mariae-virginis-evangelium",
                    "segment": "s01",
                    "language": "en",
                    "familiar_core": False,
                    "origin": "working-unsettled",
                    "review": "working",
                    "source_sha256": (
                        "b58632c63a29a5c7fc234c527f1a34cb86124b1e553c4d2d2e3b71d37ef8d946"
                    ),
                    "target_sha256": (
                        "d79167ed9cb963f3bdde68665616ac50057787fad209a3e19dc99992972b5e30"
                    ),
                },
            },
            {
                "before": {
                    "site": "proprium.beata-maria-virgo-regina-evangelium.s01.en",
                    "text": "proprium.beata-maria-virgo-regina-evangelium",
                    "segment": "s01",
                    "language": "en",
                    "familiar_core": False,
                    "origin": "working-unsettled",
                    "review": "working",
                    "source_sha256": (
                        "85d3d5f9b0d38ddedc634d2f1a049b54dacbbf07953417c42f4ebc1d0aad1e58"
                    ),
                    "target_sha256": (
                        "33bd121023961bf6ac86275e6f93f467d22d8084006cb43f5f6d3a43e7929108"
                    ),
                },
                "after": {
                    "site": "proprium.beata-maria-virgo-regina-evangelium.s01.en",
                    "text": "proprium.beata-maria-virgo-regina-evangelium",
                    "segment": "s01",
                    "language": "en",
                    "familiar_core": False,
                    "origin": "working-unsettled",
                    "review": "working",
                    "source_sha256": (
                        "fd17edb317d73fc2672186fb51b465dfbb06c71ad96a2c3efea4f2388861b2d3"
                    ),
                    "target_sha256": (
                        "987850df5eb30942765181bb0a974f46a41a857273aa3ec2f4c570d3d0e0daa0"
                    ),
                },
            },
            {
                "before": {
                    "site": "proprium.beatae-mariae-virginis-a-rosario-evangelium.s01.en",
                    "text": "proprium.beatae-mariae-virginis-a-rosario-evangelium",
                    "segment": "s01",
                    "language": "en",
                    "familiar_core": False,
                    "origin": "working-unsettled",
                    "review": "working",
                    "source_sha256": (
                        "3880df2edc12b8b4219b336b8e421357259bfbf2ff13be3a7a000a4fcc65fdd3"
                    ),
                    "target_sha256": (
                        "860ed75d5b56fb59860a25c9e43b77cd39df85f532e1545c69daaca7ca77e1f4"
                    ),
                },
                "after": {
                    "site": "proprium.beatae-mariae-virginis-a-rosario-evangelium.s01.en",
                    "text": "proprium.beatae-mariae-virginis-a-rosario-evangelium",
                    "segment": "s01",
                    "language": "en",
                    "familiar_core": False,
                    "origin": "working-unsettled",
                    "review": "working",
                    "source_sha256": (
                        "86d74a23902a109831eeb1fbcec44656dcd8ba731e87ff842884b6443863f1b7"
                    ),
                    "target_sha256": (
                        "d79167ed9cb963f3bdde68665616ac50057787fad209a3e19dc99992972b5e30"
                    ),
                },
            },
            {
                "before": {
                    "site": (
                        "proprium.dedicatio-archibasilicae-sanctissimi-salvatoris-epistola.s01.en"
                    ),
                    "text": "proprium.dedicatio-archibasilicae-sanctissimi-salvatoris-epistola",
                    "segment": "s01",
                    "language": "en",
                    "familiar_core": False,
                    "origin": "working-unsettled",
                    "review": "working",
                    "source_sha256": (
                        "1d95273d819c7494dadb75d2d63745734f619c1734fa5cfc6a04a69550cd1152"
                    ),
                    "target_sha256": (
                        "b1f270ce23942e000fb04805343d7e74613f669678103972efb6ed69e188c240"
                    ),
                },
                "after": {
                    "site": (
                        "proprium.dedicatio-archibasilicae-sanctissimi-salvatoris-epistola.s01.en"
                    ),
                    "text": "proprium.dedicatio-archibasilicae-sanctissimi-salvatoris-epistola",
                    "segment": "s01",
                    "language": "en",
                    "familiar_core": False,
                    "origin": "working-unsettled",
                    "review": "working",
                    "source_sha256": (
                        "1d95273d819c7494dadb75d2d63745734f619c1734fa5cfc6a04a69550cd1152"
                    ),
                    "target_sha256": (
                        "ca9ecaa51c596d79cd06b325443b94848bc95acd99e1e9a29ce6e8f5b8d788b0"
                    ),
                },
            },
            {
                "before": {
                    "site": "proprium.nativitas-domini-in-aurora-graduale.s01.en",
                    "text": "proprium.nativitas-domini-in-aurora-graduale",
                    "segment": "s01",
                    "language": "en",
                    "familiar_core": False,
                    "origin": "public-domain",
                    "review": "working",
                    "source_sha256": (
                        "8a3c0942ae1ef4be868cdcbb2df9608ed492c2163f06c27c83b430be721c1801"
                    ),
                    "target_sha256": (
                        "80e2af494f507a4bf60683116f246656194d384341b6f73b7fc484ae5aec7553"
                    ),
                },
                "after": {
                    "site": "proprium.nativitas-domini-in-aurora-graduale.s01.en",
                    "text": "proprium.nativitas-domini-in-aurora-graduale",
                    "segment": "s01",
                    "language": "en",
                    "familiar_core": False,
                    "origin": "public-domain",
                    "review": "working",
                    "source_sha256": (
                        "5b0d2b7af8df2d37ace98a317f9fcc88cb935c222fe4eca33ed50fa916eb902f"
                    ),
                    "target_sha256": (
                        "80e2af494f507a4bf60683116f246656194d384341b6f73b7fc484ae5aec7553"
                    ),
                },
            },
            {
                "before": {
                    "site": "proprium.septem-dolorum-beatae-mariae-virginis-sequentia.s11.en",
                    "text": "proprium.septem-dolorum-beatae-mariae-virginis-sequentia",
                    "segment": "s11",
                    "language": "en",
                    "familiar_core": False,
                    "origin": "working-unsettled",
                    "review": "working",
                    "source_sha256": (
                        "2b259455c503c95dfbad7f04569c87644045f3415353f44bf0014b32e8cae5f7"
                    ),
                    "target_sha256": (
                        "d529cc96e606dc7486b32ecd5a34d69838dc1b940c7378f3b587feb17177ccbd"
                    ),
                },
                "after": {
                    "site": "proprium.septem-dolorum-beatae-mariae-virginis-sequentia.s11.en",
                    "text": "proprium.septem-dolorum-beatae-mariae-virginis-sequentia",
                    "segment": "s11",
                    "language": "en",
                    "familiar_core": False,
                    "origin": "working-unsettled",
                    "review": "working",
                    "source_sha256": (
                        "494d83215bf818a7611197e465c5491e2361c235c6eec92149c1b0928f9fed28"
                    ),
                    "target_sha256": (
                        "d529cc96e606dc7486b32ecd5a34d69838dc1b940c7378f3b587feb17177ccbd"
                    ),
                },
            },
        ],
    },
}


def write(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def record(graph, field, identity):
    rows = [r for r in graph[field] if r["id"] == identity]
    assert len(rows) == 1
    return rows[0]


@pytest.fixture
def source(tmp_path):
    full = json.loads((ROOT / GRAPH).read_bytes())
    graph = deepcopy(full)
    graph["uses"] = [r for r in graph["uses"] if r.get("address", {}).get("text") == TEXT]
    graph["witnesses"] = [r for r in graph["witnesses"] if r["text"] == TEXT]
    graph["collations"] = [r for r in graph["collations"] if r["text"] == TEXT]
    current = json.loads((ROOT / REGISTRY).read_bytes())
    registry = {
        "version": 1,
        "archives": {F["archive_id"]: deepcopy(current["archives"][F["archive_id"]])},
        "bindings": {F["binding_id"]: deepcopy(current["bindings"][F["binding_id"]])},
    }
    assert registry["archives"][F["archive_id"]] == F["archive"]
    assert registry["bindings"][F["binding_id"]] == F["binding"]
    paths = [F["witness"], F["mr"], F["apparatus_path"], F["core"], F["archive"]["path"]]
    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    write(tmp_path, REGISTRY, registry)
    return {"root": tmp_path, "graph": graph, "registry": registry, "files": [*paths, REGISTRY]}


def healthy(state):
    root, graph = state["root"], state["graph"]
    assert load_registry(root) == state["registry"]
    actual = resolve_binding(root / F["witness"], root)
    assert actual is not None and actual.text == F["literal"]
    assert actual.source == F["expected_source"], "complete direct Common source"
    assert actual.spans == ((root / F["archive"]["path"], 349, 349),)
    assert len(actual.fragments) == 1
    fragment = actual.fragments[0]
    assert (fragment.path, fragment.line, fragment.start, fragment.end) == (
        root / F["archive"]["path"],
        349,
        0,
        len(F["literal"]),
    )
    assert fragment.raw == fragment.text == F["literal"]
    assert fragment.marker is None and fragment.whole_line and not fragment.partial_contract
    assert fragment.binding_id == F["binding_id"] and fragment.framing == ()
    doc = json.loads((root / F["core"]).read_bytes())
    witness = record(graph, "witnesses", F["witness_id"])
    subject = witness_subject(root, witness, graph, doc)
    assert subject["raw_resolution"] == F["expected_source"]
    assert set(subject["source_uses"]) == {F["use_id"]}
    assert validate_bindings(root, graph) == []
    return actual, subject


@contextmanager
def recover(state):
    root = state["root"]
    same_graph, same_registry = state["graph"], state["registry"]
    saved_graph, saved_registry = deepcopy(same_graph), deepcopy(same_registry)
    files = {p: (root / p).read_bytes() for p in state["files"]}
    try:
        yield
    finally:
        same_graph.clear()
        same_graph.update(saved_graph)
        same_registry.clear()
        same_registry.update(saved_registry)
        for relative, raw in files.items():
            (root / relative).write_bytes(raw)
        assert state["graph"] is same_graph and state["registry"] is same_registry
        assert state["graph"] == saved_graph and state["registry"] == saved_registry
        assert all((root / p).read_bytes() == raw for p, raw in files.items())
        healthy(state)


def test_complete_current_common_bytes_and_all_sixty_nine_word_coordinates(source):
    actual, _ = healthy(source)
    raw = (source["root"] / F["archive"]["path"]).read_bytes()
    assert len(raw) == 23833 and hashlib.sha256(raw).hexdigest() == F["archive"]["sha256"]
    lines = raw.decode().splitlines()
    assert lines[345:349] == F["mass_frame"]
    assert lines[349] == "" and lines[350] == "[Graduale]"
    assert len(actual.text.split()) == len(F["words"]) == 69
    assert " ".join(r["literal"] for r in F["words"]) == actual.text
    for row in F["words"]:
        assert lines[row["line"] - 1][row["start"] : row["end"]] == row["literal"]


def test_pending_native_and_reader_boundaries_do_not_promote_source_review(source):
    _, subject = healthy(source)
    root, graph = source["root"], source["graph"]
    doc = json.loads((root / F["core"]).read_bytes())
    assert subject["contract"] == "witness-review-2"
    mr = record(graph, "witnesses", F["mr_id"])
    assert "source_dependencies" not in mr
    with pytest.raises(
        BindingError, match="complete explicit source_dependencies declaration required"
    ):
        witness_subject(root, mr, graph, doc)
    assert all(
        r["review"] == {"status": "pending"} for r in graph["witnesses"] + graph["collations"]
    )
    (public,) = [r for r in public_text_evidence(graph)["texts"] if r["id"] == TEXT]
    assert public["witnesses"] == [] and "collation" not in public
    entries = [r for g in public["source_groups"] for r in g["entries"]]
    assert (
        next(r for r in entries if r["id"] == F["use_id"])["claim"]
        == (F["records"]["uses"]["after"]["claim"])
    )
    assert "raw_resolution" not in json.dumps(public)


RAW_FAULTS = (
    ("obsolete-path", "witness path declarations differ from bound evidence"),
    ("proper-path", "witness path declarations differ from bound evidence"),
    ("archive-revision", "revision differs from binding"),
    ("binding-revision", "witness revision differs from its raw binding"),
    ("digest", "SHA-256 mismatch"),
    ("section", "source section does not match evidence"),
    ("section-line", "source section does not match evidence"),
    ("range", "invalid source line range"),
    ("framing", "reading contains framing or lies outside textual evidence"),
    ("repeat", "reading omits or repeats source text"),
    ("missing-binding", "raw-binding marker and registered witness identity disagree"),
    ("missing-marker", "raw-binding marker and registered witness identity disagree"),
    ("duplicate-marker", "raw-binding marker and registered witness identity disagree"),
    ("wrong-witness", "raw-binding marker and registered witness identity disagree"),
    ("missing-archive", "unknown archive"),
    ("path-traversal", "invalid confined path"),
    ("uncorrected-accent", "transcription differs from its exact ordered raw reading"),
    ("body-order", "transcription differs from its exact ordered raw reading"),
    ("raw-bytes", "SHA-256 mismatch"),
)


@pytest.mark.parametrize("fault,message", RAW_FAULTS, ids=[r[0] for r in RAW_FAULTS])
def test_actual_raw_contract_fault_and_same_subject_recovery(source, fault, message):
    healthy(source)
    root, registry = source["root"], source["registry"]
    with recover(source):
        old = deepcopy(registry)
        witness = root / F["witness"]
        old_text = witness.read_text()
        plan = registry["bindings"][F["binding_id"]]
        archive = registry["archives"][F["archive_id"]]
        if fault in {"obsolete-path", "proper-path"}:
            archive["upstream"] = (
                "obsolete/missa/Latin/Commune/C5.txt"
                if fault == "obsolete-path"
                else "web/www/missa/Latin/Sancti/08-16.txt"
            )
        elif fault == "archive-revision":
            archive["revision"] = "0" * 40
        elif fault == "binding-revision":
            plan["revision"] = "0" * 40
        elif fault == "digest":
            archive["sha256"] = "0" * 64
        elif fault == "section":
            plan["evidence"][0]["section"] = "Lectio1"
        elif fault == "section-line":
            plan["evidence"][0]["section_line"] = 345
        elif fault == "range":
            plan["reading"][0]["last"] = 348
        elif fault == "framing":
            plan["reading"][0]["first"] = 348
        elif fault == "repeat":
            plan["reading"].append(deepcopy(plan["reading"][0]))
        elif fault == "missing-binding":
            del registry["bindings"][F["binding_id"]]
        elif fault == "missing-marker":
            witness.write_text(old_text.replace(F["marker"], "", 1))
        elif fault == "duplicate-marker":
            witness.write_text(F["marker"] + old_text)
        elif fault == "wrong-witness":
            plan["witness"] = F["mr"]
        elif fault == "missing-archive":
            del registry["archives"][F["archive_id"]]
        elif fault == "path-traversal":
            archive["path"] = "witnesses/raw/../escape.txt"
        elif fault == "uncorrected-accent":
            witness.write_text(
                old_text.replace(F["literal"], F["literal"].replace("potuit", "pótuit"), 1)
            )
        elif fault == "body-order":
            tokens = F["literal"].split()
            tokens[0], tokens[1] = tokens[1], tokens[0]
            witness.write_text(old_text.replace(F["literal"], " ".join(tokens), 1))
        else:
            raw = root / F["archive"]["path"]
            raw.write_bytes(raw.read_bytes() + b"\n# changed\n")
        write(root, REGISTRY, registry)
        assert registry != old or witness.read_text() != old_text or fault == "raw-bytes"
        with pytest.raises(RawBindingError, match=message):
            resolve_binding(witness, root)


def test_self_consistent_office_reading_is_not_a_mass_profile(source):
    healthy(source)
    root, registry = source["root"], source["registry"]
    with recover(source):
        plan = registry["bindings"][F["binding_id"]]
        plan["evidence"] = [
            {
                "archive": F["archive_id"],
                "first": 39,
                "last": 42,
                "section": "Lectio1",
                "section_line": 36,
            }
        ]
        plan["reading"] = [{"archive": F["archive_id"], "first": 39, "last": 42}]
        lines = (root / F["archive"]["path"]).read_text().splitlines()
        declaration = F["archive"]["upstream"] + " [Lectio1] (lines 39-42)"
        text = (root / F["witness"]).read_text()
        text = text.replace(F["path_header"], "# path: " + declaration + "\n", 1)
        text = text.replace(F["literal"], " ".join(lines[38:42]), 1)
        (root / F["witness"]).write_text(text)
        write(root, REGISTRY, registry)
        reading = resolve_binding(root / F["witness"], root)
        assert reading is not None and reading.text == " ".join(lines[38:42])
        assert reading.source["contract"] == "raw-reading-1"
        assert reading.text != F["literal"]
        with pytest.raises(AssertionError, match=r"^exact Mass Lectio profile(?:\n|$)"):
            assert reading.source["binding"] == F["binding"], "exact Mass Lectio profile"


SOURCE_FAULTS = (
    ("evidence", "digital evidence_sha256 identifies neither"),
    ("raw-dependency", "source requires its explicit exact raw binding"),
    ("wrong-binding", "declared raw binding differs from registered resolution"),
    ("missing-inventory", "complete explicit source_dependencies declaration required"),
    ("transcript-digest", "transcription_sha256 differs from the complete bound transcript"),
    ("apparatus-digest", "apparatus_sha256 differs from the complete apparatus"),
    ("apparatus-summary", "apparatus summary differs from the actual adjudicated entries"),
    ("witness-review", "reviewed subject changed"),
    ("collation-review", "reviewed collation requires reviewed witness bindings"),
)


@pytest.mark.parametrize("fault,message", SOURCE_FAULTS, ids=[r[0] for r in SOURCE_FAULTS])
def test_actual_bibliographic_identity_fault_and_recovery(source, fault, message):
    healthy(source)
    root, graph = source["root"], source["graph"]
    with recover(source):
        saved = deepcopy(graph)
        use = record(graph, "uses", F["use_id"])
        witness = record(graph, "witnesses", F["witness_id"])
        collation = record(graph, "collations", F["collation_id"])
        if fault == "evidence":
            use["evidence_sha256"] = F["proper_sha256"]
        elif fault == "raw-dependency":
            witness["source_dependencies"]["raw_binding"] = None
        elif fault == "wrong-binding":
            witness["source_dependencies"]["raw_binding"] = "foreign-binding"
        elif fault == "missing-inventory":
            del witness["source_dependencies"]
        elif fault == "transcript-digest":
            witness["transcription_sha256"] = "0" * 64
        elif fault == "apparatus-digest":
            raw_sha = hashlib.sha256((root / F["apparatus_path"]).read_bytes()).hexdigest()
            assert raw_sha != collation["apparatus_sha256"]
            collation["apparatus_sha256"] = raw_sha
        elif fault == "apparatus-summary":
            collation["apparatus"]["entries"] = 1
        elif fault == "witness-review":
            witness["review"] = {"status": "reviewed", "sha256": "0" * 64}
        else:
            collation["review"] = {"status": "reviewed", "sha256": "0" * 64}
        assert graph != saved
        if fault == "missing-inventory":
            # A legacy pending identity remains valid but cannot become a review subject.
            assert validate_bindings(root, graph) == []
            doc = json.loads((root / F["core"]).read_bytes())
            with pytest.raises(BindingError, match=message):
                witness_subject(root, witness, graph, doc)
        else:
            assert any(message in error for error in validate_bindings(root, graph))


@pytest.mark.parametrize("fault", ["missing-accent", "capital-accent"])
def test_the_new_lowercase_acute_is_not_hidden_or_misclassified(source, fault):
    healthy(source)
    root = source["root"]
    with recover(source):
        path = root / F["apparatus_path"]
        app = json.loads(path.read_bytes())
        assert app == F["apparatus"]
        saved = deepcopy(app)
        assert capital_accent_positions(app) == []
        try:
            if fault == "missing-accent":
                app["adjudicated"].pop()
                write(root, F["apparatus_path"], app)
                doc = json.loads((root / F["core"]).read_bytes())
                errors, _, _ = collate(expand_core(doc), root / f"witnesses/{TEXT}")
                assert any("UNADJUDICATED variant at w045" in error for error in errors)
            else:
                app["adjudicated"][-1]["class"] = "capital-accent"
                assert any(
                    "changed acute on a lowercase letter" in error
                    for error in capital_accent_positions(app)
                )
            assert app != saved
        finally:
            app.clear()
            app.update(saved)
            assert app == saved and capital_accent_positions(app) == []


def predecessor_target_input(relative, value):
    """Exact expected-side target inverse, never a native input or hash substitute."""
    rule = F["target_input_successors"][relative]
    assert F["unchanged"][relative] == rule["before_raw_sha256"]
    comparison = (
        before_language_successors(relative, value)
        if relative in CURRENT_LEDGER_PREDECESSORS
        else deepcopy(value)
    )
    if relative in CURRENT_LEDGER_PREDECESSORS:
        current = CURRENT_LEDGER_PREDECESSORS[relative]
        assert digest(comparison) == current["after_value_sha256"], "exact Joachim target successor"
        for change in current["rows"]:
            indices = [
                i
                for i, row in enumerate(comparison["sites"])
                if row["site"] == change["after"]["site"]
            ]
            assert len(indices) == 1, "exact Joachim target successor"
            i = indices[0]
            assert comparison["sites"][i] == change["after"], "exact Joachim target successor"
            comparison["sites"][i] = deepcopy(change["before"])
        assert digest(comparison) == current["before_value_sha256"], (
            "exact Joachim target successor"
        )
    assert digest(comparison) == rule["after_value_sha256"], "exact Joachim target successor"
    for change in reversed(rule["operations"]):
        field = comparison
        for key in change["key"][:-1]:
            field = field[key]
        assert field[change["key"][-1]] == change["after"], "exact Joachim target successor"
        field[change["key"][-1]] = deepcopy(change["before"])
    assert digest(comparison) == rule["before_value_sha256"], "exact Joachim target predecessor"
    return comparison


def test_real_collation_and_original_fields_remain_exact(source):
    healthy(source)
    root = source["root"]
    doc = json.loads((root / F["core"]).read_bytes())
    errors, warnings, stats = collate(expand_core(doc), root / f"witnesses/{TEXT}")
    assert errors == warnings == []
    assert (stats["words"], stats["witnesses"], stats["variants_adjudicated"]) == (69, 2, 2)
    assert stats["corrigenda"] == stats["substantive_variants"] == 0
    for relative, expected in F["unchanged"].items():
        raw_input = (ROOT / relative).read_bytes()
        if relative not in F["target_input_successors"]:
            assert hashlib.sha256(raw_input).hexdigest() == expected
            continue
        value = json.loads(raw_input)
        saved = deepcopy(value)
        predecessor = predecessor_target_input(relative, value)
        assert value == saved and predecessor is not value
        faults = ("wrong", "missing", "extra")
        if relative in CURRENT_LEDGER_PREDECESSORS:
            faults += ("source-digest", "target-digest", "row-extra")
        for fault in faults:
            try:
                if fault == "wrong":
                    key = next(iter(value))
                    value[key] = None
                elif fault == "missing":
                    del value[next(iter(value))]
                elif fault == "extra":
                    value["unexpected_comparison_field"] = True
                else:
                    changes = CURRENT_LEDGER_PREDECESSORS[relative]["rows"]
                    field = "source_sha256" if fault == "source-digest" else "target_sha256"
                    change = next(
                        r for r in changes if r["before"].get(field) != r["after"].get(field)
                    )
                    row = next(r for r in value["sites"] if r["site"] == change["after"]["site"])
                    if fault == "row-extra":
                        row["unexpected_comparison_field"] = True
                    else:
                        row[field] = "0" * 64
                assert value != saved
                with pytest.raises(
                    AssertionError, match=r"^exact Joachim target successor(?:\n|$)"
                ):
                    predecessor_target_input(relative, value)
            finally:
                value.clear()
                value.update(deepcopy(saved))
                assert value == saved
                assert predecessor_target_input(relative, value) == predecessor
    raw = (root / F["witness"]).read_text()
    assert F["historical_correction"] in raw and "# fetched: 2026-08-31\n" in raw
    assert F["apparatus"]["adjudicated"][0] == F["old_punctuation"]
    proper = (ROOT / F["proper_path"]).read_bytes()
    assert hashlib.sha256(proper).hexdigest() == F["proper_sha256"]
    lines = proper.decode().splitlines()
    assert "[Lectio]" not in lines
    assert lines[4].endswith("ex C5") and lines[6].endswith("ex C5")
    assert lines[9] == "ex C5;"


REGISTRY_FAULTS = (
    "missing-archive",
    "archive-path",
    "archive-revision",
    "archive-sha",
    "missing-binding",
    "witness",
    "binding-revision",
    "evidence",
    "reading",
    "references",
    "extra-field",
)


@pytest.mark.parametrize("fault", REGISTRY_FAULTS)
def test_exact_registry_comparison_inverse_rejects_changed_new_objects(fault):
    current = json.loads((ROOT / REGISTRY).read_bytes())
    saved = deepcopy(current)
    before = before_chant_registry(
        headers.before_joachim_registry(before_rosary_registry(before_lateran_registry(current)))
    )
    assert digest(before) == F["registry_before_canonical_sha256"]
    same_archives, same_bindings = current["archives"], current["bindings"]
    try:
        archive = current["archives"][F["archive_id"]]
        binding = current["bindings"][F["binding_id"]]
        if fault == "missing-archive":
            del same_archives[F["archive_id"]]
        elif fault.startswith("archive-"):
            archive[
                {
                    "archive-path": "upstream",
                    "archive-revision": "revision",
                    "archive-sha": "sha256",
                }[fault]
            ] += "-foreign"
        elif fault == "missing-binding":
            del same_bindings[F["binding_id"]]
        elif fault == "witness":
            binding["witness"] = F["mr"]
        elif fault == "binding-revision":
            binding["revision"] = "0" * 40
        elif fault == "evidence":
            binding["evidence"][0]["section_line"] = 36
        elif fault == "reading":
            binding["reading"][0]["last"] = 350
        elif fault == "references":
            binding["references"] = [{}]
        else:
            binding["optional"] = True
        assert current != saved
        with pytest.raises(AssertionError, match=r"^exact Joachim registry addition(?:\n|$)"):
            headers.before_joachim_registry(current)
    finally:
        same_archives.clear()
        same_archives.update(deepcopy(saved["archives"]))
        same_bindings.clear()
        same_bindings.update(deepcopy(saved["bindings"]))
        assert current["archives"] is same_archives and current["bindings"] is same_bindings
        assert current == saved
        assert (
            before_chant_registry(
                headers.before_joachim_registry(
                    before_rosary_registry(before_lateran_registry(current))
                )
            )
            == before
        )


@pytest.mark.parametrize("field", ["uses", "witnesses", "collations"])
def test_exact_complete_graph_comparison_and_recovery(field):
    graph = json.loads((ROOT / GRAPH).read_bytes())
    saved = deepcopy(graph)
    historical = before_exaltation_comparison(
        before_chant_graph(
            headers.before_joachim_records(before_rosary_graph(before_lateran_graph(graph)))
        )
    )
    assert digest(historical) == F["graph_before_canonical_sha256"]
    row = record(graph, field, F["records"][field]["after"]["id"])
    original = deepcopy(row)
    try:
        row["unexpected"] = True
        assert row != original
        with pytest.raises(
            AssertionError, match=r"^exact Joachim source comparison inverse(?:\n|$)"
        ):
            headers.before_joachim_records(graph)
    finally:
        row.clear()
        row.update(original)
        assert graph == saved
        assert (
            before_exaltation_comparison(
                before_chant_graph(
                    headers.before_joachim_records(before_rosary_graph(before_lateran_graph(graph)))
                )
            )
            == historical
        )


@pytest.mark.parametrize("fault", ["header", "accent", "body", "extra-field"])
def test_actual_current_transcript_inverse_rejects_and_recovers(source, fault):
    healthy(source)
    root = source["root"]
    path = root / F["witness"]
    saved = path.read_bytes()
    comparison = headers.before_joachim_transcript(F["witness"], saved)
    assert hashlib.sha256(comparison).hexdigest() == F["transcript"]["before_sha256"]
    assert comparison != saved and path.read_bytes() == saved
    with recover(source):
        if fault == "header":
            changed = saved.replace(F["path_header"].encode(), b"# path: foreign\n", 1)
        elif fault == "accent":
            changed = saved.replace(
                F["literal"].encode(), F["literal"].replace("potuit", "pótuit").encode(), 1
            )
        else:
            changed = saved + (b" Altered body.\n" if fault == "body" else b"# note: extra\n")
        assert changed != saved
        path.write_bytes(changed)
        with pytest.raises(AssertionError, match=r"^complete current Joachim transcript(?:\n|$)"):
            headers.before_joachim_transcript(F["witness"], path.read_bytes())
    assert path.read_bytes() == saved
    assert headers.before_joachim_transcript(F["witness"], path.read_bytes()) == comparison


def test_returned_source_does_not_mutate_a_snapshot(source):
    healthy(source)
    root = source["root"]
    snapshot = RawBindingSnapshot(root)
    first = snapshot.resolve(root / F["witness"])
    saved = deepcopy(first.source)
    first.source["binding"]["reading"].clear()
    assert first.source != saved
    assert snapshot.resolve(root / F["witness"]).source == saved == F["expected_source"]

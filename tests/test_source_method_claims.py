"""A text's source method that says its Divinum Officium reading is bound to its raw archives is
true only where that binding exists: an entry in the raw binding register for the text's `do`
witness, or retained raw files named by that witness's own path lines. A reading whose binding is
pending says so instead.
"""

import hashlib
import json
from pathlib import Path

import pytest

from build_reader.bibliography_bindings import witness_subject
from checks.raw_binding import BindingError as RawBindingError

ROOT = Path(__file__).resolve().parents[1]
CLAIM = "bound to its raw archive"


def claiming_texts():
    for path in sorted((ROOT / "texts").glob("*/*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        method = ((doc.get("editorial") or {}).get("source") or {}).get("method", "")
        if CLAIM in method:
            yield f"{path.parent.name}.{path.stem}"


def retained(relative):
    path = ROOT / relative
    return path.exists() and any(
        line.startswith("# path: witnesses/raw/")
        for line in path.read_text(encoding="utf-8").splitlines()
    )


def test_every_raw_binding_claim_has_its_binding():
    register = json.loads((ROOT / "witnesses/raw/bindings.json").read_text(encoding="utf-8"))
    bound = {entry["witness"] for entry in register["bindings"].values()}
    texts = list(claiming_texts())
    assert len(texts) > 100
    unbound = [
        text
        for text in texts
        if f"witnesses/{text}/do.txt" not in bound and not retained(f"witnesses/{text}/do.txt")
    ]
    assert unbound == []


# These are explicit source obligations, not a vocabulary search of English prose.
EXPLICIT_RAW_CLAIMS = json.loads(
    (ROOT / "tests/fixtures/raw-source-claim-bindings.json").read_text(encoding="utf-8")
)["claims"]
FAULTS = ("binding-withdrawn", "primary-use-removed", "archive-removed")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    path.write_text(raw, encoding="utf-8")


def explicit_claim_subject(root, claim):
    category, slug = claim["text"].split(".", 1)
    doc = read_json(root / "texts" / category / f"{slug}.json")
    assert doc["id"] == claim["text"]
    assert doc["editorial"]["source"]["method"].strip(), "missing source method"
    graph = read_json(root / "bibliography/graph.json")
    witnesses = [row for row in graph["witnesses"] if row["id"] == claim["witness"]]
    assert len(witnesses) == 1, "missing or repeated claimed witness"
    witness = witnesses[0]
    assert witness["text"] == claim["text"] and witness["transcription"] == "do"
    assert witness["use"] == claim["use"], "claimed primary source use differs"
    assert witness.get("source_dependencies", {}).get("raw_binding") == claim["binding"], (
        "missing declared raw binding"
    )
    uses = [row for row in graph["uses"] if row["id"] == claim["use"]]
    assert len(uses) == 1, "missing or repeated primary source use"
    assert uses[0]["address"] == {"kind": "text", "text": claim["text"]}
    assert uses[0]["role"] == "derived_digital_collation_aid"
    # The existing typed consumer checks the full transcript, source chain,
    # supplemental uses, raw resources, revision, resolved reading and hashes.
    # Constructing this subject neither changes nor grants a review status.
    subject = witness_subject(root, witness, graph, doc)
    assert subject["raw_resolution"]["binding_id"] == claim["binding"]
    assert claim["use"] in subject["source_uses"]
    return subject


def copied_claim(root, claim):
    """Copy real contributing bytes and their graph closure, never invented Latin."""
    registry = read_json(ROOT / "witnesses/raw/bindings.json")
    plan = registry["bindings"][claim["binding"]]
    keys = {
        row["archive"] for field in ("evidence", "references", "reading") for row in plan[field]
    }
    archives = {key: registry["archives"][key] for key in sorted(keys)}
    graph = read_json(ROOT / "bibliography/graph.json")
    witness = next(row for row in graph["witnesses"] if row["id"] == claim["witness"])
    use_ids = {claim["use"], *witness["source_dependencies"]["uses"]}
    uses = [row for row in graph["uses"] if row["id"] in use_ids]
    edition_ids = {row["edition"] for row in uses}
    item_ids = {row["digital_item"] for row in uses}
    editions = [row for row in graph["editions"] if row["id"] in edition_ids]
    work_ids = {row["work"] for row in editions}
    subset = {
        "works": [row for row in graph["works"] if row["id"] in work_ids],
        "editions": editions,
        "digital_items": [row for row in graph["digital_items"] if row["id"] in item_ids],
        "uses": uses,
        "witnesses": [witness],
        "collations": [],
    }
    category, slug = claim["text"].split(".", 1)
    paths = [
        f"texts/{category}/{slug}.json",
        plan["witness"],
        *(row["path"] for row in archives.values()),
    ]
    for relative in paths:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    write_json(
        root / "witnesses/raw/bindings.json",
        {
            "version": registry["version"],
            "archives": archives,
            "bindings": {claim["binding"]: plan},
        },
    )
    write_json(root / "bibliography/graph.json", subset)
    return root


def fixture_bytes(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def remove_evidence(root, claim, fault):
    graph_path = root / "bibliography/graph.json"
    graph = read_json(graph_path)
    if fault == "binding-withdrawn":
        register_path = root / "witnesses/raw/bindings.json"
        registry = read_json(register_path)
        plan = registry["bindings"].pop(claim["binding"])
        write_json(register_path, registry)
        transcript = root / plan["witness"]
        lines = transcript.read_text(encoding="utf-8").splitlines(keepends=True)
        markers = [line for line in lines if line.startswith("# raw-binding:")]
        assert markers == [f"# raw-binding: {claim['binding']}\n"]
        transcript.write_text(
            "".join(line for line in lines if not line.startswith("# raw-binding:")),
            encoding="utf-8",
        )
        witness = graph["witnesses"][0]
        del witness["source_dependencies"]
        # Keep the modified fixture's transcript digest truthful: failure must
        # concern the removed obligation, not a coincidental stale digest.
        witness["transcription_sha256"] = hashlib.sha256(
            transcript.read_text(encoding="utf-8").encode("utf-8")
        ).hexdigest()
        write_json(graph_path, graph)
    elif fault == "primary-use-removed":
        graph["uses"] = [row for row in graph["uses"] if row["id"] != claim["use"]]
        write_json(graph_path, graph)
    else:
        assert fault == "archive-removed"
        registry = read_json(root / "witnesses/raw/bindings.json")
        archive = next(iter(registry["archives"].values()))
        (root / archive["path"]).unlink()


@pytest.mark.parametrize("claim", EXPLICIT_RAW_CLAIMS, ids=lambda claim: claim["binding"])
def test_explicit_raw_claim_has_its_typed_source_subject(claim):
    assert len({row["text"] for row in EXPLICIT_RAW_CLAIMS}) == len(EXPLICIT_RAW_CLAIMS)
    explicit_claim_subject(ROOT, claim)


@pytest.mark.parametrize(
    ("claim", "fault"),
    [(claim, fault) for claim in EXPLICIT_RAW_CLAIMS for fault in FAULTS],
    ids=[f"{claim['binding']}-{fault}" for claim in EXPLICIT_RAW_CLAIMS for fault in FAULTS],
)
def test_explicit_raw_claim_rejects_removed_evidence_and_recovers(tmp_path, claim, fault):
    root = copied_claim(tmp_path, claim)
    healthy = explicit_claim_subject(root, claim)
    saved = fixture_bytes(root)
    expected = {
        "binding-withdrawn": (AssertionError, "missing declared raw binding"),
        "primary-use-removed": (AssertionError, "missing or repeated primary source use"),
        "archive-removed": (RawBindingError, "unreadable archive"),
    }
    error, message = expected[fault]
    try:
        remove_evidence(root, claim, fault)
        assert fixture_bytes(root) != saved
        with pytest.raises(error, match=message):
            explicit_claim_subject(root, claim)
    finally:
        # Restore the very same temporary subject, including a removed archive.
        for relative, raw in saved.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    assert fixture_bytes(root) == saved
    assert explicit_claim_subject(root, claim) == healthy

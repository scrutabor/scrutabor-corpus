"""Literal Advent readings keep complete contributions without granting review."""

import json
import shutil
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.bibliography import public_text_evidence
from build_reader.bibliography_bindings import (
    BindingError,
    collation_subject,
    digest,
    validate_bindings,
    witness_subject,
)
from checks.document import check as check_document
from checks.raw_binding import BindingError as RawBindingError
from checks.raw_binding import resolve_binding

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = "witnesses/raw/bindings.json"
EXPECTED = json.loads((ROOT / "tests/fixtures/advent-source-inventories.json").read_bytes())
CASES = EXPECTED["cases"]
SLICES = [case for case in CASES if case["plan"].get("contract") == "raw-reading-2"]
INTROITS = [case for case in CASES if case["text"].endswith("-introitus")]


def record(graph, collection, identity):
    rows = [row for row in graph[collection] if row["id"] == identity]
    assert len(rows) == 1
    return rows[0]


def file_bytes(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def save_registry(state):
    raw = json.dumps(state["registry"], ensure_ascii=False, indent=2) + "\n"
    (state["root"] / REGISTRY).write_text(raw, encoding="utf-8")


def isolated(tmp_path, case):
    root = tmp_path / "source"
    complete = json.loads((ROOT / "bibliography/graph.json").read_bytes())
    witnesses = [deepcopy(record(complete, "witnesses", i)) for i in case["witnesses"]]
    use_ids = {i for w in witnesses for i in [w["use"], *w["source_dependencies"]["uses"]]}
    uses = [deepcopy(record(complete, "uses", i)) for i in sorted(use_ids)]
    editions = {u["edition"] for u in uses}
    items = {u["digital_item"] for u in uses}
    works = {record(complete, "editions", i)["work"] for i in editions}
    graph = {
        "schema_version": complete["schema_version"],
        "works": [deepcopy(record(complete, "works", i)) for i in sorted(works)],
        "editions": [deepcopy(record(complete, "editions", i)) for i in sorted(editions)],
        "digital_items": [deepcopy(record(complete, "digital_items", i)) for i in sorted(items)],
        "uses": uses,
        "witnesses": witnesses,
        "collations": [deepcopy(record(complete, "collations", case["collation"]["id"]))],
    }
    register = json.loads((ROOT / REGISTRY).read_bytes())
    plan = deepcopy(register["bindings"][case["binding"]])
    assert plan == case["plan"]
    contributors = {
        s["archive"] for field in ("evidence", "references", "reading") for s in plan[field]
    }
    archives = {i: deepcopy(register["archives"][i]) for i in sorted(contributors)}
    assert archives == case["archives"]
    registry = {
        "version": register["version"],
        "archives": archives,
        "bindings": {case["binding"]: plan},
    }
    paths = [f"texts/proprium/{case['text'].split('.', 1)[1]}.json"]
    paths += [f"witnesses/{case['text']}/{name}" for name in ("do.txt", "mr.txt", "apparatus.json")]
    paths += [a["path"] for a in archives.values()]
    for relative in paths:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    state = {
        "root": root,
        "graph": graph,
        "doc": json.loads((root / paths[0]).read_bytes()),
        "registry": registry,
        "case": case,
    }
    save_registry(state)
    return state


def reading(state):
    return resolve_binding(state["root"] / state["case"]["plan"]["witness"], state["root"])


def subjects(state):
    root, graph, doc, case = (state[k] for k in ("root", "graph", "doc", "case"))
    result = {}
    for witness in graph["witnesses"]:
        result[witness["id"]] = witness_subject(root, witness, graph, doc)
        expected = case["witnesses"][witness["id"]]
        assert witness["source_dependencies"] == expected["source_dependencies"], (
            "source contribution inventory differs"
        )
        assert set(result[witness["id"]]["source_uses"]) == {
            expected["use"],
            *expected["source_dependencies"]["uses"],
        }, "source contribution inventory differs"
    collation = record(graph, "collations", case["collation"]["id"])
    return result, collation_subject(root, collation, doc, result)


@contextmanager
def restored(state):
    original = {key: deepcopy(state[key]) for key in ("graph", "doc", "registry")}
    files = file_bytes(state["root"])
    healthy, raw = subjects(state), reading(state)
    try:
        yield
    finally:
        changed = any(state[key] != value for key, value in original.items())
        changed = changed or file_bytes(state["root"]) != files
        for key, value in original.items():
            state[key].clear()
            state[key].update(deepcopy(value))
        for relative, content in files.items():
            (state["root"] / relative).write_bytes(content)
        assert file_bytes(state["root"]) == files
        assert all(state[key] == value for key, value in original.items())
        assert changed, "the adverse fixture was not changed"
        assert subjects(state) == healthy and reading(state) == raw


@pytest.mark.parametrize("case", CASES, ids=[c["binding"] for c in CASES])
def test_complete_literal_resolution_preserves_every_position(tmp_path, case):
    state = isolated(tmp_path, case)
    actual = reading(state)
    assert actual is not None and actual.text == case["reading"]
    assert actual.source["binding_id"] == case["binding"]
    assert actual.source["binding"] == case["plan"]
    assert actual.source["archives"] == case["archives"]
    positions = [
        [s["id"], w["id"], w.get("pre", ""), w["form"], w.get("post", "")]
        for s in state["doc"]["segments"]
        for w in s.get("words", [])
    ]
    assert positions == case["positions"]
    assert len(actual.text.split()) == len(positions)
    if case in SLICES:
        fragment = next(f for f in actual.fragments if not f.whole_line)
        assert fragment.partial_contract
        assert fragment.marker_scope_verified is (fragment.start == 0)


@pytest.mark.parametrize("case", CASES, ids=[c["binding"] for c in CASES])
def test_complete_source_subjects_remain_pending_and_withheld(tmp_path, case):
    state = isolated(tmp_path, case)
    text_path = state["root"] / "texts" / (case["text"].replace(".", "/", 1) + ".json")
    assert check_document(state["doc"], text_path) == []
    graph = state["graph"]
    actual, collation = subjects(state)
    assert len(actual) == len(case["witnesses"]) == 2
    for witness in graph["witnesses"]:
        expected = case["witnesses"][witness["id"]]
        assert {key: witness[key] for key in expected} == expected
        assert witness["coverage"] == {"kind": "full"}
        assert witness["review"] == {"status": "pending"}
        subject = actual[witness["id"]]
        assert subject["contract"] == "witness-review-2"
        for identity, source in subject["source_uses"].items():
            expected_use = case["uses"][identity]
            assert {key: source["use"][key] for key in expected_use} == expected_use
            assert source["digital_item"]["edition"] == source["edition"]["id"]
            if witness["transcription"] == "do":
                assert source["digital_item"]["revision"] == case["plan"]["revision"]
                assert source["digital_item"]["kind"] == "born-digital"
                if source["edition"]["id"] == "edition.divinum-officium-missa.21cb2d37":
                    assert source["edition"]["rights"]["status"] == "unverified"
            else:
                assert subject["raw_resolution"] is None
    current = record(graph, "collations", case["collation"]["id"])
    assert {key: current[key] for key in case["collation"]} == case["collation"]
    assert case["collation"]["review"] == {"status": "pending"}
    assert collation["contract"] == "collation-review-2"
    assert validate_bindings(state["root"], graph) == []
    public = public_text_evidence(graph)["texts"]
    assert len(public) == 1 and public[0]["id"] == case["text"]
    assert public[0]["witnesses"] == [] and "collation" not in public[0]


@pytest.mark.parametrize("case", SLICES, ids=[c["binding"] for c in SLICES])
def test_shared_gradual_alleluia_boundary_rejects_neighboring_text(tmp_path, case):
    state = isolated(tmp_path, case)
    with restored(state):
        plan = state["registry"]["bindings"][case["binding"]]
        span = next(s for s in plan["reading"] if "fragment" in s)
        fragment = span["fragment"]
        before = deepcopy(fragment)
        if fragment["start"]:
            fragment["start"] = 0
        else:
            path = state["root"] / case["archives"][span["archive"]]["path"]
            fragment["end"] = len(path.read_text(encoding="utf-8").splitlines()[span["first"] - 1])
        assert fragment != before
        save_registry(state)
        message = "reading contains framing or lies outside textual evidence"
        with pytest.raises(RawBindingError, match=message):
            reading(state)


@pytest.mark.parametrize("case", INTROITS, ids=[c["binding"] for c in INTROITS])
@pytest.mark.parametrize("fault", ("declaration", "evidence", "reference", "printed-contributions"))
def test_introit_gloria_and_reprise_contributions_cannot_disappear(tmp_path, case, fault):
    state = isolated(tmp_path, case)
    graph = state["graph"]
    with restored(state):
        digital = next(w for w in graph["witnesses"] if w["transcription"] == "do")
        expected, error = "source contribution inventory differs", AssertionError
        if fault == "declaration":
            assert len(digital["source_dependencies"]["uses"]) == 1
            digital["source_dependencies"]["uses"].clear()
        elif fault == "evidence":
            extra = digital["source_dependencies"]["uses"][0]
            record(graph, "uses", extra)["evidence_sha256"] = "0" * 64
            error, expected = BindingError, "digital evidence_sha256 identifies neither"
        elif fault == "reference":
            plan = state["registry"]["bindings"][case["binding"]]
            assert plan["references"][0]["text"] == "&Gloria"
            plan["references"].clear()
            save_registry(state)
            error, expected = RawBindingError, "incomplete source reference coverage"
        else:
            printed = next(w for w in graph["witnesses"] if w["transcription"] == "mr")
            assert printed["source_dependencies"]["uses"]
            printed["source_dependencies"]["uses"].clear()
        with pytest.raises(error, match=expected):
            subjects(state)


def test_fourth_communion_keeps_the_real_caller_and_historical_destination(tmp_path):
    case = next(c for c in CASES if c["binding"] == "advent-iv-communio")
    state = isolated(tmp_path, case)
    plan = case["plan"]
    assert plan["references"] == [
        {"archive": "advent-iv-21cb2d37", "line": 57, "text": "@Commune/C10a:Communio", "target": 1}
    ]
    destination = case["archives"]["advent-marian-common-21cb2d37"]
    assert destination["upstream"] == "obsolete/missa/Latin/Commune/C10a.txt"
    assert plan["evidence"][1]["section"] == "Communio"
    assert plan["reading"] == [
        {"archive": "advent-marian-common-21cb2d37", "first": 49, "last": 49}
    ]
    with restored(state):
        witness = next(w for w in state["graph"]["witnesses"] if w["transcription"] == "do")
        assert len(witness["source_dependencies"]["uses"]) == 1
        witness["source_dependencies"]["uses"].clear()
        with pytest.raises(AssertionError, match="source contribution inventory differs"):
            subjects(state)


@pytest.mark.parametrize("case", CASES, ids=[c["binding"] for c in CASES])
def test_stale_primary_evidence_is_rejected_and_same_copy_recovers(tmp_path, case):
    state = isolated(tmp_path, case)
    with restored(state):
        witness = next(w for w in state["graph"]["witnesses"] if w["transcription"] == "do")
        use = record(state["graph"], "uses", witness["use"])
        assert use["evidence_sha256"] != "0" * 64
        use["evidence_sha256"] = "0" * 64
        with pytest.raises(BindingError, match="digital evidence_sha256 identifies neither"):
            subjects(state)


@pytest.mark.parametrize("ruling", EXPECTED["rulings"], ids=[r["id"] for r in EXPECTED["rulings"]])
def test_apparatus_ruling_direction_is_exact_and_old_ruling_invalidates_subject(tmp_path, ruling):
    case = next(c for c in CASES if c["text"] == ruling["text"])
    state = isolated(tmp_path, case)
    path = state["root"] / f"witnesses/{case['text']}/apparatus.json"
    with restored(state):
        apparatus = json.loads(path.read_bytes())
        entry = next(e for e in apparatus["adjudicated"] if e["at"] == ruling["at"])
        assert entry == ruling["after"] and entry["ruling"] != ruling["before"]
        entry["ruling"] = ruling["before"]
        raw = json.dumps(apparatus, ensure_ascii=False, indent=2) + "\n"
        path.write_text(raw, encoding="utf-8")
        message = "apparatus_sha256 differs from the complete apparatus"
        with pytest.raises(BindingError, match=message):
            subjects(state)


@pytest.mark.parametrize("fault", ("transcript", "selected", "witness-review", "collation-review"))
def test_pending_is_not_an_escape_from_stale_bytes_or_fabricated_review(tmp_path, fault):
    case = next(c for c in CASES if c["binding"] == "advent-iv-communio")
    state = isolated(tmp_path, case)
    with restored(state):
        witness = state["graph"]["witnesses"][0]
        collation = state["graph"]["collations"][0]
        if fault == "transcript":
            witness["transcription_sha256"] = "0" * 64
            expected = "transcription_sha256 differs"
        elif fault == "selected":
            collation["selected_text_sha256"] = "0" * 64
            expected = "selected_text_sha256 differs"
        elif fault == "witness-review":
            witness["review"] = {"status": "reviewed", "sha256": "0" * 64}
            expected = "reviewed subject changed"
        else:
            collation["review"] = {"status": "reviewed", "sha256": "0" * 64}
            expected = "reviewed collation requires reviewed witness bindings"
        errors = validate_bindings(state["root"], state["graph"])
        if fault in {"transcript", "witness-review"}:
            message = (
                "transcription_sha256 differs from the complete bound transcript"
                if fault == "transcript"
                else "reviewed subject changed; re-review or mark pending explicitly"
            )
            assert errors == [
                f"bibliography witness {witness['id']}: {message}",
                f"bibliography collation {collation['id']}: "
                "collation has an unbound or duplicate witness",
            ]
        else:
            assert len(errors) == 1 and expected in errors[0]


def test_preexisting_raw_registry_objects_are_unchanged():
    registry = json.loads((ROOT / REGISTRY).read_bytes())
    # This separately added response must not refresh the pre-Advent baseline.
    identity = "deo-gratias-epistolae-44667ff"
    expected = {
        "witness": "witnesses/ordinarium.deo-gratias-epistolae/do.txt",
        "revision": "44667ff518b8ff1439780470828b39714f5306a2",
        "evidence": [
            {
                "archive": "prayers",
                "first": 81,
                "last": 82,
                "section": "Deo gratias",
                "section_line": 81,
            }
        ],
        "references": [],
        "reading": [{"archive": "prayers", "first": 82, "last": 82}],
    }

    # Three complete C9 objects are later additions, not a new historical baseline.
    c9 = {
        "archives": {
            "common-c9": {
                "upstream": "web/www/horas/Latin/Commune/C9.txt",
                "revision": "44667ff518b8ff1439780470828b39714f5306a2",
                "path": "witnesses/raw/do-44667ff/horas/Latin/Commune/C9.txt",
                "sha256": ("fb739e09f1cef9fd0f917db8875bfd3444e0c1d588c03e884081250e4d242516"),
            }
        },
        "bindings": {
            ("do-proprium-commemoratio-omnium-fidelium-defunctorum-missa-i-communio"): {
                "contract": "raw-reading-2",
                "witness": (
                    "witnesses/proprium.commemoratio-omnium-fidelium-defunct"
                    "orum-missa-i-communio/do.txt"
                ),
                "revision": "44667ff518b8ff1439780470828b39714f5306a2",
                "evidence": [
                    {
                        "archive": "common-c9",
                        "section": "Communio",
                        "section_line": 417,
                        "first": 419,
                        "last": 419,
                    },
                    {
                        "archive": "common-c9",
                        "section": "Communio",
                        "section_line": 417,
                        "first": 420,
                        "last": 420,
                        "fragment": {
                            "start": 2,
                            "end": 44,
                            "text": "Cum Sanctis tuis in ætérnum: quia pius es.",
                            "marker": None,
                            "reason": (
                                "Exclude only the response asterisk and its following sp"
                                "ace; retain the complete literal response."
                            ),
                        },
                    },
                    {
                        "archive": "common-c9",
                        "section": "Communio",
                        "section_line": 417,
                        "first": 421,
                        "last": 421,
                    },
                    {
                        "archive": "common-c9",
                        "section": "Communio",
                        "section_line": 417,
                        "first": 422,
                        "last": 422,
                        "fragment": {
                            "start": 2,
                            "end": 44,
                            "text": "Cum Sanctis tuis in ætérnum: quia pius es.",
                            "marker": None,
                            "reason": (
                                "Exclude only the response asterisk and its following sp"
                                "ace; retain the complete literal response."
                            ),
                        },
                    },
                ],
                "references": [],
                "reading": [
                    {"archive": "common-c9", "first": 419, "last": 419},
                    {
                        "archive": "common-c9",
                        "first": 420,
                        "last": 420,
                        "fragment": {"start": 2, "end": 44},
                    },
                    {"archive": "common-c9", "first": 421, "last": 421},
                    {
                        "archive": "common-c9",
                        "first": 422,
                        "last": 422,
                        "fragment": {"start": 2, "end": 44},
                    },
                ],
            },
            ("do-proprium-commemoratio-omnium-fidelium-defunctorum-missa-i-introitus"): {
                "contract": "raw-reading-2",
                "witness": (
                    "witnesses/proprium.commemoratio-omnium-fidelium-defunct"
                    "orum-missa-i-introitus/do.txt"
                ),
                "revision": "44667ff518b8ff1439780470828b39714f5306a2",
                "evidence": [
                    {
                        "archive": "common-c9",
                        "section": "Introitus",
                        "section_line": 281,
                        "first": 283,
                        "last": 286,
                    }
                ],
                "references": [],
                "reading": [
                    {"archive": "common-c9", "first": 283, "last": 283},
                    {"archive": "common-c9", "first": 285, "last": 285},
                    {"archive": "common-c9", "first": 286, "last": 286},
                ],
            },
        },
    }

    # Fixed independent source plans, not an allowlist inferred from this registry.
    ordo_rows = json.loads((ROOT / "tests/fixtures/main-ordo-source-oracle.json").read_bytes())[
        "rows"
    ]
    ordo = {row["id"]: row["expected_source"]["binding"] for row in ordo_rows}
    assert len(ordo) == len(ordo_rows) == 49

    def check():
        assert registry["bindings"].get(identity) == expected
        historical = deepcopy(registry)
        del historical["bindings"][identity]
        for field, rows in c9.items():
            for key, value in rows.items():
                assert historical[field].get(key) == value, "C9 registry successor differs"
                del historical[field][key]
        for key, value in ordo.items():
            assert historical["bindings"].get(key) == value, "main Ordo registry successor differs"
            del historical["bindings"][key]
        for field in ("archives", "bindings"):
            new = set(EXPECTED["new_registry_keys"][field])
            assert new <= set(historical[field])
            prior = {key: value for key, value in historical[field].items() if key not in new}
            assert digest(prior) == EXPECTED["prior_registry"][field]["sha256"]
            assert len(prior) == EXPECTED["prior_registry"][field]["records"]

    check()
    saved = deepcopy(registry)
    bindings = registry["bindings"]
    for fault in ("missing", "wrong-line", "extra-field", "unrelated-row"):
        try:
            if fault == "missing":
                del bindings[identity]
            elif fault == "wrong-line":
                bindings[identity]["reading"][0]["first"] = 81
            elif fault == "extra-field":
                bindings[identity]["optional"] = True
            else:
                bindings["unexpected-response"] = deepcopy(bindings[identity])
            assert digest(registry) != digest(saved)
            with pytest.raises(AssertionError):
                check()
        finally:
            bindings.clear()
            bindings.update(deepcopy(saved["bindings"]))
            assert registry["bindings"] is bindings and registry == saved
            assert digest(registry) == digest(saved)
            check()

    # These are exact expected-side inventory faults, not claimed raw API errors.
    for field, rows in c9.items():
        for key in rows:
            for fault in ("missing", "wrong-revision", "extra-field", "source-span"):
                saved = deepcopy(registry)
                same = {name: registry[name] for name in ("archives", "bindings")}
                try:
                    row = registry[field][key]
                    if fault == "missing":
                        del registry[field][key]
                    elif fault == "wrong-revision":
                        row["revision"] = "0" * 40
                    elif fault == "extra-field":
                        row["optional"] = True
                    elif field == "archives":
                        row["upstream"] = "web/www/horas/Latin/Commune/C10.txt"
                    else:
                        row["reading"][0]["first"] -= 1
                    assert digest(registry) != digest(saved)
                    with pytest.raises(
                        AssertionError, match=r"^C9 registry successor differs(?:\n|$)"
                    ):
                        check()
                finally:
                    for name, container in same.items():
                        container.clear()
                        container.update(deepcopy(saved[name]))
                        assert registry[name] is container
                    assert registry == saved and digest(registry) == digest(saved)
                    check()

    ordo_identity = next(row["id"] for row in ordo_rows if row["text"] == "ordinarium.per-ipsum")
    for fault in (
        "missing",
        "wrong-profile",
        "wrong-witness",
        "wrong-revision",
        "wrong-contract",
        "extra-field",
    ):
        saved = deepcopy(registry)
        same_bindings = registry["bindings"]
        try:
            row = same_bindings[ordo_identity]
            if fault == "missing":
                del same_bindings[ordo_identity]
            elif fault == "wrong-profile":
                row["profile"] += "-foreign"
            elif fault == "wrong-witness":
                row["witness"] = "witnesses/ordinarium.kyrie/do.txt"
            elif fault == "wrong-revision":
                row["revision"] = "0" * 40
            elif fault == "wrong-contract":
                row["contract"] = "raw-reading-unsupported"
            else:
                row["optional"] = True
            assert digest(registry) != digest(saved)
            with pytest.raises(
                AssertionError, match=r"^main Ordo registry successor differs(?:\n|$)"
            ):
                check()
        finally:
            same_bindings.clear()
            same_bindings.update(deepcopy(saved["bindings"]))
            assert registry["bindings"] is same_bindings
            assert registry == saved and digest(registry) == digest(saved)
            check()

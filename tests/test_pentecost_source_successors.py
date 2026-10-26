"""Bounded Pentecost source composition, exact fragments and pending reviews."""

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
from witness_header_fixture import expected_review

from build_reader import bibliography, store
from build_reader.bibliography_bindings import BindingError as SubjectError
from build_reader.bibliography_bindings import collation_subject, digest, witness_subject
from checks.raw_binding import REGISTRY, BindingError, resolve_binding

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "proprium.dominica-pentecostes-"
ALLELUIA = PREFIX + "alleluia"
KEY = "do-proprium-dominica-pentecostes-alleluia"
ARCHIVE = "pentecost-gospel"
FIXTURE = json.loads(
    (Path(__file__).with_name("fixtures") / "pentecost-successors.json").read_text()
)
SOURCE_CASES = ("P1", "N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8", "C1", "C2", "N9", "C3")


# These source subjects were reviewed; unrelated records remain pending.
ADOPTED_SOURCE_REVIEWS = {
    "witness.proprium.vigilia-pentecostes-secreta.do44667ff": (
        "f21d7b74e86cf9ee5990eccd4a91b7f05a6548387d4ed43cb748fdbe317e26e2"
    ),
    "witness.proprium.vigilia-pentecostes-secreta.mr1962": (
        "d5cc96e8569138bfe622175fc2e9a8719fcd2c6c96e5cd52befda7d988e77191"
    ),
    "collation.proprium.vigilia-pentecostes-secreta.mr1962-do44667ff": (
        "c06a88773afc98990be4ce65abf3801cce5d73019b4d47cfe1822912d0c7fcd6"
    ),
}


def write_json(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def saved_files(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def restore_files(root, saved):
    assert set(saved_files(root)) == set(saved), "source control file inventory"
    for name, raw in saved.items():
        (root / name).write_bytes(raw)
    assert saved_files(root) == saved, "source control exact restoration"


@pytest.fixture
def alleluia_source(tmp_path):
    full = json.loads((ROOT / REGISTRY).read_text())
    binding, archive = deepcopy(full["bindings"][KEY]), deepcopy(full["archives"][ARCHIVE])
    data = {"version": full["version"], "archives": {ARCHIVE: archive}, "bindings": {KEY: binding}}
    for name in (archive["path"], binding["witness"]):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    write_json(tmp_path, REGISTRY, data)
    return tmp_path, data, tmp_path / binding["witness"]


def assert_rubric(core):
    assert [s for s in core["segments"] if s["id"] == "s02"] == [
        {"id": "s02", "type": "rubric", "text": "Hic genuflectitur."}
    ], "separate Alleluia kneeling rubric"


def assert_source_fields(graph):
    uses = {row["id"]: row for row in graph["uses"]}
    for expected in FIXTURE["source_uses"]:
        assert {key: uses[expected["id"]][key] for key in expected} == expected, (
            "bounded source role and claim"
        )


def synthetic_parentheses(root):
    """A source-contract control, not another authored prayer."""
    sacred = "V. Verbum (tuum) manet."
    line = sacred + " (Hic genuflectitur)"
    raw = "[Graduale]\n" + line + "\n"
    revision = "4" * 40
    archive = {
        "path": "witnesses/raw/synthetic.txt",
        "upstream": "web/www/missa/Latin/Tempora/Test.txt",
        "revision": revision,
        "sha256": hashlib.sha256(raw.encode()).hexdigest(),
    }
    item = {"archive": "synthetic", "first": 2, "last": 2}
    binding = {
        "witness": "witnesses/proprium.test/do.txt",
        "revision": revision,
        "contract": "raw-reading-2",
        "evidence": [
            {
                **item,
                "section": "Graduale",
                "section_line": 1,
                "fragment": {
                    "start": 0,
                    "end": len(sacred),
                    "text": sacred,
                    "marker": "V",
                    "reason": "Sacred parenthesized word retained before a separate rubric suffix.",
                },
            }
        ],
        "references": [],
        "reading": [{**item, "fragment": {"start": 0, "end": len(sacred)}}],
    }
    data = {"version": 1, "archives": {"synthetic": archive}, "bindings": {"synthetic": binding}}
    for name, text in (
        (archive["path"], raw),
        (
            binding["witness"],
            f"# witness: do\n# revision: {revision}\n"
            f"# path: {archive['upstream']} [Graduale] (line 2, chars 0:{len(sacred)})\n"
            "# raw-binding: synthetic\nVerbum (tuum) manet.\n",
        ),
    ):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    write_json(root, REGISTRY, data)
    return root / binding["witness"]


@pytest.mark.parametrize("case", SOURCE_CASES)
def test_exact_alleluia_source_controls(alleluia_source, tmp_path, case):
    root, data, path = alleluia_source
    snapshot, fixture_snapshot = saved_files(root), deepcopy(FIXTURE)
    binding = data["bindings"][KEY]
    archive = root / data["archives"][ARCHIVE]["path"]
    lines = archive.read_text().splitlines()
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == data["archives"][ARCHIVE]["sha256"]
    healthy = resolve_binding(path, root)
    assert healthy is not None and healthy.source["contract"] == "raw-reading-2"
    assert len(lines[32]) == 93 and lines[32][73:] == " (Hic genuflectitur)"
    assert healthy.text == FIXTURE["alleluia_sacred_body"]
    assert [(f.line, f.start, f.end) for f in healthy.fragments] == [
        (31, 0, len(lines[30])),
        (33, 0, 73),
        (34, 0, len(lines[33])),
    ]
    assert healthy.fragments[1].raw == lines[32][:73]
    assert "Hic genuflectitur" not in healthy.text
    assert_rubric(store.core(ROOT, ALLELUIA))
    if case == "P1":
        graph, _ = bibliography.load(ROOT)
        identity = "witness." + ALLELUIA + ".do44667ff"
        row = next(w for w in graph["witnesses"] if w["id"] == identity)
        assert row["source_dependencies"] == {"uses": [], "raw_binding": KEY}
        assert row["review"]["status"] == "pending"
        subject = witness_subject(ROOT, row, graph, store.core(ROOT, ALLELUIA))
        assert subject["raw_resolution"]["binding_id"] == KEY
        assert subject["raw_resolution"]["contract"] == "raw-reading-2"
    elif case in {"C1", "C2"}:
        synthetic = tmp_path / "parentheses"
        selected = synthetic_parentheses(synthetic)
        exact = selected.read_bytes()
        assert resolve_binding(selected, synthetic).text == "Verbum (tuum) manet."
        if case == "C2":
            selected.write_bytes(exact.replace(b"(tuum) ", b""))
            with pytest.raises(
                BindingError, match=r"^transcription differs from its exact ordered raw reading$"
            ):
                resolve_binding(selected, synthetic)
            selected.write_bytes(exact)
            assert resolve_binding(selected, synthetic).text == "Verbum (tuum) manet."
        assert saved_files(root) == snapshot | {
            "parentheses/" + name: raw for name, raw in saved_files(synthetic).items()
        }
    elif case == "N9":
        core = store.core(ROOT, ALLELUIA)
        frozen = deepcopy(core)
        bad = deepcopy(core)
        next(s for s in bad["segments"] if s["id"] == "s02")["text"] = "Rubrica mutata."
        assert bad != core
        with pytest.raises(AssertionError, match=r"^separate Alleluia kneeling rubric(?:\n|$)"):
            assert_rubric(bad)
        assert_rubric(core)
        assert core == frozen and resolve_binding(path, root) == healthy
    elif case == "C3":
        graph, _ = bibliography.load(ROOT)
        frozen = deepcopy(graph)
        assert_source_fields(graph)
        for identifier, wrong_role in (
            ("use.ordinarium.praefatio-spiritus-sancti.mr1962", "official_text"),
            ("use.ordinarium.hanc-igitur-paschale.mr-vatican-table", "direct_approved_print"),
            ("use.proprium.dominica-pentecostes-evangelium.do44667ff", "official_text"),
        ):
            bad = deepcopy(graph)
            control = next(r for r in bad["uses"] if r["id"] == identifier)
            control["role"] = wrong_role
            assert bad != graph
            with pytest.raises(AssertionError, match=r"^bounded source role and claim(?:\n|$)"):
                assert_source_fields(bad)
            assert_source_fields(graph)
        assert graph == frozen
    elif case != "P1":
        expected = {
            "N1": "transcription differs from its exact ordered raw reading",
            "N2": "fragment splits a source token",
            "N3": "fragment text, marker context or boundary reason differs",
            "N4": "raw-binding marker and registered witness identity disagree",
            "N5": "reading omits or repeats source text",
            "N6": "reading reorders textual fragments",
            "N7": "archive pentecost-gospel: SHA-256 mismatch",
            "N8": "transcription differs from its exact ordered raw reading",
        }[case]
        if case == "N1":
            del binding["evidence"][1]["fragment"]
            del binding["reading"][1]["fragment"]
            path.write_text(path.read_text().replace("line 33, chars 0:73", "lines 33-33"))
        elif case == "N2":
            binding["evidence"][1]["fragment"].update(end=72, text=lines[32][:72])
            binding["reading"][1]["fragment"]["end"] = 72
            path.write_text(path.read_text().replace("chars 0:73", "chars 0:72"))
        elif case == "N3":
            binding["evidence"][1]["fragment"]["text"] += " Alienum."
        elif case == "N4":
            path.write_text(path.read_text().replace(f"# raw-binding: {KEY}\n", ""))
        elif case == "N5":
            binding["reading"].append(deepcopy(binding["reading"][0]))
        elif case == "N6":
            binding["reading"][1], binding["reading"][2] = (
                binding["reading"][2],
                binding["reading"][1],
            )
        elif case == "N7":
            archive.write_text(archive.read_text().replace("(Hic genuflectitur)", "(Hic statur)"))
        else:
            path.write_text(
                path.read_text().replace("Veni, Sancte", "(Hic genuflectitur) Veni, Sancte")
            )
        write_json(root, REGISTRY, data)
        assert saved_files(root) != snapshot
        with pytest.raises(BindingError, match="^" + re.escape(expected) + "$"):
            resolve_binding(path, root)
        restore_files(root, snapshot)
        assert resolve_binding(path, root) == healthy
    if case not in {"C1", "C2"}:
        assert saved_files(root) == snapshot
    assert fixture_snapshot == FIXTURE


@pytest.mark.parametrize("part", ("introitus", "collecta"))
def test_declared_same_edition_expansion_dependencies_are_complete(part):
    graph, _ = bibliography.load(ROOT)
    frozen, fixture_snapshot = deepcopy(graph), deepcopy(FIXTURE)
    text = PREFIX + part
    row = next(w for w in graph["witnesses"] if w["id"] == f"witness.{text}.mr1962")
    expected = FIXTURE["composite_dependencies"][part]

    def complete(candidate):
        assert candidate["source_dependencies"] == {"uses": expected, "raw_binding": None}, (
            "complete same-edition expansion inventory"
        )

    complete(row)
    core = store.core(ROOT, text)
    healthy = witness_subject(ROOT, row, graph, core)
    assert set(healthy["source_uses"]) == set(expected) | {row["use"]}
    assert healthy["raw_resolution"] is None and row["review"] == {"status": "pending"}
    for identifier in expected:
        missing = deepcopy(row)
        missing["source_dependencies"]["uses"].remove(identifier)
        assert missing != row
        with pytest.raises(
            AssertionError, match=r"^complete same-edition expansion inventory(?:\n|$)"
        ):
            complete(missing)
        foreign = deepcopy(graph)
        use = next(u for u in foreign["uses"] if u["id"] == identifier)
        use.update(
            edition="edition.divinum-officium-missa.44667ff",
            digital_item="item.divinum-officium-missa.44667ff.github",
        )
        assert foreign != graph
        with pytest.raises(SubjectError, match=r"^supplemental source belongs to another edition$"):
            witness_subject(ROOT, row, foreign, core)
        assert witness_subject(ROOT, row, graph, core) == healthy
    assert graph == frozen and fixture_snapshot == FIXTURE


def test_source_identity_repairs_do_not_promote_pending_evidence():
    graph, _ = bibliography.load(ROOT)
    frozen, fixture_snapshot = deepcopy(graph), deepcopy(FIXTURE)
    texts = set(FIXTURE["texts"])
    witnesses = [r for r in graph["witnesses"] if r["text"] in texts]
    collations = [r for r in graph["collations"] if r["text"] in texts]

    assert len(witnesses) == 27 and len(collations) == 13
    assert sorted(r["id"] for r in witnesses) == FIXTURE["witnesses"]
    assert sorted(r["id"] for r in collations) == FIXTURE["collations"]

    def bounded_reviews(rows):
        for row in rows:
            expected = ADOPTED_SOURCE_REVIEWS.get(row["id"])
            if expected is not None:
                expected = expected_review(row["id"], expected)
            if expected is None:
                assert row["review"] == {"status": "pending"}, "pending evidence is not approval"
                continue
            assert row["review"] == {"status": "reviewed", "sha256": expected}, (
                "exact adopted source review"
            )
            doc = store.core(ROOT, row["text"])
            if row["id"].startswith("witness."):
                subject = witness_subject(ROOT, row, graph, doc)
            else:
                subjects = {
                    w["id"]: witness_subject(ROOT, w, graph, doc)
                    for w in graph["witnesses"]
                    if w["id"] in row["witnesses"]
                }
                subject = collation_subject(ROOT, row, doc, subjects)
            assert digest(subject) == expected, "adopted source subject changed"

    assert set(ADOPTED_SOURCE_REVIEWS) <= {r["id"] for r in witnesses + collations}
    bounded_reviews(witnesses + collations)
    bad = deepcopy(witnesses)
    pending_row = next(r for r in bad if r["id"] not in ADOPTED_SOURCE_REVIEWS)
    pending_review = deepcopy(pending_row["review"])
    pending_row["review"] = {"status": "reviewed", "sha256": "0" * 64}
    assert bad != witnesses
    with pytest.raises(AssertionError, match=r"^pending evidence is not approval(?:\n|$)"):
        bounded_reviews(bad)
    pending_row["review"] = pending_review
    assert bad == witnesses
    bounded_reviews(bad)
    stale = deepcopy(witnesses)
    reviewed_row = next(r for r in stale if r["id"] in ADOPTED_SOURCE_REVIEWS)
    reviewed_review = deepcopy(reviewed_row["review"])
    reviewed_row["review"]["sha256"] = "0" * 64
    assert stale != witnesses
    with pytest.raises(AssertionError, match=r"^exact adopted source review(?:\n|$)"):
        bounded_reviews(stale)
    reviewed_row["review"] = reviewed_review
    assert stale == witnesses
    bounded_reviews(stale)
    bounded_reviews(witnesses + collations)
    evidence = {r["id"]: r for r in bibliography.public_text_evidence(graph)["texts"]}
    assert texts <= evidence.keys()
    for text in texts:
        entry = evidence[text]
        expected_witnesses = [
            {
                key: row[key]
                for key in ("id", "text", "use", "role", "coverage", "independence_basis")
            }
            for row in sorted(witnesses, key=lambda row: row["id"])
            if row["text"] == text and row["id"] in ADOPTED_SOURCE_REVIEWS
        ]
        assert entry["witnesses"] == expected_witnesses
        expected_collations = [
            row for row in collations if row["text"] == text and row["id"] in ADOPTED_SOURCE_REVIEWS
        ]
        if expected_collations:
            assert len(expected_collations) == 1
            assert entry["collation"] == {
                key: expected_collations[0][key]
                for key in ("id", "text", "recension", "witnesses", "apparatus")
            }
        else:
            assert "collation" not in entry
    scoped_uses = [u for u in graph["uses"] if u["address"].get("text") in texts]
    assert not any(
        "connelly" in str(u[field]).lower()
        for u in scoped_uses
        for field in ("id", "edition", "digital_item")
    )
    assert graph == frozen and fixture_snapshot == FIXTURE

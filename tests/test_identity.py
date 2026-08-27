"""The identity gate: each rule watched failing before it landed."""

import glob
import json
import subprocess
from pathlib import Path

from checks.identity import check, check_against_history

CORPUS = Path(__file__).resolve().parent.parent


def doc(words, next_=10, retired=None, segments=("s01",), seg_next=None, seg_retired=None):
    if seg_next is None:
        numeric = [int(s[1:]) for s in segments if s[1:].isdigit()]
        seg_next = (max(numeric) + 1) if numeric else 1
    segment_mint = {"next": seg_next, **({"retired": seg_retired} if seg_retired else {})}
    return {
        "id": "test.text",
        "ids": {
            "next": next_,
            **({"retired": retired} if retired else {}),
            "segments": segment_mint,
        },
        "segments": [
            {"id": segments[0], "type": "verse", "words": [{"id": w, "form": f} for w, f in words]}
        ]
        + [{"id": s, "type": "verse", "words": []} for s in segments[1:]],
    }


def test_the_corpus_as_it_stands_is_clean():
    errors = []
    for f in glob.glob(str(CORPUS / "texts/*/*.json")):
        errors += check(json.loads(Path(f).read_text(encoding="utf-8")))
    assert errors == []


def test_a_missing_mint_fails():
    d = doc([("w001", "a")])
    del d["ids"]
    assert check(d) and "mint must be recorded" in check(d)[0]


def test_an_id_at_or_past_the_mint_fails():
    # w010 with next=10 means the counter never gave it out
    errors = check(doc([("w001", "a"), ("w010", "b")], next_=10))
    assert len(errors) == 1 and "past ids.next" in errors[0]


def test_a_duplicate_id_fails():
    errors = check(doc([("w001", "a"), ("w001", "b")]))
    assert any("used twice" in e for e in errors)


def test_word_ids_grow_beyond_three_digits_without_renumbering():
    assert check(doc([("w1000", "a")], next_=1001)) == []


def test_segment_ids_grow_beyond_two_digits():
    assert check(doc([("w001", "a")], segments=("s1000",))) == []


def test_semantic_segment_aliases_are_refused():
    errors = check(doc([("w001", "a")], segments=("ave1",)))
    assert any("segment id is s + at least two digits" in error for error in errors)


def test_duplicate_segment_ids_are_refused():
    errors = check(doc([("w001", "a")], segments=("s01", "s01")))
    assert any("segment id used twice" in error for error in errors)


def test_a_word_that_is_also_a_tombstone_fails():
    errors = check(doc([("w001", "a")], retired={"w001": "s01"}))
    assert any("both a live word and a tombstone" in e for e in errors)


def test_a_tombstone_pointing_nowhere_fails():
    errors = check(doc([("w001", "a")], retired={"w002": "s99"}))
    assert any("does not have" in e for e in errors)


def test_a_tombstone_pointing_at_a_real_segment_passes():
    assert check(doc([("w001", "a")], retired={"w002": "s01"})) == []


def test_history_catches_a_word_removed_without_a_tombstone(tmp_path, monkeypatch):
    (tmp_path / "texts" / "x").mkdir(parents=True)
    p = tmp_path / "texts" / "x" / "t.json"
    p.write_text(json.dumps(doc([("w001", "a"), ("w002", "b")])))
    for args in (["init", "-q"], ["add", "-A"]):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-qm",
            "base",
        ],
        check=True,
        capture_output=True,
    )
    p.write_text(json.dumps(doc([("w001", "a")])))  # w002 simply gone
    errors = check_against_history(tmp_path)
    assert len(errors) == 1 and "without a tombstone" in errors[0]
    p.write_text(json.dumps(doc([("w001", "a")], retired={"w002": "s01"})))
    assert check_against_history(tmp_path) == []


def test_history_catches_a_rewound_mint(tmp_path):
    (tmp_path / "texts" / "x").mkdir(parents=True)
    p = tmp_path / "texts" / "x" / "t.json"
    p.write_text(json.dumps(doc([("w001", "a")], next_=40)))
    for args in (["init", "-q"], ["add", "-A"]):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-qm",
            "base",
        ],
        check=True,
        capture_output=True,
    )
    p.write_text(json.dumps(doc([("w001", "a")], next_=20)))
    errors = check_against_history(tmp_path)
    assert len(errors) == 1 and "went backwards" in errors[0]


def _repo(tmp_path, doc_obj):
    (tmp_path / "texts" / "x").mkdir(parents=True, exist_ok=True)
    p = tmp_path / "texts" / "x" / "t.json"
    p.write_text(json.dumps(doc_obj))
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-qm",
            "base",
        ],
        check=True,
        capture_output=True,
    )
    return p


def test_history_catches_a_renumbering_that_leaves_every_id_present(tmp_path):
    # The dangerous shape: shift ids up from the middle. The words are
    # untouched, so only one id vanishes and the rest still resolve — to the
    # wrong word.
    p = _repo(tmp_path, doc([("w001", "a"), ("w002", "b"), ("w003", "c")], next_=10))
    p.write_text(json.dumps(doc([("w001", "a"), ("w003", "b"), ("w004", "c")], next_=10)))
    errors = check_against_history(tmp_path)
    assert any("name a different word" in e for e in errors), errors


def test_a_typo_fix_is_not_a_renumbering(tmp_path):
    # One form changes, ids untouched. That is the correction this corpus
    # exists to make, and it must not trip the gate.
    p = _repo(tmp_path, doc([("w001", "Excita"), ("w002", "b")], next_=10))
    p.write_text(json.dumps(doc([("w001", "Éxcita"), ("w002", "b")], next_=10)))
    assert check_against_history(tmp_path) == []


def test_an_unresolvable_base_fails_rather_than_reading_every_file_as_new(tmp_path):
    # Under an unknown ref every file looks new and the whole check passes
    # vacuously — the silence this check exists to end, from the other side.
    # It ran exactly so in CI: the workflow named no base, the default was
    # HEAD, and the tree in CI IS HEAD, so nothing was ever compared.
    _repo(tmp_path, doc([("w001", "a")], next_=10))
    errors = check_against_history(tmp_path, "no-such-ref")
    assert errors and "does not resolve" in errors[0], errors


def test_a_missing_segment_mint_fails():
    d = doc([("w001", "a")])
    del d["ids"]["segments"]
    assert any("segment mint must be recorded" in e for e in check(d))


def test_a_segment_at_or_past_its_mint_fails():
    errors = check(doc([("w001", "a")], segments=("s01", "s05"), seg_next=5))
    assert any("past ids.segments.next" in e for e in errors)


def test_a_segment_that_is_both_live_and_retired_fails():
    errors = check(doc([("w001", "a")], segments=("s01", "s02"), seg_retired={"s02": "s01"}))
    assert any("both a live segment and a retired one" in e for e in errors)


def test_a_retired_segment_resolving_nowhere_fails():
    errors = check(doc([("w001", "a")], seg_next=9, seg_retired={"s02": "s07"}))
    assert any("does not have" in e for e in errors)


def test_a_retired_segment_resolving_to_a_live_one_passes():
    assert check(doc([("w001", "a")], seg_next=9, seg_retired={"s02": "s01"})) == []


def test_history_catches_a_segment_removed_without_a_record(tmp_path):
    p = _repo(tmp_path, doc([("w001", "a")], segments=("s01", "s02")))
    p.write_text(json.dumps(doc([("w001", "a")], segments=("s01",), seg_next=3)))
    errors = check_against_history(tmp_path)
    assert any("without a retirement record" in e for e in errors), errors
    p.write_text(
        json.dumps(doc([("w001", "a")], segments=("s01",), seg_next=3, seg_retired={"s02": "s01"}))
    )
    assert check_against_history(tmp_path) == []


def test_history_catches_a_dropped_retirement_record(tmp_path):
    p = _repo(tmp_path, doc([("w001", "a")], seg_next=3, seg_retired={"s02": "s01"}))
    p.write_text(json.dumps(doc([("w001", "a")], seg_next=3)))
    errors = check_against_history(tmp_path)
    assert any("retirement record has been dropped" in e for e in errors), errors


def test_history_catches_a_retired_segment_id_reused(tmp_path):
    p = _repo(tmp_path, doc([("w001", "a")], seg_next=3, seg_retired={"s02": "s01"}))
    p.write_text(
        json.dumps(
            doc([("w001", "a")], segments=("s01", "s02"), seg_next=3, seg_retired={"s02": "s01"})
        )
    )
    errors = check_against_history(tmp_path)
    assert any("come back to life" in e for e in errors), errors


def test_history_catches_a_segment_readdressing(tmp_path):
    # Two segments swap their ids; every word survives, so nothing is
    # missing, yet every link to either segment now shows the other's verse.
    def swapped(first, second):
        return {
            "id": "test.text",
            "ids": {"next": 10, "segments": {"next": 3}},
            "segments": [
                {"id": "s01", "type": "verse", "words": [{"id": w, "form": w} for w in first]},
                {"id": "s02", "type": "verse", "words": [{"id": w, "form": w} for w in second]},
            ],
        }

    p = _repo(tmp_path, swapped(["w001", "w002"], ["w003", "w004"]))
    p.write_text(json.dumps(swapped(["w003", "w004"], ["w001", "w002"])))
    errors = check_against_history(tmp_path)
    assert any("readdressed" in e for e in errors), errors


def test_history_allows_a_genuine_split(tmp_path):
    # s01 keeps its opening words and hands the rest to a freshly minted
    # segment: members are shared, so this is resegmentation, not a rename.
    base = {
        "id": "test.text",
        "ids": {"next": 10, "segments": {"next": 2}},
        "segments": [
            {
                "id": "s01",
                "type": "verse",
                "words": [{"id": w, "form": w} for w in ("w001", "w002", "w003")],
            }
        ],
    }
    split = {
        "id": "test.text",
        "ids": {"next": 10, "segments": {"next": 3}},
        "segments": [
            {"id": "s01", "type": "verse", "words": [{"id": w, "form": w} for w in ("w001",)]},
            {
                "id": "s02",
                "type": "verse",
                "words": [{"id": w, "form": w} for w in ("w002", "w003")],
            },
        ],
    }
    p = _repo(tmp_path, base)
    p.write_text(json.dumps(split))
    assert check_against_history(tmp_path) == []


def test_history_catches_a_rewound_segment_mint(tmp_path):
    p = _repo(tmp_path, doc([("w001", "a")], seg_next=9))
    p.write_text(json.dumps(doc([("w001", "a")], seg_next=4)))
    errors = check_against_history(tmp_path)
    assert any("segments.next went backwards" in e for e in errors), errors


def test_registry_history_is_an_exact_prefix(tmp_path):
    from checks.identity import check_registry_history, is_exact_prefix

    assert is_exact_prefix([1, 2], [1, 2, 3])
    assert is_exact_prefix([], [1])
    assert not is_exact_prefix([1, 2], [2, 1, 3]), "a reorder is a different address space"
    assert not is_exact_prefix([1, 2], [1]), "a shrink retires addresses"

    reg = tmp_path / "build_reader" / "registry"
    reg.mkdir(parents=True)
    p = reg / "texts.json"
    p.write_text(json.dumps(["a.one", "a.two"]))
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-qm",
            "base",
        ],
        check=True,
        capture_output=True,
    )
    p.write_text(json.dumps(["a.one", "a.two", "a.three"]))
    assert check_registry_history(tmp_path) == []
    p.write_text(json.dumps(["a.two", "a.one", "a.three"]))
    errors = check_registry_history(tmp_path)
    assert any("not an exact prefix" in e for e in errors), errors

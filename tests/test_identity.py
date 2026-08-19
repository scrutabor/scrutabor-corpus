"""The identity gate: each rule watched failing before it landed."""

import glob
import json
import subprocess
from pathlib import Path

from checks.identity import check, check_against_history

CORPUS = Path(__file__).resolve().parent.parent


def doc(words, next_=10, retired=None, segments=("s01",)):
    return {
        "id": "test.text",
        "ids": {"next": next_, **({"retired": retired} if retired else {})},
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

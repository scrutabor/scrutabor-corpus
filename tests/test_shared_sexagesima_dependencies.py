"""Shared chants and prayer keep coherent captions and exact consumer identities."""

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OFF = "proprium.dominica-vi-post-pentecosten-offertorium"
PC = "proprium.dominica-i-post-epiphaniam-postcommunio"
GROUPS = [
    ("pl", OFF, 23, 24, 24, "ocalasz"),
    ("pl", OFF, 26, 27, 27, "Tobie"),
    ("en", OFF, 1, 3, 1, "Make my steps steadfast"),
    ("en", OFF, 5, 6, 5, "Your paths"),
    ("en", OFF, 8, 11, 9, "my footsteps may not be moved"),
    ("en", OFF, 13, 14, 13, "Your ear"),
    ("en", OFF, 17, 18, 17, "my words"),
    ("en", OFF, 19, 21, 19, "Show Your wondrous mercies"),
    ("en", OFF, 23, 24, 24, "save"),
    ("pl", PC, 8, 10, 9, "pokrzepiasz swoimi sakramentami"),
    ("pl", PC, 11, 17, 17, "łaskawie pozwolił także służyć Tobie miłym życiem"),
    ("en", PC, 2, 3, 3, "we beseech You"),
    (
        "en",
        PC,
        7,
        17,
        17,
        "You may graciously allow those whom You refresh with Your sacraments "
        "to serve You also by pleasing conduct",
    ),
]


def load(tid, lang=None):
    cat, slug = tid.split(".", 1)
    rel = Path("texts") / cat / (slug + ".json")
    if lang:
        rel = Path("languages") / lang / rel
    return json.loads((ROOT / rel).read_text())


@pytest.mark.parametrize("lang,tid,start,end,anchor,gloss", GROUPS)
def test_complete_local_construction(lang, tid, start, end, anchor, gloss):
    d = load(tid, lang)
    ids = [f"w{i:03}" for i in range(start, end + 1)]
    matches = [g for g in d["segments"]["s01"].get("alignments", []) if g["words"] == ids]
    assert len(matches) == 1
    g = matches[0]
    assert g["anchor"] == f"w{anchor:03}"
    assert g["gloss"] == gloss
    assert all(not d["words"][wid].get("gloss") for wid in ids)
    words = {w["id"]: w for s in load(tid)["segments"] for w in s["words"]}
    assert all(words[wid]["lemma"] for wid in ids)


@pytest.mark.parametrize(
    "lang,wid,gloss",
    [
        ("pl", "w020", "dzieła miłosierdzia"),
        ("en", "w022", "You who"),
        ("en", "w025", "those who hope"),
    ],
)
def test_offertory_direct_caption(lang, wid, gloss):
    assert load(OFF, lang)["words"][wid]["gloss"] == gloss


def test_postcommunion_recipient_gender_pending_not_new_acceptance():
    d = load(PC)
    q = next(w for w in d["segments"][0]["words"] if w["id"] == "w007")
    assert q["lemma"] == "qui"
    assert q["morph"] == {"pos": "pron", "case": "acc", "number": "pl", "gender": "m"}
    assert d["editorial"]["words"]["w007"]["analysis"] == {
        "confidence": "high",
        "sources": ["editorial", "whitakers", "collatinus"],
        "review": "pending",
    }


def actual_consumers(tid):
    return sorted(
        (d["id"], c["key"], c["relation"])
        for p in (ROOT / "formularies").rglob("*.json")
        for d in [json.loads(p.read_text())]
        for c in d.get("components", [])
        if c.get("text") == tid
    )


def test_every_direct_consumer():
    assert actual_consumers(OFF) == [
        ("dominica-in-sexagesima", "offertorium", "reference"),
        ("dominica-vi-post-pentecosten", "offertorium", "proper"),
    ]
    assert actual_consumers(PC) == [
        ("dominica-i-post-epiphaniam", "postcommunio", "proper"),
        ("dominica-ii-in-quadragesima", "postcommunio", "reference"),
        ("dominica-in-sexagesima", "postcommunio", "reference"),
    ]


def test_reused_offertory_accent_is_declared_not_canonical_repair():
    words = load(OFF)["segments"][0]["words"]
    assert words[1]["id"] == "w002" and words[1]["form"] == "gressus"
    wd = ROOT / "witnesses" / OFF
    assert "\nPérfice gressus " in (wd / "mr.txt").read_text()
    assert "\nPérfice gréssus " in (wd / "mr-sexagesima.txt").read_text()
    a = json.loads((wd / "apparatus.json").read_text())
    row = next(r for r in a["adjudicated"] if r["at"] == "w002")
    assert row["ours"] == "gressus" and row["witnesses"] == {"mr-sexagesima": "gréssus"}
    assert row["class"] == "orthography"


@pytest.mark.parametrize("name", ["mr-sexagesima", "mr-lent-ii"])
def test_reused_postcommunion_has_only_proper_body(name):
    wd = ROOT / "witnesses" / PC
    raw = (wd / (name + ".txt")).read_text()
    body = " ".join(line for line in raw.splitlines() if not line.startswith("#"))
    assert len(body.split()) == 17 and " ut, " in body
    assert "# covers: w001-w017\n" in raw
    assert body.endswith("deservíre concédas.") and "Per Dóminum" not in body
    g = json.loads((ROOT / "bibliography/graph.json").read_text())
    w = next(r for r in g["witnesses"] if r["id"] == f"witness.{PC}.{name}")
    assert w["coverage"] == {
        "kind": "words",
        "words": [f"w{i:03}" for i in range(1, 18)],
    }
    assert w["review"] == {"status": "pending"}
    assert (
        "not the expanded ending or response"
        in next(r for r in g["uses"] if r["id"] == w["use"])["claim"]
    )


def test_postcommunion_digital_use_names_the_exact_proper_archive():
    registry = json.loads((ROOT / "witnesses/raw/bindings.json").read_text())
    archive = registry["archives"]["do-tempora-epi1-0a"]
    actual = hashlib.sha256((ROOT / archive["path"]).read_bytes()).hexdigest()
    assert actual == archive["sha256"]
    graph = json.loads((ROOT / "bibliography/graph.json").read_text())
    use = next(r for r in graph["uses"] if r["id"] == f"use.{PC}.do44667ff")
    assert use["evidence_sha256"] == actual
    witness = next(r for r in graph["witnesses"] if r["use"] == use["id"])
    assert witness["review"] == {"status": "pending"}

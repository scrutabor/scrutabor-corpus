"""Complete heading evidence, literal page readings and explicit dependencies."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from build_reader.bibliography import public_text_evidence
from build_reader.bibliography_bindings import (
    digest,
    selected_text,
    transcript_digest,
    validate_bindings,
)
from checks.apparatus import derived_summary

ROOT = Path(__file__).resolve().parents[1]
ORACLE = json.loads((ROOT / "tests/fixtures/reading-announcement-source-oracle.json").read_text())
TEXTS = set(ORACLE["headings"])
NAMES = {"mr": "mr1962", "do": "do44667ff", "vatican1962": "vatican1962"}


def snapshot():
    value = json.loads((ROOT / "bibliography/graph.json").read_text())
    value["witnesses"] = [w for w in value["witnesses"] if w["text"] in TEXTS]
    value["collations"] = [c for c in value["collations"] if c["text"] in TEXTS]
    return {
        "graph": value,
        "documents": {
            text: json.loads((ROOT / "texts" / (text.replace(".", "/", 1) + ".json")).read_text())
            for text in TEXTS
        },
        "transcripts": {
            (text, name): (ROOT / "witnesses" / text / (name + ".txt")).read_text()
            for text in TEXTS
            for name in NAMES
        },
        "apparatus": {
            text: json.loads((ROOT / "witnesses" / text / "apparatus.json").read_text())
            for text in TEXTS
        },
    }


def source_errors(state):
    """A separately frozen page oracle prevents self-consistent source drift."""
    errors = []
    value = state["graph"]
    scoped_uses = [u for u in value["uses"] if u["address"].get("text") in TEXTS]
    expected_uses = {f"use.{text}.{suffix}" for text in TEXTS for suffix in NAMES.values()} | set(
        ORACLE["context_uses"]
    )
    if len(scoped_uses) != 86 or {u["id"] for u in scoped_uses} != expected_uses:
        errors.append("source-use inventory differs: expected 86 exact uses")
    uses = {u["id"]: u for u in scoped_uses}
    if set(state["documents"]) != TEXTS or set(state["apparatus"]) != TEXTS:
        errors.append("complete 26-heading document/apparatus inventory differs")
    total_entries = 0
    for text, page in ORACLE["headings"].items():
        doc = state["documents"].get(text)
        if doc is None:
            errors.append(f"{text}: missing selected document")
            continue
        words = [w for s in doc["segments"] for w in s.get("words", [])]
        selected_words = [{k: w[k] for k in ("id", "form", "pre", "post") if k in w} for w in words]
        if (
            selected_words != page["selected_words"]
            or digest(selected_text(doc)) != page["selected_sha256"]
        ):
            errors.append(f"{text}: selected words, IDs or ritual subject changed")
        bound = [w for w in value["witnesses"] if w["text"] == text]
        expected_ids = {f"witness.{text}.{suffix}" for suffix in NAMES.values()}
        if len(bound) != 3 or {w["id"] for w in bound} != expected_ids:
            errors.append(f"{text}: expected exactly three named witnesses")
        for name, suffix in NAMES.items():
            matching = [w for w in bound if w["id"] == f"witness.{text}.{suffix}"]
            if len(matching) != 1:
                continue
            witness = matching[0]
            expected = page["transcripts"][name]
            if (
                witness.get("transcription") != name
                or witness.get("use") != f"use.{text}.{suffix}"
                or witness.get("coverage") != {"kind": "full"}
                or witness.get("role") != expected["role"]
                or witness.get("source_dependencies") != expected["source_dependencies"]
            ):
                errors.append(
                    f"{text}: {name} identity, coverage, role or source inventory differs"
                )
            transcript = state["transcripts"].get((text, name))
            if transcript is None:
                errors.append(f"{text}: missing {name} transcript")
                continue
            body = "\n".join(
                line for line in transcript.splitlines() if line and not line.startswith("#")
            )
            if body != expected["body"]:
                errors.append(f"{text}: {name} literal body differs from independent source oracle")
            if name == "vatican1962" and body != page["vatican_body"]:
                errors.append(
                    f"{text}: literal body differs from separately recorded visual reading"
                )
            actual_hash = transcript_digest(transcript)
            if (
                actual_hash != expected["sha256"]
                or witness.get("transcription_sha256") != actual_hash
            ):
                errors.append(f"{text}: {name} full transcript binding differs")
        use = uses.get(f"use.{text}.vatican1962")
        if use is None or any(use.get(k) != v for k, v in page["vatican_use"].items()):
            errors.append(f"{text}: Vatican page/reference/source identity differs")
        if page["vatican_use"]["evidence_sha256"] != ORACLE["pdf_sha256"]:
            errors.append(f"{text}: Vatican original-object oracle is inconsistent")
        if page["vatican_use"]["locator"]["scan"] != f"PDF page {page['vatican_pdf_page']}":
            errors.append(f"{text}: page oracle is inconsistent")
        if page["reference"] not in page["vatican_use"]["locator"]["section"]:
            errors.append(f"{text}: attribution oracle is inconsistent")
        app = state["apparatus"].get(text)
        if app is None:
            errors.append(f"{text}: missing apparatus")
            continue
        entries = app["adjudicated"]
        total_entries += len(entries)
        punctuation = [e for e in entries if e["class"] == "punctuation"]
        last = words[-1]
        expected_punctuation = {
            "at": last["id"],
            "ours": last["form"],
            "witnesses": {"vatican1962": last["form"] + "."},
        }
        if (
            len(punctuation) != 1
            or any(punctuation[0].get(k) != v for k, v in expected_punctuation.items())
            or "closing full stop" not in punctuation[0].get("ruling", "")
        ):
            errors.append(f"{text}: non-vacuous closing-period ruling differs")
        if app.get("summary") != derived_summary(app):
            errors.append(f"{text}: apparatus summary is not derived from its entries")
        collations = [c for c in value["collations"] if c["text"] == text]
        if len(collations) != 1:
            errors.append(f"{text}: expected exactly one collation")
            continue
        collation = collations[0]
        if (
            collation.get("id") != f"collation.{text}.mr1962-do44667ff"
            or collation.get("witnesses") != sorted(expected_ids)
            or collation.get("selected_text_sha256") != digest(selected_text(doc))
            or collation.get("apparatus_sha256") != digest(app)
            or collation.get("apparatus") != derived_summary(app)
        ):
            errors.append(f"{text}: collation identity, dependencies or current bindings differ")
    if total_entries != 35:
        errors.append("expected exactly 35 classified apparatus entries")
    for identifier, expected in ORACLE["context_uses"].items():
        use = uses.get(identifier)
        if use is None or any(use.get(k) != v for k, v in expected.items()):
            errors.append(f"{identifier}: exact Wisdom context differs")
    actuum = state["apparatus"].get("ordinarium.lectio-actuum-apostolorum", {})
    accents = [e for e in actuum.get("adjudicated", []) if e["class"] == "capital-accent"]
    if (
        len(accents) != 1
        or accents[0].get("ours") != "Áctuum"
        or accents[0].get("witnesses") != {"mr": "Actuum", "do": "Actuum", "vatican1962": "Actuum"}
    ):
        errors.append("Actuum: three literal source readings must support the house accent")
    initium = state["apparatus"].get("ordinarium.initium-sancti-evangelii-secundum-matthaeum", {})
    accent_rules = [
        e.get("ruling", "") for e in initium.get("adjudicated", []) if e["class"] != "punctuation"
    ]
    if not any("four syllables" in rule and "three syllables" not in rule for rule in accent_rules):
        errors.append("Initium: four-syllable description missing")
    return errors


def test_complete_three_witness_heading_sources():
    formulas = json.loads((ROOT / "tests/fixtures/reading-announcement-formulas.json").read_text())[
        "formulas"
    ]
    assert len(TEXTS) == 26
    assert len(formulas) == 26 and {f["text"] for f in formulas} == TEXTS
    assert sum(f["words"] for f in formulas) == 137
    assert sum(len(p["selected_words"]) for p in ORACLE["headings"].values()) == 137
    assert len(ORACLE["context_uses"]) == 8
    assert [(c["physical_page"], c["reference"], c["book"]) for c in ORACLE["wisdom_contexts"]] == [
        (106, "Eccli. 15, 1-6", "Ecclesiasticus"),
        (605, "Sap. 5, 1-5", "Wisdom"),
        (656, "Cant. 2, 8-14", "Song of Songs"),
        (731, "Prov. 8, 22-35", "Proverbs"),
    ]
    assert all(p["vatican_body"].endswith(".") for p in ORACLE["headings"].values())
    for context in ORACLE["wisdom_contexts"]:
        use = ORACLE["context_uses"][
            f"use.ordinarium.lectio-libri-sapientiae.w003.vatican1962-p{context['printed']}"
        ]
        assert use["locator"]["scan"] == f"PDF page {context['physical_page']}"
        assert context["reference"] in use["claim"] and context["book"] in use["claim"]
        assert context["heading"] in use["claim"]
    state = snapshot()
    assert len(state["graph"]["witnesses"]) == 78
    assert len(state["graph"]["collations"]) == 26
    assert len(state["transcripts"]) == 78
    assert source_errors(state) == []
    assert validate_bindings(ROOT, state["graph"]) == []


MUTATIONS = [
    "missing-witness",
    "missing-use",
    "missing-transcript",
    "missing-heading",
    "missing-collation",
    "duplicate-use",
    "wrong-use",
    "neighbor-page",
    "zero-based-page",
    "missing-period-with-refreshed-hash",
    "wrong-capital-actuum",
    "inferred-libri",
    "cross-as-word",
    "strip-digital-cross",
    "missing-punctuation-rule",
    "wrong-punctuation-quote",
    "wrong-punctuation-class",
    "wrong-entry-count",
    "wrong-apparatus-digest",
    "omitted-collation-witness",
    "duplicate-witness",
    "partial-coverage",
    "missing-source-inventory",
    "wrong-raw-binding",
    "wrong-digital-role",
    "wrong-selected-word",
    "wrong-selected-id",
    "stale-selected-hash",
    "conflated-wisdom-context",
    "actuum-apparatus-support",
    "three-syllable-initium",
]


@pytest.mark.parametrize("mutation", MUTATIONS)
def test_source_drift_is_rejected_even_when_local_hashes_are_refreshed(mutation):
    state = copy.deepcopy(snapshot())
    value = state["graph"]
    text = "ordinarium.lectio-actuum-apostolorum"
    witness = next(w for w in value["witnesses"] if w["id"] == f"witness.{text}.vatican1962")
    use = next(u for u in value["uses"] if u["id"] == witness["use"])
    collation = next(c for c in value["collations"] if c["text"] == text)
    app = state["apparatus"][text]
    punctuation = next(e for e in app["adjudicated"] if e["class"] == "punctuation")
    if mutation == "missing-witness":
        value["witnesses"].remove(witness)
    elif mutation == "missing-use":
        value["uses"].remove(use)
    elif mutation == "missing-transcript":
        del state["transcripts"][(text, "vatican1962")]
    elif mutation == "missing-heading":
        del state["documents"][text]
    elif mutation == "missing-collation":
        value["collations"].remove(collation)
    elif mutation == "duplicate-use":
        value["uses"].append(copy.deepcopy(use))
    elif mutation == "wrong-use":
        witness["use"] = "use.ordinarium.lectio-isaiae-prophetae.vatican1962"
    elif mutation in {"neighbor-page", "zero-based-page"}:
        page = ORACLE["headings"][text]["vatican_pdf_page"]
        use["locator"]["scan"] = f"PDF page {page + (1 if mutation == 'neighbor-page' else -1)}"
    elif mutation in {
        "missing-period-with-refreshed-hash",
        "wrong-capital-actuum",
        "inferred-libri",
        "cross-as-word",
    }:
        original = state["transcripts"][(text, "vatican1962")]
        if mutation == "missing-period-with-refreshed-hash":
            changed = original.replace("Apostolórum.\n", "Apostolórum\n")
        elif mutation == "wrong-capital-actuum":
            changed = original.replace("Léctio Actuum", "Léctio Áctuum")
        elif mutation == "inferred-libri":
            changed = original.replace("Léctio Actuum", "Léctio libri Actuum")
        else:
            changed = original.replace("Léctio Actuum", "Léctio + Actuum")
        assert changed != original
        state["transcripts"][(text, "vatican1962")] = changed
        witness["transcription_sha256"] = transcript_digest(changed)
    elif mutation == "strip-digital-cross":
        other = "ordinarium.sequentia-sancti-evangelii-secundum-matthaeum"
        original = state["transcripts"][(other, "do")]
        changed = original.replace("Sequéntia ++ sancti", "Sequéntia sancti")
        assert changed != original
        state["transcripts"][(other, "do")] = changed
        next(w for w in value["witnesses"] if w["id"] == f"witness.{other}.do44667ff")[
            "transcription_sha256"
        ] = transcript_digest(changed)
    elif mutation == "missing-punctuation-rule":
        app["adjudicated"].remove(punctuation)
    elif mutation == "wrong-punctuation-quote":
        punctuation["witnesses"]["vatican1962"] = "Apostolórum"
    elif mutation == "wrong-punctuation-class":
        punctuation["class"] = "capitalization"
    elif mutation == "wrong-entry-count":
        app["summary"]["entries"] += 1
    elif mutation == "wrong-apparatus-digest":
        collation["apparatus_sha256"] = "0" * 64
    elif mutation == "omitted-collation-witness":
        collation["witnesses"].remove(witness["id"])
    elif mutation == "duplicate-witness":
        value["witnesses"].append(copy.deepcopy(witness))
    elif mutation == "partial-coverage":
        witness["coverage"] = {"kind": "words", "words": ["w001"]}
    elif mutation == "missing-source-inventory":
        del witness["source_dependencies"]
    elif mutation == "wrong-raw-binding":
        next(w for w in value["witnesses"] if w["id"] == f"witness.{text}.do44667ff")[
            "source_dependencies"
        ]["raw_binding"] = "unrelated-heading"
    elif mutation == "wrong-digital-role":
        next(w for w in value["witnesses"] if w["id"] == f"witness.{text}.do44667ff")["role"] = (
            "controlling"
        )
    elif mutation in {"wrong-selected-word", "wrong-selected-id"}:
        word = state["documents"][text]["segments"][0]["words"][0]
        word["form" if mutation == "wrong-selected-word" else "id"] = (
            "Other" if mutation == "wrong-selected-word" else "w999"
        )
        collation["selected_text_sha256"] = digest(selected_text(state["documents"][text]))
    elif mutation == "stale-selected-hash":
        collation["selected_text_sha256"] = "0" * 64
    elif mutation == "conflated-wisdom-context":
        identifier = "use.ordinarium.lectio-libri-sapientiae.w003.vatican1962-p575"
        other = next(u for u in value["uses"] if u["id"] == identifier)
        other["locator"]["scan"] = "PDF page 605"
        other["claim"] = other["claim"].replace("Cant. 2, 8-14", "Sap. 5, 1-5")
    elif mutation == "actuum-apparatus-support":
        next(e for e in app["adjudicated"] if e["class"] == "capital-accent")["witnesses"][
            "vatican1962"
        ] = "Áctuum"
    else:
        other_text = "ordinarium.initium-sancti-evangelii-secundum-matthaeum"
        other = state["apparatus"][other_text]
        entry = next(e for e in other["adjudicated"] if "four syllables" in e["ruling"])
        entry["ruling"] = entry["ruling"].replace("four syllables", "three syllables")
        next(c for c in value["collations"] if c["text"] == other_text)["apparatus_sha256"] = (
            digest(other)
        )
    # A self-consistent apparatus hash/summary cannot authenticate the reading.
    if mutation in {
        "missing-punctuation-rule",
        "wrong-punctuation-quote",
        "wrong-punctuation-class",
        "actuum-apparatus-support",
    }:
        app["summary"] = derived_summary(app)
        collation["apparatus"] = derived_summary(app)
        collation["apparatus_sha256"] = digest(app)
    assert source_errors(state), mutation


def test_pending_evidence_stays_withheld_but_uses_remain_visible():
    value = snapshot()["graph"]
    # Deliberate pending copies, never manufactured reviewed subject digests.
    for record in value["witnesses"] + value["collations"]:
        record["review"] = {"status": "pending"}
    rows = [row for row in public_text_evidence(value)["texts"] if row["id"] in TEXTS]
    assert len(rows) == 26
    assert all(row["witnesses"] == [] and "collation" not in row for row in rows)
    assert all(row["source_groups"] for row in rows)


def test_a_checksum_receipt_cannot_promote_an_unreviewed_source():
    value = snapshot()["graph"]
    witness = value["witnesses"][0]
    witness["review"] = {"status": "reviewed", "sha256": "0" * 64}
    assert any(witness["id"] in error for error in validate_bindings(ROOT, value))

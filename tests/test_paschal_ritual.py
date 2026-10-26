"""Actual corpus subjects and finite resource, including rejecting controls."""

import copy
import hashlib
import json
from pathlib import Path

import pytest
from witness_header_fixture import expected_transcript

from build_reader import bibliography, dismissal, store
from build_reader import bibliography_bindings as bindings
from checks import delivery, participation, ritual
from checks.collate import collate
from kalendarium.dismissal import calendar_table, canonical_inputs, validate

CORPUS = Path(store.__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def inputs():
    return canonical_inputs(CORPUS)


@pytest.fixture(scope="module")
def table(inputs):
    return calendar_table(*inputs, corpus=CORPUS)


def test_all_actual_pairs_and_independent_reconstruction(table):
    assert table == dismissal.expected(CORPUS)
    assert len(table["pairs"]) == 7682
    assert sum(row[2] == 1 for row in table["pairs"]) == 152
    assert len(table["masses"]) == 114
    for _day, mass, profile in table["pairs"]:
        assert table["masses"][mass] != "none"
        assert table["profiles"][profile]["text"] in {"ordinarium.ite-missa-est", ritual.DISMISSAL}
    by_pair = {(d, table["masses"][m]): p for d, m, p in table["pairs"]}
    assert by_pair["2027-03-27", "vigilia-paschalis"] == 1
    assert by_pair["2027-03-28", "dominica-resurrectionis"] == 1
    assert by_pair["2027-04-04", "dominica-in-albis"] == 0
    assert ("2027-03-28", "vigilia-paschalis") not in by_pair


@pytest.mark.parametrize(
    "mutation",
    [
        lambda t: t.update(role="communicantes"),
        lambda t: t.update(schema_version="0.0.0"),
        lambda t: t.update(extra=1),
        lambda t: t["profiles"][0].update(text=ritual.DISMISSAL),
        lambda t: t.update(masses=[]),
        lambda t: t["masses"].__setitem__(0, None),
        lambda t: t["masses"].__setitem__(0, ""),
        lambda t: t["masses"].append(t["masses"][0]),
        lambda t: t.update(pairs=[]),
        lambda t: t["pairs"].append(t["pairs"][0]),
        lambda t: t["pairs"][0].__setitem__(1, -1),
        lambda t: t["pairs"][0].__setitem__(2, -1),
        lambda t: t["pairs"][0].__setitem__(1, True),
        lambda t: t["pairs"][0].__setitem__(2, True),
        lambda t: t["pairs"][0].__setitem__(0, "2027-2-2"),
        lambda t: t["pairs"][0].append(1),
        lambda t: t["pairs"].reverse(),
    ],
)
def test_resource_malformed_inputs_reject(table, mutation):
    bad = copy.deepcopy(table)
    mutation(bad)
    with pytest.raises(ValueError):
        validate(bad)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda f, c: f[0].update(id=None),
        lambda f, c: f[0].update(id=""),
        lambda f, c: f[0].update(id="none"),
        lambda f, c: f.append(copy.deepcopy(f[0])),
        lambda f, c: f[0].update(id="unknown-mass"),
        lambda f, c: f.clear(),
        lambda f, c: c["years"].clear(),
        lambda f, c: c["years"]["2027"][0].__setitem__(0, "2027-03-28"),
        lambda f, c: c["years"]["2027"][0].__setitem__(1, True),
        lambda f, c: c["years"]["2027"][0].__setitem__(1, -1),
    ],
)
def test_producer_does_not_trust_forged_calendar_or_catalogue(inputs, mutation):
    forms, calendar = copy.deepcopy(inputs)
    mutation(forms, calendar)
    with pytest.raises(ValueError):
        calendar_table(forms, calendar, corpus=CORPUS)


def test_wrong_date_vigil_pair_rejects_at_canonical_boundary(inputs):
    forms, calendar = copy.deepcopy(inputs)
    index = calendar["formularies"].index("vigilia-paschalis")
    row = next(r for r in calendar["years"]["2027"] if r[0] == "2027-03-28")
    row[1] = index
    with pytest.raises(ValueError, match="canonical"):
        calendar_table(forms, calendar, corpus=CORPUS)


def test_literal_selected_derived_and_actual_ritual_rules():
    for text in ritual.TEXTS:
        doc, _ = store.load(CORPUS, text)
        assert delivery.check_doc(doc)[0] == []
        assert participation.check_doc(doc)[0] == []
        errors, warnings, stats = collate(doc, CORPUS / "witnesses" / text)
        assert errors == warnings == []
        if text == ritual.ALLELUIA:
            assert (stats["words"], stats["literal_words"], stats["derived_words"]) == (37, 32, 5)
            literal_hashes = {
                "mr": "6bd0db1b6b9273d80f1412c967e11813e89d8098358543e02d2e431538a865c1",
                "do": "d5af5afd6428d3fa1d64e64fac6731a6353de779560d81ada1697070693186c2",
            }
            for name in ["mr", "do"]:
                assert hashlib.sha256(
                    (CORPUS / "witnesses" / text / f"{name}.txt").read_bytes()
                ).hexdigest() == (
                    expected_transcript(f"witnesses/{text}/mr.txt", literal_hashes[name])
                    if name == "mr"
                    else literal_hashes[name]
                )
        else:
            assert stats["words"] == 15


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d, a: a.pop("ritual_execution"),
        lambda d, a: a["ritual_execution"].update(source_word="w002"),
        lambda d, a: a["ritual_execution"]["performed_words"].reverse(),
        lambda d, a: a["ritual_execution"]["performed_words"].__setitem__(1, "w001"),
        lambda d, a: a["ritual_execution"]["rubric_uses"].update(mr="use.wrong-source"),
        lambda d, a: a["ritual_execution"]["speakers"].__setitem__(1, "schola"),
        lambda d, a: d["segments"][2]["words"][0].update(form="Amen"),
        lambda d, a: d["segments"][2]["words"][0].update(lemma="amen"),
        lambda d, a: d["segments"][2]["delivery"]["cantu"].update(speaker="sacerdos"),
        lambda d, a: d["segments"][2].update(speaker="sacerdos"),
        lambda d, a: d["segments"][2].update(participation={"cantu": {"degree": "III"}}),
        lambda d, a: d["segments"][0].update(text="Ter intonatur."),
        lambda d, a: d["segments"].reverse(),
    ],
)
def test_unmapped_wrong_source_or_role_performance_rejects(mutation):
    doc = store.core(CORPUS, ritual.ALLELUIA)
    app = json.loads((CORPUS / "witnesses" / ritual.ALLELUIA / "apparatus.json").read_text())
    mutation(doc, app)
    with pytest.raises(ValueError):
        ritual.execution(doc, app)


def test_dismissal_alternative_cannot_become_single_performer():
    doc = store.core(CORPUS, ritual.DISMISSAL)
    assert delivery.derive(doc, doc["segments"][4]) == {"cantu": {"voice": "cantus"}}
    doc["segments"][4]["delivery"]["cantu"]["speaker"] = "diaconus"
    assert ritual.base_errors(doc)
    assert delivery.check_doc(doc)[0]


def test_optional_execution_leaves_all_other_subjects_exact():
    graph, _ = bibliography.load(CORPUS)
    new_snapshot = bindings._SourceSnapshot(CORPUS, graph)
    compared = 0
    for witness in graph["witnesses"]:
        if witness["text"] in ritual.TEXTS:
            continue
        doc = store.core(CORPUS, witness["text"])
        after = bindings._witness_subject(CORPUS, witness, doc, new_snapshot, reviewable=False)
        assert "ritual_execution" not in after
        compared += 1
    assert compared > 20


def test_execution_subject_binds_source_use_and_old_reviews_stale():
    graph, _ = bibliography.load(CORPUS)
    doc = store.core(CORPUS, ritual.ALLELUIA)
    witness = next(
        w for w in graph["witnesses"] if w["text"] == ritual.ALLELUIA and w["transcription"] == "mr"
    )
    subject = bindings.witness_subject(CORPUS, witness, graph, doc)
    assert subject["ritual_execution"] == ritual.EXECUTION
    assert ritual.RUBRIC_USES["mr"] in subject["source_uses"]
    changed = copy.deepcopy(subject)
    changed["ritual_execution"]["speakers"][0] = "omnes"
    witness["review"] = {"status": "reviewed", "subject_sha256": bindings.digest(subject)}
    with pytest.raises(bindings.BindingError):
        bindings._review(witness, changed)
    use = next(u for u in graph["uses"] if u["id"] == ritual.RUBRIC_USES["mr"])
    use["locator"]["printed"] = "p. 999"
    with pytest.raises(bindings.BindingError, match="exact inspected"):
        bindings.witness_subject(CORPUS, witness, graph, doc)


def test_new_target_origin_honest_ordinary_and_raw_exact():
    for lang in ["pl", "en"]:
        ledger = json.loads((CORPUS / f"languages/{lang}/translation-provenance.json").read_text())
        new = [r for r in ledger["sites"] if r["text"] == ritual.DISMISSAL]
        assert len(new) == 4 and all(
            r["origin"] == "working-unsettled" and r["review"] == "working" for r in new
        )
    ordinary = store.core(CORPUS, "ordinarium.ite-missa-est")
    assert [w["id"] for s in ordinary["segments"] for w in s.get("words", [])] == [
        f"w{i:03}" for i in range(1, 12)
    ]

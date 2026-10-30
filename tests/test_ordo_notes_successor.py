"""Ordo-witness notes successors are exact, keep the Latin subject and pass faults on."""

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
from ordo_notes_successor_fixture import (
    ADDED,
    CHANGED,
    DATA,
    before_ordo_notes_bytes,
    before_ordo_notes_core_bytes,
    before_ordo_notes_core_object,
    before_ordo_notes_graph,
    before_ordo_notes_layer,
    before_ordo_notes_object,
    before_ordo_notes_use,
)

from build_reader import bibliography
from checks.collate import load_witness

ROOT = Path(__file__).resolve().parents[1]
GRAPH = "bibliography/graph.json"
TEXTS = (
    "orationes.cor-iesu",
    "orationes.deus-refugium",
    "orationes.salve-regina",
    "orationes.sancte-michael",
    "ordinarium.benedictio",
    "ordinarium.credo",
    "ordinarium.gloria",
    "ordinarium.kyrie",
    "ordinarium.placeat-tibi",
    "ordinarium.praefatio-dialogus",
    "ordinarium.sanctus",
)
RUBRICS = {
    "ordinarium.benedictio": ("s01", "s03", "s05"),
    "ordinarium.credo": ("s01", "s08"),
    "ordinarium.gloria": ("s01",),
    "ordinarium.kyrie": ("s01",),
    "ordinarium.placeat-tibi": ("s01",),
    "ordinarium.praefatio-dialogus": ("s01",),
    "ordinarium.sanctus": ("s01",),
}
RETAINED = (
    "The approved Benziger printing's punctuation is retained. "
    "The difference marks phrasing and does not change the words."
)
RETAINED_SITES = {"ordinarium.gloria": ("w079",), "ordinarium.placeat-tibi": ("w023",)}
LEONINE = (
    "orationes.cor-iesu",
    "orationes.deus-refugium",
    "orationes.salve-regina",
    "orationes.sancte-michael",
)
SPEAKERS = {
    "orationes.salve-regina": {
        **{f"s0{n}": "omnes" for n in range(1, 7)},
        "s07": None,
        "s08": "omnes",
    },
    "orationes.sancte-michael": {"s01": "omnes", "s02": "omnes", "s03": "omnes"},
    "orationes.cor-iesu": {"s01": None, "s02": "omnes"},
}
# Corrections recorded on 2026-08-28 that no current wording may carry again.
WITHDRAWN = {
    "orationes.cor-iesu": ("Pius X", "Piusa X"),
    "orationes.sancte-michael": ("composed", "ułożył"),
    "orationes.salve-regina": ("Compline", "komplecie"),
}
DIALOGUE_USE = "use.ordinarium.praefatio-dialogus.hands-rubric.mr1962"
SANCTUS_USE = "use.ordinarium.sanctus.hands-rubric.mr1962"
DEUS_REFUGIUM_USE = "use.core.ab8ff3b4c96a69a66480"
COR_IESU_USE = "use.core.238c8cb41cdab59e8000"
DIALOGUE_MR = "witnesses/ordinarium.praefatio-dialogus/mr.txt"
# Two-leaf official-text uses of the Ordinary: (address kind, segment or word,
# first leaf, second leaf, printed page of the second leaf).
COMPANIONS = {
    "ordinarium.confiteor": ("word", "w016", 298, 299, "p. 220"),
    "ordinarium.confiteor-sacerdotis": ("word", "w016", 298, 299, "p. 220"),
    "ordinarium.gloria": ("segment", "s03", 300, 301, "p. 222"),
    "ordinarium.memento-defunctorum": ("segment", "s02", 389, 390, "p. 309"),
    "ordinarium.panem-caelestem": ("segment", "s04", 395, 396, "p. 315"),
    "ordinarium.per-ipsum": ("segment", "s07", 390, 391, "p. 310"),
    "ordinarium.qui-pridie": ("segment", "s10", 387, 388, "p. 307"),
    "ordinarium.unde-et-memores": ("segment", "s02", 388, 389, "p. 308"),
}
# A page turn inside a segment is named in both claims.
TURNS = {
    "ordinarium.confiteor": "inside s02",
    "ordinarium.confiteor-sacerdotis": "inside s02",
    "ordinarium.panem-caelestem": "the page turn divides",
}
GENERIC = "complete 1962 liturgical component"
PAGE_DIGESTS = {
    298: "ee8d1c45f6cc759518ae59a1dd047dfa80033904ba5ce1799fbaa2334df9ee55",
    299: "f2974f65b87ab6c98e437417413c181b9e10094a20a50181bd8d865abd383600",
    300: "3dea429df749bd62c9a824bc2dadca1ddc74003e2c4fb93a6c2f260ffb4b89a2",
    301: "b7df421df1684232436ba62e3daf3e9b14f67ee641134cc311f8344560c16749",
    387: "f0fa9f9cb03ac8959d1f1498bacc3d9f8e4fa1cc3b9b01642ee08446884c03e4",
    388: "9d8f46853f3f5476f1620491ea99a0f212869f822bfcc646a778d18b052f64b7",
    389: "944637186a14958ceebd4f58f465493ab1bf2580c60dfe848c250b770f818ce4",
    390: "b83dcb2c742c348ef4eeeda4400cf167457494025228dbc34bedd489b002dbf6",
    391: "8756ec3bd389f23992a0d83d0e1654e3c33cbed7c4527167b8fa513edf55ef39",
    395: "54b8eff70c464fed19219b37427a121119c904112e1a72506d92989ecd22cafd",
    396: "956e54a557421ea1276f50669ca0096cec3f5f006e63b1fcaa4002a985950944",
}
PAGE_URL = "https://archive.org/details/missale-romanum-1962/page/n{}/mode/1up"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def core_path(text):
    return ROOT / ("texts/" + text.replace(".", "/", 1) + ".json")


def core(text):
    return json.loads(core_path(text).read_bytes())


def layer(language, text):
    path = ROOT / "languages" / language / ("texts/" + text.replace(".", "/", 1) + ".json")
    return json.loads(path.read_bytes())


def apparatus(text):
    return json.loads((ROOT / "witnesses" / text / "apparatus.json").read_bytes())


def graph():
    return json.loads((ROOT / GRAPH).read_bytes())


def use(value, identity):
    (match,) = [row for row in value["uses"] if row["id"] == identity]
    return match


def body(raw):
    return [line for line in raw.decode("utf-8").splitlines() if not line.startswith("#")]


def test_successor_names_exactly_the_changed_files_and_texts():
    assert tuple(sorted(DATA["texts"])) == TEXTS
    for text in TEXTS:
        assert DATA["texts"][text] == core_path(text).relative_to(ROOT).as_posix()
        assert DATA["texts"][text] in DATA["files"]
    assert len(DATA["files"]) == 26
    assert GRAPH in DATA["files"] and DIALOGUE_MR in DATA["files"]
    assert set(ADDED) == {DIALOGUE_USE} | {f"use.{t}.continuation.mr1962" for t in COMPANIONS}
    assert set(CHANGED) == {COR_IESU_USE, DEUS_REFUGIUM_USE} | {
        f"use.{t}.mr1962" for t in COMPANIONS
    }


@pytest.mark.parametrize("relative", sorted(DATA["files"]))
def test_every_changed_file_inverts_to_its_exact_predecessor(relative):
    rule = DATA["files"][relative]
    raw = (ROOT / relative).read_bytes()
    assert sha(raw) == rule["after_sha256"]
    previous = before_ordo_notes_bytes(relative, raw)
    assert sha(previous) == rule["before_sha256"] != rule["after_sha256"]
    assert before_ordo_notes_bytes(relative, previous) is previous, "a chain may reach it twice"
    if "layout" in rule:
        current = json.loads(raw)
        saved = deepcopy(current)
        assert before_ordo_notes_object(relative, current) == json.loads(previous)
        assert current == saved, "the actual object is never rewritten"
        older = json.loads(previous)
        assert before_ordo_notes_object(relative, older) is older
    assert (ROOT / relative).read_bytes() == raw, "the actual source is never rewritten"


@pytest.mark.parametrize("text", TEXTS)
def test_only_editorial_prose_and_rubric_provenance_change(text):
    current = core(text)
    previous = json.loads(before_ordo_notes_core_bytes(text, core_path(text).read_bytes()))
    assert previous == before_ordo_notes_core_object(text, current)
    assert current["segments"] == previous["segments"]
    assert {k: v for k, v in current.items() if k != "editorial"} == {
        k: v for k, v in previous.items() if k != "editorial"
    }
    now, then = current["editorial"], previous["editorial"]
    assert set(now) == set(then)
    assert {key for key in now if now[key] != then[key]} <= {"notes", "source", "segments"}
    assert {k: v for k, v in now["source"].items() if k != "method"} == {
        k: v for k, v in then["source"].items() if k != "method"
    }
    moved = {
        sid for sid in now.get("segments", {}) if now["segments"][sid] != then["segments"][sid]
    }
    assert moved == set(RUBRICS.get(text, ()))
    for sid in moved:
        assert then["segments"][sid]["analysis"]["sources"] == ["editorial", "do"]
        assert now["segments"][sid]["analysis"] == {
            **then["segments"][sid]["analysis"],
            "sources": ["editorial", "mr"],
        }


@pytest.mark.parametrize("text", sorted(RUBRICS))
def test_every_ordinary_rubric_cites_the_printed_missal(text):
    doc = core(text)
    rubrics = tuple(s["id"] for s in doc["segments"] if s["type"] == "rubric")
    assert rubrics == RUBRICS[text]
    analysis = doc["editorial"]["segments"]
    assert {analysis[sid]["analysis"]["sources"] == ["editorial", "mr"] for sid in rubrics} == {
        True
    }


def test_ten_rubrics_in_all():
    assert sum(len(ids) for ids in RUBRICS.values()) == 10


@pytest.mark.parametrize(
    "text,page",
    (
        ("ordinarium.gloria", "p. 220"),
        ("ordinarium.credo", "p. 223"),
        ("ordinarium.sanctus", "p. 225"),
        ("ordinarium.benedictio", "p. 319"),
    ),
)
def test_core_notes_ground_the_rubrics_on_the_page(text, page):
    notes = core(text)["editorial"]["notes"]
    assert "transcribed by witness do" not in notes
    assert "DO's" not in notes
    assert "approved Benziger printing" in notes and page in notes


def test_kyrie_alternation_names_its_print_basis():
    doc = core("ordinarium.kyrie")
    speakers = [s.get("speaker") for s in doc["segments"] if s["type"] == "verse"]
    assert speakers == ["sacerdos", "minister"] * 4 + ["sacerdos"]
    notes = doc["editorial"]["notes"]
    assert "alternatim cum ministris dicit" in notes and "p. 220" in notes
    assert "(IV, 2)" in notes


@pytest.mark.parametrize("text", sorted(RETAINED_SITES))
def test_retained_punctuation_matches_the_printed_page(text):
    ours = [
        (word["id"], word.get("pre", "") + word["form"] + word.get("post", ""))
        for segment in core(text)["segments"]
        for word in segment.get("words", [])
    ]
    lines = (ROOT / "witnesses" / text / "mr.txt").read_text(encoding="utf-8").splitlines()
    printed = " ".join(line for line in lines if not line.startswith("#")).split()
    assert len(ours) == len(printed)
    position = {wid: index for index, (wid, _) in enumerate(ours)}
    for at in RETAINED_SITES[text]:
        (entry,) = [e for e in apparatus(text)["adjudicated"] if e["at"] == at]
        assert entry["class"] == "punctuation" and entry["ruling"] == RETAINED
        assert entry["ours"] == ours[position[at]][1] == printed[position[at]]


def test_apparatus_notes_count_and_name_their_witnesses():
    credo = apparatus("ordinarium.credo")
    against = [sorted(entry["witnesses"]) for entry in credo["adjudicated"]]
    assert against.count(["do"]) == 9 and against.count(["mr"]) == 1
    assert credo["note"].startswith("Ten adjudicated accidental variants: nine against witness do")
    placeat = apparatus("ordinarium.placeat-tibi")
    assert len(placeat["adjudicated"]) == 5 and placeat["note"].startswith("Five adjudicated")
    sanctus = apparatus("ordinarium.sanctus")
    assert "takes an absence from each" not in sanctus["note"]
    assert "p. 286" in sanctus["note"]
    (w003,) = [entry for entry in sanctus["adjudicated"] if entry["at"] == "w003"]
    assert "p. 286" in w003["ruling"]


@pytest.mark.parametrize("text", LEONINE)
def test_leonine_prose_describes_the_digital_ordo_as_a_derived_aid(text):
    method = core(text)["editorial"]["source"]["method"]
    assert "independent witnesses" not in method
    assert "no independent transmission" in method and "not archived" in method
    rulings = [entry["ruling"] for entry in apparatus(text)["adjudicated"]]
    assert not any("1962 witness" in ruling for ruling in rulings)


@pytest.mark.parametrize("text", sorted(WITHDRAWN))
def test_recorded_corrections_reach_notes_and_both_introductions(text):
    sources = (
        core(text)["editorial"]["notes"],
        layer("en", text)["about"],
        layer("pl", text)["about"],
    )
    for value in sources:
        assert not any(phrase in value for phrase in WITHDRAWN[text])
    if text == "orationes.cor-iesu":
        assert all("1904" in value and "1932" in value for value in sources)


@pytest.mark.parametrize("text", sorted(SPEAKERS))
def test_omnes_values_are_unchanged_and_their_print_basis_is_recorded(text):
    doc = core(text)
    assert {s["id"]: s.get("speaker") for s in doc["segments"]} == SPEAKERS[text]
    assert "simul cum sacerdote (p. 521)" in doc["editorial"]["notes"]
    source = (ROOT / "checks/attribute.py").read_text(encoding="utf-8")
    assert '"simul cum sacerdote" (p. 521)' in source


def test_dialogue_rubric_use_binds_the_page_that_prints_it():
    value = graph()
    new, model = use(value, DIALOGUE_USE), use(value, SANCTUS_USE)
    assert new["address"] == {
        "kind": "segment",
        "text": "ordinarium.praefatio-dialogus",
        "segment": "s01",
    }
    for key in ("edition", "digital_item", "role", "evidence_sha256", "decision"):
        assert new[key] == model[key]
    for key in ("printed", "scan", "page_url"):
        assert new["locator"][key] == model["locator"][key]
    s01 = core("ordinarium.praefatio-dialogus")["segments"][0]
    assert s01["id"] == "s01" and s01["type"] == "rubric"
    assert s01["text"].startswith("Præfationem incipit") and "Sursum corda" in s01["text"]


def test_enchiridion_records_locate_their_pages():
    value = graph()
    deus = use(value, DEUS_REFUGIUM_USE)
    assert deus["locator"] == {"printed": "p. 520", "scan": "PDF scan 541", "section": "n. 675"}
    assert "PDF scan 541" in deus["decision_reason"]
    cor = use(value, COR_IESU_USE)
    assert cor["locator"] == {"printed": "p. 521", "scan": "PDF scan 542", "section": "n. 675"}
    assert "si addatur ter" in cor["claim"] and "directed" not in cor["claim"]


@pytest.mark.parametrize("text", sorted(COMPANIONS))
def test_each_second_leaf_has_one_leaf_bound_continuation(text):
    kind, at, first, second, printed = COMPANIONS[text]
    value = graph()
    parent = use(value, f"use.{text}.mr1962")
    companion = use(value, f"use.{text}.continuation.mr1962")
    assert parent["locator"]["scan"] == f"leaf n{first} / PDF p. {first + 1}"
    assert parent["locator"]["page_url"] == PAGE_URL.format(first)
    assert parent["evidence_sha256"] == PAGE_DIGESTS[first]
    assert parent["address"] == {"kind": "text", "text": text}
    assert companion["address"] == {"kind": kind, "text": text, kind: at}
    assert companion["locator"] == {
        "printed": printed,
        "scan": f"leaf n{second} / PDF p. {second + 1}",
        "page_url": PAGE_URL.format(second),
    }
    assert companion["evidence_sha256"] == PAGE_DIGESTS[second]
    for key in ("edition", "digital_item", "role", "decision"):
        assert companion[key] == parent[key]
    assert parent["locator"]["printed"] == f"p. {int(printed.removeprefix('p. ')) - 1}"
    for claim in (parent["claim"], companion["claim"]):
        assert claim.startswith("The cited page image prints ")
        assert GENERIC not in claim
        if text in TURNS:
            assert TURNS[text] in claim
    assert (
        f"from {at} to its end" in companion["claim"] or f"({at}) to its end" in companion["claim"]
    )
    if kind == "segment":
        assert at in {segment["id"] for segment in core(text)["segments"]}
    else:
        words = [w for segment in core(text)["segments"] for w in segment.get("words", [])]
        assert at in {w["id"] for w in words}
    bound = {
        row["id"]
        for row in value["uses"]
        if row.get("evidence_sha256") == PAGE_DIGESTS[second]
        and (row.get("address") or {}).get("text") == text
    }
    assert bound == {companion["id"]}


def test_one_leaf_claims_keep_the_residual_scope_contracts():
    """The Confiteor and Panem caelestem contracts move to the page that prints them."""
    value = graph()
    confiteor = use(value, "use.ordinarium.confiteor.continuation.mr1962")["claim"]
    assert "with tibi, pater and te, pater in place of vobis, fratres and vos, fratres" in confiteor
    assert "it is not a second complete printed formula" in confiteor
    assert "mea culpa" not in confiteor
    panem = use(value, "use.ordinarium.panem-caelestem.continuation.mr1962")["claim"]
    assert "one complete Domine, non sum dignus petition" in panem
    assert "three complete copies are not printed there" in panem
    assert "ending animam meam" in panem and "animam tuam" not in panem
    for text in ("ordinarium.confiteor", "ordinarium.panem-caelestem"):
        assert "mea culpa" not in use(value, f"use.{text}.mr1962")["claim"]


def test_no_ordinary_official_text_use_cites_two_leaves():
    rows = [
        row
        for row in graph()["uses"]
        if row["edition"] == "edition.missale-romanum.1962-typica"
        and row["role"] == "official_text"
        and row["address"]["text"].startswith("ordinarium.")
    ]
    assert len(rows) > len(COMPANIONS)
    for row in rows:
        leaf = re.fullmatch(r"leaf n(\d+) / PDF p\. (\d+)", row["locator"]["scan"])
        assert leaf and int(leaf.group(2)) == int(leaf.group(1)) + 1, row["id"]


def test_the_graph_validates():
    assert bibliography.validate(ROOT, *bibliography.load(ROOT)) == []


def test_dialogue_transcript_records_the_misprint_and_keeps_its_body():
    raw = (ROOT / DIALOGUE_MR).read_bytes()
    assert body(raw) == body(before_ordo_notes_bytes(DIALOGUE_MR, raw))
    meta, _ = load_witness(ROOT / DIALOGUE_MR)
    assert meta["speaker-sign"].startswith("the page sets ℟. before Sursum corda")
    (sursum,) = [
        segment
        for segment in core("ordinarium.praefatio-dialogus")["segments"]
        if [word["form"] for word in segment.get("words", [])] == ["Sursum", "corda"]
    ]
    assert sursum["id"] == "s04" and sursum["speaker"] == "sacerdos"


@pytest.mark.parametrize(
    "old,new",
    (
        (b'"In Missa pontificali', b'"In missa pontificali'),
        (b'"sources": ["editorial", "mr"]', b'"sources": ["editorial", "do", "mr"]'),
        (b"(XII, 1)", b"(XII,1)"),
    ),
)
def test_any_other_bytes_reach_the_older_oracle_with_the_fault(old, new):
    text = "ordinarium.benedictio"
    raw = core_path(text).read_bytes()
    changed = raw.replace(old, new, 1)
    assert changed != raw
    result = before_ordo_notes_core_bytes(text, changed)
    assert sha(result) != DATA["files"][DATA["texts"][text]]["before_sha256"]
    assert new in result
    appended = before_ordo_notes_core_bytes(text, raw + b"\n")
    assert appended == before_ordo_notes_core_bytes(text, raw) + b"\n"


@pytest.mark.parametrize("fault", ("sources", "rubric", "word", "notes"))
def test_any_other_object_reaches_the_older_oracle_with_the_fault(fault):
    text = "ordinarium.placeat-tibi"
    current = core(text)
    previous = before_ordo_notes_core_object(text, current)
    if fault == "sources":
        current["editorial"]["segments"]["s01"]["analysis"]["sources"] = ["editorial", "do", "mr"]
    elif fault == "rubric":
        current["segments"][0]["text"] += " "
    elif fault == "word":
        current["segments"][1]["words"][0]["form"] = "Pláceat,"
    else:
        current["editorial"]["notes"] += " Extra."
    result = before_ordo_notes_core_object(text, current)
    assert result != previous
    if fault == "word":
        assert result["segments"][1]["words"][0]["form"] == "Pláceat,"


def test_graph_inverse_removes_the_new_uses_and_restores_ten_records():
    value = graph()
    saved = deepcopy(value)
    previous = before_ordo_notes_graph(value)
    assert value == saved and previous is not value
    assert [row["id"] for row in previous["uses"]] == [
        row["id"] for row in value["uses"] if row["id"] not in ADDED
    ]
    for identity, change in CHANGED.items():
        assert use(previous, identity) == change["before"]
        assert before_ordo_notes_use(use(value, identity)) == change["before"]
    assert previous == json.loads(before_ordo_notes_bytes(GRAPH, (ROOT / GRAPH).read_bytes()))
    assert before_ordo_notes_object(GRAPH, value) == previous
    assert before_ordo_notes_graph(previous) is previous, "a chain may reach it twice"
    records = {"uses": [use(value, DIALOGUE_USE), use(value, COR_IESU_USE)], "witnesses": []}
    assert before_ordo_notes_graph(records) == {
        "uses": [CHANGED[COR_IESU_USE]["before"]],
        "witnesses": [],
    }


@pytest.mark.parametrize("identity", sorted([DIALOGUE_USE, COR_IESU_USE, DEUS_REFUGIUM_USE]))
def test_a_damaged_declared_use_stays_for_the_older_guards(identity):
    value = graph()
    use(value, identity)["verified_on"] = "2026-09-25"
    previous = before_ordo_notes_graph(value)
    assert use(previous, identity)["verified_on"] == "2026-09-25"
    duplicated = graph()
    duplicated["uses"].append(deepcopy(use(duplicated, identity)))
    kept = before_ordo_notes_graph(duplicated)
    assert len([row for row in kept["uses"] if row["id"] == identity]) == 2


def test_layer_inverse_follows_the_layer_address():
    current = layer("pl", "orationes.cor-iesu")
    previous = before_ordo_notes_layer(current)
    assert previous != current and "Piusa X" in previous["about"]
    assert before_ordo_notes_layer(previous) is previous


def test_unrelated_values_pass_through_untouched():
    raw = core_path("ordinarium.confiteor").read_bytes()
    assert before_ordo_notes_core_bytes("ordinarium.confiteor", raw) is raw
    value = json.loads(raw)
    assert before_ordo_notes_core_object("ordinarium.confiteor", value) is value
    assert before_ordo_notes_object("texts/ordinarium/confiteor.json", value) is value
    assert before_ordo_notes_bytes("languages/de/bibliography.json", raw) is raw
    assert before_ordo_notes_graph({"witnesses": []}) == {"witnesses": []}

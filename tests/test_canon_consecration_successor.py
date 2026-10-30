"""The Canon rubrics follow the 1962 page; every earlier exact pin stays reachable."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from canon_consecration_successor_fixture import (
    DATA,
    DIAGNOSTIC,
    GRAPH_DIAGNOSTIC,
    before_canon_bytes,
    before_canon_core_bytes,
    before_canon_core_frame,
    before_canon_core_object,
    before_canon_graph,
    before_canon_layer,
    before_canon_layer_frame,
    current_canon_row,
)
from foot_communion_successor_fixture import (
    before_foot_communion_bytes,
    before_foot_communion_graph,
)
from quam_rationabilem_successor_fixture import before_quam_core_bytes
from reader_arrow_successor_fixture import before_arrow_bytes, before_arrow_graph

ROOT = Path(__file__).resolve().parents[1]
REGISTERED = {
    row["text"]: row["core_sha256"]
    for row in json.loads((ROOT / "tests/fixtures/main-ordo-registrations.json").read_bytes())[
        "rows"
    ]
}
TEXTS = (
    "ordinarium.memento-defunctorum",
    "ordinarium.memento-vivorum",
    "ordinarium.nobis-quoque",
    "ordinarium.per-ipsum",
    "ordinarium.per-quem-haec-omnia",
    "ordinarium.quam-oblationem",
    "ordinarium.qui-pridie",
    "ordinarium.simili-modo",
    "ordinarium.supplices-te-rogamus",
    "ordinarium.supra-quae",
    "ordinarium.te-igitur",
    "ordinarium.unde-et-memores",
)
DIVIDED = ("ordinarium.qui-pridie", "ordinarium.quam-oblationem", "ordinarium.simili-modo")
# Every rubric of the twelve texts, as the 1962 Ordo Missae prints it (pp. 303–310); a
# rubric the page runs into the text keeps the house standalone capital or full stop.
RUBRICS = {
    "ordinarium.te-igitur": {
        "s01": "Finita præfatione, sacerdos extendens, elevans aliquantulum et iungens manus, "
        "elevansque ad cælum oculos, et statim demittens, profunde inclinatus ante altare, "
        "manibus super eo positis, dicit secreto:",
        "s03": "Osculatur altare, et iunctis manibus ante pectus, dicit:",
        "s05": "Signat ter super hostiam et calicem simul, dicens:",
        "s07": "Extensis manibus prosequitur:",
    },
    "ordinarium.memento-vivorum": {
        "s02": "Iungit manus, orat aliquantulum pro quibus orare intendit: deinde manibus "
        "extensis prosequitur:",
    },
    "ordinarium.quam-oblationem": {
        "s02": "Signat ter super oblata.",
        "s04": "Signat semel super hostiam,",
        "s08": "et semel super calicem,",
        "s06": "Iungit manus.",
    },
    "ordinarium.qui-pridie": {
        "s01": "Accipit hostiam.",
        "s03": "Elevat oculos ad cælum.",
        "s05": "Caput inclinat.",
        "s07": "Signat super hostiam.",
        "s10": "Tenens ambabus manibus hostiam inter indices et pollices, profert verba "
        "consecrationis distincte et attente super hostiam, et simul super omnes, si plures "
        "sint consecrandæ.",
        "s12": "Quibus verbis prolatis, statim hostiam consecratam genuflexus adorat: surgit, "
        "ostendit populo, reponit super corporale, et genuflexus iterum adorat: nec amplius "
        "pollices et indices disiungit, nisi quando hostia tractanda est, usque ad ablutionem "
        "digitorum.",
    },
    "ordinarium.simili-modo": {
        "s01": "Tunc, detecto calice, dicit:",
        "s03": "Ambabus manibus accipit calicem,",
        "s05": "Caput inclinat,",
        "s07": "Sinistra tenens calicem, dextera signat super eum,",
        "s10": "Profert verba consecrationis super calicem, attente et continuate, tenens illum "
        "parum elevatum.",
        "s12": "Quibus verbis prolatis, deponit calicem super corporale, et dicens:",
        "s14": "Genuflexus adorat: surgit, ostendit populo, deponit, cooperit, et genuflexus "
        "iterum adorat.",
    },
    "ordinarium.unde-et-memores": {
        "s01": "Deinde disiunctis manibus dicit:",
        "s04": "Iungit manus, et signat ter super hostiam, et calicem simul, dicens:",
        "s06": "Signat semel super hostiam, dicens:",
        "s08": "Et semel super calicem, dicens:",
    },
    "ordinarium.supra-quae": {"s01": "Extensis manibus prosequitur:"},
    "ordinarium.supplices-te-rogamus": {
        "s01": "Profunde inclinatus, iunctis manibus et super altare positis, dicit:",
        "s03": "Osculatur altare.",
        "s05": "Iungit manus, et signat semel super hostiam, et semel super calicem.",
        "s07": "Seipsum signat, dicens:",
        "s09": "Iungit manus.",
    },
    "ordinarium.memento-defunctorum": {
        "s02": "Iungit manus, orat aliquantulum pro iis defunctis, pro quibus orare intendit, "
        "deinde extensis manibus prosequitur:",
        "s04": "Iungit manus, et caput inclinat, dicens:",
    },
    "ordinarium.nobis-quoque": {
        "s01": "Manu dextera percutit sibi pectus, elata aliquantulum voce dicens:",
        "s03": "Extensis manibus ut prius, secrete prosequitur:",
        "s07": "Iungit manus.",
    },
    "ordinarium.per-quem-haec-omnia": {
        "s02": "Signat ter super hostiam, et calicem simul, dicens:",
    },
    "ordinarium.per-ipsum": {
        "s01": "Discooperit calicem, genuflectit, accipit hostiam inter pollicem et indicem manus "
        "dexteræ: et tenens sinistra calicem, cum hostia signat ter a labio ad labium calicis, "
        "dicens:",
        "s03": "Cum ipsa hostia signat bis inter se et calicem, dicens:",
        "s05": "Elevans parum calicem cum hostia, dicit:",
        "s07": "Reponit hostiam, calicem palla cooperit, genuflectit, surgit, et dicit "
        "intellegibili voce, vel cantat:",
    },
}
# New printed-edition uses: (use, the use already binding the same page digest).
PRINTED_BASES = (
    ("use.ordinarium.simili-modo.mr1962", "use.ordinarium.unde-et-memores.mr1962"),
    ("use.ordinarium.supplices-te-rogamus.mr1962", "use.ordinarium.supra-quae.mr1962"),
)
# (text, rubric, the spoken word it follows, the spoken word it precedes)
PLACES = (
    ("ordinarium.qui-pridie", "s01", "w004", "w005"),
    ("ordinarium.quam-oblationem", "s04", "w014", "w015"),
    ("ordinarium.quam-oblationem", "s08", "w017", "w018"),
    ("ordinarium.simili-modo", "s05", "w017", "w018"),
)
# (text, segment that keeps its id, minted segment, segments.next before, after)
MINTS = (
    ("ordinarium.qui-pridie", "s02", "s13", 13, 14),
    ("ordinarium.quam-oblationem", "s05", "s09", 8, 10),
    ("ordinarium.simili-modo", "s06", "s15", 15, 16),
)
PATTERN = rf"^{DIAGNOSTIC}$"


def core_path(text):
    return ROOT / ("texts/" + text.replace(".", "/", 1) + ".json")


def core(text):
    return json.loads(core_path(text).read_bytes())


def predecessor(relative):
    return json.loads(before_canon_bytes(relative, (ROOT / relative).read_bytes()))


def words(doc):
    return [word for segment in doc["segments"] for word in segment.get("words", [])]


def test_successor_names_exactly_the_changed_files_and_texts():
    assert tuple(sorted(DATA["texts"])) == TEXTS
    for text in TEXTS:
        assert DATA["texts"][text] == core_path(text).relative_to(ROOT).as_posix()
        assert DATA["texts"][text] in DATA["files"]
    assert sorted(DATA["core_frames"]) == sorted(DIVIDED)
    assert len(DATA["layer_frames"]) == 6
    assert len(DATA["ledger_rows"]) == 12
    assert [rule["row"]["id"] for rule in DATA["graph_uses"]] == [
        use for use, _ in sorted(PRINTED_BASES)
    ]


@pytest.mark.parametrize("relative", sorted(DATA["files"]))
def test_every_changed_file_inverts_to_its_exact_predecessor(relative):
    rule = DATA["files"][relative]
    actual = (ROOT / relative).read_bytes()
    raw = before_foot_communion_bytes(relative, before_arrow_bytes(relative, actual))
    assert hashlib.sha256(raw).hexdigest() == rule["after_sha256"]
    previous = before_canon_bytes(relative, raw)
    assert hashlib.sha256(previous).hexdigest() == rule["before_sha256"] != rule["after_sha256"]
    assert before_canon_bytes(relative, previous) == previous, "a chain may reach it twice"
    assert (ROOT / relative).read_bytes() == actual, "the actual source is never rewritten"


@pytest.mark.parametrize("text", TEXTS)
def test_current_core_inverts_to_its_registered_bytes(text):
    raw = core_path(text).read_bytes()
    comparison = before_canon_core_bytes(text, raw)
    assert comparison != raw
    # The Quam registration also predates its English note declaration.
    comparison = before_quam_core_bytes(text, comparison)
    assert hashlib.sha256(comparison).hexdigest() == REGISTERED[text]
    assert core_path(text).read_bytes() == raw


@pytest.mark.parametrize("text", TEXTS)
def test_the_latin_words_are_unchanged(text):
    current = core(text)
    previous = json.loads(before_canon_core_bytes(text, core_path(text).read_bytes()))
    assert words(current) == words(previous)
    assert {k: v for k, v in current.items() if k not in ("segments", "editorial", "ids")} == {
        k: v for k, v in previous.items() if k not in ("segments", "editorial", "ids")
    }


@pytest.mark.parametrize("text", sorted(RUBRICS))
def test_every_rubric_reads_as_printed_and_cites_the_printed_missal(text):
    doc = core(text)
    rubrics = {s["id"]: s["text"] for s in doc["segments"] if s["type"] == "rubric"}
    assert rubrics == RUBRICS[text]
    analysis = doc["editorial"]["segments"]
    assert {sid: analysis[sid]["analysis"]["sources"] for sid in rubrics} == {
        sid: ["editorial", "mr"] for sid in rubrics
    }


def test_forty_two_rubrics_in_all():
    # Te igitur to Simili modo 22 (Quam oblationem's new s08 included), Unde to Per ipsum 20.
    assert sum(len(rubrics) for rubrics in RUBRICS.values()) == 42


@pytest.mark.parametrize("text,rubric,follows,precedes", PLACES)
def test_rubric_stands_where_the_page_prints_it(text, rubric, follows, precedes):
    segments = core(text)["segments"]
    index = [s["id"] for s in segments].index(rubric)
    assert segments[index - 1]["words"][-1]["id"] == follows
    assert segments[index + 1]["words"][0]["id"] == precedes


@pytest.mark.parametrize("text,kept,minted,before,after", MINTS)
def test_divided_verse_keeps_its_id_and_mints_one(text, kept, minted, before, after):
    current = core(text)
    previous = json.loads(before_canon_core_bytes(text, core_path(text).read_bytes()))
    assert previous["ids"]["segments"]["next"] == before
    assert current["ids"]["segments"]["next"] == after
    old = {s["id"]: s for s in previous["segments"]}
    new = {s["id"]: s for s in current["segments"]}
    assert minted not in old and minted in new and int(minted[1:]) >= before
    assert set(old) <= set(new)
    joined = {w["id"] for w in new[kept]["words"]} | {w["id"] for w in new[minted]["words"]}
    assert joined == {w["id"] for w in old[kept]["words"]}
    assert new[minted]["speaker"] == old[kept]["speaker"]
    assert new[minted]["voice"] == old[kept]["voice"]


@pytest.mark.parametrize("relative", sorted(DATA["layer_frames"]))
def test_divided_translation_rejoins_to_its_predecessor(relative):
    current = json.loads((ROOT / relative).read_bytes())
    previous = predecessor(relative)
    text = current["text"]
    order = [s["id"] for s in core(text)["segments"]]
    for kept, minted in [(m["kept"], m["new"]) for m in DATA["core_frames"][text]["merges"]]:
        first, second = sorted((kept, minted), key=order.index)
        joined = (
            current["segments"][first]["translation"]
            + " "
            + (current["segments"][second]["translation"])
        )
        assert joined == previous["segments"][kept]["translation"]
        assert minted not in previous["segments"]
        assert current["segments"][kept].get("translation_citations") == (
            previous["segments"][kept].get("translation_citations")
        )
        assert "translation_citations" not in current["segments"][minted]
    assert before_canon_layer_frame(current) == previous
    assert before_canon_layer(current) == previous


@pytest.mark.parametrize("text", DIVIDED)
def test_core_frame_rebuilds_the_predecessor_segments(text):
    current = core(text)
    previous = json.loads(before_canon_core_bytes(text, core_path(text).read_bytes()))
    assert before_canon_core_frame(current)["segments"] == previous["segments"]
    assert before_canon_core_object(text, current) == previous


def test_new_ledger_sites_start_unclassified_and_changed_sites_return_to_working():
    for change in DATA["ledger_rows"]:
        ledger = json.loads((ROOT / change["relative"]).read_bytes())
        rows = [row for row in ledger["sites"] if row["site"] == change["site"]]
        assert rows == [change["after"]]
        assert change["after"]["review"] == "working"
        if change["before"] is None:
            assert change["after"]["origin"] == "working-unsettled"
        else:
            assert change["after"]["origin"] == change["before"]["origin"]
            assert current_canon_row(change["before"]) == change["after"]
    unrelated = {"site": "orationes.ave-maria.s01.pl"}
    assert current_canon_row(unrelated) is unrelated


@pytest.mark.parametrize("identity,bound_by", PRINTED_BASES)
def test_printed_basis_binds_the_page_already_bound(identity, bound_by):
    graph = json.loads((ROOT / "bibliography/graph.json").read_bytes())
    uses = {use["id"]: use for use in graph["uses"]}
    use = uses[identity]
    assert use == next(rule["row"] for rule in DATA["graph_uses"] if rule["row"]["id"] == identity)
    assert use["evidence_sha256"] == uses[bound_by]["evidence_sha256"]
    assert list(use) == list(uses[bound_by])
    for key in ("edition", "digital_item", "role", "claim", "decision"):
        assert use[key] == uses[bound_by][key]
    text = use["address"]["text"]
    method = core(text)["editorial"]["source"]["method"]
    assert method == core("ordinarium.qui-pridie")["editorial"]["source"]["method"]
    assert "independent" not in method


def test_te_igitur_transcript_prints_the_comma_the_apparatus_records():
    lines = (ROOT / "witnesses/ordinarium.te-igitur/mr.txt").read_text(encoding="utf-8")
    tokens = " ".join(line for line in lines.splitlines() if not line.startswith("#")).split()
    current = core("ordinarium.te-igitur")
    ids = [word["id"] for word in words(current)]
    assert len(tokens) == len(ids)
    assert tokens[ids.index("w015")] == "pétimus,"
    apparatus = json.loads((ROOT / "witnesses/ordinarium.te-igitur/apparatus.json").read_bytes())
    (entry,) = [e for e in apparatus["adjudicated"] if e["at"] == "w015"]
    assert entry["witnesses"] == {"do": "pétimus,", "mr": "pétimus,"}
    assert entry["ours"] == "pétimus"


def test_memento_ruling_describes_the_printed_slot():
    text = "ordinarium.memento-defunctorum"
    apparatus = json.loads((ROOT / "witnesses" / text / "apparatus.json").read_bytes())
    (entry,) = [
        e for e in apparatus["adjudicated"] if e["at"] == "w006" and e["class"] == "punctuation"
    ]
    assert entry["witnesses"] == {"do": "tuárum,"} and entry["ours"] == "tuárum"
    assert "no comma after the name slot" in entry["ruling"]
    assert "In the missal the comma follows" not in entry["ruling"]
    lines = (ROOT / "witnesses" / text / "mr.txt").read_text(encoding="utf-8").splitlines()
    tokens = " ".join(line for line in lines if not line.startswith("#")).split()
    ids = [word["id"] for word in words(core(text))]
    assert tokens[ids.index("w006")] == "tuárum"


@pytest.mark.parametrize("fault", ("rubric-byte", "provenance", "word", "appended"))
def test_inverse_rejects_any_other_current_bytes(fault):
    text = "ordinarium.simili-modo"
    raw = core_path(text).read_bytes()
    if fault == "rubric-byte":
        changed = raw.replace(b'"Caput inclinat,"', b'"Caput inclinat."', 1)
    elif fault == "provenance":
        changed = raw.replace(
            b'"sources": ["editorial", "mr"]', b'"sources": ["editorial", "do", "mr"]', 1
        )
    elif fault == "word":
        changed = raw.replace(b'"form": "item"', b'"form": "Item"', 1)
    else:
        changed = raw + b"\n"
    assert changed != raw
    with pytest.raises(AssertionError, match=PATTERN):
        before_canon_core_bytes(text, changed)
    comparison = before_canon_core_bytes(text, raw)
    assert hashlib.sha256(comparison).hexdigest() == REGISTERED[text]


@pytest.mark.parametrize("fault", ("rubric", "word", "sources"))
def test_object_inverse_rejects_any_other_current_object(fault):
    text = "ordinarium.quam-oblationem"
    current = core(text)
    if fault == "rubric":
        current["segments"][5]["text"] = "Et semel super calicem."
    elif fault == "word":
        current["segments"][6]["words"][0]["form"] = "Et"
    else:
        current["editorial"]["segments"]["s08"]["analysis"]["sources"] = ["editorial"]
    with pytest.raises(AssertionError, match=PATTERN):
        before_canon_core_object(text, current)
    if fault == "rubric":
        with pytest.raises(AssertionError, match=PATTERN):
            before_canon_core_frame(current)
    else:
        # The frame binds only the divided segments; the older oracle still sees the fault.
        framed = before_canon_core_frame(current)
        forms = [
            word["form"] for segment in framed["segments"] for word in segment.get("words", [])
        ]
        assert ("Et" in forms) == (fault == "word")
        assert framed["editorial"] == current["editorial"]


def test_frames_keep_unrelated_faults_for_the_older_oracle():
    text = "ordinarium.quam-oblationem"
    current = core(text)
    current["segments"][0]["words"][0]["form"] = "Quamx"
    framed = before_canon_core_frame(current)
    assert framed["segments"][0]["words"][0]["form"] == "Quamx"
    relative = "languages/en/texts/ordinarium/quam-oblationem.json"
    layer = json.loads((ROOT / relative).read_bytes())
    layer["segments"]["s03"]["translation"] += " Extra."
    framed = before_canon_layer_frame(layer)
    assert framed["segments"]["s03"]["translation"].endswith(" Extra.")
    assert "s09" not in framed["segments"]


def test_graph_inverse_removes_only_the_new_uses():
    graph = before_foot_communion_graph(json.loads((ROOT / "bibliography/graph.json").read_bytes()))
    saved = deepcopy(graph)
    previous = before_canon_graph(before_arrow_graph(graph))
    added = {rule["row"]["id"] for rule in DATA["graph_uses"]}
    assert graph == saved and previous is not graph
    assert [u["id"] for u in previous["uses"]] == [
        u["id"] for u in graph["uses"] if u["id"] not in added
    ]
    raw = (ROOT / "bibliography/graph.json").read_bytes()
    assert previous == json.loads(before_canon_bytes("bibliography/graph.json", raw))
    assert before_canon_graph(previous) is previous, "a chain may reach it twice"
    for rule in DATA["graph_uses"]:
        changed = deepcopy(graph)
        changed["uses"][rule["index"]]["verified_on"] = "2026-09-25"
        with pytest.raises(AssertionError, match=rf"^{GRAPH_DIAGNOSTIC}$"):
            before_canon_graph(changed)
    partial = deepcopy(graph)
    del partial["uses"][DATA["graph_uses"][0]["index"]]
    with pytest.raises(AssertionError, match=rf"^{GRAPH_DIAGNOSTIC}$"):
        before_canon_graph(partial)


def test_unrelated_values_pass_through_untouched():
    raw = core_path("ordinarium.confiteor").read_bytes()
    assert before_canon_core_bytes("ordinarium.confiteor", raw) is raw
    value = json.loads(raw)
    assert before_canon_core_object("ordinarium.confiteor", value) is value
    assert before_canon_core_frame(value) is value
    layer = {"language": "pl", "text": "ordinarium.confiteor"}
    assert before_canon_layer(layer) is layer and before_canon_layer_frame(layer) is layer

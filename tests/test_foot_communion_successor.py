"""Foot of the altar and Communion texts follow the 1962 page; older pins stay reachable."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from foot_communion_successor_fixture import (
    DATA,
    DIAGNOSTIC,
    GRAPH_DIAGNOSTIC,
    before_foot_communion_bytes,
    before_foot_communion_core_bytes,
    before_foot_communion_core_object,
    before_foot_communion_graph,
    before_foot_communion_layer,
    before_foot_communion_layer_frame,
    before_foot_communion_object,
    current_foot_communion_row,
)
from reader_arrow_successor_fixture import before_arrow_bytes, before_arrow_graph

from checks.requiem_assembly import TARGETS, target_errors

ROOT = Path(__file__).resolve().parents[1]
REGISTERED = {
    row["text"]: row["core_sha256"]
    for row in json.loads((ROOT / "tests/fixtures/main-ordo-registrations.json").read_bytes())[
        "rows"
    ]
}
TEXTS = (
    "ordinarium.adiutorium",
    "ordinarium.corpus-tuum",
    "ordinarium.deus-tu-conversus",
    "ordinarium.introibo",
    "ordinarium.iudica-me",
    "ordinarium.misereatur",
    "ordinarium.misereatur-tui",
    "ordinarium.panem-caelestem",
    "ordinarium.qui-dixisti",
    "ordinarium.quid-retribuam",
    "ordinarium.quod-ore-sumpsimus",
)
MINISTRI = "Ministri respondent:"
# Every rubric of the eleven texts, as the 1962 Ordo Missae prints it (pp. 219-220,
# 313-316); a rubric the page runs into the text keeps the house standalone capital or
# full stop.
RUBRICS = {
    "ordinarium.introibo": {
        "s01": "Sacerdos paratus cum ingreditur ad altare, facta illi debita reverentia, signat "
        "se signo crucis a fronte ad pectus, et clara voce dicit nisi peculiari rubrica aliter "
        "statuatur:",
        "s03": "Deinde, iunctis manibus ante pectus, incipit antiphonam:",
        "s06": MINISTRI,
    },
    "ordinarium.iudica-me": {
        "s01": "In Missis defunctorum, et in Missis de Tempore a dominica I Passionis usque ad "
        "feriam V in Cena Domini inclusive, omittitur psalmus Iúdica me, Deus, cum Glória "
        "Patri, et repetitione antiphonæ, sed dicto In nómine Patris, Introíbo, et Adiutórium, "
        "fit confessio.",
        "s02": "Postea alternatim cum ministris dicit sequentem",
        "s11": "Sacerdos repetit antiphonam:",
    },
    "ordinarium.adiutorium": {"s01": "Signat se, dicens:"},
    "ordinarium.misereatur-tui": {
        "s05": MINISTRI,
        "s02": "Sacerdos dicit:",
        "s04": "Et erigit se. Deinde ministri repetunt confessionem: et ubi a sacerdote "
        "dicebatur vobis, fratres, et vos, fratres, a ministris dicitur tibi, pater, et te, "
        "pater.",
    },
    "ordinarium.misereatur": {
        "s01": "Postea sacerdos, iunctis manibus, facit absolutionem, dicens:",
        "s04": "Signat se signo crucis, dicens:",
    },
    "ordinarium.deus-tu-conversus": {"s01": "Et inclinatus prosequitur:"},
    "ordinarium.qui-dixisti": {
        "s01": "Deinde, iunctis manibus super altare, inclinatus dicit secrete sequentes "
        "orationes:",
        "s07": "Si danda est pax, osculatur altare, et dans pacem, dicit:",
        "s10": "In Missis defunctorum non datur pax, neque dicitur præcedens oratio.",
    },
    "ordinarium.panem-caelestem": {
        "s01": "Genuflectit, surgit, et dicit:",
        "s03": "Deinde parum inclinatus, accipit ambas partes hostiæ inter pollicem et indicem "
        "sinistræ manus, et patenam inter eundem indicem, et medium supponit, et dextera "
        "tribus vicibus percutiens pectus, elata aliquantulum voce, ter dicit devote, et "
        "humiliter:",
        "s05": "Et secrete prosequitur:",
        "s08": "Et secrete prosequitur:",
        "s11": "Et secrete prosequitur:",
        "s13": "Postea dextera se signans cum hostia super patenam, dicit:",
        "s15": "Et se inclinans, reverenter sumit ambas partes hostiæ: quibus sumptis, deponit "
        "Patenam super corporale, et erigens se iungit manus, et quiescit aliquantulum in "
        "meditatione Ssmi Sacramenti.",
    },
    "ordinarium.quid-retribuam": {
        "s01": "Deinde discooperit calicem, genuflectit, colligit fragmenta, si quæ sint, "
        "extergit patenam super calicem, interim dicens:",
        "s05": "Accipit calicem manu dextera, et eo se signans, dicit:",
        "s07": "Et sinistra supponens patenam calici, reverenter sumit totum Sanguinem cum "
        "particula.",
    },
    "ordinarium.quod-ore-sumpsimus": {
        "s01": "Postea dicit:",
        "s03": "Interim porrigit calicem ministro, qui infundit in eo parum vini, quo se "
        "purificat.",
    },
    "ordinarium.corpus-tuum": {
        "s01": "Deinde prosequitur:",
        "s05": "Abluit et extergit digitos, ac sumit ablutionem: extergit os et calicem, quem, "
        "plicato corporali, operit et collocat in altari ut prius: deinde prosequitur Missam.",
    },
}
# (text, minted rubric, spoken word before it or None, spoken word after it,
#  segments.next before and after)
MINTS = (
    ("ordinarium.introibo", "s06", "w013", "w014", 6, 7),
    ("ordinarium.misereatur-tui", "s05", None, "w001", 5, 6),
)
NARRATIVES = {"pl": "Usługujący odpowiadają.", "en": "The ministers answer."}
# (text, word, printed reading, transcript token)
PRINTED = (
    ("ordinarium.misereatur-tui", "w014", "Amen", "Amen"),
    ("ordinarium.qui-dixisti", "w022", "tuæ:", "tuæ:"),
)
RETAINED = (
    "The approved Benziger printing's punctuation is retained. "
    "The difference marks phrasing and does not change the words."
)
RETAINED_SITES = (
    ("ordinarium.iudica-me", "w038"),
    ("ordinarium.iudica-me", "w050"),
    ("ordinarium.misereatur", "w016"),
)
METHOD = (
    "Read word by word from the page image of the Benziger Brothers 1962 Editio iuxta "
    "typicam, which the Missal witness below transcribes, and collated against the other "
    "witnesses: zero substantive divergence. All accidental variants are declared in the "
    "apparatus."
)
PATTERN = rf"^{DIAGNOSTIC}$"


def core_path(text):
    return ROOT / ("texts/" + text.replace(".", "/", 1) + ".json")


def core(text):
    return json.loads(core_path(text).read_bytes())


def predecessor(relative):
    return json.loads(before_foot_communion_bytes(relative, (ROOT / relative).read_bytes()))


def words(doc):
    return [word for segment in doc["segments"] for word in segment.get("words", [])]


def printed_tokens(text):
    lines = (ROOT / "witnesses" / text / "mr.txt").read_text(encoding="utf-8").splitlines()
    return " ".join(line for line in lines if not line.startswith("#")).split()


def test_successor_names_exactly_the_changed_files_and_texts():
    assert tuple(sorted(DATA["texts"])) == TEXTS
    for text in TEXTS:
        assert DATA["texts"][text] == core_path(text).relative_to(ROOT).as_posix()
        assert DATA["texts"][text] in DATA["files"]
    assert DATA["new_files"] == ["witnesses/ordinarium.misereatur-tui/apparatus.json"]
    assert len(DATA["ledger_rows"]) == 4
    assert DATA["graph_use"]["row"]["id"] == "use.ordinarium.qui-dixisti.mr1962"
    assert sorted(DATA["layer_frames"]) == sorted(
        f"languages/{language}/texts/ordinarium/{name}.json"
        for language in ("en", "pl")
        for name in ("introibo", "iudica-me", "misereatur-tui")
    )


@pytest.mark.parametrize("relative", sorted(DATA["files"]))
def test_every_changed_file_inverts_to_its_exact_predecessor(relative):
    rule = DATA["files"][relative]
    raw = (ROOT / relative).read_bytes()
    assert hashlib.sha256(before_arrow_bytes(relative, raw)).hexdigest() == rule["after_sha256"]
    previous = before_foot_communion_bytes(relative, raw)
    assert hashlib.sha256(previous).hexdigest() == rule["before_sha256"] != rule["after_sha256"]
    assert before_foot_communion_bytes(relative, previous) == previous, "a chain may reach it twice"
    if "layout" in rule:
        current = json.loads(raw)
        saved = deepcopy(current)
        assert before_foot_communion_object(relative, current) == json.loads(previous)
        assert current == saved, "the actual object is never rewritten"
        older = json.loads(previous)
        assert before_foot_communion_object(relative, older) is older
    assert (ROOT / relative).read_bytes() == raw, "the actual source is never rewritten"


@pytest.mark.parametrize("text", TEXTS)
def test_current_core_inverts_to_its_registered_bytes(text):
    raw = core_path(text).read_bytes()
    comparison = before_foot_communion_core_bytes(text, raw)
    assert comparison != raw
    assert hashlib.sha256(comparison).hexdigest() == REGISTERED[text]
    assert core_path(text).read_bytes() == raw


@pytest.mark.parametrize("text", TEXTS)
def test_the_latin_words_are_unchanged(text):
    current = core(text)
    previous = json.loads(before_foot_communion_core_bytes(text, core_path(text).read_bytes()))
    changed = {word for name, word, _, _ in PRINTED if name == text}
    assert [w["id"] for w in words(current)] == [w["id"] for w in words(previous)]
    for new, old in zip(words(current), words(previous), strict=True):
        if new["id"] in changed:
            assert new.get("post") != old.get("post")
        assert {k: v for k, v in new.items() if k != "post"} == {
            k: v for k, v in old.items() if k != "post"
        }
        assert new["id"] in changed or new == old
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


def test_thirty_rubrics_in_all():
    # Thirteen at the foot of the altar (the two new ones included), seventeen at Communion.
    assert sum(len(rubrics) for rubrics in RUBRICS.values()) == 30


@pytest.mark.parametrize("text,rubric,follows,precedes,before,after", MINTS)
def test_ministri_respondent_stands_where_the_page_prints_it(
    text, rubric, follows, precedes, before, after
):
    current = core(text)
    previous = json.loads(before_foot_communion_core_bytes(text, core_path(text).read_bytes()))
    segments = current["segments"]
    index = [s["id"] for s in segments].index(rubric)
    assert segments[index] == {"id": rubric, "type": "rubric", "text": MINISTRI}
    if follows is None:
        assert index == 0
    else:
        assert segments[index - 1]["words"][-1]["id"] == follows
    assert segments[index + 1]["words"][0]["id"] == precedes
    assert segments[index + 1]["speaker"] == "minister"
    assert previous["ids"]["segments"]["next"] == before == int(rubric[1:])
    assert current["ids"]["segments"]["next"] == after
    old = {s["id"]: s for s in previous["segments"]}
    assert [s["id"] for s in segments if s["id"] != rubric] == list(old)
    for language, narrative in NARRATIVES.items():
        relative = f"languages/{language}/texts/{text.replace('.', '/', 1)}.json"
        layer = json.loads((ROOT / relative).read_bytes())
        assert list(layer["segments"]) == [s["id"] for s in segments]
        assert layer["segments"][rubric] == {"narrative": narrative}
        older = predecessor(relative)
        assert rubric not in older["segments"]
        assert before_foot_communion_layer_frame(layer) == older
        assert before_foot_communion_layer(layer) == older


@pytest.mark.parametrize("text,word,printed,token", PRINTED)
def test_punctuation_reads_as_printed_and_the_apparatus_records_the_others(
    text, word, printed, token
):
    doc = core(text)
    ids = [w["id"] for w in words(doc)]
    (current,) = [w for w in words(doc) if w["id"] == word]
    assert current["form"] + current.get("post", "") == printed
    assert printed_tokens(text)[ids.index(word)] == token
    apparatus = json.loads((ROOT / "witnesses" / text / "apparatus.json").read_bytes())
    entries = [e for e in apparatus["adjudicated"] if e["at"] == word]
    assert len(entries) == 1 and entries[0]["ours"] == printed
    assert entries[0]["class"] == "punctuation"
    assert "mr" not in entries[0]["witnesses"] and "do" in entries[0]["witnesses"]
    assert "Benziger" in entries[0]["ruling"] and "Vatican" in entries[0]["ruling"]
    source = doc["editorial"]["source"]
    assert source["method"] == METHOD
    assert source["apparatus"] == f"witnesses/{text}/apparatus.json"


@pytest.mark.parametrize("text,word", RETAINED_SITES)
def test_retained_rulings_describe_the_printed_page(text, word):
    apparatus = json.loads((ROOT / "witnesses" / text / "apparatus.json").read_bytes())
    (entry,) = [e for e in apparatus["adjudicated"] if e["at"] == word]
    assert entry["ruling"].startswith(RETAINED)
    assert "with DO" not in entry["ruling"]
    ids = [w["id"] for w in words(core(text))]
    assert printed_tokens(text)[ids.index(word)] == entry["ours"]


def test_core_notes_and_introductions_state_the_1962_rule():
    introibo = core("ordinarium.introibo")["editorial"]["notes"]
    assert "through Maundy Thursday inclusive" in introibo and "Holy Saturday" not in introibo
    iudica = core("ordinarium.iudica-me")["editorial"]["notes"]
    assert "the do header notes it" not in iudica and "Good Friday has no Mass" in iudica
    misereatur = core("ordinarium.misereatur")["editorial"]["notes"]
    assert "inside the word" not in misereatur
    for language in ("pl", "en"):
        relative = f"languages/{language}/texts/ordinarium/iudica-me.json"
        about = json.loads((ROOT / relative).read_bytes())["about"]
        assert "Adiutórium" in about and about != predecessor(relative)["about"]


def test_printed_basis_binds_the_page_already_bound():
    graph = json.loads((ROOT / "bibliography/graph.json").read_bytes())
    uses = {use["id"]: use for use in graph["uses"]}
    use = uses["use.ordinarium.qui-dixisti.mr1962"]
    twin = uses["use.ordinarium.fili-dei-vivi.mr1962"]
    assert use == DATA["graph_use"]["row"]
    assert use["evidence_sha256"] == twin["evidence_sha256"]
    assert use["locator"] == twin["locator"] and list(use) == list(twin)
    for key in ("edition", "digital_item", "role", "claim", "decision"):
        assert use[key] == twin[key]
    method = core("ordinarium.qui-dixisti")["editorial"]["source"]["method"]
    assert method == METHOD and "independent" not in method


def test_requiem_assembly_binds_the_current_qui_dixisti_body():
    assert target_errors(ROOT) == []
    relative = "checks/requiem_assembly.py"
    previous = before_foot_communion_bytes(relative, (ROOT / relative).read_bytes())
    assert TARGETS["ordinarium.qui-dixisti"].encode() not in previous


def test_changed_ledger_sites_return_to_working():
    for change in DATA["ledger_rows"]:
        ledger = json.loads((ROOT / change["relative"]).read_bytes())
        rows = [row for row in ledger["sites"] if row["site"] == change["site"]]
        assert rows == [change["after"]] == [ledger["sites"][change["index"]]]
        assert change["after"]["review"] == "working"
        assert change["after"]["origin"] == change["before"]["origin"]
        assert change["after"]["target_sha256"] == change["before"]["target_sha256"]
        assert change["after"]["source_sha256"] != change["before"]["source_sha256"]
        assert current_foot_communion_row(change["before"]) == change["after"]
    unrelated = {"site": "orationes.ave-maria.s01.pl"}
    assert current_foot_communion_row(unrelated) is unrelated


@pytest.mark.parametrize("fault", ("rubric-byte", "provenance", "word", "appended"))
def test_inverse_rejects_any_other_current_bytes(fault):
    text = "ordinarium.qui-dixisti"
    raw = core_path(text).read_bytes()
    if fault == "rubric-byte":
        changed = raw.replace(b"neque dicitur pr", b"nec dicitur pr", 1)
    elif fault == "provenance":
        changed = raw.replace(
            b'"sources": ["editorial", "mr"]', b'"sources": ["editorial", "do", "mr"]', 1
        )
    elif fault == "word":
        changed = raw.replace(b'"post": ":"', b'"post": ";"', 1)
    else:
        changed = raw + b"\n"
    assert changed != raw
    with pytest.raises(AssertionError, match=PATTERN):
        before_foot_communion_core_bytes(text, changed)
    comparison = before_foot_communion_core_bytes(text, raw)
    assert hashlib.sha256(comparison).hexdigest() == REGISTERED[text]


@pytest.mark.parametrize("fault", ("rubric", "word", "sources", "order"))
def test_object_inverse_rejects_any_other_current_object(fault):
    text = "ordinarium.misereatur-tui"
    current = core(text)
    if fault == "rubric":
        current["segments"][0]["text"] = "Minister respondet:"
    elif fault == "word":
        current["segments"][3]["words"][0]["post"] = "."
    elif fault == "sources":
        current["editorial"]["segments"]["s05"]["analysis"]["sources"] = ["editorial"]
    else:
        current["segments"][0], current["segments"][1] = (
            current["segments"][1],
            current["segments"][0],
        )
    with pytest.raises(AssertionError, match=PATTERN):
        before_foot_communion_core_object(text, current)


def test_states_without_the_changes_pass_and_partial_changes_are_rejected():
    relative = "languages/pl/translation-provenance.json"
    raw = (ROOT / relative).read_bytes()
    previous = before_foot_communion_bytes(relative, raw)
    older = previous + b" "
    assert before_foot_communion_bytes(relative, older) is older, "an older chain state passes"
    first = DATA["files"][relative]["raw_inverse"][0]
    partial = raw.replace(first["after"].encode(), first["before"].encode(), 1)
    assert partial not in (raw, previous)
    with pytest.raises(AssertionError, match=PATTERN):
        before_foot_communion_bytes(relative, partial)
    value = json.loads(previous)
    value["status"] = "older"
    assert before_foot_communion_object(relative, value) is value
    current = json.loads(raw)
    current["status"] = "faulted"
    with pytest.raises(AssertionError, match=PATTERN):
        before_foot_communion_object(relative, current)


def test_frames_keep_unrelated_faults_for_the_older_oracle():
    relative = "languages/en/texts/ordinarium/introibo.json"
    layer = json.loads((ROOT / relative).read_bytes())
    layer["segments"]["s04"]["translation"] += " Extra."
    framed = before_foot_communion_layer_frame(layer)
    assert framed["segments"]["s04"]["translation"].endswith(" Extra.")
    assert "s06" not in framed["segments"]
    layer["segments"]["s06"]["narrative"] = "The server answers."
    with pytest.raises(AssertionError, match=PATTERN):
        before_foot_communion_layer_frame(layer)


def test_graph_inverse_removes_only_the_new_use():
    graph = json.loads((ROOT / "bibliography/graph.json").read_bytes())
    saved = deepcopy(graph)
    previous = before_foot_communion_graph(before_arrow_graph(graph))
    added = DATA["graph_use"]["row"]["id"]
    assert graph == saved and previous is not graph
    assert [u["id"] for u in previous["uses"]] == [
        u["id"] for u in graph["uses"] if u["id"] != added
    ]
    raw = (ROOT / "bibliography/graph.json").read_bytes()
    assert previous == json.loads(before_foot_communion_bytes("bibliography/graph.json", raw))
    assert before_foot_communion_graph(previous) is previous, "a chain may reach it twice"
    changed = deepcopy(graph)
    changed["uses"][DATA["graph_use"]["index"]]["verified_on"] = "2026-09-25"
    with pytest.raises(AssertionError, match=rf"^{GRAPH_DIAGNOSTIC}$"):
        before_foot_communion_graph(changed)
    moved = deepcopy(graph)
    moved["uses"].append(moved["uses"].pop(DATA["graph_use"]["index"]))
    with pytest.raises(AssertionError, match=rf"^{GRAPH_DIAGNOSTIC}$"):
        before_foot_communion_graph(moved)


def test_unrelated_values_pass_through_untouched():
    raw = core_path("ordinarium.confiteor").read_bytes()
    assert before_foot_communion_core_bytes("ordinarium.confiteor", raw) is raw
    value = json.loads(raw)
    assert before_foot_communion_core_object("ordinarium.confiteor", value) is value
    layer = {"language": "pl", "text": "ordinarium.confiteor"}
    assert before_foot_communion_layer(layer) is layer
    assert before_foot_communion_layer_frame(layer) is layer

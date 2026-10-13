"""The Easter Vigil's sung Lauds preserve their separate Office identity."""

import json
import shutil
from pathlib import Path

import pytest

from build_reader.bibliography import load, validate
from checks import delivery
from checks.attribute import propose
from checks.delivery import check_doc, derive
from checks.interlinear import alignment_by_word
from checks.interlinear import check as check_alignment
from checks.language_packs import check_core, check_layer
from checks.lexicon import check_paradigm, check_text_against_lexicon, lint_lemmata
from checks.office import CANTICUM, PSALMUS, TEXTS
from checks.participation import derive as participation
from checks.participation import unknown_genus
from checks.raw_binding import BindingError, resolve_binding
from checks.translation_provenance import protected

ROOT = Path(__file__).resolve().parent.parent


def read(relative):
    return json.loads((ROOT / relative).read_text())


def core(text_id):
    category, slug = text_id.split(".", 1)
    return read(f"texts/{category}/{slug}.json")


def layer(text_id, language):
    category, slug = text_id.split(".", 1)
    return read(f"languages/{language}/texts/{category}/{slug}.json")


@pytest.mark.parametrize(("text_id", "words", "segments"), [(PSALMUS, 81, 9), (CANTICUM, 181, 17)])
def test_complete_latin_and_both_realizations(text_id, words, segments):
    doc = core(text_id)
    ids = [w["id"] for s in doc["segments"] for w in s["words"]]
    assert len(doc["segments"]) == segments
    assert ids == [f"w{n:03d}" for n in range(1, words + 1)]
    assert check_core(doc) == []
    for language in ("pl", "en"):
        target = layer(text_id, language)
        assert set(target["words"]) == set(ids)
        assert set(target["segments"]) == {s["id"] for s in doc["segments"]}
        category, slug = text_id.split(".", 1)
        assert (
            check_layer(doc, target, ROOT / f"languages/{language}/texts/{category}/{slug}.json")
            == []
        )
        assert check_alignment(doc, target) == []
        aligned = alignment_by_word(target)
        assert all(target["words"][wid].get("gloss") or wid in aligned for wid in ids)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_actual_shared_and_zero_realizations_reject_dropped_and_duplicate_tokens(language):
    doc = core(CANTICUM)
    target = layer(CANTICUM, language)
    groups = [a for s in target["segments"].values() for a in s.get("alignments", [])]
    assert any("gloss" in a for a in groups)
    if language == "pl":
        assert any("reason" in a and "gloss" not in a for a in groups)
    else:
        assert not any("reason" in a for a in groups)
    shared = next(a for a in groups if "gloss" in a)
    target["words"][shared["words"][0]]["gloss"] = "duplicate"
    assert check_alignment(doc, target)
    target = layer(CANTICUM, language)
    direct = next(wid for wid, row in target["words"].items() if row.get("gloss"))
    target["words"][direct].pop("gloss")
    assert check_alignment(doc, target)


@pytest.mark.parametrize("text_id", sorted(TEXTS))
def test_source_reprises_and_exact_protected_polish(text_id):
    doc = core(text_id)
    target = layer(text_id, "pl")
    if text_id == PSALMUS:
        assert doc["segments"][5]["verse"] == 5
        assert "verses 5–6" in doc["editorial"]["source"]["method"]
        assert [w["form"] for w in doc["segments"][0]["words"]] == [
            w["form"] for w in doc["segments"][-1]["words"]
        ]
        protected_ids = ("s07", "s08")
    else:
        opening = doc["segments"][0]["words"] + doc["segments"][1]["words"]
        assert [w["form"] for w in opening] == [w["form"] for w in doc["segments"][-1]["words"]]
        protected_ids = ("s15", "s16")
    assert (
        target["segments"][protected_ids[0]]["translation"]
        == "Chwała Ojcu i Synowi, i Duchowi Świętemu."
    )
    assert (
        target["segments"][protected_ids[1]]["translation"]
        == "Jak była na początku, teraz i zawsze, i na wieki wieków. Amen."
    )
    for s in doc["segments"]:
        assert protected(text_id, "pl", s["id"]) == (s["id"] in protected_ids)
        assert not protected(text_id, "en", s["id"])


@pytest.mark.parametrize("text_id", sorted(TEXTS))
def test_sung_office_has_no_invented_low_mass_or_participation(text_id):
    doc = core(text_id)
    assert propose(doc) == {}
    assert unknown_genus(doc) is None
    assert check_doc(doc) == ([], len(doc["segments"]))
    for s in doc["segments"]:
        assert "speaker" not in s and "voice" not in s
        assert participation(doc, s) == {}
        assert "lecta" not in derive(doc, s)
        expected = {"voice": "cantus"}
        if text_id == CANTICUM and s["id"] in ("s01", "s02"):
            expected["speaker"] = "sacerdos" if s["id"] == "s01" else "schola"
        assert derive(doc, s) == {"cantu": expected}


@pytest.mark.parametrize("change", ["base", "reprise", "voice", "wrong-id"])
def test_wrong_office_claims_are_rejected(change):
    doc = core(CANTICUM)
    if change == "base":
        doc["segments"][0]["speaker"] = "sacerdos"
    elif change == "reprise":
        doc["segments"][-1]["delivery"]["cantu"]["speaker"] = "schola"
    elif change == "voice":
        doc["segments"][2]["delivery"]["cantu"]["voice"] = "clara"
    else:
        doc["id"] = "proprium.unrelated-laudes-canticum"
        assert unknown_genus(doc)
    assert check_doc(doc)[0]


@pytest.mark.parametrize("write", [False, True])
@pytest.mark.parametrize(("field", "value"), [("speaker", "sacerdos"), ("voice", "clara")])
def test_delivery_command_rejects_unestablished_base_without_rewriting(
    tmp_path, monkeypatch, capsys, write, field, value
):
    doc = core(CANTICUM)
    doc["segments"][2][field] = value
    target = tmp_path / "texts/proprium/example.json"
    target.parent.mkdir(parents=True)
    before = json.dumps(doc).encode()
    target.write_bytes(before)
    monkeypatch.setattr(delivery, "ROOT", tmp_path)
    assert delivery.run(write=write) == 1
    assert target.read_bytes() == before
    output = capsys.readouterr().out
    assert "no established low-Mass base" in output
    assert "delivery: OK" not in output


def test_compound_without_a_number_is_not_an_indeclinable_noun():
    lex = read("lexicon/lemmata.json")["entries"]
    entry = lex["iusiurandum"]
    assert entry["head"] == "iusiurándum, iurisiurándi"
    assert "decl" not in entry and "decl_alt" not in entry
    assert lint_lemmata({"iusiurandum": entry}) == []
    assert check_paradigm({"iusiurandum": entry}) == []
    assert check_text_against_lexicon(core(CANTICUM), lex) == []
    ordinary = dict(entry, head="donum, doni")
    assert check_paradigm({"donum": ordinary})
    assert check_paradigm({"iusiurandum-imitation": entry})


@pytest.mark.parametrize(
    "numeral", [{"decl": 2}, {"decl": 3}, {"decl": 2, "decl_alt": 3}, {"decl_alt": 3}]
)
def test_compound_rejects_single_and_alternative_numbers_at_both_levels(numeral):
    lex = read("lexicon/lemmata.json")["entries"]
    entry = dict(lex["iusiurandum"], **numeral)
    assert lint_lemmata({"iusiurandum": entry})
    assert check_paradigm({"iusiurandum": entry})
    doc = core(CANTICUM)
    token = next(w for s in doc["segments"] for w in s["words"] if w["lemma"] == "iusiurandum")
    token["morph"].update(numeral)
    assert check_text_against_lexicon(doc, lex)


def test_reviewed_lexical_distinctions():
    neutral = read("lexicon/lemmata.json")["entries"]
    pl = read("languages/pl/lexicon.json")["entries"]
    en = read("languages/en/lexicon.json")["entries"]
    assert neutral["crepito"]["head"] == "crépito, crepitáre"
    assert all(s.startswith("to ") for name in ("crepito", "spiro") for s in en[name]["senses"])
    assert pl["chorus"]["senses"] == ["chór", "taniec", "zespół"]
    assert en["chorus"]["senses"] == ["choir", "dance", "company"]
    assert pl["cymbalum"]["senses"] == ["cymbał (talerz perkusyjny)"]


@pytest.mark.parametrize(
    ("text_id", "word_id"),
    [
        ("orationes.te-deum", "w045"),
        ("proprium.dedicatio-archibasilicae-sanctissimi-salvatoris-graduale", "w015"),
        ("proprium.sancti-bartholomaei-apostoli-alleluia", "w006"),
        ("proprium.sancti-matthaei-apostoli-et-evangelistae-alleluia", "w006"),
    ],
)
def test_collective_chorus_consumers_are_not_changed_to_dance(text_id, word_id):
    doc = core(text_id)
    token = next(w for s in doc["segments"] for w in s["words"] if w["id"] == word_id)
    assert token["lemma"] == "chorus"
    for language, forbidden in (("pl", "taniec"), ("en", "dance")):
        target = layer(text_id, language)
        gloss = target["words"].get(word_id, {}).get("gloss")
        gloss = gloss or alignment_by_word(target).get(word_id, {}).get("gloss")
        assert gloss
        assert forbidden not in gloss


def test_office_component_order_preserves_the_seven_mass_components():
    assembly = read("formularies/temporale/vigilia-paschalis.json")
    roles = [c["role"] for c in assembly["components"]]
    assert roles == [
        "collecta",
        "epistola",
        "alleluia",
        "evangelium",
        "secreta",
        "praefatio",
        "laudes-psalmus",
        "laudes-canticum",
        "postcommunio",
    ]
    assert [c["text"] for c in assembly["components"] if c["role"].startswith("laudes-")] == [
        PSALMUS,
        CANTICUM,
    ]


@pytest.mark.parametrize(
    "change", ["wrong-edition", "unknown-segment", "false-transcript", "false-selected"]
)
def test_source_graph_rejects_actual_source_error_mutants(change):
    graph, languages = load(ROOT)
    if change in ("wrong-edition", "unknown-segment"):
        use = next(u for u in graph["uses"] if u.get("address", {}).get("text") == PSALMUS)
        if change == "wrong-edition":
            use["edition"] = "edition.lewis-short.1879"
        else:
            use["address"] = {"kind": "segment", "text": PSALMUS, "segment": "s99"}
    elif change == "false-transcript":
        witness = next(w for w in graph["witnesses"] if w["text"] == PSALMUS)
        witness["transcription_sha256"] = "0" * 64
    else:
        collation = next(c for c in graph["collations"] if c["text"] == PSALMUS)
        collation["selected_text_sha256"] = "0" * 64
    assert validate(ROOT, graph, languages)


@pytest.mark.parametrize("text_id", sorted(TEXTS))
def test_digital_recension_is_exactly_bound_and_is_not_selected_latin(text_id, tmp_path):
    witness = ROOT / "witnesses" / text_id / "do.txt"
    reading = resolve_binding(witness, ROOT)
    assert reading is not None and reading.fragments
    latin = " ".join(w["form"] for s in core(text_id)["segments"] for w in s["words"])
    assert reading.text != latin
    if text_id == PSALMUS:
        assert "in sanctis eius" in reading.text
        assert "in sanctuário eius" in latin
        assert "in cýmbalis iubilatiónis" in reading.text
        assert "cýmbalis crepitántibus" in latin
    registry = read("witnesses/raw/bindings.json")
    binding = next(
        b for b in registry["bindings"].values() if b["witness"] == f"witnesses/{text_id}/do.txt"
    )
    archive = registry["archives"][binding["evidence"][0]["archive"]]
    for relative in ("witnesses/raw/bindings.json", archive["path"], binding["witness"]):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    raw = tmp_path / archive["path"]
    raw.write_text(raw.read_text().replace("Benedíctus", "Corruptus", 1))
    with pytest.raises(BindingError):
        resolve_binding(tmp_path / binding["witness"], tmp_path)

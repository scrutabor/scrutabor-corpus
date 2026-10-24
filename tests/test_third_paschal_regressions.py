"""Bounded III Sunday readings and source seams, not general grammar rules."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from gospel_delivery_fixture import current_gospel_selected_hash
from provenance_successor_fixture import assert_protection_scope

from build_reader import bibliography, store
from build_reader.bibliography_bindings import digest, selected_text, transcript_digest
from checks import english, interlinear
from checks.apparatus import derived_summary
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "proprium.dominica-iii-post-pascha-"
LATIN = {
    "introitus": "92ef2460f05968cb9bf35a295dda114f93f5177a5552030c6893e5ef2f745ea4",
    "collecta": "6ad48177cf37f20faeac64107dd9fd908ac5906aaef67bd90bfda09fb6d62bec",
    "epistola": "3a6bc344306e65c7e695a3e4f537b3bb87c37695f7e771a4ce0860f8f6782991",
    "alleluia": "3da8d7fcbb8b8011b54d214e9cf9f998426a3dbf4c2b7f8f097110ac889008db",
    "evangelium": "078f6767f9b1f1ff094a9c8ed96fb1b3a2335ee2c06f3c4a030de24ffc484153",
    "offertorium": "d21e516c52387431bada82bd9749006662802fb70318ec6cfbe710e978a64395",
    "secreta": "55b4dc53902675b3a26b0f36de3132cae43bdd18b0be7030eb47d69b8a7a53c3",
    "communio": "10517e930b5a5e19eb9a00493b23c5f28a12cf518416fc02599dfac555f4464a",
    "postcommunio": "aa59887463ffc0c96ff9439bac4c020adcbf95f451b635bf4a5c4b9092333975",
}
# These contextual groups are deliberately local, not preferred synonyms elsewhere.
GROUPS = [
    # V Sunday after Easter audit successor (2026-10-20): date glóriam are word
    # captions (give | glory) and laudi eius one group, as the V Sunday and II Sunday after
    # Epiphany Introits read the identical psalm verse; the verse keeps its wording (PROSE).
    ("introitus", "en", 13, 14, 13, "to His praise"),
    ("introitus", "en", 66, 67, 66, "to His praise"),
    ("collecta", "pl", 17, 19, 19, "z wyznania noszą miano chrześcijan"),
    ("epistola", "pl", 33, 37, 37, "oceniając was po dobrych uczynkach"),
    ("epistola", "en", 33, 37, 37, "judging you by your good works"),
    ("secreta", "pl", 1, 5, 5, "Niech przez te tajemnice będzie nam dane, Panie"),
    ("secreta", "en", 1, 5, 5, "By these mysteries, Lord, may it be granted to us"),
    ("postcommunio", "pl", 7, 10, 9, "niech odnawiają nas duchowym pokarmem"),
    ("collecta", "en", 41, 45, 43, "who lives and reigns with You"),
    ("secreta", "en", 20, 24, 22, "who lives and reigns with You"),
    ("postcommunio", "en", 22, 26, 24, "who lives and reigns with You"),
]
# Successor of the 2026-10-16 Polish groups (2026-10-20 audit): the word layer glosses each word,
# as the V Sunday Introit does for the identical Latin; the verse keeps its wording (PROSE below).
TOKENS = [
    ("introitus", 11, ["oddajcie", "chwałę", "uwielbieniu", "Jego"]),
    ("introitus", 64, ["oddajcie", "chwałę", "uwielbieniu", "Jego"]),
    ("postcommunio", 12, ["cielesną", "niech chronią", "pomocą"]),
]
PROSE = [
    ("introitus", "pl", "oddajcie Mu chwałę, wysławiając Go", 2),
    ("introitus", "en", "make His praise glorious", 2),
    ("collecta", "pl", "z wyznania noszą miano chrześcijan", 1),
    ("epistola", "pl", "oceniając was po dobrych uczynkach", 1),
    ("epistola", "en", "judging you by your good works", 1),
    ("secreta", "pl", "Niech przez te tajemnice będzie nam dane, Panie", 1),
    ("secreta", "en", "may it be granted to us", 1),
    ("postcommunio", "pl", "chronią nas, niosąc pomoc ciału", 1),
    ("collecta", "en", "who lives and reigns with You", 1),
    ("postcommunio", "en", "who lives and reigns with You", 1),
    (
        "introitus",
        "en",
        "Glory be to the Father, and to the Son, and to the Holy Spirit. "
        "As it was in the beginning, is now, and ever shall be, world without end. Amen.",
        1,
    ),
]
RELATIVES = [("collecta", "w041"), ("secreta", "w020"), ("postcommunio", "w022")]
COMPOSITES = {
    "introitus": (34, 298, "219", 17),
    "collecta": (34, 22, "xvii", 16),
    "secreta": (13, 22, "xvii", 15),
    "postcommunio": (15, 22, "xvii", 13),
}
PAGES = {
    22: "b511f3aa4016b387d2995b5089e15aa62593c04118052ef48dcc09352fcf769c",
    298: "ee8d1c45f6cc759518ae59a1dd047dfa80033904ba5ce1799fbaa2334df9ee55",
}
SOURCE_HASHES = {
    "introitus": "e13fa197788db161ecfa4e062d253872da662e6ad306553aafa8bc47b9eed96d",
    "collecta": "c8edae0d633dca70032f7e5d045a0e6ae515feaf4f85864937fe25aca281d266",
    "epistola": "d1bcb8696f3734c9c9870938534c480b53b149d6d58bc145dd4df9d62728dece",
    "secreta": "0e8e517e9ef0d49831b202aae1101d14fda5d57f67d2ecbc3e22b16aa3d6cf6e",
    "postcommunio": "03efa6620b7aac0f3f8dc099aac754a3d722dd18350afe71a1d88dacb929bd0c",
}
WORKING = [
    ("pl", "introitus"),
    ("pl", "collecta"),
    ("pl", "epistola"),
    ("pl", "secreta"),
    ("pl", "postcommunio"),
    ("en", "introitus"),
    ("en", "epistola"),
    ("en", "secreta"),
]
CONTEXT_NOTES = [("introitus", "pl"), ("introitus", "en"), ("epistola", "pl"), ("epistola", "en")]


def load(relative):
    return json.loads((ROOT / relative).read_bytes())


def reading(role, lang):
    return store.core(ROOT, PREFIX + role), store.raw_layer(ROOT, lang, PREFIX + role)


def words(doc):
    return {w["id"]: w for s in doc["segments"] for w in s.get("words", [])}


def assert_group(doc, layer, first, last, anchor, gloss):
    ids = [f"w{number:03d}" for number in range(first, last + 1)]
    segment = next(s for s in doc["segments"] if s["id"] == "s01")
    ordered = [w["id"] for w in segment["words"]]
    start = ordered.index(ids[0])
    assert ordered[start : start + len(ids)] == ids
    selected = [
        g for g in layer["segments"]["s01"].get("alignments", []) if set(g["words"]) & set(ids)
    ]
    assert selected == [{"words": ids, "anchor": f"w{anchor:03d}", "gloss": gloss}]
    assert all("gloss" not in layer["words"][wid] for wid in ids)
    assert interlinear.check(doc, layer) == []


@pytest.mark.parametrize("role,lang,first,last,anchor,gloss", GROUPS)
def test_complete_contextual_groups(role, lang, first, last, anchor, gloss):
    doc, layer = reading(role, lang)
    assert_group(doc, layer, first, last, anchor, gloss)
    if role == "epistola":
        assert words(doc)["w036"]["lemma"] == "vos"
        assert words(doc)["w036"]["morph"]["case"] == "acc"
    if role == "secreta" and first == 1:
        assert words(doc)["w005"]["morph"]["voice"] == "pass"


@pytest.mark.parametrize("role,lang,first,last,anchor,gloss", GROUPS)
@pytest.mark.parametrize("damage", ["meaning", "member", "anchor", "duplicate", "direct"])
def test_group_damage_is_rejected_then_original_restored(
    role, lang, first, last, anchor, gloss, damage
):
    doc, good = reading(role, lang)
    assert_group(doc, good, first, last, anchor, gloss)
    bad = deepcopy(good)
    wid = f"w{first:03d}"
    group = next(g for g in bad["segments"]["s01"]["alignments"] if wid in g["words"])
    if damage == "meaning":
        if role == "introitus":
            group["gloss"] = "oddajcie Mu cześć" if lang == "pl" else "praise Him"
        elif role == "collecta" and lang == "pl":
            group["gloss"] = "sami nazywają się chrześcijanami"
        elif role == "epistola":
            group["gloss"] = (
                "oceniając dobre uczynki" if lang == "pl" else "considering the good works"
            )
        elif role == "secreta" and first == 1:
            group["gloss"] = (
                "Te tajemnice dają nam, Panie"
                if lang == "pl"
                else "These mysteries grant us, O Lord"
            )
        elif role == "postcommunio" and lang == "pl":
            group["gloss"] = "niech karmią nas" if first == 7 else "niech chronią nasze ciała"
        else:
            group["gloss"] = "You live and reign"
    elif damage == "member":
        group["words"].remove(wid)
    elif damage == "anchor":
        group["anchor"] = next(member for member in group["words"] if member != group["anchor"])
    elif damage == "duplicate":
        bad["segments"]["s01"]["alignments"].append(deepcopy(group))
    else:
        bad["words"][wid]["gloss"] = "duplicated realization"
    assert bad != good
    with pytest.raises(AssertionError):
        assert_group(doc, bad, first, last, anchor, gloss)
    assert_group(doc, good, first, last, anchor, gloss)


def assert_tokens(doc, layer, first, glosses):
    ids = [f"w{first + offset:03d}" for offset in range(len(glosses))]
    segment = next(s for s in doc["segments"] if s["id"] == "s01")
    ordered = [w["id"] for w in segment["words"]]
    start = ordered.index(ids[0])
    assert ordered[start : start + len(ids)] == ids
    groups = layer["segments"]["s01"].get("alignments", [])
    assert not [g for g in groups if set(g["words"]) & set(ids)]
    assert [layer["words"][wid].get("gloss") for wid in ids] == glosses
    assert interlinear.check(doc, layer) == []


@pytest.mark.parametrize("role,first,glosses", TOKENS)
def test_polish_words_are_glossed_one_by_one(role, first, glosses):
    doc, layer = reading(role, "pl")
    assert_tokens(doc, layer, first, glosses)
    if role == "postcommunio":
        assert words(doc)["w012"]["morph"]["pos"] == "adj"


@pytest.mark.parametrize("role,first,glosses", TOKENS)
@pytest.mark.parametrize("damage", ["meaning", "regroup", "missing", "overlap"])
def test_token_damage_is_rejected_then_original_restored(role, first, glosses, damage):
    doc, good = reading(role, "pl")
    assert_tokens(doc, good, first, glosses)
    bad = deepcopy(good)
    ids = [f"w{first + offset:03d}" for offset in range(len(glosses))]
    if damage == "meaning":
        bad["words"][ids[2 if role == "introitus" else 0]]["gloss"] = (
            "wysławiając Go" if role == "introitus" else "ciału"
        )
    elif damage == "regroup":
        for wid in ids:
            bad["words"][wid].pop("gloss")
        bad["segments"]["s01"].setdefault("alignments", []).append(
            {
                "words": ids,
                "anchor": ids[0] if role == "introitus" else ids[1],
                "gloss": "oddajcie Mu chwałę, wysławiając Go"
                if role == "introitus"
                else "niech chronią nas, niosąc pomoc ciału",
            }
        )
    elif damage == "missing":
        bad["words"][ids[-1]].pop("gloss")
    else:
        bad["segments"]["s01"].setdefault("alignments", []).append(
            {"words": ids[:2], "anchor": ids[0], "gloss": " ".join(glosses[:2])}
        )
    assert bad != good
    with pytest.raises(AssertionError):
        assert_tokens(doc, bad, first, glosses)
    assert_tokens(doc, good, first, glosses)


def assert_prose(layer, phrase, count):
    assert layer["segments"]["s01"]["translation"].count(phrase) == count


@pytest.mark.parametrize("role,lang,phrase,count", PROSE)
def test_complete_prose_retains_the_repaired_relation(role, lang, phrase, count):
    _, layer = reading(role, lang)
    assert_prose(layer, phrase, count)
    if role == "collecta" and lang == "pl":
        assert "temu imieniu" in layer["segments"]["s01"]["translation"]
    if role == "postcommunio" and lang == "pl":
        assert "odnawiają nas duchowym pokarmem" in layer["segments"]["s01"]["translation"]


@pytest.mark.parametrize("role,lang,phrase,count", PROSE)
def test_missing_prose_relation_is_rejected_and_original_restored(role, lang, phrase, count):
    _, good = reading(role, lang)
    assert_prose(good, phrase, count)
    bad = deepcopy(good)
    bad["segments"]["s01"]["translation"] = bad["segments"]["s01"]["translation"].replace(
        phrase, "", 1
    )
    assert bad != good
    with pytest.raises(AssertionError):
        assert_prose(bad, phrase, count)
    assert_prose(good, phrase, count)


def assert_relative(doc, layer, wid):
    assert words(doc)[wid]["lemma"] == "qui"
    assert layer["words"][wid]["gloss"] == "który"
    assert all(wid not in g["words"] for g in layer["segments"]["s01"].get("alignments", []))
    assert ", który z Tobą żyje i króluje" in layer["segments"]["s01"]["translation"]
    assert interlinear.check(doc, layer) == []


@pytest.mark.parametrize("role,wid", RELATIVES)
def test_polish_in_sentence_relative_is_lowercase(role, wid):
    assert_relative(*reading(role, "pl"), wid)


@pytest.mark.parametrize("role,wid", RELATIVES)
@pytest.mark.parametrize("bad_gloss", ["Który", "Ty żyjesz"])
def test_relative_case_or_person_regression_is_rejected(role, wid, bad_gloss):
    doc, good = reading(role, "pl")
    assert_relative(doc, good, wid)
    bad = deepcopy(good)
    bad["words"][wid]["gloss"] = bad_gloss
    with pytest.raises(AssertionError):
        assert_relative(doc, bad, wid)
    assert_relative(doc, good, wid)


def assert_latin(doc, role):
    # Pin only the sacred/ritual subject, not editorial metadata or morphology.
    assert digest(selected_text(doc)) == current_gospel_selected_hash(doc["id"], LATIN[role])


@pytest.mark.parametrize("role", LATIN)
def test_vernacular_and_source_metadata_edits_leave_selected_latin_unchanged(role):
    assert_latin(store.core(ROOT, PREFIX + role), role)


@pytest.mark.parametrize("role", LATIN)
def test_changed_sacred_word_is_rejected_then_original_restored(role):
    good = store.core(ROOT, PREFIX + role)
    assert_latin(good, role)
    bad = deepcopy(good)
    next(w for s in bad["segments"] for w in s.get("words", []))["form"] = "Verbum"
    with pytest.raises(AssertionError):
        assert_latin(bad, role)
    assert_latin(good, role)


def assert_composite(data, role, transcript, apparatus):
    text = PREFIX + role
    first, leaf, printed, entries = COMPOSITES[role]
    uses = {u["id"]: u for u in data["uses"]}
    witness = next(w for w in data["witnesses"] if w["id"] == f"witness.{text}.mr1962")
    suffix = "gloria-expansion" if role == "introitus" else "conclusion-expansion"
    common_id = f"use.{text}.{suffix}.mr1962"
    dependencies = [common_id]
    if role != "introitus":
        dependencies.append(f"use.{text}.oration-boundaries.mr1962")
    assert witness["source_dependencies"] == {"uses": sorted(dependencies), "raw_binding": None}
    assert witness["orthography_profile"] == "literal-printed-proper-common-composite"
    assert "not independent print editions" in witness["independence_basis"]
    assert witness["review"] == {"status": "pending"}
    assert witness["transcription_sha256"] == transcript_digest(transcript)
    primary = uses[f"use.{text}.mr1962"]
    assert "complete 1962 liturgical component selected here" not in primary["claim"]
    assert primary["decision"] == "RETAIN_WITH_CORRECTION"
    if role == "introitus":
        assert "does not print the full expanded" in primary["claim"]
    else:
        assert "not printed on this proper leaf" in primary["claim"]
    common = uses[common_id]
    assert common["edition"] == primary["edition"] == "edition.missale-romanum.1962-typica"
    assert common["digital_item"] == primary["digital_item"]
    assert common["role"] == "direct_approved_print"
    assert common["address"] == {"kind": "word", "text": text, "word": f"w{first:03d}"}
    assert common["locator"]["printed"] == "p. " + printed
    assert common["locator"]["scan"] == f"leaf n{leaf} / PDF p. {leaf + 1}"
    assert common["locator"]["page_url"].endswith(f"/page/n{leaf}/mode/1up")
    assert common["evidence_sha256"] == PAGES[leaf]
    assert "# composite-corrected:" in transcript and "# source-spans:" in transcript
    assert "# orthography: literal contributing-source" in transcript
    if role == "introitus":
        assert "semper: et in sǽcula" in transcript
        assert "# expansion-controls:" in transcript
    else:
        assert "Per Dominum nostrum Iesum Christum Filium tuum, qui" in transcript
        assert transcript.rstrip().endswith("Amen;")
    assert apparatus["summary"] == derived_summary(apparatus)
    assert apparatus["summary"]["entries"] == entries
    at = {entry["at"]: entry for entry in apparatus["adjudicated"]}
    if role == "introitus":
        expected = {"w048": ("semper,", "semper:")}
    else:
        last = {"collecta": 55, "secreta": 34, "postcommunio": 36}[role]
        expected = {
            f"w{first + 1:03d}": ("Dóminum", "Dominum"),
            f"w{first + 6:03d}": ("tuum:", "tuum,"),
            f"w{first + 7:03d}": ("Qui", "qui"),
            f"w{last:03d}": ("Amen.", "Amen;"),
        }
    for wid, (selected, literal) in expected.items():
        assert at[wid]["ours"] == selected
        assert at[wid]["witnesses"]["mr"] == literal


@pytest.mark.parametrize("role", COMPOSITES)
def test_proper_and_common_spans_are_honest_and_pending(role):
    transcript = (ROOT / "witnesses" / (PREFIX + role) / "mr.txt").read_text()
    apparatus = load(f"witnesses/{PREFIX}{role}/apparatus.json")
    assert_composite(load("bibliography/graph.json"), role, transcript, apparatus)


@pytest.mark.parametrize("role", COMPOSITES)
@pytest.mark.parametrize(
    "damage", ["blanket-claim", "dependency", "review", "edition", "raw", "apparatus"]
)
def test_source_scope_damage_is_rejected_and_original_restored(role, damage):
    good = load("bibliography/graph.json")
    transcript = (ROOT / "witnesses" / (PREFIX + role) / "mr.txt").read_text()
    apparatus = load(f"witnesses/{PREFIX}{role}/apparatus.json")
    assert_composite(good, role, transcript, apparatus)
    bad = deepcopy(good)
    bad_apparatus = deepcopy(apparatus)
    changed_transcript = transcript
    text = PREFIX + role
    primary = next(u for u in bad["uses"] if u["id"] == f"use.{text}.mr1962")
    witness = next(w for w in bad["witnesses"] if w["id"] == f"witness.{text}.mr1962")
    if damage == "blanket-claim":
        primary["claim"] = (
            "The proper page prints the complete 1962 liturgical component selected here."
        )
    elif damage == "dependency":
        witness["source_dependencies"]["uses"].pop()
    elif damage == "review":
        witness["review"] = {"status": "reviewed", "sha256": witness["transcription_sha256"]}
    elif damage == "edition":
        common = next(
            u for u in bad["uses"] if u["id"] == witness["source_dependencies"]["uses"][0]
        )
        common["edition"] = "edition.unrelated"
    elif damage == "raw":
        changed_transcript += "Unprinted addition.\n"
    else:
        first = COMPOSITES[role][0]
        wid = "w048" if role == "introitus" else f"w{first + 6:03d}"
        entry = next(e for e in bad_apparatus["adjudicated"] if e["at"] == wid)
        entry["witnesses"]["mr"] = entry["ours"]
    with pytest.raises(AssertionError):
        assert_composite(bad, role, changed_transcript, bad_apparatus)
    assert_composite(good, role, transcript, apparatus)


def test_all_nine_source_reviews_stay_pending_not_reader_approval():
    data = load("bibliography/graph.json")
    texts = {PREFIX + role for role in LATIN}
    witnesses = [w for w in data["witnesses"] if w["text"] in texts]
    collations = [c for c in data["collations"] if c["text"] in texts]
    assert len(witnesses) == 18 and len(collations) == 9
    assert all(w["review"] == {"status": "pending"} for w in witnesses)
    assert all(c["review"] == {"status": "pending"} for c in collations)
    projected = [e for e in bibliography.public_text_evidence(data)["texts"] if e["id"] in texts]
    assert len(projected) == 9
    assert all(e["witnesses"] == [] and "collation" not in e for e in projected)


def working_record(lang, role):
    text = PREFIX + role
    return next(
        r
        for r in load(f"languages/{lang}/translation-provenance.json")["sites"]
        if r["site"] == f"{text}.s01.{lang}"
    )


def assert_working(record, doc, layer, lang, role):
    segment = next(s for s in doc["segments"] if s["id"] == "s01")
    assert canonical_hash(source_payload(segment)) == SOURCE_HASHES[role]
    target = layer["segments"]["s01"]["translation"]
    expected_protection = (lang, role) == ("pl", "introitus")
    assert assert_protection_scope(doc["id"], lang, "s01", target) is expected_protection
    assert record == {
        "site": f"{PREFIX}{role}.s01.{lang}",
        "text": PREFIX + role,
        "segment": "s01",
        "language": lang,
        "familiar_core": expected_protection,
        "origin": "working-unsettled",
        "review": "working",
        "source_sha256": SOURCE_HASHES[role],
        "target_sha256": canonical_hash(layer["segments"]["s01"]["translation"]),
    }


@pytest.mark.parametrize("lang,role", WORKING)
def test_changed_prose_keeps_only_working_origin_and_exact_target_binding(lang, role):
    assert_working(working_record(lang, role), *reading(role, lang), lang, role)


@pytest.mark.parametrize("lang,role", WORKING)
@pytest.mark.parametrize("damage", ["source", "target", "origin", "review", "familiar"])
def test_working_record_cannot_reseal_rebind_or_keep_stale_target(lang, role, damage):
    doc, layer = reading(role, lang)
    good = working_record(lang, role)
    assert_working(good, doc, layer, lang, role)
    bad = deepcopy(good)
    if damage in {"source", "target"}:
        bad[damage + "_sha256"] = "0" * 64
    elif damage == "origin":
        bad["origin"] = "own"
    elif damage == "review":
        bad["review"] = "internally-reviewed"
    else:
        bad["familiar_core"] = not good["familiar_core"]
    assert bad != good
    with pytest.raises(AssertionError):
        assert_working(bad, doc, layer, lang, role)
    assert_working(good, doc, layer, lang, role)


def test_introit_protection_covers_only_the_formula_without_promoting_working_provenance():
    doc, layer = reading("introitus", "pl")
    original = deepcopy(layer)
    record = working_record("pl", "introitus")
    assert_working(record, doc, layer, "pl", "introitus")
    outside = deepcopy(layer)
    outside["segments"]["s01"]["translation"] = (
        "Próba przed. " + outside["segments"]["s01"]["translation"] + " Próba po."
    )
    outside_record = deepcopy(record)
    outside_record["target_sha256"] = canonical_hash(outside["segments"]["s01"]["translation"])
    assert outside != original and outside_record != record
    assert_working(outside_record, doc, outside, "pl", "introitus")
    damaged = deepcopy(layer)
    target = damaged["segments"]["s01"]["translation"]
    assert target.count("Chwała Ojcu") == 1
    damaged["segments"]["s01"]["translation"] = target.replace("Chwała Ojcu", "Chwała", 1)
    damaged_record = deepcopy(record)
    damaged_record["target_sha256"] = canonical_hash(damaged["segments"]["s01"]["translation"])
    assert damaged != original and damaged_record != record
    with pytest.raises(AssertionError, match="protected Gloria Patri"):
        assert_working(damaged_record, doc, damaged, "pl", "introitus")
    assert layer == original and working_record("pl", "introitus") == record
    assert_working(record, doc, layer, "pl", "introitus")


def assert_context_note(doc, layer, role, lang):
    wid = "w030" if role == "introitus" else "w048"
    assert words(doc)[wid]["lemma"] == ("mentior" if role == "introitus" else "creatura")
    fragments = {
        ("introitus", "pl"): ["mogą", "nieszczerej uległości", "możliwy", "nie jedyne znaczenie"],
        ("introitus", "en"): ["may", "insincere submission", "possible", "not the only meaning"],
        ("epistola", "pl"): ["króla", "namiestników", "W tym kontekście", "przez wzgląd na Boga"],
        ("epistola", "en"): ["king", "governors", "In this context", "for God’s sake"],
    }[role, lang]
    note = layer["words"][wid].get("explanation", "")
    assert all(fragment in note for fragment in fragments)
    literal = {
        ("introitus", "pl"): "kłamać",
        ("introitus", "en"): "will lie",
        ("epistola", "pl"): "stworzeniu",
        ("epistola", "en"): "human creature",
    }[role, lang]
    assert literal in interlinear.effective_gloss(layer, wid)


@pytest.mark.parametrize("role,lang", CONTEXT_NOTES)
def test_context_notes_qualify_without_replacing_literal_reading(role, lang):
    assert_context_note(*reading(role, lang), role, lang)


@pytest.mark.parametrize("role,lang", CONTEXT_NOTES)
@pytest.mark.parametrize("damage", ["absent", "exclusive"])
def test_lost_context_qualification_is_rejected_then_restored(role, lang, damage):
    doc, good = reading(role, lang)
    assert_context_note(doc, good, role, lang)
    bad = deepcopy(good)
    wid = "w030" if role == "introitus" else "w048"
    if damage == "absent":
        bad["words"][wid].pop("explanation")
    else:
        bad["words"][wid]["explanation"] = (
            "To jedyne możliwe znaczenie słowa."
            if lang == "pl"
            else "This is the only possible meaning."
        )
    with pytest.raises(AssertionError):
        assert_context_note(doc, bad, role, lang)
    assert_context_note(doc, good, role, lang)


def assert_pepererit(doc, pl, en):
    word = words(doc)["w124"]
    assert word["form"] == "pepérerit" and word["lemma"] == "pario"
    assert word["morph"] == {
        "pos": "verb",
        "mood": "ind",
        "number": "sg",
        "person": 3,
        "tense": "futperf",
        "voice": "act",
        "conj": 3,
    }
    assert doc["editorial"]["words"]["w124"]["analysis"] == {
        "confidence": "medium",
        "sources": ["editorial", "whitakers", "collatinus"],
        "review": "disputed",
    }
    assert "w124" in doc["localization"]["notes"]
    for layer, fragments in [
        (
            pl,
            [
                "przyszłym dokonanym trybu oznajmującego",
                "przeszłym dokonanym trybu łączącego",
                "pierwszą możliwość",
                "Obie",
            ],
        ),
        (
            en,
            ["future perfect indicative", "perfect subjunctive", "first possibility", "Both"],
        ),
    ]:
        note = layer["words"]["w124"].get("note", "")
        assert all(fragment in note for fragment in fragments)


def test_pepererit_keeps_plausible_parse_and_explicit_two_language_uncertainty():
    doc, pl = reading("evangelium", "pl")
    assert_pepererit(doc, pl, reading("evangelium", "en")[1])


@pytest.mark.parametrize(
    "damage",
    ["high", "accepted", "parse", "neutral-note", "pl-note", "en-note", "pl-only", "en-only"],
)
def test_pepererit_false_certainty_or_missing_local_note_is_rejected(damage):
    doc, pl = reading("evangelium", "pl")
    en = reading("evangelium", "en")[1]
    assert_pepererit(doc, pl, en)
    bad, bad_pl, bad_en = deepcopy(doc), deepcopy(pl), deepcopy(en)
    if damage == "high":
        bad["editorial"]["words"]["w124"]["analysis"]["confidence"] = "high"
    elif damage == "accepted":
        bad["editorial"]["words"]["w124"]["analysis"]["review"] = "accepted"
    elif damage == "parse":
        words(bad)["w124"]["morph"]["mood"] = "subj"
    elif damage == "neutral-note":
        bad["localization"]["notes"].remove("w124")
    elif damage in {"pl-note", "en-note"}:
        (bad_pl if damage == "pl-note" else bad_en)["words"]["w124"].pop("note")
    elif damage == "pl-only":
        bad_pl["words"]["w124"]["note"] = "To wyłącznie czas przyszły dokonany."
    else:
        bad_en["words"]["w124"]["note"] = "This is exclusively future perfect indicative."
    with pytest.raises(AssertionError):
        assert_pepererit(bad, bad_pl, bad_en)
    assert_pepererit(doc, pl, en)


@pytest.mark.parametrize("part", sorted(LATIN))
def test_complete_english_layer_passes_language_checks(part):
    doc, layers = store.load(ROOT, PREFIX + part)
    layer = layers["en"]
    assert layer["lang"] == "en"
    assert not english.check(doc, layer)


@pytest.mark.parametrize(
    "part, word, field",
    [
        ("introitus", "w030", "explanation"),
        ("epistola", "w048", "explanation"),
        ("evangelium", "w124", "note"),
    ],
)
def test_explanatory_apostrophe_damage_is_rejected_and_restored(part, word, field):
    doc, layers = store.load(ROOT, PREFIX + part)
    layer = layers["en"]
    assert layer["lang"] == "en"
    assert not english.check(doc, layer)
    original = layer["words"][word][field]
    assert "’" in original
    layer["words"][word][field] = original.replace("’", "'")
    errors = english.check(doc, layer)
    assert any(f"{word}.{field}: straight apostrophe" in error for error in errors)
    layer["words"][word][field] = original
    assert not english.check(doc, layer)

"""St Petronilla's Postcommunion: the body printed for her on 31 May is word for word the
prayer printed for St Anastasia at the Christmas Mass at Dawn (Benziger p. 544, Vatican
p. 541; MR1962 p. 20). The standalone text reuses that body exactly (words, analyses, Polish
and English prose, captions and alignments) and closes with the ordinary conclusion of the
sibling Secret in the same four-segment topology."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.bibliography_bindings import digest, selected_text, transcript_digest
from checks import delivery, language_packs, orations, participation, prose
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parent.parent
TEXT = "proprium.sanctae-petronillae-postcommunio"
DAWN = "proprium.nativitas-domini-in-aurora-postcommunio"
SECRET = "proprium.sanctae-petronillae-secreta"
BODY = {f"w{38 + i:03d}": f"w{1 + i:03d}" for i in range(15)}
CONCLUSION = {f"w{20 + i:03d}": f"w{16 + i:03d}" for i in range(22)}
SEGMENTS = {
    "s01": [f"w{n:03d}" for n in range(1, 16)],
    "s02": [f"w{n:03d}" for n in range(16, 33)],
    "s03": [f"w{n:03d}" for n in range(33, 37)],
    "s04": ["w037"],
}
PROSE = {
    "pl": "Nasyciłeś, Panie, Twoją rodzinę świętymi darami; prosimy, umacniaj nas zawsze "
    "wstawiennictwem tej, której uroczystość obchodzimy.",
    "en": "You have filled Your household, O Lord, with sacred gifts; always refresh us, we "
    "beseech You, through the intercession of her whose solemnity we celebrate.",
}
PROSE_SHA256 = {
    "pl": "9ae72f16c45243f6a70288fb5ffdc9b1b4f1d6431f752486c6ca7351a8ee7afe",
    "en": "380f84546ea670c92891d8f7c602157bd930cfbf2ec76a2489ef2e604ab77dc0",
}
ONSET = {"pl": " Przez Pana naszego", "en": " Through our Lord"}


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def core(text_id):
    return read(f"texts/{text_id.replace('.', '/', 1)}.json")


def layer(text_id, language):
    return read(f"languages/{language}/texts/{text_id.replace('.', '/', 1)}.json")


def words(doc):
    return {word["id"]: word for segment in doc["segments"] for word in segment.get("words", [])}


def analysis(doc, word_id):
    editorial = doc["editorial"]
    override = ((editorial.get("words") or {}).get(word_id) or {}).get("analysis")
    return override or editorial.get("analysis_defaults_words") or editorial["analysis_defaults"]


def remapped(word, mapping):
    out = {key: value for key, value in word.items()}
    out["id"] = mapping[word["id"]]
    if "head" in word:
        out["head"] = mapping[word["head"]]
    return out


def assert_reuse(doc, dawn, secret):
    new = words(doc)
    for source, mapping in ((dawn, BODY), (secret, CONCLUSION)):
        old = words(source)
        for old_id, new_id in mapping.items():
            assert new[new_id] == remapped(old[old_id], mapping), "exact word reuse"
            assert analysis(doc, new_id) == analysis(source, old_id), "exact analysis reuse"
    assert len(new) == 37 and set(new) == set(BODY.values()) | set(CONCLUSION.values())


def assert_layer_reuse(target, dawn_layer, secret_layer, language):
    dawn_prose = dawn_layer["segments"]["s03"]["translation"]
    assert dawn_prose.count(ONSET[language]) == 1, "one conclusion onset in the Dawn prose"
    body = dawn_prose[: dawn_prose.index(ONSET[language])]
    assert target["segments"]["s01"]["translation"] == body == PROSE[language], "body prose"
    for sid in ("s02", "s03", "s04"):
        expected = deepcopy(secret_layer["segments"][sid])
        for group in expected.get("alignments", []):
            group["words"] = [CONCLUSION[w] for w in group["words"]]
            group["anchor"] = CONCLUSION[group["anchor"]]
        assert target["segments"][sid] == expected, "sibling conclusion prose and groups"
    groups = [
        {
            "words": [BODY[w] for w in group["words"]],
            "anchor": BODY[group["anchor"]],
            "gloss": group["gloss"],
        }
        for group in dawn_layer["segments"]["s03"].get("alignments", [])
        if set(group["words"]) <= set(BODY)
    ]
    assert target["segments"]["s01"].get("alignments", []) == groups, "Dawn body groups"
    for source, mapping in ((dawn_layer, BODY), (secret_layer, CONCLUSION)):
        for old_id, new_id in mapping.items():
            assert target["words"][new_id] == source["words"][old_id], "captions and notes"


def test_the_body_and_its_analyses_are_the_dawn_anastasia_body_exactly():
    doc, dawn, secret = core(TEXT), core(DAWN), core(SECRET)
    assert_reuse(doc, dawn, secret)
    body = [word["form"] + word.get("post", "") for word in doc["segments"][0]["words"]]
    assert " ".join(body) == (
        "Satiásti, Dómine, famíliam tuam munéribus sacris: eius, quǽsumus, semper "
        "interventióne nos réfove, cuius solémnia celebrámus."
    )
    assert doc["editorial"]["analysis_defaults"] == {
        "confidence": "high",
        "sources": ["editorial"],
        "review": "pending",
    }
    assert "analysis_defaults_words" not in doc["editorial"]
    assert set(doc["editorial"]["words"]) == set(BODY.values()) | set(CONCLUSION.values())


def test_the_standalone_topology_and_ritual_fields_are_the_siblings():
    doc = core(TEXT)
    assert {s["id"]: [w["id"] for w in s["words"]] for s in doc["segments"]} == SEGMENTS
    assert doc["ids"] == {"next": 38, "segments": {"next": 5}}
    assert [(s["speaker"], s["voice"]) for s in doc["segments"]] == [
        ("sacerdos", "clara"),
        ("sacerdos", "clara"),
        ("sacerdos", "clara"),
        ("minister", "clara"),
    ]
    assert orations.structure(doc) == (
        [],
        {"s01": "body", "s02": "body", "s03": "tail", "s04": "response"},
    )
    assert orations.check_doc(doc) == ([], 1)
    assert delivery.check_doc(doc)[0] == []
    assert participation.check_doc(doc)[0] == []
    assert language_packs.check_core(doc) == []
    assert doc["localization"] == {"about": True, "explanations": {"w032": {}}}


@pytest.mark.parametrize("language", ("pl", "en"))
def test_the_language_layers_reuse_the_dawn_body_and_the_sibling_conclusion(language):
    doc, target = core(TEXT), layer(TEXT, language)
    assert_layer_reuse(target, layer(DAWN, language), layer(SECRET, language), language)
    body = target["segments"]["s01"]["translation"].encode()
    assert hashlib.sha256(body).hexdigest() == PROSE_SHA256[language]
    for segment in doc["segments"]:
        members = [word["id"] for word in segment["words"]]
        realized = [wid for wid in members if "gloss" in target["words"][wid]]
        for group in target["segments"][segment["id"]].get("alignments", []):
            assert set(group["words"]) <= set(members), "group wholly inside its segment"
            realized.extend(group["words"])
        assert Counter(realized) == Counter(members), "each member realized exactly once"
    path = ROOT / f"languages/{language}/texts/{TEXT.replace('.', '/', 1)}.json"
    assert language_packs.check_layer(doc, target, path) == []
    assert prose.check(target) == []
    assert (
        target["about"]
        == {
            "pl": "Pokomunia na wspomnienie św. Petroneli.",
            "en": "Postcommunion for the commemoration of Saint Petronilla.",
        }[language]
    )


@pytest.mark.parametrize("language", ("pl", "en"))
def test_four_working_provenance_rows(language):
    rows = [
        row
        for row in read(f"languages/{language}/translation-provenance.json")["sites"]
        if row["text"] == TEXT
    ]
    doc, target = core(TEXT), layer(TEXT, language)
    assert [row["segment"] for row in rows] == ["s01", "s02", "s03", "s04"]
    for row, segment in zip(rows, doc["segments"], strict=True):
        assert row["site"] == f"{TEXT}.{segment['id']}.{language}"
        assert (row["origin"], row["review"], row["familiar_core"]) == (
            "working-unsettled",
            "working",
            False,
        )
        assert row["source_sha256"] == canonical_hash(source_payload(segment))
        translation = target["segments"][segment["id"]]["translation"]
        assert row["target_sha256"] == canonical_hash(translation)


def test_printed_sources_are_narrow_and_pending():
    graph = read("bibliography/graph.json")
    uses = {row["id"]: row for row in graph["uses"] if row["address"].get("text") == TEXT}
    assert sorted(uses) == [
        f"use.{TEXT}.conclusion-rg115a.mr1962",
        f"use.{TEXT}.conclusion-rg115a.vatican1962",
        f"use.{TEXT}.mr1962",
        f"use.{TEXT}.vatican1962",
    ]
    benziger, vatican = uses[f"use.{TEXT}.mr1962"], uses[f"use.{TEXT}.vatican1962"]
    assert (benziger["role"], benziger["locator"]["printed"]) == ("direct_approved_print", "p. 544")
    assert benziger["locator"]["section"] == "Pro S. Petronilla, Postcommunio"
    assert (vatican["role"], vatican["locator"]["printed"]) == (
        "corroborating_latin_witness",
        "p. 541",
    )
    assert vatican["locator"]["section"] == "no.2696, Pro S. Petronilla, Postcommunio"
    assert all(use["address"] == {"kind": "text", "text": TEXT} for use in (benziger, vatican))
    witnesses = [row for row in graph["witnesses"] if row["text"] == TEXT]
    collations = [row for row in graph["collations"] if row["text"] == TEXT]
    assert len(witnesses) == 2 and len(collations) == 1
    for witness in witnesses:
        assert witness["review"] == {"status": "pending"}
        assert witness["source_dependencies"]["raw_binding"] is None
        name = witness["transcription"]
        text = (ROOT / f"witnesses/{TEXT}/{name}.txt").read_text(encoding="utf-8")
        assert witness["transcription_sha256"] == transcript_digest(text)
        cue = {"mr": "“Per Dóminum.”", "vatican": "“Per Dóminum nostrum.”"}[name]
        assert cue in text, "the printed cue is header information"
    collation = collations[0]
    assert collation["review"] == {"status": "pending"}
    assert collation["selected_text_sha256"] == digest(selected_text(core(TEXT)))
    apparatus = read(f"witnesses/{TEXT}/apparatus.json")
    assert collation["apparatus_sha256"] == digest(apparatus)
    assert all(int(entry["at"][1:]) >= 16 for entry in apparatus["adjudicated"])


@pytest.mark.parametrize("mutation", ("morphology", "lemma", "head", "analysis"))
def test_a_changed_body_word_breaks_exact_reuse_and_the_healthy_text_is_restored(mutation):
    original, dawn, secret = core(TEXT), core(DAWN), core(SECRET)
    bad = deepcopy(original)
    body = {word["id"]: word for word in bad["segments"][0]["words"]}
    if mutation == "morphology":
        body["w012"]["morph"]["mood"] = "ind"
    elif mutation == "lemma":
        body["w014"]["lemma"] = "sollemnis"
    elif mutation == "head":
        body["w004"]["head"] = "w005"
    else:
        bad["editorial"]["words"]["w007"]["analysis"]["review"] = "accepted"
    diagnostic = "exact analysis reuse" if mutation == "analysis" else "exact word reuse"
    with pytest.raises(AssertionError, match=diagnostic):
        assert_reuse(bad, dawn, secret)
    assert_reuse(original, dawn, secret)


@pytest.mark.parametrize("mutation", ("prose", "caption", "group"))
def test_a_changed_translation_breaks_exact_reuse_and_the_healthy_layer_is_restored(mutation):
    original = layer(TEXT, "en")
    bad = deepcopy(original)
    if mutation == "prose":
        bad["segments"]["s01"]["translation"] = PROSE["en"].replace("refresh", "renew")
        diagnostic = "body prose"
    elif mutation == "caption":
        bad["words"]["w012"]["gloss"] = "renew"
        diagnostic = "captions and notes"
    else:
        bad["segments"]["s01"]["alignments"][0]["gloss"] = "Your family"
        diagnostic = "Dawn body groups"
    sources = (layer(DAWN, "en"), layer(SECRET, "en"))
    with pytest.raises(AssertionError, match=diagnostic):
        assert_layer_reuse(bad, *sources, "en")
    assert_layer_reuse(original, *sources, "en")


@pytest.mark.parametrize("mutation", ("boundary", "formula", "response"))
def test_the_split_shape_fails_closed_without_roles(mutation):
    original = core(TEXT)
    bad = deepcopy(original)
    if mutation == "boundary":
        bad["segments"][0]["words"].append(bad["segments"][1]["words"].pop(0))
        diagnostic = "exact body/ending/response boundaries"
    elif mutation == "formula":
        bad["segments"][2]["words"][0]["form"] = "in"
        diagnostic = "complete ordinary formula and Amen"
    else:
        bad["segments"][-1]["words"][0]["form"] = "Alleluia"
        diagnostic = "complete ordinary formula and Amen"
    errors, roles = orations.structure(bad)
    assert roles == {} and any(diagnostic in error for error in errors)
    assert orations.check_doc(original) == ([], 1)


def test_an_unlisted_postcommunion_cannot_inherit_the_split_exception():
    bad = deepcopy(core(TEXT))
    bad["id"] = "proprium.other-postcommunio"
    errors, roles = orations.structure(bad)
    assert roles == {} and any("complete body/Amen" in error for error in errors)
    assert orations.check_doc(core(TEXT)) == ([], 1)

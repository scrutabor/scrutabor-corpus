"""Adoro’s current prayer text, source lineation and narrow wording evidence."""

import json
from pathlib import Path

import pytest

from build_reader import store
from build_reader.emit import Table, language_artifact
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
TEXT = "orationes.adoro-te-devote"
CURRENT = {
    "pl": {
        "s06": "lecz tylko słuch daje pewność wiary:",
        "s23": "której jedna zbawcza kropla",
        "s24": "może oczyścić cały świat z wszelkiego grzechu.",
    },
    "en": {
        "s01": "With devotion I adore You, hidden Godhead,",
        "s02": "who are truly hidden beneath these forms:",
        "s06": "but hearing alone gives sure ground for faith:",
        "s10": "but here Your humanity is hidden as well.",
        "s22": "cleanse me, unclean as I am, with Your blood.",
        "s23": "One saving drop of that blood",
        "s24": "can free the whole world from every sin.",
    },
}
INHERITED = {"pl": {"s01", "s23", "s24"}, "en": {"s01", "s02", "s23", "s24"}}


def load(relative):
    return json.loads((ROOT / relative).read_bytes())


def assert_current(segments, language):
    for sid, target in CURRENT[language].items():
        assert segments[sid]["translation"] == target, (language, sid)


def test_current_reading_and_actual_reader_payload_use_the_new_values():
    core, layers = store.load(ROOT, TEXT)
    assert len(core["segments"]) == 28
    assert sum(len(s["words"]) for s in core["segments"]) == 149
    for language, layer in layers.items():
        assert_current(layer["segments"], language)
        emitted = language_artifact(
            core, layer, Table(), store.translation_relationships(ROOT, language)
        )
        rows = {s["id"]: s for s in emitted["seg"]}
        assert len(rows) == 28
        for sid, expected in CURRENT[language].items():
            assert rows[sid]["tr"] == expected
        assert {sid for sid, row in rows.items() if row.get("tb") == "revised"} == INHERITED[
            language
        ]
        for segment in core["segments"]:
            sid = segment["id"]
            assert len(rows[sid]["g"]) == len(segment["words"])


def test_every_current_site_keeps_its_individually_supported_origin_and_hashes():
    core = load("texts/orationes/adoro-te-devote.json")
    source = {s["id"]: s for s in core["segments"]}
    for language, inherited in INHERITED.items():
        layer = load(f"languages/{language}/texts/orationes/adoro-te-devote.json")
        rows = [
            r
            for r in load(f"languages/{language}/translation-provenance.json")["sites"]
            if r["text"] == TEXT
        ]
        assert len(rows) == 28
        for row in rows:
            sid = row["segment"]
            assert row["origin"] == ("public-domain" if sid in inherited else "own")
            assert row["review"] == "working" and row["familiar_core"] is False
            assert row["source_sha256"] == canonical_hash(source_payload(source[sid]))
            assert row["target_sha256"] == canonical_hash(layer["segments"][sid]["translation"])
        uses = [
            u
            for u in load(f"languages/{language}/bibliography.json")["uses"]
            if u["address"].get("text") == TEXT
        ]
        assert {u["address"]["segment"] for u in uses} == inherited
        assert len(uses) == len(inherited)
    # A punctuation revision neither borrows a historical clause nor creates an author.
    en_rows = load("languages/en/translation-provenance.json")["sites"]
    assert next(r for r in en_rows if r["site"] == TEXT + ".s22.en")["origin"] == "own"


def test_the_new_polish_basis_is_the_actual_drop_page_not_the_opening_page():
    uses = load("languages/pl/bibliography.json")["uses"]
    selected = [
        u
        for u in uses
        if u["id"] in {f"use.{TEXT}.kuehn1902-pl-s23", f"use.{TEXT}.kuehn1902-pl-s24"}
    ]
    assert len(selected) == 2
    for use in selected:
        assert use["address"]["kind"] == "segment"
        assert use["edition"] == "edition.katolik-w-modlitwie-1902"
        assert use["digital_item"] == "item.katolik-w-modlitwie-1902.obc"
        assert use["role"] == "historical_wording_basis"
        assert use["locator"]["printed"] == "p. 156"
        assert use["locator"]["scan"] == "physical PDF p. 170 (one-based)"
        assert (
            use["evidence_sha256"]
            == "5e6e47a1bef9d2d08dba2b4f45cc51ad463209827522e35a34abdc262fefac15"
        )
        assert use["decision"] == "RETAIN_WITH_CORRECTION"
        assert use["legacy_refs"] == []


@pytest.mark.parametrize(
    "language,sid,wrong",
    [
        ("en", "s01", "The hidden Godhead whom I adore with devotion:"),
        ("en", "s06", "but through hearing alone I can believe with certainty:"),
        ("en", "s24", "frees the whole world from every sin."),
        ("pl", "s24", "oczyszcza cały świat z wszelkiego grzechu."),
    ],
)
def test_current_oracles_reject_the_old_attachment_person_shift_and_actual_salvation(
    language, sid, wrong
):
    layer = load(f"languages/{language}/texts/orationes/adoro-te-devote.json")
    layer["segments"][sid]["translation"] = wrong
    with pytest.raises(AssertionError):
        assert_current(layer["segments"], language)


def test_latin_printed_lineation_and_generic_belief_are_preserved():
    core = load("texts/orationes/adoro-te-devote.json")
    segments = {segment["id"]: segment for segment in core["segments"]}
    assert list(segments) == [f"s{number:02d}" for number in range(1, 29)]
    assert [word["id"] for segment in core["segments"] for word in segment["words"]] == [
        f"w{number:03d}" for number in range(1, 150)
    ]
    assert [word["form"] for word in segments["s23"]["words"]] == [
        "Cuius",
        "una",
        "stilla",
        "salvum",
        "fácere",
    ]
    assert [word["form"] for word in segments["s24"]["words"]] == [
        "Totum",
        "mundum",
        "quit",
        "ab",
        "omni",
        "scélere",
    ]
    assert segments["s23"]["words"][-1].get("post", "") == ""
    assert segments["s24"]["words"][-1]["post"] == "."
    assert "s24" not in core["ids"]["segments"].get("retired", {})
    impersonal = next(word for word in segments["s06"]["words"] if word["id"] == "w033")
    personal = segments["s07"]["words"][0]
    assert (impersonal["morph"]["person"], impersonal["morph"]["voice"]) == (3, "pass")
    assert personal["form"] == "Credo" and personal["morph"]["person"] == 1


def assert_polish_drop_locator(use):
    assert use["locator"]["printed"] == "p. 156"
    assert use["locator"]["scan"] == "physical PDF p. 170 (one-based)"


@pytest.mark.parametrize(
    "field,wrong", [("printed", "p. 154"), ("scan", "physical PDF p. 168 (one-based)")]
)
def test_an_opening_page_cannot_support_the_polish_drop_clause(field, wrong):
    use = next(
        use
        for use in load("languages/pl/bibliography.json")["uses"]
        if use["id"] == f"use.{TEXT}.kuehn1902-pl-s23"
    )
    assert_polish_drop_locator(use)
    use["locator"][field] = wrong
    with pytest.raises(AssertionError):
        assert_polish_drop_locator(use)


@pytest.mark.parametrize(
    ("language", "hearing", "faith", "humanity"),
    [
        ("en", "through hearing alone", "one believes with certainty", "Your humanity as well"),
        (
            "pl",
            "jedynie dzięki słuchowi",
            "można wierzyć bez obawy błędu",
            "także Twoje człowieczeństwo",
        ),
    ],
)
def test_the_word_help_expresses_assurance_and_the_single_addition(
    language, hearing, faith, humanity
):
    layer = store.raw_layer(ROOT, language, TEXT)
    for sid, spans in {
        "s06": [(["w030", "w031"], hearing), (["w032", "w033"], faith)],
        "s10": [(["w052", "w053", "w054"], humanity)],
    }.items():
        groups = layer["segments"][sid].get("alignments", [])
        assert [(g["words"], g["gloss"]) for g in groups] == spans
        for words, _ in spans:
            assert all("gloss" not in layer["words"][word] for word in words)
    assert "tutus" in layer["words"]["w032"]["note"]
    assert not any(
        x in layer["words"]["w032"]["note"] for x in ("safety", "safe hearing", "bezpieczeństwo")
    )

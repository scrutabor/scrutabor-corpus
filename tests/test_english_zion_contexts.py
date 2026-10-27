"""Contextual English names do not rewrite Latin or historical wording."""

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import store
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
CONTEXTS = (
    (
        "proprium.commemoratio-omnium-fidelium-defunctorum-missa-i-introitus",
        ("segments", "s01", "translation"),
        1,
        None,
    ),
    (
        "proprium.commemoratio-omnium-fidelium-defunctorum-missa-i-introitus",
        ("words", "w016", "gloss"),
        1,
        "Zion",
    ),
    ("proprium.dominica-ii-adventus-graduale", ("segments", "s01", "translation"), 1, None),
    ("proprium.dominica-ii-adventus-graduale", ("words", "w002", "gloss"), 1, "Zion"),
    ("proprium.dominica-ii-adventus-introitus", ("about",), 1, None),
    ("proprium.dominica-ii-adventus-introitus", ("segments", "s01", "translation"), 1, None),
    ("proprium.dominica-ii-adventus-introitus", ("segments", "s05", "translation"), 1, None),
    ("proprium.dominica-ii-adventus-introitus", ("words", "w002", "gloss"), 1, "of Zion"),
    ("proprium.dominica-ii-adventus-introitus", ("words", "w050", "gloss"), 1, "of Zion"),
    (
        "proprium.dominica-iii-post-epiphaniam-introitus",
        ("segments", "s01", "translation"),
        2,
        None,
    ),
    (
        "proprium.dominica-iii-post-epiphaniam-introitus",
        ("segments", "s01", "alignments", 1, "gloss"),
        1,
        "Zion heard and was glad",
    ),
    (
        "proprium.dominica-iii-post-epiphaniam-introitus",
        ("segments", "s01", "alignments", 7, "gloss"),
        1,
        "Zion heard and was glad",
    ),
    (
        "proprium.dominica-iii-post-pentecosten-offertorium",
        ("segments", "s01", "translation"),
        1,
        None,
    ),
    (
        "proprium.dominica-iii-post-pentecosten-offertorium",
        ("words", "w020", "gloss"),
        1,
        "Zion",
    ),
    (
        "proprium.dominica-x-post-pentecosten-alleluia",
        ("segments", "s01", "translation"),
        1,
        None,
    ),
    ("proprium.dominica-x-post-pentecosten-alleluia", ("words", "w008", "gloss"), 1, "Zion"),
    (
        "proprium.dominica-xvi-post-pentecosten-graduale",
        ("segments", "s01", "translation"),
        1,
        None,
    ),
    ("proprium.dominica-xvi-post-pentecosten-graduale", ("words", "w015", "gloss"), 1, "Zion"),
    (
        "proprium.dominica-xx-post-pentecosten-offertorium",
        ("segments", "s01", "translation"),
        1,
        None,
    ),
    (
        "proprium.dominica-xx-post-pentecosten-offertorium",
        ("words", "w011", "gloss"),
        1,
        "Zion",
    ),
    ("proprium.immaculata-conceptio-tractus", ("segments", "s01", "translation"), 1, None),
    ("proprium.immaculata-conceptio-tractus", ("words", "w009", "gloss"), 1, "of Zion"),
    (
        "proprium.nativitas-domini-in-aurora-communio",
        ("segments", "s01", "translation"),
        1,
        None,
    ),
    ("proprium.nativitas-domini-in-aurora-communio", ("words", "w003", "gloss"), 1, "of Zion"),
    (
        "proprium.sanctorum-innocentium-martyrum-epistola",
        ("segments", "s01", "translation"),
        1,
        None,
    ),
    ("proprium.sanctorum-innocentium-martyrum-epistola", ("words", "w007", "gloss"), 1, "Zion"),
)
LITERAL_CONTEXTS = (
    ("proprium.corporis-christi-sequentia", ("about",), "Lauda Sion"),
    (
        "proprium.dominica-ii-adventus-introitus",
        ("segments", "s04", "narrative"),
        "Pópulus Sion",
    ),
)
WORDING_USES = (
    ("use.en.c40d4ecf34249c94edec", "s01"),
    ("use.en.84d901e39b2c20ff4f9e", "s05"),
)
WORDING_CLAIM = (
    "The Introit printed in the 1846 missal supplies the historical wording basis "
    "for this revised English rendering. The page prints “PEOPLE of Sion” and "
    "“save the Gentiles”; the current English uses “people of Zion” and "
    "“save the nations”. The current rendering is revised, not a verbatim quotation."
)


def value_at(layer, address):
    for key in address:
        layer = layer[key]
    return layer


def name_errors(value, count, exact):
    if (
        not isinstance(value, str)
        or len(re.findall(r"\bZion\b", value)) != count
        or re.search(r"\bSion\b", value, re.IGNORECASE)
        or (exact is not None and value != exact)
    ):
        return ["contextual English name"]
    return []


@pytest.fixture(scope="module")
def ledger_rows():
    rows = json.loads((ROOT / "languages/en/translation-provenance.json").read_text())["sites"]
    indexed = {row["site"]: row for row in rows}
    assert len(indexed) == len(rows)
    return indexed


@pytest.mark.parametrize(
    "text,address,count,exact",
    CONTEXTS,
    ids=[
        f"{text.split('.', 1)[1]}-{'.'.join(map(str, address))}" for text, address, _, _ in CONTEXTS
    ],
)
def test_contextual_name_rejects_old_spelling_and_same_copy_recovers(
    text, address, count, exact, ledger_rows
):
    layer = store.raw_layer(ROOT, "en", text)
    saved = deepcopy(layer)
    value = value_at(layer, address)
    assert name_errors(value, count, exact) == []
    core = store.core(ROOT, text)
    assert any(w.get("lemma") == "Sion" for s in core["segments"] for w in s.get("words", []))
    if address[-1] == "translation":
        segment = next(s for s in core["segments"] if s["id"] == address[1])
        row = ledger_rows[f"{text}.{address[1]}.en"]
        assert row["target_sha256"] == canonical_hash(value)
        assert row["source_sha256"] == canonical_hash(source_payload(segment))
        assert row["review"] == "working" and row["familiar_core"] is False
        expected_origin = (
            "public-domain"
            if text == "proprium.dominica-ii-adventus-introitus"
            else "working-unsettled"
        )
        assert row["origin"] == expected_origin
    holder = value_at(layer, address[:-1])
    wrong = value.replace("Zion", "Sion", 1)
    assert wrong != value
    try:
        holder[address[-1]] = wrong
        assert layer != saved
        assert name_errors(value_at(layer, address), count, exact) == ["contextual English name"]
    finally:
        holder[address[-1]] = value
        assert layer == saved
        assert name_errors(value_at(layer, address), count, exact) == []


@pytest.mark.parametrize(
    "text,address,phrase", LITERAL_CONTEXTS, ids=["latin-title", "latin-reprise-cue"]
)
def test_latin_title_and_cue_keep_their_spelling(text, address, phrase):
    value = value_at(store.raw_layer(ROOT, "en", text), address)
    assert phrase in value and phrase.replace("Sion", "Zion") not in value


def test_shared_lexical_identity_is_not_a_contextual_caption():
    neutral = json.loads((ROOT / "lexicon/lemmata.json").read_text())["entries"]["Sion"]
    english = json.loads((ROOT / "languages/en/lexicon.json").read_text())["entries"]["Sion"]
    assert neutral["head"] == "Sion" and neutral["pos"] == "noun"
    assert english["senses"] == ["Sion"]


def source_claim_errors(claim):
    if (
        "“PEOPLE of Sion”" not in claim
        or "“save the Gentiles”" not in claim
        or "“PEOPLE of Zion”" in claim
        or "revised, not a verbatim quotation" not in claim
    ):
        return ["historical source spelling"]
    return []


@pytest.mark.parametrize(
    "identity,segment", WORDING_USES, ids=["introit-proper", "introit-reprise"]
)
def test_revised_basis_does_not_claim_the_page_prints_zion(identity, segment):
    rows = json.loads((ROOT / "languages/en/bibliography.json").read_text())["uses"]
    (use,) = [deepcopy(row) for row in rows if row["id"] == identity]
    saved = deepcopy(use)
    assert use["claim"] == WORDING_CLAIM and source_claim_errors(use["claim"]) == []
    assert use["address"] == {
        "kind": "segment",
        "text": "proprium.dominica-ii-adventus-introitus",
        "segment": segment,
    }
    assert use["edition"] == "edition.the-missal-for-the-laity-1846"
    assert use["digital_item"] == "item.missal-for-the-laity-1846.scan"
    assert use["role"] == "historical_wording_basis"
    assert use["verified_on"] == "2026-08-28"
    assert use["evidence_sha256"] == (
        "8e692b256e08350896902e55787f70c171a444d33e754f4d67e84fe000f81dd1"
    )
    try:
        use["claim"] = use["claim"].replace("“PEOPLE of Sion”", "“PEOPLE of Zion”", 1)
        assert use != saved
        assert source_claim_errors(use["claim"]) == ["historical source spelling"]
    finally:
        use["claim"] = saved["claim"]
        assert use == saved and source_claim_errors(use["claim"]) == []

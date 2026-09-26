"""Polish dictionary cards cover the distinct senses used in the corpus."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("lemma", "senses"),
    [
        ("intendo", {"kierować", "zwracać uwagę", "nakłaniać"}),
        ("consto", {"trwać", "składać się", "być wiadomym", "być pewnym"}),
        ("sors", {"los", "udział"}),
        ("formido", {"bać się", "lękać się"}),
        ("diffamo", {"rozgłaszać", "rozpowszechniać", "zniesławiać", "oczerniać"}),
        ("mansio", {"mieszkanie, siedziba", "pozostawanie", "pobyt", "postój"}),
        ("suggero", {"przypominać", "proponować", "sugerować"}),
        ("suscito", {"budzić", "wskrzeszać", "pobudzać"}),
        ("quisquam", {"ktokolwiek", "ktoś", "cokolwiek"}),
        ("forma", {"postać, kształt", "wzór, przykład", "wygląd", "uroda"}),
        ("simulacrum", {"bożek", "posąg", "obraz", "podobieństwo"}),
    ],
)
def test_dictionary_retains_distinct_contextually_needed_senses(lemma, senses):
    entries = json.loads((ROOT / "languages/pl/lexicon.json").read_text())["entries"]
    assert senses <= set(entries[lemma]["senses"])


def test_invisible_adjective_has_one_headword_with_a_real_nominative():
    entries = json.loads((ROOT / "lexicon/lemmata.json").read_text())["entries"]
    assert "invisibil" not in entries
    assert entries["invisibilis"]["head"] == "invisíbilis, -e"
    assert entries["invisibilis"]["pos"] == "adj"


@pytest.mark.parametrize(
    ("lemma", "entry"),
    [
        ("intendo", "n24136"),
        ("consto", "n10640"),
        ("sors", "n44805"),
        ("invisibilis", "n24782"),
        ("formido", "n18588"),
        ("diffamo", "n13854"),
        ("mansio", "n27904"),
        ("suggero", "n46481"),
        ("suscito", "n47103"),
        ("forma", "n18566"),
        ("simulacrum", "n44337"),
    ],
)
def test_lexical_support_identifies_the_actual_dictionary_entry(lemma, entry):
    graph = json.loads((ROOT / "bibliography/graph.json").read_text())
    use = next(row for row in graph["uses"] if row["id"] == f"use.lemma.{lemma}.lewis-short.1879")
    assert use["role"] == "lexical_support"
    assert use["address"] == {"kind": "lemma", "lemma": lemma}
    assert use["locator"]["section"] == f"Perseus TEI entry {entry}"
    assert use["evidence_sha256"]


@pytest.mark.parametrize(
    ("lemma", "head"),
    [
        ("formido", "formído, formidáre, formidávi, formidátum"),
        ("diffamo", "diffámo, diffamáre, diffamávi, diffamátum"),
        ("suscito", "súscito, suscitáre, suscitávi, suscitátum"),
        ("forma", "forma, formæ"),
    ],
)
def test_dictionary_heads_preserve_vowel_quantity_and_diphthongs(lemma, head):
    entries = json.loads((ROOT / "lexicon/lemmata.json").read_text())["entries"]
    assert entries[lemma]["head"] == head


def test_fearing_verb_does_not_retain_the_homonymous_noun_senses():
    entries = json.loads((ROOT / "languages/pl/lexicon.json").read_text())["entries"]
    assert not {"bojaźń", "strach", "przerażenie"} & set(entries["formido"]["senses"])

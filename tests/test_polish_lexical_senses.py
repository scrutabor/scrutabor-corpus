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
    ],
)
def test_dictionary_retains_distinct_contextually_needed_senses(lemma, senses):
    entries = json.loads((ROOT / "languages/pl/lexicon.json").read_text())["entries"]
    assert senses <= set(entries[lemma]["senses"])


def test_invisible_adjective_displays_a_real_nominative_not_its_identifier():
    entries = json.loads((ROOT / "lexicon/lemmata.json").read_text())["entries"]
    assert entries["invisibil"]["head"] == "invisíbilis, -e"
    assert entries["invisibil"]["pos"] == "adj"


@pytest.mark.parametrize(
    ("lemma", "entry"),
    [("intendo", "n24136"), ("consto", "n10640"), ("sors", "n44805"), ("invisibil", "n24782")],
)
def test_lexical_support_identifies_the_actual_dictionary_entry(lemma, entry):
    graph = json.loads((ROOT / "bibliography/graph.json").read_text())
    use = next(row for row in graph["uses"] if row["id"] == f"use.lemma.{lemma}.lewis-short.1879")
    assert use["role"] == "lexical_support"
    assert use["address"] == {"kind": "lemma", "lemma": lemma}
    assert use["locator"]["section"] == f"Perseus TEI entry {entry}"
    assert use["evidence_sha256"]

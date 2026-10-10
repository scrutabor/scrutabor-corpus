"""Two dictionary cards distinguish renewal, passive recap and command recipients."""

import copy
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def card_contracts(language, entries):
    if language == "pl":
        assert entries["instauro"]["senses"] == [
            "odnawiać",
            "przywracać",
            "streszczać się (w stronie biernej)",
        ]
        assert entries["impero"]["note"] == (
            "Celownik może wskazywać, komu lub czemu wydaje się rozkaz."
        )
    else:
        assert language == "en"
        assert entries["instauro"]["senses"] == ["to restore, renew", "to sum up"]
        assert entries["impero"]["note"] == (
            "The dative can indicate the person or thing being commanded."
        )


def entries_for(language):
    return json.loads((ROOT / f"languages/{language}/lexicon.json").read_text())["entries"]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_cards_keep_renewal_and_clarify_command_recipients(language):
    card_contracts(language, entries_for(language))


@pytest.mark.parametrize(
    ("language", "lemma", "field", "bad_value"),
    [
        ("pl", "instauro", "senses", ["odnawiać", "przywracać", "streszczać się"]),
        ("pl", "instauro", "senses", ["streszczać się (w stronie biernej)"]),
        ("pl", "instauro", "senses", ["odnawiać", "streszczać się (w stronie biernej)"]),
        ("en", "instauro", "senses", ["to sum up"]),
        ("pl", "impero", "note", "Łączy się z celownikiem osoby, której się rozkazuje."),
        ("pl", "impero", "note", "Celownik zawsze wskazuje, komu lub czemu wydaje się rozkaz."),
        ("pl", "impero", "note", "Celownik wskazuje treść rozkazu."),
        ("en", "impero", "note", "Takes the dative for the person commanded."),
        ("en", "impero", "note", "The dative always indicates the person or thing commanded."),
        ("en", "impero", "note", "The dative indicates the content of a command."),
    ],
)
def test_cards_reject_lost_senses_and_narrow_or_mandatory_dative_notes(
    language, lemma, field, bad_value
):
    entries = entries_for(language)
    card_contracts(language, entries)
    bad = copy.deepcopy(entries)
    bad[lemma][field] = bad_value
    with pytest.raises(AssertionError):
        card_contracts(language, bad)
    card_contracts(language, entries)

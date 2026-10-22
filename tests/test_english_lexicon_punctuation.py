"""English lexical notes preserve their wording and quotation punctuation."""

import json
from pathlib import Path

import pytest

from checks.lexicon import lint_senses

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_NOTES = {
    "Agatha": "A Greek name, “good.” The Sicilian martyr named in the Canon.",
    "Agnes": "A Greek name, “pure.” The Roman martyr named in the Canon.",
    "Alexander": "A Greek name, “defending men.”",
    "Anastasia": "A Greek name, “resurrection.” The martyr named in the Canon.",
    "Andreas": "A Greek name, “manly,” from anér — “man.”",
    "Barnabas": "The name the Apostles gave him. Acts 4:36 renders it “son of consolation.”",
    "Bartholomaeus": "An Aramaic name — bar-Talmai, “son of Talmai.”",
    "Chrysogonus": "A Greek name, “gold-begotten.”",
    "Clemens": "The Latin adjective clemens — “mild, merciful.”",
    "Cletus": "A Greek name, “called.”",
    "Cosmas": "A Greek name, “order.” A physician, martyred in Cilicia with Damian.",
    "Cyprianus": "“Of Cyprus,” from the Latin name of the island.",
    "Felicitas": "The Latin noun felicitas — “happiness.”",
    "Iesus": (
        "Through Greek from the Hebrew name Yeshua — “God saves.” Irregular declension "
        "(nominative Iesus, accusative Iesum, all other cases Iesu)."
    ),
    "Ioannes": "From Hebrew Yochanan — “the Lord is gracious.”",
    "Matthaeus": "A shortened Hebrew name — “gift of the Lord.”",
    "Michael": "From Hebrew Mika’el — “Who is like God?”",
    "Paulus": "The Latin adjective paulus — “small.”",
    "Perpetua": "The Latin adjective perpetua — “unbroken, continuous.”",
    "Petrus": (
        "Aramaic Cephas means “rock.” In John 1:42 the Evangelist interprets it with Greek Pétros."
    ),
    "Philippus": "A Greek name, “horse-lover.”",
    "Thomas": "John gives the Greek byname as well — Dídymus, “twin.”",
    "adversus": "Neuter plural advérsa means “adversities.”",
    "ago": "In the phrase grátias ágere it means “to give thanks.”",
    "alleluia": (
        "Hebrew hallelu-Yah — “praise the Lord.” The word passed through Greek "
        "and is indeclinable in Latin."
    ),
    "angelus": "Greek ángelos means “messenger.” The word entered Latin through Greek.",
    "aufero": "The case name ablative comes from ablátum, “taken away.”",
    "dignor": (
        "A deponent verb derived from dignus — worthy. In a deferential request, "
        "it can take an infinitive with the sense “be pleased to do something.”"
    ),
    "eleison": "Greek ἐλέησον, the imperative of ἐλεέω, “to have mercy.”",
    "eucharistia": "A Greek noun, “the giving of thanks.”",
    "ex": (
        "Before a vowel always “ex.” Before a consonant both “e” and “ex” occur (ex María Vírgine)."
    ),
    "fio": (
        "Irregular. Serves as the passive of “fácere,” to do or make, "
        "in the present system — the perfect passive is factus sum."
    ),
    "futurus": "The future participle of sum. Neuter plural futura means “things to come.”",
    "gaudeo": (
        "A semi-deponent: active forms in the present system and passive forms "
        "in the perfect system, e.g. gavísus sum — “I rejoiced.”"
    ),
    "inferi": "Used substantivally in the plural. Ab ínferis means “from among the dead.”",
    "kyrie": "Greek κύριε, the vocative of κύριος, “Lord.”",
    "martyr": (
        "Greek mártys means “witness.” A martyr bears supreme witness to Christ, even to death."
    ),
    "mirabilis": "Substantive mirabília means “wonders” or “marvelous works.”",
    "nec": "The phrase nec non means “and also.”",
    "odi": (
        "A defective verb. Perfect forms often express a present state, as in odi, “I hate.” "
        "Later Latin also has present forms, including the participle odientes. "
        "The time reference of a particular form depends on its context."
    ),
    "ops": "The plural opes means “resources” or “wealth.”",
    "perhibeo": "Often used in the phrase testimónium perhibére, “to bear witness.”",
    "saeculum": (
        "In the phrase in sǽcula sæculórum, the repeated word expresses unending "
        "duration: “forever and ever.”"
    ),
    "spero": (
        "In the sense “to trust,” it can take in with the ablative: "
        "speráre in Deo — to put one’s hope in God."
    ),
    "sumo": "With reference to Communion, sumere means “to receive.”",
    "ut": (
        "With the subjunctive, ut can introduce a purpose, a result, or the content "
        "of a request. With the indicative, it commonly means “as.”"
    ),
    "venter": "In the received English of the Ave María the word is “womb”: “fruit of thy womb.”",
    "quis": (
        "After si, nisi, ne and num, quis usually has the indefinite sense "
        "“someone” or “something.”"
    ),
    "sabaoth": (
        "Sabaoth is an indeclinable transcription of a plural Hebrew noun meaning “hosts.” "
        "In Deus Sabaoth it means “God of Hosts.”"
    ),
    "socius": "Used as a noun, sócius means “companion.”",
    "una": "An adverb formed from the ablative of unus. Una cum means “together with.”",
}


@pytest.mark.parametrize("lemma,expected", EXPECTED_NOTES.items())
def test_quoted_lexical_notes_keep_their_exact_wording(lemma, expected):
    entries = json.loads((ROOT / "languages/en/lexicon.json").read_text())["entries"]
    assert entries[lemma]["note"] == expected


@pytest.mark.parametrize(
    "note",
    [
        "The name means “good”.",
        "The name means “good”, and names a saint.",
        "The name means “Who is like God?”.",
        "The command is “Come!”.",
    ],
)
def test_english_note_rejects_external_comma_or_period(note):
    errors = lint_senses("en", {"name": {"senses": ["name"], "note": note}}, {"name": {}})
    assert any("commas and periods belong inside" in error for error in errors)


@pytest.mark.parametrize(
    "note",
    [
        "The name means “good.”",
        "The name means “good,” and names a saint.",
        "The name means “Who is like God?”",
        "The command is “Come!”",
        "Does the name mean “good”?",
        "It really means “good”!",
    ],
)
def test_question_and_exclamation_placement_is_not_generalized(note):
    assert lint_senses("en", {"name": {"senses": ["name"], "note": note}}, {"name": {}}) == []


def test_polish_note_keeps_polish_sentence_punctuation():
    assert (
        lint_senses(
            "pl", {"name": {"senses": ["imię"], "note": "Imię znaczy „dobry”."}}, {"name": {}}
        )
        == []
    )


@pytest.mark.parametrize(
    "note",
    [
        (
            "After si, nisi, ne and num, quis usually has the indefinite sense ‘someone’ "
            "or ‘something’."
        ),
        (
            "Sabaoth is an indeclinable transcription of a plural Hebrew noun meaning "
            "‘hosts’. In Deus Sabaoth it means ‘God of Hosts’."
        ),
        "Used as a noun, sócius means ‘companion’.",
        "An adverb formed from the ablative of unus. Una cum means ‘together with’.",
        "It means ‘good’, and is a name.",
        "An incomplete “outer with ‘inner’ quotations.",
    ],
)
def test_english_note_rejects_primary_single_quotations(note):
    errors = lint_senses("en", {"name": {"senses": ["name"], "note": note}}, {"name": {}})
    assert any("primary quotations use English double quotation marks" in error for error in errors)


@pytest.mark.parametrize(
    "note",
    [
        "It describes “the ‘good’ life.”",
        "The quoted phrase is “someone’s ‘own’ name.”",
        "The elision ’tis does not open a quotation.",
    ],
)
def test_nested_single_quotations_and_elision_are_not_primary_quotations(note):
    assert lint_senses("en", {"name": {"senses": ["name"], "note": note}}, {"name": {}}) == []


@pytest.mark.parametrize(
    "lemma",
    [
        "Abel",
        "Melchisedech",
        "Michael",
        "advocata",
        "agnus",
        "dextera",
        "iustificatio",
        "quotidianus",
        "spero",
    ],
)
def test_existing_lexical_apostrophes_are_not_single_quotations(lemma):
    entries = json.loads((ROOT / "languages/en/lexicon.json").read_text())["entries"]
    note = entries[lemma]["note"]
    assert "’" in note and "‘" not in note
    assert lint_senses("en", {"name": {"senses": ["name"], "note": note}}, {"name": {}}) == []

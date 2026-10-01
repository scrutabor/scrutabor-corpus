"""The enim card describes normal placement without an absolute restriction."""

from pathlib import Path

import pytest

from build_reader import emit, store
from checks import interlinear
from checks.lexicon import check_note_prose, lint_senses, load_lexicon

ROOT = Path(__file__).resolve().parents[1]
NOTES = {
    "pl": (
        "Zwykle stoi po pierwszym wyrazie lub po ściśle związanej grupie wyrazów "
        "na początku zdania."
    ),
    "en": (
        "Normally follows the first word or a closely connected opening word group in its clause."
    ),
}
SENSES = {"pl": ["bowiem", "albowiem"], "en": ["for", "indeed"]}


@pytest.mark.parametrize("language", ["pl", "en"])
def test_enim_note_qualifies_normal_placement(language):
    entry = emit.lexicon_slice(ROOT, language, {"enim"})["enim"]
    assert entry["note"] == NOTES[language]
    assert entry["senses"] == SENSES[language]


def test_enim_keeps_its_neutral_note_requirement():
    assert emit.lexicon_slice(ROOT, lemmas={"enim"}) == {
        "enim": {"head": "enim", "pos": "conj", "localization": {"note": True}}
    }
    heads, languages, errors = load_lexicon(ROOT)
    assert errors == []
    for language in ("pl", "en"):
        entry = languages[language]["enim"]
        assert lint_senses(language, {"enim": entry}, {"enim": heads["enim"]}) == []
        assert check_note_prose({"language": language, "entries": {"enim": entry}}) == []


@pytest.mark.parametrize(
    ("language", "lemma", "note"),
    [
        (
            "pl",
            "autem",
            "Nigdy nie stoi na pierwszym miejscu w zdaniu — zwykle po pierwszym wyrazie, "
            "czasem po całym zwrocie wziętym za jedno (In diébus autem illis).",
        ),
        (
            "en",
            "autem",
            "It never stands first in its sentence — normally after the first word, "
            "sometimes after a word-group taken as one (In diébus autem illis).",
        ),
        (
            "pl",
            "ex",
            "Przed samogłoską zawsze „ex”. Przed spółgłoską spotyka się i „e”, "
            "i „ex” (ex María Vírgine).",
        ),
        (
            "en",
            "ex",
            "Before a vowel always “ex”. Before a consonant both “e” and “ex” occur "
            "(ex María Vírgine).",
        ),
    ],
)
def test_distinct_source_supported_rules_are_not_softened(language, lemma, note):
    assert emit.lexicon_slice(ROOT, language, {lemma})[lemma]["note"] == note


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize(
    ("text", "word_id"),
    [
        ("orationes.magnificat", "w019"),
        ("proprium.sancti-andreae-apostoli-epistola", "w024"),
        ("proprium.commemoratio-omnium-fidelium-defunctorum-missa-iii-epistola", "w027"),
    ],
)
def test_actual_direct_and_shared_members_keep_the_dictionary_note(language, text, word_id):
    doc, languages = store.load(ROOT, text)
    layer = languages[language]
    assert interlinear.check(doc, layer) == []
    word = next(w for s in doc["segments"] for w in s.get("words", []) if w["id"] == word_id)
    assert word["lemma"] == "enim"
    direct = layer["words"].get(word_id, {}).get("gloss")
    membership = interlinear.alignment_by_word(layer).get(word_id)
    assert bool(direct) != bool(membership)
    assert emit.lexicon_slice(ROOT, language, {word["lemma"]})["enim"]["note"] == NOTES[language]


@pytest.mark.parametrize(("language", "gloss"), [("pl", "więc"), ("en", "then")])
def test_rhetorical_context_is_not_forced_into_one_lexical_equivalent(language, gloss):
    doc, languages = store.load(ROOT, "proprium.dominica-ii-passionis-evangelium")
    assert interlinear.check(doc, languages[language]) == []
    word = next(w for s in doc["segments"] for w in s.get("words", []) if w["id"] == "w961")
    assert word["lemma"] == "enim"
    assert languages[language]["words"]["w961"]["gloss"] == gloss

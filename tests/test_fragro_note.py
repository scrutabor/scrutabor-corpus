"""The shared scent note stays linked, bilingual and visible at its real consumer."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.emit import lexicon_slice
from checks.lexicon import check_note_prose, lint_lemmata, lint_senses, load_lexicon

ROOT = Path(__file__).resolve().parents[1]
NEUTRAL = {
    "head": "fragro, fragráre, fragrávi",
    "pos": "verb",
    "conj": 1,
    "localization": {"note": True},
}
NOTES = {
    "pl": ("Zapach może być przyjemny lub nieprzyjemny. Kontekst wskazuje, o jaką woń chodzi."),
    "en": (
        "The verb can refer to a pleasant or an unpleasant smell. Its sense depends on the context."
    ),
}
SENSES = {
    "pl": ["pachnieć", "wydzielać zapach"],
    "en": ["to give off a scent", "to be fragrant"],
}
FILES = {
    "neutral": "lexicon/lemmata.json",
    "en": "languages/en/lexicon.json",
    "pl": "languages/pl/lexicon.json",
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("language", ["pl", "en"])
def test_actual_fragro_note_is_linked_and_reaches_its_real_card(language):
    heads, languages, errors = load_lexicon(ROOT)
    assert errors == []
    assert heads["fragro"] == NEUTRAL
    assert lint_lemmata({"fragro": heads["fragro"]}) == []
    expected = {"senses": SENSES[language], "note": NOTES[language]}
    assert languages[language]["fragro"] == expected
    assert lint_senses(language, {"fragro": expected}, {"fragro": heads["fragro"]}) == []
    assert check_note_prose({"language": language, "entries": {"fragro": expected}}) == []
    assert lexicon_slice(ROOT, language, {"fragro"}) == {"fragro": expected}
    doc = read(ROOT / "texts/proprium/sanctae-catharinae-senensis-secreta.json")
    word = next(
        word for segment in doc["segments"] for word in segment["words"] if word["id"] == "w016"
    )
    assert (word["form"], word["lemma"]) == ("fragrans", "fragro")


def note_fixture(tmp_path):
    """Copy only the real lemma fragments, never a fabricated prayer or assembly."""
    corpus = tmp_path / "note-contract"
    paths = {}
    for key, relative in FILES.items():
        document = read(ROOT / relative)
        document["entries"] = {"fragro": deepcopy(document["entries"]["fragro"])}
        path = corpus / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document, ensure_ascii=False) + "\n", encoding="utf-8")
        paths[key] = path
    return corpus, paths


@pytest.mark.parametrize("damage", ["neutral-requirement", "en-note", "pl-note"])
def test_real_note_linkage_defects_fail_and_exact_bytes_recover(tmp_path, damage):
    corpus, paths = note_fixture(tmp_path)
    before = {key: path.read_bytes() for key, path in paths.items()}
    healthy = load_lexicon(corpus)
    assert healthy[2] == []
    if damage == "neutral-requirement":
        key = "neutral"
        expected = [
            "lexicon:en:fragro: note has no neutral requirement",
            "lexicon:pl:fragro: note has no neutral requirement",
        ]
    else:
        key = damage.split("-", 1)[0]
        expected = [f"lexicon:{key}:fragro: localized note is required"]
    changed = read(paths[key])
    if key == "neutral":
        del changed["entries"]["fragro"]["localization"]
    else:
        del changed["entries"]["fragro"]["note"]
    try:
        paths[key].write_text(json.dumps(changed, ensure_ascii=False) + "\n", encoding="utf-8")
        assert load_lexicon(corpus)[2] == expected
    finally:
        paths[key].write_bytes(before[key])
    assert {key: path.read_bytes() for key, path in paths.items()} == before
    assert load_lexicon(corpus) == healthy

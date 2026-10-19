"""Reviewed Polish first-person referents in two Requiem Gospel passages."""

import copy
import json
import re
from pathlib import Path

import pytest

from checks.translation_provenance import canonical_hash, check

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "proprium.commemoratio-omnium-fidelium-defunctorum-missa-"
TEXTS = {mass: PREFIX + mass + "-evangelium" for mass in ("ii", "iii")}
CAPTIONS = [
    ("ii", "w033", "meam", "Moją"),
    ("ii", "w086", "ego", "Ja"),
    ("iii", "w008", "Ego", "Ja"),
    ("iii", "w028", "ego", "Ja"),
    ("iii", "w031", "mea", "Moje"),
    ("iii", "w075", "meam", "Moje"),
    ("iii", "w079", "meum", "Moją"),
    ("iii", "w085", "ego", "Ja"),
]
FIRST_PERSON = re.compile(r"\b(?:mi|mnie|moją|mojego|moim|moje|ja)\b", re.IGNORECASE)
EXPECTED_PRONOUNS = {
    "ii": ["Mi", "Mnie", "Mnie", "Moją", "Mnie", "Mnie", "Mi", "Mojego", "Mnie", "Ja"],
    "iii": ["Ja", "Ja", "Moim", "Moje", "Moją", "Ja"],
}


def read(relative, root=ROOT):
    return json.loads((root / relative).read_bytes())


def text_path(mass):
    return "texts/" + TEXTS[mass].replace(".", "/", 1) + ".json"


def layer(mass, root=ROOT):
    return read("languages/pl/" + text_path(mass), root)


def assert_caption(target, word, expected):
    assert target["words"][word]["gloss"] == expected, word


def assert_verse(target, mass):
    actual = FIRST_PERSON.findall(target["segments"]["s01"]["translation"])
    assert actual == EXPECTED_PRONOUNS[mass], TEXTS[mass]


@pytest.mark.parametrize("mass,word,form,expected", CAPTIONS)
def test_jesus_first_person_captions(mass, word, form, expected):
    core = read(text_path(mass))
    words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    assert words[word]["form"] == form
    assert words[word]["lemma"] == ("ego" if form.lower() == "ego" else "meus")
    assert_caption(layer(mass), word, expected)


@pytest.mark.parametrize("mass,word,form,expected", CAPTIONS)
def test_caption_control_rejects_lowercase_and_accepts_restoration(mass, word, form, expected):
    target = layer(mass)
    before = copy.deepcopy(target)
    assert_caption(target, word, expected)
    target["words"][word]["gloss"] = expected.lower()
    with pytest.raises(AssertionError, match=word):
        assert_caption(target, word, expected)
    target = before
    assert_caption(target, word, expected)


@pytest.mark.parametrize("mass", ["ii", "iii"])
def test_continuous_first_person_pronouns(mass):
    assert_verse(layer(mass), mass)


def test_other_speakers_and_addressees_are_not_blanket_capitalized():
    target = layer("iii")
    expected = {"w045": "nam", "w047": "swoje", "w058": "wam", "w072": "sobie", "w087": "go"}
    assert {word: target["words"][word]["gloss"] for word in expected} == expected
    text = target["segments"]["s01"]["translation"]
    assert "Jak On może dać nam swoje ciało do spożycia?" in text
    assert "mówię wam" in text
    assert "życia w sobie" in text


@pytest.mark.parametrize("mass", ["ii", "iii"])
def test_first_person_decisions_remain_inside_jesus_speech(mass):
    core = read(text_path(mass))
    words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}

    def phrase(first, last):
        return " ".join(words[f"w{i:03}"]["form"] for i in range(first, last + 1))

    assert phrase(4, 7) == "Dixit Iesus turbis Iudæórum"
    if mass == "iii":
        assert phrase(36, 41) == "Litigábant ergo Iudǽi ad ínvicem dicéntes"
        assert phrase(51, 54) == "Dixit ergo eis Iesus"
        assert all(
            int(word[1:]) < 36 or int(word[1:]) > 54 for m, word, _, _ in CAPTIONS if m == mass
        )


def write(root, relative, value):
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def provenance_corpus(tmp_path):
    # Real source graph and language dependencies, reduced only to these texts.
    graph = tmp_path / "bibliography/graph.json"
    graph.parent.mkdir(parents=True)
    graph.write_bytes((ROOT / "bibliography/graph.json").read_bytes())
    for mass in TEXTS:
        write(tmp_path, text_path(mass), read(text_path(mass)))
        write(tmp_path, "languages/pl/" + text_path(mass), layer(mass))
    for name, key in (
        ("manifest", "texts"),
        ("translation-provenance", "sites"),
        ("bibliography", "uses"),
    ):
        relative = "languages/pl/" + name + ".json"
        document = read(relative)
        document[key] = (
            [tid for tid in document[key] if tid in TEXTS.values()]
            if name == "manifest"
            else [
                row
                for row in document[key]
                if (row.get("text") if key == "sites" else row.get("address", {}).get("text"))
                in TEXTS.values()
            ]
        )
        write(tmp_path, relative, document)
    return tmp_path


@pytest.mark.parametrize("mass", ["ii", "iii"])
def test_provenance_hash_does_not_replace_speaker_case_review(provenance_corpus, mass):
    root = provenance_corpus
    errors, tally = check(root)
    assert errors == []
    assert sum(tally.values()) == 2
    relative = "languages/pl/" + text_path(mass)
    ledger_path = "languages/pl/translation-provenance.json"
    original_text = (root / relative).read_bytes()
    original_ledger = (root / ledger_path).read_bytes()
    target = layer(mass, root)
    assert_verse(target, mass)
    text = target["segments"]["s01"]["translation"]
    match = FIRST_PERSON.search(text)
    assert match is not None
    target["segments"]["s01"]["translation"] = (
        text[: match.start()] + match.group().lower() + text[match.end() :]
    )
    try:
        write(root, relative, target)
        errors, _ = check(root)
        assert errors == [f"{TEXTS[mass]}.s01.pl: stale target_sha256"]
        ledger = read(ledger_path, root)
        site = next(row for row in ledger["sites"] if row["text"] == TEXTS[mass])
        site["target_sha256"] = canonical_hash(target["segments"]["s01"]["translation"])
        write(root, ledger_path, ledger)
        assert check(root)[0] == []
        with pytest.raises(AssertionError, match=TEXTS[mass]):
            assert_verse(layer(mass, root), mass)
    finally:
        (root / relative).write_bytes(original_text)
        (root / ledger_path).write_bytes(original_ledger)
    assert (root / relative).read_bytes() == original_text
    assert (root / ledger_path).read_bytes() == original_ledger
    assert check(root)[0] == []
    assert_verse(layer(mass, root), mass)

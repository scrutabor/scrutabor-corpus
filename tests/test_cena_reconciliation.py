"""Bounded Holy Thursday regressions; these assertions do not grant editorial acceptance."""

import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest
from cena_secret_fixture import assert_secret_scope

from build_reader import store
from build_reader.bibliography_bindings import BindingError as GraphBindingError
from build_reader.bibliography_bindings import source_dependencies
from checks import interlinear
from checks.raw_binding import BindingError, resolve_binding

ROOT = Path(__file__).resolve().parents[1]
CE = "proprium.feria-v-in-cena-domini-"
GR = "proprium.exaltatio-sanctae-crucis-graduale"
KEY = "do-proprium-exaltatio-sanctae-crucis-graduale"


def load(rel):
    return json.loads((ROOT / rel).read_text())


def layer(language, text):
    return load(f"languages/{language}/texts/{text.replace('.', '/', 1)}.json")


def assert_group(data, first, last, anchor, caption):
    ids = [f"w{n:03}" for n in range(first, last + 1)]
    groups = [a for a in data["segments"]["s01"]["alignments"] if a["words"] == ids]
    assert len(groups) == 1
    assert groups[0]["anchor"] == f"w{anchor:03}"
    assert groups[0]["gloss"] == caption
    assert all("gloss" not in data["words"].get(wid, {}) for wid in ids)


EN = [
    (
        "collecta",
        4,
        14,
        14,
        "both Judas received the punishment of his guilt "
        "and the thief the reward of his confession",
    ),
    ("epistola", 6, 11, 8, "this is no longer eating the Lord’s supper"),
    ("epistola", 14, 18, 16, "begins to eat his own supper first"),
    ("evangelium", 219, 225, 220, "I, the Lord and Master, have washed your feet"),
    ("secreta", 12, 13, 12, "may make acceptable"),
]


@pytest.mark.parametrize("name,first,last,anchor,caption", EN)
def test_complete_english_constructions(name, first, last, anchor, caption):
    data = layer("en", CE + name)
    assert_group(data, first, last, anchor, caption)
    if name == "secreta":
        assert_secret_scope(data)


@pytest.mark.parametrize("index", range(len(EN)))
def test_negative_control_removed_complete_group(index):
    name, first, last, anchor, caption = EN[index]
    data = deepcopy(layer("en", CE + name))
    ids = [f"w{n:03}" for n in range(first, last + 1)]
    data["segments"]["s01"]["alignments"] = [
        a for a in data["segments"]["s01"]["alignments"] if a["words"] != ids
    ]
    with pytest.raises(AssertionError):
        assert_group(data, first, last, anchor, caption)


@pytest.mark.parametrize("name,first,last,anchor,caption", EN)
def test_negative_control_duplicate_group_member(name, first, last, anchor, caption):
    data = deepcopy(layer("en", CE + name))
    for number in range(first, last + 1):
        data["words"].setdefault(f"w{number:03}", {}).pop("gloss", None)
    assert_group(data, first, last, anchor, caption)
    for number in range(first, last + 1):
        duplicate = deepcopy(data)
        duplicate["words"].setdefault(f"w{number:03}", {})["gloss"] = "duplicate"
        with pytest.raises(AssertionError):
            assert_group(duplicate, first, last, anchor, caption)


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize(
    "text",
    [
        CE + name
        for name in (
            "introitus",
            "collecta",
            "epistola",
            "evangelium",
            "secreta",
            "communio",
            "postcommunio",
        )
    ]
    + [GR, "proprium.dominica-iii-post-epiphaniam-offertorium"],
)
def test_all_component_words_have_one_realization(language, text):
    doc, layers = store.load(ROOT, text)
    assert interlinear.check(doc, layers[language]) == []


def test_negative_control_swapped_secret_agent_and_addressee():
    data = layer("en", CE + "secreta")
    frozen = deepcopy(data)
    assert_secret_scope(data)
    bad = deepcopy(data)
    bad["words"]["w001"]["gloss"] = "the Father"
    bad["words"]["w002"]["gloss"] = "to His Son"
    assert bad != data
    with pytest.raises(AssertionError, match=r"^Secret emphatic Christ subject(?:\n|$)"):
        assert_secret_scope(bad)
    assert_secret_scope(data)
    assert data == frozen


PL = [
    (CE + "collecta", 29, 33, 31, "obydwu odpłacił odmiennie według tego, na co zasłużyli"),
    (CE + "collecta", 39, 41, 41, "łaskę swojego zmartwychwstania"),
    (GR, 10, 11, 10, "i to śmierci"),
    (CE + "epistola", 184, 186, 186, "gdybyśmy sami siebie osądzali"),
    (CE + "epistola", 14, 18, 16, "zaczyna wcześniej jeść swoją wieczerzę"),
]


@pytest.mark.parametrize("text,first,last,anchor,caption", PL)
def test_bounded_polish_refinements(text, first, last, anchor, caption):
    assert_group(layer("pl", text), first, last, anchor, caption)


def test_polish_nominal_group_does_not_absorb_following_verb():
    data = layer("pl", CE + "collecta")
    assert data["words"]["w042"]["gloss"] == "darował"
    assert not any("w042" in a["words"] for a in data["segments"]["s01"]["alignments"])


@pytest.mark.parametrize(
    "name,suffixes",
    [
        ("collecta", ["conclusion-rg115c.mr1962"]),
        ("secreta", ["conclusion-rg115c.mr1962"]),
        (
            "postcommunio",
            ["conclusion-middle.mr1962", "conclusion-rg115a.mr1962", "conclusion-terminal.mr1962"],
        ),
    ],
)
def test_composite_witness_level_dependencies(name, suffixes):
    graph = load("bibliography/graph.json")
    text = CE + name
    witness = next(w for w in graph["witnesses"] if w["id"] == f"witness.{text}.mr1962")
    expected = {"uses": sorted(f"use.{text}.{s}" for s in suffixes), "raw_binding": None}
    assert source_dependencies(witness) == expected
    with pytest.raises(GraphBindingError):
        source_dependencies({k: v for k, v in witness.items() if k != "source_dependencies"})


def test_gradual_exact_source_excludes_adjacent_alleluia():
    bound = resolve_binding(ROOT / f"witnesses/{GR}/do.txt", ROOT)
    assert bound is not None
    assert len(bound.text.split()) == 27
    assert bound.text.endswith("quod est super omne nomen.")
    assert "Allelúja" not in bound.text
    assert [f.line for f in bound.fragments] == [36, 37]
    assert bound.fragments[-1].marker == "V"
    assert bound.fragments[-1].marker_scope_verified


def test_negative_control_gradual_includes_adjacent_alleluia(tmp_path):
    registry = load("witnesses/raw/bindings.json")
    record = deepcopy(registry["bindings"][KEY])
    archive = registry["archives"]["do-sancti-09-14"]
    witness_rel = record["witness"]
    for rel in [witness_rel, archive["path"]]:
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, target)
    line = (tmp_path / archive["path"]).read_text().splitlines()[36]
    old_end = record["evidence"][1]["fragment"]["end"]
    record["evidence"][1]["fragment"].update(end=len(line), text=line)
    record["reading"][1]["fragment"]["end"] = len(line)
    text = (tmp_path / witness_rel).read_text()
    text = text.replace(f"chars 0:{old_end}", f"chars 0:{len(line)}")
    (tmp_path / witness_rel).write_text(text)
    (tmp_path / "witnesses/raw/bindings.json").write_text(
        json.dumps(
            {"version": 1, "archives": {"do-sancti-09-14": archive}, "bindings": {KEY: record}}
        )
    )
    with pytest.raises(
        BindingError, match="transcription differs from its exact ordered raw reading"
    ):
        resolve_binding(tmp_path / witness_rel, tmp_path)


def assert_authority_header(text):
    header = text.split("\nIX -")[0]
    assert "printed pp. xxxiii–xxxiv, leaves n38–n39 / PDF pp. 39–40" in header
    assert "registered page images at 300 dpi" in header
    assert "not a diplomatic transcription" in header
    assert "Acute accents in named prayer incipits are supplied" in header
    assert "not a graph-bound archived witness" in header


def test_normalized_authority_has_truthful_bounded_metadata():
    text = (ROOT / "witnesses/raw/mr-rubricae-generales-ix.txt").read_text()
    assert_authority_header(text)
    wrong = text.replace(
        "printed pp. xxxiii–xxxiv, leaves n38–n39 / PDF pp. 39–40", "printed XXXV/n32"
    )
    with pytest.raises(AssertionError):
        assert_authority_header(wrong)
    wrong = text.replace("not a diplomatic transcription", "exact printed lettering and accents")
    with pytest.raises(AssertionError):
        assert_authority_header(wrong)


@pytest.mark.parametrize(
    "language,phrase",
    [
        ("en", "traditional “after supper” interpretation is also possible"),
        ("pl", "Możliwe jest również tradycyjne odczytanie „po wieczerzy”"),
    ],
)
def test_cena_facta_preserves_alternative_and_source_boundary(language, phrase):
    note = layer(language, CE + "evangelium")["words"]["w031"]["explanation"]
    assert phrase in note
    assert "postquam cenavit" in note
    with pytest.raises(AssertionError):
        assert phrase in note.replace(phrase, "only permits an ongoing supper")


def test_institution_first_person_case_and_working_review_are_preserved():
    data = layer("pl", CE + "epistola")
    assert [data["words"][w]["gloss"] for w in ["w084", "w092", "w106", "w113"]] == [
        "Moje",
        "Moją",
        "Mojej",
        "Moją",
    ]
    for language in ["pl", "en"]:
        records = load(f"languages/{language}/translation-provenance.json")["sites"]
        assert all(
            r["review"] == "working" for r in records if r["text"].startswith(CE) or r["text"] == GR
        )


def test_secret_relative_resumes_the_son_not_the_father():
    data = layer("en", CE + "secreta")
    assert data["words"]["w014"]["gloss"] == "He who"
    assert data["words"]["w025"]["gloss"] == "Jesus"
    bad = deepcopy(data)
    bad["words"]["w014"]["gloss"] = "who"
    with pytest.raises(AssertionError):
        assert bad["words"]["w014"]["gloss"] == "He who"


@pytest.mark.parametrize(
    "language,private_phrase",
    [
        ("en", "No Greek textual or patristic source is claimed here"),
        ("pl", "Nie przywołuje się tu"),
    ],
)
def test_cena_facta_public_note_has_no_private_process_disclaimer(language, private_phrase):
    note = layer(language, CE + "evangelium")["words"]["w031"]["explanation"]
    assert private_phrase not in note
    with pytest.raises(AssertionError):
        assert private_phrase not in note + " " + private_phrase


# Direct speech retains the distinction between Jesus and His interlocutor.
DIRECT_SPEECH = [
    ("epistola", "to jest Moje ciało", "to jest moje ciało"),
    ("epistola", "czyńcie to na Moją pamiątkę", "czyńcie to na moją pamiątkę"),
    ("epistola", "w Mojej krwi", "w mojej krwi"),
    (
        "epistola",
        "czyńcie to, ilekroć będziecie pić, na Moją pamiątkę",
        "czyńcie to, ilekroć będziecie pić, na moją pamiątkę",
    ),
    ("evangelium", "Co Ja czynię", "Co ja czynię"),
    ("evangelium", "ze Mną udziału", "ze mną udziału"),
    ("evangelium", "Wy Mnie nazywacie", "Wy mnie nazywacie"),
    ("evangelium", "umyłem wasze nogi Ja, Pan", "umyłem wasze nogi ja, Pan"),
    ("evangelium", "jak Ja wam uczyniłem", "jak ja wam uczyniłem"),
    ("communio", "uczyniłem Ja, Pan", "uczyniłem ja, Pan"),
]


def assert_direct_speech(data, expected, superseded):
    verse = data["segments"]["s01"]["translation"]
    assert verse.count(expected) == 1
    assert superseded not in verse


@pytest.mark.parametrize("name,expected,superseded", DIRECT_SPEECH)
def test_polish_direct_speech_case(name, expected, superseded):
    assert_direct_speech(layer("pl", CE + name), expected, superseded)


@pytest.mark.parametrize("name,expected,superseded", DIRECT_SPEECH)
def test_negative_control_direct_speech_case(name, expected, superseded):
    data = deepcopy(layer("pl", CE + name))
    data["segments"]["s01"]["translation"] = data["segments"]["s01"]["translation"].replace(
        expected, superseded
    )
    with pytest.raises(AssertionError):
        assert_direct_speech(data, expected, superseded)


def test_peter_and_narrative_are_not_capitalized_as_jesus():
    gospel = layer("pl", CE + "evangelium")
    verse = gospel["segments"]["s01"]["translation"]
    assert "Panie, nie tylko moje nogi" in verse
    assert "Jeśli cię nie umyję" in verse
    assert "bo rzeczywiście nim jestem" in verse
    assert gospel["words"]["w133"]["gloss"] == "cię"
    assert gospel["words"]["w146"]["gloss"] == "moje"


@pytest.mark.parametrize(
    "language,perfect,preparation,alternative",
    [
        (
            "pl",
            "imiesłowem dokonanym",
            "przygotowania i podania posiłku",
            "Możliwe jest również tradycyjne odczytanie „po wieczerzy”",
        ),
        (
            "en",
            "perfect participle",
            "meal having been prepared and served",
            "traditional “after supper” interpretation is also possible",
        ),
    ],
)
def test_cena_facta_explains_the_perfect_without_excluding_the_alternative(
    language, perfect, preparation, alternative
):
    note = layer(language, CE + "evangelium")["words"]["w031"]["explanation"]
    for phrase in [perfect, preparation, alternative, "postquam cenavit"]:
        assert phrase in note
        with pytest.raises(AssertionError):
            assert phrase in note.replace(phrase, "[removed]")

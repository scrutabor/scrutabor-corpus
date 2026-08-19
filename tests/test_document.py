"""What a document claims about itself, and what its file says.

Every one of these mutations passed the whole suite before the check existed
(census, 2026-08-19): a text could call itself by another text's id, name a
section that is not a section, carry `sung` as a string, and point its declared
witness path at somebody else's folder.
"""

import json
from pathlib import Path

from checks.document import CATEGORIES, SECTIONS, check

CORPUS = Path(__file__).resolve().parent.parent


def a_text(**over):
    doc = {
        "id": "ordinarium.credo",
        "title": "Credo",
        "category": "ordinarium",
        "section": "missa-fidelium",
        "sung": True,
        "editorial": {
            "source": {
                "witnesses": "witnesses/ordinarium.credo/",
                "apparatus": "witnesses/ordinarium.credo/apparatus.json",
            }
        },
    }
    doc.update(over)
    return doc


PATH = Path("texts/ordinarium/credo.json")


def test_the_corpus_as_it_stands_is_clean():
    errors = []
    for path in sorted(CORPUS.glob("texts/*/*.json")):
        errors += check(json.loads(path.read_text(encoding="utf-8")), path)
    assert errors == []


def test_a_clean_document_passes():
    assert check(a_text(), PATH) == []


def test_an_id_that_does_not_match_its_path_is_refused():
    found = check(a_text(id="orationes.pater-noster"), PATH)
    assert any("calls itself 'orationes.pater-noster'" in e for e in found)


def test_a_category_that_does_not_match_its_directory_is_refused():
    found = check(a_text(category="orationes"), PATH)
    assert any("but the text is stored under 'ordinarium'" in e for e in found)


def test_a_typod_section_is_refused():
    found = check(a_text(section="missa-fideliium"), PATH)
    assert len(found) == 1 and "is not one of the sections this book has" in found[0]


def test_sung_must_be_a_boolean_and_not_a_truthy_string():
    found = check(a_text(sung="true"), PATH)
    assert len(found) == 1 and "sung is JSON true or false" in found[0]


def test_sung_must_be_a_boolean_and_not_a_number():
    # `1 in frozenset((True, False))` is True in Python, which is exactly the
    # way this rule could have been written and been no rule at all.
    found = check(a_text(sung=1), PATH)
    assert len(found) == 1 and "sung is JSON true or false" in found[0]


def test_a_missing_section_is_refused_like_a_wrong_one():
    doc = a_text()
    del doc["section"]
    assert any("section=None" in e for e in check(doc, PATH))


def test_a_witness_path_pointing_at_another_text_is_refused():
    doc = a_text()
    doc["editorial"]["source"]["witnesses"] = "witnesses/ordinarium.gloria/"
    found = check(doc, PATH)
    assert len(found) == 1
    assert found[0] == (
        "ordinarium.credo: source.witnesses declares 'witnesses/ordinarium.gloria/', and "
        "the collation reads 'witnesses/ordinarium.credo/' — the path is derived from the "
        "text id, so a declaration that disagrees with it is read by nobody"
    )


def test_an_apparatus_path_is_held_to_the_same_derivation():
    doc = a_text()
    doc["editorial"]["source"]["apparatus"] = "witnesses/ordinarium.credo/apparatus-old.json"
    assert any("source.apparatus declares" in e for e in check(doc, PATH))


def test_a_text_with_no_apparatus_declared_is_not_made_to_have_one():
    doc = a_text()
    del doc["editorial"]["source"]["apparatus"]
    assert check(doc, PATH) == []


def test_the_vocabularies_are_the_ones_the_corpus_uses():
    # A gate whose vocabulary drifts from the corpus reports on nothing.
    stored_sections, stored_categories = set(), set()
    for path in sorted(CORPUS.glob("texts/*/*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        stored_sections.add(doc["section"])
        stored_categories.add(path.parent.name)
    assert stored_sections == set(SECTIONS)
    assert stored_categories == set(CATEGORIES)

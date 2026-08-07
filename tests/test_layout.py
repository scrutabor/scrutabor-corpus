"""The house layout, which exists so that a diff can be read.

A corpus text is reviewed in diffs far more often than it is read whole. If
a word is spread over fourteen lines, changing one accent produces a
thirty-line hunk and the reviewer stops seeing what changed — so a word
goes on ONE line, and the tool that does it has to be exactly faithful to
what the corpus already holds, or adopting it would have rewritten every
file and buried the corpus's real history under a reformat.
"""

import json

from checks.layout import documents, formatted


def word(**over):
    w = {"id": "w001", "form": "Salve", "lemma": "salveo", "morph": {"pos": "verb", "conj": 2}}
    w.update(over)
    return w


def verse(*words):
    return {"id": "s01", "type": "verse", "words": list(words)}


def doc(**over):
    d = {
        "schema_version": "0.9.0",
        "id": "orationes.test",
        "analysis_defaults": {"confidence": "high", "sources": ["editorial"], "review": "pending"},
        "segments": [{"id": "s01", "type": "verse", "words": [word()]}],
    }
    d.update(over)
    return d


def lines(d) -> list[str]:
    return formatted(d).split("\n")


class TestAWordOnOneLine:
    def test_the_word_and_its_morph_are_one_line(self):
        [only] = [ln.strip() for ln in lines(doc()) if '"w001"' in ln]
        assert only.startswith('{ "id": "w001"')
        assert '"morph": { "pos": "verb", "conj": 2 }' in only

    def test_so_a_text_of_two_words_grows_by_exactly_one_line(self):
        two = doc(segments=[verse(word(), word(id="w002"))])
        assert len(lines(two)) == len(lines(doc())) + 1

    def test_and_an_analysis_override_rides_along_on_it(self):
        analysis = {"confidence": "high", "sources": ["editorial"], "review": "disputed"}
        with_override = doc(segments=[verse(word(analysis=analysis))])
        assert len(lines(with_override)) == len(lines(doc()))


class TestTheGlossLayer:
    """A gloss keys its entries by id instead of carrying the id inside
    them, so "one word to a line" has to be stated for the MAP or every
    gloss in the corpus expands. It did, once, in a draft of this tool."""

    def test_each_gloss_entry_is_one_line(self):
        g = {
            "schema_version": "0.9.0",
            "lang": "pl",
            "words": {"w001": {"gloss": "Witaj", "function": "Tryb rozkazujący."}},
            "segments": {"s01": {"translation": "Witaj."}},
        }
        out = formatted(g)
        assert '"w001": { "gloss": "Witaj", "function": "Tryb rozkazujący." }' in out
        assert '"s01": { "translation": "Witaj." }' in out


class TestFaithfulness:
    def test_formatting_is_idempotent(self):
        once = formatted(doc())
        assert formatted(json.loads(once)) == once

    def test_it_never_changes_what_the_document_says(self):
        d = doc(notes="Génetrix — one spelling throughout", segments=[])
        assert json.loads(formatted(d)) == d

    def test_every_document_in_the_corpus_is_already_in_layout(self):
        # The tool was adopted only because it reproduced 56 of 59 texts
        # byte for byte; the three it did not were files some round-trip had
        # already expanded. This keeps that true.
        off = [
            str(p)
            for p in documents()
            if p.read_text(encoding="utf-8") != formatted(json.loads(p.read_text(encoding="utf-8")))
        ]
        assert off == []

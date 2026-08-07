"""What the gloss layer refuses to say to a reader.

The terminology contract (TERMINOLOGY.md) is not style advice: `ablatiw` is
a Polonized spelling this edition does not use, and an agreement claim has
one wording so that fifty of them read alike. The rules were applied to
every gloss and every translation — and not to `about`, which is the
paragraph the app puts behind the "about this prayer" button and therefore
the most read prose in the layer.
"""

from checks.lint import lint_gloss

TEXT = {
    "id": "orationes.test",
    "segments": [
        {
            "id": "s01",
            "type": "verse",
            "words": [{"id": "w001", "form": "Salve", "lemma": "salveo", "morph": {"pos": "verb"}}],
        }
    ],
}


def gloss(**over):
    g = {
        "schema_version": "0.9.0",
        "text": "orationes.test",
        "lang": "pl",
        "status": "working-edition",
        "analysis_defaults": {"confidence": "high", "sources": ["editorial"], "review": "pending"},
        "segments": {"s01": {"translation": "Witaj."}},
        "words": {"w001": {"gloss": "witaj"}},
    }
    g.update(over)
    return g


class TestTheIntroduction:
    def test_a_clean_one_passes(self):
        assert lint_gloss(gloss(about="Antyfona maryjna okresu wielkanocnego."), TEXT) == []

    def test_a_banned_term_in_it_is_refused(self):
        found = lint_gloss(gloss(about="Rzeczownik stoi w ablatiwie."), TEXT)
        assert any("banned terminology" in e for e in found)

    def test_and_the_approved_spelling_passes(self):
        assert lint_gloss(gloss(about="Rzeczownik stoi w ablativie."), TEXT) == []

    def test_a_layer_with_no_introduction_at_all_is_fine(self):
        # `about` arrived in 0.8.0 and is optional; a missing one must not
        # be read as an empty string that fails some other rule.
        assert lint_gloss(gloss(), TEXT) == []


class TestWhereTheRulesAlreadyApplied:
    def test_a_banned_term_in_a_function_note_is_still_refused(self):
        g = gloss(words={"w001": {"gloss": "witaj", "function": "Stoi w ablatiwie."}})
        assert any("banned terminology" in e for e in lint_gloss(g, TEXT))

    def test_and_in_a_translation(self):
        g = gloss(segments={"s01": {"translation": "Witaj w ablatiwie."}})
        assert any("banned terminology" in e for e in lint_gloss(g, TEXT))

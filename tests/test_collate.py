"""What the collation lets through, and what it will not.

Every rule here is a claim about a printed page, so the tests are written
from the page's side: a witness file and an apparatus, and the question of
whether this edition may print what it prints.
"""

import json
from typing import ClassVar

from checks.collate import collate


def a_text(*forms):
    return {
        "id": "orationes.test",
        "segments": [
            {
                "id": "s01",
                "type": "verse",
                "words": [
                    {"id": f"w{i:03d}", "form": f, "lemma": "x", "morph": {"pos": "noun"}}
                    for i, f in enumerate(forms, 1)
                ],
            }
        ],
    }


def witnesses(tmp_path, pages: dict[str, str], apparatus=None):
    """pages: witness id -> file body, header lines included."""
    d = tmp_path / "witnesses"
    d.mkdir(exist_ok=True)
    for wid, body in pages.items():
        (d / f"{wid}.txt").write_text(f"# witness: {wid}\n{body}\n", encoding="utf-8")
    if apparatus is not None:
        (d / "apparatus.json").write_text(
            json.dumps({"text": "orationes.test", "note": "", "adjudicated": apparatus}),
            encoding="utf-8",
        )
    return d


PAIR = {"a": "cum beato Ioseph", "b": "cum beato Ioseph"}


class TestTheEasyCase:
    def test_two_pages_that_agree_pass(self, tmp_path):
        errors, _, stats = collate(a_text("cum", "beato", "Ioseph"), witnesses(tmp_path, PAIR))
        assert errors == []
        assert stats["witnesses"] == 2

    def test_one_page_is_never_enough(self, tmp_path):
        errors, _, _ = collate(a_text("cum"), witnesses(tmp_path, {"a": "cum"}))
        assert any("full witness" in e for e in errors)


class TestAnInflectedName:
    """Latin took the Hebrew names in twice — Ioseph never changes, Iosephus
    declines — so one page sets `cum beato Ioseph` and another `cum beato
    Iosepho`. Both are the man's name in the ablative."""

    DECLINED: ClassVar = {"a": "cum beato Ioseph", "b": "cum beato Iosepho"}

    def test_it_is_refused_with_no_ruling(self, tmp_path):
        errors, _, _ = collate(a_text("cum", "beato", "Ioseph"), witnesses(tmp_path, self.DECLINED))
        assert any("SUBSTANTIVE divergence" in e for e in errors)

    def test_and_passes_with_one(self, tmp_path):
        app = [
            {
                "at": "w003",
                "ours": "Ioseph",
                "witnesses": {"b": "Iosepho"},
                "class": "inflection",
                "ruling": "Indeclinable, with the other page and with the Canon.",
            }
        ]
        errors, _, stats = collate(
            a_text("cum", "beato", "Ioseph"), witnesses(tmp_path, self.DECLINED, app)
        )
        assert errors == []
        assert stats["inflections"] == 1

    def test_and_is_not_counted_as_a_spelling(self, tmp_path):
        # The whole reason it has its own class: a verdict line reporting
        # `orthographic=2` must never be covering a question about grammar.
        app = [
            {
                "at": "w003",
                "ours": "Ioseph",
                "witnesses": {"b": "Iosepho"},
                "class": "inflection",
                "ruling": "Indeclinable, with the other page and with the Canon.",
            }
        ]
        _, _, stats = collate(
            a_text("cum", "beato", "Ioseph"), witnesses(tmp_path, self.DECLINED, app)
        )
        assert stats["orthographic"] == 0

    def test_a_ruling_of_no_class_at_all_does_not_let_it_through(self, tmp_path):
        app = [
            {
                "at": "w003",
                "ours": "Ioseph",
                "witnesses": {"b": "Iosepho"},
                "class": "accidental",
                "ruling": "…",
            }
        ]
        errors, _, _ = collate(
            a_text("cum", "beato", "Ioseph"), witnesses(tmp_path, self.DECLINED, app)
        )
        assert any("SUBSTANTIVE divergence" in e for e in errors)


class TestAStaleRuling:
    """A ruling that matches nothing on the page it names is a claim about
    that page which the page does not support. This was a warning, and
    twenty-one of them accumulated across two texts before anyone read
    one."""

    def test_is_refused(self, tmp_path):
        app = [
            {
                "at": "w001",
                "ours": "cum",
                "witnesses": {"b": "quum"},
                "class": "orthography",
                "ruling": "…",
            }
        ]
        errors, _, _ = collate(a_text("cum", "beato", "Ioseph"), witnesses(tmp_path, PAIR, app))
        assert any("stale ruling" in e for e in errors)

    def test_and_it_is_an_error_rather_than_a_warning(self, tmp_path):
        app = [
            {
                "at": "w001",
                "ours": "cum",
                "witnesses": {"b": "quum"},
                "class": "orthography",
                "ruling": "…",
            }
        ]
        _, warnings, _ = collate(a_text("cum", "beato", "Ioseph"), witnesses(tmp_path, PAIR, app))
        assert not [w for w in warnings if "stale" in w]

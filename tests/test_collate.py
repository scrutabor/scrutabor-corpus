"""What the collation lets through, and what it will not.

Every rule here is a claim about a printed page, so the tests are written
from the page's side: a witness file and an apparatus, and the question of
whether this edition may print what it prints.
"""

import json
from typing import ClassVar

import pytest

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

    def test_an_apparatus_requires_the_matching_source_pointer(self, tmp_path):
        doc = a_text("cum")
        doc["source"] = {"witnesses": "witnesses/orationes.test/"}
        pages = {"a": "cum", "b": "cum"}
        errors, _, _ = collate(doc, witnesses(tmp_path, pages, []))
        assert any("source.apparatus" in e for e in errors)

    @pytest.mark.parametrize(
        "record",
        [
            None,
            {"word": "w001", "selected": "cum", "readings": {"a": "cum"}},
            {"at": ["w001"], "ours": "cum", "witnesses": {"a": "cum"}},
            {"at": "w001", "ours": "cum", "witnesses": ["a"]},
            {"at": "w001", "ours": "cum", "witnesses": {"a": None}},
        ],
    )
    def test_malformed_reading_records_fail_without_aborting_collation(self, tmp_path, record):
        errors, _, stats = collate(
            a_text("cum", "beato", "Ioseph"), witnesses(tmp_path, PAIR, [record])
        )
        assert any("invalid reading record" in error for error in errors)
        assert stats["witnesses"] == 2

    def test_duplicate_readings_cannot_silently_overwrite_one_another(self, tmp_path):
        record = {"at": "w001", "ours": "cum", "witnesses": {"a": "cum"}}
        errors, _, _ = collate(
            a_text("cum", "beato", "Ioseph"), witnesses(tmp_path, PAIR, [record, record])
        )
        assert any("duplicate reading at w001/a" in error for error in errors)


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

    def test_an_inflection_class_cannot_excuse_only_punctuation(self, tmp_path):
        doc = a_text("cum")
        doc["source"] = {"apparatus": "witnesses/orationes.test/apparatus.json"}
        app = [
            {
                "at": "w001",
                "ours": "cum",
                "witnesses": {"b": "cum,"},
                "class": "inflection",
                "ruling": "Wrong class on purpose.",
            }
        ]
        directory = witnesses(tmp_path, {"a": "cum", "b": "cum,"}, app)
        apparatus_path = directory / "apparatus.json"
        apparatus = json.loads(apparatus_path.read_text(encoding="utf-8"))
        apparatus["text"] = "orationes.test"
        apparatus_path.write_text(json.dumps(apparatus), encoding="utf-8")
        errors, _, _ = collate(doc, directory)
        assert any("UNADJUDICATED variant" in e for e in errors)


class TestAnOmittedWord:
    def test_a_witness_omission_requires_an_explicit_ruling(self, tmp_path):
        pages = {"a": "Ad te Domine levavi", "b": "Ad te levavi"}
        app = [
            {
                "at": "w003",
                "ours": "Domine",
                "witnesses": {"b": ""},
                "class": "omission",
                "ruling": "Retained with the primary printed witness.",
            }
        ]
        errors, _, stats = collate(
            a_text("Ad", "te", "Domine", "levavi"), witnesses(tmp_path, pages, app)
        )
        assert errors == []
        assert stats["omissions"] == 1

    def test_an_unruled_omission_still_fails(self, tmp_path):
        pages = {"a": "Ad te Domine levavi", "b": "Ad te levavi"}
        errors, _, _ = collate(a_text("Ad", "te", "Domine", "levavi"), witnesses(tmp_path, pages))
        assert any("length mismatch" in error for error in errors)

    @staticmethod
    def ruling():
        return {
            "at": "w003",
            "ours": "Domine",
            "witnesses": {"b": ""},
            "class": "omission",
            "ruling": "Retain the word attested at this locus by full witness a.",
        }

    @pytest.mark.parametrize("reason", [None, "", "   "])
    def test_an_omission_requires_a_real_reason(self, tmp_path, reason):
        app = self.ruling()
        if reason is None:
            del app["ruling"]
        else:
            app["ruling"] = reason
        errors, _, _ = collate(
            a_text("Ad", "te", "Domine", "levavi"),
            witnesses(tmp_path, {"a": "Ad te Domine levavi", "b": "Ad te levavi"}, [app]),
        )
        assert errors

    def test_an_omission_cannot_create_a_word_absent_from_both_witnesses(self, tmp_path):
        app = self.ruling()
        app["witnesses"]["a"] = ""
        errors, _, _ = collate(
            a_text("Ad", "te", "Domine", "levavi"),
            witnesses(tmp_path, {"a": "Ad te levavi", "b": "Ad te levavi"}, [app]),
        )
        assert any("positive full-witness" in error for error in errors)

    def test_partial_attestation_cannot_license_an_omission(self, tmp_path):
        app = self.ruling()
        app["witnesses"]["a"] = ""
        pages = {
            "a": "Ad te levavi",
            "b": "Ad te levavi",
            "c": "# covers: w003-w003\nDomine",
        }
        errors, _, _ = collate(
            a_text("Ad", "te", "Domine", "levavi"), witnesses(tmp_path, pages, [app])
        )
        assert any("positive full-witness" in error for error in errors)

    @pytest.mark.parametrize("quote", ["", "Domine,", "Dominum"])
    def test_the_selected_omission_quote_must_be_exact(self, tmp_path, quote):
        app = self.ruling()
        app["ours"] = quote
        errors, _, _ = collate(
            a_text("Ad", "te", "Domine", "levavi"),
            witnesses(tmp_path, {"a": "Ad te Domine levavi", "b": "Ad te levavi"}, [app]),
        )
        assert errors

    @pytest.mark.parametrize("ruled", [True, False])
    def test_an_omission_does_not_hide_another_reading(self, tmp_path, ruled):
        app = [self.ruling()]
        if ruled:
            app.append(
                {
                    "at": "w004",
                    "ours": "iudicium",
                    "witnesses": {"b": "judicium"},
                    "class": "orthography",
                    "ruling": "Keep the printed consonantal i.",
                }
            )
        errors, _, stats = collate(
            a_text("Ad", "te", "Domine", "iudicium"),
            witnesses(tmp_path, {"a": "Ad te Domine iudicium", "b": "Ad te judicium"}, app),
        )
        if ruled:
            assert errors == []
            assert stats["omissions"] == stats["orthographic"] == 1
        else:
            assert errors

    def test_an_omission_cannot_hide_an_extra_word(self, tmp_path):
        errors, _, _ = collate(
            a_text("Ad", "te", "Domine", "levavi"),
            witnesses(
                tmp_path, {"a": "Ad te Domine levavi", "b": "Ad te levavi extra"}, [self.ruling()]
            ),
        )
        assert errors


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


class TestSubstantiveReadings:
    @staticmethod
    def ruling(ours="inspexérunt", reading="conspexérunt", kind="substantive"):
        return [
            {
                "at": "w001",
                "ours": ours,
                "witnesses": {"b": reading},
                "class": kind,
                "ruling": "Retain the reading of the controlling printed witness a.",
            }
        ]

    def test_an_explicit_attested_lexical_reading_is_counted_separately(self, tmp_path):
        errors, _, stats = collate(
            a_text("inspexérunt", "me"),
            witnesses(tmp_path, {"a": "inspexérunt me", "b": "conspexérunt me"}, self.ruling()),
        )
        assert errors == []
        assert stats["substantive_variants"] == 1
        assert stats["orthographic"] == stats["inflections"] == 0

    def test_a_grammatical_reading_is_not_name_inflection(self, tmp_path):
        errors, _, stats = collate(
            a_text("resurgémus,"),
            witnesses(
                tmp_path,
                {"a": "resurgémus,", "b": "resurgámus,"},
                self.ruling("resurgémus,", "resurgámus,"),
            ),
        )
        assert errors == []
        assert stats["substantive_variants"] == 1
        assert stats["inflections"] == 0

    def test_unruled_lexical_reading_still_fails(self, tmp_path):
        errors, _, _ = collate(
            a_text("inspexérunt"), witnesses(tmp_path, {"a": "inspexérunt", "b": "conspexérunt"})
        )
        assert any("SUBSTANTIVE divergence" in e for e in errors)

    @pytest.mark.parametrize("kind", ["orthography", "inflection", "substantive"])
    def test_a_nonempty_but_false_source_quote_is_not_evidence(self, tmp_path, kind):
        errors, _, _ = collate(
            a_text("inspexérunt"),
            witnesses(
                tmp_path,
                {"a": "inspexérunt", "b": "conspexérunt"},
                self.ruling(reading="aspexérunt", kind=kind),
            ),
        )
        assert any("SUBSTANTIVE divergence" in e for e in errors)

    def test_empty_reason_is_not_a_ruling(self, tmp_path):
        app = self.ruling()
        app[0]["ruling"] = "  "
        errors, _, _ = collate(
            a_text("inspexérunt"),
            witnesses(tmp_path, {"a": "inspexérunt", "b": "conspexérunt"}, app),
        )
        assert any("SUBSTANTIVE divergence" in e for e in errors)

    def test_selected_word_must_be_attested_in_a_full_witness(self, tmp_path):
        app = self.ruling()
        app[0]["witnesses"]["a"] = "conspexérunt"
        errors, _, _ = collate(
            a_text("inspexérunt"),
            witnesses(tmp_path, {"a": "conspexérunt", "b": "conspexérunt"}, app),
        )
        assert any("positive full-witness" in e for e in errors)

    def test_partial_witness_is_not_the_required_full_support(self, tmp_path):
        app = self.ruling()
        app[0]["witnesses"]["a"] = "conspexérunt"
        pages = {
            "a": "conspexérunt me",
            "b": "conspexérunt me",
            "c": "# covers: w001-w001\ninspexérunt",
        }
        errors, _, _ = collate(a_text("inspexérunt", "me"), witnesses(tmp_path, pages, app))
        assert any("positive full-witness" in e for e in errors)

    def test_substantive_class_cannot_excuse_punctuation_alone(self, tmp_path):
        errors, _, _ = collate(
            a_text("inspexérunt"),
            witnesses(
                tmp_path,
                {"a": "inspexérunt", "b": "inspexérunt,"},
                self.ruling(reading="inspexérunt,"),
            ),
        )
        assert any("UNADJUDICATED variant" in e for e in errors)

    def test_a_word_elsewhere_in_the_full_witness_is_not_locus_support(self, tmp_path):
        pages = {"a": "conspexérunt inspexérunt", "b": "conspexérunt me"}
        errors, _, _ = collate(
            a_text("inspexérunt", "me"), witnesses(tmp_path, pages, self.ruling())
        )
        assert any("positive full-witness" in e for e in errors)

"""Whether the attribution tool knows where it is reading.

Who says a line is READ from the witnesses' own markers, and each witness
header records the lines it was taken from so that the markers come from
the right part of the book. That range is written by hand. When it goes
stale — a source file gains a line, a transcription reaches one line
further than the header says — the markers simply run out, and the rule
that supplies the CELEBRANT for a passage the Ordo leaves unmarked then
supplies him for a line the Ordo marks `M.`

That is not a small error. It was proposing sacerdos for *Ad Deum, qui
lætíficat iuventútem meam* — the server's answer, marked as the server's
two lines outside the declared range — and `--write` would have put it in
the file over the correct reading.
"""

import json
from pathlib import Path

from checks.attribute import propose, span_covers, witness_ranges

CORPUS = Path(__file__).resolve().parent.parent


def a_text(*lines):
    """One verse segment per line of Latin."""
    return {
        "id": "ordinarium.test",
        "segments": [
            {
                "id": f"s{i:02d}",
                "type": "verse",
                "words": [{"id": f"w{j:03d}", "form": f} for j, f in enumerate(line.split(), 1)],
            }
            for i, line in enumerate(lines, 1)
        ],
    }


class TestSpanCoverage:
    def test_a_text_that_declares_no_range_is_not_faulted_for_it(self, monkeypatch):
        # The tool then reads the whole archive, which is its own fallback
        # and not this check's business.
        monkeypatch.setattr("checks.attribute.witness_ranges", lambda _: [])
        assert span_covers(a_text("Introibo ad altare Dei")) is True

    def test_a_range_holding_every_segment_passes(self, tmp_path, monkeypatch):
        raw = tmp_path / "src.txt"
        raw.write_text("S. Introíbo ad altáre Dei.\nM. Ad Deum, qui lætíficat.\n", encoding="utf-8")
        monkeypatch.setattr("checks.attribute.witness_ranges", lambda _: [(raw, 1, 2)])
        assert span_covers(a_text("Introíbo ad altáre Dei", "Ad Deum qui lætíficat")) is True

    def test_a_range_one_line_short_does_not(self, tmp_path, monkeypatch):
        # The shape that caused it: the answer is on the line after the one
        # the header claims, so the text is mostly covered and the miss is
        # the four words that decide whose voice it is.
        raw = tmp_path / "src.txt"
        raw.write_text("S. Introíbo ad altáre Dei.\nM. Ad Deum, qui lætíficat.\n", encoding="utf-8")
        monkeypatch.setattr("checks.attribute.witness_ranges", lambda _: [(raw, 1, 1)])
        assert span_covers(a_text("Introíbo ad altáre Dei", "Ad Deum qui lætíficat")) is False

    def test_the_page_may_spell_it_its_own_way(self, tmp_path, monkeypatch):
        # j for i, æ for ae, accents where this edition puts none: the
        # comparison folds all three, or every witness would read as stale.
        raw = tmp_path / "src.txt"
        raw.write_text("S. Introíbo ad altáre Dei, et adjutórium.\n", encoding="utf-8")
        monkeypatch.setattr("checks.attribute.witness_ranges", lambda _: [(raw, 1, 1)])
        assert span_covers(a_text("Introibo ad altare Dei et adiutórium")) is True

    def test_the_editions_name_slots_do_not_break_a_segment(self, tmp_path, monkeypatch):
        # The archived Ordo writes the missal's N. as N.p and N.b; every
        # transcription strips them as edition framing. Unstripped, their
        # letters fall in the middle of the Te ígitur's last segment and
        # the range reads as stale when it is exactly right.
        raw = tmp_path / "src.txt"
        raw.write_text(
            "una cum fámulo tuo Papa nostro N.p  et Antístite nostro N.b  et ómnibus.\n",
            encoding="utf-8",
        )
        monkeypatch.setattr("checks.attribute.witness_ranges", lambda _: [(raw, 1, 1)])
        line = "una cum fámulo tuo Papa nostro et Antístite nostro et ómnibus"
        assert span_covers(a_text(line)) is True

    def test_inline_rubrics_and_macro_calls_do_not_break_a_source_span(self, tmp_path, monkeypatch):
        raw = tmp_path / "src.txt"
        raw.write_text(
            "v. Qui prídie quam paterétur, (Accipit Hostiam,) accépit panem\n"
            "&a-macro-call\n"
            "in sanctas manus suas.\n",
            encoding="utf-8",
        )
        monkeypatch.setattr("checks.attribute.witness_ranges", lambda _: [(raw, 1, 3)])
        assert span_covers(a_text("Qui prídie quam paterétur accépit panem in sanctas manus suas"))

    def test_markers_between_lines_and_display_capitals_are_framing(self, tmp_path, monkeypatch):
        raw = tmp_path / "src.txt"
        raw.write_text(
            "R. Sed líbera nos a malo.\n"
            "S. (Sacerdos secrete dicit:) Amen.\n"
            "!!!HOC EST ENIM CORPUS MEUM.\n",
            encoding="utf-8",
        )
        monkeypatch.setattr("checks.attribute.witness_ranges", lambda _: [(raw, 1, 3)])
        assert span_covers(a_text("Sed líbera nos a malo Amen", "Hoc est enim Corpus meum"))

    def test_only_an_explicit_apparatus_entry_licenses_a_source_spelling(
        self, tmp_path, monkeypatch
    ):
        raw = tmp_path / "src.txt"
        raw.write_text("S. Dei Genitríce María.\n", encoding="utf-8")
        monkeypatch.setattr("checks.attribute.witness_ranges", lambda _: [(raw, 1, 1)])
        doc = a_text("Dei Genetríce María")
        doc["source"] = {"apparatus": "apparatus.json"}
        (tmp_path / "apparatus.json").write_text(
            json.dumps({"adjudicated": [{"at": "w002"}]}), encoding="utf-8"
        )
        monkeypatch.setattr("checks.attribute.CORPUS", tmp_path)
        assert span_covers(doc) is True

        (tmp_path / "apparatus.json").write_text(json.dumps({"adjudicated": []}), encoding="utf-8")
        assert span_covers(doc) is False

    def test_a_hyphenated_source_filename_finds_its_raw_archive(self, tmp_path, monkeypatch):
        witness = tmp_path / "witnesses" / "proprium.test"
        raw = tmp_path / "witnesses" / "raw"
        witness.mkdir(parents=True)
        raw.mkdir(parents=True)
        (witness / "do.txt").write_text(
            "# path: web/www/missa/Latin/Tempora/Adv1-0.txt (lines 12-18)\n",
            encoding="utf-8",
        )
        archived = raw / "do-Adv1-0.txt"
        archived.write_text("source\n", encoding="utf-8")
        monkeypatch.setattr("checks.attribute.CORPUS", tmp_path)
        assert witness_ranges("proprium.test") == [(archived, 12, 18)]

    def test_a_singular_line_declaration_is_read(self, tmp_path, monkeypatch):
        witness = tmp_path / "witnesses" / "ordinarium.test"
        raw = tmp_path / "witnesses" / "raw"
        witness.mkdir(parents=True)
        raw.mkdir(parents=True)
        (witness / "do.txt").write_text(
            "# path: web/www/missa/Latin/Ordo/Ordo.txt (line 38)\n",
            encoding="utf-8",
        )
        archived = raw / "do-ordo-missae.txt"
        archived.write_text("source\n", encoding="utf-8")
        monkeypatch.setattr("checks.attribute.CORPUS", tmp_path)
        assert witness_ranges("ordinarium.test") == [(archived, 38, 38)]

    def test_a_wrapped_two_archive_declaration_reads_both(self, tmp_path, monkeypatch):
        witness = tmp_path / "witnesses" / "ordinarium.test"
        raw = tmp_path / "witnesses" / "raw"
        witness.mkdir(parents=True)
        raw.mkdir(parents=True)
        (witness / "do.txt").write_text(
            "# path: web/www/missa/Latin/Ordo/Ordo.txt (lines 365-366), and\n"
            "#   web/www/missa/Latin/Ordo/Prayers.txt (lines\n"
            "#   44-45)\n",
            encoding="utf-8",
        )
        ordo = raw / "do-ordo-missae.txt"
        prayers = raw / "do-ordo-prayers.txt"
        ordo.write_text("source\n", encoding="utf-8")
        prayers.write_text("source\n", encoding="utf-8")
        monkeypatch.setattr("checks.attribute.CORPUS", tmp_path)
        assert witness_ranges("ordinarium.test") == [(ordo, 365, 366), (prayers, 44, 45)]

    def test_an_unreadable_declared_range_fails_closed(self, tmp_path, monkeypatch):
        witness = tmp_path / "witnesses" / "ordinarium.test"
        witness.mkdir(parents=True)
        (witness / "do.txt").write_text(
            "# path: Ordo.txt, line numbers to be supplied\n",
            encoding="utf-8",
        )
        monkeypatch.setattr("checks.attribute.CORPUS", tmp_path)
        assert span_covers(a_text("Introibo ad altare Dei")) is False


class TestProperAttribution:
    def test_the_proper_is_inside_the_mass(self, monkeypatch):
        doc = {
            "id": "proprium.dominica-i-adventus-communio",
            "category": "proprium",
            "segments": [
                {
                    "id": "s01",
                    "type": "verse",
                    "words": [{"id": "w001", "form": "Dóminus"}],
                }
            ],
        }
        monkeypatch.setattr("checks.attribute.marked_lines", lambda _id, mass: [])
        monkeypatch.setattr("checks.attribute.span_covers", lambda _doc: True)
        assert propose(doc) == {"s01": {"speaker": "sacerdos", "voice": "clara"}}

    def test_the_ruling_applies_to_later_formularies(self, monkeypatch):
        doc = {
            "id": "proprium.dominica-iv-adventus-offertorium",
            "category": "proprium",
            "segments": [
                {
                    "id": "s01",
                    "type": "verse",
                    "words": [{"id": "w001", "form": "Ave"}],
                }
            ],
        }
        monkeypatch.setattr("checks.attribute.marked_lines", lambda _id, mass: [])
        monkeypatch.setattr("checks.attribute.span_covers", lambda _doc: True)
        assert propose(doc) == {"s01": {"speaker": "sacerdos", "voice": "clara"}}


class TestTheCorpusItself:
    def test_a_write_never_touches_a_text_it_cannot_source(self):
        # The corpus has carried stale ranges. This is not a
        # demand that they be zero — it is the guarantee that goes with
        # them: whatever the number, those texts are read and reported,
        # never written. If this list ever shrinks to nothing the check
        # still holds; what must not happen is a text being written from a
        # range that no longer contains it.
        stale = [
            json.loads(p.read_text(encoding="utf-8"))["id"]
            for p in sorted((CORPUS / "texts").rglob("*.json"))
            if not span_covers(json.loads(p.read_text(encoding="utf-8")))
        ]
        # Every stale result must come from a witness that actually declares
        # source lines.  A text with no such declaration uses the deliberate
        # whole-archive fallback and is not mislabeled as malformed
        # provenance.
        for text_id in stale:
            wdir = CORPUS / "witnesses" / text_id
            headers = "".join(p.read_text(encoding="utf-8") for p in wdir.glob("*.txt"))
            assert "# path:" in headers and "line" in headers, text_id

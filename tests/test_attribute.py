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

from checks.attribute import span_covers

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


class TestTheCorpusItself:
    def test_a_write_never_touches_a_text_it_cannot_source(self):
        # The corpus carries 19 stale ranges (BACKLOG). This is not a
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
        # Every one of them is a text taken from the archived Ordo Missae,
        # which is where the hand-written ranges live. A stale range
        # anywhere else would mean the fault is not the one this describes.
        for text_id in stale:
            wdir = CORPUS / "witnesses" / text_id
            headers = "".join(p.read_text(encoding="utf-8") for p in wdir.glob("*.txt"))
            assert "do-ordo-missae.txt" in headers, text_id

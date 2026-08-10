"""The participation layer: what the faithful say, and what they do not.

These are the cases that would be wrong if the rule were written loosely —
each one is a line the corpus actually carries.
"""

import json
from pathlib import Path
from typing import Any, ClassVar

from checks.participation import LAW, check_doc, derive

CORPUS = Path(__file__).resolve().parent.parent


def text(text_id: str) -> dict[str, Any]:
    category, name = text_id.split(".", 1)
    return json.loads((CORPUS / "texts" / category / f"{name}.json").read_text(encoding="utf-8"))


def segment(doc: dict[str, Any], seg_id: str) -> dict[str, Any]:
    return next(s for s in doc["segments"] if s["id"] == seg_id)


def part(text_id: str, seg_id: str) -> dict[str, Any]:
    doc = text(text_id)
    return derive(doc, segment(doc, seg_id))


class TestFirstDegree:
    """n. 31 a and n. 25 a — the responses a reader meets at every Mass."""

    def test_the_dialogue_response_is_theirs_at_either_kind_of_mass(self):
        assert part("ordinarium.praefatio-dialogus", "s03") == {
            "lecta": {"gradus": 1, "source": "DMS 31 a"},
            "cantu": {"gradus": 1, "source": "DMS 25 a"},
        }

    def test_deo_gratias_at_the_dismissal(self):
        assert part("ordinarium.ite-missa-est", "s06")["lecta"]["gradus"] == 1

    def test_the_amen_of_the_doxology(self):
        assert part("ordinarium.per-ipsum", "s09")["lecta"]["source"] == "DMS 31 a"


class TestTheAmensThatAreNotTheirs:
    """The reason the speaker is part of the test and not the text alone."""

    def test_the_priest_answering_the_server_keeps_his_own_amen(self):
        # misereatur-tui s03: the celebrant's Amen after the server's prayer
        # for him. Reads exactly like the enumeration in n. 31 a and is not
        # a response of the faithful.
        assert part("ordinarium.misereatur-tui", "s03") == {}

    def test_the_amen_said_submissa_after_the_suscipiat_is_not_theirs(self):
        assert part("ordinarium.orate-fratres", "s06") == {}

    def test_but_the_amen_closing_the_pater_is_theirs_by_n_32(self):
        # n. 32: "addito ab omnibus Amen" — theirs, on a different title,
        # and so without a gradus, because n. 32 grades nothing.
        assert part("ordinarium.pater-noster", "s14") == {"lecta": {"source": "DMS 32"}}


class TestTheServersOtherParts:
    """n. 31 b — the parts the rubrics give the minister."""

    def test_the_suscipiat_is_second_degree_at_a_low_mass(self):
        assert part("ordinarium.orate-fratres", "s04") == {
            "lecta": {"gradus": 2, "source": "DMS 31 b"}
        }

    def test_the_ministers_confiteor_is_second_degree(self):
        assert part("ordinarium.confiteor", "s02")["lecta"]["source"] == "DMS 31 b"

    def test_and_none_of_them_is_given_at_a_sung_mass(self):
        # n. 25 a is a closed list of seven responses; the server's other
        # parts are not on it, and n. 25 b names only the Ordinary.
        assert "cantu" not in part("ordinarium.orate-fratres", "s04")


class TestTheOrdinary:
    """n. 31 c and n. 25 b — said or sung with the celebrant."""

    def test_the_sanctus_is_theirs_at_both_kinds_of_mass(self):
        assert part("ordinarium.sanctus", "s02") == {
            "lecta": {"gradus": 3, "source": "DMS 31 c"},
            "cantu": {"gradus": 2, "source": "DMS 25 b"},
        }

    def test_the_kyrie_is_sung_by_all_but_not_recited_by_all(self):
        # The Kyrie stands in n. 25 b and NOT in n. 31 c. At a low Mass the
        # people's title to it is that it is the server's part, so the
        # celebrant's own invocations carry a sung attribution only.
        priests = part("ordinarium.kyrie", "s02")
        assert priests == {"cantu": {"gradus": 2, "source": "DMS 25 b"}}
        servers = part("ordinarium.kyrie", "s03")
        assert servers["lecta"] == {"gradus": 2, "source": "DMS 31 b"}
        assert servers["cantu"] == {"gradus": 2, "source": "DMS 25 b"}


class TestTheProper:
    """nn. 31 d and 25 c — the Proper recited or sung by the faithful."""

    def test_the_four_recited_propers_are_fourth_degree(self):
        assert part("proprium.dominica-i-adventus-introitus", "s01") == {
            "lecta": {"gradus": 4, "source": "DMS 31 d"},
            "cantu": {"gradus": 3, "source": "DMS 25 c"},
        }
        assert part("proprium.dominica-i-adventus-graduale", "s01")["lecta"] == {
            "gradus": 4,
            "source": "DMS 31 d",
        }

    def test_the_alleluia_is_sung_but_not_in_the_recited_fourth_degree(self):
        assert part("proprium.dominica-i-adventus-alleluia", "s02") == {
            "cantu": {"gradus": 3, "source": "DMS 25 c"}
        }

    def test_a_prayer_of_the_proper_takes_neither_attribution(self):
        assert part("proprium.dominica-i-adventus-collecta", "s01") == {}

    def test_the_readings_are_read_TO_the_people_at_either_mass(self):
        # The rule keys on the genus of the piece and not on the document's
        # `sung` flag, which answers a different question: at a solemn Mass
        # the Epistle and the Gospel are chanted, and the people sing
        # neither. Marking either sung must not hand it to them.
        for piece in ("epistola", "evangelium"):
            doc = text(f"proprium.dominica-i-adventus-{piece}")
            doc["sung"] = True
            assert derive(doc, doc["segments"][0]) == {}, piece

    def test_a_response_inside_a_proper_still_gets_its_own_title(self):
        # Laus tibi, Christe stands in n. 31 a and in no other list, and it
        # is the answer after the GOSPEL — so it can only ever live in a
        # proper text. The proper rules must not swallow the segment before
        # the response rules see it.
        doc = text("proprium.dominica-i-adventus-evangelium")
        response = {
            "id": "s99",
            "type": "verse",
            "speaker": "minister",
            "words": [
                {"id": "w1", "form": "Laus"},
                {"id": "w2", "form": "tibi"},
                {"id": "w3", "form": "Christe", "post": "."},
            ],
        }
        assert derive(doc, response) == {
            "lecta": {"gradus": 1, "source": "DMS 31 a"},
        }

    def test_a_genus_the_module_has_never_seen_is_reported(self):
        # n. 25 c grants the whole Proper, so a piece with no ruling means
        # this module is behind the corpus — not that the piece is nobody's.
        doc = text("proprium.dominica-i-adventus-graduale")
        doc["id"] = "proprium.dominica-i-adventus-tropus"
        errors, _ = check_doc(doc)
        assert any("no ruling" in e for e in errors), errors


class TestThePaterNoster:
    """n. 32 — the whole prayer, and only the prayer."""

    def test_the_prayer_itself_is_theirs(self):
        assert part("ordinarium.pater-noster", "s05") == {"lecta": {"source": "DMS 32"}}

    def test_but_not_the_preface_that_introduces_it(self):
        # "Orémus" and "Præceptis salutaribus moniti" lead into the Pater
        # noster; n. 32 gives the faithful totum Pater noster, not its
        # introduction.
        assert part("ordinarium.pater-noster", "s02") == {}
        assert part("ordinarium.pater-noster", "s03") == {}

    def test_and_the_response_keeps_its_own_and_better_title(self):
        assert part("ordinarium.pater-noster", "s12")["lecta"]["source"] == "DMS 31 a"


class TestWhatTheLawDoesNotReach:
    OUTSIDE: ClassVar[list[str]] = [
        "orationes.salve-regina",
        "orationes.sancte-michael",
        "orationes.ave-maria",
    ]

    def test_the_devotional_prayers_take_nothing_from_a_law_about_the_mass(self):
        for text_id in self.OUTSIDE:
            doc = text(text_id)
            for seg in doc["segments"]:
                assert derive(doc, seg) == {}, f"{text_id} {seg['id']}"

    def test_a_rubric_is_nobody_s_line(self):
        doc = text("ordinarium.pater-noster")
        assert derive(doc, segment(doc, "s01")) == {}


class TestTheCorpusAgrees:
    def test_every_text_carries_what_the_law_derives(self):
        problems = []
        for path in sorted(CORPUS.glob("texts/*/*.json")):
            doc = json.loads(path.read_text(encoding="utf-8"))
            errors, _ = check_doc(doc)
            problems += [f"{doc['id']} {e}" for e in errors]
        assert problems == []

    def test_the_law_is_archived_in_the_corpus(self):
        # The attributions are worth nothing if the source is not in the
        # repository with them.
        archived = (CORPUS / LAW).read_text(encoding="utf-8")
        assert "31. Tertius denique isque plenior modus obtinetur" in archived
        assert "25. In Missa itaque solemni" in archived
        assert "eadem prorsus valent etiam pro Missa cantata" in archived

"""The four Advent Sundays as the Missal assembles them.

Pages 2, 4, 5 and 15 print the Preface of the Holy Trinity for these Sundays, and the
expanded Secret and Postcommunion conclusions follow the edition's own full printing
of the formula (p. 123: Fílium tuum: Qui tecum vivit ...), as the other expanded
conclusions of the corpus do. The Fourth Sunday's Offertory is the Ave Maria verse and is
protected as that familiar formula, like the two Annunciation Offertories.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUNDAYS = ("i", "ii", "iii", "iv")


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_advent_sundays_assign_the_trinity_preface_after_the_secret():
    for sunday in SUNDAYS:
        formulary = load(f"formularies/temporale/dominica-{sunday}-adventus.json")
        keys = [component["key"] for component in formulary["components"]]
        prefaces = [c for c in formulary["components"] if c["role"] == "praefatio"]
        trinity = ["ordinarium.praefatio-sanctissimae-trinitatis"]
        assert [c["text"] for c in prefaces] == trinity, sunday
        assert prefaces[0]["relation"] == "shared" and "condition" not in prefaces[0], sunday
        assert keys.index("praefatio") == keys.index("secreta") + 1, sunday


def test_advent_expanded_conclusions_follow_the_printed_formula():
    for sunday in SUNDAYS:
        for part in ("secreta", "postcommunio"):
            text = load(f"texts/proprium/dominica-{sunday}-adventus-{part}.json")
            words = [word for segment in text["segments"] for word in segment.get("words", [])]
            forms = [word["form"] for word in words]
            last = len(forms) - 1 - forms[::-1].index("Fílium")
            tuum = words[last + 1]
            assert tuum["form"] == "tuum" and tuum.get("post") == ":", (sunday, part)
            assert words[last + 2]["form"] == "Qui", (sunday, part)


def test_the_fourth_sunday_offertory_is_protected_as_the_ave_maria():
    text_id = "proprium.dominica-iv-adventus-offertorium"
    for language in ("pl", "en"):
        provenance = load(f"languages/{language}/translation-provenance.json")
        site = next(s for s in provenance["sites"] if s["site"] == f"{text_id}.s01.{language}")
        assert site["familiar_core"] is True, language

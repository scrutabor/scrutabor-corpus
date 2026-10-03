"""The prefaces speak one English register and share their repeated formulas.

Owner decision 2026-09-28 (contemporary You/Your in own and working translations,
including glosses and word explanations, without mixing registers inside a prayer).
The formulas that repeat the Common Preface's Latin read as the Common Preface reads;
the nine *Et ídeo* closings read alike; the angelic orders have one name in each
language, in prose and in word help.
"""

import json
import re
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NAMES = sorted(p.stem for p in (ROOT / "texts/ordinarium").glob("praefatio-*.json"))
ARCHAIC = re.compile(
    r"\b(?:thou|thee|thy|thine|thyself|art|hast|hath|doth|dost|didst|wouldst|mayst|unto"
    r"|whence|thence|wherefore|meet|liveth|reigneth|rejoiceth|Ghost)\b",
    re.I,
)
ET_IDEO = (
    "And therefore with Angels and Archangels, with Thrones and Dominions, and with all the"
    " host of the heavenly army, we sing the hymn of Your glory, evermore saying:"
)


def load(*parts):
    return json.loads(ROOT.joinpath(*parts).read_text())


def norm(form):
    s = unicodedata.normalize("NFD", form.lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.replace("æ", "ae").replace("œ", "oe").strip(".,;:!?")


def strings(value, path=()):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from strings(child, (*path, key))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from strings(child, (*path, i))


def segments(name):
    doc = load("texts/ordinarium", f"{name}.json")
    return {s["id"]: s.get("words", []) for s in doc["segments"]}


def latin(words):
    return " ".join(w["form"] for w in words)


def archaic_fields(doc):
    return [(path, value) for path, value in strings(doc) if ARCHAIC.search(value)]


def test_there_are_twenty_four_prefaces():
    assert len(NAMES) == 24


@pytest.mark.parametrize("name", NAMES)
def test_english_layer_has_one_contemporary_register(name):
    doc = load("languages/en/texts/ordinarium", f"{name}.json")
    assert archaic_fields(doc) == []


def test_the_register_check_sees_an_archaic_gloss():
    doc = load("languages/en/texts/ordinarium", "praefatio-nativitatis.json")
    doc["words"]["w032"]["gloss"] = "Thy"
    assert archaic_fields(doc) == [(("words", "w032", "gloss"), "Thy")]


def test_shared_formulas_read_as_the_common_preface():
    common = segments("praefatio-communis")
    common_en = load("languages/en/texts/ordinarium/praefatio-communis.json")["segments"]
    shared = {latin(common[s]): common_en[s]["translation"] for s in ("s02", "s04", "s05", "s06")}
    seen = 0
    for name in NAMES:
        en = load("languages/en/texts/ordinarium", f"{name}.json")["segments"]
        for sid, words in segments(name).items():
            if latin(words) in shared:
                assert en[sid]["translation"] == shared[latin(words)], (name, sid)
                seen += 1
    assert seen == 18 + 12 + 12 + 12


def test_every_et_ideo_closing_reads_alike():
    seen = 0
    for name in NAMES:
        en = load("languages/en/texts/ordinarium", f"{name}.json")["segments"]
        for sid, words in segments(name).items():
            text = latin(words)
            if text.startswith("Et ídeo cum Ángelis") or " Et ídeo cum Ángelis" in text:
                assert en[sid]["translation"].endswith(ET_IDEO), (name, sid)
                seen += 1
    assert seen == 9


ORDERS = {
    "en": {"dominationes": {"the Dominions"}, "dominationibus": {"Dominions"}},
    "pl": {
        "dominationes": {"Państwa"},
        "dominationibus": {"Państwami"},
        "militia": {"rycerstwem"},
        "exercitus": {"zastępu"},
        "seraphim": {"Serafini"},
    },
}


@pytest.mark.parametrize("language", ["en", "pl"])
def test_angelic_orders_have_one_name_in_word_help(language):
    found = {}
    for name in NAMES:
        layer = load("languages", language, "texts/ordinarium", f"{name}.json")["words"]
        for words in segments(name).values():
            for w in words:
                form = norm(w["form"])
                if form in ORDERS[language]:
                    found.setdefault(form, set()).add(layer[w["id"]]["gloss"])
    assert found == ORDERS[language]


def test_english_prose_names_the_dominions():
    for name in NAMES:
        en = load("languages/en/texts/ordinarium", f"{name}.json")["segments"]
        for seg in en.values():
            assert "Dominations" not in (seg.get("translation") or ""), name

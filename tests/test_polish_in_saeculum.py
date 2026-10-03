"""Polish word help for *in sǽculum (sǽculi)* reads as the Polish idiom.

*In sǽculum sǽculi* is singular in Latin; Polish says „na wieki wieków”, and a lone
*in sǽculum* „na wieki”. The literal „na wiek wieku” is not Polish usage. The familiar
Te Deum keeps its protected prose; only word help follows this rule.
"""

import copy
import unicodedata
from pathlib import Path

from build_reader import store
from checks import interlinear

ROOT = Path(__file__).resolve().parents[1]


def norm(form):
    s = unicodedata.normalize("NFD", form.lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.replace("æ", "ae").replace("œ", "oe").strip(".,;:!?")


def occurrences():
    for path in sorted((ROOT / "texts").glob("*/*.json")):
        text = f"{path.parent.name}.{path.stem}"
        doc = store.core(ROOT, text)
        for segment in doc["segments"]:
            words = segment.get("words", [])
            forms = [norm(w["form"]) for w in words]
            for i in range(len(words) - 1):
                if forms[i] == "in" and forms[i + 1] == "saeculum":
                    double = i + 2 < len(words) and forms[i + 2] == "saeculi"
                    yield text, [w["id"] for w in words[i : i + (3 if double else 2)]]


def glosses(layer, ids):
    return [interlinear.effective_gloss(layer, word) for word in ids]


def check(layer, ids):
    expected = ["na", "wieki", "wieków"] if len(ids) == 3 else ["na", "wieki"]
    return glosses(layer, ids) == expected


def test_every_in_saeculum_reads_na_wieki():
    found = list(occurrences())
    assert sum(len(ids) == 3 for _, ids in found) == 13
    assert sum(len(ids) == 2 for _, ids in found) == 10
    for text, ids in found:
        layer = store.raw_layer(ROOT, "pl", text)
        assert check(layer, ids), (text, ids, glosses(layer, ids))


def test_the_literal_singular_is_rejected():
    text, ids = next((t, i) for t, i in occurrences() if len(i) == 3)
    layer = copy.deepcopy(store.raw_layer(ROOT, "pl", text))
    layer["words"][ids[1]]["gloss"], layer["words"][ids[2]]["gloss"] = "wiek", "wieku"
    assert not check(layer, ids)


def test_protected_te_deum_prose_is_unchanged():
    prose = store.raw_layer(ROOT, "pl", "orationes.te-deum")["segments"]["s25"]["translation"]
    assert prose.startswith("Po wiek wieków nie ustanie pieśń")

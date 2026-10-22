"""Readings that follow the printed page at checked loci, and declared Introit repeats."""

import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import store
from checks.apparatus import DEPRECATED_ACCENT_RULING
from checks.collate import collate

ROOT = Path(__file__).resolve().parents[1]
JOACHIM = "proprium.sancti-ioachim-confessoris-evangelium"
PENTECOST_XXIV = "proprium.dominica-xxiv-post-pentecosten-evangelium"
ACCENT = {"at": "w081", "ours": "Uríæ.", "witnesses": {"do": "Uriæ."}, "class": "accent"}
PUNCTUATION = {"at": "w235", "ours": "tuba,", "witnesses": {"do": "tuba"}, "class": "punctuation"}
ORTHOGRAPHY = (
    "# orthography: printed proper body with explicitly declared house-expanded formula; "
    "not a diplomatic full-page transcript"
)
NOTE = (
    "# note: the page prints the Gloria Patri and the repeated antiphon as cues only "
    "(℣. Glória Patri. {cue}.); {gloria} expand the Gloria Patri from the Ordo, p. 219, "
    "leaf n298, with the house comma after semper where the Ordo prints semper:, and "
    "{repeat} repeat the antiphon under RG 427, p. xxix, leaf n34"
)
DECLARATIONS = [
    pytest.param(
        "dedicatio-sancti-michaelis-archangeli",
        "Benedícite",
        "w030–w049",
        "w050–w065",
        id="michael",
    ),
    pytest.param(
        "dominica-xx-post-pentecosten", "Omnia", "w039–w058", "w059–w087", id="pentecost-xx"
    ),
    pytest.param("omnium-sanctorum", "Gaudeámus omnes", "w028–w047", "w048–w067", id="all-saints"),
    pytest.param(
        "sanctae-annae-matris-beatae-mariae-virginis",
        "Gaudeámus",
        "w031–w050",
        "w051–w070",
        id="st-anne",
    ),
    pytest.param(
        "sancti-petri-et-pauli-apostolorum",
        "Nunc scio",
        "w034–w053",
        "w054–w073",
        id="peter-and-paul",
    ),
]
RULINGS = [
    pytest.param(
        "dedicatio-sancti-michaelis-archangeli", "w053", "Benedícite", "w004", id="michael-w053"
    ),
    pytest.param("dominica-iii-in-quadragesima", "w058", "Oculi", "w001", id="lent-iii-w058"),
    pytest.param("dominica-iii-post-epiphaniam", "w045", "Adoráte", "w004", id="epiphany-iii-w045"),
    pytest.param("dominica-xx-post-pentecosten", "w059", "Omnia", "w001", id="pentecost-xx-w059"),
    pytest.param("omnium-sanctorum", "w063", "Gaudeámus omnes", "w016", id="all-saints-w063"),
    pytest.param(
        "sanctae-annae-matris-beatae-mariae-virginis",
        "w066",
        "Gaudeámus",
        "w016",
        id="st-anne-w066",
    ),
    pytest.param(
        "sancti-petri-et-pauli-apostolorum", "w060", "Nunc scio", "w007", id="peter-and-paul-w060"
    ),
]
REPEAT_RULE = (
    "is the house expansion of that cue under the repetition rule of Rubricae generales 427."
)


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def core(text):
    return load("texts/" + text.replace(".", "/", 1) + ".json")


def words(doc):
    return [word for segment in doc["segments"] for word in segment.get("words", [])]


def word(doc, identifier):
    (found,) = [w for w in words(doc) if w["id"] == identifier]
    return found


def header(text):
    path = ROOT / "witnesses" / f"proprium.{text}-introitus" / "mr.txt"
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line[:1] == "#"]


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def assert_penult_accent(doc, lemmata):
    pair = (word(doc, "w081")["form"], lemmata["Urias"]["head"])
    assert pair == ("Uríæ", "Urías, -æ"), "printed penult accent"


def assert_comma(doc):
    assert word(doc, "w235").get("post") == ",", "printed comma after tuba"


def assert_single_entry(apparatus, expected):
    found = [
        {key: entry[key] for key in ("at", "ours", "witnesses", "class")}
        for entry in apparatus["adjudicated"]
        if entry["at"] == expected["at"]
    ]
    assert found == [expected], "single exact entry"


def assert_declared(lines, doc, cue, gloria, repeat):
    ids, forms = [w["id"] for w in words(doc)], [w["form"] for w in words(doc)]
    first, amen = (ids.index(identifier) for identifier in gloria.split("–"))
    start, end = (ids.index(identifier) for identifier in repeat.split("–"))
    note = NOTE.format(cue=cue, gloria=gloria, repeat=repeat)
    assert (
        lines.count(note) == 1
        and lines.count(ORTHOGRAPHY) == 1
        and (forms[first], forms[amen], amen - first) == ("Glória", "Amen", 19)
        and (start, end) == (amen + 1, len(ids) - 1)
        and forms[start:] == forms[: end - start + 1]
    ), "declared repeat expansion"


def assert_repeat_ruling(apparatus, locus, cue, first):
    attested = [e for e in apparatus["adjudicated"] if "mr" in e["witnesses"]]
    (entry,) = [e for e in attested if e["at"] == locus]
    (printed,) = [e for e in attested if e["at"] == first]
    ruling = entry["ruling"]
    opening = f"The page prints the repeated antiphon only as a cue (℣. Glória Patri. {cue}.)"
    letters = entry["witnesses"]["mr"].rstrip(",.") == printed["witnesses"]["mr"].rstrip(",.")
    assert (
        entry["class"] == "capital-accent"
        and letters
        and ruling.startswith(opening)
        and REPEAT_RULE in ruling
        and f"first printing at {first}, which was checked on the page" in ruling
    ), "repeat ruling"


def test_the_genitive_of_urias_follows_the_printed_penult_accent():
    doc, lemmata = core(JOACHIM), load("lexicon/lemmata.json")["entries"]
    original = deepcopy((doc, lemmata))
    assert_penult_accent(doc, lemmata)
    capital = deepcopy(doc)
    word(capital, "w081")["form"] = "Úriæ"
    with pytest.raises(AssertionError, match=r"^printed penult accent"):
        assert_penult_accent(capital, lemmata)
    heads = deepcopy(lemmata)
    heads["Urias"]["head"] = "Úrias, -æ"
    with pytest.raises(AssertionError, match=r"^printed penult accent"):
        assert_penult_accent(doc, heads)
    assert_penult_accent(doc, lemmata)
    assert (doc, lemmata) == original


def test_the_comma_after_tuba_is_selected():
    doc = core(PENTECOST_XXIV)
    original = deepcopy(doc)
    assert_comma(doc)
    bare = deepcopy(doc)
    del word(bare, "w235")["post"]
    with pytest.raises(AssertionError, match=r"^printed comma after tuba"):
        assert_comma(bare)
    assert_comma(doc)
    assert doc == original


@pytest.mark.parametrize(
    "text,expected",
    [
        pytest.param(JOACHIM, ACCENT, id="w081-accent"),
        pytest.param(PENTECOST_XXIV, PUNCTUATION, id="w235-punctuation"),
    ],
)
def test_the_digital_difference_is_one_exact_entry(text, expected, tmp_path):
    folder = tmp_path / text
    shutil.copytree(ROOT / "witnesses" / text, folder)
    doc = store.load(ROOT, text)[0]
    value = json.loads((folder / "apparatus.json").read_text(encoding="utf-8"))
    original = deepcopy(value)
    assert_single_entry(value, expected)
    assert collate(doc, folder)[0] == []
    without = deepcopy(value)
    without["adjudicated"] = [e for e in value["adjudicated"] if e["at"] != expected["at"]]
    with pytest.raises(AssertionError, match=r"^single exact entry"):
        assert_single_entry(without, expected)
    save(folder / "apparatus.json", without)
    errors = collate(doc, folder)[0]
    assert any(e.startswith(f"do: UNADJUDICATED variant at {expected['at']}:") for e in errors)
    save(folder / "apparatus.json", original)
    assert collate(doc, folder)[0] == []
    assert_single_entry(original, expected)


def test_the_print_and_the_selected_text_agree_at_w081(tmp_path):
    folder = tmp_path / JOACHIM
    shutil.copytree(ROOT / "witnesses" / JOACHIM, folder)
    doc = store.load(ROOT, JOACHIM)[0]
    value = json.loads((folder / "apparatus.json").read_text(encoding="utf-8"))
    original = deepcopy(value)
    reinstated = deepcopy(value)
    at = next(i for i, e in enumerate(value["adjudicated"]) if e["at"] == "w081")
    stale = {"at": "w081", "ours": "Uríæ.", "witnesses": {"mr": "Uriæ."}}
    reinstated["adjudicated"].insert(at, stale | {"class": "capital-accent", "ruling": "x"})
    with pytest.raises(AssertionError, match=r"^single exact entry"):
        assert_single_entry(reinstated, ACCENT)
    save(folder / "apparatus.json", reinstated)
    assert any("w081/mr" in e and "stale ruling" in e for e in collate(doc, folder)[0])
    save(folder / "apparatus.json", original)
    assert collate(doc, folder)[0] == []


@pytest.mark.parametrize("text,cue,gloria,repeat", DECLARATIONS)
def test_the_repeat_expansion_is_declared(text, cue, gloria, repeat):
    lines, doc = header(text), core(f"proprium.{text}-introitus")
    original = deepcopy((lines, doc))
    assert_declared(lines, doc, cue, gloria, repeat)
    undeclared = [line for line in lines if not line.startswith("# note: the page prints")]
    with pytest.raises(AssertionError, match=r"^declared repeat expansion"):
        assert_declared(undeclared, doc, cue, gloria, repeat)
    diplomatic = [
        "# orthography: exact printed accents, ligatures, capitalization, and punctuation"
        if line == ORTHOGRAPHY
        else line
        for line in lines
    ]
    with pytest.raises(AssertionError, match=r"^declared repeat expansion"):
        assert_declared(diplomatic, doc, cue, gloria, repeat)
    shifted = deepcopy(doc)
    word(shifted, repeat.split("–")[0])["form"] = "Amen"
    with pytest.raises(AssertionError, match=r"^declared repeat expansion"):
        assert_declared(lines, shifted, cue, gloria, repeat)
    assert_declared(lines, doc, cue, gloria, repeat)
    assert (lines, doc) == original


@pytest.mark.parametrize("text,locus,cue,first", RULINGS)
def test_the_repeat_ruling_names_the_cue_and_the_checked_first_printing(text, locus, cue, first):
    apparatus = load(f"witnesses/proprium.{text}-introitus/apparatus.json")
    original = deepcopy(apparatus)
    assert_repeat_ruling(apparatus, locus, cue, first)
    withdrawn = deepcopy(apparatus)
    for entry in withdrawn["adjudicated"]:
        if entry["at"] == locus and "mr" in entry["witnesses"]:
            entry["ruling"] = DEPRECATED_ACCENT_RULING
    with pytest.raises(AssertionError, match=r"^repeat ruling"):
        assert_repeat_ruling(withdrawn, locus, cue, first)
    assert_repeat_ruling(apparatus, locus, cue, first)
    assert apparatus == original

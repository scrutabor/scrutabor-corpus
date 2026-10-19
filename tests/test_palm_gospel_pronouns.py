"""Reviewed Polish first-person referents in the Palm Passion Gospel."""

import copy
import json
import re
from pathlib import Path

import pytest

from checks.translation_provenance import canonical_hash, check

ROOT = Path(__file__).resolve().parents[1]
TEXT = "proprium.dominica-ii-passionis-evangelium"
CORE_PATH = "texts/proprium/dominica-ii-passionis-evangelium.json"
PL_PATH = "languages/pl/" + CORE_PATH
LEDGER_PATH = "languages/pl/translation-provenance.json"
CAPTIONS = [
    ("s04", "w040", "mea", "meus", "Moja"),
    ("s04", "w048", "mecum", "ego", "ze Mną"),
    ("s06", "w060", "mi", "meus", "Mój"),
    ("s06", "w066", "me", "ego", "Mnie"),
    ("s06", "w072", "ego", "ego", "Ja"),
    ("s08", "w095", "mecum", "ego", "ze Mną"),
    ("s10", "w118", "mi", "meus", "Mój"),
    ("s12", "w181", "me", "ego", "Mnie"),
    ("s20", "w298", "meum", "meus", "Mego"),
    ("s20", "w301", "mihi", "ego", "Mi"),
    ("s22", "w331", "me", "ego", "Mnie"),
    ("s22", "w341", "me", "ego", "nie pojmaliście Mnie"),
    ("s28", "w464", "nobis", "nos", "nam"),
    ("s36", "w537", "nobis", "nos", "nam"),
    ("s45", "w648", "me", "ego", "Mnie"),
    ("s48", "w709", "nos", "nos", "nas"),
    ("s51", "w794", "mihi", "ego", "mi"),
    ("s74", "w988", "ego", "ego", "ja"),
    ("s76", "w1004", "nos", "nos", "nas"),
    ("s76", "w1008", "nostros", "noster", "naszych"),
    ("s79", "w1148", "mea", "meus", "moje"),
    ("s79", "w1152", "meam", "meus", "moją"),
    ("s86", "w1298", "meus", "meus", "Mój"),
    ("s86", "w1300", "meus", "meus", "Mój"),
    ("s86", "w1304", "me", "ego", "Mnie"),
]
PROSE = {
    "s04": ["Moja", "Mną"],
    "s06": ["Mój", "Mnie", "Ja"],
    "s08": ["Mną"],
    "s10": ["Mój"],
    "s12": ["Mnie"],
    "s20": ["Mojego", "Mi"],
    "s22": ["Mnie", "Mnie"],
    "s28": ["nam"],
    "s32": ["nam"],
    "s36": ["nam"],
    "s45": ["Mnie"],
    "s48": ["nam"],
    "s51": ["mi"],
    "s74": ["Ja"],
    "s76": ["nas", "nasze"],
    "s79": ["moje", "moje"],
    "s86": ["Mój", "Mój", "Mnie"],
}
# This finite lexical finder extracts case at reviewed sites. It does not infer speakers.
FIRST_PERSON = re.compile(
    r"\b(?:ja|mnie|mi|mną|mój|moja|moje|moją|mojego|mego|nas|nam|nasze|naszych)\b",
    re.IGNORECASE,
)
HEADS = {
    "w040": "w039",
    "w060": "w059",
    "w118": "w117",
    "w298": "w297",
    "w1008": "w1007",
    "w1148": "w1147",
    "w1152": "w1151",
    "w1298": "w1297",
    "w1300": "w1299",
}
SHARED = ["w340", "w341", "w342"]
CONTEXTS = [
    ("s01", 2, 4, "Venit Iesus cum"),
    ("s03", 34, 36, "Tunc ait illis"),
    ("s05", 56, 58, "orans et dicens"),
    ("s07", 86, 88, "et dicit Petro"),
    ("s09", 111, 116, "Íterum secúndo ábiit et orávit dicens"),
    ("s11", 154, 161, "Tunc venit ad discípulos suos et dicit illis"),
    ("s19", 274, 277, "Tunc ait illi Iesus"),
    ("s21", 316, 321, "In illa hora dixit Iesus turbis"),
    ("s27", 452, 456, "Et princeps sacerdótum ait illi"),
    ("s35", 528, 535, "álii autem palmas in fáciem eius dedérunt dicéntes"),
    (
        "s45",
        636,
        649,
        "Et recordátus est Petrus verbi Iesu quod díxerat Priúsquam gallus cantet ter me negábis",
    ),
    ("s47", 704, 706, "At illi dixérunt"),
    ("s51", 768, 774, "quod dictum est per Ieremíam prophétam dicéntem"),
    ("s51", 792, 795, "sicut constítuit mihi Dóminus"),
    ("s73", 970, 972, "Videns autem Pilátus"),
    ("s75", 996, 1000, "Et respóndens univérsus pópulus dixit"),
    (
        "s79",
        1137,
        1154,
        "ut implerétur quod dictum est per Prophétam dicéntem "
        "Divisérunt sibi vestiménta mea et super vestem meam misérunt sortem",
    ),
    ("s83", 1282, 1290, "Et circa horam nonam clamávit Iesus voce magna dicens"),
    ("s84", 1291, 1294, "Eli Eli lamma sabactháni"),
    ("s85", 1295, 1296, "Hoc est"),
    ("s86", 1297, 1304, "Deus meus Deus meus ut quid dereliquísti me"),
]


def read(relative, root=ROOT):
    return json.loads((root / relative).read_bytes())


def layer(root=ROOT):
    return read(PL_PATH, root)


def assert_caption(core, target, case):
    segment, word, form, lemma, expected = case
    assert core["id"] == TEXT
    sources = [(s, w) for s in core["segments"] for w in s.get("words", []) if w["id"] == word]
    assert len(sources) == 1, f"source:{word}"
    source_segment, source_word = sources[0]
    assert source_segment["id"] == segment, f"segment:{word}"
    assert (source_word["form"], source_word["lemma"]) == (form, lemma), f"latin:{word}"
    if word in HEADS:
        assert source_word.get("head") == HEADS[word], f"head:{word}"
    direct = "gloss" in target.get("words", {}).get(word, {})
    groups = [
        (sid, group)
        for sid, localized in target["segments"].items()
        for group in localized.get("alignments", [])
        if word in group["words"]
    ]
    assert int(direct) + len(groups) == 1, f"realization:{word}"
    if word == "w341":
        assert not direct, "shared:w341"
        sid, group = groups[0]
        assert sid == segment, "shared-segment:w341"
        assert group["words"] == SHARED, "shared-members:w341"
        assert group["anchor"] == "w342", "shared-anchor:w341"
        ids = [w["id"] for w in source_segment["words"]]
        first = ids.index(SHARED[0])
        assert ids[first : first + len(SHARED)] == SHARED, "shared-contiguous:w341"
        for member in SHARED:
            assert "gloss" not in target.get("words", {}).get(member, {}), f"shared-direct:{member}"
            occurrences = [
                (other_sid, other)
                for other_sid, localized in target["segments"].items()
                for other in localized.get("alignments", [])
                if member in other["words"]
            ]
            assert len(occurrences) == 1, f"shared-coverage:{member}"
        actual = group["gloss"]
    else:
        assert direct and groups == [], f"direct:{word}"
        actual = target["words"][word]["gloss"]
    assert actual == expected, f"caption:{word}"


def assert_prose(target, segment):
    actual = FIRST_PERSON.findall(target["segments"][segment]["translation"])
    assert actual == PROSE[segment], f"prose:{segment}"


@pytest.mark.parametrize("case", CAPTIONS, ids=[row[1] for row in CAPTIONS])
def test_reviewed_first_person_caption(case):
    assert_caption(read(CORE_PATH), layer(), case)


@pytest.mark.parametrize("segment", PROSE)
def test_reviewed_prose_pronoun_sequence(segment):
    assert_prose(layer(), segment)


def test_reviewed_latin_contexts_do_not_infer_from_actor_label_alone():
    core = read(CORE_PATH)
    segments = {s["id"]: s for s in core["segments"]}
    for segment, first, last, expected in CONTEXTS:
        words = {w["id"]: w["form"] for w in segments[segment]["words"]}
        actual = " ".join(words[f"w{i:03}"] for i in range(first, last + 1))
        assert actual == expected, f"context:{segment}:{first}"
    assert segments["s45"]["delivery"]["cantu"]["speaker"] == "chronista"
    assert segments["s79"]["delivery"]["cantu"]["speaker"] == "chronista"
    assert segments["s86"]["delivery"]["cantu"]["speaker"] == "christus"


def lower_prose_occurrence(target, segment, occurrence):
    text = target["segments"][segment]["translation"]
    matches = list(FIRST_PERSON.finditer(text))
    assert [m.group() for m in matches] == PROSE[segment], f"mutation-precondition:{segment}"
    match = matches[occurrence]
    assert match.group() != match.group().lower(), f"mutation-changes-case:{segment}"
    target["segments"][segment]["translation"] = (
        text[: match.start()] + match.group().lower() + text[match.end() :]
    )


@pytest.mark.parametrize(
    "kind,key,occurrence",
    [
        ("caption", "w072", 0),
        ("caption", "w301", 0),
        ("prose", "s45", 0),
        ("prose", "s86", 1),
    ],
    ids=["caption-w072", "caption-w301", "prose-s45", "prose-s86-second"],
)
def test_lowercase_mutant_reaches_owned_assertion_and_restores(kind, key, occurrence):
    core = read(CORE_PATH)
    target = layer()
    original = copy.deepcopy(target)
    if kind == "caption":
        case = next(row for row in CAPTIONS if row[1] == key)
        assert_caption(core, target, case)
        target["words"][key]["gloss"] = case[-1].lower()
        with pytest.raises(AssertionError, match=f"caption:{key}"):
            assert_caption(core, target, case)
    else:
        assert_prose(target, key)
        lower_prose_occurrence(target, key, occurrence)
        with pytest.raises(AssertionError, match=f"prose:{key}"):
            assert_prose(target, key)
    # A case-only local mutant must not alter a group, note or other target field.
    restored = copy.deepcopy(target)
    if kind == "caption":
        restored["words"][key]["gloss"] = original["words"][key]["gloss"]
    else:
        restored["segments"][key]["translation"] = original["segments"][key]["translation"]
    assert restored == original
    if kind == "caption":
        assert_caption(core, restored, case)
    else:
        assert_prose(restored, key)


@pytest.mark.parametrize(
    "mutation,diagnostic",
    [("remove-member", "realization:w341"), ("duplicate-direct", "realization:w341")],
    ids=["missing-w341", "duplicate-direct-w341"],
)
def test_shared_caption_contract_rejects_missing_or_duplicate_realization(mutation, diagnostic):
    core = read(CORE_PATH)
    target = layer()
    original = copy.deepcopy(target)
    case = next(row for row in CAPTIONS if row[1] == "w341")
    assert_caption(core, target, case)
    group = next(g for g in target["segments"]["s22"]["alignments"] if "w341" in g["words"])
    if mutation == "remove-member":
        group["words"].remove("w341")
    else:
        target["words"].setdefault("w341", {})["gloss"] = "Mnie"
    with pytest.raises(AssertionError, match=diagnostic):
        assert_caption(core, target, case)
    assert_caption(core, original, case)


def write(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def provenance_corpus(tmp_path):
    # Actual neutral source, localized text and graph, reduced to this one text.
    graph = tmp_path / "bibliography/graph.json"
    graph.parent.mkdir(parents=True)
    graph.write_bytes((ROOT / "bibliography/graph.json").read_bytes())
    write(tmp_path, CORE_PATH, read(CORE_PATH))
    write(tmp_path, PL_PATH, layer())
    for name, key in (
        ("manifest", "texts"),
        ("translation-provenance", "sites"),
        ("bibliography", "uses"),
    ):
        relative = "languages/pl/" + name + ".json"
        document = read(relative)
        document[key] = (
            [tid for tid in document[key] if tid == TEXT]
            if name == "manifest"
            else [
                row
                for row in document[key]
                if (row.get("text") if key == "sites" else row.get("address", {}).get("text"))
                == TEXT
            ]
        )
        write(tmp_path, relative, document)
    return tmp_path


@pytest.mark.parametrize(
    "segment,occurrence",
    [("s45", 0), ("s86", 1)],
    ids=["s45-embedded", "s86-second"],
)
def test_target_hash_repair_does_not_replace_speaker_case_guard(
    provenance_corpus,
    segment,
    occurrence,
):
    root = provenance_corpus
    errors, tally = check(root)
    assert errors == []
    assert sum(tally.values()) == 94
    original_text = (root / PL_PATH).read_bytes()
    original_ledger = (root / LEDGER_PATH).read_bytes()
    target = layer(root)
    ledger_before = read(LEDGER_PATH, root)
    assert len(ledger_before["sites"]) == 94
    assert_prose(target, segment)
    lower_prose_occurrence(target, segment, occurrence)
    try:
        write(root, PL_PATH, target)
        errors, _ = check(root)
        assert errors == [f"{TEXT}.{segment}.pl: stale target_sha256"]
        ledger = read(LEDGER_PATH, root)
        rows = [r for r in ledger["sites"] if r["site"] == f"{TEXT}.{segment}.pl"]
        assert len(rows) == 1
        rows[0]["target_sha256"] = canonical_hash(target["segments"][segment]["translation"])
        write(root, LEDGER_PATH, ledger)
        assert check(root)[0] == []
        expected_ledger = copy.deepcopy(ledger_before)
        expected_row = next(r for r in expected_ledger["sites"] if r["site"] == rows[0]["site"])
        expected_row["target_sha256"] = rows[0]["target_sha256"]
        assert ledger == expected_ledger
        with pytest.raises(AssertionError, match=f"prose:{segment}"):
            assert_prose(layer(root), segment)
    finally:
        (root / PL_PATH).write_bytes(original_text)
        (root / LEDGER_PATH).write_bytes(original_ledger)
    assert (root / PL_PATH).read_bytes() == original_text
    assert (root / LEDGER_PATH).read_bytes() == original_ledger
    assert check(root)[0] == []
    assert_prose(layer(root), segment)


def test_current_uncited_wording_scope_and_state_classes():
    core = read(CORE_PATH)
    assert core["id"] == TEXT
    assert len(core["segments"]) == 95
    assert sum(len(s.get("words", [])) for s in core["segments"]) == 1512
    target = layer()

    def citations(value):
        if isinstance(value, dict):
            return sum(
                int(bool(child)) if key.endswith("_citations") else citations(child)
                for key, child in value.items()
            )
        if isinstance(value, list):
            return sum(citations(child) for child in value)
        return 0

    assert citations(target) == 0
    uses = read("languages/pl/bibliography.json")["uses"]
    assert not [u for u in uses if u.get("address", {}).get("text") == TEXT]
    sites = [r for r in read(LEDGER_PATH)["sites"] if r["text"] == TEXT]
    assert len(sites) == 94
    assert all(not r["familiar_core"] for r in sites)
    assert all(r["origin"] in {"own", "working-unsettled"} for r in sites)
    assert all(r["review"] in {"working", "internally-reviewed", "expert-reviewed"} for r in sites)

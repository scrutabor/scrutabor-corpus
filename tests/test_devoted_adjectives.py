"""Devout states use the adjective; former verb confirmations do not transfer."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.layers import expand_core
from checks import lexicon, syntax
from checks import translation_provenance as provenance

ROOT = Path(__file__).resolve().parents[1]
# Source-derived constants are substituted before proposing this test module.
ROWS = [
    {
        "stem": "dominica-post-ascensionem-collecta",
        "word": "w009",
        "form": "devótam",
        "morph": {"pos": "adj", "case": "acc", "gender": "f", "number": "sg"},
        "old_morph": {
            "pos": "verb",
            "case": "acc",
            "gender": "f",
            "number": "sg",
            "tense": "perf",
            "voice": "pass",
            "mood": "part",
            "conj": 2,
        },
        "head": "w011",
    },
    {
        "stem": "dominica-vii-post-pentecosten-secreta",
        "word": "w013",
        "form": "devótis",
        "morph": {"pos": "adj", "case": "abl", "gender": "m", "number": "pl"},
        "old_morph": {
            "pos": "verb",
            "case": "abl",
            "gender": "m",
            "number": "pl",
            "tense": "perf",
            "voice": "pass",
            "mood": "part",
            "conj": 2,
        },
        "head": "w015",
    },
    {
        "stem": "dominica-xxi-post-pentecosten-collecta",
        "word": "w023",
        "form": "devóta",
        "morph": {"pos": "adj", "case": "nom", "gender": "f", "number": "sg"},
        "old_morph": {
            "pos": "verb",
            "case": "nom",
            "gender": "f",
            "number": "sg",
            "tense": "perf",
            "voice": "pass",
            "mood": "part",
            "conj": 2,
        },
        "head": "w022",
    },
    {
        "stem": "immaculatum-cor-beatae-mariae-virginis-collecta",
        "word": "w022",
        "form": "devóta",
        "morph": {"pos": "adj", "case": "abl", "gender": "f", "number": "sg"},
        "old_morph": {
            "pos": "verb",
            "case": "abl",
            "gender": "f",
            "number": "sg",
            "tense": "perf",
            "voice": "pass",
            "mood": "part",
            "conj": 2,
        },
        "head": "w023",
    },
]

ROW_IDS = (
    "dominica-post-ascensionem-collecta",
    "dominica-vii-post-pentecosten-secreta",
    "dominica-xxi-post-pentecosten-collecta",
    "immaculatum-cor-beatae-mariae-virginis-collecta",
)

MUTANTS = [
    (0, "lemma"),
    (0, "participle"),
    (0, "head"),
    (0, "providers"),
    (0, "promotion"),
    (1, "lemma"),
    (1, "participle"),
    (1, "head"),
    (1, "providers"),
    (1, "promotion"),
    (2, "lemma"),
    (2, "participle"),
    (2, "head"),
    (2, "providers"),
    (2, "promotion"),
    (3, "lemma"),
    (3, "participle"),
    (3, "head"),
    (3, "providers"),
    (3, "promotion"),
]

MUTANT_IDS = (
    "lemma-dominica-post-ascensionem-collecta",
    "participle-dominica-post-ascensionem-collecta",
    "head-dominica-post-ascensionem-collecta",
    "providers-dominica-post-ascensionem-collecta",
    "promotion-dominica-post-ascensionem-collecta",
    "lemma-dominica-vii-post-pentecosten-secreta",
    "participle-dominica-vii-post-pentecosten-secreta",
    "head-dominica-vii-post-pentecosten-secreta",
    "providers-dominica-vii-post-pentecosten-secreta",
    "promotion-dominica-vii-post-pentecosten-secreta",
    "lemma-dominica-xxi-post-pentecosten-collecta",
    "participle-dominica-xxi-post-pentecosten-collecta",
    "head-dominica-xxi-post-pentecosten-collecta",
    "providers-dominica-xxi-post-pentecosten-collecta",
    "promotion-dominica-xxi-post-pentecosten-collecta",
    "lemma-immaculatum-cor-beatae-mariae-virginis-collecta",
    "participle-immaculatum-cor-beatae-mariae-virginis-collecta",
    "head-immaculatum-cor-beatae-mariae-virginis-collecta",
    "providers-immaculatum-cor-beatae-mariae-virginis-collecta",
    "promotion-immaculatum-cor-beatae-mariae-virginis-collecta",
)

PROVENANCE_CASES = [
    (0, "pl"),
    (0, "en"),
    (1, "pl"),
    (1, "en"),
    (2, "pl"),
    (2, "en"),
    (3, "pl"),
    (3, "en"),
]

PROVENANCE_IDS = (
    "pl-dominica-post-ascensionem-collecta",
    "en-dominica-post-ascensionem-collecta",
    "pl-dominica-vii-post-pentecosten-secreta",
    "en-dominica-vii-post-pentecosten-secreta",
    "pl-dominica-xxi-post-pentecosten-collecta",
    "en-dominica-xxi-post-pentecosten-collecta",
    "pl-immaculatum-cor-beatae-mariae-virginis-collecta",
    "en-immaculatum-cor-beatae-mariae-virginis-collecta",
)

CARDS = {
    "neutral": {"head": "devótus, -a, -um", "pos": "adj"},
    "pl": {"senses": ["pobożny", "oddany"]},
    "en": {"senses": ["devout", "devoted"]},
}

RETIRED = {
    "neutral": {"head": "devóveo, devovére, devóvi, devótum", "pos": "verb", "conj": 2},
    "pl": {"senses": ["poświęcać", "oddawać", "ślubować"]},
    "en": {"senses": ["to devote, consecrate", "to vow"]},
}

OLD_SOURCE = {
    "dominica-post-ascensionem-collecta": (
        "b38a14752e77f8bb138f29901bb1c6d5bd3f3e6f47f7a8d8da100774041db71e"
    ),
    "dominica-vii-post-pentecosten-secreta": (
        "c620d29bd8191e126e94745036ab52ff1bba32d374cd57c5e6930be0bf335312"
    ),
    "dominica-xxi-post-pentecosten-collecta": (
        "e83e9696e37d8d8c16334a3328c35f91bb7337dd60fc49b336194a4a9d9ecb0b"
    ),
    "immaculatum-cor-beatae-mariae-virginis-collecta": (
        "165df278e85e283a0de04c2b0d7fca071f5acb464ee260b3e0aaf49ea4309c7f"
    ),
}

RECORDS = {
    "proprium.dominica-post-ascensionem-collecta.s01.pl": {
        "site": "proprium.dominica-post-ascensionem-collecta.s01.pl",
        "text": "proprium.dominica-post-ascensionem-collecta",
        "segment": "s01",
        "language": "pl",
        "familiar_core": False,
        "origin": "working-unsettled",
        "review": "working",
        "source_sha256": "7fb22409b07c78940cf2fbef6503f6a2db004d50a3b41b30f1e81ff8f9fdfe25",
        "target_sha256": "73d409d1ad3cb570f66fb623366c54d84412ffdfd39ba3d3e50a2c25bc5c7003",
    },
    "proprium.dominica-vii-post-pentecosten-secreta.s01.pl": {
        "site": "proprium.dominica-vii-post-pentecosten-secreta.s01.pl",
        "text": "proprium.dominica-vii-post-pentecosten-secreta",
        "segment": "s01",
        "language": "pl",
        "familiar_core": False,
        "origin": "working-unsettled",
        "review": "working",
        "source_sha256": "ffdea14c102e23649e28e5acc471784a49fe5ab42e100f1ed1063a24cbe9d1cd",
        "target_sha256": "2e864407838818c30e431b24b6b8d3d0f0dca2459cdcd0a1203c7425c2181b33",
    },
    "proprium.dominica-xxi-post-pentecosten-collecta.s01.pl": {
        "site": "proprium.dominica-xxi-post-pentecosten-collecta.s01.pl",
        "text": "proprium.dominica-xxi-post-pentecosten-collecta",
        "segment": "s01",
        "language": "pl",
        "familiar_core": False,
        "origin": "working-unsettled",
        "review": "working",
        "source_sha256": "f5d9ca717613f1a6356098bcf52ab40f58bdf5cada03ac312cf513bae79c4532",
        "target_sha256": "661d04319248e8b9cfa607db90a6f61a6f52cc3ffc172f5222f2e692d7317b77",
    },
    "proprium.immaculatum-cor-beatae-mariae-virginis-collecta.s01.pl": {
        "site": "proprium.immaculatum-cor-beatae-mariae-virginis-collecta.s01.pl",
        "text": "proprium.immaculatum-cor-beatae-mariae-virginis-collecta",
        "segment": "s01",
        "language": "pl",
        "familiar_core": False,
        "origin": "working-unsettled",
        "review": "working",
        "source_sha256": "572de92a1162fb863e8828ef82e50de80246b978bb94b218fc62b1a793f6dcdf",
        "target_sha256": "b16b9382463d8302aee3fe89285f0813c74fc02d77cca2365d8fb18ab53e235d",
    },
    "proprium.dominica-post-ascensionem-collecta.s01.en": {
        "site": "proprium.dominica-post-ascensionem-collecta.s01.en",
        "text": "proprium.dominica-post-ascensionem-collecta",
        "segment": "s01",
        "language": "en",
        "familiar_core": False,
        "origin": "public-domain",
        "review": "working",
        "source_sha256": "7fb22409b07c78940cf2fbef6503f6a2db004d50a3b41b30f1e81ff8f9fdfe25",
        "target_sha256": "80d66ba3f74009ec6c2d0e77188476ce0c779e17e0260b1abdaaee81e6710b52",
    },
    "proprium.dominica-vii-post-pentecosten-secreta.s01.en": {
        "site": "proprium.dominica-vii-post-pentecosten-secreta.s01.en",
        "text": "proprium.dominica-vii-post-pentecosten-secreta",
        "segment": "s01",
        "language": "en",
        "familiar_core": False,
        "origin": "public-domain",
        "review": "working",
        "source_sha256": "ffdea14c102e23649e28e5acc471784a49fe5ab42e100f1ed1063a24cbe9d1cd",
        "target_sha256": "204d719a41e58ff9b4a02469e5e9ad5d0a50b2501bfc52bcc4e7b8d1997f5533",
    },
    "proprium.dominica-xxi-post-pentecosten-collecta.s01.en": {
        "site": "proprium.dominica-xxi-post-pentecosten-collecta.s01.en",
        "text": "proprium.dominica-xxi-post-pentecosten-collecta",
        "segment": "s01",
        "language": "en",
        "familiar_core": False,
        "origin": "working-unsettled",
        "review": "working",
        "source_sha256": "f5d9ca717613f1a6356098bcf52ab40f58bdf5cada03ac312cf513bae79c4532",
        "target_sha256": "5fa682326d532b2e5ce2370b3fc2e12c64a91aaa908814926609a08a99280973",
    },
    "proprium.immaculatum-cor-beatae-mariae-virginis-collecta.s01.en": {
        "site": "proprium.immaculatum-cor-beatae-mariae-virginis-collecta.s01.en",
        "text": "proprium.immaculatum-cor-beatae-mariae-virginis-collecta",
        "segment": "s01",
        "language": "en",
        "familiar_core": False,
        "origin": "working-unsettled",
        "review": "working",
        "source_sha256": "572de92a1162fb863e8828ef82e50de80246b978bb94b218fc62b1a793f6dcdf",
        "target_sha256": "8dea3aed09eee0fd949f6ac5e881eef8153c0d4b20b184d733fcba202e6035e1",
    },
}


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def words(core):
    return {word["id"]: word for segment in core["segments"] for word in segment.get("words", [])}


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def assert_occurrence(core, row):
    require(core["id"] == "proprium." + row["stem"], "devotion identity")
    word = words(core)[row["word"]]
    require(word["form"] == row["form"], "devotion literal form")
    require(word["lemma"] == "devotus", "devotion adjective lemma")
    require(word["morph"] == row["morph"], "devotion adjective morphology")
    require(word["head"] == row["head"], "devotion contextual head")
    require(
        core["editorial"]["words"][row["word"]]["analysis"]
        == {
            "confidence": "high",
            "sources": ["editorial", "whitakers", "collatinus"],
            "review": "pending",
        },
        "devotion fresh analysis evidence",
    )


@pytest.mark.parametrize("row", ROWS, ids=ROW_IDS)
def test_actual_adjective_states_and_existing_syntax_contract(row):
    core = read("texts/proprium/" + row["stem"] + ".json")
    assert_occurrence(core, row)
    assert syntax.check(expand_core(core)) == []
    heads = read("lexicon/lemmata.json")["entries"]
    assert lexicon.check_text_against_lexicon(expand_core(core), heads) == []


@pytest.mark.parametrize("row_index,defect", MUTANTS, ids=MUTANT_IDS)
def test_source_and_evidence_mutants_fail_then_the_same_copy_recovers(row_index, defect):
    row = ROWS[row_index]
    core = read("texts/proprium/" + row["stem"] + ".json")
    assert_occurrence(core, row)
    saved = deepcopy(core)
    broken = deepcopy(core)
    word = words(broken)[row["word"]]
    if defect == "lemma":
        word["lemma"] = "devoveo"
        message = "devotion adjective lemma"
    elif defect == "participle":
        word["morph"] = deepcopy(row["old_morph"])
        message = "devotion adjective morphology"
    elif defect == "head":
        word["head"] = "w001"
        message = "devotion contextual head"
    else:
        analysis = broken["editorial"]["words"][row["word"]]["analysis"]
        if defect == "providers":
            analysis["sources"] = ["editorial"]
        else:
            analysis["review"] = "accepted"
        message = "devotion fresh analysis evidence"
    assert broken != saved
    with pytest.raises(AssertionError, match=message):
        assert_occurrence(broken, row)
    broken.clear()
    broken.update(deepcopy(saved))
    assert_occurrence(broken, row)
    assert broken == core == saved


def used_lemmas():
    return {
        word["lemma"]
        for path in ROOT.glob("texts/*/*.json")
        for segment in json.loads(path.read_text(encoding="utf-8"))["segments"]
        for word in segment.get("words", [])
    }


def test_exact_five_adjective_consumers_and_complete_retirement():
    hits = []
    paths = list(ROOT.glob("texts/*/*.json"))
    assert paths
    for path in paths:
        core = json.loads(path.read_text(encoding="utf-8"))
        for segment in core["segments"]:
            for word in segment.get("words", []):
                if word["lemma"] in {"devoveo", "devotus"}:
                    hits.append((core["id"], segment["id"], word["id"], word["lemma"]))
    expected = [("proprium." + r["stem"], "s01", r["word"], "devotus") for r in ROWS]
    expected.append(("proprium.sacratissimi-cordis-iesu-collecta", "s01", "w021", "devotus"))
    assert sorted(hits) == sorted(expected)
    for relative in (
        "lexicon/lemmata.json",
        "languages/pl/lexicon.json",
        "languages/en/lexicon.json",
    ):
        assert "devoveo" not in read(relative)["entries"]


@pytest.mark.parametrize("lane", ("neutral", "pl", "en"))
def test_native_dictionary_guards_reject_reintroduced_retired_entry(lane):
    heads = read("lexicon/lemmata.json")["entries"]
    assert heads["devotus"] == CARDS["neutral"]
    if lane == "neutral":
        used = used_lemmas()
        assert used and lexicon.check_orphans(heads, used) == []
        broken = deepcopy(heads)
        broken["devoveo"] = deepcopy(RETIRED[lane])
        assert lexicon.check_orphans(broken, used) == [
            "lexicon: orphan entries not used by any text: ['devoveo']"
        ]
        del broken["devoveo"]
        assert broken == heads and lexicon.check_orphans(broken, used) == []
    else:
        entries = read("languages/" + lane + "/lexicon.json")["entries"]
        assert entries["devotus"] == CARDS[lane] and "devoveo" not in entries
        healthy = {"devotus": deepcopy(entries["devotus"])}
        scope = {"devotus": heads["devotus"]}
        assert lexicon.lint_senses(lane, healthy, scope, required={"devotus"}) == []
        broken = deepcopy(healthy)
        broken["devoveo"] = deepcopy(RETIRED[lane])
        assert lexicon.lint_senses(lane, broken, scope, required={"devotus"}) == [
            "lexicon:" + lane + ": entries for unknown lemmas ['devoveo']"
        ]
        del broken["devoveo"]
        assert broken == healthy
        assert lexicon.lint_senses(lane, broken, scope, required={"devotus"}) == []


def assert_source_record(core, layer, records, row, language):
    assert_occurrence(core, row)
    site = "proprium." + row["stem"] + ".s01." + language
    actual = [record for record in records if record["site"] == site]
    require(len(actual) == 1, "devotion provenance identity")
    segment = next(s for s in core["segments"] if s["id"] == "s01")
    expected = RECORDS[site]
    require(
        actual[0]["source_sha256"]
        == provenance.canonical_hash(provenance.source_payload(segment))
        == expected["source_sha256"],
        "devotion source binding",
    )
    require(actual[0] == expected, "devotion preserved provenance fields")
    require(
        provenance.canonical_hash(layer["segments"]["s01"]["translation"])
        == expected["target_sha256"],
        "devotion unchanged translation",
    )


@pytest.mark.parametrize("row_index,language", PROVENANCE_CASES, ids=PROVENANCE_IDS)
def test_native_source_payload_and_stale_ledger_recovery(row_index, language):
    row = ROWS[row_index]
    relative = "texts/proprium/" + row["stem"] + ".json"
    core = read(relative)
    layer = read("languages/" + language + "/" + relative)
    records = read("languages/" + language + "/translation-provenance.json")["sites"]
    assert_source_record(core, layer, records, row, language)
    broken = deepcopy(records)
    site = "proprium." + row["stem"] + ".s01." + language
    record = next(record for record in broken if record["site"] == site)
    saved = deepcopy(record)
    record["source_sha256"] = OLD_SOURCE[row["stem"]]
    with pytest.raises(AssertionError, match="devotion source binding"):
        assert_source_record(core, layer, broken, row, language)
    record.clear()
    record.update(saved)
    assert_source_record(core, layer, broken, row, language)
    assert broken == records


def test_existing_sacred_heart_adjective_is_not_rewritten():
    core = read("texts/proprium/sacratissimi-cordis-iesu-collecta.json")
    word = words(core)["w021"]
    assert word["form"] == "devótum" and word["lemma"] == "devotus"
    assert word["morph"] == {"pos": "adj", "case": "acc", "number": "sg", "gender": "n"}
    assert word["head"] == "w025"

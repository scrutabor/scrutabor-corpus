"""Check English register without letting changed prose exclude its own text.

Every localized text is checked, including new texts and legacy wording. The exact-field
legacy fixture is unresolved debt, not approval of a translation or traditional formula.
An existing flagged field may remain byte-identical pending review, but new, changed and
obsolete allowances fail. Deliberately retained historical register has a separate,
disjoint exact-field inventory. Neither inventory exempts a whole text.
This lexical detector does not replace contextual review.
"""

import hashlib
import json
import re
import unicodedata
from copy import deepcopy
from pathlib import Path

import pytest

from checks import interlinear

ROOT = Path(__file__).resolve().parents[1]
ARCHAIC = re.compile(
    r"\b(?:thou|thee|thy|thine|thyself|art|hast|hath|doth|dost|saith|didst|wouldst|shouldst|mayst"
    r"|mayest|mightest|canst|wilt|shalt|unto|whence|thence|wherefore|ye)\b|\b[a-z]+(?:eth|est)\b",
    re.I,
)
NOT_ARCHAIC = {
    "rest",
    "test",
    "best",
    "lest",
    "west",
    "east",
    "nest",
    "guest",
    "forest",
    "harvest",
    "manifest",
    "conquest",
    "request",
    "chest",
    "interest",
    "honest",
    "modest",
    "priest",
    "highest",
    "greatest",
    "least",
    "lowest",
    "eldest",
    "first",
    "last",
    "earnest",
    "protest",
    "detest",
    "holiest",
    "mightiest",
    "dearest",
    "purest",
    "truest",
    "nearest",
    "fairest",
    "brightest",
    "humblest",
    "wisest",
    "richest",
    "sweetest",
    "latest",
    "strongest",
    "deepest",
    "smallest",
    "worthiest",
    "gentlest",
    "kindest",
    "loveliest",
    "happiest",
    "shortest",
    "longest",
    "fullest",
    "finest",
    "oldest",
    "youngest",
    "everlasting",
    "nazareth",
    "elizabeth",
    "beth",
    "japheth",
    "seth",
    "behest",
    "bethlehem",
    "gethsemane",
    "breast",
    "tempest",
    "arrest",
    "invest",
    "suggest",
    "digest",
    "contest",
    "attest",
    "quest",
    "crest",
    "zest",
    "vest",
    "jest",
    "pest",
    "unrest",
    "lowliest",
    "feeblest",
    "fiercest",
    "gravest",
    "bitterest",
    "sorest",
    "hardest",
    "lightest",
    "darkest",
    "coldest",
    "tenderest",
}
GLORIA_PATRI_END = "As it was in the beginning, is now, and ever shall be, world without end."
# Saint John's Postcommunion keeps the conclusion of its recorded historical wording basis.
HISTORICAL_CONCLUSION = {"proprium.sancti-ioannis-apostoli-et-evangelistae-postcommunio"}
# "forever and ever" is the contemporary standard. Keep legacy spacing detectable
# separately while unrevised texts still retain their recorded wording.
ENDINGS = (" forever and ever.", " for ever and ever.")
CONCLUSIONS = {
    "per dominum nostrum iesum christum filium tuum qui tecum vivit et regnat in unitate"
    " spiritus sancti deus": "Through our Lord Jesus Christ, Your Son, who lives and reigns"
    " with You in the unity of the Holy Spirit, God,",
    "per eundem dominum nostrum iesum christum filium tuum qui tecum vivit et regnat in unitate"
    " spiritus sancti deus": "Through the same Jesus Christ, our Lord, Your Son, who lives and"
    " reigns with You in the unity of the Holy Spirit, God,",
}


def archaic(text):
    return [m for m in ARCHAIC.findall(text or "") if m.lower() not in NOT_ARCHAIC]


def stale(text):
    rest = (text or "").replace(GLORIA_PATRI_END, "")
    return bool(archaic(text)) or "Ghost" in text or "world without end" in rest


def strings(value, path=()):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from strings(child, (*path, key))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from strings(child, (*path, i))


def norm(form):
    s = unicodedata.normalize("NFD", form.lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.replace("æ", "ae").replace("œ", "oe").strip(".,;:!?")


def layers():
    for path in sorted((ROOT / "languages/en/texts").glob("*/*.json")):
        yield json.loads(path.read_text())


def contemporary(doc):
    prose = " ".join(s.get("translation") or "" for s in doc["segments"].values())
    return not stale(prose)


def mixed_fields(doc):
    return [(path, value) for path, value in strings(doc) if stale(value)]


def field_inventory(payload, *, status):
    assert payload["schema_version"] == 1
    assert payload["status"] == status
    inventory = {}
    for record in payload["records"]:
        text = record["text"]
        assert isinstance(text, str) and text not in inventory, text
        fields = {}
        assert record["fields"], text
        for field in record["fields"]:
            path = tuple(field["path"])
            digest = field["sha256"]
            assert path and all(isinstance(key, (str, int)) for key in path), (
                text,
                path,
            )
            assert path not in fields, (text, path)
            assert isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest)
            fields[path] = digest
        inventory[text] = fields
    return inventory


def legacy_inventory(payload):
    return field_inventory(payload, status="unreviewed_legacy_fields")


def historical_inventory(payload):
    inventory = field_inventory(payload, status="retained_historical_register_fields")
    for record in payload["records"]:
        assert isinstance(record.get("reason"), str) and record["reason"].strip()
        assert isinstance(record.get("basis_use"), str) and record["basis_use"].startswith(
            "use.en."
        )
        for field in record["fields"]:
            path = field["path"]
            assert len(path) == 3 and path[0] == "segments" and path[2] == "translation"
    return inventory


def combine_inventories(legacy, historical, subjects):
    assert set(legacy) | set(historical) <= subjects
    combined = deepcopy(legacy)
    for text, fields in historical.items():
        existing = combined.setdefault(text, {})
        assert not existing.keys() & fields.keys(), text
        existing.update(fields)
    return combined


def register_changes(doc, inventory):
    expected = inventory.get(doc["text"], {})
    actual = {path: hashlib.sha256(value.encode()).hexdigest() for path, value in mixed_fields(doc)}
    return {
        "new": set(actual) - set(expected),
        "changed": {
            path for path in actual.keys() & expected.keys() if actual[path] != expected[path]
        },
        "obsolete": set(expected) - set(actual),
    }


LEGACY_PAYLOAD = json.loads((ROOT / "tests/fixtures/english-register-legacy.json").read_text())
LEGACY = legacy_inventory(LEGACY_PAYLOAD)
HISTORICAL_PAYLOAD = json.loads(
    (ROOT / "tests/fixtures/english-register-historical.json").read_text()
)
HISTORICAL = historical_inventory(HISTORICAL_PAYLOAD)
DOCUMENTS = list(layers())
TEXT_IDS = {doc["text"] for doc in DOCUMENTS}
ALLOWANCES = combine_inventories(LEGACY, HISTORICAL, TEXT_IDS)
# Keep the existing conclusion contract independent of current prose: only an explicit
# legacy prose field can defer it, and that field itself is checked by the all-text gate.
CONCLUSION_TEXTS = [
    doc["text"]
    for doc in DOCUMENTS
    if not any(
        path[0] == "segments" and path[-1] == "translation" for path in LEGACY.get(doc["text"], {})
    )
]


def test_register_inventory_has_subjects_and_no_missing_or_duplicate_texts():
    assert DOCUMENTS
    assert len(DOCUMENTS) == len(TEXT_IDS)
    assert set(LEGACY) <= TEXT_IDS
    assert len(CONCLUSION_TEXTS) > 700


@pytest.mark.parametrize("doc", DOCUMENTS, ids=lambda doc: doc["text"])
def test_every_text_preserves_english_register(doc):
    assert not any(register_changes(doc, ALLOWANCES).values()), doc["text"]


def test_no_prose_change_can_exempt_any_existing_text():
    for doc in DOCUMENTS:
        mutant = deepcopy(doc)
        segment = next(key for key, value in mutant["segments"].items() if value.get("translation"))
        mutant["segments"][segment]["translation"] += " Thy"
        changes = register_changes(mutant, ALLOWANCES)
        assert ("segments", segment, "translation") in changes["new"] | changes["changed"], doc[
            "text"
        ]


def test_changed_and_obsolete_legacy_fields_are_not_blanket_exceptions():
    documents = {doc["text"]: doc for doc in DOCUMENTS}
    for text, fields in ALLOWANCES.items():
        for path in fields:
            for replacement, expected in [
                (None, "changed"),
                ("A contemporary control", "obsolete"),
            ]:
                mutant = deepcopy(documents[text])
                parent = mutant
                for key in path[:-1]:
                    parent = parent[key]
                parent[path[-1]] = (
                    replacement if replacement is not None else parent[path[-1]] + " Thy"
                )
                assert path in register_changes(mutant, ALLOWANCES)[expected], (
                    text,
                    path,
                    expected,
                )


@pytest.mark.parametrize("text", ["control.new", next(iter(LEGACY))])
@pytest.mark.parametrize("field", ["translation", "gloss", "note"])
def test_new_fields_are_checked_in_new_and_legacy_texts(text, field):
    doc = {"text": text, "segments": {}, "words": {}}
    if field == "translation":
        doc["segments"]["new"] = {field: "Your mercy"}
        path = ("segments", "new", field)
    else:
        doc["words"]["new"] = {field: "Your mercy"}
        path = ("words", "new", field)
    assert path not in register_changes(doc, LEGACY)["new"]
    doc[path[0]][path[1]][path[2]] = "Thy mercy"
    assert path in register_changes(doc, LEGACY)["new"]


@pytest.mark.parametrize("mutation", ["text", "field", "hash", "status"])
def test_invalid_or_duplicate_legacy_allowances_are_rejected(mutation):
    payload = deepcopy(LEGACY_PAYLOAD)
    if mutation == "text":
        payload["records"].append(deepcopy(payload["records"][0]))
    elif mutation == "field":
        payload["records"][0]["fields"].append(deepcopy(payload["records"][0]["fields"][0]))
    elif mutation == "hash":
        payload["records"][0]["fields"][0]["sha256"] = "invalid"
    else:
        payload["status"] = "approved"
    with pytest.raises(AssertionError):
        legacy_inventory(payload)


@pytest.mark.parametrize("mutation", ["status", "hash", "duplicate", "reason", "basis", "path"])
def test_invalid_historical_register_records_are_rejected(mutation):
    payload = deepcopy(HISTORICAL_PAYLOAD)
    record = payload["records"][0]
    if mutation == "status":
        payload["status"] = "approved"
    elif mutation == "hash":
        record["fields"][0]["sha256"] = "invalid"
    elif mutation == "duplicate":
        record["fields"].append(deepcopy(record["fields"][0]))
    elif mutation == "reason":
        record["reason"] = " "
    elif mutation == "basis":
        del record["basis_use"]
    else:
        record["fields"][0]["path"] = ["words", "w347", "gloss"]
    with pytest.raises(AssertionError):
        historical_inventory(payload)


def test_register_inventories_reject_overlap_and_unknown_subjects():
    with pytest.raises(AssertionError):
        combine_inventories(HISTORICAL, HISTORICAL, TEXT_IDS)
    with pytest.raises(AssertionError):
        combine_inventories(LEGACY, {"missing.text": next(iter(HISTORICAL.values()))}, TEXT_IDS)


def assert_historical_wording_bases(payload, uses):
    historical_inventory(payload)
    for record in payload["records"]:
        assert record["basis_use"] in uses
        use = uses[record["basis_use"]]
        assert use["role"] == "historical_wording_basis"
        assert use["decision"] in {"RETAIN", "RETAIN_WITH_CORRECTION"}
        assert use["address"]["kind"] == "segment"
        assert use["address"]["text"] == record["text"]
        assert [field["path"] for field in record["fields"]] == [
            ["segments", use["address"]["segment"], "translation"]
        ]


def test_historical_register_remains_bound_to_its_exact_wording_basis():
    uses = {
        use["id"]: use
        for use in json.loads((ROOT / "languages/en/bibliography.json").read_text())["uses"]
    }
    assert_historical_wording_bases(HISTORICAL_PAYLOAD, uses)


@pytest.mark.parametrize(
    "damage",
    [
        "COMPARATOR",
        "REMOVE",
        "REPLACE",
        "UNVERIFIED_NO_DIRECT_EVIDENCE",
        "text",
        "segment",
        "text-wide",
        "missing-basis",
        "unknown-basis",
        "multiple-fields",
    ],
)
def test_exact_historical_source_binding_rejects_damage_then_restores(damage):
    payload = deepcopy(HISTORICAL_PAYLOAD)
    uses = {
        use["id"]: use
        for use in json.loads((ROOT / "languages/en/bibliography.json").read_text())["uses"]
    }
    saved_payload, saved_uses = deepcopy(payload), deepcopy(uses)
    assert_historical_wording_bases(payload, uses)
    record = payload["records"][0]
    use = uses[record["basis_use"]]
    if damage == "COMPARATOR":
        use["role"] = "historical_wording_comparator"
    elif damage in {"REMOVE", "REPLACE", "UNVERIFIED_NO_DIRECT_EVIDENCE"}:
        use["decision"] = damage
    elif damage == "text":
        use["address"]["text"] = "orationes.magnificat"
    elif damage == "segment":
        use["address"]["segment"] = "s087"
    elif damage == "text-wide":
        use["address"] = {"kind": "text", "text": record["text"]}
    elif damage == "missing-basis":
        del record["basis_use"]
    elif damage == "unknown-basis":
        record["basis_use"] = "use.en.missing-historical-basis"
    else:
        additional = deepcopy(record["fields"][0])
        additional["path"] = ["segments", "s087", "translation"]
        record["fields"].append(additional)
    with pytest.raises(AssertionError):
        assert_historical_wording_bases(payload, uses)
    payload.clear()
    payload.update(saved_payload)
    uses.clear()
    uses.update(saved_uses)
    assert payload == HISTORICAL_PAYLOAD
    assert uses == saved_uses
    assert_historical_wording_bases(payload, uses)


def test_historical_field_deletion_change_and_same_text_additions_are_detected():
    documents = {doc["text"]: doc for doc in DOCUMENTS}
    for text, fields in HISTORICAL.items():
        original = documents[text]
        assert not any(register_changes(original, ALLOWANCES).values())
        for field in fields:
            mutant = deepcopy(original)
            del mutant[field[0]][field[1]][field[2]]
            assert field in register_changes(mutant, ALLOWANCES)["obsolete"]
            mutant[field[0]][field[1]][field[2]] = original[field[0]][field[1]][field[2]] + " Thy"
            assert field in register_changes(mutant, ALLOWANCES)["changed"]
            mutant[field[0]][field[1]][field[2]] = original[field[0]][field[1]][field[2]]
            assert not any(register_changes(mutant, ALLOWANCES).values())
        for section, key, name in [
            ("segments", "new", "translation"),
            ("words", "w347", "gloss"),
            ("words", "w347", "explanation"),
        ]:
            mutant = deepcopy(original)
            mutant[section].setdefault(key, {})[name] = "Thy mercy"
            assert (section, key, name) in register_changes(mutant, ALLOWANCES)["new"]
            assert not any(register_changes(original, ALLOWANCES).values())


def test_the_check_sees_a_traditional_gloss_in_a_contemporary_prayer():
    doc = json.loads((ROOT / "languages/en/texts/ordinarium/gloria.json").read_text())
    assert contemporary(doc) and mixed_fields(doc) == []
    word = next(iter(doc["words"]))
    doc["words"][word]["gloss"] = "Thy"
    assert mixed_fields(doc) == [(("words", word, "gloss"), "Thy")]


def test_king_gospel_distinguishes_jesus_and_pilate():
    path = "languages/en/texts/proprium/d-n-iesu-christi-regis-evangelium.json"
    words = json.loads((ROOT / path).read_bytes())["words"]
    assert words["w015"]["gloss"] == "yourself"
    assert words["w021"]["gloss"] == "you"
    # Pilate addresses Christ in these three occurrences.
    assert all(words[wid]["gloss"] == "You" for wid in ("w008", "w035", "w077"))
    # Jesus addresses Pilate, but this word begins a sentence.
    assert words["w080"]["gloss"] == "You"


def test_rosary_secret_conclusion_returns_to_the_son():
    path = "languages/en/texts/proprium/beatae-mariae-virginis-a-rosario-secreta.json"
    prose = json.loads((ROOT / path).read_bytes())["segments"]["s01"]["translation"]
    assert "His promises. He lives and reigns with You" in prose
    assert "His promises, who" not in prose
    assert "You live and reign" not in prose


def test_holy_cross_postcommunion_preserves_its_petition():
    name = "exaltatio-sanctae-crucis-postcommunio"
    core = json.loads((ROOT / f"texts/proprium/{name}.json").read_bytes())
    layer = json.loads((ROOT / f"languages/en/texts/proprium/{name}.json").read_bytes())
    body = core["segments"][0]["words"][:17]
    assert [w["lemma"] for w in body] == [
        "adsum",
        "nos",
        "dominus",
        "deus",
        "noster",
        "et",
        "qui",
        "sanctus",
        "crux",
        "laetor",
        "facio",
        "honor",
        "is",
        "quoque",
        "perpetuus",
        "defendo",
        "subsidium",
    ]
    prose = layer["segments"]["s01"]["translation"]
    assert prose.startswith(
        "Stand by us, O Lord our God, and also defend, with the unceasing aid of the "
        "holy Cross, those whom You make rejoice in its honor. Through our Lord"
    )
    assert "sacrament" not in prose
    assert layer["segments"]["s02"]["translation"] == "Amen."


def conclusion_matches(prose, english, *, duration):
    variants = (english,)
    if english.startswith("Through the same "):
        variants += (english.replace("Through the same ", "Through this same ", 1),)
    endings = ENDINGS if duration else ("",)
    return prose.endswith(tuple(variant + ending for variant in variants for ending in endings))


@pytest.mark.parametrize("determiner", ["the", "this"])
@pytest.mark.parametrize("duration", [False, True])
def test_eundem_keeps_both_contemporary_anaphoric_forms(determiner, duration):
    english = next(value for key, value in CONCLUSIONS.items() if " eundem " in key)
    prose = english.replace("Through the same ", f"Through {determiner} same ", 1)
    if duration:
        prose += " forever and ever."
    assert conclusion_matches(prose, english, duration=duration)


@pytest.mark.parametrize(
    "old,new",
    [
        ("Your Son", "Thy Son"),
        ("our Lord", "Lord"),
        ("who lives", "who will live"),
        ("the same", "another"),
    ],
)
def test_eundem_alternative_does_not_erase_register_or_meaning(old, new):
    english = next(value for key, value in CONCLUSIONS.items() if " eundem " in key)
    assert not conclusion_matches(
        english.replace(old, new) + " forever and ever.", english, duration=True
    )


def test_plain_dominum_does_not_acquire_an_unsupported_same():
    english = next(value for key, value in CONCLUSIONS.items() if " eundem " not in key)
    assert not conclusion_matches(
        english.replace("Through our", "Through this same") + " forever and ever.",
        english,
        duration=True,
    )


def test_contemporary_orations_conclude_in_the_same_register():
    seen = 0
    for text in CONCLUSION_TEXTS:
        if text in HISTORICAL_CONCLUSION:
            continue
        category, name = text.split(".", 1)
        latin = json.loads((ROOT / "texts" / category / f"{name}.json").read_text())
        en = json.loads((ROOT / "languages/en/texts" / category / f"{name}.json").read_text())
        for seg in latin["segments"]:
            forms = " ".join(norm(w["form"]) for w in seg.get("words", []))
            prose = en["segments"].get(seg["id"], {}).get("translation") or ""
            for incipit, english in CONCLUSIONS.items():
                if text in {
                    "proprium.vigilia-paschalis-collecta",
                    "proprium.dominica-resurrectionis-collecta",
                    "proprium.dominica-ii-post-pascha-collecta",
                    "proprium.vigilia-paschalis-secreta",
                }:
                    english = (
                        "Through "
                        + ("the same " if " eundem " in incipit else "")
                        + "Jesus Christ, our Lord, Your Son, who, as God, "
                        "lives and reigns with You in the unity of the Holy Spirit"
                    )
                if forms.endswith(incipit + " per omnia saecula saeculorum"):
                    assert conclusion_matches(prose, english, duration=True), (
                        text,
                        seg["id"],
                    )
                    seen += 1
                elif forms.endswith(incipit):
                    assert conclusion_matches(prose, english, duration=False), (
                        text,
                        seg["id"],
                    )
                    seen += 1
    assert seen > 150


def test_baptist_secret_retains_due_honor_and_identifies_the_son_after_both_actions():
    name = "nativitas-sancti-ioannis-baptistae-secreta"
    core = json.loads((ROOT / f"texts/proprium/{name}.json").read_bytes())
    layer = json.loads((ROOT / f"languages/en/texts/proprium/{name}.json").read_bytes())
    words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    assert [words[w]["lemma"] for w in ["w008", "w009"]] == ["honor", "debeo"]
    prose = layer["segments"]["s01"]["translation"]
    assert "celebrating with due honor the birth of him" in prose
    assert (
        "both foretold the coming of the Savior of the world and made His presence known" in prose
    )
    assert "known: our Lord Jesus Christ, Your Son. He lives and reigns with You" in prose
    assert "You live and reign" not in prose
    # Plural altaria can name one altar; grammar alone must not force a rewrite.
    assert "Your altar with gifts" in prose and words["w004"]["morph"]["number"] == "pl"
    assert layer["segments"]["s02"]["translation"] == "forever and ever."
    assert layer["segments"]["s03"]["translation"] == "Amen."


@pytest.mark.parametrize(
    "segment,members,anchor,gloss",
    [
        ("s01", ["w006", "w007"], "w007", "his birth"),
        ("s01", ["w008", "w009"], "w008", "with due honor"),
        ("s01", ["w021", "w022"], "w021", "our Lord"),
        ("s01", ["w025", "w026"], "w025", "Your Son"),
        ("s01", ["w034", "w035"], "w034", "of the Holy Spirit"),
        ("s02", ["w037", "w038", "w039", "w040"], "w039", "forever and ever"),
    ],
)
def test_baptist_secret_natural_groups_keep_one_complete_realization(
    segment, members, anchor, gloss
):
    name = "nativitas-sancti-ioannis-baptistae-secreta"
    core = json.loads((ROOT / f"texts/proprium/{name}.json").read_bytes())
    layer = json.loads((ROOT / f"languages/en/texts/proprium/{name}.json").read_bytes())
    groups = layer["segments"][segment].get("alignments", [])
    assert {"words": members, "anchor": anchor, "gloss": gloss} in groups
    assert all("gloss" not in layer["words"][wid] for wid in members)
    assert layer["words"]["w001"]["gloss"] == "Your"
    assert layer["words"]["w003"]["gloss"] == "with gifts"
    assert interlinear.check(core, layer) == []


def test_baptist_postcommunion_keeps_its_valid_immediate_christ_relative():
    name = "nativitas-sancti-ioannis-baptistae-postcommunio"
    prose = json.loads((ROOT / f"languages/en/texts/proprium/{name}.json").read_bytes())[
        "segments"
    ]["s01"]["translation"]
    assert "Your Son, our Lord Jesus Christ, who lives and reigns with You" in prose


def test_second_paschal_collect_cannot_self_exempt_from_contemporary_register():
    path = "languages/en/texts/proprium/dominica-ii-post-pascha-collecta.json"
    doc = json.loads((ROOT / path).read_bytes())
    assert contemporary(doc)
    assert mixed_fields(doc) == []

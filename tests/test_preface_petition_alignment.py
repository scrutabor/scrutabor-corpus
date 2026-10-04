"""Keep each preface admission petition complete and realized exactly once."""

import json
from copy import deepcopy

import pytest

from checks.interlinear import check, effective_gloss
from checks.language_packs import check_layer
from checks.layout import CORPUS
from checks.prose import check as check_prose

SITES = [
    ("beatae-mariae-virginis-in-annuntiatione", "s08", 73),
    ("beatae-mariae-virginis-in-assumptione", "s08", 73),
    ("beatae-mariae-virginis-in-conceptione-immaculata", "s08", 74),
    ("beatae-mariae-virginis-in-nativitate", "s08", 73),
    ("beatae-mariae-virginis-in-transfixione", "s08", 73),
    ("beatae-mariae-virginis-in-visitatione", "s08", 73),
    ("beatae-mariae-virginis", "s08", 73),
    ("communis", "s06", 45),
    ("quadragesimae", "s07", 56),
    ("sanctae-crucis", "s07", 69),
    ("sancti-ioseph-in-festivitate", "s08", 88),
    ("sancti-ioseph-in-solemnitate", "s08", 88),
]
LEMMAS = [
    "cum",
    "qui",
    "et",
    "noster",
    "vox",
    "ut",
    "admitto",
    "iubeo",
    "deprecor",
    "supplex",
    "confessio",
    "dico",
]
# These complete construction fixtures are not a universal rule for iubeo.
# Retain supported causative/passive and bid/command alternatives; do not
# mistake an exact candidate choice for the only possible faithful English.
REQUESTS = {
    "pl": (
        "Prosimy, abyś nakazał dopuścić także nasze głosy wraz z nimi",
        "Prosimy, abyś nakazał, by także nasze głosy zostały dopuszczone wraz z nimi",
    ),
    "en": (
        "We pray that You command our voices also to be admitted with them",
        "We pray that You bid our voices also be admitted with them",
        "We pray that You command that our voices also be admitted with them",
    ),
}
MANNER = {"pl": "mówiąc w pokornym wyznaniu", "en": "saying in humble confession"}
NOTES = {
    "pl": (
        "Iúbeas to 2. osoba liczby pojedynczej trybu łączącego. Zależność od deprecámur "
        "wyraża prośbę skierowaną do Boga, aby nakazał dopuszczenie naszych głosów. "
        "Polskie „abyś nakazał dopuścić” zachowuje tę zależność. Nasze głosy są dopuszczane, "
        "a nie same dopuszczają innych."
    ),
    "en": (
        "Iúbeas is second-person singular subjunctive within the request expressed by deprecámur. "
        "We ask God to command that our voices be admitted. The prayer is not a command "
        "addressed to God."
    ),
}
CONFESSION_NOTES = {
    "pl": "Wyznanie nie winy, lecz chwały — to, co za chwilę wyśpiewa Sanctus.",
    "en": "A confession not of guilt but of praise — what the Sanctus is about to sing.",
}


def load(slug, language):
    name = "praefatio-" + slug + ".json"
    doc = json.loads((CORPUS / "texts/ordinarium" / name).read_text())
    layer = json.loads((CORPUS / "languages" / language / "texts/ordinarium" / name).read_text())
    return doc, layer


def ids(first):
    return [f"w{i:03d}" for i in range(first, first + 12)]


def assert_petition(doc, layer, language, segment, first):
    words = next(s for s in doc["segments"] if s["id"] == segment)["words"]
    members = ids(first)
    assert [w["id"] for w in words] == members
    assert [w["lemma"] for w in words] == LEMMAS
    assert words[6]["morph"]["voice"] == "pass"
    assert words[7]["morph"]["person"] == 2 and words[7]["morph"]["mood"] == "subj"
    assert words[8]["morph"]["person"] == 1 and words[8]["morph"]["number"] == "pl"
    groups = layer["segments"][segment].get("alignments", [])
    assert len(groups) == 2
    assert [g["words"] for g in groups] == [members[:9], members[9:]]
    assert [g["anchor"] for g in groups] == [members[8], members[11]]
    assert all(set(g) == {"words", "anchor", "gloss"} for g in groups)
    assert groups[0]["gloss"] in REQUESTS[language]
    assert groups[1]["gloss"] == MANNER[language]
    assert all("gloss" not in layer["words"].get(wid, {}) for wid in members)
    assert all(wid in layer["words"] for wid in members)
    assert list(layer["words"]) == [w["id"] for s in doc["segments"] for w in s.get("words", [])]
    assert (
        check_layer(
            doc,
            layer,
            CORPUS
            / "languages"
            / language
            / "texts"
            / "ordinarium"
            / (doc["id"].split(".", 1)[1] + ".json"),
        )
        == []
    )
    assert check(doc, layer) == []
    realized = [
        (wid, effective_gloss(layer, wid)) for wid in members if effective_gloss(layer, wid)
    ]
    assert realized == [
        (groups[0]["anchor"], groups[0]["gloss"]),
        (groups[1]["anchor"], groups[1]["gloss"]),
    ]


def protected_payload(layer, segment, first):
    """Normalize only this unit's allowed fields, for before/after comparison."""
    payload = deepcopy(layer)
    payload["segments"][segment].pop("alignments", None)
    for wid in ids(first):
        entry = payload["words"].get(wid, {})
        entry.pop("gloss", None)
        if layer["text"] == "ordinarium.praefatio-communis" and wid == "w052":
            entry.pop("explanation", None)
        if not entry:
            payload["words"].pop(wid, None)
    return payload


def fixture(doc, layer, language, segment, first):
    candidate = deepcopy(layer)
    members = ids(first)
    candidate["segments"][segment]["alignments"] = [
        {"words": members[:9], "anchor": members[8], "gloss": REQUESTS[language][0]},
        {"words": members[9:], "anchor": members[11], "gloss": MANNER[language]},
    ]
    for wid in members:
        entry = candidate["words"].get(wid, {})
        entry.pop("gloss", None)
        candidate["words"][wid] = entry
    assert check(doc, candidate) == []
    return candidate


def test_preface_petition_population_is_exact():
    found = set()
    for path in (CORPUS / "texts/ordinarium").glob("praefatio-*.json"):
        doc = json.loads(path.read_text())
        for segment in doc["segments"]:
            if [w["lemma"] for w in segment.get("words", [])] == LEMMAS:
                found.add(
                    (
                        path.stem.removeprefix("praefatio-"),
                        segment["id"],
                        int(segment["words"][0]["id"][1:]),
                    )
                )
    assert found == set(SITES) and len(found) == 12


@pytest.mark.parametrize("slug,segment,first", SITES)
@pytest.mark.parametrize("language", ["pl", "en"])
def test_preface_petition_is_a_complete_target_construction(slug, segment, first, language):
    doc, layer = load(slug, language)
    assert_petition(doc, layer, language, segment, first)


def test_petitions_cover_288_target_tokens_with_48_realizations():
    members, groups = 0, 0
    for language in ["pl", "en"]:
        for slug, segment, first in SITES:
            doc, layer = load(slug, language)
            assert_petition(doc, layer, language, segment, first)
            alignments = layer["segments"][segment]["alignments"]
            members += sum(len(g["words"]) for g in alignments)
            groups += len(alignments)
    assert (members, groups) == (288, 48)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_common_iubeas_note_distinguishes_request_from_requested_command(language):
    _, layer = load("communis", language)
    assert layer["words"]["w052"]["explanation"] == NOTES[language]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_common_confession_of_praise_note_is_retained(language):
    _, layer = load("communis", language)
    assert layer["words"]["w055"]["explanation"] == CONFESSION_NOTES[language]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_petition_explanations_follow_the_reader_prose_contract(language):
    _, layer = load("communis", language)
    assert check_prose(layer) == []
    before, after = (". Nasze", "; nasze") if language == "pl" else (". The prayer", "; the prayer")
    layer["words"]["w052"]["explanation"] = NOTES[language].replace(before, after)
    assert any("w052.explanation" in error and "semicolon" in error for error in check_prose(layer))


@pytest.mark.parametrize(
    "language,phrase", [(lang, phrase) for lang in REQUESTS for phrase in REQUESTS[lang]]
)
def test_supported_complete_alternatives_are_not_rejected(language, phrase):
    slug, segment, first = SITES[0]
    doc, layer = load(slug, language)
    candidate = fixture(doc, layer, language, segment, first)
    candidate["segments"][segment]["alignments"][0]["gloss"] = phrase
    assert_petition(doc, candidate, language, segment, first)
    assert protected_payload(layer, segment, first) == protected_payload(candidate, segment, first)


@pytest.mark.parametrize("slug,segment,first", SITES)
@pytest.mark.parametrize("language", ["pl", "en"])
def test_direct_gloss_reintroduction_mutations_are_rejected(slug, segment, first, language):
    doc, layer = load(slug, language)
    layer["words"].setdefault(ids(first)[7], {})["gloss"] = (
        "pozwolił" if language == "pl" else "may allow"
    )
    assert any("exactly one" in error for error in check(doc, layer))
    with pytest.raises(AssertionError):
        assert_petition(doc, layer, language, segment, first)


STRUCTURAL_MUTATIONS = (
    "missing-member",
    "reversed-members",
    "overlap",
    "outside-segment",
    "missing-anchor",
    "outside-anchor",
    "empty-gloss",
    "technical-marker",
    "extra-zero-reason",
)


def mutate_structure(layer, segment, mutation):
    groups = layer["segments"][segment]["alignments"]
    if mutation == "missing-member":
        groups[0]["words"].pop(4)
    elif mutation == "reversed-members":
        groups[0]["words"].reverse()
    elif mutation == "overlap":
        groups[1]["words"].insert(0, groups[0]["words"][-1])
    elif mutation == "outside-segment":
        groups[0]["words"][0] = "w001"
    elif mutation == "missing-anchor":
        groups[0].pop("anchor")
    elif mutation == "outside-anchor":
        groups[0]["anchor"] = groups[1]["words"][-1]
    elif mutation == "empty-gloss":
        groups[0]["gloss"] = ""
    elif mutation == "technical-marker":
        groups[0]["gloss"] = "[included]"
    elif mutation == "extra-zero-reason":
        groups[0]["reason"] = "word-order"
    else:
        raise AssertionError(mutation)


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("mutation", STRUCTURAL_MUTATIONS)
def test_alignment_mutations_fail_existing_structural_contract(language, mutation):
    slug, segment, _first = SITES[0]
    doc, layer = load(slug, language)
    mutate_structure(layer, segment, mutation)
    assert check(doc, layer)


BROKEN_REQUESTS = {
    "pl": [
        "Nasze głosy aby zostały dopuszczone pozwolił prosimy",
        "Prosimy, abyś pozwolił także naszym głosom dołączyć do nich",
        "Prosimy, aby nasze głosy dopuściły ich wraz z nami",
        "Wraz z nimi prosimy, abyś nakazał dopuścić nasze głosy",
        "Prosimy, abyś nakazał dopuścić także nasze głosy",
    ],
    "en": [
        "Our voices that to be admitted may allow we pray",
        "We pray that You may allow our voices to join theirs",
        "We pray that our voices admit them with us",
        "With them we pray that You command our voices to be admitted",
        "We pray that You command our voices to be admitted",
    ],
}


@pytest.mark.parametrize(
    "language,phrase",
    [(lang, phrase) for lang in BROKEN_REQUESTS for phrase in BROKEN_REQUESTS[lang]],
)
def test_incomplete_or_reassigned_construction_mutations_are_rejected(language, phrase):
    slug, segment, first = SITES[0]
    doc, layer = load(slug, language)
    layer["segments"][segment]["alignments"][0]["gloss"] = phrase
    with pytest.raises(AssertionError):
        assert_petition(doc, layer, language, segment, first)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_language_swapping_mutations_are_rejected(language):
    slug, segment, first = SITES[0]
    doc, layer = load(slug, language)
    other = "en" if language == "pl" else "pl"
    layer["segments"][segment]["alignments"][0]["gloss"] = REQUESTS[other][0]
    with pytest.raises(AssertionError):
        assert_petition(doc, layer, language, segment, first)


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize(
    "mutation", ["remove-empty-members", "remove-one-member", "reorder-members"]
)
def test_required_word_object_mutations_are_rejected(language, mutation):
    slug, segment, first = SITES[0]
    doc, layer = load(slug, language)
    members = ids(first)
    if mutation == "remove-empty-members":
        for wid in members:
            if not layer["words"][wid]:
                del layer["words"][wid]
    elif mutation == "remove-one-member":
        del layer["words"][members[0]]
    else:
        keys = list(layer["words"])
        a, b = keys.index(members[0]), keys.index(members[1])
        keys[a], keys[b] = keys[b], keys[a]
        layer["words"] = {wid: layer["words"][wid] for wid in keys}
    path = CORPUS / "languages" / language / "texts/ordinarium" / ("praefatio-" + slug + ".json")
    assert any("word coverage or order" in error for error in check_layer(doc, layer, path))
    with pytest.raises(AssertionError):
        assert_petition(doc, layer, language, segment, first)


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize(
    "mutation", ["prose", "other-gloss", "confession-note", "about", "status", "provenance"]
)
def test_protected_payload_mutations_are_detected(language, mutation):
    _, before = load("communis", language)
    after = deepcopy(before)
    if mutation == "prose":
        after["segments"]["s06"]["translation"] += " Changed."
    elif mutation == "other-gloss":
        after["words"]["w001"]["gloss"] = "Changed"
    elif mutation == "confession-note":
        after["words"]["w055"]["explanation"] = "Changed"
    elif mutation == "about":
        after["about"] += " Changed."
    elif mutation == "status":
        after["status"] = "accepted"
    elif mutation == "provenance":
        after["provenance"] = {"reviewed_on": "2026-10-04"}
    assert protected_payload(before, "s06", 45) != protected_payload(after, "s06", 45)

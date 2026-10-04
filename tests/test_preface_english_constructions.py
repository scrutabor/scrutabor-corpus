"""Guard reviewed English constructions and their untouched context."""

import json
from copy import deepcopy
from typing import Any

import pytest

from checks.interlinear import check, effective_gloss
from checks.language_packs import check_layer
from checks.layout import CORPUS, formatted
from checks.translation_provenance import canonical_hash, source_payload

# Fixed contextual fixtures, not blanket translation rules. The baseline hashes
# bind every unselected field; only the explicit construction/prose changes below
# may be reversed before comparison.
FIXTURES: dict[str, Any] = {
    "sites": [
        {
            "slug": "apostolorum",
            "segment": "s04",
            "words": ["w028", "w029", "w030", "w031"],
            "anchor": "w031",
            "gloss": "that it may be governed by those same leaders",
        },
        {
            "slug": "apostolorum",
            "segment": "s04",
            "words": ["w032", "w033", "w034", "w035", "w036", "w037", "w038", "w039"],
            "anchor": "w037",
            "gloss": "whom You appointed to preside over it as shepherds, deputies in Your work",
        },
        {
            "slug": "ascensionis",
            "segment": "s02",
            "words": ["w042", "w043", "w044", "w045", "w046", "w047", "w048"],
            "anchor": "w046",
            "gloss": "that He might grant us a share in His divinity",
        },
        {
            "slug": "epiphaniae",
            "segment": "s04",
            "words": ["w031", "w032", "w033", "w034", "w035", "w036"],
            "anchor": "w036",
            "gloss": "He renewed us by the new light of His immortality",
        },
        {
            "slug": "nativitatis",
            "segment": "s04",
            "words": ["w027", "w028", "w029", "w030", "w031", "w032", "w033", "w034"],
            "anchor": "w034",
            "gloss": "a new light of Your glory has shone upon the eyes of our mind",
        },
        {
            "slug": "paschalis-in-die",
            "segment": "s01",
            "words": ["w021", "w022", "w023", "w024", "w025", "w026"],
            "anchor": "w024",
            "gloss": "for Christ, our Passover, has been sacrificed",
        },
        {
            "slug": "paschalis-in-nocte",
            "segment": "s01",
            "words": ["w021", "w022", "w023", "w024", "w025", "w026"],
            "anchor": "w024",
            "gloss": "for Christ, our Passover, has been sacrificed",
        },
        {
            "slug": "d-n-iesu-christi-regis",
            "segment": "s04",
            "words": ["w053", "w054", "w055", "w056", "w057"],
            "anchor": "w054",
            "gloss": "with all creatures subjected to His dominion",
        },
        {
            "slug": "d-n-iesu-christi-regis",
            "segment": "s04",
            "words": ["w058", "w059", "w060", "w061", "w062", "w063", "w064", "w065"],
            "anchor": "w064",
            "gloss": "He might deliver to Your infinite Majesty an eternal and universal kingdom",
        },
        {
            "slug": "sanctissimae-trinitatis",
            "segment": "s05",
            "words": ["w051", "w052"],
            "anchor": "w051",
            "gloss": "by Your revelation",
        },
        {
            "slug": "sancti-ioseph-in-festivitate",
            "segment": "s05",
            "words": ["w062", "w063"],
            "anchor": "w063",
            "gloss": "in a father’s place",
        },
        {
            "slug": "sancti-ioseph-in-solemnitate",
            "segment": "s05",
            "words": ["w062", "w063"],
            "anchor": "w063",
            "gloss": "in a father’s place",
        },
    ],
    "baselines": {
        "apostolorum": {
            "protected_digest": "3af0afbc1db7fe07e1502f8cd3b409f8ab40f03a9d59d6bce6205c015989cf0b",
            "words": {
                "w028": {"gloss": "that"},
                "w029": {"gloss": "by those same"},
                "w030": {"gloss": "rulers"},
                "w031": {"gloss": "may be governed"},
                "w032": {"gloss": "whom"},
                "w033": {"gloss": "work"},
                "w034": {"gloss": "Your"},
                "w035": {"gloss": "vicars"},
                "w036": {"gloss": "over it"},
                "w037": {"gloss": "appointed"},
                "w038": {"gloss": "to preside"},
                "w039": {"gloss": "as pastors"},
            },
            "had_alignments": {"s04": False},
            "absorbed": {"s04": []},
            "source_contexts": {
                "s04": "49d97120a9e49b56a35a801596088feb3c5fb6e37617a352f893ecc61d8fefdc"
            },
        },
        "ascensionis": {
            "protected_digest": "0d9de544a327cf33f8f646cf3d4a68798174b57edff12db87313aa7bb8205e11",
            "words": {
                "w042": {"gloss": "that"},
                "w043": {"gloss": "us"},
                "w044": {"gloss": "of divinity"},
                "w045": {"gloss": "His"},
                "w046": {"gloss": "might grant"},
                "w047": {"gloss": "to be"},
                "w048": {"gloss": "partakers"},
            },
            "had_alignments": {"s02": True},
            "absorbed": {"s02": []},
            "source_contexts": {
                "s02": "b0c2f06d8b7484c5db1fc29da646b30f75460fbaffc4266dc4ccbc51ef4dbde1"
            },
        },
        "d-n-iesu-christi-regis": {
            "protected_digest": "88077ae262680274331b3a45267033e94b5938da619cfd9209872e005b73d38a",
            "words": {
                "w053": {"gloss": "His"},
                "w054": {"gloss": "having been subjected"},
                "w055": {"gloss": "dominion"},
                "w056": {"gloss": "all"},
                "w057": {"gloss": "creatures"},
                "w058": {"gloss": "eternal"},
                "w059": {"gloss": "and"},
                "w060": {"gloss": "universal"},
                "w061": {"gloss": "kingdom"},
                "w062": {"gloss": "infinite"},
                "w063": {"gloss": "Your"},
                "w064": {"gloss": "might deliver"},
                "w065": {"gloss": "to Majesty"},
            },
            "had_alignments": {"s04": True},
            "absorbed": {"s04": []},
            "source_contexts": {
                "s04": "619a0870ec08c6c334e1f6839d32ed54fe19711e506300d062295eb16412ecab"
            },
        },
        "epiphaniae": {
            "protected_digest": "0d6b47b756252c50c42267642caa3c3a8e29c89fd69c473a51d24db90276922d",
            "words": {
                "w031": {"gloss": "new"},
                "w032": {"gloss": "us"},
                "w033": {"gloss": "immortality"},
                "w034": {"gloss": "His"},
                "w035": {"gloss": "light"},
                "w036": {"gloss": "renewed"},
            },
            "had_alignments": {"s04": True},
            "absorbed": {"s04": []},
            "source_contexts": {
                "s04": "507282711ff7727e17ae8b6bc2617689f8ee33cca86a99405ace56107f721316"
            },
        },
        "nativitatis": {
            "protected_digest": "a4d9055b76831a9a123a2d8100eda85a31060dd99c65a05b47894481890c8410",
            "words": {
                "w027": {"gloss": "new"},
                "w028": {"gloss": "of mind"},
                "w029": {"gloss": "our"},
                "w030": {"gloss": "to the eyes"},
                "w031": {"gloss": "a light"},
                "w032": {"gloss": "Your"},
                "w033": {"gloss": "of glory"},
                "w034": {"gloss": "has shone"},
            },
            "had_alignments": {"s04": False},
            "absorbed": {"s04": []},
            "source_contexts": {
                "s04": "43379d47ec2a5834c227408c971686546e103b16dce65bc0c17faef7b200077f"
            },
        },
        "paschalis-in-die": {
            "protected_digest": "4511ee06c90ad90ac51eb09ba80d917a5f1f3f8a94716f3a7778617ecb7c5f0c",
            "words": {
                "w021": {"gloss": "when"},
                "w022": {"gloss": "Pasch"},
                "w023": {"gloss": "our"},
                "w024": {},
                "w025": {},
                "w026": {"gloss": "Christ"},
            },
            "had_alignments": {"s01": True},
            "absorbed": {
                "s01": [
                    {"words": ["w024", "w025"], "anchor": "w024", "gloss": "has been sacrificed"}
                ]
            },
            "source_contexts": {
                "s01": "6a82e960e249fa38652f9df606de95db25e21b92e508adb3e2b3aec530a6ba66"
            },
            "prose": {
                "segment": "s01",
                "before": "Truly it is right and just, fitting "
                "and leading to salvation, that at all "
                "times we should praise You, O Lord, "
                "but more gloriously on this day above "
                "all, when Christ our Pasch was "
                "sacrificed. For He is the true Lamb "
                "who has taken away the sins of the "
                "world; who by dying has destroyed our "
                "death and by rising again has "
                "restored life. And therefore with "
                "Angels and Archangels, with Thrones "
                "and Dominions, and with all the host "
                "of the heavenly army, we sing the "
                "hymn of Your glory, evermore saying:",
                "after": "Truly it is right and just, fitting "
                "and leading to salvation, that at all "
                "times we should praise You, O Lord, "
                "but more gloriously on this day above "
                "all, for Christ, our Passover, has "
                "been sacrificed. For He is the true "
                "Lamb who has taken away the sins of "
                "the world; who by dying has destroyed "
                "our death and by rising again has "
                "restored life. And therefore with "
                "Angels and Archangels, with Thrones "
                "and Dominions, and with all the host "
                "of the heavenly army, we sing the hymn "
                "of Your glory, evermore saying:",
                "provenance_before": {
                    "site": "ordinarium.praefatio-paschalis-in-die.s01.en",
                    "text": "ordinarium.praefatio-paschalis-in-die",
                    "segment": "s01",
                    "language": "en",
                    "familiar_core": False,
                    "origin": "working-unsettled",
                    "review": "working",
                    "source_sha256": (
                        "6a82e960e249fa38652f9df606de95db25e21b92e508adb3e2b3aec530a6ba66"
                    ),
                    "target_sha256": (
                        "e9768cc9762d89f03119eabef68cbe850429b355ae07a6c67dbd20f6219d33be"
                    ),
                },
                "target_after": "4f05eb90b9b945cbe04fa122278fb0f99efd81adbb529a62209ffdccd6719d35",
            },
        },
        "paschalis-in-nocte": {
            "protected_digest": "ac47dd630ec6a43674f1de9cea1a291310bcef94ead164f3ce1c884e610201f1",
            "words": {
                "w021": {"gloss": "when"},
                "w022": {"gloss": "Pasch"},
                "w023": {"gloss": "our"},
                "w024": {},
                "w025": {},
                "w026": {"gloss": "Christ"},
            },
            "had_alignments": {"s01": True},
            "absorbed": {
                "s01": [
                    {"words": ["w024", "w025"], "anchor": "w024", "gloss": "has been sacrificed"}
                ]
            },
            "source_contexts": {
                "s01": "0bc62f66db072c4393eb13a4cf7727f2f128b328d40a0d07b3ae3f5b549f81d1"
            },
            "prose": {
                "segment": "s01",
                "before": "Truly it is right and just, fitting "
                "and leading to salvation, that at "
                "all times we should praise You, O "
                "Lord, but more gloriously on this "
                "night above all, when Christ our "
                "Pasch was sacrificed. For He is the "
                "true Lamb who has taken away the "
                "sins of the world; who by dying has "
                "destroyed our death and by rising "
                "again has restored life. And "
                "therefore with Angels and "
                "Archangels, with Thrones and "
                "Dominions, and with all the host of "
                "the heavenly army, we sing the hymn "
                "of Your glory, evermore saying:",
                "after": "Truly it is right and just, fitting "
                "and leading to salvation, that at "
                "all times we should praise You, O "
                "Lord, but more gloriously on this "
                "night above all, for Christ, our "
                "Passover, has been sacrificed. For "
                "He is the true Lamb who has taken "
                "away the sins of the world; who by "
                "dying has destroyed our death and by "
                "rising again has restored life. And "
                "therefore with Angels and "
                "Archangels, with Thrones and "
                "Dominions, and with all the host of "
                "the heavenly army, we sing the hymn "
                "of Your glory, evermore saying:",
                "provenance_before": {
                    "site": "ordinarium.praefatio-paschalis-in-nocte.s01.en",
                    "text": "ordinarium.praefatio-paschalis-in-nocte",
                    "segment": "s01",
                    "language": "en",
                    "familiar_core": False,
                    "origin": "working-unsettled",
                    "review": "working",
                    "source_sha256": (
                        "0bc62f66db072c4393eb13a4cf7727f2f128b328d40a0d07b3ae3f5b549f81d1"
                    ),
                    "target_sha256": (
                        "5de12dbd14c9260136d79859803c73390d55012775f9cbfb5c493179aeadd674"
                    ),
                },
                "target_after": "697736353e0d8e7e5607f21e2a1d77e98eb2fd8d91b1df5459644e10fe1fbee0",
            },
        },
        "sancti-ioseph-in-festivitate": {
            "protected_digest": "9898839d9fc959764a9139ddaf7f137114416eaab1f55ea91e53bc9b51c566fb",
            "words": {"w062": {"gloss": "with a father’s"}, "w063": {"gloss": "stead"}},
            "had_alignments": {"s05": True},
            "absorbed": {"s05": []},
            "source_contexts": {
                "s05": "2689e1c0225b4d5acf2ebf6bbcf84741f8682c95c57ce24df6a798c1ab8044c9"
            },
        },
        "sancti-ioseph-in-solemnitate": {
            "protected_digest": "57765a8dc96aa041f6a9ba26e342d4f7fa67685bc6d836f7d4ce07be05131d16",
            "words": {"w062": {"gloss": "with a father’s"}, "w063": {"gloss": "stead"}},
            "had_alignments": {"s05": True},
            "absorbed": {"s05": []},
            "source_contexts": {
                "s05": "2689e1c0225b4d5acf2ebf6bbcf84741f8682c95c57ce24df6a798c1ab8044c9"
            },
        },
        "sanctissimae-trinitatis": {
            "protected_digest": "6c56c4c7de0d7cc5626c269070676326cde462c647a590b94e35f48b1c21e2e8",
            "words": {"w051": {"gloss": "by the revelation of"}, "w052": {"gloss": "Your"}},
            "had_alignments": {"s05": True},
            "absorbed": {"s05": []},
            "source_contexts": {
                "s05": "88d4fe9af744ad39978d27b4f8f6e137fd42d0cea4205ff8b89f551165587bd3"
            },
        },
    },
}
SITES = FIXTURES["sites"]
BASELINES = FIXTURES["baselines"]
SLUGS = sorted(BASELINES)


def load(slug):
    filename = "praefatio-" + slug + ".json"
    doc = json.loads((CORPUS / "texts/ordinarium" / filename).read_text())
    layer = json.loads((CORPUS / "languages/en/texts/ordinarium" / filename).read_text())
    return doc, layer


def selected(slug):
    return [site for site in SITES if site["slug"] == slug]


def group_for(layer, site):
    touching = [
        group
        for group in layer["segments"][site["segment"]].get("alignments", [])
        if set(group["words"]) & set(site["words"])
    ]
    assert len(touching) == 1
    return touching[0]


def supported(site):
    chosen = site["gloss"]
    alternatives = {
        "whom You appointed to preside over it as shepherds, deputies in Your work": {
            "whom You appointed to preside over it as shepherds, vicars in Your work"
        },
        "that He might grant us a share in His divinity": {
            "that He might grant us to be partakers of His divinity"
        },
        "with all creatures subjected to His dominion": {
            "with all creatures having been subjected to His dominion"
        },
        "He might deliver to Your infinite Majesty an eternal and universal kingdom": {
            "He might hand over to Your infinite Majesty an eternal and universal kingdom"
        },
        "in a father’s place": {"in a father’s stead", "in the role of a father"},
        "for Christ, our Passover, has been sacrificed": {
            "when Christ, our Passover, has been sacrificed",
            "for Christ, our Pasch, has been sacrificed",
        },
    }
    return {chosen} | alternatives.get(chosen, set())


def assert_site(doc, layer, site):
    words = next(s["words"] for s in doc["segments"] if s["id"] == site["segment"])
    positions = {w["id"]: i for i, w in enumerate(words)}
    positions_in_group = [positions[w] for w in site["words"]]
    assert positions_in_group == list(
        range(positions_in_group[0], positions_in_group[0] + len(positions_in_group))
    )
    group = group_for(layer, site)
    assert set(group) == {"words", "anchor", "gloss"}
    assert group["words"] == site["words"]
    assert group["anchor"] == site["anchor"]
    assert group["gloss"] in supported(site)
    assert all(w in layer["words"] and "gloss" not in layer["words"][w] for w in site["words"])
    assert [(w, effective_gloss(layer, w)) for w in site["words"] if effective_gloss(layer, w)] == [
        (group["anchor"], group["gloss"])
    ]


def restore_reviewed_fields(layer, slug):
    """Reverse only the named groups/glosses/prose; never mask new metadata."""
    restored = deepcopy(layer)
    baseline = BASELINES[slug]
    for site in selected(slug):
        group = group_for(restored, site)
        assert set(group) == {"words", "anchor", "gloss"}
        assert group["words"] == site["words"]
        assert group["anchor"] == site["anchor"]
        assert group["gloss"] in supported(site)
        restored["segments"][site["segment"]]["alignments"].remove(group)
        for wid in site["words"]:
            assert wid in restored["words"]
            assert "gloss" not in restored["words"][wid]
            if "gloss" in baseline["words"][wid]:
                restored["words"][wid]["gloss"] = baseline["words"][wid]["gloss"]
    for sid, absorbed in baseline["absorbed"].items():
        segment = restored["segments"][sid]
        groups = segment["alignments"]
        for group in absorbed:
            assert not any(set(group["words"]) & set(g["words"]) for g in groups)
            groups.append(deepcopy(group))
        groups.sort(key=lambda g: g["words"][0])
        if not baseline["had_alignments"][sid]:
            assert not groups
            del segment["alignments"]
    if "prose" in baseline:
        prose = baseline["prose"]
        assert restored["segments"][prose["segment"]]["translation"] == prose["after"]
        restored["segments"][prose["segment"]]["translation"] = prose["before"]
    return restored


def assert_protected(doc, layer, slug):
    assert list(layer["words"]) == [w["id"] for s in doc["segments"] for w in s.get("words", [])]
    restored = restore_reviewed_fields(layer, slug)
    assert canonical_hash(restored) == BASELINES[slug]["protected_digest"]


def assert_provenance(record, doc, layer, slug):
    prose = BASELINES[slug]["prose"]
    expected = deepcopy(prose["provenance_before"])
    expected["target_sha256"] = prose["target_after"]
    assert record == expected
    segment = next(s for s in doc["segments"] if s["id"] == prose["segment"])
    assert record["source_sha256"] == canonical_hash(source_payload(segment))
    assert record["target_sha256"] == canonical_hash(
        layer["segments"][prose["segment"]]["translation"]
    )


def test_population_and_distinct_construction_boundaries():
    assert len(SLUGS) == 10 and len(SITES) == 12
    assert sum(len(s["words"]) for s in SITES) == 64
    assert len({(s["slug"], w) for s in SITES for w in s["words"]}) == 64
    assert (
        sum(len(groups) for row in BASELINES.values() for groups in row["absorbed"].values()) == 2
    )
    assert sum("prose" in row for row in BASELINES.values()) == 2


@pytest.mark.parametrize("site", SITES)
def test_reviewed_construction_is_realized_once(site):
    doc, layer = load(site["slug"])
    assert_site(doc, layer, site)


@pytest.mark.parametrize("slug", SLUGS)
def test_complete_layer_and_canonical_layout(slug):
    doc, layer = load(slug)
    path = CORPUS / "languages/en/texts/ordinarium" / ("praefatio-" + slug + ".json")
    assert check_layer(doc, layer, path) == []
    assert check(doc, layer) == []
    assert path.read_text() == formatted(layer)


@pytest.mark.parametrize("slug", SLUGS)
def test_source_context_is_unchanged(slug):
    doc, _ = load(slug)
    for sid, expected in BASELINES[slug]["source_contexts"].items():
        segment = next(s for s in doc["segments"] if s["id"] == sid)
        assert canonical_hash(source_payload(segment)) == expected


@pytest.mark.parametrize("slug", SLUGS)
def test_unselected_fields_restore_to_whole_layer_baseline(slug):
    doc, layer = load(slug)
    assert_protected(doc, layer, slug)


@pytest.mark.parametrize("slug", ["paschalis-in-die", "paschalis-in-nocte"])
def test_easter_prose_has_only_the_reviewed_clause_substitution(slug):
    _, layer = load(slug)
    prose = BASELINES[slug]["prose"]
    old, new = (
        "when Christ our Pasch was sacrificed",
        "for Christ, our Passover, has been sacrificed",
    )
    assert prose["before"].count(old) == 1
    assert prose["after"] == prose["before"].replace(old, new)
    assert layer["segments"]["s01"]["translation"] == prose["after"]


@pytest.mark.parametrize("slug", ["paschalis-in-die", "paschalis-in-nocte"])
def test_easter_provenance_updates_target_only(slug):
    doc, layer = load(slug)
    sites = json.loads((CORPUS / "languages/en/translation-provenance.json").read_text())["sites"]
    record = next(r for r in sites if r["text"] == doc["id"] and r["segment"] == "s01")
    assert_provenance(record, doc, layer, slug)


@pytest.mark.parametrize("site", SITES)
@pytest.mark.parametrize(
    "mutation", ["direct", "overlap", "missing-word", "noncontiguous", "anchor"]
)
def test_malformed_realization_is_rejected(site, mutation):
    doc, layer = load(site["slug"])
    group = group_for(layer, site)
    if mutation == "direct":
        layer["words"][site["words"][0]]["gloss"] = "changed"
    elif mutation == "overlap":
        layer["segments"][site["segment"]]["alignments"].append(deepcopy(group))
    elif mutation == "missing-word":
        del layer["words"][site["words"][0]]
    elif mutation == "noncontiguous":
        group["words"].remove(site["words"][1])
    else:
        group["anchor"] = "w001"
    assert check(doc, layer) or check_layer(
        doc, layer, CORPUS / "languages/en/texts/ordinarium/fixture.json"
    )
    with pytest.raises((AssertionError, KeyError)):
        assert_site(doc, layer, site)


SEMANTIC_MUTATIONS = [
    ("apostolorum", "w028", "that those same leaders may be governed"),
    (
        "apostolorum",
        "w032",
        "whom He appointed to preside over it as shepherds, deputies in Your work",
    ),
    (
        "apostolorum",
        "w032",
        "whom You appointed to preside over it as shepherds, deputies in our work",
    ),
    ("ascensionis", "w042", "that we might share in His divinity"),
    ("ascensionis", "w042", "that He might grant us a portion of His divinity"),
    ("epiphaniae", "w031", "He renewed the new light by our immortality"),
    ("nativitatis", "w027", "a new light of our glory has shone upon the eyes of Your mind"),
    ("paschalis-in-die", "w021", "for Christ, our Passover, has sacrificed"),
    ("paschalis-in-nocte", "w021", "for Christ, our Passover, has sacrificed"),
    ("d-n-iesu-christi-regis", "w053", "all creatures having subjected His dominion"),
    (
        "d-n-iesu-christi-regis",
        "w058",
        "You might deliver to His infinite Majesty an eternal and universal kingdom",
    ),
    ("sanctissimae-trinitatis", "w051", "by our revelation"),
    ("sancti-ioseph-in-festivitate", "w062", "by the Father"),
    ("sancti-ioseph-in-solemnitate", "w062", "by the Father"),
]


@pytest.mark.parametrize("slug,first,gloss", SEMANTIC_MUTATIONS)
def test_semantic_counterexamples_are_not_accepted_by_shape_alone(slug, first, gloss):
    site = next(s for s in SITES if s["slug"] == slug and s["words"][0] == first)
    doc, layer = load(slug)
    group_for(layer, site)["gloss"] = gloss
    assert check(doc, layer) == []
    with pytest.raises(AssertionError):
        assert_site(doc, layer, site)


ALTERNATIVES = [
    (site, wording) for site in SITES for wording in sorted(supported(site) - {site["gloss"]})
]


@pytest.mark.parametrize("site,wording", ALTERNATIVES)
def test_supported_alternatives_do_not_become_false_correctness_rules(site, wording):
    doc, layer = load(site["slug"])
    group_for(layer, site)["gloss"] = wording
    assert_site(doc, layer, site)
    assert_protected(doc, layer, site["slug"])
    assert check(doc, layer) == []


@pytest.mark.parametrize(
    "mutation",
    [
        "prose",
        "note",
        "other-gloss",
        "about",
        "status",
        "word-order",
        "missing-object",
        "existing-passive",
        "true-zero",
        "petition",
        "extra-overlap",
    ],
)
def test_protected_payload_mutations_cannot_be_hidden(mutation):
    slug = "sancti-ioseph-in-festivitate"
    doc, layer = load(slug)
    if mutation == "prose":
        layer["segments"]["s02"]["translation"] += " Changed."
    elif mutation == "note":
        layer["words"]["w062"]["explanation"] = "Added."
    elif mutation == "other-gloss":
        layer["words"]["w001"]["gloss"] = "Changed."
    elif mutation == "about":
        layer["about"] += " Changed."
    elif mutation == "status":
        layer["status"] = "accepted"
    elif mutation == "word-order":
        layer["words"] = dict(reversed(list(layer["words"].items())))
    elif mutation == "missing-object":
        del layer["words"]["w062"]
    elif mutation == "existing-passive":
        next(g for g in layer["segments"]["s05"]["alignments"] if g["words"] == ["w043", "w044"])[
            "gloss"
        ] = "has given"
    elif mutation == "true-zero":
        layer["segments"]["s05"]["alignments"] = [
            g for g in layer["segments"]["s05"]["alignments"] if g["words"] != ["w035"]
        ]
    elif mutation == "petition":
        layer["segments"]["s08"]["alignments"][0]["gloss"] = "Changed."
    else:
        layer["segments"]["s05"]["alignments"].append(
            {"words": ["w061", "w062"], "anchor": "w061", "gloss": "Changed."}
        )
    with pytest.raises((AssertionError, KeyError)):
        assert_protected(doc, layer, slug)


@pytest.mark.parametrize("slug", ["paschalis-in-die", "paschalis-in-nocte"])
def test_absorbed_passive_must_not_reappear_as_an_overlap(slug):
    doc, layer = load(slug)
    layer["segments"]["s01"]["alignments"].append(
        {"words": ["w024", "w025"], "anchor": "w024", "gloss": "has been sacrificed"}
    )
    assert check(doc, layer)
    with pytest.raises(AssertionError):
        assert_protected(doc, layer, slug)


@pytest.mark.parametrize(
    "field,value",
    [
        ("origin", "own"),
        ("review", "accepted"),
        ("familiar_core", True),
        ("source_sha256", "0" * 64),
        ("target_sha256", "0" * 64),
    ],
)
def test_provenance_promotion_or_stale_bindings_are_rejected(field, value):
    slug = "paschalis-in-die"
    doc, layer = load(slug)
    record = deepcopy(BASELINES[slug]["prose"]["provenance_before"])
    record["target_sha256"] = BASELINES[slug]["prose"]["target_after"]
    record[field] = value
    with pytest.raises(AssertionError):
        assert_provenance(record, doc, layer, slug)


def test_untouched_passive_and_true_zero_controls():
    _, ascension = load("ascensionis")
    assert next(g for g in ascension["segments"]["s02"]["alignments"] if "w038" in g["words"]) == {
        "words": ["w038", "w039"],
        "anchor": "w039",
        "gloss": "was raised up",
    }
    for slug in ("sancti-ioseph-in-festivitate", "sancti-ioseph-in-solemnitate"):
        _, layer = load(slug)
        groups = layer["segments"]["s05"]["alignments"]
        assert {"words": ["w035"], "reason": "idiom"} in groups
        assert {"words": ["w043", "w044"], "anchor": "w044", "gloss": "was given"} in groups
        assert {"words": ["w053", "w054"], "anchor": "w054", "gloss": "was appointed"} in groups
        assert [len(g["words"]) for g in layer["segments"]["s08"]["alignments"]] == [9, 3]

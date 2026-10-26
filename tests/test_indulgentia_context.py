"""Bounded authored lexical/context controls; not a general grammar validator.

The fifteen contextual uses were read against their full Latin clauses. New uses
must receive contextual review before this exact oracle is expanded. This
module does not label a complete prayer/source review accepted.
"""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from checks.lexicon import lint_senses
from checks.translation_provenance import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
NOTES = {
    "pl": (
        "Słowo może oznaczać przebaczenie lub łaskawość. Ma także szczególne "
        "znaczenie teologiczne: odpust, czyli darowanie przed Bogiem kary "
        "doczesnej za grzechy zgładzone już co do winy."
    ),
    "en": (
        "The word can mean pardon or mercy. In its specific theological "
        "sense, it also denotes an indulgence: remission before God of "
        "temporal punishment for sins whose guilt has already been forgiven."
    ),
}
OLD_NOTES = {
    "pl": (
        "W terminologii kościelnej oznacza odpust: darowanie przed Bogiem "
        "kary doczesnej za grzechy zgładzone już co do winy."
    ),
    "en": (
        "In Church terminology, it means an indulgence: remission before God "
        "of temporal punishment for sins whose guilt has already been "
        "forgiven."
    ),
}
ABOUTS = {
    "pl": (
        "Kolekta IV Niedzieli Adwentu. Prosi, aby dzięki pomocy Bożej łaski "
        "miłosierne przebaczenie przyspieszyło to, co nasze grzechy "
        "opóźniają."
    ),
    "en": (
        "The collect of the Fourth Sunday of Advent. It asks that, through "
        "the help of God’s grace, merciful forgiveness may hasten what our "
        "sins delay."
    ),
}
OLD_ABOUTS = {
    "pl": (
        "Kolekta IV Niedzieli Adwentu. Prosi o pośpiech: łaska ma nadejść "
        "szybciej, niż zdążą przeszkodzić grzechy."
    ),
    "en": (
        "The collect of the Fourth Sunday of Advent. It asks for haste, that "
        "grace outrun the sins standing in its way."
    ),
}
XII = "proprium.dominica-xii-post-pentecosten-secreta"
ADVENT = "proprium.dominica-iv-adventus-collecta"
CONTEXTS = (
    ("ordinarium.misereatur", "s05", "w015", "przebaczenia", "pardon"),
    ("proprium.cathedra-sancti-petri-postcommunio", "s01", "w020", "przebaczenia", "forgiveness"),
    (
        "proprium.commemoratio-omnium-fidelium-defunctorum-missa-i-collecta",
        "s01",
        "w016",
        "przebaczenie",
        "pardon",
    ),
    (
        "proprium.commemoratio-omnium-fidelium-defunctorum-missa-ii-collecta",
        "s01",
        "w002",
        "przebaczeń",
        "of mercies",
    ),
    (
        "proprium.commemoratio-omnium-fidelium-defunctorum-missa-ii-postcommunio",
        "s01",
        "w012",
        "przebaczenie",
        "forgiveness",
    ),
    (ADVENT, "s01", "w022", "przebaczenie", "may the forgiveness of Your mercy hasten"),
    (XII, "s01", "w012", "przebaczenia", "pardon"),
    ("proprium.dominica-xiii-post-pentecosten-secreta", "s01", "w012", "przebaczenia", "pardon"),
    ("proprium.dominica-xx-post-pentecosten-collecta", "s01", "w006", "przebaczenia", "pardon"),
    (
        "proprium.sanctorum-innocentium-martyrum-secreta",
        "s01",
        "w017",
        "przebaczenie",
        "Your pardon for us",
    ),
    (
        "proprium.sanctae-monicae-collecta",
        "s01",
        "w031",
        "w Twojej łasce znaleźć przebaczenie",
        "pardon",
    ),
    (
        "proprium.sancti-athanasii-postcommunio",
        "s01",
        "w018",
        "przez modlitwy otrzymali przebaczenie",
        "pardon",
    ),
    (
        "proprium.sancti-gregorii-nazianzeni-secreta",
        "s01",
        "w021",
        "przebaczenie",
        "may always obtain Your pardon for us",
    ),
    (
        "proprium.sancti-bedae-venerabilis-secreta",
        "s01",
        "w021",
        "i Twoje przebaczenie dla nas",
        "always obtain Your pardon for us",
    ),
    (
        "proprium.sanctorum-nerei-achillei-domitillae-et-pancratii-secreta",
        "s01",
        "w023",
        "zawsze wyprasza nam Twoje przebaczenie",
        "always implore Your pardon for us",
    ),
)


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def core(text):
    return read(f"texts/{text.replace('.', '/', 1)}.json")


def layer(text, language):
    return read(f"languages/{language}/texts/{text.replace('.', '/', 1)}.json")


def scope_note(card, language):
    assert card["note"] == NOTES[language], "general and technical scopes must remain distinct"


def caption(target, segment, word):
    groups = [
        group
        for group in target["segments"][segment].get("alignments", [])
        if word in group["words"]
    ]
    direct = target.get("words", {}).get(word, {}).get("gloss")
    assert (direct is not None) != bool(groups)
    assert len(groups) <= 1
    return direct if direct is not None else groups[0]["gloss"]


def xii_reading(target):
    prose = target["segments"]["s01"]["translation"]
    assert "upon Your sacred altars;" in prose, "plural altars must remain plural"
    assert "so that by bestowing forgiveness on us, they may give honor to Your name." in prose, (
        "honor is the requested result; bestowing forgiveness is the means"
    )
    assert "while they give honor" not in prose


def advent_about(target, language):
    assert target["about"] == ABOUTS[language], "present hindrance and requested haste"


def test_shared_cards_keep_general_and_specific_senses_without_changing_definition():
    neutral = read("lexicon/lemmata.json")["entries"]["indulgentia"]
    assert neutral["localization"]["note"] is True
    assert any(cite["locator"] == "n. 1471" for cite in neutral["localization"]["note_citations"])
    for language in ("pl", "en"):
        card = read(f"languages/{language}/lexicon.json")["entries"]["indulgentia"]
        scope_note(card, language)
        assert lint_senses(language, {"indulgentia": card}, {"indulgentia": neutral}) == []
    # The technical definition is a valid positive control, not forbidden wording.
    assert "kary doczesnej" in NOTES["pl"]
    assert "temporal punishment" in NOTES["en"]


@pytest.mark.parametrize("language", ("pl", "en"))
def test_categorical_old_scope_is_rejected_and_exact_card_recovers(language):
    healthy = read(f"languages/{language}/lexicon.json")["entries"]["indulgentia"]
    saved = deepcopy(healthy)
    scope_note(healthy, language)
    bad = deepcopy(healthy)
    bad["note"] = OLD_NOTES[language]
    with pytest.raises(AssertionError, match="general and technical scopes"):
        scope_note(bad, language)
    assert healthy == saved
    scope_note(healthy, language)


def test_complete_current_fanout_has_the_reviewed_general_contextual_realizations():
    observed = set()
    for path in sorted((ROOT / "texts").rglob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for segment in doc["segments"]:
            for word in segment.get("words", []):
                if word.get("lemma") == "indulgentia":
                    observed.add((doc["id"], segment["id"], word["id"]))
    assert observed == {(text, segment, word) for text, segment, word, _, _ in CONTEXTS}
    for text, segment, word, polish, english in CONTEXTS:
        doc = core(text)
        source = next(s for s in doc["segments"] if s["id"] == segment)
        token = next(w for w in source["words"] if w["id"] == word)
        assert token["lemma"] == "indulgentia" and token["morph"]["pos"] == "noun"
        assert caption(layer(text, "pl"), segment, word) == polish
        assert caption(layer(text, "en"), segment, word) == english


def test_twelfth_secret_preserves_the_printed_number_and_result_relation():
    doc, target = core(XII), layer(XII, "en")
    words = {w["id"]: w for s in doc["segments"] for w in s.get("words", [])}
    assert words["w007"]["form"] == "sacris"
    assert words["w008"]["form"] == "altáribus"
    assert words["w008"]["morph"]["number"] == "pl"
    assert words["w010"]["form"] == "ut" and words["w016"]["form"] == "dent"
    assert words["w013"]["form"] == "largiéndo"
    xii_reading(target)
    assert caption(target, "s01", "w008") == "altars"
    sites = read("languages/en/translation-provenance.json")["sites"]
    site = next(s for s in sites if s["site"] == f"{XII}.s01.en")
    assert site["target_sha256"] == canonical_hash(target["segments"]["s01"]["translation"])
    assert (site["origin"], site["review"], site["familiar_core"]) == (
        "working-unsettled",
        "working",
        False,
    )


@pytest.mark.parametrize("defect", ("number", "result"))
def test_twelfth_secret_mutations_fail_without_changing_source_or_healthy_target(defect):
    healthy = layer(XII, "en")
    saved = deepcopy(healthy)
    xii_reading(healthy)
    bad = deepcopy(healthy)
    prose = bad["segments"]["s01"]["translation"]
    if defect == "number":
        prose = prose.replace("Your sacred altars;", "Your sacred altar;")
        expected = "plural altars"
    else:
        prose = prose.replace(
            "by bestowing forgiveness on us, they may give honor",
            "they may bring us plentiful forgiveness while they give honor",
        )
        expected = "honor is the requested result"
    bad["segments"]["s01"]["translation"] = prose
    with pytest.raises(AssertionError, match=expected):
        xii_reading(bad)
    assert healthy == saved
    xii_reading(healthy)


@pytest.mark.parametrize("language", ("pl", "en"))
def test_fourth_advent_summary_keeps_present_hindrance_and_divine_pardon(language):
    doc = core(ADVENT)
    words = {w["id"]: w for s in doc["segments"] for w in s.get("words", [])}
    assert words["w020"]["form"] == "peccáta"
    assert words["w021"]["form"] == "præpédiunt"
    assert words["w021"]["morph"]["tense"] == "pres"
    assert words["w022"]["form"] == "indulgéntia"
    assert words["w025"]["form"] == "accéleret"
    advent_about(layer(ADVENT, language), language)


@pytest.mark.parametrize("language", ("pl", "en"))
def test_fourth_advent_old_race_or_not_yet_hindrance_fails_and_original_recovers(language):
    healthy = layer(ADVENT, language)
    saved = deepcopy(healthy)
    advent_about(healthy, language)
    bad = deepcopy(healthy)
    bad["about"] = OLD_ABOUTS[language]
    with pytest.raises(AssertionError, match="present hindrance"):
        advent_about(bad, language)
    assert healthy == saved
    advent_about(healthy, language)

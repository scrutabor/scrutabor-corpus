"""Source-bound feast selections, including transferred calendar occurrences."""

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.emit import formulary_catalog
from checks.formularies import component_applies
from kalendarium.roman import year

CORPUS = Path(__file__).resolve().parents[1]
ANNUNCIATION = "annuntiatio-beatae-mariae-virginis"
ANNE = "sanctae-annae-matris-beatae-mariae-virginis"
SORROWS = "septem-dolorum-beatae-mariae-virginis"
CHANTS = {"graduale", "alleluia", "tractus", "sequentia"}


def selected(components, occurrence):
    return [
        part
        for part in components
        if component_applies(
            part.get("condition"),
            weekday=occurrence.when.weekday(),
            season=occurrence.season,
        )
    ]


def expected_chants(occurrence):
    if occurrence.formulary == ANNUNCIATION:
        # Benziger1962 pp.495–496: G+T outside Eastertide; the entire P pair
        # replaces both, including when the feast is transferred after Easter.
        return ["alleluia"] if occurrence.season == "paschale" else ["graduale", "tractus"]
    # pp.614–615 and670–671: the extra tracts are expressly votive, not feast.
    return ["graduale", "alleluia"] + (["sequentia"] if occurrence.formulary == SORROWS else [])


def chant_roles(parts):
    return [part["role"] for part in parts if part["role"] in CHANTS]


def test_all_shipped_occurrences_select_only_the_printed_feast_chants():
    catalogue = {form["id"]: form for form in formulary_catalog(CORPUS)["formularies"]}
    seen = Counter()
    seasons = Counter()
    for ending in range(2026, 2102):
        for occurrence in year(ending):
            if occurrence.formulary not in (ANNUNCIATION, ANNE, SORROWS):
                continue
            components = catalogue[occurrence.formulary]["components"]
            assert chant_roles(selected(components, occurrence)) == expected_chants(occurrence), (
                occurrence.when,
                occurrence.formulary,
            )
            seen[occurrence.formulary] += 1
            if occurrence.formulary == ANNUNCIATION:
                seasons[occurrence.season] += 1
    assert seen == {ANNUNCIATION: 76, ANNE: 65, SORROWS: 66}
    assert seasons == {"quadragesima": 41, "passionis": 16, "paschale": 19}


@pytest.mark.parametrize("formulary", [ANNE, SORROWS])
def test_reintroducing_an_unconditional_votive_tract_breaks_the_feast(formulary):
    doc = json.loads((CORPUS / "formularies/sanctorale" / f"{formulary}.json").read_text())
    occurrence = next(d for d in year(2027) if d.formulary == formulary)
    assert chant_roles(selected(doc["components"], occurrence)) == expected_chants(occurrence)
    mutated = deepcopy(doc["components"])
    next(c for c in mutated if c["role"] == "tractus").pop("condition")
    assert chant_roles(selected(mutated, occurrence)) != expected_chants(occurrence)


def test_source_only_votive_alternatives_are_retained_for_labelled_study():
    for formulary in (ANNE, SORROWS):
        doc = json.loads((CORPUS / "formularies/sanctorale" / f"{formulary}.json").read_text())
        tract = next(c for c in doc["components"] if c["role"] == "tractus")
        assert tract["condition"] == {"use": "votive-after-septuagesima"}
        assert component_applies(tract["condition"], study=True)
        assert not component_applies(tract["condition"], weekday=2, season="quadragesima")


@pytest.mark.parametrize("season", [None, "", "spring", "per annum"])
def test_missing_or_unknown_season_never_becomes_the_non_paschal_branch(season):
    for condition in ({"season": "paschale"}, {"season": "not-paschale"}):
        assert not component_applies(condition, season=season)
        assert component_applies(condition, study=True)


def test_condition_contract_is_closed_and_does_not_combine_predicates():
    for condition in (
        {},
        {"season": "quadragesima"},
        {"weekday": "sunday", "season": "paschale"},
        {"use": "votive"},
    ):
        assert not component_applies(condition, weekday=6, season="paschale")
        assert not component_applies(condition, study=True)


def test_complementary_seasonal_recensions_select_once_for_every_context():
    conditions = [{"season": "paschale"}, {"season": "not-paschale"}]
    for season in (
        "adventus",
        "nativitas",
        "epiphania",
        "septuagesima",
        "quadragesima",
        "passionis",
        "paschale",
        "per-annum",
    ):
        for weekday in range(7):
            assert (
                sum(component_applies(c, weekday=weekday, season=season) for c in conditions) == 1
            )


def test_annunciation_selects_complete_ioc_recensions_for_all_published_dates():
    form = next(f for f in formulary_catalog(CORPUS)["formularies"] if f["id"] == ANNUNCIATION)
    expected = {
        False: {
            "introitus": ("extra-tempus-paschale-introitus", 68),
            "offertorium": ("extra-tempus-paschale-offertorium", 15),
            "communio": ("communio", 11),
        },
        True: {
            "introitus": ("introitus", 72),
            "offertorium": ("offertorium", 16),
            "communio": ("tempore-paschali-communio", 12),
        },
    }
    seen = Counter()
    for ending in range(2026, 2102):
        for occurrence in year(ending):
            if occurrence.formulary != ANNUNCIATION:
                continue
            paschal = occurrence.season == "paschale"
            chosen = selected(form["components"], occurrence)
            for role, (suffix, count) in expected[paschal].items():
                components = [c for c in chosen if c["role"] == role]
                assert len(components) == 1, (occurrence.when, role)
                tid = "proprium." + ANNUNCIATION + "-" + suffix
                assert components[0]["text"] == tid.replace(".", "/", 1)
                doc = json.loads(
                    (CORPUS / "texts" / (tid.replace(".", "/", 1) + ".json")).read_text()
                )
                words = [w for segment in doc["segments"] for w in segment.get("words", [])]
                assert len(words) == count
                assert sum(w["lemma"] == "alleluia" for w in words) == (
                    (4 if role == "introitus" else 1) if paschal else 0
                )
            seen[paschal] += 1
    assert seen == {False: 57, True: 19}


def test_unknown_annunciation_season_does_not_select_unconditional_ioc():
    doc = json.loads((CORPUS / "formularies/sanctorale" / f"{ANNUNCIATION}.json").read_text())
    for component in doc["components"]:
        if component["role"] in {"introitus", "offertorium", "communio"}:
            assert not component_applies(component.get("condition"), season=None)

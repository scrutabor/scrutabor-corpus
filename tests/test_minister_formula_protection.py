"""Narrow fixed-formula protection at the two ministerial s03 addresses."""

import pytest

from checks.translation_provenance import protected

TEXTS = {
    "ordinary": "ordinarium.iube-domne-benedicere",
    "palm": "ordinarium.iube-domne-benedicere-in-passione",
}
SITES = [
    (text, language, segment, segment == "s03")
    for text in TEXTS.values()
    for language in ("pl", "en")
    for segment in ("s01", "s02", "s03", "s04")
]
SITE_IDS = [
    f"{label}-{language}-{segment}"
    for label in TEXTS
    for language in ("pl", "en")
    for segment in ("s01", "s02", "s03", "s04")
]
UNQUALIFIED = [(text, language) for text in TEXTS.values() for language in ("pl", "en")]
UNQUALIFIED_IDS = [f"{label}-{language}" for label in TEXTS for language in ("pl", "en")]
EXISTING = [
    ("orationes.signum-crucis", "pl", None, True),
    ("orationes.signum-crucis", "en", None, True),
    ("orationes.signum-crucis", "pl", "s01", True),
    ("orationes.signum-crucis", "en", "s01", True),
    ("orationes.gloria-patri", "pl", "s01", True),
    ("orationes.gloria-patri", "en", "s01", True),
    ("litaniae.lauretanae", "pl", None, True),
    ("litaniae.lauretanae", "en", None, False),
    ("ordinarium.credo", "pl", None, True),
    ("ordinarium.credo", "en", None, False),
    ("ordinarium.ite-missa-est-paschale", "pl", "s02", True),
    ("ordinarium.ite-missa-est-paschale", "pl", "s01", False),
    ("ordinarium.ite-missa-est-paschale", "pl", None, False),
    ("ordinarium.ite-missa-est-paschale", "en", "s02", False),
    ("proprium.vigilia-paschalis-laudes-psalmus", "pl", "s07", True),
    ("proprium.vigilia-paschalis-laudes-psalmus", "pl", "s06", False),
    ("proprium.vigilia-paschalis-laudes-psalmus", "en", "s07", False),
    ("proprium.vigilia-paschalis-laudes-canticum", "pl", "s15", True),
    ("proprium.vigilia-paschalis-laudes-canticum", "pl", "s14", False),
    ("proprium.vigilia-paschalis-laudes-canticum", "en", "s15", False),
    ("orationes.test", "pl", "s01", False),
    ("orationes.test", "en", "s01", False),
    ("ordinarium.iube-domine-benedicere", "pl", "s03", False),
    ("ordinarium.iube-domine-benedicere", "en", "s03", False),
    ("ordinarium.munda-cor-meum", "pl", "s01", False),
    ("ordinarium.munda-cor-meum", "en", "s01", False),
]
EXISTING_IDS = [
    f"{text}-{language}-{segment or 'whole'}" for text, language, segment, _ in EXISTING
]


@pytest.mark.parametrize("text,language,segment,expected", SITES, ids=SITE_IDS)
def test_only_fixed_s03_is_protected(text, language, segment, expected):
    assert protected(text, language, segment) is expected


@pytest.mark.parametrize("text,language", UNQUALIFIED, ids=UNQUALIFIED_IDS)
def test_new_ministerial_text_is_not_whole_text_protected(text, language):
    assert protected(text, language) is False
    assert protected(text, language, None) is False
    assert protected(text, language, "s99") is False


@pytest.mark.parametrize("language", ["la", "xx"])
def test_unknown_language_remains_unprotected(language):
    for text in (*TEXTS.values(), "orationes.signum-crucis"):
        assert protected(text, language, "s03") is False
        assert protected(text, language) is False


@pytest.mark.parametrize("text,language,segment,expected", EXISTING, ids=EXISTING_IDS)
def test_existing_protection_outcomes_remain_unchanged(text, language, segment, expected):
    assert protected(text, language, segment) is expected

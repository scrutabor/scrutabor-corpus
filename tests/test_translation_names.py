"""Positive and negative controls for the bounded translation-name guard."""

from copy import deepcopy

import pytest

from checks.translation_names import check


def core(lemma="munus"):
    return {"id": "test.secret", "segments": [{"id": "s01", "words": [{"lemma": lemma}]}]}


def layer(language, text):
    return {"language": language, "segments": {"s01": {"translation": text}}}


@pytest.mark.parametrize("name", ["Abel", "Abla", "Abela", "Abelowi", "Ablem", "Abelu"])
def test_imported_polish_name_fails(name):
    assert check(core(), layer("pl", f"Dary {name}."))


def test_imported_english_name_fails():
    assert check(core(), layer("en", "The gifts of Abel."))


@pytest.mark.parametrize("language,text", [("pl", "dary Abla"), ("en", "Abel’s gifts")])
def test_latin_name_is_a_positive_control(language, text):
    assert not check(core("Abel"), layer(language, text))


def test_explicit_name_can_recall_an_earlier_segment():
    doc = core("Abel")
    doc["segments"].append({"id": "s02", "words": [{"lemma": "qui"}]})
    target = {"language": "pl", "segments": {"s02": {"translation": "Abel"}}}
    assert not check(doc, target)


def test_commentary_and_similar_words_are_not_prayer_names():
    target = layer("pl", "Przyjmij dary.")
    target.update(about="Porównaj z darami Abla.", words={"w001": {"note": "Abel"}})
    target["segments"]["s02"] = {"narrative": "Abel"}
    assert not check(core(), target)
    assert not check(core(), layer("en", "Isabel carries a label."))


def test_translation_swap_fails_but_source_matched_prayer_passes():
    target = layer("pl", "Przyjmij, Panie, dary z Twojej hojności.")
    assert not check(core(), target)
    swapped = deepcopy(target)
    swapped["segments"]["s01"]["translation"] = "Uświęć je jak dary Abla."
    assert check(core(), swapped)
    assert not check(core("Abel"), swapped)


def test_unreviewed_language_is_not_guessed():
    assert not check(core(), layer("fr", "Abel"))


def test_translation_name_guard_is_wired_into_normal_checks(monkeypatch, capsys):
    import run_checks

    text_id = "proprium.dominica-viii-post-pentecosten-secreta"
    calls = []

    def reject(core, layer):
        language = layer.get("language") or layer.get("lang")
        calls.append((core["id"], language))
        return [f"translation-name-wiring-sentinel:{language}"]

    monkeypatch.setattr(run_checks, "check_translation_names", reject)

    assert run_checks.main(text_id) == 1
    output = capsys.readouterr().out
    assert calls == [(text_id, "en"), (text_id, "pl")]
    for language in ("en", "pl"):
        assert f"ERROR: translation-name-wiring-sentinel:{language}" in output

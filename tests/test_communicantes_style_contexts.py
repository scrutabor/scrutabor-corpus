"""Bounded known Communicantes referents and inherited-wording controls."""

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def subject(slug, language):
    rel = f"texts/ordinarium/{slug}.json"
    return json.loads((ROOT / rel).read_text()), json.loads(
        (ROOT / "languages" / language / rel).read_text()
    )


def realization(layer, wid):
    matches = [
        a
        for segment in layer["segments"].values()
        for a in segment.get("alignments", [])
        if wid in a["words"]
    ]
    direct = layer["words"][wid].get("gloss")
    assert int(direct is not None) + len(matches) == 1
    return direct if direct is not None else matches[0]["gloss"]


def gloss_address(layer, wid):
    """Mutate the actual realization, whether direct or explicitly grouped."""
    # This is test setup, not a relaxation of the known referent checks.
    if "gloss" in layer["words"][wid]:
        return ["words", wid, "gloss"]
    matches = [
        ["segments", sid, "alignments", index, "gloss"]
        for sid, segment in layer["segments"].items()
        for index, alignment in enumerate(segment.get("alignments", []))
        if wid in alignment["words"]
    ]
    assert len(matches) == 1
    return matches[0]


def context_errors(slug, language, core, layer):
    """Explicitly known sites; not automatic inference of arbitrary referents."""
    errors = []
    ordinary = slug == "communicantes"
    words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    saints = "w061" if ordinary else "w076"
    mary = "w022" if ordinary else "w037"
    christ = "w075" if ordinary else "w090"
    saints_segment = "s05" if ordinary else "s12"
    conclusion = "s07" if ordinary else "s14"
    assert words[saints]["lemma"] == "sanctus" and words[saints]["substantive"]
    assert words[mary]["morph"] == {"pos": "pron", "case": "gen", "number": "sg", "gender": "f"}
    assert words[christ]["morph"] == {"pos": "pron", "case": "acc", "number": "sg", "gender": "m"}
    saint_word = "świętych" if language == "pl" else "saints"
    for value in [realization(layer, saints), layer["segments"][saints_segment]["translation"]]:
        if re.search(rf"\b{saint_word}\b", value) is None or re.search(
            rf"\b{saint_word.capitalize()}\b", value
        ):
            errors.append("generic saints require lower case")
    mary_caption = realization(layer, mary)
    if language == "pl":
        if re.search(r"\btej(?:że| samej)\b", mary_caption) is None:
            errors.append("Mary-referent idem is not a divine capital")
        if realization(layer, christ) != ("Tegoż" if ordinary else "Tego samego"):
            errors.append("Christ-referent caption requires divine capitalization")
        if ordinary:
            about = layer["about"]
            if "prosi Boga, aby" not in about or "otaczał wiernych swoją opieką" not in about:
                errors.append("God remains the agent of His protection in the introduction")
            if layer["segments"][conclusion]["translation"] != (
                "Przez tegoż Chrystusa, Pana naszego. Amen."
            ):
                errors.append("inherited ordinary Polish conclusion must remain exact")
        else:
            if realization(layer, "w026") != "Tego samego":
                errors.append("Mother-of-Christ caption requires divine capitalization")
            if "Matki Tego samego Boga" not in layer["segments"]["s06"]["translation"]:
                errors.append("Mother-of-Christ verse requires divine capitalization")
            if "Przez Tego samego Chrystusa" not in layer["segments"][conclusion]["translation"]:
                errors.append("Christ conclusion verse requires divine capitalization")
        mary_segment = "s02" if ordinary else "s09"
        if "tej samej Dziewicy" not in layer["segments"][mary_segment]["translation"]:
            errors.append("Mary-referent verse must retain human capitalization")
    else:
        for wid in [mary, christ] + ([] if ordinary else ["w026"]):
            value = realization(layer, wid)
            if not re.search(r"\b(?:the|that) same\b", value) or re.search(r"\bSame\b", value):
                errors.append("English same remains an attributive lower-case expression")
    return errors


@pytest.mark.parametrize("slug", ["communicantes", "communicantes-in-cena-domini"])
@pytest.mark.parametrize("language", ["pl", "en"])
def test_actual_known_referents_and_retained_counterexamples(slug, language):
    core, layer = subject(slug, language)
    assert context_errors(slug, language, core, layer) == []


BAD_CASES = [
    ("communicantes", "pl", ["about"], "swoją", "Swoją"),
    ("communicantes", "pl", ["words", "w061", "gloss"], "świętych", "Świętych"),
    ("communicantes", "en", ["words", "w061", "gloss"], "saints", "Saints"),
    ("communicantes", "pl", ["words", "w075", "gloss"], "Tegoż", "tegoż"),
    ("communicantes-in-cena-domini", "pl", ["segments", "s06", "translation"], "Tego", "tego"),
    ("communicantes-in-cena-domini", "pl", ["words", "w026", "gloss"], "Tego", "tego"),
    (
        "communicantes-in-cena-domini",
        "pl",
        ["segments", "s12", "translation"],
        "świętych",
        "Świętych",
    ),
    ("communicantes-in-cena-domini", "pl", ["words", "w076", "gloss"], "świętych", "Świętych"),
    ("communicantes-in-cena-domini", "pl", ["segments", "s14", "translation"], "Tego", "tego"),
    ("communicantes-in-cena-domini", "pl", ["words", "w090", "gloss"], "Tego", "tego"),
    ("communicantes-in-cena-domini", "en", ["segments", "s12", "translation"], "saints", "Saints"),
    (
        "communicantes-in-cena-domini",
        "en",
        ["segments", "s12", "alignments", 0, "gloss"],
        "saints",
        "Saints",
    ),
    ("communicantes", "pl", ["words", "w022", "gloss"], "tejże", "Tejże"),
    ("communicantes", "pl", ["segments", "s02", "translation"], "tej", "Tej"),
    ("communicantes-in-cena-domini", "pl", ["words", "w037", "gloss"], "tej", "Tej"),
    ("communicantes-in-cena-domini", "pl", ["segments", "s09", "translation"], "tej", "Tej"),
    ("communicantes", "en", ["words", "w075", "gloss"], "same", "Same"),
    ("communicantes-in-cena-domini", "en", ["words", "w090", "gloss"], "same", "Same"),
    (
        "communicantes-in-cena-domini",
        "en",
        ["segments", "s06", "alignments", 0, "gloss"],
        "same",
        "Same",
    ),
    (
        "communicantes-in-cena-domini",
        "en",
        ["segments", "s09", "alignments", 1, "gloss"],
        "same",
        "Same",
    ),
    ("communicantes", "pl", ["segments", "s07", "translation"], "tegoż", "Tegoż"),
    ("communicantes", "pl", ["about"], "prosi Boga", "prosi świętych"),
]


@pytest.mark.parametrize("slug,language,address,before,after", BAD_CASES)
def test_wrong_case_or_preservation_mutations_are_refused(slug, language, address, before, after):
    core, layer = subject(slug, language)
    assert context_errors(slug, language, core, layer) == []
    changed = deepcopy(layer)
    if address[0] == "words" and address[-1] == "gloss":
        address = gloss_address(changed, address[1])
    field = changed
    for key in address[:-1]:
        field = field[key]
    assert before in field[address[-1]]
    field[address[-1]] = field[address[-1]].replace(before, after)
    assert changed != layer
    assert context_errors(slug, language, core, changed)

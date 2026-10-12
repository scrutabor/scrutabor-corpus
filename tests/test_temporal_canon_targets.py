"""Temporal Canon language coverage and bounded source-context regressions."""

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest

from checks.interlinear import check, effective_gloss
from checks.language_packs import check_core, check_layer

ROOT = Path(__file__).resolve().parents[1]
COUNTS = {
    "communicantes-in-nativitate-domini-in-nocte": 95,
    "communicantes-in-nativitate-domini-in-die": 95,
    "communicantes-in-epiphania-domini": 100,
    "communicantes-in-nocte-paschae": 92,
    "communicantes-in-die-paschae": 92,
    "communicantes-in-ascensione-domini": 101,
    "communicantes-in-pentecoste": 92,
    "hanc-igitur-paschale": 59,
}


def subject(slug, language):
    relative = f"texts/ordinarium/{slug}.json"
    return json.loads((ROOT / relative).read_text()), json.loads(
        (ROOT / "languages" / language / relative).read_text()
    )


def alignment(layer, word):
    return next(
        a for s in layer["segments"].values() for a in s.get("alignments", []) if word in a["words"]
    )


def line(core, layer, segments=None):
    return " ".join(
        gloss
        for s in core["segments"]
        if segments is None or s["id"] in segments
        for w in s.get("words", [])
        if (gloss := effective_gloss(layer, w["id"]))
    )


def context_errors(slug, language, core, layer):
    """Chosen contextual model; not a general semantic or naturalness parser."""
    errors = []
    words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    caption = line(core, layer)
    prose = " ".join(s.get("translation", "") for s in layer["segments"].values())
    if slug.startswith("communicantes"):
        v = next(w["id"] for w in words.values() if w["lemma"] == "veneror")
        if not re.search(
            r"czcimy pamięć" if language == "pl" else r"we venerate the memory",
            alignment(layer, v)["gloss"],
        ):
            errors.append("memory predicate must resume praying We, not event actor")
        m = next(w["id"] for w in words.values() if w["lemma"] == "munio")
        protection = alignment(layer, m)["gloss"]
        pattern = (
            r"byli umocnieni.*pomoc.*Twojej opieki"
            if language == "pl"
            else r"we may be defended.*help.*Your protection"
        )
        if not re.search(pattern, protection):
            errors.append("passive We, help means and Father protection remain")
        if "Twoich Świętych" in caption + prose or "Your Saints" in caption + prose:
            errors.append("generic collective saints is not a proper divine title")
        if language == "pl":
            for w in words.values():
                if (
                    w["lemma"] == "idem"
                    and w["morph"].get("gender") == "m"
                    and w["morph"].get("case") == "gen"
                    and layer["words"][w["id"]]["gloss"] != "Tego samego"
                ):
                    errors.append("unambiguous Christ pronoun capitalization")
        if "paschae" in slug:
            if alignment(layer, "w005")["words"] != ["w003", "w004", "w005"]:
                errors.append("celebration group need not absorb external genitives")
            if "w006" not in layer["words"] or not layer["words"]["w006"].get("gloss"):
                errors.append("Resurrection remains independent genitive realization")
            if alignment(layer, "w007")["words"] != ["w007", "w008"]:
                errors.append("Lord possession is a separate minimum nominal group")
        if "nativitate" in slug:
            actor = (
                r"Maryi.*dziewictwo zrodziło.*Zbawiciela"
                if language == "pl"
                else r"Mary’s inviolate virginity brought forth the Savior"
            )
            if not re.search(actor, prose):
                errors.append("virginity subject, genitive Mary and Savior object")
            if words["w013"]["lemma"] != "edo_proferre" or words["w013"]["morph"]["voice"] != "act":
                errors.append("bringing forth is distinct active lexical identity")
        if "epiphania" in slug:
            tokens = (
                [
                    "współwieczny",
                    "Tobą",
                    "Twojej chwale",
                    "naszym prawdziwym ciele",
                    "widzialnie",
                    "cielesnej postaci",
                ]
                if language == "pl"
                else [
                    "coeternal",
                    "with You",
                    "Your glory",
                    "our real flesh",
                    "visibly",
                    "bodily form",
                ]
            )
            if not all(t in caption for t in tokens):
                errors.append("coeternal Son, Father, real shared flesh and bodily visibility")
            if language == "en" and (
                alignment(layer, "w015")["words"] != ["w014", "w015", "w016", "w017"]
                or alignment(layer, "w020")["words"] != ["w018", "w019", "w020"]
            ):
                errors.append("two coherent minimum English manifestation spans")
        if "ascensione" in slug:
            pattern = (
                r"Twój Jednorodzony Syn.*umieścił.*naszą słabą naturę zjednoczoną z Sobą"
                if language == "pl"
                else (
                    r"Your Only-begotten Son.*placed our frail human nature, united to Himself, "
                    r"at the right hand of Your glory"
                )
            )
            if not re.search(pattern, prose):
                errors.append("Son places united frail human nature at Father glory")
        if "pentecoste" in slug:
            if (
                "niezliczonych językach" if language == "pl" else "countless tongues"
            ) not in caption:
                errors.append("countless tongues retained")
            if re.search(r"ognist|fire|flame|siedem|seven", caption + prose, re.I):
                errors.append("no unattested fire adjective or number")
    else:
        dependent = line(core, layer, {"s04", "s05"})
        group = alignment(layer, "w052")
        if group["words"] != [f"w{i:03}" for i in range(43, 55)]:
            errors.append("delayed common command/passive group boundaries")
        if language == "pl":
            if not re.search(
                r"abyś łaskawie przyjął.*uporządkował.*nakazał, byśmy zostali uwolnieni"
                r".*i zaliczeni do trzody Twoich wybranych",
                dependent,
            ):
                errors.append("dependent Father petitions and two passive We outcomes/flock")
            if re.search(r"abyś.*\bracz\b", dependent):
                errors.append("imperative cannot be stranded under abyś")
            if "i nasze dni" not in dependent or "a także" not in dependent:
                errors.append("-que and external atque both retained")
        else:
            if not re.search(
                r"that You graciously accept.*and order our days.*and command that we be rescued"
                r".*and counted in the flock of Your chosen",
                dependent,
            ):
                errors.append("shared dependent Father and passive We/flock")
            if "accept;" in prose:
                errors.append("semicolon detaches the continuing dependent petitions")
        if not layer["segments"]["s04"]["translation"].endswith(","):
            errors.append("continued dependent request punctuation")
        if (
            "Tego samego" in layer["segments"]["s07"]["translation"]
            or "the same" in layer["segments"]["s07"]["translation"]
        ):
            errors.append("H has no eundem imported from Communicantes")
        regeneration = alignment(layer, "w019")["gloss"]
        if regeneration != (
            "raczyłeś odrodzić" if language == "pl" else "You graciously regenerated"
        ):
            errors.append("completed Father regeneration, not Himself regenerated")
        if (
            words["w019"]["morph"]["voice"] != "dep"
            or words["w047"]["morph"]["voice"] != "pass"
            or words["w054"]["morph"]["voice"] != "pass"
        ):
            errors.append("perfect deponent and shared passive infinitives retained")
    return errors


SITES = [
    (s, lang, n)
    for s, count in COUNTS.items()
    for lang in ["pl", "en"]
    for n in range(1, count + 1)
]


@pytest.mark.parametrize("slug,language,number", SITES)
def test_each_realization_and_real_rejection(slug, language, number):
    core, layer = subject(slug, language)
    wid = f"w{number:03}"
    groups = [
        a for s in layer["segments"].values() for a in s.get("alignments", []) if wid in a["words"]
    ]
    direct = bool(layer["words"].get(wid, {}).get("gloss"))
    assert int(direct) + len(groups) == 1
    missing = deepcopy(layer)
    if direct:
        del missing["words"][wid]["gloss"]
    else:
        alignment(missing, wid)["words"].remove(wid)
    errors = check(core, missing)
    assert any(wid in error for error in errors)
    if groups:
        duplicate = deepcopy(layer)
        duplicate["words"].setdefault(wid, {})["gloss"] = "duplicate"
        assert any(wid in error for error in check(core, duplicate))
    else:
        marker = deepcopy(layer)
        marker["words"][wid]["gloss"] = "[grammar]"
        assert any(wid in error for error in check(core, marker))


@pytest.mark.parametrize("slug,language", [(s, lang) for s in COUNTS for lang in ["pl", "en"]])
def test_complete_context_layer_and_pending_provenance(slug, language):
    core, layer = subject(slug, language)
    assert sum(len(s.get("words", [])) for s in core["segments"]) == COUNTS[slug]
    assert check_core(core) == []
    assert (
        check_layer(
            core, layer, ROOT / "languages" / language / "texts/ordinarium" / f"{slug}.json"
        )
        == []
    )
    assert check(core, layer) == []
    assert context_errors(slug, language, core, layer) == []
    assert core["editorial"]["analysis_defaults"]["review"] == "pending"
    editorial = core["editorial"]
    default = editorial.get("analysis_defaults_words") or editorial["analysis_defaults"]
    assert all(
        (editorial.get("words", {}).get(w["id"], {}).get("analysis") or default)["review"]
        == "pending"
        for segment in core["segments"]
        for w in segment.get("words", [])
    )
    provenance = json.loads(
        (ROOT / "languages" / language / "translation-provenance.json").read_text()
    )
    sites = [r for r in provenance["sites"] if r["text"] == core["id"]]
    assert len(sites) == sum(s["type"] == "verse" for s in core["segments"])
    assert all(r["origin"] == "working-unsettled" and r["review"] == "working" for r in sites)


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize(
    "kind",
    [
        "wrong-regeneration-actor",
        "missing-flock",
        "lost-passive-outcome",
        "lost-que",
        "lost-atque",
        "detached-request",
    ],
)
def test_real_context_mutants(language, kind):
    slug = "hanc-igitur-paschale"
    core, layer = subject(slug, language)
    group = alignment(layer, "w052")
    if kind == "wrong-regeneration-actor":
        alignment(layer, "w019")["gloss"] = (
            "zostałeś odrodzony" if language == "pl" else "You were regenerated"
        )
    elif kind == "missing-flock":
        group["gloss"] = group["gloss"].replace("trzody", "grona").replace("flock", "number")
    elif kind == "lost-passive-outcome":
        group["gloss"] = group["gloss"].replace("i zaliczeni", "").replace("and counted", "")
    elif kind == "lost-que":
        g = alignment(layer, "w036")
        g["gloss"] = g["gloss"].removeprefix("i ").removeprefix("and ")
    elif kind == "lost-atque":
        layer["words"]["w042"]["gloss"] = ""
    elif kind == "detached-request":
        layer["segments"]["s04"]["translation"] = (
            layer["segments"]["s04"]["translation"].removesuffix(",") + ";"
        )
    assert context_errors(slug, language, core, layer)


def test_polish_imperative_under_abys_is_rejected():
    core, layer = subject("hanc-igitur-paschale", "pl")
    alignment(layer, "w052")["gloss"] = alignment(layer, "w052")["gloss"].replace(
        "nakazał", "racz nakazać"
    )
    assert context_errors("hanc-igitur-paschale", "pl", core, layer)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_father_cannot_replace_son_in_ascension(language):
    slug = "communicantes-in-ascensione-domini"
    core, layer = subject(slug, language)
    layer["segments"]["s01"]["translation"] = (
        layer["segments"]["s01"]["translation"]
        .replace("Twój Jednorodzony Syn", "Ojciec")
        .replace("Your Only-begotten Son", "the Father")
    )
    assert context_errors(slug, language, core, layer)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_lexical_homonym_cards_are_distinct(language):
    entries = json.loads((ROOT / "languages" / language / "lexicon.json").read_text())["entries"]
    assert entries["edo"]["senses"] == (["jeść", "spożywać"] if language == "pl" else ["to eat"])
    assert all(
        entries[head]["senses"] for head in ["edo_proferre", "coaeternus", "colloco", "innumerus"]
    )
    assert entries["edo_proferre"] != entries["edo"]

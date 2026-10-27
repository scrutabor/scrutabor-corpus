"""Holy Thursday Canon target coverage and bounded contextual regressions."""

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
from cena_hanc_fixture import hanc_polish_errors

from build_reader.layers import enrich_layer, expand_core
from checks.interlinear import check, effective_gloss
from checks.language_packs import check_core, check_layer
from checks.lint import lint_gloss
from checks.prose import check as check_prose

ROOT = Path(__file__).resolve().parents[1]
SLUGS = ["communicantes", "hanc-igitur", "qui-pridie"]
COUNTS = dict(zip(SLUGS, [94, 60, 50], strict=True))


def subject(slug, language):
    rel = f"texts/ordinarium/{slug}-in-cena-domini.json"
    return json.loads((ROOT / rel).read_text()), json.loads(
        (ROOT / "languages" / language / rel).read_text()
    )


def captions(core, layer, segments=None):
    return " ".join(
        effective_gloss(layer, word["id"])
        for segment in core["segments"]
        if segments is None or segment["id"] in segments
        for word in segment.get("words", [])
        if effective_gloss(layer, word["id"])
    )


def alignment(layer, word):
    return next(
        a
        for segment in layer["segments"].values()
        for a in segment.get("alignments", [])
        if word in a["words"]
    )


def outcome_alternative(layer, caption):
    """Construct a supported long semantic alternative, not the current layout."""
    members = [f"w{i:03}" for i in range(43, 55)]
    layer["segments"]["s06"]["alignments"] = [
        a for a in layer["segments"]["s06"]["alignments"] if not set(a["words"]) & set(members)
    ]
    layer["segments"]["s06"]["alignments"].append(
        {"words": members, "anchor": "w052", "gloss": caption}
    )
    for wid in members:
        layer["words"][wid].pop("gloss", None)


def days_alternative(layer, caption):
    """Retain the source-aware predicate-group lint controls on a real fixture."""
    members = [f"w{i:03}" for i in range(36, 42)]
    remaining = [
        a for a in layer["segments"]["s06"]["alignments"] if not set(a["words"]) & set(members)
    ]
    layer["segments"]["s06"]["alignments"] = [
        {"words": members, "anchor": "w041", "gloss": caption},
        *remaining,
    ]
    for wid in members:
        layer["words"][wid].pop("gloss", None)


SOURCE_FEATURES = {
    "communicantes": {"w014": {"voice": "pass", "tense": "perf"}, "w018": {"voice": "dep"}},
    "hanc-igitur": {
        "w022": {"voice": "act", "tense": "perf"},
        "w030": {"mood": "part", "tense": "fut", "voice": "pass"},
        "w047": {"voice": "pass"},
        "w054": {"voice": "pass"},
    },
    "qui-pridie": {"w008": {"tense": "impf"}, "w021": {"voice": "pass"}},
}


def source_relation_errors(slug, core):
    words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    return [
        f"{wid}.{key}: selected source relation changed"
        for wid, fields in SOURCE_FEATURES[slug].items()
        for key, value in fields.items()
        if words[wid]["morph"].get(key) != value
    ]


def context_errors(slug, language, core, layer):
    """Named source relations, not a general semantic or prose parser."""
    errors = []
    line = captions(core, layer)
    if slug == "communicantes":
        veneration = alignment(layer, "w018")["gloss"]
        finite = (
            r"\b(?:czcimy|oddajemy cześć)\b"
            if language == "pl"
            else r"\bwe (?:also )?(?:venerate|revere|honou?r)\b"
        )
        if not re.search(finite, veneration, re.I):
            errors.append("opening participles need praying We, not Father imperative actor")
        if language == "en" and re.search(r"day most (?:sacred|holy) celebrating", line, re.I):
            errors.append("English celebration-object inversion")
        if language == "en" and re.search(r"memory venerating", line, re.I):
            errors.append("English veneration-object inversion")
        first = layer["words"]["w026"]["explanation"]
        second = layer["words"]["w037"]["explanation"]
        if not re.search(r"Chrystus|Christ", first) or not re.search(r"Mary|Maryj", second):
            errors.append("eiusdem antecedents are distinct Christ and Mary")
        passive = alignment(layer, "w087")["gloss"]
        if language == "en" and not re.search(
            r"we may be (?:strengthened|fortified|protected|guarded)", passive
        ):
            errors.append("passive praying We under Father's grant")
        if language == "pl" and not re.search(r"byli (?:umocnieni|chronieni|strzeżeni)", passive):
            errors.append("passive praying We under Father's grant")
        terms = (
            (r"wsparci|pomoc", r"opieki|ochrony|obrony")
            if language == "pl"
            else (r"aid|help", r"protection|shelter")
        )
        if not all(re.search(term, passive) for term in terms):
            errors.append("aid and protection must both remain")
    if slug == "hanc-igitur":
        dependent = captions(core, layer, {"s05", "s06"})
        if language == "pl" and re.search(r"abyś.*\bracz\b", dependent):
            errors.append("independent imperative stranded under upstream abyś")
        if language == "en":
            if not re.search(r"that You (?:graciously )?accept", dependent):
                errors.append("You acceptance/disposition/command share upstream that")
            if (
                alignment(layer, "w036")["gloss"] != "and our days"
                or alignment(layer, "w038")["gloss"] != "in Your peace"
                or effective_gloss(layer, "w041") not in {"order", "arrange"}
                or effective_gloss(layer, "w042") != "and"
            ):
                errors.append("You acceptance/disposition/command share upstream that")
        if language == "pl":
            errors.extend(hanc_polish_errors(core, layer))
            if not layer["segments"]["s06"]["translation"].startswith("I "):
                errors.append("verse drops diesque coordination")
        else:
            direct = layer["words"]["w052"].get("gloss")
            if direct is not None:
                if (
                    direct not in {"command", "bid"}
                    or effective_gloss(layer, "w046") != "us"
                    or effective_gloss(layer, "w047") not in {"to be delivered", "to be rescued"}
                    or effective_gloss(layer, "w048") != "and"
                    or effective_gloss(layer, "w054")
                    not in {"to be counted", "to be numbered", "to be reckoned"}
                ):
                    errors.append("common divine governor of both passive outcomes")
                if (
                    effective_gloss(layer, "w049") != "in"
                    or effective_gloss(layer, "w053") != "the flock"
                    or alignment(layer, "w050")["gloss"] != "of Your elect"
                ):
                    errors.append("Father elect flock membership")
                if (
                    effective_gloss(layer, "w043") != "from"
                    or effective_gloss(layer, "w044") != "eternal"
                    or effective_gloss(layer, "w045") != "condemnation"
                ):
                    errors.append("release from eternal condemnation")
            else:
                group = alignment(layer, "w052")
                if group["words"] != [f"w{i:03}" for i in range(43, 55)]:
                    errors.append(
                        "chosen caption model strands common governor or passive dependents"
                    )
                target = group["gloss"]
                verbal = re.search(
                    r"(?:command|bid) that we be (?:delivered|rescued)"
                    r".*and (?:counted|numbered|reckoned)",
                    target,
                )
                nominal = re.search(r"(?:command|bid) our deliverance.*and our inclusion", target)
                if not verbal and not nominal:
                    errors.append("common divine governor of both passive outcomes")
                if "flock" not in target or "Your" not in target:
                    errors.append("Father elect flock membership")
        body = alignment(layer, "w029")
        if (
            body["words"] != [f"w{i:03}" for i in range(25, 30)]
            or body["anchor"] != "w029"
            or body["gloss"]
            != (
                "tajemnice swojego Ciała i Krwi"
                if language == "pl"
                else "the mysteries of His Body and Blood"
            )
            or effective_gloss(layer, "w030")
            != ("do sprawowania" if language == "pl" else "to be celebrated")
        ):
            errors.append("His Body AND Blood mysteries commissioned for celebration")
    if slug == "qui-pridie":
        if language == "en" and re.search(r"holy.*venerable His hands", line):
            errors.append("possessive cannot follow adjectives before hands")
        text = layer["segments"]["s13"]["narrative"]
        if language == "en" and "handled" not in text:
            errors.append("handling exception is not mere touching")
        if language == "pl" and "posługiwanie się hostią" not in text:
            errors.append("handling exception is not mere touching")
        condition = layer["segments"]["s11"]["narrative"]
        if language == "en" and not ("all the hosts" in condition and "if several" in condition):
            errors.append("multiple-host condition omitted")
        if language == "pl" and not ("wszystkimi" in condition and "jeśli" in condition):
            errors.append("multiple-host condition omitted")
        if language == "pl":
            if layer["segments"]["s10"]["translation"] != "Bierzcie i jedzcie z tego wszyscy:":
                errors.append("protected invitation changed without exact authority")
            if layer["segments"]["s12"]["translation"] != "To jest bowiem Ciało Moje.":
                errors.append("protected bread formula changed without exact authority")
            if layer["words"]["w050"]["gloss"] != "Moje":
                errors.append("protected meum caption changed")
        if "Amen" in layer["segments"]["s12"]["translation"]:
            errors.append("bread formula is not followed by Amen")
        if re.search(
            r"bell|dzwon|kielich|chalice",
            " ".join(r.get("narrative", "") for r in layer["segments"].values()),
            re.I,
        ):
            errors.append("unattested bell or chalice rubric added")
    return errors


@pytest.mark.parametrize(
    "slug,language,number",
    [(s, language, n) for s in SLUGS for language in ["pl", "en"] for n in range(1, COUNTS[s] + 1)],
)
def test_every_actual_word_has_one_real_realization(slug, language, number):
    core, layer = subject(slug, language)
    wid = f"w{number:03}"
    realizations = int(bool(layer["words"][wid].get("gloss"))) + sum(
        wid in a["words"]
        for segment in layer["segments"].values()
        for a in segment.get("alignments", [])
    )
    assert realizations == 1
    assert len([w for s in core["segments"] for w in s.get("words", [])]) == COUNTS[slug]


@pytest.mark.parametrize(
    "slug,language", [(s, language) for s in SLUGS for language in ["pl", "en"]]
)
def test_actual_full_layers_and_context(slug, language):
    core, layer = subject(slug, language)
    assert check_core(core) == []
    assert source_relation_errors(slug, core) == []
    assert (
        check_layer(
            core,
            layer,
            ROOT / "languages" / language / "texts/ordinarium" / f"{slug}-in-cena-domini.json",
        )
        == []
    )
    assert check(core, layer) == []
    assert context_errors(slug, language, core, layer) == []
    assert check_prose(layer) == []


@pytest.mark.parametrize("slug", SLUGS)
def test_source_analyses_remain_pending(slug):
    core, _ = subject(slug, "pl")
    editorial = core["editorial"]
    assert editorial["analysis_defaults"]["review"] == "pending"
    assert editorial["analysis_defaults_words"]["review"] == "pending"
    assert all(
        v.get("analysis", {}).get("review", "pending") == "pending"
        for v in editorial.get("words", {}).values()
    )


@pytest.mark.parametrize(
    "kind",
    [
        "duplicate-direct",
        "gap",
        "overlap",
        "noncontiguous",
        "anchor-outside",
        "technical-gloss",
        "zero-no-reason",
        "unsupported-explanation-shape",
    ],
)
def test_structural_mutations_are_refused(kind):
    core, layer = subject("hanc-igitur", "en")
    group = alignment(layer, "w029")
    if kind == "duplicate-direct":
        layer["words"]["w025"]["gloss"] = "of His Body"
    elif kind == "gap":
        del layer["words"]["w032"]["gloss"]
    elif kind == "overlap":
        layer["segments"]["s04"]["alignments"].append(deepcopy(group))
    elif kind == "noncontiguous":
        group["words"].remove("w027")
    elif kind == "anchor-outside":
        group["anchor"] = "w042"
    elif kind == "technical-gloss":
        group["gloss"] = "[UNRESOLVED]"
    elif kind == "zero-no-reason":
        group.pop("gloss")
        group.pop("anchor")
    else:
        core["localization"]["explanations"]["w030"] = {"mode": "editorial"}
    assert check(core, layer) or check_core(core)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_wrong_eiusdem_referents_are_refused(language):
    core, layer = subject("communicantes", language)
    layer["words"]["w026"]["explanation"], layer["words"]["w037"]["explanation"] = (
        layer["words"]["w037"]["explanation"],
        layer["words"]["w026"]["explanation"],
    )
    assert context_errors("communicantes", language, core, layer)


def test_polish_imperative_under_abys_is_refused_in_actual_full_caption():
    core, layer = subject("hanc-igitur", "pl")
    assert context_errors("hanc-igitur", "pl", core, layer) == []
    before = layer["words"]["w052"]["gloss"]
    assert "nakazał" in before
    layer["words"]["w052"]["gloss"] = before.replace("nakazał", "racz nakazać")
    assert layer["words"]["w052"]["gloss"] != before
    assert check(core, layer) == []  # Structure alone cannot prove whole-clause grammar.
    assert "abyś" in captions(core, layer) and "racz" in captions(core, layer)
    assert "independent imperative stranded under upstream abyś" in context_errors(
        "hanc-igitur", "pl", core, layer
    )
    layer["words"]["w052"]["gloss"] = before
    assert context_errors("hanc-igitur", "pl", core, layer) == []


def test_wrong_english_possessive_position_is_refused_in_actual_caption():
    core, layer = subject("qui-pridie", "en")
    alignment(layer, "w018")["gloss"] = "holy and venerable His hands"
    assert check(core, layer) == []
    assert context_errors("qui-pridie", "en", core, layer)


@pytest.mark.parametrize(
    "slug,word,field,value",
    [
        ("communicantes", "w014", "voice", "act"),
        ("communicantes", "w014", "tense", "pres"),
        ("communicantes", "w018", "voice", "act"),
        ("hanc-igitur", "w022", "voice", "pass"),
        ("hanc-igitur", "w022", "tense", "pres"),
        ("hanc-igitur", "w030", "tense", "pres"),
        ("hanc-igitur", "w047", "voice", "act"),
        ("hanc-igitur", "w054", "voice", "act"),
        ("qui-pridie", "w008", "tense", "pres"),
        ("qui-pridie", "w021", "voice", "act"),
    ],
)
def test_selected_source_features_are_not_relabelled(slug, word, field, value):
    core, _ = subject(slug, "en")
    actual = next(w for s in core["segments"] for w in s.get("words", []) if w["id"] == word)
    assert actual["morph"][field] != value
    assert source_relation_errors(slug, core) == []
    actual["morph"][field] = value
    assert source_relation_errors(slug, core)


@pytest.mark.parametrize(
    "caption",
    [
        "bid that we be rescued from eternal condemnation and numbered in the flock of Your elect",
        "command our deliverance from eternal condemnation "
        "and our inclusion in the flock of Your elect",
    ],
)
def test_semantically_viable_english_outcome_alternatives_are_not_preference_locked(caption):
    core, layer = subject("hanc-igitur", "en")
    original = deepcopy(layer)
    assert check(core, layer) == [] and context_errors("hanc-igitur", "en", core, layer) == []
    outcome_alternative(layer, caption)
    assert layer != original
    assert check(core, layer) == []
    assert context_errors("hanc-igitur", "en", core, layer) == []
    layer.clear()
    layer.update(original)
    assert check(core, layer) == [] and context_errors("hanc-igitur", "en", core, layer) == []


@pytest.mark.parametrize(
    "caption",
    [
        "deliver us from eternal condemnation "
        "and command that we be counted in the flock of Your elect",
        "command that we deliver from eternal condemnation and count the flock of Your elect",
        "command that we be delivered from eternal condemnation",
        "command that we be delivered from eternal condemnation and counted among Your elect",
    ],
)
def test_governor_voice_and_flock_losses_are_refused(caption):
    core, layer = subject("hanc-igitur", "en")
    original = deepcopy(layer)
    assert check(core, layer) == [] and context_errors("hanc-igitur", "en", core, layer) == []
    outcome_alternative(layer, caption)
    assert layer != original and check(core, layer) == []
    assert context_errors("hanc-igitur", "en", core, layer)
    layer.clear()
    layer.update(original)
    assert check(core, layer) == [] and context_errors("hanc-igitur", "en", core, layer) == []


@pytest.mark.parametrize("language", ["pl", "en"])
def test_touching_cannot_replace_handling_condition(language):
    core, layer = subject("qui-pridie", language)
    text = layer["segments"]["s13"]["narrative"]
    layer["segments"]["s13"]["narrative"] = text.replace("handled", "touched").replace(
        "posługiwanie się hostią", "dotknięcie hostii"
    )
    assert context_errors("qui-pridie", language, core, layer)


@pytest.mark.parametrize(
    "site,value",
    [
        ("s10", "Bierzcie i jedzcie wszyscy:"),
        ("s12", "To jest bowiem Ciało moje."),
        ("w050", "moje"),
    ],
)
def test_unauthorized_protected_delta_is_refused(site, value):
    core, layer = subject("qui-pridie", "pl")
    if site.startswith("s"):
        layer["segments"][site]["translation"] = value
    else:
        layer["words"][site]["gloss"] = value
    assert context_errors("qui-pridie", "pl", core, layer)


def absorption(core, layer):
    return [
        e for e in lint_gloss(enrich_layer(core, layer), expand_core(core)) if "conjunction" in e
    ]


@pytest.mark.parametrize(
    "caption",
    [
        "and order our days in Your peace",
        "and arrange our days in Your peace",
        "order our days in Your peace as well",
    ],
)
def test_enclosed_que_and_separate_atque_are_both_realized(caption):
    core, layer = subject("hanc-igitur", "en")
    original = deepcopy(layer)
    days_alternative(layer, caption)
    assert layer != original
    assert check(core, layer) == []
    assert absorption(core, layer) == []
    layer.clear()
    layer.update(original)
    assert check(core, layer) == [] and absorption(core, layer) == []


@pytest.mark.parametrize(
    "caption", ["order our days in Your peace", "and order our days in Your peace and command"]
)
def test_dropped_que_or_absorbed_atque_is_refused(caption):
    core, layer = subject("hanc-igitur", "en")
    original = deepcopy(layer)
    days_alternative(layer, caption)
    assert layer != original and check(core, layer) == []
    assert absorption(core, layer)
    layer.clear()
    layer.update(original)
    assert absorption(core, layer) == []


def test_absorbing_atque_into_the_group_cannot_hide_its_missing_realization():
    core, layer = subject("hanc-igitur", "en")
    original = deepcopy(layer)
    days_alternative(layer, "and order our days in Your peace")
    assert check(core, layer) == [] and absorption(core, layer) == []
    group = alignment(layer, "w041")
    group["words"].append("w042")
    del layer["words"]["w042"]["gloss"]
    assert check(core, layer) == []
    assert absorption(core, layer)
    group["gloss"] += " and"
    assert absorption(core, layer) == []
    layer.clear()
    layer.update(original)
    assert check(core, layer) == [] and absorption(core, layer) == []


@pytest.mark.parametrize(
    "field,value", [("form", "dies"), ("lemma", "diesque"), ("morph", {"pos": "adv"})]
)
def test_wrong_enclitic_source_cannot_license_and(field, value):
    core, layer = subject("hanc-igitur", "en")
    original = deepcopy((core, layer))
    days_alternative(layer, "and order our days in Your peace")
    assert check(core, layer) == [] and absorption(core, layer) == []
    word = next(w for s in core["segments"] for w in s.get("words", []) if w["id"] == "w036")
    word[field] = value
    assert absorption(core, layer)
    core.clear()
    core.update(original[0])
    layer.clear()
    layer.update(original[1])
    assert check(core, layer) == [] and absorption(core, layer) == []


def test_source_aware_exception_is_not_text_id_specific():
    core, layer = subject("hanc-igitur", "en")
    original = deepcopy((core, layer))
    days_alternative(layer, "and order our days in Your peace")
    core["id"] = layer["text"] = "ordinarium.other-prayer"
    assert absorption(core, layer) == []
    core.clear()
    core.update(original[0])
    layer.clear()
    layer.update(original[1])
    assert check(core, layer) == [] and absorption(core, layer) == []


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("kind", ["owner", "gerundive"])
def test_mysteries_owner_and_gerundive_reject_and_restore(language, kind):
    core, layer = subject("hanc-igitur", language)
    original = deepcopy(layer)
    assert check(core, layer) == [] and context_errors("hanc-igitur", language, core, layer) == []
    if kind == "owner":
        item = alignment(layer, "w029")
        before = item["gloss"]
        item["gloss"] = before.replace("swojego", "uczniów").replace("His", "their")
    else:
        layer["words"]["w030"]["gloss"] = (
            "już sprawowane" if language == "pl" else "already celebrated"
        )
    assert layer != original and check(core, layer) == []
    assert "His Body AND Blood mysteries commissioned for celebration" in context_errors(
        "hanc-igitur", language, core, layer
    )
    layer.clear()
    layer.update(original)
    assert check(core, layer) == [] and context_errors("hanc-igitur", language, core, layer) == []


@pytest.mark.parametrize("kind", ["patient", "rescue-voice", "counting-voice", "elect-owner"])
def test_short_english_outcome_losses_reject_and_restore(kind):
    core, layer = subject("hanc-igitur", "en")
    original = deepcopy(layer)
    assert check(core, layer) == [] and context_errors("hanc-igitur", "en", core, layer) == []
    if kind == "patient":
        layer["words"]["w046"]["gloss"] = "them"
    elif kind == "rescue-voice":
        layer["words"]["w047"]["gloss"] = "to deliver others"
    elif kind == "counting-voice":
        layer["words"]["w054"]["gloss"] = "to count others"
    else:
        alignment(layer, "w050")["gloss"] = "of our elect"
    assert layer != original and check(core, layer) == []
    assert context_errors("hanc-igitur", "en", core, layer)
    layer.clear()
    layer.update(original)
    assert check(core, layer) == [] and context_errors("hanc-igitur", "en", core, layer) == []


def hanc_outside(layer):
    """Project only the fields outside this exact caption correction scope."""
    value = deepcopy(layer)
    language = value["language"]
    if value["text"] == "ordinarium.hanc-igitur-in-cena-domini":
        spans = {"s04": range(25, 31), "s06": range(43, 55) if language == "pl" else range(36, 55)}
        mutable = (
            [30, 43, 44, 45, 46, 47, 49, 52, 53, 54]
            if language == "pl"
            else [30, 41, 43, 44, 45, 46, 47, 48, 49, 52, 53, 54]
        )
        value["words"]["w052"].pop("explanation")
    elif value["text"] == "ordinarium.hanc-igitur-paschale" and language == "en":
        spans, mutable = {"s05": range(36, 42)}, [41]
    else:
        assert value["text"] == "ordinarium.hanc-igitur-paschale" and language == "pl"
        spans, mutable = {}, []
    for sid, numbers in spans.items():
        selected = {f"w{i:03}" for i in numbers}
        value["segments"][sid]["alignments"] = [
            group
            for group in value["segments"][sid]["alignments"]
            if not selected.intersection(group["words"])
        ]
    for number in mutable:
        value["words"][f"w{number:03}"].pop("gloss", None)
    return value


def canonical(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def test_hanc_source_prose_origin_and_every_outside_field_are_preserved():
    sources = {
        "hanc-igitur-in-cena-domini": (
            "c226e902778fd453900efa5dbd19515ab914c7251d98121adab495eaa0312b59"
        ),
        "hanc-igitur-paschale": "5daa210173709de21810cdd5e644dc42896961c3f9cef8918646256755d97973",
    }
    expected = {
        (
            "hanc-igitur-in-cena-domini",
            "pl",
        ): "9eb02cf3639d7f1822a8a824ad48b9db73211e786420a4e19f35b0572c55cae4",
        (
            "hanc-igitur-in-cena-domini",
            "en",
        ): "66672f93c0ac6338ba480c45916ee9b8858de47f03bc6adf2a7e3b66270380a6",
        (
            "hanc-igitur-paschale",
            "pl",
        ): "1f239ca92c91eaa5a5ad4996c47820f6f327651c49bca517001c6d027b08ad9c",
        (
            "hanc-igitur-paschale",
            "en",
        ): "2eefdc282f75a8687b131d9511540e48f4c72dc42538f192b5bdc9a2cc8eaee7",
    }
    for slug, source_sha in sources.items():
        source = (ROOT / f"texts/ordinarium/{slug}.json").read_bytes()
        assert hashlib.sha256(source).hexdigest() == source_sha
    for (slug, language), outside_sha in expected.items():
        path = ROOT / f"languages/{language}/texts/ordinarium/{slug}.json"
        layer = json.loads(path.read_bytes())
        assert canonical(hanc_outside(layer)) == outside_sha
        original = deepcopy(layer)
        layer["segments"]["s02"]["translation"] += " omitted source"
        assert canonical(hanc_outside(layer)) != outside_sha
        layer.clear()
        layer.update(original)
        assert canonical(hanc_outside(layer)) == outside_sha
    for language, expected_sha in (
        ("pl", "c2ac122c25b33de0fb26bbe951f44477ead529277f97c52da48c21d10a5eb96d"),
        ("en", "38cd6a445d6002a2f5423ae52018eb7ba22735c2dcb3c7eca746e8f9910e088f"),
    ):
        path = ROOT / f"languages/{language}/translation-provenance.json"
        rows = json.loads(path.read_bytes())["sites"]
        selected = [
            row for row in rows if row["text"] in {"ordinarium." + slug for slug in sources}
        ]
        assert canonical(selected) == expected_sha

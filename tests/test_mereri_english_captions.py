"""English captions of finite mereo/mereor constructions in short interlinear groups.

Each repaired realization is anchored on the finite Latin verb and keeps its person,
number, tense, mood and voice: a subordinate present subjunctive reads "we may ...",
a perfect indicative reads "we have been ...", and a passive infinitive stays passive.
The groups stay short. Complements that Latin order places before or around the verb
remain separate captions, or join the group only where the verb interrupts them.
Retained realizations at other mereo/mereor sites are pinned as controls, so that an
indicative, a past tense, a third-person subject or a nominal object is never
rewritten into a first-person-plural wish. One in-memory mutant per diagnostic class
must fail that class, and the restored documents must pass again.
"""

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs

ROOT = Path(__file__).resolve().parents[1]
P = "proprium."
ANNUNTIATIO = P + "annuntiatio-beatae-mariae-virginis-secreta"
ASSUMPTIO = P + "assumptio-beatae-mariae-virginis-collecta"
REGINA = P + "beata-maria-virgo-regina-collecta"
BAPTISMA = P + "commemoratio-baptismatis-domini-collecta"
LATERANUM = P + "dedicatio-archibasilicae-sanctissimi-salvatoris-secreta"
ADVENTUS = P + "dominica-i-adventus-collecta"
XVI = P + "dominica-xvi-post-pentecosten-secreta"
EXALTATIO = P + "exaltatio-sanctae-crucis-secreta"
OCTAVA = P + "in-octava-nativitatis-collecta"
NOCTE = P + "nativitas-domini-in-nocte-postcommunio"
FAMILIA = P + "sancta-familia-postcommunio"
ANNA = P + "sanctae-annae-matris-beatae-mariae-virginis-postcommunio"
IOACHIM_PC = P + "sancti-ioachim-confessoris-postcommunio"
IOACHIM_SECRETA = P + "sancti-ioachim-confessoris-secreta"
PHILIPPUS = P + "sanctorum-philippi-et-iacobi-apostolorum-secreta"

# text: (words, anchor, gloss) of the shared realization at the construction.
GROUPS = {
    ANNUNTIATIO: (
        ("w025", "w026", "w027", "w028", "w029"),
        "w027",
        "we may deserve to attain everlasting joy",
    ),
    ASSUMPTIO: (("w025", "w026"), "w026", "of her glory"),
    REGINA: (("w024", "w025"), "w025", "we may be worthy to attain"),
    BAPTISMA: (("w020", "w021"), "w021", "we may be found worthy to be reformed"),
    LATERANUM: (("w017", "w018"), "w018", "we may be worthy to attain"),
    ADVENTUS: (("w014", "w015", "w016"), "w015", "with You protecting, we may deserve"),
    XVI: (("w014", "w015", "w016", "w017"), "w015", "we may deserve to be partakers of it"),
    EXALTATIO: (("w021", "w022", "w023"), "w023", "we have been found worthy to venerate it"),
    FAMILIA: (("w032", "w033"), "w033", "we may merit to be received"),
    ANNA: (("w022", "w023"), "w023", "we may deserve to attain"),
    IOACHIM_PC: (("w034", "w035", "w036"), "w036", "we may deserve to be partakers"),
    IOACHIM_SECRETA: (
        ("w025", "w026", "w027", "w028"),
        "w027",
        "we may deserve to obtain full remission",
    ),
}

# text: (first word, last word, local caption sequence as the reader composes it).
LINES = {
    ANNUNTIATIO: (
        "w019",
        "w029",
        (
            "we confess",
            "through",
            "His",
            "redeeming",
            "of the Resurrection",
            "power",
            "we may deserve to attain everlasting joy",
        ),
    ),
    ASSUMPTIO: (
        "w020",
        "w029",
        (
            "that",
            "to",
            "heavenly things",
            "always",
            "devoting ourselves",
            "of her glory",
            "we may deserve",
            "to be",
            "sharers",
        ),
    ),
    REGINA: (
        "w017",
        "w025",
        (
            "peace",
            "in",
            "the present",
            "and",
            "glory",
            "in",
            "the future",
            "we may be worthy to attain",
        ),
    ),
    BAPTISMA: (
        "w016",
        "w021",
        ("us", "outwardly", "we have known", "inwardly", "we may be found worthy to be reformed"),
    ),
    LATERANUM: (
        "w011",
        "w018",
        ("we render", "to", "eternal", "rewards", "You", "helping", "we may be worthy to attain"),
    ),
    ADVENTUS: (
        "w008",
        "w020",
        (
            "that",
            "from",
            "impending",
            "dangers of our sins",
            "with You protecting, we may deserve",
            "to be rescued",
            "with You",
            "delivering",
            "to be saved",
        ),
    ),
    XVI: ("w012", "w017", ("us", "that", "we may deserve to be partakers of it")),
    EXALTATIO: (
        "w019",
        "w030",
        (
            "that we",
            "as",
            "we have been found worthy to venerate it",
            "so",
            "forever",
            "its",
            "glory",
            "saving",
            "may enjoy",
            "the fruit",
        ),
    ),
    OCTAVA: (
        "w021",
        "w026",
        ("through", "whom", "we have merited", "to receive the Author of life"),
    ),
    NOCTE: ("w018", "w024", ("by worthy", "lives", "may deserve to attain to His fellowship")),
    FAMILIA: (
        "w026",
        "w033",
        (
            "Joseph",
            "through",
            "You",
            "into",
            "everlasting",
            "tabernacles",
            "we may merit to be received",
        ),
    ),
    ANNA: (
        "w018",
        "w023",
        ("You willed", "to", "eternal", "salvation", "we may deserve to attain"),
    ),
    IOACHIM_PC: (
        "w024",
        "w036",
        (
            "Christ",
            "of Your",
            "grace",
            "in",
            "the present",
            "and",
            "of eternal",
            "glory",
            "in",
            "the future",
            "we may deserve to be partakers",
        ),
    ),
    IOACHIM_SECRETA: (
        "w023",
        "w032",
        (
            "child",
            "interceding",
            "we may deserve to obtain full remission",
            "of sins",
            "and",
            "glory",
            "everlasting",
        ),
    ),
}

# text: (finite first-person-plural verb, lemma, mood, tense, phrases its caption keeps).
PREDICATES = {
    ANNUNTIATIO: ("w027", "mereor", "subj", "pres", ("to attain", "everlasting joy")),
    ASSUMPTIO: ("w027", "mereor", "subj", "pres", ()),
    REGINA: ("w025", "mereor", "subj", "pres", ("to attain",)),
    BAPTISMA: ("w021", "mereor", "subj", "pres", ()),
    LATERANUM: ("w018", "mereor", "subj", "pres", ("to attain",)),
    ADVENTUS: ("w015", "mereor", "subj", "pres", ("with You protecting",)),
    XVI: ("w015", "mereor", "subj", "pres", ("to be partakers of it",)),
    EXALTATIO: ("w023", "mereo", "ind", "perf", ("to venerate it",)),
    FAMILIA: ("w033", "mereor", "subj", "pres", ()),
    ANNA: ("w023", "mereor", "subj", "pres", ("to attain",)),
    IOACHIM_PC: ("w036", "mereor", "subj", "pres", ("to be partakers",)),
    IOACHIM_SECRETA: ("w027", "mereor", "subj", "pres", ("to obtain full remission",)),
}

# text: passive Latin infinitives and the English passive their caption keeps.
PASSIVES = {
    BAPTISMA: (("w020", "to be reformed"),),
    ADVENTUS: (("w017", "to be rescued"), ("w020", "to be saved")),
    FAMILIA: (("w032", "to be received"),),
}

# text: (word, explanation, Latin forms it quotes, English phrase shared with the caption).
EXPLANATIONS = {
    ANNUNTIATIO: (
        "w027",
        "After “ut,” “mereámur” takes the infinitive “perveníre”: “that we may deserve to "
        "attain.” Both verbs stand between “ad ætérnam” and “lætítiam,” which belong "
        "together: “to everlasting joy.”",
        ("ut", "mereámur", "perveníre", "ad ætérnam", "lætítiam"),
        "we may deserve to attain",
    ),
    ASSUMPTIO: (
        "w026",
        "Here “ipsíus glóriæ” belongs with “consórtes,” which follows the verb: “sharers of "
        "her own glory.” The glory is Mary’s, the heavenly glory into which she was taken up.",
        ("ipsíus glóriæ", "consórtes"),
        "her",
    ),
    XVI: (
        "w015",
        "Here “eius” stands before “mereámur esse” but belongs with “partícipes”: “partakers "
        "of it.”",
        ("eius", "mereámur esse", "partícipes"),
        "partakers of it",
    ),
    IOACHIM_SECRETA: (
        "w027",
        "After “ut,” “mereámur” takes the infinitive “cónsequi”: “that we may deserve to "
        "obtain.” Both verbs stand between “perféctam” and “remissiónem,” which belong "
        "together: “full remission.” The second object is “glóriam sempitérnam,” "
        "“everlasting glory.”",
        ("ut", "mereámur", "cónsequi", "perféctam", "remissiónem", "glóriam sempitérnam"),
        "we may deserve to obtain",
    ),
}

# Retained realizations at other mereo/mereor sites and the Latin form they render.
# text: (segment, verb, lemma, person, number, tense, mood, caption of the verb).
CONTROLS = {
    "orationes.regina-caeli": (
        "s02",
        "w007",
        "mereo",
        2,
        "sg",
        "perf",
        "ind",
        "you were counted worthy",
    ),
    "ordinarium.aufer-a-nobis": (
        "s04",
        "w014",
        "mereor",
        1,
        "pl",
        "pres",
        "subj",
        "with pure minds we may be worthy",
    ),
    P + "commemoratio-omnium-fidelium-defunctorum-missa-i-tractus": (
        "s01",
        "w015",
        "mereor",
        3,
        "pl",
        "pres",
        "subj",
        "may they be worthy",
    ),
    P + "dominica-ii-adventus-collecta": (
        "s01",
        "w018",
        "mereor",
        1,
        "pl",
        "pres",
        "subj",
        "we may be found worthy to serve You with purified minds",
    ),
    P + "dominica-ii-passionis-collecta": (
        "s01",
        "w030",
        "mereor",
        1,
        "pl",
        "pres",
        "subj",
        "we may be worthy both to learn from His patience and to share in His resurrection",
    ),
    P + "dominica-infra-octavam-nativitatis-collecta": (
        "s01",
        "w016",
        "mereor",
        1,
        "pl",
        "pres",
        "subj",
        "we may merit",
    ),
    P + "dominica-xiii-post-pentecosten-collecta": (
        "s01",
        "w013",
        "mereor",
        1,
        "pl",
        "pres",
        "subj",
        "we may deserve",
    ),
    P + "exaltatio-sanctae-crucis-collecta": (
        "s01",
        "w025",
        "mereor",
        1,
        "pl",
        "pres",
        "subj",
        "we may deserve",
    ),
    P + "sanctae-annae-matris-beatae-mariae-virginis-collecta": (
        "s01",
        "w016",
        "mereor",
        3,
        "sg",
        "impf",
        "subj",
        "she might merit",
    ),
    PHILIPPUS: ("s01", "w018", "mereor", 1, "pl", "pres", "ind", "we deserve"),
    P + "septem-dolorum-beatae-mariae-virginis-communio": (
        "s01",
        "w009",
        "mereo",
        3,
        "pl",
        "perf",
        "ind",
        "earned",
    ),
    OCTAVA: ("s01", "w023", "mereo", 1, "pl", "perf", "ind", "we have merited"),
    NOCTE: (
        "s01",
        "w022",
        "mereor",
        1,
        "pl",
        "pres",
        "subj",
        "may deserve to attain to His fellowship",
    ),
}

INVERTED = re.compile(r"\b(?:may|have|might) (?:we|they|she)\b")
QUOTE = re.compile(r"“([^”]+?)[,.]?”")


def path_of(text, language=None):
    category, name = text.split(".", 1)
    base = ROOT / ("languages/" + language + "/texts" if language else "texts")
    return base / category / f"{name}.json"


def load(text, language=None):
    return json.loads(path_of(text, language).read_text(encoding="utf-8"))


def latin(core):
    return {w["id"]: w for s in core["segments"] for w in s.get("words", [])}


def realization(layer, segment, word):
    """The caption that carries a word: its group's gloss or its own direct gloss."""
    for group in layer["segments"][segment].get("alignments", []):
        if word in group["words"]:
            return group.get("gloss", "")
    return layer["words"][word].get("gloss", "")


def composed(core, layer, segment, first, last):
    words = next(s["words"] for s in core["segments"] if s["id"] == segment)
    ids = [w["id"] for w in words]
    window = ids[ids.index(first) : ids.index(last) + 1]
    groups = {g["words"][0]: g for g in layer["segments"][segment].get("alignments", [])}
    out, i = [], 0
    while i < len(window):
        group = groups.get(window[i])
        if group:
            if group.get("gloss"):
                out.append(group["gloss"])
            i += len(group["words"])
        else:
            out.append(layer["words"][window[i]]["gloss"])
            i += 1
    return tuple(out)


def diagnostics(text, core, layer):
    """Class-tagged departures from the pinned English realization of one text."""
    found = []
    words = latin(core)
    if text in GROUPS:
        ids, anchor, gloss = GROUPS[text]
        actual = [
            g for g in layer["segments"]["s01"].get("alignments", []) if set(ids) & set(g["words"])
        ]
        if actual != [{"words": list(ids), "anchor": anchor, "gloss": gloss}]:
            found.append(f"line:{text}: group {list(ids)} is {actual}")
    if text in LINES:
        first, last, expected = LINES[text]
        line = composed(core, layer, "s01", first, last)
        if line != expected:
            found.append(f"line:{text}: {line}")
    if text in PREDICATES:
        verb, lemma, mood, tense, phrases = PREDICATES[text]
        morph = words[verb]["morph"]
        parse = (words[verb]["lemma"], morph.get("person"), morph.get("number"))
        if (*parse, morph.get("mood"), morph.get("tense")) != (lemma, 1, "pl", mood, tense):
            found.append(f"latin:{text}:{verb}: {words[verb]['lemma']} {morph}")
        caption = realization(layer, "s01", verb)
        if not re.search(r"\bwe\b", caption):
            found.append(f"subject:{text}:{verb}: {caption!r}")
        if INVERTED.search(caption):
            found.append(f"order:{text}:{verb}: {caption!r}")
        if tense == "perf":
            if not re.search(r"\bhave been\b", caption):
                found.append(f"tense:{text}:{verb}: {caption!r}")
        elif not re.search(r"\bmay\b", caption) or re.search(r"\bhave\b", caption):
            found.append(f"tense:{text}:{verb}: {caption!r}")
        found += [
            f"complement:{text}:{verb}: {phrase!r} missing from {caption!r}"
            for phrase in phrases
            if phrase not in caption
        ]
    for infinitive, phrase in PASSIVES.get(text, ()):
        morph = words[infinitive]["morph"]
        if (morph.get("mood"), morph.get("voice")) != ("inf", "pass"):
            found.append(f"latin:{text}:{infinitive}: {morph}")
        if phrase not in realization(layer, "s01", infinitive):
            found.append(f"voice:{text}:{infinitive}: {phrase!r} not kept")
    if text in EXPLANATIONS:
        word, prose, _, _ = EXPLANATIONS[text]
        requirement = (core.get("localization") or {}).get("explanations", {}).get(word)
        if requirement is None or "en" not in requirement.get("languages", ["en"]):
            found.append(f"explanation:{text}:{word}: no English requirement")
        if layer["words"][word].get("explanation") != prose:
            found.append(f"explanation:{text}:{word}: {layer['words'][word].get('explanation')!r}")
    if text in CONTROLS:
        segment, verb, lemma, person, number, tense, mood, caption = CONTROLS[text]
        morph = words[verb]["morph"]
        parse = (words[verb]["lemma"], morph.get("person"), morph.get("number"))
        if (*parse, morph.get("tense"), morph.get("mood")) != (lemma, person, number, tense, mood):
            found.append(f"latin:{text}:{verb}: {words[verb]['lemma']} {morph}")
        if realization(layer, segment, verb) != caption:
            found.append(f"control:{text}:{verb}: {realization(layer, segment, verb)!r}")
    return found


PINNED = sorted(set(GROUPS) | set(LINES) | set(CONTROLS))


@pytest.mark.parametrize("text", PINNED)
def test_pinned_english_realization(text):
    assert diagnostics(text, load(text), load(text, "en")) == []


@pytest.mark.parametrize("text", sorted(GROUPS))
def test_repaired_layers_pass_the_product_validators(text):
    core, layer = load(text), load(text, "en")
    assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
    assert language_packs.check_core(core) == []
    assert language_packs.check_layer(core, layer, path_of(text, "en")) == []


@pytest.mark.parametrize("text", sorted(EXPLANATIONS))
def test_explanation_quotes_the_printed_latin_and_its_caption(text):
    core, layer = load(text), load(text, "en")
    word, prose, quoted, shared = EXPLANATIONS[text]
    segment = next(s for s in core["segments"] if any(w["id"] == word for w in s["words"]))
    forms = [w["form"] for w in segment["words"]]
    latin_quotes = [q for q in QUOTE.findall(prose) if all(t in forms for t in q.split())]
    assert latin_quotes == list(quoted)
    assert latin(core)[word]["form"] in prose
    assert shared in prose
    assert shared in " ".join(composed(core, layer, "s01", *LINES[text][:2]))
    assert ";" not in prose


def remove_group(layer, segment, ids, glosses):
    layer["segments"][segment]["alignments"] = [
        g for g in layer["segments"][segment]["alignments"] if g["words"] != list(ids)
    ]
    for word, gloss in zip(ids, glosses, strict=True):
        layer["words"][word] = {"gloss": gloss}


def set_group_gloss(layer, segment, anchor, gloss):
    for group in layer["segments"][segment]["alignments"]:
        if group.get("anchor") == anchor:
            group["gloss"] = gloss


def set_latin_tense(core, word, tense):
    latin(core)[word]["morph"]["tense"] = tense


MUTANTS = {
    "line": (
        FAMILIA,
        lambda core, layer: remove_group(
            layer, "s01", ("w032", "w033"), ("to be received", "we may merit")
        ),
    ),
    "subject": (
        ANNUNTIATIO,
        lambda core, layer: set_group_gloss(
            layer, "s01", "w027", "may deserve to attain everlasting joy"
        ),
    ),
    "order": (
        REGINA,
        lambda core, layer: set_group_gloss(layer, "s01", "w025", "may we be worthy to attain"),
    ),
    "tense": (
        EXALTATIO,
        lambda core, layer: set_group_gloss(
            layer, "s01", "w023", "we may be found worthy to venerate it"
        ),
    ),
    "voice": (
        BAPTISMA,
        lambda core, layer: set_group_gloss(
            layer, "s01", "w021", "we may be found worthy to reform"
        ),
    ),
    "complement": (
        IOACHIM_SECRETA,
        lambda core, layer: set_group_gloss(
            layer, "s01", "w027", "we may deserve to obtain remission"
        ),
    ),
    "explanation": (XVI, lambda core, layer: layer["words"]["w015"].pop("explanation")),
    "control": (
        PHILIPPUS,
        lambda core, layer: layer["words"]["w018"].update(gloss="we may deserve"),
    ),
    "latin": (EXALTATIO, lambda core, layer: set_latin_tense(core, "w023", "pres")),
}


@pytest.mark.parametrize("kind", sorted(MUTANTS))
def test_mutant_fails_its_class_and_restores(kind):
    text, mutate = MUTANTS[kind]
    core, layer = load(text), load(text, "en")
    originals = deepcopy(core), deepcopy(layer)
    assert diagnostics(text, core, layer) == []
    mutate(core, layer)
    found = diagnostics(text, core, layer)
    assert any(item.startswith(kind + ":") for item in found), found
    assert {item.split(":", 1)[0] for item in found} <= {kind, "line"}, found
    if kind == "explanation":
        assert (
            f"en:{text}: explanation topology differs — missing=['w015'] extra=[]"
            in language_packs.check_layer(core, layer, path_of(text, "en"))
        )
    if kind == "line":
        assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
    core.clear()
    core.update(originals[0])
    layer.clear()
    layer.update(originals[1])
    assert diagnostics(text, core, layer) == []
    assert language_packs.check_layer(core, layer, path_of(text, "en")) == []

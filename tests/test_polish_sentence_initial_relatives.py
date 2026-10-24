"""Polish conclusion captions follow the Polish prose sentence, not the Latin colon before them.

The Missal prints a colon before the conclusion relative (`…: Qui vivis …`, `…: Qui tecum
vivit …`). Where the continuous Polish prose ends the petition with a full stop and opens the
conclusion as its own sentence (`…. Który żyjesz …`, `…. Który z Tobą żyje …`), the caption takes
the capital `Który`; where the prose continues the sentence, it keeps the lowercase `który`.
"""

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
P = "proprium."

# Oration conclusions whose Polish prose opens the conclusion as a separate sentence.
SENTENCE_STARTS = (
    (P + "beatae-mariae-virginis-a-rosario-postcommunio", "s01", "w024"),
    (P + "beatae-mariae-virginis-a-rosario-secreta", "s01", "w028"),
    (P + "commemoratio-baptismatis-domini-collecta", "s01", "w022"),
    (P + "commemoratio-omnium-fidelium-defunctorum-missa-i-collecta", "s01", "w023"),
    (P + "commemoratio-omnium-fidelium-defunctorum-missa-i-postcommunio", "s01", "w023"),
    (P + "corporis-christi-collecta", "s01", "w030"),
    (P + "corporis-christi-postcommunio", "s01", "w019"),
    (P + "d-n-iesu-christi-regis-collecta", "s01", "w027"),
    (P + "d-n-iesu-christi-regis-postcommunio", "s01", "w022"),
    (P + "dominica-i-adventus-collecta", "s01", "w021"),
    (P + "dominica-ii-adventus-collecta", "s01", "w019"),
    (P + "dominica-iii-adventus-collecta", "s01", "w016"),
    (P + "dominica-iv-adventus-collecta", "s01", "w026"),
    (P + "dominica-infra-octavam-nativitatis-collecta", "s01", "w020"),
    (P + "dominica-xxii-post-pentecosten-postcommunio", "s01", "w021"),
    (P + "feria-v-in-cena-domini-collecta", "s01", "w043"),
    (P + "nativitas-domini-in-die-postcommunio", "s01", "w022"),
    (P + "nativitas-domini-in-nocte-collecta", "s01", "w026"),
    (P + "nativitas-domini-in-nocte-postcommunio", "s01", "w025"),
    (P + "nativitas-domini-in-nocte-secreta", "s01", "w027"),
    (P + "pretiosissimi-sanguinis-domini-nostri-iesu-christi-postcommunio", "s01", "w024"),
    (P + "sacratissimi-cordis-iesu-postcommunio", "s01", "w021"),
    (P + "sancta-familia-collecta", "s01", "w027"),
    (P + "sancta-familia-postcommunio", "s01", "w034"),
    (P + "sancti-ioseph-sponsi-beatae-mariae-virginis-collecta", "s01", "w019"),
    (P + "septem-dolorum-beatae-mariae-virginis-collecta", "s01", "w043"),
    (P + "septem-dolorum-beatae-mariae-virginis-postcommunio", "s01", "w023"),
    (P + "septem-dolorum-beatae-mariae-virginis-secreta", "s01", "w038"),
    (P + "vigilia-nativitatis-secreta", "s01", "w019"),
)
# The closing prayer of the Litany of the Holy Name already reads `Który` at its prose sentence
# start (familiar wording, pinned with the other initial capitals of the relative-caption suite).
SETTLED_CAPITALS = (("litaniae.sanctissimi-nominis-iesu", "s146", "w473"),)
# Conclusions that open their own segment while the Polish prose continues the sentence of the
# previous segment after a comma or a colon.
CONTINUATIONS = (
    ("orationes.agimus-tibi-gratias", "s03", "w010", ","),
    ("ordinarium.corpus-tuum", "s04", "w028", ":"),
)
CLAUSE = re.compile(r"(?<![\w])[Kk]tóry (?:żyjesz|z Tobą żyje)\b")
RELATIVE = {"pos": "pron", "case": "nom", "number": "sg", "gender": "m"}


def site_id(site):
    text, _, word = site[:3]
    return f"{text.removeprefix(P)}-{word}"


def document(text, language=None):
    prefix = ROOT if language is None else ROOT / "languages" / language
    path = prefix / "texts" / (text.replace(".", "/", 1) + ".json")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def documents():
    texts = {site[0] for site in (*SENTENCE_STARTS, *CONTINUATIONS)}
    return {text: (document(text), document(text, "pl")) for text in texts}


@pytest.fixture(scope="module")
def corpus():
    found = {}
    for path in sorted((ROOT / "languages" / "pl" / "texts").glob("*/*.json")):
        text = f"{path.parent.name}.{path.stem}"
        found[(text, None)] = document(text)
        found[(text, "pl")] = json.loads(path.read_text(encoding="utf-8"))
    return found


def conclusion_relative(core, segment_id, word_id):
    """The verse segment and index of a Latin conclusion relative `Qui` before vivis/tecum."""
    (segment,) = [segment for segment in core["segments"] if segment["id"] == segment_id]
    words = segment["words"]
    (index,) = [index for index, word in enumerate(words) if word["id"] == word_id]
    word = words[index]
    assert (word["form"], word["lemma"], word["morph"]) == ("Qui", "qui", RELATIVE)
    assert words[index + 1]["form"] in {"vivis", "tecum"}
    assert segment["type"] == "verse"
    return segment, index


def sentence_start_diagnostics(core, layer, segment_id, word_id):
    """Misses at a conclusion whose Polish prose opens a new sentence at the relative."""
    found = []
    where = f"{core['id']} {word_id}"
    segment, index = conclusion_relative(core, segment_id, word_id)
    if segment["words"][index - 1].get("post") != ":":
        found.append(f"latin colon: {where}")
    local = layer["segments"][segment_id]
    if any(word_id in group["words"] for group in local.get("alignments", [])):
        found.append(f"grouped caption: {where}")
    clauses = list(CLAUSE.finditer(local["translation"]))
    before = local["translation"][: clauses[0].start()].rstrip() if len(clauses) == 1 else ""
    if len(clauses) != 1 or not before.endswith(".") or clauses[0].group(0)[0] != "K":
        found.append(f"prose boundary: {where}")
    if layer["words"][word_id] != {"gloss": "Który"}:
        found.append(f"caption case: {where}")
    return found


def continuation_diagnostics(core, layer, segment_id, word_id, mark):
    """Misses at a segment-initial conclusion whose Polish prose continues the sentence."""
    found = []
    where = f"{core['id']} {word_id}"
    _, index = conclusion_relative(core, segment_id, word_id)
    position = [item["id"] for item in core["segments"]].index(segment_id)
    previous = core["segments"][position - 1]
    if index != 0 or previous.get("type") != "verse" or previous["words"][-1].get("post") != ":":
        found.append(f"latin opening: {where}")
    previous_prose = layer["segments"][previous["id"]]["translation"].rstrip()
    if not previous_prose.endswith(mark):
        found.append(f"previous prose: {where}")
    if not layer["segments"][segment_id]["translation"].startswith("który żyjesz i królujesz"):
        found.append(f"prose continuation: {where}")
    if layer["words"][word_id] != {"gloss": "który"}:
        found.append(f"caption case: {where}")
    return found


def conclusion_sites(core):
    """Mid-segment Latin conclusion relatives, one per verse segment."""
    for segment in core["segments"]:
        if segment.get("type") != "verse":
            continue
        words = segment.get("words") or []
        found = [
            index
            for index, word in enumerate(words[:-1])
            if word["lemma"] == "qui"
            and word["morph"].get("case") == "nom"
            and word["morph"].get("number") == "sg"
            and words[index + 1]["form"].lower() in {"vivis", "tecum"}
        ]
        if len(found) == 1 and found[0] > 0:
            yield segment["id"], words[found[0]]["id"]


def required_caption(layer, segment_id, word_id):
    """The caption case the Polish prose requires, or None where the prose renders the clause
    other than exactly once, or the caption is grouped or another word."""
    local = layer["segments"].get(segment_id) or {}
    if any(word_id in group["words"] for group in local.get("alignments", [])):
        return None
    if (layer["words"].get(word_id) or {}).get("gloss") not in {"który", "Który"}:
        return None
    clauses = list(CLAUSE.finditer(local.get("translation") or ""))
    if len(clauses) != 1:
        return None
    before = local["translation"][: clauses[0].start()].rstrip()
    return "Który" if before.endswith(".") else "który"


def conclusion_case(load, texts):
    """Every examined conclusion relative with its required caption, and the disagreements: a
    caption, or a prose clause, whose case differs from the prose sentence boundary."""
    examined, mismatches = [], []
    for text in texts:
        core, layer = load(text, None), load(text, "pl")
        for segment_id, word_id in conclusion_sites(core):
            required = required_caption(layer, segment_id, word_id)
            if required is None:
                continue
            examined.append((text, segment_id, word_id, required))
            clause = CLAUSE.search(layer["segments"][segment_id]["translation"])
            assert clause is not None
            if layer["words"][word_id]["gloss"] != required or clause.group(0)[0] != required[0]:
                mismatches.append((text, word_id))
    return examined, mismatches


def corpus_loader(corpus, replacements=None):
    replaced = replacements or {}

    def load(text, language):
        return replaced.get((text, language), corpus[(text, language)])

    return load


def corpus_texts(corpus):
    return sorted({text for text, _ in corpus})


def test_finite_inventory_is_complete_and_outside_the_familiar_core():
    sites = [site[:3] for site in (*SENTENCE_STARTS, *CONTINUATIONS)]
    assert (len(SENTENCE_STARTS), len(CONTINUATIONS), len(set(sites))) == (29, 2, 31)
    provenance = json.loads((ROOT / "languages/pl/translation-provenance.json").read_text())
    rows = {row["site"]: row for row in provenance["sites"]}
    for text, segment_id, _ in sites:
        assert rows[f"{text}.{segment_id}.pl"]["familiar_core"] is False


@pytest.mark.parametrize("site", SENTENCE_STARTS, ids=[site_id(site) for site in SENTENCE_STARTS])
def test_sentence_start_caption_takes_the_capital(documents, site):
    text, segment_id, word_id = site
    assert sentence_start_diagnostics(*documents[text], segment_id, word_id) == []


@pytest.mark.parametrize("site", CONTINUATIONS, ids=[site_id(site) for site in CONTINUATIONS])
def test_continuing_relative_keeps_the_lowercase(documents, site):
    text, segment_id, word_id, mark = site
    assert continuation_diagnostics(*documents[text], segment_id, word_id, mark) == []


def test_no_conclusion_caption_disagrees_with_its_prose_sentence(corpus):
    examined, mismatches = conclusion_case(corpus_loader(corpus), corpus_texts(corpus))
    assert mismatches == []
    assert len(examined) >= 326
    capitals = {site[:3] for site in examined if site[3] == "Który"}
    assert capitals == {*SENTENCE_STARTS, *SETTLED_CAPITALS}


def test_sentence_start_guard_rejects_a_lowercase_caption_and_restores(documents):
    text, segment_id, word_id = SENTENCE_STARTS[9]
    core, layer = documents[text]
    saved = deepcopy(layer)
    broken = deepcopy(layer)
    broken["words"][word_id]["gloss"] = "który"
    assert sentence_start_diagnostics(core, broken, segment_id, word_id) == [
        f"caption case: {text} {word_id}"
    ]
    assert sentence_start_diagnostics(core, layer, segment_id, word_id) == []
    assert layer == saved


def test_sentence_start_guard_rejects_a_continuing_prose_and_restores(documents):
    text, segment_id, word_id = SENTENCE_STARTS[15]
    core, layer = documents[text]
    saved = deepcopy(layer)
    broken = deepcopy(layer)
    prose = broken["segments"][segment_id]["translation"]
    assert prose.count(". Który z Tobą żyje ") == 1
    broken["segments"][segment_id]["translation"] = prose.replace(
        ". Który z Tobą żyje ", ", Który z Tobą żyje "
    )
    assert sentence_start_diagnostics(core, broken, segment_id, word_id) == [
        f"prose boundary: {text} {word_id}"
    ]
    assert sentence_start_diagnostics(core, layer, segment_id, word_id) == []
    assert layer == saved


def test_continuation_guard_rejects_a_capital_caption_and_restores(documents):
    text, segment_id, word_id, mark = CONTINUATIONS[0]
    core, layer = documents[text]
    saved = deepcopy(layer)
    broken = deepcopy(layer)
    broken["words"][word_id]["gloss"] = "Który"
    assert continuation_diagnostics(core, broken, segment_id, word_id, mark) == [
        f"caption case: {text} {word_id}"
    ]
    assert continuation_diagnostics(core, layer, segment_id, word_id, mark) == []
    assert layer == saved


def test_continuation_guard_rejects_a_closed_previous_sentence_and_restores(documents):
    text, segment_id, word_id, mark = CONTINUATIONS[1]
    core, layer = documents[text]
    saved = deepcopy(layer)
    broken = deepcopy(layer)
    previous = broken["segments"]["s03"]
    assert previous["translation"].endswith(mark)
    previous["translation"] = previous["translation"][: -len(mark)] + "."
    assert continuation_diagnostics(core, broken, segment_id, word_id, mark) == [
        f"previous prose: {text} {word_id}"
    ]
    assert continuation_diagnostics(core, layer, segment_id, word_id, mark) == []
    assert layer == saved


ROSARY = P + "beatae-mariae-virginis-a-rosario-postcommunio"
MARK_COLLECT = P + "sancti-marci-evangelistae-collecta"
CORPUS_MUTANTS = ("lowercase-at-sentence-start", "capital-in-continuation", "prose-continues")


@pytest.mark.parametrize("kind", CORPUS_MUTANTS)
def test_corpus_guard_rejects_each_disagreement_and_restores(corpus, kind):
    texts = corpus_texts(corpus)
    if kind == "lowercase-at-sentence-start":
        text, word_id = ROSARY, "w024"
        broken = deepcopy(corpus[(text, "pl")])
        assert broken["words"][word_id] == {"gloss": "Który"}
        broken["words"][word_id]["gloss"] = "który"
    elif kind == "capital-in-continuation":
        text, word_id = MARK_COLLECT, "w029"
        broken = deepcopy(corpus[(text, "pl")])
        assert broken["words"][word_id] == {"gloss": "który"}
        assert ", który z Tobą żyje " in broken["segments"]["s01"]["translation"]
        broken["words"][word_id]["gloss"] = "Który"
    else:
        text, word_id = ROSARY, "w024"
        broken = deepcopy(corpus[(text, "pl")])
        prose = broken["segments"]["s01"]["translation"]
        assert prose.count(". Który żyjesz ") == 1
        broken["segments"]["s01"]["translation"] = prose.replace(
            ". Który żyjesz ", ", który żyjesz "
        )
    saved = deepcopy(corpus[(text, "pl")])
    _, mismatches = conclusion_case(corpus_loader(corpus, {(text, "pl"): broken}), texts)
    assert mismatches == [(text, word_id)]
    assert conclusion_case(corpus_loader(corpus), texts)[1] == []
    assert corpus[(text, "pl")] == saved

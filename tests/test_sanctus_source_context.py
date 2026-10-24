"""Bounded Sanctus source identities and separately reviewed rubric narratives."""

import copy
import json
from pathlib import Path

import pytest

from build_reader import store
from checks import prose
from checks.lint import lint_gloss

CORPUS = Path(__file__).resolve().parent.parent
TEXT = "ordinarium.sanctus"
MR = "edition.missale-romanum.1962-typica"
DMS = "edition.sacra-rituum-congregatio.de-musica-sacra.1958-aas50"
DMS_ITEM = "item.sacra-rituum-congregatio.de-musica-sacra.1958-aas50.vatican"
MR_USES = {
    "use.ordinarium.sanctus.hands-rubric.mr1962": ("p. 225", "n304"),
    "use.ordinarium.sanctus.recitation-gestures.mr1962": ("p. LIV", "n59"),
    "use.ordinarium.sanctus.recitation-canon.mr1962": ("p. LV", "n60"),
    "use.ordinarium.sanctus.canon-boundary.mr1962": ("p. XXXIII", "n38"),
    "use.ordinarium.sanctus.recitation-voice.mr1962": ("p. XXXIV", "n39"),
}
DMS_USES = {
    "sung-participation": ("official_liturgical_context", "pp. 639–640", "25 b and 26"),
    "chant-timing": ("rubric_control", "p. 641", "27 d–f"),
    "low-recitation": ("official_liturgical_context", "pp. 642–643", "31, introduction and c"),
}
NARRATIVES = {
    "pl": (
        "Prefacja dobiega końca. Kapłan składa ręce przed piersią i pochyla się, "
        "odmawiając Sanctus. We Mszy cichej mówi je głosem słyszalnym, a "
        "usługujący dzwoni. We Mszy śpiewanej kapłan odmawia ten sam tekst po "
        "cichu, podczas gdy schola śpiewa, a wierni mogą dołączyć. Przy słowach "
        "„Benedíctus qui venit in nómine Dómini” kapłan prostuje się i czyni "
        "znak krzyża od czoła do piersi. Po zakończeniu własnej recytacji "
        "rozpoczyna Kanon, odmawiany po cichu poza kilkoma zdaniami mówionymi "
        "głośno. Nie czeka na zakończenie śpiewu. Gregoriańskie Sanctus i "
        "Benedictus śpiewa się bez przerwy. Przy innych opracowaniach muzycznych "
        "Benedictus następuje po konsekracji. Podczas konsekracji śpiew ustaje."
    ),
    "en": (
        "The Preface comes to its end. The priest joins his hands before his "
        "breast and bows as he recites the Sanctus. At low Mass he says it "
        "audibly while the server rings the bell. At sung Mass the priest "
        "recites the same text quietly while the choir sings. The faithful may "
        "join the singing. At the words “Benedíctus qui venit in nómine Dómini” "
        "the priest straightens up and signs himself with the cross from "
        "forehead to breast. After completing his own recitation he begins the "
        "Canon, said silently apart from a few sentences spoken aloud. The priest "
        "does not wait for the choir to finish. The Gregorian Sanctus and Benedictus "
        "are sung continuously. With other musical settings the Benedictus "
        "follows the Consecration. Singing ceases during the Consecration."
    ),
}


def read_graph():
    return json.loads((CORPUS / "bibliography/graph.json").read_text(encoding="utf-8"))


def one(graph, array, identity):
    rows = [row for row in graph[array] if row["id"] == identity]
    assert len(rows) == 1
    return rows[0]


def assert_context(graph):
    primary = one(graph, "uses", "use.ordinarium.sanctus.mr1962")
    assert primary["role"] == "direct_approved_print"
    assert primary["edition"] == MR
    assert primary["locator"]["printed"] == "p. 286"
    assert "n365" in primary["locator"]["scan"]
    assert one(graph, "editions", MR)["authority"] == "approved_ecclesiastical_edition"
    witness = one(graph, "witnesses", "witness.ordinarium.sanctus.mr1962")
    assert witness["use"] == primary["id"]
    assert witness["coverage"] == {
        "kind": "segments",
        "segments": ["s02", "s03", "s04", "s05", "s06"],
    }
    assert witness["source_dependencies"] == {"uses": sorted(MR_USES), "raw_binding": None}
    for identity, (printed, scan) in MR_USES.items():
        use = one(graph, "uses", identity)
        assert use["edition"] == MR and use["role"] == "rubric_control"
        assert use["address"]["text"] == TEXT
        assert use["locator"]["printed"] == printed
        assert scan in use["locator"]["scan"]
        assert one(graph, "digital_items", use["digital_item"])["edition"] == MR
    edition = one(graph, "editions", DMS)
    assert edition["authority"] == "official_document"
    assert (edition["year"], edition["volume"]) == ("1958", "50")
    assert one(graph, "works", edition["work"])["responsible"] == "Sacra Rituum Congregatio"
    item = one(graph, "digital_items", DMS_ITEM)
    assert item["edition"] == DMS and item["kind"] == "scan"
    assert len(item["sha256"]) == 64
    for suffix, (role, printed, section) in DMS_USES.items():
        use = one(graph, "uses", f"use.ordinarium.sanctus.{suffix}.dms1958")
        assert use["edition"] == DMS and use["digital_item"] == DMS_ITEM
        assert use["role"] == role
        assert use["address"] == {"kind": "text", "text": TEXT}
        assert use["locator"]["printed"] == printed
        assert use["locator"]["section"].endswith(section)
        assert use["evidence_sha256"] == item["sha256"]


def test_actual_bounded_context_keeps_missal_and_instruction_distinct():
    assert_context(read_graph())


@pytest.mark.parametrize(
    "mutation",
    [
        "role",
        "missing-mr",
        "cross-edition",
        "missing-timing",
        "page",
        "digest",
        "item-edition",
        "authority",
        "responsible",
    ],
)
def test_context_fixture_rejects_dropped_or_misidentified_support(mutation):
    graph = copy.deepcopy(read_graph())
    witness = one(graph, "witnesses", "witness.ordinarium.sanctus.mr1962")
    timing = one(graph, "uses", "use.ordinarium.sanctus.chant-timing.dms1958")
    if mutation == "role":
        one(graph, "uses", "use.ordinarium.sanctus.mr1962")["role"] = "official_text"
    elif mutation == "missing-mr":
        witness["source_dependencies"]["uses"].pop()
    elif mutation == "cross-edition":
        witness["source_dependencies"]["uses"].append(timing["id"])
    elif mutation == "missing-timing":
        graph["uses"].remove(timing)
    elif mutation == "page":
        timing["locator"]["printed"] = "p. 639"
    elif mutation == "digest":
        timing["evidence_sha256"] = "0" * 64
    elif mutation == "item-edition":
        one(graph, "digital_items", DMS_ITEM)["edition"] = MR
    elif mutation == "authority":
        one(graph, "editions", DMS)["authority"] = "secondary_study"
    else:
        work = one(graph, "editions", DMS)["work"]
        one(graph, "works", work)["responsible"] = "Sacra Congregatio Consistorialis"
    with pytest.raises(AssertionError):
        assert_context(graph)


def narrative(language):
    path = CORPUS / f"languages/{language}/texts/ordinarium/sanctus.json"
    return json.loads(path.read_text(encoding="utf-8"))["segments"]["s01"]["narrative"]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_each_complete_narrative_retains_both_actions_and_timing(language):
    assert narrative(language) == NARRATIVES[language]


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("mutation", ["voice", "universal", "wait", "timing", "consecration"])
def test_narrative_fixture_rejects_each_escaped_ritual_class(language, mutation):
    fragments = {
        "pl": {
            "voice": ("ten sam tekst po cichu", "ten sam tekst na głos"),
            "universal": ("wierni mogą dołączyć", "wszyscy wierni zawsze śpiewają"),
            "wait": ("Nie czeka na zakończenie śpiewu", "Czeka na zakończenie śpiewu"),
            "timing": ("Benedictus następuje po konsekracji", "Benedictus poprzedza konsekrację"),
            "consecration": ("Podczas konsekracji śpiew ustaje", "Podczas konsekracji śpiew trwa"),
        },
        "en": {
            "voice": ("recites the same text quietly", "recites the same text aloud"),
            "universal": (
                "The faithful may join the singing",
                "Every faithful person always sings",
            ),
            "wait": (
                "The priest does not wait for the choir to finish",
                "The priest waits for the choir to finish",
            ),
            "timing": (
                "Benedictus follows the Consecration",
                "Benedictus precedes the Consecration",
            ),
            "consecration": (
                "Singing ceases during the Consecration",
                "Singing continues during the Consecration",
            ),
        },
    }
    before, after = fragments[language][mutation]
    original = narrative(language)
    assert original.count(before) == 1
    with pytest.raises(AssertionError):
        assert original.replace(before, after) == NARRATIVES[language]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_actual_sanctus_language_passes_the_own_prose_contract(language):
    path = CORPUS / f"languages/{language}/texts/ordinarium/sanctus.json"
    layer = json.loads(path.read_text(encoding="utf-8"))
    assert prose.check(layer) == []


@pytest.mark.parametrize("language", ["pl", "en"])
def test_own_prose_guard_rejects_a_narrative_semicolon(language):
    path = CORPUS / f"languages/{language}/texts/ordinarium/sanctus.json"
    layer = json.loads(path.read_text(encoding="utf-8"))
    assert prose.check(layer) == []
    text = layer["segments"]["s01"]["narrative"]
    assert ". " in text
    layer["segments"]["s01"]["narrative"] = text.replace(". ", "; ", 1)
    assert any(
        "uses a semicolon" in error and f".narrative.{language}" in error
        for error in prose.check(layer)
    )


def test_english_narrative_names_the_actor_under_the_actual_lint_contract():
    core, layers = store.load(CORPUS, TEXT)
    layer = layers["en"]
    assert lint_gloss(layer, core) == []
    before = "The priest does not wait for the choir to finish."
    after = "He does not wait for the choir to finish."
    text = layer["segments"]["s01"]["narrative"]
    assert text.count(before) == 1
    broken = copy.deepcopy(layer)
    broken["segments"]["s01"]["narrative"] = text.replace(before, after)
    assert lint_gloss(broken, core) == [
        "en:s01: narrative opens with a pronoun "
        "('He does not wait for the choir to finish') — name the priest"
    ]
    assert lint_gloss(layer, core) == []

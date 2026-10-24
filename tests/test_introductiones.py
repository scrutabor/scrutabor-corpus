"""The Ordo introduction library and its reader resource.

Units address whole owner segments in stored order and read, never copy, their owners' base
delivery and participation; each event carries the delivery of its own occurrences; the reader
resource is restated from the stored files without its producer. Every negative control is a
real mutation with its owned diagnostic, followed by restoration of the healthy state. The
reading announcements and their bindings have their own module
(tests/test_reading_announcement_bindings.py).
"""

import copy
import hashlib
import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from build_reader import bibliography, emit, store
from build_reader import introductiones as reader
from checks import introductiones as checker
from checks.delivery import check_doc as check_delivery
from checks.participation import check_doc as check_participation

CORPUS = Path(__file__).resolve().parent.parent
LIBRARY = "ordo/introductiones.json"
DIALOGUE = "ordinarium.praefatio-dialogus"
AUFER = "ordinarium.aufer-a-nobis"
LAST_GOSPEL = "ordinarium.evangelium-ultimum"
OWNERS = (AUFER, LAST_GOSPEL, DIALOGUE)
FORMULAS = json.loads(
    (CORPUS / "tests/fixtures/reading-announcement-formulas.json").read_text(encoding="utf-8")
)["formulas"]
ANNOUNCEMENT_TEXTS = tuple(formula["text"] for formula in FORMULAS)
UNITS = {
    "invitatio-oremus": ("invitation", AUFER, "s02", ["w001"]),
    "responsio-gloria-tibi": ("gospel-response", LAST_GOSPEL, "s06", ["w012", "w013", "w014"]),
    "responsio-salutationis": ("response", DIALOGUE, "s03", ["w003", "w004", "w005", "w006"]),
    "salutatio": ("greeting", DIALOGUE, "s02", ["w001", "w002"]),
    "initium-sancti-evangelii-secundum-ioannem": (
        "announcement",
        LAST_GOSPEL,
        "s05",
        ["w007", "w008", "w009", "w010", "w011"],
    ),
    **{
        formula["text"].split(".", 1)[1]: (
            "announcement",
            formula["text"],
            "s01",
            [f"w{number:03d}" for number in range(1, formula["words"] + 1)],
        )
        for formula in FORMULAS
    },
}
# Where the Missal prints each announcement unit in its role.
LESSON = "the Proper's heading over each bound reading"
ANNOUNCEMENT_SOURCES = {
    "lectio": LESSON,
    "sequentia": "RG 471; Ritus servandus VI, 2; " + LESSON,
    "initium": "RG 471; Ritus servandus VI, 2; " + LESSON,
    "passio": "RG 472; the Proper's heading over the bound reading",
}
INTRODUCTION = ["salutatio", "responsio-salutationis", "invitatio-oremus"]
SLOT = None
# The events in the order of the Mass; None marks the announcement slot.
EVENTS = {
    "collecta-introductio": ("collecta", "Ritus servandus V, 1", INTRODUCTION),
    "epistola-annuntiatio": (
        "epistola",
        "Ritus servandus VI, 1; the Proper's heading over each reading",
        [SLOT],
    ),
    "evangelium-salutatio": ("evangelium", "Ritus servandus VI, 2", INTRODUCTION[:2]),
    "evangelium-annuntiatio": (
        "evangelium",
        "RG 471; Ritus servandus VI, 2",
        [SLOT, "responsio-gloria-tibi"],
    ),
    "offertorium-introductio": ("offertorium", "Ritus servandus VII, 1", INTRODUCTION),
    "postcommunio-introductio": ("postcommunio", "Ritus servandus XI, 1 and V, 1", INTRODUCTION),
}
# The low-Mass citation of each occurrence: the Rubricae generales where they name the words
# (511 d, g, i), otherwise the Ritus servandus or the Ordo Missae that prints them.
LECTA_SOURCES = {
    "collecta-introductio": ["RG 511 d", "Ritus servandus V, 1", "RG 511 d"],
    "epistola-annuntiatio": ["RG 511 e; Ritus servandus VI, 1"],
    "evangelium-salutatio": ["Ritus servandus VI, 2", "Ritus servandus VI, 2"],
    "evangelium-annuntiatio": ["RG 511 e; Ritus servandus VI, 2", "Ritus servandus VI, 2"],
    "offertorium-introductio": [
        "RG 511 g",
        "Ordo Missae, before the Offertory antiphon",
        "RG 511 g",
    ],
    "postcommunio-introductio": [
        "RG 511 i",
        "Ritus servandus XI, 1 and V, 1",
        "Ritus servandus XI, 1 and V, 1",
    ],
}
SUNG = {
    "salutatio": ("sacerdos", "RG 513 a, 514"),
    "responsio-salutationis": ("schola", "DMS 16 b, 25 a, 26"),
    "invitatio-oremus": ("sacerdos", "RG 513 a, 514"),
    "responsio-gloria-tibi": ("schola", "DMS 16 b, 25 a, 26"),
}
LOW = {
    "salutatio": "sacerdos",
    "responsio-salutationis": "minister",
    "invitatio-oremus": "sacerdos",
    "responsio-gloria-tibi": "minister",
}
# The announcement slot of each event: its sung delivery, clara for the Epistle (RG 514).
SLOT_SUNG = {
    "epistola-annuntiatio": {"speaker": "sacerdos", "voice": "clara", "source": "RG 514"},
    "evangelium-annuntiatio": {
        "speaker": "sacerdos",
        "voice": "cantus",
        "source": "RG 473, 514; Ritus servandus VI, 5",
    },
}
COUNTS = {"units": 31, "events": 6, "occurrences": 14, "owner_texts": 29, "announcements": 205}
EMPTY = {"units": 0, "events": 0, "occurrences": 0, "owner_texts": 0, "announcements": 0}
RUBRICS = {
    "scope",
    "secret",
    "passion",
    "easter-vigil",
    "prayer-groups",
    "announcements",
    "sung-epistle",
    "references",
    "responses",
}


def library() -> dict[str, Any]:
    return json.loads((CORPUS / LIBRARY).read_text(encoding="utf-8"))


def unit_of(doc: dict[str, Any], identity: str) -> dict[str, Any]:
    return next(unit for unit in doc["units"] if unit["id"] == identity)


def event_of(doc: dict[str, Any], identity: str) -> dict[str, Any]:
    return next(event for event in doc["events"] if event["id"] == identity)


def segment_of(doc: dict[str, Any], segment_id: str) -> dict[str, Any]:
    return next(segment for segment in doc["segments"] if segment["id"] == segment_id)


# ---------------------------------------------------------------------------------------------
# The authored library
# ---------------------------------------------------------------------------------------------


def test_the_library_is_exact_and_counted():
    doc = library()
    assert set(doc) == {
        "introduction_schema",
        "units",
        "events",
        "passion",
        "announcements",
        "rubrics",
    }
    assert doc["introduction_schema"] == "2.0.0"
    assert checker.check(CORPUS) == ([], COUNTS)
    assert [unit["id"] for unit in doc["units"]] == sorted(UNITS)
    for unit in doc["units"]:
        role, text, segment, words = UNITS[unit["id"]]
        assert (unit["role"], unit["text"], unit["segment"]) == (role, text, segment)
        assert (unit["first"], unit["last"]) == (words[0], words[-1])
        if role == "announcement":
            head = unit["id"].split("-", 1)[0]
            expected = ANNOUNCEMENT_SOURCES[head]
            if unit["text"] == LAST_GOSPEL:
                expected = (
                    "RG 471; Ritus servandus VI, 2; the Proper's heading over the bound reading"
                )
            assert unit["source"] == expected
        else:
            assert unit["source"].startswith("Ritus servandus ")
    assert [event["id"] for event in doc["events"]] == list(EVENTS)
    for event in doc["events"]:
        before, source, units = EVENTS[event["id"]]
        assert (event["before"], event["source"]) == (before, source)
        assert [occurrence.get("unit") for occurrence in event["occurrences"]] == units
        for occurrence, lecta_source in zip(
            event["occurrences"], LECTA_SOURCES[event["id"]], strict=True
        ):
            if "slot" in occurrence:
                assert set(occurrence) == {"slot", "lecta", "cantu"}
                assert occurrence["slot"] == "announcement"
                assert occurrence["lecta"] == {
                    "speaker": "sacerdos",
                    "voice": "clara",
                    "source": lecta_source,
                }
                assert occurrence["cantu"] == SLOT_SUNG[event["id"]]
                continue
            speaker, sung_source = SUNG[occurrence["unit"]]
            assert occurrence["lecta"] == {
                "speaker": LOW[occurrence["unit"]],
                "voice": "clara",
                "source": lecta_source,
            }
            assert occurrence["cantu"] == {
                "speaker": speaker,
                "voice": "cantus",
                "source": sung_source,
            }
    assert set(doc["rubrics"]) == RUBRICS
    for key, citation in (
        ("scope", "VI, 5"),
        ("secret", "VII, 7"),
        ("passion", "8 a"),
        ("easter-vigil", "p. 212"),
        ("prayer-groups", "XI, 1"),
        ("announcements", "p. 223"),
        ("sung-epistle", "satius erit"),
        ("references", "p. 335"),
        ("responses", "p. 214"),
    ):
        assert citation in doc["rubrics"][key]
    assert (CORPUS / LIBRARY).read_text(encoding="utf-8") == (
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    )


@pytest.mark.parametrize("identity", sorted(UNITS))
def test_each_unit_is_a_whole_owner_segment_with_both_translations(identity):
    role, text, segment_id, words = UNITS[identity]
    unit = unit_of(library(), identity)
    owner = store.core(CORPUS, text)
    segment = segment_of(owner, segment_id)
    assert [word["id"] for word in segment["words"]] == words
    assert checker.unit_words(CORPUS, unit) == words
    speaker, _sung, answered = checker.ROLES[role]
    assert (segment["speaker"], segment["voice"]) == (speaker, "clara")
    assert bool(segment.get("participation")) is answered
    if answered:
        assert segment["participation"] == {
            "lecta": {"gradus": 1, "source": "DMS 31 a"},
            "cantu": {"gradus": 1, "source": "DMS 25 a"},
        }
    for language in ("pl", "en"):
        layer = store.raw_layer(CORPUS, language, text)
        assert layer["segments"][segment_id]["translation"].strip()
        aligned = {
            word
            for entry in layer["segments"].values()
            for group in entry.get("alignments") or []
            for word in group["words"]
        }
        if role != "announcement":
            assert not aligned & set(words)
            continue
        # An announcement's layer may group words of its own single verse, and only those.
        for stored_under, entry in layer["segments"].items():
            for group in entry.get("alignments") or []:
                if set(group["words"]) & set(words):
                    assert stored_under == segment_id and set(group["words"]) <= set(words)


def test_the_dialogue_override_is_inherited_and_the_aufer_oremus_delivery_is_authored():
    dialogue = store.core(CORPUS, DIALOGUE)
    assert segment_of(dialogue, "s02")["delivery"] == {
        "cantu": {"speaker": "sacerdos", "voice": "cantus"}
    }
    assert segment_of(dialogue, "s03")["delivery"] == {
        "cantu": {"speaker": "schola", "voice": "cantus"}
    }
    assert "delivery" not in segment_of(store.core(CORPUS, AUFER), "s02")
    assert "delivery" not in segment_of(store.core(CORPUS, LAST_GOSPEL), "s06")
    for event in library()["events"]:
        for occurrence in event["occurrences"]:
            sung = {key: occurrence["cantu"][key] for key in ("speaker", "voice")}
            if "slot" in occurrence:
                continue
            if occurrence["unit"] == "invitatio-oremus":
                assert sung == {"speaker": "sacerdos", "voice": "cantus"}
                assert occurrence["cantu"]["source"] == "RG 513 a, 514"
            elif occurrence["unit"] == "responsio-gloria-tibi":
                assert sung == {"speaker": "schola", "voice": "cantus"}
                assert occurrence["cantu"]["source"] == "DMS 16 b, 25 a, 26"
            else:
                segment = UNITS[occurrence["unit"]][2]
                assert sung == segment_of(dialogue, segment)["delivery"]["cantu"]


def test_the_library_writes_nothing_and_its_owners_keep_their_delivery():
    owners = OWNERS + ANNOUNCEMENT_TEXTS
    paths = [store.path_of(CORPUS, text) for text in owners] + [
        store.layer_path(CORPUS, language, text) for language in ("pl", "en") for text in owners
    ]
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    checker.check(CORPUS)
    reader.resource(CORPUS)
    reader.expected(CORPUS)
    assert before == {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    overrides = {text: check_delivery(store.core(CORPUS, text)) for text in owners}
    assert overrides == {
        DIALOGUE: ([], 6),
        AUFER: ([], 0),
        LAST_GOSPEL: ([], 0),
        **{text: ([], 0) for text in ANNOUNCEMENT_TEXTS},
    }
    for text in owners:
        assert check_participation(store.core(CORPUS, text))[0] == []


# ---------------------------------------------------------------------------------------------
# Owned negative controls on a small copy of the corpus
# ---------------------------------------------------------------------------------------------


def bound_readings() -> list[str]:
    """Every text a formulary names as its Epistle or Gospel."""
    return sorted(
        {
            component["text"]
            for formulary in store.formularies(CORPUS)
            for component in formulary["components"]
            if component["role"] in ("epistola", "evangelium")
        }
    )


def small_corpus(root: Path) -> Path:
    """The library, its owner texts, both published packages, the formularies and every bound
    reading with its printed witness, copied byte for byte."""
    corpus = root / "corpus"
    (corpus / "ordo").mkdir(parents=True)
    shutil.copyfile(CORPUS / LIBRARY, corpus / LIBRARY)
    shutil.copytree(CORPUS / "formularies", corpus / "formularies")
    for text in bound_readings():
        target = store.path_of(corpus, text)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(store.path_of(CORPUS, text), target)
        witness = corpus / "witnesses" / text / "mr.txt"
        witness.parent.mkdir(parents=True)
        shutil.copyfile(CORPUS / "witnesses" / text / "mr.txt", witness)
    for text in OWNERS + ANNOUNCEMENT_TEXTS:
        target = store.path_of(corpus, text)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(store.path_of(CORPUS, text), target)
        for language in ("pl", "en"):
            layer = store.layer_path(corpus, language, text)
            layer.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(store.layer_path(CORPUS, language, text), layer)
    for language in ("pl", "en"):
        shutil.copyfile(
            CORPUS / "languages" / language / "manifest.json",
            corpus / "languages" / language / "manifest.json",
        )
    return corpus


def target_path(corpus: Path, target: str) -> Path:
    """`library`, `owner:<text>`, `layer:<language>:<text>` or `manifest:<language>`."""
    kind, _, rest = target.partition(":")
    if kind == "library":
        return corpus / LIBRARY
    if kind == "owner":
        return store.path_of(corpus, rest)
    if kind == "layer":
        language, text = rest.split(":", 1)
        return store.layer_path(corpus, language, text)
    return corpus / "languages" / rest / "manifest.json"


def edit(path: Path, mutate: Callable[[Any], Any]) -> None:
    """Mutate the document in place; whatever the mutation returns is ignored."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    mutate(doc)
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


def unit_set(identity: str, key: str, value: Any) -> Callable[[Any], None]:
    return lambda doc: unit_of(doc, identity).__setitem__(key, value)


def event_set(identity: str, key: str, value: Any) -> Callable[[Any], None]:
    return lambda doc: event_of(doc, identity).__setitem__(key, value)


def delivery_set(event: str, index: int, form: str, key: str, value: Any) -> Callable:
    return lambda doc: event_of(doc, event)["occurrences"][index][form].__setitem__(key, value)


def owner_set(segment: str, key: str, value: Any) -> Callable[[Any], None]:
    def mutate(doc):
        if value is None:
            segment_of(doc, segment).pop(key)
        else:
            segment_of(doc, segment)[key] = value

    return mutate


def translation_set(segment: str, value: str) -> Callable[[Any], None]:
    return lambda doc: doc["segments"][segment].__setitem__("translation", value)


def alignment_add(segment: str, words: list[str]) -> Callable[[Any], None]:
    group = {"words": words, "anchor": words[0], "gloss": "x"}
    return lambda doc: doc["segments"][segment].setdefault("alignments", []).append(group)


def swap_occurrences(event: str) -> Callable[[Any], None]:
    def mutate(doc):
        sequence = event_of(doc, event)["occurrences"]
        sequence[0], sequence[1] = sequence[1], sequence[0]

    return mutate


# (case id, target, mutation, owned diagnostic fragment)
LIBRARY_CASES: list[tuple[str, str, Callable[[Any], Any], str]] = [
    ("partial-segment", "library", unit_set("salutatio", "last", "w001"), "whole segment"),
    ("foreign-endpoint", "library", unit_set("salutatio", "last", "w003"), "outside s02"),
    (
        "reversed-endpoints",
        "library",
        lambda d: unit_of(d, "responsio-salutationis").update(first="w006", last="w003"),
        "reversed in stored order",
    ),
    ("rubric-segment", "library", unit_set("salutatio", "segment", "s01"), "not a verse"),
    ("missing-segment", "library", unit_set("salutatio", "segment", "s99"), "no segment"),
    (
        "missing-owner",
        "library",
        unit_set("salutatio", "text", "ordinarium.dominus-vobiscum"),
        "does not exist",
    ),
    (
        "slash-owner",
        "library",
        unit_set("salutatio", "text", "ordinarium/praefatio-dialogus"),
        "not a dotted text id",
    ),
    ("unknown-role", "library", unit_set("salutatio", "role", "blessing"), "unknown role"),
    ("empty-unit-source", "library", unit_set("salutatio", "source", " "), "source citation"),
    (
        "duplicate-unit",
        "library",
        lambda d: d["units"].append(copy.deepcopy(d["units"][0])),
        "duplicate unit",
    ),
    ("unsorted-units", "library", lambda d: d["units"].reverse(), "units must be in identity"),
    ("extra-unit-field", "library", unit_set("salutatio", "words", ["w001"]), "exactly the fields"),
    ("wrong-role-for-owner", "library", unit_set("salutatio", "role", "response"), "owner's base"),
    (
        "occurrence-order",
        "library",
        swap_occurrences("collecta-introductio"),
        "a greeting stands here",
    ),
    (
        "dropped-invitation",
        "library",
        lambda d: event_of(d, "offertorium-introductio")["occurrences"].pop(),
        "exactly the ordered roles",
    ),
    (
        "added-gospel-invitation",
        "library",
        lambda d: event_of(d, "evangelium-salutatio")["occurrences"].append(
            copy.deepcopy(event_of(d, "collecta-introductio")["occurrences"][2])
        ),
        "exactly the ordered roles",
    ),
    (
        "unknown-unit",
        "library",
        lambda d: event_of(d, "collecta-introductio")["occurrences"][0].__setitem__(
            "unit", "pax-vobis"
        ),
        "names no valid unit",
    ),
    (
        "gloria-tibi-as-greeting-response",
        "library",
        lambda d: event_of(d, "evangelium-salutatio")["occurrences"][1].__setitem__(
            "unit", "responsio-gloria-tibi"
        ),
        "a response stands here, not the gospel-response",
    ),
    (
        "wrong-before",
        "library",
        event_set("collecta-introductio", "before", "epistola"),
        "precedes",
    ),
    (
        "unknown-event",
        "library",
        event_set("postcommunio-introductio", "id", "secreta-introductio"),
        "unknown event",
    ),
    (
        "missing-event",
        "library",
        lambda d: d["events"].pop(),
        "events missing: postcommunio-introductio",
    ),
    (
        "duplicate-event",
        "library",
        lambda d: d["events"].append(copy.deepcopy(d["events"][-1])),
        "duplicate event",
    ),
    (
        "unsorted-events",
        "library",
        lambda d: d["events"].reverse(),
        "events must be in the order of the Mass",
    ),
    (
        "empty-event-source",
        "library",
        event_set("offertorium-introductio", "source", ""),
        "source citation is empty",
    ),
    (
        "lecta-speaker-vocabulary",
        "library",
        delivery_set("collecta-introductio", 0, "lecta", "speaker", "populus"),
        "outside the closed vocabulary",
    ),
    (
        "lecta-voice-vocabulary",
        "library",
        delivery_set("collecta-introductio", 2, "lecta", "voice", "secreto"),
        "outside the closed vocabulary",
    ),
    (
        "cantu-voice-vocabulary",
        "library",
        delivery_set("offertorium-introductio", 0, "cantu", "voice", "clara"),
        "outside the closed vocabulary",
    ),
    (
        "cantu-omnes-vocabulary",
        "library",
        delivery_set("collecta-introductio", 1, "cantu", "speaker", "omnes"),
        "outside the closed vocabulary",
    ),
    (
        "response-sung-by-celebrant",
        "library",
        delivery_set("postcommunio-introductio", 1, "cantu", "speaker", "sacerdos"),
        "belongs to the schola",
    ),
    (
        "greeting-said-by-server",
        "library",
        delivery_set("evangelium-salutatio", 0, "lecta", "speaker", "minister"),
        "belongs to the sacerdos",
    ),
    (
        "oremus-sung-by-schola",
        "library",
        delivery_set("offertorium-introductio", 2, "cantu", "speaker", "schola"),
        "belongs to the sacerdos",
    ),
    (
        "delivery-without-source",
        "library",
        lambda d: event_of(d, "collecta-introductio")["occurrences"][0]["cantu"].pop("source"),
        "delivery needs exactly",
    ),
    (
        "delivery-empty-source",
        "library",
        delivery_set("collecta-introductio", 2, "lecta", "source", ""),
        "no source citation",
    ),
    ("missing-rubric", "library", lambda d: d["rubrics"].pop("secret"), "rubrics need exactly"),
    (
        "empty-rubric",
        "library",
        lambda d: d["rubrics"].__setitem__("passion", ""),
        "nonempty citation",
    ),
    (
        "extra-field",
        "library",
        lambda d: d.__setitem__("title", "Ordo"),
        "needs exactly the fields",
    ),
    (
        "schema",
        "library",
        lambda d: d.__setitem__("introduction_schema", "1.1.0"),
        "introduction_schema",
    ),
]

OWNER_CASES: list[tuple[str, str, Callable[[Any], Any], str]] = [
    (
        "aufer-oremus-secreto",
        f"owner:{AUFER}",
        owner_set("s02", "voice", "secreto"),
        "owner's base sacerdos/secreto",
    ),
    (
        "response-without-participation",
        f"owner:{DIALOGUE}",
        owner_set("s03", "participation", None),
        "needs its owner's participation",
    ),
    (
        "greeting-with-participation",
        f"owner:{DIALOGUE}",
        owner_set("s02", "participation", {"lecta": {"gradus": 1, "source": "DMS 31 a"}}),
        "carries participation",
    ),
    (
        "owner-override-differs",
        f"owner:{DIALOGUE}",
        owner_set("s02", "delivery", {"cantu": {"speaker": "schola", "voice": "cantus"}}),
        "differs from the owner's own override",
    ),
    (
        "owner-words-renumbered",
        f"owner:{DIALOGUE}",
        lambda d: segment_of(d, "s02")["words"][1].__setitem__("id", "w021"),
        "outside s02",
    ),
    (
        "empty-english-translation",
        f"layer:en:{DIALOGUE}",
        translation_set("s02", ""),
        "en has no translation of ordinarium.praefatio-dialogus s02",
    ),
    (
        "empty-polish-translation",
        f"layer:pl:{LAST_GOSPEL}",
        translation_set("s06", " "),
        "pl has no translation of ordinarium.evangelium-ultimum s06",
    ),
    (
        "unpublished-owner",
        "manifest:pl",
        lambda d: d["texts"].remove(AUFER),
        "must be published once in the pl package",
    ),
    (
        "foreign-layer",
        f"layer:en:{AUFER}",
        lambda d: d.__setitem__("text", DIALOGUE),
        "names another text",
    ),
    (
        "crossing-alignment",
        f"layer:pl:{DIALOGUE}",
        alignment_add("s03", ["w002", "w003"]),
        "pl alignment group crosses the boundary of s02",
    ),
    (
        "alignment-stored-elsewhere",
        f"layer:en:{DIALOGUE}",
        alignment_add("s04", ["w006", "w007"]),
        "en alignment group crosses the boundary of s03",
    ),
]


@pytest.mark.parametrize(
    "target,mutate,message",
    [case[1:] for case in LIBRARY_CASES + OWNER_CASES],
    ids=[case[0] for case in LIBRARY_CASES + OWNER_CASES],
)
def test_each_defect_fails_its_owned_diagnostic_and_restores(tmp_path, target, mutate, message):
    corpus = small_corpus(tmp_path)
    assert checker.check(corpus) == ([], COUNTS)
    path = target_path(corpus, target)
    healthy = path.read_bytes()
    edit(path, mutate)
    errors, _counts = checker.check(corpus)
    assert any(message in error for error in errors), errors
    assert all(error.startswith("introductiones: ") for error in errors)
    with pytest.raises(ValueError, match="invalid authored library"):
        checker.authored(corpus)
    path.write_bytes(healthy)
    assert checker.check(corpus) == ([], COUNTS)


def test_an_alignment_wholly_inside_the_unit_is_not_a_crossing(tmp_path):
    corpus = small_corpus(tmp_path)
    edit(target_path(corpus, f"layer:pl:{DIALOGUE}"), alignment_add("s03", ["w004", "w005"]))
    assert checker.check(corpus) == ([], COUNTS)


@pytest.mark.parametrize(
    "corrupt,message",
    [
        (
            lambda text: text.replace(
                '"role": "greeting"', '"role": "greeting", "role": "greeting"'
            ),
            "appears 2 times",
        ),
        (lambda text: text[:-3], "cannot be read"),
        (lambda text: "[]\n", "needs exactly the fields"),
    ],
    ids=["repeated-key", "truncated", "not-an-object"],
)
def test_the_file_itself_is_refused_when_it_is_not_one_clean_object(tmp_path, corrupt, message):
    corpus = small_corpus(tmp_path)
    path = corpus / LIBRARY
    healthy = path.read_text(encoding="utf-8")
    path.write_text(corrupt(healthy), encoding="utf-8")
    errors, counts = checker.check(corpus)
    assert any(message in error for error in errors), errors
    assert counts == EMPTY
    path.write_text(healthy, encoding="utf-8")
    assert checker.check(corpus) == ([], COUNTS)


def test_a_missing_library_is_an_error_and_not_an_empty_pass(tmp_path):
    corpus = small_corpus(tmp_path)
    (corpus / LIBRARY).unlink()
    assert checker.check(corpus)[0] == [f"introductiones: {LIBRARY} is missing"]
    with pytest.raises(ValueError, match="introductiones"):
        reader.input_bodies(corpus)


# ---------------------------------------------------------------------------------------------
# The reader resource
# ---------------------------------------------------------------------------------------------


def pinned_resource() -> dict[str, Any]:
    doc = library()
    return {
        "schema_version": "2.0.0",
        "units": [
            {
                "id": identity,
                "role": UNITS[identity][0],
                "text": UNITS[identity][1].replace(".", "/", 1),
                "segment": UNITS[identity][2],
                "words": UNITS[identity][3],
                "source": unit_of(doc, identity)["source"],
            }
            for identity in sorted(UNITS)
        ],
        "events": doc["events"],
        "passion": doc["passion"],
        "announcements": [
            {
                "reading": binding["reading"].replace(".", "/", 1),
                "unit": binding["unit"],
                "reference": binding["reference_as_printed"],
                "pericope": binding["pericope"],
                **{
                    flag: True
                    for flag in ("book_supplied", "misprint")
                    if flag in binding and (flag != "misprint" or "uncertain" not in binding)
                },
                **({"reference_uncertain": True} if "uncertain" in binding else {}),
            }
            for binding in doc["announcements"]
        ],
    }


def test_the_restatement_calls_neither_producer_nor_checker(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("the restatement must stand on the stored files alone")

    for module, name in (
        (reader, "resource"),
        (checker, "check"),
        (checker, "authored"),
        (checker, "unit_words"),
        (checker, "owner_segment"),
    ):
        monkeypatch.setattr(module, name, forbidden)
    assert reader.expected(CORPUS) == pinned_resource()


def test_the_producer_equals_the_pinned_resource():
    table = reader.resource(CORPUS)
    assert table == pinned_resource()
    text = reader.artifact_json(table)
    for text_id in OWNERS:
        for segment in store.core(CORPUS, text_id)["segments"]:
            for word in segment.get("words") or []:
                assert f'"{word["form"]}"' not in text, "no owner word is copied"
    # A pericope names its book with the Proper's abbreviation, which for Judith is the word.
    bookless = reader.artifact_json(
        {
            **table,
            "announcements": [
                {**row, "pericope": {**row["pericope"], "book": ""}}
                for row in table["announcements"]
            ],
        }
    )
    for text_id in ANNOUNCEMENT_TEXTS:
        core = store.core(CORPUS, text_id)
        heading = " ".join(word["form"] for word in core["segments"][0]["words"])
        assert heading not in text, "no announcement is copied"
        for word in core["segments"][0]["words"]:
            assert f'"{word["form"]}"' not in bookless, "no owner word is copied"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda t: t.__setitem__("schema_version", "1.1.0"),
        lambda t: t.__setitem__("title", "Ordo"),
        lambda t: t["units"][0].__setitem__("role", "blessing"),
        lambda t: t["units"][0].__setitem__("text", "ordinarium.aufer-a-nobis"),
        lambda t: t["units"][0].__setitem__("segment", "2"),
        lambda t: t["units"][1].__setitem__("words", []),
        lambda t: t["units"][1].__setitem__("words", ["w012", "w012"]),
        lambda t: t["units"][1].__setitem__("source", ""),
        lambda t: t["units"].append(copy.deepcopy(t["units"][0])),
        lambda t: t["units"].reverse(),
        lambda t: t["events"][0]["occurrences"][0].__setitem__("unit", "pax-vobis"),
        lambda t: t["events"][0]["occurrences"][0]["lecta"].__setitem__("voice", "cantus"),
        lambda t: t["events"][0]["occurrences"][1]["cantu"].__setitem__("speaker", "omnes"),
        lambda t: t["events"][0]["occurrences"][1]["cantu"].pop("source"),
        lambda t: t["events"][0].__setitem__("occurrences", []),
        lambda t: t["events"][0].__setitem__("source", " "),
        lambda t: t["events"].reverse(),
        lambda t: t.pop("events"),
    ],
    ids=[
        "schema",
        "extra-field",
        "unknown-role",
        "dotted-address",
        "bad-segment",
        "no-words",
        "repeated-word",
        "empty-unit-source",
        "duplicate-unit",
        "unsorted-units",
        "unknown-unit",
        "lecta-voice",
        "cantu-speaker",
        "delivery-fields",
        "empty-event",
        "empty-event-source",
        "unsorted-events",
        "no-events",
    ],
)
def test_the_emitted_contract_rejects_malformed_resources(mutation):
    table = reader.resource(CORPUS)
    broken = copy.deepcopy(table)
    mutation(broken)
    with pytest.raises(ValueError, match="introductiones: "):
        reader.validate(broken)
    reader.validate(table)


@pytest.fixture(scope="module")
def edition(tmp_path_factory):
    out = tmp_path_factory.mktemp("introductiones-reader")
    emit.emit(CORPUS, out)
    graph, languages = bibliography.load(CORPUS)
    projection = bibliography.ReaderCitationProjection(CORPUS, graph, languages)
    return out, graph, projection


@pytest.fixture
def change(edition):
    """Modify real emitted files, and restore each exact original byte string."""
    out, _, _ = edition
    saved: dict[Path, bytes] = {}

    def mutate(name: str, value: Any) -> None:
        path = out / name
        saved.setdefault(path, path.read_bytes())
        if value is None:
            path.unlink()
        else:
            path.write_text(
                value if isinstance(value, str) else json.dumps(value), encoding="utf-8"
            )

    yield mutate
    for path, data in saved.items():
        path.write_bytes(data)


def read(edition, name):
    return json.loads((edition[0] / name).read_text(encoding="utf-8"))


def artifact_errors(edition):
    out, graph, projection = edition
    return emit.verify_edition_artifacts(CORPUS, out, graph, projection)


def test_the_edition_declares_the_resource_and_reads_it_back_equal(edition):
    out = edition[0]
    manifest = read(edition, "manifest.json")
    assert manifest["schema_version"] == emit.SCHEMA == "6.5.0"
    assert manifest["base"]["introductiones"] == "introductiones.json"
    emitted = (out / "introductiones.json").read_text(encoding="utf-8")
    assert emitted == reader.artifact_json(reader.resource(CORPUS))
    assert json.loads(emitted) == reader.expected(CORPUS) == pinned_resource()
    for language in ("pl", "en"):
        package = read(edition, f"languages/{language}/manifest.json")
        assert "introductiones" not in package
    assert reader.verify(CORPUS, out, manifest, emit.SCHEMA) == []
    assert artifact_errors(edition) == []


def _without_segment(edition, name, segment):
    artifact = read(edition, name)
    artifact["seg"] = [row for row in artifact["seg"] if row["id"] != segment]
    return artifact


def _dropped_cell(edition, name, segment):
    artifact = read(edition, name)
    row = next(row for row in artifact["seg"] if row["id"] == segment)
    row["w"] = row["w"][:-1]
    return artifact


def _emptied_translation(edition, name, segment):
    artifact = read(edition, name)
    next(row for row in artifact["seg"] if row["id"] == segment)["tr"] = ""
    return artifact


def _undeclared(edition, name, text):
    package = read(edition, name)
    package["texts"] = [entry for entry in package["texts"] if entry["id"] != text]
    return package


def _rebased(edition, value):
    manifest = read(edition, "manifest.json")
    if value is None:
        del manifest["base"]["introductiones"]
    else:
        manifest["base"]["introductiones"] = value
    return manifest


def _resource_with(edition, mutate):
    table = read(edition, "introductiones.json")
    mutate(table)
    return table


def _lost_reference_uncertainty(table, promote=False):
    row = next(
        row
        for row in table["announcements"]
        if row["reading"] == "proprium/dominica-in-albis-evangelium"
    )
    row.pop("reference_uncertain")
    if promote:
        row["misprint"] = True


DIALOGUE_PATH = "texts/ordinarium/praefatio-dialogus.json"
EMITTED_FAULTS: dict[str, Callable[[Any], tuple[str, Any]]] = {
    "no-file": lambda e: ("introductiones.json", None),
    "malformed": lambda e: ("introductiones.json", "{"),
    "null": lambda e: ("introductiones.json", "null"),
    "reordered-words": lambda e: (
        "introductiones.json",
        _resource_with(e, lambda t: t["units"][3]["words"].reverse()),
    ),
    "foreign-segment": lambda e: (
        "introductiones.json",
        _resource_with(e, lambda t: t["units"][3].__setitem__("segment", "s04")),
    ),
    "dropped-event": lambda e: (
        "introductiones.json",
        _resource_with(e, lambda t: t["events"].pop()),
    ),
    "authored-source-changed": lambda e: (
        "introductiones.json",
        _resource_with(
            e, lambda t: t["events"][4]["occurrences"][2]["cantu"].__setitem__("source", "RG 511 g")
        ),
    ),
    "invalid-voice": lambda e: (
        "introductiones.json",
        _resource_with(
            e, lambda t: t["events"][0]["occurrences"][0]["lecta"].__setitem__("voice", "secreto")
        ),
    ),
    "undeclared-base": lambda e: ("manifest.json", _rebased(e, None)),
    "wrong-base": lambda e: ("manifest.json", _rebased(e, "commemorationes.json")),
    "owner-segment-missing": lambda e: (DIALOGUE_PATH, _without_segment(e, DIALOGUE_PATH, "s02")),
    "owner-words-differ": lambda e: (DIALOGUE_PATH, _dropped_cell(e, DIALOGUE_PATH, "s03")),
    "owner-undeclared": lambda e: (
        "manifest.json",
        _undeclared(e, "manifest.json", AUFER),
    ),
    "language-owner-undeclared": lambda e: (
        "languages/en/manifest.json",
        _undeclared(e, "languages/en/manifest.json", LAST_GOSPEL),
    ),
    "language-translation-empty": lambda e: (
        f"languages/pl/{DIALOGUE_PATH}",
        _emptied_translation(e, f"languages/pl/{DIALOGUE_PATH}", "s03"),
    ),
    "language-package-version": lambda e: (
        "languages/pl/manifest.json",
        {**read(e, "languages/pl/manifest.json"), "schema_version": "6.0.0"},
    ),
    "lost-reference-uncertainty": lambda e: (
        "introductiones.json",
        _resource_with(e, lambda t: _lost_reference_uncertainty(t)),
    ),
    "uncertainty-promoted-to-misprint": lambda e: (
        "introductiones.json",
        _resource_with(e, lambda t: _lost_reference_uncertainty(t, promote=True)),
    ),
    "dropped-announcement": lambda e: (
        "introductiones.json",
        _resource_with(e, lambda t: t["announcements"].pop()),
    ),
    "passion-source-changed": lambda e: (
        "introductiones.json",
        _resource_with(e, lambda t: t["passion"].__setitem__("source", "RG 471")),
    ),
    "announced-reading-undeclared": lambda e: (
        "manifest.json",
        _undeclared(e, "manifest.json", "proprium.dominica-i-adventus-epistola"),
    ),
}


@pytest.mark.parametrize("fault", sorted(EMITTED_FAULTS))
def test_each_emitted_fault_is_caught_by_the_full_artifact_gate(edition, change, fault):
    name, value = EMITTED_FAULTS[fault](edition)
    change(name, value)
    errors = artifact_errors(edition)
    assert any(message.startswith("introductiones:") for message in errors), (fault, errors)


def test_a_wrong_producer_cannot_supply_its_own_expectation(tmp_path, monkeypatch):
    honest = reader.resource(CORPUS)
    wrong = copy.deepcopy(honest)
    wrong["units"][3]["words"] = list(reversed(wrong["units"][3]["words"]))
    reader.validate(wrong)
    monkeypatch.setattr(reader, "resource", lambda _corpus: wrong)
    out = tmp_path / "wrong-producer"
    emit.emit(CORPUS, out)
    assert json.loads((out / "introductiones.json").read_text(encoding="utf-8")) == wrong
    graph, languages = bibliography.load(CORPUS)
    projection = bibliography.ReaderCitationProjection(CORPUS, graph, languages)
    errors = emit.verify_edition_artifacts(CORPUS, out, graph, projection)
    assert "introductiones: resource differs from the independent restatement" in errors

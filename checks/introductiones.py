"""Ordo introductions: the reusable units that open a part of the Mass, and the events of
the priest-led Ordo that are made of them.

The Ritus servandus prints the greeting, its answer and the invitation before the Collect
(V, 1), the Offertory (VII, 1) and the prayers after Communion (XI, 1, in the manner of V, 1),
and the greeting and answer before the Gospel (VI, 2). They are words the reader follows, not
headings. Those words already stand, with stable word ids and their Polish and English layers,
as complete verse segments of other Ordinary texts. A unit addresses one such segment whole,
by its owner text, segment and first and last word in stored order, and never copies a word.

An event is the ordered sequence of units before one Mass part. Every occurrence of a unit in
an event carries its own delivery in both forms of Mass, cited where it is authored: the
Rubricae generales (511 for the low Mass, 513 a and 514 for the celebrant at a sung Mass) and
the Ritus servandus, and De musica sacra 16 b, 25 a and 26 for the answer the schola and the
faithful sing. An occurrence takes nothing from the place where its owner is said: the
invitation addressed in Aufer a nobis is said there at the foot of the altar, and its delivery
before the Collect is authored for the Collect.

The owner's base speaker, voice and participation are read here and held against the unit's
role, never copied into the library. Where the owner itself carries a sung override, as the
Preface dialogue does, the occurrence must agree with it. Which events a given date or Mass
uses (the Easter Vigil, the Secret) is not decided here; `rubrics` records those rules with
their citations.

The Proper prints an announcement over every reading: a lesson heading over the Epistle and,
after the greeting and its answer, the Gospel's Sequéntia or Inítium sancti Evangélii, answered
Glória tibi, Dómine (RG 471; Ritus servandus VI, 1-2). Each formula is an Ordinary text of its
own, and a unit with the role `announcement`. In an event the announcement is a slot, filled
for each reading from `announcements`: one binding per reading the formularies name as an
Epistle or a Gospel, with the leaf and page of the printed heading, the print where it differs
from the formula, and the printed reference beside a normalised pericope. The Passion takes its
announcement alone (RG 472), a rule recorded in `passion`. An announcement sung at a sung Mass
must be sung as its reading is: the Gospel is sung, while the celebrant at a Missa cantata
better reads the Epistle without chant (RG 514), so its announcement stays clara.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from build_reader import store
from checks.formularies import ROLES as MASS_ROLES
from checks.lint import duplicate_keys

SCHEMA = "2.0.0"
PATH = "ordo/introductiones.json"
KEYS = {"introduction_schema", "units", "events", "passion", "announcements", "rubrics"}
UNIT_KEYS = {"id", "role", "text", "segment", "first", "last", "source"}
EVENT_KEYS = {"id", "before", "source", "occurrences"}
OCCURRENCE_KEYS = {"unit", "lecta", "cantu"}
SLOT_KEYS = {"slot", "lecta", "cantu"}
DELIVERY_KEYS = {"speaker", "voice", "source"}
PASSION_KEYS = {"units", "omitted_events", "omitted_units", "lecta", "cantu", "source"}
BINDING_KEYS = {"reading", "unit", "leaf", "page", "reference_as_printed", "pericope"}
BINDING_OPTIONAL = {"as_printed", "book_supplied", "misprint", "comparator", "uncertain"}
RUBRIC_KEYS = {
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
IDENTITY = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
TEXT_IDENTITY = re.compile(r"[a-z]+\.[a-z0-9]+(?:-[a-z0-9]+)*\Z")

# The two forms of Mass, and the closed delivery vocabulary of each: the low Mass is said
# aloud by the celebrant and the server, the sung Mass is sung by the celebrant and answered
# by the schola, with the faithful's own part in the owner's participation.
FORMS = ("lecta", "cantu")
VOICES = {"lecta": "clara", "cantu": "cantus"}
SPEAKERS = {"lecta": ("sacerdos", "minister"), "cantu": ("sacerdos", "schola")}

# A role fixes who says the unit in each form and whether its owner carries the faithful's
# participation: the celebrant's greeting and invitation carry none, an answer carries the
# DMS 31 a and 25 a grades that its own words earn wherever they stand.
ROLES: dict[str, tuple[str, str, bool]] = {
    "greeting": ("sacerdos", "sacerdos", False),
    "response": ("minister", "schola", True),
    "invitation": ("sacerdos", "sacerdos", False),
    "gospel-response": ("minister", "schola", True),
    "announcement": ("sacerdos", "sacerdos", False),
}

# The one extension of the closed vocabulary: an announcement may stay clara at a sung Mass.
# RG 514 has the celebrant of a Missa cantata better read the Epistle without chant (satius
# erit) when no lector sings it, and an announcement is delivered as its reading is.
SUNG_VOICES: dict[str, tuple[str, ...]] = {"announcement": ("cantus", "clara")}

# The class of an announcement is the lemma of its owner's first word, read from the owner,
# and fixes the Mass part it can announce: a lesson heading the Epistle, the Gospel's
# continuation or beginning, and the Passion.
ANNOUNCEMENT_CLASSES = {
    "lectio": "epistola",
    "sequentia": "evangelium",
    "initium": "evangelium",
    "passio": "evangelium",
}

# The events of the priest-led Ordo in the order of the Mass: the part each one precedes and
# the roles of its occurrences in order. Before the Gospel the greeting and its answer come
# first, then the announcement and Glória tibi (RG 471). An announcement is always a slot.
EVENTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "collecta-introductio": ("collecta", ("greeting", "response", "invitation")),
    "epistola-annuntiatio": ("epistola", ("announcement",)),
    "evangelium-salutatio": ("evangelium", ("greeting", "response")),
    "evangelium-annuntiatio": ("evangelium", ("announcement", "gospel-response")),
    "offertorium-introductio": ("offertorium", ("greeting", "response", "invitation")),
    "postcommunio-introductio": ("postcommunio", ("greeting", "response", "invitation")),
}
assert all(before in MASS_ROLES for before, _roles in EVENTS.values())
SLOT = "announcement"

# The Passion is announced alone: no greeting, no Glória tibi (RG 472). A reading is a Passion
# when its verses are sung in the three traditional parts.
PASSION_OMITTED_EVENTS = ["evangelium-salutatio"]
PASSION_OMITTED_UNITS = ["responsio-gloria-tibi"]
PASSION_PARTS = {"chronista", "christus", "synagoga"}

# The book abbreviations the Proper prints in its references, and the books each formula can
# announce. A reference printed without a book takes it from the heading (`book_supplied`).
ABBREVIATIONS = {
    "Act.": "Act",
    "Apoc.": "Apoc",
    "Cant.": "Cant",
    "Col.": "Col",
    "Coloss.": "Col",
    "1 Cor.": "1 Cor",
    "2 Cor.": "2 Cor",
    "Eccli.": "Eccli",
    "Ephes.": "Ephes",
    "Ezech.": "Ezech",
    "Gal.": "Gal",
    "Galat.": "Gal",
    "Heb.": "Hebr",
    "Hebr.": "Hebr",
    "Iac.": "Iac",
    "Ioann.": "Ioann",
    "1 Ioann.": "1 Ioann",
    "Isai.": "Isai",
    "Iudith": "Iudith",
    "Luc.": "Luc",
    "2 Mach.": "2 Mach",
    "Malach.": "Malach",
    "Marc.": "Marc",
    "Matt.": "Matth",
    "Matth.": "Matth",
    "1 Petr.": "1 Petr",
    "2 Petr.": "2 Petr",
    "Philipp.": "Philipp",
    "Prov.": "Prov",
    "Rom.": "Rom",
    "Sap.": "Sap",
    "1 Thess.": "1 Thess",
    "Tit.": "Tit",
}
UNIT_BOOKS: dict[str, frozenset[str]] = {
    "initium-sancti-evangelii-secundum-ioannem": frozenset({"Ioann"}),
    "initium-sancti-evangelii-secundum-matthaeum": frozenset({"Matth"}),
    "lectio-actuum-apostolorum": frozenset({"Act"}),
    "lectio-epistolae-beati-iacobi-apostoli": frozenset({"Iac"}),
    "lectio-epistolae-beati-ioannis-apostoli": frozenset({"1 Ioann", "2 Ioann", "3 Ioann"}),
    "lectio-epistolae-beati-pauli-apostoli-ad-colossenses": frozenset({"Col"}),
    "lectio-epistolae-beati-pauli-apostoli-ad-corinthios": frozenset({"1 Cor", "2 Cor"}),
    "lectio-epistolae-beati-pauli-apostoli-ad-ephesios": frozenset({"Ephes"}),
    "lectio-epistolae-beati-pauli-apostoli-ad-galatas": frozenset({"Gal"}),
    "lectio-epistolae-beati-pauli-apostoli-ad-hebraeos": frozenset({"Hebr"}),
    "lectio-epistolae-beati-pauli-apostoli-ad-philippenses": frozenset({"Philipp"}),
    "lectio-epistolae-beati-pauli-apostoli-ad-romanos": frozenset({"Rom"}),
    "lectio-epistolae-beati-pauli-apostoli-ad-thessalonicenses": frozenset({"1 Thess", "2 Thess"}),
    "lectio-epistolae-beati-pauli-apostoli-ad-titum": frozenset({"Tit"}),
    "lectio-epistolae-beati-petri-apostoli": frozenset({"1 Petr", "2 Petr"}),
    "lectio-ezechielis-prophetae": frozenset({"Ezech"}),
    "lectio-isaiae-prophetae": frozenset({"Isai"}),
    "lectio-libri-apocalypsis-beati-ioannis-apostoli": frozenset({"Apoc"}),
    "lectio-libri-iudith": frozenset({"Iudith"}),
    "lectio-libri-machabaeorum": frozenset({"1 Mach", "2 Mach"}),
    "lectio-libri-sapientiae": frozenset({"Prov", "Eccl", "Cant", "Sap", "Eccli"}),
    "lectio-malachiae-prophetae": frozenset({"Malach"}),
    "passio-domini-nostri-iesu-christi-secundum-matthaeum": frozenset({"Matth"}),
    "sequentia-sancti-evangelii-secundum-ioannem": frozenset({"Ioann"}),
    "sequentia-sancti-evangelii-secundum-lucam": frozenset({"Luc"}),
    "sequentia-sancti-evangelii-secundum-marcum": frozenset({"Marc"}),
    "sequentia-sancti-evangelii-secundum-matthaeum": frozenset({"Matth"}),
}
BOOK = re.compile(r"((?:[12] )?[A-Z][a-z]+\.?) ")
LEAF = re.compile(r"^# location: .*?n([0-9]+)", re.MULTILINE)


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _fold(value: str) -> str:
    """A heading without acute accents, case or closing full stop: the print's variant set."""
    bare = "".join(c for c in unicodedata.normalize("NFD", value) if c != "\u0301")
    return unicodedata.normalize("NFC", bare).lower().removesuffix(".")


def formula(segment: dict[str, Any]) -> str:
    """The words of a unit's segment as they are read, with their punctuation."""
    return " ".join(word["form"] + word.get("post", "") for word in segment["words"])


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load(corpus: Path) -> tuple[Any, list[str]]:
    """The authored library, or why it cannot be read. Repeated keys are refused."""
    path = corpus / PATH
    if not path.is_file():
        return None, [f"introductiones: {PATH} is missing"]
    try:
        repeated = duplicate_keys(path)
        doc = _read(path)
    except (OSError, ValueError) as exc:
        return None, [f"introductiones: {PATH} cannot be read: {exc}"]
    if repeated:
        return None, [f"introductiones: {PATH}: {message}" for message in repeated]
    return doc, []


def owner_segment(corpus: Path, unit: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """The owner's stored segment a unit names, or the reason it names none."""
    where = f"introductiones: unit {unit['id']}"
    text, segment_id = unit["text"], unit["segment"]
    if not isinstance(text, str) or not TEXT_IDENTITY.fullmatch(text):
        return None, f"{where}: owner text {text!r} is not a dotted text id"
    path = store.path_of(corpus, text)
    if not path.is_file():
        return None, f"{where}: owner text {text} does not exist"
    owner = _read(path)
    if owner.get("id") != text:
        return None, f"{where}: {path.name} does not carry the id {text}"
    found = [s for s in owner.get("segments") or [] if s.get("id") == segment_id]
    if len(found) != 1:
        return None, f"{where}: {text} has no segment {segment_id!r}"
    segment = found[0]
    if segment.get("type") != "verse" or not segment.get("words"):
        return None, f"{where}: {text} {segment_id} is not a verse with words"
    return segment, ""


def unit_words(corpus: Path, unit: dict[str, Any]) -> list[str]:
    """The word ids a valid unit addresses, in the owner's stored order."""
    segment, problem = owner_segment(corpus, unit)
    if segment is None:
        raise ValueError(problem)
    ids = [word["id"] for word in segment["words"]]
    return ids[ids.index(unit["first"]) : ids.index(unit["last"]) + 1]


def _unit_errors(corpus: Path, unit: dict[str, Any]) -> tuple[list[str], dict[str, Any] | None]:
    """Everything wrong with one unit, and its owner segment when the address resolves."""
    where = f"introductiones: unit {unit['id']}"
    errors: list[str] = []
    role = unit["role"]
    if role not in ROLES:
        errors.append(f"{where}: unknown role {role!r}")
    if not _nonempty(unit["source"]):
        errors.append(f"{where}: source citation is empty")
    segment, problem = owner_segment(corpus, unit)
    if segment is None:
        return [*errors, problem], None
    text, segment_id = unit["text"], unit["segment"]
    ids = [word.get("id") for word in segment["words"]]
    first, last = unit["first"], unit["last"]
    if first not in ids or last not in ids:
        return [*errors, f"{where}: {first!r}-{last!r} names a word outside {segment_id}"], None
    if ids.index(first) > ids.index(last):
        return [*errors, f"{where}: {first}-{last} is reversed in stored order"], None
    if (first, last) != (ids[0], ids[-1]):
        errors.append(
            f"{where}: a unit is a whole segment, and {segment_id} runs {ids[0]}-{ids[-1]}"
        )
    if role in ROLES:
        speaker, _performer, answered = ROLES[role]
        base = (segment.get("speaker"), segment.get("voice"))
        if base != (speaker, VOICES["lecta"]):
            errors.append(
                f"{where}: the owner's base {base[0]}/{base[1]} is not the {role}'s "
                f"{speaker}/{VOICES['lecta']}"
            )
        participation = segment.get("participation") or {}
        if answered and not all(participation.get(form) for form in FORMS):
            errors.append(f"{where}: a {role} needs its owner's participation in both forms")
        if not answered and participation:
            errors.append(
                f"{where}: a {role} is the celebrant's and its owner carries participation"
            )
    if role == "announcement":
        if segment["words"][0].get("lemma") not in ANNOUNCEMENT_CLASSES:
            errors.append(
                f"{where}: an announcement opens with {', '.join(ANNOUNCEMENT_CLASSES)}, "
                f"not {segment['words'][0].get('lemma')!r}"
            )
        if unit["id"] not in UNIT_BOOKS:
            errors.append(f"{where}: an announcement needs its row in the closed table of books")
    members = set(ids)
    for language in store.language_ids(corpus):
        manifest = _read(corpus / "languages" / language / "manifest.json")
        if (manifest.get("texts") or []).count(text) != 1:
            errors.append(f"{where}: {text} must be published once in the {language} package")
            continue
        try:
            layer = _read(store.layer_path(corpus, language, text))
        except (OSError, ValueError):
            errors.append(f"{where}: the {language} layer of {text} cannot be read")
            continue
        if layer.get("text") != text or layer.get("language") != language:
            errors.append(f"{where}: the {language} layer of {text} names another text")
            continue
        localized = layer.get("segments") or {}
        if not _nonempty((localized.get(segment_id) or {}).get("translation")):
            errors.append(f"{where}: {language} has no translation of {text} {segment_id}")
        for stored_under, entry in localized.items():
            for group in (entry or {}).get("alignments") or []:
                grouped = set(group.get("words") or [])
                if grouped & members and (stored_under != segment_id or not grouped <= members):
                    errors.append(
                        f"{where}: a {language} alignment group crosses the boundary of "
                        f"{segment_id}"
                    )
    return errors, segment


def _units(corpus: Path, units: Any) -> tuple[dict[str, dict[str, Any]], list[str]]:
    if not isinstance(units, list) or not units:
        return {}, ["introductiones: units must be a nonempty list"]
    errors: list[str] = []
    identities: list[str] = []
    resolved: dict[str, dict[str, Any]] = {}
    for position, unit in enumerate(units):
        if not isinstance(unit, dict) or set(unit) != UNIT_KEYS:
            errors.append(
                f"introductiones: units[{position}] needs exactly the fields {sorted(UNIT_KEYS)}"
            )
            continue
        identity = unit["id"]
        if not isinstance(identity, str) or not IDENTITY.fullmatch(identity):
            errors.append(f"introductiones: units[{position}] has an invalid id {identity!r}")
            continue
        if identity in identities:
            errors.append(f"introductiones: duplicate unit {identity}")
            continue
        identities.append(identity)
        problems, segment = _unit_errors(corpus, unit)
        errors += problems
        if segment is not None and unit["role"] in ROLES:
            lemma = segment["words"][0].get("lemma")
            resolved[identity] = {
                "role": unit["role"],
                "text": unit["text"],
                "owner": segment,
                "class": lemma if unit["role"] == "announcement" else None,
            }
    if identities != sorted(identities):
        errors.append("introductiones: units must be in identity order")
    return resolved, errors


def _delivery_errors(where: str, occurrence: dict[str, Any], role: str) -> list[str]:
    """Both forms of one occurrence's delivery against the closed vocabulary of its role."""
    errors: list[str] = []
    performers = dict(zip(FORMS, ROLES[role][:2], strict=True))
    for form in FORMS:
        delivery = occurrence[form]
        if not isinstance(delivery, dict) or set(delivery) != DELIVERY_KEYS:
            errors.append(f"{where}: {form} delivery needs exactly {sorted(DELIVERY_KEYS)}")
            continue
        speaker, voice = delivery["speaker"], delivery["voice"]
        voices = SUNG_VOICES.get(role, (VOICES[form],)) if form == "cantu" else (VOICES[form],)
        if speaker not in SPEAKERS[form] or voice not in voices:
            errors.append(
                f"{where}: {form} delivery {speaker!r}/{voice!r} is outside the closed vocabulary"
            )
            continue
        if speaker != performers[form]:
            errors.append(
                f"{where}: in the {form} form the {role} belongs to the {performers[form]}, "
                f"not the {speaker}"
            )
        if not _nonempty(delivery["source"]):
            errors.append(f"{where}: {form} delivery has no source citation")
    return errors


def _occurrence_errors(
    where: str, occurrence: dict[str, Any], role: str, unit: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    if unit["role"] != role:
        errors.append(f"{where}: a {role} stands here, not the {unit['role']} {occurrence['unit']}")
    errors += _delivery_errors(where, occurrence, role)
    inherited = (unit["owner"].get("delivery") or {}).get("cantu")
    sung = occurrence["cantu"]
    if (
        inherited
        and isinstance(sung, dict)
        and {"speaker": sung.get("speaker"), "voice": sung.get("voice")} != inherited
    ):
        errors.append(
            f"{where}: the sung delivery differs from the owner's own override {inherited}"
        )
    return errors


def _events(events: Any, units: dict[str, dict[str, Any]]) -> tuple[int, int, list[str]]:
    if not isinstance(events, list) or not events:
        return 0, 0, ["introductiones: events must be a nonempty list"]
    errors: list[str] = []
    identities: list[str] = []
    occurrences = 0
    for position, event in enumerate(events):
        if not isinstance(event, dict) or set(event) != EVENT_KEYS:
            errors.append(
                f"introductiones: events[{position}] needs exactly the fields {sorted(EVENT_KEYS)}"
            )
            continue
        identity = event["id"]
        if not isinstance(identity, str) or identity not in EVENTS:
            errors.append(f"introductiones: events[{position}] is an unknown event {identity!r}")
            continue
        if identity in identities:
            errors.append(f"introductiones: duplicate event {identity}")
            continue
        identities.append(identity)
        where = f"introductiones: event {identity}"
        before, roles = EVENTS[identity]
        if event["before"] != before:
            errors.append(f"{where}: it precedes the {before}, not {event['before']!r}")
        if not _nonempty(event["source"]):
            errors.append(f"{where}: source citation is empty")
        sequence = event["occurrences"]
        if not isinstance(sequence, list) or len(sequence) != len(roles):
            errors.append(f"{where}: needs exactly the ordered roles {', '.join(roles)}")
            continue
        for index, (occurrence, role) in enumerate(zip(sequence, roles, strict=True)):
            here = f"{where} occurrence {index}"
            if role == SLOT:
                if not isinstance(occurrence, dict) or set(occurrence) != SLOT_KEYS:
                    errors.append(
                        f"{here}: an announcement is a slot with exactly the fields "
                        f"{sorted(SLOT_KEYS)}"
                    )
                    continue
                if occurrence["slot"] != SLOT:
                    errors.append(f"{here}: the slot is {SLOT!r}, not {occurrence['slot']!r}")
                    continue
                errors += _delivery_errors(here, occurrence, role)
                occurrences += 1
                continue
            if not isinstance(occurrence, dict) or set(occurrence) != OCCURRENCE_KEYS:
                errors.append(f"{here}: needs exactly the fields {sorted(OCCURRENCE_KEYS)}")
                continue
            unit = units.get(occurrence["unit"]) if isinstance(occurrence["unit"], str) else None
            if unit is None:
                errors.append(f"{here}: names no valid unit ({occurrence['unit']!r})")
                continue
            errors += _occurrence_errors(here, occurrence, role, unit)
            occurrences += 1
    missing = sorted(set(EVENTS) - set(identities))
    if missing:
        errors.append(f"introductiones: events missing: {', '.join(missing)}")
    if identities != [identity for identity in EVENTS if identity in identities]:
        errors.append("introductiones: events must be in the order of the Mass")
    return len(identities), occurrences, errors


def _sung_voice(occurrence: Any) -> str | None:
    sung = occurrence.get("cantu") if isinstance(occurrence, dict) else None
    return sung.get("voice") if isinstance(sung, dict) else None


def _passion(passion: Any, units: dict[str, dict[str, Any]]) -> list[str]:
    """The Passion's own announcement: the units it applies to, what it omits, its delivery."""
    where = "introductiones: passion"
    if not isinstance(passion, dict) or set(passion) != PASSION_KEYS:
        return [f"{where} needs exactly the fields {sorted(PASSION_KEYS)}"]
    errors: list[str] = []
    expected = sorted(identity for identity, unit in units.items() if unit["class"] == "passio")
    if passion["units"] != expected:
        errors.append(f"{where}: the units must be the passio announcements {expected}")
    if passion["omitted_events"] != PASSION_OMITTED_EVENTS:
        errors.append(f"{where}: the Passion omits exactly the events {PASSION_OMITTED_EVENTS}")
    if passion["omitted_units"] != PASSION_OMITTED_UNITS:
        errors.append(f"{where}: the Passion omits exactly the units {PASSION_OMITTED_UNITS}")
    if not _nonempty(passion["source"]):
        errors.append(f"{where}: source citation is empty")
    for form in FORMS:
        delivery = passion[form]
        if not isinstance(delivery, dict) or set(delivery) != DELIVERY_KEYS:
            errors.append(f"{where}: {form} delivery needs exactly {sorted(DELIVERY_KEYS)}")
        elif (delivery["speaker"], delivery["voice"]) != ("sacerdos", VOICES[form]):
            errors.append(
                f"{where}: {form} delivery {delivery['speaker']!r}/{delivery['voice']!r} "
                f"is not the celebrant's sacerdos/{VOICES[form]}"
            )
        elif not _nonempty(delivery["source"]):
            errors.append(f"{where}: {form} delivery has no source citation")
    return errors


def _readings(corpus: Path) -> tuple[dict[str, str], list[str]]:
    """Every text a formulary names as its Epistle or Gospel, with that role."""
    roles: dict[str, set[str]] = {}
    for formulary in store.formularies(corpus):
        for component in formulary.get("components") or []:
            if component.get("role") in ("epistola", "evangelium"):
                roles.setdefault(component["text"], set()).add(component["role"])
    errors = [
        f"introductiones: {text} is both an Epistle and a Gospel"
        for text, found in sorted(roles.items())
        if len(found) != 1
    ]
    return {text: min(found) for text, found in roles.items()}, errors


def _reading_numbers(reference: str) -> list[int]:
    return [int(number) for number in re.findall(r"[0-9]+", BOOK.sub("", reference, count=1))]


def _pericope_errors(where: str, pericope: Any) -> tuple[list[int], list[str]]:
    """The normalised pericope's shape, and its numbers in printed order."""
    if not isinstance(pericope, dict) or set(pericope) != {"book", "passages"}:
        return [], [f"{where}: a pericope has exactly book and passages"]
    passages = pericope["passages"]
    if not isinstance(passages, list) or not passages:
        return [], [f"{where}: a pericope has at least one passage"]
    numbers: list[int] = []
    for passage in passages:
        if (
            not isinstance(passage, dict)
            or set(passage) != {"chapter", "verses"}
            or type(passage["chapter"]) is not int
            or passage["chapter"] < 1
            or not isinstance(passage["verses"], list)
            or not passage["verses"]
        ):
            return [], [f"{where}: a passage is a chapter with its verse ranges"]
        numbers.append(passage["chapter"])
        for verse in passage["verses"]:
            if (
                not isinstance(verse, list)
                or len(verse) != 2
                or not all(type(number) is int for number in verse)
                or not 1 <= verse[0] <= verse[1]
            ):
                return [], [f"{where}: a verse range is [first, last] in order"]
            numbers += verse[:1] if verse[0] == verse[1] else verse
    return numbers, []


def _binding_errors(
    corpus: Path,
    binding: dict[str, Any],
    units: dict[str, dict[str, Any]],
    readings: dict[str, str],
    sung: dict[str, str | None],
) -> list[str]:
    where = f"introductiones: announcement {binding['reading']}"
    reading = binding["reading"]
    if reading not in readings:
        return [f"{where}: no formulary reads it as an Epistle or a Gospel"]
    unit = units.get(binding["unit"]) if isinstance(binding["unit"], str) else None
    if unit is None or unit["role"] != "announcement" or unit["class"] not in ANNOUNCEMENT_CLASSES:
        return [f"{where}: {binding['unit']!r} is not an announcement unit"]
    errors: list[str] = []
    part = ANNOUNCEMENT_CLASSES[unit["class"]]
    if part != readings[reading]:
        errors.append(
            f"{where}: a {unit['class']} announcement cannot head the {readings[reading]}"
        )
    leaf, page = binding["leaf"], binding["page"]
    if type(leaf) is not int or leaf < 1 or not _nonempty(page):
        errors.append(f"{where}: leaf and printed page are required")
    else:
        try:
            header = (corpus / "witnesses" / reading / "mr.txt").read_text(encoding="utf-8")
        except OSError:
            header = ""
        found = LEAF.search(header)
        if found is None or int(found[1]) != leaf:
            errors.append(f"{where}: leaf {leaf} is not the first leaf of its printed witness")
    printed = binding.get("as_printed")
    heading = formula(unit["owner"])
    if printed is not None and (
        not isinstance(printed, str) or printed == heading or _fold(printed) != _fold(heading)
    ):
        errors.append(
            f"{where}: as_printed must differ from {heading!r} only by accent, case or stop"
        )
    reference = binding["reference_as_printed"]
    numbers, problems = _pericope_errors(where, binding["pericope"])
    errors += problems
    if not _nonempty(reference) or problems:
        return [*errors, *([] if problems else [f"{where}: the printed reference is empty"])]
    book = binding["pericope"]["book"]
    if book not in UNIT_BOOKS.get(binding["unit"], frozenset()):
        errors.append(f"{where}: {binding['unit']} does not announce the book {book!r}")
    printed_book = BOOK.match(reference)
    if printed_book is None:
        if binding.get("book_supplied") is not True:
            errors.append(f"{where}: a reference printed without a book needs book_supplied")
    else:
        if ABBREVIATIONS.get(printed_book[1]) != book:
            errors.append(f"{where}: the printed {printed_book[1]!r} is not the book {book!r}")
        if "book_supplied" in binding:
            errors.append(f"{where}: the print names its book, none is supplied")
    if "book_supplied" in binding and binding["book_supplied"] is not True:
        errors.append(f"{where}: book_supplied is only ever true")
    misprint = binding.get("misprint")
    if misprint is None:
        if _reading_numbers(reference) != numbers:
            errors.append(f"{where}: the pericope must keep the printed chapter and verses")
        if "comparator" in binding or "uncertain" in binding:
            errors.append(f"{where}: a comparator or an uncertain glyph belongs to a misprint")
    elif misprint is not True or _reading_numbers(reference) == numbers:
        errors.append(f"{where}: a misprint is true and differs from its pericope")
    elif not _nonempty(binding.get("comparator")):
        errors.append(f"{where}: a misprint names the comparator that reads the reading")
    if "uncertain" in binding and not _nonempty(binding["uncertain"]):
        errors.append(f"{where}: an uncertain glyph is described")
    voice = sung.get("passio" if unit["class"] == "passio" else part)
    try:
        body = json.loads(store.path_of(corpus, reading).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [*errors, f"{where}: the reading cannot be read"]
    verses = [segment for segment in body.get("segments") or [] if segment.get("type") == "verse"]
    sung_forms = [(segment.get("delivery") or {}).get("cantu") or {} for segment in verses]
    voices = {
        form.get("voice") or segment.get("voice")
        for form, segment in zip(sung_forms, verses, strict=True)
    }
    if bool({form.get("speaker") for form in sung_forms} & PASSION_PARTS) != (
        unit["class"] == "passio"
    ):
        errors.append(f"{where}: a Passion sung in parts takes a passio announcement, and only it")
    if voices != {voice}:
        errors.append(
            f"{where}: the sung announcement ({voice}) must be delivered as its reading "
            f"({', '.join(sorted(str(v) for v in voices))})"
        )
    return errors


def _announcements(
    corpus: Path,
    announcements: Any,
    units: dict[str, dict[str, Any]],
    sung: dict[str, str | None],
) -> tuple[int, list[str]]:
    if not isinstance(announcements, list) or not announcements:
        return 0, ["introductiones: announcements must be a nonempty list"]
    readings, errors = _readings(corpus)
    bound: list[str] = []
    for position, binding in enumerate(announcements):
        if (
            not isinstance(binding, dict)
            or not BINDING_KEYS <= set(binding) <= BINDING_KEYS | BINDING_OPTIONAL
        ):
            errors.append(
                f"introductiones: announcements[{position}] needs the fields "
                f"{sorted(BINDING_KEYS)} and only the optional {sorted(BINDING_OPTIONAL)}"
            )
            continue
        reading = binding["reading"]
        if not isinstance(reading, str) or not TEXT_IDENTITY.fullmatch(reading):
            errors.append(f"introductiones: announcements[{position}] names no reading")
            continue
        if reading in bound:
            errors.append(f"introductiones: {reading} is bound twice")
            continue
        bound.append(reading)
        errors += _binding_errors(corpus, binding, units, readings, sung)
    unbound = sorted(set(readings) - set(bound))
    if unbound:
        errors.append(f"introductiones: readings without an announcement: {', '.join(unbound)}")
    if bound != sorted(bound):
        errors.append("introductiones: announcements must be in reading order")
    return len(bound), errors


def check(corpus: Path) -> tuple[list[str], dict[str, int]]:
    """Return errors and non-vacuous denominators for the Ordo introduction library."""
    counts = {"units": 0, "events": 0, "occurrences": 0, "owner_texts": 0, "announcements": 0}
    doc, errors = load(corpus)
    if errors:
        return errors, counts
    if not isinstance(doc, dict) or set(doc) != KEYS:
        return [f"introductiones: {PATH} needs exactly the fields {sorted(KEYS)}"], counts
    if doc["introduction_schema"] != SCHEMA:
        errors.append(f"introductiones: introduction_schema must be {SCHEMA}")
    units, unit_errors = _units(corpus, doc["units"])
    events, occurrences, event_errors = _events(doc["events"], units)
    errors += unit_errors + event_errors + _passion(doc["passion"], units)
    # The sung voice of each announcement slot, by the part it announces, and of the Passion.
    slots: dict[str, str | None] = {
        event["before"]: _sung_voice(event["occurrences"][0])
        for event in (doc["events"] if isinstance(doc["events"], list) else [])
        if isinstance(event, dict)
        and event.get("id") in ("epistola-annuntiatio", "evangelium-annuntiatio")
        and isinstance(event.get("before"), str)
        and isinstance(event.get("occurrences"), list)
        and event["occurrences"]
    }
    slots["passio"] = _sung_voice(doc["passion"])
    bindings, binding_errors = _announcements(corpus, doc["announcements"], units, slots)
    errors += binding_errors
    rubrics = doc["rubrics"]
    if not isinstance(rubrics, dict) or set(rubrics) != RUBRIC_KEYS:
        errors.append(f"introductiones: rubrics need exactly {sorted(RUBRIC_KEYS)}")
    elif not all(_nonempty(value) for value in rubrics.values()):
        errors.append("introductiones: every rubric must be a nonempty citation")
    counts = {
        "units": len(units),
        "events": events,
        "occurrences": occurrences,
        "owner_texts": len({unit["text"] for unit in units.values()}),
        "announcements": bindings,
    }
    return errors, counts


def authored(corpus: Path) -> dict[str, Any]:
    """The validated authored library; an invalid one is refused, never projected."""
    problems, _counts = check(corpus)
    if problems:
        raise ValueError("introductiones: invalid authored library: " + "; ".join(problems))
    doc, _errors = load(corpus)
    return doc

"""Finite commemoration occurrences and their decisions on the edition's date/Mass pairs.

The authored commemoration owns its occurrence rule and its three ordered slots: the Greater
Litanies (Rubricae generales 80: April 25, or the following Tuesday when that day is Easter
Sunday or Easter Monday), St Petronilla (31 May, never transferred), the impeded Sunday (RG
15–18: a Sunday on which one of the first-class feasts named by its authored rule is kept), the
impeded feast (RG 16, 95: a second-class Sunday on which one of the second-class feasts named by
its authored rule falls) and the Advent feria (RG 24–25: a weekday of Advent on which one of the
feasts named by its authored rule is kept). Every occurrence in the supported span is published,
whether or not a Mass row is represented on that day.

A pair is an explicit decision for one represented Mass on an occurrence date, stated for each
of three situations: a low Mass (lecta), a sung conventual Mass and a sung Mass that is not
conventual. Low conventual and non-conventual Masses receive the same decision (RG 108), so the
low situation is stated once. A privileged commemoration is admitted in all three (RG 108–109).
The fixed-date ordinary commemorations carried here are not themselves second-class feasts, so
each is decided on a second-class weekday only: a first-class day admits no ordinary
commemoration and a second-class Sunday only a second-class feast (RG 111 a–b, 434), and no pair
is published for it there. On that weekday it is admitted in low and sung conventual Masses and
not in a sung Mass that is not conventual (RG 108), unless a de Tempore commemoration takes the
single place (RG 111 c, 113–114). The impeded Ascension Vigil is such an ordinary day (RG 31–33):
when enabled, its own canonical orations take that place and a competing Petronilla is not
admitted. The explicit
weekday-Vigil relations require their complete source-role/body bindings before any emission;
missing lower saints are never relabelled unavailable de Tempore. The legacy unavailable branch
remains only while the complete Vigil feature has not been enabled. At most one commemoration
is admitted for a date, Mass and situation: a second would need an order and a conclusion plan
this contract does not model.

The impeded Sunday's three orations are not fixed texts. Each pair names the formulary of the
Sunday that the calendar would have kept that day, which is not always its position in the
year: a Sunday after Epiphany resumed after the Twenty-third Sunday after Pentecost keeps its
own formulary (RG 18). Its orations are the Collect, Secret and Postcommunion that formulary
assembles. Where that formulary or one of its orations is not in this edition, the pair states
that the required de Tempore commemoration is unavailable instead of admitting a gap.

The impeded feast's three orations are not fixed texts either. Each pair is the second-class
Sunday's Mass and names the formulary of the second-class feast that falls on it; its orations
are the Collect, Secret and Postcommunion that formulary assembles (those of the Chair of St
Peter join St Paul's oration to St Peter's, RG 110). It is the single commemoration that Sunday
admits, an ordinary one, made in low and sung conventual Masses and not in a sung Mass that is
not conventual (RG 108, 111 b, 434 b); a feast that a first-class Sunday impedes has no pair
(111 a). A feast whose formulary or orations this edition lacks stops the selection rather than
leaving a gap.

The Advent feria's three orations are those of the feria's own Mass. Each pair is the feast's
Mass and names that Mass: the ferias of Advent say the Mass of the preceding Sunday, and the
Ember days of Advent have a Mass of their own (RG 299). It is a privileged commemoration, made
in all Masses (RG 108–109 e). An Ember day's Mass is not yet in this edition, so its pair names
that absent Mass and states that the required de Tempore commemoration is unavailable, never
the Sunday's orations in its place; a Sunday whose orations this edition lacks stops the
selection. No procession, local calendar or Office commemoration is inferred.
"""

from __future__ import annotations

import copy
import json
import re
from datetime import date, timedelta
from pathlib import Path

from kalendarium.computus import easter
from kalendarium.dismissal import canonical_inputs
from kalendarium.roman import year
from kalendarium.sanctorale import occurrences as sanctoral_occurrences
from kalendarium.temporale import Dies
from kalendarium.temporale import year as temporal_year
from kalendarium.weekday_vigil import (
    IMPEDED as IMPEDED_VIGIL,
)
from kalendarium.weekday_vigil import (
    UNDER as UNDER_VIGIL,
)
from kalendarium.weekday_vigil import (
    VIGIL,
)
from kalendarium.weekday_vigil import (
    kind as vigil_kind,
)
from kalendarium.weekday_vigil import (
    occurrences as weekday_vigil_occurrences,
)
from kalendarium.weekday_vigil import (
    require_inputs as require_vigil_inputs,
)

SCHEMA = "2.1.0"
PROFILES = [{"id": "ordinary-separate-conclusions"}]
SITUATIONS = ["lecta", "cantu-conventualis", "cantu-non-conventualis"]
DECISIONS = [
    {"id": "admitted"},
    {"id": "not-admitted"},
    {"id": "omitted-required-de-tempore-unavailable"},
]
ADMITTED, NOT_ADMITTED, DE_TEMPORE_UNAVAILABLE = range(len(DECISIONS))
YEARS = range(2026, 2102)
IDENTITY = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
FIELDS = {
    "schema_version",
    "commemorations",
    "profiles",
    "situations",
    "decisions",
    "masses",
    "occurrences",
    "pairs",
}
ENTRY_FIELDS = {"id", "title", "rank", "conclusion", "slots"}
SLOT_FIELDS = {"key", "after", "text"}
RANKS = ("privileged", "ordinary")
# The Mass roles a commemoration slot follows, in order.
ORATIONS = ("collecta", "secreta", "postcommunio")
# De Tempore days this edition does not yet carry that take the single second-class place on
# the fixed dates an ordinary commemoration may use (checks.commemorationes.ORDINARY_DATES),
# by their distance from Easter Sunday: the Vigil of the Ascension, a second-class vigil
# commemorated when impeded (RG 31–33).
UNAVAILABLE_DE_TEMPORE = {"vigilia-ascensionis": 38}
# The Ember days of Advent, the Wednesday, Friday and Saturday of the week of the Third Sunday of
# Advent (by weekday, Monday 0), have their own Masses (RG 24 b, 299), which this edition does
# not yet carry. A pair names each by a stable identity in the form of the Missal's Ember-day
# headings; none is an authored Mass.
ADVENT_EMBER_DAYS = {
    2: "feria-quarta-quatuor-temporum-adventus",
    4: "feria-sexta-quatuor-temporum-adventus",
    5: "sabbato-quatuor-temporum-adventus",
}


def displaced(commemoration: dict) -> bool:
    """True for the impeded-Sunday occurrence kind, whose dates the calendar supplies."""
    return commemoration["occurrence"].get("kind") == "displaced-sunday"


def impeded(commemoration: dict) -> bool:
    """True for the impeded-feast occurrence kind, whose dates the calendar supplies."""
    return commemoration["occurrence"].get("kind") == "impeded-feast"


def advent_feria(commemoration: dict) -> bool:
    """True for the Advent-feria occurrence kind, whose dates the calendar supplies."""
    return commemoration["occurrence"].get("kind") == "advent-feria"


def occurrence(commemoration: dict, civil_year: int) -> date:
    """The civil date of one commemoration in one year, after its transfer rule."""
    rule = commemoration["occurrence"]
    if displaced(commemoration):  # pragma: no cover — its dates come from impeded_sundays()
        raise ValueError("commemorationes: an impeded Sunday has no fixed civil date")
    if impeded(commemoration):  # pragma: no cover — its dates come from impeded_feasts()
        raise ValueError("commemorationes: an impeded feast has no fixed civil date")
    if advent_feria(commemoration):  # pragma: no cover — its dates come from advent_ferias()
        raise ValueError("commemorationes: an Advent feria has no fixed civil date")
    when = date(civil_year, rule["month"], rule["day"])
    if rule["transfer"] == "easter-sunday-or-monday-to-tuesday":
        pascha = easter(civil_year)
        if when in (pascha, pascha + timedelta(days=1)):
            when = pascha + timedelta(days=2)
    elif rule["transfer"] != "none":  # pragma: no cover — the checker admits only these rules
        raise ValueError(f"commemorationes: unknown transfer rule {rule['transfer']!r}")
    return when


def impeded_sunday(day: Dies, ending: int) -> str:
    """The formulary of the Sunday that the feast kept on `day` impedes (RG 15–18).

    The temporal cycle names that Sunday's own formulary, including a Sunday after Epiphany
    resumed after the Twenty-third Sunday after Pentecost (18). Where the temporal cycle has
    already given the day to the feast itself (the Immaculate Conception over the Second Sunday
    of Advent, 15), the Sunday is the day's position.
    """
    for temporal in temporal_year(ending):
        if temporal.when == day.when:
            own = temporal.formulary == day.formulary
            sunday = temporal.position if own else temporal.formulary
            if (
                day.when.weekday() != 6
                or temporal.position != day.position
                or not sunday.startswith("dominica-")
            ):
                raise ValueError(f"commemorationes: {day.when} has no impeded Sunday")
            return sunday
    raise ValueError(f"commemorationes: {day.when} is not a day of the temporal cycle")


def impeded_sundays(commemoration: dict) -> dict[str, str]:
    """Each date of the supported span on which a named feast impedes a Sunday, with the
    formulary of that Sunday."""
    feasts = commemoration["occurrence"]["feasts"]
    return {
        day.when.isoformat(): impeded_sunday(day, ending)
        for ending in YEARS
        for day in year(ending)
        if day.formulary in feasts and day.when.weekday() == 6
    }


def impeded_feasts(commemoration: dict) -> dict[str, str]:
    """Each date of the supported span on which one of the named second-class feasts falls on a
    second-class Sunday, which is preferred to it (RG 16), with the feast's formulary. A feast
    on a first-class Sunday, or on a Sunday whose place a feast of the Lord takes, is not here."""
    feasts = commemoration["occurrence"]["feasts"]
    found: dict[str, str] = {}
    for ending in YEARS:
        kept = {day.when: day for day in year(ending)}
        for when, feast in sanctoral_occurrences(ending):
            day = kept.get(when)
            if (
                feast.formulary not in feasts
                or day is None
                or when.weekday() != 6
                or day.dies_class != 2
                or not day.formulary.startswith("dominica-")
            ):
                continue
            if when.isoformat() in found:
                raise ValueError(f"commemorationes: {when} impedes more than one named feast")
            found[when.isoformat()] = feast.formulary
    return found


def advent_ferias(commemoration: dict) -> dict[str, str]:
    """Each date of the supported span on which one of the named feasts is kept on a weekday of
    Advent (RG 21), with the Mass of the feria it impedes: the Ember day's own Mass on the
    Wednesday, Friday and Saturday of the week of the Third Sunday of Advent, and otherwise the
    Mass of the preceding Sunday (RG 299), named by that Sunday's position in the temporal cycle.
    """
    feasts = commemoration["occurrence"]["feasts"]
    found: dict[str, str] = {}
    for ending in YEARS:
        sundays = [
            temporal
            for temporal in temporal_year(ending)
            if temporal.position.startswith("dominica-") and temporal.position.endswith("-adventus")
        ]
        for day in year(ending):
            if day.formulary not in feasts or day.when.weekday() == 6 or day.season != "adventus":
                continue
            before = [sunday for sunday in sundays if sunday.when < day.when]
            if not before:
                raise ValueError(f"commemorationes: {day.when} follows no Sunday of Advent")
            sunday = before[-1].position
            ember = sunday == "dominica-iii-adventus" and day.when.weekday() in ADVENT_EMBER_DAYS
            found[day.when.isoformat()] = ADVENT_EMBER_DAYS[day.when.weekday()] if ember else sunday
    return found


def formulary_orations(form: dict | None) -> list[str] | None:
    """The Collect, Secret and Postcommunion texts a formulary assembles, in slot order, or None
    when the formulary or one of those orations is not in this edition."""
    if form is None:
        return None
    texts = []
    for role in ORATIONS:
        components = [c for c in form["components"] if c["role"] == role]
        if not components:
            return None
        if len(components) != 1 or "condition" in components[0]:
            raise ValueError(f"commemorationes: {form['id']} has no single unconditional {role}")
        texts.append(components[0]["text"])
    return texts


def sunday_orations(form: dict | None) -> list[str] | None:
    """The orations an impeded Sunday's formulary assembles (formulary_orations)."""
    return formulary_orations(form)


def impeded_feast_decision(form: dict | None, day: str, dies_class: int) -> list[int]:
    """The decision for the second-class feast that a second-class Sunday impedes: an ordinary
    commemoration, made in low and sung conventual Masses and not in a sung Mass that is not
    conventual (RG 108, 111 b, 434 b). A feast whose formulary or orations this edition lacks
    stops the selection rather than publishing a gap."""
    if dies_class != 2:
        raise ValueError(f"commemorationes: {day} is not a second-class Sunday")
    if formulary_orations(form) is None:
        raise ValueError(f"commemorationes: the feast impeded on {day} is not in this edition")
    return [ADMITTED, ADMITTED, NOT_ADMITTED]


def advent_feria_decision(form: dict | None, mass: str, day: str) -> list[int]:
    """The decision for the Advent feria that the feast kept on `day` impedes: a privileged
    commemoration, made in all Masses (RG 108–109 e), with the orations of the feria's Mass.
    An Ember day's own Mass, absent from this edition, is stated unavailable in all three
    situations and never replaced by the Sunday's; its commemoration takes the first of its
    Collects, which this rule does not model, so an authored Ember Mass stops the selection, as
    does a preceding Sunday whose orations this edition lacks."""
    if mass in ADVENT_EMBER_DAYS.values():
        if form is not None:
            raise ValueError(f"commemorationes: {mass} needs its own commemoration rule")
        return [DE_TEMPORE_UNAVAILABLE] * len(SITUATIONS)
    if formulary_orations(form) is None:
        raise ValueError(
            f"commemorationes: the Mass of the Advent feria on {day} is not in this edition"
        )
    return [ADMITTED] * len(SITUATIONS)


def unavailable_de_tempore(when: date) -> str | None:
    """Legacy de Tempore absence dates, used only while the Vigil feature is not enabled."""
    pascha = easter(when.year)
    for name, offset in UNAVAILABLE_DE_TEMPORE.items():
        if when == pascha + timedelta(days=offset):
            return name
    return None


def decision(
    commemoration: dict, when: date, dies_class: int, *, vigil_available: bool = False
) -> list[int] | None:
    """The decision in each situation for a represented Mass on an occurrence date.

    None means the day admits no such commemoration and no pair is published for it.
    """
    from checks.commemorationes import ORDINARY_DATES

    if commemoration["rank"] == "privileged":
        return [ADMITTED, ADMITTED, ADMITTED]
    if commemoration["rank"] != "ordinary" or (when.month, when.day) not in ORDINARY_DATES:
        raise ValueError(f"commemorationes: {commemoration['id']} is outside the modeled scope")
    if dies_class != 2 or when.weekday() == 6:
        return None
    if unavailable_de_tempore(when) is not None:
        if vigil_available:
            return [NOT_ADMITTED] * len(SITUATIONS)
        return [DE_TEMPORE_UNAVAILABLE, DE_TEMPORE_UNAVAILABLE, NOT_ADMITTED]
    return [ADMITTED, ADMITTED, NOT_ADMITTED]


def authored(corpus: Path) -> list[dict]:
    """The validated authored commemorations in identity order."""
    from checks.commemorationes import check, documents

    problems, _ = check(corpus)
    if problems:
        raise ValueError("commemorationes: invalid authored documents: " + "; ".join(problems))
    return sorted((doc for _path, doc in documents(corpus)), key=lambda doc: doc["id"])


def _masses(forms: list[dict]) -> list[str]:
    masses = []
    for form in forms:
        mass = form.get("id") if isinstance(form, dict) else None
        if (
            not isinstance(mass, str)
            or not IDENTITY.fullmatch(mass)
            or mass == "none"
            or mass in masses
        ):
            raise ValueError("commemorationes: invalid, empty or duplicate Mass identity")
        masses.append(mass)
    return sorted(masses)


def entries(commemorations: list[dict]) -> list[dict]:
    return [
        {
            "id": doc["id"],
            "title": doc["title"],
            "rank": doc["rank"],
            "conclusion": doc["conclusion"],
            "slots": [
                {
                    "key": slot["key"],
                    "after": slot["after"],
                    "text": None if slot["text"] is None else slot["text"].replace(".", "/", 1),
                }
                for slot in doc["slots"]
            ],
        }
        for doc in commemorations
    ]


def calendar_table(forms: list[dict], calendar: dict, *, corpus: Path) -> dict:
    from build_reader import store

    masses = _masses(forms)
    actual_forms, actual_calendar = canonical_inputs(corpus)

    def canonical(value):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    if canonical(forms) != canonical(actual_forms) or canonical(calendar) != canonical(
        actual_calendar
    ):
        raise ValueError(
            "commemorationes: inputs differ from canonical authored catalogue/calendar"
        )
    commemorations = authored(corpus)
    vigil_available = require_vigil_inputs(
        corpus, commemorations, store.formularies(corpus), VIGIL in calendar["formularies"]
    )
    resolutions = {
        index: (
            {
                day: mass
                for ending in YEARS
                for day, mass in weekday_vigil_occurrences(doc, ending).items()
            }
            if vigil_kind(doc) in (IMPEDED_VIGIL, UNDER_VIGIL)
            else impeded_sundays(doc)
            if displaced(doc)
            else impeded_feasts(doc)
            if impeded(doc)
            else advent_ferias(doc)
        )
        for index, doc in enumerate(commemorations)
        if displaced(doc)
        or impeded(doc)
        or advent_feria(doc)
        or vigil_kind(doc) in (IMPEDED_VIGIL, UNDER_VIGIL)
    }
    occurrences = sorted(
        [
            *(
                [occurrence(doc, civil_year).isoformat(), index]
                for index, doc in enumerate(commemorations)
                if index not in resolutions
                for civil_year in YEARS
            ),
            *([day, index] for index, found in resolutions.items() for day in found),
        ]
    )
    dates = {(day, index) for day, index in occurrences}
    by_key: dict[str, list[dict]] = {}
    by_id = {form["id"]: form for form in forms}
    for form in forms:
        by_key.setdefault(form["calendar"]["key"], []).append(form)
    pairs = []
    for rows in calendar["years"].values():
        for row in rows:
            for index, doc in enumerate(commemorations):
                if (row[0], index) not in dates:
                    continue
                resolved: str | None = None
                plan: list[int] | None
                if index in resolutions and vigil_kind(doc) == UNDER_VIGIL:
                    plan = [ADMITTED, ADMITTED, NOT_ADMITTED]
                elif index in resolutions and vigil_kind(doc) == IMPEDED_VIGIL:
                    resolved = resolutions[index][row[0]]
                    plan = [ADMITTED, ADMITTED, NOT_ADMITTED]
                elif index in resolutions and displaced(doc):
                    resolved = resolutions[index][row[0]]
                    available = sunday_orations(by_id.get(resolved)) is not None
                    plan = [ADMITTED if available else DE_TEMPORE_UNAVAILABLE] * len(SITUATIONS)
                elif index in resolutions and advent_feria(doc):
                    resolved = resolutions[index][row[0]]
                    plan = advent_feria_decision(by_id.get(resolved), resolved, row[0])
                elif index in resolutions:
                    resolved = resolutions[index][row[0]]
                    plan = impeded_feast_decision(by_id.get(resolved), row[0], row[3])
                else:
                    plan = decision(
                        doc, date.fromisoformat(row[0]), row[3], vigil_available=vigil_available
                    )
                if plan is None:
                    continue
                for form in by_key.get(calendar["formularies"][row[1]], []):
                    pairs.append([row[0], masses.index(form["id"]), index, 0, *plan, resolved])
    table = {
        "schema_version": SCHEMA,
        "commemorations": entries(commemorations),
        "profiles": copy.deepcopy(PROFILES),
        "situations": list(SITUATIONS),
        "decisions": copy.deepcopy(DECISIONS),
        "masses": masses,
        "occurrences": occurrences,
        "pairs": sorted(pairs),
    }
    validate(table)
    return table


def validate(table: dict) -> None:
    if not isinstance(table, dict) or set(table) != FIELDS:
        raise ValueError("commemorationes: exact resource fields required")
    if (
        table["schema_version"] != SCHEMA
        or table["profiles"] != PROFILES
        or table["situations"] != SITUATIONS
        or table["decisions"] != DECISIONS
    ):
        raise ValueError(
            "commemorationes: schema, profiles, situations or decisions differ from the contract"
        )
    commemorations = table["commemorations"]
    if not isinstance(commemorations, list) or not commemorations:
        raise ValueError("commemorationes: at least one commemoration required")
    identities: list[str] = []
    ranks: list[str] = []
    # A commemoration whose slots name no text is resolved per pair: each of its pairs names
    # the formulary whose orations are said, and no other pair names one.
    resolved: list[bool] = []
    for entry in commemorations:
        if not isinstance(entry, dict) or set(entry) != ENTRY_FIELDS:
            raise ValueError("commemorationes: exact commemoration entry fields required")
        if (
            not isinstance(entry["id"], str)
            or not IDENTITY.fullmatch(entry["id"])
            or entry["id"] in identities
        ):
            raise ValueError("commemorationes: invalid or duplicate commemoration identity")
        identities.append(entry["id"])
        if entry["rank"] not in RANKS:
            raise ValueError(f"commemorationes: {entry['id']} has an unknown rank")
        ranks.append(entry["rank"])
        if not isinstance(entry["title"], str) or not entry["title"].strip():
            raise ValueError(f"commemorationes: {entry['id']} needs a Latin title")
        slots = entry["slots"]
        if not isinstance(slots, list) or not slots:
            raise ValueError(f"commemorationes: {entry['id']} has no slots")
        for slot in slots:
            if not isinstance(slot, dict) or set(slot) != SLOT_FIELDS:
                raise ValueError(
                    f"commemorationes: {entry['id']} slot fields differ from the contract"
                )
            if not all(isinstance(slot[key], str) and slot[key] for key in ("key", "after")):
                raise ValueError(
                    f"commemorationes: {entry['id']} slot values must be nonempty strings"
                )
            if slot["text"] is not None and (
                not isinstance(slot["text"], str)
                or not re.fullmatch(r"[a-z]+/[a-z0-9-]+", slot["text"])
            ):
                raise ValueError(
                    f"commemorationes: {entry['id']} slot text must be a slash address"
                )
        unaddressed = [slot["text"] is None for slot in slots]
        if any(unaddressed) and not all(unaddressed):
            raise ValueError(
                f"commemorationes: {entry['id']} slots are all addressed or all resolved per pair"
            )
        if all(unaddressed) and [slot["key"] for slot in slots] != list(ORATIONS):
            raise ValueError(
                f"commemorationes: {entry['id']} resolved slots must be " + ", ".join(ORATIONS)
            )
        resolved.append(all(unaddressed))
    if identities != sorted(identities):
        raise ValueError("commemorationes: commemorations must be in identity order")
    masses = table["masses"]
    if (
        not isinstance(masses, list)
        or not masses
        or masses != sorted(set(masses))
        or any(not isinstance(m, str) or not IDENTITY.fullmatch(m) or m == "none" for m in masses)
    ):
        raise ValueError("commemorationes: masses must be sorted unique identities")

    def civil(value: object) -> str:
        try:
            if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
                raise ValueError
        except ValueError:
            raise ValueError("commemorationes: canonical civil date required") from None
        return value

    occurrences = table["occurrences"]
    if not isinstance(occurrences, list):
        raise ValueError("commemorationes: occurrences must be a sorted list")
    seen: set[tuple[str, int]] = set()
    for row in occurrences:
        if (
            not isinstance(row, list)
            or len(row) != 2
            or type(row[1]) is not int
            or not 0 <= row[1] < len(identities)
        ):
            raise ValueError("commemorationes: occurrence rows are [date, commemoration]")
        key = (civil(row[0]), row[1])
        if key in seen:
            raise ValueError("commemorationes: duplicate occurrence")
        seen.add(key)
    # Typed rows compare as (date, number, ...) tuples: numeric order, never string order.
    if occurrences != sorted(occurrences):
        raise ValueError("commemorationes: occurrences must be a sorted list")
    pairs = table["pairs"]
    if not isinstance(pairs, list):
        raise ValueError("commemorationes: pairs must be a sorted list")
    used: set[tuple[str, int, int]] = set()
    places: dict[tuple[str, int, int], list[int]] = {}
    width = 4 + len(SITUATIONS)
    for row in pairs:
        if (
            not isinstance(row, list)
            or len(row) != width + 1
            or any(type(value) is not int for value in row[1:width])
            or not 0 <= row[1] < len(masses)
            or not 0 <= row[2] < len(identities)
            or not 0 <= row[3] < len(PROFILES)
            or any(not 0 <= value < len(DECISIONS) for value in row[4:width])
            or not (
                row[width] is None
                or (isinstance(row[width], str) and IDENTITY.fullmatch(row[width]))
            )
        ):
            raise ValueError(
                "commemorationes: pair rows are [date, mass, commemoration, profile, "
                + ", ".join(SITUATIONS)
                + ", resolved formulary or null]"
            )
        day = civil(row[0])
        if (day, row[2]) not in seen:
            raise ValueError("commemorationes: a pair must fall on a published occurrence")
        triple = (day, row[1], row[2])
        if triple in used:
            raise ValueError("commemorationes: duplicate pair")
        used.add(triple)
        plan, formulary = row[4:width], row[width]
        if resolved[row[2]] != (formulary is not None):
            raise ValueError(
                "commemorationes: a pair names its formulary exactly when its commemoration's "
                "slots are resolved per pair"
            )
        if formulary is not None and ADMITTED in plan and formulary not in masses:
            raise ValueError(
                "commemorationes: an admitted resolved commemoration needs an authored formulary"
            )
        if formulary in ADVENT_EMBER_DAYS.values() and (
            formulary in masses or plan != [DE_TEMPORE_UNAVAILABLE] * len(SITUATIONS)
        ):
            raise ValueError(
                "commemorationes: a pair resolved to an Ember day of Advent names its own Mass, "
                "not authored in this edition, and is unavailable in all three situations"
            )
        unavailable = formulary is not None and plan == [DE_TEMPORE_UNAVAILABLE] * len(SITUATIONS)
        if (
            ranks[row[2]] == "privileged"
            and plan != [ADMITTED] * len(SITUATIONS)
            and not unavailable
        ):
            raise ValueError(
                "commemorationes: a privileged commemoration is made in all Masses, or stated "
                "unavailable in all where its resolved formulary is not in this edition"
            )
        if ranks[row[2]] == "ordinary" and (plan[0] != plan[1] or plan[2] != NOT_ADMITTED):
            raise ValueError(
                "commemorationes: an ordinary commemoration has one decision for low and sung "
                "conventual Masses and is not admitted in a sung Mass that is not conventual"
            )
        if (
            ranks[row[2]] == "ordinary"
            and formulary is not None
            and plan != [ADMITTED, ADMITTED, NOT_ADMITTED]
        ):
            raise ValueError(
                "commemorationes: a resolved ordinary commemoration is admitted in low and sung "
                "conventual Masses, its formulary being in this edition"
            )
        for situation, value in enumerate(plan):
            places.setdefault((day, row[1], situation), []).append(value)
    for (day, _mass, situation), values in places.items():
        if values.count(ADMITTED) > 1 or (ADMITTED in values and DE_TEMPORE_UNAVAILABLE in values):
            raise ValueError(
                f"commemorationes: {day} {SITUATIONS[situation]} admits more than the single "
                "commemoration this contract models"
            )
    if pairs != sorted(pairs):
        raise ValueError("commemorationes: pairs must be a sorted list")

"""Authored commemoration assemblies: a privileged or ordinary set of orations that joins a
Mass of the day under the rubrics, addressed by its own occurrence rule rather than by the
winning Mass. The Greater Litanies (Rubricae generales 80–81, 108–109 f, 111, 434–437) are
privileged; St Petronilla on 31 May (proper of the Saints, after the Queenship of the Blessed
Virgin Mary) is ordinary; the impeded Sunday (RG 15–18, 108–109 a) is privileged and joins the
Mass of the first-class feast that takes its place. Each has three orations, each after the
corresponding Mass oration under its own conclusion.

The authored document owns identity, rank, occurrence rule and the three ordered slots; the
calendar computes the dates; nothing here infers a procession, a local calendar or an Office.
The scope is closed: the one privileged fixed-date rule this edition models, the impeded Sunday
under the first-class feasts that owe its commemoration, and an ordinary commemoration only on
a fixed date whose competing commemorations the selector models.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

from build_reader import store

SCHEMA = "1.2.0"
TITLE_SCHEMA = "1.0.0"
KEYS = {
    "commemoration_schema",
    "id",
    "title",
    "rank",
    "scope",
    "occurrence",
    "conclusion",
    "slots",
    "rubrics",
}
# A proper slot addresses proprium.<text_prefix>-<key>; the prefix defaults to the identity
# (the Greater Litanies) and is stated when the texts carry the saint's genitive name.
OPTIONAL_KEYS = {"text_prefix"}
TITLE_KEYS = {"commemoration_schema", "id", "language", "title"}
OCCURRENCE_KEYS = {"month", "day", "transfer"}
# The second occurrence kind names no date: the commemoration occurs wherever one of the named
# feasts is kept on a Sunday it impedes, and the calendar resolves which Sunday that is.
DISPLACED_KEYS = {"kind", "feasts"}
DISPLACED_SUNDAY = "displaced-sunday"
# RG 15–16 and 109 a: a first-class feast that is not a feast of the Lord takes the place of a
# Sunday, which is then commemorated (the Immaculate Conception even the Second Sunday of
# Advent, 15). A feast of the Lord and the feasts of 17 take the place with no commemoration
# (16 a, 17, 112 b), so the Precious Blood is not here; St Joseph, Spouse, and the Annunciation
# always meet a first-class Sunday of Lent or Passiontide and are transferred (96), and a Sunday
# is preferred to All Souls, which moves to the Monday (16 b, 96 b). These are the remaining
# first-class days of this calendar's sanctoral, in identity order.
DISPLACED_SUNDAY_FEASTS = (
    "assumptio-beatae-mariae-virginis",
    "dedicatio-sancti-michaelis-archangeli",
    "immaculata-conceptio",
    "nativitas-sancti-ioannis-baptistae",
    "omnium-sanctorum",
    "sancti-ioseph-opificis",
    "sancti-petri-et-pauli-apostolorum",
)
SLOT_KEYS = {"key", "after", "text", "relation"}
RUBRIC_KEYS = {"date", "scope", "rank", "admission", "conclusion"}
RANKS = ("privileged", "ordinary")
SCOPES = ("missa",)
CONCLUSIONS = ("separate",)
TRANSFERS = ("easter-sunday-or-monday-to-tuesday", "none")
# The rule each rank may use. The Greater Litanies are the one privileged fixed-date occurrence
# this edition models; an ordinary commemoration is fixed to its day and never transferred.
RANK_TRANSFERS = {
    "privileged": ("easter-sunday-or-monday-to-tuesday",),
    "ordinary": ("none",),
}
# The occurrence kinds each rank may use besides a fixed date: the commemoration of a Sunday
# is privileged (RG 109 a).
RANK_KINDS: dict[str, tuple[str, ...]] = {"privileged": (DISPLACED_SUNDAY,), "ordinary": ()}
# Fixed dates on which the selector models every commemoration that can compete for the
# single second-class place (kalendarium/commemorationes.py): 31 May, where the impeded Vigil
# of the Ascension is the only de Tempore day that can meet a second-class feast.
ORDINARY_DATES = ((5, 31),)
SLOT_ORDER = ("collecta", "secreta", "postcommunio")
# `calendar` names no text: the calendar resolves it per date to the impeded Sunday's own
# oration of that role, as the Sunday's formulary assembles it.
RELATIONS = ("proper", "reference", "calendar")
IDENTITY = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")


def documents(corpus: Path) -> list[tuple[Path, dict]]:
    return [
        (path, json.loads(path.read_text(encoding="utf-8")))
        for path in sorted((corpus / "commemorationes").glob("*.json"))
    ]


def language_documents(corpus: Path, language: str) -> list[tuple[Path, dict]]:
    return [
        (path, json.loads(path.read_text(encoding="utf-8")))
        for path in sorted((corpus / "languages" / language / "commemorationes").glob("*.json"))
    ]


def slot_texts(corpus: Path) -> Counter[str]:
    """Every text a commemoration slot reaches, counted per use."""
    uses: Counter[str] = Counter()
    for _path, doc in documents(corpus):
        for slot in doc.get("slots") or []:
            if isinstance(slot, dict) and isinstance(slot.get("text"), str):
                uses[slot["text"]] += 1
    return uses


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _displaced_errors(identity: str, doc: dict, occurrence: dict) -> list[str]:
    """The impeded-Sunday occurrence: the closed feast list, a privileged rank, no prefix."""
    from kalendarium.sanctorale import FESTA

    errors = []
    if set(occurrence) != DISPLACED_KEYS or occurrence["kind"] != DISPLACED_SUNDAY:
        errors.append(
            f"{identity}: occurrence kind needs exactly kind {DISPLACED_SUNDAY!r} and feasts"
        )
    elif occurrence["feasts"] != list(DISPLACED_SUNDAY_FEASTS):
        errors.append(
            f"{identity}: feasts must be exactly the first-class feasts that impede a Sunday "
            "and commemorate it, in identity order"
        )
    first_class = {feast.formulary for feast in FESTA if feast.dies_class == 1}
    if not set(DISPLACED_SUNDAY_FEASTS) <= first_class:
        errors.append(f"{identity}: an impeding feast is not a first-class feast of the calendar")
    if doc["rank"] in RANKS and DISPLACED_SUNDAY not in RANK_KINDS[doc["rank"]]:
        errors.append(
            f"{identity}: a {doc['rank']} commemoration cannot use occurrence kind "
            f"{DISPLACED_SUNDAY!r}"
        )
    if "text_prefix" in doc:
        errors.append(f"{identity}: text_prefix addresses proper slots, which this kind has not")
    return errors


def check(corpus: Path) -> tuple[list[str], dict[str, int]]:
    """Return errors and non-vacuous denominators for the authored commemorations."""
    errors: list[str] = []
    rows = documents(corpus)
    text_ids = {f"{path.parent.name}.{path.stem}" for path in (corpus / "texts").glob("*/*.json")}
    seen: set[str] = set()
    relations: Counter[str] = Counter()
    for path, doc in rows:
        where = path.relative_to(corpus).as_posix()
        if not isinstance(doc, dict) or not KEYS <= set(doc) <= KEYS | OPTIONAL_KEYS:
            errors.append(
                f"{where}: exact commemoration fields required {sorted(KEYS)} "
                f"(optional {sorted(OPTIONAL_KEYS)})"
            )
            continue
        identity = doc["id"]
        if (
            not isinstance(identity, str)
            or not IDENTITY.fullmatch(identity)
            or identity != path.stem
        ):
            errors.append(f"{where}: id must be a valid identity matching the file name")
            continue
        if identity in seen:
            errors.append(f"{where}: duplicate commemoration {identity}")
        seen.add(identity)
        prefix = doc.get("text_prefix", identity)
        if "text_prefix" in doc and (
            not isinstance(prefix, str) or not IDENTITY.fullmatch(prefix) or prefix == identity
        ):
            errors.append(f"{identity}: text_prefix must be a distinct valid identity")
            prefix = identity
        if doc["commemoration_schema"] != SCHEMA:
            errors.append(f"{identity}: commemoration_schema must be {SCHEMA}")
        if not _nonempty(doc["title"]):
            errors.append(f"{identity}: title is empty")
        if doc["rank"] not in RANKS:
            errors.append(f"{identity}: unknown rank {doc['rank']!r}")
        if doc["scope"] not in SCOPES:
            errors.append(f"{identity}: unknown scope {doc['scope']!r}")
        if doc["conclusion"] not in CONCLUSIONS:
            errors.append(f"{identity}: unknown conclusion rule {doc['conclusion']!r}")
        occurrence = doc["occurrence"]
        displaced = isinstance(occurrence, dict) and "kind" in occurrence
        if displaced:
            errors.extend(_displaced_errors(identity, doc, occurrence))
        elif not isinstance(occurrence, dict) or set(occurrence) != OCCURRENCE_KEYS:
            errors.append(f"{identity}: occurrence needs exactly month, day and transfer")
        else:
            month, day = occurrence["month"], occurrence["day"]
            try:
                if type(month) is not int or type(day) is not int:
                    raise ValueError
                date(2026, month, day)
            except ValueError:
                errors.append(f"{identity}: occurrence month/day is not a civil date")
            if occurrence["transfer"] not in TRANSFERS:
                errors.append(f"{identity}: unknown transfer rule {occurrence['transfer']!r}")
            elif doc["rank"] in RANKS and occurrence["transfer"] not in RANK_TRANSFERS[doc["rank"]]:
                errors.append(
                    f"{identity}: a {doc['rank']} commemoration cannot use transfer rule "
                    f"{occurrence['transfer']!r}"
                )
            if doc["rank"] == "ordinary" and (month, day) not in ORDINARY_DATES:
                errors.append(
                    f"{identity}: an ordinary commemoration on {month}/{day} is outside the "
                    "fixed dates whose competing commemorations the selector models"
                )
        slots = doc["slots"]
        if not isinstance(slots, list) or len(slots) != len(SLOT_ORDER):
            errors.append(f"{identity}: exactly {len(SLOT_ORDER)} ordered slots required")
            slots = []
        for position, slot in enumerate(slots):
            if not isinstance(slot, dict) or set(slot) != SLOT_KEYS:
                errors.append(
                    f"{identity}: slot {position} needs exactly key, after, text, relation"
                )
                continue
            expected_key = SLOT_ORDER[position]
            if slot["key"] != expected_key or slot["after"] != expected_key:
                errors.append(
                    f"{identity}: slot {position} must be {expected_key!r} "
                    f"after the Mass {expected_key}"
                )
            target, relation = slot["text"], slot["relation"]
            if displaced or relation == "calendar":
                if not displaced or relation != "calendar":
                    errors.append(
                        f"{identity}:{slot['key']}: the calendar relation is used by, and only "
                        "by, the impeded-Sunday occurrence"
                    )
                elif target is not None:
                    errors.append(
                        f"{identity}:{slot['key']}: a calendar slot names no text; the calendar "
                        "resolves it per date"
                    )
                else:
                    relations[relation] += 1
                continue
            if not isinstance(target, str) or target not in text_ids:
                errors.append(f"{identity}:{slot['key']}: missing text {target!r}")
                continue
            if relation not in RELATIONS:
                errors.append(f"{identity}:{slot['key']}: unknown relation {relation!r}")
                continue
            relations[relation] += 1
            own = f"proprium.{prefix}-{expected_key}"
            if relation == "proper" and target != own:
                errors.append(f"{identity}:{slot['key']}: proper relation must address {own}")
            if relation == "reference" and (not target.startswith("proprium.") or target == own):
                errors.append(f"{identity}:{slot['key']}: reference must address another proprium")
        rubrics = doc["rubrics"]
        if not isinstance(rubrics, dict) or set(rubrics) != RUBRIC_KEYS:
            errors.append(f"{identity}: rubrics need exactly {sorted(RUBRIC_KEYS)}")
        elif not all(_nonempty(value) for value in rubrics.values()):
            errors.append(f"{identity}: every rubric citation must be a nonempty string")
    for language in store.language_ids(corpus):
        localized = {}
        for path, doc in language_documents(corpus, language):
            where = path.relative_to(corpus).as_posix()
            if not isinstance(doc, dict) or set(doc) != TITLE_KEYS:
                errors.append(f"{where}: exact localized fields required {sorted(TITLE_KEYS)}")
                continue
            if doc["commemoration_schema"] != TITLE_SCHEMA:
                errors.append(f"{where}: commemoration_schema must be {TITLE_SCHEMA}")
            if doc["id"] != path.stem or doc["language"] != language:
                errors.append(f"{where}: id/language does not match its path")
            if not _nonempty(doc["title"]):
                errors.append(f"{where}: localized title is empty")
            localized[path.stem] = doc
        missing = sorted(seen - set(localized))
        extra = sorted(set(localized) - seen)
        if missing:
            errors.append(f"commemorationes:{language}: missing titles for {', '.join(missing)}")
        if extra:
            errors.append(f"commemorationes:{language}: unknown titles for {', '.join(extra)}")
    counts = {
        "commemorations": len(rows),
        "slot_uses": sum(relations.values()),
        "proper_slots": relations["proper"],
        "reference_slots": relations["reference"],
        "calendar_slots": relations["calendar"],
    }
    return errors, counts

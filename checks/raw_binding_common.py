"""One pinned literal Postcommunion inherited from a Common through the Mass data.

The feast file only selects the Common: its Rank and Rule declare ``ex C8`` and
it has no Postcommunio of its own. The Common supplies the body and its
``$Per Dominum`` cue, which the Mass Ordo prayer file expands. Every bound line
is asserted exactly; the reading keeps the source's literal spelling, accents,
capitalization and punctuation and drops only the conclusion's line-initial
``r. ``/``R. `` framing. No upstream program runs here and nothing is
normalized beyond whitespace. The result proves textual identity only.
"""

from __future__ import annotations

import hashlib
import re
from copy import deepcopy

from .raw_binding import BindingError, BoundReading, _space

PROFILE = "roman1960-latin-missa-c8-postcommunio"
REVISION = "44667ff518b8ff1439780470828b39714f5306a2"
DECLARATION = "ex C8"
ABSENT = "[Postcommunio]"
CUE = "$Per Dominum"
# role -> (upstream path, complete archive SHA-256, {record: (line, literal or None)})
ROLES: dict[str, tuple[str, str, dict[str, tuple[int, str | None]]]] = {
    "selection": (
        "web/www/missa/Latin/Sancti/11-09.txt",
        "a80d47d0b5f190830ce15f3926bdc7925a5f04467d44835b461915207d4ba8f9",
        {
            "rank_heading": (1, "[Rank]"),
            "rank": (2, None),
            "rule_heading": (4, "[Rule]"),
            "rule": (5, None),
        },
    ),
    "body": (
        "web/www/horas/Latin/Commune/C8.txt",
        "4259d9ddd8669a6a6dcb8de2ac7bfd918e3e39a4e8fe8a5bc04b28afdb97c5c8",
        {"heading": (640, ABSENT), "text": (641, None), "cue": (642, CUE)},
    ),
    "conclusion": (
        "web/www/missa/Latin/Ordo/Prayers.txt",
        "7bf86beb01c170212fa07438de45b16b321f117013321400d65c2229c6624d9b",
        # The cue's only destination is this Mass Ordo section of the same name.
        {"heading": (95, f"[{CUE[1:]}]"), "formula": (96, None), "amen": (97, None)},
    ),
}
PREFIXES = {"formula": "r. ", "amen": "R. "}
PATH = (
    "selection, context only: web/www/missa/Latin/Sancti/11-09.txt [Rank] (lines 1-2), "
    "[Rule] (lines 4-5), no [Postcommunio]; "
    "body: web/www/horas/Latin/Commune/C8.txt [Postcommunio] (lines 640-642); "
    "conclusion: web/www/missa/Latin/Ordo/Prayers.txt [Per Dominum] (lines 95-97)"
)
CONTROL = ("!", "[", "#", "_", "&", "@", "$")


def profile() -> dict:
    """The complete closed profile, recorded in the source subject."""
    return {
        "id": PROFILE,
        "revision": REVISION,
        "declaration": DECLARATION,
        "absent_heading": ABSENT,
        "cue": CUE,
        "prefixes": dict(PREFIXES),
        "path": PATH,
        "roles": {
            role: {
                "upstream": upstream,
                "sha256": sha256,
                "records": {
                    name: {"line": line, "text": literal}
                    for name, (line, literal) in records.items()
                },
            }
            for role, (upstream, sha256, records) in ROLES.items()
        },
    }


def _section(lines: tuple[str, ...], heading: int) -> list[int]:
    """Nonblank physical line numbers after a heading, up to the next heading."""
    numbers = []
    for number in range(heading + 1, len(lines) + 1):
        if lines[number - 1].startswith("["):
            break
        if lines[number - 1].strip():
            numbers.append(number)
    return numbers


def _unframed(line: str) -> bool:
    return (
        bool(line.strip())
        and line == line.strip()
        and not line.startswith(CONTROL)
        and "~" not in line
        and re.match(r"[DSMVROdsmvro]\.\s", line) is None
    )


def resolve_literal_common(text, headers, identity, binding, snapshot) -> BoundReading:
    """Bind the exact feast/Common/Mass chain; return no performer span or fragment."""
    if binding["revision"] != REVISION:
        raise BindingError("raw-reading-8 requires the pinned Latin revision")
    if binding["profile"] != PROFILE:
        raise BindingError("raw-reading-8 profile is not supported")
    keys = [binding[role]["archive"] for role in ROLES]
    if len(set(keys)) != len(keys):
        raise BindingError("raw-reading-8 requires three distinct archives")
    archives: dict[str, dict] = {}
    sources: dict[str, tuple[str, ...]] = {}
    for role, (upstream, sha256, records) in ROLES.items():
        item = binding[role]
        _, lines = snapshot._archive(item["archive"], binding["revision"])
        record = snapshot._registry["archives"][item["archive"]]
        if record["upstream"] != upstream:
            raise BindingError(f"raw-reading-8 {role} archive has the wrong upstream path")
        if record["sha256"] != sha256:
            raise BindingError(f"raw-reading-8 {role} requires the exact pinned archive object")
        for name, (line, literal) in records.items():
            if item[name]["line"] != line:
                raise BindingError(
                    f"raw-reading-8 {role} {name} requires its exact pinned coordinate"
                )
            if literal is not None and item[name]["text"] != literal:
                raise BindingError(f"raw-reading-8 {role} {name} must be the literal {literal}")
        archives[item["archive"]] = record
        sources[role] = lines
    selection, body, conclusion = binding["selection"], binding["body"], binding["conclusion"]
    if (
        selection["rank"]["text"].split(";;")[-1] != DECLARATION
        or selection["rule"]["text"].rstrip(";") != DECLARATION
    ):
        raise BindingError(
            "raw-reading-8 selection must bind the literal ex C8 Rank and Rule lines"
        )
    if selection["absent_heading"] != ABSENT:
        raise BindingError("raw-reading-8 selection must prove the feast has no own [Postcommunio]")
    if any(conclusion[name]["prefix"] != prefix for name, prefix in PREFIXES.items()):
        raise BindingError("raw-reading-8 conclusion requires the literal r. and R. prefixes")
    for role, (_, _, records) in ROLES.items():
        lines = sources[role]
        for name in records:
            item = binding[role][name]
            if not 1 <= item["line"] <= len(lines) or lines[item["line"] - 1] != item["text"]:
                raise BindingError(
                    f"raw-reading-8 {role} {name} differs from its exact physical line"
                )
    feast = sources["selection"]
    if any(line.startswith(ABSENT[:-1]) for line in feast):
        raise BindingError("raw-reading-8 selection must prove the feast has no own [Postcommunio]")
    if _section(feast, 1) != [2] or _section(feast, 4)[:1] != [5]:
        raise BindingError("raw-reading-8 selection must bind the complete Rank and Rule lines")
    common = sources["body"]
    if common.count(body["heading"]["text"]) != 1:
        raise BindingError("raw-reading-8 body requires the unique selected [Postcommunio] section")
    if _section(common, body["heading"]["line"]) != [body["text"]["line"], body["cue"]["line"]]:
        raise BindingError("raw-reading-8 body must bind the complete section through its cue")
    if not _unframed(body["text"]["text"]):
        raise BindingError("raw-reading-8 body line must be unframed text")
    ordo = sources["conclusion"]
    heading = conclusion["heading"]
    if ordo.count(heading["text"]) != 1 or _section(ordo, heading["line"]) != [
        conclusion["formula"]["line"],
        conclusion["amen"]["line"],
    ]:
        raise BindingError("raw-reading-8 conclusion must bind the complete [Per Dominum] section")
    pieces = [
        {
            "role": "body",
            "name": "text",
            "archive": body["archive"],
            "line": body["text"]["line"],
            "raw": body["text"]["text"],
            "remove_prefix": "",
            "text": body["text"]["text"],
        },
    ]
    for name, prefix in PREFIXES.items():
        raw = conclusion[name]["text"]
        if not raw.startswith(prefix) or not _unframed(raw[len(prefix) :]):
            raise BindingError("raw-reading-8 conclusion requires the literal r. and R. prefixes")
        pieces.append(
            {
                "role": "conclusion",
                "name": name,
                "archive": conclusion["archive"],
                "line": conclusion[name]["line"],
                "raw": raw,
                "remove_prefix": prefix,
                "text": raw[len(prefix) :],
            }
        )
    context = [
        {
            "role": role,
            "name": name,
            "archive": binding[role]["archive"],
            "line": binding[role][name]["line"],
            "text": binding[role][name]["text"],
        }
        for role, name in (
            ("selection", "rank_heading"),
            ("selection", "rank"),
            ("selection", "rule_heading"),
            ("selection", "rule"),
            ("body", "heading"),
            ("body", "cue"),
            ("conclusion", "heading"),
        )
    ]
    reading = _space(" ".join(piece["text"] for piece in pieces))
    if headers.get("path") != [PATH]:
        raise BindingError("witness path declarations differ from bound evidence")
    witnessed = _space("\n".join(line for line in text.splitlines() if not line.startswith("#")))
    if not witnessed or witnessed != reading:
        raise BindingError("transcription differs from its exact literal composition")
    source = {
        "contract": "raw-reading-8",
        "registry_version": snapshot._registry["version"],
        "binding_id": identity,
        "transcription_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "binding": binding,
        "archives": {key: archives[key] for key in sorted(archives)},
        "profile": profile(),
        "resolved_literal_composition": {"context": context, "pieces": pieces, "text": reading},
    }
    return BoundReading((), reading, deepcopy(source), ())

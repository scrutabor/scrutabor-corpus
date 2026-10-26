"""Two closed inherited Secret readings in the pinned Latin Mass context.

Commons physically reside in the Office tree, but the Mass caller loads its
prayers from Ordo. This is not a general macro interpreter or performer proof.
Only the two complete pinned chains below are admitted. No upstream code runs.
"""

from __future__ import annotations

import hashlib
from copy import deepcopy
from typing import TypedDict

from .raw_binding import BindingError, BoundReading, _space

Section = tuple[str, int, int, str]


class SecretChain(TypedDict):
    text: str
    sections: tuple[Section, ...]


REVISION = "44667ff518b8ff1439780470828b39714f5306a2"
PROFILE = "roman1960-latin-missa-two-inherited-secrets"
CONCLUSION: Section = ("prayers", 95, 97, "Per Dominum")
ORDO = "missa-ordo-44667ff"
# Key -> exact upstream path and complete original component digest.
ARCHIVES: dict[str, tuple[str, str]] = {
    "do-sancti-10-11": (
        "web/www/missa/Latin/Sancti/10-11.txt",
        "606473b4f90e617b60963fb74ed42e82055c7f73f56fdbba969f6753a8f24b16",
    ),
    "all-saints": (
        "web/www/missa/Latin/Sancti/11-01.txt",
        "b6e49964e28e5a136b4733ef923255e1c2a279e9818a21247e8315abc58e4112",
    ),
    "common-c10": (
        "web/www/horas/Latin/Commune/C10.txt",
        "463fcb39e6d91e899a4da4c608ecb0d45d51f1d983769efceaad975a69ab108e",
    ),
    "common-c11": (
        "web/www/horas/Latin/Commune/C11.txt",
        "cff3086e9c0f698b67c7fa0972d2b8cd7a953b4fe45fbf23100ec471db27c428",
    ),
    "common-c3a": (
        "web/www/horas/Latin/Commune/C3a.txt",
        "023a499c135df597cd53da1232d042a2f3b603b432da704ad2c2739f56567312",
    ),
    "prayers": (
        "web/www/missa/Latin/Ordo/Prayers.txt",
        "7bf86beb01c170212fa07438de45b16b321f117013321400d65c2229c6624d9b",
    ),
    ORDO: (
        "web/www/missa/Latin/Ordo/Ordo.txt",
        "a7f63e8030325b809f74dd4587c649bf8eb45cdd150fc9a2817fe2a1ed6a42e3",
    ),
}
# Each entry declares every complete section through its inheritance cue.
CHAINS: dict[str, SecretChain] = {
    "secret-maternitas-do44667ff": {
        "text": "proprium.maternitas-beatae-mariae-virginis-secreta",
        "sections": (
            ("do-sancti-10-11", 46, 47, "@Commune/C10"),
            ("common-c10", 216, 217, "@Commune/C11"),
            ("common-c11", 400, 402, "$Per Dominum"),
        ),
    },
    "secret-omnium-sanctorum-do44667ff": {
        "text": "proprium.omnium-sanctorum-secreta",
        "sections": (
            ("all-saints", 41, 42, "@Commune/C3a"),
            ("common-c3a", 62, 64, "$Per Dominum"),
        ),
    },
}


def _extent(lines: tuple[str, ...], heading: int) -> list[int]:
    result = []
    for number in range(heading + 1, len(lines) + 1):
        if lines[number - 1].startswith("["):
            break
        if lines[number - 1].strip():
            result.append(number)
    return result


def resolve_mass_secret(text, headers, identity, binding, snapshot) -> BoundReading:
    """Resolve only a complete closed chain; retain no performer spans."""
    if binding["profile"] != PROFILE or identity not in CHAINS:
        raise BindingError("raw-reading-9 requires a supported closed Mass Secret profile")
    chain = CHAINS[identity]
    if binding["revision"] != REVISION or binding["witness"] != f"witnesses/{chain['text']}/do.txt":
        raise BindingError("raw-reading-9 requires its exact witness and revision")
    sections = chain["sections"]
    keys = [item[0] for item in sections] + [CONCLUSION[0], ORDO]
    archives, sources = {}, {}  # type: tuple[dict[str, dict], dict[str, tuple[str, ...]]]
    for key in keys:
        _, lines = snapshot._archive(key, REVISION)
        record = snapshot._registry["archives"][key]
        upstream, digest = ARCHIVES[key]
        if record["upstream"] != upstream or record["sha256"] != digest:
            raise BindingError("raw-reading-9 requires the exact pinned source objects")
        archives[key], sources[key] = record, lines
    declarations, context = [], []  # type: tuple[list[str], list[dict]]
    for key, heading, last, cue in sections:
        lines = sources[key]
        body_numbers = list(range(heading + 1, last + 1))
        if (
            lines[heading - 1] != "[Secreta]"
            or lines.count("[Secreta]") != 1
            or _extent(lines, heading) != body_numbers
            or lines[last - 1] != cue
        ):
            raise BindingError("raw-reading-9 requires the complete literal Secret chain")
        declarations.append(f"{ARCHIVES[key][0]} [Secreta] (lines {heading}-{last})")
        context.extend(
            {"archive": key, "line": number, "text": lines[number - 1]}
            for number in [heading, last]
        )
    prayers = sources[CONCLUSION[0]]
    if (
        prayers[94] != "[Per Dominum]"
        or prayers.count("[Per Dominum]") != 1
        or _extent(prayers, 95) != [96, 97]
        or not prayers[95].startswith("r. ")
        or prayers[96] != "R. Amen."
    ):
        raise BindingError("raw-reading-9 requires the complete Mass conclusion and response")
    declarations.append(f"{ARCHIVES['prayers'][0]} [Per Dominum] (lines 95-97)")
    # Complete bytes are bound above; these coordinates preserve the visible
    # call and its surrounding Secret/Preface rubric rather than a free context.
    ordo = sources[ORDO]
    if ordo[197] != "!!Secreta" or ordo[198] != "&secreta":
        raise BindingError("raw-reading-9 requires the actual Mass Ordo Secret call")
    context.extend(
        {"archive": ORDO, "line": number, "text": ordo[number - 1]} for number in range(196, 203)
    )
    context.append({"archive": "prayers", "line": 95, "text": prayers[94]})
    key, heading, _, _ = sections[-1]
    pieces: list[dict] = [
        {
            "archive": key,
            "line": heading + 1,
            "raw": sources[key][heading],
            "remove_prefix": "",
            "text": sources[key][heading],
        },
        {
            "archive": "prayers",
            "line": 96,
            "raw": prayers[95],
            "remove_prefix": "r. ",
            "text": prayers[95][3:],
        },
        {
            "archive": "prayers",
            "line": 97,
            "raw": prayers[96],
            "remove_prefix": "R. ",
            "text": prayers[96][3:],
        },
    ]
    reading = _space(" ".join(piece["text"] for piece in pieces))
    body = _space("\n".join(line for line in text.splitlines() if not line.startswith("#")))
    if headers.get("path") != ["; ".join(declarations)]:
        raise BindingError("witness path declarations differ from bound evidence")
    if not body or body != reading:
        raise BindingError("transcription differs from its exact Mass Secret reading")
    profile = {
        "id": PROFILE,
        "text": chain["text"],
        "revision": REVISION,
        "logical_caller": "missa",
        "sections": [list(item) for item in sections],
        "conclusion": list(CONCLUSION),
        "ordo": ORDO,
        "archive_roles": {
            key: {"upstream": ARCHIVES[key][0], "sha256": ARCHIVES[key][1]} for key in sorted(keys)
        },
    }
    source = {
        "contract": "raw-reading-9",
        "registry_version": snapshot._registry["version"],
        "binding_id": identity,
        "transcription_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "binding": binding,
        "archives": {key: archives[key] for key in sorted(archives)},
        "profile": profile,
        "resolved_literal_composition": {"context": context, "pieces": pieces, "text": reading},
    }
    return BoundReading((), reading, deepcopy(source), ())

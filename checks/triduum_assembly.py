"""Closed Communion prescriptions of the two represented 1962 Triduum Masses."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

THURSDAY = "feria-v-in-cena-domini"
VIGIL = "vigilia-paschalis"
MASSES = (THURSDAY, VIGIL)
AGNUS = "ordinarium.agnus-dei-in-cena-domini"
SCHEMA = "1.6.0"
PEACE = {"text": "ordinarium.qui-dixisti", "reason": "triduum-peace-prayer"}
OMISSIONS = {
    THURSDAY: [
        {"text": "ordinarium.lavabo", "segments": ["s09", "s10"], "reason": "lavabo-doxology"},
        PEACE,
    ],
    VIGIL: [{"text": "ordinarium.agnus-dei", "reason": "vigil-agnus-dei"}, PEACE],
}
COMPONENT = {"key": "agnus-dei", "role": "agnus-dei", "text": AGNUS, "relation": "shared"}
LINE = "Agnus Dei, qui tollis peccáta mundi: miserére nobis."
# Whole omitted and explicitly retained study bodies, checked before projection.
TARGETS: dict[str, str] = {
    "ordinarium.agnus-dei": "47aeb0536a2c6ad4684ee8d12b205105c697cd7d4650a9b46d209d3e6aad2ff3",
    "ordinarium.qui-dixisti": "55b19faace7d84c1eefe7d43a11577bdc5e30794d518da821ad689e2f9b5a28d",
    "ordinarium.pax-domini": "87954024ee7f1af36a975a8175c75fd368fab8e0a59a11ce1ce85fc54ce89281",
    "ordinarium.haec-commixtio": "7f48cbed12d833774bfba79574fae40adff67c5c096ba2d95ff14b2c4df607b6",
    "ordinarium.fili-dei-vivi": "92a2c70476cb02e569cbe72ff31f5ad7c0be89ebea1384886630bb021e1ded8f",
    "ordinarium.perceptio-corporis": (
        "a144c90348c0b08094f23d584e864f0d343ad309a86c69ec399ef2c2140a5a23"
    ),
}


def is_triduum(doc: dict) -> bool:
    return doc.get("id") in MASSES or doc.get("observance") in MASSES


def body_hash(doc: dict) -> str:
    selected = {
        "id": doc["id"],
        "segments": [
            {k: s[k] for k in ("id", "type", "text", "speaker", "voice", "words") if k in s}
            for s in doc["segments"]
        ],
    }
    return hashlib.sha256(
        json.dumps(selected, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def agnus_errors(doc: dict) -> list[str]:
    """Each occurrence has its own stable cards; no rule-derived third petition."""
    from checks.participation_performance import publication_errors

    try:
        rows = doc["segments"]
        words = [w for s in rows for w in s["words"]]
        if (
            doc.get("id") != AGNUS
            or doc.get("ids") != {"next": 25, "segments": {"next": 4}}
            or [s["id"] for s in rows] != ["s01", "s02", "s03"]
            or [w["id"] for w in words] != [f"w{i:03}" for i in range(1, 25)]
            or any(len(s["words"]) != 8 for s in rows)
            or any(
                " ".join(w.get("pre", "") + w["form"] + w.get("post", "") for w in s["words"])
                != LINE
                for s in rows
            )
        ):
            return ["Triduum Agnus requires three complete eight-word mercy invocations"]
        return publication_errors(doc)
    except (KeyError, TypeError, AttributeError):
        return ["Triduum Agnus requires complete structured source rows"]


def target_errors(corpus: Path) -> list[str]:
    errors = []
    for identity, expected in TARGETS.items():
        try:
            doc = json.loads((corpus / f"texts/{identity.replace('.', '/', 1)}.json").read_text())
            if body_hash(doc) != expected:
                errors.append(f"Triduum target: {identity} complete source body differs")
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            errors.append(f"Triduum target: {identity}: {error}")
    return errors


def assembly_errors(doc: dict, corpus: Path) -> list[str]:
    from checks.lavabo_omissions import target_errors as lavabo_errors

    errors = []
    identity = doc.get("id")
    if identity not in MASSES:
        return ["Triduum assembly requires the exact authored Mass identity"]
    if (
        doc.get("observance") != identity
        or doc.get("collection") != "temporale"
        or doc.get("season") != ("passionis" if identity == THURSDAY else "paschale")
        or doc.get("calendar") != {"key": identity, "default": True}
    ):
        errors.append("Triduum assembly requires the exact authored date/Mass identity")
    if doc.get("formulary_schema") != SCHEMA:
        errors.append(f"formulary_schema must be {SCHEMA}")
    if doc.get("ordinary_omissions") != OMISSIONS[identity]:
        errors.append("ordinary_omissions must contain the exact Triduum prescriptions")
    components = doc.get("components")
    if not isinstance(components, list) or any(not isinstance(c, dict) for c in components):
        return [*errors, "Triduum assembly components must be objects"]
    rows = [(i, c) for i, c in enumerate(components) if c.get("role") == "agnus-dei"]
    if identity == THURSDAY:
        if (
            len(rows) != 1
            or rows[0][1] != COMPONENT
            or rows[0][0] == 0
            or rows[0][0] + 1 >= len(components)
            or components[rows[0][0] - 1].get("role") != "praefatio"
            or components[rows[0][0] + 1].get("role") != "communio"
        ):
            errors.append(
                "Triduum assembly requires its shared Agnus between Preface and Communion"
            )
        errors.extend(lavabo_errors(corpus))
        try:
            body = json.loads(
                (corpus / "texts/ordinarium/agnus-dei-in-cena-domini.json").read_text()
            )
            errors.extend(agnus_errors(body))
        except (OSError, ValueError) as error:
            errors.append(f"Triduum Agnus body: {error}")
    elif rows or any(c.get("text") in (AGNUS, "ordinarium.agnus-dei") for c in components):
        errors.append("Vigil assembly must not acquire an Agnus Dei component")
    errors.extend(target_errors(corpus))
    return errors

"""Source-defined Lauds inside the Easter Vigil Mass.

MR1962 pp. 216–218 assigns sung delivery, with an explicit celebrant/cantor
handover only at the opening Benedictus antiphon. Office delivery is not a
low-Mass base or a congregational participation grade.
"""

from typing import Any

PSALMUS = "proprium.vigilia-paschalis-laudes-psalmus"
CANTICUM = "proprium.vigilia-paschalis-laudes-canticum"
TEXTS = frozenset({PSALMUS, CANTICUM})


def is_office(doc: dict[str, Any]) -> bool:
    return doc.get("id") in TEXTS


def sung_delivery(doc: dict[str, Any], seg: dict[str, Any]) -> dict[str, Any]:
    if seg.get("type") != "verse":
        return {}
    fields = {"voice": "cantus"}
    if doc.get("id") == CANTICUM and seg.get("id") in {"s01", "s02"}:
        fields["speaker"] = "sacerdos" if seg["id"] == "s01" else "schola"
    return {"cantu": fields}


def base_errors(doc: dict[str, Any]) -> list[str]:
    if not is_office(doc):
        return []
    return [
        f"{seg['id']}: Vigil Lauds has no established low-Mass base {field}"
        for seg in doc.get("segments", [])
        for field in ("speaker", "voice")
        if field in seg
    ]

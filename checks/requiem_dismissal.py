"""Source-owned Requiem dismissal; generic cantu does not identify its minister."""

from __future__ import annotations

TEXT = "ordinarium.ite-missa-est-defunctorum"
ROWS = {
    "s01": (1, "Dóminus vobíscum", "sacerdos", "clara"),
    "s02": (3, "Et cum spíritu tuo", "minister", "clara"),
    "s03": (7, "Requiéscant in pace", None, None),
    "s04": (10, "Amen", "minister", "clara"),
}
DELIVERY = {
    "s01": {"cantu": {"speaker": "sacerdos", "voice": "cantus"}},
    "s02": {"cantu": {"speaker": "schola", "voice": "cantus"}},
    "s03": {"lecta": {"speaker": "sacerdos", "voice": "clara"}, "cantu": {"voice": "cantus"}},
    "s04": {"cantu": {"speaker": "schola", "voice": "cantus"}},
}


def base_errors(doc: dict) -> list[str]:
    if doc.get("id") != TEXT:
        return []
    errors = []
    segments = doc.get("segments", [])
    if [s.get("id") for s in segments] != list(ROWS):
        errors.append("Requiem dismissal requires the exact four source rows")
    for seg in segments:
        if seg.get("id") not in ROWS:
            continue
        first, forms, speaker, voice = ROWS[seg["id"]]
        expected = [(f"w{first + n:03}", form) for n, form in enumerate(forms.split())]
        if (
            seg.get("type") != "verse"
            or [(w.get("id"), w.get("form")) for w in seg.get("words", [])] != expected
        ):
            errors.append(f"{seg['id']}: Requiem dismissal source words/IDs differ")
        if seg.get("speaker") != speaker or seg.get("voice") != voice:
            errors.append(f"{seg['id']}: Requiem dismissal base actor/voice differs")
        if speaker is None and ("speaker" in seg or "voice" in seg):
            errors.append(f"{seg['id']}: Requiem dismissal has no generic base attribution")
    return errors


def delivery(doc: dict, seg: dict) -> dict:
    from copy import deepcopy

    if doc.get("id") == TEXT and not base_errors(doc):
        return deepcopy(DELIVERY.get(seg.get("id", ""), {}))
    return {}


def publication_errors(doc: dict) -> list[str]:
    errors = base_errors(doc)
    if doc.get("id") != TEXT:
        return errors
    for seg in doc.get("segments", []):
        if seg.get("delivery") != DELIVERY.get(seg.get("id")):
            errors.append(f"{seg.get('id')}: Requiem dismissal delivery differs")
        expected = (
            {
                "lecta": {"gradus": 1, "source": "DMS 31 a"},
                "cantu": {"gradus": 1, "source": "DMS 25 a"},
            }
            if seg.get("id") in ("s02", "s04")
            else None
        )
        if seg.get("participation") != expected:
            errors.append(f"{seg.get('id')}: Requiem dismissal participation differs")
    return errors

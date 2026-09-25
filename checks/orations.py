"""Closed ritual boundaries for expanded Proper orations.

RG 480–481 distinguishes the secret body from the LAST secret's audible
conclusion. RG 511 d/i and 513–514 govern collects/postcommunions and sung
delivery; the Ordo Missae prints Per omnia ... R. Amen before the preface.
DMS 16 b, 25 a/26 and 31 a distinguish that answer from priestly Amen.

RG 110 b joins the other Apostle's prayer to a Mass of St Peter or St Paul
"sub unica conclusione": the page prints the first prayer without a
conclusion, that rubric, and the second prayer carrying the single
conclusion. Only the printed rubric, standing between the two verses,
licenses a verse without its own conclusion.

This is deliberately not a general Amen matcher or a conclusion expander.
Only complete, separately modeled boundaries receive new derived labels.
An unsplit or abbreviated prayer fails without receiving new attribution.
The normal corpus gate runs this validator; ``python -m checks.orations``
also reports the complete boundary census independently.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from checks.normalize import substantive

ROOT = Path(__file__).resolve().parent.parent
GENERA = {"collecta", "secreta", "postcommunio"}
TAIL = ("per", "omnia", "saecula", "saeculorum")
DAWN = "proprium.nativitas-domini-in-aurora-"
PREFACE = "ordinarium.praefatio-dialogus"
UNICA = "sub unica conclusione"


def genus(doc: dict[str, Any]) -> str | None:
    piece = doc.get("id", "").rsplit("-", 1)[-1]
    return piece if doc.get("category") == "proprium" and piece in GENERA else None


def tokens(seg: dict[str, Any]) -> tuple[str, ...]:
    return tuple(substantive(w["form"], fold_ji=True) for w in seg.get("words", []))


def _dawn_nonfinal(verses: list[dict[str, Any]]) -> bool:
    """The actual two-secret Dawn arrangement, not a blanket first-Amen rule.

    MR1962 p.20 prints Munera nostra followed by Pro S. Anastasia / Accipe.
    Stable IDs bind this exception to that complete, still-selected sequence.
    Removing the second prayer invalidates it; new arrangements need review.
    """
    if len(verses) < 2:
        return False
    first, second = verses[:2]
    return (
        first.get("id") == "s01"
        and second.get("id") == "s03"
        and [w["id"] for w in first.get("words", [])] == [f"w{i:03d}" for i in range(1, 55)]
        and [w["id"] for s in verses[1:] for w in s.get("words", [])]
        == [f"w{i:03d}" for i in range(55, 96)]
        and tokens(first)[:2] == ("munera", "nostra")
        and tokens(first)[-5:] == (*TAIL, "amen")
        and tokens(second)[:1] == ("accipe",)
    )


def joined(doc: dict[str, Any]) -> set[str]:
    """Verses the printed rubric joins to the next prayer (RG 110 b).

    MR1962 pp. 477 and 479 print the Peter prayer, then "Et fit commemoratio
    S. Pauli Ap. sub unica conclusione:", then the Paul prayer ending Per
    Dominum; the two prayers count as one oration. A verse qualifies only
    when that rubric immediately follows it and another verse follows the
    rubric.
    """
    segs = doc.get("segments", [])
    return {
        first["id"]
        for first, rubric, second in zip(segs, segs[1:], segs[2:], strict=False)
        if first.get("type") == "verse"
        and rubric.get("type") == "rubric"
        and second.get("type") == "verse"
        and UNICA in substantive(rubric.get("text", ""))
    }


def structure(doc: dict[str, Any]) -> tuple[list[str], dict[str, str]]:
    """Return shape errors and segment roles, independent of stored labels.

    A shape error suppresses the entire new role map. Thus deriving labels
    never blesses an absorbed Amen, a partially split secret, or a shortened
    conclusion. Voice/speaker errors are separately checked, not used as
    evidence for deciding what the source-defined roles ought to be.
    """
    piece = genus(doc)
    if piece is None:
        return [], {}
    verses = [s for s in doc.get("segments", []) if s.get("type") == "verse"]
    errors: list[str] = []
    roles: dict[str, str] = {}
    first_prayers = joined(doc)
    for seg in verses:
        said = tokens(seg)
        if not said:
            errors.append(f"{seg['id']}: empty oration verse")
        if seg["id"] in first_prayers and (said[-1:] == ("deus",) or said[-4:] == TAIL):
            errors.append(
                f"{seg['id']}: a prayer joined sub unica conclusione has no conclusion of its own"
            )
        if said[-2:] in {("per", "dominum"), ("qui", "tecum"), ("qui", "vivis")} or said[-3:] == (
            "per",
            "eundem",
            "dominum",
        ):
            errors.append(f"{seg['id']}: abbreviated conclusion is not a complete enacted oration")
        if (
            len(said) > 1
            and "amen" in said
            and not (doc["id"] == DAWN + "secreta" and _dawn_nonfinal(verses) and seg is verses[0])
        ):
            errors.append(f"{seg['id']}: Amen is absorbed into a priestly oration")

    roles.update(
        {sid: "joined-secret" if piece == "secreta" else "joined" for sid in first_prayers}
    )
    verses = [s for s in verses if s["id"] not in first_prayers]
    if piece == "secreta":
        if doc["id"] == DAWN + "secreta":
            if not _dawn_nonfinal(verses):
                errors.append(
                    "Dawn nonfinal secret requires intact s01 and the following Anastasia prayer"
                )
            elif verses:
                roles[verses[0]["id"]] = "nonfinal-secret"
            final = verses[1:]
        else:
            final = verses
        if len(final) != 3:
            errors.append("final secret requires body, four-word audible tail, and separate Amen")
        else:
            body, tail, response = final
            if len(tokens(body)) < 2 or tokens(body)[-1:] != ("deus",):
                errors.append(f"{body['id']}: secret body must end before Per omnia, at Deus")
            if tokens(tail) != TAIL:
                errors.append(
                    f"{tail['id']}: final secret tail must be exactly Per omnia saecula saeculorum"
                )
            if tokens(response) != ("amen",):
                errors.append(f"{response['id']}: final secret requires a one-word Amen response")
            roles.update(
                {body["id"]: "secret-body", tail["id"]: "tail", response["id"]: "response"}
            )
    else:
        expected = 2 if doc["id"] == DAWN + piece else 1
        if len(verses) != 2 * expected:
            errors.append(f"{piece} requires {expected} complete body/Amen pair(s)")
        else:
            for i in range(0, len(verses), 2):
                body, response = verses[i : i + 2]
                if len(tokens(body)) <= 5 or tokens(body)[-5:] != ("deus", *TAIL):
                    errors.append(
                        f"{body['id']}: oration body requires the complete conclusion before Amen"
                    )
                if tokens(response) != ("amen",):
                    errors.append(f"{response['id']}: oration requires a one-word Amen response")
                roles.update({body["id"]: "body", response["id"]: "response"})
    return errors, {} if errors else roles


def base_attributes(doc: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Low-Mass roles for a complete modeled boundary; no legacy rewrites."""
    _, roles = structure(doc)
    return {
        sid: {
            "speaker": "minister" if role == "response" else "sacerdos",
            "voice": "secreto"
            if role in {"secret-body", "nonfinal-secret", "joined-secret"}
            else "clara",
        }
        for sid, role in roles.items()
    }


def sung_delivery(role: str | None) -> dict[str, Any]:
    if role in {"body", "joined", "tail", "response"}:
        return {
            "cantu": {"speaker": "schola" if role == "response" else "sacerdos", "voice": "cantus"}
        }
    return {}


def check_doc(doc: dict[str, Any]) -> tuple[list[str], int]:
    """Validate one boundary subject; count is zero outside the closed scope."""
    if doc.get("id") == PREFACE:
        said = tuple(t for s in doc.get("segments", []) for t in tokens(s))
        duplicate = any(said[i : i + 5] == (*TAIL, "amen") for i in range(len(said) - 4))
        return (
            ["preface dialogue duplicates the final-secret Per omnia / Amen transition"]
            if duplicate
            else []
        ), 1
    if genus(doc) is None:
        return [], 0
    errors, roles = structure(doc)
    if errors:
        return errors, 1

    # Import here: participation and delivery consume structure, whereas
    # validation compares the resulting stored fields without a module cycle.
    from checks.participation import derive as participation

    attributes = base_attributes(doc)
    for seg in doc["segments"]:
        if seg["id"] not in roles:
            continue
        sid = seg["id"]
        for key, wanted in attributes[sid].items():
            if seg.get(key) != wanted:
                errors.append(f"{sid}: oration {key} must be {wanted}, found {seg.get(key)!r}")
        expected_delivery = sung_delivery(roles[sid])
        if (seg.get("delivery") or {}) != expected_delivery:
            errors.append(f"{sid}: oration delivery must be {expected_delivery!r}")
        # Compute participation using the ruled base role, not a wrong stored
        # priest label that would otherwise conceal a missing public answer.
        expected_part = participation(doc, {**seg, **attributes[sid]})
        if (seg.get("participation") or {}) != expected_part:
            errors.append(f"{sid}: oration participation must be {expected_part!r}")
    return errors, 1


def run(root: Path | None = None) -> int:
    root = root or ROOT
    problems = orations = subjects = 0
    for path in sorted(root.glob("texts/*/*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        errors, checked = check_doc(doc)
        subjects += checked
        orations += int(genus(doc) is not None)
        for error in errors:
            print(f"orations: {doc['id']} {error}")
        problems += len(errors)
    if not orations:
        print("orations: FATAL no Proper orations examined")
        return 1
    print(
        f"orations: checked {orations} Proper orations / {subjects} boundary subjects; "
        f"{problems} errors"
    )
    return problems


if __name__ == "__main__":
    sys.exit(1 if run() else 0)

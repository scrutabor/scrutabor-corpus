"""The two explicitly modelled Paschal sung rites, not generic Mass rules."""

from __future__ import annotations

ALLELUIA = "proprium.vigilia-paschalis-alleluia"
DISMISSAL = "ordinarium.ite-missa-est-paschale"
TEXTS = {ALLELUIA, DISMISSAL}
PERFORMED = ["w001", "w033", "w034", "w035", "w036", "w037"]
LITERAL = [f"w{i:03}" for i in range(1, 33)]
ROLES = ["sacerdos", "omnes"] * 3
RUBRIC = (
    "Allelúia a celebrante ter intonatur, tono gradatim elevato, "
    "et post quamlibet vicem ab omnibus in eodem tono repetitur."
)
ALTERNATIVE = "Et diaconus, vertens se ad populum, seu ipse sacerdos, cantat:"
RUBRIC_USES = {
    "mr": "use.proprium.vigilia-paschalis-alleluia.mr1962-rubric",
    "do": "use.proprium.vigilia-paschalis-alleluia.do44667ff-rubric",
}
EXECUTION = {
    "schema_version": "1.0.0",
    "rule": "paschal-three-intonations-with-responses",
    "literal_words": LITERAL,
    "source_word": "w001",
    "performed_words": PERFORMED,
    "speakers": ROLES,
    "rubric_segment": "s01",
    "rubric_uses": RUBRIC_USES,
}
RUBRIC_SOURCES = {
    "mr": {
        "edition": "edition.missale-romanum.1962-typica",
        "digital_item": "item.missale-romanum.1962-typica.ia",
        "role": "rubric_control",
        "address": {"kind": "segment", "text": ALLELUIA, "segment": "s01"},
        "locator": {
            "printed": "p. 214, Alleluia intonation rubric",
            "scan": "leaf n293 / PDF p. 294",
            "page_url": "https://archive.org/details/missale-romanum-1962/page/n293/mode/1up",
        },
        "evidence_sha256": "f9fdbf55438de30731ac50b8cffb4009d19badf0305a09c9cb2d4115840b8fec",
    },
    "do": {
        "edition": "edition.divinum-officium-missa.44667ff",
        "digital_item": "item.divinum-officium-missa.44667ff.github",
        "role": "rubric_control",
        "address": {"kind": "segment", "text": ALLELUIA, "segment": "s01"},
        "locator": {
            "section": (
                "web/www/missa/Latin/Tempora/Quad6-6r.txt [Prelude], physical lines 497–508; "
                "ritual rubric line 499, six utterances lines 498, 500, 502–503, 505–506"
            )
        },
        "evidence_sha256": "ed02ec52034eb46099622477bf6067216a7494fa4122dfbd39f4c7f2f03770ca",
    },
}


def delivery(doc: dict, seg: dict) -> dict:
    if seg.get("type") != "verse":
        return {}
    identifier = seg.get("id")
    if doc.get("id") == ALLELUIA:
        roles = {f"s{i + 2:02}": role for i, role in enumerate(ROLES)}
        roles["s08"] = "schola"
    elif doc.get("id") == DISMISSAL:
        roles = {"s02": "sacerdos", "s03": "omnes", "s06": "omnes"}
    else:
        return {}
    value = {"voice": "cantus"}
    if identifier in roles:
        value["speaker"] = roles[identifier]
    return {"cantu": value}


def base_errors(doc: dict) -> list[str]:
    if doc.get("id") not in TEXTS:
        return []
    errors = []
    segments = doc.get("segments", [])
    expected = [f"s{i:02}" for i in range(1, 10 if doc["id"] == ALLELUIA else 8)]
    if [s.get("id") for s in segments] != expected:
        errors.append("ritual: exact ordered segment identities required")
    for seg in segments:
        if "speaker" in seg or "voice" in seg or seg.get("participation"):
            errors.append(f"ritual: {seg.get('id')} must not invent a lecta role or degree")
        if (seg.get("delivery") or {}) != delivery(doc, seg):
            errors.append(f"ritual: {seg.get('id')} has the wrong sung source role")
    by_id = {s.get("id"): s for s in segments}
    if doc["id"] == ALLELUIA:
        if by_id.get("s01", {}).get("text") != RUBRIC:
            errors.append("ritual: complete three-intonation/all-response rubric required")
        ordered = [w.get("id") for s in segments for w in s.get("words", [])]
        if ordered != PERFORMED + LITERAL[1:]:
            errors.append("ritual: selected order must be six utterances then literal psalms")
        source = {"form": "Allelúia", "lemma": "alleluia", "morph": {"pos": "intj"}, "post": "."}
        for i, identifier in enumerate(PERFORMED):
            seg = by_id.get(f"s{i + 2:02}", {})
            words = [{k: v for k, v in w.items() if k != "analysis"} for w in seg.get("words", [])]
            if words != [{"id": identifier, **source}]:
                errors.append(
                    f"ritual: {identifier} must reproduce the exact one-word source utterance"
                )
    elif by_id.get("s04", {}).get("text") != ALTERNATIVE:
        errors.append("ritual: explicit deacon-or-priest alternative rubric required")
    return errors


def execution(doc: dict, apparatus: dict) -> dict | None:
    """Validate before collapsing; never turn an arbitrary omission into evidence."""
    value = apparatus.get("ritual_execution")
    if doc.get("id") != ALLELUIA:
        if "ritual_execution" in apparatus:
            raise ValueError("ritual execution is unsupported for this text")
        return None
    errors = base_errors(doc)
    if value != EXECUTION:
        errors.append("ritual: complete exact versioned execution mapping required")
    if errors:
        raise ValueError("; ".join(errors))
    if any(
        e.get("at") in PERFORMED or e.get("through") in PERFORMED
        for e in apparatus.get("adjudicated", [])
    ):
        raise ValueError("ritual: execution cannot be supplied by a reading/span ruling")
    return value

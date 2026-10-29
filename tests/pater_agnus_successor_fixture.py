"""Six exact Pater noster to Agnus Dei core successors, reversed only on comparison copies.

Editorial notes describe the witnesses and the 1962 Ordo Missae page
accurately, and thirteen rubric segments cite the printed Missal witness
instead of the digital Ordo. The caller keeps the actual current source; only
a comparison copy is inverted.
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((Path(__file__).parent / "fixtures/pater-agnus-successor.json").read_bytes())
DIAGNOSTIC = "exact Pater to Agnus core successor"


def require(condition, diagnostic):
    if not condition:
        raise AssertionError(diagnostic)


def before_pater_agnus_core_bytes(text, raw, diagnostic=DIAGNOSTIC):
    rule = DATA["texts"].get(text)
    if rule is None:
        return raw
    require(hashlib.sha256(raw).hexdigest() == rule["after_sha256"], diagnostic)
    result = raw
    for operation in reversed(rule["raw_inverse"]):
        after, before = operation["after"].encode(), operation["before"].encode()
        require(result.count(after) == operation["count"], diagnostic)
        result = result.replace(after, before, operation["count"])
    require(hashlib.sha256(result).hexdigest() == rule["before_sha256"], diagnostic)
    return result


def before_pater_agnus_core_object(text, value, diagnostic=DIAGNOSTIC):
    """Accept only the complete actual current core, then parse its exact predecessor."""
    rule = DATA["texts"].get(text)
    if rule is None:
        return value
    raw = (ROOT / rule["relative"]).read_bytes()
    require(value == json.loads(raw), diagnostic)
    return json.loads(before_pater_agnus_core_bytes(text, raw, diagnostic))

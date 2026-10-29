"""Seven exact Offertory core successors, reversed only on historical comparison copies.

The Lavabo opening rubric follows the 1962 Ordo Missae page, two editorial
sentences describe the witness declarations accurately, and twelve rubric
segments cite the printed Missal witness instead of the digital Ordo. The
caller keeps the actual current source; only a comparison copy is inverted.
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((Path(__file__).parent / "fixtures/offertory-rubric-successor.json").read_bytes())


def require(condition, diagnostic):
    if not condition:
        raise AssertionError(diagnostic)


def before_offertory_core_bytes(text, raw, diagnostic="exact Offertory core successor"):
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


def before_offertory_core_object(text, value, diagnostic="exact Offertory core successor"):
    """Accept only the complete actual current core, then parse its exact predecessor."""
    rule = DATA["texts"].get(text)
    if rule is None:
        return value
    raw = (ROOT / rule["relative"]).read_bytes()
    require(value == json.loads(raw), diagnostic)
    return json.loads(before_offertory_core_bytes(text, raw, diagnostic))

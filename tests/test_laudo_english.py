"""Laudare describes praising an object, not glorying in something."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_laudo_uses_contemporary_transitive_english_senses():
    english = json.loads((ROOT / "languages/en/lexicon.json").read_text())
    # Lewis and Short, s.v. laudo, I: praise, laud, commend, extol.
    assert english["entries"]["laudo"]["senses"] == [
        "to praise",
        "to commend",
        "to extol",
    ]

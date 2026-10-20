"""Exact English Easter-day and Easter-night captions and note of the 2026-10-20 revision.

One twelve-word group was split into word captions (Te … prædicáre), its note lost the
sentence the word caption now carries, and the sentence openings Who and And
were capitalized. Reverse exactly these first, then hand the predecessor to the earlier
protection unchanged.
"""

import json
from pathlib import Path

from preface_transition_fixture import restore_preface_transitions

DATA = json.loads(Path(__file__).with_suffix(".json").read_text())


def restore_preface_tokens(layer):
    return restore_preface_transitions(layer, DATA[layer["text"]])

"""Exact English Easter-day revisions, layered over the earlier protection."""

import json
from pathlib import Path

from preface_token_fixture import restore_preface_tokens
from preface_transition_fixture import restore_preface_transitions

DATA = json.loads(Path(__file__).with_suffix(".json").read_text())
TARGET = DATA["target_sha256"]


def restore_day_preface(layer):
    return restore_preface_transitions(restore_preface_tokens(layer), DATA)

"""Exact English Easter-night transitions; retain the earlier protection."""

import json
from pathlib import Path

from preface_token_fixture import restore_preface_tokens
from preface_transition_fixture import restore_preface_transitions

DATA = json.loads(Path(__file__).with_suffix(".json").read_text())
TARGET = DATA["target_sha256"]


def restore_vigil_preface(layer):
    return restore_preface_transitions(restore_preface_tokens(layer), DATA)


def current_prose():
    return next(r["after"] for r in DATA["transitions"] if r["path"].endswith("/translation"))

"""Bounded Holy Thursday Hanc caption relations, not a general grammar parser."""

import re

from checks.interlinear import effective_gloss

HANC = "ordinarium.hanc-igitur-in-cena-domini"
GROUPS = ((50, 51, 50, "Twoich wybranych"),)
DIRECT = {
    "w043": "z",
    "w044": "wiecznego",
    "w045": "potępienia",
    "w046": "nas",
    "w047": "wyrwać",
    "w048": "i",
    "w049": "do",
    "w052": "nakazał",
    "w053": "trzody",
    "w054": "zaliczyć",
}
DETAIL = (
    "„Nakazał” zależy od wcześniejszego „abyś” i łączy się z oboma bezokolicznikami: "
    "„wyrwać nas” i „zaliczyć”. Łacińskie formy są bierne: prosimy, aby to nas wyrwano "
    "i zaliczono. „Do” łączy się z dalszym „trzody”, a „Twoich wybranych” określa osoby "
    "tworzące trzodę."
)
SOURCE = {
    "w043": {"form": "ab", "governs": "abl", "head": "w045"},
    "w044": {"form": "ætérna", "case": "abl", "head": "w045"},
    "w045": {"form": "damnatióne", "lemma": "damnatio", "case": "abl"},
    "w046": {"form": "nos", "pos": "pron", "case": "acc", "number": "pl"},
    "w047": {
        "form": "éripi",
        "lemma": "eripio",
        "pos": "verb",
        "tense": "pres",
        "mood": "inf",
        "voice": "pass",
    },
    "w048": {"form": "et", "pos": "conj"},
    "w049": {"form": "in", "governs": "abl", "head": "w053"},
    "w050": {"form": "electórum", "case": "gen", "number": "pl", "substantive": True},
    "w051": {"form": "tuórum", "case": "gen", "head": "w050"},
    "w052": {
        "form": "iúbeas",
        "lemma": "iubeo",
        "pos": "verb",
        "person": 2,
        "number": "sg",
        "tense": "pres",
        "mood": "subj",
        "voice": "act",
    },
    "w053": {"form": "grege", "lemma": "grex", "case": "abl"},
    "w054": {
        "form": "numerári",
        "lemma": "numero",
        "pos": "verb",
        "tense": "pres",
        "mood": "inf",
        "voice": "pass",
    },
}


def ids(first, last):
    return [f"w{number:03}" for number in range(first, last + 1)]


def assert_hanc_source(core):
    assert core["id"] == HANC, "Hanc selected source identity"
    words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    for wid, expected in SOURCE.items():
        word = words[wid]
        actual = {
            key: word.get(key)
            if key in {"form", "lemma", "head", "substantive"}
            else word["morph"].get(key)
            for key in expected
        }
        assert actual == expected, "Hanc selected source: " + wid


def assert_hanc_scope(layer):
    assert layer["text"] == HANC and layer["language"] == "pl", "Hanc Polish identity"
    expected = [
        {"words": ids(first, last), "anchor": f"w{anchor:03}", "gloss": caption}
        for first, last, anchor, caption in GROUPS
    ]
    assert layer["segments"]["s06"]["alignments"] == expected, "Hanc reviewed short groups"
    for group in expected:
        assert all(not layer["words"][wid].get("gloss") for wid in group["words"]), (
            "Hanc grouped words have one provider"
        )
    assert {wid: layer["words"][wid].get("gloss") for wid in DIRECT} == DIRECT, (
        "Hanc short direct contributions"
    )
    assert layer["words"]["w052"].get("explanation") == DETAIL, "Hanc shared passive detail"


def hanc_polish_errors(core, layer):
    """Check the short model's relations, not arbitrary prayer translations."""
    groups = layer["segments"]["s06"].get("alignments", [])
    selected = [
        [group for group in groups if group.get("words") == ids(first, last)]
        for first, last, _, _ in GROUPS
    ]
    if any(len(matches) != 1 for matches in selected):
        return ["Hanc short model needs its complete elect constituent"]
    elect = selected[0][0].get("gloss", "")
    direct = {wid: layer["words"][wid].get("gloss", "") for wid in DIRECT}
    errors = []
    if direct["w046"] != "nas" or not re.fullmatch(r"wyrwać|ocalić|uwolnić", direct["w047"]):
        errors.append("Hanc rescue keeps us as patients of release from eternal condemnation")
    if (
        direct["w043"] not in {"z", "od"}
        or direct["w044"] != "wiecznego"
        or direct["w045"] != "potępienia"
    ):
        errors.append("Hanc rescue keeps us as patients of release from eternal condemnation")
    if layer["words"]["w048"].get("gloss") != "i":
        errors.append("Hanc both outcomes remain coordinated")
    if direct["w054"] not in {"zaliczyć", "policzyć"}:
        errors.append("Hanc second outcome remains commanded inclusion")
    if direct["w049"] != "do" or direct["w053"] != "trzody" or elect != "Twoich wybranych":
        errors.append("Hanc inclusion retains the Father's elect flock")
    if direct["w052"] not in {"nakazał", "polecił", "rozkazał"}:
        errors.append("Hanc one final finite governor commands both nominal outcomes")
    line = " ".join(
        effective_gloss(layer, word["id"])
        for segment in core["segments"]
        if segment["id"] in {"s05", "s06"}
        for word in segment.get("words", [])
        if effective_gloss(layer, word["id"])
    )
    if not re.search(r"\babyś\b.*\bprzyjął\b.*\buporządkował\b", line):
        errors.append("Hanc acceptance, disposition and command share upstream abyś")
    if re.search(r"\babyś\b.*\bracz\b", line):
        errors.append("Hanc independent imperative cannot stand under upstream abyś")
    if layer["words"]["w052"].get("explanation") != DETAIL:
        errors.append(
            "Hanc detail distinguishes target infinitives and shared Latin passive patient"
        )
    return errors

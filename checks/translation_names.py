"""Reject selected unambiguous personal names absent from the Latin text.

This is a narrow wrong-text guard, not a name recognizer or a translation
verdict. Only explicitly reviewed spellings belong here. Checking the whole
text permits an explicit name translating an anaphoric pronoun in another
segment; it does not certify that such an expansion is justified.
"""

from __future__ import annotations

import re

# Proper lemma, then reviewed target-language name forms. Do not infer
# names from capitalization or prefixes: they collide with ordinary words.
NAMES = {"Abel": {"pl": r"Abel(?:a|owi|em|u)?|Abl(?:a|owi|em|u)", "en": r"Abel"}}


def check(core: dict, layer: dict) -> list[str]:
    """Flag a known target name with no Latin antecedent anywhere in this text.

    Missing names, unknown names, aliases and semantic substitutions are not
    checked. Commentary, citations, rubrics and word glosses are not prayer
    translations and are deliberately outside this check.
    """
    language = layer.get("language") or layer.get("lang")
    lemmas = {
        word.get("lemma")
        for segment in core.get("segments", [])
        for word in segment.get("words", [])
    }
    errors = []
    for lemma, forms in NAMES.items():
        if lemma in lemmas or language not in forms:
            continue
        pattern = re.compile(rf"\b(?:{forms[language]})\b", re.IGNORECASE)
        for sid, segment in layer.get("segments", {}).items():
            if pattern.search(segment.get("translation", "")):
                errors.append(
                    f"{core.get('id', '?')}:{sid}.translation.{language}: "
                    f"personal name {lemma} has no Latin antecedent in this text"
                )
    return errors

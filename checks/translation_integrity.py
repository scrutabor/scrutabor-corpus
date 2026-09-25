"""Translation defects that a string can prove: source markup and Alleluias.

A translation segment once shipped as the literal include string of the
digital source it was imported from ("@Sancti/04-25:Lectio1"), and several
chants carried an Alleluia the Latin does not have, lacked one it has, or
spelled it the Latin way inside English prose. Each is a fact about the
segment and its Latin, not a matter of style, so each is refused here.
"""

from __future__ import annotations

import re

from .normalize import substantive

# Markup of the digital sources the translations were once imported from:
# include directives (@), line continuations (~), macros ($), the Gospel
# cross (++) and a line-initial rubric or reference marker (! or &).
MARKUP = re.compile(r"[@~$]|\+\+|^\s*[!&]")
SPELLING = {"en": "alleluia", "pl": "alleluja"}
ANY = re.compile(r"\b[Aa]llel[uú][ij]a\b")
# An Alleluia ends its sentence or clause before the next capitalised word.
RUN_ON = re.compile(r"\b[Aa]llelu[ij]a\s+[A-ZĄĆĘŁŃÓŚŹŻ]")


def latin_alleluias(segment: dict) -> int:
    return sum(
        1 for word in segment.get("words") or [] if substantive(word.get("form", "")) == "alleluia"
    )


def check(doc: dict, layer: dict) -> list[str]:
    language = layer.get("language") or layer.get("lang")
    spelling = SPELLING.get(str(language))
    segments = layer.get("segments") or {}
    errors: list[str] = []
    for segment in doc.get("segments") or []:
        translation = (segments.get(str(segment.get("id"))) or {}).get("translation")
        if not isinstance(translation, str):
            continue
        where = f"{doc.get('id', '?')}:{segment.get('id')}.translation.{language}"
        if MARKUP.search(translation):
            errors.append(f"{where}: source markup in the translation")
        if spelling is None or segment.get("type") != "verse":
            continue
        found = ANY.findall(translation)
        wrong = sorted({word for word in found if word.lower() != spelling})
        if wrong:
            errors.append(f"{where}: Alleluia spelled {', '.join(wrong)}; write {spelling}")
        expected = latin_alleluias(segment)
        if len(found) != expected:
            errors.append(
                f"{where}: {len(found)} Alleluia(s) in the translation, {expected} in the Latin"
            )
        if RUN_ON.search(translation):
            errors.append(f"{where}: an Alleluia runs on into the next sentence without a stop")
    return errors

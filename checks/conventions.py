"""The gloss conventions the reading campaign settled, held to the corpus.

Three rulings landed on 2026-08-17 (reviews/PLAYBOOK.md) and each was applied
by hand across the whole corpus. Nothing compared them afterwards, which is the
exact shape of every defect this edition has ever had: a thing asserted once
and never checked again. So they are checked here.

Each rule is stated where a reader can find it, and each failure names the rule
rather than only the site, because the next person to hit one will be deciding
whether to fix the gloss or to change the rule.
"""

from __future__ import annotations

# Rule 3. A capital marks a NAME, not a description. `sanctus` is an adjective
# and takes its capital from what it stands with: the heads below make a name
# of a divine person, and everything else — hands, a sacrifice, a mountain, a
# nation — is described rather than named. Declared as data, like every other
# ruling in this corpus, so that adding a name is an edit to a list and not to
# a condition.
DIVINE_NAME_HEADS = {
    "Spíritus",
    "Spirítui",
    "Spíritu",
    "Spíritum",
    "Trínitas",
    "María",
    "Maríæ",
    "Maríam",
    "Génetrix",
    "Genetríce",
    "Genetrícis",
    "Virgo",
    "Vírgine",
    "Vírginis",
    "Vírginem",
}

ARCHAIC = {"thee", "thou", "thy", "thine"}
MODERN = {"you", "your", "yours"}


def _register(gloss: str) -> set[str]:
    """Which second-person registers a gloss uses, if any."""
    found = set()
    for token in gloss.lower().replace(",", " ").split():
        if token in ARCHAIC:
            found.add("archaic")
        elif token in MODERN:
            found.add("modern")
    return found


def check(doc: dict, gloss: dict) -> list[str]:
    """One message per gloss that breaks a settled convention."""
    errors: list[str] = []
    lang = gloss.get("lang", "?")
    entries = gloss.get("words") or {}

    for segment in doc.get("segments", []):
        words = segment.get("words") or []
        by_id = {w["id"]: w for w in words}

        # Rule 1 — a vocative is glossed bare. The particle renders no Latin
        # word, and the case tag already says the word is address.
        for word in words:
            if word["morph"].get("case") != "voc":
                continue
            text = (entries.get(word["id"], {}).get("gloss") or "").strip()
            if text.startswith("O "):
                errors.append(
                    f"{doc['id']}:{word['id']} ({word['form']}): the {lang} gloss "
                    f"{text!r} carries the vocative particle, which renders no Latin "
                    f"word — a vocative is glossed bare (PLAYBOOK, convention 1)"
                )

        # Rule 3 — a capital marks a name, not a description.
        for word in words:
            if word["lemma"] != "sanctus" or word.get("substantive"):
                continue
            head = by_id.get(word.get("head") or "")
            if head is None:
                continue  # substantival: "the Saints", governed by its own entry
            text = (entries.get(word["id"], {}).get("gloss") or "").strip()
            if not text:
                continue
            names = head["form"] in DIVINE_NAME_HEADS
            if names and not text[:1].isupper():
                errors.append(
                    f"{doc['id']}:{word['id']} ({word['form']} {head['form']}): the {lang} "
                    f"gloss {text!r} names a divine person and wants a capital "
                    f"(PLAYBOOK, convention 3)"
                )
            if not names and text[:1].isupper():
                errors.append(
                    f"{doc['id']}:{word['id']} ({word['form']} {head['form']}): the {lang} "
                    f"gloss {text!r} describes rather than names and wants no capital "
                    f"(PLAYBOOK, convention 3)"
                )

        # Rule 2 — the register follows who is addressed, so one segment speaks
        # to one person and cannot hold both registers. Checked per segment
        # rather than per text because a text may address God in one line and a
        # man in the next, which the Confiteor and the kiss of peace both do.
        if lang == "en":
            registers: set[str] = set()
            for word in words:
                if word["lemma"] not in ("tu", "tuus"):
                    continue
                registers |= _register(entries.get(word["id"], {}).get("gloss") or "")
            if len(registers) > 1:
                line = " ".join(w["form"] for w in words)
                errors.append(
                    f"{doc['id']}:{segment['id']}: the English second person is glossed in "
                    f"both registers inside one segment — {line[:60]!r} — and the register "
                    f"follows who is addressed (PLAYBOOK, convention 2)"
                )

    return errors

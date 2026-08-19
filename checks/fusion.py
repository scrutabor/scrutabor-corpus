"""A gloss that renders nothing must say why.

The word gloss renders its word and leaves nothing unrendered (the
two-layer rule). One thing defeats that honestly: a Latin compound perfect is
two words — a participle and a part of *sum* — and a language may build the
same tense with an inflection instead of a second word. Polish does: *locútus
est* is *mówił*, one word, and there is nothing for the auxiliary's cell.

Where that happens the cell carries an em dash, and this check requires the
pair to declare it — a note on the participle, or on the auxiliary itself,
saying the construction has no separate counterpart in this language. A bare
dash with no explanation is a hole a reader falls into: they tap the word and
are told nothing at all.

Where the language DOES have a word the dash is simply wrong, and the check
says so too: Polish splits *factum est* as *stało* + *się* and English as
*made* + *was*, and both cells earn their place.
"""

from __future__ import annotations

DASHES = {"—", "–", "-"}


def check(doc: dict, gloss: dict) -> list[str]:
    """One message per unexplained blank."""
    errors: list[str] = []
    lang = gloss.get("lang", "?")
    words = {w["id"]: w for s in doc.get("segments", []) for w in (s.get("words") or [])}
    order = [w["id"] for s in doc.get("segments", []) for w in (s.get("words") or [])]
    entries = gloss.get("words") or {}

    for wid, entry in entries.items():
        text = (entry.get("gloss") or "").strip()
        if text not in DASHES:
            continue
        word = words.get(wid)
        if word is None:
            continue

        # A dash is only ever right on the auxiliary of a compound perfect.
        index = order.index(wid)
        previous = words.get(order[index - 1]) if index else None
        if word["lemma"] != "sum" or previous is None or previous["morph"].get("mood") != "part":
            errors.append(
                f"{doc['id']}:{wid} ({word['form']}): the {lang} gloss is a dash, and a dash "
                f"belongs only to the auxiliary of a compound perfect"
            )
            continue

        explained = (entry.get("function") or "").strip() or (
            entries.get(previous["id"], {}).get("function") or ""
        ).strip()
        if not explained:
            errors.append(
                f"{doc['id']}:{wid} ({previous['form']} {word['form']}): the {lang} gloss is a "
                f"dash and nothing says why — note the fusion on the participle or on the "
                f"auxiliary, or gloss the auxiliary with the word this language uses"
            )
    return errors

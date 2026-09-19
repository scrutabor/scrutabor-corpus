"""Exact source punctuation without changing lexical forms or word identities.

This validates representation, not source authority. A paired sacred aside
requires source evidence; ritual directions and optional readings are not pairs.
"""

from dataclasses import dataclass


def check_parentheses(segment: dict) -> list[str]:
    """Validate source-ordered, disjoint, inclusive ranges in one verse."""
    if "parentheses" not in segment:
        return []
    label = f"{segment.get('id', '?')}: parentheses"
    if segment.get("type") != "verse":
        return [f"{label}: allowed only on a verse"]
    pairs = segment["parentheses"]
    if not isinstance(pairs, list) or not pairs:
        return [f"{label}: must be a nonempty array; omit unused punctuation"]
    words = segment.get("words")
    if (
        not isinstance(words, list)
        or not words
        or any(not isinstance(word, dict) or not isinstance(word.get("id"), str) for word in words)
    ):
        return [f"{label}: requires live words with unique string ids"]
    positions = {word["id"]: index for index, word in enumerate(words)}
    if len(positions) != len(words):
        return [f"{label}: requires unique word ids"]
    errors = []
    previous_end = -1
    for index, pair in enumerate(pairs):
        where = f"{label}[{index}]"
        if not isinstance(pair, dict) or not {"from", "through"} <= pair.keys():
            errors.append(f"{where}: requires from and through endpoints")
            continue
        if pair.keys() - {"from", "through", "closing"}:
            errors.append(f"{where}: unknown fields; only from, through and closing are allowed")
        if any(
            not isinstance(pair[key], str) or pair[key] not in positions
            for key in ("from", "through")
        ):
            errors.append(f"{where}: endpoints must be live words in this same verse")
            continue
        first, last = positions[pair["from"]], positions[pair["through"]]
        if first > last:
            errors.append(f"{where}: endpoints must follow document order")
        if first <= previous_end:
            errors.append(f"{where}: ranges must be ordered and disjoint, without shared endpoints")
        previous_end = last
        if "closing" in pair:
            if pair["closing"] != "after-post":
                errors.append(f"{where}: closing must be after-post or omitted")
            post = words[last].get("post")
            if not isinstance(post, str) or len(post) != 1 or post not in ",.;:?!":
                errors.append(f"{where}: after-post requires one valid ordinary post mark")
    return errors


@dataclass(frozen=True)
class WordFace:
    """A displayed token with its lexical form kept separately addressable."""

    id: str
    prefix: str
    form: str
    suffix: str

    @property
    def text(self) -> str:
        return self.prefix + self.form + self.suffix


def word_faces(segment: dict) -> list[WordFace]:
    """Project exact full-verse tokens; malformed pairs never silently vanish."""
    errors = check_parentheses(segment)
    if errors:
        raise ValueError("; ".join(errors))
    pairs = segment.get("parentheses", [])
    openings = {pair["from"] for pair in pairs}
    closings = {pair["through"]: pair.get("closing") for pair in pairs}
    result = []
    for word in segment.get("words") or []:
        wid, post = word["id"], word.get("post", "")
        suffix = post
        if wid in closings:
            suffix = post + ")" if closings[wid] == "after-post" else ")" + post
        result.append(WordFace(wid, "(" if wid in openings else "", word["form"], suffix))
    return result

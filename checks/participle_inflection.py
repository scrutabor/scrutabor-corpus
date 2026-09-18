"""A narrow form gate for regular perfect and future participles.

Agreement alone cannot reject two consistently mis-tagged words. These
participles inflect as first/second-declension adjectives. This gate tests
compatibility, not which of several possible cases the sentence requires.
Present participles, gerunds and other paradigms are outside its scope.
"""

from checks.normalize import fold_ligatures, strip_accents

ENDINGS = {
    ("sg", "m"): {"nom": "us", "gen": "i", "dat": "o", "acc": "um", "abl": "o", "voc": "e"},
    ("sg", "f"): {"nom": "a", "gen": "ae", "dat": "ae", "acc": "am", "abl": "a", "voc": "a"},
    ("sg", "n"): {"nom": "um", "gen": "i", "dat": "o", "acc": "um", "abl": "o", "voc": "um"},
    ("pl", "m"): {"nom": "i", "gen": "orum", "dat": "is", "acc": "os", "abl": "is", "voc": "i"},
    ("pl", "f"): {"nom": "ae", "gen": "arum", "dat": "is", "acc": "as", "abl": "is", "voc": "ae"},
    ("pl", "n"): {"nom": "a", "gen": "orum", "dat": "is", "acc": "a", "abl": "is", "voc": "a"},
}


def check(doc: dict) -> list[str]:
    errors = []
    for segment in doc.get("segments", []):
        for word in segment.get("words", []):
            morph = word.get("morph", {})
            if morph.get("mood") != "part" or morph.get("tense") not in {"perf", "fut"}:
                continue
            ending = ENDINGS.get((morph.get("number"), morph.get("gender")), {}).get(
                morph.get("case")
            )
            if not ending:
                continue  # The schema gate reports missing features.
            form = fold_ligatures(strip_accents(word["form"])).lower()
            for enclitic in ("que", "ve", "ne"):
                if form.endswith(enclitic):
                    form = form[: -len(enclitic)]
                    break
            if not form.endswith(ending):
                errors.append(
                    f"{doc['id']}:{word['id']}: participle {word['form']!r} is incompatible "
                    f"with {morph['case']} {morph['number']} {morph['gender']} (ending -{ending})"
                )
    return errors

"""English glosses, checked where English can be checked exactly.

The Polish line has Morfeusz behind it and can be held to agreement. English
has no such analyzer here, and its prepositions answer to the English verb
rather than to the Latin case — *believe IN one God* renders an accusative,
*have mercy ON us* a dative, and neither is a mistake. So this module asserts
only what is decidable without English morphology, and says nothing else.

Narrow gloss patterns are checked:

- **A preposition rendered twice.** When *de* is glossed *from* and its own
  object *cælis* is glossed *of heaven*, the gloss line reads *Father from of
  heaven*. Exact, because the Latin `head` says which word is the object.
- **A noun rendered twice across its preposition.** Adjacent direct glosses
  such as *with water* plus *water* duplicate the explicitly linked noun.
  Only an English preposition plus that complete noun gloss is matched;
  modifiers, synonyms and nonadjacent constituents need editorial review.
- **Usque and its following connective rendered redundantly.** Separate
  glosses such as *until unto* or *as far to* do not express the Latin phrase
  in English. Only the specific malformed junctions below are rejected;
  this is not a general English grammar or translation validator.
- **A modal negation rendered twice.** Adjacent direct glosses for *non*
  and *possum* may not read *not* plus *cannot*, *could not*, or a contracted
  equivalent, including when a complement or punctuation follows. Other
  negation scopes and shared alignments require separate checks or review.
- **An explicit subject or witness object rendered twice.** Adjacent direct
  glosses of *ego* and a first-person verb must not repeat *I*. Likewise,
  *testimonium perhibere* must not repeat *witness* or *testimony*. This rule
  does not judge nonadjacent subjects, synonyms or coordinated predicates.

- **A person treated as the garment.** The adjacent direct rendering of
  imperative *induite vos* must not read *put on yourselves*. This narrow
  rule leaves other forms, clause boundaries and shared providers alone.

The Latin case of a two-case preposition is still useful as an editorial
diagnostic, but it is not an English correctness gate.  Natural English often
selects a preposition from the governing verb or idiom rather than mechanically
copying Latin spatial case (*wait for*, *rejoice in*, *upon the Cross*).
"""

from __future__ import annotations

import re
import unicodedata
from itertools import pairwise

from checks.syntax import check_conclusion_gloss

LEADING_PREPOSITION = re.compile(
    r"^\s*(of|to|unto|for|with|by|in|from|at|on|into|through|upon)\b", re.IGNORECASE
)
SIMPLE_PREPOSITIONS = frozenset(
    [
        "at",
        "by",
        "for",
        "from",
        "in",
        "into",
        "of",
        "on",
        "onto",
        "to",
        "unto",
        "upon",
        "with",
        "without",
        "within",
        "among",
        "through",
    ]
)

# What a two-case preposition may be glossed with, per case it governs.
BY_CASE: dict[tuple[str, str], set[str]] = {
    ("in", "abl"): {"in", "on", "among", "within"},
    ("in", "acc"): {"into", "to", "unto", "on", "upon", "for"},
    ("sub", "abl"): {"under", "beneath"},
    ("sub", "acc"): {"under", "beneath"},
    ("super", "abl"): {"over", "above", "concerning"},
    ("super", "acc"): {"over", "above", "upon"},
    ("subter", "abl"): {"under", "beneath"},
    ("subter", "acc"): {"under", "beneath"},
}

# English idiom that overrides the Latin case, declared site by site so the
# check above can be a gate. Each is right English and would be wrong to
# "correct": one does not believe INTO God, and the hour of death is AT.
IDIOM_RULINGS: dict[tuple[str, str], str] = {
    ("orationes.angelus-domini", "w036"): "in hora mortis: at the hour",
    ("orationes.angelus-domini", "w075"): "in hora mortis: at the hour",
    ("orationes.angelus-domini", "w115"): "in hora mortis: at the hour",
    ("orationes.ave-maria", "w027"): "in hora mortis: at the hour",
    ("ordinarium.communicantes", "w005"): "in primis: the phrase reads first of all",
    ("ordinarium.credo", "w002"): "credo in: one believes IN God, not into",
    ("ordinarium.credo", "w016"): "credo in: one believes IN God, not into",
    ("ordinarium.credo", "w117"): "credo in: one believes IN the Spirit, not into",
    ("ordinarium.simili-modo", "w057"): "in memoriam: in memory of",
    ("ordinarium.suscipe-sancta-trinitas", "w020"): "in honorem: in honour of",
    ("ordinarium.te-igitur", "w029"): "in primis: the phrase reads first of all",
    ("psalmi.118-he", "w022"): "in toto corde meo: with my whole heart",
}


def _index(doc: dict) -> dict[str, dict]:
    return {w["id"]: w for s in doc.get("segments", []) for w in (s.get("words") or [])}


def check_doubled_preposition(doc: dict, gloss: dict) -> list[str]:
    """A preposition glossed once by itself and again inside its object."""
    errors: list[str] = []
    words = gloss.get("words", {})
    index = _index(doc)
    for w in index.values():
        if w["morph"].get("pos") != "prep":
            continue
        head_id = w.get("head")
        if head_id is None or head_id not in index:
            continue
        own = (words.get(w["id"]) or {}).get("gloss") or ""
        obj = (words.get(head_id) or {}).get("gloss") or ""
        if LEADING_PREPOSITION.match(own) and LEADING_PREPOSITION.match(obj):
            errors.append(
                f"{doc['id']}:{w['id']} ({w['form']}): glossed {own.strip()!r} over "
                f"{index[head_id]['form']!r} glossed {obj.strip()!r} — the gloss line "
                f"renders the preposition twice"
            )
    return errors


def check_doubled_noun_head(doc: dict, gloss: dict) -> list[str]:
    """Reject a linked noun repeated in two adjacent direct realizations.

    This deliberately narrow rule matches one simple English preposition and
    the entire separately glossed noun, not arbitrary overlapping phrases.
    Shared/zero providers are handled by the interlinear validator. The rule
    does not infer lexical equivalence, missing dependencies or English case.
    """
    errors: list[str] = []
    glosses = gloss.get("words") or {}
    segments = gloss.get("segments") or {}

    def tokens(value: object) -> list[str]:
        if not isinstance(value, str):
            return []
        return re.findall(
            r"[^\W_]+(?:[’'][^\W_]+)*", unicodedata.normalize("NFKC", value).casefold()
        )

    for segment in doc.get("segments", []):
        grouped = {
            wid
            for group in (segments.get(segment.get("id")) or {}).get("alignments", [])
            for wid in group["words"]
        }
        for prep, noun in pairwise(segment.get("words") or []):
            if (
                prep.get("morph", {}).get("pos") != "prep"
                or noun.get("morph", {}).get("pos") != "noun"
                or prep.get("head") != noun["id"]
                or prep["id"] in grouped
                or noun["id"] in grouped
            ):
                continue
            left = (glosses.get(prep["id"]) or {}).get("gloss")
            right = (glosses.get(noun["id"]) or {}).get("gloss")
            own, head = tokens(left), tokens(right)
            if (
                head
                and len(own) == len(head) + 1
                and own[0] in SIMPLE_PREPOSITIONS
                and own[1:] == head
            ):
                errors.append(
                    f"{doc['id']}:{prep['id']}–{noun['id']} "
                    f"({prep['form']} {noun['form']}): separate glosses "
                    f"{left!r} + {right!r} render the noun twice — "
                    "use a coherent split or a shared interlinear alignment"
                )
    return errors


def check_two_case_prepositions(doc: dict, gloss: dict) -> list[str]:
    """in with the ablative is `in`; with the accusative it is `into`."""
    errors: list[str] = []
    words = gloss.get("words", {})
    index = _index(doc)
    for w in index.values():
        if w["morph"].get("pos") != "prep":
            continue
        head_id = w.get("head")
        if head_id is None or head_id not in index:
            continue
        if (doc["id"], w["id"]) in IDIOM_RULINGS:
            continue
        allowed = BY_CASE.get((w["lemma"], index[head_id]["morph"].get("case")))
        if not allowed:
            continue
        text = ((words.get(w["id"]) or {}).get("gloss") or "").strip().lower()
        if not text or text in allowed:
            continue
        errors.append(
            f"{doc['id']}:{w['id']} ({w['form']}): governs {index[head_id]['form']!r} in "
            f"the {index[head_id]['morph'].get('case')}, but is glossed {text!r} — "
            f"expected one of {'/'.join(sorted(allowed))}"
        )
    return errors


def check_usque_junctions(doc: dict, gloss: dict) -> list[str]:
    """Reject known redundant direct glosses of an adjacent usque phrase.

    Shared alignments have no separate word glosses and are validated by the
    interlinear checker. Keep grammatical splits such as ``up`` + ``to`` and
    ``as far`` + ``as``. Never compare across segment boundaries or infer an
    error from the Latin preposition alone.
    """
    errors: list[str] = []
    glosses = gloss.get("words", {})
    for segment in doc.get("segments", []):
        words = segment.get("words") or []
        for first, second in pairwise(words):
            if first.get("lemma") != "usque" or second.get("lemma") not in {"ad", "in", "dum"}:
                continue
            left = str((glosses.get(first["id"]) or {}).get("gloss") or "").strip()
            right = str((glosses.get(second["id"]) or {}).get("gloss") or "").strip()
            duplicate = re.search(r"\b(?:until|unto|to)$", left, re.IGNORECASE) and re.match(
                r"(?:to|unto|until|for)\b", right, re.IGNORECASE
            )
            incomplete_extent = left.lower() == "as far" and re.match(
                r"(?:to|unto)\b", right, re.IGNORECASE
            )
            duplicate_conjunction = (
                second["lemma"] == "dum"
                and re.search(r"\buntil$", left, re.IGNORECASE)
                and right.lower() == "when"
            )
            if duplicate or incomplete_extent or duplicate_conjunction:
                errors.append(
                    f"{doc['id']}:{first['id']}–{second['id']} "
                    f"({first['form']} {second['form']}): separate glosses "
                    f"{left!r} + {right!r} repeat or misjoin the English connective — "
                    "use a coherent split or a shared interlinear alignment"
                )
    return errors


def check_modal_negation_junctions(doc: dict, gloss: dict) -> list[str]:
    """Reject one Latin non realized twice in adjacent direct English glosses.

    Match a complete negative can/could predicate at the start of the right
    gloss, allowing a following complement or punctuation. Shared alignments,
    other negative words, non-adjacent scopes and general English word order
    belong to separate checks/editorial review.
    """
    errors: list[str] = []
    glosses = gloss.get("words", {})
    for segment in doc.get("segments", []):
        for first, second in pairwise(segment.get("words") or []):
            if (first.get("lemma"), second.get("lemma")) != ("non", "possum"):
                continue
            left = str((glosses.get(first["id"]) or {}).get("gloss") or "").strip()
            right = str((glosses.get(second["id"]) or {}).get("gloss") or "").strip()
            if left.casefold() != "not" or not re.match(
                r"(?:(?:I|you|he|she|it|we|they)\s+)?"
                r"(?:cannot|can\s+not|can’t|could\s+not|couldn’t)\b",
                right,
                re.IGNORECASE,
            ):
                continue
            errors.append(
                f"{doc['id']}:{first['id']}–{second['id']} "
                f"({first['form']} {second['form']}): separate glosses "
                f"{left!r} + {right!r} render the modal negation twice — "
                "use one negative predicate or a shared interlinear alignment"
            )
    return errors


def check_repeated_arguments(doc: dict, gloss: dict) -> list[str]:
    """Reject two narrow duplicated arguments in adjacent direct providers.

    Match either Latin order, but never cross punctuation or segment bounds.
    A shared/zero provider belongs to the interlinear validator. Coordinated
    subjects, lexical synonyms and general argument structure require review.
    """
    errors: list[str] = []
    glosses = gloss.get("words") or {}
    localized_segments = gloss.get("segments") or {}

    def normalized(value: object) -> str:
        if not isinstance(value, str):
            return ""
        return " ".join(unicodedata.normalize("NFKC", value).casefold().split())

    for segment in doc.get("segments", []):
        grouped = {
            wid
            for group in (localized_segments.get(segment.get("id")) or {}).get("alignments", [])
            for wid in group["words"]
        }
        for first, second in pairwise(segment.get("words") or []):
            if (
                first.get("post", "").strip()
                or second.get("pre", "").strip()
                or first["id"] in grouped
                or second["id"] in grouped
            ):
                continue
            for argument, verb in ((first, second), (second, first)):
                noun_morph, verb_morph = argument.get("morph", {}), verb.get("morph", {})
                if verb_morph.get("pos") != "verb" or verb_morph.get("mood") not in {"ind", "subj"}:
                    continue
                own = normalized((glosses.get(argument["id"]) or {}).get("gloss"))
                predicate = normalized((glosses.get(verb["id"]) or {}).get("gloss"))
                duplicate_subject = (
                    argument.get("lemma") == "ego"
                    and noun_morph.get("pos") == "pron"
                    and noun_morph.get("case") == "nom"
                    and noun_morph.get("number") == "sg"
                    and verb_morph.get("person") == 1
                    and verb_morph.get("number") == "sg"
                    and own == "i"
                    and re.match(r"^i\s+\S", predicate) is not None
                )
                predicate_words = re.findall(r"[^\W_]+(?:[’'][^\W_]+)*", predicate)
                duplicate_witness = (
                    argument.get("lemma") == "testimonium"
                    and noun_morph.get("pos") == "noun"
                    and noun_morph.get("case") == "acc"
                    and noun_morph.get("number") == "sg"
                    and verb.get("lemma") == "perhibeo"
                    and own in {"witness", "testimony"}
                    and len(predicate_words) > 1
                    and predicate_words[-1] == own
                )
                if duplicate_subject or duplicate_witness:
                    kind = "subject" if duplicate_subject else "witness object"
                    errors.append(
                        f"{doc['id']}:{first['id']}–{second['id']} "
                        f"({first['form']} {second['form']}): separate glosses "
                        f"{own!r} + {predicate!r} render the {kind} twice — "
                        "use a coherent split or a shared interlinear alignment"
                    )
    return errors


def check_reflexive_clothing(doc: dict, gloss: dict) -> list[str]:
    """Reject direct ``put on / yourselves`` for adjacent imperative induite vos.

    English clothes a person and puts on a garment. This narrow diagnostic
    does not infer a garment from a later gloss or judge other inflections,
    metaphors, paraphrases, or grouped/zero providers. Never join clauses.
    """
    errors: list[str] = []
    glosses = gloss.get("words") or {}
    localized = gloss.get("segments") or {}

    def normalized(value: object) -> str:
        if not isinstance(value, str):
            return ""
        return " ".join(unicodedata.normalize("NFKC", value).casefold().split())

    for segment in doc.get("segments", []):
        grouped = {
            wid
            for group in (localized.get(segment.get("id")) or {}).get("alignments", [])
            for wid in group["words"]
        }
        for verb, pronoun in pairwise(segment.get("words") or []):
            vm, pm = verb.get("morph", {}), pronoun.get("morph", {})
            if (
                verb.get("lemma") != "induo"
                or vm.get("pos") != "verb"
                or vm.get("mood") != "imp"
                or vm.get("person") != 2
                or vm.get("number") != "pl"
                or pronoun.get("lemma") != "vos"
                or pm.get("pos") != "pron"
                or pm.get("case") != "acc"
                or pm.get("number") != "pl"
                or verb.get("post", "").strip()
                or pronoun.get("pre", "").strip()
                or verb["id"] in grouped
                or pronoun["id"] in grouped
            ):
                continue
            left = (glosses.get(verb["id"]) or {}).get("gloss")
            right = (glosses.get(pronoun["id"]) or {}).get("gloss")
            if normalized(left) == "put on" and normalized(right) == "yourselves":
                errors.append(
                    f"{doc['id']}:{verb['id']}–{pronoun['id']} "
                    f"({verb['form']} {pronoun['form']}): separate glosses "
                    f"{left!r} + {right!r} treat the person as a garment — "
                    "use a coherent clothing construction"
                )
    return errors


def check_apostrophes(gloss: dict) -> list[str]:
    """The English layer types the typographic apostrophe (’) in what a reader meets.

    The redrafts and the older lines had come to mix ’ with the straight ' of a
    keyboard (Lord's beside Lord’s). The straight mark is never a quotation
    mark in this prose, so the rule is exact: none in the translation, the
    narrative, the gloss line, the aligned glosses, the word help or the about.
    Citations are bibliographic data and keep the form of the title they cite.
    """
    where = gloss.get("text", "?")
    fields: list[tuple[str, object]] = [("about", gloss.get("about"))]
    for sid, segment in (gloss.get("segments") or {}).items():
        fields.append((f"{sid}.translation", segment.get("translation")))
        fields.append((f"{sid}.narrative", segment.get("narrative")))
        for alignment in segment.get("alignments") or []:
            fields.append((f"{sid}.alignment {alignment['words'][0]}", alignment.get("gloss")))
    for wid, word in (gloss.get("words") or {}).items():
        for key in ("gloss", "explanation", "note"):
            fields.append((f"{wid}.{key}", word.get(key)))
    return [
        f"{where}:{field}: straight apostrophe — the English layer types ’"
        for field, value in fields
        if isinstance(value, str) and "'" in value
    ]


def check(doc: dict, gloss: dict) -> list[str]:
    if gloss.get("lang") != "en":
        return []
    return (
        check_doubled_preposition(doc, gloss)
        + check_doubled_noun_head(doc, gloss)
        + check_usque_junctions(doc, gloss)
        + check_modal_negation_junctions(doc, gloss)
        + check_repeated_arguments(doc, gloss)
        + check_reflexive_clothing(doc, gloss)
        + check_conclusion_gloss(doc, gloss)
        + check_apostrophes(gloss)
    )


# A Latin plural the edition renders with an English singular, declared site by
# site so the check below can be a gate. Each is an editorial decision: the
# ecclesiastical *caeli* names one heaven, *sanguinibus* in the Last Gospel is a
# Hebraism for one substance, and *in cælis et in terris* is the same idiom.
ENGLISH_NUMBER_RULINGS: dict[str, str] = {
    "caelum": "the ecclesiastical plural caeli names one heaven",
    "dies": "the distributive per singulos dies is rendered every day",
    "sanguis": "sanguinibus is a Hebraism for one substance",
    "species": "the English noun species has the same form in singular and plural",
    "terra": "in caelis et in terris: English says earth",
    "Ierosolyma": "the plural-form place name denotes the one city Jerusalem",
}


def check_number(docs: list[tuple[dict, dict]]) -> list[str]:
    """One English gloss may not serve both numbers of one Latin noun.

    English has no analyzer here, so number is checked against the CORPUS
    itself: if *caelo* and *caelis* are both glossed 'heaven', either one of
    them is wrong or the collapse is an editorial decision — and the corpus
    says which by declaring it. Adjectives and pronouns are exempt because
    English does not inflect them for number, which is why this reads nouns
    alone.
    """
    seen: dict[tuple[str, str], set[str]] = {}
    where: dict[tuple[str, str], str] = {}
    for doc, gloss in docs:
        words = gloss.get("words") or {}
        for segment in doc.get("segments", []):
            for w in segment.get("words") or []:
                m = w["morph"]
                if m.get("pos") != "noun" or not m.get("number"):
                    continue
                text = (words.get(w["id"]) or {}).get("gloss")
                if not text:
                    continue
                key = (w["lemma"], text.lower())
                seen.setdefault(key, set()).add(m["number"])
                where.setdefault(key, f"{doc['id']}:{w['id']} ({w['form']})")
    return [
        f"{where[key]}: gloss {key[1]!r} serves both the singular and the plural "
        f"of {key[0]!r} — declare the collapse or distinguish the numbers"
        for key, nums in sorted(seen.items())
        if len(nums) > 1 and key[0] not in ENGLISH_NUMBER_RULINGS
    ]

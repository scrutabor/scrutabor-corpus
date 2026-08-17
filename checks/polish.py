"""Polish that a Polish reader would catch before an expert ever saw it.

The word layer is read AS A LINE. Under *Ad te levávi* stood the glosses *ku*
and *Ciebie*, which is not Polish — *ku* takes the dative — and under *in verbo*
stood *w* and *słowem*, which is not Polish either. No check in this corpus
could see that, because every defence it had was aimed at the Latin. These are
aimed at the Polish, and they are aimed at the errors a reader notices in the
first five minutes, which is the risk the edition actually runs before it has
an expert or an audience.

Morfeusz 2 supplies the morphology. It is a BUILD-TIME dependency: the corpus
ships JSON, the reader's browser never sees a morphological analyzer, and the
GPL never touches the published artifact.
"""

from __future__ import annotations

import functools
import re

# What each Polish preposition governs. Where a preposition takes more than one
# case the check accepts any of them: it speaks only when the gloss beside it
# stands in NONE of them, which is the shape of a real mistake.
PREP_CASE: dict[str, set[str]] = {
    "bez": {"gen"},
    "dla": {"gen"},
    "do": {"gen"},
    "od": {"gen"},
    "ode": {"gen"},
    "u": {"gen"},
    "z": {"gen", "inst"},
    "ze": {"gen", "inst"},
    "wśród": {"gen"},
    "według": {"gen"},
    "podczas": {"gen"},
    "obok": {"gen"},
    "wobec": {"gen"},
    "spośród": {"gen"},
    "ku": {"dat"},
    "przeciw": {"dat"},
    "przeciwko": {"dat"},
    "dzięki": {"dat"},
    "w": {"acc", "loc"},
    "we": {"acc", "loc"},
    "na": {"acc", "loc"},
    "o": {"acc", "loc"},
    "po": {"acc", "loc"},
    "przy": {"loc"},
    "przez": {"acc"},
    "nad": {"acc", "inst"},
    "nade": {"acc", "inst"},
    "pod": {"acc", "inst"},
    "przed": {"acc", "inst"},
    "za": {"acc", "inst", "gen"},
    "między": {"acc", "inst"},
    "pomiędzy": {"acc", "inst"},
    "poza": {"acc", "inst"},
}

# Glosses that are a fixed phrase rather than a preposition plus its object.
# Each is a rendering the edition chose on purpose, and none is a place where
# the next gloss answers to the preposition inside it.
PHRASE_GLOSSES = {
    "z powodu",
    "ze względu na",
    "za wstawiennictwem",
    "za sprawą",
    "wraz z",
    "przede",
}

WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


# Morfeusz tags that carry case and number. `pact` and `ppas` are the
# adjectival participles: they decline exactly like adjectives, and leaving
# them out made every participle gloss read as CASELESS, which silently
# exempted the ablative absolute — the one construction built out of them.
NOMINAL_TAGS = {"subst", "adj", "pact", "ppas", "ppron12", "ppron3", "num", "ger", "depr"}


@functools.lru_cache(maxsize=1)
def _morfeusz():
    import morfeusz2

    return morfeusz2.Morfeusz()


@functools.lru_cache(maxsize=4096)
def cases(form: str) -> frozenset[str]:
    """Every case this Polish form can stand in. Empty if Morfeusz knows none."""
    out: set[str] = set()
    for analysis in _morfeusz().analyse(form):
        interp = analysis[2]
        parts = interp[2].split(":")
        if parts[0] in NOMINAL_TAGS:
            for field in parts[1:]:
                out |= {c for c in field.split(".") if c in CASES}
    return frozenset(out)


CASES = {"nom", "gen", "dat", "acc", "inst", "loc", "voc"}


def _head_word(gloss: str | None) -> str | None:
    """The word a preposition would govern: the last word of the gloss."""
    if not gloss:
        return None
    found = WORD_RE.findall(gloss)
    return found[-1] if found else None


def check_prepositions(doc: dict, gloss: dict) -> list[str]:
    """A Polish preposition in the gloss line must govern the gloss beside it."""
    errors: list[str] = []
    words = gloss.get("words", {})
    for segment in doc.get("segments", []):
        for w in segment.get("words") or []:
            text = (words.get(w["id"]) or {}).get("gloss")
            if not text or text.strip() in PHRASE_GLOSSES:
                continue
            tokens = WORD_RE.findall(text)
            if not tokens:
                continue

            # A gloss that is itself preposition + object carries its own
            # object: "z Tobą", "nade mną". Check inside it and stop there.
            if len(tokens) >= 2 and tokens[0].lower() in PREP_CASE:
                allowed = PREP_CASE[tokens[0].lower()]
                got = cases(tokens[-1])
                if got and not (got & allowed):
                    errors.append(
                        f"{doc['id']}:{w['id']} ({w['form']}): gloss {text!r} — "
                        f"{tokens[0]!r} takes the {'/'.join(sorted(allowed))}, but "
                        f"{tokens[-1]!r} is {'/'.join(sorted(got))}"
                    )
                continue

            # A gloss that is a bare preposition governs the gloss of the word
            # the LATIN preposition governs — which is not always the next one.
            # *Per sanctíssimæ Eucharístiæ institutiónem* puts two genitives
            # between them, and reading the next gloss reported a mistake that
            # was not there. The `head` recorded in schema 0.13.0 says exactly
            # which word it is, so the Latin syntax now steadies the Polish
            # check. A preposition without a head yet is skipped, not guessed.
            if len(tokens) != 1 or tokens[0].lower() not in PREP_CASE:
                continue
            if w["morph"].get("pos") != "prep":
                continue  # *O clemens*: an interjection, not the preposition o
            head_id = w.get("head")
            if head_id is None:
                continue
            allowed = PREP_CASE[tokens[0].lower()]
            target = _head_word((words.get(head_id) or {}).get("gloss"))
            if target is None:
                continue
            got = cases(target)
            if got and not (got & allowed):
                errors.append(
                    f"{doc['id']}:{w['id']} ({w['form']}): gloss line reads "
                    f"{tokens[0]!r} … {target!r} — {tokens[0]!r} takes the "
                    f"{'/'.join(sorted(allowed))}, but {target!r} is "
                    f"{'/'.join(sorted(got))}"
                )
    return errors


# A Polish PREDICATE COMPLEMENT stands in the instrumental even where the Latin
# has its modifier agreeing with the head's case: *notas fac* is *uczyń drogi
# ZNANYMI*, and the instrumental is what Polish requires after uczynić.
# Declared site by site so the agreement check below stays a gate.
PREDICATE_RULINGS: dict[tuple[str, str], str] = {
    ("ordinarium.per-quem-haec-omnia", "w007"): (
        "bona: hæc ómnia bona creas — Polish takes an instrumental "
        "complement where the Latin has a predicate accusative"
    ),
    ("proprium.dominica-i-adventus-graduale", "w011"): (
        "notas fac: uczynić takes an instrumental complement"
    ),
}


MASCULINE = {"m1", "m2", "m3"}


@functools.lru_cache(maxsize=4096)
def genders(form: str) -> frozenset[str]:
    """m/f/n for this Polish form. The three masculines collapse: a gloss pair
    need only agree on the gender a reader hears, not on animacy."""
    out: set[str] = set()
    for analysis in _morfeusz().analyse(form):
        parts = analysis[2][2].split(":")
        if parts[0] not in NOMINAL_TAGS:
            continue
        for field in parts[1:]:
            for x in field.split("."):
                if x in MASCULINE:
                    out.add("m")
                elif x in {"f", "n"}:
                    out.add(x)
    return frozenset(out)


def check_modifier_glosses(doc: dict, gloss: dict) -> list[str]:
    """A modifier's gloss agrees with its head's gloss, in Polish as in Latin.

    *a tua numquam laude* glossed *Twoją* over a *chwały* that is genitive is
    the same defect as the preposition one, one step further in: the reader
    sees two Polish words that cannot stand together.
    """
    errors: list[str] = []
    words = gloss.get("words", {})
    index = {w["id"]: w for s in doc.get("segments", []) for w in (s.get("words") or [])}
    for w in index.values():
        head_id = w.get("head")
        if head_id is None or w["morph"].get("pos") not in {"adj", "num"}:
            continue
        head = index.get(head_id)
        if head is None or head["morph"].get("pos") not in {"noun", "adj"}:
            continue
        if (doc["id"], w["id"]) in PREDICATE_RULINGS:
            continue
        # Only single-word glosses on both sides. *godna podziwu* and *z kości
        # słoniowej* are phrases whose head is not their last word, and
        # guessing which word carries the agreement invents mistakes rather
        # than finding them.
        mine_text = (words.get(w["id"]) or {}).get("gloss") or ""
        theirs_text = (words.get(head_id) or {}).get("gloss") or ""
        if len(WORD_RE.findall(mine_text)) != 1 or len(WORD_RE.findall(theirs_text)) != 1:
            continue
        mine = _head_word(mine_text)
        theirs = _head_word(theirs_text)
        if not mine or not theirs:
            continue
        for label, mine_f, theirs_f in (
            ("case", cases(mine), cases(theirs)),
            ("gender", genders(mine), genders(theirs)),
            ("number", numbers(mine), numbers(theirs)),
        ):
            if mine_f and theirs_f and not (mine_f & theirs_f):
                errors.append(
                    f"{doc['id']}:{w['id']} ({w['form']}): gloss {mine!r} is "
                    f"{label}={'/'.join(sorted(mine_f))}, but it modifies "
                    f"{head['form']!r}, glossed {theirs!r}, which is "
                    f"{label}={'/'.join(sorted(theirs_f))}"
                )
                break
    return errors


def check_divine_address(doc: dict, gloss: dict) -> list[str]:
    """The second person addressed to God is capitalised, as the verses are.

    Lowercase is right where the words address a person — *Et cum spiritu tuo*
    to the priest, *Misereatur tui* to the penitent — so the test is not the
    word but whether this text's own translation of the same verse capitalises
    it. Where the verse writes *Twój* and the gloss writes *twój*, the reader
    sees the edition contradict itself on the same line.
    """
    errors: list[str] = []
    words = gloss.get("words", {})
    segments = gloss.get("segments", {})
    for segment in doc.get("segments", []):
        translation = (segments.get(segment["id"]) or {}).get("translation") or ""
        capitalised = {t for t in WORD_RE.findall(translation) if t[:1].isupper()}
        lowered = {t.lower() for t in capitalised}
        for w in segment.get("words") or []:
            if w["lemma"] not in {"tuus", "tu"}:
                continue
            text = (words.get(w["id"]) or {}).get("gloss")
            if not text:
                continue
            tokens = WORD_RE.findall(text)
            if not tokens or not tokens[-1][:1].islower():
                continue
            if tokens[-1].lower() in lowered:
                errors.append(
                    f"{doc['id']}:{w['id']} ({w['form']}): gloss {text!r} is lowercase, "
                    f"but this verse writes it capitalised"
                )
    return errors


def check(doc: dict, gloss: dict) -> list[str]:
    if gloss.get("lang") != "pl":
        return []
    return (
        check_prepositions(doc, gloss)
        + check_modifier_glosses(doc, gloss)
        + check_divine_address(doc, gloss)
        + check_number(doc, gloss)
        + check_ablative_absolute(doc, gloss)
        + check_purpose_clauses(doc, gloss)
        + check_two_case_prepositions(doc, gloss)
    )


# A Latin plural that Polish says in the singular, declared site by site so
# that the number check below can be a gate and not a report. Each is an
# editorial decision, not an accident: Polish renders a Latin neuter plural
# with a collective (*ómnia* → wszystko, *hæc* → to), says *w niebie i na
# ziemi* where the Canon says *in cælis et in terris*, and has no singular for
# *os* in the sense of a mouth that speaks, so *ore* can only be *ustami*.
NUMBER_RULINGS: dict[tuple[str, str], str] = {
    ("ordinarium.credo", "w049"): "omnia: the Polish collective wszystko",
    ("ordinarium.evangelium-ultimum", "w034"): "omnia: the Polish collective wszystko",
    ("ordinarium.per-quem-haec-omnia", "w003"): "haec: the Polish collective to",
    ("ordinarium.per-quem-haec-omnia", "w004"): "omnia: the Polish collective wszystko",
    ("ordinarium.quid-retribuam", "w005"): "omnibus: the Polish collective wszystko",
    ("ordinarium.quid-retribuam", "w006"): "quae: the Polish collective co",
    ("ordinarium.simili-modo", "w054"): "haec: the Polish collective to",
    ("ordinarium.supplices-te-rogamus", "w007"): "haec: the Polish collective to",
    ("proprium.dominica-i-adventus-evangelium", "w092"): "haec: the Polish collective to",
    ("proprium.dominica-i-adventus-secreta", "w001"): "haec: the Polish collective to",
    ("ordinarium.suscipe-sancta-trinitas", "w057"): "in caelis: the received w niebie",
    ("ordinarium.suscipe-sancta-trinitas", "w062"): "in terris: the received na ziemi",
    ("ordinarium.te-igitur", "w048"): "orbe terrarum: the received świat",
    ("ordinarium.quod-ore-sumpsimus", "w002"): "ore: usta is a Polish plurale tantum",
    ("litaniae.sanctissimi-nominis-iesu", "w440"): "ore: usta is a Polish plurale tantum",
    ("proprium.dominica-i-adventus-epistola", "w031"): "arma: the collective zbroja",
    ("proprium.dominica-i-adventus-epistola", "w045"): "cubilibus: the abstract rozpusta",
    ("proprium.dominica-i-adventus-epistola", "w047"): "impudicitiis: the abstract wyuzdanie",
    ("ordinarium.libera-nos", "w006"): "ab omnibus malis: od zła wszelkiego, one phrase",
    ("ordinarium.libera-nos", "w008"): "praeteritis: agrees with zła wszelkiego",
    ("ordinarium.libera-nos", "w009"): "praesentibus: agrees with zła wszelkiego",
    ("ordinarium.libera-nos", "w011"): "futuris: agrees with zła wszelkiego",
    ("ordinarium.fili-dei-vivi", "w033"): "universis malis: od wszelkiego zła, one phrase",
}

NUMBERED_POS = {"noun", "adj", "pron", "num"}


@functools.lru_cache(maxsize=8192)
def numbers(form: str) -> frozenset[str]:
    """Whether this Polish form can be singular, plural, or either."""
    out: set[str] = set()
    for analysis in _morfeusz().analyse(form):
        parts = analysis[2][2].split(":")
        if parts[0] in NOMINAL_TAGS:
            for field in parts[1:]:
                out |= {n for n in field.split(".") if n in {"sg", "pl"}}
    return frozenset(out)


def check_number(doc: dict, gloss: dict) -> list[str]:
    """A Latin plural is glossed in the plural, unless a ruling says otherwise."""
    errors: list[str] = []
    words = gloss.get("words", {})
    for segment in doc.get("segments", []):
        for w in segment.get("words") or []:
            n = w["morph"].get("number")
            if n not in {"sg", "pl"} or w["morph"].get("pos") not in NUMBERED_POS:
                continue
            if (doc["id"], w["id"]) in NUMBER_RULINGS:
                continue
            text = (words.get(w["id"]) or {}).get("gloss")
            if not text:
                continue
            tokens = WORD_RE.findall(text)
            if len(tokens) != 1:
                continue
            got = numbers(tokens[0])
            if got and n not in got:
                errors.append(
                    f"{doc['id']}:{w['id']} ({w['form']}): Latin is {n}, but the gloss "
                    f"{tokens[0]!r} is {'/'.join(sorted(got))}"
                )
    return errors


def check_ablative_absolute(doc: dict, gloss: dict) -> list[str]:
    """An ablative absolute is glossed as an instrumental pair, and nothing else.

    The construction has no Polish counterpart, so the four renderings Polish
    grammars sanction — a *gdy* clause, a *-wszy/-łszy* converb, a coordinate
    clause, a prepositional phrase — all restructure it. Allen & Greenough say
    the same of English: a change of form is generally required in translation.
    That change belongs to the VERSE. The gloss line follows the source's
    structure (Leipzig Glossing Rules: a gloss is not required to be
    grammatical in the metalanguage), so it renders each word in its own right,
    in the case Polish grammars name as the ablative's counterpart.

    Two shapes are therefore errors, and both stood at four of the twelve sites
    before this rule: a gloss carrying a preposition the Latin does not have
    (*przez anioła* for a bare *Ángelo*), and a member standing in some case
    other than the instrumental (*odpuszczone grzechy*, a nominative, for
    *dimíssis peccátis*).
    """
    words = {w["id"]: w for s in doc.get("segments", []) for w in (s.get("words") or [])}
    glosses = gloss.get("words") or {}
    governed = {
        w["head"] for w in words.values() if w["morph"].get("pos") == "prep" and w.get("head")
    }
    errors = []
    for wid, word in words.items():
        m = word["morph"]
        if not (m.get("pos") == "verb" and m.get("mood") == "part" and m.get("case") == "abl"):
            continue
        head_id = word.get("head")
        head = words.get(head_id) if head_id else None
        if head is None or head["morph"].get("case") != "abl":
            continue
        if wid in governed or head_id in governed:
            continue  # governed by a preposition: not an absolute
        for member in (wid, head_id):
            text = (glosses.get(member) or {}).get("gloss")
            if not text:
                continue
            parts = WORD_RE.findall(text)
            if not parts:
                continue
            if parts[0].lower() in PREP_CASE:
                errors.append(
                    f"{doc['id']}:{member} ({words[member]['form']}): gloss {text!r} opens "
                    f"with a preposition the Latin does not have — an ablative absolute is "
                    f"glossed as an instrumental pair"
                )
            elif not any("inst" in cases(part) for part in parts):
                errors.append(
                    f"{doc['id']}:{member} ({words[member]['form']}): gloss {text!r} is not "
                    f"instrumental — an ablative absolute is glossed as an instrumental pair"
                )
    return errors


# The Polish conjunctions that already carry subordination and, where the
# clitic is attached, the person. A verb glossed under one of these takes the
# l-form: *abyśmy byli*, never *abyśmy niech będziemy* or *abyśmy byśmy byli*.
ABY = {
    "aby",
    "abym",
    "abyś",
    "abyśmy",
    "abyście",
    "żeby",
    "żebym",
    "żebyś",
    "żebyśmy",
    "by",
    "byś",
    "byśmy",
}


# A subjunctive that stands after a purpose clause but is not IN it: *et illi
# pro nobis intercédere dignéntur* opens a coordinate main clause with its own
# expressed nominative subject (*illi*), which Polish states as a jussive.
# Declared site by site so the check below can be a gate and not a report.
PURPOSE_RULINGS: dict[tuple[str, str], str] = {
    ("ordinarium.suscipe-sancta-trinitas", "w055"): (
        "dignentur: a coordinate main clause, subject illi expressed"
    ),
}


def check_purpose_clauses(doc: dict, gloss: dict) -> list[str]:
    """A verb glossed under *aby* takes the l-form, and nothing else.

    Latin `ut` + subjunctive is a purpose clause, and Polish renders it with
    *aby* and a past-participial l-form. Three shapes break it, and all three
    stood in the corpus: an IMPERATIVE (*aby racz*, *aby każ*), a *niech*
    jussive (*aby niech posłuży*), and a second *by* particle (*aby byśmy
    byli*). Each is ungrammatical where it stands, which makes it the kind of
    defect a reader meets before an expert ever does — and in five of the eight
    the text's own verse already carried the right word.
    """
    glosses = gloss.get("words") or {}
    errors: list[str] = []
    for segment in doc.get("segments", []):
        seq = segment.get("words") or []
        for i, w in enumerate(seq):
            if w["lemma"] != "ut":
                continue
            lead = ((glosses.get(w["id"]) or {}).get("gloss") or "").strip().lower()
            if lead not in ABY:
                continue
            for nxt in seq[i + 1 :]:
                if nxt["lemma"] == "ut":
                    break
                if nxt["morph"].get("mood") != "subj":
                    continue
                if (doc["id"], nxt["id"]) in PURPOSE_RULINGS:
                    continue
                text = (glosses.get(nxt["id"]) or {}).get("gloss") or ""
                parts = WORD_RE.findall(text)
                if not parts:
                    continue
                first = parts[0].lower()
                bad = None
                if first == "niech":
                    bad = "a niech jussive"
                elif first in ABY:
                    bad = "a second by particle"
                elif any(a[2][2].split(":")[0] == "impt" for a in _morfeusz().analyse(parts[0])):
                    bad = "an imperative"
                if bad:
                    errors.append(
                        f"{doc['id']}:{nxt['id']} ({nxt['form']}): gloss {text!r} is {bad}, "
                        f"but it stands under {lead!r} — a purpose clause takes the l-form"
                    )
    return errors


# Polish prepositions that take more than one case, and what each case means.
# The LATIN decides which: `in` + ablative is static and `in` + accusative is
# motion, and Polish marks the same difference on the same preposition.
TWO_CASE_PL: dict[str, dict[str, set[str]]] = {
    "w": {"abl": {"loc"}, "acc": {"acc"}},
    "we": {"abl": {"loc"}, "acc": {"acc"}},
    "na": {"abl": {"loc"}, "acc": {"acc"}},
    "o": {"abl": {"loc"}, "acc": {"acc"}},
    "pod": {"abl": {"inst"}, "acc": {"acc"}},
    "nad": {"abl": {"inst"}, "acc": {"acc"}},
    "przed": {"abl": {"inst"}, "acc": {"acc"}},
    "za": {"abl": {"inst", "gen"}, "acc": {"acc"}},
}


def check_two_case_prepositions(doc: dict, gloss: dict) -> list[str]:
    """A Polish two-case preposition must take the case the LATIN chose.

    `check_prepositions` asks only whether the object stands in SOME case the
    preposition can govern, so *w trzody* passed: `w` takes the accusative, and
    *trzody* is accusative among its readings. But the Latin was `in grege`,
    ablative and static, and *w trzody* reads "into the flock". The Latin case
    is recorded and names the object, so the choice is decidable.

    This applies ONLY where the LATIN preposition is itself two-case, because
    only there does the ablative/accusative contrast carry static-versus-motion.
    Keying it on the Latin case alone flagged *pro peccátis* glossed *za
    grzechy*, which is the right Polish: `pro` is not two-case, and `za` +
    accusative is simply how Polish says "for".
    """
    from checks.syntax import PREP_CASE as LATIN_PREP_CASE

    words = {w["id"]: w for s in doc.get("segments", []) for w in (s.get("words") or [])}
    glosses = gloss.get("words") or {}
    errors: list[str] = []
    for wid, w in words.items():
        if w["morph"].get("pos") != "prep":
            continue
        if len(LATIN_PREP_CASE.get(w["lemma"], ())) < 2:
            continue
        head_id = w.get("head")
        head = words.get(head_id) if head_id else None
        if head is None:
            continue
        latin_case = head["morph"].get("case")
        text = (glosses.get(wid) or {}).get("gloss") or ""
        parts = WORD_RE.findall(text)
        if not parts:
            continue
        wanted = TWO_CASE_PL.get(parts[0].lower(), {}).get(latin_case)
        if not wanted:
            continue
        object_text = (glosses.get(head_id) or {}).get("gloss") or ""
        object_parts = WORD_RE.findall(object_text)
        if not object_parts:
            continue
        got = cases(object_parts[-1])
        if got and not (got & wanted):
            errors.append(
                f"{doc['id']}:{head_id} ({head['form']}): gloss {object_text!r} is "
                f"{'/'.join(sorted(got))}, but it stands under Polish {parts[0]!r} "
                f"rendering Latin {w['form']!r}+{latin_case} — that needs the "
                f"{'/'.join(sorted(wanted))}"
            )
    return errors

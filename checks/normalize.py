"""Normalization for collation and linting. Stdlib only (dependency budget)."""

import unicodedata

LIGATURES = {"æ": "ae", "œ": "oe", "Æ": "Ae", "Œ": "Oe", "ǽ": "ae", "Ǽ": "Ae"}

# U+0301 is needed after œ: Unicode has no precomposed accented œ, while
# liturgical editions print the stress in forms such as fœ́deris and
# obœ́diens. NFC therefore legitimately leaves that one accent decomposed.
ACCENTED_VOWELS = set("áéíóúýǽÁÉÍÓÚÝǼ\u0301")

# Vowel letters for syllable counting; ligatures and accented vowels count as
# one. ë (diaeresis, ORTHOGRAPHY.md rule 7) is its own syllable: Mí-cha-ël.
VOWELS = set("aeiouyáéíóúýæœǽë")


def strip_accents(text: str) -> str:
    out = []
    for ch in unicodedata.normalize("NFD", text):
        if unicodedata.category(ch) != "Mn":
            out.append(ch)
    return unicodedata.normalize("NFC", "".join(out))


def fold_ligatures(text: str) -> str:
    for k, v in LIGATURES.items():
        text = text.replace(k, v)
    return text


def substantive(text: str, fold_ji: bool = False, fold_xs: bool = False) -> str:
    """Level A: what must NEVER differ between witnesses of one recension —
    the letters. Case-folded, accents stripped, ligatures expanded,
    punctuation removed, whitespace collapsed. j is folded to i only for
    witnesses that declare an i-style orthography profile (fold-ji: true in
    the witness header); otherwise j/v differences are substantive
    (ORTHOGRAPHY.md). fold-xs likewise declares an edition that prints
    assimilated ex- for exs- (expecto for exspecto): exs is folded to ex
    on both sides for that witness only."""
    text = fold_ligatures(strip_accents(text)).lower()
    if fold_ji:
        text = text.replace("j", "i")
    if fold_xs:
        text = text.replace("exs", "ex")
    kept = [ch if ch.isalpha() or ch.isspace() else " " for ch in text]
    return " ".join("".join(kept).split())


# A compound keeps the consonantal i of the simplex it is built on:
# adiutórium is ad + iuvo, so its i is the consonant and the word has five
# syllables (ad-iu-tó-ri-um), not six. Prefix AND stem both have to be
# named, because the same position holds a VOCALIC i in the compounds of eo
# — ábiit is ab + iit, three syllables — and nothing in the spelling tells
# the two apart. Stems are listed by the shapes they take in composition
# (iacio/iectus, iungo/iunctus), accents and ligatures folded away.
GLIDE_PREFIXES = frozenset(
    ("ab", "ad", "con", "de", "dis", "in", "inter", "ob", "per", "prae", "sub", "trans")
)
GLIDE_STEMS = ("iac", "iect", "iud", "iung", "iunct", "iur", "iust", "iut", "iuv")


def after_prefix(word: str, at: int) -> bool:
    """True when everything before position `at` is a prefix and what
    follows is a stem that begins with the consonant (ad|iutórium)."""
    head = fold_ligatures(strip_accents(word[:at]))
    return head in GLIDE_PREFIXES and fold_ligatures(strip_accents(word[at:])).startswith(
        GLIDE_STEMS
    )


def syllable_nuclei(form: str) -> list[int]:
    """Where the syllables of a Latin form in 1962 orthography are — the index
    of each nucleus, in order. Vocalic i and u are nuclei; the exceptions are u
    in the qu/gu glides and consonantal i, which ORTHOGRAPHY.md prints as i,
    not j. Diphthongs: au counts once; ae/oe occur only as ligatures (one
    char). eu is NOT treated as a diphthong (De-um).

    Consonantal i stands between two vowels (E-ia, al-le-lú-ia, e-ius), at
    the head of a word before another vowel (Ie-sus, Io-án-nes, iu-be), and
    after the prefix of a compound whose simplex begins with it — see
    GLIDE_PREFIXES. The qu/gu glide is consumed before this can see it, so
    quia and relíquiæ are untouched.

    This counted rather than located until 2026-08-19, and one number cannot
    answer where the stress falls. It is the same walk either way, and
    `syllable_count` is now its length, so the two answers cannot drift apart.
    """
    s = unicodedata.normalize("NFC", form).lower()
    nuclei = []
    prev = ""
    prev_was_vowel = False
    for i, ch in enumerate(s):
        nxt = s[i + 1] if i + 1 < len(s) else ""
        is_vowel = ch in VOWELS
        if is_vowel:
            if ch == "u" and prev in ("q", "g") and nxt in VOWELS:
                # glide: qu-/gu- BEFORE A VOWEL (lingua, sanguis, quia). The
                # vowel test is not decoration. Without it every u after q or
                # g was swallowed, so surgunt counted 1 syllable and regum 1,
                # and the error stayed invisible while no such word carried an
                # accent. resúrgunt, in the Advent II gospel, is the first that
                # does, and it was reported as a two-syllable word wrongly
                # accented.
                prev = ch
                prev_was_vowel = False
                continue
            if ch == "i" and nxt in VOWELS and (prev_was_vowel or prev == "" or after_prefix(s, i)):
                # Consonantal i: a glide, not a nucleus. Between vowels
                # (allelúia, eius), at the head of a word before another
                # vowel (Iesus, Ioánnes, iube) — which is where nearly all
                # of them are, now that this edition prints the consonant
                # as i rather than j — and across a prefix seam (ad-iutórium).
                #
                # An ACCENTED í is never one of them, whatever stands beside
                # it: a glide is not a nucleus and a nucleus is what carries
                # the stress. The test read `ch in ("i", "í")` until the
                # accent-position gate was written, and Isaías — I-sa-í-as,
                # a Hebrew name whose i is a vowel between two vowels — came
                # back as a three-syllable word with its accent nowhere.
                prev = ch
                prev_was_vowel = False
                continue
            if prev_was_vowel and prev in ("a", "á") and ch == "u":
                # 'au' diphthong: already counted at 'a'. The accent of a
                # diphthong is written on its FIRST vowel — páuperum,
                # gáudium, thesáurus, exáudi — so the test that reads the
                # letter before must read past the mark. Comparing against a
                # bare "a" made twenty-one such words one syllable too long,
                # which no rule then in force could see: every one of them
                # was over the three-syllable line either way.
                prev = ch
                prev_was_vowel = True
                continue
            nuclei.append(i)
        prev = ch
        prev_was_vowel = is_vowel
    return nuclei


def syllable_count(form: str) -> int:
    return len(syllable_nuclei(form))


def has_accent(form: str) -> bool:
    return any(ch in ACCENTED_VOWELS for ch in unicodedata.normalize("NFD", form))


def accented_syllable(form: str) -> int | None:
    """How far the written accent stands from the end, counted in syllables:
    0 the last, 1 the penult, 2 the antepenult. None when the form carries no
    accent, or carries one the syllabifier cannot place on a nucleus.

    Latin stress falls on the penult or the antepenult and never before it —
    an invariant that needs no vowel quantities, which is why this edition can
    hold it mechanically. Callers report a number above 2.
    """
    s = unicodedata.normalize("NFC", form)
    nuclei = syllable_nuclei(form)
    for position, index in enumerate(nuclei):
        # Either a precomposed accented vowel, or the combining acute that
        # follows œ — Unicode has no precomposed œ́, and fœ́deris is printed.
        if s[index] in ACCENTED_VOWELS or s[index + 1 : index + 2] == "́":
            return len(nuclei) - 1 - position
    return None

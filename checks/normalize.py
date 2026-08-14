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


def syllable_count(form: str) -> int:
    """Count syllables of a Latin form in 1962 orthography. Vocalic i and u
    are nuclei; the exceptions are u in the qu/gu glides and consonantal i,
    which ORTHOGRAPHY.md prints as i, not j. Diphthongs: au counts once;
    ae/oe occur only as ligatures (one char). eu is NOT treated as a
    diphthong (De-um).

    Consonantal i stands between two vowels (E-ia, al-le-lú-ia, e-ius), at
    the head of a word before another vowel (Ie-sus, Io-án-nes, iu-be), and
    after the prefix of a compound whose simplex begins with it — see
    GLIDE_PREFIXES. The qu/gu glide is consumed before this can see it, so
    quia and relíquiæ are untouched."""
    s = unicodedata.normalize("NFC", form.lower())
    count = 0
    prev = ""
    prev_was_vowel = False
    for i, ch in enumerate(s):
        nxt = s[i + 1] if i + 1 < len(s) else ""
        is_vowel = ch in VOWELS
        if is_vowel:
            if ch == "u" and prev in ("q", "g"):
                # glide: qu-/gu- before a vowel; if no vowel follows this is
                # wrong, but such forms (e.g. 'gutta') have no q/g+u+vowel
                # ambiguity in practice — the next iteration adds the vowel.
                prev = ch
                prev_was_vowel = False
                continue
            if (
                ch in ("i", "í")
                and nxt in VOWELS
                and (prev_was_vowel or prev == "" or after_prefix(s, i))
            ):
                # Consonantal i: a glide, not a nucleus. Between vowels
                # (allelúia, eius), at the head of a word before another
                # vowel (Iesus, Ioánnes, iube) — which is where nearly all
                # of them are, now that this edition prints the consonant
                # as i rather than j — and across a prefix seam (ad-iutórium).
                prev = ch
                prev_was_vowel = False
                continue
            if prev_was_vowel and prev == "a" and ch == "u":
                # 'au' diphthong: already counted at 'a'
                prev = ch
                prev_was_vowel = True
                continue
            count += 1
        prev = ch
        prev_was_vowel = is_vowel
    return count


def has_accent(form: str) -> bool:
    return any(ch in ACCENTED_VOWELS for ch in unicodedata.normalize("NFD", form))

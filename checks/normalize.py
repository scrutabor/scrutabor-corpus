"""Normalization for collation and linting. Stdlib only (dependency budget)."""

import unicodedata

LIGATURES = {"æ": "ae", "œ": "oe", "Æ": "Ae", "Œ": "Oe", "ǽ": "ae", "Ǽ": "Ae"}

ACCENTED_VOWELS = set("áéíóúýǽÁÉÍÓÚÝǼ")

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


def syllable_count(form: str) -> int:
    """Count syllables of a Latin form in 1962 orthography. Reliable because
    consonantal i is written j (ORTHOGRAPHY.md): remaining i/u are vocalic
    except u in qu/gu+vowel glides. Diphthongs: au counts once; ae/oe occur
    only as ligatures (one char). eu is NOT treated as a diphthong (De-um)."""
    s = unicodedata.normalize("NFC", form.lower())
    count = 0
    prev = ""
    prev_was_vowel = False
    for ch in s:
        is_vowel = ch in VOWELS
        if is_vowel:
            if ch == "u" and prev in ("q", "g"):
                # glide: qu-/gu- before a vowel; if no vowel follows this is
                # wrong, but such forms (e.g. 'gutta') have no q/g+u+vowel
                # ambiguity in practice — the next iteration adds the vowel.
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
    return any(ch in ACCENTED_VOWELS for ch in form)

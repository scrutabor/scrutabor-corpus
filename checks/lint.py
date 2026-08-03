"""Mechanical corpus lint: schema shape, charset, orthography (ORTHOGRAPHY.md),
accent rules, cross-references, quoted forms, terminology, layer parity."""

import re

from .normalize import ACCENTED_VOWELS, fold_ligatures, has_accent, strip_accents, syllable_count

MORPH_ENUMS = {
    "pos": {"verb", "noun", "adj", "pron", "adv", "conj", "prep", "intj"},
    "case": {"nom", "gen", "dat", "acc", "abl", "voc"},
    "number": {"sg", "pl"},
    "gender": {"m", "f", "n"},
    "tense": {"pres", "impf", "fut", "perf", "plup", "futperf"},
    "mood": {"ind", "subj", "imp", "inf"},
    "voice": {"act", "pass", "dep"},
    "degree": {"comp", "sup"},
    "governs": {"acc", "abl"},
}

FORM_RE = re.compile(r"^[A-Za-zÁÉÍÓÚÝáéíóúýÆæŒœǼǽ]+$")
REF_RE = re.compile(r"\((w\d{3})\)")
QUOTE_REF_RE = re.compile(r"[„“]([^”“„]+)”\s*\((w\d{3})\)")

# Terminology contract (corpus/TERMINOLOGY.md): banned variants per language.
BANNED_TERMS = {
    "pl": [r"ablatiw"],  # ablatiwus/ablatiwie/... -> ablativus/ablativie/...
    "en": ["„"],  # Polish low-opening quote in English text
}

PROPER_LEMMAS = {"Maria", "Michael", "Ioannes", "Baptista", "Petrus", "Paulus", "Iesus"}


def lint_text(doc):
    errors = []
    words = [w for s in doc["segments"] for w in s.get("words") or []]
    if not words:
        errors.append("no words in document — refusing to pass on zero")
        return errors, 0
    ids = [w["id"] for w in words]
    if len(ids) != len(set(ids)):
        errors.append("duplicate word ids")
    for w in words:
        wid, f = w["id"], w["form"]
        if not FORM_RE.match(f):
            errors.append(f"{wid}: charset violation in form {f!r}")
        lemma = w.get("lemma", "")
        if lemma and lemma[0].isupper() and lemma not in PROPER_LEMMAS:
            errors.append(f"{wid}: lemma {lemma!r} capitalized but not in proper-name list (SCHEMA.md)")
        for k, v in w["morph"].items():
            if k in MORPH_ENUMS and v not in MORPH_ENUMS[k]:
                errors.append(f"{wid}: morph.{k}={v!r} not in enum")
        plain = fold_ligatures(strip_accents(f)).lower()
        # u after q/g before a vowel is a glide, not a vowel (quia, sanguis) —
        # drop it before the vocalic-context tests.
        plain = re.sub(r"([qg])u(?=[aeiouy])", r"\1", plain)
        if re.search(r"[aeouy]i[aeouy]", plain):
            errors.append(f"{wid}: {f!r} has i between vowels — ORTHOGRAPHY.md wants j (allowlist if genuine)")
        if re.match(r"i[aeiouy]", plain):
            errors.append(f"{wid}: {f!r} starts i+vowel — ORTHOGRAPHY.md wants J (allowlist if genuine)")
        n, acc = syllable_count(f), has_accent(f)
        n_marks = sum(1 for ch in f if ch in ACCENTED_VOWELS)
        if n >= 3 and not acc:
            errors.append(f"{wid}: {f!r} has {n} syllables but no accent")
        if n <= 2 and acc:
            errors.append(f"{wid}: {f!r} has {n} syllables but carries an accent")
        if n_marks > 1:
            errors.append(f"{wid}: {f!r} carries {n_marks} accents")
    return errors, len(words)


def lint_gloss(doc, text_doc):
    errors = []
    lang = doc["lang"]
    words = {w["id"]: w for s in text_doc["segments"] for w in s.get("words") or []}
    seg_types = {s["id"]: s["type"] for s in text_doc["segments"]}
    gw = doc.get("words", {})
    missing = sorted(set(words) - set(gw))
    extra = sorted(set(gw) - set(words))
    if missing:
        errors.append(f"{lang}: no gloss for {missing}")
    if extra:
        errors.append(f"{lang}: gloss for unknown ids {extra}")

    banned = BANNED_TERMS.get(lang, [])

    def check_prose(where, prose):
        for pat in banned:
            # IGNORECASE: a capitalized sentence-initial variant is the same
            # banned term (proven necessary by mutation, 2026-08-03).
            if re.search(pat, prose, re.IGNORECASE):
                errors.append(f"{lang}:{where}: banned terminology/typography {pat!r} (TERMINOLOGY.md)")

    for wid, entry in gw.items():
        fn = entry.get("function", "")
        check_prose(wid, entry.get("gloss", "") + " " + fn)
        for ref in REF_RE.finditer(fn):
            if ref.group(1) not in words:
                errors.append(f"{lang}:{wid}: dangling cross-reference {ref.group(1)}")
        for qm in QUOTE_REF_RE.finditer(fn):
            quoted, rid = qm.groups()
            if rid in words and quoted != words[rid]["form"]:
                errors.append(
                    f"{lang}:{wid}: quoted {quoted!r} != form {words[rid]['form']!r} of {rid}"
                )
        # Reader-facing prose must be self-contained: the ONLY permitted id
        # reference is the quoted-form pattern above (the app renders it as a
        # link and hides the id). Bare ids ("Jak w004") are author shorthand
        # leaking to readers.
        remainder = QUOTE_REF_RE.sub("", fn)
        for bare in re.finditer(r"\bw\d{3}\b", remainder):
            errors.append(
                f"{lang}:{wid}: bare word-id {bare.group(0)!r} in reader-facing prose"
            )
    for sid, seg in doc.get("segments", {}).items():
        check_prose(sid, (seg.get("translation", "") or "") + " " + (seg.get("narrative", "") or ""))
        if sid not in seg_types:
            errors.append(f"{lang}: segment {sid} not in text document")
        elif "translation" in seg and seg_types[sid] != "verse":
            errors.append(f"{lang}:{sid}: translation on a non-verse segment")
        elif "narrative" in seg and seg_types[sid] != "rubric":
            errors.append(f"{lang}:{sid}: narrative on a non-rubric segment")
    return errors


def lint_parity(gloss_docs):
    errors = []
    if len(gloss_docs) < 2:
        return errors
    base = gloss_docs[0]
    for other in gloss_docs[1:]:
        if set(base["words"]) != set(other["words"]):
            errors.append(
                f"parity: word coverage differs {base['lang']} vs {other['lang']}: "
                f"{sorted(set(base['words']) ^ set(other['words']))}"
            )
        if set(base.get("segments", {})) != set(other.get("segments", {})):
            errors.append(f"parity: segment coverage differs {base['lang']} vs {other['lang']}")
    return errors

"""Collation: corpus verse text against independent witnesses of the SAME
recension. Substantive text (letters) must match with zero divergence;
accidentals (punctuation, capitalization, capital-accents) must each be
covered by an adjudicated entry in the text's apparatus.json.

A witness may print a DIFFERENT REAL SPELLING of the same word — the
classical neglegentia against the ecclesiastical negligentia, caelum against
coelum. Both are the word; neither page is wrong; but the letters differ, so
this is neither an accidental nor a corrigendum. Such a reading passes only
with an apparatus entry of `"class": "orthography"` quoting both spellings
and ruling which the edition prints. Counted as `orthographic` in the stats.

A witness may INFLECT a name this edition leaves alone. Latin took the
Hebrew names in twice: Ioseph stands unchanged in every case, and Iosephus
declines like any second-declension noun, so one page sets *cum beato
Ioseph* and another *cum beato Iosepho*. That is not a spelling — the
letters differ because the grammar does — and calling it one would bury a
real editorial question inside a class that exists for questions nobody
needs to think about twice. It passes only with an apparatus entry of
`"class": "inflection"`, and it is counted separately, so the number a
verdict line reports as `orthographic` never quietly includes it.

A witness may also carry a printer's slip — a letter its own edition sets
wrong. Such a reading is not a variant to adjudicate and not something to
tolerate silently, so a witness file DECLARES it:

    # corrigendum: princípo -> princípio (this printing drops the i; the
    #   same edition sets the doxology correctly on page 11)

The collation applies declared corrigenda before comparing, refuses a
declaration whose printed reading is not in the file, refuses one with no
reason, and counts them in the verdict.

A witness may instead be right about a text this edition does not print:
the same prayer circulates in more than one RECENSION, and a page giving
the devotional form of an antiphon closes it with an Amen where the
liturgical form runs straight on. That is not a slip and not a spelling —
the page is correct for its own recension — so it is declared too:

    # recension: -Amen (after "Virgo Maria"; this page gives the
    #   devotional form, which closes the antiphon with an Amen; the
    #   Leonine recension has none and witness do runs on to the versicle)

Only the minus direction exists, and deliberately. Dropping a word the
witness has is a claim about the witness; ADDING one it lacks would be a
claim about our own text that no page attests, and a word this edition
prints must stand in a witness. Declared removals are applied before
comparing, refused if the witness does not print the word, refused if our
own text does print it (which would hide a real divergence), refused
without a reason, and counted in the verdict.

WHAT THIS DOES NOT DEFEND AGAINST, stated plainly: a transcriber who
quietly "corrects" the page while typing it. That transcription passes,
because nothing here can read the original — and worse, a silent
emendation of exactly this kind HIDES a real divergence by making the two
witnesses agree. The mechanism makes an emendation declarable, checkable
and counted; keeping it honest is the transcription discipline, not the
checker."""

import difflib
import json
import re
from pathlib import Path
from typing import Any

from .normalize import substantive

# The two classes a ruling may put on a letter difference. Both need an
# apparatus entry quoting both readings; they are counted apart so the
# verdict line never reports a grammatical question as a spelling one.
RULED_CLASSES = ("orthography", "inflection")


def _bare(token: str) -> str:
    """Compare the way the collation compares — accents, case and
    punctuation folded — or a declaration fails to match the very page it
    describes (María against Maria) and the check fires for the wrong
    reason."""
    return substantive(token).strip()


def _emend(token: str, printed: str, emended: str) -> str:
    """One corrigendum applied to one token. The declared reading is the
    WORD; the token may carry the page's punctuation, which the emendation
    leaves alone."""
    body = token.rstrip(",.:;?!")
    tail = token[len(body) :]
    return emended + tail if body == printed else token


def load_witness(path: Path) -> tuple[dict[str, Any], str]:
    # The header is mostly `key: value` strings, but two keys are parsed into
    # lists of tuples before they go in — hence Any rather than str.
    meta: dict[str, Any] = {}
    lines: list[str] = []
    corrigenda: list[tuple[str, str, str]] = []
    recensions: list[tuple[str, str]] = []
    # Header values wrap: a `#` line that does not open a new `key:` is a
    # continuation of the one above. Reading them line by line instead
    # truncates every reason at its first line break.
    header: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            m = re.match(r"#\s*([\w-]+):\s*(.*)", line)
            if m:
                header.append((m.group(1), m.group(2)))
            elif header:
                header[-1] = (header[-1][0], f"{header[-1][1]} {line.lstrip('# ').strip()}")
        elif line.strip():
            lines.append(line.strip())

    for key, value in header:
        if key == "recension":
            drop = re.match(r"-(\S+)\s*(?:\((.*)\))?", value)
            recensions.append((drop.group(1), drop.group(2) or "") if drop else (value, ""))
        elif key == "corrigendum":
            arrow = re.match(r"(\S+)\s*->\s*(\S+)\s*(?:\((.*)\))?", value)
            if arrow:
                corrigenda.append((arrow.group(1), arrow.group(2), arrow.group(3) or ""))
            else:
                corrigenda.append((value, "", ""))  # malformed; reported below
        else:
            meta[key] = value
    meta["corrigenda"] = corrigenda
    meta["recensions"] = recensions
    return meta, " ".join(lines)


def corpus_tokens(doc):
    """Verse tokens in document order as (word_id, form+post). Rubrics are
    not collated — they are edition-specific framing, flagged separately."""
    toks = []
    for seg in doc["segments"]:
        for w in seg.get("words") or []:
            toks.append((w["id"], w["form"] + w.get("post", "")))
    return toks


def collate(doc, witness_dir: Path):
    """Returns (errors, warnings, stats)."""
    errors: list[str] = []
    # Empty on purpose, and kept: the stale-ruling report was the only thing
    # this ever put here, and it is an error now. The channel stays because
    # run_checks reads it and because a finding that is worth showing and
    # not worth failing on is a real category — there just isn't one today.
    warnings: list[str] = []
    toks = corpus_tokens(doc)
    ours_raw = [t for _, t in toks]
    ours_sub = substantive(" ".join(ours_raw)).split()

    app_path = witness_dir / "apparatus.json"
    apparatus = (
        json.loads(app_path.read_text(encoding="utf-8"))
        if app_path.exists()
        else {"adjudicated": []}
    )
    adjudicated = {(e["at"], wid): e for e in apparatus["adjudicated"] for wid in e["witnesses"]}

    witness_files = sorted(p for p in witness_dir.glob("*.txt"))
    if not witness_files:
        errors.append(
            f"no witness files in {witness_dir} — collation cannot pass on zero witnesses"
        )

    used = set()
    n_variants = 0
    n_corrigenda = 0
    n_orthographic = 0
    n_inflection = 0
    n_recensions = 0
    n_omissions = 0
    n_partial = 0
    for wf in witness_files:
        meta, text = load_witness(wf)
        wid = meta.get("witness", wf.stem)
        # A witness may testify to PART of a text and nothing else. The
        # Clementine Vulgate is the authority for the Gospel a Mass reads
        # and says nothing about the versicles around it; a printed Ordo
        # may carry the prayers and not the psalm. Coverage is DECLARED —
        # `# covers: w015-w187` — never inferred from where the words stop
        # matching, which is how a partial witness would otherwise be used
        # to explain away a divergence.
        toks_w, ours_raw_w, ours_sub_w = toks, ours_raw, ours_sub
        covers = meta.get("covers", "").strip()
        if covers:
            ids = [i for i, _ in toks]
            m = re.fullmatch(r"(w\d+)\s*-\s*(w\d+)", covers)
            if not m:
                errors.append(f"{wid}: malformed covers {covers!r} — write 'wNNN-wMMM'")
                continue
            first, last = m.groups()
            if first not in ids or last not in ids:
                errors.append(f"{wid}: covers {covers!r} names a token this text does not have")
                continue
            i0, i1 = ids.index(first), ids.index(last)
            if i1 < i0:
                errors.append(f"{wid}: covers {covers!r} runs backwards")
                continue
            if (i0, i1) == (0, len(toks) - 1):
                errors.append(f"{wid}: covers the whole text — drop the declaration")
                continue
            toks_w = toks[i0 : i1 + 1]
            ours_raw_w = [t for _, t in toks_w]
            ours_sub_w = substantive(" ".join(ours_raw_w)).split()
            n_partial += 1
        # Declared printer's slips: each must actually be in the file, and
        # each is applied openly before anything is compared.
        for printed, emended, reason in meta["corrigenda"]:
            if not emended:
                errors.append(
                    f"{wid}: malformed corrigendum {printed!r} — "
                    "write 'printed -> emended (reason)'"
                )
                continue
            if not reason:
                errors.append(f"{wid}: corrigendum {printed!r} carries no reason")
            # The declared reading is the WORD; the token may carry the
            # page's punctuation, which the emendation leaves alone.
            tokens = text.split()
            if not any(_emend(t, printed, emended) != t for t in tokens):
                errors.append(
                    f"{wid}: corrigendum declares {printed!r}, which this witness does not print "
                    "— stale declaration, or the transcription was already emended"
                )
                continue
            text = " ".join(_emend(t, printed, emended) for t in tokens)
            n_corrigenda += 1
        # Declared recension differences: a word this page's recension has
        # and ours does not. Refused unless the page really prints it and
        # our own text really lacks it — otherwise a declaration here could
        # quietly delete a divergence instead of explaining one.
        for word, reason in meta["recensions"]:
            if not word.strip():
                errors.append(f"{wid}: malformed recension note — write '-word (reason)'")
                continue
            if not reason:
                errors.append(f"{wid}: recension note {word!r} carries no reason")
            # Compare the way the collation compares — accents, case and
            # punctuation folded — or a declaration fails to match the very
            # page it describes (María against Maria) and the check fires
            # for the wrong reason.
            word_cmp = _bare(word)
            tokens = text.split()
            if not any(_bare(t) == word_cmp for t in tokens):
                errors.append(
                    f"{wid}: recension note declares {word!r}, which this witness does not print "
                    "— stale declaration, or the transcription already dropped it"
                )
                continue
            if any(_bare(t) == word_cmp for t in ours_raw_w):
                errors.append(
                    f"{wid}: recension note declares {word!r}, but this edition prints it too "
                    "— that is a divergence to adjudicate, not a recension difference"
                )
                continue
            cut = next(i for i, t in enumerate(tokens) if _bare(t) == word_cmp)
            text = " ".join(tokens[:cut] + tokens[cut + 1 :])
            n_recensions += 1
        fold_ji = meta.get("fold-ji", "").strip().lower() == "true"
        fold_xs = meta.get("fold-xs", "").strip().lower() == "true"
        folded = fold_ji or fold_xs
        ours_cmp = (
            substantive(" ".join(ours_raw_w), fold_ji=fold_ji, fold_xs=fold_xs).split()
            if folded
            else ours_sub_w
        )
        wit_sub = substantive(text, fold_ji=fold_ji, fold_xs=fold_xs).split()
        if len(wit_sub) != len(ours_cmp):
            # A full witness may omit a word which the primary witness and
            # this edition print. That is a real substantive divergence, so
            # it passes only through an explicit apparatus ruling whose
            # witness reading is the empty string.
            wit_raw_before = text.split()
            rebuilt: list[str] = []
            valid = True
            matcher = difflib.SequenceMatcher(None, ours_cmp, wit_sub)
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == "equal":
                    rebuilt.extend(wit_raw_before[j1:j2])
                    continue
                if tag == "delete":
                    for i in range(i1, i2):
                        word_id, ours_tok = toks_w[i]
                        entry = adjudicated.get((word_id, wid))
                        if not (
                            entry
                            and entry.get("class") == "omission"
                            and entry.get("ours") == ours_tok
                            and entry.get("witnesses", {}).get(wid) == ""
                        ):
                            valid = False
                            break
                        rebuilt.append(ours_tok)
                        used.add((word_id, wid))
                        n_omissions += 1
                    if not valid:
                        break
                    continue
                valid = False
                break
            if valid:
                text = " ".join(rebuilt)
                wit_sub = substantive(text, fold_ji=fold_ji, fold_xs=fold_xs).split()
        if wit_sub != ours_cmp:
            if len(wit_sub) != len(ours_cmp):
                errors.append(
                    f"{wid}: SUBSTANTIVE length mismatch: "
                    f"ours={len(ours_cmp)} witness={len(wit_sub)}"
                )
                continue
            unruled = False
            for i, (a, b) in enumerate(zip(ours_cmp, wit_sub, strict=True)):
                if a == b:
                    continue
                # An ADJUDICATED ORTHOGRAPHIC VARIANT is a letter difference
                # where both spellings are real words of the same recension
                # (neglegentia/negligentia, caelum/coelum) and the edition has
                # ruled which it prints. Unlike a corrigendum, neither witness
                # is wrong; unlike an accidental, the letters differ. It passes
                # only with a ruling that quotes both readings.
                #
                # An ADJUDICATED INFLECTION is the other ruled letter
                # difference: a name this edition leaves indeclinable and the
                # witness declines. It is counted apart from orthography
                # because it is a question about grammar, not about spelling.
                word_id, ours_tok = toks_w[i] if i < len(toks_w) else ("?", "")
                entry = adjudicated.get((word_id, wid))
                if (
                    entry
                    and entry.get("class") in RULED_CLASSES
                    and entry["ours"] == ours_tok
                    and entry["witnesses"].get(wid)
                ):
                    used.add((word_id, wid))
                    if entry["class"] == "inflection":
                        n_inflection += 1
                    else:
                        n_orthographic += 1
                    continue
                errors.append(
                    f"{wid}: SUBSTANTIVE divergence at word {i + 1} "
                    f"({word_id}): ours={a!r} witness={b!r}"
                )
                unruled = True
                break
            if unruled:
                continue
            # every letter difference was ruled: the accidentals still get
            # compared below, as they do for a witness that matched outright

        if meta.get("profile", "").strip() == "substantive-only":
            # Witness with a different accidental profile (unaccented,
            # different punctuation): the letters have been verified above;
            # accidental comparison against it would be noise.
            continue
        wit_raw = text.split()
        if len(wit_raw) != len(ours_raw_w):
            errors.append(
                f"{wid}: raw token count mismatch despite substantive match "
                f"(ours={len(ours_raw_w)} witness={len(wit_raw)}) — punctuation split a token?"
            )
            continue
        for (word_id, ours_tok), wit_tok in zip(toks_w, wit_raw, strict=True):
            if ours_tok == wit_tok or (word_id, wid) in used:
                continue  # identical, or already ruled as an orthographic variant
            entry = adjudicated.get((word_id, wid))
            if entry and entry["ours"] == ours_tok and entry["witnesses"][wid] == wit_tok:
                used.add((word_id, wid))
                n_variants += 1
            else:
                errors.append(
                    f"{wid}: UNADJUDICATED variant at {word_id}: "
                    f"ours={ours_tok!r} witness={wit_tok!r} — "
                    "record a ruling in apparatus.json or fix the text"
                )

    # Stale apparatus entries: recorded diffs that no witness produced.
    # This was a warning, and 21 of them accumulated across two texts before
    # anyone read one: seventeen rulings in the prayer to St Michael that
    # said "this edition accents capitals" over lowercase words, against a
    # page that is unaccented throughout and declares the profile that
    # never compares accents at all. A stale ruling is worse than no ruling
    # — it is a claim about a page, recorded in a public apparatus, that
    # the page does not support — so the gate refuses it.
    for (word_id, wid), entry in adjudicated.items():
        if entry["witnesses"][wid] != entry["ours"] and (word_id, wid) not in used:
            errors.append(
                f"apparatus entry {word_id}/{wid} matches no variant this witness produces "
                "— stale ruling: delete it, or name the witness that does produce it"
            )

    # A partial witness ADDS evidence; it can never be the evidence. Every
    # text still has to stand on two witnesses that cover all of it, or the
    # part outside the partial witness's range would rest on one voice
    # while the summary line said two.
    if witness_files and len(witness_files) - n_partial < 2:
        errors.append(
            f"only {len(witness_files) - n_partial} full witness(es) for this text "
            f"({n_partial} partial) — a partial witness cannot make up the second voice"
        )

    stats = {
        "witnesses": len(witness_files) - n_partial,
        "partial": n_partial,
        "words": len(toks),
        "variants_adjudicated": n_variants,
        "corrigenda": n_corrigenda,
        "orthographic": n_orthographic,
        "inflections": n_inflection,
        "recensions": n_recensions,
        "omissions": n_omissions,
    }
    return errors, warnings, stats

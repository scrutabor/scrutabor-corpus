"""Collation: corpus verse text against independent witnesses of the SAME
recension. Substantive text (letters) must match with zero divergence;
accidentals (punctuation, capitalization, capital-accents) must each be
covered by an adjudicated entry in the text's apparatus.json.

A witness may also carry a printer's slip — a letter its own edition sets
wrong. Such a reading is not a variant to adjudicate and not something to
tolerate silently, so a witness file DECLARES it:

    # corrigendum: princípo -> princípio (this printing drops the i; the
    #   same edition sets the doxology correctly on page 11)

The collation applies declared corrigenda before comparing, refuses a
declaration whose printed reading is not in the file, refuses one with no
reason, and counts them in the verdict.

WHAT THIS DOES NOT DEFEND AGAINST, stated plainly: a transcriber who
quietly "corrects" the page while typing it. That transcription passes,
because nothing here can read the original — and worse, a silent
emendation of exactly this kind HIDES a real divergence by making the two
witnesses agree. The mechanism makes an emendation declarable, checkable
and counted; keeping it honest is the transcription discipline, not the
checker."""

import json
import re
from pathlib import Path

from .normalize import substantive


def load_witness(path: Path):
    meta, lines, corrigenda = {}, [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            m = re.match(r"#\s*([\w-]+):\s*(.*)", line)
            if not m:
                continue
            key, value = m.group(1), m.group(2)
            if key == "corrigendum":
                arrow = re.match(r"(\S+)\s*->\s*(\S+)\s*(?:\((.*)\))?", value)
                if arrow:
                    corrigenda.append((arrow.group(1), arrow.group(2), arrow.group(3) or ""))
                else:
                    corrigenda.append((value, "", ""))  # malformed; reported below
            else:
                meta[key] = value
        elif line.strip():
            lines.append(line.strip())
    meta["corrigenda"] = corrigenda
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
    errors, warnings = [], []
    toks = corpus_tokens(doc)
    ours_raw = [t for _, t in toks]
    ours_sub = substantive(" ".join(ours_raw)).split()

    app_path = witness_dir / "apparatus.json"
    apparatus = (
        json.loads(app_path.read_text(encoding="utf-8"))
        if app_path.exists()
        else {"adjudicated": []}
    )
    adjudicated = {
        (e["at"], wid): e
        for e in apparatus["adjudicated"]
        for wid in e["witnesses"]
    }

    witness_files = sorted(p for p in witness_dir.glob("*.txt"))
    if not witness_files:
        errors.append(f"no witness files in {witness_dir} — collation cannot pass on zero witnesses")

    used = set()
    n_variants = 0
    n_corrigenda = 0
    for wf in witness_files:
        meta, text = load_witness(wf)
        wid = meta.get("witness", wf.stem)
        # Declared printer's slips: each must actually be in the file, and
        # each is applied openly before anything is compared.
        for printed, emended, reason in meta["corrigenda"]:
            if not emended:
                errors.append(
                    f"{wid}: malformed corrigendum {printed!r} — write 'printed -> emended (reason)'"
                )
                continue
            if not reason:
                errors.append(f"{wid}: corrigendum {printed!r} carries no reason")
            # The declared reading is the WORD; the token may carry the
            # page's punctuation, which the emendation leaves alone.
            def _swap(token: str) -> str:
                body = token.rstrip(",.:;?!")
                tail = token[len(body) :]
                return emended + tail if body == printed else token

            tokens = text.split()
            if not any(_swap(t) != t for t in tokens):
                errors.append(
                    f"{wid}: corrigendum declares {printed!r}, which this witness does not print "
                    "— stale declaration, or the transcription was already emended"
                )
                continue
            text = " ".join(_swap(t) for t in tokens)
            n_corrigenda += 1
        fold_ji = meta.get("fold-ji", "").strip().lower() == "true"
        fold_xs = meta.get("fold-xs", "").strip().lower() == "true"
        folded = fold_ji or fold_xs
        ours_cmp = (
            substantive(" ".join(ours_raw), fold_ji=fold_ji, fold_xs=fold_xs).split()
            if folded
            else ours_sub
        )
        wit_sub = substantive(text, fold_ji=fold_ji, fold_xs=fold_xs).split()
        if wit_sub != ours_cmp:
            diverged = False
            for i, (a, b) in enumerate(zip(ours_cmp, wit_sub)):
                if a != b:
                    errors.append(
                        f"{wid}: SUBSTANTIVE divergence at word {i + 1} "
                        f"({toks[i][0] if i < len(toks) else '?'}): ours={a!r} witness={b!r}"
                    )
                    diverged = True
                    break
            if not diverged:
                errors.append(
                    f"{wid}: SUBSTANTIVE length mismatch: ours={len(ours_cmp)} witness={len(wit_sub)}"
                )
            continue
        if meta.get("profile", "").strip() == "substantive-only":
            # Witness with a different accidental profile (unaccented,
            # different punctuation): the letters have been verified above;
            # accidental comparison against it would be noise.
            continue
        wit_raw = text.split()
        if len(wit_raw) != len(ours_raw):
            errors.append(
                f"{wid}: raw token count mismatch despite substantive match "
                f"(ours={len(ours_raw)} witness={len(wit_raw)}) — punctuation split a token?"
            )
            continue
        for (word_id, ours_tok), wit_tok in zip(toks, wit_raw):
            if ours_tok == wit_tok:
                continue
            entry = adjudicated.get((word_id, wid))
            if entry and entry["ours"] == ours_tok and entry["witnesses"][wid] == wit_tok:
                used.add((word_id, wid))
                n_variants += 1
            else:
                errors.append(
                    f"{wid}: UNADJUDICATED variant at {word_id}: "
                    f"ours={ours_tok!r} witness={wit_tok!r} — record a ruling in apparatus.json or fix the text"
                )

    # Stale apparatus entries: recorded diffs that no witness produced.
    for (word_id, wid), entry in adjudicated.items():
        if entry["witnesses"][wid] != entry["ours"] and (word_id, wid) not in used:
            warnings.append(f"apparatus entry {word_id}/{wid} did not match any observed variant — stale?")

    stats = {
        "witnesses": len(witness_files),
        "words": len(toks),
        "variants_adjudicated": n_variants,
        "corrigenda": n_corrigenda,
    }
    return errors, warnings, stats

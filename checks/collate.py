"""Collation: corpus verse text against independent witnesses of the SAME
recension. Substantive text (letters) must match with zero divergence;
accidentals (punctuation, capitalization, capital-accents) must each be
covered by an adjudicated entry in the text's apparatus.json."""

import json
import re
from pathlib import Path

from .normalize import substantive


def load_witness(path: Path):
    meta, lines = {}, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            m = re.match(r"#\s*([\w-]+):\s*(.*)", line)
            if m:
                meta[m.group(1)] = m.group(2)
        elif line.strip():
            lines.append(line.strip())
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
    for wf in witness_files:
        meta, text = load_witness(wf)
        wid = meta.get("witness", wf.stem)
        wit_sub = substantive(text).split()
        if wit_sub != ours_sub:
            diverged = False
            for i, (a, b) in enumerate(zip(ours_sub, wit_sub)):
                if a != b:
                    errors.append(
                        f"{wid}: SUBSTANTIVE divergence at word {i + 1} "
                        f"({toks[i][0] if i < len(toks) else '?'}): ours={a!r} witness={b!r}"
                    )
                    diverged = True
                    break
            if not diverged:
                errors.append(
                    f"{wid}: SUBSTANTIVE length mismatch: ours={len(ours_sub)} witness={len(wit_sub)}"
                )
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
    }
    return errors, warnings, stats

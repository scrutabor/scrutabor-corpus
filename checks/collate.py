"""Collation: corpus verse text against independent witnesses, including
explicitly adjudicated alternate-recension readings. Substantive text
(letters) must match or have an explicit reading ruling;
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

A witness may carry a different lexical or grammatical READING, such as
inspexerunt/conspexerunt or resurgemus/resurgamus. A `substantive` ruling
quotes both exact tokens and explains the choice without calling it a spelling
or a printer's slip. The selected word must be positively attested at the
aligned locus by another full witness. These one-to-one variants are counted
separately; they cannot authorize missing words or excuse punctuation alone.

A `substantive-span` ruling quotes a complete replacement phrase, bounded
by `at` and `through` in document order. Its exact raw witness reading is
consumed at that locus, never searched for elsewhere. Only the comparison
buffer is aligned; the witness transcription remains unchanged. Another
full, unmodified, one-to-one aligned witness must attest the entire chosen
phrase. The ordinary checks still examine every word outside the span.

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

import json
import re
from pathlib import Path
from typing import Any

from .normalize import substantive

# Letter-difference classes quote exact readings and are counted separately.
RULED_CLASSES = ("orthography", "inflection", "substantive")
ACCIDENTAL_CLASSES = ("accent", "capital-accent", "capitalization", "orthography", "punctuation")


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


def _spans(entries, toks, errors):
    """Validate explicit ranges before any witness can use them."""
    positions = {word_id: i for i, (word_id, _) in enumerate(toks)}
    spans = []
    for entry in entries:
        if entry.get("class") != "substantive-span":
            continue
        at, through = entry["at"], entry.get("through")
        label = f"apparatus substantive-span {at}..{through}"
        if at not in positions or not isinstance(through, str) or through not in positions:
            errors.append(f"{label}: endpoints must name existing words")
            continue
        first, last = positions[at], positions[through]
        if last < first:
            errors.append(f"{label}: range runs backwards in document order")
            continue
        if entry["ours"] != " ".join(token for _, token in toks[first : last + 1]):
            errors.append(f"{label}: ours must quote the exact complete form+post sequence")
            continue
        if not isinstance(entry.get("ruling"), str) or not entry["ruling"].strip():
            errors.append(f"{label}: a nonempty ruling is required")
            continue
        valid = True
        for wid, reading in entry["witnesses"].items():
            words = reading.split()
            if (
                not words
                or reading != " ".join(words)
                or not any(c.isalpha() for c in words[0])
                or not any(c.isalpha() for c in words[-1])
                or any(
                    len(substantive(w).split()) != 1 for w in words if any(c.isalpha() for c in w)
                )
            ):
                errors.append(f"{label}/{wid}: quote a nonempty exact word sequence")
                valid = False
            elif substantive(reading) == substantive(entry["ours"]):
                errors.append(f"{label}/{wid}: redundant or accidental-only span")
                valid = False
        if valid:
            spans.append((first, last, entry))
    spans.sort(key=lambda span: span[0])
    for i, (first, last, entry) in enumerate(spans):
        for prior_first, prior_last, prior in spans[:i]:
            if first <= prior_last and prior_first <= last:
                errors.append(
                    f"apparatus: overlapping substantive spans {prior['at']}..{prior['through']} "
                    f"and {entry['at']}..{entry['through']}"
                )
        for other in entries:
            if other.get("class") == "substantive-span":
                continue
            if first <= positions.get(other["at"], -1) <= last:
                shared = entry["witnesses"].keys() & other["witnesses"].keys()
                if shared:
                    errors.append(
                        f"apparatus: reading at {other['at']}/{','.join(sorted(shared))} "
                        f"overlaps substantive span {entry['at']}..{entry['through']}"
                    )
    return spans


def _span_support(spans, witnesses, entries, ours_raw):
    """Raw ordinal alignment only: never obtain support from a replacement.

    Even balanced insertions/deletions can move a repeated phrase to the
    wrong locus while preserving total length. Exclude witnesses declaring
    any length-changing alignment, rather than using those rulings to prove
    themselves. This intentionally does not infer alignment for them.
    """
    support: dict[str, set[str]] = {}
    ours = [substantive(token) for token in ours_raw]
    for path, meta, text in witnesses:
        wid = meta.get("witness", path.stem)
        if meta.get("covers", "").strip() or meta["recensions"]:
            continue
        if any(
            wid in entry["witnesses"]
            and (
                entry.get("class") == "omission"
                or (
                    entry.get("class") == "substantive-span"
                    and len(substantive(entry["ours"]).split())
                    != len(substantive(entry["witnesses"][wid]).split())
                )
            )
            for entry in entries
        ):
            continue
        raw = [t for t in text.split() if any(c.isalpha() for c in t)]
        printed = [substantive(token) for token in raw]
        if len(printed) != len(ours) or any(len(token.split()) != 1 for token in printed):
            continue
        for first, last, entry in spans:
            if printed[first : last + 1] == ours[first : last + 1]:
                support.setdefault(entry["at"], set()).add(wid)
    return support


def _align_spans(toks, text, wid, spans, adjudicated, attested, support, errors):
    """Consume declared phrases once, left-to-right; never fuzzy-match.

    Returns a comparison buffer and used ruling keys, or None on failure.
    Free-standing punctuation is retained in the exact interior quote;
    outside a span it follows the existing word-level accidental policy.
    """
    ids = {word_id: i for i, (word_id, _) in enumerate(toks)}
    ranges = {}
    for _, _, entry in spans:
        if entry["at"] not in ids or entry["through"] not in ids:
            errors.append(f"{wid}: substantive span lies outside declared witness coverage")
            return None
        ranges[ids[entry["at"]]] = (ids[entry["through"]], entry)
    raw = text.split()
    word_positions = [i for i, token in enumerate(raw) if any(c.isalpha() for c in token)]
    if any(len(substantive(raw[i]).split()) != 1 for i in word_positions):
        errors.append(f"{wid}: substantive span requires unambiguous word tokenization")
        return None
    rebuilt: list[str] = []
    used = set()
    omissions = 0
    i = j = 0
    while i < len(toks):
        word_id, ours = toks[i]
        if i in ranges:
            last, entry = ranges[i]
            reading = entry["witnesses"][wid]
            count = len(substantive(reading).split())
            if j + count > len(word_positions):
                observed = ""
            else:
                observed = " ".join(raw[word_positions[j] : word_positions[j + count - 1] + 1])
            if observed != reading:
                errors.append(
                    f"{wid}: substantive span {word_id}..{entry['through']} does not match "
                    f"the exact raw witness phrase at this locus: quoted={reading!r} "
                    f"observed={observed!r}"
                )
                return None
            if not (support.get(word_id, set()) - {wid}):
                errors.append(
                    f"{wid}: substantive span at {word_id} has no positive full-witness "
                    "support for the entire selected reading at this locus"
                )
                return None
            rebuilt.extend(token for _, token in toks[i : last + 1])
            used.add((word_id, wid))
            i, j = last + 1, j + count
            continue
        entry = adjudicated.get((word_id, wid))
        if entry and entry.get("class") == "omission":
            if not (
                entry["ours"] == ours
                and entry["witnesses"][wid] == ""
                and isinstance(entry.get("ruling"), str)
                and entry["ruling"].strip()
                and attested.get(word_id, set()) - {wid}
            ):
                errors.append(f"{wid}: invalid or unsupported omission alongside substantive span")
                return None
            rebuilt.append(ours)
            used.add((word_id, wid))
            omissions += 1
            i += 1
            continue
        if j == len(word_positions):
            errors.append(f"{wid}: SUBSTANTIVE length mismatch outside substantive spans")
            return None
        rebuilt.append(raw[word_positions[j]])
        i, j = i + 1, j + 1
    if j != len(word_positions):
        errors.append(f"{wid}: SUBSTANTIVE length mismatch outside substantive spans")
        return None
    return " ".join(rebuilt), used, omissions


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
    if not isinstance(apparatus, dict):
        errors.append("apparatus must be an object")
        apparatus = {}
    expected_apparatus = f"witnesses/{doc['id']}/apparatus.json"
    declared_apparatus = (doc.get("source") or {}).get("apparatus")
    # Tiny synthetic documents in unit tests need no repository layout.
    # Real corpus documents always carry ``source`` and therefore get the
    # bidirectional pointer check.
    if doc.get("source") is not None:
        if app_path.exists():
            if declared_apparatus != expected_apparatus:
                errors.append(
                    f"source.apparatus must point to {expected_apparatus!r} when that file exists"
                )
            if apparatus.get("text") != doc["id"]:
                errors.append(f"apparatus text must be {doc['id']!r}")
        elif declared_apparatus is not None:
            errors.append(f"source.apparatus points to missing file {declared_apparatus!r}")
    entries = apparatus.get("adjudicated")
    if not isinstance(entries, list):
        errors.append("apparatus.adjudicated must be an array")
        entries = []
    adjudicated = {}
    valid_entries = []
    for index, entry in enumerate(entries):
        if not (
            isinstance(entry, dict)
            and isinstance(entry.get("at"), str)
            and entry["at"]
            and isinstance(entry.get("ours"), str)
            and isinstance(entry.get("witnesses"), dict)
            and entry["witnesses"]
            and all(
                isinstance(wid, str) and wid and isinstance(reading, str)
                for wid, reading in entry["witnesses"].items()
            )
        ):
            errors.append(f"apparatus.adjudicated[{index}]: invalid reading record")
            continue
        valid_entries.append(entry)
        for wid in entry["witnesses"]:
            key = (entry["at"], wid)
            if key in adjudicated:
                errors.append(f"apparatus: duplicate reading at {entry['at']}/{wid}")
            else:
                adjudicated[key] = entry

    spans = _spans(valid_entries, toks, errors)

    witness_files = sorted(p for p in witness_dir.glob("*.txt"))
    if not witness_files:
        errors.append(
            f"no witness files in {witness_dir} — collation cannot pass on zero witnesses"
        )

    witnesses = [(path, *load_witness(path)) for path in witness_files]
    span_support = _span_support(spans, witnesses, valid_entries, ours_raw) if spans else {}
    # Positive support comes from the actual uncorrected transcription, not
    # from an apparatus replacement. Align by locus rather than searching for
    # the same word anywhere on a page. A partial witness cannot supply it.
    attested: dict[str, set[str]] = {}
    for path, meta, text in witnesses:
        if meta.get("covers", "").strip():
            continue
        printed = substantive(text).split()
        if len(printed) != len(ours_sub):
            continue
        for index, (chosen, observed) in enumerate(zip(ours_sub, printed, strict=True)):
            if chosen == observed:
                attested.setdefault(toks[index][0], set()).add(meta.get("witness", path.stem))

    used: set[tuple[str, str]] = set()
    n_variants = 0
    n_corrigenda = 0
    n_orthographic = 0
    n_inflection = 0
    n_recensions = 0
    n_omissions = 0
    n_partial = 0
    n_substantive = 0
    n_spans = 0
    for wf, meta, text in witnesses:
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
        witness_spans = [span for span in spans if wid in span[2]["witnesses"]]
        if witness_spans:
            if meta["recensions"]:
                errors.append(
                    f"{wid}: substantive spans cannot be aligned with header recension removals"
                )
                continue
            aligned = _align_spans(
                toks_w, text, wid, witness_spans, adjudicated, attested, span_support, errors
            )
            if aligned is None:
                continue
            text, span_used, omitted_count = aligned
            used.update(span_used)
            n_omissions += omitted_count
            n_spans += len(witness_spans)
            n_substantive += len(witness_spans)
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
            wit_raw_before = [t for t in text.split() if any(c.isalpha() for c in t)]
            omitted: dict[int, str] = {}
            valid = True
            # The apparatus names the exact locus. Do not guess the missing
            # position with sequence matching: an adjacent spelling variant
            # can otherwise merge the omission into an unequal replacement.
            for i, (word_id, ours_tok) in enumerate(toks_w):
                entry = adjudicated.get((word_id, wid))
                if not entry or entry.get("class") != "omission":
                    continue
                if not (
                    entry.get("ours") == ours_tok
                    and entry.get("witnesses", {}).get(wid) == ""
                    and isinstance(entry.get("ruling"), str)
                    and entry["ruling"].strip()
                ):
                    valid = False
                    continue
                if not (attested.get(word_id, set()) - {wid}):
                    errors.append(
                        f"{wid}: omission ruling at {word_id} has no positive full-witness "
                        "support for the selected reading at this locus"
                    )
                    valid = False
                    continue
                omitted[i] = word_id
            if (
                valid
                and omitted
                and len(wit_raw_before) == len(wit_sub)
                and len(wit_raw_before) + len(omitted) == len(toks_w)
            ):
                observed_tokens = iter(wit_raw_before)
                rebuilt = [
                    ours_tok if i in omitted else next(observed_tokens)
                    for i, (_, ours_tok) in enumerate(toks_w)
                ]
                text = " ".join(rebuilt)
                wit_sub = substantive(text, fold_ji=fold_ji, fold_xs=fold_xs).split()
                used.update((word_id, wid) for word_id in omitted.values())
                n_omissions += len(omitted)
        wit_raw = [token for token in text.split() if any(char.isalpha() for char in token)]
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
                # An ADJUDICATED INFLECTION is a ruled letter
                # difference: a name this edition leaves indeclinable and the
                # witness declines. It is counted apart from orthography
                # because it is a question about grammar, not about spelling.
                word_id, ours_tok = toks_w[i] if i < len(toks_w) else ("?", "")
                entry = adjudicated.get((word_id, wid))
                if (
                    entry
                    and entry.get("class") in RULED_CLASSES
                    and entry["ours"] == ours_tok
                    and len(wit_raw) == len(toks_w)
                    and entry["witnesses"].get(wid) == wit_raw[i]
                    and isinstance(entry.get("ruling"), str)
                    and entry["ruling"].strip()
                ):
                    if entry["class"] == "substantive" and not (
                        attested.get(word_id, set()) - {wid}
                    ):
                        errors.append(
                            f"{wid}: substantive ruling at {word_id} has no positive full-witness "
                            "support for the selected reading at this locus"
                        )
                        unruled = True
                        break
                    used.add((word_id, wid))
                    if entry["class"] == "inflection":
                        n_inflection += 1
                    elif entry["class"] == "substantive":
                        n_substantive += 1
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
        # A source may set a parenthetic break as a free-standing dash.  It
        # is punctuation, not a word, and therefore has no corpus word ID;
        # retain it in the exact witness transcription and ignore only that
        # punctuation-only token when aligning word-level accidentals.
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
            if (
                entry
                and entry.get("class") in ACCIDENTAL_CLASSES
                and entry["ours"] == ours_tok
                and entry["witnesses"][wid] == wit_tok
            ):
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
        "substantive_variants": n_substantive,
        "substantive_spans": n_spans,
        "recensions": n_recensions,
        "omissions": n_omissions,
    }
    return errors, warnings, stats

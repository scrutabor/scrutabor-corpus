"""Every inherited translation states how it relates to its wording sources.

The hash ledger answers whether a reviewed translation changed. This grouped
registry answers a different reader-facing question: whether the displayed
wording is exact, normalized, revised, or a traditional composite. Records are
grouped by text and optional segment selection so the same fact is not repeated
at every translation site.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from build_reader import store
from checks.translation_provenance import load as load_provenance

RELATIONSHIPS = frozenset(("exact", "normalized", "revised", "traditional-composite"))
INHERITED = frozenset(("public-domain", "traditional"))


def check(corpus: Path) -> tuple[list[str], dict[str, int]]:
    provenance, errors = load_provenance(corpus)
    expected = {site for site, entry in provenance.items() if entry.get("origin") in INHERITED}
    expanded: dict[str, str] = {}
    tally: Counter[str] = Counter()

    for language in store.language_ids(corpus):
        path = corpus / "languages" / language / "translation-basis.json"
        where = str(path.relative_to(corpus))
        if not path.exists():
            errors.append(f"{where} is missing")
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        if doc.get("schema_version") != "1.0.0":
            errors.append(f"{where}: schema_version must be '1.0.0'")
        if doc.get("language") != language:
            errors.append(f"{where}: language does not match its directory")
        records = doc.get("records")
        if not isinstance(records, list):
            errors.append(f"{where}: records must be a list")
            continue

        covered = set(store.language_manifest(corpus, language).get("texts") or [])
        for index, record in enumerate(records):
            label = f"{where}:records[{index}]"
            if not isinstance(record, dict) or set(record) - {
                "texts",
                "segments",
                "relationship",
            }:
                errors.append(f"{label}: unknown record shape")
                continue
            texts = record.get("texts")
            segments = record.get("segments")
            relationship = record.get("relationship")
            if (
                not isinstance(texts, list)
                or not texts
                or len(texts) != len(set(texts))
                or not all(isinstance(text, str) and text in covered for text in texts)
            ):
                errors.append(f"{label}: texts must be unique covered text ids")
                continue
            if segments is not None and (
                not isinstance(segments, list)
                or not segments
                or len(segments) != len(set(segments))
                or not all(isinstance(segment, str) for segment in segments)
            ):
                errors.append(f"{label}: segments must be unique nonempty ids")
                continue
            if relationship not in RELATIONSHIPS:
                errors.append(f"{label}: unknown relationship {relationship!r}")
                continue

            for text_id in texts:
                core = store.core(corpus, text_id)
                verse_ids = [
                    segment["id"]
                    for segment in core.get("segments") or []
                    if segment.get("type") == "verse"
                ]
                selected = verse_ids if segments is None else segments
                unknown = sorted(set(selected) - set(verse_ids))
                if unknown:
                    errors.append(f"{label}: {text_id} has no verse segment(s) {unknown}")
                    continue
                for segment_id in selected:
                    site = f"{text_id}.{segment_id}.{language}"
                    if site in expanded:
                        errors.append(f"{site}: translation-basis records overlap")
                    else:
                        expanded[site] = relationship
                        tally[relationship] += 1

    missing = sorted(expected - set(expanded))
    extra = sorted(set(expanded) - expected)
    if missing:
        errors.append(
            f"translation basis: {len(missing)} inherited site(s) missing; first={missing[:5]}"
        )
    if extra:
        errors.append(
            f"translation basis: {len(extra)} non-inherited site(s) classified; first={extra[:5]}"
        )
    return errors, dict(sorted(tally.items()))

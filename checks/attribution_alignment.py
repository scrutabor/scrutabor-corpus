"""Source-specific performer evidence across declared one-to-one variants.

This does not establish textual identity. It is restricted to one complete
Mass verse and one unmarked, explicitly bound source line, supported by another
complete unmodified witness. Partial or length-changing readings are ineligible.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from .collate import collate, corpus_tokens, load_witness
from .normalize import substantive
from .raw_binding import BindingError, resolve_binding


@dataclass(frozen=True)
class AlignedWord:
    word_id: str
    selected: str
    source: str
    relation: str


@dataclass(frozen=True)
class AttributionAlignment:
    witness_id: str
    witness_path: Path
    source_path: Path
    source_line: int
    source_sha256: str
    supporting_witnesses: tuple[str, ...]
    words: tuple[AlignedWord, ...]
    literal_text_equal: bool

    @property
    def substantive_variants(self) -> int:
        return sum(word.relation == "substantive" for word in self.words)


def _complete_unmodified(meta: dict) -> bool:
    return not any(meta.get(key) for key in ("covers", "corrigenda", "recensions"))


def align_unmarked_reading(doc: dict, root: Path) -> AttributionAlignment | None:
    """Return single-source attribution evidence, never pooled textual support.

    Ineligibility or invalid evidence returns None. Exact raw comparison and
    full collation are prerequisites, not alternatives to this alignment.
    """
    segments = doc.get("segments", [])
    if (
        doc.get("category") not in {"ordinarium", "proprium"}
        or len(segments) != 1
        or segments[0].get("type") != "verse"
        or not segments[0].get("words")
    ):
        return None
    witness_dir = root / "witnesses" / doc["id"]
    source = doc.get("source") or (doc.get("editorial") or {}).get("source") or {}
    if source.get("apparatus") != f"witnesses/{doc['id']}/apparatus.json":
        return None
    try:
        selected = corpus_tokens(doc)
        apparatus = json.loads((witness_dir / "apparatus.json").read_text(encoding="utf-8"))
        errors, warnings, _ = collate(doc, witness_dir)
    except (OSError, ValueError):
        return None
    if errors or warnings:
        return None
    selected_normal = [substantive(face) for _, face in selected]
    if any(len(face.split()) != 1 for face in selected_normal):
        return None
    try:
        witnesses = [(path, *load_witness(path)) for path in sorted(witness_dir.glob("*.txt"))]
    except (OSError, ValueError):
        return None
    for witness, meta, _ in witnesses:
        witness_id = meta.get("witness", witness.stem)
        if witness_id != witness.stem or not _complete_unmodified(meta):
            continue
        try:
            bound = resolve_binding(witness, root)
        except BindingError:
            return None
        if bound is None or len(bound.spans) != 1:
            continue
        raw, first, last = bound.spans[0]
        if first != last:
            continue
        raw_bytes = raw.read_bytes()
        line = raw_bytes.decode("utf-8").splitlines()[first - 1]
        if re.match(r"^[SMVROsmvro]\.\s+", line.strip()):
            continue
        entries = [entry for entry in apparatus["adjudicated"] if witness_id in entry["witnesses"]]
        if any(entry["class"] in {"omission", "substantive-span"} for entry in entries):
            continue
        supporting = tuple(
            other.stem
            for other, other_meta, other_body in witnesses
            if other != witness
            and other_meta.get("witness", other.stem) == other.stem
            and _complete_unmodified(other_meta)
            and substantive(other_body).split() == selected_normal
        )
        if not supporting:
            continue
        printed = bound.text.split()
        if len(printed) != len(selected):
            continue
        by_word = {entry["at"]: entry for entry in entries}
        aligned = []
        for (word_id, ours), observed in zip(selected, printed, strict=True):
            if len(substantive(observed).split()) != 1:
                break
            if substantive(ours) == substantive(observed):
                relation = "same-substantive-token"
            else:
                entry = by_word.get(word_id)
                if (
                    not entry
                    or entry["class"] not in {"orthography", "inflection", "substantive"}
                    or entry["ours"] != ours
                    or entry["witnesses"][witness_id] != observed
                    or not entry.get("ruling", "").strip()
                ):
                    break
                relation = entry["class"]
            aligned.append(AlignedWord(word_id, ours, observed, relation))
        else:
            return AttributionAlignment(
                witness_id,
                witness,
                raw,
                first,
                hashlib.sha256(raw_bytes).hexdigest(),
                supporting,
                tuple(aligned),
                bound.text == " ".join(face for _, face in selected),
            )
    return None

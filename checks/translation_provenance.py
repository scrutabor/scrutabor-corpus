"""Every vernacular translation names its public provenance state.

A citation inventory cannot cover an uncited translation, and an absent
citation is itself a claim: the wording is the edition's own. The public
provenance ledger therefore covers every `verse segment × language` site and
binds its state to hashes of both source and target. A translation edit cannot
inherit an old review state silently, and deleting a citation cannot delete the
site.

The ledger deliberately contains no drafting notes or comparison text. It says
only what a public reader of the corpus needs to know: origin, review level,
whether exact familiarity is being protected, and which two strings were
classified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from build_reader import store

ORIGINS = frozenset(("working-unsettled", "own", "public-domain", "traditional", "trivial"))
REVIEWS = frozenset(("working", "internally-reviewed", "expert-reviewed"))

PROTECTED_PL_TEXTS = frozenset(
    {
        "defunctorum.requiem-aeternam",
        "litaniae.lauretanae",
        "litaniae.sacratissimi-cordis-iesu",
        "litaniae.sanctissimi-nominis-iesu",
        "orationes.angelus-domini",
        "orationes.ave-maria",
        "orationes.gloria-patri",
        "orationes.magnificat",
        "orationes.anima-christi",
        "orationes.memorare",
        "orationes.pater-noster",
        "orationes.regina-caeli",
        "orationes.salve-regina",
        "orationes.sancte-michael",
        "orationes.signum-crucis",
        "orationes.sub-tuum-praesidium",
        "orationes.symbolum-apostolorum",
        "ordinarium.agnus-dei",
        "ordinarium.confiteor",
        "ordinarium.confiteor-sacerdotis",
        "ordinarium.credo",
        "ordinarium.gloria",
        "ordinarium.kyrie",
        "ordinarium.pater-noster",
        "ordinarium.sanctus",
    }
)

PROTECTED_EN_TEXTS = frozenset(
    {
        "defunctorum.requiem-aeternam",
        "orationes.angelus-domini",
        "orationes.ave-maria",
        "orationes.gloria-patri",
        "orationes.pater-noster",
        "orationes.regina-caeli",
        "orationes.salve-regina",
        "orationes.sancte-michael",
        "orationes.signum-crucis",
        "orationes.sub-tuum-praesidium",
        "orationes.symbolum-apostolorum",
        "ordinarium.confiteor",
        "ordinarium.confiteor-sacerdotis",
        "ordinarium.kyrie",
        "ordinarium.pater-noster",
    }
)


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def source_payload(segment: dict) -> dict:
    """Source-bearing fields whose change makes a translation review stale."""
    return {
        "id": segment["id"],
        "speaker": segment.get("speaker"),
        "voice": segment.get("voice"),
        **({"delivery": segment["delivery"]} if "delivery" in segment else {}),
        "words": [
            {
                key: word[key]
                for key in (
                    "id",
                    "form",
                    "post",
                    "lemma",
                    "morph",
                    "head",
                    "substantive",
                )
                if key in word
            }
            for word in segment.get("words", [])
        ],
    }


def protected(text_id: str, language: str) -> bool:
    if language == "pl":
        return text_id in PROTECTED_PL_TEXTS
    if language == "en":
        return text_id in PROTECTED_EN_TEXTS
    return False


def corpus_sites(corpus: Path) -> dict[str, dict]:
    sites: dict[str, dict] = {}
    for doc, layers in store.all_texts(corpus):
        for segment in doc["segments"]:
            if segment["type"] != "verse":
                continue
            for language, layer in sorted(layers.items()):
                localized = (layer.get("segments") or {}).get(segment["id"]) or {}
                target = localized.get("translation")
                if not isinstance(target, str):
                    continue
                site = f"{doc['id']}.{segment['id']}.{language}"
                sites[site] = {
                    "site": site,
                    "text": doc["id"],
                    "segment": segment["id"],
                    "language": language,
                    "familiar_core": protected(doc["id"], language),
                    "source_sha256": canonical_hash(source_payload(segment)),
                    "target_sha256": canonical_hash(target),
                    "has_wording_citations": bool(localized.get("translation_citations")),
                }
    return sites


def load(corpus: Path) -> tuple[dict, list[str]]:
    by_site: dict[str, dict] = {}
    errors: list[str] = []
    for language in store.language_ids(corpus):
        path = corpus / "languages" / language / "translation-provenance.json"
        where = str(path.relative_to(corpus))
        if not path.exists():
            errors.append(f"{where} is missing")
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        if doc.get("schema_version") != "1.0.0":
            errors.append(f"{where}: schema_version must be '1.0.0'")
        if doc.get("language") != language:
            errors.append(f"{where}: language does not match its directory")
        if doc.get("status") != "working-edition":
            errors.append(f"{where}: status must be 'working-edition'")
        entries = doc.get("sites")
        if not isinstance(entries, list):
            errors.append(f"{where}: sites must be a list")
            continue
        for entry in entries:
            site = entry.get("site") if isinstance(entry, dict) else None
            if site in by_site:
                errors.append(f"{where}: duplicate site key {site!r}")
            elif site is not None:
                by_site[site] = entry
    return by_site, errors


def check(corpus: Path) -> tuple[list[str], dict[str, int]]:
    current = corpus_sites(corpus)
    recorded, errors = load(corpus)
    missing = sorted(set(current) - set(recorded))
    orphaned = sorted(set(recorded) - set(current))
    if missing:
        errors.append(
            f"translation provenance: {len(missing)} site(s) missing; first={missing[:5]}"
        )
    if orphaned:
        errors.append(
            f"translation provenance: {len(orphaned)} orphaned site(s); first={orphaned[:5]}"
        )

    tally: Counter[str] = Counter()
    for site in sorted(set(current) & set(recorded)):
        actual = current[site]
        entry = recorded[site]
        origin = entry.get("origin")
        review = entry.get("review")
        tally[str(origin)] += 1
        if origin not in ORIGINS:
            errors.append(f"{site}: unknown origin {origin!r}")
        if review not in REVIEWS:
            errors.append(f"{site}: unknown review level {review!r}")
        for key in ("text", "segment", "language", "familiar_core"):
            if entry.get(key) != actual[key]:
                errors.append(f"{site}: stale or incorrect {key}")
        for key in ("source_sha256", "target_sha256"):
            if entry.get(key) != actual[key]:
                errors.append(f"{site}: stale {key}")
        cited = actual["has_wording_citations"]
        if origin in {"own", "trivial"} and cited:
            errors.append(f"{site}: origin={origin} cannot carry a wording citation")
        if origin in {"public-domain", "traditional"} and not cited:
            errors.append(f"{site}: origin={origin} requires a wording citation")
        if origin == "working-unsettled" and review != "working":
            errors.append(f"{site}: unsettled origin cannot claim review={review}")
    return errors, dict(sorted(tally.items()))


def initialize(corpus: Path, language: str) -> int:
    if language not in store.language_ids(corpus):
        print(f"refusing to initialize unknown language {language!r}")
        return 1
    path = corpus / "languages" / language / "translation-provenance.json"
    if path.exists():
        print(f"refusing to overwrite {path.name}")
        return 1
    sites = {
        site: value for site, value in corpus_sites(corpus).items() if value["language"] == language
    }
    entries = []
    for site in sorted(sites):
        actual = sites[site]
        entries.append(
            {key: actual[key] for key in ("site", "text", "segment", "language", "familiar_core")}
            | {
                "origin": "working-unsettled",
                "review": "working",
                "source_sha256": actual["source_sha256"],
                "target_sha256": actual["target_sha256"],
            }
        )
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "language": language,
                "status": "working-edition",
                "sites": entries,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"translation provenance initialized — sites={len(entries)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--language")
    args = parser.parse_args()
    corpus = Path(__file__).resolve().parent.parent
    if args.initialize:
        if not args.language:
            parser.error("--initialize requires --language")
        return initialize(corpus, args.language)
    errors, tally = check(corpus)
    for error in errors:
        print(f"ERROR: {error}")
    print(
        f"TRANSLATION PROVENANCE sites={sum(tally.values())} "
        + " ".join(f"{key}={value}" for key, value in tally.items())
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

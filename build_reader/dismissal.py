"""Independent reconstruction and dependency checks for dismissal.json."""

from __future__ import annotations

import json
from pathlib import Path

from kalendarium.computus import easter
from kalendarium.dismissal import YEARS, canonical_inputs, validate
from kalendarium.roman import year

# Independently declared body/profile inventory; no producer projection or classifier.
PROFILES = [
    {"id": "ordinary", "text": "ordinarium.ite-missa-est"},
    {"id": "paschale", "text": "ordinarium.ite-missa-est-paschale"},
    {"id": "defunctorum", "text": "ordinarium.ite-missa-est-defunctorum"},
]


def input_bodies(corpus: Path) -> None:
    """Fail before emission if either declared body is unavailable in PL/EN."""
    from build_reader import store
    from checks.ritual import base_errors

    for profile in PROFILES:
        identity = profile["text"]
        doc = store.core(corpus, identity)
        from checks.requiem_dismissal import publication_errors

        errors = base_errors(doc) + publication_errors(doc)
        if errors:
            raise ValueError("dismissal: invalid source ritual: " + "; ".join(errors))
        if doc.get("id") != identity or not any(s.get("words") for s in doc.get("segments", [])):
            raise ValueError(f"dismissal: {identity} requires a nonempty neutral body")
        for language in ("pl", "en"):
            manifest = json.loads(
                (corpus / f"languages/{language}/manifest.json").read_text(encoding="utf-8")
            )
            if (
                not isinstance(manifest.get("texts"), list)
                or manifest["texts"].count(identity) != 1
            ):
                raise ValueError(f"dismissal: {identity} requires a declared {language} body")
            layer = json.loads(
                (
                    corpus / f"languages/{language}/texts/{identity.replace('.', '/', 1)}.json"
                ).read_text(encoding="utf-8")
            )
            if layer.get("text") != identity or layer.get("language") != language:
                raise ValueError(
                    f"dismissal: {identity} requires a correctly identified {language} body"
                )
            for segment in doc["segments"]:
                if segment.get("words"):
                    localized = layer.get("segments", {}).get(segment["id"], {})
                    if (
                        not isinstance(localized.get("translation"), str)
                        or not localized["translation"].strip()
                    ):
                        raise ValueError(
                            f"dismissal: {identity}/{language}/{segment['id']} has no translation"
                        )


def expected(corpus: Path) -> dict:
    """No call to the producer selector: iterate actual canonical days anew."""
    forms, _ = canonical_inputs(corpus)
    masses = sorted(form["id"] for form in forms)
    pairs = []
    for ending in YEARS:
        for day in year(ending):
            candidates = [f for f in forms if f["calendar"]["key"] == day.formulary]
            for form in candidates:
                delta = day.when - easter(day.when.year)
                profile = 0
                if (form["id"] == "vigilia-paschalis" and delta.days == -1) or (
                    form["collection"] == "temporale" and delta.days in range(7)
                ):
                    profile = 1
                if (
                    form["id"]
                    in {
                        "commemoratio-omnium-fidelium-defunctorum",
                        "commemoratio-omnium-fidelium-defunctorum-missa-ii",
                        "commemoratio-omnium-fidelium-defunctorum-missa-iii",
                    }
                    and form["observance"] == "commemoratio-omnium-fidelium-defunctorum"
                    and form["collection"] == "sanctorale"
                ):
                    profile = 2
                pairs.append([day.when.isoformat(), masses.index(form["id"]), profile])
    return {
        "schema_version": "1.1.0",
        "role": "ite-missa-est",
        "profiles": PROFILES,
        "masses": masses,
        "pairs": sorted(pairs),
    }


def verify(corpus: Path, out: Path, manifest: dict, reader_schema: str) -> list[str]:
    errors = []

    def read(name):
        try:
            return json.loads((out / name).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(f"dismissal: cannot read {name}: {exc}")
            return None

    base = manifest.get("base")
    if (
        manifest.get("schema_version") != reader_schema
        or not isinstance(base, dict)
        or base.get("dismissal") != "dismissal.json"
    ):
        errors.append("dismissal: root schema and base.dismissal declaration required")
    table = read("dismissal.json")
    try:
        validate(table)
    except ValueError as exc:
        errors.append(str(exc))
    if table != expected(corpus):
        errors.append("dismissal: resource differs from independent canonical reconstruction")

    def bodies(package, prefix, language=None):
        if not isinstance(package, dict):
            return
        declarations = package.get("texts")
        if not isinstance(declarations, list):
            errors.append(f"dismissal: {prefix} text declarations missing")
            return
        for profile in PROFILES:
            identity = profile["text"]
            path = f"{prefix}texts/{identity.replace('.', '/', 1)}.json"
            matches = [d for d in declarations if isinstance(d, dict) and d.get("id") == identity]
            if len(matches) != 1 or matches[0].get("path") != path:
                errors.append(f"dismissal: {path} must be declared exactly once")
                continue
            body = read(path)
            if (
                not isinstance(body, dict)
                or body.get("id") != identity
                or not isinstance(body.get("seg"), list)
                or not body["seg"]
                or (language and body.get("language") != language)
            ):
                errors.append(f"dismissal: {path} has wrong identity/language or empty body")

    bodies(manifest, "")
    for language in ("pl", "en"):
        name = f"languages/{language}/manifest.json"
        declarations = manifest.get("languages")
        matches = (
            [d for d in declarations if isinstance(d, dict) and d.get("id") == language]
            if isinstance(declarations, list)
            else []
        )
        if len(matches) != 1 or matches[0].get("path") != name:
            errors.append(f"dismissal: {name} must be declared exactly once")
            continue
        package = read(name)
        if (
            not isinstance(package, dict)
            or package.get("language") != language
            or package.get("schema_version") != reader_schema
            or package.get("corpus_schema") != manifest.get("corpus_schema")
        ):
            errors.append(f"dismissal: {name} has wrong package identity/version")
        bodies(package, f"languages/{language}/", language)
    return errors

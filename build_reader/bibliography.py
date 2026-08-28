"""Validate and project the corpus evidence graph.

The authored graph distinguishes abstract works, concrete editions, digital
items, uses, witnesses, and collations.  Reader artifacts are explicit
allowlisted projections of that graph: migration aliases, verification
digests, and editorial decisions never travel merely because they exist in
the source document.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

SCHEMA = "1.1.0"

GRAPH_KEYS = {
    "schema_version",
    "migration",
    "works",
    "editions",
    "digital_items",
    "uses",
    "witnesses",
    "collations",
}
LANGUAGE_GRAPH_KEYS = {"schema_version", "language", "uses"}
MIGRATION_KEYS = {"complete", "legacy_inventory", "removals"}
LEGACY_INVENTORY_KEYS = {"count", "sha256"}
REMOVAL_KEYS = {"legacy_ref", "reason"}
WORK_KEYS = {"id", "responsible", "title"}
EDITION_KEYS = {
    "id",
    "work",
    "recension",
    "title",
    "edition_statement",
    "contributors",
    "place",
    "publisher",
    "year",
    "volume",
    "publication_type",
    "authority",
    "rights",
}
RIGHTS_KEYS = {"status", "basis"}
DIGITAL_ITEM_KEYS = {
    "id",
    "edition",
    "repository",
    "kind",
    "record_url",
    "scan_url",
    "revision",
    "sha256",
    "access",
    "owner_scan_id",
    "digitization_rights",
}
USE_KEYS = {
    "id",
    "edition",
    "digital_item",
    "role",
    "address",
    "locator",
    "claim",
    "verified_on",
    "evidence_sha256",
    "decision",
    "decision_reason",
    "legacy_refs",
}
ADDRESS_KEYS = {"kind", "text", "segment", "word", "lemma"}
LOCATOR_KEYS = {"printed", "scan", "section", "page_url"}
WITNESS_KEYS = {
    "id",
    "text",
    "use",
    "role",
    "coverage",
    "transcription_sha256",
    "orthography_profile",
    "independence_basis",
}
COVERAGE_KEYS = {"kind", "segments", "words"}
COLLATION_KEYS = {
    "id",
    "text",
    "recension",
    "selected_text_sha256",
    "witnesses",
    "apparatus",
}
APPARATUS_KEYS = {"entries", "classes"}

PUBLICATION_TYPES = {
    "missal",
    "breviary",
    "ritual",
    "prayer_book",
    "official_act",
    "scripture",
    "lexicon",
    "grammar",
    "scholarly_book",
    "periodical",
    "web_resource",
    "other",
}
AUTHORITIES = {
    "typical_liturgical_edition",
    "official_liturgical_edition",
    "approved_ecclesiastical_edition",
    "official_document",
    "scriptural_edition",
    "scholarly_edition",
    "historical_devotional_edition",
    "reference_work",
    "secondary_study",
}
RIGHTS_STATUSES = {"public-domain", "own", "permission", "unverified"}
DIGITAL_KINDS = {"scan", "born-digital"}
ACCESS_STATES = {"open", "restricted", "owner-held"}
DECISIONS = {
    "RETAIN",
    "RETAIN_WITH_CORRECTION",
    "REPLACE",
    "REMOVE",
    "UNVERIFIED_NO_DIRECT_EVIDENCE",
}

LATIN_ROLES = {
    "controlling_official_text",
    "corroborating_latin_witness",
    "direct_approved_print",
    "derived_digital_collation_aid",
}
WORDING_ROLES = {"historical_wording_basis", "historical_wording_comparator"}
OFFICIAL_ROLES = {
    "official_liturgical_context",
    "rubric_control",
    "liturgical_history",
    "historical_context",
}
SCHOLARLY_ROLES = {
    "quotation_control",
    "scripture_control",
    "lexical_support",
    "grammatical_support",
    "semantic_comparator",
    "search_aid",
}
ROLES = LATIN_ROLES | WORDING_ROLES | OFFICIAL_ROLES | SCHOLARLY_ROLES
WITNESS_ROLES = {
    "controlling",
    "independent_corroboration",
    "approved_corroboration",
    "derived_comparison",
}

SECTION_ORDER = (
    "latin_textual_sources",
    "wording_witnesses",
    "official_documents_and_liturgical_history",
    "scripture_language_and_scholarship",
)
SECTION_ROLES = {
    "latin_textual_sources": LATIN_ROLES,
    "wording_witnesses": WORDING_ROLES,
    "official_documents_and_liturgical_history": OFFICIAL_ROLES,
    "scripture_language_and_scholarship": SCHOLARLY_ROLES,
}
ROLE_ORDER = {
    role: (section_number, role_number)
    for section_number, section in enumerate(SECTION_ORDER)
    for role_number, role in enumerate(sorted(SECTION_ROLES[section]))
}

ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def graph_path(corpus: Path) -> Path:
    return corpus / "bibliography" / "graph.json"


def language_graph_path(corpus: Path, language: str) -> Path:
    return corpus / "languages" / language / "bibliography.json"


def load(corpus: Path) -> tuple[dict, dict[str, dict]]:
    graph = json.loads(graph_path(corpus).read_text(encoding="utf-8"))
    language_graphs = {
        language: json.loads(language_graph_path(corpus, language).read_text(encoding="utf-8"))
        for language in _language_ids(corpus)
    }
    return graph, language_graphs


def _language_ids(corpus: Path) -> list[str]:
    return [path.parent.name for path in sorted((corpus / "languages").glob("*/manifest.json"))]


def _pointer(parts: tuple[str, ...]) -> str:
    return "/".join(part.replace("~", "~0").replace("/", "~1") for part in parts)


def legacy_inventory(corpus: Path) -> list[dict]:
    """Return every legacy inline citation with a deterministic source pointer."""
    paths = [
        *sorted(corpus.glob("texts/*/*.json")),
        *sorted(corpus.glob("languages/*/texts/*/*.json")),
        corpus / "lexicon" / "lemmata.json",
        *sorted(corpus.glob("languages/*/lexicon.json")),
    ]
    records: list[dict] = []

    def walk(node: object, path: Path, parts: tuple[str, ...]) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("title"), str) and "locator" in node:
                relative = path.relative_to(corpus).as_posix()
                records.append(
                    {
                        "ref": f"{relative}#/{_pointer(parts)}",
                        "citation": node,
                    }
                )
            for key, value in node.items():
                walk(value, path, (*parts, str(key)))
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, path, (*parts, str(index)))

    for path in paths:
        if path.is_file():
            walk(json.loads(path.read_text(encoding="utf-8")), path, ())
    return sorted(records, key=lambda record: record["ref"])


def legacy_digest(records: list[dict]) -> str:
    body = json.dumps(
        records,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(body).hexdigest()


def legacy_scope(reference: str) -> str:
    match = re.match(r"languages/([^/]+)/", reference)
    return match.group(1) if match else "neutral"


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _https(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _date(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _unknown(record: object, allowed: set[str], where: str, errors: list[str]) -> dict:
    if not isinstance(record, dict):
        errors.append(f"{where}: must be an object")
        return {}
    extra = set(record) - allowed
    if extra:
        errors.append(f"{where}: unknown keys {sorted(extra)}")
    return record


def _required_strings(record: dict, keys: tuple[str, ...], where: str, errors: list[str]) -> None:
    for key in keys:
        if not _nonempty(record.get(key)):
            errors.append(f"{where}.{key}: must be a nonempty string")


def _records(
    graph: dict, key: str, allowed: set[str], errors: list[str], *, prefix: str = "bibliography"
) -> list[dict]:
    values = graph.get(key)
    if not isinstance(values, list):
        errors.append(f"{prefix}.{key}: must be an array")
        return []
    out = [
        _unknown(value, allowed, f"{prefix}.{key}[{index}]", errors)
        for index, value in enumerate(values)
    ]
    ids: list[str] = [identifier for value in out if isinstance(identifier := value.get("id"), str)]
    duplicates = sorted(value for value, count in Counter(ids).items() if count > 1)
    if duplicates:
        errors.append(f"{prefix}.{key}: duplicate ids {duplicates}")
    if ids != sorted(ids):
        errors.append(f"{prefix}.{key}: records must be sorted by id")
    for index, value in enumerate(out):
        identifier = value.get("id")
        if not isinstance(identifier, str) or not ID_RE.fullmatch(identifier):
            errors.append(f"{prefix}.{key}[{index}].id: must be a stable lowercase id")
    return out


def _address_sets(
    corpus: Path,
) -> tuple[dict[str, set[str]], dict[str, set[str]], dict[str, list[str]], set[str]]:
    segments: dict[str, set[str]] = {}
    words: dict[str, set[str]] = {}
    word_order: dict[str, list[str]] = {}
    for path in sorted(corpus.glob("texts/*/*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        text_id = doc["id"]
        segments[text_id] = {segment["id"] for segment in doc.get("segments") or []}
        word_order[text_id] = [
            word["id"]
            for segment in doc.get("segments") or []
            for word in segment.get("words") or []
        ]
        words[text_id] = set(word_order[text_id])
    lemmata = set(
        json.loads((corpus / "lexicon" / "lemmata.json").read_text(encoding="utf-8"))["entries"]
    )
    return segments, words, word_order, lemmata


def _validate_address(
    address: object,
    where: str,
    segments: dict[str, set[str]],
    words: dict[str, set[str]],
    lemmata: set[str],
    errors: list[str],
) -> None:
    address = _unknown(address, ADDRESS_KEYS, where, errors)
    kind = address.get("kind")
    expected = {
        "text": {"kind", "text"},
        "segment": {"kind", "text", "segment"},
        "word": {"kind", "text", "word"},
        "lemma": {"kind", "lemma"},
    }
    if kind not in expected:
        errors.append(f"{where}.kind: must be one of {sorted(expected)}")
        return
    if set(address) != expected[kind]:
        errors.append(f"{where}: {kind} address must have exactly {sorted(expected[kind])}")
        return
    if kind == "lemma":
        if address.get("lemma") not in lemmata:
            errors.append(f"{where}: unknown lemma {address.get('lemma')!r}")
        return
    text_id = address.get("text")
    if text_id not in segments:
        errors.append(f"{where}: unknown text {text_id!r}")
        return
    if kind == "segment":
        if address.get("segment") not in segments[str(text_id)]:
            errors.append(f"{where}: unknown segment {address.get('segment')!r}")
    elif kind == "word" and address.get("word") not in words[str(text_id)]:
        errors.append(f"{where}: unknown word {address.get('word')!r}")


def _validate_uses(
    values: list[dict],
    editions: dict[str, dict],
    items: dict[str, dict],
    segments: dict[str, set[str]],
    words: dict[str, set[str]],
    lemmata: set[str],
    errors: list[str],
    *,
    language: str | None,
) -> None:
    prefix = f"languages.{language}.uses" if language else "bibliography.uses"
    for index, use in enumerate(values):
        where = f"{prefix}[{index}]"
        _required_strings(
            use,
            ("id", "edition", "digital_item", "role", "claim", "verified_on", "decision"),
            where,
            errors,
        )
        edition_id = use.get("edition")
        item_id = use.get("digital_item")
        if edition_id not in editions:
            errors.append(f"{where}.edition: unknown edition {edition_id!r}")
        item = items.get(item_id) if isinstance(item_id, str) else None
        if item is None:
            errors.append(f"{where}.digital_item: unknown item {item_id!r}")
        elif item.get("edition") != edition_id:
            errors.append(f"{where}: digital item belongs to a different edition")
        role = use.get("role")
        if role not in ROLES:
            errors.append(f"{where}.role: must be one of {sorted(ROLES)}")
        elif language is None and role in WORDING_ROLES:
            errors.append(f"{where}.role: wording evidence belongs in a language package")
        elif language is not None and role not in WORDING_ROLES:
            errors.append(f"{where}.role: language packages contain only wording evidence")
        if use.get("decision") not in DECISIONS:
            errors.append(f"{where}.decision: must be one of {sorted(DECISIONS)}")
        if use.get("decision") != "RETAIN" and not _nonempty(use.get("decision_reason")):
            errors.append(f"{where}.decision_reason: required unless decision is RETAIN")
        if not _date(use.get("verified_on")):
            errors.append(f"{where}.verified_on: must be an ISO date")
        digest = use.get("evidence_sha256")
        if digest is not None and (not isinstance(digest, str) or not SHA256_RE.fullmatch(digest)):
            errors.append(f"{where}.evidence_sha256: must be a lowercase SHA-256")
        _validate_address(
            use.get("address"),
            f"{where}.address",
            segments,
            words,
            lemmata,
            errors,
        )
        locator = _unknown(use.get("locator"), LOCATOR_KEYS, f"{where}.locator", errors)
        if "page_url" in locator and not _https(locator.get("page_url")):
            errors.append(f"{where}.locator.page_url: must be an absolute HTTPS URL")
        if item is not None and item.get("kind") == "scan":
            if not _nonempty(locator.get("printed")) or not _nonempty(locator.get("scan")):
                errors.append(f"{where}.locator: a scan requires printed and scan locators")
        elif (
            item is not None
            and item.get("kind") == "born-digital"
            and not _nonempty(locator.get("section"))
        ):
            errors.append(f"{where}.locator: born-digital evidence requires a section")
        legacy_refs = use.get("legacy_refs") or []
        if not isinstance(legacy_refs, list) or any(not _nonempty(ref) for ref in legacy_refs):
            errors.append(f"{where}.legacy_refs: must be an array of nonempty references")
        elif len(legacy_refs) != len(set(legacy_refs)):
            errors.append(f"{where}.legacy_refs: references must be unique")
        elif any(legacy_scope(ref) != (language or "neutral") for ref in legacy_refs):
            errors.append(f"{where}.legacy_refs: a use cannot claim another package's citation")


def validate(
    corpus: Path,
    graph: dict | None = None,
    language_graphs: dict[str, dict] | None = None,
) -> list[str]:
    """Validate graph shape, identity, package isolation, and legacy parity."""
    errors: list[str] = []
    if graph is None or language_graphs is None:
        try:
            loaded_graph, loaded_languages = load(corpus)
        except (OSError, json.JSONDecodeError) as exc:
            return [f"bibliography: cannot load evidence graph — {exc}"]
        graph = loaded_graph if graph is None else graph
        language_graphs = loaded_languages if language_graphs is None else language_graphs

    graph = _unknown(graph, GRAPH_KEYS, "bibliography", errors)
    if graph.get("schema_version") != SCHEMA:
        errors.append(f"bibliography.schema_version: must be {SCHEMA}")
    works = _records(graph, "works", WORK_KEYS, errors)
    editions = _records(graph, "editions", EDITION_KEYS, errors)
    items = _records(graph, "digital_items", DIGITAL_ITEM_KEYS, errors)
    uses = _records(graph, "uses", USE_KEYS, errors)
    witnesses = _records(graph, "witnesses", WITNESS_KEYS, errors)
    collations = _records(graph, "collations", COLLATION_KEYS, errors)

    works_by_id: dict[str, dict] = {
        identifier: work for work in works if isinstance(identifier := work.get("id"), str)
    }
    editions_by_id: dict[str, dict] = {
        identifier: edition
        for edition in editions
        if isinstance(identifier := edition.get("id"), str)
    }
    items_by_id: dict[str, dict] = {
        identifier: item for item in items if isinstance(identifier := item.get("id"), str)
    }
    uses_by_id: dict[str, dict] = {
        identifier: use for use in uses if isinstance(identifier := use.get("id"), str)
    }
    witnesses_by_id: dict[str, dict] = {
        identifier: witness
        for witness in witnesses
        if isinstance(identifier := witness.get("id"), str)
    }
    segments_by_text, words_by_text, word_order_by_text, lemmata = _address_sets(corpus)

    for index, work in enumerate(works):
        where = f"bibliography.works[{index}]"
        _required_strings(work, ("id", "title"), where, errors)
        responsible = work.get("responsible")
        if responsible is not None and not _nonempty(responsible):
            errors.append(f"{where}.responsible: must be a nonempty string when present")

    for index, edition in enumerate(editions):
        where = f"bibliography.editions[{index}]"
        _required_strings(
            edition,
            ("id", "work", "title", "year", "publication_type", "authority"),
            where,
            errors,
        )
        if edition.get("work") not in works_by_id:
            errors.append(f"{where}.work: unknown work {edition.get('work')!r}")
        if edition.get("publication_type") not in PUBLICATION_TYPES:
            errors.append(f"{where}.publication_type: unknown value")
        if edition.get("authority") not in AUTHORITIES:
            errors.append(f"{where}.authority: unknown value")
        contributors = edition.get("contributors") or []
        if not isinstance(contributors, list) or any(not _nonempty(v) for v in contributors):
            errors.append(f"{where}.contributors: must be an array of nonempty strings")
        rights = _unknown(edition.get("rights"), RIGHTS_KEYS, f"{where}.rights", errors)
        if rights.get("status") not in RIGHTS_STATUSES:
            errors.append(f"{where}.rights.status: unknown value")
        if not _nonempty(rights.get("basis")):
            errors.append(f"{where}.rights.basis: must be a nonempty string")

    for index, item in enumerate(items):
        where = f"bibliography.digital_items[{index}]"
        _required_strings(item, ("id", "edition", "repository", "kind", "access"), where, errors)
        if item.get("edition") not in editions_by_id:
            errors.append(f"{where}.edition: unknown edition {item.get('edition')!r}")
        if item.get("kind") not in DIGITAL_KINDS:
            errors.append(f"{where}.kind: must be one of {sorted(DIGITAL_KINDS)}")
        if item.get("access") not in ACCESS_STATES:
            errors.append(f"{where}.access: must be one of {sorted(ACCESS_STATES)}")
        for key in ("record_url", "scan_url"):
            if key in item and not _https(item.get(key)):
                errors.append(f"{where}.{key}: must be an absolute HTTPS URL")
        if not _https(item.get("record_url")) and not _nonempty(item.get("owner_scan_id")):
            errors.append(f"{where}: needs a stable record URL or an owner-held scan id")
        if (
            item.get("kind") == "scan"
            and not _https(item.get("scan_url"))
            and not _nonempty(item.get("owner_scan_id"))
        ):
            errors.append(f"{where}: a scan needs a scan URL or an owner-held scan id")
        digest = item.get("sha256")
        if digest is not None and (not isinstance(digest, str) or not SHA256_RE.fullmatch(digest)):
            errors.append(f"{where}.sha256: must be a lowercase SHA-256")

    _validate_uses(
        uses,
        editions_by_id,
        items_by_id,
        segments_by_text,
        words_by_text,
        lemmata,
        errors,
        language=None,
    )

    language_ids = set(_language_ids(corpus))
    if set(language_graphs) != language_ids:
        errors.append(
            "bibliography languages: graph coverage differs — "
            f"missing={sorted(language_ids - set(language_graphs))} "
            f"extra={sorted(set(language_graphs) - language_ids)}"
        )
    language_uses: dict[str, list[dict]] = {}
    all_use_ids = set(uses_by_id)
    for language, language_graph in sorted(language_graphs.items()):
        prefix = f"languages.{language}.bibliography"
        language_graph = _unknown(language_graph, LANGUAGE_GRAPH_KEYS, prefix, errors)
        if language_graph.get("schema_version") != SCHEMA:
            errors.append(f"{prefix}.schema_version: must be {SCHEMA}")
        if language_graph.get("language") != language:
            errors.append(f"{prefix}.language: must match its package")
        values = _records(
            language_graph,
            "uses",
            USE_KEYS,
            errors,
            prefix=f"languages.{language}.bibliography",
        )
        package_use_ids = {
            identifier for use in values if isinstance(identifier := use.get("id"), str)
        }
        duplicates = sorted(all_use_ids & package_use_ids)
        if duplicates:
            errors.append(f"{prefix}.uses: ids collide with another package {duplicates}")
        all_use_ids.update(package_use_ids)
        _validate_uses(
            values,
            editions_by_id,
            items_by_id,
            segments_by_text,
            words_by_text,
            lemmata,
            errors,
            language=language,
        )
        language_uses[language] = values

    edition_items = defaultdict(list)
    for item in items:
        edition_items[item.get("edition")].append(item.get("id"))
    for edition in editions:
        if not edition_items[edition.get("id")]:
            errors.append(f"bibliography.editions.{edition.get('id')}: has no digital item")

    for index, witness in enumerate(witnesses):
        where = f"bibliography.witnesses[{index}]"
        _required_strings(
            witness,
            (
                "id",
                "text",
                "use",
                "role",
                "transcription_sha256",
                "orthography_profile",
                "independence_basis",
            ),
            where,
            errors,
        )
        if witness.get("role") not in WITNESS_ROLES:
            errors.append(f"{where}.role: must be one of {sorted(WITNESS_ROLES)}")
        if not SHA256_RE.fullmatch(str(witness.get("transcription_sha256", ""))):
            errors.append(f"{where}.transcription_sha256: must be a lowercase SHA-256")
        use_id = witness.get("use")
        use = uses_by_id.get(use_id) if isinstance(use_id, str) else None
        if use is None:
            errors.append(f"{where}.use: must name a neutral use")
        elif use.get("role") not in LATIN_ROLES:
            errors.append(f"{where}.use: witness use must have a Latin textual role")
        elif (use.get("address") or {}).get("text") != witness.get("text"):
            errors.append(f"{where}.use: use and witness must address the same text")
        text_id = witness.get("text")
        if text_id not in segments_by_text:
            errors.append(f"{where}.text: unknown text {text_id!r}")
        coverage = _unknown(witness.get("coverage"), COVERAGE_KEYS, f"{where}.coverage", errors)
        if coverage.get("kind") not in {"full", "segments", "words"}:
            errors.append(f"{where}.coverage.kind: must be full, segments or words")
        if coverage.get("kind") == "full" and set(coverage) != {"kind"}:
            errors.append(f"{where}.coverage: full coverage has no segment list")
        if coverage.get("kind") == "segments":
            if set(coverage) != {"kind", "segments"}:
                errors.append(f"{where}.coverage: segment coverage has exactly a segment list")
            segments = coverage.get("segments")
            if (
                not isinstance(segments, list)
                or not segments
                or len(segments) != len(set(segments))
            ):
                errors.append(f"{where}.coverage.segments: must be a unique nonempty array")
            elif text_id in segments_by_text and (
                unknown := sorted(set(segments) - segments_by_text[str(text_id)])
            ):
                errors.append(f"{where}.coverage.segments: unknown ids {unknown}")
        if coverage.get("kind") == "words":
            if set(coverage) != {"kind", "words"}:
                errors.append(f"{where}.coverage: word coverage has exactly a word list")
            covered_words = coverage.get("words")
            if (
                not isinstance(covered_words, list)
                or not covered_words
                or len(covered_words) != len(set(covered_words))
            ):
                errors.append(f"{where}.coverage.words: must be a unique nonempty array")
            elif text_id in words_by_text:
                unknown = sorted(set(covered_words) - words_by_text[str(text_id)])
                if unknown:
                    errors.append(f"{where}.coverage.words: unknown ids {unknown}")
                expected_order = [
                    word_id
                    for word_id in word_order_by_text[str(text_id)]
                    if word_id in set(covered_words)
                ]
                if covered_words != expected_order:
                    errors.append(f"{where}.coverage.words: must follow canonical text order")

    seen_texts: set[str] = set()
    for index, collation in enumerate(collations):
        where = f"bibliography.collations[{index}]"
        _required_strings(
            collation,
            ("id", "text", "recension", "selected_text_sha256"),
            where,
            errors,
        )
        text_id = collation.get("text")
        if text_id in seen_texts:
            errors.append(f"{where}.text: a text has more than one active collation")
        if isinstance(text_id, str):
            seen_texts.add(text_id)
        if text_id not in segments_by_text:
            errors.append(f"{where}.text: unknown text {text_id!r}")
        if not SHA256_RE.fullmatch(str(collation.get("selected_text_sha256", ""))):
            errors.append(f"{where}.selected_text_sha256: must be a lowercase SHA-256")
        witness_ids = collation.get("witnesses")
        if (
            not isinstance(witness_ids, list)
            or len(witness_ids) < 2
            or len(witness_ids) != len(set(witness_ids))
        ):
            errors.append(f"{where}.witnesses: must name at least two unique witnesses")
            witness_ids = []
        for witness_id in witness_ids:
            collation_witness = (
                witnesses_by_id.get(witness_id) if isinstance(witness_id, str) else None
            )
            if collation_witness is None:
                errors.append(f"{where}.witnesses: unknown witness {witness_id!r}")
            elif collation_witness.get("text") != text_id:
                errors.append(f"{where}.witnesses: {witness_id!r} belongs to another text")
        apparatus = _unknown(
            collation.get("apparatus"), APPARATUS_KEYS, f"{where}.apparatus", errors
        )
        if not isinstance(apparatus.get("entries"), int) or apparatus.get("entries", -1) < 0:
            errors.append(f"{where}.apparatus.entries: must be a nonnegative integer")
        classes = apparatus.get("classes")
        if not isinstance(classes, list) or any(not _nonempty(value) for value in classes):
            errors.append(f"{where}.apparatus.classes: must be an array of nonempty strings")
        elif classes != sorted(set(classes)):
            errors.append(f"{where}.apparatus.classes: must be sorted and unique")

    migration = _unknown(graph.get("migration"), MIGRATION_KEYS, "bibliography.migration", errors)
    if not isinstance(migration.get("complete"), bool):
        errors.append("bibliography.migration.complete: must be boolean")
    snapshot = _unknown(
        migration.get("legacy_inventory"),
        LEGACY_INVENTORY_KEYS,
        "bibliography.migration.legacy_inventory",
        errors,
    )
    inventory = legacy_inventory(corpus)
    if snapshot.get("count") != len(inventory):
        errors.append(
            "bibliography.migration.legacy_inventory.count: "
            f"records {snapshot.get('count')!r}, found {len(inventory)}"
        )
    digest = legacy_digest(inventory)
    if snapshot.get("sha256") != digest:
        errors.append("bibliography.migration.legacy_inventory.sha256: legacy citations changed")
    removals = migration.get("removals")
    if not isinstance(removals, list):
        errors.append("bibliography.migration.removals: must be an array")
        removals = []
    removal_refs: list[str] = []
    for index, removal in enumerate(removals):
        where = f"bibliography.migration.removals[{index}]"
        removal = _unknown(removal, REMOVAL_KEYS, where, errors)
        _required_strings(removal, ("legacy_ref", "reason"), where, errors)
        if isinstance(reference := removal.get("legacy_ref"), str):
            removal_refs.append(reference)
    if removal_refs != sorted(removal_refs):
        errors.append("bibliography.migration.removals: must be sorted by legacy_ref")
    all_uses = [*uses, *(use for values in language_uses.values() for use in values)]
    mapped_refs = [ref for use in all_uses for ref in (use.get("legacy_refs") or [])]
    duplicates = sorted(ref for ref, count in Counter(mapped_refs).items() if count > 1)
    if duplicates:
        errors.append(f"bibliography parity: legacy references mapped more than once {duplicates}")
    legacy_refs = {record["ref"] for record in inventory}
    unknown_mapped = sorted(set(mapped_refs) - legacy_refs)
    unknown_removed = sorted(set(removal_refs) - legacy_refs)
    if unknown_mapped:
        errors.append(
            f"bibliography parity: mappings name unknown legacy references {unknown_mapped}"
        )
    if unknown_removed:
        errors.append(
            f"bibliography parity: removals name unknown legacy references {unknown_removed}"
        )
    overlap = sorted(set(mapped_refs) & set(removal_refs))
    if overlap:
        errors.append(f"bibliography parity: references are both mapped and removed {overlap}")
    unresolved = legacy_refs - set(mapped_refs) - set(removal_refs)
    if migration.get("complete") is True and unresolved:
        errors.append(
            f"bibliography parity: migration is complete but {len(unresolved)} references remain"
        )
    return errors


def parity(corpus: Path, graph: dict, language_graphs: dict[str, dict]) -> dict:
    inventory = legacy_inventory(corpus)
    known = {record["ref"] for record in inventory}
    uses = [
        *(graph.get("uses") or []),
        *(
            use
            for language_graph in language_graphs.values()
            for use in (language_graph.get("uses") or [])
        ),
    ]
    mapped = {ref for use in uses for ref in (use.get("legacy_refs") or [])}
    removed = {
        record["legacy_ref"] for record in (graph.get("migration") or {}).get("removals") or []
    }
    return {
        "legacy": len(known),
        "mapped": len(mapped),
        "removed": len(removed),
        "unmapped": len(known - mapped - removed),
        "sha256": legacy_digest(inventory),
        "complete": (graph.get("migration") or {}).get("complete") is True,
    }


def _project_work(work: dict) -> dict:
    return {key: work[key] for key in ("id", "responsible", "title") if key in work}


def _project_edition(edition: dict) -> dict:
    fields = (
        "id",
        "work",
        "recension",
        "title",
        "edition_statement",
        "contributors",
        "place",
        "publisher",
        "year",
        "volume",
        "publication_type",
        "authority",
        "rights",
    )
    return {key: edition[key] for key in fields if key in edition}


def _project_item(item: dict) -> dict:
    fields = (
        "id",
        "edition",
        "repository",
        "kind",
        "record_url",
        "scan_url",
        "revision",
        "access",
        "digitization_rights",
    )
    return {key: item[key] for key in fields if key in item}


def _project_use(use: dict) -> dict:
    fields = (
        "id",
        "edition",
        "digital_item",
        "role",
        "address",
        "locator",
        "claim",
        "verified_on",
    )
    return {key: use[key] for key in fields if key in use}


def _project_witness(witness: dict) -> dict:
    fields = ("id", "text", "use", "role", "coverage", "independence_basis")
    return {key: witness[key] for key in fields if key in witness}


def _project_collation(collation: dict) -> dict:
    fields = ("id", "text", "recension", "witnesses", "apparatus")
    return {key: collation[key] for key in fields if key in collation}


def _publishable(values: list[dict]) -> list[dict]:
    return [use for use in values if use.get("decision") in {"RETAIN", "RETAIN_WITH_CORRECTION"}]


def _retained_uses(graph: dict, language_graph: dict | None = None) -> list[dict]:
    """Return all publishable uses visible in a reader package."""
    return _publishable([*(graph.get("uses") or []), *((language_graph or {}).get("uses") or [])])


def _package_uses(graph: dict, language_graph: dict | None = None) -> list[dict]:
    """Return only the uses authored by one package.

    A language bibliography index combines the neutral and localized layers,
    but its per-text file contains only the localized layer.  The reading page
    can therefore load the neutral slice and one selected language slice
    without receiving the neutral evidence twice.
    """
    source = graph if language_graph is None else language_graph
    return _publishable(source.get("uses") or [])


def _catalog_for_uses(graph: dict, uses: list[dict], excluded: dict | None = None) -> dict:
    excluded = excluded or {"works": [], "editions": [], "digital_items": []}
    excluded_editions = {edition["id"] for edition in excluded["editions"]}
    excluded_works = {work["id"] for work in excluded["works"]}
    excluded_items = {item["id"] for item in excluded["digital_items"]}
    edition_ids = {use["edition"] for use in uses} - excluded_editions
    editions = [edition for edition in graph.get("editions") or [] if edition["id"] in edition_ids]
    work_ids = {edition["work"] for edition in editions} - excluded_works
    item_ids = {use["digital_item"] for use in uses} - excluded_items
    return {
        "schema_version": SCHEMA,
        "works": [
            _project_work(work) for work in graph.get("works") or [] if work["id"] in work_ids
        ],
        "editions": [_project_edition(edition) for edition in editions],
        "digital_items": [
            _project_item(item)
            for item in graph.get("digital_items") or []
            if item["id"] in item_ids
        ],
    }


def public_catalog(graph: dict) -> dict:
    """The neutral catalogue contains only identities reached by neutral uses."""
    return _catalog_for_uses(graph, _retained_uses(graph))


def public_catalog_delta(graph: dict, language_graph: dict) -> dict:
    """Identities needed by one language in addition to the neutral catalogue."""
    neutral = public_catalog(graph)
    return _catalog_for_uses(
        graph,
        _retained_uses({"uses": []}, language_graph),
        excluded=neutral,
    )


def _sort_text(value: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(char)
    )


def _edition_sort_key(edition: dict, works: dict[str, dict]) -> tuple[str, str, str, str]:
    work = works[edition["work"]]
    return (
        _sort_text(work.get("responsible") or work["title"]),
        _sort_text(work["title"]),
        _sort_text(edition["year"]),
        edition["id"],
    )


def public_index(graph: dict, language_graph: dict | None = None) -> dict:
    uses = _retained_uses(graph, language_graph)
    by_edition: dict[str, list[dict]] = defaultdict(list)
    for use in uses:
        by_edition[use["edition"]].append(use)
    works = {work["id"]: work for work in graph.get("works") or []}
    editions = {edition["id"]: edition for edition in graph.get("editions") or []}
    sections = []
    included_sections = (
        SECTION_ORDER
        if language_graph is not None
        else tuple(section for section in SECTION_ORDER if section != "wording_witnesses")
    )
    buckets: dict[str, list[dict]] = {section: [] for section in included_sections}
    for edition_id, edition_uses in by_edition.items():
        for section in included_sections:
            section_uses = [use for use in edition_uses if use["role"] in SECTION_ROLES[section]]
            if not section_uses:
                continue
            roles = sorted({use["role"] for use in section_uses}, key=ROLE_ORDER.__getitem__)
            uses_by_text: dict[str, list[dict]] = defaultdict(list)
            for use in section_uses:
                uses_by_text[use["address"]["text"]].append(use)
            buckets[section].append(
                {
                    "edition": edition_id,
                    "roles": roles,
                    "texts": [
                        {
                            "id": text_id,
                            "roles": sorted(
                                {use["role"] for use in text_uses},
                                key=ROLE_ORDER.__getitem__,
                            ),
                            "uses": len(text_uses),
                        }
                        for text_id, text_uses in sorted(uses_by_text.items())
                    ],
                }
            )
    for section in included_sections:
        entries = sorted(
            buckets[section],
            key=lambda entry: _edition_sort_key(editions[entry["edition"]], works),
        )
        sections.append({"id": section, "entries": entries})
    out = {"schema_version": SCHEMA, "sections": sections}
    if language_graph is not None:
        out["language"] = language_graph["language"]
    return out


def _text_source_groups(uses: list[dict], text_id: str) -> list[dict]:
    grouped: dict[tuple[str, str, str, str, str], list[dict]] = defaultdict(list)
    for use in uses:
        key = (
            use["edition"],
            use["digital_item"],
            use["role"],
            json.dumps(use["locator"], ensure_ascii=False, sort_keys=True),
            use.get("verified_on") or "",
        )
        grouped[key].append(use)
    records = []
    for key, grouped_uses in sorted(grouped.items()):
        edition, digital_item, role, _locator_key, verified_on = key
        entries = []
        for use in sorted(grouped_uses, key=lambda value: value["id"]):
            address = {key: value for key, value in use["address"].items() if key != "text"}
            entry = {"id": use["id"], "address": address, "claim": use["claim"]}
            entries.append(entry)
        record = {
            "edition": edition,
            "digital_item": digital_item,
            "role": role,
            "locator": grouped_uses[0]["locator"],
            "entries": entries,
        }
        if verified_on:
            record["verified_on"] = verified_on
        records.append(record)
    return records


def public_text_evidence(graph: dict, language_graph: dict | None = None) -> dict:
    """Return compact evidence slices, ready to write one file per text.

    Source identities live in the manifest-declared catalogue. Repeating the
    same edition and digital-item records in every text slice would make the
    lazy layout larger than its authored source without making it more useful.
    """
    uses = _package_uses(graph, language_graph)
    by_text: dict[str, list[dict]] = defaultdict(list)
    for use in uses:
        text_id = (use.get("address") or {}).get("text")
        if text_id:
            by_text[text_id].append(use)
    public_witnesses = [
        witness
        for witness in graph.get("witnesses") or []
        if language_graph is None and witness.get("use") in {use["id"] for use in uses}
    ]
    witnesses_by_text: dict[str, list[dict]] = defaultdict(list)
    for witness in public_witnesses:
        witnesses_by_text[witness["text"]].append(_project_witness(witness))
    collations = {
        collation["text"]: _project_collation(collation)
        for collation in graph.get("collations") or []
        if set(collation.get("witnesses") or []) <= {witness["id"] for witness in public_witnesses}
    }
    text_ids = sorted(set(by_text) | set(witnesses_by_text) | set(collations))
    records = []
    for text_id in text_ids:
        text_uses = sorted(by_text[text_id], key=lambda value: value["id"])
        record = {
            "id": text_id,
            "source_groups": _text_source_groups(text_uses, text_id),
            "witnesses": sorted(witnesses_by_text[text_id], key=lambda value: value["id"]),
        }
        if text_id in collations:
            record["collation"] = collations[text_id]
        if language_graph is not None:
            record["language"] = language_graph["language"]
        records.append(record)
    out = {"schema_version": SCHEMA, "texts": records}
    if language_graph is not None:
        out["language"] = language_graph["language"]
    return out
